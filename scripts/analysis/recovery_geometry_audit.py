"""Recovery-style audit for propagation geometry relative to NORMAL baseline."""

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

from lead_lag_propagation_audit import (
    PAIR_CHAIN,
    _best_lag_and_corr,
    _load_data,
)

CORE_CHAIN = [
    "xmeas_7",
    "xmeas_11",
    "xmeas_18",
    "xmeas_19",
]
WINDOW = 100
STEP = 20
SAMPLE_FILTER = 200
N_RUNS = 200
RECOVERY_THRESHOLD = 5.0

OUTPUT_RUNLEVEL = PROJECT_ROOT / "outputs" / "csv" / "recovery_geometry_runlevel.csv"
OUTPUT_SUMMARY = PROJECT_ROOT / "outputs" / "csv" / "recovery_geometry_summary.csv"
OUTPUT_TRAJECTORY = PROJECT_ROOT / "outputs" / "taxonomy" / "geometry_error_trajectory.png"
OUTPUT_RECOVERY_HIST = PROJECT_ROOT / "outputs" / "taxonomy" / "recovery_time_distribution.png"
OUTPUT_UNRECOVERED = PROJECT_ROOT / "outputs" / "taxonomy" / "unrecovered_ratio_comparison.png"


def _extract_series(run_df, resolved_columns):
    sample_col = next((col for col in run_df.columns if col.lower() == "sample"), None)
    if sample_col is not None:
        run_df = run_df.loc[run_df[sample_col] > SAMPLE_FILTER].sort_values(sample_col)
    out = {}
    for logical_name, actual_name in resolved_columns.items():
        out[logical_name] = run_df[actual_name].to_numpy(dtype=float)
    return out


def _compute_window_lag_rows(run_map, resolved_columns, source_label):
    rows = []
    for run_idx in range(1, N_RUNS + 1):
        run_df = run_map.get(run_idx)
        if run_df is None:
            continue
        series_map = _extract_series(run_df, resolved_columns)
        length = len(next(iter(series_map.values())))
        if length < WINDOW:
            continue
        window_id = 0
        for end in range(WINDOW, length + 1, STEP):
            start = end - WINDOW
            window_id += 1
            for src, dst in PAIR_CHAIN:
                best_lag, best_corr = _best_lag_and_corr(
                    series_map[src][start:end],
                    series_map[dst][start:end],
                )
                rows.append(
                    {
                        "source_label": source_label,
                        "run_id": int(run_idx),
                        "window_id": int(window_id),
                        "pair": f"{src}->{dst}",
                        "best_lag": float(best_lag),
                        "best_corr": float(best_corr),
                    }
                )
    return pd.DataFrame(rows)


def _compute_normal_baseline_lags(runlevel_df):
    normal_df = runlevel_df.loc[runlevel_df["source_label"] == "NORMAL"]
    return normal_df.groupby("pair", as_index=False)["best_lag"].mean().rename(
        columns={"best_lag": "normal_baseline_lag"}
    )


def _compute_geometry_error_df(runlevel_df, baseline_df):
    merged = runlevel_df.merge(baseline_df, on="pair", how="left")
    merged["pair_error"] = (merged["best_lag"] - merged["normal_baseline_lag"]).abs()
    geometry_error_df = (
        merged.groupby(["source_label", "run_id", "window_id"], as_index=False)["pair_error"]
        .mean()
        .rename(columns={"pair_error": "geometry_error"})
    )
    return geometry_error_df


def _summarize_recovery(geometry_error_df):
    rows = []
    for source_label, group in geometry_error_df.groupby("source_label", sort=True):
        recovery_times = []
        max_errors = []
        mean_errors = []
        unrecovered_ratios = []
        for run_id, run_df in group.groupby("run_id", sort=True):
            errors = run_df.sort_values("window_id")["geometry_error"].to_numpy(dtype=float)
            errors = errors[np.isfinite(errors)]
            if errors.size == 0:
                continue
            max_errors.append(float(np.max(errors)))
            mean_errors.append(float(np.mean(errors)))
            unrecovered_ratios.append(float(np.mean(errors >= RECOVERY_THRESHOLD)))
            recovered = np.where(errors < RECOVERY_THRESHOLD)[0]
            if recovered.size > 0:
                recovery_times.append(float(recovered[0] + 1))
        rows.append(
            {
                "source_label": source_label,
                "mean_recovery_time": float(np.mean(recovery_times)) if recovery_times else float("nan"),
                "mean_max_geometry_error": float(np.mean(max_errors)) if max_errors else float("nan"),
                "mean_geometry_error": float(np.mean(mean_errors)) if mean_errors else float("nan"),
                "mean_unrecovered_ratio": float(np.mean(unrecovered_ratios)) if unrecovered_ratios else float("nan"),
            }
        )
    return pd.DataFrame(rows).sort_values("source_label").reset_index(drop=True)


