"""ES-v3.3b Collapse Cluster Audit.

Status: EL-1 exploratory.

Checks whether recovery-quality collapse runs are fixed across block_3,
block_5, and block_10, or attack dependent. This is analysis only: no detector
change, no new attack, no soft lock, TE, mixed disturbance, marine transfer,
taxonomy update, industrial interpretation, or early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

QUALITY_RUNS = CSV_DIR / "es_v3_recovery_quality_runs.csv"
RECOVERY_RUNS = CSV_DIR / "es_v3_recovery_runs.csv"
BOUNDARY_RUNS = CSV_DIR / "es_v3_recovery_boundary_runs.csv"
F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_collapse_cluster_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_collapse_cluster_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_collapse_cluster_audit.md"

TARGET_PAIR = "XMEAS7-XMEAS11"
MODES = ["block_3", "block_5", "block_10"]


def _load_quality() -> pd.DataFrame:
    df = pd.read_csv(QUALITY_RUNS)
    required = ["run_id", "mode", "quality_class"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{QUALITY_RUNS} missing required columns: {missing}")
    return df.loc[df["mode"].isin(MODES)].copy()


def _collapse_sets(quality: pd.DataFrame) -> dict[str, set[int]]:
    out = {}
    for mode in MODES:
        runs = quality.loc[
            (quality["mode"] == mode) & (quality["quality_class"] == "collapse"),
            "run_id",
        ]
        out[mode] = set(int(run_id) for run_id in runs)
    return out


def _optional_no_replacement() -> set[int]:
    if not RECOVERY_RUNS.exists():
        return set()
    df = pd.read_csv(RECOVERY_RUNS)
    if not {"run_id", "mode", "relock_status"}.issubset(df.columns):
        return set()
    rows = df.loc[df["mode"].isin(MODES) & (df["relock_status"] == "no_replacement")]
    return set(int(run_id) for run_id in rows["run_id"])


def _optional_horizon_overlap() -> set[int]:
    if not BOUNDARY_RUNS.exists():
        return set()
    df = pd.read_csv(BOUNDARY_RUNS)
    if not {"run_id", "horizon_margin", "relock_status"}.issubset(df.columns):
        return set()
    rows = df.loc[(df["relock_status"] != "relocked") & (df["horizon_margin"] <= 1)]
    return set(int(run_id) for run_id in rows["run_id"])


def _baseline_by_run() -> pd.DataFrame:
    if not F13_TRACE.exists():
        return pd.DataFrame(columns=["run_id", "baseline_locked_fraction", "baseline_duration"])
    trace = pd.read_csv(F13_TRACE)
    required = ["run_id", "window_index", "dominant_pair"]
    missing = [column for column in required if column not in trace.columns]
    if missing:
        return pd.DataFrame(columns=["run_id", "baseline_locked_fraction", "baseline_duration"])
    rows = []
    for run_id, group in trace.groupby("run_id", sort=True):
        group = group.sort_values("window_index")
        run_length = 0
        locked_flags: list[bool] = []
        durations: list[int] = []
        current = 0
        for row in group.itertuples(index=False):
            if str(row.dominant_pair) == TARGET_PAIR:
                run_length += 1
            else:
                run_length = 0
            is_locked = run_length >= 10
            locked_flags.append(is_locked)
            if is_locked:
                current += 1
            elif current:
                durations.append(current)
                current = 0
        if current:
            durations.append(current)
        rows.append(
            {
                "run_id": int(run_id),
                "baseline_locked_fraction": float(np.mean(locked_flags)) if locked_flags else np.nan,
                "baseline_duration": int(max(durations)) if durations else 0,
            }
        )
    return pd.DataFrame(rows)


def _classify_count(count: int) -> str:
    if count == 0:
        return "never"
    if count == 1:
        return "single"
    if count == 2:
        return "partial"
    return "fixed"


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _build_runs_table(
    quality: pd.DataFrame,
    collapse_sets: dict[str, set[int]],
    fixed: set[int],
    union: set[int],
    no_replacement: set[int],
    horizon: set[int],
    baseline: pd.DataFrame,
) -> pd.DataFrame:
    all_runs = sorted(set(int(run_id) for run_id in quality["run_id"].unique()))
    rows = []
    for run_id in all_runs:
        flags = {
            "block3": run_id in collapse_sets["block_3"],
            "block5": run_id in collapse_sets["block_5"],
            "block10": run_id in collapse_sets["block_10"],
        }
        count = int(sum(flags.values()))
        rows.append(
            {
                "run_id": run_id,
                "collapse_count": count,
                "collapse_class": _classify_count(count),
                **flags,
                "is_fixed_cluster": run_id in fixed,
                "is_no_replacement": run_id in no_replacement,
                "is_horizon_overlap": run_id in horizon,
            }
        )
    out = pd.DataFrame(rows)
    if not baseline.empty:
        out = out.merge(baseline, on="run_id", how="left")
    else:
        out["baseline_locked_fraction"] = np.nan
        out["baseline_duration"] = np.nan
    out["is_collapse_union"] = out["run_id"].isin(union)
    return out


def _baseline_stats(runs: pd.DataFrame, mask: pd.Series) -> dict[str, float]:
    group = runs.loc[mask, "baseline_locked_fraction"].dropna()
    if group.empty:
        return {"mean": np.nan, "median": np.nan, "p25": np.nan, "p75": np.nan}
    return {
        "mean": float(group.mean()),
        "median": float(group.median()),
        "p25": float(group.quantile(0.25)),
        "p75": float(group.quantile(0.75)),
    }


def _summary_rows(
    runs: pd.DataFrame,
    union: set[int],
    fixed: set[int],
    no_replacement: set[int],
    horizon: set[int],
) -> pd.DataFrame:
    collapse_mask = runs["is_collapse_union"]
    noncollapse_mask = ~collapse_mask
    collapse_stats = _baseline_stats(runs, collapse_mask)
    noncollapse_stats = _baseline_stats(runs, noncollapse_mask)
    rows = [
        {"metric": "n_union", "value": len(union)},
        {"metric": "n_intersection", "value": len(fixed)},
        {"metric": "fixed_fraction", "value": len(fixed) / len(union) if union else 0.0},
        {"metric": "n_never", "value": int((runs["collapse_class"] == "never").sum())},
        {"metric": "n_single", "value": int((runs["collapse_class"] == "single").sum())},
        {"metric": "n_partial", "value": int((runs["collapse_class"] == "partial").sum())},
        {"metric": "n_fixed", "value": int((runs["collapse_class"] == "fixed").sum())},
        {"metric": "overlap_no_replacement", "value": len(union & no_replacement)},
        {"metric": "overlap_no_replacement_jaccard", "value": _jaccard(union, no_replacement)},
        {"metric": "overlap_horizon", "value": len(union & horizon)},
        {"metric": "overlap_horizon_jaccard", "value": _jaccard(union, horizon)},
        {"metric": "collapse_baseline_mean", "value": collapse_stats["mean"]},
        {"metric": "collapse_baseline_median", "value": collapse_stats["median"]},
        {"metric": "collapse_baseline_p25", "value": collapse_stats["p25"]},
        {"metric": "collapse_baseline_p75", "value": collapse_stats["p75"]},
        {"metric": "noncollapse_baseline_mean", "value": noncollapse_stats["mean"]},
        {"metric": "noncollapse_baseline_median", "value": noncollapse_stats["median"]},
        {"metric": "noncollapse_baseline_p25", "value": noncollapse_stats["p25"]},
        {"metric": "noncollapse_baseline_p75", "value": noncollapse_stats["p75"]},
    ]
    return pd.DataFrame(rows)


def _verdict(summary: pd.DataFrame) -> str:
    values = {row.metric: float(row.value) for row in summary.itertuples(index=False)}
    n_union = values.get("n_union", 0.0)
    fixed_fraction = values.get("fixed_fraction", 0.0)
    no_rep = values.get("overlap_no_replacement", 0.0)
    horizon = values.get("overlap_horizon", 0.0)
    explained = (no_rep + horizon) / n_union if n_union else 0.0
    if n_union and explained >= 0.70:
        return "artifact"
    if fixed_fraction >= 0.70:
        return "structural"
    return "mixed"


def _markdown_table(df: pd.DataFrame, floatfmt: str = ".6f") -> str:
    if df.empty:
        return "(empty)"
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(str(column) for column in columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _idx, row in df.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, (float, np.floating)):
                values.append(format(float(value), floatfmt) if np.isfinite(value) else str(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_doc(
    collapse_sets: dict[str, set[int]],
    intersection: set[int],
    union: set[int],
    runs: pd.DataFrame,
    summary: pd.DataFrame,
    verdict: str,
) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    sets_df = pd.DataFrame(
        [
            {"set": "C3", "runs": ", ".join(map(str, sorted(collapse_sets["block_3"])))},
            {"set": "C5", "runs": ", ".join(map(str, sorted(collapse_sets["block_5"])))},
            {"set": "C10", "runs": ", ".join(map(str, sorted(collapse_sets["block_10"])))},
            {"set": "Intersection", "runs": ", ".join(map(str, sorted(intersection)))},
            {"set": "Union", "runs": ", ".join(map(str, sorted(union)))},
        ]
    )
    persistence = runs["collapse_class"].value_counts().rename_axis("class").reset_index(name="count")
    baseline_cols = [
        "collapse_class",
        "baseline_locked_fraction",
        "baseline_duration",
        "is_no_replacement",
        "is_horizon_overlap",
    ]
    text = f"""# ES-v3.3b Collapse Cluster Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Collapse sets

