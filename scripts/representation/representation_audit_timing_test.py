"""Timing test for extending representation audit to 500 runs per fault."""

from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from tep_experiment import (
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
K_TOP = 3
N_HISTORY = 10
FAULT_NUMBER = 6
N_RUNS = 500


def _run_lengths(sequence: list[str]) -> list[int]:
    if not sequence:
        return []
    lengths = []
    current = sequence[0]
    count = 1
    for item in sequence[1:]:
        if item == current:
            count += 1
        else:
            lengths.append(count)
            current = item
            count = 1
    lengths.append(count)
    return lengths


def _run_metrics(run_id: int, dominant_pairs: list[str]) -> dict[str, object]:
    counts = Counter(dominant_pairs)
    total = len(dominant_pairs)
    freqs = np.asarray(list(counts.values()), dtype=float) / float(total)
    dominant_pair, dominant_count = counts.most_common(1)[0]
    lengths = _run_lengths(dominant_pairs)
    return {
        "run_id": int(run_id),
        "occupancy": float(dominant_count / total),
        "entropy": float(scipy_entropy(freqs)),
        "mean_run_length": float(np.mean(lengths)),
        "dominant_pair": dominant_pair,
    }


def main() -> None:
    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(np.asarray(baseline_data, dtype=float), WINDOW, STEP)

    runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=FAULT_NUMBER)
    selected_run_ids = sorted(runs)[:N_RUNS]
    metrics = []

    t_start = time.time()
    for run_id in selected_run_ids:
        run_df = runs[run_id].sort_values("sample")
        run_data = run_df[selected_columns].to_numpy(dtype=float)
        series = _compute_version_b_trajectory_series(
            run_data,
            WINDOW,
            STEP,
            K_TOP,
            N_HISTORY,
            baseline_model,
        )
        sample_times = np.asarray(series["sample_times"], dtype=int)
        mask = sample_times > SAMPLE_FILTER
        top1_indices = np.asarray(series["top1_indices"], dtype=int)[mask]
        dominant_pairs = [PAIR_LABELS[int(idx)] for idx in top1_indices]
        if dominant_pairs:
            metrics.append(_run_metrics(run_id, dominant_pairs))
    t_end = time.time()

    completed = len(metrics)
    elapsed = t_end - t_start
    metrics_df = pd.DataFrame(metrics)

    print("=== TIMING TEST ===")
    print("Fault: F06")
    print(f"Runs completed: {completed}")
    print(f"Total time: {elapsed:.1f} seconds")
    print(f"Per-run average: {elapsed / max(completed, 1):.3f} seconds")
    print("Estimated total (20 faults x 500 runs):")
    print(f"  {elapsed * 20 / 60:.1f} minutes")
    print(f"  {elapsed * 20 / 3600:.2f} hours")
    print("")
    print("=== F06 SAMPLE OUTPUT (first 5 runs) ===")
    print(metrics_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
