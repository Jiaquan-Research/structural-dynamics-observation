"""Multirun top1_mass benchmark on TEP using the geometry pipeline."""

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
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
K_PERSIST = 3
K_TOP = 3
N_HISTORY = 10
THRESHOLD_QUANTILE = 0.99
FAULT_NUMBERS = list(range(1, 21))

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
TRACE_OUTPUT = CSV_OUTPUT_DIR / "top1_mass_detector_trace.csv"
FAULT_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "top1_mass_fault_summary.csv"
OVERALL_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "top1_mass_overall_summary.csv"
RATE_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "top1_fault_detection_rate.png"
DELAY_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "top1_fault_detection_delay.png"
FP_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "top1_fp_rate.png"
PCA_FAULT_SUMMARY = CSV_OUTPUT_DIR / "pca_baseline_fault_summary.csv"
PCA_OVERALL_SUMMARY = CSV_OUTPUT_DIR / "pca_baseline_overall_summary.csv"


def _fault_label(fault_number: int) -> str:
    return f"F{int(fault_number):02d}"


def _persistent_alarm_windows(alarms: np.ndarray, k_persist: int) -> np.ndarray:
    alarms = np.asarray(alarms, dtype=bool)
    flagged = np.zeros_like(alarms, dtype=bool)
    start = None
    for idx, alarm in enumerate(alarms):
        if alarm and start is None:
            start = idx
        if (not alarm or idx == len(alarms) - 1) and start is not None:
            end = idx if alarm and idx == len(alarms) - 1 else idx - 1
            if (end - start + 1) >= k_persist:
                flagged[start : end + 1] = True
            start = None
    return flagged


def _first_persistent_window_index(alarms: np.ndarray, k_persist: int) -> tuple[bool, float]:
    streak = 0
    for idx, alarm in enumerate(np.asarray(alarms, dtype=bool), start=1):
        if alarm:
            streak += 1
        else:
            streak = 0
        if streak >= k_persist:
            return True, float(idx)
    return False, float("nan")


def _build_trace_rows(
    run_type: str,
    fault: str,
    simulation_run: int,
    top1_mass: np.ndarray,
    threshold: float,
) -> list[dict[str, object]]:
    rows = []
    for window_index, value in enumerate(np.asarray(top1_mass, dtype=float), start=1):
        rows.append(
            {
                "run_type": run_type,
                "fault": fault,
                "simulation_run": int(simulation_run),
                "window_index": int(window_index),
                "top1_mass": float(value),
                "top1_alarm": bool(value > threshold),
            }
        )
    return rows


def _prepare_multirun_data():
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")

    training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    normal_runs_df = _load_normal_runs(".", selected_columns)
    if not normal_runs_df:
        raise ValueError("No NORMAL testing runs available.")

    normal_runs = {
        int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
        for run_id, run_df in normal_runs_df.items()
    }
    fault_run_map: dict[int, dict[int, np.ndarray]] = {}
    for fault_number in FAULT_NUMBERS:
        fault_runs_df = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        fault_run_map[fault_number] = {
            int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
            for run_id, run_df in fault_runs_df.items()
        }

    return {
        "training_path": training_path,
        "testing_path": testing_path,
        "selected_columns": selected_columns,
        "baseline_data": np.asarray(baseline_data, dtype=float),
        "normal_runs": normal_runs,
        "fault_run_map": fault_run_map,
    }


def _compute_series(run_data: np.ndarray, baseline_model: dict[str, object]) -> dict[str, np.ndarray]:
    return _compute_version_b_trajectory_series(
        run_data,
        WINDOW,
        STEP,
        K_TOP,
        N_HISTORY,
        baseline_model,
    )


