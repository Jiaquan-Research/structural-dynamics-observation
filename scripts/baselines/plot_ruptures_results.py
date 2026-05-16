"""Plot and summarize ruptures benchmark results from CSV outputs."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ruptures_benchmark_common import (
    FAULT_NUMBERS,
    FAULT_SUMMARY_OUTPUT,
    FP_TARGETS,
    OPERATING_PLOT_OUTPUT,
    OVERALL_SUMMARY_OUTPUT,
    PCA_OVERALL_SUMMARY,
    RATE_PLOT_OUTPUT,
    TAXONOMY_OUTPUT_DIR,
    TOP1_OVERALL_SUMMARY,
    VERSIONS,
    conservative_interpretation_lines,
    fault_label,
)


def _existing_detector_points() -> list[dict[str, object]]:
    points = []
    if PCA_OVERALL_SUMMARY.exists():
        pca_df = pd.read_csv(PCA_OVERALL_SUMMARY)
        for method in ("T2", "SPE"):
            rows = pca_df.loc[pca_df["method"] == method]
            if rows.empty:
                continue
            row = rows.iloc[0]
            fp_col = "mean_fp_rate" if "mean_fp_rate" in row.index else "fp_rate"
            det_col = "mean_detection_rate" if "mean_detection_rate" in row.index else "detection_rate"
            points.append(
                {
                    "detector": method,
                    "actual_fp_rate": float(row[fp_col]),
                    "mean_detection_rate": float(row[det_col]),
                }
            )
    if TOP1_OVERALL_SUMMARY.exists():
        top1_df = pd.read_csv(TOP1_OVERALL_SUMMARY)
        row = top1_df.iloc[0]
        fp_col = "mean_fp_rate" if "mean_fp_rate" in row.index else "fp_rate"
        det_col = "mean_detection_rate" if "mean_detection_rate" in row.index else "detection_rate"
        points.append(
            {
                "detector": "top1_mass",
                "actual_fp_rate": float(row[fp_col]),
                "mean_detection_rate": float(row[det_col]),
            }
        )
    return points


def _plot_detection_rate(fault_df: pd.DataFrame) -> None:
    labels = [
        ("Version A", 0.01, "Version_A_FP1"),
        ("Version A", 0.05, "Version_A_FP5"),
        ("Version B", 0.01, "Version_B_FP1"),
        ("Version B", 0.05, "Version_B_FP5"),
    ]
    available_faults = sorted(
        fault_df["fault"].unique().tolist(),
        key=lambda value: int(str(value).replace("F", "")),
    )
    all_faults = [fault_label(fault_number) for fault_number in FAULT_NUMBERS]
    faults = [fault for fault in all_faults if fault in available_faults]
    x = np.arange(len(faults))
    width = 0.20

    fig, ax = plt.subplots(figsize=(14, 6))
    for idx, (version, target, label) in enumerate(labels):
        values = []
        for fault in faults:
            rows = fault_df.loc[
                (fault_df["version"] == version)
                & np.isclose(fault_df["fp_target"].to_numpy(dtype=float), target)
                & (fault_df["fault"] == fault),
                "detection_rate",
            ]
            values.append(float(rows.iloc[0]) if not rows.empty else np.nan)
        ax.bar(x + (idx - 1.5) * width, values, width=width, label=label)

    ax.set_xticks(x)
    ax.set_xticklabels(faults, rotation=45, ha="right")
    ax.set_xlabel("fault")
    ax.set_ylabel("detection_rate")
    ax.set_title("Ruptures detection rate comparison")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(RATE_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _plot_operating_points(overall_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = {
        "ruptures_A_fp1": "tab:orange",
        "ruptures_A_fp5": "tab:red",
        "ruptures_B_fp1": "tab:green",
        "ruptures_B_fp5": "tab:olive",
        "T2": "tab:blue",
        "SPE": "tab:purple",
        "top1_mass": "tab:gray",
    }

    label_counts = {}

    def _label_offset(x: float, y: float) -> tuple[int, int]:
        key = (round(float(x), 6), round(float(y), 6))
        count = label_counts.get(key, 0)
        label_counts[key] = count + 1
        offsets = [(5, 4), (5, 18), (5, -10), (5, 32)]
        return offsets[count % len(offsets)]

    for row in overall_df.itertuples(index=False):
        detector = (
            f"ruptures_{VERSIONS[row.version]['short']}_"
            f"{'fp1' if abs(float(row.fp_target) - 0.01) < 1e-12 else 'fp5'}"
        )
        x = float(row.actual_fp_rate)
        y = float(row.mean_detection_rate)
        ax.scatter(x, y, s=70, color=colors.get(detector, "black"))
        ax.annotate(detector, (x, y), xytext=_label_offset(x, y), textcoords="offset points", fontsize=9)

    for point in _existing_detector_points():
        detector = str(point["detector"])
        x = float(point["actual_fp_rate"])
        y = float(point["mean_detection_rate"])
        ax.scatter(x, y, s=70, color=colors.get(detector, "black"), marker="s")
        ax.annotate(detector, (x, y), xytext=_label_offset(x, y), textcoords="offset points", fontsize=9)

    ax.set_xlabel("actual_fp_rate")
    ax.set_ylabel("mean_detection_rate")
    ax.set_title("Operating point comparison")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OPERATING_PLOT_OUTPUT, dpi=150)
    plt.close(fig)


def _print_summary(overall_df: pd.DataFrame, fault_df: pd.DataFrame) -> None:
    print("")
    print("=== RUPTURES BASELINE SUMMARY ===")
    print("")
    for version in ("Version A", "Version B"):
        print(f"{VERSIONS[version]['display']}:")
        for target in FP_TARGETS:
            rows = overall_df.loc[
                (overall_df["version"] == version)
                & np.isclose(overall_df["fp_target"].to_numpy(dtype=float), float(target))
            ]
            if rows.empty:
                print(f"  FP~{int(target * 100)}%: detection=nan delay=nan")
                continue
            row = rows.iloc[0]
            print(
                f"  FP~{int(target * 100)}%: "
                f"detection={float(row.mean_detection_rate):.6f} "
                f"delay={float(row.mean_delay):.6f}"
            )
        print("")

    print("=== HARD FAULT CHECK ===")
    print("")
    for fault in ("F03", "F09", "F15"):
        print(f"{fault}:")
        for version in ("Version A", "Version B"):
            rows = fault_df.loc[
                (fault_df["version"] == version)
                & np.isclose(fault_df["fp_target"].to_numpy(dtype=float), 0.01)
                & (fault_df["fault"] == fault)
            ]
            if rows.empty:
                print(f"  Version_{VERSIONS[version]['short']}_FP1: missing")
                continue
            row = rows.iloc[0]
            print(
                f"  Version_{VERSIONS[version]['short']}_FP1: "
                f"detection={float(row.detection_rate):.6f}, "
                f"median_delay={float(row.median_delay):.6f}, "
                f"mean_delay={float(row.mean_delay):.6f}"
            )
    print("")

    print("=== COMPARISON WITH EXISTING DETECTORS ===")
    comparison_rows = []
    for point in _existing_detector_points():
        comparison_rows.append(
            {
                "detector": point["detector"],
                "FP": float(point["actual_fp_rate"]),
                "detection": float(point["mean_detection_rate"]),
            }
        )
    for version in ("Version A", "Version B"):
        rows = overall_df.loc[
            (overall_df["version"] == version)
            & np.isclose(overall_df["fp_target"].to_numpy(dtype=float), 0.01)
        ]
        if rows.empty:
            continue
        row = rows.iloc[0]
        comparison_rows.append(
            {
                "detector": f"ruptures_{VERSIONS[version]['short']}_fp1",
                "FP": float(row.actual_fp_rate),
                "detection": float(row.mean_detection_rate),
            }
        )
    comparison_df = pd.DataFrame(comparison_rows)
    if comparison_df.empty:
        print("No existing detector summaries found.")
    else:
        print(comparison_df.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    for line in conservative_interpretation_lines():
        print(line)


def main() -> None:
    if not FAULT_SUMMARY_OUTPUT.exists():
        raise FileNotFoundError(f"Missing fault summary: {FAULT_SUMMARY_OUTPUT}")
    if not OVERALL_SUMMARY_OUTPUT.exists():
        raise FileNotFoundError(f"Missing overall summary: {OVERALL_SUMMARY_OUTPUT}")

    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fault_df = pd.read_csv(FAULT_SUMMARY_OUTPUT)
    overall_df = pd.read_csv(OVERALL_SUMMARY_OUTPUT)

    _plot_detection_rate(fault_df)
    _plot_operating_points(overall_df)
    _print_summary(overall_df, fault_df)

    print("")
    print("Generated files:")
    print(f"- {RATE_PLOT_OUTPUT}")
    print(f"- {OPERATING_PLOT_OUTPUT}")


if __name__ == "__main__":
    main()
