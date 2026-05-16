"""Lead-lag propagation consistency audit for the F13 core variable chain."""

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

from fault_stationary_scan import _load_normal_runs
from tep_experiment import _load_all_fault_runs, _resolve_paths

CORE_CHAIN = [
    "xmeas_7",
    "xmeas_11",
    "xmeas_18",
    "xmeas_19",
]
PAIR_CHAIN = [
    ("xmeas_7", "xmeas_11"),
    ("xmeas_11", "xmeas_18"),
    ("xmeas_18", "xmeas_19"),
    ("xmeas_7", "xmeas_18"),
    ("xmeas_7", "xmeas_19"),
]
LAGS = range(-50, 51)
SAMPLE_FILTER = 200
N_RUNS = 200

OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "lead_lag_propagation.csv"
OUTPUT_GRAPH = PROJECT_ROOT / "outputs" / "taxonomy" / "lead_lag_graph.png"
OUTPUT_HIST = PROJECT_ROOT / "outputs" / "taxonomy" / "lag_distribution.png"


def _resolve_core_columns(columns):
    lower_map = {column.lower(): column for column in columns}
    resolved = {}
    for variable in CORE_CHAIN:
        if variable in lower_map:
            resolved[variable] = lower_map[variable]
        else:
            raise ValueError(f"Missing required variable column: {variable}")
    return resolved


