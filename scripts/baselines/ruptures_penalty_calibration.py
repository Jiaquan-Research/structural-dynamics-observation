"""Calibrate ruptures penalties on NORMAL runs."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ruptures_benchmark_common import (
    CSV_OUTPUT_DIR,
    FP_TARGETS,
    N_RUNS,
    PENALTY_CANDIDATES,
    PENALTY_TABLE_OUTPUT,
    VERSIONS,
    evaluate_run,
    fp_label,
    load_metadata,
    load_normal_run_arrays,
)


def _calibrate_version(
    normal_runs: dict[int, np.ndarray],
    version: str,
    x7_idx: int,
    x11_idx: int,
) -> tuple[dict[float, float], dict[float, float]]:
    selected_runs = {run_id: normal_runs[run_id] for run_id in sorted(normal_runs)[:N_RUNS]}
    false_alarm_counts = {float(penalty): 0 for penalty in PENALTY_CANDIDATES}
    processed_runs = 0

    for run_idx, run_data in enumerate(selected_runs.values(), start=1):
        results = evaluate_run(run_data, version, PENALTY_CANDIDATES, x7_idx, x11_idx)
        for penalty, (detected, _delay) in results.items():
            false_alarm_counts[float(penalty)] += int(bool(detected))
        processed_runs += 1
        if run_idx % 50 == 0 or run_idx == len(selected_runs):
            print(f"[{version} calibration] run {run_idx} / {len(selected_runs)}", flush=True)

    if processed_runs == 0:
        raise ValueError(f"No NORMAL runs available for {version} calibration.")

    fp_rates = {
        float(penalty): float(count / processed_runs)
        for penalty, count in false_alarm_counts.items()
    }
    selected = {}
    for target in FP_TARGETS:
        selected[float(target)] = min(
            fp_rates,
            key=lambda penalty: (abs(fp_rates[penalty] - float(target)), -float(penalty)),
        )
    return selected, fp_rates


def main() -> None:
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _testing_path, selected_columns, _usecols, x7_idx, x11_idx = load_metadata()
    normal_runs = load_normal_run_arrays(selected_columns)

    rows = []
    print("=== PENALTY CALIBRATION ===")
    print("")
    for version in ("Version A", "Version B"):
        selected, fp_rates = _calibrate_version(normal_runs, version, x7_idx, x11_idx)
        print(f"{version}:")
        for target in FP_TARGETS:
            penalty = float(selected[float(target)])
            actual_fp = float(fp_rates[penalty])
            rows.append(
                {
                    "version": version,
                    "fp_target": float(target),
                    "penalty": penalty,
                    "actual_fp_rate": actual_fp,
                    "detector_type": VERSIONS[version]["detector_type"],
                }
            )
            print(
                f"  penalty for FP~{int(target * 100)}%: "
                f"penalty={penalty:g} actual_fp={actual_fp:.6f}"
            )
        print("")

    pd.DataFrame(rows).to_csv(PENALTY_TABLE_OUTPUT, index=False)
    print("=== PENALTY CALIBRATION COMPLETE ===")
    print(f"Generated file: {PENALTY_TABLE_OUTPUT}")


if __name__ == "__main__":
    main()
