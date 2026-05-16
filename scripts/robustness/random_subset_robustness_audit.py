"""Random-subset robustness audit for F13 concentration."""

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
    _collect_window_features,
    _differenced_correlation_features,
    _load_all_fault_runs,
    _resolve_paths,
    _score_features,
)

W = 100
S = 100
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
SOFTMAX_T = 1.0
N_RUNS = 200
RNG = np.random.default_rng(42)
SUBSET_SIZES = [5, 8]
N_SUBSETS = 100

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "random_subset_robustness.csv"
OUTPUT_DIST = PROJECT_ROOT / "outputs" / "taxonomy" / "random_subset_distribution.png"
OUTPUT_DELTA = PROJECT_ROOT / "outputs" / "taxonomy" / "random_subset_delta_distribution.png"
OUTPUT_SCATTER = PROJECT_ROOT / "outputs" / "taxonomy" / "random_subset_scatter.png"


def _candidate_xmeas_columns(columns):
    lower_map = {c.lower(): c for c in columns}
    resolved = []
    for idx in range(1, 42):
        key = f"xmeas_{idx}"
        if key in lower_map:
            resolved.append(lower_map[key])
    return resolved


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


def _mean_top1_mass(run_arrays, baseline_model):
    masses = []
    for run_idx in range(1, N_RUNS + 1):
        run_data = run_arrays.get(run_idx)
        if run_data is None:
            continue
        try:
            series = _compute_continuous_series(run_data, baseline_model)
        except ValueError:
            continue
        mask = series["sample_times"] > SAMPLE_FILTER
        if not np.any(mask):
            continue
        contributions = np.asarray(series["per_pair_contribution"], dtype=float)[mask]
        probs = _softmax_rows(contributions, temperature=SOFTMAX_T)
        masses.append(np.max(probs, axis=1))
    if not masses:
        raise ValueError("No valid windows produced.")
    return float(np.mean(np.concatenate(masses, axis=0)))


def _load_full_data():
    training_path, testing_path = _resolve_paths(".")
    if training_path is None or testing_path is None:
        raise FileNotFoundError("请先从Kaggle下载TEP CSV数据集")

    header = pd.read_csv(training_path, nrows=0).columns.tolist()
    xmeas_cols = _candidate_xmeas_columns(header)
    if len(xmeas_cols) < 41:
        raise ValueError(f"Expected 41 XMEAS columns, found {len(xmeas_cols)}")

    training_df = pd.read_csv(training_path, usecols=xmeas_cols)
    normal_runs = _load_normal_runs(".", xmeas_cols)
    usecols = ["faultNumber", "simulationRun", "sample", *xmeas_cols]
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    return xmeas_cols, training_df, normal_runs, f13_runs


def _sample_subsets(xmeas_cols):
    subsets = []
    used = set()
    for subset_size in SUBSET_SIZES:
        count = 0
        while count < N_SUBSETS:
            choice = tuple(sorted(RNG.choice(xmeas_cols, size=subset_size, replace=False).tolist()))
            if (subset_size, choice) in used:
                continue
            used.add((subset_size, choice))
            subsets.append((subset_size, count + 1, list(choice)))
            count += 1
    return subsets


def _plot_distribution(results_df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for ax, subset_size in zip(axes, SUBSET_SIZES):
        group = results_df.loc[results_df["subset_size"] == subset_size]
        ax.hist(group["normal_mass"], bins=20, alpha=0.5, label="NORMAL", color="tab:gray")
        ax.hist(group["f13_mass"], bins=20, alpha=0.5, label="F13", color="tab:orange")
        ax.set_title(f"V{subset_size}")
        ax.set_xlabel("mean_top1_mass")
        ax.set_ylabel("count")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.savefig(OUTPUT_DIST, dpi=150)
    plt.close(fig)


def _plot_delta(results_df):
    fig, ax = plt.subplots(figsize=(10, 6))
    for subset_size, color in zip(SUBSET_SIZES, ("tab:blue", "tab:green")):
        group = results_df.loc[results_df["subset_size"] == subset_size]
        ax.hist(group["delta_mass"], bins=20, alpha=0.5, label=f"V{subset_size}", color=color)
    ax.set_xlabel("delta_mass")
    ax.set_ylabel("count")
    ax.set_title("Random subset delta distribution")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DELTA, dpi=150)
    plt.close(fig)


