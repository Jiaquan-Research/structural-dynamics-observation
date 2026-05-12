"""P1 temporal surrogate validation for structural concentration."""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import _load_normal_runs
from tep_experiment import (
    _build_baseline_model,
    _collect_window_features,
    _differenced_correlation_features,
    _load_all_fault_runs,
    _load_baseline_and_columns,
    _score_features,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

W = 100
S = 100
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
N_RUNS = 200
SOFTMAX_T = 1.0
BLOCK_SIZE = 50
RNG_SEED = 0


def _prepare_run_arrays(run_frames, selected_columns, n_runs):
    arrays = {}
    for run_idx in range(1, n_runs + 1):
        run_df = run_frames.get(run_idx)
        if run_df is None:
            continue
        arrays[int(run_idx)] = run_df[selected_columns].to_numpy(dtype=float)
    return arrays


def _softmax_rows(values, temperature=1.0):
    values = np.asarray(values, dtype=float) / float(temperature)
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)


def _cosine_similarity_rows(a, b):
    numerator = np.sum(a * b, axis=1)
    denominator = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    denominator = np.where(denominator <= 0.0, 1e-12, denominator)
    return numerator / denominator


def _compute_continuous_series(run_data, baseline_model):
    sample_times = list(range(W, len(run_data) + 1, S))
    if not sample_times:
        raise ValueError("No valid windows.")
    features = _collect_window_features(
        run_data,
        sample_times,
        W,
        _differenced_correlation_features,
    )
    d2_values = _score_features(features, baseline_model["mu_b"], baseline_model["s_b_inv"])
    centered = features - baseline_model["mu_b"]
    contributions = (centered**2) * np.diag(baseline_model["s_b_inv"])
    return {
        "sample_times": np.asarray(sample_times, dtype=int),
        "d2_b": d2_values,
        "per_pair_contribution": contributions,
    }


def _phase_randomize_1d(x, rng):
    x = np.asarray(x, dtype=float)
    n = len(x)
    spectrum = np.fft.rfft(x)
    amplitudes = np.abs(spectrum)
    phases = np.angle(spectrum)
    if len(spectrum) > 2:
        random_phases = rng.uniform(0.0, 2.0 * np.pi, size=len(spectrum) - 2)
        phases[1:-1] = random_phases
    randomized = amplitudes * np.exp(1j * phases)
    out = np.fft.irfft(randomized, n=n)
    return np.real(out)


def _phase_randomize_run(run_data, rng):
    run_data = np.asarray(run_data, dtype=float)
    output = np.empty_like(run_data)
    for col in range(run_data.shape[1]):
        output[:, col] = _phase_randomize_1d(run_data[:, col], rng)
    return output


def _block_shuffle_run(run_data, rng, block_size=BLOCK_SIZE):
    run_data = np.asarray(run_data, dtype=float)
    n = run_data.shape[0]
    starts = list(range(0, n, block_size))
    block_indices = list(range(len(starts)))
    rng.shuffle(block_indices)
    shuffled_blocks = []
    for idx in block_indices:
        start = starts[idx]
        end = min(start + block_size, n)
        shuffled_blocks.append(run_data[start:end])
    return np.vstack(shuffled_blocks)


def _surrogate_run_map(run_arrays, method, seed_offset):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    output = {}
    for run_idx in sorted(run_arrays):
        if method == "phase":
            output[run_idx] = _phase_randomize_run(run_arrays[run_idx], rng)
        elif method == "block_shuffle":
            output[run_idx] = _block_shuffle_run(run_arrays[run_idx], rng, block_size=BLOCK_SIZE)
        else:
            raise ValueError(f"Unknown surrogate method: {method}")
    return output


def _surrogate_baseline_data(baseline_data, method, seed_offset):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    # Use surrogate-transformed NORMAL baseline data for surrogate baselines.
    # This avoids train/test leakage and avoids using fault-specific baseline structure.
    if method == "phase":
        return _phase_randomize_run(baseline_data, rng)
    if method == "block_shuffle":
        return _block_shuffle_run(baseline_data, rng, block_size=BLOCK_SIZE)
    raise ValueError(f"Unknown surrogate method: {method}")


