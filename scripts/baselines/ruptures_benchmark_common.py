"""Shared helpers for ruptures baseline benchmark scripts."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import ruptures as rpt
except ImportError:
    raise ImportError("pip install ruptures")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import _load_normal_runs
from tep_experiment import _load_all_fault_runs, _load_baseline_and_columns

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
K_PERSIST = 3

N_RUNS = 500
FAULT_NUMBERS = list(range(1, 21))

ROLLING_WINDOW = 100

FP_TARGETS = [0.01, 0.05]
PENALTY_CANDIDATES = [1, 2, 5, 10, 20, 50, 100, 200, 500]

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
PENALTY_TABLE_OUTPUT = CSV_OUTPUT_DIR / "ruptures_penalty_table.csv"
FAULT_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "ruptures_baseline_fault_summary.csv"
OVERALL_SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "ruptures_baseline_overall_summary.csv"
RATE_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "ruptures_detection_rate.png"
OPERATING_PLOT_OUTPUT = TAXONOMY_OUTPUT_DIR / "ruptures_operating_points.png"
PCA_OVERALL_SUMMARY = CSV_OUTPUT_DIR / "pca_baseline_overall_summary.csv"
TOP1_OVERALL_SUMMARY = CSV_OUTPUT_DIR / "top1_mass_overall_summary.csv"

VERSIONS = {
    "Version A": {
        "short": "A",
        "display": "Version A (raw signal)",
        "detector_type": "ruptures_raw",
    },
    "Version B": {
        "short": "B",
        "display": "Version B (rolling corr)",
        "detector_type": "ruptures_rolling_corr",
    },
}


def fault_label(fault_number: int) -> str:
    return f"F{int(fault_number):02d}"


def fp_label(fp_target: float) -> str:
    return "FP1%" if abs(float(fp_target) - 0.01) < 1e-12 else "FP5%"


def result_key(version: str, fp_target: float, fault: str) -> str:
    return f"Version_{VERSIONS[version]['short']}_{fp_label(fp_target).replace('%', '')}_{fault}"


def normalize_column_name(name: str) -> str:
    return str(name).replace("_", "").replace(" ", "").lower()


def find_column_index(selected_columns: list[str], target: str) -> int:
    normalized_target = normalize_column_name(target)
    for idx, column in enumerate(selected_columns):
        if normalize_column_name(column) == normalized_target:
            return int(idx)
    raise ValueError(f"Column {target} not found in selected columns: {selected_columns}")


def runs_to_arrays(run_frames: dict[int, pd.DataFrame], selected_columns: list[str]) -> dict[int, np.ndarray]:
    arrays = {}
    for run_id, run_df in run_frames.items():
        arrays[int(run_id)] = run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
    return arrays


def load_metadata() -> tuple[Path, list[str], list[str], int, int]:
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")

    _training_path, testing_path, selected_columns, usecols, _baseline_data = loaded
    x7_idx = find_column_index(selected_columns, "XMEAS7")
    x11_idx = find_column_index(selected_columns, "XMEAS11")
    return testing_path, selected_columns, usecols, x7_idx, x11_idx


def load_normal_run_arrays(selected_columns: list[str]) -> dict[int, np.ndarray]:
    normal_frames = _load_normal_runs(".", selected_columns)
    return runs_to_arrays(normal_frames, selected_columns)


def load_fault_run_arrays(
    testing_path: Path,
    usecols: list[str],
    selected_columns: list[str],
    fault_number: int,
) -> dict[int, np.ndarray]:
    fault_frames = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
    return runs_to_arrays(fault_frames, selected_columns)


def version_a_signal(run_data: np.ndarray, x7_idx: int, x11_idx: int) -> np.ndarray:
    return np.column_stack([run_data[:, x7_idx], run_data[:, x11_idx]])


def version_b_signal(run_data: np.ndarray, x7_idx: int, x11_idx: int) -> np.ndarray | None:
    rolling_corr = pd.Series(run_data[:, x7_idx]).rolling(ROLLING_WINDOW).corr(
        pd.Series(run_data[:, x11_idx])
    )
    signal = rolling_corr.dropna().to_numpy(dtype=float).reshape(-1, 1)
    if len(signal) < 50:
        return None
    if not np.all(np.isfinite(signal)):
        return None
    if float(np.std(signal)) < 1e-8:
        return None
    return signal


def build_signal(
    run_data: np.ndarray,
    version: str,
    x7_idx: int,
    x11_idx: int,
) -> tuple[np.ndarray | None, int]:
    if version == "Version A":
        return version_a_signal(run_data, x7_idx, x11_idx), 0
    if version == "Version B":
        return version_b_signal(run_data, x7_idx, x11_idx), ROLLING_WINDOW - 1
    raise ValueError(f"Unknown version: {version}")


def fit_predict_breakpoints(signal: np.ndarray, penalties: list[float]) -> dict[float, list[int]]:
    breakpoints_by_penalty = {}
    algo = rpt.Pelt(model="rbf").fit(signal)
    for penalty in penalties:
        try:
            breakpoints = algo.predict(pen=float(penalty))
        except Exception:
            breakpoints = []
        valid_breakpoints = [int(cp) for cp in breakpoints if int(cp) < len(signal)]
        breakpoints_by_penalty[float(penalty)] = valid_breakpoints
    return breakpoints_by_penalty


def detection_from_breakpoints(
    breakpoints: list[int],
    offset: int,
) -> tuple[bool, float]:
    adjusted = sorted(int(cp) + int(offset) for cp in breakpoints)
    valid = [cp for cp in adjusted if cp > SAMPLE_FILTER]
    if not valid:
        return False, float("nan")
    first = int(valid[0])
    return True, float((first - SAMPLE_FILTER) // STEP)


def evaluate_run(
    run_data: np.ndarray,
    version: str,
    penalties: list[float],
    x7_idx: int,
    x11_idx: int,
) -> dict[float, tuple[bool, float]]:
    signal, offset = build_signal(run_data, version, x7_idx, x11_idx)
    if signal is None:
        return {float(penalty): (False, float("nan")) for penalty in penalties}
    try:
        breakpoints_by_penalty = fit_predict_breakpoints(signal, penalties)
    except Exception:
        return {float(penalty): (False, float("nan")) for penalty in penalties}
    return {
        float(penalty): detection_from_breakpoints(breakpoints, offset)
        for penalty, breakpoints in breakpoints_by_penalty.items()
    }


def conservative_interpretation_lines() -> list[str]:
    return [
        "Conservative interpretation:",
        "1. Version A detects distributional changepoints in raw signals.",
        "2. Version B detects changepoints in coupling statistics.",
        "3. Neither detector is a geometry locking detector.",
        "4. Results are only for operating regime comparison.",
        "5. Results are not used for causal claims.",
        (
            "6. ruptures structurally favors piecewise-stationary regime changes, "
            "not persistent geometry concentration."
        ),
    ]
