"""Cross-seed stability audit for F13 observability subspaces."""

from __future__ import annotations

import itertools
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

from random_subset_robustness_audit import (
    _load_full_data,
    _mean_top1_mass,
    _prepare_run_arrays,
)
from tep_experiment import _build_baseline_model

W = 100
S = 100
SAMPLE_FILTER = 200
SOFTMAX_T = 1.0
N_RUNS = 200
SUBSET_SIZES = [5, 8]
SEEDS = [1, 2, 3, 4, 5]
N_SUBSETS = 100
CORE_VARS = [
    "xmeas_7",
    "xmeas_11",
    "xmeas_18",
    "xmeas_19",
]

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "multiseed_variable_stability.csv"
OUTPUT_CORE_CSV = PROJECT_ROOT / "outputs" / "csv" / "core_variable_stability_summary.csv"
OUTPUT_CORE_FIG = PROJECT_ROOT / "outputs" / "taxonomy" / "core_variable_stability.png"
OUTPUT_TOP10_FIG = PROJECT_ROOT / "outputs" / "taxonomy" / "top10_frequency.png"
OUTPUT_JACCARD_FIG = PROJECT_ROOT / "outputs" / "taxonomy" / "jaccard_similarity_matrix.png"


def _sample_seed_subsets(xmeas_cols, seed):
    rng = np.random.default_rng(seed)
    subsets = []
    used = set()
    for subset_size in SUBSET_SIZES:
        count = 0
        while count < N_SUBSETS:
            choice = tuple(sorted(rng.choice(xmeas_cols, size=subset_size, replace=False).tolist()))
            if (subset_size, choice) in used:
                continue
            used.add((subset_size, choice))
            subsets.append((subset_size, count + 1, list(choice)))
            count += 1
    return subsets


def _strong_subset_mask(df):
    return (df["delta_mass"] > 0.30) | (df["f13_mass"] > 0.50)


def _compute_seed_subset_results(training_df, normal_runs, f13_runs, subsets):
    rows = []
    for subset_size, subset_id, variables in subsets:
        baseline_data = training_df[variables].to_numpy(dtype=float)
        baseline_model = _build_baseline_model(baseline_data, W, S)
        normal_arrays = _prepare_run_arrays(normal_runs, variables, N_RUNS)
        f13_arrays = _prepare_run_arrays(f13_runs, variables, N_RUNS)
        normal_mass = _mean_top1_mass(normal_arrays, baseline_model)
        f13_mass = _mean_top1_mass(f13_arrays, baseline_model)
        rows.append(
            {
                "subset_size": int(subset_size),
                "subset_id": int(subset_id),
                "variables": list(variables),
                "normal_mass": float(normal_mass),
                "f13_mass": float(f13_mass),
                "delta_mass": float(f13_mass - normal_mass),
            }
        )
    return pd.DataFrame(rows)


