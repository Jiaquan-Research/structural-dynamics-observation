"""Build a unified detector response taxonomy from existing benchmark CSVs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"

PCA_FAULT = CSV_OUTPUT_DIR / "pca_baseline_fault_summary.csv"
PCA_OVERALL = CSV_OUTPUT_DIR / "pca_baseline_overall_summary.csv"
TOP1_FAULT = CSV_OUTPUT_DIR / "top1_mass_fault_summary.csv"
TOP1_OVERALL = CSV_OUTPUT_DIR / "top1_mass_overall_summary.csv"
RUPTURES_FAULT = CSV_OUTPUT_DIR / "ruptures_baseline_fault_summary.csv"

COMPARISON_OUTPUT = CSV_OUTPUT_DIR / "detector_comparison_summary_v2.csv"
MATRIX_OUTPUT = CSV_OUTPUT_DIR / "fault_detector_response_matrix.csv"
MARKDOWN_OUTPUT = TAXONOMY_OUTPUT_DIR / "fault_detector_taxonomy_v2.md"

FAULTS = [f"F{i:02d}" for i in range(1, 21)]
PROFILE_FAULTS = ["F02", "F03", "F06", "F08", "F12", "F13", "F14", "F01"]

DETECTOR_META = {
    "T2": {
        "input_signal": "trajectory_window_52vars",
        "detector_type": "pca_t2",
        "notes": "low FP, misses hard faults, gaussian assumption violated",
    },
    "SPE": {
        "input_signal": "trajectory_window_52vars",
        "detector_type": "pca_spe",
        "notes": "high coverage, FP=32%, trajectory flattening artifact",
    },
    "top1_mass": {
        "input_signal": "XMEAS7-11_correlation",
        "detector_type": "geometry_locking",
        "notes": "geometry locking detector, selective, FP floor=2.5%",
    },
    "ruptures_A": {
        "input_signal": "XMEAS7+XMEAS11_raw",
        "detector_type": "ruptures_raw",
        "notes": "raw signal changepoint, piecewise-stationary bias",
    },
    "ruptures_B": {
        "input_signal": "XMEAS7-XMEAS11_rolling_corr",
        "detector_type": "ruptures_rolling_corr",
        "notes": "coupling statistics changepoint, very low coverage",
    },
}

CONSERVATIVE_LINES = [
    "1. All conclusions are based on TEP simulation data.",
    "2. top1_mass / ruptures only cover the XMEAS7-11 subspace.",
    "3. fault_pattern is a descriptive classification, not proof of physical causality.",
    "4. Domain expert validation is needed to assess physical plausibility.",
]


def _require_files(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input CSVs: {missing}")


def _response_level(rate: float) -> str:
    rate = float(rate)
    if rate >= 0.70:
        return "Strong"
    if rate >= 0.20:
        return "Moderate"
    if rate >= 0.05:
        return "Weak"
    return "Insensitive"


def _fault_pattern(row: pd.Series) -> str:
    t2_rate = float(row["t2_rate"])
    spe_rate = float(row["spe_rate"])
    top1_rate = float(row["top1_rate"])
    ruptures_a_rate = float(row["ruptures_a_rate"])
    ruptures_b_rate = float(row["ruptures_b_rate"])

    if top1_rate >= 0.70 and ruptures_a_rate >= 0.50:
        return "geometry_locked"
    if top1_rate >= 0.70 and ruptures_a_rate < 0.50:
        return "geometry_only"
    if top1_rate < 0.20 and ruptures_a_rate >= 0.50:
        return "raw_shift_only"
    if 0.20 <= top1_rate < 0.70 and ruptures_b_rate >= 0.10:
        return "convergent_geometry"
    if 0.05 <= top1_rate < 0.20 and ruptures_b_rate >= 0.05:
        return "weak_geometry"
    if (
        t2_rate < 0.05
        and spe_rate < 0.20
        and top1_rate < 0.05
        and ruptures_a_rate < 0.05
    ):
        return "fully_insensitive"
    if (
        (t2_rate >= 0.70 or spe_rate >= 0.70)
        and top1_rate < 0.05
        and ruptures_a_rate < 0.20
    ):
        return "classical_only"
    return "mixed"


def _one_row(df: pd.DataFrame, column: str, value: object) -> pd.Series:
    rows = df.loc[df[column] == value]
    if rows.empty:
        raise ValueError(f"Missing row where {column}={value}")
    return rows.iloc[0]


def _load_inputs() -> dict[str, pd.DataFrame]:
    _require_files([PCA_FAULT, PCA_OVERALL, TOP1_FAULT, TOP1_OVERALL, RUPTURES_FAULT])
    return {
        "pca_fault": pd.read_csv(PCA_FAULT),
        "pca_overall": pd.read_csv(PCA_OVERALL),
        "top1_fault": pd.read_csv(TOP1_FAULT),
        "top1_overall": pd.read_csv(TOP1_OVERALL),
        "ruptures_fault": pd.read_csv(RUPTURES_FAULT),
    }


def _ruptures_subset(ruptures_df: pd.DataFrame, version: str) -> pd.DataFrame:
    rows = ruptures_df.loc[
        (ruptures_df["version"] == version)
        & np.isclose(ruptures_df["fp_target"].to_numpy(dtype=float), 0.01)
    ].copy()
    if rows.empty:
        raise ValueError(f"No ruptures rows for {version}, fp_target=0.01")
    return rows


def _build_matrix(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pca = data["pca_fault"].set_index("fault")
    top1 = data["top1_fault"].set_index("fault")
    ruptures_a = _ruptures_subset(data["ruptures_fault"], "Version A").set_index("fault")
    ruptures_b = _ruptures_subset(data["ruptures_fault"], "Version B").set_index("fault")

    rows = []
    for fault in FAULTS:
        row = {
            "fault": fault,
            "t2_rate": float(pca.loc[fault, "t2_detection_rate"]),
            "spe_rate": float(pca.loc[fault, "spe_detection_rate"]),
            "top1_rate": float(top1.loc[fault, "top1_detection_rate"]),
            "ruptures_a_rate": float(ruptures_a.loc[fault, "detection_rate"]),
            "ruptures_b_rate": float(ruptures_b.loc[fault, "detection_rate"]),
        }
        row["t2_level"] = _response_level(row["t2_rate"])
        row["spe_level"] = _response_level(row["spe_rate"])
        row["top1_level"] = _response_level(row["top1_rate"])
        row["ruptures_a_level"] = _response_level(row["ruptures_a_rate"])
        row["ruptures_b_level"] = _response_level(row["ruptures_b_rate"])
        row["fault_pattern"] = _fault_pattern(pd.Series(row))
        rows.append(row)

    columns = [
        "fault",
        "t2_level",
        "t2_rate",
        "spe_level",
        "spe_rate",
        "top1_level",
        "top1_rate",
        "ruptures_a_level",
        "ruptures_a_rate",
        "ruptures_b_level",
        "ruptures_b_rate",
        "fault_pattern",
    ]
    return pd.DataFrame(rows, columns=columns)


def _level_counts(rates: pd.Series) -> dict[str, int]:
    levels = rates.map(_response_level)
    return {
        "strong_fault_count": int((levels == "Strong").sum()),
        "moderate_fault_count": int((levels == "Moderate").sum()),
        "weak_fault_count": int((levels == "Weak").sum()),
        "insensitive_fault_count": int((levels == "Insensitive").sum()),
    }


def _build_comparison(data: dict[str, pd.DataFrame], matrix_df: pd.DataFrame) -> pd.DataFrame:
    pca_overall = data["pca_overall"]
    top1_overall = data["top1_overall"]
    ruptures_a = _ruptures_subset(data["ruptures_fault"], "Version A")
    ruptures_b = _ruptures_subset(data["ruptures_fault"], "Version B")

    detector_sources = {
        "T2": {
            "overall": _one_row(pca_overall, "method", "T2"),
            "rates": matrix_df["t2_rate"],
        },
        "SPE": {
            "overall": _one_row(pca_overall, "method", "SPE"),
            "rates": matrix_df["spe_rate"],
        },
        "top1_mass": {
            "overall": _one_row(top1_overall, "method", "top1_mass"),
            "rates": matrix_df["top1_rate"],
        },
    }

    rows = []
    for detector in ("T2", "SPE", "top1_mass"):
        source = detector_sources[detector]
        overall = source["overall"]
        meta = DETECTOR_META[detector]
        counts = _level_counts(source["rates"])
        rows.append(
            {
                "detector": detector,
                "input_signal": meta["input_signal"],
                "fp_rate": float(overall["mean_fp_rate"]),
                "mean_detection_rate": float(overall["mean_detection_rate"]),
                "mean_delay": float(overall["mean_delay"]),
                "detector_type": meta["detector_type"],
                **counts,
                "notes": meta["notes"],
            }
        )

    for detector, df, rate_col in (
        ("ruptures_A", ruptures_a, "ruptures_a_rate"),
        ("ruptures_B", ruptures_b, "ruptures_b_rate"),
    ):
        meta = DETECTOR_META[detector]
        counts = _level_counts(matrix_df[rate_col])
        rows.append(
            {
                "detector": detector,
                "input_signal": meta["input_signal"],
                "fp_rate": float(df["actual_fp_rate"].iloc[0]),
                "mean_detection_rate": float(df["detection_rate"].mean()),
                "mean_delay": float(df["mean_delay"].dropna().mean()),
                "detector_type": meta["detector_type"],
                **counts,
                "notes": meta["notes"],
            }
        )

    columns = [
        "detector",
        "input_signal",
        "fp_rate",
        "mean_detection_rate",
        "mean_delay",
        "detector_type",
        "strong_fault_count",
        "moderate_fault_count",
        "weak_fault_count",
        "insensitive_fault_count",
        "notes",
    ]
    return pd.DataFrame(rows, columns=columns)


def _delay_lookup(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {
        "pca": data["pca_fault"].set_index("fault"),
        "top1": data["top1_fault"].set_index("fault"),
        "ruptures_a": _ruptures_subset(data["ruptures_fault"], "Version A").set_index("fault"),
        "ruptures_b": _ruptures_subset(data["ruptures_fault"], "Version B").set_index("fault"),
    }


def _fmt_delay(value: object) -> str:
    try:
        if pd.isna(value):
            return "nan"
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "nan"


def _profile_observations(fault: str, row: pd.Series) -> list[str]:
    observations = []
    if row["top1_rate"] >= 0.70 and row["ruptures_a_rate"] < 0.20:
        observations.append("top1_mass strong while ruptures_A is weak: geometry-specific separation.")
    if row["ruptures_a_rate"] >= 0.70 and row["top1_rate"] < 0.20:
        observations.append("ruptures_A strong while top1_mass is weak: raw signal shift dominates.")
    if max(row["t2_rate"], row["spe_rate"], row["top1_rate"], row["ruptures_a_rate"]) < 0.20:
        observations.append("All primary detectors are weak: genuinely hard fault under this benchmark.")
    if row["t2_rate"] >= 0.70 and row["spe_rate"] >= 0.70 and row["top1_rate"] >= 0.70:
        observations.append("Classical and geometry detectors are all strong.")
    if row["ruptures_b_rate"] >= 0.10:
        observations.append("ruptures_B also responds: coupling statistics shift is visible.")
    if fault == "F14":
        observations.append("F14 is a strong top1_mass versus ruptures_A separation point.")
    if not observations:
        observations.append("Detector responses are mixed; no single response mode dominates.")
    return observations


def _print_profiles(matrix_df: pd.DataFrame, data: dict[str, pd.DataFrame]) -> None:
    delays = _delay_lookup(data)
    matrix = matrix_df.set_index("fault")
    for fault in PROFILE_FAULTS:
        row = matrix.loc[fault]
        print("")
        print(f"=== FAULT PROFILE: {fault} ===")
        print(f"fault_pattern: {row['fault_pattern']}")
        print(
            f"T2:         rate={row['t2_rate']:.3f}  level={row['t2_level']:<11} "
            f"delay={_fmt_delay(delays['pca'].loc[fault, 't2_median_delay'])}"
        )
        print(
            f"SPE:        rate={row['spe_rate']:.3f}  level={row['spe_level']:<11} "
            f"delay={_fmt_delay(delays['pca'].loc[fault, 'spe_median_delay'])}"
        )
        print(
            f"top1_mass:  rate={row['top1_rate']:.3f}  level={row['top1_level']:<11} "
            f"delay={_fmt_delay(delays['top1'].loc[fault, 'top1_median_delay'])}"
        )
        print(
            f"ruptures_A: rate={row['ruptures_a_rate']:.3f}  level={row['ruptures_a_level']:<11} "
            f"delay={_fmt_delay(delays['ruptures_a'].loc[fault, 'median_delay'])}"
        )
        print(
            f"ruptures_B: rate={row['ruptures_b_rate']:.3f}  level={row['ruptures_b_level']:<11} "
            f"delay={_fmt_delay(delays['ruptures_b'].loc[fault, 'median_delay'])}"
        )
        print("")
        print("Key observation:")
        for observation in _profile_observations(fault, row):
            print(f"- {observation}")


def _markdown_table(df: pd.DataFrame) -> str:
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{value:.6f}")
    headers = list(display.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in display.astype(str).itertuples(index=False):
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _pattern_sections(matrix_df: pd.DataFrame) -> str:
    characteristics = {
        "geometry_locked": "Strong geometry response accompanied by raw changepoint response.",
        "geometry_only": "Strong geometry response without comparable raw signal changepoint.",
        "raw_shift_only": "Raw XMEAS7/XMEAS11 changepoint response dominates geometry locking.",
        "convergent_geometry": "Moderate geometry response with visible rolling-correlation changepoint.",
        "weak_geometry": "Weak geometry response with some coupling-statistic support.",
        "fully_insensitive": "All evaluated detectors have low response.",
        "classical_only": "Classical trajectory detectors respond while geometry and raw pair detectors do not.",
        "mixed": "Detector responses do not match a single predefined pattern.",
    }
    sections = []
    for pattern in characteristics:
        faults = matrix_df.loc[matrix_df["fault_pattern"] == pattern, "fault"].tolist()
        fault_text = " ".join(faults) if faults else "(none)"
        sections.append(f"### {pattern}\nFaults: {fault_text}\nCharacteristics: {characteristics[pattern]}")
    return "\n\n".join(sections)


def _write_markdown(comparison_df: pd.DataFrame, matrix_df: pd.DataFrame) -> None:
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Fault-Detector Taxonomy v2",
        "## Date: 2026-05",
        "",
        "## Detector Operating Points",
        _markdown_table(comparison_df),
        "",
        "## Fault Response Matrix",
        _markdown_table(matrix_df),
        "",
        "## Fault Patterns",
        _pattern_sections(matrix_df),
        "",
        "## Key Findings",
        "",
        "1. F14 separation:\n   top1_mass=97% vs ruptures_A=0.4%\n   Strongest evidence for geometry-specific signal",
        "",
        "2. F02/F13:\n   ruptures_A strong, top1_mass weak\n   Raw signal shift dominates",
        "",
        "3. F03/F09/F15:\n   All detectors weak\n   Genuinely hard faults",
        "",
        "## Conservative Interpretation",
    ]
    lines.extend(CONSERVATIVE_LINES)
    lines.extend(
        [
            "",
            "## Limitations",
            "- top1_mass limited to XMEAS7-11 subspace",
            "- ruptures_A/B only use XMEAS7+XMEAS11",
            "- Results based on TEP simulation data",
            "- Physical causality not established",
            "- Domain expert validation is needed to assess physical plausibility",
        ]
    )
    MARKDOWN_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_terminal_summary(comparison_df: pd.DataFrame, matrix_df: pd.DataFrame) -> None:
    print("=== DETECTOR COMPARISON SUMMARY ===")
    print(comparison_df.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("=== FAULT PATTERN DISTRIBUTION ===")
    for pattern in [
        "geometry_locked",
        "geometry_only",
        "raw_shift_only",
        "convergent_geometry",
        "weak_geometry",
        "fully_insensitive",
        "classical_only",
        "mixed",
    ]:
        faults = matrix_df.loc[matrix_df["fault_pattern"] == pattern, "fault"].tolist()
        print(f"{pattern}: {' '.join(faults) if faults else '(none)'}")
    print("")
    print("=== KEY SEPARATION POINTS ===")
    sep = matrix_df.assign(top1_minus_ruptures_a=matrix_df["top1_rate"] - matrix_df["ruptures_a_rate"])
    for row in sep.reindex(sep["top1_minus_ruptures_a"].abs().sort_values(ascending=False).index).head(5).itertuples(index=False):
        print(
            f"{row.fault}: top1={row.top1_rate:.3f}, "
            f"ruptures_A={row.ruptures_a_rate:.3f}, "
            f"delta={row.top1_minus_ruptures_a:.3f}, pattern={row.fault_pattern}"
        )
    print("")
    _print_profiles(matrix_df, _load_inputs())
    print("")
    print("=== CONSERVATIVE INTERPRETATION ===")
    for line in CONSERVATIVE_LINES:
        print(line)


def main() -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = _load_inputs()
    matrix_df = _build_matrix(data)
    comparison_df = _build_comparison(data, matrix_df)

    comparison_df.to_csv(COMPARISON_OUTPUT, index=False)
    matrix_df.to_csv(MATRIX_OUTPUT, index=False)
    _write_markdown(comparison_df, matrix_df)
    _print_terminal_summary(comparison_df, matrix_df)

    print("")
    print("Generated files:")
    print(f"- {COMPARISON_OUTPUT}")
    print(f"- {MATRIX_OUTPUT}")
    print(f"- {MARKDOWN_OUTPUT}")


if __name__ == "__main__":
    main()
