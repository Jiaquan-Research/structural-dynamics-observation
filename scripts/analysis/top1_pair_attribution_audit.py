"""Pair attribution audit for top1_mass-sensitive TEP conditions."""

from __future__ import annotations

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
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
N_RUNS_PER_CONDITION = 20
THRESHOLD = 0.80
K_PERSIST = 3
K_TOP = 3
N_HISTORY = 10
CONDITIONS = ["NORMAL", "F06", "F14", "F08", "F12", "F01", "F03"]

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "top1_pair_attribution_summary.csv"
HEATMAP_OUTPUT = TAXONOMY_OUTPUT_DIR / "top1_pair_freq_heatmap.png"
PERSISTENCE_OUTPUT = TAXONOMY_OUTPUT_DIR / "top1_pair_persistence.png"


def _condition_fault_number(condition: str) -> int | None:
    if condition == "NORMAL":
        return None
    return int(condition[1:])


def _persistent_same_pair_mask(pair_names: list[str], k_persist: int) -> np.ndarray:
    n = len(pair_names)
    flagged = np.zeros(n, dtype=bool)
    if n == 0:
        return flagged

    start = 0
    while start < n:
        end = start
        while end + 1 < n and pair_names[end + 1] == pair_names[start]:
            end += 1
        if (end - start + 1) >= k_persist:
            flagged[start : end + 1] = True
        start = end + 1
    return flagged


def _collect_condition_rows(condition: str, runs: dict[int, np.ndarray], baseline_model: dict[str, object]) -> tuple[pd.DataFrame, dict[str, object]]:
    records: list[dict[str, object]] = []
    selected_run_ids = sorted(runs)[:N_RUNS_PER_CONDITION]

    for run_id in selected_run_ids:
        run_data = runs[run_id]
        series = _compute_version_b_trajectory_series(
            run_data,
            WINDOW,
            STEP,
            K_TOP,
            N_HISTORY,
            baseline_model,
        )
        sample_times = np.asarray(series["sample_times"], dtype=int)
        top1_indices = np.asarray(series["top1_indices"], dtype=int)
        top_pair_dominance = np.asarray(series["top_pair_dominance"], dtype=float)

        eval_mask = sample_times > SAMPLE_FILTER
        eval_indices = top1_indices[eval_mask]
        eval_dominance = top_pair_dominance[eval_mask]

        for window_idx, (pair_idx, dominance_value) in enumerate(zip(eval_indices, eval_dominance), start=1):
            pair_name = PAIR_LABELS[int(pair_idx)]
            records.append(
                {
                    "condition": condition,
                    "simulation_run": int(run_id),
                    "window_index": int(window_idx),
                    "pair": pair_name,
                    "top1_mass": float(dominance_value),
                }
            )

    rows_df = pd.DataFrame(records)
    if rows_df.empty:
        raise ValueError(f"No valid attribution windows for {condition}.")

    pair_rows = []
    total_windows = int(len(rows_df))
    persistent_windows = 0

    for _run_id, run_df in rows_df.groupby("simulation_run", sort=True):
        pair_names = run_df["pair"].tolist()
        persistent_windows += int(np.sum(_persistent_same_pair_mask(pair_names, K_PERSIST)))

    persistent_ratio = float(persistent_windows / total_windows)

    for pair_name in PAIR_LABELS:
        pair_df = rows_df.loc[rows_df["pair"] == pair_name]
        pair_frequency = float(len(pair_df) / total_windows)
        mean_dominance = float(pair_df["top1_mass"].mean()) if not pair_df.empty else float("nan")
        pair_rows.append(
            {
                "condition": condition,
                "pair": pair_name,
                "pair_frequency": pair_frequency,
                "mean_dominance": mean_dominance,
                "persistent_ratio": persistent_ratio,
            }
        )

    summary_df = pd.DataFrame(pair_rows)
    top_row = summary_df.sort_values("pair_frequency", ascending=False).iloc[0]
    condition_summary = {
        "condition": condition,
        "top_pair": str(top_row["pair"]),
        "top_pair_frequency": float(top_row["pair_frequency"]),
        "persistent_ratio": persistent_ratio,
        "run_count": int(len(selected_run_ids)),
        "window_count": total_windows,
    }
    return summary_df, condition_summary


def _plot_heatmap(summary_df: pd.DataFrame) -> None:
    pivot = (
        summary_df.pivot(index="pair", columns="condition", values="pair_frequency")
        .reindex(index=PAIR_LABELS, columns=CONDITIONS)
    )
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="viridis", origin="upper", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(CONDITIONS)))
    ax.set_xticklabels(CONDITIONS, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(PAIR_LABELS)))
    ax.set_yticklabels(PAIR_LABELS)
    ax.set_xlabel("condition")
    ax.set_ylabel("pair")
    ax.set_title("Dominant pair frequency by condition")
    fig.colorbar(image, ax=ax, label="pair_frequency")
    fig.tight_layout()
    fig.savefig(HEATMAP_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_persistence(condition_summaries: list[dict[str, object]]) -> None:
    df = pd.DataFrame(condition_summaries)
    df["condition"] = pd.Categorical(df["condition"], categories=CONDITIONS, ordered=True)
    df = df.sort_values("condition")

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df["condition"].astype(str), df["persistent_ratio"], color="tab:green", alpha=0.85)
    ax.set_xlabel("condition")
    ax.set_ylabel("persistent_ratio")
    ax.set_title("Persistent dominant-pair ratio")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PERSISTENCE_OUTPUT, dpi=150)
    plt.close(fig)


