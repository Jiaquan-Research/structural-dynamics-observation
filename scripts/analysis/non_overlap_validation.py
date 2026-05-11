"""A1 non-overlap validation for structural taxonomy on TEP."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

W = 100
STRIDES = [10, 50, 100]
FAULTS_TO_RUN = [0, 4, 6, 8, 12, 13, 14, 17, 18]
N_RUNS = 200
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
RETURN_K = 5
TYPICAL_MASS = 0.80


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


def _load_run_arrays(selected_columns, usecols, testing_path):
    normal_runs = _load_normal_runs(".", selected_columns)
    run_arrays = {0: _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)}
    for fault_number in FAULTS_TO_RUN:
        if fault_number == 0:
            continue
        fault_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        run_arrays[fault_number] = _prepare_run_arrays(fault_runs, selected_columns, N_RUNS)
    return run_arrays


def _summarize_basin_metrics(run_arrays, baseline_model, stride):
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
                stride,
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
    typical_edge_entropy = compute_typical_edge_entropy(typical_edges)
    edge_count = int(len(typical_edges))
    max_idx = int(np.argmax(stationary))
    max_occ = float(stationary[max_idx])
    stat_h = float(-np.sum(stationary * np.log(stationary + 1e-10)))
    stat_h_norm = float(stat_h / np.log(len(PAIR_LABELS)))
    trans_h = compute_transition_entropy(trans_matrix)
    self_loop_mass = float(np.trace(mass_matrix))
    taxonomy_class = _classify_taxonomy(edge_count, self_loop_mass)

    all_segments = []
    weighted_inside = 0
    weighted_exits = 0
    weighted_returns = 0
    for states in run_series:
        segments = _residence_segments(states, max_idx)
        all_segments.extend(segments)
        escape_rate, return_prob = _escape_and_return(states, max_idx, RETURN_K)
        inside_time = int(np.sum(states == max_idx))
        weighted_inside += inside_time
        if inside_time > 0 and np.isfinite(escape_rate):
            exits = int(round(escape_rate * inside_time))
            weighted_exits += exits
            if exits > 0 and np.isfinite(return_prob):
                weighted_returns += float(return_prob) * exits

    mean_residence_time = float(np.mean(all_segments)) if all_segments else np.nan
    escape_rate = float(weighted_exits / weighted_inside) if weighted_inside > 0 else np.nan
    return_probability = float(weighted_returns / weighted_exits) if weighted_exits > 0 else np.nan

    return {
        "max_stationary_occupancy": max_occ,
        "stationary_entropy": stat_h_norm,
        "transition_entropy": trans_h,
        "mean_residence_time": mean_residence_time,
        "escape_rate": escape_rate,
        "return_probability": return_probability,
        "edge_count": edge_count,
        "taxonomy_class": taxonomy_class,
        "typical_edge_entropy": typical_edge_entropy,
        "dominant_pair": PAIR_LABELS[max_idx],
    }


def _evaluate_shift(group):
    group = group.sort_values("stride")
    class_10 = str(group.loc[group["stride"] == 10, "taxonomy_class"].iloc[0])
    class_100 = str(group.loc[group["stride"] == 100, "taxonomy_class"].iloc[0])
    occ_10 = float(group.loc[group["stride"] == 10, "max_stationary_occupancy"].iloc[0])
    occ_100 = float(group.loc[group["stride"] == 100, "max_stationary_occupancy"].iloc[0])
    edge_10 = float(group.loc[group["stride"] == 10, "edge_count"].iloc[0])
    edge_100 = float(group.loc[group["stride"] == 100, "edge_count"].iloc[0])

    if class_10 == class_100 and occ_100 >= 0.8 * occ_10:
        return "survived"
    if occ_100 >= 0.5 * occ_10 and edge_100 <= max(5.0, 2.0 * edge_10):
        return "weakened"
    return "collapsed"


def _plot_stability(results_df, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(11, 15), constrained_layout=True)
    labels = {0: "NORMAL", 4: "F04", 6: "F06", 8: "F08", 12: "F12", 13: "F13", 14: "F14", 17: "F17", 18: "F18"}

    for fault_number, group in results_df.groupby("fault_number", sort=True):
        group = group.sort_values("stride")
        label = labels[int(fault_number)]
        axes[0].plot(group["stride"], group["max_stationary_occupancy"], marker="o", label=label)
        axes[1].plot(group["stride"], group["mean_residence_time"], marker="o", label=label)
        axes[2].plot(group["stride"], group["edge_count"], marker="o", label=label)

    axes[0].set_ylabel("occupancy")
    axes[1].set_ylabel("mean_residence_time")
    axes[2].set_ylabel("edge_count")
    axes[2].set_xlabel("stride")
    for ax in axes:
        ax.grid(alpha=0.3)
    axes[0].legend(ncol=3, fontsize=8)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_taxonomy_shift(results_df, output_path):
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = {10: "tab:blue", 50: "tab:orange", 100: "tab:green"}
    focus_faults = {6, 8, 12, 13, 14, 17, 18}

    for stride in STRIDES:
        group = results_df.loc[results_df["stride"] == stride]
        ax.scatter(
            group["max_stationary_occupancy"],
            group["stationary_entropy"],
            s=90,
            alpha=0.85,
            color=colors[stride],
            label=f"S={stride}",
        )
        for row in group.itertuples(index=False):
            if int(row.fault_number) in focus_faults:
                ax.text(
                    float(row.max_stationary_occupancy) + 0.006,
                    float(row.stationary_entropy) + 0.006,
                    f"{_fault_label(int(row.fault_number))}@{int(row.stride)}",
                    fontsize=8,
                )

    ax.set_xlabel("occupancy")
    ax.set_ylabel("stationary_entropy")
    ax.set_title("Non-overlap taxonomy shift")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    run_arrays = _load_run_arrays(selected_columns, usecols, testing_path)

    rows = []
    for stride in STRIDES:
        baseline_model = _build_baseline_model(baseline_data, W, stride)
        for fault_number in FAULTS_TO_RUN:
            metrics = _summarize_basin_metrics(run_arrays[fault_number], baseline_model, stride)
            rows.append(
                {
                    "fault_number": int(fault_number),
                    "stride": int(stride),
                    **metrics,
                }
            )

    results_df = pd.DataFrame(rows).sort_values(["fault_number", "stride"]).reset_index(drop=True)
    output_df = results_df[
        [
            "fault_number",
            "stride",
            "taxonomy_class",
            "max_stationary_occupancy",
            "stationary_entropy",
            "transition_entropy",
            "mean_residence_time",
            "escape_rate",
            "return_probability",
            "edge_count",
        ]
    ].copy()

    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "taxonomy").mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_ROOT / "csv" / "non_overlap_validation.csv", index=False, encoding="utf-8")
    _plot_stability(output_df, OUTPUT_ROOT / "taxonomy" / "non_overlap_stability.png")
    _plot_taxonomy_shift(output_df, OUTPUT_ROOT / "taxonomy" / "non_overlap_taxonomy_shift.png")

    labels = {0: "NORMAL", 4: "F04", 6: "F06", 8: "F08", 12: "F12", 13: "F13", 14: "F14", 17: "F17", 18: "F18"}
    shift_summary = {}
    for fault_number, group in output_df.groupby("fault_number", sort=True):
        label = labels[int(fault_number)]
        print(f"{label}:")
        for row in group.sort_values("stride").itertuples(index=False):
            print(
                f"  S={int(row.stride):<3} | {row.taxonomy_class:<22} | "
                f"occ={row.max_stationary_occupancy:.3f}"
            )
        shift_summary[label] = _evaluate_shift(group)

    print("\n=== OVERLAP SENSITIVITY SUMMARY ===")
    survived = [label for label, status in shift_summary.items() if status == "survived"]
    weakened = [label for label, status in shift_summary.items() if status == "weakened"]
    collapsed = [label for label, status in shift_summary.items() if status == "collapsed"]
    print(f"survived: {', '.join(survived) if survived else 'none'}")
    print(f"weakened: {', '.join(weakened) if weakened else 'none'}")
    print(f"collapsed: {', '.join(collapsed) if collapsed else 'none'}")
    return output_df


if __name__ == "__main__":
    main()
