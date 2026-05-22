"""ES-v3.3a Recovery Quality Audit.

Status: EL-1 exploratory.

Evaluates lock quality after relock occurs, using only the recovery region
from relock_window to trace end. This avoids baseline-duration normalization
and horizon artifacts. Detector logic remains unchanged: ES-v2 hard lock.
No soft lock, TE, absorb_score, transition matrix, load proxy, mixed
disturbance, marine transfer, taxonomy update, industrial interpretation, or
early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"
RECOVERY_RUNS = CSV_DIR / "es_v3_recovery_runs.csv"
RECOVERY_SUMMARY = CSV_DIR / "es_v3_recovery_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_recovery_quality_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_recovery_quality_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_recovery_quality.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
MODES = ["block_3", "block_5", "block_10"]
SEED = 7


def _load_trace() -> pd.DataFrame:
    df = pd.read_csv(F13_TRACE)
    missing = [column for column in TRACE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{F13_TRACE} missing required columns: {missing}")
    df = df[TRACE_COLUMNS].copy()
    found = set(df["fault"].astype(str).unique())
    if found != {"F13"}:
        raise ValueError(f"{F13_TRACE} expected F13, found {sorted(found)}")
    return df


def _load_recovery_runs() -> pd.DataFrame:
    df = pd.read_csv(RECOVERY_RUNS)
    required = [
        "run_id",
        "mode",
        "attack_start_window",
        "attack_end_window",
        "relock_status",
        "relock_window",
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{RECOVERY_RUNS} missing required columns: {missing}")
    return df.loc[(df["mode"].isin(MODES)) & (df["relock_status"] == "relocked")].copy()


def _apply_attack(group: pd.DataFrame, attack_start: int, attack_end: int) -> pd.DataFrame:
    modified = group.copy()
    mask = (modified["window_index"] >= attack_start) & (modified["window_index"] <= attack_end)
    modified.loc[mask, "dominant_pair"] = "__ATTACK_NON_TARGET__"
    return modified


def _states(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    run_length = 0
    for row in df.sort_values("window_index").itertuples(index=False):
        if str(row.dominant_pair) == TARGET_PAIR:
            run_length += 1
        else:
            run_length = 0
        if run_length < 3:
            state = "idle"
            state_rank = 0
        elif run_length < 5:
            state = "candidate"
            state_rank = 1
        elif run_length < 10:
            state = "persistent"
            state_rank = 2
        else:
            state = "locked"
            state_rank = 3
        rows.append(
            {
                "window_index": int(row.window_index),
                "sample_time": int(row.sample_time),
                "run_length": int(run_length),
                "state": state,
                "state_rank": state_rank,
            }
        )
    return pd.DataFrame(rows)


def _max_locked_duration(recovery: pd.DataFrame) -> int:
    current = 0
    durations: list[int] = []
    for is_locked in (recovery["state"] == "locked").tolist():
        if is_locked:
            current += 1
        elif current:
            durations.append(current)
            current = 0
    if current:
        durations.append(current)
    return int(max(durations)) if durations else 0


def _quality_class(score: float) -> str:
    if score > 0.70:
        return "stable"
    if score >= 0.30:
        return "fragile"
    return "collapse"


def _evaluate(trace: pd.DataFrame, recovery_runs: pd.DataFrame) -> pd.DataFrame:
    # Seed retained for reproducibility policy; replay is deterministic.
    _rng = np.random.default_rng(SEED)
    rows = []
    trace_by_run = {
        int(run_id): group.sort_values("window_index").reset_index(drop=True)
        for run_id, group in trace.groupby("run_id", sort=True)
    }
    for rec in recovery_runs.itertuples(index=False):
        run_id = int(rec.run_id)
        group = trace_by_run[run_id]
        modified = _apply_attack(group, int(rec.attack_start_window), int(rec.attack_end_window))
        state_df = _states(modified)
        recovery = state_df.loc[state_df["window_index"] >= int(rec.relock_window)].copy()
        n_recovery = int(len(recovery))
        if n_recovery == 0:
            locked_fraction = np.nan
            drop_rate = np.nan
            max_duration = 0
            score = np.nan
            quality = "collapse"
        else:
            locked_windows = int((recovery["state"] == "locked").sum())
            persistent_or_locked = int((recovery["state_rank"] >= 2).sum())
            # persistent_or_locked retained as an explicit computation for audit traceability.
            _ = persistent_or_locked
            locked_fraction = locked_windows / n_recovery
            drop_rate = int((recovery["state"] != "locked").sum()) / n_recovery
            max_duration = _max_locked_duration(recovery)
            score = locked_fraction * (1.0 - drop_rate)
            quality = _quality_class(score)
        rows.append(
            {
                "run_id": run_id,
                "mode": str(rec.mode),
                "relock_window": int(rec.relock_window),
                "n_recovery_windows": n_recovery,
                "post_relock_locked_fraction": float(locked_fraction),
                "secondary_lock_drop_rate": float(drop_rate),
                "post_relock_max_duration": int(max_duration),
                "recovery_quality_score": float(score),
                "quality_class": quality,
            }
        )
    return pd.DataFrame(rows)


def _status(score: float) -> str:
    if score > 0.70:
        return "ROBUST"
    if score >= 0.30:
        return "DEGRADED"
    return "COLLAPSED"


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode in MODES:
        group = runs.loc[runs["mode"] == mode]
        n = int(len(group))
        mean_score = float(group["recovery_quality_score"].mean()) if n else np.nan
        rows.append(
            {
                "mode": mode,
                "n_relocked": n,
                "mean_locked_fraction": float(group["post_relock_locked_fraction"].mean()) if n else np.nan,
                "mean_drop_rate": float(group["secondary_lock_drop_rate"].mean()) if n else np.nan,
                "mean_post_duration": float(group["post_relock_max_duration"].mean()) if n else np.nan,
                "mean_quality_score": mean_score,
                "stable_fraction": float((group["quality_class"] == "stable").mean()) if n else np.nan,
                "fragile_fraction": float((group["quality_class"] == "fragile").mean()) if n else np.nan,
                "collapse_fraction": float((group["quality_class"] == "collapse").mean()) if n else np.nan,
                "status": _status(mean_score) if np.isfinite(mean_score) else "COLLAPSED",
            }
        )
    return pd.DataFrame(rows)


def _load_reference() -> pd.DataFrame | None:
    if not RECOVERY_SUMMARY.exists():
        return None
    ref = pd.read_csv(RECOVERY_SUMMARY)
    keep = ["mode", "relock_rate", "median_relock_time_samples", "status"]
    missing = [column for column in keep if column not in ref.columns]
    if missing:
        return None
    return ref.loc[ref["mode"].isin(MODES), keep].copy()


def _final_verdict(summary: pd.DataFrame) -> str:
    if (summary["status"] == "ROBUST").all():
        return "ROBUST"
    if (summary["status"] == "COLLAPSED").any():
        return "COLLAPSED"
    return "DEGRADED"


def _markdown_table(df: pd.DataFrame | None, floatfmt: str = ".6f") -> str:
    if df is None or df.empty:
        return "(not available)"
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


def _write_doc(summary: pd.DataFrame, reference: pd.DataFrame | None, verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""# ES-v3.3a Recovery Quality Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Recovery region:

relock_window

↓

trace_end

No baseline normalization

No duration ratio

No horizon correction

Detector:

ES-v2 hard lock

## Metrics

post_relock_locked_fraction

secondary_lock_drop_rate

post_relock_max_duration

recovery_quality_score

## Results

{_markdown_table(summary)}

## Recovery classes

stable

fragile

collapse

## ES-v3.2c reference

{_markdown_table(reference)}

## Key question

Does recovery preserve lock quality?

## Interpretation

Recovery existence

and

Recovery quality

are independent

## Verdict

{verdict}

## Restrictions

No soft lock

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.3a Recovery Quality Audit ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock")

    trace = _load_trace()
    recovery_runs = _load_recovery_runs()
    runs = _evaluate(trace, recovery_runs)
    summary = _summary(runs)
    reference = _load_reference()
    verdict = _final_verdict(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, reference, verdict)

    print("\nRecovery quality summary:")
    print(summary.to_string(index=False))

    print("\nES-v3.2c reference:")
    if reference is None:
        print("(reference skipped)")
    else:
        print(reference.to_string(index=False))

    print(f"\nFinal verdict: {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print(
        "\nBoundary: EL-1 exploratory only. No TE, absorb_score, transition matrix, "
        "mixed disturbance, taxonomy update, industrial interpretation, or early-warning claim."
    )


if __name__ == "__main__":
    main()
