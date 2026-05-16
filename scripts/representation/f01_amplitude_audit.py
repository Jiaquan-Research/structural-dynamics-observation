"""F01 amplitude audit for XMEAS7-XMEAS11 geometry activation."""

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
K_TOP = 3
N_HISTORY = 10
THRESHOLD = 0.80
N_RUNS = 20
TARGET_PAIR = "XMEAS7-XMEAS11"

CSV_OUTPUT = PROJECT_ROOT / "outputs" / "csv" / "f01_amplitude_audit.csv"
PLOT_OUTPUT = PROJECT_ROOT / "outputs" / "taxonomy" / "f01_amplitude_distribution.png"

CONDITIONS = ("F01", "F06", "NORMAL")


def _fault_number(condition: str) -> int:
    return int(condition[1:])


def _runs_to_arrays(run_frames: dict[int, pd.DataFrame], selected_columns: list[str]) -> dict[int, np.ndarray]:
    arrays = {}
    for run_id, run_df in run_frames.items():
        arrays[int(run_id)] = run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
    return arrays


def _collect_condition_windows(
    condition: str,
    runs: dict[int, np.ndarray],
    baseline_model: dict[str, object],
) -> pd.DataFrame:
    records = []
    selected_run_ids = sorted(runs)[:N_RUNS]

    for run_id in selected_run_ids:
        series = _compute_version_b_trajectory_series(
            runs[run_id],
            WINDOW,
            STEP,
            K_TOP,
            N_HISTORY,
            baseline_model,
        )
        sample_times = np.asarray(series["sample_times"], dtype=int)
        top1_indices = np.asarray(series["top1_indices"], dtype=int)
        top1_mass = np.asarray(series["top_pair_dominance"], dtype=float)

        mask = sample_times > SAMPLE_FILTER
        for window_index, (sample_time, pair_idx, mass) in enumerate(
            zip(sample_times[mask], top1_indices[mask], top1_mass[mask]),
            start=1,
        ):
            records.append(
                {
                    "condition": condition,
                    "simulation_run": int(run_id),
                    "window_index": int(window_index),
                    "sample_time": int(sample_time),
                    "dominant_pair": PAIR_LABELS[int(pair_idx)],
                    "top1_mass": float(mass),
                }
            )

    if not records:
        raise ValueError(f"No valid windows for {condition}.")
    return pd.DataFrame(records)


def _summary_for_group(condition: str, pair_group: str, values: pd.Series) -> dict[str, object]:
    arr = values.to_numpy(dtype=float)
    if arr.size == 0:
        return {
            "condition": condition,
            "pair_group": pair_group,
            "count": 0,
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "p10": float("nan"),
            "p25": float("nan"),
            "p50": float("nan"),
            "p75": float("nan"),
            "p90": float("nan"),
            "sub_threshold_rate": float("nan"),
            "above_threshold_rate": float("nan"),
        }

    return {
        "condition": condition,
        "pair_group": pair_group,
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "p10": float(np.quantile(arr, 0.10)),
        "p25": float(np.quantile(arr, 0.25)),
        "p50": float(np.quantile(arr, 0.50)),
        "p75": float(np.quantile(arr, 0.75)),
        "p90": float(np.quantile(arr, 0.90)),
        "sub_threshold_rate": float(np.mean(arr < THRESHOLD)),
        "above_threshold_rate": float(np.mean(arr > THRESHOLD)),
    }


