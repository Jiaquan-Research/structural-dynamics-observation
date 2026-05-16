"""Audit deformation of lead-lag propagation geometry between NORMAL and F13."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from lead_lag_propagation_audit import (
    PAIR_CHAIN,
    _compute_run_level_lags,
    _load_data,
)

OUTPUT_RUNLEVEL = PROJECT_ROOT / "outputs" / "csv" / "propagation_geometry_runlevel.csv"
OUTPUT_SUMMARY = PROJECT_ROOT / "outputs" / "csv" / "propagation_geometry_deformation.csv"
OUTPUT_SCORE = PROJECT_ROOT / "outputs" / "taxonomy" / "propagation_deformation_score.png"
OUTPUT_OVERLAY = PROJECT_ROOT / "outputs" / "taxonomy" / "propagation_lag_distribution_overlay.png"
OUTPUT_GRAPH = PROJECT_ROOT / "outputs" / "taxonomy" / "propagation_mean_shift_graph.png"


def _compute_summary(runlevel_df):
    rows = []
    for src, dst in PAIR_CHAIN:
        pair_name = f"{src}->{dst}"
        normal_pair = runlevel_df.loc[
            (runlevel_df["source_label"] == "NORMAL") & (runlevel_df["pair"] == pair_name)
        ]
        f13_pair = runlevel_df.loc[
            (runlevel_df["source_label"] == "F13") & (runlevel_df["pair"] == pair_name)
        ]

        normal_lags = normal_pair["best_lag"].dropna().to_numpy(dtype=float)
        f13_lags = f13_pair["best_lag"].dropna().to_numpy(dtype=float)
        normal_corr = normal_pair["best_corr"].dropna().to_numpy(dtype=float)
        f13_corr = f13_pair["best_corr"].dropna().to_numpy(dtype=float)

        normal_mean_lag = float(np.mean(normal_lags)) if normal_lags.size else float("nan")
        f13_mean_lag = float(np.mean(f13_lags)) if f13_lags.size else float("nan")
        delta_mean_lag = float(f13_mean_lag - normal_mean_lag)

        normal_std_lag = float(np.std(normal_lags, ddof=1)) if normal_lags.size > 1 else 0.0
        f13_std_lag = float(np.std(f13_lags, ddof=1)) if f13_lags.size > 1 else 0.0
        delta_std_lag = float(f13_std_lag - normal_std_lag)

        normal_mean_corr = float(np.mean(normal_corr)) if normal_corr.size else float("nan")
        f13_mean_corr = float(np.mean(f13_corr)) if f13_corr.size else float("nan")
        delta_mean_corr = float(f13_mean_corr - normal_mean_corr)

        if normal_lags.size and f13_lags.size:
            wdist = float(wasserstein_distance(normal_lags, f13_lags))
            ks_stat, ks_pvalue = ks_2samp(normal_lags, f13_lags)
            ks_stat = float(ks_stat)
            ks_pvalue = float(ks_pvalue)
        else:
            wdist = float("nan")
            ks_stat = float("nan")
            ks_pvalue = float("nan")

        wdist_norm = wdist / 100.0 if np.isfinite(wdist) else float("nan")
        deformation_score = (
            abs(delta_mean_lag) + 0.5 * abs(delta_std_lag) + 10.0 * wdist_norm
            if np.isfinite(wdist_norm)
            else float("nan")
        )

        rows.append(
            {
                "pair": pair_name,
                "normal_mean_lag": normal_mean_lag,
                "f13_mean_lag": f13_mean_lag,
                "delta_mean_lag": delta_mean_lag,
                "normal_std_lag": normal_std_lag,
                "f13_std_lag": f13_std_lag,
                "delta_std_lag": delta_std_lag,
                "normal_mean_corr": normal_mean_corr,
                "f13_mean_corr": f13_mean_corr,
                "delta_mean_corr": delta_mean_corr,
                "wasserstein_distance": wdist,
                "ks_statistic": ks_stat,
                "ks_pvalue": ks_pvalue,
                "deformation_score": deformation_score,
            }
        )
    return pd.DataFrame(rows).sort_values("deformation_score", ascending=False).reset_index(drop=True)


def _plot_score(summary_df):
    fig, ax = plt.subplots(figsize=(10, 6))
    ordered = summary_df.sort_values("deformation_score", ascending=False)
    ax.bar(ordered["pair"], ordered["deformation_score"], color="tab:red", alpha=0.85)
    ax.set_title("Propagation geometry deformation score")
    ax.set_xlabel("pair")
    ax.set_ylabel("deformation_score")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_SCORE, dpi=150)
    plt.close(fig)


def _plot_overlay(runlevel_df, summary_df):
    fig, axes = plt.subplots(3, 2, figsize=(12, 12), constrained_layout=True)
    axes = axes.flatten()
    for ax, (src, dst) in zip(axes, PAIR_CHAIN):
        pair_name = f"{src}->{dst}"
        normal_lags = runlevel_df.loc[
            (runlevel_df["source_label"] == "NORMAL") & (runlevel_df["pair"] == pair_name),
            "best_lag",
        ].dropna().to_numpy(dtype=float)
        f13_lags = runlevel_df.loc[
            (runlevel_df["source_label"] == "F13") & (runlevel_df["pair"] == pair_name),
            "best_lag",
        ].dropna().to_numpy(dtype=float)
        row = summary_df.loc[summary_df["pair"] == pair_name].iloc[0]
        bins = np.arange(-50.5, 51.5, 2.0)
        ax.hist(normal_lags, bins=bins, alpha=0.45, color="tab:gray", label="NORMAL")
        ax.hist(f13_lags, bins=bins, alpha=0.55, color="tab:orange", label="F13")
        ax.axvline(row["normal_mean_lag"], color="tab:gray", linestyle="--", linewidth=1.2)
        ax.axvline(row["f13_mean_lag"], color="tab:orange", linestyle="--", linewidth=1.2)
        ax.set_title(pair_name)
        ax.set_xlabel("best_lag")
        ax.set_ylabel("count")
        ax.grid(alpha=0.3)
        ax.legend()
    axes[-1].axis("off")
    fig.savefig(OUTPUT_OVERLAY, dpi=150)
    plt.close(fig)


def _plot_mean_shift_graph(summary_df):
    positions = {
        "xmeas_7": (0.1, 0.6),
        "xmeas_11": (0.4, 0.75),
        "xmeas_18": (0.7, 0.45),
        "xmeas_19": (0.9, 0.2),
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Propagation mean-lag shift graph (NORMAL -> F13)")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    for node, (x, y) in positions.items():
        ax.scatter([x], [y], s=1200, color="tab:blue", alpha=0.9, edgecolors="black")
        ax.text(x, y, node, ha="center", va="center", color="white", fontsize=10, weight="bold")

    for row in summary_df.itertuples(index=False):
        src, dst = row.pair.split("->")
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        if abs(row.delta_mean_lag) > 10:
            color = "tab:red" if row.delta_mean_lag > 0 else "tab:blue"
        else:
            color = "tab:gray"
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", linewidth=2.8, color=color, alpha=0.85),
        )
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        ax.text(
            mx,
            my,
            f"{row.normal_mean_lag:.1f}->{row.f13_mean_lag:.1f}\nΔ={row.delta_mean_lag:.1f}",
            fontsize=8,
            ha="center",
            va="center",
            bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", boxstyle="round,pad=0.2"),
        )

    fig.tight_layout()
    fig.savefig(OUTPUT_GRAPH, dpi=150)
    plt.close(fig)


def main():
    resolved_columns, normal_runs, f13_runs = _load_data()
    normal_df = _compute_run_level_lags(normal_runs, resolved_columns, "NORMAL")
    f13_df = _compute_run_level_lags(f13_runs, resolved_columns, "F13")
    runlevel_df = pd.concat([normal_df, f13_df], axis=0, ignore_index=True)
    summary_df = _compute_summary(runlevel_df)

    OUTPUT_RUNLEVEL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_GRAPH.parent.mkdir(parents=True, exist_ok=True)
    runlevel_df.to_csv(OUTPUT_RUNLEVEL, index=False, encoding="utf-8")
    summary_df.to_csv(OUTPUT_SUMMARY, index=False, encoding="utf-8")

    _plot_score(summary_df)
    _plot_overlay(runlevel_df, summary_df)
    _plot_mean_shift_graph(summary_df)

    print("=== PROPAGATION GEOMETRY DEFORMATION SUMMARY ===")
    display_cols = [
        "pair",
        "normal_mean_lag",
        "f13_mean_lag",
        "delta_mean_lag",
        "wasserstein_distance",
        "ks_pvalue",
        "deformation_score",
    ]
    print(summary_df[display_cols].to_string(index=False))
    print("\nMost deformed pairs:")
    for row in summary_df.head(3).itertuples(index=False):
        print(
            f"{row.pair}: delta_mean_lag={row.delta_mean_lag:.3f}, "
            f"wasserstein_distance={row.wasserstein_distance:.3f}, "
            f"ks_pvalue={row.ks_pvalue:.6f}, "
            f"deformation_score={row.deformation_score:.3f}"
        )

    print("\nConservative interpretation:")
    print("NORMAL already has strong propagation structure.")
    print("F13 should be evaluated by deformation relative to NORMAL.")
    print("This experiment tests distributional deformation of lead-lag geometry only.")
    print("It does not prove physical causality.")
    return summary_df


if __name__ == "__main__":
    main()
