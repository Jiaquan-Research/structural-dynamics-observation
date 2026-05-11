"""A4 variable-expansion validation for structural dynamics concentration."""

from __future__ import annotations

import math
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
    _collect_window_features,
    _build_baseline_model,
    _differenced_correlation_features,
    _load_all_fault_runs,
    _resolve_paths,
    _score_features,
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

# Variable sets are explicitly chosen to remain within a coherent reactor /
# separator / stripper process neighborhood. These are not random subsets.
VARIABLE_CONFIGS = {
    "V5": [
        "XMEAS_7",   # reactor pressure
        "XMEAS_8",   # reactor level
        "XMEAS_9",   # reactor temperature
        "XMEAS_10",  # purge rate
        "XMEAS_11",  # separator temperature
    ],
    "V8": [
        "XMEAS_7",
        "XMEAS_8",
        "XMEAS_9",
        "XMEAS_10",
        "XMEAS_11",
        "XMEAS_12",  # separator pressure
        "XMEAS_13",  # separator underflow
        "XMEAS_17",  # stripper temperature
    ],
    "V12": [
        "XMEAS_6",   # reactor feed / related flow
        "XMEAS_7",
        "XMEAS_8",
        "XMEAS_9",
        "XMEAS_10",
        "XMEAS_11",
        "XMEAS_12",
        "XMEAS_13",
        "XMEAS_14",  # stripper level
        "XMEAS_15",  # stripper pressure
        "XMEAS_16",  # stripper underflow
        "XMEAS_17",
    ],
}


def _resolve_variable_columns(columns, requested_columns):
    lower_to_original = {column.lower(): column for column in columns}
    resolved = []
    for requested in requested_columns:
        if requested in columns:
            resolved.append(requested)
            continue
        lowered = requested.lower()
        if lowered in lower_to_original:
            resolved.append(lower_to_original[lowered])
            continue
        raise KeyError(f"Missing requested column: {requested}")
    return resolved


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
    denominator = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    denominator = np.where(denominator <= 0.0, 1e-12, denominator)
    return numerator / denominator


def _classify_soft_state(mean_top1_mass, normalized_entropy):
    if mean_top1_mass >= 0.60 and normalized_entropy <= 0.45:
        return "strong_concentrated"
    if mean_top1_mass <= 0.25 and normalized_entropy >= 0.90:
        return "diffuse"
    return "intermediate"


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


def _load_dataset_paths():
    training_path, testing_path = _resolve_paths(".")
    if training_path is None or testing_path is None:
        raise FileNotFoundError("Please download the TEP CSV dataset first.")
    return training_path, testing_path


def _load_config_data(training_path, testing_path, requested_columns):
    header = pd.read_csv(training_path, nrows=0).columns.tolist()
    selected_columns = _resolve_variable_columns(header, requested_columns)
    baseline_df = pd.read_csv(training_path, usecols=selected_columns)
    baseline_data = baseline_df[selected_columns].to_numpy(dtype=float)

    normal_runs = _load_normal_runs(".", selected_columns)
    normal_arrays = _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)

    usecols = ["faultNumber", "simulationRun", "sample", *selected_columns]
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    f12_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=12)
    f13_arrays = _prepare_run_arrays(f13_runs, selected_columns, N_RUNS)
    f12_arrays = _prepare_run_arrays(f12_runs, selected_columns, N_RUNS)

    return baseline_data, {
        "NORMAL": normal_arrays,
        "F13": f13_arrays,
        "F12": f12_arrays,
    }


def _summarize_source(run_arrays, baseline_model):
    soft_vectors = []
    temporal_values = []

    for run_idx in range(1, N_RUNS + 1):
        run_data = run_arrays.get(run_idx)
        if run_data is None:
            continue
        try:
            series = _compute_continuous_series(run_data, baseline_model)
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
    pair_count = int(probs_all.shape[1])
    top_sorted = np.sort(probs_all, axis=1)[:, ::-1]
    top1 = top_sorted[:, 0]
    top2 = np.maximum(top_sorted[:, 1], 1e-12)
    entropy_raw = -np.sum(probs_all * np.log(probs_all + 1e-12), axis=1)
    entropy_norm = entropy_raw / math.log(pair_count)
    effective_pair_count = np.exp(entropy_raw)
    temporal_stability = (
        float(np.mean(np.concatenate(temporal_values, axis=0)))
        if temporal_values
        else float("nan")
    )

    mean_top1_mass = float(np.mean(top1))
    normalized_entropy = float(np.mean(entropy_norm))
    concentration_ratio = float(np.mean(top1 / top2))
    effective_pairs = float(np.mean(effective_pair_count))
    taxonomy = _classify_soft_state(mean_top1_mass, normalized_entropy)

    return {
        "pair_count": pair_count,
        "mean_top1_mass": mean_top1_mass,
        "normalized_entropy": normalized_entropy,
        "effective_pair_count": effective_pairs,
        "concentration_ratio": concentration_ratio,
        "temporal_stability": temporal_stability,
        "taxonomy_label": taxonomy,
    }


