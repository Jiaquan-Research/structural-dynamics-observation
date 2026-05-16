"""F14 deep dive: rolling statistics and pair persistence diagnostics."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import entropy

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

SELECTED_RUNS = {
    "F02": 366,
    "F06": 164,
    "F14": 150,
}

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
METRICS_OUTPUT = CSV_OUTPUT_DIR / "f14_pair_persistence_metrics.csv"
STD_COMPARISON_OUTPUT = TAXONOMY_OUTPUT_DIR / "f14_rolling_std_comparison.png"
PERSISTENCE_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "f14_pair_persistence_comparison.png"

FAULT_COLORS = {
    "F02": "tab:orange",
    "F06": "tab:green",
    "F14": "tab:blue",
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


def _rolling_stats(xmeas7: np.ndarray, xmeas11: np.ndarray) -> dict[str, np.ndarray]:
    s7 = pd.Series(xmeas7)
    s11 = pd.Series(xmeas11)
    return {
        "rolling_mean_x7": s7.rolling(ROLLING_WINDOW, min_periods=1).mean().to_numpy(dtype=float),
        "rolling_std_x7": s7.rolling(ROLLING_WINDOW, min_periods=1).std().to_numpy(dtype=float),
        "rolling_mean_x11": s11.rolling(ROLLING_WINDOW, min_periods=1).mean().to_numpy(dtype=float),
        "rolling_std_x11": s11.rolling(ROLLING_WINDOW, min_periods=1).std().to_numpy(dtype=float),
        "rolling_corr": s7.rolling(ROLLING_WINDOW, min_periods=10).corr(s11).to_numpy(dtype=float),
    }


def _ruptures_a_changepoints(signal_a: np.ndarray) -> list[int]:
    algo = rpt.Pelt(model="rbf").fit(signal_a)
    breakpoints = algo.predict(pen=RUPTURES_PENALTY_A)
    return [int(cp) for cp in breakpoints if int(cp) < len(signal_a)]


def _run_lengths(sequence: list[str]) -> list[int]:
    if not sequence:
        return []
    lengths = []
    current = sequence[0]
    count = 1
    for item in sequence[1:]:
        if item == current:
            count += 1
        else:
            lengths.append(count)
            current = item
            count = 1
    lengths.append(count)
    return lengths


def _pair_persistence_metrics(fault: str, run_id: int, dominant_pairs: list[str]) -> dict[str, object]:
    if not dominant_pairs:
        raise ValueError(f"No dominant pairs for {fault} run {run_id}")
    counts = Counter(dominant_pairs)
    total = len(dominant_pairs)
    freqs = np.asarray(list(counts.values()), dtype=float) / float(total)
    dominant_pair, dominant_count = counts.most_common(1)[0]
    lengths = _run_lengths(dominant_pairs)
    return {
        "fault": fault,
        "run_id": int(run_id),
        "mean_run_length": float(np.mean(lengths)),
        "max_run_length": int(np.max(lengths)),
        "pair_switch_count": int(max(len(lengths) - 1, 0)),
        "occupancy_ratio": float(dominant_count / total),
        "pair_entropy": float(entropy(freqs)),
        "unique_pair_count": int(len(counts)),
        "dominant_pair": dominant_pair,
        "dominant_pair_frequency": float(dominant_count / total),
    }


def _prepare_fault_profile(
    fault: str,
    run_df: pd.DataFrame,
    selected_columns: list[str],
    baseline_model: dict[str, object],
    x7_idx: int,
    x11_idx: int,
) -> dict[str, object]:
    run_id = SELECTED_RUNS[fault]
    run_df = run_df.sort_values("sample")
    samples = run_df["sample"].to_numpy(dtype=int)
    run_data = run_df[selected_columns].to_numpy(dtype=float)
    xmeas7 = run_data[:, x7_idx]
    xmeas11 = run_data[:, x11_idx]
    stats = _rolling_stats(xmeas7, xmeas11)

    signal_a = np.column_stack([xmeas7, xmeas11])
    changepoints = _ruptures_a_changepoints(signal_a)

    series = _compute_version_b_trajectory_series(
        run_data,
        WINDOW,
        STEP,
        K_TOP,
        N_HISTORY,
        baseline_model,
    )
    sample_times = np.asarray(series["sample_times"], dtype=int)
    mask = sample_times > SAMPLE_FILTER
    top1_mass = np.asarray(series["top_pair_dominance"], dtype=float)[mask]
    top1_indices = np.asarray(series["top1_indices"], dtype=int)[mask]
    dominant_pairs = [PAIR_LABELS[int(idx)] for idx in top1_indices]

    after_filter = samples > SAMPLE_FILTER
    rolling_std_x7 = np.asarray(stats["rolling_std_x7"], dtype=float)
    rolling_std_after = rolling_std_x7[after_filter]

    return {
        "fault": fault,
        "run_id": int(run_id),
        "samples": samples,
        "xmeas7": xmeas7,
        "xmeas11": xmeas11,
        **stats,
        "changepoints": changepoints,
        "changepoints_after_filter": [cp for cp in changepoints if cp > SAMPLE_FILTER],
        "window_index": np.arange(1, len(top1_mass) + 1),
        "sample_times": sample_times[mask],
        "top1_mass": top1_mass,
        "dominant_pairs": dominant_pairs,
        "rolling_std_after_mean": float(np.nanmean(rolling_std_after)),
        "rolling_std_after_max": float(np.nanmax(rolling_std_after)),
        "metrics": _pair_persistence_metrics(fault, run_id, dominant_pairs),
    }


def _plot_rolling_stats(profile: dict[str, object]) -> Path:
    fault = str(profile["fault"])
    output_path = TAXONOMY_OUTPUT_DIR / f"f14_rolling_stats_{fault}.png"
    samples = np.asarray(profile["samples"], dtype=int)

    fig, axes = plt.subplots(5, 1, figsize=(14, 18), sharex=True)
    fig.suptitle(
        f"F14 Deep Dive - Rolling Statistics: {fault}\n"
        f"run={profile['run_id']}\n"
        "Panel B (rolling std) is key for ruptures_A interpretation",
        fontsize=14,
    )

    axes[0].plot(samples, profile["xmeas7"], color="lightskyblue", alpha=0.4, label="raw XMEAS7")
    axes[0].plot(samples, profile["rolling_mean_x7"], color="tab:blue", linewidth=2, label="rolling mean")
    axes[0].axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0)
    axes[0].text(SAMPLE_FILTER + 5, axes[0].get_ylim()[1], "SAMPLE_FILTER=200", va="top")
    axes[0].set_ylabel("XMEAS7 (reactor pressure)")
    axes[0].legend(loc="best")
    axes[0].grid(alpha=0.25)

    axes[1].plot(samples, profile["rolling_std_x7"], color="tab:blue")
    axes[1].axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0)
    axes[1].set_ylabel("XMEAS7 rolling std")
    axes[1].grid(alpha=0.25)

    axes[2].plot(samples, profile["xmeas11"], color="moccasin", alpha=0.5, label="raw XMEAS11")
    axes[2].plot(samples, profile["rolling_mean_x11"], color="tab:orange", linewidth=2, label="rolling mean")
    axes[2].axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0)
    axes[2].set_ylabel("XMEAS11 (separator temperature)")
    axes[2].legend(loc="best")
    axes[2].grid(alpha=0.25)

    axes[3].plot(samples, profile["rolling_corr"], color="tab:green")
    axes[3].axhline(0, color="black", linestyle="--", linewidth=1.0)
    axes[3].axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0)
    axes[3].set_ylim(-1.05, 1.05)
    axes[3].set_ylabel("XMEAS7-XMEAS11 rolling corr")
    axes[3].grid(alpha=0.25)

    axes[4].set_ylim(0, 1)
    for cp in profile["changepoints"]:
        axes[4].axvline(cp, color="tab:red", linewidth=1.5, alpha=0.85)
    if not profile["changepoints"]:
        axes[4].text(
            0.5,
            0.5,
            "No changepoint detected (ruptures_A, penalty=50)",
            transform=axes[4].transAxes,
            ha="center",
            va="center",
        )
    axes[4].axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0)
    axes[4].set_ylabel("ruptures_A changepoints")
    axes[4].set_xlabel("sample index")
    axes[4].grid(alpha=0.25)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _plot_rolling_std_comparison(profiles: dict[str, dict[str, object]]) -> Path:
    fig, ax = plt.subplots(figsize=(12, 6))
    for fault in TARGET_FAULTS:
        profile = profiles[fault]
        samples = np.asarray(profile["samples"], dtype=int)
        ax.plot(
            samples,
            profile["rolling_std_x7"],
            color=FAULT_COLORS[fault],
            label=fault,
            linewidth=1.5,
        )
        for cp in profile["changepoints"]:
            ax.axvline(cp, color=FAULT_COLORS[fault], linewidth=1.2, alpha=0.5)
    ax.axvline(SAMPLE_FILTER, color="black", linestyle="--", linewidth=1.0, label="SAMPLE_FILTER=200")
    ax.set_xlabel("sample index")
    ax.set_ylabel("XMEAS7 rolling std")
    ax.set_title(
        "XMEAS7 Rolling Std Comparison: F02 vs F06 vs F14\n"
        "(ruptures changepoints shown as vertical lines)"
    )
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(STD_COMPARISON_OUTPUT, dpi=150)
    plt.close(fig)
    return STD_COMPARISON_OUTPUT


def _plot_pair_persistence(metrics_df: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    metrics = [
        ("mean_run_length", "mean_run_length"),
        ("occupancy_ratio", "occupancy_ratio"),
        ("pair_entropy", "pair_entropy"),
        ("unique_pair_count", "unique_pair_count"),
    ]
    x = np.arange(len(TARGET_FAULTS))
    colors = [FAULT_COLORS[fault] for fault in TARGET_FAULTS]
    ordered = metrics_df.set_index("fault").loc[TARGET_FAULTS].reset_index()

    for ax, (column, ylabel) in zip(axes.ravel(), metrics):
        ax.bar(x, ordered[column].to_numpy(dtype=float), color=colors, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(TARGET_FAULTS)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", alpha=0.25)

    fig.suptitle("Pair Persistence Metrics: F02 vs F06 vs F14\n(p95 run for each fault)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(PERSISTENCE_PLOT_OUTPUT, dpi=150)
    plt.close(fig)
    return PERSISTENCE_PLOT_OUTPUT


def _print_summary(profiles: dict[str, dict[str, object]], metrics_df: pd.DataFrame) -> None:
    print("=== F14 DEEP DIVE SUMMARY ===")
    print("")
    print("--- Direction 1: Rolling Statistics ---")
    print("")
    for fault in TARGET_FAULTS:
        profile = profiles[fault]
        print(f"{fault} (run={profile['run_id']}):")
        print("  XMEAS7 rolling std (after filter):")
        print(f"    mean = {profile['rolling_std_after_mean']:.6f}")
        print(f"    max = {profile['rolling_std_after_max']:.6f}")
        print(f"  ruptures_A changepoints: {profile['changepoints_after_filter']}")
        print("")

    f06_mean = float(profiles["F06"]["rolling_std_after_mean"])
    f14_mean = float(profiles["F14"]["rolling_std_after_mean"])
    print("--- Rolling Std Diagnostic ---")
    print("")
    if f14_mean < f06_mean * 0.5:
        print("DIAGNOSIS: F14 XMEAS7 rolling std is substantially")
        print("lower than F06. This likely explains ruptures_A silence:")
        print("F14 produces a stable level shift without")
        print("ongoing variance amplification.")
        print("ruptures_A (rbf model) is sensitive to distribution")
        print("spread changes, not just mean shifts.")
    else:
        print("DIAGNOSIS: Rolling std difference between F14 and F06")
        print("is not substantial. The ruptures_A silence in F14")
        print("may reflect joint distribution structure differences")
        print("rather than univariate variance differences.")
        print("Further investigation needed.")
    print("")

    print("--- Direction 4: Pair Persistence ---")
    print("")
    for row in metrics_df.itertuples(index=False):
        print(
            f"{row.fault}: mean_run_length={row.mean_run_length:.6f} "
            f"occupancy={row.occupancy_ratio:.6f} entropy={row.pair_entropy:.6f}"
        )
    print("")
    print("--- Pair Persistence Diagnostic ---")
    print("")
    f14_occ = float(metrics_df.loc[metrics_df["fault"] == "F14", "occupancy_ratio"].iloc[0])
    f02_occ = float(metrics_df.loc[metrics_df["fault"] == "F02", "occupancy_ratio"].iloc[0])
    if f14_occ > 0.95 and f02_occ < 0.5:
        print("FINDING: Pair persistence clearly differentiates")
        print("F14 (geometry-concentrated) from F02 (geometry-diffuse).")
        print("Dominant pair occupancy may be a more fundamental")
        print("descriptor than top1_mass amplitude alone.")
    else:
        print("FINDING: Pair persistence does not cleanly separate")
        print("F14 from F02 under this selected-run comparison.")
        print("Additional run-level aggregation is needed.")
    print("")
    print("Conservative interpretation:")
    print("1. Analysis is based on a single p95 run and does not represent all 500 runs.")
    print("2. Rolling std interpretation is a representation-level observation.")
    print("3. Pair persistence metrics are descriptive statistics.")
    print("4. No physical causal inference is made.")
    print("5. ruptures_A silence interpretation requires further validation.")


def main() -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        fault_runs = _load_all_fault_runs(
            testing_path,
            usecols=usecols,
            fault_number=_fault_number(fault),
        )
        run_id = SELECTED_RUNS[fault]
        if run_id not in fault_runs:
            raise ValueError(f"{fault} selected run {run_id} not found.")
        profiles[fault] = _prepare_fault_profile(
            fault=fault,
            run_df=fault_runs[run_id],
            selected_columns=selected_columns,
            baseline_model=baseline_model,
            x7_idx=x7_idx,
            x11_idx=x11_idx,
        )
        generated_files.append(_plot_rolling_stats(profiles[fault]))

    metrics_df = pd.DataFrame([profiles[fault]["metrics"] for fault in TARGET_FAULTS])
    metrics_df.to_csv(METRICS_OUTPUT, index=False)
    generated_files.append(METRICS_OUTPUT)
    generated_files.append(_plot_rolling_std_comparison(profiles))
    generated_files.append(_plot_pair_persistence(metrics_df))

    _print_summary(profiles, metrics_df)

    print("")
    print("Generated files:")
    for path in generated_files:
        print(f"- {path}")


if __name__ == "__main__":
    main()
