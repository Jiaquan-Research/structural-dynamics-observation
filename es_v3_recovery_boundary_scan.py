"""ES-v3.2d-lite Recovery Boundary Scan.

Status: EL-1 exploratory.

Expands contiguous maintenance disturbance size and checks whether natural
relock failure reflects true recovery failure or observation horizon limits.
Detector logic remains unchanged: ES-v2 hard lock k=5.
No soft lock, TE, absorb_score, transition matrix, load proxy, marine transfer,
mixed disturbance, taxonomy update, industrial interpretation, or early-warning
claim.
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
RECOVERY_REFERENCE = CSV_DIR / "es_v3_recovery_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_recovery_boundary_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_recovery_boundary_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_recovery_boundary_scan.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
REFERENCE_RELOCK_WINDOWS = 10.0
MODES: list[tuple[str, int]] = [("block_15", 15), ("block_20", 20), ("block_30", 30)]


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
        rows.append(
            {
                "window_index": int(row.window_index),
                "sample_time": int(row.sample_time),
                "dominant_pair": str(row.dominant_pair),
                "run_length": int(run_length),
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
    locked_flags = [int(row["run_length"]) >= 10 for row in _run_lengths(df)]
    locked_fraction = float(np.mean(locked_flags)) if locked_flags else 0.0
    segments: list[int] = []
    current = 0
    for is_locked in locked_flags:
        if is_locked:
            current += 1
        elif current:
            segments.append(current)
            current = 0
    if current:
        segments.append(current)
    return {
        "locked_fraction": locked_fraction,
        "max_locked_duration": int(max(segments)) if segments else 0,
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
    actual_block_size = segment_length if segment_length < requested_block else requested_block
    center_start = segment_start + (segment_length - actual_block_size) // 2
    attack_start = int(center_start)
    attack_end = int(center_start + actual_block_size - 1)
    return {
        "windows": list(range(attack_start, attack_end + 1)),
        "actual_block_size": int(actual_block_size),
        "attack_start_window": attack_start,
        "attack_end_window": attack_end,
        "recovery_start_window": int(attack_end + 1),
    }


def _apply_attack(group: pd.DataFrame, windows: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if windows:
        modified.loc[modified["window_index"].isin(windows), "dominant_pair"] = replacement
    return modified


def _relock_metrics(modified: pd.DataFrame, attack_end_window: int | float) -> dict[str, object]:
    trace_end = int(modified["window_index"].max())
    if pd.isna(attack_end_window):
        return {
            "relock_status": "no_relock",
            "relock_window": np.nan,
            "relock_time_windows": np.nan,
            "relock_time_samples": np.nan,
            "recovery_horizon": np.nan,
            "horizon_margin": np.nan,
        }
    attack_end = int(attack_end_window)
    recovery_start = attack_end + 1
    states = _run_lengths(modified)
    relock = next(
        (
            row
            for row in states
            if int(row["window_index"]) >= recovery_start and int(row["run_length"]) >= 10
        ),
        None,
    )
    recovery_horizon = trace_end - attack_end
    horizon_margin = recovery_horizon / REFERENCE_RELOCK_WINDOWS
    if relock is None:
        return {
            "relock_status": "no_relock",
            "relock_window": np.nan,
            "relock_time_windows": np.nan,
            "relock_time_samples": np.nan,
            "recovery_horizon": int(recovery_horizon),
            "horizon_margin": float(horizon_margin),
        }
    attack_end_sample = int(
        modified.loc[modified["window_index"] == attack_end, "sample_time"].iloc[0]
    )
    return {
        "relock_status": "relocked",
        "relock_window": int(relock["window_index"]),
        "relock_time_windows": int(relock["window_index"]) - attack_end,
        "relock_time_samples": int(relock["sample_time"]) - attack_end_sample,
        "recovery_horizon": int(recovery_horizon),
        "horizon_margin": float(horizon_margin),
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
                rows.append(_empty_row(run_id, mode, requested_block, "baseline_miss"))
                continue
            if replacement is None:
                rows.append(_empty_row(run_id, mode, requested_block, "no_replacement"))
                continue
            block = _attack_block(group, int(base["trigger_window"]), requested_block)
            if not block["windows"]:
                rows.append(_empty_row(run_id, mode, requested_block, "no_post_target"))
                continue
            modified = _apply_attack(group, block["windows"], replacement)
            metrics = _relock_metrics(modified, block["attack_end_window"])
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


def _empty_row(run_id: int, mode: str, requested_block: int, status: str) -> dict[str, object]:
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
        "relock_time_windows": np.nan,
        "relock_time_samples": np.nan,
        "recovery_horizon": np.nan,
        "horizon_margin": np.nan,
    }


def _row_status(relock_rate: float, mean_horizon_margin: float) -> str:
    if mean_horizon_margin <= 1:
        return "HORIZON_LIMITED"
    if relock_rate >= 0.70:
        return "ROBUST"
    if relock_rate >= 0.30:
        return "DEGRADED"
    return "FAILED"


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode, requested_block in MODES:
        group = runs.loc[runs["mode"] == mode]
        relocked = group.loc[group["relock_status"] == "relocked"]
        relock_rate = float((group["relock_status"] == "relocked").mean())
        median_windows = float(relocked["relock_time_windows"].median()) if not relocked.empty else np.nan
        median_samples = float(relocked["relock_time_samples"].median()) if not relocked.empty else np.nan
        mean_horizon = float(group["recovery_horizon"].mean())
        mean_margin = float(group["horizon_margin"].mean())
        n_horizon_limited = int((group["horizon_margin"] <= 1).sum())
        rows.append(
            {
                "mode": mode,
                "requested_block": int(requested_block),
                "relock_rate": relock_rate,
                "median_relock_time_windows": median_windows,
                "median_relock_time_samples": median_samples,
                "mean_recovery_horizon": mean_horizon,
                "mean_horizon_margin": mean_margin,
                "n_horizon_limited": n_horizon_limited,
                "status": _row_status(relock_rate, mean_margin),
            }
        )
    return pd.DataFrame(rows)


def _load_reference() -> pd.DataFrame | None:
    if not RECOVERY_REFERENCE.exists():
        return None
    ref = pd.read_csv(RECOVERY_REFERENCE)
    keep = [
        "mode",
        "requested_block",
        "relock_rate",
        "median_relock_time_windows",
        "median_relock_time_samples",
        "status",
    ]
    missing = [column for column in keep if column not in ref.columns]
    if missing:
        return None
    return ref[keep].copy()


def _overall_verdict(summary: pd.DataFrame) -> str:
    if (summary["status"] == "HORIZON_LIMITED").all():
        return "HORIZON_LIMITED"
    if (summary["status"] == "ROBUST").all():
        return "ROBUST"
    if (summary["status"] == "FAILED").any():
        return "FAILED"
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
    text = f"""# ES-v3.2d-lite Recovery Boundary Scan

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Attack:

contiguous maintenance disturbance

Recovery:

natural trace continuation

Detector:

ES-v2 hard lock

k=5

## Results

{_markdown_table(summary)}

## Horizon diagnostics

mean_recovery_horizon

mean_horizon_margin

horizon_limited count

## Key question

When does recovery fail?

Recovery failure

or

observation horizon limit?

## Comparison

ES-v3.2c

block_3

block_5

block_10

vs

extended attack

block_15

block_20

block_30

{_markdown_table(reference)}

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
    print("=== ES-v3.2d-lite Recovery Boundary Scan ===")
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
    verdict = _overall_verdict(summary)

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

    print("\nRecovery boundary summary:")
    print(summary.to_string(index=False))

    print("\nReference ES-v3.2c summary:")
    if reference is None:
        print("(comparison skipped)")
    else:
        print(reference.to_string(index=False))

    print("\nFinal verdict:")
    print(verdict)

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print(
        "\nBoundary: EL-1 exploratory only. No TE, absorb_score, transition matrix, "
        "mixed disturbance, taxonomy update, industrial interpretation, or early-warning claim."
    )


if __name__ == "__main__":
    main()