def _plot_detection_rate(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(summary_df))
    ax.bar(x, summary_df["top1_detection_rate"].to_numpy(dtype=float), color="tab:green", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["fault"].tolist(), rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("detection rate")
    ax.set_title("top1_mass fault detection rate")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RATE_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_detection_delay(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(summary_df))
    ax.bar(x, summary_df["top1_median_delay"].to_numpy(dtype=float), color="tab:green", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["fault"].tolist(), rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("median delay (window count)")
    ax.set_title("top1_mass fault detection delay")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(DELAY_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_fp(fp_rate: float) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(["top1_mass"], [fp_rate], color="tab:green", alpha=0.85)
    ax.set_xlabel("method")
    ax.set_ylabel("FP rate")
    ax.set_title("top1_mass false-positive rate")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FP_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _print_comparison(top1_overall_df: pd.DataFrame, top1_fault_df: pd.DataFrame) -> None:
    if not PCA_FAULT_SUMMARY.exists() or not PCA_OVERALL_SUMMARY.exists():
        print("=== COMPARISON WITH TRAJECTORY PCA ===")
        print("PCA baseline summary files not found.")
        return

    pca_fault_df = pd.read_csv(PCA_FAULT_SUMMARY)
    pca_overall_df = pd.read_csv(PCA_OVERALL_SUMMARY)
    spe_overall = pca_overall_df.loc[pca_overall_df["method"] == "SPE"].iloc[0]
    top1_overall = top1_overall_df.iloc[0]

    print("=== COMPARISON WITH TRAJECTORY PCA ===")
    print("top1 vs SPE:")
    print("FP:")
    print(f"top1 = {float(top1_overall['mean_fp_rate']):.6f}")
    print(f"SPE = {float(spe_overall['mean_fp_rate']):.6f}")
    print("Mean detection rate:")
    print(f"top1 = {float(top1_overall['mean_detection_rate']):.6f}")
    print(f"SPE = {float(spe_overall['mean_detection_rate']):.6f}")
    print("Mean delay:")
    print(f"top1 = {float(top1_overall['mean_delay']):.6f}")
    print(f"SPE = {float(spe_overall['mean_delay']):.6f}")
    print("Hard faults:")
    for label in ("F03", "F09", "F15"):
        top1_row = top1_fault_df.loc[top1_fault_df["fault"] == label].iloc[0]
        spe_row = pca_fault_df.loc[pca_fault_df["fault"] == label].iloc[0]
        print(f"{label}:")
        print(
            f"top1 = detect_rate {float(top1_row['top1_detection_rate']):.6f}, "
            f"median_delay {top1_row['top1_median_delay']}"
        )
        print(
            f"SPE = detect_rate {float(spe_row['spe_detection_rate']):.6f}, "
            f"median_delay {spe_row['spe_median_delay']}"
        )


def main():
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = _prepare_multirun_data()
    baseline_data = dataset["baseline_data"]
    normal_runs = dataset["normal_runs"]
    fault_run_map = dataset["fault_run_map"]

    baseline_model = _build_baseline_model(baseline_data, WINDOW, STEP)
    train_series = _compute_series(baseline_data, baseline_model)
    train_top1_mass = np.asarray(train_series["top_pair_dominance"], dtype=float)
    top1_mass_threshold = float(np.quantile(train_top1_mass, THRESHOLD_QUANTILE))

    print(f"top1_mass threshold = {top1_mass_threshold:.6f}")

    trace_rows: list[dict[str, object]] = []
    normal_false_alarm_windows = 0
    normal_eval_window_total = 0
    normal_total_window_count = 0

    for run_id, run_data in sorted(normal_runs.items()):
        series = _compute_series(run_data, baseline_model)
        sample_times = np.asarray(series["sample_times"], dtype=int)
        top1_mass = np.asarray(series["top_pair_dominance"], dtype=float)
        trace_rows.extend(_build_trace_rows("normal", "NORMAL", run_id, top1_mass, top1_mass_threshold))
        normal_total_window_count += int(top1_mass.size)

        eval_mask = sample_times > SAMPLE_FILTER
        if np.any(eval_mask):
            alarms = top1_mass[eval_mask] > top1_mass_threshold
            normal_false_alarm_windows += int(np.sum(_persistent_alarm_windows(alarms, K_PERSIST)))
            normal_eval_window_total += int(np.sum(eval_mask))

    if normal_eval_window_total == 0:
        raise ValueError("SAMPLE_FILTER=200 removed all NORMAL test windows.")

    print(f"=== NORMAL done: {len(normal_runs)} runs processed ===")

    top1_fp_rate = float(normal_false_alarm_windows / normal_eval_window_total)

    fault_summary_rows = []
    all_detected_delays = []
    fault_run_counts: dict[str, int] = {}

    for fault_number in FAULT_NUMBERS:
        fault_label = _fault_label(fault_number)
        print(f"=== Processing {fault_label} ===")
        runs = fault_run_map[fault_number]
        fault_run_counts[fault_label] = int(len(runs))

        detected_count = 0
        delays = []
        processed_runs = 0

        for run_id, run_data in sorted(runs.items()):
            series = _compute_series(run_data, baseline_model)
            sample_times = np.asarray(series["sample_times"], dtype=int)
            top1_mass = np.asarray(series["top_pair_dominance"], dtype=float)
            trace_rows.extend(_build_trace_rows("fault", fault_label, run_id, top1_mass, top1_mass_threshold))

            eval_mask = sample_times > SAMPLE_FILTER
            if np.any(eval_mask):
                detected, delay = _first_persistent_window_index(
                    top1_mass[eval_mask] > top1_mass_threshold,
                    K_PERSIST,
                )
                if detected:
                    detected_count += 1
                    delays.append(float(delay))
                    all_detected_delays.append(float(delay))
            processed_runs += 1

        fault_summary_rows.append(
            {
                "fault": fault_label,
                "top1_detection_rate": float(detected_count / max(len(runs), 1)),
                "top1_median_delay": float(np.median(delays)) if delays else float("nan"),
                "top1_mean_delay": float(np.mean(delays)) if delays else float("nan"),
                "top1_std_delay": float(np.std(delays, ddof=1)) if len(delays) >= 2 else float("nan"),
                "n_runs": int(len(runs)),
            }
        )
        print(f"=== {fault_label} done: {processed_runs} runs processed ===")

    fault_summary_df = pd.DataFrame(fault_summary_rows)
    trace_df = pd.DataFrame(trace_rows)
    overall_summary_df = pd.DataFrame(
        [
            {
                "method": "top1_mass",
                "mean_fp_rate": top1_fp_rate,
                "mean_detection_rate": float(fault_summary_df["top1_detection_rate"].mean()),
                "mean_delay": float(np.mean(all_detected_delays)) if all_detected_delays else float("nan"),
            }
        ]
    )

    trace_df.to_csv(TRACE_OUTPUT, index=False, encoding="utf-8")
    fault_summary_df.to_csv(FAULT_SUMMARY_OUTPUT, index=False, encoding="utf-8")
    overall_summary_df.to_csv(OVERALL_SUMMARY_OUTPUT, index=False, encoding="utf-8")

    _plot_detection_rate(fault_summary_df)
    _plot_detection_delay(fault_summary_df)
    _plot_fp(top1_fp_rate)

    print("=== TOP1 MASS MULTIRUN BENCHMARK SUMMARY ===")
    print(f"top1_mass threshold = {top1_mass_threshold:.6f}")
    print("NORMAL:")
    print(f"top1_fp_rate = {top1_fp_rate:.6f}")
    print("Per-fault summary:")
    for row in fault_summary_df.itertuples(index=False):
        print(f"{row.fault}:")
        print(f"top1 detect_rate={float(row.top1_detection_rate):.6f}")
        print(f"top1 median_delay={row.top1_median_delay}")

    _print_comparison(overall_summary_df, fault_summary_df)

    print("=== INTERPRETATION ===")
    print("This benchmark compares a geometry-derived detector against a trajectory covariance detector.")
    print("Trajectory SPE is already a windowed dynamic representation, not a classical PCA baseline.")
    print("These results support operating regime comparison only, not causal claim.")

    return {
        "trace_df": trace_df,
        "fault_summary_df": fault_summary_df,
        "overall_summary_df": overall_summary_df,
        "top1_mass_threshold": top1_mass_threshold,
        "normal_total_window_count": int(normal_eval_window_total),
        "fault_run_counts": fault_run_counts,
    }


if __name__ == "__main__":
    main()
