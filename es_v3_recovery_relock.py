"""ES-v3.2c Recovery / Relock Audit.

Status: EL-1 exploratory.

Tests whether lock state recovers naturally after a temporary contiguous
post-trigger maintenance disturbance. Detector logic remains unchanged:
ES-v2 hard lock k=5. No soft lock, TE, absorb_score, transition matrix,
load proxy, marine transfer, taxonomy update, industrial interpretation,
or early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"
NORMAL_TRACE = CSV_DIR / "dominant_pair_trace_NORMAL.csv"
CONTIGUOUS_SUMMARY = CSV_DIR / "es_v3_contiguous_maintenance_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_recovery_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_recovery_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_recovery_relock.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
MODES: list[tuple[str, int]] = [("block_3", 3), ("block_5", 5), ("block_10", 10)]


def _load_trace(path: Path, condition: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [column for column in TRACE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    df = df[TRACE_COLUMNS].copy()
    found = set(df["fault"].astype(str).unique())
    if found != {condition}:
        raise ValueError(f"{path} expected {condition}, found {sorted(found)}")
    return df


def _run_lengths(df: pd.DataFrame) -> list[dict[str, object]]:
    run_length = 0
    rows = []
    for row in df.sort_values("window_index").itertuples(index=False):
        if str(row.dominant_pair) == TARGET_PAIR:
            run_length += 1
        else:
            run_length = 0
        if run_length < 3:
            state = "idle"
        elif run_length < 5:
            state = "candidate"
        elif run_length < 10:
            state = "persistent"
        else:
            state = "locked"
        rows.append(
            {
                "window_index": int(row.window_index),
                "sample_time": int(row.sample_time),
                "dominant_pair": str(row.dominant_pair),
                "run_length": int(run_length),
                "state": state,
            }
        )
    return rows


def _trigger(df: pd.DataFrame) -> dict[str, object]:
    for row in _run_lengths(df):
        if int(row["run_length"]) >= K:
            sample = int(row["sample_time"])
            return {
                "trigger_window": int(row["window_index"]),
                "trigger_sample": sample,
                "delay": sample - FAULT_INJECTION_SAMPLE,
                "status": "triggered",
            }
    return {
        "trigger_window": np.nan,
        "trigger_sample": np.nan,
        "delay": np.nan,
        "status": "miss",
    }


def _state_metrics(df: pd.DataFrame) -> dict[str, object]:
    states = _run_lengths(df)
    locked_flags = [row["state"] == "locked" for row in states]
    locked_fraction = float(np.mean(locked_flags)) if locked_flags else 0.0
    segments = _locked_segments_from_states(states, min_window=None)
    return {
        "locked_fraction": locked_fraction,
        "max_locked_duration": int(max((seg["duration"] for seg in segments), default=0)),
        "n_locked_segments": int(len(segments)),
    }


def _locked_segments_from_states(
    states: list[dict[str, object]], min_window: int | None
) -> list[dict[str, int]]:
    segments: list[dict[str, int]] = []
    current: list[dict[str, object]] = []
    for row in states:
        if min_window is not None and int(row["window_index"]) < min_window:
            if current:
                segments.append(_segment_record(current))
                current = []
            continue
        if row["state"] == "locked":
            current.append(row)
        elif current:
            segments.append(_segment_record(current))
            current = []
    if current:
        segments.append(_segment_record(current))
    return segments


def _segment_record(rows: list[dict[str, object]]) -> dict[str, int]:
    return {
        "start_window": int(rows[0]["window_index"]),
        "end_window": int(rows[-1]["window_index"]),
        "start_sample": int(rows[0]["sample_time"]),
        "end_sample": int(rows[-1]["sample_time"]),
        "duration": int(len(rows)),
    }


def _baseline(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for run_id, group in df.groupby("run_id", sort=True):
        group = group.sort_values("window_index").reset_index(drop=True)
        rows.append({"run_id": int(run_id), **_trigger(group), **_state_metrics(group)})
    return pd.DataFrame(rows)


def _normal_fpr(normal: pd.DataFrame) -> float:
    return float((_baseline(normal)["status"] == "triggered").mean())


def _replacement_pair(group: pd.DataFrame) -> str | None:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return None
    return str(non_target.value_counts().idxmax())


def _post_target_segments(group: pd.DataFrame, trigger_window: int) -> list[list[int]]:
    post = group.loc[
        (group["window_index"] >= int(trigger_window) + 1)
        & (group["dominant_pair"] == TARGET_PAIR)
    ].sort_values("window_index")
    if post.empty:
        return []
    windows = post["window_index"].astype(int).tolist()
    segments: list[list[int]] = [[windows[0]]]
    for window in windows[1:]:
        if window == segments[-1][-1] + 1:
            segments[-1].append(window)
        else:
            segments.append([window])
    return segments


def _attack_block(group: pd.DataFrame, trigger_window: int, requested_block: int) -> dict[str, object]:
    segments = _post_target_segments(group, trigger_window)
    if not segments:
        return {
            "windows": [],
            "actual_block_size": 0,
            "attack_start_window": np.nan,
            "attack_end_window": np.nan,
            "recovery_start_window": np.nan,
        }
    segment = max(segments, key=len)
    segment_start = int(segment[0])
    segment_length = len(segment)
    if segment_length < requested_block:
        actual_block_size = segment_length
    else:
        actual_block_size = requested_block
    center_start = segment_start + (segment_length - actual_block_size) // 2
    attack_start_window = int(center_start)
    attack_end_window = int(center_start + actual_block_size - 1)
    windows = list(range(attack_start_window, attack_end_window + 1))
    return {
        "windows": windows,
        "actual_block_size": int(actual_block_size),
        "attack_start_window": attack_start_window,
        "attack_end_window": attack_end_window,
        "recovery_start_window": int(attack_end_window + 1),
    }


def _apply_attack(group: pd.DataFrame, windows: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if windows:
        mask = modified["window_index"].isin(windows)
        modified.loc[mask, "dominant_pair"] = replacement
    return modified


def _relock_metrics(
    modified: pd.DataFrame,
    attack_end_window: int | float,
    recovery_start_window: int | float,
    baseline_duration: float,
) -> dict[str, object]:
    if pd.isna(recovery_start_window):
        return {
            "relock_status": "no_relock",
            "relock_window": np.nan,
            "relock_sample": np.nan,
            "relock_time_windows": np.nan,
            "relock_time_samples": np.nan,
            "max_recovered_lock": 0,
            "baseline_duration": baseline_duration,
            "residual_damage": 0.0 if baseline_duration == 0 else 1.0,
        }
    states = _run_lengths(modified)
    relock = next(
        (
            row
            for row in states
            if int(row["window_index"]) >= int(recovery_start_window)
            and int(row["run_length"]) >= 10
        ),
        None,
    )
    segments = _locked_segments_from_states(states, min_window=int(recovery_start_window))
    max_recovered_lock = int(max((seg["duration"] for seg in segments), default=0))
    if baseline_duration == 0:
        residual_damage = 0.0
    else:
        residual_damage = 1.0 - (max_recovered_lock / baseline_duration)
    if relock is None:
        return {
            "relock_status": "no_relock",
            "relock_window": np.nan,
            "relock_sample": np.nan,
            "relock_time_windows": np.nan,
            "relock_time_samples": np.nan,
            "max_recovered_lock": max_recovered_lock,
            "baseline_duration": baseline_duration,
            "residual_damage": residual_damage,
        }
    attack_end_sample = int(
        modified.loc[modified["window_index"] == int(attack_end_window), "sample_time"].iloc[0]
    )
    relock_window = int(relock["window_index"])
    relock_sample = int(relock["sample_time"])
    return {
        "relock_status": "relocked",
        "relock_window": relock_window,
        "relock_sample": relock_sample,
        "relock_time_windows": relock_window - int(attack_end_window),
        "relock_time_samples": relock_sample - attack_end_sample,
        "max_recovered_lock": max_recovered_lock,
        "baseline_duration": baseline_duration,
        "residual_damage": residual_damage,
    }


def _evaluate(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    # Seed retained for reproducibility policy; centered block attack is deterministic.
    _rng = np.random.default_rng(SEED)
    baseline_by_run = baseline.set_index("run_id").to_dict(orient="index")
    rows = []
    for run_id, raw_group in f13.groupby("run_id", sort=True):
        run_id = int(run_id)
        group = raw_group.sort_values("window_index").reset_index(drop=True)
        base = baseline_by_run[run_id]
        replacement = _replacement_pair(group)
        for mode, requested_block in MODES:
            if base["status"] != "triggered":
                rows.append(_empty_row(run_id, mode, requested_block, "baseline_miss", base))
                continue
            if replacement is None:
                rows.append(_empty_row(run_id, mode, requested_block, "no_replacement", base))
                continue
            block = _attack_block(group, int(base["trigger_window"]), requested_block)
            windows = block["windows"]
            if not windows:
                rows.append(_empty_row(run_id, mode, requested_block, "no_post_target", base))
                continue
            modified = _apply_attack(group, windows, replacement)
            metrics = _relock_metrics(
                modified,
                block["attack_end_window"],
                block["recovery_start_window"],
                float(base["max_locked_duration"]),
            )
            rows.append(
                {
                    "run_id": run_id,
                    "mode": mode,
                    "requested_block": int(requested_block),
                    "actual_block_size": int(block["actual_block_size"]),
                    "attack_start_window": int(block["attack_start_window"]),
                    "attack_end_window": int(block["attack_end_window"]),
                    "recovery_start_window": int(block["recovery_start_window"]),
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def _empty_row(
    run_id: int,
    mode: str,
    requested_block: int,
    status: str,
    base: dict[str, object],
) -> dict[str, object]:
    baseline_duration = float(base["max_locked_duration"])
    return {
        "run_id": int(run_id),
        "mode": mode,
        "requested_block": int(requested_block),
        "actual_block_size": 0,
        "attack_start_window": np.nan,
        "attack_end_window": np.nan,
        "recovery_start_window": np.nan,
        "relock_status": status,
        "relock_window": np.nan,
        "relock_sample": np.nan,
        "relock_time_windows": np.nan,
        "relock_time_samples": np.nan,
        "max_recovered_lock": 0,
        "baseline_duration": baseline_duration,
        "residual_damage": 0.0 if baseline_duration == 0 else 1.0,
    }


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode, requested_block in MODES:
        group = runs.loc[runs["mode"] == mode]
        relocked = group.loc[group["relock_status"] == "relocked"]
        relock_rate = float((group["relock_status"] == "relocked").mean())
        if relocked.empty:
            median_windows = np.nan
            median_samples = np.nan
        else:
            median_windows = float(relocked["relock_time_windows"].median())
            median_samples = float(relocked["relock_time_samples"].median())
        if relock_rate >= 0.70:
            status = "ROBUST"
        elif relock_rate >= 0.30:
            status = "DEGRADED"
        else:
            status = "FAILED"
        rows.append(
            {
                "mode": mode,
                "requested_block": int(requested_block),
                "relock_rate": relock_rate,
                "median_relock_time_windows": median_windows,
                "median_relock_time_samples": median_samples,
                "mean_recovered_lock": float(group["max_recovered_lock"].mean()),
                "mean_residual_damage": float(group["residual_damage"].mean()),
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def _load_reference() -> pd.DataFrame | None:
    if not CONTIGUOUS_SUMMARY.exists():
        return None
    ref = pd.read_csv(CONTIGUOUS_SUMMARY)
    keep = ["mode", "mean_locked_fraction", "mean_max_locked_duration", "maintenance_survival_rate", "status"]
    missing = [column for column in keep if column not in ref.columns]
    if missing:
        return None
    return ref.loc[ref["mode"].isin([mode for mode, _ in MODES]), keep].copy()


def _verdict(summary: pd.DataFrame) -> str:
    if (summary["relock_rate"] >= 0.70).all() and (summary["median_relock_time_windows"] <= 10).all():
        return "fast"
    if (summary["relock_rate"] >= 0.70).any():
        return "slow"
    return "absent"


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
    text = f"""# ES-v3.2c Recovery / Relock Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Attack:

