"""TEP industrial-data validation experiment for second-order anomaly detection."""

from __future__ import annotations

import csv
import json
import os
import sys
import unittest
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data" / "raw"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

from task0_protocol import stride_sample
from task3_detectors import (
    _auc_against_baseline,
    _collect_window_features,
    _estimate_covariance,
)

VARIABLE_SPECS = [
    ("XMEAS_7", "reactor pressure"),
    ("XMEAS_8", "reactor level"),
    ("XMEAS_9", "reactor temperature"),
    ("XMEAS_10", "purge rate"),
    ("XMEAS_11", "separator temperature"),
]

FEATURE_INDEX_TO_PAIR = {
    0: (0, 1),
    1: (0, 2),
    2: (0, 3),
    3: (0, 4),
    4: (1, 2),
    5: (1, 3),
    6: (1, 4),
    7: (2, 3),
    8: (2, 4),
    9: (3, 4),
}


def _pair_label(idx: int) -> str:
    """Return a human-readable pair label for a feature index."""

    i, j = FEATURE_INDEX_TO_PAIR[idx]
    return f"{VARIABLE_SPECS[i][0]}-{VARIABLE_SPECS[j][0]}"


def _resolve_dataset_paths(data_dir="."):
    """Resolve the expected Kaggle TEP CSV paths."""

    directory = DATA_ROOT if Path(data_dir) == Path(".") else Path(data_dir)
    training_candidates = [
        directory / "fault_free_training.csv",
        directory / "Fault_Free_Training.csv",
    ]
    testing_candidates = [
        directory / "faulty_testing.csv",
        directory / "Faulty_Testing.csv",
    ]

    training_path = next((path for path in training_candidates if path.exists()), None)
    testing_path = next((path for path in testing_candidates if path.exists()), None)
    return training_path, testing_path