def _summarize_windows(windows_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition in CONDITIONS:
        condition_df = windows_df.loc[windows_df["condition"] == condition]
        target_df = condition_df.loc[condition_df["dominant_pair"] == TARGET_PAIR]
        other_df = condition_df.loc[condition_df["dominant_pair"] != TARGET_PAIR]
        rows.append(_summary_for_group(condition, TARGET_PAIR, target_df["top1_mass"]))
        rows.append(_summary_for_group(condition, "other", other_df["top1_mass"]))
    return pd.DataFrame(rows)


def _plot_target_distribution(windows_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = {"F01": "tab:orange", "F06": "tab:green", "NORMAL": "tab:blue"}
    bins = np.linspace(0.0, 1.0, 21)

    for condition in CONDITIONS:
        values = windows_df.loc[
            (windows_df["condition"] == condition)
            & (windows_df["dominant_pair"] == TARGET_PAIR),
            "top1_mass",
        ].to_numpy(dtype=float)
        if values.size == 0:
            continue
        ax.hist(
            values,
            bins=bins,
            density=True,
            alpha=0.35,
            color=colors[condition],
            label=f"{condition} (n={values.size})",
        )

    ax.axvline(THRESHOLD, color="black", linestyle="--", linewidth=1.5, label="threshold=0.80")
    ax.set_xlabel("top1_mass")
    ax.set_ylabel("frequency")
    ax.set_title(f"{TARGET_PAIR} top1_mass distribution")
    ax.set_xlim(0.0, 1.0)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _row(summary_df: pd.DataFrame, condition: str, pair_group: str) -> pd.Series:
    return summary_df.loc[
        (summary_df["condition"] == condition) & (summary_df["pair_group"] == pair_group)
    ].iloc[0]


def _print_diagnostics(summary_df: pd.DataFrame) -> None:
    f01 = _row(summary_df, "F01", TARGET_PAIR)
    f06 = _row(summary_df, "F06", TARGET_PAIR)
    normal = _row(summary_df, "NORMAL", TARGET_PAIR)

    f01_median = float(f01["median"])
    f06_median = float(f06["median"])
    normal_median = float(normal["median"])
    f01_sub = float(f01["sub_threshold_rate"])
    median_gap = f06_median - f01_median

    print("=== F01 AMPLITUDE AUDIT ===")
    print(f"Target pair: {TARGET_PAIR}")
    print(f"Runs per condition: first {N_RUNS}")
    print(f"Window={WINDOW}, step={STEP}, sample_filter>{SAMPLE_FILTER}, threshold={THRESHOLD:.2f}")
    print("")
    print("Q1: F01 target-pair top1_mass")
    print(f"median = {f01_median:.6f}")
    print(f"systematically below 0.80 = {f01_sub > 0.70}")
    print("")
    print("Q2: F06 target-pair top1_mass")
    print(f"median = {f06_median:.6f}")
    print(f"F06_minus_F01_median_gap = {median_gap:.6f}")
    print("")
    print("Q3: F01 pair-active but sub-threshold rate")
    print(f"sub_threshold_rate = {f01_sub:.6f}")
    print("")
    print("Q4: NORMAL target-pair top1_mass")
    print(
        "count={count}, mean={mean:.6f}, median={median:.6f}, p10={p10:.6f}, "
        "p90={p90:.6f}, sub_threshold_rate={sub:.6f}".format(
            count=int(normal["count"]),
            mean=float(normal["mean"]),
            median=normal_median,
            p10=float(normal["p10"]),
            p90=float(normal["p90"]),
            sub=float(normal["sub_threshold_rate"]),
        )
    )
    print(f"F01_minus_NORMAL_median_gap = {f01_median - normal_median:.6f}")
    print("")

    if f01_sub > 0.70:
        print("DIAGNOSIS: F01 shows sub-threshold geometry activation.")
        print("Signal exists but amplitude is systematically insufficient.")
        print("Classification: weak geometry activation, not noisy switching.")
    else:
        print("DIAGNOSIS: F01 geometry activation is intermittent/noisy.")
        print("Amplitude distribution does not show systematic sub-threshold pattern.")
        print("Classification: noisy partial activation.")

    print("")
    print("Conservative interpretation:")
    print("1. Analysis is limited to the XMEAS7-11 subspace.")
    print("2. Conclusion is based on the first 20 runs, not all 500 runs.")
    print("3. No physical causal inference is made.")


def main() -> None:
    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PLOT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded

    baseline_model = _build_baseline_model(np.asarray(baseline_data, dtype=float), WINDOW, STEP)

    normal_frames = _load_normal_runs(".", selected_columns)
    run_sets: dict[str, dict[int, np.ndarray]] = {
        "NORMAL": _runs_to_arrays(normal_frames, selected_columns),
    }

    for condition in ("F01", "F06"):
        fault_frames = _load_all_fault_runs(
            testing_path,
            usecols=usecols,
            fault_number=_fault_number(condition),
        )
        run_sets[condition] = _runs_to_arrays(fault_frames, selected_columns)

    window_frames = []
    for condition in CONDITIONS:
        print(f"Processing {condition}...")
        window_frames.append(_collect_condition_windows(condition, run_sets[condition], baseline_model))

    windows_df = pd.concat(window_frames, axis=0, ignore_index=True)
    summary_df = _summarize_windows(windows_df)
    summary_df.to_csv(CSV_OUTPUT, index=False)
    _plot_target_distribution(windows_df)
    _print_diagnostics(summary_df)

    print("")
    print("Generated files:")
    print(f"- {CSV_OUTPUT}")
    print(f"- {PLOT_OUTPUT}")


if __name__ == "__main__":
    main()