def _plot_trajectory(geometry_error_df):
    fig, ax = plt.subplots(figsize=(10, 6))
    for source_label, color in [("NORMAL", "tab:gray"), ("F13", "tab:orange")]:
        group = geometry_error_df.loc[geometry_error_df["source_label"] == source_label]
        mean_by_window = group.groupby("window_id", as_index=False)["geometry_error"].mean()
        ax.plot(
            mean_by_window["window_id"],
            mean_by_window["geometry_error"],
            label=source_label,
            color=color,
            linewidth=2.0,
        )
    ax.axhline(RECOVERY_THRESHOLD, color="black", linestyle="--", linewidth=1.2)
    ax.set_title("Average geometry error trajectory")
    ax.set_xlabel("window index")
    ax.set_ylabel("geometry_error")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_TRAJECTORY, dpi=150)
    plt.close(fig)


def _plot_recovery_hist(geometry_error_df):
    fig, ax = plt.subplots(figsize=(10, 6))
    for source_label, color in [("NORMAL", "tab:gray"), ("F13", "tab:orange")]:
        recovery_times = []
        for _, run_df in geometry_error_df.loc[geometry_error_df["source_label"] == source_label].groupby("run_id"):
            errors = run_df.sort_values("window_id")["geometry_error"].to_numpy(dtype=float)
            recovered = np.where(errors < RECOVERY_THRESHOLD)[0]
            if recovered.size > 0:
                recovery_times.append(float(recovered[0] + 1))
        ax.hist(recovery_times, bins=20, alpha=0.5, label=source_label, color=color)
    ax.set_title("Recovery time distribution")
    ax.set_xlabel("recovery_time (window index)")
    ax.set_ylabel("count")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_RECOVERY_HIST, dpi=150)
    plt.close(fig)


def _plot_unrecovered(summary_df):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(
        summary_df["source_label"],
        summary_df["mean_unrecovered_ratio"],
        color=["tab:gray", "tab:orange"],
        alpha=0.85,
    )
    ax.set_title("Mean unrecovered ratio")
    ax.set_xlabel("source")
    ax.set_ylabel("mean_unrecovered_ratio")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_UNRECOVERED, dpi=150)
    plt.close(fig)


def main():
    resolved_columns, normal_runs, f13_runs = _load_data()
    normal_runlevel = _compute_window_lag_rows(normal_runs, resolved_columns, "NORMAL")
    f13_runlevel = _compute_window_lag_rows(f13_runs, resolved_columns, "F13")
    lag_runlevel = pd.concat([normal_runlevel, f13_runlevel], axis=0, ignore_index=True)

    baseline_df = _compute_normal_baseline_lags(lag_runlevel)
    geometry_error_df = _compute_geometry_error_df(lag_runlevel, baseline_df)
    summary_df = _summarize_recovery(geometry_error_df)

    OUTPUT_RUNLEVEL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TRAJECTORY.parent.mkdir(parents=True, exist_ok=True)
    geometry_error_df.to_csv(OUTPUT_RUNLEVEL, index=False, encoding="utf-8")
    summary_df.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8")

    _plot_trajectory(geometry_error_df)
    _plot_recovery_hist(geometry_error_df)
    _plot_unrecovered(summary_df)

    print("=== RECOVERY GEOMETRY SUMMARY ===")
    for row in summary_df.itertuples(index=False):
        print(f"{row.source_label}:")
        print(f"mean_recovery_time = {row.mean_recovery_time:.6f}")
        print(f"mean_max_geometry_error = {row.mean_max_geometry_error:.6f}")
        print(f"mean_geometry_error = {row.mean_geometry_error:.6f}")
        print(f"mean_unrecovered_ratio = {row.mean_unrecovered_ratio:.6f}")

    normal_row = summary_df.loc[summary_df["source_label"] == "NORMAL"].iloc[0]
    f13_row = summary_df.loc[summary_df["source_label"] == "F13"].iloc[0]
    print("\ndelta_recovery_time = {:.6f}".format(f13_row["mean_recovery_time"] - normal_row["mean_recovery_time"]))
    print(
        "delta_unrecovered_ratio = {:.6f}".format(
            f13_row["mean_unrecovered_ratio"] - normal_row["mean_unrecovered_ratio"]
        )
    )

    print("\nConservative interpretation:")
    print("NORMAL itself contains dynamic geometry fluctuations.")
    print("This experiment measures deviation relative to NORMAL baseline geometry.")
    print("This is a resilience-style metric, not a proof of causality.")
    return summary_df


if __name__ == "__main__":
    main()
