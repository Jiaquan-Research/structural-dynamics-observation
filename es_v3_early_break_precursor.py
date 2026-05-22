"""ES-v3.4c Early-break Precursor Audit.

Status: EL-1 exploratory.

Recomputes per-window state from dominant_pair_trace_F13.csv using the same
contiguous attack, relock, and drop-tracking logic as ES-v3.1c, ES-v3.2c, and
ES-v3.4b. Tests fixed precursor rules only: no model training, threshold
optimization, detector change, taxonomy update, industrial interpretation, or
early-warning claim.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_DIR = PROJECT_ROOT / "outputs" / "csv"
DOC_DIR = PROJECT_ROOT / "docs" / "exploratory"

FLOOR_RUNS = CSV_DIR / "es_v3_floor_mechanism_runs.csv"
STRESS_RUNS = CSV_DIR / "es_v3_recovery_stress_split_runs.csv"
F13_TRACE = CSV_DIR / "dominant_pair_trace_F13.csv"

RUNS_OUTPUT = CSV_DIR / "es_v3_early_break_precursor_runs.csv"
SUMMARY_OUTPUT = CSV_DIR / "es_v3_early_break_precursor_summary.csv"
RULES_OUTPUT = CSV_DIR / "es_v3_early_break_rule_scores.csv"
DOC_OUTPUT = DOC_DIR / "es_v3_early_break_precursor.md"

TARGET_PAIR = "XMEAS7-XMEAS11"
POPULATION_B = {15, 22, 23, 24, 30, 48}
ATTACK_BLOCKS = {
    "block_3": 3,
    "block_5": 5,
    "block_10": 10,
    "block_15": 15,
    "block_20": 20,
}
H_VALUES = [3, 5, 10]


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    floor = pd.read_csv(FLOOR_RUNS)
    stress = pd.read_csv(STRESS_RUNS)
    trace = pd.read_csv(F13_TRACE)
    missing_floor = [column for column in ["run_id", "attack_mode"] if column not in floor.columns]
    missing_stress = [column for column in ["run_id", "attack_mode"] if column not in stress.columns]
    missing_trace = [column for column in ["run_id", "window_index", "sample_time", "dominant_pair"] if column not in trace.columns]
    if missing_floor:
        raise ValueError(f"{FLOOR_RUNS} missing required columns: {missing_floor}")
    if missing_stress:
        raise ValueError(f"{STRESS_RUNS} missing required columns: {missing_stress}")
    if missing_trace:
        raise ValueError(f"{F13_TRACE} missing required columns: {missing_trace}")
    return floor, stress, trace


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
    hit = _states(group).loc[lambda df: df["run_length"] >= 5]
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
    actual = min(requested_block, len(segment))
    center_start = int(segment[0]) + (len(segment) - actual) // 2
    return list(range(center_start, center_start + actual))


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


def _replay(group: pd.DataFrame, attack_mode: str) -> tuple[pd.DataFrame, int | None, int | None]:
    trigger = _trigger_window(group)
    if trigger is None:
        return pd.DataFrame(), None, None
    windows = _attack_windows(group, trigger, ATTACK_BLOCKS[attack_mode])
    if not windows:
        return pd.DataFrame(), None, None
    modified = _apply_attack(group, windows, _replacement_pair(group))
    state_df = _states(modified)
    attack_end = max(windows)
    relock_hits = state_df.loc[(state_df["window_index"] >= attack_end + 1) & (state_df["run_length"] >= 10)]
    if relock_hits.empty:
        return state_df, None, attack_end
    return state_df, int(relock_hits.iloc[0]["window_index"]), attack_end


def _drop_latency(state_df: pd.DataFrame, relock_window: int) -> int:
    first_drop = state_df.loc[(state_df["window_index"] > relock_window) & (state_df["state"] != "locked")]
    if first_drop.empty:
        recovery = state_df.loc[state_df["window_index"] >= relock_window]
        return int(len(recovery))
    return int(first_drop.iloc[0]["window_index"] - relock_window)


def _precursor_row(
    run_id: int,
    population: str,
    attack_mode: str,
    h: int,
    state_df: pd.DataFrame,
    relock_window: int,
    latency: int,
) -> dict[str, object]:
    window = state_df.loc[
        (state_df["window_index"] >= relock_window)
        & (state_df["window_index"] <= relock_window + h - 1)
    ].copy()
    if window.empty:
        locked_fraction = np.nan
        persistent_fraction = np.nan
        mean_run = np.nan
        min_run = np.nan
        slope = np.nan
        state_drop = False
        below_persistent = False
    else:
        locked_fraction = float((window["state"] == "locked").mean())
        persistent_fraction = float((window["state_rank"] >= 2).mean())
        mean_run = float(window["run_length"].mean())
        min_run = int(window["run_length"].min())
        slope = int(window["run_length"].iloc[-1] - window["run_length"].iloc[0])
        state_drop = bool((window["state"] != "locked").any())
        below_persistent = bool((window["state_rank"] < 2).any())
    return {
        "run_id": int(run_id),
        "population": population,
        "attack_mode": attack_mode,
        "H": int(h),
        "relock_window": int(relock_window),
        "relock_to_drop_latency": int(latency),
        "early_break": int(latency <= 10),
        "early_locked_fraction": locked_fraction,
        "early_persistent_or_locked_fraction": persistent_fraction,
        "early_mean_run_length": mean_run,
        "early_min_run_length": min_run,
        "early_run_length_slope": slope,
        "early_state_drop": state_drop,
        "early_below_persistent": below_persistent,
    }


def _evaluate(stress: pd.DataFrame, trace: pd.DataFrame) -> pd.DataFrame:
    trace_by_run = {
        int(run_id): group.sort_values("window_index").reset_index(drop=True)
        for run_id, group in trace.groupby("run_id", sort=True)
    }
    pairs = stress[["run_id", "attack_mode"]].drop_duplicates()
    rows = []
    for item in pairs.itertuples(index=False):
        run_id = int(item.run_id)
        attack_mode = str(item.attack_mode)
        if attack_mode not in ATTACK_BLOCKS:
            continue
        state_df, relock_window, _attack_end = _replay(trace_by_run[run_id], attack_mode)
        if relock_window is None or state_df.empty:
            continue
        population = "B" if run_id in POPULATION_B else "A"
        latency = _drop_latency(state_df, relock_window)
        for h in H_VALUES:
            rows.append(_precursor_row(run_id, population, attack_mode, h, state_df, relock_window, latency))
    return pd.DataFrame(rows)


def _summary(runs: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "early_locked_fraction",
        "early_persistent_or_locked_fraction",
        "early_mean_run_length",
        "early_min_run_length",
        "early_run_length_slope",
        "early_state_drop",
        "early_below_persistent",
    ]
    rows = []
    for h in H_VALUES:
        hdf = runs.loc[runs["H"] == h]
        for metric in metrics:
            a = hdf.loc[hdf["population"] == "A", metric].astype(float)
            b = hdf.loc[hdf["population"] == "B", metric].astype(float)
            early = hdf.loc[hdf["early_break"] == 1, metric].astype(float)
            non = hdf.loc[hdf["early_break"] == 0, metric].astype(float)
            a_mean = float(a.mean()) if not a.empty else np.nan
            b_mean = float(b.mean()) if not b.empty else np.nan
            e_mean = float(early.mean()) if not early.empty else np.nan
            n_mean = float(non.mean()) if not non.empty else np.nan
            rows.append(
                {
                    "H": h,
                    "metric": metric,
                    "A_mean": a_mean,
                    "B_mean": b_mean,
                    "A_minus_B": a_mean - b_mean if np.isfinite(a_mean) and np.isfinite(b_mean) else np.nan,
                    "early_break_mean": e_mean,
                    "non_early_break_mean": n_mean,
                    "early_minus_non": e_mean - n_mean if np.isfinite(e_mean) and np.isfinite(n_mean) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _score_rule(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    yt = y_true.astype(bool)
    yp = y_pred.astype(bool)
    tp = int((yt & yp).sum())
    fp = int((~yt & yp).sum())
    fn = int((yt & ~yp).sum())
    tn = int((~yt & ~yp).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _rule_scores(runs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for h in H_VALUES:
        hdf = runs.loc[runs["H"] == h]
        rules = {
            "early_locked_fraction_H < 0.8": hdf["early_locked_fraction"] < 0.8,
            "early_min_run_length_H < 10": hdf["early_min_run_length"] < 10,
            "early_state_drop_H == True": hdf["early_state_drop"] == True,
            "early_below_persistent_H == True": hdf["early_below_persistent"] == True,
        }
        for name, pred in rules.items():
            scores = _score_rule(hdf["early_break"] == 1, pred)
            rows.append({"H": h, "rule": name, **scores})
    return pd.DataFrame(rows)


def _verdict(scores: pd.DataFrame) -> str:
    best = float(scores["f1"].max()) if not scores.empty else 0.0
    if best >= 0.70:
        return "precursor_detected"
    if best >= 0.50:
        return "weak_precursor"
    return "no_clear_precursor"


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


def _write_doc(summary: pd.DataFrame, scores: pd.DataFrame, verdict: str) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    best = scores.sort_values("f1", ascending=False).head(8)
    text = f"""# ES-v3.4c Early-break Precursor Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Question

