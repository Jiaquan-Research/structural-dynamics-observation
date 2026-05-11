"""A3 soft-state / continuous representation validation."""

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

from fault_stationary_scan import _load_normal_runs
from tep_experiment import (
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
N_RUNS = 200
SOFTMAX_T = 1.0

SOURCES = ["NORMAL", "F13", "F12"]


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
    denom = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    denom = np.where(denom <= 0.0, 1e-12, denom)
    return numerator / denom


def _summarize_source(run_arrays, baseline_model):
    soft_vectors = []
    temporal_values = []

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
        soft_vectors.append(probs)
        if len(probs) >= 2:
            temporal_values.append(_cosine_similarity_rows(probs[:-1], probs[1:]))

    if not soft_vectors:
        raise ValueError("No valid soft-state windows produced.")

    probs_all = np.vstack(soft_vectors)
    top_sorted = np.sort(probs_all, axis=1)[:, ::-1]
    top1 = top_sorted[:, 0]
    top2 = np.maximum(top_sorted[:, 1], 1e-12)
    entropy_raw = -np.sum(probs_all * np.log(probs_all + 1e-12), axis=1)
    entropy_norm = entropy_raw / np.log(probs_all.shape[1])
    effective_pair_count = np.exp(entropy_raw)
    temporal_stability = (
        float(np.mean(np.concatenate(temporal_values, axis=0)))
        if temporal_values
        else float("nan")
    )

    return {
        "mean_top1_mass": float(np.mean(top1)),
        "mean_entropy": float(np.mean(entropy_norm)),
        "temporal_stability": temporal_stability,
        "concentration_ratio": float(np.mean(top1 / top2)),
        "effective_pair_count": float(np.mean(effective_pair_count)),
    }


def _plot_entropy(results_df, output_path):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {"NORMAL": "tab:gray", "F13": "tab:orange", "F12": "tab:green"}
    for row in results_df.itertuples(index=False):
        ax.scatter(
            row.mean_top1_mass,
            row.mean_entropy,
            s=180,
            color=colors[row.source],
            alpha=0.85,
            edgecolors="black",
        )
        ax.text(
            float(row.mean_top1_mass) + 0.01,
            float(row.mean_entropy) + 0.01,
            row.source,
            fontsize=9,
        )
    ax.set_xlabel("mean_top1_mass")
    ax.set_ylabel("mean_entropy")
    ax.set_title("Soft-state entropy / concentration")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_concentration(results_df, output_path):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), constrained_layout=True)
    labels = results_df["source"].tolist()
    axes[0].bar(labels, results_df["concentration_ratio"], color=["tab:gray", "tab:orange", "tab:green"], alpha=0.85)
    axes[0].set_title("Concentration ratio")
    axes[0].set_ylabel("top1 / top2")
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].bar(labels, results_df["effective_pair_count"], color=["tab:gray", "tab:orange", "tab:green"], alpha=0.85)
    axes[1].set_title("Effective pair count")
    axes[1].set_ylabel("exp(entropy)")
    axes[1].grid(axis="y", alpha=0.3)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_temporal_stability(results_df, output_path):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(
        results_df["source"].tolist(),
        results_df["temporal_stability"].tolist(),
        color=["tab:gray", "tab:orange", "tab:green"],
        alpha=0.85,
    )
    ax.set_ylabel("mean cosine similarity")
    ax.set_title("Soft-state temporal stability")
    ax.grid(axis="y", alpha=0.3)
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
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    f12_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=12)
    f13_arrays = _prepare_run_arrays(f13_runs, selected_columns, N_RUNS)
    f12_arrays = _prepare_run_arrays(f12_runs, selected_columns, N_RUNS)

    baseline_model = _build_baseline_model(baseline_data, W, S)

    source_arrays = {
        "NORMAL": normal_arrays,
        "F13": f13_arrays,
        "F12": f12_arrays,
    }

    rows = []
    for source in SOURCES:
        metrics = _summarize_source(source_arrays[source], baseline_model)
        rows.append({"source": source, **metrics})

    results_df = pd.DataFrame(rows)
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "taxonomy").mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_ROOT / "csv" / "soft_state_validation.csv", index=False, encoding="utf-8")

    _plot_entropy(results_df, OUTPUT_ROOT / "taxonomy" / "soft_state_entropy.png")
    _plot_concentration(results_df, OUTPUT_ROOT / "taxonomy" / "soft_state_concentration.png")
    _plot_temporal_stability(results_df, OUTPUT_ROOT / "taxonomy" / "soft_state_temporal_stability.png")

    print(results_df.to_string(index=False))

    normal = results_df.loc[results_df["source"] == "NORMAL"].iloc[0]
    f13 = results_df.loc[results_df["source"] == "F13"].iloc[0]
    f12 = results_df.loc[results_df["source"] == "F12"].iloc[0]

    strong_survived = (
        f13["mean_top1_mass"] > normal["mean_top1_mass"] * 1.5
        and f13["mean_entropy"] < normal["mean_entropy"]
        and f13["concentration_ratio"] > normal["concentration_ratio"] * 1.5
    )
    metastable_weakened = (
        f12["mean_top1_mass"] < f13["mean_top1_mass"]
        and f12["mean_entropy"] > f13["mean_entropy"]
    )
    taxonomy_collapsed = (
        abs(float(f13["mean_top1_mass"]) - float(normal["mean_top1_mass"])) < 0.05
        and abs(float(f13["mean_entropy"]) - float(normal["mean_entropy"])) < 0.05
    )

    print("\nConservative interpretation:")
    if strong_survived:
        print("- soft concentration remains visible for F13 under continuous representation.")
    else:
        print("- F13 loses most of its concentration under continuous representation.")
    if metastable_weakened:
        print("- metastable structure weakens under continuous representation relative to the strongest attractor.")
    else:
        print("- the F12 boundary case does not separate cleanly from the strongest attractor under this soft-state view.")
    if taxonomy_collapsed:
        print("- continuous structure does not remain clearly separated from NORMAL.")
    else:
        print("- continuous structure partially survives without hard argmax collapse.")

    print("\nOutcome flags:")
    print(f"- strong attractor survived: {'yes' if strong_survived else 'no'}")
    print(f"- metastable structure weakened: {'yes' if metastable_weakened else 'no'}")
    print(f"- taxonomy collapsed: {'yes' if taxonomy_collapsed else 'no'}")

    return results_df


if __name__ == "__main__":
    main()