def _variable_stats_for_group(seed, subset_size, results_df, all_variables):
    group = results_df.loc[results_df["subset_size"] == subset_size].copy()
    strong = group.loc[_strong_subset_mask(group)]

    frequency = dict.fromkeys(all_variables, 0)
    delta_values = {var: [] for var in all_variables}

    for row in group.itertuples(index=False):
        for variable in row.variables:
            delta_values[variable].append(float(row.delta_mass))
    for row in strong.itertuples(index=False):
        for variable in row.variables:
            frequency[variable] += 1

    rows = []
    for variable in all_variables:
        avg_delta = float(np.mean(delta_values[variable])) if delta_values[variable] else 0.0
        rows.append(
            {
                "seed": int(seed),
                "subset_size": int(subset_size),
                "variable": variable,
                "frequency": int(frequency[variable]),
                "average_delta_mass": avg_delta,
            }
        )

    stats_df = pd.DataFrame(rows)
    stats_df = stats_df.sort_values(
        ["frequency", "average_delta_mass", "variable"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    top10_variables = set(stats_df.head(10)["variable"].tolist())
    stats_df["top10_flag"] = stats_df["variable"].isin(top10_variables).astype(int)
    return stats_df, stats_df.head(10).copy()


def _jaccard_similarity(set_a, set_b):
    union = set_a | set_b
    if not union:
        return 1.0
    return float(len(set_a & set_b) / len(union))


def _build_jaccard_tables(top10_map):
    rows = []
    matrices = {}
    for subset_size in SUBSET_SIZES:
        matrix = np.zeros((len(SEEDS), len(SEEDS)), dtype=float)
        for i, seed_i in enumerate(SEEDS):
            for j, seed_j in enumerate(SEEDS):
                score = _jaccard_similarity(
                    top10_map[(subset_size, seed_i)],
                    top10_map[(subset_size, seed_j)],
                )
                matrix[i, j] = score
                if i < j:
                    rows.append(
                        {
                            "subset_size": int(subset_size),
                            "seed_i": int(seed_i),
                            "seed_j": int(seed_j),
                            "jaccard_similarity": score,
                        }
                    )
        matrices[subset_size] = matrix
    return pd.DataFrame(rows), matrices


def _plot_core_variable_stability(core_summary):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, subset_size in zip(axes, SUBSET_SIZES):
        group = core_summary.loc[core_summary["subset_size"] == subset_size]
        ax.bar(
            group["variable"],
            group["mean_average_delta_mass"],
            yerr=group["std_average_delta_mass"],
            color="tab:blue",
            alpha=0.85,
            capsize=4,
        )
        ax.set_title(f"V{subset_size}")
        ax.set_xlabel("core variable")
        ax.set_ylabel("mean average_delta_mass")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", alpha=0.3)
    fig.savefig(OUTPUT_CORE_FIG, dpi=150)
    plt.close(fig)


def _plot_top10_frequency(summary_df):
    top_summary = (
        summary_df.groupby(["subset_size", "variable"], as_index=False)["top10_flag"]
        .sum()
        .rename(columns={"top10_flag": "top10_frequency"})
        .sort_values(["subset_size", "top10_frequency", "variable"], ascending=[True, False, True])
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    for ax, subset_size in zip(axes, SUBSET_SIZES):
        group = top_summary.loc[top_summary["subset_size"] == subset_size].head(15)
        ax.bar(group["variable"], group["top10_frequency"], color="tab:orange", alpha=0.85)
        ax.set_title(f"V{subset_size} top10 frequency")
        ax.set_xlabel("variable")
        ax.set_ylabel("times in seed top10")
        ax.tick_params(axis="x", rotation=60)
        ax.grid(axis="y", alpha=0.3)
    fig.savefig(OUTPUT_TOP10_FIG, dpi=150)
    plt.close(fig)


def _plot_jaccard_heatmaps(matrices):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, subset_size in zip(axes, SUBSET_SIZES):
        matrix = matrices[subset_size]
        image = ax.imshow(matrix, vmin=0.0, vmax=1.0, cmap="Blues")
        ax.set_title(f"V{subset_size} top10 Jaccard")
        ax.set_xticks(range(len(SEEDS)), labels=[str(seed) for seed in SEEDS])
        ax.set_yticks(range(len(SEEDS)), labels=[str(seed) for seed in SEEDS])
        ax.set_xlabel("seed")
        ax.set_ylabel("seed")
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=axes, shrink=0.9, label="Jaccard similarity")
    fig.savefig(OUTPUT_JACCARD_FIG, dpi=150)
    plt.close(fig)


def main():
    xmeas_cols, training_df, normal_runs, f13_runs = _load_full_data()

    all_stats = []
    top10_map = {}
    seed_level_top10 = []

    for seed in SEEDS:
        print(f"=== seed {seed} running ===")
        subsets = _sample_seed_subsets(xmeas_cols, seed)
        results_df = _compute_seed_subset_results(training_df, normal_runs, f13_runs, subsets)
        for subset_size in SUBSET_SIZES:
            stats_df, top10_df = _variable_stats_for_group(
                seed,
                subset_size,
                results_df,
                xmeas_cols,
            )
            all_stats.append(stats_df)
            top10_map[(subset_size, seed)] = set(top10_df["variable"].tolist())
            seed_level_top10.append(top10_df.assign(seed=seed, subset_size=subset_size))

    summary_df = pd.concat(all_stats, axis=0, ignore_index=True)
    top10_seed_df = pd.concat(seed_level_top10, axis=0, ignore_index=True)
    jaccard_df, jaccard_matrices = _build_jaccard_tables(top10_map)

    core_summary = (
        summary_df.loc[summary_df["variable"].isin(CORE_VARS)]
        .groupby(["subset_size", "variable"], as_index=False)
        .agg(
            top10_frequency=("top10_flag", "sum"),
            mean_frequency=("frequency", "mean"),
            std_frequency=("frequency", "std"),
            mean_average_delta_mass=("average_delta_mass", "mean"),
            std_average_delta_mass=("average_delta_mass", "std"),
        )
        .sort_values(["subset_size", "mean_average_delta_mass"], ascending=[True, False])
        .reset_index(drop=True)
    )

    summary_df = summary_df.sort_values(["subset_size", "seed", "variable"]).reset_index(drop=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CORE_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CORE_FIG.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    core_summary.to_csv(OUTPUT_CORE_CSV, index=False, encoding="utf-8")

    _plot_core_variable_stability(core_summary)
    _plot_top10_frequency(summary_df)
    _plot_jaccard_heatmaps(jaccard_matrices)

    print("=== MULTISEED VARIABLE STABILITY SUMMARY ===")
    for subset_size in SUBSET_SIZES:
        subset_jaccard = jaccard_df.loc[jaccard_df["subset_size"] == subset_size, "jaccard_similarity"]
        mean_jaccard = float(subset_jaccard.mean()) if not subset_jaccard.empty else float("nan")
        print(f"\nV{subset_size}:")
        print(f"mean_jaccard_similarity = {mean_jaccard:.6f}")
        print("Core variables:")
        core_group = core_summary.loc[core_summary["subset_size"] == subset_size]
        for variable in CORE_VARS:
            row = core_group.loc[core_group["variable"] == variable]
            if row.empty:
                continue
            item = row.iloc[0]
            print(
                f"{variable}: top10_frequency = {int(item['top10_frequency'])}/5 "
                f"mean_delta = {item['mean_average_delta_mass']:.6f} "
                f"std_delta = {0.0 if pd.isna(item['std_average_delta_mass']) else item['std_average_delta_mass']:.6f} "
                f"mean_frequency = {item['mean_frequency']:.3f} "
                f"std_frequency = {0.0 if pd.isna(item['std_frequency']) else item['std_frequency']:.3f}"
            )

        top_stable = (
            summary_df.loc[summary_df["subset_size"] == subset_size]
            .groupby("variable", as_index=False)
            .agg(
                top10_frequency=("top10_flag", "sum"),
                mean_average_delta_mass=("average_delta_mass", "mean"),
            )
            .sort_values(["top10_frequency", "mean_average_delta_mass", "variable"], ascending=[False, False, True])
            .head(10)
        )
        print("Top stable variables:")
        for row in top_stable.itertuples(index=False):
            print(
                f"{row.variable}: top10_frequency={int(row.top10_frequency)}/5 "
                f"mean_delta={row.mean_average_delta_mass:.6f}"
            )

    return {
        "summary_df": summary_df,
        "core_summary": core_summary,
        "jaccard_df": jaccard_df,
        "top10_seed_df": top10_seed_df,
    }


if __name__ == "__main__":
    main()
