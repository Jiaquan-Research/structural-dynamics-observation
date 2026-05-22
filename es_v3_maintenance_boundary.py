"""ES-v3.1b Maintenance Boundary Scan.

Status: EL-1 exploratory.

Tests post-trigger lock maintenance robustness. The pre-trigger region is left
unchanged in every mode, and detector logic remains unchanged: ES-v2 hard lock
k=5. No soft lock, TE, absorb_score, transition matrix, marine transfer,
taxonomy update, industrial interpretation, or early-warning claim.
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
RUNS_OUTPUT = CSV_DIR / "es_v3_maintenance_boundary_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_maintenance_boundary_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_maintenance_boundary.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
MODES: list[tuple[str, float | None]] = [
    ("noise_10pct", 0.10),
    ("noise_20pct", 0.20),
    ("noise_30pct", 0.30),
    ("noise_50pct", 0.50),
    ("noise_70pct", 0.70),
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
    states: list[str] = []
    locked_flags: list[bool] = []
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
        states.append(state)
        locked_flags.append(state == "locked")

    n_windows = len(states)
    locked_fraction = float(np.mean(locked_flags)) if locked_flags else 0.0
    locked_segments: list[int] = []
    current = 0
    for is_locked in locked_flags:
        if is_locked:
            current += 1
        elif current:
            locked_segments.append(current)
            current = 0
    if current:
        locked_segments.append(current)

    return {
        "locked_fraction": locked_fraction,
        "max_locked_duration": int(max(locked_segments)) if locked_segments else 0,
        "n_locked_segments": int(len(locked_segments)),
        "n_windows": int(n_windows),
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


def _post_trigger_positions(group: pd.DataFrame, trigger_window: int) -> list[int]:
    last_window = int(group["window_index"].max())
    start = int(trigger_window) + 1
    mask = (
        (group["window_index"] >= start)
        & (group["window_index"] <= last_window)
        & (group["dominant_pair"] == TARGET_PAIR)
    )
    return group.index[mask].astype(int).tolist()


def _apply(group: pd.DataFrame, positions: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if positions:
        modified.loc[positions, "dominant_pair"] = replacement
    return modified


def _evaluate(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    baseline_by_run = baseline.set_index("run_id").to_dict(orient="index")
    rows = []
    for run_id, raw_group in f13.groupby("run_id", sort=True):
        run_id = int(run_id)
        group = raw_group.sort_values("window_index").reset_index(drop=True)
        base = baseline_by_run[run_id]
        replacement = _replacement_pair(group)
        positions: list[int] = []
        if base["status"] == "triggered" and pd.notna(base["trigger_window"]):
            positions = _post_trigger_positions(group, int(base["trigger_window"]))
        n_post_target = len(positions)

        for mode, fraction in MODES:
            if base["status"] != "triggered":
                replay = group
                trigger_result = _trigger(replay)
                status = "baseline_miss"
                n_replaced = 0
            elif replacement is None:
                replay = group
                trigger_result = _trigger(replay)
                status = "no_replacement"
                n_replaced = 0
            elif n_post_target == 0:
                replay = group
                trigger_result = _trigger(replay)
                status = "no_post_target"
                n_replaced = 0
            else:
                if fraction is None:
                    n_replaced = n_post_target
                else:
                    n_replaced = max(1, round(n_post_target * float(fraction)))
                    n_replaced = min(n_replaced, n_post_target)
                if fraction is None:
                    selected = positions
                else:
                    selected = rng.choice(positions, size=n_replaced, replace=False).astype(int).tolist()
                replay = _apply(group, selected, replacement)
                trigger_result = _trigger(replay)
                status = str(trigger_result["status"])

            metrics = _state_metrics(replay)
            baseline_locked_fraction = float(base["locked_fraction"])
            baseline_max_duration = float(base["max_locked_duration"])
            locked_fraction = float(metrics["locked_fraction"])
            max_duration = float(metrics["max_locked_duration"])
            if baseline_locked_fraction == 0:
                maintenance_damage = 0.0
            else:
                maintenance_damage = 1.0 - (locked_fraction / baseline_locked_fraction)
            maintenance_survived = bool(
                (locked_fraction >= 0.5 * baseline_locked_fraction)
                or (max_duration >= 0.5 * baseline_max_duration)
            )

            rows.append(
                {
                    "run_id": run_id,
                    "mode": mode,
                    "n_post_target": int(n_post_target),
                    "n_replaced": int(n_replaced),
                    "trigger_sample": trigger_result["trigger_sample"],
                    "delay": trigger_result["delay"],
                    "trigger_status": trigger_result["status"],
                    "locked_fraction": locked_fraction,
                    "max_locked_duration": int(metrics["max_locked_duration"]),
                    "n_locked_segments": int(metrics["n_locked_segments"]),
                    "maintenance_damage": float(maintenance_damage),
                    "maintenance_survived": maintenance_survived,
                    "status": status,
                }
            )
    return pd.DataFrame(rows)


def _row_status(survival_rate: float, trigger_rate: float) -> str:
    if survival_rate >= 0.70 and trigger_rate >= 0.70:
        return "ROBUST"
    if survival_rate >= 0.50 and trigger_rate >= 0.50:
        return "DEGRADED"
    return "COLLAPSED"


def _summary(
    runs: pd.DataFrame,
    baseline_mean_locked_fraction: float,
    baseline_mean_max_locked_duration: float,
    normal_fpr: float,
) -> pd.DataFrame:
    rows = []
    for mode, _fraction in MODES:
        group = runs.loc[runs["mode"] == mode]
        triggered = group.loc[group["trigger_status"] == "triggered"]
        trigger_rate = float((group["trigger_status"] == "triggered").mean())
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.inf
        mean_locked_fraction = float(group["locked_fraction"].mean())
        mean_max_duration = float(group["max_locked_duration"].mean())
        survival_rate = float(group["maintenance_survived"].mean())
        rows.append(
            {
                "mode": mode,
                "n_no_post_target": int((group["status"] == "no_post_target").sum()),
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "mean_locked_fraction": mean_locked_fraction,
                "mean_max_locked_duration": mean_max_duration,
                "mean_n_locked_segments": float(group["n_locked_segments"].mean()),
                "locked_fraction_shift": mean_locked_fraction - baseline_mean_locked_fraction,
                "duration_shift": mean_max_duration - baseline_mean_max_locked_duration,
                "mean_maintenance_damage": float(group["maintenance_damage"].mean()),
                "maintenance_survival_rate": survival_rate,
                "NORMAL_FPR": normal_fpr,
                "status": _row_status(survival_rate, trigger_rate),
            }
        )
    return pd.DataFrame(rows)


def _phase_transition(summary: pd.DataFrame) -> str:
    failed = summary.loc[summary["status"] != "ROBUST"]
    if failed.empty:
        return "No phase transition within tested range"
    mode = str(failed.iloc[0]["mode"])
    return f"Maintenance phase transition at: {mode}"


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
                if np.isfinite(value):
                    values.append(format(float(value), floatfmt))
                else:
                    values.append(str(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_doc(
    baseline_values: dict[str, float],
    summary: pd.DataFrame,
    phase_text: str,
) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    baseline_df = pd.DataFrame([baseline_values])
    curve = summary[
        [
            "mode",
            "mean_locked_fraction",
            "mean_maintenance_damage",
            "maintenance_survival_rate",
            "status",
        ]
    ].copy()
    text = f"""# ES-v3.1b Maintenance Boundary Scan

