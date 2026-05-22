"""ES-v3.4a Recovery Stress Separation.

Status: EL-1 exploratory.

Expands contiguous maintenance stress and compares recovery response between
Population A and the fixed Population B collapse cluster. This characterizes
stress response only; it does not prove statistical separation. No detector
modification, soft lock, mixed disturbance, marine transfer, taxonomy update,
industrial interpretation, or early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

PROFILE_RUNS = CSV_DIR / "es_v3_collapse_profile_runs.csv"
F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"
QUALITY_REFERENCE = CSV_DIR / "es_v3_recovery_quality_summary.csv"
BOUNDARY_REFERENCE = CSV_DIR / "es_v3_recovery_boundary_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_recovery_stress_split_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_recovery_stress_split_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_recovery_stress_split.md"

TARGET_PAIR = "XMEAS7-XMEAS11"
FAULT_INJECTION_SAMPLE = 160
POPULATION_B = {15, 22, 23, 24, 30, 48}
ATTACK_MODES = [("block_3", 3), ("block_5", 5), ("block_10", 10), ("block_15", 15), ("block_20", 20)]


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    profile = pd.read_csv(PROFILE_RUNS)
    trace = pd.read_csv(F13_TRACE)
    missing_profile = [column for column in ["run_id"] if column not in profile.columns]
    missing_trace = [column for column in ["run_id", "window_index", "sample_time", "dominant_pair"] if column not in trace.columns]
    if missing_profile:
        raise ValueError(f"{PROFILE_RUNS} missing required columns: {missing_profile}")
    if missing_trace:
        raise ValueError(f"{F13_TRACE} missing required columns: {missing_trace}")
    return profile, trace


def _run_lengths(df: pd.DataFrame) -> pd.DataFrame:
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


def _trigger(df: pd.DataFrame) -> dict[str, object]:
    states = _run_lengths(df)
    hit = states.loc[states["run_length"] >= 5]
    if hit.empty:
        return {"trigger_window": np.nan, "trigger_sample": np.nan, "status": "miss"}
    row = hit.iloc[0]
    return {"trigger_window": int(row["window_index"]), "trigger_sample": int(row["sample_time"]), "status": "triggered"}


def _replacement_pair(group: pd.DataFrame) -> str:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return "__ATTACK_NON_TARGET__"
    return str(non_target.value_counts().idxmax())


def _post_target_segments(group: pd.DataFrame, trigger_window: int) -> list[list[int]]:
    post = group.loc[
        (group["window_index"] >= int(trigger_window) + 1)
        & (group["dominant_pair"] == TARGET_PAIR)
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
    segment_start = int(segment[0])
    segment_length = len(segment)
    actual_block = min(requested_block, segment_length)
    center_start = segment_start + (segment_length - actual_block) // 2
    return list(range(center_start, center_start + actual_block))


def _apply_attack(group: pd.DataFrame, windows: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if windows:
        modified.loc[modified["window_index"].isin(windows), "dominant_pair"] = replacement
    return modified


def _quality_from_relock(modified: pd.DataFrame, relock_window: int | float) -> dict[str, object]:
    if pd.isna(relock_window):
        return {
            "quality_score": 0.0,
            "locked_fraction": 0.0,
            "drop_rate": 1.0,
            "quality_class": "collapse",
        }
    states = _run_lengths(modified)
    recovery = states.loc[states["window_index"] >= int(relock_window)].copy()
    if recovery.empty:
        return {
            "quality_score": 0.0,
            "locked_fraction": 0.0,
            "drop_rate": 1.0,
            "quality_class": "collapse",
        }
    locked_fraction = float((recovery["state"] == "locked").mean())
    drop_rate = float((recovery["state"] != "locked").mean())
    score = locked_fraction * (1.0 - drop_rate)
    if score > 0.70:
        quality_class = "stable"
    elif score >= 0.30:
        quality_class = "fragile"
    else:
        quality_class = "collapse"
    return {
        "quality_score": float(score),
        "locked_fraction": locked_fraction,
        "drop_rate": drop_rate,
        "quality_class": quality_class,
    }


def _evaluate(profile: pd.DataFrame, trace: pd.DataFrame) -> pd.DataFrame:
    trace_by_run = {
        int(run_id): group.sort_values("window_index").reset_index(drop=True)
        for run_id, group in trace.groupby("run_id", sort=True)
    }
    run_ids = sorted(int(run_id) for run_id in profile["run_id"].unique())
    rows = []
    for run_id in run_ids:
        group = trace_by_run[run_id]
        population = "B" if run_id in POPULATION_B else "A"
        base_trigger = _trigger(group)
        for attack_mode, requested_block in ATTACK_MODES:
            if base_trigger["status"] != "triggered":
                rows.append(_run_row(run_id, population, attack_mode, 0, np.nan, np.nan, 0.0, 0.0, 1.0, "collapse"))
                continue
            windows = _attack_windows(group, int(base_trigger["trigger_window"]), requested_block)
            replacement = _replacement_pair(group)
            modified = _apply_attack(group, windows, replacement)
            states = _run_lengths(modified)
            recovery_start = (max(windows) + 1) if windows else np.nan
            relock_rows = (
                states.loc[(states["window_index"] >= int(recovery_start)) & (states["run_length"] >= 10)]
                if pd.notna(recovery_start)
                else pd.DataFrame()
            )
            if relock_rows.empty:
                relock_window = np.nan
                relock_time = np.nan
                relock_rate = 0.0
            else:
                relock_window = int(relock_rows.iloc[0]["window_index"])
                relock_time = relock_window - int(max(windows))
                relock_rate = 1.0
            quality = _quality_from_relock(modified, relock_window)
            rows.append(
                _run_row(
                    run_id,
                    population,
                    attack_mode,
                    relock_rate,
                    relock_time,
                    relock_window,
                    quality["quality_score"],
                    quality["locked_fraction"],
                    quality["drop_rate"],
                    quality["quality_class"],
                )
            )
    return pd.DataFrame(rows)


def _run_row(
    run_id: int,
    population: str,
    attack_mode: str,
    relock_rate: float,
    relock_time: float,
    relock_window: float,
    quality_score: float,
    locked_fraction: float,
    drop_rate: float,
    quality_class: str,
) -> dict[str, object]:
    return {
        "run_id": int(run_id),
        "population": population,
        "attack_mode": attack_mode,
        "relock_rate": float(relock_rate),
        "relock_time": relock_time,
        "quality_score": float(quality_score),
        "locked_fraction": float(locked_fraction),
        "drop_rate": float(drop_rate),
        "quality_class": quality_class,
    }


def _labels_for_mode(mode_summary: pd.DataFrame) -> str:
    row_a = mode_summary.loc[mode_summary["population"] == "A"].iloc[0]
    row_b = mode_summary.loc[mode_summary["population"] == "B"].iloc[0]
    delta_quality = float(row_a["mean_quality"] - row_b["mean_quality"])
    labels = []
    if delta_quality > 0.30:
        labels.append("persistent_separation")
    elif delta_quality >= 0.10:
        labels.append("weak_separation")
    else:
        labels.append("merged")
    return ";".join(labels)


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for attack_mode in [mode for mode, _ in ATTACK_MODES]:
        mode_group = runs.loc[runs["attack_mode"] == attack_mode]
        pop_rows = []
        for population in ["A", "B"]:
            group = mode_group.loc[mode_group["population"] == population]
            pop_rows.append(
                {
                    "population": population,
                    "attack_mode": attack_mode,
                    "mean_quality": float(group["quality_score"].mean()),
                    "mean_locked_fraction": float(group["locked_fraction"].mean()),
                    "mean_drop_rate": float(group["drop_rate"].mean()),
                    "stable_fraction": float((group["quality_class"] == "stable").mean()),
                    "fragile_fraction": float((group["quality_class"] == "fragile").mean()),
                    "collapse_fraction": float((group["quality_class"] == "collapse").mean()),
                    "mean_relock": float(group["relock_rate"].mean()),
                }
            )
        mode_summary = pd.DataFrame(pop_rows)
        quality_a = float(mode_summary.loc[mode_summary["population"] == "A", "mean_quality"].iloc[0])
        quality_b = float(mode_summary.loc[mode_summary["population"] == "B", "mean_quality"].iloc[0])
        relock_a = float(mode_summary.loc[mode_summary["population"] == "A", "mean_relock"].iloc[0])
        relock_b = float(mode_summary.loc[mode_summary["population"] == "B", "mean_relock"].iloc[0])
        labels = _labels_for_mode(mode_summary)
        for row in pop_rows:
            row["delta_quality"] = quality_a - quality_b
            row["delta_relock"] = relock_a - relock_b
            row["labels"] = labels
            rows.append(row)
    return pd.DataFrame(rows)


def _trend_labels(summary: pd.DataFrame) -> list[str]:
    a = summary.loc[summary["population"] == "A"].sort_values("attack_mode")
    b = summary.loc[summary["population"] == "B"].sort_values("attack_mode")
    labels = []
    if len(a) >= 2 and float(a["mean_quality"].iloc[-1]) < float(a["mean_quality"].iloc[0]):
        labels.append("A_degradation")
    if float(b["mean_quality"].max()) < 0.30 and float(b["mean_quality"].std(ddof=0)) <= 0.10:
        labels.append("B_floor_effect")
    if (summary["delta_quality"] > 0.30).all():
        labels.append("persistent_separation")
    if not labels:
        labels.append("inconclusive")
    return labels


def _load_optional_refs() -> str:
    lines = []
    if QUALITY_REFERENCE.exists():
        lines.append("es_v3_recovery_quality_summary.csv loaded")
    if BOUNDARY_REFERENCE.exists():
        lines.append("es_v3_recovery_boundary_summary.csv loaded")
    return "\n".join(lines) if lines else "(not available)"


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


def _write_doc(summary: pd.DataFrame, final_verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""# ES-v3.4a Recovery Stress Separation

Status: EL-1 exploratory
Date: 2026-05-23

## Populations

A:

44 runs

stable recovery

B:

6 runs

collapse cluster

Population B:

small sample

n = 6

Indicators only

Not statistically validated

## Stress levels

block_3

block_5

block_10

block_15

block_20

## Results

{_markdown_table(summary)}

## Interpretation

Population B:

small sample

n = 6

Indicators only

Not statistically validated

Expected pattern:

B may remain near recovery floor

A may degrade gradually

## Labels

persistent_separation

weak_separation

merged

A_degradation

B_floor_effect

## Key question

Stress response split?

## Optional references

{_load_optional_refs()}

## Final verdict

{final_verdict}

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

No frozen modification

EL-1 exploratory only
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.4a Recovery Stress Separation ===")
    print("Status: EL-1 exploratory")
    print("Population B n=6; labels are exploratory indicators only.")

    profile, trace = _load_inputs()
    runs = _evaluate(profile, trace)
    summary = _summary(runs)
    trend = _trend_labels(summary)
    final_verdict = ";".join(trend)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, final_verdict)

    print("\nStress response:")
    table = summary.pivot(index="attack_mode", columns="population", values=["mean_quality", "mean_relock"])
    print(table.to_string())

    print("\nPer attack mode:")
    for attack_mode in [mode for mode, _ in ATTACK_MODES]:
        mode = summary.loc[summary["attack_mode"] == attack_mode]
        a = mode.loc[mode["population"] == "A"].iloc[0]
        b = mode.loc[mode["population"] == "B"].iloc[0]
        print(
            f"{attack_mode}: quality_A={a.mean_quality:.6f}, quality_B={b.mean_quality:.6f}, "
            f"delta_quality={a.delta_quality:.6f}, relock_A={a.mean_relock:.6f}, relock_B={b.mean_relock:.6f}, labels={a.labels}"
        )

    print("\nTrend summary:")
    print(final_verdict)

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print("\nBoundary: EL-1 exploratory only. No detector change, taxonomy update, industrial interpretation, or early-warning claim.")


if __name__ == "__main__":
    main()
