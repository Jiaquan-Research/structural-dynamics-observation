"""Visualize structural state trajectories for selected TEP faults."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

from tep_experiment import (
    _load_baseline_and_columns,
    _build_baseline_model,
    _collect_window_features,
    _differenced_correlation_features,
    _dominance_series,
    _pair_switching_rate,
    _score_features,
    _stream_fault_run_csv,
    _run_version_b_on_fault_run,
)
from task0_protocol import stride_sample


def _resolve_fault_free_testing_path():
    """Resolve the fault-free testing CSV path with case-insensitive fallbacks."""

    candidates = [
        str(DATA_ROOT / "fault_free_testing.csv"),
        str(DATA_ROOT / "Fault_Free_Testing.csv"),
    ]
    for candidate in candidates:
        try:
            path = pd.io.common.get_handle(candidate, mode="r").handle.name
            return path
        except Exception:
            continue
    return None


def save_fault_trajectory(
    faults_to_plot=(8, 13, 19),
    run_idx=1,
    W=100,
    S=10,
    fault_onset=160,
    K_persist=5,
    k_top=3,
    n_history=10,
    output_path=None,
):
    """Generate the requested 3-panel fault trajectory figure."""

    if output_path is None:
        output_path = OUTPUT_ROOT / "trajectories" / "fault_trajectory.png"
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, W, S)
    records_path = OUTPUT_ROOT / "csv" / "trajectory_records.csv"
    normal_testing_path = _resolve_fault_free_testing_path()
    if normal_testing_path is None:
        print("请先从Kaggle下载TEP CSV数据集")
        return None

    normal_usecols = ["simulationRun", "sample", *selected_columns]
    normal_df = pd.read_csv(normal_testing_path, usecols=normal_usecols)
    normal_df = normal_df.loc[normal_df["simulationRun"] == run_idx].sort_values("sample")
    normal_data = normal_df[selected_columns].to_numpy(dtype=float)
    normal_range = range(0, len(normal_data))
    normal_times = stride_sample(normal_range, W, S)
    normal_sample_times = np.asarray(normal_times, dtype=int)
    normal_features = _collect_window_features(
        normal_data, normal_times, W, _differenced_correlation_features
    )
    normal_d2 = _score_features(normal_features, baseline_model["mu_b"], baseline_model["s_b_inv"])
    normal_centered = normal_features - baseline_model["mu_b"]
    normal_contributions = (normal_centered**2) * np.diag(baseline_model["s_b_inv"])
    normal_dominance_pairs, normal_dominance = _dominance_series(
        normal_contributions, normal_sample_times, k_top=k_top, n_history=n_history
    )
    normal_top1_indices = np.argmax(normal_contributions, axis=1)
    normal_switching = _pair_switching_rate(
        normal_top1_indices, normal_sample_times, n_history=n_history
    )
    normal_version = {
        "sample_times": normal_sample_times,
        "d2_b": normal_d2,
        "top_pair_dominance": normal_dominance,
        "pair_switching_rate": normal_switching,
        "dominance_pairs": normal_dominance_pairs,
    }

    trajectories = {}
    records_df = None
    if records_path.exists():
        records_df = pd.read_csv(records_path)
    for fault_number in faults_to_plot:
        if records_df is not None:
            fault_records = records_df.loc[
                (records_df["fault_id"] == fault_number) & (records_df["run_idx"] == run_idx)
            ].sort_values("sample_idx")
        else:
            fault_records = pd.DataFrame()
        if not fault_records.empty:
            trajectories[fault_number] = {
                "sample_times": fault_records["sample_idx"].to_numpy(dtype=int),
                "switching": fault_records["switching"].to_numpy(dtype=float),
                "dominance": fault_records["dominance"].to_numpy(dtype=float),
                "log_d2": fault_records["log_d2"].to_numpy(dtype=float),
            }
        else:
            fault_df, first_run = _stream_fault_run_csv(
                testing_path, usecols=usecols, fault_number=fault_number
            )
            if int(first_run) != run_idx:
                raise ValueError(
                    f"Requested run_idx={run_idx}, but first available run for fault {fault_number} "
                    f"is {first_run}."
                )
            fault_data = fault_df[selected_columns].to_numpy(dtype=float)
            version_b = _run_version_b_on_fault_run(
                fault_data,
                fault_onset,
                W,
                S,
                K_persist,
                k_top,
                n_history,
                baseline_model,
                threshold_sigma=2.0,
            )
            trajectories[fault_number] = {
                "sample_times": version_b["sample_times"],
                "switching": version_b["pair_switching_rate"],
                "dominance": version_b["top_pair_dominance"],
                "log_d2": np.log1p(version_b["d2_b"]),
            }

    colors = {8: "tab:blue", 13: "tab:orange", 19: "tab:green"}

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    ax = axes[0]
    ax.plot(
        normal_version["pair_switching_rate"],
        normal_version["top_pair_dominance"],
        color="gray",
        linestyle="--",
        alpha=0.6,
        linewidth=1.4,
        label="Normal",
        zorder=0,
    )
    for fault_number in faults_to_plot:
        traj = trajectories[fault_number]
        x = traj["switching"]
        y = traj["dominance"]
        t = np.linspace(0.1, 1.0, len(x))
        ax.scatter(x, y, c=t, cmap="Blues" if fault_number == 8 else ("Oranges" if fault_number == 13 else "Greens"), s=18)
        ax.plot(
            x,
            y,
            color=colors[fault_number],
            alpha=0.35,
            linewidth=1.2,
            label=f"F{fault_number:02d}",
            zorder=1,
        )
        onset_idx = int(np.searchsorted(traj["sample_times"], fault_onset))
        onset_idx = min(onset_idx, len(x) - 1)
        ax.scatter(x[0], y[0], color=colors[fault_number], marker="o", s=70, edgecolors="black", zorder=2)
        ax.scatter(x[-1], y[-1], color=colors[fault_number], marker="s", s=70, edgecolors="black", zorder=2)
        ax.scatter(x[onset_idx], y[onset_idx], color=colors[fault_number], marker="*", s=140, edgecolors="black", zorder=2)
        for idx in range(0, len(x) - 10, 10):
            dx = x[idx + 1] - x[idx]
            dy = y[idx + 1] - y[idx]
            ax.arrow(
                x[idx],
                y[idx],
                dx,
                dy,
                color=colors[fault_number],
                alpha=0.5,
                width=0.0005,
                head_width=0.01,
                length_includes_head=True,
                zorder=2,
            )
    ax.set_xlabel("switching(t)")
    ax.set_ylabel("dominance(t)")
    ax.set_title("Trajectory in switching-dominance space")
    ax.grid(alpha=0.3)
    ax.legend()

    ax = axes[1]
    ax.plot(
        normal_version["sample_times"],
        np.log1p(normal_version["d2_b"]),
        color="gray",
        linestyle="--",
        alpha=0.6,
        linewidth=1.5,
        label="Normal",
    )
    for fault_number in faults_to_plot:
        traj = trajectories[fault_number]
        ax.plot(
            traj["sample_times"],
            traj["log_d2"],
            color=colors[fault_number],
            linewidth=1.5,
            label=f"F{fault_number:02d}",
        )
    ax.axvline(fault_onset, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("sample index")
    ax.set_ylabel("log(1 + D2)")
    ax.set_title("log(1 + D2(t))")
    ax.grid(alpha=0.3)
    ax.legend()

    ax = axes[2]
    axr = ax.twinx()
    ax.plot(
        normal_version["sample_times"],
        normal_version["pair_switching_rate"],
        color="gray",
        linewidth=1.4,
        linestyle="--",
        alpha=0.6,
        label="Normal switching",
    )
    axr.plot(
        normal_version["sample_times"],
        normal_version["top_pair_dominance"],
        color="gray",
        linewidth=1.4,
        linestyle="--",
        alpha=0.6,
        label="Normal dominance",
    )
    for fault_number in (8, 13):
        traj = trajectories[fault_number]
        ax.plot(
            traj["sample_times"],
            traj["switching"],
            color=colors[fault_number],
            linewidth=1.4,
            linestyle="-",
            label=f"F{fault_number:02d} switching",
        )
        axr.plot(
            traj["sample_times"],
            traj["dominance"],
            color=colors[fault_number],
            linewidth=1.4,
            linestyle="--",
            label=f"F{fault_number:02d} dominance",
        )
    ax.axvline(fault_onset, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("sample index")
    ax.set_ylabel("switching(t)")
    axr.set_ylabel("dominance(t)")
    ax.set_title("F08 vs F13: switching and dominance")
    ax.grid(alpha=0.3)
    handles_l, labels_l = ax.get_legend_handles_labels()
    handles_r, labels_r = axr.get_legend_handles_labels()
    ax.legend(handles_l + handles_r, labels_l + labels_r, loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    save_fault_trajectory()
