"""ES-v3.4b Floor Mechanism Audit.

Status: EL-1 exploratory.

Recomputes per-window state tracking from dominant_pair_trace_F13.csv using
the same contiguous attack, relock, and recovery-quality logic as ES-v3.1c,
ES-v3.2c, and ES-v3.3a. The stress split output is used only to identify
run/mode scope and population membership context. No detector change, soft
lock, mixed disturbance, marine transfer, taxonomy update, industrial
interpretation, or early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

STRESS_RUNS = CSV_DIR / "es_v3_recovery_stress_split_runs.csv"
F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_floor_mechanism_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_floor_mechanism_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_floor_mechanism.md"

TARGET_PAIR = "XMEAS7-XMEAS11"
POPULATION_B = {15, 22, 23, 24, 30, 48}
ATTACK_BLOCKS = {
    "block_3": 3,
    "block_5": 5,
    "block_10": 10,
    "block_15": 15,
    "block_20": 20,
}


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    stress = pd.read_csv(STRESS_RUNS)
    trace = pd.read_csv(F13_TRACE)
    missing_stress = [column for column in ["run_id", "attack_mode"] if column not in stress.columns]
    missing_trace = [column for column in ["run_id", "window_index", "sample_time", "dominant_pair"] if column not in trace.columns]
    if missing_stress:
        raise ValueError(f"{STRESS_RUNS} missing required columns: {missing_stress}")
    if missing_trace:
        raise ValueError(f"{F13_TRACE} missing required columns: {missing_trace}")
    stress = stress.loc[stress["attack_mode"].isin(ATTACK_BLOCKS)].copy()
    return stress, trace


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
            rank = 0
        elif run_length < 5:
            state = "candidate"
            rank = 1
        elif run_length < 10:
            state = "persistent"
            rank = 2
        else:
            state = "locked"
            rank = 3
        rows.append(
            {
                "window_index": int(row.window_index),
                "sample_time": int(row.sample_time),
                "run_length": int(run_length),
                "state": state,
                "state_rank": rank,
            }
        )
    return pd.DataFrame(rows)


def _trigger_window(group: pd.DataFrame) -> int | None:
    states = _states(group)
    hit = states.loc[states["run_length"] >= 5]
    if hit.empty:
        return None
    return int(hit.iloc[0]["window_index"])


def _post_target_segments(group: pd.DataFrame, trigger_window: int) -> list[list[int]]:
    post = group.loc[
        (group["window_index"] >= trigger_window + 1) & (group["dominant_pair"] == TARGET_PAIR)
    ].sort_values("window_index")
    windows = post["window_index"].astype(int).tolist()
    if not windows:
        return []
    segments = [[windows[0]]]
    for window in windows[1:]:
        if window == segments[-1][-1] + 1:
            segments[-1].append(window)
        else:
            segments.append([window])
    return segments


def _attack_windows(group: pd.DataFrame, trigger_window: int, requested_block: int) -> list[int]:
    segments = _post_target_segments(group, trigger_window)
    if not segments:
        return []
    segment = max(segments, key=len)
    actual_block = min(requested_block, len(segment))
    center_start = int(segment[0]) + (len(segment) - actual_block) // 2
    return list(range(center_start, center_start + actual_block))


def _replacement_pair(group: pd.DataFrame) -> str:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return "__ATTACK_NON_TARGET__"
    return str(non_target.value_counts().idxmax())


def _apply_attack(group: pd.DataFrame, windows: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if windows:
        modified.loc[modified["window_index"].isin(windows), "dominant_pair"] = replacement
    return modified


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


def _drop_count(recovery: pd.DataFrame) -> int:
    states = recovery["state"].tolist()
    count = 0
    for prev, curr in zip(states, states[1:]):
        if prev == "locked" and curr != "locked":
            count += 1
    return int(count)


def _evaluate_row(group: pd.DataFrame, attack_mode: str) -> dict[str, object]:
    requested_block = ATTACK_BLOCKS[attack_mode]
    trigger_window = _trigger_window(group)
    if trigger_window is None:
        return _empty_metrics("no_trigger")
    windows = _attack_windows(group, trigger_window, requested_block)
    if not windows:
        return _empty_metrics("no_attack_window")
    modified = _apply_attack(group, windows, _replacement_pair(group))
    attack_end = max(windows)
    state_df = _states(modified)
    relock_hits = state_df.loc[(state_df["window_index"] >= attack_end + 1) & (state_df["run_length"] >= 10)]
    if relock_hits.empty:
        return _empty_metrics("no_relock")
    relock_window = int(relock_hits.iloc[0]["window_index"])
    recovery = state_df.loc[state_df["window_index"] >= relock_window].copy()
    remaining = int(len(recovery))
    first_drop = recovery.loc[(recovery["window_index"] > relock_window) & (recovery["state"] != "locked")]
    if first_drop.empty:
        first_drop_window = np.nan
        latency = remaining
        stable_to_end = True
    else:
        first_drop_window = int(first_drop.iloc[0]["window_index"])
        latency = first_drop_window - relock_window
        stable_to_end = False
    drop_position = float(latency / remaining) if remaining else np.nan
    post_duration = _max_locked_duration(recovery)
    secondary_drop_count = _drop_count(recovery)
    secondary_drop_rate = float(secondary_drop_count / remaining) if remaining else np.nan
    return {
        "relock_window": relock_window,
        "first_drop_window": first_drop_window,
        "relock_to_drop_latency": int(latency),
        "drop_position_fraction": drop_position,
        "post_relock_max_duration": post_duration,
        "secondary_drop_count": secondary_drop_count,
        "secondary_drop_rate": secondary_drop_rate,
        "stable_to_end": stable_to_end,
        "status": "evaluated",
    }


def _empty_metrics(status: str) -> dict[str, object]:
    return {
        "relock_window": np.nan,
        "first_drop_window": np.nan,
        "relock_to_drop_latency": np.nan,
        "drop_position_fraction": np.nan,
        "post_relock_max_duration": 0,
        "secondary_drop_count": np.nan,
        "secondary_drop_rate": np.nan,
        "stable_to_end": False,
        "status": status,
    }


def _labels(row: pd.Series, a_p75_drop_count: float, quality_low: bool) -> str:
    labels = []
    latency = row["drop_position_fraction"]
    drop_rate = row["secondary_drop_rate"]
    drop_count = row["secondary_drop_count"]
    if pd.notna(latency) and latency > 0.70 and pd.notna(drop_rate) and drop_rate < 0.10:
        labels.append("stable_floor")
    if pd.notna(latency) and latency < 0.30:
        labels.append("early_break")
    if pd.notna(drop_count) and drop_count > a_p75_drop_count:
        labels.append("oscillatory")
    if quality_low and pd.notna(latency) and latency < 0.30:
        labels.append("persistent_floor")
    return ";".join(labels) if labels else "none"


def _evaluate(stress: pd.DataFrame, trace: pd.DataFrame) -> pd.DataFrame:
    trace_by_run = {
        int(run_id): group.sort_values("window_index").reset_index(drop=True)
        for run_id, group in trace.groupby("run_id", sort=True)
    }
    rows = []
    pairs = stress[["run_id", "attack_mode", "quality_score"]].drop_duplicates()
    for item in pairs.itertuples(index=False):
        run_id = int(item.run_id)
        attack_mode = str(item.attack_mode)
        population = "B" if run_id in POPULATION_B else "A"
        metrics = _evaluate_row(trace_by_run[run_id], attack_mode)
        rows.append(
            {
                "run_id": run_id,
                "population": population,
                "attack_mode": attack_mode,
                **metrics,
                "_quality_score": float(item.quality_score),
            }
        )
    out = pd.DataFrame(rows)
    a_p75_drop = out.loc[out["population"] == "A", "secondary_drop_count"].quantile(0.75)
    out["labels"] = [
        _labels(row, a_p75_drop, bool(row["_quality_score"] < 0.30))
        for _idx, row in out.iterrows()
    ]
    return out.drop(columns=["_quality_score"])


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("latency", "relock_to_drop_latency"),
        ("drop_position", "drop_position_fraction"),
        ("post_duration", "post_relock_max_duration"),
        ("drop_count", "secondary_drop_count"),
        ("drop_rate", "secondary_drop_rate"),
    ]
    rows = []
    for metric, column in metrics:
        a = runs.loc[runs["population"] == "A", column].dropna()
        b = runs.loc[runs["population"] == "B", column].dropna()
        a_mean = float(a.mean()) if not a.empty else np.nan
        b_mean = float(b.mean()) if not b.empty else np.nan
        rows.append(
            {
                "metric": metric,
                "A_mean": a_mean,
                "B_mean": b_mean,
                "delta": a_mean - b_mean if np.isfinite(a_mean) and np.isfinite(b_mean) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _verdict(summary: pd.DataFrame) -> str:
    values = {row.metric: row for row in summary.itertuples(index=False)}
    latency_delta = float(values["latency"].delta)
    drop_rate_delta = float(values["drop_rate"].delta)
    duration_delta = float(values["post_duration"].delta)
    parts = []
    if latency_delta > 0:
        parts.append("B_drops_earlier")
    if drop_rate_delta < 0:
        parts.append("B_drops_more")
    if duration_delta > 0:
        parts.append("B_shorter_persistence")
    return ";".join(parts) if parts else "inconclusive"


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
    label_counts = runs["labels"].str.get_dummies(sep=";").sum().reset_index()
    label_counts.columns = ["label", "count"]
    pop_summary = runs.groupby("population", dropna=False)[
        ["relock_to_drop_latency", "drop_position_fraction", "post_relock_max_duration", "secondary_drop_rate"]
    ].mean().reset_index()
    text = f"""# ES-v3.4b Floor Mechanism Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Question

