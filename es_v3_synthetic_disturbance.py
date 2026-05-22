"""ES-v3.0b Synthetic Disturbance Replay.

Status: EL-1 exploratory.

Attacks only the pre-trigger persistence formation phase for F13 and keeps the
ES-v2 persistence trigger logic unchanged. NORMAL receives no disturbance.
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
SUMMARY_OUTPUT = CSV_DIR / "es_v3_disturbance_summary.csv"
RUNS_OUTPUT = CSV_DIR / "es_v3_disturbance_runs.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_synthetic_disturbance.md"

TRACE_COLUMNS = ["fault", "run_id", "window_index", "sample_time", "dominant_pair"]
TARGET_PAIR = "XMEAS7-XMEAS11"
K = 5
SEED = 7
FAULT_INJECTION_SAMPLE = 160


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


def _trigger(sequence_df: pd.DataFrame) -> dict[str, object]:
    run_length = 0
    for row in sequence_df.sort_values("window_index").itertuples(index=False):
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


def _baseline_by_run(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for run_id, group in df.groupby("run_id", sort=True):
        rows.append({"run_id": int(run_id), **_trigger(group)})
    return pd.DataFrame(rows)


def _normal_fpr(normal: pd.DataFrame) -> float:
    baseline = _baseline_by_run(normal)
    return float((baseline["status"] == "triggered").mean())


def _non_target_replacement(group: pd.DataFrame) -> str | None:
    non_target = group.loc[group["dominant_pair"] != TARGET_PAIR, "dominant_pair"].astype(str)
    if non_target.empty:
        return None
    return str(non_target.value_counts().idxmax())


def _attack_context(group: pd.DataFrame, baseline_trigger_window: int) -> tuple[pd.DataFrame, list[int], str | None]:
    group = group.sort_values("window_index").reset_index(drop=True)
    attack_start = max(0, int(baseline_trigger_window) - 10)
    attack_end = int(baseline_trigger_window) - 1
    if attack_start >= attack_end:
        return group, [], None
    attack_mask = (
        (group["window_index"] >= attack_start)
        & (group["window_index"] <= attack_end)
        & (group["dominant_pair"] == TARGET_PAIR)
    )
    attack_positions = group.index[attack_mask].astype(int).tolist()
    replacement = _non_target_replacement(group)
    return group, attack_positions, replacement


def _apply_replacements(group: pd.DataFrame, positions: list[int], replacement: str) -> pd.DataFrame:
    modified = group.copy()
    if positions:
        modified.loc[positions, "dominant_pair"] = replacement
    return modified


def _select_double_break(positions: list[int], rng: np.random.Generator) -> list[int] | None:
    pairs = [(a, b) for i, a in enumerate(positions) for b in positions[i + 1 :] if abs(b - a) >= 3]
    if not pairs:
        return None
    idx = int(rng.integers(0, len(pairs)))
    return [int(pairs[idx][0]), int(pairs[idx][1])]


def _record_run(run_id: int, mode: str, strength: str, result: dict[str, object]) -> dict[str, object]:
    return {
        "run_id": int(run_id),
        "mode": mode,
        "strength": strength,
        "trigger_sample": result["trigger_sample"],
        "delay": result["delay"],
        "status": result["status"],
    }


def _evaluate_disturbances(f13: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for baseline_row in baseline.itertuples(index=False):
        run_id = int(baseline_row.run_id)
        if baseline_row.status != "triggered" or pd.isna(baseline_row.trigger_window):
            continue
        group = f13.loc[f13["run_id"] == run_id]
        context, positions, replacement = _attack_context(group, int(baseline_row.trigger_window))
        if not positions or replacement is None:
            for mode, strength in [
                ("single_break", "1"),
                ("double_break", "2"),
                ("noise_replay", "5%"),
                ("noise_replay", "10%"),
                ("noise_replay", "20%"),
            ]:
                rows.append(
                    {
                        "run_id": run_id,
                        "mode": mode,
                        "strength": strength,
                        "trigger_sample": np.nan,
                        "delay": np.nan,
                        "status": "skip",
                    }
                )
            continue

        single_pos = [int(rng.choice(positions))]
        rows.append(_record_run(run_id, "single_break", "1", _trigger(_apply_replacements(context, single_pos, replacement))))

        double_pos = _select_double_break(positions, rng)
        if double_pos is None:
            rows.append(
                {
                    "run_id": run_id,
                    "mode": "double_break",
                    "strength": "2",
                    "trigger_sample": np.nan,
                    "delay": np.nan,
                    "status": "skip",
                }
            )
        else:
            rows.append(_record_run(run_id, "double_break", "2", _trigger(_apply_replacements(context, double_pos, replacement))))

        for fraction in [0.05, 0.10, 0.20]:
            n_attack = len(positions)
            n_replace = max(1, int(round(n_attack * fraction)))
            n_replace = min(n_replace, n_attack)
            selected = rng.choice(positions, size=n_replace, replace=False).astype(int).tolist()
            rows.append(
                _record_run(
                    run_id,
                    "noise_replay",
                    f"{int(fraction * 100)}%",
                    _trigger(_apply_replacements(context, selected, replacement)),
                )
            )
    return pd.DataFrame(rows)


def _status(trigger_rate: float, normal_fpr: float, median_delay: float) -> str:
    if trigger_rate >= 0.70 and normal_fpr <= 0.10 and median_delay <= 200:
        return "ROBUST"
    if trigger_rate >= 0.50:
        return "DEGRADED"
    return "COLLAPSED"


def _summarize_runs(
    runs: pd.DataFrame,
    baseline_median_delay: float,
    normal_fpr: float,
    include_baseline: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rows = []
    if include_baseline is not None:
        triggered = include_baseline.loc[include_baseline["status"] == "triggered"]
        trigger_rate = float((include_baseline["status"] == "triggered").mean())
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.nan
        rows.append(
            {
                "mode": "baseline",
                "strength": "none",
                "n_eligible": int(len(include_baseline)),
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "delay_shift": 0.0,
                "miss_rate": float((include_baseline["status"] == "miss").mean()),
                "NORMAL_FPR": normal_fpr,
                "survival_score": trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - median_delay / 300.0),
                "status": _status(trigger_rate, normal_fpr, median_delay),
            }
        )

    for (mode, strength), group in runs.groupby(["mode", "strength"], sort=True):
        eligible = group.loc[group["status"] != "skip"]
        triggered = eligible.loc[eligible["status"] == "triggered"]
        n_eligible = int(len(eligible))
        trigger_rate = float((eligible["status"] == "triggered").mean()) if n_eligible else 0.0
        median_delay = float(triggered["delay"].median()) if not triggered.empty else np.nan
        miss_rate = float((eligible["status"] == "miss").mean()) if n_eligible else np.nan
        delay_shift = median_delay - baseline_median_delay if np.isfinite(median_delay) else np.nan
        survival_score = (
            trigger_rate * (1.0 - normal_fpr) * max(0.0, 1.0 - median_delay / 300.0)
            if np.isfinite(median_delay)
            else 0.0
        )
        rows.append(
            {
                "mode": mode,
                "strength": strength,
                "n_eligible": n_eligible,
                "trigger_rate": trigger_rate,
                "median_delay": median_delay,
                "delay_shift": delay_shift,
                "miss_rate": miss_rate,
                "NORMAL_FPR": normal_fpr,
                "survival_score": survival_score,
                "status": _status(trigger_rate, normal_fpr, median_delay if np.isfinite(median_delay) else np.inf),
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
    baseline = summary.loc[summary["mode"] == "baseline"]
    single = summary.loc[summary["mode"] == "single_break"]
    double = summary.loc[summary["mode"] == "double_break"]
    noise = summary.loc[summary["mode"] == "noise_replay"]
    text = f"""# ES-v3.0b Synthetic Disturbance Replay
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Attack region: [trigger_window-10, trigger_window-1]
Only pre-trigger persistence formation is attacked.
Detector logic: unchanged (k=5 hard lock).

