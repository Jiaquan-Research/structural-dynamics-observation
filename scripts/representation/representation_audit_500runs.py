"""Full 500-run representation stability audit for F01-F20."""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

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
N_RUNS = 500
FAULT_NUMBERS = list(range(1, 21))

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
PERRUN_OUTPUT = CSV_OUTPUT_DIR / "representation_audit_500runs_perrun.csv"
SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "representation_audit_500runs_summary.csv"
SUMMARY_20RUN = CSV_OUTPUT_DIR / "full_fault_representation_audit.csv"
SCATTER_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_500runs_scatter.png"
COMPARISON_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_20vs500_comparison.png"
OCC_DISTRIBUTION_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_occupancy_distribution.png"
F13_HIST_OUTPUT = TAXONOMY_OUTPUT_DIR / "f13_occupancy_histogram.png"
CONSISTENCY_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_occupancy_consistency.png"

CLASS_ORDER = ["Locked", "Stable", "Transitional", "Diffuse"]
CLASS_COLORS = {
    "Locked": "#006400",
    "Stable": "#66bb6a",
    "Transitional": "#f28e2b",
    "Diffuse": "#d62728",
}
PERRUN_COLUMNS = [
    "fault",
    "run_id",
    "occupancy_ratio",
    "pair_entropy",
    "mean_run_length",
    "dominant_pair",
    "dominant_pair_frequency",
    "unique_pair_count",
]


def _fault_label(fault_number: int) -> str:
    return f"F{int(fault_number):02d}"


def _fault_number(fault: str) -> int:
    return int(str(fault).replace("F", ""))


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


def _run_metrics(fault: str, run_id: int, dominant_pairs: list[str]) -> dict[str, object]:
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
        "occupancy_ratio": float(dominant_count / total),
        "pair_entropy": float(scipy_entropy(freqs)),
        "mean_run_length": float(np.mean(lengths)),
        "dominant_pair": dominant_pair,
        "dominant_pair_frequency": float(dominant_count / total),
        "unique_pair_count": int(len(counts)),
    }


def _representation_class(mean_occupancy: float, mean_entropy: float) -> str:
    if mean_occupancy >= 0.90 and mean_entropy <= 0.20:
        return "Locked"
    if mean_occupancy >= 0.70 and mean_entropy <= 0.60:
        return "Stable"
    if 0.40 <= mean_occupancy < 0.70 or 0.60 < mean_entropy <= 1.20:
        return "Transitional"
    if mean_occupancy < 0.40 or mean_entropy > 1.20:
        return "Diffuse"
    return "Diffuse"


def _completed_faults() -> set[str]:
    if not PERRUN_OUTPUT.exists():
        return set()
    df = pd.read_csv(PERRUN_OUTPUT, usecols=["fault", "run_id"])
    completed = set()
    for fault, group in df.groupby("fault"):
        if group["run_id"].nunique() >= N_RUNS:
            completed.add(str(fault))
    return completed


def _append_fault_rows(rows: list[dict[str, object]]) -> None:
    write_header = not PERRUN_OUTPUT.exists()
    pd.DataFrame(rows, columns=PERRUN_COLUMNS).to_csv(
        PERRUN_OUTPUT,
        mode="a",
        header=write_header,
        index=False,
    )


def _compute_fault_rows(
    testing_path: Path,
    usecols: list[str],
    selected_columns: list[str],
    baseline_model: dict[str, object],
    fault_number: int,
) -> list[dict[str, object]]:
    fault = _fault_label(fault_number)
    runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
    rows = []
    for idx, run_id in enumerate(sorted(runs)[:N_RUNS], start=1):
        run_df = runs[run_id].sort_values("sample")
        run_data = run_df[selected_columns].to_numpy(dtype=float)
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
        top1_indices = np.asarray(series["top1_indices"], dtype=int)[mask]
        dominant_pairs = [PAIR_LABELS[int(pair_idx)] for pair_idx in top1_indices]
        if dominant_pairs:
            rows.append(_run_metrics(fault, run_id, dominant_pairs))
        if idx % 100 == 0 or idx == N_RUNS:
            print(f"{fault}: run {idx} / {N_RUNS}", flush=True)
    if len(rows) < N_RUNS:
        print(f"WARNING: {fault} produced {len(rows)} valid rows, expected {N_RUNS}.")
    return rows


