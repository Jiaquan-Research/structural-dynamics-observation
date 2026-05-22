"""ES-v3.1c Contiguous Maintenance Attack.

Status: EL-1 exploratory.

Attacks post-trigger lock maintenance with contiguous block removal instead of
random sparse replacement. Detector logic remains unchanged: ES-v2 hard lock
k=5. No soft lock, TE, absorb_score, transition matrix, load proxy, marine
transfer, taxonomy update, industrial interpretation, or early-warning claim.
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
SPARSE_SUMMARY = CSV_DIR / "es_v3_maintenance_boundary_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_contiguous_maintenance_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_contiguous_maintenance_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_contiguous_maintenance.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7

MODES: list[tuple[str, int | None]] = [
    ("block_1", 1),
    ("block_2", 2),
    ("block_3", 3),
    ("block_5", 5),
    ("block_10", 10),
    ("maintenance_exhaustion", None),
]


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


def _trigger(df: pd.DataFrame) -> dict[str, object]:
    run_length = 0
    for row in df.sort_values("window_index").itertuples(index=False):
        if str(row.dominant_pair) == TARGET_PAIR:
            run_length += 1
        else:
            run_length = 0
        if run_length >= K:
            sample = int(row.sample_time)
            return {
                "trigger_window": int(row.window_index),
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
    run_length = 0
    locked_flags: list[bool] = []
    for row in df.sort_values("window_index").itertuples(index=False):
        if str(row.dominant_pair) == TARGET_PAIR:
            run_length += 1
        else:
            run_length = 0
        locked_flags.append(run_length >= 10)

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
        "n_locked_segments": int(len(segments)),
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


def _post_target_positions(group: pd.DataFrame, trigger_window: int) -> list[int]:
    mask = (group["window_index"] >= int(trigger_window) + 1) & (group["dominant_pair"] == TARGET_PAIR)
    return group.index[mask].astype(int).tolist()


def _target_segments(positions: list[int]) -> list[list[int]]:
    if not positions:
        return []
    ordered = sorted(int(pos) for pos in positions)
    segments: list[list[int]] = [[ordered[0]]]
    for pos in ordered[1:]:
        if pos == segments[-1][-1] + 1:
            segments[-1].append(pos)
        else:
            segments.append([pos])
    return segments


def _choose_block(positions: list[int], requested_block: int | None) -> tuple[list[int], int, int, float]:
    if not positions:
        return [], 0, 0, 0.0
    if requested_block is None:
        return sorted(positions), len(positions), len(positions), 1.0

    segments = _target_segments(positions)
    longest = max(segments, key=len)
    segment_length = len(longest)
    if segment_length < requested_block:
        selected = longest
        actual_block = segment_length
    else:
        center_start = 0 + (segment_length - requested_block) // 2
        selected = longest[center_start : center_start + requested_block]
        actual_block = requested_block
    block_fraction = float(actual_block / segment_length) if segment_length else 0.0
    return selected, int(actual_block), int(segment_length), block_fraction


def _apply(group: pd.DataFrame, positions: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if positions:
        modified.loc[positions, "dominant_pair"] = replacement
    return modified


def _evaluate(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    # Seed retained for reproducibility policy; contiguous center removal is deterministic.
    _rng = np.random.default_rng(SEED)
    baseline_by_run = baseline.set_index("run_id").to_dict(orient="index")
    rows = []
    for run_id, raw_group in f13.groupby("run_id", sort=True):
        run_id = int(run_id)
        group = raw_group.sort_values("window_index").reset_index(drop=True)
        base = baseline_by_run[run_id]
        replacement = _replacement_pair(group)
        positions: list[int] = []
        if base["status"] == "triggered" and pd.notna(base["trigger_window"]):
            positions = _post_target_positions(group, int(base["trigger_window"]))

        for mode, requested_block in MODES:
            if base["status"] != "triggered":
                replay = group
                trigger_result = _trigger(replay)
                metrics = _state_metrics(replay)
                rows.append(
                    _row(
                        run_id,
                        mode,
                        requested_block,
                        0,
                        0,
                        0.0,
                        trigger_result,
                        metrics,
                        False,
                        "baseline_miss",
                    )
                )
                continue
            if replacement is None:
                replay = group
                trigger_result = _trigger(replay)
                metrics = _state_metrics(replay)
                rows.append(
                    _row(
                        run_id,
                        mode,
                        requested_block,
                        0,
                        0,
                        0.0,
                        trigger_result,
                        metrics,
                        False,
                        "no_replacement",
                    )
                )
                continue

            selected, actual_block, segment_length, block_fraction = _choose_block(positions, requested_block)
            replay = _apply(group, selected, replacement) if selected else group
            trigger_result = _trigger(replay)
            metrics = _state_metrics(replay)
            baseline_locked = float(base["locked_fraction"])
            baseline_duration = float(base["max_locked_duration"])
            survived = bool(
                (float(metrics["locked_fraction"]) >= 0.5 * baseline_locked)
                or (float(metrics["max_locked_duration"]) >= 0.5 * baseline_duration)
            )
            status = str(trigger_result["status"]) if selected else "no_post_target"
            rows.append(
                _row(
                    run_id,
                    mode,
                    requested_block,
                    actual_block,
                    segment_length,
                    block_fraction,
                    trigger_result,
                    metrics,
                    survived,
                    status,
                )
            )
    return pd.DataFrame(rows)


def _row(
    run_id: int,
    mode: str,
    requested_block: int | None,
    actual_block_size: int,
    segment_length: int,
    block_fraction: float,
    trigger_result: dict[str, object],
    metrics: dict[str, object],
    maintenance_survived: bool,
    status: str,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "mode": mode,
        "requested_block": -1 if requested_block is None else int(requested_block),
        "actual_block_size": int(actual_block_size),
        "segment_length": int(segment_length),
        "block_fraction": float(block_fraction),
        "trigger_sample": trigger_result["trigger_sample"],
        "locked_fraction": float(metrics["locked_fraction"]),
        "max_locked_duration": int(metrics["max_locked_duration"]),
        "maintenance_survived": bool(maintenance_survived),
        "status": status,
    }


def _row_status(trigger_rate: float, survival_rate: float) -> str:
    if survival_rate >= 0.70 and trigger_rate >= 0.70:
        return "ROBUST"
    if survival_rate >= 0.50 and trigger_rate >= 0.50:
        return "DEGRADED"
    return "COLLAPSED"


def _summary(
    runs: pd.DataFrame,
    baseline_locked_fraction: float,
    baseline_duration: float,
) -> pd.DataFrame:
    rows = []
    for mode, requested_block in MODES:
        group = runs.loc[runs["mode"] == mode]
        triggered = group.loc[group["status"] == "triggered"]
        trigger_rate = float((group["status"] == "triggered").mean())
        delays = triggered["trigger_sample"].astype(float) - FAULT_INJECTION_SAMPLE
        median_delay = float(delays.median()) if not delays.empty else np.inf
        mean_locked_fraction = float(group["locked_fraction"].mean())
        mean_duration = float(group["max_locked_duration"].mean())
        survival_rate = float(group["maintenance_survived"].mean())
        damage = 1.0 - (mean_locked_fraction / baseline_locked_fraction) if baseline_locked_fraction else 0.0
        rows.append(
            {
                "mode": mode,
                "requested_block": -1 if requested_block is None else int(requested_block),
                "mean_actual_block": float(group["actual_block_size"].mean()),
                "mean_block_fraction": float(group["block_fraction"].mean()),
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "mean_locked_fraction": mean_locked_fraction,
                "mean_max_locked_duration": mean_duration,
                "maintenance_survival_rate": survival_rate,
                "maintenance_damage": damage,
                "status": _row_status(trigger_rate, survival_rate),
            }
        )
    return pd.DataFrame(rows)


def _load_sparse_comparison() -> pd.DataFrame | None:
    if not SPARSE_SUMMARY.exists():
        return None
    sparse = pd.read_csv(SPARSE_SUMMARY)
    keep = [
        "mode",
        "mean_locked_fraction",
        "mean_max_locked_duration",
        "maintenance_survival_rate",
        "status",
    ]
    missing = [column for column in keep if column not in sparse.columns]
    if missing:
        return None
    sparse = sparse[keep].copy()
    sparse["source"] = "sparse_random"
    return sparse


def _comparison_table(summary: pd.DataFrame) -> pd.DataFrame | None:
    sparse = _load_sparse_comparison()
    if sparse is None:
        return None
    contiguous = summary[
        [
            "mode",
            "mean_locked_fraction",
            "mean_max_locked_duration",
            "maintenance_survival_rate",
            "status",
        ]
    ].copy()
    contiguous["source"] = "contiguous"
    return pd.concat([sparse, contiguous], ignore_index=True)[
        [
            "source",
            "mode",
            "mean_locked_fraction",
            "mean_max_locked_duration",
            "maintenance_survival_rate",
            "status",
        ]
    ]


def _verdict(summary: pd.DataFrame, comparison: pd.DataFrame | None) -> str:
    collapsed = set(summary.loc[summary["status"] == "COLLAPSED", "mode"].astype(str))
    if "block_1" in collapsed:
        return "temporary-sensitive"
    if "block_5" in collapsed or "block_10" in collapsed:
        return "mixed"
    if comparison is not None:
        sparse_collapsed = comparison.loc[
            (comparison["source"] == "sparse_random") & (comparison["status"] == "COLLAPSED")
        ]
        if not sparse_collapsed.empty and collapsed == {"maintenance_exhaustion"}:
            return "fragment-sensitive"
    return "mixed"


def _markdown_table(df: pd.DataFrame, floatfmt: str = ".6f") -> str:
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


def _write_doc(summary: pd.DataFrame, comparison: pd.DataFrame | None, verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""# ES-v3.1c Contiguous Maintenance Attack

Status: EL-1 exploratory
Date: 2026-05-22

## Setup

Attack: post-trigger only
Detector: ES-v2 hard lock k=5
Attack type: contiguous block removal
NOT random sparse deletion

## Results

{_markdown_table(summary)}

## Comparison

Sparse random attack vs contiguous attack

{_markdown_table(comparison)}

## Key question

Does maintenance fail because of:

- fragmentation
- temporary contiguous disturbance
- mixed effects?

## Verdict

maintenance: {verdict}

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
    print("=== ES-v3.1c Contiguous Maintenance Attack ===")
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
    summary = _summary(runs, baseline_locked_fraction, baseline_duration)
    comparison = _comparison_table(summary)
    verdict = _verdict(summary, comparison)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, comparison, verdict)

    print("\nBaseline:")
    print(f"trigger_rate = {baseline_trigger_rate:.6f}")
    print(f"median_delay = {baseline_median_delay:.6f}")
    print(f"mean_locked_fraction = {baseline_locked_fraction:.6f}")
    print(f"mean_max_locked_duration = {baseline_duration:.6f}")
    print(f"NORMAL_FPR = {normal_fpr:.6f}")

    print("\nContiguous block results:")
    print(summary.to_string(index=False))

    print("\nMean block fraction:")
    print(summary[["mode", "mean_actual_block", "mean_block_fraction"]].to_string(index=False))

    print("\nComparison with ES-v3.1b sparse attack:")
    if comparison is not None:
        print(comparison.to_string(index=False))
    else:
        print("(comparison skipped)")

    print(f"\nFinal verdict: maintenance {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print(
        "\nBoundary: EL-1 exploratory only. No TE, absorb_score, transition matrix, "
        "taxonomy update, industrial interpretation, or early-warning claim."
    )


if __name__ == "__main__":
    main()
