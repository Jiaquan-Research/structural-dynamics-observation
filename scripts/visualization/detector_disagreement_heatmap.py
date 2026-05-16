"""Visualize detector response disagreement from the unified response matrix."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"

INPUT_MATRIX = CSV_OUTPUT_DIR / "fault_detector_response_matrix.csv"
DETECTION_HEATMAP = TAXONOMY_OUTPUT_DIR / "detector_disagreement_heatmap.png"
PAIRWISE_HEATMAP = TAXONOMY_OUTPUT_DIR / "detector_pairwise_disagreement.png"
PER_FAULT_BAR = TAXONOMY_OUTPUT_DIR / "per_fault_max_disagreement.png"

DETECTORS = ["T2", "SPE", "top1_mass", "ruptures_A", "ruptures_B"]
RATE_COLUMNS = {
    "T2": "t2_rate",
    "SPE": "spe_rate",
    "top1_mass": "top1_rate",
    "ruptures_A": "ruptures_a_rate",
    "ruptures_B": "ruptures_b_rate",
}

PATTERN_ORDER = {
    "geometry_locked": 0,
    "geometry_only": 1,
    "raw_shift_only": 2,
    "weak_geometry": 3,
    "mixed": 4,
}
PATTERN_ABBREVIATIONS = {
    "geometry_locked": "GL",
    "geometry_only": "GO",
    "raw_shift_only": "RS",
    "weak_geometry": "WG",
    "convergent_geometry": "CG",
    "mixed": "MX",
    "classical_only": "CL",
    "fully_insensitive": "FI",
}
PATTERN_COLORS = {
    "geometry_locked": "#2ca02c",
    "geometry_only": "#1f77b4",
    "raw_shift_only": "#d62728",
    "weak_geometry": "#ff7f0e",
    "convergent_geometry": "#9467bd",
    "mixed": "#7f7f7f",
    "classical_only": "#8c564b",
    "fully_insensitive": "#17becf",
}


def _fault_number(fault: str) -> int:
    return int(str(fault).replace("F", ""))


def _load_matrix() -> pd.DataFrame:
    if not INPUT_MATRIX.exists():
        raise FileNotFoundError(f"Missing input matrix: {INPUT_MATRIX}")
    df = pd.read_csv(INPUT_MATRIX)
    required = {"fault", "fault_pattern", *RATE_COLUMNS.values()}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Input matrix missing columns: {sorted(missing)}")
    return df


def _sort_faults(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = df.copy()
    sorted_df["_pattern_order"] = sorted_df["fault_pattern"].map(
        lambda value: PATTERN_ORDER.get(str(value), 99)
    )
    sorted_df["_fault_number"] = sorted_df["fault"].map(_fault_number)
    sorted_df = sorted_df.sort_values(["_pattern_order", "_fault_number"])
    return sorted_df.drop(columns=["_pattern_order", "_fault_number"])


def _rate_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[[RATE_COLUMNS[detector] for detector in DETECTORS]].to_numpy(dtype=float)


def _plot_detection_heatmap(df: pd.DataFrame) -> None:
    sorted_df = _sort_faults(df)
    values = _rate_matrix(sorted_df)
    y_labels = [
        f"{row.fault} [{PATTERN_ABBREVIATIONS.get(str(row.fault_pattern), 'OT')}]"
        for row in sorted_df.itertuples(index=False)
    ]

    fig, ax = plt.subplots(figsize=(10, 12))
    image = ax.imshow(values, cmap="RdYlGn", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(len(DETECTORS)))
    ax.set_xticklabels(DETECTORS, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(y_labels)))
    ax.set_yticklabels(y_labels)
    ax.set_title("Fault × Detector Detection Rate Heatmap")

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=8)

    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("detection rate")
    fig.tight_layout()
    fig.savefig(DETECTION_HEATMAP, dpi=150)
    plt.close(fig)


def _pairwise_disagreement(df: pd.DataFrame) -> pd.DataFrame:
    values = {detector: df[RATE_COLUMNS[detector]].to_numpy(dtype=float) for detector in DETECTORS}
    matrix = np.zeros((len(DETECTORS), len(DETECTORS)), dtype=float)
    for i, detector_i in enumerate(DETECTORS):
        for j, detector_j in enumerate(DETECTORS):
            matrix[i, j] = float(np.mean(np.abs(values[detector_i] - values[detector_j])))
    return pd.DataFrame(matrix, index=DETECTORS, columns=DETECTORS)


def _plot_pairwise_heatmap(pairwise_df: pd.DataFrame) -> None:
    values = pairwise_df.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8, 7))
    image = ax.imshow(values, cmap="Blues", vmin=0.0, vmax=float(np.max(values)))
    ax.set_xticks(np.arange(len(DETECTORS)))
    ax.set_xticklabels(DETECTORS, rotation=30, ha="right")
    ax.set_yticks(np.arange(len(DETECTORS)))
    ax.set_yticklabels(DETECTORS)
    ax.set_title("Pairwise Detector Disagreement (mean |delta| over F01-F20)")

    for i in range(values.shape[0]):
        for j in range(values.shape[1]):
            ax.text(j, i, f"{values[i, j]:.3f}", ha="center", va="center", fontsize=9)

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(PAIRWISE_HEATMAP, dpi=150)
    plt.close(fig)


def _per_fault_disagreement(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in df.itertuples(index=False):
        rates = {detector: float(getattr(row, RATE_COLUMNS[detector])) for detector in DETECTORS}
        pair_deltas = [
            (detector_i, detector_j, abs(rates[detector_i] - rates[detector_j]))
            for detector_i, detector_j in combinations(DETECTORS, 2)
        ]
        detector_i, detector_j, max_delta = max(pair_deltas, key=lambda item: item[2])
        rows.append(
            {
                "fault": str(row.fault),
                "fault_pattern": str(row.fault_pattern),
                "max_disagreement": float(max_delta),
                "detector1": detector_i,
                "detector2": detector_j,
            }
        )
    result = pd.DataFrame(rows)
    result["_fault_number"] = result["fault"].map(_fault_number)
    return result.sort_values("_fault_number").drop(columns=["_fault_number"])


def _plot_per_fault_bar(disagreement_df: pd.DataFrame) -> None:
    colors = [
        PATTERN_COLORS.get(pattern, "#333333")
        for pattern in disagreement_df["fault_pattern"].tolist()
    ]
    mean_disagreement = float(disagreement_df["max_disagreement"].mean())

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(disagreement_df))
    ax.bar(x, disagreement_df["max_disagreement"].to_numpy(dtype=float), color=colors, alpha=0.85)
    ax.axhline(mean_disagreement, color="black", linestyle="--", linewidth=1.2, label="mean_disagreement")
    ax.set_xticks(x)
    ax.set_xticklabels(disagreement_df["fault"].tolist(), rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("max_disagreement")
    ax.set_title("Per-fault Max Detector Disagreement")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(PER_FAULT_BAR, dpi=150)
    plt.close(fig)


def _print_summary(pairwise_df: pd.DataFrame, disagreement_df: pd.DataFrame) -> None:
    print("=== DETECTOR DISAGREEMENT SUMMARY ===")
    print("")
    print("Top 5 faults by max disagreement:")
    for row in disagreement_df.sort_values("max_disagreement", ascending=False).head(5).itertuples(index=False):
        print(
            f"{row.fault}: max_delta={row.max_disagreement:.3f} "
            f"pattern={row.fault_pattern} ({row.detector1} vs {row.detector2})"
        )
    print("")
    print("Bottom 5 faults by max disagreement:")
    for row in disagreement_df.sort_values("max_disagreement", ascending=True).head(5).itertuples(index=False):
        print(f"{row.fault}: max_delta={row.max_disagreement:.3f} pattern={row.fault_pattern}")
    print("")
    print("Pairwise disagreement matrix:")
    print(pairwise_df.to_string(float_format=lambda value: f"{value:.3f}"))

    off_diag = []
    for detector_i, detector_j in combinations(DETECTORS, 2):
        off_diag.append((detector_i, detector_j, float(pairwise_df.loc[detector_i, detector_j])))
    most_disagreeing = max(off_diag, key=lambda item: item[2])
    most_agreeing = min(off_diag, key=lambda item: item[2])
    print("")
    print(
        f"Most disagreeing pair: {most_disagreeing[0]} vs {most_disagreeing[1]} "
        f"(mean_delta={most_disagreeing[2]:.3f})"
    )
    print(
        f"Most agreeing pair: {most_agreeing[0]} vs {most_agreeing[1]} "
        f"(mean_delta={most_agreeing[2]:.3f})"
    )
    print("")
    print("Conservative interpretation:")
    print("1. Heatmap covers all F01-F20.")
    print("2. top1_mass / ruptures only cover the XMEAS7-11 subspace.")
    print("3. disagreement is descriptive statistics, not proof of causality.")
    print("4. High disagreement indicates different detectors are seeing different signal structures.")


def main() -> None:
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = _load_matrix()
    pairwise_df = _pairwise_disagreement(df)
    disagreement_df = _per_fault_disagreement(df)

    _plot_detection_heatmap(df)
    _plot_pairwise_heatmap(pairwise_df)
    _plot_per_fault_bar(disagreement_df)
    _print_summary(pairwise_df, disagreement_df)

    print("")
    print("Generated files:")
    print(f"- {DETECTION_HEATMAP}")
    print(f"- {PAIRWISE_HEATMAP}")
    print(f"- {PER_FAULT_BAR}")


if __name__ == "__main__":
    main()