def _safe_corr(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or y.size < 3:
        return np.nan
    x_std = float(np.std(x))
    y_std = float(np.std(y))
    if x_std < 1e-12 or y_std < 1e-12:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _lagged_corr(x, y, lag):
    if lag > 0:
        x_seg = x[:-lag]
        y_seg = y[lag:]
    elif lag < 0:
        x_seg = x[-lag:]
        y_seg = y[:lag]
    else:
        x_seg = x
        y_seg = y
    return _safe_corr(x_seg, y_seg)


def _best_lag_and_corr(x, y):
    best_lag = None
    best_corr = None
    best_abs = -np.inf
    for lag in LAGS:
        corr = _lagged_corr(x, y, lag)
        if np.isnan(corr):
            continue
        abs_corr = abs(corr)
        if abs_corr > best_abs:
            best_abs = abs_corr
            best_lag = int(lag)
            best_corr = float(corr)
    if best_lag is None:
        return np.nan, np.nan
    return float(best_lag), float(best_corr)


def _load_data():
    training_path, testing_path = _resolve_paths(".")
    if training_path is None or testing_path is None:
        raise FileNotFoundError("TEP CSV files not found under data/raw.")

    header = pd.read_csv(training_path, nrows=0).columns.tolist()
    resolved = _resolve_core_columns(header)
    selected_columns = list(resolved.values())

    normal_runs = _load_normal_runs(".", selected_columns)
    usecols = ["faultNumber", "simulationRun", "sample", *selected_columns]
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    return resolved, normal_runs, f13_runs


def _extract_series(run_df, resolved_columns):
    sample_col = next((col for col in run_df.columns if col.lower() == "sample"), None)
    if sample_col is not None:
        run_df = run_df.loc[run_df[sample_col] > SAMPLE_FILTER].sort_values(sample_col)
    out = {}
    for logical_name, actual_name in resolved_columns.items():
        out[logical_name] = run_df[actual_name].to_numpy(dtype=float)
    return out


def _compute_run_level_lags(run_map, resolved_columns, label):
    rows = []
    for run_idx in range(1, N_RUNS + 1):
        run_df = run_map.get(run_idx)
        if run_df is None:
            continue
        series_map = _extract_series(run_df, resolved_columns)
        for src, dst in PAIR_CHAIN:
            best_lag, best_corr = _best_lag_and_corr(series_map[src], series_map[dst])
            rows.append(
                {
                    "source_label": label,
                    "run_id": int(run_idx),
                    "pair": f"{src}->{dst}",
                    "src": src,
                    "dst": dst,
                    "best_lag": best_lag,
                    "best_corr": best_corr,
                }
            )
    return pd.DataFrame(rows)


def _summarize_pair(real_df, normal_df):
    rows = []
    for src, dst in PAIR_CHAIN:
        pair_name = f"{src}->{dst}"
        real_pair = real_df.loc[real_df["pair"] == pair_name]
        normal_pair = normal_df.loc[normal_df["pair"] == pair_name]

        real_lags = real_pair["best_lag"].dropna().to_numpy(dtype=float)
        real_corr = real_pair["best_corr"].dropna().to_numpy(dtype=float)
        normal_lags = normal_pair["best_lag"].dropna().to_numpy(dtype=float)

        direction_consistency = float(np.mean(real_lags > 0)) if real_lags.size else float("nan")
        normal_direction_consistency = (
            float(np.mean(normal_lags > 0)) if normal_lags.size else float("nan")
        )

        rows.append(
            {
                "pair": pair_name,
                "mean_best_lag": float(np.mean(real_lags)) if real_lags.size else float("nan"),
                "std_best_lag": float(np.std(real_lags, ddof=1)) if real_lags.size > 1 else 0.0,
                "mean_best_corr": float(np.mean(real_corr)) if real_corr.size else float("nan"),
                "direction_consistency": direction_consistency,
                "normal_direction_consistency": normal_direction_consistency,
                "delta_consistency": direction_consistency - normal_direction_consistency,
            }
        )
    return pd.DataFrame(rows)


def _plot_graph(summary_df):
    positions = {
        "xmeas_7": (0.1, 0.6),
        "xmeas_11": (0.4, 0.75),
        "xmeas_18": (0.7, 0.45),
        "xmeas_19": (0.9, 0.2),
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Lead-lag consistency graph (F13)")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    for node, (x, y) in positions.items():
        ax.scatter([x], [y], s=1200, color="tab:blue", alpha=0.9, edgecolors="black")
        ax.text(x, y, node, ha="center", va="center", color="white", fontsize=10, weight="bold")

    for row in summary_df.itertuples(index=False):
        if not (row.direction_consistency > 0.70):
            continue
        src, dst = row.pair.split("->")
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        width = 1.0 + 6.0 * float(row.direction_consistency)
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", linewidth=width, color="tab:red", alpha=0.8),
        )
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        ax.text(
            mx,
            my,
            f"{row.mean_best_lag:.1f}",
            fontsize=9,
            color="black",
            bbox=dict(facecolor="white", alpha=0.8, edgecolor="none", boxstyle="round,pad=0.2"),
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_GRAPH, dpi=150)
    plt.close(fig)


def _plot_histograms(real_df, normal_df):
    fig, axes = plt.subplots(3, 2, figsize=(12, 12), constrained_layout=True)
    axes = axes.flatten()
    for ax, (src, dst) in zip(axes, PAIR_CHAIN):
        pair_name = f"{src}->{dst}"
        real_lags = real_df.loc[real_df["pair"] == pair_name, "best_lag"].dropna().to_numpy(dtype=float)
        normal_lags = normal_df.loc[normal_df["pair"] == pair_name, "best_lag"].dropna().to_numpy(dtype=float)
        ax.hist(real_lags, bins=np.arange(-50.5, 51.5, 2.0), alpha=0.55, color="tab:orange", label="F13")
        ax.hist(normal_lags, bins=np.arange(-50.5, 51.5, 2.0), alpha=0.45, color="tab:gray", label="NORMAL")
        ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
        ax.set_title(pair_name)
        ax.set_xlabel("best_lag")
        ax.set_ylabel("count")
        ax.grid(alpha=0.3)
        ax.legend()
    axes[-1].axis("off")
    fig.savefig(OUTPUT_HIST, dpi=150)
    plt.close(fig)


def main():
    resolved_columns, normal_runs, f13_runs = _load_data()
    normal_df = _compute_run_level_lags(normal_runs, resolved_columns, "NORMAL")
    f13_df = _compute_run_level_lags(f13_runs, resolved_columns, "F13")
    summary_df = _summarize_pair(f13_df, normal_df)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    _plot_graph(summary_df)
    _plot_histograms(f13_df, normal_df)

    print("=== LEAD-LAG PROPAGATION SUMMARY ===")
    print(summary_df.to_string(index=False))
    print("\nConservative interpretation:")
    strong_pairs = summary_df.loc[
        (summary_df["direction_consistency"] > 0.70)
        & (summary_df["delta_consistency"] > 0.15),
        "pair",
    ].tolist()
    if strong_pairs:
        print(
            "Consistent lead-lag structure is visible for: "
            + ", ".join(strong_pairs)
            + "."
        )
    else:
        print("No reliable directional structure observed above the chosen consistency threshold.")
    print(
        "This remains an observability audit only. It does not establish fault causality or "
        "prove physical system dynamics."
    )
    return summary_df


if __name__ == "__main__":
    main()