def main():
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")

    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, WINDOW, STEP)
    normal_runs_df = _load_normal_runs(".", selected_columns)

    run_maps: dict[str, dict[int, np.ndarray]] = {
        "NORMAL": {
            int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
            for run_id, run_df in normal_runs_df.items()
        }
    }
    for condition in CONDITIONS:
        fault_number = _condition_fault_number(condition)
        if fault_number is None:
            continue
        fault_runs_df = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        run_maps[condition] = {
            int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
            for run_id, run_df in fault_runs_df.items()
        }

    summary_frames = []
    condition_summaries = []

    print("=== TOP1 PAIR ATTRIBUTION SUMMARY ===")
    for condition in CONDITIONS:
        summary_df, condition_summary = _collect_condition_rows(condition, run_maps[condition], baseline_model)
        summary_frames.append(summary_df)
        condition_summaries.append(condition_summary)
        print(f"{condition}:")
        print(f"  top pair = {condition_summary['top_pair']}  (frequency={condition_summary['top_pair_frequency']:.6f})")
        print(f"  persistent_ratio = {condition_summary['persistent_ratio']:.6f}")

    combined_summary_df = pd.concat(summary_frames, axis=0, ignore_index=True)
    combined_summary_df.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8")

    _plot_heatmap(combined_summary_df)
    _plot_persistence(condition_summaries)

    condition_summary_df = pd.DataFrame(condition_summaries).set_index("condition")
    print("=== BACKBONE ANALYSIS ===")
    focus_conditions = ["F06", "F08", "F12", "F14"]
    focus_df = combined_summary_df.loc[combined_summary_df["condition"].isin(focus_conditions)].copy()
    backbone_pairs = []
    for pair_name in PAIR_LABELS:
        pair_focus = focus_df.loc[(focus_df["pair"] == pair_name) & (focus_df["pair_frequency"] >= 0.30)]
        if not pair_focus.empty:
            backbone_pairs.append(pair_name)
            normal_freq = float(
                combined_summary_df.loc[
                    (combined_summary_df["condition"] == "NORMAL") & (combined_summary_df["pair"] == pair_name),
                    "pair_frequency",
                ].iloc[0]
            )
            values = []
            for condition in focus_conditions:
                freq = float(
                    combined_summary_df.loc[
                        (combined_summary_df["condition"] == condition) & (combined_summary_df["pair"] == pair_name),
                        "pair_frequency",
                    ].iloc[0]
                )
                values.append(f"{condition}={freq:.3f}")
            print(f"{pair_name}: {' '.join(values)} NORMAL={normal_freq:.3f}")

    print("=== CORE QUESTIONS ===")
    normal_top_pair = str(condition_summary_df.loc["NORMAL", "top_pair"])
    for condition in ("F06", "F14"):
        top_pair = str(condition_summary_df.loc[condition, "top_pair"])
        diff_flag = "different" if top_pair != normal_top_pair else "same"
        print(f"{condition} top pair vs NORMAL: {diff_flag} ({top_pair} vs {normal_top_pair})")
    for condition in ("F06", "F14"):
        ratio = float(condition_summary_df.loc[condition, "persistent_ratio"])
        normal_ratio = float(condition_summary_df.loc["NORMAL", "persistent_ratio"])
        relation = "higher" if ratio > normal_ratio else "not higher"
        print(f"{condition} persistent_ratio vs NORMAL: {relation} ({ratio:.6f} vs {normal_ratio:.6f})")
    shared_top_pairs = [str(condition_summary_df.loc[condition, "top_pair"]) for condition in focus_conditions]
    print(f"F06/F08/F12/F14 top pairs = {shared_top_pairs}")
    for condition in ("F01", "F03"):
        top_pair = str(condition_summary_df.loc[condition, "top_pair"])
        similarity = "close" if top_pair == normal_top_pair else "different"
        print(f"{condition} top pair vs NORMAL: {similarity} ({top_pair} vs {normal_top_pair})")

    print("=== INTERPRETATION ===")
    print("This is dominance attribution, not causal proof.")
    print("A dominant pair does not imply physical causality.")
    print("These results describe the source of geometry concentration structure.")
    print("Physical plausibility still needs domain-expert validation.")

    print(f"backbone_pairs = {backbone_pairs}")
    print(f"generated_files = {[str(SUMMARY_OUTPUT), str(HEATMAP_OUTPUT), str(PERSISTENCE_OUTPUT)]}")

    return combined_summary_df, condition_summaries, backbone_pairs


if __name__ == "__main__":
    main()
