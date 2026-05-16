"""Audit representation stability across F01-F20 using pair occupancy and entropy."""

from __future__ import annotations

import sys
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
N_RUNS = 20
FAULT_NUMBERS = list(range(1, 21))

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "full_fault_representation_audit.csv"
DETECTOR_MATRIX = CSV_OUTPUT_DIR / "fault_detector_response_matrix.csv"
SCATTER_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_occupancy_entropy.png"
CLASS_BAR_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_class_distribution.png"
OCCUPANCY_HEATMAP_OUTPUT = TAXONOMY_OUTPUT_DIR / "representation_occupancy_heatmap.png"

CLASS_ORDER = ["Locked", "Stable", "Transitional", "Diffuse"]
CLASS_COLORS = {
    "Locked": "#006400",
    "Stable": "#66bb6a",
    "Transitional": "#f28e2b",
    "Diffuse": "#d62728",
}


def _fault_label(fault_number: int) -> str:
    return f"F{int(fault_number):02d}"


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
        "unique_pair_count": int(len(counts)),
        "dominant_pair": dominant_pair,
        "dominant_pair_frequency": float(dominant_count / total),
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


def _collect_fault_metrics(
    testing_path: Path,
    usecols: list[str],
    selected_columns: list[str],
    baseline_model: dict[str, object],
    fault_number: int,
) -> list[dict[str, object]]:
    fault = _fault_label(fault_number)
    runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
    rows = []
    for run_id in sorted(runs)[:N_RUNS]:
        run_df = runs[run_id].sort_values("sample")
        run_data = run_df[selected_columns].to_numpy(dtype=float)
        try:
            series = _compute_version_b_trajectory_series(
                run_data,
                WINDOW,
                STEP,
                K_TOP,
                N_HISTORY,
                baseline_model,
            )
        except ValueError:
            continue
        sample_times = np.asarray(series["sample_times"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        top1_indices = np.asarray(series["top1_indices"], dtype=int)[mask]
        dominant_pairs = [PAIR_LABELS[int(idx)] for idx in top1_indices]
        if dominant_pairs:
            rows.append(_run_metrics(fault, run_id, dominant_pairs))
    if not rows:
        raise ValueError(f"No valid runs for {fault}")
    return rows


def _aggregate_summary(run_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fault, group in run_df.groupby("fault", sort=True):
        dominant_counts = Counter(group["dominant_pair"].tolist())
        most_common_pair, count = dominant_counts.most_common(1)[0]
        mean_occupancy = float(group["occupancy_ratio"].mean())
        mean_entropy = float(group["pair_entropy"].mean())
        rows.append(
            {
                "fault": fault,
                "mean_occupancy": mean_occupancy,
                "std_occupancy": float(group["occupancy_ratio"].std(ddof=1)),
                "mean_entropy": mean_entropy,
                "std_entropy": float(group["pair_entropy"].std(ddof=1)),
                "mean_run_length": float(group["mean_run_length"].mean()),
                "mean_unique_pair_count": float(group["unique_pair_count"].mean()),
                "most_common_dominant_pair": most_common_pair,
                "dominant_pair_consistency": float(count / len(group)),
                "representation_class": _representation_class(mean_occupancy, mean_entropy),
            }
        )
    return pd.DataFrame(rows).sort_values("fault")


def _plot_scatter(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))
    for class_name in CLASS_ORDER:
        group = summary_df.loc[summary_df["representation_class"] == class_name]
        if group.empty:
            continue
        ax.scatter(
            group["mean_entropy"],
            group["mean_occupancy"],
            s=80,
            color=CLASS_COLORS[class_name],
            label=class_name,
            alpha=0.9,
        )
        for row in group.itertuples(index=False):
            ax.annotate(row.fault, (row.mean_entropy, row.mean_occupancy), xytext=(5, 4), textcoords="offset points")

    ax.axhline(0.90, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(0.70, color="black", linestyle="--", linewidth=1.0)
    ax.axvline(0.20, color="black", linestyle="--", linewidth=1.0)
    ax.axvline(0.60, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("mean_entropy")
    ax.set_ylabel("mean_occupancy")
    ax.set_title("Fault Representation Stability:\nOccupancy vs Entropy (F01-F20, first 20 runs)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(SCATTER_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_class_distribution(summary_df: pd.DataFrame) -> None:
    counts = summary_df["representation_class"].value_counts().reindex(CLASS_ORDER, fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(CLASS_ORDER))
    ax.bar(x, counts.to_numpy(dtype=int), color=[CLASS_COLORS[name] for name in CLASS_ORDER], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(CLASS_ORDER)
    ax.set_ylabel("fault count")
    ax.set_title("Representation Class Distribution")
    for idx, class_name in enumerate(CLASS_ORDER):
        faults = summary_df.loc[summary_df["representation_class"] == class_name, "fault"].tolist()
        ax.text(idx, int(counts[class_name]) + 0.05, " ".join(faults) if faults else "(none)", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, max(int(counts.max()) + 2, 3))
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CLASS_BAR_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_occupancy_heatmap(run_df: pd.DataFrame) -> None:
    pivot = run_df.pivot(index="fault", columns="run_id", values="occupancy_ratio")
    pivot = pivot.reindex([_fault_label(number) for number in FAULT_NUMBERS])
    pivot = pivot.reindex(sorted(pivot.columns), axis=1)
    values = pivot.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(12, 9))
    image = ax.imshow(values, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index.tolist())
    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels([str(col) for col in pivot.columns], rotation=45, ha="right")
    ax.set_xlabel("run_id")
    ax.set_ylabel("fault")
    ax.set_title("Per-run Dominant Pair Occupancy (F01-F20, first 20 runs)")
    fig.colorbar(image, ax=ax, label="occupancy_ratio")
    fig.tight_layout()
    fig.savefig(OCCUPANCY_HEATMAP_OUTPUT, dpi=150)
    plt.close(fig)


def _print_grouped_summary(summary_df: pd.DataFrame) -> None:
    print("=== FULL FAULT REPRESENTATION AUDIT ===")
    print("")
    for class_name in CLASS_ORDER:
        print(f"{class_name.upper()} faults:")
        group = summary_df.loc[summary_df["representation_class"] == class_name]
        if group.empty:
            print("(none)")
        for row in group.itertuples(index=False):
            print(
                f"{row.fault}: occupancy={row.mean_occupancy:.3f} "
                f"entropy={row.mean_entropy:.3f} dominant_pair={row.most_common_dominant_pair}"
            )
        print("")

    print("=== CLUSTERING SUMMARY ===")
    print("")
    for class_name in CLASS_ORDER:
        faults = summary_df.loc[summary_df["representation_class"] == class_name, "fault"].tolist()
        print(f"{class_name}: n={len(faults)} faults: {' '.join(faults) if faults else '(none)'}")
    print("")


def _cross_reference_detector_taxonomy(summary_df: pd.DataFrame) -> None:
    print("=== CROSS-REFERENCE WITH DETECTOR TAXONOMY ===")
    print("")
    if not DETECTOR_MATRIX.exists():
        print(f"Missing detector matrix: {DETECTOR_MATRIX}")
        return
    detector_df = pd.read_csv(DETECTOR_MATRIX).set_index("fault")
    for class_name in CLASS_ORDER:
        faults = summary_df.loc[summary_df["representation_class"] == class_name, "fault"].tolist()
        print(f"{class_name} faults:")
        rates = []
        for fault in faults:
            rate = float(detector_df.loc[fault, "top1_rate"])
            rates.append(rate)
            print(f"  {fault}: top1_rate={rate:.3f}")
        if rates:
            print(f"  mean top1_rate = {float(np.mean(rates)):.3f}")
        else:
            print("  mean top1_rate = nan")
        print("")


def _print_conservative_interpretation() -> None:
    print("Conservative interpretation:")
    print("1. Analysis is based on the first 20 runs and does not represent all 500 runs.")
    print("2. representation_class is a descriptive classification.")
    print("3. occupancy/entropy are representation-space metrics.")
    print("4. No physical causal inference is made.")
    print("5. Clustering results need validation on more runs.")


def main() -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(np.asarray(baseline_data, dtype=float), WINDOW, STEP)

    run_rows = []
    for fault_number in FAULT_NUMBERS:
        run_rows.extend(
            _collect_fault_metrics(
                testing_path,
                usecols,
                selected_columns,
                baseline_model,
                fault_number,
            )
        )
    run_df = pd.DataFrame(run_rows)
    summary_df = _aggregate_summary(run_df)
    summary_df.to_csv(SUMMARY_OUTPUT, index=False)

    _plot_scatter(summary_df)
    _plot_class_distribution(summary_df)
    _plot_occupancy_heatmap(run_df)

    _print_grouped_summary(summary_df)
    _cross_reference_detector_taxonomy(summary_df)
    _print_conservative_interpretation()

    print("")
    print("Generated files:")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {SCATTER_OUTPUT}")
    print(f"- {CLASS_BAR_OUTPUT}")
    print(f"- {OCCUPANCY_HEATMAP_OUTPUT}")


if __name__ == "__main__":
    main()
