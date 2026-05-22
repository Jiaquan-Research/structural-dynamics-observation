"""ES-v3.3c Collapse Run Profile Audit.

Status: EL-1 exploratory.

Profiles the fixed ES-v3.3b collapse cluster against non-collapse runs across
baseline lock structure, trigger geometry, recovery quality, and optional
recovery-boundary horizon information. Analysis only: no detector modification,
no new attack, no soft lock, mixed disturbance, marine transfer, taxonomy
update, industrial interpretation, or early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

CLUSTER_RUNS = CSV_DIR / "es_v3_collapse_cluster_runs.csv"
QUALITY_RUNS = CSV_DIR / "es_v3_recovery_quality_runs.csv"
RECOVERY_RUNS = CSV_DIR / "es_v3_recovery_runs.csv"
BOUNDARY_RUNS = CSV_DIR / "es_v3_recovery_boundary_runs.csv"
F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_collapse_profile_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_collapse_profile_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_collapse_profile.md"

TARGET_PAIR = "XMEAS7-XMEAS11"
FAULT_INJECTION_SAMPLE = 160
COLLAPSE_RUNS = {15, 22, 23, 24, 30, 48}


def _load_required(path: Path, required: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    return df


def _baseline_and_trigger() -> pd.DataFrame:
    trace = _load_required(F13_TRACE, ["run_id", "window_index", "sample_time", "dominant_pair"])
    rows = []
    for run_id, group in trace.groupby("run_id", sort=True):
        group = group.sort_values("window_index")
        run_length = 0
        locked_flags: list[bool] = []
        durations: list[int] = []
        current = 0
        trigger_window = np.nan
        trigger_sample = np.nan
        target_count = 0
        for row in group.itertuples(index=False):
            is_target = str(row.dominant_pair) == TARGET_PAIR
            target_count += int(is_target)
            if is_target:
                run_length += 1
            else:
                run_length = 0
            if run_length >= 5 and pd.isna(trigger_window):
                trigger_window = int(row.window_index)
                trigger_sample = int(row.sample_time)
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
                "baseline_max_duration": int(max(durations)) if durations else 0,
                "n_locked_segments": int(len(durations)),
                "mean_locked_duration": float(np.mean(durations)) if durations else 0.0,
                "target_pair_frequency": float(target_count / len(group)) if len(group) else np.nan,
                "trigger_window": trigger_window,
                "trigger_delay": trigger_sample - FAULT_INJECTION_SAMPLE if pd.notna(trigger_sample) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _quality_profile() -> pd.DataFrame:
    quality = _load_required(
        QUALITY_RUNS,
        [
            "run_id",
            "mode",
            "post_relock_locked_fraction",
            "secondary_lock_drop_rate",
            "post_relock_max_duration",
            "recovery_quality_score",
            "quality_class",
        ],
    )
    rows = []
    for run_id, group in quality.groupby("run_id", sort=True):
        rows.append(
            {
                "run_id": int(run_id),
                "quality_score": float(group["recovery_quality_score"].mean()),
                "mean_locked_fraction_after_relock": float(group["post_relock_locked_fraction"].mean()),
                "drop_rate": float(group["secondary_lock_drop_rate"].mean()),
                "mean_post_duration": float(group["post_relock_max_duration"].mean()),
                "stable_count": int((group["quality_class"] == "stable").sum()),
                "fragile_count": int((group["quality_class"] == "fragile").sum()),
                "collapse_count": int((group["quality_class"] == "collapse").sum()),
            }
        )
    return pd.DataFrame(rows)


def _boundary_profile() -> pd.DataFrame:
    if not BOUNDARY_RUNS.exists():
        return pd.DataFrame(columns=["run_id", "recovery_horizon", "horizon_margin"])
    boundary = pd.read_csv(BOUNDARY_RUNS)
    required = {"run_id", "recovery_horizon", "horizon_margin"}
    if not required.issubset(boundary.columns):
        return pd.DataFrame(columns=["run_id", "recovery_horizon", "horizon_margin"])
    rows = []
    for run_id, group in boundary.groupby("run_id", sort=True):
        rows.append(
            {
                "run_id": int(run_id),
                "recovery_horizon": float(group["recovery_horizon"].mean()),
                "horizon_margin": float(group["horizon_margin"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _label_runs(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    non = out.loc[~out["is_collapse"]]
    thresholds = {
        "baseline_locked_fraction_p25": non["baseline_locked_fraction"].quantile(0.25),
        "trigger_delay_p75": non["trigger_delay"].quantile(0.75),
        "n_locked_segments_p75": non["n_locked_segments"].quantile(0.75),
        "quality_score_p25": non["quality_score"].quantile(0.25),
    }
    labels = []
    for row in out.itertuples(index=False):
        row_labels = []
        if row.baseline_locked_fraction < thresholds["baseline_locked_fraction_p25"]:
            row_labels.append("weak_lock")
        if row.trigger_delay > thresholds["trigger_delay_p75"]:
            row_labels.append("late_trigger")
        if row.n_locked_segments > thresholds["n_locked_segments_p75"]:
            row_labels.append("fragmented")
        if row.quality_score < thresholds["quality_score_p25"]:
            row_labels.append("recovery_fragile")
        labels.append(";".join(row_labels) if row_labels else "none")
    out["labels"] = labels
    return out


def _summary(df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("baseline_locked_fraction", "baseline_locked_fraction"),
        ("baseline_duration", "baseline_max_duration"),
        ("locked_segments", "n_locked_segments"),
        ("target_frequency", "target_pair_frequency"),
        ("trigger_delay", "trigger_delay"),
        ("quality_score", "quality_score"),
        ("drop_rate", "drop_rate"),
        ("horizon_margin", "horizon_margin"),
    ]
    rows = []
    collapse = df.loc[df["is_collapse"]]
    non = df.loc[~df["is_collapse"]]
    for label, column in metrics:
        c_mean = float(collapse[column].mean()) if column in collapse else np.nan
        n_mean = float(non[column].mean()) if column in non else np.nan
        rows.append(
            {
                "metric": label,
                "collapse_mean": c_mean,
                "noncollapse_mean": n_mean,
                "delta": c_mean - n_mean if np.isfinite(c_mean) and np.isfinite(n_mean) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _group_stats(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows = []
    for column in columns:
        for is_collapse, group in df.groupby("is_collapse", sort=False):
            values = group[column].dropna()
            rows.append(
                {
                    "metric": column,
                    "group": "collapse" if is_collapse else "non-collapse",
                    "mean": float(values.mean()) if not values.empty else np.nan,
                    "median": float(values.median()) if not values.empty else np.nan,
                    "p25": float(values.quantile(0.25)) if not values.empty else np.nan,
                    "p75": float(values.quantile(0.75)) if not values.empty else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _verdict(df: pd.DataFrame) -> str:
    collapse = df.loc[df["is_collapse"]]
    if collapse.empty:
        return "mixed mechanism"
    label_counts = collapse["labels"].str.get_dummies(sep=";").sum()
    recovery_fragile = int(label_counts.get("recovery_fragile", 0))
    weak_lock = int(label_counts.get("weak_lock", 0))
    fragmented = int(label_counts.get("fragmented", 0))
    late = int(label_counts.get("late_trigger", 0))
    if weak_lock >= 4 and recovery_fragile >= 4:
        return "population split"
    if max(recovery_fragile, weak_lock, fragmented, late) >= 4:
        return "population split"
    return "mixed mechanism"


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


def _write_doc(runs: pd.DataFrame, summary: pd.DataFrame, verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    baseline_stats = _group_stats(
        runs,
        ["baseline_locked_fraction", "baseline_max_duration", "n_locked_segments", "mean_locked_duration", "target_pair_frequency"],
    )
    trigger_stats = _group_stats(runs, ["trigger_window", "trigger_delay"])
    recovery_stats = _group_stats(runs, ["quality_score", "drop_rate", "mean_post_duration"])
    label_counts = runs.loc[runs["is_collapse"], "labels"].str.get_dummies(sep=";").sum().reset_index()
    label_counts.columns = ["label", "count"]
    text = f"""# ES-v3.3c Collapse Run Profile

