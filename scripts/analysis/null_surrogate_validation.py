"""A2 null / surrogate validation for structural dynamics taxonomy."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from attractor_subgraph import (
    build_mass_matrix,
    compute_typical_edge_entropy,
    extract_typical_edge_set,
)
from basin_escape_dynamics import _escape_and_return, _residence_segments
from fault_stationary_scan import (
    build_transition_matrix,
    compute_stationary,
    compute_transition_entropy,
    _load_normal_runs,
)
from tep_experiment import (
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

W = 100
S = 100
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
TYPICAL_MASS = 0.80
RETURN_K = 5
N_RUNS = 200
RNG_SEED = 0

SOURCES = ["NORMAL", "F13", "WHITE_NOISE", "CORRELATED_GAUSSIAN"]


def _classify_taxonomy(edge_count, self_loop_mass):
    if edge_count <= 2 and self_loop_mass >= 0.9:
        return "single_edge_attractor"
    if edge_count <= 5:
        return "metastable_basin"
    if edge_count >= 20:
        return "diffuse_wandering"
    return "partial_locking"


def _prepare_run_arrays(run_frames, selected_columns, n_runs):
    arrays = {}
    for run_idx in range(1, n_runs + 1):
        run_df = run_frames.get(run_idx)
        if run_df is None:
            continue
        arrays[int(run_idx)] = run_df[selected_columns].to_numpy(dtype=float)
    return arrays


def _generate_white_noise_runs(n_runs, run_length, n_features, rng):
    return {
        run_idx: rng.normal(0.0, 1.0, size=(run_length, n_features))
        for run_idx in range(1, n_runs + 1)
    }


def _generate_correlated_gaussian_runs(n_runs, run_length, cov, rng):
    cov = np.asarray(cov, dtype=float)
    cov = cov + 1e-6 * np.eye(cov.shape[0], dtype=float)
    mean = np.zeros(cov.shape[0], dtype=float)
    return {
        run_idx: rng.multivariate_normal(mean, cov, size=run_length)
        for run_idx in range(1, n_runs + 1)
    }


def _build_source_metrics(run_arrays, baseline_model):
    counts = np.zeros((len(PAIR_LABELS), len(PAIR_LABELS)), dtype=float)
    run_series = []

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
        top1 = np.asarray(series["top1_indices"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        states = top1[mask]
        if len(states) < 2:
            continue
        run_series.append(states)
        for i, j in zip(states[:-1], states[1:]):
            counts[int(i), int(j)] += 1.0

    trans_matrix = build_transition_matrix(counts)
    stationary = compute_stationary(trans_matrix)
    stationary = stationary / max(float(stationary.sum()), 1e-12)
    mass_matrix = build_mass_matrix(trans_matrix, stationary)
    typical_edges = extract_typical_edge_set(mass_matrix, target_mass=TYPICAL_MASS)

    max_idx = int(np.argmax(stationary))
    max_occ = float(stationary[max_idx])
    dominant_pair = PAIR_LABELS[max_idx]
    stat_h = float(-np.sum(stationary * np.log(stationary + 1e-10)))
    stat_h_norm = float(stat_h / np.log(len(PAIR_LABELS)))
    trans_h = compute_transition_entropy(trans_matrix)
    self_loop_mass = float(np.trace(mass_matrix))
    taxonomy_class = _classify_taxonomy(int(len(typical_edges)), self_loop_mass)
    typical_edge_entropy = compute_typical_edge_entropy(typical_edges)

    all_segments = []
    weighted_inside = 0
    weighted_exits = 0
    weighted_returns = 0.0
    for states in run_series:
        segments = _residence_segments(states, max_idx)
        all_segments.extend(segments)
        escape_rate, return_prob = _escape_and_return(states, max_idx, RETURN_K)
        inside_time = int(np.sum(states == max_idx))
        weighted_inside += inside_time
        if inside_time > 0 and np.isfinite(escape_rate):
            exits = int(round(float(escape_rate) * inside_time))
            weighted_exits += exits
            if exits > 0 and np.isfinite(return_prob):
                weighted_returns += float(return_prob) * exits

    mean_residence_time = float(np.mean(all_segments)) if all_segments else np.nan
    escape_rate = float(weighted_exits / weighted_inside) if weighted_inside > 0 else np.nan
    return_probability = float(weighted_returns / weighted_exits) if weighted_exits > 0 else np.nan

    return {
        "taxonomy_class": taxonomy_class,
        "max_stationary_occupancy": max_occ,
        "stationary_entropy": stat_h_norm,
        "transition_entropy": trans_h,
        "mean_residence_time": mean_residence_time,
        "escape_rate": escape_rate,
        "return_probability": return_probability,
        "edge_count": int(len(typical_edges)),
        "typical_edge_entropy": typical_edge_entropy,
        "dominant_pair": dominant_pair,
    }


def _plot_taxonomy(results_df, output_path):
    fig, ax = plt.subplots(figsize=(9, 7))
    colors = {
        "NORMAL": "tab:gray",
        "F13": "tab:orange",
        "WHITE_NOISE": "tab:blue",
        "CORRELATED_GAUSSIAN": "tab:green",
    }
    for row in results_df.itertuples(index=False):
        ax.scatter(
            row.max_stationary_occupancy,
            row.stationary_entropy,
            s=160,
            color=colors[row.source],
            alpha=0.85,
            edgecolors="black",
        )
        ax.text(
            float(row.max_stationary_occupancy) + 0.006,
            float(row.stationary_entropy) + 0.006,
            row.source,
            fontsize=9,
        )
    ax.set_xlabel("max_stationary_occupancy")
    ax.set_ylabel("stationary_entropy")
    ax.set_title("Null / surrogate taxonomy comparison")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_metrics(results_df, output_path):
    fig, ax = plt.subplots(figsize=(11, 7))
    metrics = [
        ("max_stationary_occupancy", "occupancy"),
        ("edge_count_norm", "edge_count_norm"),
        ("stationary_entropy", "stationary_entropy"),
        ("mean_residence_norm", "mean_residence_norm"),
    ]
    x = np.arange(len(results_df))
    width = 0.18
    for idx, (column, label) in enumerate(metrics):
        ax.bar(x + (idx - 1.5) * width, results_df[column], width=width, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(results_df["source"].tolist(), rotation=20)
    ax.set_ylabel("normalized value")
    ax.set_title("Null / surrogate metric comparison")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded

    normal_runs = _load_normal_runs(".", selected_columns)
    normal_arrays = _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)
    fault_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    fault_arrays = _prepare_run_arrays(fault_runs, selected_columns, N_RUNS)

    first_normal_run = normal_arrays[min(normal_arrays)]
    run_length = int(first_normal_run.shape[0])
    n_features = int(first_normal_run.shape[1])

    rng = np.random.default_rng(RNG_SEED)
    normal_cov = np.cov(baseline_data, rowvar=False)

    white_baseline_runs = _generate_white_noise_runs(N_RUNS, run_length, n_features, rng)
    white_test_runs = _generate_white_noise_runs(N_RUNS, run_length, n_features, rng)
    corr_baseline_runs = _generate_correlated_gaussian_runs(N_RUNS, run_length, normal_cov, rng)
    corr_test_runs = _generate_correlated_gaussian_runs(N_RUNS, run_length, normal_cov, rng)

    normal_baseline_model = _build_baseline_model(baseline_data, W, S)
    fault_baseline_model = _build_baseline_model(baseline_data, W, S)
    white_baseline_data = np.vstack([white_baseline_runs[idx] for idx in sorted(white_baseline_runs)])
    corr_baseline_data = np.vstack([corr_baseline_runs[idx] for idx in sorted(corr_baseline_runs)])
    white_baseline_model = _build_baseline_model(white_baseline_data, W, S)
    corr_baseline_model = _build_baseline_model(corr_baseline_data, W, S)

    source_payloads = {
        "NORMAL": (normal_arrays, normal_baseline_model),
        "F13": (fault_arrays, fault_baseline_model),
        "WHITE_NOISE": (white_test_runs, white_baseline_model),
        "CORRELATED_GAUSSIAN": (corr_test_runs, corr_baseline_model),
    }

    rows = []
    for source in SOURCES:
        metrics = _build_source_metrics(*source_payloads[source])
        rows.append({"source": source, **metrics})

    results_df = pd.DataFrame(rows)
    results_df["edge_count_norm"] = results_df["edge_count"] / float(len(PAIR_LABELS) * len(PAIR_LABELS))
    max_res = float(results_df["mean_residence_time"].max()) if np.isfinite(results_df["mean_residence_time"]).any() else 1.0
    results_df["mean_residence_norm"] = results_df["mean_residence_time"] / max(max_res, 1e-12)

    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "taxonomy").mkdir(parents=True, exist_ok=True)
    results_df[
        [
            "source",
            "taxonomy_class",
            "max_stationary_occupancy",
            "stationary_entropy",
            "transition_entropy",
            "mean_residence_time",
            "escape_rate",
            "return_probability",
            "edge_count",
            "typical_edge_entropy",
            "dominant_pair",
        ]
    ].to_csv(OUTPUT_ROOT / "csv" / "null_surrogate_validation.csv", index=False, encoding="utf-8")

    _plot_taxonomy(results_df, OUTPUT_ROOT / "taxonomy" / "null_surrogate_taxonomy.png")
    _plot_metrics(results_df, OUTPUT_ROOT / "taxonomy" / "null_surrogate_metrics.png")

    for row in results_df.itertuples(index=False):
        print(f"{row.source}:")
        print(f"  class={row.taxonomy_class}")
        print(f"  occ={row.max_stationary_occupancy:.3f}")
        print(f"  edge_count={int(row.edge_count)}")
        print(f"  residence={row.mean_residence_time:.3f}")

    null_classes = results_df.set_index("source")["taxonomy_class"].to_dict()
    print("\n=== NULL VALIDATION SUMMARY ===")
    if any(
        null_classes[source] == "single_edge_attractor"
        for source in ("WHITE_NOISE", "CORRELATED_GAUSSIAN")
    ):
        print("FAIL: null data produced attractor-like structure")
        verdict = "failed"
    elif all(
        null_classes[source] == "diffuse_wandering"
        for source in ("WHITE_NOISE", "CORRELATED_GAUSSIAN")
    ):
        print("PASS: null data did not reproduce strong attractor structure")
        verdict = "passed"
    else:
        print("WARNING: null data produced partial structural concentration")
        verdict = "warning"

    return results_df, verdict


if __name__ == "__main__":
    main()
