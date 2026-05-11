"""Fault stationary / transition taxonomy scan on TEP data."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tep_experiment import (
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

FAULT_NUMBERS = [0] + list(range(1, 21))
W = 100
S = 10
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200


def compute_stationary(trans_matrix):
    """Compute stationary distribution from the dominant eigenvector."""

    matrix = np.asarray(trans_matrix, dtype=float)
    n_states = matrix.shape[0]
    safe = matrix.copy()
    row_sums = safe.sum(axis=1, keepdims=True)
    zero_rows = row_sums[:, 0] == 0
    if np.any(zero_rows):
        safe[zero_rows] = 1.0 / float(n_states)

    eigenvalues, eigenvectors = np.linalg.eig(safe.T)
    idx = int(np.argmin(np.abs(eigenvalues - 1.0)))
    vec = np.real(eigenvectors[:, idx])
    vec = np.abs(vec)
    if vec.sum() <= 0:
        vec = np.ones(n_states, dtype=float)
    pi = vec / vec.sum()
    return pi


def compute_transition_entropy(trans_matrix):
    """Compute transition entropy over nonzero probabilities only."""

    probs = np.asarray(trans_matrix, dtype=float)
    positive = probs > 0
    return float(-np.sum(probs[positive] * np.log(probs[positive] + 1e-10)))


def build_transition_matrix(counts):
    """Row-normalize transition counts; zero rows become uniform."""

    counts = np.asarray(counts, dtype=float)
    n_states = counts.shape[0]
    row_sums = counts.sum(axis=1, keepdims=True)
    probs = np.zeros_like(counts)
    nonzero = row_sums[:, 0] > 0
    probs[nonzero] = counts[nonzero] / row_sums[nonzero]
    probs[~nonzero] = 1.0 / float(n_states)
    return probs


def _load_normal_runs(data_dir, selected_columns):
    normal_candidates = [
        (DATA_ROOT if Path(data_dir) == Path(".") else Path(data_dir)) / "fault_free_testing.csv",
        (DATA_ROOT if Path(data_dir) == Path(".") else Path(data_dir)) / "Fault_Free_Testing.csv",
    ]
    normal_path = next((path for path in normal_candidates if path.exists()), None)
    if normal_path is None:
        raise FileNotFoundError("请先从Kaggle下载TEP CSV数据集")

    df = pd.read_csv(normal_path, usecols=["simulationRun", "sample", *selected_columns])
    runs = {}
    for run_id, run_df in df.groupby("simulationRun", sort=True):
        runs[int(run_id)] = run_df.sort_values("sample")
    return runs


def _fault_label(fault_number):
    return "NORMAL" if fault_number == 0 else f"F{int(fault_number):02d}"


def _accumulate_counts_for_runs(runs, selected_columns, baseline_model, n_runs):
    counts = np.zeros((len(PAIR_LABELS), len(PAIR_LABELS)), dtype=float)
    for run_idx in range(1, n_runs + 1):
        run_df = runs.get(run_idx)
        if run_df is None:
            continue
        run_data = run_df[selected_columns].to_numpy(dtype=float)
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
        for i, j in zip(states[:-1], states[1:]):
            counts[int(i), int(j)] += 1.0
    return counts


def _plot_stationary_heatmap(summary_df, occupancy_matrix, output_path):
    fig, ax = plt.subplots(figsize=(14, 6))
    image = ax.imshow(occupancy_matrix, aspect="auto", cmap="viridis", origin="lower")
    ax.set_xticks(np.arange(len(summary_df)))
    ax.set_xticklabels(
        ["0"] + [str(int(f)) for f in summary_df["fault_number"].to_numpy()[1:]],
        rotation=45,
        ha="right",
    )
    ax.set_yticks(np.arange(len(PAIR_LABELS)))
    ax.set_yticklabels(PAIR_LABELS)
    ax.set_xlabel("fault number")
    ax.set_ylabel("pair")
    ax.set_title("Stationary occupancy by fault")
    fig.colorbar(image, ax=ax, label="stationary occupancy")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_taxonomy(summary_df, output_path):
    fig, ax = plt.subplots(figsize=(10, 7))
    sizes = summary_df["max_stationary_occupancy"].to_numpy(dtype=float) * 1200.0
    colors = summary_df["transition_entropy"].to_numpy(dtype=float)

    non_normal = summary_df["fault_number"] != 0
    normal = summary_df["fault_number"] == 0

    scatter = ax.scatter(
        summary_df.loc[non_normal, "stationary_entropy_norm"],
        summary_df.loc[non_normal, "diagonal_mass"],
        s=sizes[non_normal.to_numpy()],
        c=colors[non_normal.to_numpy()],
        cmap="viridis",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.7,
    )
    ax.scatter(
        summary_df.loc[normal, "stationary_entropy_norm"],
        summary_df.loc[normal, "diagonal_mass"],
        s=sizes[normal.to_numpy()],
        c=colors[normal.to_numpy()],
        cmap="viridis",
        alpha=0.95,
        edgecolors="gray",
        linewidths=2.0,
    )

    for row in summary_df.itertuples(index=False):
        label = "N" if int(row.fault_number) == 0 else f"F{int(row.fault_number):02d}"
        ax.text(
            float(row.stationary_entropy_norm) + 0.005,
            float(row.diagonal_mass) + 0.002,
            label,
            fontsize=9,
        )

    ax.set_xlabel("stationary_entropy_norm")
    ax.set_ylabel("diagonal_mass")
    ax.set_title("Fault structural taxonomy")
    ax.grid(alpha=0.3)
    fig.colorbar(scatter, ax=ax, label="transition entropy")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, W, S)

    normal_runs = _load_normal_runs(".", selected_columns)

    summary_rows = []
    occupancy_columns = []

    for fault_number in FAULT_NUMBERS:
        fault_label = _fault_label(fault_number)
        if fault_number == 0:
            print("=== NORMAL running ===")
            runs = normal_runs
        else:
            print(f"=== F{fault_number:02d} running ===")
            runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)

        counts = _accumulate_counts_for_runs(runs, selected_columns, baseline_model, n_runs=500)
        trans_matrix = build_transition_matrix(counts)
        stationary = compute_stationary(trans_matrix)
        stationary = stationary / max(stationary.sum(), 1e-12)

        max_idx = int(np.argmax(stationary))
        max_pair = PAIR_LABELS[max_idx]
        max_occ = float(stationary[max_idx])
        stat_h = float(-np.sum(stationary * np.log(stationary + 1e-10)))
        stat_h_norm = float(stat_h / np.log(len(PAIR_LABELS)))
        trans_h = compute_transition_entropy(trans_matrix)
        diag_mass = float(np.trace(trans_matrix) / len(PAIR_LABELS))

        occupancy_columns.append(stationary)
        summary_rows.append(
            {
                "fault_number": int(fault_number),
                "max_stationary_pair": max_pair,
                "max_stationary_occupancy": max_occ,
                "stationary_entropy": stat_h,
                "stationary_entropy_norm": stat_h_norm,
                "transition_entropy": trans_h,
                "diagonal_mass": diag_mass,
            }
        )

        prefix = "NORMAL" if fault_number == 0 else f"F{fault_number:02d}"
        print(
            f"{prefix} | "
            f"max_pair={max_pair} | "
            f"max_occ={max_occ:.3f} | "
            f"stat_H={stat_h_norm:.3f} | "
            f"trans_H={trans_h:.3f} | "
            f"diag={diag_mass:.3f}"
        )

    summary_df = pd.DataFrame(summary_rows)
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_ROOT / "csv" / "fault_stationary_summary.csv", index=False, encoding="utf-8")

    occupancy_matrix = np.column_stack(occupancy_columns)
    _plot_stationary_heatmap(summary_df, occupancy_matrix, OUTPUT_ROOT / "taxonomy" / "fault_stationary_heatmap.png")
    _plot_taxonomy(summary_df, OUTPUT_ROOT / "taxonomy" / "fault_taxonomy.png")
    return summary_df


if __name__ == "__main__":
    main()