Status: EL-1 exploratory
Date: 2026-05-22

## Setup

Attack region: post-trigger only [trigger_window+1, end]
Pre-trigger region: unchanged
Modes: 10%, 20%, 30%, 50%, 70%, maintenance_exhaustion
Detector: ES-v2 hard lock k=5, unchanged.

## Baseline

{_markdown_table(baseline_df)}

## Results

{_markdown_table(summary)}

## Maintenance curve

{_markdown_table(curve)}

## Phase transition

{phase_text}

## Interpretation

Formation robustness (ES-v3.1a): not the bottleneck.
F13 signal is globally strong; pre-trigger exhaustion cannot prevent trigger.
Maintenance robustness: this experiment tests post-trigger lock survival.

## Restrictions

No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.1b Maintenance Boundary Scan ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock k=5")

    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline(f13)
    normal_fpr = _normal_fpr(normal)

    baseline_trigger_rate = float((baseline["status"] == "triggered").mean())
    baseline_median_delay = float(baseline.loc[baseline["status"] == "triggered", "delay"].median())
    baseline_mean_locked_fraction = float(baseline["locked_fraction"].mean())
    baseline_mean_max_locked_duration = float(baseline["max_locked_duration"].mean())
    baseline_values = {
        "baseline_trigger_rate": baseline_trigger_rate,
        "baseline_median_delay": baseline_median_delay,
        "baseline_mean_locked_fraction": baseline_mean_locked_fraction,
        "baseline_mean_max_locked_duration": baseline_mean_max_locked_duration,
        "NORMAL_FPR": normal_fpr,
    }

    runs = _evaluate(f13, baseline)
    summary = _summary(runs, baseline_mean_locked_fraction, baseline_mean_max_locked_duration, normal_fpr)
    phase_text = _phase_transition(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(baseline_values, summary, phase_text)

    print("\nBaseline:")
    for key, value in baseline_values.items():
        print(f"{key} = {value:.6f}")

    print("\nFull summary table:")
    print(summary.to_string(index=False))

    print("\nMaintenance curve:")
    curve = summary[["mode", "mean_locked_fraction", "mean_maintenance_damage", "maintenance_survival_rate", "status"]]
    print(curve.to_string(index=False))

    print(f"\n{phase_text}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print(
        "\nBoundary: EL-1 exploratory only. No soft lock, TE, industrial claim, "
        "early-warning claim, taxonomy update, or frozen modification."
    )


if __name__ == "__main__":
    main()
