"""Threshold sweep / operating curve analysis for existing top1_mass traces."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"

TRACE_INPUT = CSV_OUTPUT_DIR / "top1_mass_detector_trace.csv"
SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "top1_operating_curve_summary.csv"
FAULTS_OUTPUT = CSV_OUTPUT_DIR / "top1_operating_curve_faults.csv"
OPERATING_CURVE_PLOT = TAXONOMY_OUTPUT_DIR / "top1_operating_curve.png"
DELAY_TRADEOFF_PLOT = TAXONOMY_OUTPUT_DIR / "top1_delay_tradeoff.png"
HEATMAP_PLOT = TAXONOMY_OUTPUT_DIR / "top1_fault_sensitivity_heatmap.png"

THRESHOLD_VALUES = [0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
FAULT_ORDER = [f"F{i:02d}" for i in range(1, 21)]
K_PERSIST = 3


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


def _plot_operating_curve(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(summary_df["fp_rate"], summary_df["mean_detection_rate"], marker="o", color="tab:green")
    for row in summary_df.itertuples(index=False):
        ax.text(float(row.fp_rate) + 0.003, float(row.mean_detection_rate) + 0.003, f"{row.threshold:.2f}", fontsize=9)
    ax.set_xlabel("fp_rate")
    ax.set_ylabel("mean_detection_rate")
    ax.set_title("top1_mass operating curve")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OPERATING_CURVE_PLOT, dpi=150)
    plt.close(fig)


def _plot_delay_tradeoff(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(summary_df["fp_rate"], summary_df["mean_delay"], marker="o", color="tab:blue")
    for row in summary_df.itertuples(index=False):
        ax.text(float(row.fp_rate) + 0.003, float(row.mean_delay) + 0.03, f"{row.threshold:.2f}", fontsize=9)
    ax.set_xlabel("fp_rate")
    ax.set_ylabel("mean_delay")
    ax.set_title("top1_mass delay tradeoff")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(DELAY_TRADEOFF_PLOT, dpi=150)
    plt.close(fig)


def _plot_heatmap(faults_df: pd.DataFrame) -> None:
    pivot = (
        faults_df.pivot(index="fault", columns="threshold", values="detection_rate")
        .reindex(FAULT_ORDER)
        .reindex(columns=THRESHOLD_VALUES)
    )
    fig, ax = plt.subplots(figsize=(9, 8))
    image = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="viridis", origin="upper", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(THRESHOLD_VALUES)))
    ax.set_xticklabels([f"{v:.2f}" for v in THRESHOLD_VALUES])
    ax.set_yticks(np.arange(len(FAULT_ORDER)))
    ax.set_yticklabels(FAULT_ORDER)
    ax.set_xlabel("threshold")
    ax.set_ylabel("fault")
    ax.set_title("top1_mass fault sensitivity heatmap")
    fig.colorbar(image, ax=ax, label="detection_rate")
    fig.tight_layout()
    fig.savefig(HEATMAP_PLOT, dpi=150)
    plt.close(fig)


def main():
    if not TRACE_INPUT.exists():
        raise FileNotFoundError(f"Trace CSV not found: {TRACE_INPUT}")

    df = pd.read_csv(TRACE_INPUT)
    required_columns = {"run_type", "fault", "simulation_run", "window_index", "top1_mass"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Trace CSV missing required columns: {sorted(missing)}")

    use_prefilter_trim = int(df["window_index"].min()) <= 2
    eval_df = df.loc[df["window_index"] > 2].copy() if use_prefilter_trim else df.copy()
    eval_df = eval_df.sort_values(["run_type", "fault", "simulation_run", "window_index"]).reset_index(drop=True)

    normal_df = eval_df.loc[eval_df["run_type"] == "normal"].copy()
    normal_window_total = int(len(normal_df))
    print(f"NORMAL windows used for FP = {normal_window_total}")

    summary_rows = []
    fault_rows = []

    normal_groups = list(normal_df.groupby("simulation_run", sort=True))
    fault_grouped = {
        fault: list(group.groupby("simulation_run", sort=True))
        for fault, group in eval_df.loc[eval_df["run_type"] == "fault"].groupby("fault", sort=True)
    }

    print("=== TOP1 OPERATING CURVE SUMMARY ===")
    for threshold in THRESHOLD_VALUES:
        normal_false_alarm_windows = 0
        for _run_id, run_df in normal_groups:
            alarms = run_df["top1_mass"].to_numpy(dtype=float) > threshold
            normal_false_alarm_windows += int(np.sum(_persistent_alarm_windows(alarms, K_PERSIST)))
        fp_rate = float(normal_false_alarm_windows / max(normal_window_total, 1))

        threshold_delays = []
        threshold_detection_rates = []

        for fault in FAULT_ORDER:
            runs = fault_grouped.get(fault, [])
            detected_count = 0
            delays = []
            for _run_id, run_df in runs:
                alarms = run_df["top1_mass"].to_numpy(dtype=float) > threshold
                detected, delay = _first_persistent_window_index(alarms, K_PERSIST)
                if detected:
                    detected_count += 1
                    delays.append(float(delay))
                    threshold_delays.append(float(delay))
            detection_rate = float(detected_count / max(len(runs), 1))
            median_delay = float(np.median(delays)) if delays else float("nan")
            threshold_detection_rates.append(detection_rate)
            fault_rows.append(
                {
                    "threshold": float(threshold),
                    "fault": fault,
                    "detection_rate": detection_rate,
                    "median_delay": median_delay,
                }
            )

        mean_detection_rate = float(np.mean(threshold_detection_rates))
        mean_delay = float(np.mean(threshold_delays)) if threshold_delays else float("nan")
        summary_rows.append(
            {
                "threshold": float(threshold),
                "fp_rate": fp_rate,
                "mean_detection_rate": mean_detection_rate,
                "mean_delay": mean_delay,
            }
        )

        print(f"threshold={threshold:.2f}")
        print(f"FP={fp_rate:.6f}")
        print(f"mean_detection={mean_detection_rate:.6f}")
        print(f"mean_delay={mean_delay:.6f}")

    summary_df = pd.DataFrame(summary_rows)
    faults_df = pd.DataFrame(fault_rows)

    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8")
    faults_df.to_csv(FAULTS_OUTPUT, index=False, encoding="utf-8")

    _plot_operating_curve(summary_df)
    _plot_delay_tradeoff(summary_df)
    _plot_heatmap(faults_df)

    low_fp_df = summary_df.loc[summary_df["fp_rate"] <= 0.10].copy()
    best_low_fp = low_fp_df.sort_values(["mean_detection_rate", "fp_rate"], ascending=[False, True]).iloc[0]
    balanced_df = summary_df.copy()
    balanced_df["objective"] = balanced_df["mean_detection_rate"] - balanced_df["fp_rate"]
    best_balanced = balanced_df.sort_values(["objective", "mean_detection_rate"], ascending=[False, False]).iloc[0]

    print("BEST LOW-FP OPERATING POINT:")
    print(f"threshold={float(best_low_fp['threshold']):.2f}")
    print(f"FP={float(best_low_fp['fp_rate']):.6f}")
    print(f"mean_detection={float(best_low_fp['mean_detection_rate']):.6f}")
    print(f"mean_delay={float(best_low_fp['mean_delay']):.6f}")

    print("BEST BALANCED POINT:")
    print(f"threshold={float(best_balanced['threshold']):.2f}")
    print(f"FP={float(best_balanced['fp_rate']):.6f}")
    print(f"mean_detection={float(best_balanced['mean_detection_rate']):.6f}")
    print(f"mean_delay={float(best_balanced['mean_delay']):.6f}")

    for target_threshold in (0.80, 0.75, 0.70):
        stable_faults = faults_df.loc[
            (faults_df["threshold"] == target_threshold) & (faults_df["detection_rate"] >= 0.50),
            "fault",
        ].tolist()
        print(f"threshold={target_threshold:.2f}: {' '.join(stable_faults) if stable_faults else '(none)'}")

    print("=== INTERPRETATION ===")
    print("This experiment changes the operating point only.")
    print("It does not change the geometry detector itself.")
    print("These results are for FP/detection tradeoff analysis.")
    print("They are not for causal claim.")

    print(f"generated_files = {[str(SUMMARY_OUTPUT), str(FAULTS_OUTPUT), str(OPERATING_CURVE_PLOT), str(DELAY_TRADEOFF_PLOT), str(HEATMAP_PLOT)]}")
    print("summary_preview:")
    print(summary_df.to_string(index=False))

    return summary_df, faults_df


if __name__ == "__main__":
    main()