{_markdown_table(sets_df)}

## Persistence

{_markdown_table(persistence)}

## Artifact overlap

{_markdown_table(summary.loc[summary["metric"].isin(["overlap_no_replacement", "overlap_no_replacement_jaccard", "overlap_horizon", "overlap_horizon_jaccard"])])}

## Baseline comparison

{_markdown_table(runs[baseline_cols].groupby("collapse_class", dropna=False).agg(["mean", "median"]).reset_index())}

## Key question

Fixed cluster?

or

attack dependent?

## Verdict

{verdict}

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

EL-1 exploratory only
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.3b Collapse Cluster Audit ===")
    print("Status: EL-1 exploratory")

    quality = _load_quality()
    csets = _collapse_sets(quality)
    intersection = set.intersection(*(csets[mode] for mode in MODES)) if MODES else set()
    union = set.union(*(csets[mode] for mode in MODES)) if MODES else set()
    fixed_fraction = len(intersection) / len(union) if union else 0.0

    no_replacement = _optional_no_replacement()
    horizon = _optional_horizon_overlap()
    baseline = _baseline_by_run()
    runs = _build_runs_table(quality, csets, intersection, union, no_replacement, horizon, baseline)
    summary = _summary_rows(runs, union, intersection, no_replacement, horizon)
    verdict = _verdict(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(csets, intersection, union, runs, summary, verdict)

    print("\nCollapse sets:")
    for mode in MODES:
        print(f"{mode}: {sorted(csets[mode])}")
    print(f"intersection_all: {sorted(intersection)}")
    print(f"union_all: {sorted(union)}")
    print(f"fixed_fraction = {fixed_fraction:.6f}")

    print("\nPersistence counts:")
    print(runs["collapse_class"].value_counts().to_string())

    print("\nArtifact overlap:")
    print(summary.loc[summary["metric"].isin(["overlap_no_replacement", "overlap_no_replacement_jaccard", "overlap_horizon", "overlap_horizon_jaccard"])].to_string(index=False))

    print("\nBaseline comparison:")
    collapse_stats = _baseline_stats(runs, runs["is_collapse_union"])
    noncollapse_stats = _baseline_stats(runs, ~runs["is_collapse_union"])
    print(f"collapse mean = {collapse_stats['mean']:.6f}, median = {collapse_stats['median']:.6f}, p25 = {collapse_stats['p25']:.6f}, p75 = {collapse_stats['p75']:.6f}")
    print(f"non-collapse mean = {noncollapse_stats['mean']:.6f}, median = {noncollapse_stats['median']:.6f}, p25 = {noncollapse_stats['p25']:.6f}, p75 = {noncollapse_stats['p75']:.6f}")

    print(f"\nFinal verdict: {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print("\nBoundary: EL-1 exploratory only. No detector change, taxonomy update, industrial interpretation, or early-warning claim.")


if __name__ == "__main__":
    main()