## Baseline
{_markdown_table(baseline, floatfmt=".6f")}

## Mode A: Single break
{_markdown_table(single, floatfmt=".6f")}

## Mode B: Double break
{_markdown_table(double, floatfmt=".6f")}

## Mode C: Noise (5%, 10%, 20%)
{_markdown_table(noise, floatfmt=".6f")}

## Robustness boundary
{_markdown_table(summary[["mode", "strength", "status"]], floatfmt=".6f")}

## Interpretation
Pre-trigger formation robustness only.
Post-trigger lock maintenance not tested (ES-v3.1 scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.0b Synthetic Disturbance Replay ===")
    print("Status: EL-1 exploratory")
    print("Detector logic unchanged: TARGET_PAIR persistence k=5")
    f13 = _load_trace(F13_TRACE, "F13")
    normal = _load_trace(NORMAL_TRACE, "NORMAL")
    baseline = _baseline_by_run(f13)
    normal_fpr = _normal_fpr(normal)
    baseline_triggered = baseline.loc[baseline["status"] == "triggered"]
    baseline_rate = float((baseline["status"] == "triggered").mean())
    baseline_median_delay = float(baseline_triggered["delay"].median())

    print("")
    print("Baseline:")
    print(f"F13 trigger_rate = {baseline_rate:.6f}")
    print(f"F13 median_delay = {baseline_median_delay:.6f}")
    print(f"NORMAL FPR = {normal_fpr:.6f}")

    disturbed_runs = _evaluate_disturbances(f13, baseline)
    baseline_runs = baseline.copy()
    baseline_runs["mode"] = "baseline"
    baseline_runs["strength"] = "none"
    baseline_runs = baseline_runs[["run_id", "mode", "strength", "trigger_sample", "delay", "status"]]
    all_runs = pd.concat([baseline_runs, disturbed_runs], ignore_index=True)
    summary = _summarize_runs(disturbed_runs, baseline_median_delay, normal_fpr, include_baseline=baseline)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    all_runs.to_csv(RUNS_OUTPUT, index=False)
    _write_doc(summary)

    print("")
    print("Mode results:")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print("")
    print("Robustness verdict per mode:")
    for row in summary.itertuples(index=False):
        print(f"{row.mode} {row.strength}: {row.status}")
    print("")
    print("Generated files:")
    print(f"- {SUMMARY_OUTPUT}")
    print(f"- {RUNS_OUTPUT}")
    print(f"- {DOC_OUTPUT}")
    print("")
    print("Boundary: EL-1 exploratory only. No soft lock, TE, industrial claim, early-warning claim, taxonomy update, or frozen modification.")


if __name__ == "__main__":
    main()
