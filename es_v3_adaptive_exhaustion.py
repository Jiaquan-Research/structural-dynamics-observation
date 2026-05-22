"""ES-v3.0b++ Adaptive Local Exhaustion.

Status: EL-1 exploratory.

Tests whether the ES-v2 hard lock survives complete removal of target-pair
windows in the immediate pre-trigger region. Detector logic is unchanged.
No soft lock, TE, absorb_score, transition matrix, load proxy, marine transfer,
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
FIXED_SUMMARY = CSV_DIR / "es_v3_noise_escalation_summary.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_adaptive_exhaustion_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_adaptive_exhaustion_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_adaptive_exhaustion.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
MODES = [
    ("baseline", 0),
    ("noise_1", 1),
    ("noise_2", 2),
    ("noise_3", 3),
    ("noise_4", 4),
    ("exhaustion", -1),
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


def _baseline(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [{"run_id": int(run_id), **_trigger(group)} for run_id, group in df.groupby("run_id", sort=True)]
    )


def _normal_fpr(normal: pd.DataFrame) -> float:
    base = _baseline(normal)
    return float((base["status"] == "triggered").mean())


def _replacement_pair(group: pd.DataFrame) -> str | None:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return None
    return str(non_target.value_counts().idxmax())


def _attack_positions(group: pd.DataFrame, trigger_window: int) -> list[int]:
    start = max(0, int(trigger_window) - 10)
    end = int(trigger_window) - 1
    mask = (
        (group["window_index"] >= start)
        & (group["window_index"] <= end)
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
    rows = []
    for base_row in baseline.itertuples(index=False):
        run_id = int(base_row.run_id)
        group = f13.loc[f13["run_id"] == run_id].sort_values("window_index").reset_index(drop=True)
        replacement = _replacement_pair(group)
        positions: list[int] = []
        if base_row.status == "triggered" and pd.notna(base_row.trigger_window):
            positions = _attack_positions(group, int(base_row.trigger_window))
        n_target = len(positions)

        for mode, requested in MODES:
            if mode == "baseline":
                result = _trigger(group)
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "requested_replace": 0,
                        "effective_replace": 0,
                        "n_target_windows": n_target,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": result["trigger_sample"],
                        "delay": result["delay"],
                        "status": result["status"],
                    }
                )
                continue

            if base_row.status != "triggered":
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "requested_replace": int(requested),
                        "effective_replace": 0,
                        "n_target_windows": n_target,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": np.nan,
                        "delay": np.nan,
                        "status": "baseline_miss",
                    }
                )
                continue

            if replacement is None:
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "requested_replace": int(requested),
                        "effective_replace": 0,
                        "n_target_windows": n_target,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": np.nan,
                        "delay": np.nan,
                        "status": "no_replacement",
                    }
                )
                continue

            if n_target == 0:
                result = _trigger(group)
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "requested_replace": int(requested),
                        "effective_replace": 0,
                        "n_target_windows": 0,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": result["trigger_sample"],
                        "delay": result["delay"],
                        "status": "no_target" if result["status"] == "triggered" else result["status"],
                    }
                )
                continue

            effective = n_target if mode == "exhaustion" else min(int(requested), n_target)
            selected = (
                positions
                if mode == "exhaustion"
                else rng.choice(positions, size=effective, replace=False).astype(int).tolist()
            )
            result = _trigger(_apply(group, selected, replacement))
            rows.append(
                {
                    "run_id": run_id,
                    "mode": mode,
                    "requested_replace": int(requested),
                    "effective_replace": int(effective),
                    "n_target_windows": int(n_target),
                    "exhausted_fraction": float(effective / n_target),
                    "trigger_sample": result["trigger_sample"],
                    "delay": result["delay"],
                    "status": result["status"],
                }
            )
    return pd.DataFrame(rows)


def _row_status(trigger_rate: float, normal_fpr: float, median_delay: float) -> str:
    if trigger_rate >= 0.70 and normal_fpr <= 0.10 and median_delay <= 200:
        return "ROBUST"
    if trigger_rate >= 0.50:
        return "DEGRADED"
    return "COLLAPSED"


def _summary(runs: pd.DataFrame, baseline_median: float, normal_fpr: float) -> pd.DataFrame:
    rows = []
    for mode, group in runs.groupby("mode", sort=False):
        triggered_mask = group["status"].isin(["triggered", "no_target"])
        triggered = group.loc[triggered_mask]
        misses = group.loc[group["status"].isin(["miss", "baseline_miss", "no_replacement"])]
        trigger_rate = float(len(triggered) / len(group)) if len(group) else np.nan
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.inf
        miss_rate = float(len(misses) / len(group)) if len(group) else np.nan
        survival_score = trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - median_delay / 300.0)
        requested = int(group["requested_replace"].iloc[0])
        rows.append(
            {
                "mode": mode,
                "requested_replace": requested,
                "mean_effective_replace": float(group["effective_replace"].mean()),
                "mean_exhausted_fraction": float(group["exhausted_fraction"].mean()),
                "n_no_target": int((group["n_target_windows"] == 0).sum()),
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "delay_shift": median_delay - baseline_median if np.isfinite(median_delay) else np.nan,
                "miss_rate": miss_rate,
                "NORMAL_FPR": normal_fpr,
                "survival_score": survival_score,
                "status": _row_status(trigger_rate, normal_fpr, median_delay),
            }
        )
    order = {mode: idx for idx, (mode, _requested) in enumerate(MODES)}
    out = pd.DataFrame(rows)
    out["_order"] = out["mode"].map(order)
    return out.sort_values("_order").drop(columns=["_order"])


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
                values.append(format(float(value), floatfmt))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_doc(summary: pd.DataFrame, verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""# ES-v3.0b++ Adaptive Local Exhaustion
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Attack region: [trigger_window-10, trigger_window-1]
Modes: baseline, noise_1-4, exhaustion
no_target runs: replay original trace unchanged (not counted as miss)
Detector: ES-v2 hard lock k=5, unchanged.

## Baseline
{_markdown_table(summary.loc[summary["mode"] == "baseline"], floatfmt=".6f")}

## Results
{_markdown_table(summary, floatfmt=".6f")}

## Robustness curve
exhausted_fraction vs trigger_rate and delay_shift

{_markdown_table(summary[["mode", "mean_exhausted_fraction", "trigger_rate", "delay_shift", "status"]], floatfmt=".6f")}

## Verdict
{verdict}

## Interpretation
exhaustion mode = complete removal of TARGET_PAIR windows
in immediate pre-trigger region.
Result does NOT test post-trigger lock maintenance (ES-v3.1 scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.0b++ Adaptive Local Exhaustion ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock k=5")
    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline(f13)
    normal_fpr = _normal_fpr(normal)
    baseline_triggered = baseline.loc[baseline["status"] == "triggered"]
    baseline_rate = float((baseline["status"] == "triggered").mean())
    baseline_median = float(baseline_triggered["delay"].median())

    runs = _evaluate(f13, baseline)
    summary = _summary(runs, baseline_median, normal_fpr)
    exhaustion = summary.loc[summary["mode"] == "exhaustion"].iloc[0]
    if exhaustion["status"] == "ROBUST":
        verdict = "ES-v2 hard lock: saturated local robustness CONFIRMED"
    else:
        verdict = "ES-v2 hard lock: saturated local robustness NOT confirmed"
        failed = []
        if float(exhaustion["trigger_rate"]) < 0.70:
            failed.append("trigger_rate < 0.70")
        if float(exhaustion["NORMAL_FPR"]) > 0.10:
            failed.append("NORMAL_FPR > 0.10")
        if float(exhaustion["median_delay"]) > 200:
            failed.append("median_delay > 200")
        if failed:
            verdict += " (" + ", ".join(failed) + ")"

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, verdict)

    print("")
    print("Baseline results:")
    print(f"trigger_rate = {baseline_rate:.6f}")
    print(f"median_delay = {baseline_median:.6f}")
    print(f"NORMAL_FPR = {normal_fpr:.6f}")
    print("")
    print("Full summary table:")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("n_no_target by mode:")
    for row in summary.itertuples(index=False):
        print(f"{row.mode}: n_no_target={row.n_no_target}")
    print("")
    if FIXED_SUMMARY.exists():
        fixed = pd.read_csv(FIXED_SUMMARY)
        print("Comparison with ES-v3.0b fixed results:")
        print(fixed.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
        print("")
    print(verdict)
    print("")
    print("Generated files:")
    print(f"- {RUNS_OUTPUT}")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {DOC_OUTPUT}")
    print("")
    print("Boundary: EL-1 exploratory only. No soft lock, TE, industrial claim, early-warning claim, taxonomy update, or frozen modification.")


if __name__ == "__main__":
    main()
