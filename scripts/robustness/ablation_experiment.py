"""Ablation experiment isolating baseline-length effects on Mahalanobis AUC."""

from __future__ import annotations

import csv
import os
import unittest

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import select_threshold, stride_sample
from task1_data_generator import generate_data
from task3_detectors import (
    _auc_against_baseline,
    _collect_window_features,
    _estimate_covariance,
    _upper_triangle_features,
)


def _safe_threshold(scores):
    """Select a threshold with a fallback for single-class calibration labels."""

    scores = np.asarray(scores, dtype=float)
    if scores.size == 0:
        raise ValueError("calibration scores must be non-empty.")
    labels = np.ones(scores.shape[0], dtype=int)
    if np.unique(labels).size < 2:
        return float(np.max(scores))
    return float(select_threshold(scores, labels, method="f1_max"))


def _baseline_features_for_length(normal_data, L, W, S):
    """Collect baseline features with a minimal fallback when L < W."""

    baseline_range = range(0, L)
    baseline_times = stride_sample(baseline_range, W, S)
    if baseline_times:
        return _collect_window_features(normal_data, baseline_times, W, _upper_triangle_features)

    # When L < W, there is no legal W-step window inside the first L steps.
    # Use the earliest available W-step window as an insufficient-experience proxy.
    if normal_data.shape[0] < W:
        raise ValueError("normal_data must be at least as long as W.")
    return _collect_window_features(normal_data, [W], W, _upper_triangle_features)


def run_ablation(rho=0.10, W=100, S=20, n_repeats=100, seed_base=0):
    """Run the fixed-T ablation isolating baseline-length effects."""

    L_values = [50, 100, 200, 500, 1000, 2000, 3000]
    results = {}

    calibration_range = range(0, 400)
    test_range = range(400, 1200)
    test_offset = calibration_range.stop

    for L in L_values:
        print(f"L={L} running ({n_repeats} repeats)...")
        aucs = []
        condition_numbers = []
        fprs = []

        for repeat_idx in range(n_repeats):
            seed = seed_base + repeat_idx
            normal_data, _ = generate_data("A", T=4000, seed=seed)
            anomaly_data, _ = generate_data("B", T=1200, rho=rho, seed=seed)

            baseline_features = _baseline_features_for_length(normal_data, L, W, S)
            mu_f = baseline_features.mean(axis=0)
            S_f = _estimate_covariance(baseline_features)
            S_f_inv = np.linalg.pinv(S_f + 0.1 * np.eye(10))
            condition_number = float(np.linalg.cond(S_f))
            if not np.isfinite(condition_number):
                condition_number = 1e6

            calibration_times = stride_sample(calibration_range, W, S)
            calibration_features = _collect_window_features(
                anomaly_data, calibration_times, W, _upper_triangle_features
            )
            test_times = stride_sample(test_range, W, S)
            test_features = _collect_window_features(
                anomaly_data, test_times, W, _upper_triangle_features
            )

            def mahal_sq(features):
                centered = features - mu_f
                return np.einsum("ij,jk,ik->i", centered, S_f_inv, centered)

            d2_calibration = mahal_sq(calibration_features)
            d2_test = mahal_sq(test_features)
            theta = _safe_threshold(d2_calibration)
            auc = _auc_against_baseline(d2_calibration, d2_test)
            fpr = float(np.mean(d2_calibration > theta))

            aucs.append(float(auc))
            condition_numbers.append(condition_number)
            fprs.append(fpr)

        aucs_array = np.asarray(aucs, dtype=float)
        auc_mean = float(np.mean(aucs_array))
        auc_std = float(np.std(aucs_array, ddof=1)) if len(aucs_array) > 1 else 0.0
        auc_ci_half = 1.96 * auc_std / np.sqrt(len(aucs_array)) if len(aucs_array) > 0 else 0.0

        results[L] = {
            "auc_mean": auc_mean,
            "auc_std": auc_std,
            "auc_95ci_lower": float(auc_mean - auc_ci_half),
            "auc_95ci_upper": float(auc_mean + auc_ci_half),
            "fpr_mean": float(np.mean(fprs)),
            "condition_number_mean": float(np.mean(condition_numbers)),
            "raw_aucs": aucs,
        }

    return {"L_values": L_values, "results": results, "config": {"rho": rho, "W": W, "S": S}}


def load_task5_results_csv(csv_path):
    """Load task5 CSV results into a compact dict keyed by L_baseline."""

    loaded = {}
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            L = int(row["L_baseline"])
            loaded[L] = {
                "auc_mean": float(row["auc_mean"]),
                "auc_95ci_lower": float(row["auc_95ci_lower"]),
                "auc_95ci_upper": float(row["auc_95ci_upper"]),
                "condition_number_mean": float(row["condition_number_mean"]),
                "fpr_mean": float(row["fpr_mean"]),
            }
    return loaded


def save_ablation_figures(results, task5_results=None, output_dir="."):
    """Save ablation figures and CSV summary."""

    os.makedirs(output_dir, exist_ok=True)
    L_values = results["L_values"]
    auc_means = [results["results"][L]["auc_mean"] for L in L_values]
    auc_lowers = [results["results"][L]["auc_95ci_lower"] for L in L_values]
    auc_uppers = [results["results"][L]["auc_95ci_upper"] for L in L_values]
    condition_numbers = [results["results"][L]["condition_number_mean"] for L in L_values]
    fprs = [results["results"][L]["fpr_mean"] for L in L_values]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, auc_means, color="tab:blue", marker="o", label="Ablation")
    ax.fill_between(L_values, auc_lowers, auc_uppers, color="tab:blue", alpha=0.2)
    if task5_results is not None:
        task5_L = sorted(task5_results.keys())
        ax.plot(
            task5_L,
            [task5_results[L]["auc_mean"] for L in task5_L],
            color="gray",
            linestyle="--",
            marker="s",
            label="Task5",
        )
    ax.axhline(0.75, color="black", linestyle="--", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("AUC")
    ax.set_title("Ablation AUC vs Baseline Length")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "ablation_auc_vs_L.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, condition_numbers, color="tab:green", marker="o")
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("Mean condition number")
    ax.set_title("Ablation Condition Number vs Baseline Length")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "ablation_condition_number_vs_L.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, fprs, color="tab:red", marker="o")
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("Mean FPR")
    ax.set_title("Ablation FPR vs Baseline Length")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "ablation_fpr_vs_L.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "ablation_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "L_baseline",
                "auc_mean",
                "auc_std",
                "auc_95ci_lower",
                "auc_95ci_upper",
                "fpr_mean",
                "condition_number_mean",
            ]
        )
        for L in L_values:
            row = results["results"][L]
            writer.writerow(
                [
                    L,
                    row["auc_mean"],
                    row["auc_std"],
                    row["auc_95ci_lower"],
                    row["auc_95ci_upper"],
                    row["fpr_mean"],
                    row["condition_number_mean"],
                ]
            )


class AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_ablation(n_repeats=10)

    def test_auc_improves_from_l50_to_l2000(self):
        self.assertGreater(
            self.results["results"][2000]["auc_mean"],
            self.results["results"][50]["auc_mean"],
        )

    def test_condition_number_decreases_from_l50_to_l2000(self):
        self.assertLess(
            self.results["results"][2000]["condition_number_mean"],
            self.results["results"][50]["condition_number_mean"],
        )

    def test_all_raw_auc_lengths_match_n_repeats(self):
        for L in self.results["L_values"]:
            self.assertEqual(len(self.results["results"][L]["raw_aucs"]), 10)


if __name__ == "__main__":
    unittest.main()
