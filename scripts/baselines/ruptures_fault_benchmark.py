"""Recoverable ruptures fault benchmark with fault-level checkpoints."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ruptures_benchmark_common import (
    CSV_OUTPUT_DIR,
    FAULT_SUMMARY_OUTPUT,
    FP_TARGETS,
    N_RUNS,
    OVERALL_SUMMARY_OUTPUT,
    PENALTY_TABLE_OUTPUT,
    VERSIONS,
    evaluate_run,
    fault_label,
    fp_label,
    load_fault_run_arrays,
    load_metadata,
    result_key,
)

START_FAULT = 1
END_FAULT = 20

FAULT_SUMMARY_COLUMNS = [
    "version",
    "fp_target",
    "fault",
    "detection_rate",
    "median_delay",
    "mean_delay",
    "n_runs",
    "actual_fp_rate",
    "penalty_used",
    "detector_type",
]

OVERALL_SUMMARY_COLUMNS = [
    "version",
    "fp_target",
    "actual_fp_rate",
    "mean_detection_rate",
    "mean_delay",
    "penalty_used",
    "detector_type",
]


def _load_penalty_table() -> pd.DataFrame:
    if not PENALTY_TABLE_OUTPUT.exists():
        raise FileNotFoundError(
            f"Missing penalty table: {PENALTY_TABLE_OUTPUT}. "
            "Run scripts/analysis/ruptures_penalty_calibration.py first."
        )
    table = pd.read_csv(PENALTY_TABLE_OUTPUT)
    required = {"version", "fp_target", "penalty", "actual_fp_rate", "detector_type"}
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Penalty table missing columns: {sorted(missing)}")
    return table


def _penalty_record(penalty_table: pd.DataFrame, version: str, fp_target: float) -> pd.Series:
    rows = penalty_table.loc[
        (penalty_table["version"] == version)
        & np.isclose(penalty_table["fp_target"].to_numpy(dtype=float), float(fp_target))
    ]
    if rows.empty:
        raise ValueError(f"No penalty row for {version} fp_target={fp_target}")
    return rows.iloc[0]


def _version_penalty_rows(penalty_table: pd.DataFrame, version: str) -> pd.DataFrame:
    rows = penalty_table.loc[penalty_table["version"] == version].copy()
    if rows.empty:
        raise ValueError(f"No penalty rows for {version}")
    rows["fp_target"] = rows["fp_target"].astype(float)
    rows["penalty"] = rows["penalty"].astype(float)
    rows["actual_fp_rate"] = rows["actual_fp_rate"].astype(float)
    return rows.sort_values(["penalty", "fp_target"])


def _existing_keys() -> set[tuple[str, float, str]]:
    if not FAULT_SUMMARY_OUTPUT.exists():
        return set()
    existing = pd.read_csv(FAULT_SUMMARY_OUTPUT)
    if existing.empty:
        return set()
    return {
        (str(row.version), float(row.fp_target), str(row.fault))
        for row in existing.itertuples(index=False)
    }


def _append_fault_row(row: dict[str, object]) -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not FAULT_SUMMARY_OUTPUT.exists()
    pd.DataFrame([row], columns=FAULT_SUMMARY_COLUMNS).to_csv(
        FAULT_SUMMARY_OUTPUT,
        mode="a",
        header=write_header,
        index=False,
    )


def _aggregate_overall_summary() -> pd.DataFrame:
    if not FAULT_SUMMARY_OUTPUT.exists():
        raise FileNotFoundError(f"Missing fault summary: {FAULT_SUMMARY_OUTPUT}")
    fault_df = pd.read_csv(FAULT_SUMMARY_OUTPUT)
    rows = []
    for (version, fp_target), group in fault_df.groupby(["version", "fp_target"], sort=True):
        detected_mean_delay = group["mean_delay"].dropna().to_numpy(dtype=float)
        rows.append(
            {
                "version": str(version),
                "fp_target": float(fp_target),
                "actual_fp_rate": float(group["actual_fp_rate"].iloc[0]),
                "mean_detection_rate": float(group["detection_rate"].mean()),
                "mean_delay": float(np.mean(detected_mean_delay))
                if detected_mean_delay.size
                else float("nan"),
                "penalty_used": float(group["penalty_used"].iloc[0]),
                "detector_type": str(group["detector_type"].iloc[0]),
            }
        )
    overall_df = pd.DataFrame(rows, columns=OVERALL_SUMMARY_COLUMNS)
    overall_df.to_csv(OVERALL_SUMMARY_OUTPUT, index=False)
    return overall_df


def _benchmark_one_result(
    version: str,
    fp_target: float,
    fault: str,
    runs: dict[int, np.ndarray],
    penalty: float,
    actual_fp_rate: float,
    x7_idx: int,
    x11_idx: int,
) -> dict[str, object]:
    detected_values = []
    delays = []
    selected_runs = {run_id: runs[run_id] for run_id in sorted(runs)[:N_RUNS]}
    total_runs = len(selected_runs)

    for run_idx, run_data in enumerate(selected_runs.values(), start=1):
        run_results = evaluate_run(run_data, version, [float(penalty)], x7_idx, x11_idx)
        detected, delay = run_results[float(penalty)]
        detected_values.append(bool(detected))
        if detected:
            delays.append(float(delay))
        if run_idx % 20 == 0 or run_idx == total_runs:
            print(f"[{version} {fp_label(fp_target)} {fault}]", flush=True)
            print(f"run {run_idx} / {total_runs}", flush=True)

    detection_rate = float(np.mean(detected_values)) if detected_values else float("nan")
    median_delay = float(np.median(delays)) if delays else float("nan")
    mean_delay = float(np.mean(delays)) if delays else float("nan")
    return {
        "version": version,
        "fp_target": float(fp_target),
        "fault": fault,
        "detection_rate": detection_rate,
        "median_delay": median_delay,
        "mean_delay": mean_delay,
        "n_runs": int(total_runs),
        "actual_fp_rate": float(actual_fp_rate),
        "penalty_used": float(penalty),
        "detector_type": VERSIONS[version]["detector_type"],
    }


def main() -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    penalty_table = _load_penalty_table()
    existing = _existing_keys()
    testing_path, selected_columns, usecols, x7_idx, x11_idx = load_metadata()

    for fault_number in range(START_FAULT, END_FAULT + 1):
        fault = fault_label(fault_number)
        runs = load_fault_run_arrays(testing_path, usecols, selected_columns, fault_number)

        for version in ("Version A", "Version B"):
            version_rows = _version_penalty_rows(penalty_table, version)
            pending_rows = []
            for fp_target in FP_TARGETS:
                key = (version, float(fp_target), fault)
                if key in existing:
                    print(f"SKIP existing result: {result_key(version, fp_target, fault)}")
                    continue
                pending_rows.append(_penalty_record(penalty_table, version, float(fp_target)))

            if not pending_rows:
                continue

            pending_df = pd.DataFrame(pending_rows)
            for penalty, penalty_group in pending_df.groupby("penalty", sort=True):
                penalty = float(penalty)
                targets = sorted(penalty_group["fp_target"].astype(float).tolist())
                target_labels = ", ".join(fp_label(target) for target in targets)
                if len(targets) > 1:
                    print(
                        f"REUSE same-penalty benchmark: {version} {fault} "
                        f"penalty={penalty:g} targets={target_labels}",
                        flush=True,
                    )

                first_row = penalty_group.sort_values("fp_target").iloc[0]
                base_row = _benchmark_one_result(
                    version=version,
                    fp_target=float(first_row["fp_target"]),
                    fault=fault,
                    runs=runs,
                    penalty=penalty,
                    actual_fp_rate=float(first_row["actual_fp_rate"]),
                    x7_idx=x7_idx,
                    x11_idx=x11_idx,
                )

                for penalty_row in penalty_group.sort_values("fp_target").itertuples(index=False):
                    fp_target = float(penalty_row.fp_target)
                    key = (version, fp_target, fault)
                    if key in existing:
                        print(f"SKIP existing result: {result_key(version, fp_target, fault)}")
                        continue
                    row = dict(base_row)
                    row["fp_target"] = fp_target
                    row["actual_fp_rate"] = float(penalty_row.actual_fp_rate)
                    row["penalty_used"] = float(penalty_row.penalty)
                    _append_fault_row(row)
                    existing.add(key)
                    print(f"=== {version} {fp_label(fp_target)} {fault} COMPLETE ===")
                    print("CSV appended successfully.")

    overall_df = _aggregate_overall_summary()
    print(f"Overall summary written: {OVERALL_SUMMARY_OUTPUT}")
    print(f"Rows aggregated: {len(overall_df)}")


if __name__ == "__main__":
    main()
