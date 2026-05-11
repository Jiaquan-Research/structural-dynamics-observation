"""Transition-matrix analysis for structural trajectory records."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

PAIR_LABELS = [
    "XMEAS7-XMEAS8",
    "XMEAS7-XMEAS9",
    "XMEAS7-XMEAS10",
    "XMEAS7-XMEAS11",
    "XMEAS8-XMEAS9",
    "XMEAS8-XMEAS10",
    "XMEAS8-XMEAS11",
    "XMEAS9-XMEAS10",
    "XMEAS9-XMEAS11",
    "XMEAS10-XMEAS11",
]

INPUT_PATH = OUTPUT_ROOT / "csv" / "trajectory_records_F0_F4_F13_runs500.csv"
FAULT_ORDER = ["NORMAL", "F04", "F13"]
FAULT_COLORS = {"NORMAL": "gray", "F04": "tab:orange", "F13": "tab:blue"}


def build_transition_matrix(df_fault):
    """Build a 10x10 transition-probability matrix from one fault subset."""

    counts = np.zeros((len(PAIR_LABELS), len(PAIR_LABELS)), dtype=float)
    for _run_id, run_df in df_fault.groupby("run_id", sort=True):
        run_df = run_df.sort_values("sample")
        states = run_df["top_pair_idx"].to_numpy(dtype=int)
        if len(states) < 2:
            continue
        current = states[:-1]
        nxt = states[1:]
        for i, j in zip(current, nxt):
            counts[i, j] += 1.0

    row_sums = counts.sum(axis=1, keepdims=True)
    trans_matrix = np.zeros_like(counts)
    nonzero_rows = row_sums[:, 0] > 0
    trans_matrix[nonzero_rows] = counts[nonzero_rows] / row_sums[nonzero_rows]
    return trans_matrix


def compute_transition_entropy(trans_matrix):
    """Compute transition entropy using only nonzero rows/probabilities."""

    probs = np.asarray(trans_matrix, dtype=float)
    row_mask = probs.sum(axis=1) > 0
    if not np.any(row_mask):
        return 0.0
    masked = probs[row_mask]
    positive = masked > 0
    return float(-np.sum(masked[positive] * np.log(masked[positive] + 1e-10)))


def compute_stationary(trans_matrix):
    """Compute stationary distribution via power iteration."""

    n_states = trans_matrix.shape[0]
    pi = np.ones(n_states, dtype=float) / float(n_states)
    row_sums = trans_matrix.sum(axis=1, keepdims=True)
    safe_matrix = np.asarray(trans_matrix, dtype=float).copy()
    zero_rows = row_sums[:, 0] == 0
    if np.any(zero_rows):
        safe_matrix[zero_rows] = 1.0 / float(n_states)

    for _ in range(1000):
        pi = pi @ safe_matrix
        pi = pi / max(pi.sum(), 1e-12)
    return pi


def _active_submatrix(trans_matrix):
    """Return active rows/cols only for plotting."""

    row_active = trans_matrix.sum(axis=1) > 0
    col_active = trans_matrix.sum(axis=0) > 0
    active = row_active | col_active
    idx = np.where(active)[0]
    if len(idx) == 0:
        return trans_matrix[:1, :1], [PAIR_LABELS[0]], [0]
    return trans_matrix[np.ix_(idx, idx)], [PAIR_LABELS[i] for i in idx], idx.tolist()


def _plot_transition_heatmaps(matrices, entropies, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(12, 15), constrained_layout=True)

    for ax, fault_label in zip(axes, FAULT_ORDER):
        submatrix, labels, _idx = _active_submatrix(matrices[fault_label])
        image = ax.imshow(submatrix, cmap="viridis", vmin=0.0, vmax=1.0, aspect="auto")
        ax.set_xticks(np.arange(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_yticks(np.arange(len(labels)))
        ax.set_yticklabels(labels)
        ax.set_xlabel("next state")
        ax.set_ylabel("current state")
        ax.set_title(f"{fault_label} (H_trans={entropies[fault_label]:.3f})")

        for i in range(submatrix.shape[0]):
            for j in range(submatrix.shape[1]):
                value = submatrix[i, j]
                if value > 0:
                    ax.text(
                        j,
                        i,
                        f"{value:.2f}",
                        ha="center",
                        va="center",
                        color="white" if value > 0.5 else "black",
                        fontsize=8,
                    )

    fig.colorbar(image, ax=axes, shrink=0.75, label="transition probability")
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_entropy_bars(entropies, output_path):
    labels = FAULT_ORDER
    values = [entropies[label] for label in labels]
    colors = [FAULT_COLORS[label] for label in labels]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, values, color=colors, alpha=0.85)
    ax.set_ylabel("transition entropy")
    ax.set_title("Transition entropy comparison")
    ax.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_stationary_distributions(stationary_map, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(12, 14), constrained_layout=True)

    for ax, fault_label in zip(axes, FAULT_ORDER):
        stationary = stationary_map[fault_label]
        top_idx = int(np.argmax(stationary))
        bars = ax.bar(PAIR_LABELS, stationary, color=FAULT_COLORS[fault_label], alpha=0.85)
        ax.axhline(0.1, color="black", linestyle="--", linewidth=1.0, label="uniform=0.1")
        ax.set_ylabel("occupancy probability")
        ax.set_xticks(np.arange(len(PAIR_LABELS)))
        ax.set_xticklabels(PAIR_LABELS, rotation=45, ha="right")
        ax.set_title(
            f"{fault_label}: max={PAIR_LABELS[top_idx]} ({stationary[top_idx]:.3f})"
        )
        ax.grid(axis="y", alpha=0.3)

        for bar, value in zip(bars, stationary):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    input_path = Path(INPUT_PATH)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input CSV: {input_path}")

    df = pd.read_csv(input_path)
    df = df.loc[df["sample"] > 200].copy()

    matrices = {}
    entropies = {}
    stationary_map = {}
    for fault_label in FAULT_ORDER:
        df_fault = df.loc[df["fault_label"] == fault_label].copy()
        matrix = build_transition_matrix(df_fault)
        entropy = compute_transition_entropy(matrix)
        stationary = compute_stationary(matrix)
        matrices[fault_label] = matrix
        entropies[fault_label] = entropy
        stationary_map[fault_label] = stationary

    _plot_transition_heatmaps(matrices, entropies, OUTPUT_ROOT / "taxonomy" / "transition_heatmap.png")
    _plot_entropy_bars(entropies, OUTPUT_ROOT / "taxonomy" / "transition_entropy_comparison.png")
    _plot_stationary_distributions(stationary_map, OUTPUT_ROOT / "taxonomy" / "stationary_distribution.png")

    print(f"NORMAL transition entropy = {entropies['NORMAL']:.3f}")
    print(f"F04    transition entropy = {entropies['F04']:.3f}")
    print(f"F13    transition entropy = {entropies['F13']:.3f}")

    for fault_label in FAULT_ORDER:
        stationary = stationary_map[fault_label]
        top3_idx = np.argsort(stationary)[::-1][:3]
        print(f"{fault_label} stationary top-3:")
        for idx in top3_idx:
            print(f"  {PAIR_LABELS[int(idx)]}: {stationary[int(idx)]:.3f}")


if __name__ == "__main__":
    main()
