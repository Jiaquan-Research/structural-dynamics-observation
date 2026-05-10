"""Robustness sweep for structural taxonomy under parameter changes."""

from __future__ import annotations

import itertools
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from attractor_subgraph import (
    build_mass_matrix,
    compute_typical_edge_entropy,
    extract_typical_edge_set,
)
from fault_stationary_scan import (
    build_transition_matrix,
    compute_stationary,
    _fault_label,
    _load_normal_runs,
)
from tep_experiment import (
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)


W_VALUES = [80, 100, 150]
S_VALUES = [5, 10, 20]
TYPICAL_MASS_VALUES = [0.75, 0.80, 0.90]
FAULTS_TO_RUN = [0, 4, 6, 8, 12, 13, 14, 15, 16, 17, 18]
N_RUNS = 200
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200

CLASS_COLORS = {
    "single_edge_attractor": "tab:blue",
    "metastable_basin": "tab:orange",
    "diffuse_wandering": "tab:gray",
    "partial_locking": "tab:green",
}


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


def _accumulate_counts_for_runs_param(run_arrays, baseline_model, W, S, n_runs):
    counts = np.zeros((len(PAIR_LABELS), len(PAIR_LABELS)), dtype=float)
    for run_idx in range(1, n_runs + 1):
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
        for i, j in zip(states[:-1], states[1:]):
            counts[int(i), int(j)] += 1.0
    return counts


def _load_all_run_arrays(selected_columns, usecols, testing_path):
    normal_runs = _load_normal_runs(".", selected_columns)
    run_arrays = {0: _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)}
    for fault_number in FAULTS_TO_RUN:
        if fault_number == 0:
            continue
        fault_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        run_arrays[fault_number] = _prepare_run_arrays(fault_runs, selected_columns, N_RUNS)
    return run_arrays


