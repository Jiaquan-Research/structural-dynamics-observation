"""Column-shuffle temporal-dependency validation on the original V5 pair-space."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import _load_normal_runs
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

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "column_shuffle_validation.csv"
OUTPUT_COMPARISON = PROJECT_ROOT / "outputs" / "taxonomy" / "column_shuffle_comparison.png"
OUTPUT_MAP = PROJECT_ROOT / "outputs" / "taxonomy" / "temporal_dependency_map.png"

CLASS_COLORS = {
    "strong temporal dependence": "tab:blue",
    "local-window structure": "tab:orange",
    "distribution-dominated": "tab:red",
    "diffuse/no-signal": "tab:gray",
    "mixed": "tab:green",
}


def _fault_label(fault_number):
    return "NORMAL" if int(fault_number) == 0 else f"F{int(fault_number):02d}"


def _prepare_run_arrays(run_frames, selected_columns, n_runs=N_RUNS):
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


def _column_shuffle_run(run_data, rng):
    output = np.asarray(run_data, dtype=float).copy()
    for col in range(output.shape[1]):
        rng.shuffle(output[:, col])
    return output


def _surrogate_run_map(run_arrays, method, seed_offset):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    output = {}
    for run_idx in sorted(run_arrays):
        if method == "block":
            output[run_idx] = _block_shuffle_run(run_arrays[run_idx], rng, block_size=BLOCK_SIZE)
        elif method == "column":
            output[run_idx] = _column_shuffle_run(run_arrays[run_idx], rng)
        else:
            raise ValueError(f"Unknown method: {method}")
    return output


def _summarize_version(run_arrays, baseline_model):
    soft_top1_masses = []
    entropy_values = []

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
        entropy_values.append(-np.sum(probs * np.log(probs + 1e-12), axis=1) / math.log(probs.shape[1]))

    if not soft_top1_masses:
        raise ValueError("No valid windows for this source/version.")

    mean_top1_mass = float(np.mean(np.concatenate(soft_top1_masses, axis=0)))
    entropy_all = np.concatenate(entropy_values, axis=0)
    mean_entropy = float(np.mean(entropy_all))
    effective_pair_count = float(np.exp(np.mean(entropy_all) * math.log(10)))

    return {
        "mean_top1_mass": mean_top1_mass,
        "normalized_entropy": mean_entropy,
        "effective_pair_count": effective_pair_count,
    }


def _classify_temporal_dependency(real_mass, block_ratio, column_ratio):
    if real_mass < 0.30:
        return "diffuse/no-signal"
    if column_ratio <= 0.40:
        return "strong temporal dependence"
    if block_ratio >= 0.85 and column_ratio <= 0.60:
        return "local-window structure"
    if column_ratio >= 0.85:
        return "distribution-dominated"
    return "mixed"


def _plot_comparison(results_df):
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
    ax.bar(x + width, _pick("COLUMN_SHUFFLE"), width=width, color="lightgray", edgecolor="black", label="COLUMN")
    ax.set_xticks(x)
    ax.set_xticklabels([_fault_label(f) for f in fault_order], rotation=20)
    ax.set_ylabel("mean_top1_mass")
    ax.set_title("Column-shuffle comparison by fault")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_COMPARISON, dpi=150)
    plt.close(fig)


def _plot_dependency_map(summary_df):
    fig, ax = plt.subplots(figsize=(10, 7))
    for row in summary_df.itertuples(index=False):
        ax.scatter(
            row.column_retention_ratio,
            row.real_mean_top1_mass,
            s=120,
            color=CLASS_COLORS[row.temporal_dependency_class],
            alpha=0.85,
            edgecolors="black",
        )
        ax.text(
            float(row.column_retention_ratio) + 0.01,
            float(row.real_mean_top1_mass) + 0.01,
            _fault_label(int(row.fault_number)),
            fontsize=9,
        )
    ax.axvline(0.40, color="tab:blue", linestyle="--", linewidth=1.2)
    ax.axvline(0.60, color="tab:orange", linestyle="--", linewidth=1.2)
    ax.axvline(0.85, color="tab:red", linestyle="--", linewidth=1.2)
    ax.axhline(0.30, color="tab:gray", linestyle="--", linewidth=1.2)
    ax.set_xlabel("column_retention_ratio")
    ax.set_ylabel("REAL mean_top1_mass")
    ax.set_title("Temporal dependency map")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_MAP, dpi=150)
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

        block_arrays = _surrogate_run_map(real_arrays, method="block", seed_offset=1000 + fault_number)
        column_arrays = _surrogate_run_map(real_arrays, method="column", seed_offset=2000 + fault_number)

        real_metrics = _summarize_version(real_arrays, baseline_model)
        block_metrics = _summarize_version(block_arrays, baseline_model)
        column_metrics = _summarize_version(column_arrays, baseline_model)

        block_ratio = float(block_metrics["mean_top1_mass"] / max(real_metrics["mean_top1_mass"], 1e-12))
        column_ratio = float(column_metrics["mean_top1_mass"] / max(real_metrics["mean_top1_mass"], 1e-12))
        temporal_class = _classify_temporal_dependency(
            float(real_metrics["mean_top1_mass"]),
            block_ratio,
            column_ratio,
        )

        for version, metrics in (
            ("REAL", real_metrics),
            ("BLOCK_SHUFFLE", block_metrics),
            ("COLUMN_SHUFFLE", column_metrics),
        ):
            rows.append(
                {
                    "fault_number": int(fault_number),
                    "version": version,
                    "mean_top1_mass": float(metrics["mean_top1_mass"]),
                    "normalized_entropy": float(metrics["normalized_entropy"]),
                    "effective_pair_count": float(metrics["effective_pair_count"]),
                    "block_retention_ratio": block_ratio,
                    "column_retention_ratio": column_ratio,
                    "temporal_dependency_class": temporal_class,
                }
            )

        summary_rows.append(
            {
                "fault_number": int(fault_number),
                "real_mean_top1_mass": float(real_metrics["mean_top1_mass"]),
                "block_retention_ratio": block_ratio,
                "column_retention_ratio": column_ratio,
                "temporal_dependency_class": temporal_class,
            }
        )

        print(
            f"{_fault_label(fault_number)} REAL={real_metrics['mean_top1_mass']:.3f}\n"
            f"     BLOCK={block_metrics['mean_top1_mass']:.3f}(×{block_ratio:.2f})\n"
            f"     COLUMN={column_metrics['mean_top1_mass']:.3f}(×{column_ratio:.2f})\n"
            f"     class={temporal_class}"
        )

    results_df = pd.DataFrame(rows)
    summary_df = pd.DataFrame(summary_rows).sort_values("fault_number").reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_COMPARISON.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    _plot_comparison(results_df)
    _plot_dependency_map(summary_df)

    print("\n=== COLUMN SHUFFLE SUMMARY ===")
    for target_class in (
        "strong temporal dependence",
        "distribution-dominated",
        "mixed",
        "local-window structure",
        "diffuse/no-signal",
    ):
        labels = [
            _fault_label(int(row.fault_number))
            for row in summary_df.itertuples(index=False)
            if row.temporal_dependency_class == target_class
        ]
        if labels:
            print(f"{target_class}: {', '.join(labels)}")

    print("\nConservative interpretation:")
    print("- This experiment tests whether concentration depends on temporal ordering, not whether the framework is correct.")
    print("- Faults with low column-retention ratios are more consistent with genuine temporal dependence.")
    print("- Faults with high column-retention ratios are more consistent with static-distribution or non-trajectory explanations.")
    print("- Intermediate cases should not be overinterpreted.")
    return results_df, summary_df


if __name__ == "__main__":
    main()
