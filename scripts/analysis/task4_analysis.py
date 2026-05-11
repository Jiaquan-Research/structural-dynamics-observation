"""Comparison analysis and visualization for experiment one."""

from __future__ import annotations

import csv
import os
import unittest

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_auc_score

from task0_protocol import split_data
from task1_data_generator import generate_data
from task2_single_sensor import run_single_sensor_detector
from task3_detectors import (
    _roc_curve_from_scores,
    run_mahalanobis_detector,
    run_ocsvm_detector,
    run_pca_detector,
)


def _calibration_stride_labels(calibration_range, anomaly_start, W, S, condition):
    """Construct calibration labels on stride sample times."""

    sample_times = np.asarray([], dtype=int)
    if len(calibration_range) >= W:
        sample_times = np.asarray(
            list(range(calibration_range.start + W, calibration_range.stop, S)),
            dtype=int,
        )
    if condition == "A":
        labels = np.zeros(sample_times.shape[0], dtype=int)
    else:
        labels = (sample_times > anomaly_start).astype(int)
        if sample_times.size > 0 and np.all(sample_times > anomaly_start):
            labels = np.ones(sample_times.shape[0], dtype=int)
    return labels


def paired_bootstrap_auc(
    baseline_scores_a,
    test_scores_a,
    baseline_scores_b,
    test_scores_b,
    n_bootstrap=1000,
):
    """Paired bootstrap comparison between two ROC AUC values."""

    baseline_scores_a = np.asarray(baseline_scores_a, dtype=float)
    test_scores_a = np.asarray(test_scores_a, dtype=float)
    baseline_scores_b = np.asarray(baseline_scores_b, dtype=float)
    test_scores_b = np.asarray(test_scores_b, dtype=float)

    if len(baseline_scores_a) != len(baseline_scores_b):
        raise ValueError("baseline score arrays must have the same length.")
    if len(test_scores_a) != len(test_scores_b):
        raise ValueError("test score arrays must have the same length.")

    rng = np.random.default_rng(0)

    def _auc(baseline_scores, test_scores):
        y_true = np.concatenate(
            [
                np.zeros(len(baseline_scores), dtype=int),
                np.ones(len(test_scores), dtype=int),
            ]
        )
        y_score = np.concatenate([baseline_scores, test_scores])
        return float(roc_auc_score(y_true, y_score))

    observed_a = _auc(baseline_scores_a, test_scores_a)
    observed_b = _auc(baseline_scores_b, test_scores_b)
    observed_delta = observed_a - observed_b

    baseline_n = len(baseline_scores_a)
    test_n = len(test_scores_a)
    deltas = np.empty(n_bootstrap, dtype=float)

    for idx in range(n_bootstrap):
        baseline_idx = rng.integers(0, baseline_n, size=baseline_n)
        test_idx = rng.integers(0, test_n, size=test_n)
        auc_a = _auc(baseline_scores_a[baseline_idx], test_scores_a[test_idx])
        auc_b = _auc(baseline_scores_b[baseline_idx], test_scores_b[test_idx])
        deltas[idx] = auc_a - auc_b

    p_value = float(np.mean(np.abs(deltas) >= abs(observed_delta)))
    return {
        "delta_auc": float(observed_delta),
        "delta_auc_std": float(np.std(deltas, ddof=1)),
        "p_value": p_value,
        "significant": bool(p_value < 0.05),
    }


