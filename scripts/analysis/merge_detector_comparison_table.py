"""Merge existing detector benchmark CSVs into one comparison table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"

PCA_FAULT_SUMMARY = CSV_OUTPUT_DIR / "pca_baseline_fault_summary.csv"
PCA_OVERALL_SUMMARY = CSV_OUTPUT_DIR / "pca_baseline_overall_summary.csv"
TOP1_FAULT_SUMMARY = CSV_OUTPUT_DIR / "top1_mass_fault_summary.csv"
TOP1_OVERALL_SUMMARY = CSV_OUTPUT_DIR / "top1_mass_overall_summary.csv"
OUTPUT_PATH = CSV_OUTPUT_DIR / "detector_comparison_summary.csv"
FAULT_ORDER = [f"F{i:02d}" for i in range(1, 21)]


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")


def main():
    for path in (
        PCA_FAULT_SUMMARY,
        PCA_OVERALL_SUMMARY,
        TOP1_FAULT_SUMMARY,
        TOP1_OVERALL_SUMMARY,
    ):
        _require_file(path)

    pca_fault_df = pd.read_csv(PCA_FAULT_SUMMARY)
    pca_overall_df = pd.read_csv(PCA_OVERALL_SUMMARY)
    top1_fault_df = pd.read_csv(TOP1_FAULT_SUMMARY)
    top1_overall_df = pd.read_csv(TOP1_OVERALL_SUMMARY)

    t2_fp_rate = float(pca_overall_df.loc[pca_overall_df["method"] == "T2", "mean_fp_rate"].iloc[0])
    spe_fp_rate = float(pca_overall_df.loc[pca_overall_df["method"] == "SPE", "mean_fp_rate"].iloc[0])
    top1_fp_rate = float(top1_overall_df.loc[top1_overall_df["method"] == "top1_mass", "mean_fp_rate"].iloc[0])

    merged_df = (
        pca_fault_df[
            [
                "fault",
                "t2_detection_rate",
                "spe_detection_rate",
                "t2_median_delay",
                "spe_median_delay",
            ]
        ]
        .merge(
            top1_fault_df[
                [
                    "fault",
                    "top1_detection_rate",
                    "top1_median_delay",
                ]
            ],
            on="fault",
            how="outer",
        )
        .copy()
    )

    merged_df["t2_fp_rate"] = t2_fp_rate
    merged_df["spe_fp_rate"] = spe_fp_rate
    merged_df["top1_fp_rate"] = top1_fp_rate
    merged_df["fault"] = pd.Categorical(merged_df["fault"], categories=FAULT_ORDER, ordered=True)
    merged_df = merged_df.sort_values("fault").reset_index(drop=True)
    merged_df["fault"] = merged_df["fault"].astype(str)

    merged_df = merged_df[
        [
            "fault",
            "t2_detection_rate",
            "spe_detection_rate",
            "top1_detection_rate",
            "t2_median_delay",
            "spe_median_delay",
            "top1_median_delay",
            "t2_fp_rate",
            "spe_fp_rate",
            "top1_fp_rate",
        ]
    ]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    merged_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    diff_df = merged_df.copy()
    diff_df["top1_minus_spe"] = diff_df["top1_detection_rate"] - diff_df["spe_detection_rate"]
    top1_better = diff_df.sort_values("top1_minus_spe", ascending=False).head(5)
    spe_better = diff_df.sort_values("top1_minus_spe", ascending=True).head(5)

    print("=== DETECTOR COMPARISON SUMMARY ===")
    print("top5 faults where top1_mass > SPE:")
    for row in top1_better.itertuples(index=False):
        print(
            f"{row.fault}: "
            f"top1={float(row.top1_detection_rate):.6f}, "
            f"SPE={float(row.spe_detection_rate):.6f}, "
            f"diff={float(row.top1_minus_spe):.6f}"
        )

    print("top5 faults where SPE >> top1_mass:")
    for row in spe_better.itertuples(index=False):
        print(
            f"{row.fault}: "
            f"SPE={float(row.spe_detection_rate):.6f}, "
            f"top1={float(row.top1_detection_rate):.6f}, "
            f"diff={float(row.top1_minus_spe):.6f}"
        )

    print("FP summary:")
    print(f"T2 = {t2_fp_rate:.6f}")
    print(f"SPE = {spe_fp_rate:.6f}")
    print(f"top1_mass = {top1_fp_rate:.6f}")

    print(f"output_path = {OUTPUT_PATH}")
    print(f"columns = {list(merged_df.columns)}")
    print("preview:")
    print(merged_df.head(5).to_string(index=False))

    return merged_df


if __name__ == "__main__":
    main()
