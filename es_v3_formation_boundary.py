"""ES-v3.1a Formation Boundary Scan.

Status: EL-1 exploratory.

Expands the pre-trigger attack region and removes all TARGET_PAIR windows in
that region. Detector logic remains unchanged: ES-v2 hard lock k=5.
No soft lock, TE, absorb_score, transition matrix, marine transfer, taxonomy
update, industrial interpretation, or early-warning claim.
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
RUNS_OUTPUT = CSV_DIR / "es_v3_formation_boundary_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_formation_boundary_summary.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_formation_boundary.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
ATTACK_SIZES: list[int | str] = [10, 20, 30, 40, 50, "all_pre_trigger"]


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
    return float((_baseline(normal)["status"] == "triggered").mean())


def _replacement_pair(group: pd.DataFrame) -> str | None:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return None
    return str(non_target.value_counts().idxmax())


def _attack_positions(group: pd.DataFrame, trigger_window: int, attack_size: int | str) -> list[int]:
    if attack_size == "all_pre_trigger":
        start = 0
    else:
        start = max(0, int(trigger_window) - int(attack_size))
    end = int(trigger_window) - 1
    mask = (
        (group["window_index"] >= start)
        & (group["window_index"] <= end)
        & (group["dominant_pair"] == TARGET_PAIR)
    )
    return group.index[mask].astype(int).tolist()


def _apply_exhaustion(group: pd.DataFrame, positions: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if positions:
        modified.loc[positions, "dominant_pair"] = replacement
    return modified


def _evaluate(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    # Seed retained for reproducibility policy; exhaustion itself is deterministic.
    _rng = np.random.default_rng(SEED)
    rows = []
    for base_row in baseline.itertuples(index=False):
        run_id = int(base_row.run_id)
        group = f13.loc[f13["run_id"] == run_id].sort_values("window_index").reset_index(drop=True)
        replacement = _replacement_pair(group)
        for attack_size in ATTACK_SIZES:
            attack_label = str(attack_size)
            if base_row.status != "triggered":
                original = _trigger(group)
                rows.append(
                    {
                        "run_id": run_id,
                        "attack_size": attack_label,
                        "n_target_windows": 0,
                        "effective_replace": 0,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": original["trigger_sample"],
                        "delay": original["delay"],
                        "status": "baseline_miss",
                    }
                )
                continue
            if replacement is None:
                original = _trigger(group)
                rows.append(
                    {
                        "run_id": run_id,
                        "attack_size": attack_label,
                        "n_target_windows": 0,
                        "effective_replace": 0,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": original["trigger_sample"],
                        "delay": original["delay"],
                        "status": "no_replacement",
                    }
                )
                continue
            positions = _attack_positions(group, int(base_row.trigger_window), attack_size)
            n_target = len(positions)
            if n_target == 0:
                original = _trigger(group)
                rows.append(
                    {
                        "run_id": run_id,
                        "attack_size": attack_label,
                        "n_target_windows": 0,
                        "effective_replace": 0,
                        "exhausted_fraction": 0.0,
                        "trigger_sample": original["trigger_sample"],
                        "delay": original["delay"],
                        "status": "no_target" if original["status"] == "triggered" else original["status"],
                    }
                )
                continue
            result = _trigger(_apply_exhaustion(group, positions, replacement))
            rows.append(
                {
                    "run_id": run_id,
                    "attack_size": attack_label,
                    "n_target_windows": int(n_target),
                    "effective_replace": int(n_target),
                    "exhausted_fraction": 1.0,
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
    for attack_size in [str(item) for item in ATTACK_SIZES]:
        group = runs.loc[runs["attack_size"] == attack_size]
        triggered_mask = group["status"].isin(["triggered", "no_target"])
        triggered = group.loc[triggered_mask]
        miss_mask = group["status"].isin(["miss", "baseline_miss", "no_replacement"])
        trigger_rate = float(triggered_mask.mean())
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.inf
        miss_rate = float(miss_mask.mean())
        survival_score = trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - median_delay / 300.0)
        rows.append(
            {
                "attack_size": attack_size,
                "mean_n_target": float(group["n_target_windows"].mean()),
                "mean_effective_replace": float(group["effective_replace"].mean()),
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
    out = pd.DataFrame(rows)
    order = {str(item): idx for idx, item in enumerate(ATTACK_SIZES)}
    out["_order"] = out["attack_size"].map(order)
    return out.sort_values("_order").drop(columns=["_order"])


def _phase_transition(summary: pd.DataFrame) -> str:
    dropped = summary.loc[summary["trigger_rate"] < 0.70]
    if dropped.empty:
        return "No phase transition observed within tested range"
    attack_size = str(dropped.iloc[0]["attack_size"])
    return f"Phase transition detected at attack_size = {attack_size}"


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


def _write_doc(summary: pd.DataFrame, baseline_row: pd.DataFrame, phase_transition: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    curve = summary[["attack_size", "trigger_rate", "delay_shift", "status"]].copy()
    text = f"""# ES-v3.1a Formation Boundary Scan
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Mode: exhaustion (remove all TARGET windows in attack region)
Attack sizes: 10, 20, 30, 40, 50, all_pre_trigger
Detector: ES-v2 hard lock k=5, unchanged.
no_target runs: replay original trace (not counted as miss)

## Baseline
{_markdown_table(baseline_row, floatfmt=".6f")}

## Results
{_markdown_table(summary, floatfmt=".6f")}

## Robustness curve
{_markdown_table(curve, floatfmt=".6f")}

## Phase transition
{phase_transition}

## Interpretation
Formation robustness only.
Post-trigger maintenance not tested (ES-v3.1b scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.1a Formation Boundary Scan ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock k=5")
    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline(f13)
    normal_fpr = _normal_fpr(normal)
    baseline_triggered = baseline.loc[baseline["status"] == "triggered"]
    baseline_trigger_rate = float((baseline["status"] == "triggered").mean())
    baseline_median = float(baseline_triggered["delay"].median())
    baseline_row = pd.DataFrame(
        [
            {
                "trigger_rate": baseline_trigger_rate,
                "median_delay": baseline_median,
                "NORMAL_FPR": normal_fpr,
            }
        ]
    )

    runs = _evaluate(f13, baseline)
    summary = _summary(runs, baseline_median, normal_fpr)
    phase = _phase_transition(summary)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    _write_doc(summary, baseline_row, phase)

    print("")
    print("Baseline:")
    print(f"trigger_rate = {baseline_trigger_rate:.6f}")
    print(f"median_delay = {baseline_median:.6f}")
    print(f"NORMAL_FPR = {normal_fpr:.6f}")
    print("")
    print("Full summary table:")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print(phase)
    print("")
    print("Robustness curve:")
    print(summary[["attack_size", "trigger_rate", "median_delay", "status"]].to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("Generated files:")
    print(f"- {RUNS_OUTPUT}")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {DOC_OUTPUT}")
    print("")
    print("Boundary: EL-1 exploratory only. No soft lock, TE, industrial claim, early-warning claim, taxonomy update, or frozen modification.")


if __name__ == "__main__":
    main()