def _plot_scatter(results_df):
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = {5: "tab:blue", 8: "tab:green"}
    for subset_size in SUBSET_SIZES:
        group = results_df.loc[results_df["subset_size"] == subset_size]
        ax.scatter(
            group["normal_mass"],
            group["f13_mass"],
            alpha=0.7,
            color=colors[subset_size],
            label=f"V{subset_size}",
        )
    min_val = float(min(results_df["normal_mass"].min(), results_df["f13_mass"].min()))
    max_val = float(max(results_df["normal_mass"].max(), results_df["f13_mass"].max()))
    ax.plot([min_val, max_val], [min_val, max_val], linestyle="--", color="black", linewidth=1.2)
    ax.set_xlabel("NORMAL_mass")
    ax.set_ylabel("F13_mass")
    ax.set_title("Random subset separation scatter")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_SCATTER, dpi=150)
    plt.close(fig)


def main():
    xmeas_cols, training_df, normal_runs, f13_runs = _load_full_data()
    subsets = _sample_subsets(xmeas_cols)

    rows = []
    for subset_size, subset_id, variables in subsets:
        selected = list(variables)
        baseline_data = training_df[selected].to_numpy(dtype=float)
        baseline_model = _build_baseline_model(baseline_data, W, S)

        normal_arrays = _prepare_run_arrays(normal_runs, selected, N_RUNS)
        f13_arrays = _prepare_run_arrays(f13_runs, selected, N_RUNS)

        normal_mass = _mean_top1_mass(normal_arrays, baseline_model)
        f13_mass = _mean_top1_mass(f13_arrays, baseline_model)
        delta_mass = float(f13_mass - normal_mass)
        retention_ratio = float(f13_mass / (normal_mass + 1e-10))

        rows.append(
            {
                "subset_size": int(subset_size),
                "subset_id": int(subset_id),
                "variables": ",".join(selected),
                "normal_mass": normal_mass,
                "f13_mass": f13_mass,
                "delta_mass": delta_mass,
                "retention_ratio": retention_ratio,
            }
        )

    results_df = pd.DataFrame(rows).sort_values(["subset_size", "subset_id"]).reset_index(drop=True)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIST.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    _plot_distribution(results_df)
    _plot_delta(results_df)
    _plot_scatter(results_df)

    print("=== RANDOM SUBSET ROBUSTNESS SUMMARY ===")
    for subset_size in SUBSET_SIZES:
        group = results_df.loc[results_df["subset_size"] == subset_size]
        print(f"\nV{subset_size}:")
        print(f"mean F13 mass = {group['f13_mass'].mean():.6f}")
        print(f"mean NORMAL mass = {group['normal_mass'].mean():.6f}")
        print(f"mean delta = {group['delta_mass'].mean():.6f}")
        print(f"high concentration rate = {float((group['f13_mass'] > 0.5).mean()):.6f}")
        print(f"strong separation rate = {float((group['delta_mass'] > 0.3).mean()):.6f}")

    top5 = results_df.sort_values("f13_mass", ascending=False).head(5)
    bottom5 = results_df.sort_values("f13_mass", ascending=True).head(5)

    print("\nTOP 5 subsets:")
    for row in top5.itertuples(index=False):
        print(
            f"subset_size={row.subset_size} subset_id={row.subset_id} "
            f"variables={row.variables} F13_mass={row.f13_mass:.6f} delta={row.delta_mass:.6f}"
        )

    print("\nBOTTOM 5 subsets:")
    for row in bottom5.itertuples(index=False):
        print(
            f"subset_size={row.subset_size} subset_id={row.subset_id} "
            f"variables={row.variables} F13_mass={row.f13_mass:.6f} delta={row.delta_mass:.6f}"
        )

    return results_df


if __name__ == "__main__":
    main()