temporary contiguous maintenance disturbance

Recovery:

natural trace continuation

No synthetic recovery

Detector:

ES-v2 hard lock

k=5

## Results

{_markdown_table(summary)}

## Recovery metrics

relock_rate

relock_time

residual_damage

## Comparison

ES-v3.1c maintenance

vs

ES-v3.2c recovery

{_markdown_table(reference)}

## Key question

Can lock state recover

after disturbance ends?

## Verdict

Recovery:

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
    print("=== ES-v3.2c Recovery / Relock Audit ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock k=5")

    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline(f13)
    normal_fpr = _normal_fpr(normal)

    baseline_trigger_rate = float((baseline["status"] == "triggered").mean())
    baseline_median_delay = float(baseline.loc[baseline["status"] == "triggered", "delay"].median())
    baseline_locked_fraction = float(baseline["locked_fraction"].mean())
    baseline_duration = float(baseline["max_locked_duration"].mean())

    runs = _evaluate(f13, baseline)
    summary = _summary(runs)
    reference = _load_reference()
    verdict = _verdict(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, reference, verdict)

    print("\nBaseline:")
    print(f"trigger_rate = {baseline_trigger_rate:.6f}")
    print(f"median_delay = {baseline_median_delay:.6f}")
    print(f"mean_locked_fraction = {baseline_locked_fraction:.6f}")
    print(f"mean_max_locked_duration = {baseline_duration:.6f}")
    print(f"NORMAL_FPR = {normal_fpr:.6f}")

    print("\nRecovery summary:")
    print(summary.to_string(index=False))

    print("\nComparison with ES-v3.1c contiguous maintenance:")
    if reference is None:
        print("(comparison skipped)")
    else:
        print(reference.to_string(index=False))

    print(f"\nFinal verdict: Recovery {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print(
        "\nBoundary: EL-1 exploratory only. No TE, absorb_score, transition matrix, "
        "taxonomy update, industrial interpretation, or early-warning claim."
    )


if __name__ == "__main__":
    main()
