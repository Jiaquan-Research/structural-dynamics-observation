"""Multi-fault temporal surrogate validation on the original V5 pair-space."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import build_transition_matrix, compute_stationary, _load_normal_runs
from tep_experiment import (
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

FAULT_NUMBERS = [0, 4, 6, 8, 12, 13, 14, 17, 18]
W = 100
S = 100
N_RUNS = 200
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
BLOCK_SIZE = 100
SOFTMAX_T = 1.0
RNG_SEED = 0

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "temporal_surrogate_multifault.csv"
OUTPUT_DELTA = PROJECT_ROOT / "outputs" / "taxonomy" / "temporal_surrogate_multifault_delta.png"
OUTPUT_CLASS = PROJECT_ROOT / "outputs" / "taxonomy" / "temporal_scale_classification.png"

CLASS_COLORS = {
    "local-window dominated": "tab:red",
    "trajectory-sensitive": "tab:blue",
    "diffuse/no-signal": "tab:gray",
    "possible spectral artifact": "tab:orange",
    "ambiguous": "tab:green",
}


def _softmax_rows(values, temperature=1.0):
    values = np.asarray(values, dtype=float) / float(temperature)
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)


def _phase_randomize_1d(x, rng):
    x = np.asarray(x, dtype=float)
    n = len(x)
    spectrum = np.fft.rfft(x)
    amplitudes = np.abs(spectrum)
    phases = np.angle(spectrum)
    if len(phases) > 2:
        phases[1:-1] = rng.uniform(0.0, 2.0 * np.pi, size=len(phases) - 2)
    randomized = amplitudes * np.exp(1j * phases)
    return np.real(np.fft.irfft(randomized, n=n))


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
    order = np.arange(len(starts))
    rng.shuffle(order)
    blocks = []
    for idx in order:
        start = starts[idx]
        end = min(start + block_size, n)
        blocks.append(run_data[start:end])
    return np.vstack(blocks)


def _prepare_run_arrays(run_frames, selected_columns, n_runs=N_RUNS):
    arrays = {}
    for run_idx in range(1, n_runs + 1):
        run_df = run_frames.get(run_idx)
        if run_df is None:
            continue
        arrays[int(run_idx)] = run_df[selected_columns].to_numpy(dtype=float)
    return arrays


def _surrogate_run_map(run_arrays, method, seed_offset):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    output = {}
    for run_idx in sorted(run_arrays):
        if method == "phase":
            output[run_idx] = _phase_randomize_run(run_arrays[run_idx], rng)
        elif method == "block":
            output[run_idx] = _block_shuffle_run(run_arrays[run_idx], rng, block_size=BLOCK_SIZE)
        else:
            raise ValueError(f"Unknown method: {method}")
    return output


def _normalized_stationary_entropy(stationary):
    stationary = np.asarray(stationary, dtype=float)
    raw = float(-np.sum(stationary * np.log(stationary + 1e-10)))
    norm = raw / math.log(len(stationary))
    return raw, float(norm)


def _summarize_version(run_arrays, baseline_model):
    counts = np.zeros((10, 10), dtype=float)
    soft_top1_masses = []

    for run_idx in range(1, N_RUNS + 1):
        run_data = run_arrays.get(run_idx)
        if run_data is None:
            continue
        try:
            series = _compute_version_b_trajectory_series(
                run_data,
                W,
                S,
                K_TOP,
                N_HISTORY,
                baseline_model,
            )
        except ValueError:
            continue

        sample_times = np.asarray(series["sample_times"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        if not np.any(mask):
            continue

        contributions = np.asarray(series["per_pair_contribution"], dtype=float)[mask]
        probs = _softmax_rows(contributions, temperature=SOFTMAX_T)
        soft_top1_masses.append(np.max(probs, axis=1))

        states = np.asarray(series["top1_indices"], dtype=int)[mask]
        if len(states) >= 2:
            for i, j in zip(states[:-1], states[1:]):
                counts[int(i), int(j)] += 1.0

    if not soft_top1_masses:
        raise ValueError("No valid windows for this source/version.")

    top1_mass = float(np.mean(np.concatenate(soft_top1_masses, axis=0)))
    transition = build_transition_matrix(counts)
    stationary = compute_stationary(transition)
    stationary = stationary / max(float(stationary.sum()), 1e-12)
    raw_entropy, norm_entropy = _normalized_stationary_entropy(stationary)

    return {
        "mean_top1_mass": top1_mass,
        "normalized_entropy": norm_entropy,
        "effective_pair_count": float(np.exp(raw_entropy)),
    }


def _fault_label(fault_number):
    return "NORMAL" if int(fault_number) == 0 else f"F{int(fault_number):02d}"


def _classify_temporal_scale(real_mass, normal_mass, block_ratio, phase_ratio):
    if block_ratio >= 0.85:
        return "local-window dominated"
    if block_ratio <= 0.60:
        return "trajectory-sensitive"
    if real_mass < 0.30:
        return "diffuse/no-signal"
    if phase_ratio >= 0.85:
        return "possible spectral artifact"
    return "ambiguous"


def _plot_delta(results_df):
    fig, ax = plt.subplots(figsize=(12, 6))
    fault_order = FAULT_NUMBERS
    x = np.arange(len(fault_order))
    width = 0.25

    def _pick(version):
        values = []
        for fault in fault_order:
            value = results_df.loc[
                (results_df["fault_number"] == fault) & (results_df["version"] == version),
                "mean_top1_mass",
            ].iloc[0]
            values.append(float(value))
        return values

    ax.bar(x - width, _pick("REAL"), width=width, color="tab:blue", label="REAL")
    ax.bar(x, _pick("BLOCK_SHUFFLE"), width=width, color="tab:orange", label="BLOCK")
    ax.bar(x + width, _pick("PHASE_SURROGATE"), width=width, color="lightgray", edgecolor="black", label="PHASE")

    ax.set_xticks(x)
    ax.set_xticklabels([_fault_label(f) for f in fault_order], rotation=20)
    ax.set_ylabel("mean_top1_mass")
    ax.set_title("Temporal surrogate comparison by fault")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DELTA, dpi=150)
    plt.close(fig)


def _plot_classification(summary_df):
    fig, ax = plt.subplots(figsize=(10, 7))
    for row in summary_df.itertuples(index=False):
        ax.scatter(
            row.block_shuffle_retention_ratio,
            row.real_mean_top1_mass,
            s=120,
            color=CLASS_COLORS[row.temporal_scale_class],
            alpha=0.85,
            edgecolors="black",
        )
        ax.text(
            float(row.block_shuffle_retention_ratio) + 0.01,
            float(row.real_mean_top1_mass) + 0.01,
            _fault_label(int(row.fault_number)),
            fontsize=9,
        )
    ax.axvline(0.85, color="tab:red", linestyle="--", linewidth=1.2)
    ax.axvline(0.60, color="tab:blue", linestyle="--", linewidth=1.2)
    ax.axhline(0.30, color="tab:gray", linestyle="--", linewidth=1.2)
    ax.set_xlabel("block_shuffle_retention_ratio")
    ax.set_ylabel("REAL mean_top1_mass")
    ax.set_title("Temporal scale classification")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_CLASS, dpi=150)
    plt.close(fig)


def main():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, W, S)

    normal_runs = _load_normal_runs(".", selected_columns)
    normal_arrays = _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)

    rows = []
    summary_rows = []

    for fault_number in FAULT_NUMBERS:
        print(f"=== {_fault_label(fault_number)} running ===")
        if fault_number == 0:
            real_arrays = normal_arrays
        else:
            fault_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
            real_arrays = _prepare_run_arrays(fault_runs, selected_columns, N_RUNS)

        phase_arrays = _surrogate_run_map(real_arrays, method="phase", seed_offset=1000 + fault_number)
        block_arrays = _surrogate_run_map(real_arrays, method="block", seed_offset=2000 + fault_number)

        real_metrics = _summarize_version(real_arrays, baseline_model)
        phase_metrics = _summarize_version(phase_arrays, baseline_model)
        block_metrics = _summarize_version(block_arrays, baseline_model)

        block_ratio = float(block_metrics["mean_top1_mass"] / max(real_metrics["mean_top1_mass"], 1e-12))
        phase_ratio = float(phase_metrics["mean_top1_mass"] / max(real_metrics["mean_top1_mass"], 1e-12))
        normal_reference = float(real_metrics["mean_top1_mass"]) if fault_number == 0 else float(
            summary_rows[0]["real_mean_top1_mass"] if summary_rows else 0.0
        )
        temporal_class = _classify_temporal_scale(
            float(real_metrics["mean_top1_mass"]),
            float(normal_reference),
            block_ratio,
            phase_ratio,
        )

        for version, metrics in (
            ("REAL", real_metrics),
            ("BLOCK_SHUFFLE", block_metrics),
            ("PHASE_SURROGATE", phase_metrics),
        ):
            rows.append(
                {
                    "fault_number": int(fault_number),
                    "version": version,
                    "mean_top1_mass": float(metrics["mean_top1_mass"]),
                    "normalized_entropy": float(metrics["normalized_entropy"]),
                    "effective_pair_count": float(metrics["effective_pair_count"]),
                    "block_shuffle_retention_ratio": block_ratio,
                    "phase_surrogate_retention_ratio": phase_ratio,
                    "temporal_scale_class": temporal_class,
                }
            )

        summary_rows.append(
            {
                "fault_number": int(fault_number),
                "real_mean_top1_mass": float(real_metrics["mean_top1_mass"]),
                "block_shuffle_retention_ratio": block_ratio,
                "phase_surrogate_retention_ratio": phase_ratio,
                "temporal_scale_class": temporal_class,
            }
        )

        print(
            f"{_fault_label(fault_number)} REAL={real_metrics['mean_top1_mass']:.3f}\n"
            f"     BLOCK={block_metrics['mean_top1_mass']:.3f}(×{block_ratio:.2f})\n"
            f"     PHASE={phase_metrics['mean_top1_mass']:.3f}(×{phase_ratio:.2f})\n"
            f"     class={temporal_class}"
        )

    results_df = pd.DataFrame(rows)
    summary_df = pd.DataFrame(summary_rows).sort_values("fault_number").reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DELTA.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    _plot_delta(results_df)
    _plot_classification(summary_df)
    return results_df, summary_df


if __name__ == "__main__":
    main()