Why does Population B relock

but remain near quality floor?

## Metrics

relock_to_drop_latency

drop_position_fraction

post_relock_max_duration

secondary_drop_rate

## Population comparison

{_markdown_table(pop_summary)}

A

vs

B

## Labels

{_markdown_table(label_counts)}

stable_floor

early_break

oscillatory

persistent_floor

## Interpretation

Recovery existence

and

Recovery persistence

are separate properties

Population B:

small sample

n = 6

Indicators only

## Summary

{_markdown_table(summary)}

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
    print("=== ES-v3.4b Floor Mechanism Audit ===")
    print("Status: EL-1 exploratory")
    print("Recomputing per-window state from dominant_pair_trace_F13.csv.")

    stress, trace = _load_inputs()
    runs = _evaluate(stress, trace)
    summary = _summary(runs)
    verdict = _verdict(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs[
        [
            "run_id",
            "population",
            "attack_mode",
            "relock_window",
            "first_drop_window",
            "relock_to_drop_latency",
            "drop_position_fraction",
            "post_relock_max_duration",
            "secondary_drop_count",
            "secondary_drop_rate",
            "labels",
        ]
    ].to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(runs, summary, verdict)

    pop = runs.groupby("population")[["relock_to_drop_latency", "secondary_drop_rate", "post_relock_max_duration"]].mean()
    print("\nPopulation means:")
    print(pop.to_string())

    a = pop.loc["A"]
    b = pop.loc["B"]
    print("\nKey metrics:")
    print(f"latency_A = {a.relock_to_drop_latency:.6f}")
    print(f"latency_B = {b.relock_to_drop_latency:.6f}")
    print(f"drop_rate_A = {a.secondary_drop_rate:.6f}")
    print(f"drop_rate_B = {b.secondary_drop_rate:.6f}")
    print(f"duration_A = {a.post_relock_max_duration:.6f}")
    print(f"duration_B = {b.post_relock_max_duration:.6f}")

    print("\nLabel counts:")
    print(runs["labels"].str.get_dummies(sep=";").sum().to_string())

    print(f"\nFinal verdict: {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print("\nBoundary: EL-1 exploratory only. No detector change, taxonomy update, industrial interpretation, or early-warning claim.")


if __name__ == "__main__":
    main()
