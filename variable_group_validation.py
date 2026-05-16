"""Physical-locality variable-group validation for F13 concentration."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import _load_normal_runs
from tep_experiment import (
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _resolve_paths,
)

W = 100
S = 100
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
N_RUNS = 200
SOFTMAX_T = 1.0

VARIABLE_GROUPS = {
    "V5_orig": ["xmeas_7", "xmeas_8", "xmeas_9", "xmeas_10", "xmeas_11"],
    "V5_new1": ["xmeas_1", "xmeas_2", "xmeas_3", "xmeas_4", "xmeas_5"],
    "V5_new2": ["xmeas_14", "xmeas_15", "xmeas_16", "xmeas_17", "xmeas_18"],
}


def _resolve_variable_columns(columns, requested_columns):
    lower_to_original = {column.lower(): column for column in columns}
    resolved = []
    for requested in requested_columns:
        lowered = requested.lower()
        if lowered in lower_to_original:
            resolved.append(lower_to_original[lowered])
            continue
        raise KeyError(f"Missing requested column: {requested}")
    return resolved


def _prepare_run_arrays(run_frames, selected_columns, n_runs=N_RUNS):
    arrays = {}
    for run_idx in range(1, n_runs + 1):
        run_df = run_frames.get(run_idx)
        if run_df is None:
            continue
        arrays[int(run_idx)] = run_df[selected_columns].to_numpy(dtype=float)
    return arrays


def _softmax_rows(values, temperature=1.0):
    values = np.asarray(values, dtype=float) / float(temperature)
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)


def _mean_top1_mass(run_arrays, baseline_model):
    top1_masses = []
    for run_idx in range(1, N_RUNS + 1):
        run_data = run_arrays.get(run_idx)
        if run_data is None:
            continue
        try:
            series = _compute_version_b_trajectory_series(
                run_data,
                W,
                S,
                K_TOP,
                N_HISTORY,
                baseline_model,
            )
        except ValueError:
            continue
        sample_times = np.asarray(series["sample_times"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        if not np.any(mask):
            continue
        contributions = np.asarray(series["per_pair_contribution"], dtype=float)[mask]
        probs = _softmax_rows(contributions, temperature=SOFTMAX_T)
        top1_masses.append(np.max(probs, axis=1))
    if not top1_masses:
        raise ValueError("No valid windows produced.")
    return float(np.mean(np.concatenate(top1_masses, axis=0)))


def _load_group_data(training_path, testing_path, requested_columns):
    header = pd.read_csv(training_path, nrows=0).columns.tolist()
    selected_columns = _resolve_variable_columns(header, requested_columns)

    baseline_df = pd.read_csv(training_path, usecols=selected_columns)
    baseline_data = baseline_df[selected_columns].to_numpy(dtype=float)

    normal_runs = _load_normal_runs(".", selected_columns)
    normal_arrays = _prepare_run_arrays(normal_runs, selected_columns, N_RUNS)

    usecols = ["faultNumber", "simulationRun", "sample", *selected_columns]
    f13_runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=13)
    f13_arrays = _prepare_run_arrays(f13_runs, selected_columns, N_RUNS)

    return baseline_data, normal_arrays, f13_arrays


def main():
    training_path, testing_path = _resolve_paths(".")
    if training_path is None or testing_path is None:
        print("请先从Kaggle下载TEP CSV数据集")
        return None

    print("variable_group  fault   mean_top1_mass")
    results = []

    for group_name, requested_columns in VARIABLE_GROUPS.items():
        baseline_data, normal_arrays, f13_arrays = _load_group_data(
            training_path,
            testing_path,
            requested_columns,
        )
        baseline_model = _build_baseline_model(baseline_data, W, S)

        normal_mass = _mean_top1_mass(normal_arrays, baseline_model)
        f13_mass = _mean_top1_mass(f13_arrays, baseline_model)

        print(f"{group_name:<14} NORMAL  {normal_mass:.3f}")
        print(f"{group_name:<14} F13     {f13_mass:.3f}")

        results.append((group_name, "NORMAL", normal_mass))
        results.append((group_name, "F13", f13_mass))

    print()
    print("解读标准：")
    print("若多个工艺区域的F13 concentration > 0.3：")
    print("  支持：F13更接近系统级状态空间shift")
    print("  而非单一区域局部artifact")
    print("若仅V5_orig高，其他区域接近NORMAL：")
    print("  说明concentration可能是局部变量artifact")
    print("注意：本实验仍属手工变量组验证，")
    print("  不能替代random subset robustness audit")

    return results


if __name__ == "__main__":
    main()