def _aggregate_summary(perrun_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fault, group in perrun_df.groupby("fault", sort=True):
        dominant_counts = Counter(group["dominant_pair"].tolist())
        most_common_pair, count = dominant_counts.most_common(1)[0]
        occ = group["occupancy_ratio"].to_numpy(dtype=float)
        ent = group["pair_entropy"].to_numpy(dtype=float)
        mean_occupancy = float(np.mean(occ))
        mean_entropy = float(np.mean(ent))
        rows.append(
            {
                "fault": fault,
                "mean_occupancy": mean_occupancy,
                "std_occupancy": float(np.std(occ, ddof=1)),
                "median_occupancy": float(np.median(occ)),
                "p05_occupancy": float(np.quantile(occ, 0.05)),
                "p95_occupancy": float(np.quantile(occ, 0.95)),
                "mean_entropy": mean_entropy,
                "std_entropy": float(np.std(ent, ddof=1)),
                "median_entropy": float(np.median(ent)),
                "p05_entropy": float(np.quantile(ent, 0.05)),
                "p95_entropy": float(np.quantile(ent, 0.95)),
                "mean_run_length": float(group["mean_run_length"].mean()),
                "mean_unique_pair_count": float(group["unique_pair_count"].mean()),
                "most_common_dominant_pair": most_common_pair,
                "dominant_pair_consistency": float(count / len(group)),
                "representation_class": _representation_class(mean_occupancy, mean_entropy),
            }
        )
    summary = pd.DataFrame(rows)
    summary["_fault_number"] = summary["fault"].map(_fault_number)
    return summary.sort_values("_fault_number").drop(columns=["_fault_number"])


def _plot_scatter(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    for class_name in CLASS_ORDER:
        group = summary_df.loc[summary_df["representation_class"] == class_name]
        if group.empty:
            continue
        ax.errorbar(
            group["mean_entropy"],
            group["mean_occupancy"],
            xerr=group["std_entropy"],
            yerr=group["std_occupancy"],
            fmt="o",
            markersize=7,
            color=CLASS_COLORS[class_name],
            ecolor=CLASS_COLORS[class_name],
            alpha=0.85,
            capsize=3,
            label=class_name,
        )
        for row in group.itertuples(index=False):
            ax.annotate(row.fault, (row.mean_entropy, row.mean_occupancy), xytext=(5, 4), textcoords="offset points")
    ax.axhline(0.90, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(0.70, color="black", linestyle="--", linewidth=1.0)
    ax.axvline(0.20, color="black", linestyle="--", linewidth=1.0)
    ax.axvline(0.60, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("mean_entropy")
    ax.set_ylabel("mean_occupancy")
    ax.set_title("Fault Representation Stability (500 runs):\nOccupancy vs Entropy with std error bars")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(SCATTER_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_20vs500(summary_df: pd.DataFrame) -> None:
    if not SUMMARY_20RUN.exists():
        print(f"WARNING: Missing 20-run summary for comparison: {SUMMARY_20RUN}")
        return
    summary20 = pd.read_csv(SUMMARY_20RUN).set_index("fault")
    summary500 = summary_df.set_index("fault")
    fig, ax = plt.subplots(figsize=(9, 7))
    for fault in summary500.index:
        row20 = summary20.loc[fault]
        row500 = summary500.loc[fault]
        ax.plot(
            [row20["mean_entropy"], row500["mean_entropy"]],
            [row20["mean_occupancy"], row500["mean_occupancy"]],
            color="gray",
            alpha=0.45,
            linewidth=1,
        )
        ax.scatter(row20["mean_entropy"], row20["mean_occupancy"], facecolors="none", edgecolors="black", s=45)
        ax.scatter(
            row500["mean_entropy"],
            row500["mean_occupancy"],
            color=CLASS_COLORS[row500["representation_class"]],
            s=75,
        )
        ax.annotate(fault, (row500["mean_entropy"], row500["mean_occupancy"]), xytext=(5, 4), textcoords="offset points")
    ax.set_xlabel("mean_entropy")
    ax.set_ylabel("mean_occupancy")
    ax.set_title("20-run vs 500-run Comparison:\nRepresentation Stability Estimates")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(COMPARISON_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_occupancy_distribution(perrun_df: pd.DataFrame, summary_df: pd.DataFrame) -> None:
    faults = [_fault_label(number) for number in FAULT_NUMBERS]
    data = [
        perrun_df.loc[perrun_df["fault"] == fault, "occupancy_ratio"].to_numpy(dtype=float)
        for fault in faults
    ]
    classes = summary_df.set_index("fault")["representation_class"].to_dict()
    colors = [CLASS_COLORS[classes[fault]] for fault in faults]

    fig, ax = plt.subplots(figsize=(14, 6))
    box = ax.boxplot(data, patch_artist=True, tick_labels=faults, showfliers=False)
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("fault")
    ax.set_ylabel("occupancy_ratio")
    ax.set_title("Per-fault Occupancy Distribution (500 runs)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OCC_DISTRIBUTION_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_f13_histogram(perrun_df: pd.DataFrame) -> tuple[int, int]:
    f13 = perrun_df.loc[perrun_df["fault"] == "F13", "occupancy_ratio"].to_numpy(dtype=float)
    n_gt = int(np.sum(f13 > 0.90))
    n_lt = int(np.sum(f13 < 0.50))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(f13, bins=20, range=(0, 1), color="tab:blue", alpha=0.75, edgecolor="black")
    try:
        f13_series = pd.Series(f13)
        kde = f13_series.plot(kind="kde", ax=ax, secondary_y=True, color="tab:red", linewidth=2)
        kde.set_ylabel("density")
    except Exception:
        pass
    ax.set_xlabel("occupancy_ratio")
    ax.set_ylabel("count")
    ax.set_title(f"F13 Occupancy Distribution (500 runs)\nn(occ>0.9)={n_gt} n(occ<0.5)={n_lt}")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(F13_HIST_OUTPUT, dpi=150)
    plt.close(fig)
    return n_gt, n_lt


def _plot_consistency(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    for class_name in CLASS_ORDER:
        group = summary_df.loc[summary_df["representation_class"] == class_name]
        if group.empty:
            continue
        ax.scatter(
            group["mean_occupancy"],
            group["dominant_pair_consistency"],
            s=80,
            color=CLASS_COLORS[class_name],
            label=class_name,
            alpha=0.9,
        )
        for row in group.itertuples(index=False):
            ax.annotate(row.fault, (row.mean_occupancy, row.dominant_pair_consistency), xytext=(5, 4), textcoords="offset points")
    ax.set_xlabel("mean_occupancy")
    ax.set_ylabel("dominant_pair_consistency")
    ax.set_title(
        "Occupancy vs Dominant Pair Consistency (500 runs)\n"
        "High occupancy + high consistency = stable pair locking\n"
        "High occupancy + low consistency = unstable pair identity"
    )
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(CONSISTENCY_OUTPUT, dpi=150)
    plt.close(fig)


def _print_grouped_summary(summary_df: pd.DataFrame) -> None:
    print("=== REPRESENTATION AUDIT 500 RUNS ===")
    print("")
    for class_name in CLASS_ORDER:
        print(f"{class_name.upper()} faults:")
        group = summary_df.loc[summary_df["representation_class"] == class_name]
        if group.empty:
            print("(none)")
        for row in group.itertuples(index=False):
            print(
                f"{row.fault}: occupancy={row.mean_occupancy:.3f}+/-{row.std_occupancy:.3f} "
                f"entropy={row.mean_entropy:.3f}+/-{row.std_entropy:.3f} "
                f"consistency={row.dominant_pair_consistency:.3f}"
            )
        print("")


def _print_stability_check(summary_df: pd.DataFrame) -> None:
    print("=== CLUSTERING STABILITY CHECK ===")
    print("")
    if not SUMMARY_20RUN.exists():
        print(f"Missing 20-run summary: {SUMMARY_20RUN}")
        return
    summary20 = pd.read_csv(SUMMARY_20RUN).set_index("fault")
    summary500 = summary_df.set_index("fault")
    changes = []
    print("fault  20run_class  500run_class  stable?")
    for fault in [_fault_label(number) for number in FAULT_NUMBERS]:
        class20 = str(summary20.loc[fault, "representation_class"])
        class500 = str(summary500.loc[fault, "representation_class"])
        stable = class20 == class500
        if not stable:
            changes.append((fault, class20, class500))
        print(f"{fault:<5}  {class20:<12} {class500:<13} {'yes' if stable else 'no'}")
    print("")
    print("=== CLASS CHANGES ===")
    print("")
    if changes:
        for fault, class20, class500 in changes:
            print(f"CHANGED: {fault} was {class20} now {class500}")
    else:
        print("All 20 faults maintain same class.")
        print("Clustering is stable.")
    print("")


def _print_f13_check(summary_df: pd.DataFrame, perrun_df: pd.DataFrame, n_gt: int, n_lt: int) -> None:
    print("=== F13 BIMODAL CHECK ===")
    print("")
    f13 = perrun_df.loc[perrun_df["fault"] == "F13", "occupancy_ratio"].to_numpy(dtype=float)
    print("F13 occupancy distribution:")
    print(f"mean = {float(np.mean(f13)):.6f}")
    print(f"std = {float(np.std(f13, ddof=1)):.6f}")
    print(f"p05 = {float(np.quantile(f13, 0.05)):.6f}")
    print(f"p25 = {float(np.quantile(f13, 0.25)):.6f}")
    print(f"p50 = {float(np.quantile(f13, 0.50)):.6f}")
    print(f"p75 = {float(np.quantile(f13, 0.75)):.6f}")
    print(f"p95 = {float(np.quantile(f13, 0.95)):.6f}")
    print(f"n_runs_occ_gt_0.9 = {n_gt}")
    print(f"n_runs_occ_lt_0.5 = {n_lt}")
    print("")
    if float(np.std(f13, ddof=1)) > 0.30 and n_gt > 50 and n_lt > 50:
        print("F13 shows heterogeneous occupancy structure.")
        print("Both high-stability and low-stability runs present.")
        print("Bimodal hypothesis plausible but requires")
        print("further distribution analysis to confirm.")
    else:
        print("F13 occupancy distribution does not show")
        print("clear heterogeneous structure in 500-run sample.")
    print("")


def _print_conservative_interpretation() -> None:
    print("Conservative interpretation:")
    print("1. representation_class is empirical descriptive bins.")
    print("2. threshold is heuristic, not ground truth.")
    print("3. occupancy/entropy are representation-space metrics.")
    print("4. clustering stability is based on TEP simulation data.")
    print("5. No physical causal inference is made.")


def main() -> None:
    t_start = time.time()
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(np.asarray(baseline_data, dtype=float), WINDOW, STEP)

    completed = _completed_faults()
    for fault_number in FAULT_NUMBERS:
        fault = _fault_label(fault_number)
        if fault in completed:
            print(f"SKIP {fault}: already completed (500 runs found)")
            continue
        rows = _compute_fault_rows(testing_path, usecols, selected_columns, baseline_model, fault_number)
        _append_fault_rows(rows)
        print(f"APPENDED {fault}: {len(rows)} rows")

    perrun_df = pd.read_csv(PERRUN_OUTPUT)
    summary_df = _aggregate_summary(perrun_df)
    summary_df.to_csv(SUMMARY_OUTPUT, index=False)

    _plot_scatter(summary_df)
    _plot_20vs500(summary_df)
    _plot_occupancy_distribution(perrun_df, summary_df)
    n_gt, n_lt = _plot_f13_histogram(perrun_df)
    _plot_consistency(summary_df)

    _print_grouped_summary(summary_df)
    _print_stability_check(summary_df)
    _print_f13_check(summary_df, perrun_df, n_gt, n_lt)
    _print_conservative_interpretation()

    elapsed = time.time() - t_start
    print("")
    print(f"Total computation time: {elapsed:.1f} seconds")
    print("")
    print("Generated files:")
    print(f"- {PERRUN_OUTPUT}")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {SCATTER_OUTPUT}")
    print(f"- {COMPARISON_OUTPUT}")
    print(f"- {OCC_DISTRIBUTION_OUTPUT}")
    print(f"- {F13_HIST_OUTPUT}")
    print(f"- {CONSISTENCY_OUTPUT}")


if __name__ == "__main__":
    main()
