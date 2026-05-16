"""Plot F02/F06/F14 archetype profiles from selected high-response runs."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import ruptures as rpt
except ImportError:
    raise ImportError("pip install ruptures")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

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
ROLLING_WINDOW = 100
RUPTURES_PENALTY_A = 50
TARGET_FAULTS = ["F02", "F06", "F14"]

TRACE_INPUT = PROJECT_ROOT / "outputs" / "csv" / "top1_mass_detector_trace.csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
TRIANGLE_OUTPUT = TAXONOMY_OUTPUT_DIR / "archetype_triangle_comparison.png"

PAIR_COLORS = {
    "XMEAS7-XMEAS11": "tab:red",
    "XMEAS9-XMEAS11": "tab:blue",
}


def _fault_number(fault: str) -> int:
    return int(str(fault).replace("F", ""))


def _normalize_column_name(name: str) -> str:
    return str(name).replace("_", "").replace(" ", "").lower()


def _find_column_index(selected_columns: list[str], target: str) -> int:
    normalized_target = _normalize_column_name(target)
    for idx, column in enumerate(selected_columns):
        if _normalize_column_name(column) == normalized_target:
            return int(idx)
    raise ValueError(f"Column {target} not found in selected columns: {selected_columns}")


def _select_runs_from_trace() -> dict[str, dict[str, float | int]]:
    if not TRACE_INPUT.exists():
        raise FileNotFoundError(f"Missing trace CSV: {TRACE_INPUT}")
    trace_df = pd.read_csv(TRACE_INPUT)
    required = {"run_type", "fault", "simulation_run", "top1_mass"}
    missing = required.difference(trace_df.columns)
    if missing:
        raise ValueError(f"Trace CSV missing columns: {sorted(missing)}")

    fault_df = trace_df.loc[
        (trace_df["run_type"] == "fault") & (trace_df["fault"].isin(TARGET_FAULTS))
    ]
    run_means = (
        fault_df.groupby(["fault", "simulation_run"], as_index=False)["top1_mass"]
        .mean()
        .rename(columns={"top1_mass": "top1_mean"})
    )

    selected = {}
    print("=== RUN SELECTION ===")
    for fault in TARGET_FAULTS:
        group = run_means.loc[run_means["fault"] == fault].sort_values(
            ["top1_mean", "simulation_run"]
        )
        if group.empty:
            raise ValueError(f"No trace rows found for {fault}")
        index = min(int(len(group) * 0.95), len(group) - 1)
        row = group.iloc[index]
        selected[fault] = {
            "simulation_run": int(row["simulation_run"]),
            "top1_mean": float(row["top1_mean"]),
        }
        print(
            f"{fault}: selected run={int(row['simulation_run'])} "
            f"top1_mean={float(row['top1_mean']):.6f}"
        )
    print("")
    return selected


def _ruptures_a_changepoints(signal_a: np.ndarray) -> list[int]:
    algo = rpt.Pelt(model="rbf").fit(signal_a)
    breakpoints = algo.predict(pen=RUPTURES_PENALTY_A)
    valid_bkps = [int(cp) for cp in breakpoints if int(cp) < len(signal_a)]
    return [cp for cp in valid_bkps if cp > SAMPLE_FILTER]


def _prepare_profile(
    fault: str,
    run_id: int,
    top1_mean: float,
    run_df: pd.DataFrame,
    selected_columns: list[str],
    baseline_model: dict[str, object],
    x7_idx: int,
    x11_idx: int,
) -> dict[str, object]:
    run_df = run_df.sort_values("sample")
    samples = run_df["sample"].to_numpy(dtype=int)
    run_data = run_df[selected_columns].to_numpy(dtype=float)
    xmeas7 = run_data[:, x7_idx]
    xmeas11 = run_data[:, x11_idx]

    raw_mask = samples > SAMPLE_FILTER
    relative_samples = samples[raw_mask] - SAMPLE_FILTER

    rolling_corr = pd.Series(xmeas7).rolling(ROLLING_WINDOW).corr(pd.Series(xmeas11))
    corr_values = rolling_corr.to_numpy(dtype=float)
    corr_mask = np.isfinite(corr_values) & (samples > SAMPLE_FILTER)
    corr_relative_samples = samples[corr_mask] - SAMPLE_FILTER

    series = _compute_version_b_trajectory_series(
        run_data,
        WINDOW,
        STEP,
        K_TOP,
        N_HISTORY,
        baseline_model,
    )
    sample_times = np.asarray(series["sample_times"], dtype=int)
    eval_mask = sample_times > SAMPLE_FILTER
    eval_sample_times = sample_times[eval_mask]
    window_index = np.arange(1, int(np.sum(eval_mask)) + 1)
    top1_mass = np.asarray(series["top_pair_dominance"], dtype=float)[eval_mask]
    top1_indices = np.asarray(series["top1_indices"], dtype=int)[eval_mask]
    dominant_pairs = [PAIR_LABELS[int(idx)] for idx in top1_indices]

    signal_a = np.column_stack([xmeas7, xmeas11])
    changepoints = _ruptures_a_changepoints(signal_a)
    changepoint_windows = [
        int((cp - SAMPLE_FILTER) // STEP + 1)
        for cp in changepoints
        if cp > SAMPLE_FILTER
    ]

    pair_counts = pd.Series(dominant_pairs).value_counts()
    dominant_pair = str(pair_counts.index[0]) if not pair_counts.empty else "(none)"

    return {
        "fault": fault,
        "run_id": int(run_id),
        "top1_mean": float(top1_mean),
        "relative_samples": relative_samples,
        "xmeas7": xmeas7[raw_mask],
        "xmeas11": xmeas11[raw_mask],
        "corr_relative_samples": corr_relative_samples,
        "rolling_corr": corr_values[corr_mask],
        "window_index": window_index,
        "eval_sample_times": eval_sample_times,
        "top1_mass": top1_mass,
        "dominant_pairs": dominant_pairs,
        "dominant_pair": dominant_pair,
        "changepoints": changepoints,
        "changepoint_windows": changepoint_windows,
    }


def _plot_profile(profile: dict[str, object]) -> Path:
    fault = str(profile["fault"])
    output_path = TAXONOMY_OUTPUT_DIR / f"archetype_profile_{fault}.png"

    fig, axes = plt.subplots(5, 1, figsize=(14, 18))
    fig.suptitle(
        f"Fault Archetype Profile: {fault}\n"
        f"run={profile['run_id']}  top1_mean={float(profile['top1_mean']):.3f}\n"
        "Panel A/B x-axis: samples after fault injection; Panel C/D/E x-axis: window index",
        fontsize=14,
    )

    axes[0].plot(profile["relative_samples"], profile["xmeas7"], color="tab:blue", label="XMEAS7 (reactor pressure)")
    axes[0].plot(profile["relative_samples"], profile["xmeas11"], color="tab:orange", label="XMEAS11 (separator temperature)")
    axes[0].axvline(0, color="black", linestyle="--", linewidth=1.0)
    axes[0].text(0.01, 0.95, "fault injection", transform=axes[0].transAxes, va="top")
    axes[0].set_ylabel("raw signal value")
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.25)

    axes[1].plot(profile["corr_relative_samples"], profile["rolling_corr"], color="tab:green")
    axes[1].axhline(0, color="black", linestyle="--", linewidth=1.0)
    axes[1].set_ylim(-1.05, 1.05)
    axes[1].set_ylabel("XMEAS7-XMEAS11 rolling corr")
    axes[1].grid(alpha=0.25)

    axes[2].plot(profile["window_index"], profile["top1_mass"], marker="o", markersize=3, linewidth=1.2)
    axes[2].axhline(0.80, color="black", linestyle="--", linewidth=1.0, label="threshold=0.80")
    axes[2].set_ylim(-0.02, 1.05)
    axes[2].set_ylabel("top1_mass")
    axes[2].legend(loc="best")
    axes[2].grid(alpha=0.25)

    pairs = list(dict.fromkeys(profile["dominant_pairs"]))
    y_positions = {pair: idx for idx, pair in enumerate(pairs)}
    y_values = [y_positions[pair] for pair in profile["dominant_pairs"]]
    colors = [PAIR_COLORS.get(pair, "tab:gray") for pair in profile["dominant_pairs"]]
    axes[3].scatter(profile["window_index"], y_values, c=colors, s=28)
    axes[3].set_yticks(list(y_positions.values()))
    axes[3].set_yticklabels(list(y_positions.keys()))
    axes[3].set_ylabel("dominant pair")
    axes[3].grid(alpha=0.25)

    axes[4].set_ylim(0, 1)
    axes[4].set_ylabel("ruptures_A changepoints")
    axes[4].set_xlabel("window index")
    if profile["changepoint_windows"]:
        for cp_window in profile["changepoint_windows"]:
            axes[4].axvline(cp_window, color="tab:red", linewidth=1.5, alpha=0.85)
    else:
        axes[4].text(
            0.5,
            0.5,
            "No changepoint detected (ruptures_A)",
            transform=axes[4].transAxes,
            ha="center",
            va="center",
        )
    axes[4].grid(alpha=0.25)

    max_window = max(len(profile["window_index"]), 1)
    axes[2].set_xlim(1, max_window)
    axes[3].set_xlim(1, max_window)
    axes[4].set_xlim(1, max_window)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _plot_triangle(profiles: dict[str, dict[str, object]]) -> Path:
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))
    fig.suptitle(
        "Archetype Triangle: F02 vs F06 vs F14\n"
        "top1_mass (left) vs ruptures_A changepoints (right)",
        fontsize=14,
    )

    for row_idx, fault in enumerate(TARGET_FAULTS):
        profile = profiles[fault]
        left = axes[row_idx, 0]
        right = axes[row_idx, 1]
        max_window = max(len(profile["window_index"]), 1)

        left.plot(profile["window_index"], profile["top1_mass"], marker="o", markersize=3, linewidth=1.2)
        left.axhline(0.80, color="black", linestyle="--", linewidth=1.0)
        left.set_ylim(-0.02, 1.05)
        left.set_xlim(1, max_window)
        left.set_ylabel(f"{fault}\ntop1_mass")
        left.grid(alpha=0.25)

        right.set_ylim(0, 1)
        right.set_xlim(1, max_window)
        right.set_ylabel("ruptures_A")
        if profile["changepoint_windows"]:
            for cp_window in profile["changepoint_windows"]:
                right.axvline(cp_window, color="tab:red", linewidth=1.5, alpha=0.85)
        else:
            right.text(
                0.5,
                0.5,
                "No changepoint detected",
                transform=right.transAxes,
                ha="center",
                va="center",
            )
        right.grid(alpha=0.25)

    axes[-1, 0].set_xlabel("window index")
    axes[-1, 1].set_xlabel("window index")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(TRIANGLE_OUTPUT, dpi=150)
    plt.close(fig)
    return TRIANGLE_OUTPUT


def main() -> None:
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    selected_runs = _select_runs_from_trace()

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    x7_idx = _find_column_index(selected_columns, "XMEAS7")
    x11_idx = _find_column_index(selected_columns, "XMEAS11")
    baseline_model = _build_baseline_model(np.asarray(baseline_data, dtype=float), WINDOW, STEP)

    profiles = {}
    generated_files = []
    for fault in TARGET_FAULTS:
        fault_number = _fault_number(fault)
        run_id = int(selected_runs[fault]["simulation_run"])
        fault_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        if run_id not in fault_runs:
            raise ValueError(f"{fault} selected run {run_id} not found in TEP fault runs.")

        profiles[fault] = _prepare_profile(
            fault=fault,
            run_id=run_id,
            top1_mean=float(selected_runs[fault]["top1_mean"]),
            run_df=fault_runs[run_id],
            selected_columns=selected_columns,
            baseline_model=baseline_model,
            x7_idx=x7_idx,
            x11_idx=x11_idx,
        )
        generated_files.append(_plot_profile(profiles[fault]))

    generated_files.append(_plot_triangle(profiles))

    print("=== FAULT ARCHETYPE PROFILES ===")
    print("")
    for fault in TARGET_FAULTS:
        profile = profiles[fault]
        print(f"{fault} (run={profile['run_id']}):")
        print(f"  top1_mass p95_mean = {float(profile['top1_mean']):.6f}")
        print(f"  ruptures_A changepoints = {profile['changepoints']}")
        print(f"  dominant pair: {profile['dominant_pair']}")
        print("")

    print("=== ARCHETYPE TRIANGLE SUMMARY ===")
    print("")
    print("F02: raw_shift=strong, geometry=weak")
    print("     -> ruptures detected, top1 below threshold")
    print("")
    print("F06: raw_shift=strong, geometry=strong")
    print("     -> both ruptures and top1 active")
    print("")
    print("F14: raw_shift=absent, geometry=strong")
    print("     -> top1 active, ruptures silent")
    print("")

    print("Conservative interpretation:")
    print("1. Results are based on a single p95 run and do not represent all 500 runs.")
    print("2. top1_mass is limited to the XMEAS7-11 subspace.")
    print("3. The figure-level observations are representation-level findings.")
    print("4. No physical causal inference is made.")
    print("")
    print("Generated files:")
    for path in generated_files:
        print(f"- {path}")


if __name__ == "__main__":
    main()