def run_experiment_one(T=2000, W=100, S=20, rho=0.4, seed=42, n_bootstrap=1000):
    """Run the full experiment-one evaluation across conditions A-E."""

    conditions = ["A", "B", "C", "D", "E"]
    baseline_range, calibration_range, test_range = split_data(T)

    single_sensor = {}
    mahalanobis_results = {}
    pca_results = {}
    ocsvm_results = {}
    mahalanobis_auc = {}
    pca_auc = {}
    ocsvm_auc = {}
    calibration_labels = {}

    for condition in conditions:
        data, metadata = generate_data(condition, T=T, rho=rho, seed=seed)
        single_sensor[condition] = run_single_sensor_detector(data, metadata)
        calibration_labels[condition] = _calibration_stride_labels(
            calibration_range,
            metadata["anomaly_start"],
            W,
            S,
            condition,
        )

        mahalanobis_results[condition] = run_mahalanobis_detector(
            data, baseline_range, calibration_range, test_range, W=W, S=S
        )
        pca_results[condition] = run_pca_detector(
            data, baseline_range, calibration_range, test_range, W=W, S=S
        )
        ocsvm_results[condition] = run_ocsvm_detector(
            data, baseline_range, calibration_range, test_range, W=W, S=S
        )

        mahalanobis_auc[condition] = mahalanobis_results[condition]["auc_test"]
        pca_auc[condition] = pca_results[condition]["auc_test"]
        ocsvm_auc[condition] = ocsvm_results[condition]["auc_test"]

    bootstrap_B_vs_C = paired_bootstrap_auc(
        mahalanobis_results["B"]["scores_baseline"],
        mahalanobis_results["B"]["d2_test"],
        mahalanobis_results["C"]["scores_baseline"],
        mahalanobis_results["C"]["d2_test"],
        n_bootstrap=n_bootstrap,
    )
    bootstrap_B_vs_D = paired_bootstrap_auc(
        mahalanobis_results["B"]["scores_baseline"],
        mahalanobis_results["B"]["d2_test"],
        mahalanobis_results["D"]["scores_baseline"],
        mahalanobis_results["D"]["d2_test"],
        n_bootstrap=n_bootstrap,
    )
    bootstrap_B_vs_baseline1 = paired_bootstrap_auc(
        mahalanobis_results["B"]["scores_baseline"],
        mahalanobis_results["B"]["d2_test"],
        pca_results["B"]["scores_baseline"],
        pca_results["B"]["scores_test"],
        n_bootstrap=n_bootstrap,
    )
    bootstrap_B_vs_baseline2 = paired_bootstrap_auc(
        mahalanobis_results["B"]["scores_baseline"],
        mahalanobis_results["B"]["d2_test"],
        ocsvm_results["B"]["scores_baseline"],
        ocsvm_results["B"]["scores_test"],
        n_bootstrap=n_bootstrap,
    )

    stride_values = [1, 10, 20, 50]
    auc_values = []
    data_b, _ = generate_data("B", T=T, rho=rho, seed=seed)
    for stride in stride_values:
        stride_result = run_mahalanobis_detector(
            data_b, baseline_range, calibration_range, test_range, W=W, S=stride
        )
        auc_values.append(float(stride_result["auc_test"]))

    return {
        "conditions": conditions,
        "single_sensor": single_sensor,
        "mahalanobis_auc": mahalanobis_auc,
        "pca_auc": pca_auc,
        "ocsvm_auc": ocsvm_auc,
        "bootstrap_B_vs_C": bootstrap_B_vs_C,
        "bootstrap_B_vs_D": bootstrap_B_vs_D,
        "bootstrap_B_vs_baseline1": bootstrap_B_vs_baseline1,
        "bootstrap_B_vs_baseline2": bootstrap_B_vs_baseline2,
        "stride_sensitivity": {
            "stride_values": stride_values,
            "auc_values": auc_values,
        },
        "mahalanobis_results": mahalanobis_results,
        "pca_results": pca_results,
        "ocsvm_results": ocsvm_results,
        "calibration_labels": calibration_labels,
        "config": {
            "T": T,
            "W": W,
            "S": S,
            "rho": rho,
            "seed": seed,
            "n_bootstrap": n_bootstrap,
        },
    }