def _summarize_source(run_arrays, baseline_model):
    soft_vectors = []
    temporal_values = []

    for run_idx in range(1, N_RUNS + 1):
        run_data = run_arrays.get(run_idx)
        if run_data is None:
            continue
        try:
            series = _compute_continuous_series(run_data, baseline_model)
        except ValueError:
            continue
        sample_times = np.asarray(series["sample_times"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        if not np.any(mask):
            continue

        contributions = np.asarray(series["per_pair_contribution"], dtype=float)[mask]
        probs = _softmax_rows(contributions, temperature=SOFTMAX_T)
        soft_vectors.append(probs)
        if len(probs) >= 2:
            temporal_values.append(_cosine_similarity_rows(probs[:-1], probs[1:]))

    if not soft_vectors:
        raise ValueError("No valid soft-state windows produced.")

    probs_all = np.vstack(soft_vectors)
    pair_count = int(probs_all.shape[1])
    top_sorted = np.sort(probs_all, axis=1)[:, ::-1]
    top1 = top_sorted[:, 0]
    top2 = np.maximum(top_sorted[:, 1], 1e-12)
    entropy_raw = -np.sum(probs_all * np.log(probs_all + 1e-12), axis=1)
    entropy_norm = entropy_raw / math.log(pair_count)
    effective_pair_count = np.exp(entropy_raw)
    temporal_stability = (
        float(np.mean(np.concatenate(temporal_values, axis=0)))
        if temporal_values
        else float("nan")
    )

    return {
        "mean_top1_mass": float(np.mean(top1)),
        "normalized_entropy": float(np.mean(entropy_norm)),
        "effective_pair_count": float(np.mean(effective_pair_count)),
        "concentration_ratio": float(np.mean(top1 / top2)),
        "temporal_stability": temporal_stability,
        "pair_count": pair_count,
    }


def _plot_entropy(results_df, output_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {
        "NORMAL_REAL": "tab:gray",
        "F13_REAL": "tab:orange",
        "F13_PHASE_SURROGATE": "tab:blue",
        "F13_BLOCK_SHUFFLE": "tab:red",
        "NORMAL_PHASE_SURROGATE": "tab:green",
    }
    for row in results_df.itertuples(index=False):
        ax.scatter(
            row.mean_top1_mass,
            row.normalized_entropy,
            s=160,
            color=colors[row.source],
            alpha=0.85,
            edgecolors="black",
        )
        ax.text(
            float(row.mean_top1_mass) + 0.01,
            float(row.normalized_entropy) + 0.01,
            row.source,
            fontsize=8,
        )
    ax.set_xlabel("mean_top1_mass")
    ax.set_ylabel("normalized_entropy")
    ax.set_title("Temporal surrogate entropy comparison")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_effective_pairs(results_df, output_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(results_df["source"], results_df["effective_pair_count"], color="tab:blue", alpha=0.85)
    ax.set_ylabel("effective_pair_count")
    ax.set_title("Temporal surrogate effective pair count")
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_concentration(results_df, output_path):
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(results_df))
    width = 0.35
    ax.bar(x - width / 2.0, results_df["mean_top1_mass"], width=width, label="mean_top1_mass", alpha=0.85)
    ax.bar(x + width / 2.0, results_df["normalized_entropy"], width=width, label="normalized_entropy", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(results_df["source"], rotation=20)
    ax.set_title("Temporal surrogate concentration comparison")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    started = time.time()
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded

    normal_runs = _load_normal_runs(".", selected_columns)
    normal_arrays = _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    f13_arrays = _prepare_run_arrays(f13_runs, selected_columns, N_RUNS)

    normal_baseline_model = _build_baseline_model(baseline_data, W, S)

    phase_baseline = _surrogate_baseline_data(baseline_data, method="phase", seed_offset=1000)
    block_baseline = _surrogate_baseline_data(baseline_data, method="block_shuffle", seed_offset=2000)
    phase_baseline_model = _build_baseline_model(phase_baseline, W, S)
    block_baseline_model = _build_baseline_model(block_baseline, W, S)

    f13_phase_arrays = _surrogate_run_map(f13_arrays, method="phase", seed_offset=3000)
    f13_block_arrays = _surrogate_run_map(f13_arrays, method="block_shuffle", seed_offset=4000)
    normal_phase_arrays = _surrogate_run_map(normal_arrays, method="phase", seed_offset=5000)

    sources = [
        ("NORMAL_REAL", "real", normal_arrays, normal_baseline_model),
        ("F13_REAL", "real", f13_arrays, normal_baseline_model),
        ("F13_PHASE_SURROGATE", "phase_randomized", f13_phase_arrays, phase_baseline_model),
        ("F13_BLOCK_SHUFFLE", "block_shuffle", f13_block_arrays, block_baseline_model),
        ("NORMAL_PHASE_SURROGATE", "phase_randomized", normal_phase_arrays, phase_baseline_model),
    ]

    rows = []
    for source, surrogate_type, run_arrays, baseline_model in sources:
        metrics = _summarize_source(run_arrays, baseline_model)
        rows.append(
            {
                "source": source,
                "surrogate_type": surrogate_type,
                **metrics,
                "n_runs": N_RUNS,
                "W": W,
                "S": S,
            }
        )

    results_df = pd.DataFrame(rows)
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "taxonomy").mkdir(parents=True, exist_ok=True)
    results_df[
        [
            "source",
            "surrogate_type",
            "mean_top1_mass",
            "normalized_entropy",
            "effective_pair_count",
            "concentration_ratio",
            "temporal_stability",
            "n_runs",
            "W",
            "S",
        ]
    ].to_csv(OUTPUT_ROOT / "csv" / "temporal_surrogate_validation.csv", index=False, encoding="utf-8")

    _plot_entropy(results_df, OUTPUT_ROOT / "taxonomy" / "temporal_surrogate_entropy.png")
    _plot_effective_pairs(results_df, OUTPUT_ROOT / "taxonomy" / "temporal_surrogate_effective_pairs.png")
    _plot_concentration(results_df, OUTPUT_ROOT / "taxonomy" / "temporal_surrogate_concentration.png")

    print(
        results_df[
            [
                "source",
                "mean_top1_mass",
                "normalized_entropy",
                "effective_pair_count",
                "temporal_stability",
            ]
        ].to_string(index=False)
    )

    f13_real = results_df.loc[results_df["source"] == "F13_REAL"].iloc[0]
    null_like_sources = ["F13_PHASE_SURROGATE", "F13_BLOCK_SHUFFLE", "NORMAL_PHASE_SURROGATE"]
    approaches = []
    equals_or_exceeds = []
    for source_name in null_like_sources:
        row = results_df.loc[results_df["source"] == source_name].iloc[0]
        if (
            float(row["mean_top1_mass"]) >= 0.75 * float(f13_real["mean_top1_mass"])
            or float(row["normalized_entropy"]) <= float(f13_real["normalized_entropy"]) * 1.25
        ):
            approaches.append(source_name)
        if (
            float(row["mean_top1_mass"]) >= float(f13_real["mean_top1_mass"])
            or float(row["normalized_entropy"]) <= float(f13_real["normalized_entropy"])
        ):
            equals_or_exceeds.append(source_name)

    print("\n=== TEMPORAL SURROGATE SUMMARY ===")
    if equals_or_exceeds:
        print("FAIL: surrogate reproduced F13-like concentration.")
        verdict = "fail"
    elif approaches:
        if "F13_PHASE_SURROGATE" in approaches:
            print("WARNING: spectral/autocorrelation structure may explain much of F13 concentration.")
        if "F13_BLOCK_SHUFFLE" in approaches:
            print("WARNING: local temporal structure may explain much of F13 concentration.")
        if "NORMAL_PHASE_SURROGATE" in approaches:
            print("WARNING: normal temporal surrogate produced partial concentration.")
        verdict = "warning"
    else:
        print("PASS: F13 concentration not reproduced by tested temporal surrogates.")
        verdict = "pass"

    runtime_seconds = time.time() - started
    return results_df, verdict, runtime_seconds


if __name__ == "__main__":
    main()
