"""PCA / T2 / SPE multirun baseline benchmark on TEP."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import _load_normal_runs
from task0_protocol import stride_sample
from tep_experiment import (
    _collect_window_features,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
K_PERSIST = 3
EXPLAINED_VARIANCE_TARGET = 0.95
THRESHOLD_QUANTILE = 0.99
FAULT_NUMBERS = list(range(1, 21))

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
TRACE_OUTPUT = CSV_OUTPUT_DIR / "pca_detector_trace.csv"
FAULT_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "pca_baseline_fault_summary.csv"
OVERALL_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "pca_baseline_overall_summary.csv"
RATE_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "pca_fault_detection_rate.png"
DELAY_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "pca_fault_detection_delay.png"
FP_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "pca_fp_comparison.png"


def _fault_label(fault_number: int) -> str:
    return f"F{int(fault_number):02d}"


def _window_matrix(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    sample_times = np.asarray(stride_sample(range(0, len(data)), WINDOW, STEP), dtype=int)
    if sample_times.size == 0:
        return np.empty((0, 0), dtype=float), sample_times
    windows = _collect_window_features(
        data,
        sample_times.tolist(),
        WINDOW,
        lambda chunk: np.asarray(chunk, dtype=float).reshape(-1),
    )
    return np.asarray(windows, dtype=float), sample_times


def _compute_t2_spe_scores(
    pca: PCA,
    windows: np.ndarray,
    train_window_mean: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    centered = windows - train_window_mean
    scores = pca.transform(windows)
    eigenvalues = np.maximum(np.asarray(pca.explained_variance_, dtype=float), 1e-12)
    t2_scores = np.sum((scores**2) / eigenvalues, axis=1)
    reconstructed = pca.inverse_transform(scores)
    residual = centered - reconstructed
    spe_scores = np.sum(residual**2, axis=1)
    return np.asarray(t2_scores, dtype=float), np.asarray(spe_scores, dtype=float)


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
    t2_scores: np.ndarray,
    spe_scores: np.ndarray,
    t2_threshold: float,
    spe_threshold: float,
) -> list[dict[str, object]]:
    rows = []
    for window_index, (t2_score, spe_score) in enumerate(zip(t2_scores, spe_scores), start=1):
        rows.append(
            {
                "run_type": run_type,
                "fault": fault,
                "simulation_run": int(simulation_run),
                "window_index": int(window_index),
                "t2": float(t2_score),
                "spe": float(spe_score),
                "t2_alarm": bool(t2_score > t2_threshold),
                "spe_alarm": bool(spe_score > spe_threshold),
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


def _print_env_check(train_windows: np.ndarray, normal_window_count: int) -> None:
    print("=== ENV CHECK ===")
    print("fault loader ok")
    print("sample filter ok")
    print(f"train shape = {train_windows.shape}")
    print(f"test shape = ({normal_window_count}, {train_windows.shape[1]})")


def _plot_detection_rate(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(summary_df))
    width = 0.38
    ax.bar(
        x - width / 2,
        summary_df["t2_detection_rate"].to_numpy(dtype=float),
        width=width,
        label="T2",
        color="tab:blue",
    )
    ax.bar(
        x + width / 2,
        summary_df["spe_detection_rate"].to_numpy(dtype=float),
        width=width,
        label="SPE",
        color="tab:orange",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["fault"].tolist(), rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("detection rate")
    ax.set_title("PCA baseline fault detection rate")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RATE_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_detection_delay(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(summary_df))
    width = 0.38
    ax.bar(
        x - width / 2,
        summary_df["t2_median_delay"].to_numpy(dtype=float),
        width=width,
        label="T2",
        color="tab:blue",
    )
    ax.bar(
        x + width / 2,
        summary_df["spe_median_delay"].to_numpy(dtype=float),
        width=width,
        label="SPE",
        color="tab:orange",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(summary_df["fault"].tolist(), rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("median delay (window count)")
    ax.set_title("PCA baseline fault detection delay")
    ax.grid(axis="y", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(DELAY_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_fp(normal_summary: dict[str, float]) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    methods = ["T2", "SPE"]
    values = [normal_summary["t2_fp_rate"], normal_summary["spe_fp_rate"]]
    ax.bar(methods, values, color=["tab:blue", "tab:orange"], alpha=0.85)
    ax.set_xlabel("method")
    ax.set_ylabel("FP rate")
    ax.set_title("PCA baseline false-positive comparison")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FP_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def main():
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = _prepare_multirun_data()
    baseline_data = dataset["baseline_data"]
    normal_runs = dataset["normal_runs"]
    fault_run_map = dataset["fault_run_map"]

    sample_mean = baseline_data.mean(axis=0)
    sample_std = baseline_data.std(axis=0, ddof=1)
    sample_std = np.where(sample_std == 0.0, 1.0, sample_std)
    baseline_scaled = (baseline_data - sample_mean) / sample_std

    train_windows, _train_sample_times = _window_matrix(baseline_scaled)
    if train_windows.size == 0:
        raise ValueError("Insufficient training windows for PCA benchmark.")

    normal_window_count = 0
    for run_data in normal_runs.values():
        run_scaled = (run_data - sample_mean) / sample_std
        run_windows, _sample_times = _window_matrix(run_scaled)
        normal_window_count += int(run_windows.shape[0])
    _print_env_check(train_windows, normal_window_count)

    train_window_mean = train_windows.mean(axis=0)
    train_window_std = train_windows.std(axis=0, ddof=1)
    train_window_std = np.where(train_window_std == 0.0, 1.0, train_window_std)
    train_windows_z = (train_windows - train_window_mean) / train_window_std

    pca_full = PCA(svd_solver="full")
    pca_full.fit(train_windows_z)
    cumulative = np.cumsum(pca_full.explained_variance_ratio_)
    n_components = int(np.searchsorted(cumulative, EXPLAINED_VARIANCE_TARGET) + 1)

    pca = PCA(n_components=n_components, svd_solver="full")
    pca.fit(train_windows_z)

    train_t2, train_spe = _compute_t2_spe_scores(pca, train_windows_z, pca.mean_)
    t2_threshold = float(np.quantile(train_t2, THRESHOLD_QUANTILE))
    spe_threshold = float(np.quantile(train_spe, THRESHOLD_QUANTILE))

    print(f"n_components retained = {n_components}")
    print(f"T2 threshold = {t2_threshold:.6f}")
    print(f"SPE threshold = {spe_threshold:.6f}")

    trace_rows: list[dict[str, object]] = []

    normal_t2_false_alarm_windows = 0
    normal_spe_false_alarm_windows = 0
    normal_eval_window_total = 0

    for run_id, run_data in sorted(normal_runs.items()):
        run_scaled = (run_data - sample_mean) / sample_std
        run_windows, run_sample_times = _window_matrix(run_scaled)
        if run_windows.size == 0:
            continue
        run_windows_z = (run_windows - train_window_mean) / train_window_std
        run_t2, run_spe = _compute_t2_spe_scores(pca, run_windows_z, pca.mean_)
        trace_rows.extend(
            _build_trace_rows("normal", "NORMAL", run_id, run_t2, run_spe, t2_threshold, spe_threshold)
        )

        eval_mask = run_sample_times > SAMPLE_FILTER
        if not np.any(eval_mask):
            continue
        eval_t2_alarm = run_t2[eval_mask] > t2_threshold
        eval_spe_alarm = run_spe[eval_mask] > spe_threshold
        normal_t2_false_alarm_windows += int(np.sum(_persistent_alarm_windows(eval_t2_alarm, K_PERSIST)))
        normal_spe_false_alarm_windows += int(np.sum(_persistent_alarm_windows(eval_spe_alarm, K_PERSIST)))
        normal_eval_window_total += int(np.sum(eval_mask))

    if normal_eval_window_total == 0:
        raise ValueError("SAMPLE_FILTER=200 removed all NORMAL testing windows.")

    normal_summary = {
        "t2_fp_rate": float(normal_t2_false_alarm_windows / normal_eval_window_total),
        "spe_fp_rate": float(normal_spe_false_alarm_windows / normal_eval_window_total),
        "normal_window_total": int(normal_eval_window_total),
        "n_normal_runs": int(len(normal_runs)),
    }

    print("=== PCA MULTIRUN BENCHMARK SUMMARY ===")
    print("NORMAL:")
    print(f"t2_fp_rate = {normal_summary['t2_fp_rate']:.6f}")
    print(f"spe_fp_rate = {normal_summary['spe_fp_rate']:.6f}")
    print("Per-fault summary:")

    fault_summary_rows = []
    all_t2_delays = []
    all_spe_delays = []
    all_t2_detected = 0
    all_spe_detected = 0
    all_fault_runs = 0
    fault_run_counts: dict[str, int] = {}

    for fault_number in FAULT_NUMBERS:
        fault_label = _fault_label(fault_number)
        runs = fault_run_map[fault_number]
        fault_run_counts[fault_label] = int(len(runs))

        t2_detected_count = 0
        spe_detected_count = 0
        t2_delays = []
        spe_delays = []

        for run_id, run_data in sorted(runs.items()):
            run_scaled = (run_data - sample_mean) / sample_std
            run_windows, run_sample_times = _window_matrix(run_scaled)
            if run_windows.size == 0:
                continue
            run_windows_z = (run_windows - train_window_mean) / train_window_std
            run_t2, run_spe = _compute_t2_spe_scores(pca, run_windows_z, pca.mean_)
            trace_rows.extend(
                _build_trace_rows("fault", fault_label, run_id, run_t2, run_spe, t2_threshold, spe_threshold)
            )

            eval_mask = run_sample_times > SAMPLE_FILTER
            if not np.any(eval_mask):
                continue

            t2_detected, t2_delay = _first_persistent_window_index(run_t2[eval_mask] > t2_threshold, K_PERSIST)
            spe_detected, spe_delay = _first_persistent_window_index(run_spe[eval_mask] > spe_threshold, K_PERSIST)

            if t2_detected:
                t2_detected_count += 1
                t2_delays.append(float(t2_delay))
                all_t2_delays.append(float(t2_delay))
            if spe_detected:
                spe_detected_count += 1
                spe_delays.append(float(spe_delay))
                all_spe_delays.append(float(spe_delay))

        all_t2_detected += t2_detected_count
        all_spe_detected += spe_detected_count
        all_fault_runs += int(len(runs))

        row = {
            "fault": fault_label,
            "t2_detection_rate": float(t2_detected_count / max(len(runs), 1)),
            "spe_detection_rate": float(spe_detected_count / max(len(runs), 1)),
            "t2_median_delay": float(np.median(t2_delays)) if t2_delays else float("nan"),
            "spe_median_delay": float(np.median(spe_delays)) if spe_delays else float("nan"),
            "t2_mean_delay": float(np.mean(t2_delays)) if t2_delays else float("nan"),
            "spe_mean_delay": float(np.mean(spe_delays)) if spe_delays else float("nan"),
            "t2_std_delay": float(np.std(t2_delays, ddof=1)) if len(t2_delays) >= 2 else float("nan"),
            "spe_std_delay": float(np.std(spe_delays, ddof=1)) if len(spe_delays) >= 2 else float("nan"),
            "n_runs": int(len(runs)),
        }
        fault_summary_rows.append(row)

        print(f"{fault_label}:")
        print(f"T2 detect_rate={row['t2_detection_rate']:.6f}")
        print(f"SPE detect_rate={row['spe_detection_rate']:.6f}")
        print(f"T2 median_delay={row['t2_median_delay']}")
        print(f"SPE median_delay={row['spe_median_delay']}")

    fault_summary_df = pd.DataFrame(fault_summary_rows)
    trace_df = pd.DataFrame(trace_rows)

    overall_summary_df = pd.DataFrame(
        [
            {
                "method": "T2",
                "mean_fp_rate": float(normal_summary["t2_fp_rate"]),
                "mean_detection_rate": float(fault_summary_df["t2_detection_rate"].mean()),
                "mean_delay": float(np.mean(all_t2_delays)) if all_t2_delays else float("nan"),
            },
            {
                "method": "SPE",
                "mean_fp_rate": float(normal_summary["spe_fp_rate"]),
                "mean_detection_rate": float(fault_summary_df["spe_detection_rate"].mean()),
                "mean_delay": float(np.mean(all_spe_delays)) if all_spe_delays else float("nan"),
            },
        ]
    )

    trace_df.to_csv(TRACE_OUTPUT, index=False, encoding="utf-8")
    fault_summary_df.to_csv(FAULT_SUMMARY_OUTPUT, index=False, encoding="utf-8")
    overall_summary_df.to_csv(OVERALL_SUMMARY_OUTPUT, index=False, encoding="utf-8")

    _plot_detection_rate(fault_summary_df)
    _plot_detection_delay(fault_summary_df)
    _plot_fp(normal_summary)

    print("Hard fault check:")
    for fault_number in (3, 9, 15):
        label = _fault_label(fault_number)
        row = fault_summary_df.loc[fault_summary_df["fault"] == label].iloc[0]
        print(
            f"{label}: "
            f"T2 detect_rate={float(row['t2_detection_rate']):.6f}, "
            f"SPE detect_rate={float(row['spe_detection_rate']):.6f}, "
            f"T2 median_delay={row['t2_median_delay']}, "
            f"SPE median_delay={row['spe_median_delay']}"
        )

    print("=== INTERPRETATION ===")
    print("This is a static covariance baseline, not a geometry or propagation model.")
    print("TEP is known to violate PCA Gaussian assumptions, so T2 underperformance is expected in literature.")
    print("This benchmark is for baseline anchoring only, not for causal claim.")

    return {
        "trace_df": trace_df,
        "fault_summary_df": fault_summary_df,
        "overall_summary_df": overall_summary_df,
        "normal_summary": normal_summary,
        "n_components": n_components,
        "t2_threshold": t2_threshold,
        "spe_threshold": spe_threshold,
        "fault_run_counts": fault_run_counts,
        "all_fault_runs": int(all_fault_runs),
        "all_t2_detected": int(all_t2_detected),
        "all_spe_detected": int(all_spe_detected),
    }


if __name__ == "__main__":
    main()