def _plot_entropy(results_df, output_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {"NORMAL": "tab:gray", "F13": "tab:orange", "F12": "tab:green"}
    for source, group in results_df.groupby("source", sort=False):
        group = group.sort_values("variable_count")
        ax.plot(
            group["variable_count"],
            group["normalized_entropy"],
            marker="o",
            label=source,
            color=colors[source],
        )
    ax.set_xlabel("variable_count")
    ax.set_ylabel("normalized_entropy")
    ax.set_title("Variable expansion: normalized entropy")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_effective_pairs(results_df, output_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {"NORMAL": "tab:gray", "F13": "tab:orange", "F12": "tab:green"}
    for source, group in results_df.groupby("source", sort=False):
        ax.scatter(
            group["pair_count"],
            group["effective_pair_count"],
            s=140,
            alpha=0.85,
            color=colors[source],
            label=source,
        )
        for row in group.itertuples(index=False):
            ax.text(
                float(row.pair_count) + 0.2,
                float(row.effective_pair_count) + 0.1,
                f"{row.source}-{row.config}",
                fontsize=8,
            )
    ax.set_xlabel("pair_count")
    ax.set_ylabel("effective_pair_count")
    ax.set_title("Variable expansion: effective pairs vs pair count")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_taxonomy(results_df, output_path):
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {"NORMAL": "tab:gray", "F13": "tab:orange", "F12": "tab:green"}
    for source, group in results_df.groupby("source", sort=False):
        ax.scatter(
            group["mean_top1_mass"],
            group["normalized_entropy"],
            s=160,
            alpha=0.85,
            color=colors[source],
            label=source,
        )
        for row in group.itertuples(index=False):
            ax.text(
                float(row.mean_top1_mass) + 0.01,
                float(row.normalized_entropy) + 0.01,
                f"{row.source}-{row.config}",
                fontsize=8,
            )
    ax.set_xlabel("mean_top1_mass")
    ax.set_ylabel("normalized_entropy")
    ax.set_title("Variable expansion: soft-state taxonomy view")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    training_path, testing_path = _load_dataset_paths()

    rows = []
    for config_name, requested_columns in VARIABLE_CONFIGS.items():
        baseline_data, source_arrays = _load_config_data(training_path, testing_path, requested_columns)
        baseline_model = _build_baseline_model(baseline_data, W, S)
        variable_count = len(requested_columns)
        pair_count = variable_count * (variable_count - 1) // 2

        for source in SOURCES:
            metrics = _summarize_source(source_arrays[source], baseline_model)
            rows.append(
                {
                    "config": config_name,
                    "source": source,
                    "variable_count": variable_count,
                    "pair_count": pair_count,
                    **metrics,
                }
            )

    results_df = pd.DataFrame(rows).sort_values(["source", "variable_count"]).reset_index(drop=True)
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "taxonomy").mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_ROOT / "csv" / "variable_expansion_validation.csv", index=False, encoding="utf-8")

    _plot_entropy(results_df, OUTPUT_ROOT / "taxonomy" / "variable_expansion_entropy.png")
    _plot_effective_pairs(results_df, OUTPUT_ROOT / "taxonomy" / "variable_expansion_effective_pairs.png")
    _plot_taxonomy(results_df, OUTPUT_ROOT / "taxonomy" / "variable_expansion_taxonomy.png")

    print("==================================================")
    print("VARIABLE EXPANSION SUMMARY")
    print("==================================================")
    for row in results_df.itertuples(index=False):
        print(f"{row.source} / {row.config}:")
        print(f"  variable_count={int(row.variable_count)}")
        print(f"  pair_count={int(row.pair_count)}")
        print(f"  top1_mass={row.mean_top1_mass:.6f}")
        print(f"  entropy={row.normalized_entropy:.6f}")
        print(f"  effective_pair_count={row.effective_pair_count:.6f}")
        print(f"  taxonomy={row.taxonomy_label}")

    def _pick(source, config, column):
        return float(
            results_df.loc[
                (results_df["source"] == source) & (results_df["config"] == config),
                column,
            ].iloc[0]
        )

    f13_top1_v5 = _pick("F13", "V5", "mean_top1_mass")
    f13_top1_v12 = _pick("F13", "V12", "mean_top1_mass")
    normal_top1_v12 = _pick("NORMAL", "V12", "mean_top1_mass")
    f13_eff_v12 = _pick("F13", "V12", "effective_pair_count")
    f13_pairs_v12 = _pick("F13", "V12", "pair_count")
    f12_entropy_v5 = _pick("F12", "V5", "normalized_entropy")
    f12_entropy_v12 = _pick("F12", "V12", "normalized_entropy")
    f13_tax_v12 = results_df.loc[
        (results_df["source"] == "F13") & (results_df["config"] == "V12"),
        "taxonomy_label",
    ].iloc[0]

    strong_survived = bool(
        f13_tax_v12 == "strong_concentrated"
        and f13_top1_v12 > normal_top1_v12 * 1.5
    )
    concentration_weakened = bool(f13_top1_v12 < f13_top1_v5 * 0.8)
    taxonomy_collapsed = bool(
        f13_tax_v12 == "diffuse"
        or f13_eff_v12 >= 0.8 * f13_pairs_v12
    )
    metastable_weakened = bool(f12_entropy_v12 > f12_entropy_v5)

    print("\nA4 outcome assessment:")
    print(f"- strong attractor survived: {'yes' if strong_survived else 'no'}")
    print(f"- concentration weakened: {'yes' if concentration_weakened else 'no'}")
    print(f"- taxonomy collapsed: {'yes' if taxonomy_collapsed else 'no'}")

    print("\nConservative interpretation:")
    if strong_survived:
        print("- F13 remains clearly more concentrated than NORMAL under variable expansion.")
    else:
        print("- F13 no longer separates clearly from NORMAL under variable expansion.")
    if concentration_weakened:
        print("- concentration weakens as pair-space expands.")
    else:
        print("- concentration does not weaken substantially over the tested expansion range.")
    if taxonomy_collapsed:
        print("- effective pair usage expands enough to weaken the low-dimensional attractor picture.")
    else:
        print("- the expanded pair-space does not collapse fully into diffuse wandering over the tested range.")
    if metastable_weakened:
        print("- the F12 boundary case moves toward a more diffuse regime under expansion.")
    else:
        print("- the F12 boundary case does not move strongly toward NORMAL under expansion.")

    return results_df


if __name__ == "__main__":
    main()
