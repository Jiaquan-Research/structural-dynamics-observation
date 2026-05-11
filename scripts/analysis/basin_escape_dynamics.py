"""Basin escape / return dynamics from structural trajectory records."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

PAIR_LABELS = [
    "XMEAS7-XMEAS8",
    "XMEAS7-XMEAS9",
    "XMEAS7-XMEAS10",
    "XMEAS7-XMEAS11",
    "XMEAS8-XMEAS9",
    "XMEAS8-XMEAS10",
    "XMEAS8-XMEAS11",
    "XMEAS9-XMEAS10",
    "XMEAS9-XMEAS11",
    "XMEAS10-XMEAS11",
]

FOCUS_FAULTS = [0, 4, 12, 13, 14]
RETURN_K = 5


def _fault_label(fault_number):
    return "NORMAL" if int(fault_number) == 0 else f"F{int(fault_number):02d}"


def _pair_to_idx(pair_name):
    return PAIR_LABELS.index(pair_name)


def _load_one_file(path):
    df = pd.read_csv(path, dtype=str, low_memory=False)
    if "fault_number" in df.columns:
        out = df[
            ["fault_number", "fault_label", "run_id", "sample", "top_pair", "top_pair_idx"]
        ].copy()
        out["fault_number"] = pd.to_numeric(out["fault_number"], errors="coerce")
        out["run_id"] = pd.to_numeric(out["run_id"], errors="coerce")
        out["sample"] = pd.to_numeric(out["sample"], errors="coerce")
        out["top_pair_idx"] = pd.to_numeric(out["top_pair_idx"], errors="coerce")
    else:
        fault_number = pd.to_numeric(df["fault_id"], errors="coerce")
        run_id = pd.to_numeric(df["run_idx"], errors="coerce")
        sample = pd.to_numeric(df["sample_idx"], errors="coerce")
        top_pair = df["top_pair"].astype(str)
        top_pair_idx = top_pair.map(lambda x: _pair_to_idx(x) if x in PAIR_LABELS else np.nan)
        out = pd.DataFrame(
            {
                "fault_number": fault_number,
                "fault_label": fault_number.map(lambda x: _fault_label(int(x)) if pd.notna(x) else np.nan),
                "run_id": run_id,
                "sample": sample,
                "top_pair": top_pair,
                "top_pair_idx": top_pair_idx,
            }
        )
    out = out.loc[
        out["fault_number"].notna()
        & out["run_id"].notna()
        & out["sample"].notna()
        & out["top_pair"].isin(PAIR_LABELS)
        & out["top_pair_idx"].notna()
    ].copy()
    out["fault_number"] = out["fault_number"].astype(int)
    out["run_id"] = out["run_id"].astype(int)
    out["sample"] = out["sample"].astype(int)
    out["top_pair_idx"] = out["top_pair_idx"].astype(int)
    return out


def load_trajectory_records():
    """Load and standardize all available trajectory_records*.csv files."""

    candidates = [
        OUTPUT_ROOT / "csv" / "trajectory_records_F0_F4_F13_runs500.csv",
        OUTPUT_ROOT / "csv" / "trajectory_records_F0_F4_F13_runs10.csv",
        OUTPUT_ROOT / "csv" / "trajectory_records.csv",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        raise FileNotFoundError("No trajectory_records*.csv files found.")

    frames = [_load_one_file(path) for path in existing]
    combined = pd.concat(frames, axis=0, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["fault_number", "run_id", "sample"], keep="first"
    )
    combined = combined.sort_values(["fault_number", "run_id", "sample"]).reset_index(drop=True)
    return combined


def _residence_segments(states, dominant_idx):
    lengths = []
    current = 0
    for state in states:
        if int(state) == dominant_idx:
            current += 1
        else:
            if current > 0:
                lengths.append(current)
                current = 0
    if current > 0:
        lengths.append(current)
    return lengths


def _escape_and_return(states, dominant_idx, k_return):
    inside_time = int(np.sum(states == dominant_idx))
    escape_count = 0
    return_count = 0
    n = len(states)
    idx = 0
    while idx < n - 1:
        if states[idx] == dominant_idx and states[idx + 1] != dominant_idx:
            escape_count += 1
            future = states[idx + 1 : min(n, idx + 1 + k_return)]
            if np.any(future == dominant_idx):
                return_count += 1
        idx += 1
    escape_rate = float(escape_count / inside_time) if inside_time > 0 else np.nan
    return_probability = float(return_count / escape_count) if escape_count > 0 else np.nan
    return escape_rate, return_probability


def summarize_fault(df_fault):
    """Compute dominant-basin residence / escape / return metrics for one fault."""

    occupancy = (
        df_fault["top_pair_idx"].value_counts(normalize=True).sort_index().reindex(range(len(PAIR_LABELS)), fill_value=0.0)
    )
    dominant_idx = int(occupancy.idxmax())
    dominant_pair = PAIR_LABELS[dominant_idx]
    dominant_occ = float(occupancy.iloc[dominant_idx])

    all_segments = []
    weighted_inside = 0
    weighted_exits = 0
    weighted_returns = 0
    return_defined = 0

    for _run_id, run_df in df_fault.groupby("run_id", sort=True):
        states = run_df.sort_values("sample")["top_pair_idx"].to_numpy(dtype=int)
        segments = _residence_segments(states, dominant_idx)
        all_segments.extend(segments)
        escape_rate, return_prob = _escape_and_return(states, dominant_idx, RETURN_K)
        inside_time = int(np.sum(states == dominant_idx))
        weighted_inside += inside_time
        if inside_time > 0 and np.isfinite(escape_rate):
            exits = int(round(escape_rate * inside_time))
            weighted_exits += exits
            if exits > 0 and np.isfinite(return_prob):
                weighted_returns += return_prob * exits
                return_defined += exits

    mean_res = float(np.mean(all_segments)) if all_segments else np.nan
    median_res = float(np.median(all_segments)) if all_segments else np.nan
    max_res = int(np.max(all_segments)) if all_segments else 0
    escape_rate = float(weighted_exits / weighted_inside) if weighted_inside > 0 else np.nan
    return_probability = float(weighted_returns / weighted_exits) if weighted_exits > 0 else np.nan

    return {
        "dominant_pair": dominant_pair,
        "occupancy": dominant_occ,
        "mean_residence_time": mean_res,
        "median_residence_time": median_res,
        "max_residence_time": max_res,
        "escape_rate": escape_rate,
        "return_probability": return_probability,
        "segment_lengths": all_segments,
    }


def _plot_taxonomy(summary_df, output_path):
    fig, axes = plt.subplots(3, 1, figsize=(11, 15), constrained_layout=True)

    ax = axes[0]
    for row in summary_df.itertuples(index=False):
        label = _fault_label(row.fault_number)
        ax.scatter(row.occupancy, row.mean_residence_time, s=140, alpha=0.85)
        ax.text(row.occupancy + 0.005, row.mean_residence_time + 0.5, label, fontsize=8)
    ax.set_xlabel("occupancy")
    ax.set_ylabel("mean_residence_time")
    ax.grid(alpha=0.3)

    ax = axes[1]
    for row in summary_df.itertuples(index=False):
        label = _fault_label(row.fault_number)
        ax.scatter(row.escape_rate, row.return_probability, s=140, alpha=0.85)
        ax.text(row.escape_rate + 0.003, row.return_probability + 0.01, label, fontsize=8)
    ax.set_xlabel("escape_rate")
    ax.set_ylabel("return_probability")
    ax.grid(alpha=0.3)

    ax = axes[2]
    bins = np.arange(1, max(int(summary_df["max_residence_time"].max()), 2) + 2) - 0.5
    colors = {0: "gray", 12: "tab:green", 13: "tab:orange", 14: "tab:blue"}
    for fault_number in FOCUS_FAULTS:
        row = summary_df.loc[summary_df["fault_number"] == fault_number]
        if row.empty:
            continue
        segments = row.iloc[0]["segment_lengths"]
        if not segments:
            continue
        ax.hist(
            segments,
            bins=bins,
            alpha=0.4,
            label=_fault_label(fault_number),
            density=True,
            color=colors.get(fault_number, None),
        )
    ax.set_xlabel("residence time")
    ax.set_ylabel("density")
    ax.legend()
    ax.grid(alpha=0.3)

    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    df = load_trajectory_records()
    available_faults = sorted(int(value) for value in df["fault_number"].unique())

    summary_rows = []
    for fault_number in available_faults:
        df_fault = df.loc[df["fault_number"] == fault_number].copy()
        metrics = summarize_fault(df_fault)
        summary_rows.append(
            {
                "fault_number": int(fault_number),
                "dominant_pair": metrics["dominant_pair"],
                "mean_residence_time": metrics["mean_residence_time"],
                "median_residence_time": metrics["median_residence_time"],
                "max_residence_time": metrics["max_residence_time"],
                "escape_rate": metrics["escape_rate"],
                "return_probability": metrics["return_probability"],
                "occupancy": metrics["occupancy"],
                "segment_lengths": metrics["segment_lengths"],
            }
        )

    summary_df = pd.DataFrame(summary_rows).sort_values("fault_number").reset_index(drop=True)
    summary_df_csv = summary_df.drop(columns=["segment_lengths"])
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    summary_df_csv.to_csv(OUTPUT_ROOT / "csv" / "basin_escape_summary.csv", index=False, encoding="utf-8")
    _plot_taxonomy(summary_df, OUTPUT_ROOT / "taxonomy" / "basin_escape_taxonomy.png")

    for row in summary_df.itertuples(index=False):
        label = _fault_label(row.fault_number)
        print(f"{label} | pair={row.dominant_pair}")
        print(f"     occ={row.occupancy:.3f}")
        print(f"     mean_res={row.mean_residence_time:.1f}")
        print(f"     escape={row.escape_rate:.3f}")
        print(f"     return={row.return_probability:.2f}")

    return summary_df_csv


if __name__ == "__main__":
    main()