def _read_csv_header(path: Path) -> list[str]:
    """Read just the header row of a CSV file."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def _resolve_variable_columns(header: list[str]) -> list[str] | None:
    """Resolve requested variable names against the CSV header."""

    lower_to_original = {name.lower(): name for name in header}
    resolved = []
    for requested, _description in VARIABLE_SPECS:
        if requested in header:
            resolved.append(requested)
            continue
        lowered = requested.lower()
        if lowered in lower_to_original:
            resolved.append(lower_to_original[lowered])
            continue
        print("列名不匹配，当前CSV列名如下：")
        print(", ".join(header))
        return None
    return resolved


def _stream_first_run(path: Path, selected_columns: list[str], fault_number: int | None = None):
    """Stream a CSV and return the first simulation run, optionally for one fault."""

    values = []
    samples = []
    target_run = None

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_fault = int(float(row["faultNumber"]))
            row_run = int(float(row["simulationRun"]))

            if fault_number is not None and row_fault != fault_number:
                if target_run is not None and row_run != target_run:
                    break
                continue

            if target_run is None:
                target_run = row_run

            if row_run != target_run:
                break

            samples.append(int(float(row["sample"])))
            values.append([float(row[column]) for column in selected_columns])

    if not values:
        raise ValueError(f"No rows found in {path.name} for fault_number={fault_number}.")

    return np.asarray(values, dtype=float), np.asarray(samples, dtype=int), int(target_run)


def _raw_correlation_features(window: np.ndarray) -> np.ndarray:
    """Return raw Pearson correlation upper-triangle features."""

    corr = np.corrcoef(window, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    tri = np.triu_indices(corr.shape[0], k=1)
    return corr[tri]


def _differenced_correlation_features(window: np.ndarray) -> np.ndarray:
    """Return Pearson correlation features after first differencing."""

    diffed = np.diff(window, axis=0)
    corr = np.corrcoef(diffed, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    tri = np.triu_indices(corr.shape[0], k=1)
    return corr[tri]


def _score_features(features: np.ndarray, mu_f: np.ndarray, covariance_inv: np.ndarray) -> np.ndarray:
    """Return Mahalanobis-like squared scores."""

    centered = features - mu_f
    return np.einsum("ij,jk,ik->i", centered, covariance_inv, centered)


def _per_dim_contributions(
    features: np.ndarray, mu_f: np.ndarray, covariance_inv: np.ndarray
) -> np.ndarray:
    """Approximate per-dimension contributions using the precision diagonal."""

    centered = features - mu_f
    return (centered**2) * np.diag(covariance_inv)


def _persistent_trigger(times, alarms, k_persist, fault_onset):
    """Return the first persistent trigger time and detection delay."""

    streak = 0
    for t, alarm in zip(times, alarms):
        if t < fault_onset:
            streak = 0
            continue
        if alarm:
            streak += 1
        else:
            streak = 0
        if streak >= k_persist:
            return int(t), int(t - fault_onset)
    return None, None


def _top_pair_summary(contributions: np.ndarray, sample_times, k_top: int, n_history: int):
    """Summarize post-fault dominant pairs and recent-history dominance."""

    if contributions.size == 0:
        return {
            "mean_contributions": {},
            "top1_pair_counts": {},
            "topk_pair_counts": {},
            "dominant_pair_over_history": None,
            "history_snapshots": [],
        }

    mean_contributions = contributions.mean(axis=0)
    top1_indices = np.argmax(contributions, axis=1)
    topk_indices = np.argsort(contributions, axis=1)[:, ::-1][:, :k_top]

    top1_counts = Counter(int(idx) for idx in top1_indices)
    topk_counts = Counter(int(idx) for idx in topk_indices.reshape(-1))

    dominant_history = []
    for idx, t in enumerate(sample_times):
        start = max(0, idx - n_history + 1)
        recent = top1_indices[start : idx + 1]
        recent_counts = Counter(int(x) for x in recent)
        dominant_idx, dominant_count = recent_counts.most_common(1)[0]
        dominant_history.append(
            {
                "window_end_sample": int(t),
                "dominant_pair": _pair_label(dominant_idx),
                "dominant_count": int(dominant_count),
            }
        )

    dominant_counter = Counter(item["dominant_pair"] for item in dominant_history)
    dominant_pair = dominant_counter.most_common(1)[0][0] if dominant_counter else None

    return {
        "mean_contributions": {
            _pair_label(i): float(value) for i, value in enumerate(mean_contributions)
        },
        "top1_pair_counts": {_pair_label(i): int(c) for i, c in sorted(top1_counts.items())},
        "topk_pair_counts": {_pair_label(i): int(c) for i, c in sorted(topk_counts.items())},
        "dominant_pair_over_history": dominant_pair,
        "history_snapshots": dominant_history[: min(10, len(dominant_history))],
    }


def _run_version(
    normal_data: np.ndarray,
    fault_data: np.ndarray,
    fault_onset: int,
    W: int,
    S: int,
    k_persist: int,
    k_top: int,
    n_history: int,
    feature_fn,
):
    """Run one feature version of the TEP validation experiment."""

    baseline_range = range(0, len(normal_data))
    fault_range = range(0, len(fault_data))

    baseline_times = stride_sample(baseline_range, W, S)
    fault_times = stride_sample(fault_range, W, S)
    pre_fault_times = [t for t in fault_times if t < fault_onset]
    post_fault_times = [t for t in fault_times if t >= fault_onset]

    baseline_features = _collect_window_features(normal_data, baseline_times, W, feature_fn)
    fault_features = _collect_window_features(fault_data, fault_times, W, feature_fn)

    if baseline_features.size == 0:
        raise ValueError("Baseline data do not contain enough windows for the chosen W and S.")
    if len(pre_fault_times) == 0:
        raise ValueError("No pre-fault windows available; reduce W or S.")
    if len(post_fault_times) == 0:
        raise ValueError("No post-fault windows available; reduce W or S.")

    mu_f = baseline_features.mean(axis=0)
    covariance = _estimate_covariance(baseline_features)
    covariance_inv = np.linalg.pinv(covariance + 0.1 * np.eye(baseline_features.shape[1]))
    condition_number = float(np.linalg.cond(covariance))

    baseline_scores = _score_features(baseline_features, mu_f, covariance_inv)
    fault_scores = _score_features(fault_features, mu_f, covariance_inv)
    pre_mask = np.asarray([t < fault_onset for t in fault_times], dtype=bool)
    post_mask = ~pre_mask
    pre_scores = fault_scores[pre_mask]
    post_scores = fault_scores[post_mask]

    theta = float(np.max(pre_scores))
    alarms_all = fault_scores >= theta
    first_alarm_time = next((int(t) for t, alarm in zip(fault_times, alarms_all) if t >= fault_onset and alarm), None)
    persistent_time, detection_delay = _persistent_trigger(
        fault_times, alarms_all, k_persist, fault_onset
    )

    fault_contributions = _per_dim_contributions(fault_features, mu_f, covariance_inv)
    post_contributions = fault_contributions[post_mask]
    pair_summary = _top_pair_summary(post_contributions, post_fault_times, k_top, n_history)

    return {
        "baseline_mu_f": mu_f.tolist(),
        "baseline_condition_number": condition_number,
        "theta": theta,
        "auc_pre_vs_post": float(_auc_against_baseline(pre_scores, post_scores)),
        "fpr_pre": float(np.mean(pre_scores > theta)),
        "mean_score_pre": float(np.mean(pre_scores)),
        "mean_score_post": float(np.mean(post_scores)),
        "first_alarm_window_end_sample": first_alarm_time,
        "persistent_trigger_window_end_sample": persistent_time,
        "detection_delay_samples": detection_delay,
        "n_eff_baseline": int(len(baseline_times)),
        "n_eff_pre_fault": int(len(pre_fault_times)),
        "n_eff_post_fault": int(len(post_fault_times)),
        "fault_times": [int(t) for t in fault_times],
        "fault_scores": fault_scores.tolist(),
        "pre_fault_times": [int(t) for t in pre_fault_times],
        "post_fault_times": [int(t) for t in post_fault_times],
        "pre_fault_scores": pre_scores.tolist(),
        "post_fault_scores": post_scores.tolist(),
        "pair_summary": pair_summary,
    }


def run_tep_validation(
    data_dir=".",
    fault_number=4,
    fault_onset=160,
    W=100,
    S=10,
    K_persist=5,
    k_top=3,
    n_history=10,
):
    """Run the TEP industrial-data validation experiment."""

    training_path, testing_path = _resolve_dataset_paths(data_dir)
    if training_path is None or testing_path is None:
        print("请先从Kaggle下载TEP CSV数据集")
        return None

    header = _read_csv_header(training_path)
    selected_columns = _resolve_variable_columns(header)
    if selected_columns is None:
        return None

    normal_data, normal_samples, normal_run = _stream_first_run(training_path, selected_columns)
    fault_data, fault_samples, fault_run = _stream_first_run(
        testing_path, selected_columns, fault_number=fault_number
    )

    del normal_samples, fault_samples

    versions = {
        "version_A_raw": _run_version(
            normal_data,
            fault_data,
            fault_onset=fault_onset,
            W=W,
            S=S,
            k_persist=K_persist,
            k_top=k_top,
            n_history=n_history,
            feature_fn=_raw_correlation_features,
        ),
        "version_B_differenced": _run_version(
            normal_data,
            fault_data,
            fault_onset=fault_onset,
            W=W,
            S=S,
            k_persist=K_persist,
            k_top=k_top,
            n_history=n_history,
            feature_fn=_differenced_correlation_features,
        ),
    }

    return {
        "data_paths": {
            "fault_free_training": str(training_path),
            "faulty_testing": str(testing_path),
        },
        "selected_variables": [
            {"column": column, "description": description}
            for column, (_, description) in zip(selected_columns, VARIABLE_SPECS)
        ],
        "fault_number": int(fault_number),
        "fault_onset_sample": int(fault_onset),
        "normal_run": int(normal_run),
        "fault_run": int(fault_run),
        "parameters": {
            "W": int(W),
            "S": int(S),
            "K_persist": int(K_persist),
            "k_top": int(k_top),
            "n_history": int(n_history),
        },
        "versions": versions,
    }


def save_tep_validation_figures(results, output_dir="."):
    """Save summary plots and JSON for the TEP validation experiment."""

    output_dir = OUTPUT_ROOT / "trajectories" if output_dir == "." else Path(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    onset = results["fault_onset_sample"]

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for ax, (name, version) in zip(axes, results["versions"].items()):
        times = np.asarray(version["fault_times"], dtype=int)
        scores = np.asarray(version["fault_scores"], dtype=float)
        ax.plot(times, scores, color="tab:blue", linewidth=1.5)
        ax.axhline(version["theta"], color="tab:red", linestyle="--", linewidth=1.2, label="theta")
        ax.axvline(onset, color="black", linestyle="--", linewidth=1.2, label="fault onset")
        if version["persistent_trigger_window_end_sample"] is not None:
            ax.axvline(
                version["persistent_trigger_window_end_sample"],
                color="tab:green",
                linestyle=":",
                linewidth=1.2,
                label="persistent trigger",
            )
        ax.set_ylabel("score")
        ax.set_title(
            f"{name}: AUC={version['auc_pre_vs_post']:.3f}, "
            f"delay={version['detection_delay_samples']}"
        )
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left")
    axes[-1].set_xlabel("window end sample")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "tep_validation_scores.png"), dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for ax, (name, version) in zip(axes, results["versions"].items()):
        labels = list(version["pair_summary"]["mean_contributions"].keys())
        values = list(version["pair_summary"]["mean_contributions"].values())
        ax.bar(labels, values, color="tab:orange", alpha=0.85)
        ax.set_ylabel("mean contrib")
        ax.set_title(
            f"{name}: dominant={version['pair_summary']['dominant_pair_over_history']}"
        )
        ax.grid(axis="y", alpha=0.3)
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "tep_validation_pair_contributions.png"), dpi=150)
    plt.close(fig)

    summary_rows = []
    for name, version in results["versions"].items():
        summary_rows.append(
            {
                "version": name,
                "auc_pre_vs_post": version["auc_pre_vs_post"],
                "theta": version["theta"],
                "fpr_pre": version["fpr_pre"],
                "mean_score_pre": version["mean_score_pre"],
                "mean_score_post": version["mean_score_post"],
                "persistent_trigger_window_end_sample": version[
                    "persistent_trigger_window_end_sample"
                ],
                "detection_delay_samples": version["detection_delay_samples"],
                "n_eff_baseline": version["n_eff_baseline"],
                "n_eff_pre_fault": version["n_eff_pre_fault"],
                "n_eff_post_fault": version["n_eff_post_fault"],
                "dominant_pair_over_history": version["pair_summary"][
                    "dominant_pair_over_history"
                ],
            }
        )

    with open(
        os.path.join(output_dir, "tep_validation_summary.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)

    with open(
        os.path.join(output_dir, "tep_validation_summary.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)


class TepValidationUnitTests(unittest.TestCase):
    def test_raw_feature_dimension_is_ten(self):
        window = np.arange(500, dtype=float).reshape(100, 5)
        feature = _raw_correlation_features(window)
        self.assertEqual(feature.shape, (10,))

    def test_differenced_feature_dimension_is_ten(self):
        window = np.arange(500, dtype=float).reshape(100, 5)
        feature = _differenced_correlation_features(window)
        self.assertEqual(feature.shape, (10,))

    def test_case_insensitive_column_resolution(self):
        header = ["faultNumber", "simulationRun", "sample", "xmeas_7", "xmeas_8", "xmeas_9", "xmeas_10", "xmeas_11"]
        resolved = _resolve_variable_columns(header)
        self.assertEqual(resolved, ["xmeas_7", "xmeas_8", "xmeas_9", "xmeas_10", "xmeas_11"])

    def test_persistent_trigger_requires_k_consecutive_alarms(self):
        times = [150, 160, 170, 180, 190, 200]
        alarms = [False, True, True, True, True, True]
        trigger_time, delay = _persistent_trigger(times, alarms, 5, 160)
        self.assertEqual(trigger_time, 200)
        self.assertEqual(delay, 40)


def main():
    """Run the TEP validation experiment from the command line."""

    results = run_tep_validation()
    if results is None:
        return
    save_tep_validation_figures(results)

    for version_name, version in results["versions"].items():
        print(version_name)
        print(
            f"  AUC={version['auc_pre_vs_post']:.3f} "
            f"theta={version['theta']:.3f} "
            f"delay={version['detection_delay_samples']}"
        )
        print(
            f"  pre_mean={version['mean_score_pre']:.3f} "
            f"post_mean={version['mean_score_post']:.3f} "
            f"dominant_pair={version['pair_summary']['dominant_pair_over_history']}"
        )


if __name__ == "__main__":
    main()