def _plot_robustness(summary_df, taxonomy_df, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(12, 16), constrained_layout=True)

    ax = axes[0]
    for cls, color in CLASS_COLORS.items():
        cls_df = taxonomy_df.loc[taxonomy_df["taxonomy_class"] == cls]
        if cls_df.empty:
            continue
        ax.errorbar(
            cls_df["mean_edge_count"],
            cls_df["mean_self_loop_mass"],
            xerr=cls_df["std_edge_count"],
            yerr=cls_df["std_self_loop_mass"],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=1.0,
            capsize=3,
            label=cls,
        )
        for row in cls_df.itertuples(index=False):
            label = "NORMAL" if int(row.fault_number) == 0 else f"F{int(row.fault_number):02d}"
            ax.text(float(row.mean_edge_count) + 0.2, float(row.mean_self_loop_mass) + 0.005, label, fontsize=8)
    ax.set_xlabel("mean_edge_count")
    ax.set_ylabel("mean_self_loop_mass")
    ax.grid(alpha=0.3)
    ax.legend()

    ax = axes[1]
    for cls, color in CLASS_COLORS.items():
        cls_df = taxonomy_df.loc[taxonomy_df["taxonomy_class"] == cls]
        if cls_df.empty:
            continue
        ax.scatter(
            cls_df["mean_max_occ"],
            cls_df["mean_stationary_entropy"],
            color=color,
            alpha=0.85,
            label=cls,
        )
        for row in cls_df.itertuples(index=False):
            label = "NORMAL" if int(row.fault_number) == 0 else f"F{int(row.fault_number):02d}"
            ax.text(float(row.mean_max_occ) + 0.005, float(row.mean_stationary_entropy) + 0.005, label, fontsize=8)
    ax.set_xlabel("mean_max_occ")
    ax.set_ylabel("mean_stationary_entropy")
    ax.grid(alpha=0.3)

    ax = axes[2]
    labels = ["NORMAL" if f == 0 else f"F{int(f):02d}" for f in taxonomy_df["fault_number"].tolist()]
    values = taxonomy_df["classification_consistency"].to_numpy(dtype=float)
    colors = [CLASS_COLORS[cls] for cls in taxonomy_df["taxonomy_class"].tolist()]
    bars = ax.bar(labels, values, color=colors, alpha=0.85)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("classification consistency")
    ax.grid(axis="y", alpha=0.3)
    ax.tick_params(axis="x", rotation=45)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    run_arrays = _load_all_run_arrays(selected_columns, usecols, testing_path)

    rows = []
    param_grid = list(itertools.product(W_VALUES, S_VALUES, TYPICAL_MASS_VALUES))
    total = len(param_grid)
    for idx, (W, S, typical_mass) in enumerate(param_grid, start=1):
        print(f"Setting {idx}/{total}: W={W}, S={S}, typical_mass={typical_mass:.2f}")
        baseline_model = _build_baseline_model(baseline_data, W, S)
        for fault_number in FAULTS_TO_RUN:
            counts = _accumulate_counts_for_runs_param(
                run_arrays[fault_number], baseline_model, W, S, N_RUNS
            )
            trans_matrix = build_transition_matrix(counts)
            stationary = compute_stationary(trans_matrix)
            stationary = stationary / max(float(stationary.sum()), 1e-12)
            mass_matrix = build_mass_matrix(trans_matrix, stationary)
            typical_edges = extract_typical_edge_set(mass_matrix, target_mass=typical_mass)

            max_idx = int(np.argmax(stationary))
            max_occ = float(stationary[max_idx])
            stat_h = float(-np.sum(stationary * np.log(stationary + 1e-10)))
            stat_h_norm = float(stat_h / np.log(len(PAIR_LABELS)))
            edge_count = int(len(typical_edges))
            edge_entropy = compute_typical_edge_entropy(typical_edges)
            self_loop_mass = float(np.trace(mass_matrix))
            cycle_mass = float(1.0 - self_loop_mass)
            taxonomy_class = _classify_taxonomy(edge_count, self_loop_mass)

            rows.append(
                {
                    "fault_number": int(fault_number),
                    "W": int(W),
                    "S": int(S),
                    "typical_mass": float(typical_mass),
                    "max_stationary_occupancy": max_occ,
                    "stationary_entropy_norm": stat_h_norm,
                    "typical_edge_count": edge_count,
                    "typical_edge_entropy": edge_entropy,
                    "self_loop_mass": self_loop_mass,
                    "cycle_mass": cycle_mass,
                    "dominant_pair": PAIR_LABELS[max_idx],
                    "taxonomy_class": taxonomy_class,
                }
            )

    summary_df = pd.DataFrame(rows)
    summary_df.to_csv("robustness_summary.csv", index=False, encoding="utf-8")

    taxonomy_rows = []
    for fault_number, group in summary_df.groupby("fault_number", sort=True):
        class_counts = Counter(group["taxonomy_class"].tolist())
        taxonomy_class, class_count = class_counts.most_common(1)[0]
        consistency = float(class_count / len(group))
        taxonomy_rows.append(
            {
                "fault_number": int(fault_number),
                "mean_max_occ": float(group["max_stationary_occupancy"].mean()),
                "std_max_occ": float(group["max_stationary_occupancy"].std(ddof=1)),
                "mean_edge_count": float(group["typical_edge_count"].mean()),
                "std_edge_count": float(group["typical_edge_count"].std(ddof=1)),
                "mean_self_loop_mass": float(group["self_loop_mass"].mean()),
                "std_self_loop_mass": float(group["self_loop_mass"].std(ddof=1)),
                "mean_stationary_entropy": float(group["stationary_entropy_norm"].mean()),
                "std_stationary_entropy": float(group["stationary_entropy_norm"].std(ddof=1)),
                "taxonomy_class": taxonomy_class,
                "classification_consistency": consistency,
            }
        )

    taxonomy_df = pd.DataFrame(taxonomy_rows).sort_values("fault_number")
    taxonomy_df.to_csv("robustness_taxonomy.csv", index=False, encoding="utf-8")
    _plot_robustness(summary_df, taxonomy_df, "robustness_stability.png")

    for row in taxonomy_df.itertuples(index=False):
        label = "NORMAL" if int(row.fault_number) == 0 else f"F{int(row.fault_number):02d}"
        print(
            f"{label} | class={row.taxonomy_class}\n"
            f"     consistency={row.classification_consistency:.2f}\n"
            f"     edge_count={row.mean_edge_count:.1f}\u00b1{row.std_edge_count:.1f}\n"
            f"     self={row.mean_self_loop_mass:.2f}\u00b1{row.std_self_loop_mass:.2f}"
        )
    return summary_df, taxonomy_df


if __name__ == "__main__":
    main()
