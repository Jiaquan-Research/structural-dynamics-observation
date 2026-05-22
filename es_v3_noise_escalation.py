"""ES-v3.0b+ Noise Escalation Audit.

Status: EL-1 exploratory.

Attacks pre-trigger persistence formation with fixed replacement counts while
keeping the ES-v2 hard-lock detector unchanged. No soft lock, TE,
absorb_score, transition matrix, load proxy, marine transfer, taxonomy update,
or industrial interpretation.
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
SUMMARY_OUTPUT = CSV_DIR / "es_v3_noise_escalation_summary.csv"
RUNS_OUTPUT = CSV_DIR / "es_v3_noise_escalation_runs.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_noise_escalation.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
FAULT_INJECTION_SAMPLE = 160
SEED = 7
REPLACE_COUNTS = [1, 2, 3, 4]


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
    rows = []
    for run_id, group in df.groupby("run_id", sort=True):
        rows.append({"run_id": int(run_id), **_trigger(group)})
    return pd.DataFrame(rows)


def _normal_fpr(normal: pd.DataFrame) -> float:
    base = _baseline(normal)
    return float((base["status"] == "triggered").mean())


def _replacement_pair(group: pd.DataFrame) -> str | None:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return None
    return str(non_target.value_counts().idxmax())


def _attack_positions(group: pd.DataFrame, trigger_window: int) -> list[int]:
    attack_start = max(0, int(trigger_window) - 10)
    attack_end = int(trigger_window) - 1
    mask = (
        (group["window_index"] >= attack_start)
        & (group["window_index"] <= attack_end)
        & (group["dominant_pair"] == TARGET_PAIR)
    )
    return group.index[mask].astype(int).tolist()


def _apply_attack(group: pd.DataFrame, positions: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    modified.loc[positions, "dominant_pair"] = replacement
    return modified


def _evaluate(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for base_row in baseline.itertuples(index=False):
        run_id = int(base_row.run_id)
        group = f13.loc[f13["run_id"] == run_id].sort_values("window_index").reset_index(drop=True)
        replacement = _replacement_pair(group)
        n_target = 0
        positions: list[int] = []
        if base_row.status == "triggered" and pd.notna(base_row.trigger_window):
            positions = _attack_positions(group, int(base_row.trigger_window))
            n_target = len(positions)
        for replace_count in REPLACE_COUNTS:
            if base_row.status != "triggered" or replacement is None or n_target < replace_count:
                rows.append(
                    {
                        "run_id": run_id,
                        "replace_count": int(replace_count),
                        "n_target_windows": int(n_target),
                        "trigger_sample": np.nan,
                        "delay": np.nan,
                        "status": "skip",
                    }
                )
                continue
            selected = rng.choice(positions, size=replace_count, replace=False).astype(int).tolist()
            result = _trigger(_apply_attack(group, selected, replacement))
            rows.append(
                {
                    "run_id": run_id,
                    "replace_count": int(replace_count),
                    "n_target_windows": int(n_target),
                    "trigger_sample": result["trigger_sample"],
                    "delay": result["delay"],
                    "status": result["status"],
                }
            )
    return pd.DataFrame(rows)


def _status(trigger_rate: float, normal_fpr: float, median_delay: float) -> str:
    if normal_fpr > 0.10 or trigger_rate < 0.50 or median_delay > 200:
        return "COLLAPSED"
    if trigger_rate >= 0.70 and normal_fpr <= 0.10 and median_delay <= 200:
        return "ROBUST"
    return "DEGRADED"


def _summary(runs: pd.DataFrame, baseline: pd.DataFrame, normal_fpr: float) -> pd.DataFrame:
    baseline_triggered = baseline.loc[baseline["status"] == "triggered"]
    baseline_trigger_rate = float((baseline["status"] == "triggered").mean())
    baseline_delay = float(baseline_triggered["delay"].median()) if not baseline_triggered.empty else np.nan
    rows = [
        {
            "mode": "baseline",
            "replace_count": 0,
            "n_eligible": int(len(baseline)),
            "trigger_rate": baseline_trigger_rate,
            "median_delay": baseline_delay,
            "delay_shift": 0.0,
            "miss_rate": float((baseline["status"] == "miss").mean()),
            "NORMAL_FPR": normal_fpr,
            "survival_score": baseline_trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - baseline_delay / 300.0),
            "status": _status(baseline_trigger_rate, normal_fpr, baseline_delay),
        }
    ]
    for replace_count in REPLACE_COUNTS:
        subset = runs.loc[runs["replace_count"] == replace_count]
        eligible = subset.loc[subset["status"] != "skip"]
        triggered = eligible.loc[eligible["status"] == "triggered"]
        n_eligible = int(len(eligible))
        trigger_rate = float((eligible["status"] == "triggered").mean()) if n_eligible else 0.0
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.inf
        miss_rate = float((eligible["status"] == "miss").mean()) if n_eligible else np.nan
        survival_score = trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - median_delay / 300.0)
        rows.append(
            {
                "mode": f"noise_{replace_count}",
                "replace_count": int(replace_count),
                "n_eligible": n_eligible,
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "delay_shift": median_delay - baseline_delay if np.isfinite(median_delay) else np.nan,
                "miss_rate": miss_rate,
                "NORMAL_FPR": normal_fpr,
                "survival_score": survival_score,
                "status": _status(trigger_rate, normal_fpr, median_delay),
            }
        )
    return pd.DataFrame(rows)


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


def _write_doc(summary: pd.DataFrame) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""# ES-v3.0b+ Noise Escalation

Status:

EL-1 exploratory

Date:

2026-05-22

## Setup

Detector:

ES-v2 hard lock

k=5

Attack:

pre-trigger persistence formation only

Attack region:

[trigger_window-10,
 trigger_window-1]

Noise type:

fixed replacement count

1

2

3

4

## Results

{_markdown_table(summary, floatfmt=".6f")}

## Robustness boundary

{_markdown_table(summary[["mode", "replace_count", "status"]], floatfmt=".6f")}

## Interpretation

Detector unchanged.

Observation attacked.

No soft lock.

## Restrictions

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.0b+ Noise Escalation Audit ===")
    print("Status: EL-1 exploratory")
    print("Detector unchanged: ES-v2 hard lock k=5")
    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline(f13)
    normal_fpr = _normal_fpr(normal)
    baseline_triggered = baseline.loc[baseline["status"] == "triggered"]
    baseline_rate = float((baseline["status"] == "triggered").mean())
    baseline_delay = float(baseline_triggered["delay"].median())

    runs = _evaluate(f13, baseline)
    summary = _summary(runs, baseline, normal_fpr)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    runs.to_csv(RUNS_OUTPUT, index=False)
    _write_doc(summary)

    print("")
    print("Baseline")
    print(f"trigger_rate = {baseline_rate:.6f}")
    print(f"median_delay = {baseline_delay:.6f}")
    print(f"NORMAL_FPR = {normal_fpr:.6f}")
    print("")
    print("Noise escalation results:")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("Eligibility / skip details:")
    for replace_count in REPLACE_COUNTS:
        subset = runs.loc[runs["replace_count"] == replace_count]
        n_total = int(len(subset))
        n_skipped = int((subset["status"] == "skip").sum())
        n_eligible = n_total - n_skipped
        fraction_skipped = float(n_skipped / n_total) if n_total else np.nan
        print(
            f"noise_{replace_count}: n_eligible={n_eligible} "
            f"n_skipped={n_skipped} fraction_skipped={fraction_skipped:.6f}"
        )
        if fraction_skipped > 0.30:
            print("WARNING: high skip rate, results may be limited")
    print("")
    print("Survival ranking:")
    ranking = summary.sort_values("survival_score", ascending=False)
    print(ranking[["mode", "replace_count", "survival_score", "status"]].to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("Boundary verdict:")
    for row in summary.itertuples(index=False):
        print(f"{row.mode}: {row.status}")
    print("")
    print("Generated files:")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {RUNS_OUTPUT}")
    print(f"- {DOC_OUTPUT}")
    print("")
    print("Boundary: EL-1 exploratory only. No soft lock, TE, industrial claim, early-warning claim, taxonomy update, or frozen modification.")


if __name__ == "__main__":
    main()