def save_experiment_one_figures(results, output_dir="."):
    """Save ROC, AUC comparison, stride sensitivity, and CSV outputs."""

    os.makedirs(output_dir, exist_ok=True)
    conditions = ["B", "C", "D", "E"]

    fig, axes = plt.subplots(4, 1, figsize=(10, 16))
    for ax, condition in zip(axes, conditions):
        mah = results["mahalanobis_results"][condition]
        pca = results["pca_results"][condition]
        ocsvm = results["ocsvm_results"][condition]

        mah_fpr, mah_tpr = _roc_curve_from_scores(mah["scores_baseline"], mah["d2_test"])
        pca_fpr, pca_tpr = _roc_curve_from_scores(
            pca["scores_baseline"], pca["scores_test"]
        )
        ocsvm_fpr, ocsvm_tpr = _roc_curve_from_scores(
            ocsvm["scores_baseline"], ocsvm["scores_test"]
        )

        ax.plot(mah_fpr, mah_tpr, label=f"Mahalanobis AUC={mah['auc_test']:.3f}")
        ax.plot(pca_fpr, pca_tpr, label=f"PCA AUC={pca['auc_test']:.3f}")
        ax.plot(ocsvm_fpr, ocsvm_tpr, label=f"OCSVM AUC={ocsvm['auc_test']:.3f}")
        ax.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1.0)
        ax.set_title(f"Condition {condition}")
        ax.set_xlabel("False positive rate")
        ax.set_ylabel("True positive rate")
        ax.legend(loc="lower right")
        ax.grid(alpha=0.3)

    fig.suptitle(
        "ROC Curves for Conditions B-E\n"
        f"Condition A Mahalanobis D2: baseline mean="
        f"{results['mahalanobis_results']['A']['d2_baseline'].mean():.3f}, "
        f"test mean={results['mahalanobis_results']['A']['d2_test'].mean():.3f}, "
        f"AUC={results['mahalanobis_auc']['A']:.3f}",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(os.path.join(output_dir, "task4_roc_curves.png"), dpi=150)
    plt.close(fig)

    detectors = ["Mahalanobis", "PCA", "OCSVM"]
    detector_to_auc = {
        "Mahalanobis": results["mahalanobis_auc"],
        "PCA": results["pca_auc"],
        "OCSVM": results["ocsvm_auc"],
    }
    x = np.arange(len(conditions))
    width = 0.22

    fig, ax = plt.subplots(figsize=(10, 6))
    bar_containers = []
    for idx, detector in enumerate(detectors):
        aucs = [detector_to_auc[detector][condition] for condition in conditions]
        bars = ax.bar(x + (idx - 1) * width, aucs, width=width, label=detector)
        bar_containers.append(bars)

    ax.axhline(0.75, color="black", linestyle="--", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(conditions)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("AUC")
    ax.set_title("Detector AUC Comparison")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    if results["bootstrap_B_vs_C"]["significant"]:
        ax.text(x[1] - width, detector_to_auc["Mahalanobis"]["C"] + 0.03, "*", ha="center")
    if results["bootstrap_B_vs_D"]["significant"]:
        ax.text(x[2] - width, detector_to_auc["Mahalanobis"]["D"] + 0.03, "*", ha="center")
    if results["bootstrap_B_vs_baseline1"]["significant"]:
        ax.text(x[0], detector_to_auc["PCA"]["B"] + 0.03, "*", ha="center")
    if results["bootstrap_B_vs_baseline2"]["significant"]:
        ax.text(x[0] + width, detector_to_auc["OCSVM"]["B"] + 0.03, "*", ha="center")

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "task4_auc_comparison.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        results["stride_sensitivity"]["stride_values"],
        results["stride_sensitivity"]["auc_values"],
        marker="o",
    )
    ax.set_xscale("log")
    ax.set_xticks(results["stride_sensitivity"]["stride_values"])
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("stride")
    ax.set_ylabel("Mahalanobis AUC")
    ax.set_title("Stride Sensitivity on Condition B")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "task4_stride_sensitivity.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "task4_results.csv")
    bootstrap_lookup = {
        ("B", "Mahalanobis"): "",
        ("C", "Mahalanobis"): results["bootstrap_B_vs_C"]["p_value"],
        ("D", "Mahalanobis"): results["bootstrap_B_vs_D"]["p_value"],
        ("B", "PCA"): results["bootstrap_B_vs_baseline1"]["p_value"],
        ("B", "OCSVM"): results["bootstrap_B_vs_baseline2"]["p_value"],
    }
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["condition", "detector", "auc", "bootstrap_pvalue"])
        for condition in results["conditions"]:
            for detector, auc_map in detector_to_auc.items():
                writer.writerow(
                    [
                        condition,
                        detector,
                        auc_map[condition],
                        bootstrap_lookup.get((condition, detector), ""),
                    ]
                )


class ExperimentOneTests(unittest.TestCase):
    def test_condition_a_mahalanobis_auc_is_near_chance(self):
        results = run_experiment_one(n_bootstrap=100)
        self.assertGreaterEqual(results["mahalanobis_auc"]["A"], 0.3)
        self.assertLessEqual(results["mahalanobis_auc"]["A"], 0.7)

    def test_condition_b_mahalanobis_auc_exceeds_threshold(self):
        results = run_experiment_one(n_bootstrap=100)
        self.assertGreater(results["mahalanobis_auc"]["B"], 0.7)

    def test_bootstrap_deltas_for_b_vs_c_and_d_are_positive(self):
        results = run_experiment_one(n_bootstrap=100)
        self.assertGreater(results["bootstrap_B_vs_C"]["delta_auc"], 0.0)
        self.assertGreater(results["bootstrap_B_vs_D"]["delta_auc"], 0.0)

    def test_stride_sensitivity_contains_four_auc_values(self):
        results = run_experiment_one(n_bootstrap=100)
        self.assertEqual(len(results["stride_sensitivity"]["auc_values"]), 4)


if __name__ == "__main__":
    unittest.main()