Status: EL-1 exploratory
Date: 2026-05-23

## Collapse cluster

15
22
23
24
30
48

## Baseline comparison

{_markdown_table(baseline_stats)}

## Trigger comparison

{_markdown_table(trigger_stats)}

## Recovery comparison

{_markdown_table(recovery_stats)}

## Labels

{_markdown_table(label_counts)}

weak_lock

late_trigger

fragmented

recovery_fragile

Note:

Threshold labels are exploratory only.

Derived from non-collapse quantiles.

Not statistically validated.

## Key question

Why do collapse runs collapse?

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
    print("=== ES-v3.3c Collapse Run Profile Audit ===")
    print("Status: EL-1 exploratory")

    # Loaded to enforce required input presence and retain linkage to ES-v3.3b.
    _load_required(CLUSTER_RUNS, ["run_id", "collapse_class"])
    _load_required(RECOVERY_RUNS, ["run_id", "mode"])

    baseline = _baseline_and_trigger()
    quality = _quality_profile()
    boundary = _boundary_profile()

    runs = baseline.merge(quality, on="run_id", how="left").merge(boundary, on="run_id", how="left")
    runs["is_collapse"] = runs["run_id"].isin(COLLAPSE_RUNS)
    runs = _label_runs(runs)
    summary = _summary(runs)
    verdict = _verdict(runs)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs[
        [
            "run_id",
            "is_collapse",
            "baseline_locked_fraction",
            "baseline_max_duration",
            "n_locked_segments",
            "mean_locked_duration",
            "target_pair_frequency",
            "trigger_window",
            "trigger_delay",
            "quality_score",
            "drop_rate",
            "stable_count",
            "fragile_count",
            "collapse_count",
            "recovery_horizon",
            "horizon_margin",
            "labels",
        ]
    ].to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(runs, summary, verdict)

    collapse_table = runs.loc[runs["is_collapse"], [
        "run_id",
        "baseline_locked_fraction",
        "baseline_max_duration",
        "n_locked_segments",
        "trigger_delay",
        "quality_score",
        "drop_rate",
        "labels",
    ]]
    print("\nCollapse table:")
    print(collapse_table.to_string(index=False))

    print("\nLabel counts:")
    print(runs.loc[runs["is_collapse"], "labels"].str.get_dummies(sep=";").sum().to_string())

    print("\nBaseline comparison:")
    print(_group_stats(runs, ["baseline_locked_fraction", "baseline_max_duration", "n_locked_segments", "target_pair_frequency"]).to_string(index=False))

    print("\nTrigger comparison:")
    print(_group_stats(runs, ["trigger_window", "trigger_delay"]).to_string(index=False))

    print("\nRecovery comparison:")
    print(_group_stats(runs, ["quality_score", "drop_rate", "mean_post_duration"]).to_string(index=False))

    print(f"\nFinal verdict: {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print("\nBoundary: EL-1 exploratory only. No detector change, taxonomy update, industrial interpretation, or early-warning claim.")


if __name__ == "__main__":
    main()