Can early-break behavior be seen

in the first few windows after relock?

## Setup

H:

3

5

10

Outcome:

early_break = relock_to_drop_latency <= 10

Unit:

window count

No model training.

Fixed rules only.

Population B:

n = 6 runs

Maximum evaluated:

30 run-mode samples

Rule scores:

order-of-magnitude indicators only

F1 thresholds:

exploratory labels

NOT statistical validation

## Population comparison

A

vs

B

{_markdown_table(summary.loc[summary["metric"].isin(["early_locked_fraction", "early_mean_run_length", "early_state_drop"])])}

## Early-break comparison

early_break

vs

non_early_break

## Rule scores

fixed rules

precision

recall

F1

{_markdown_table(best)}

## Interpretation

If fixed rules work:

precursor exists

If not:

early-break may require longer horizon

or richer state features.

## Verdict

{verdict}

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

No detector modification

EL-1 exploratory only
"""
    DOC_OUTPUT.write_text(text, encoding="utf-8")


def main() -> None:
    print("=== ES-v3.4c Early-break Precursor Audit ===")
    print("Status: EL-1 exploratory")

    _floor, stress, trace = _load_inputs()
    runs = _evaluate(stress, trace)
    summary = _summary(runs)
    scores = _rule_scores(runs)
    verdict = _verdict(scores)

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    runs.to_csv(RUNS_OUTPUT, index=False)
    summary.to_csv(SUMMARY_OUTPUT, index=False)
    scores.to_csv(RULES_OUTPUT, index=False)
    _write_doc(summary, scores, verdict)

    print("\nPopulation comparison:")
    print(summary.loc[summary["metric"].isin(["early_locked_fraction", "early_mean_run_length", "early_state_drop"])].to_string(index=False))

    print("\nEarly-break comparison:")
    print(summary.loc[summary["metric"].isin(["early_locked_fraction", "early_min_run_length", "early_state_drop"])][["H", "metric", "early_break_mean", "non_early_break_mean", "early_minus_non"]].to_string(index=False))

    best = scores.sort_values("f1", ascending=False).iloc[0]
    print("\nBest fixed rule by F1:")
    print(best.to_string())

    print(f"\nFinal verdict: {verdict}")

    print("\nGenerated files:")
    for path in [RUNS_OUTPUT, SUMMARY_OUTPUT, RULES_OUTPUT, DOC_OUTPUT]:
        print(f"- {path}")

    print("\nBoundary: EL-1 exploratory only. No detector change, model training, threshold optimization, taxonomy update, industrial interpretation, or early-warning claim.")


if __name__ == "__main__":
    main()
