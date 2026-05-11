"""Window-length sweep experiment for weak relation anomalies."""

from __future__ import annotations

import csv
import os
import unittest

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data, stride_sample
from task1_data_generator import generate_data
from task3_detectors import (
    _auc_against_baseline,
    _collect_window_features,
    _estimate_covariance,
    _upper_triangle_features,
    run_mahalanobis_detector,
)
from partial_coupling_experiment import generate_partial_coupling


def _run_mahalanobis_with_baseline_fallback(data, baseline_range, calibration_range, test_range, W, S):
    """Run Mahalanobis detection, with a single-window fallback if W > L_baseline."""

    try:
        return run_mahalanobis_detector(
            data,
            baseline_range,
            calibration_range,
            test_range,
            W=W,
            S=S,
        )
    except ValueError:
        anomaly_start = test_range.start
        if W > anomaly_start:
            raise

        baseline_times = [W]
        calibration_times = stride_sample(calibration_range, W, S)
        test_times = stride_sample(test_range, W, S)
        if not calibration_times:
            calibration_times = [calibration_range.stop]
        if not test_times:
            test_times = [test_range.stop]
        baseline_features = _collect_window_features(
            data, baseline_times, W, _upper_triangle_features
        )
        calibration_features = _collect_window_features(
            data, calibration_times, W, _upper_triangle_features
        )
        test_features = _collect_window_features(data, test_times, W, _upper_triangle_features)
        mu_f = baseline_features.mean(axis=0)
        S_f = _estimate_covariance(baseline_features)
        S_f_inv = np.linalg.pinv(S_f + 0.1 * np.eye(10))
        condition_number = float(np.linalg.cond(S_f))
        if not np.isfinite(condition_number):
            condition_number = 1e6

        def mahal_sq(features):
            centered = features - mu_f
            return np.einsum("ij,jk,ik->i", centered, S_f_inv, centered)

        d2_baseline = mahal_sq(baseline_features)
        d2_calibration = mahal_sq(calibration_features)
        d2_test = mahal_sq(test_features)
        theta_second = float(np.max(d2_calibration))
        return {
            "d2_baseline": d2_baseline,
            "d2_calibration": d2_calibration,
            "d2_test": d2_test,
            "theta_second": theta_second,
            "auc_test": _auc_against_baseline(d2_calibration, d2_test),
            "S_f_condition_number": condition_number,
        }


def run_window_sweep(rho=0.10, S=20, L_baseline=500, T=2000, n_repeats=100, seed_base=0):
    """Sweep correlation-window length W under weak-signal conditions."""

    W_values = [50, 100, 200, 400, 800]
    conditions = ["B_1pair_12", "B_global"]
    baseline_range_full, calibration_range, test_range = split_data(T)
    baseline_range = range(baseline_range_full.start, min(baseline_range_full.stop, L_baseline))
    results = {condition: {} for condition in conditions}

    for W in W_values:
        print(f"W={W} running...")
        overlap_ratio = 1.0 - (S / W)

        for condition in conditions:
            aucs = []
            fprs = []
            condition_numbers = []
            n_eff_baseline_values = []
            n_eff_anomaly_values = []

            for repeat_idx in range(n_repeats):
                seed = seed_base + repeat_idx
                if condition == "B_global":
                    data, _ = generate_data("B", T=T, rho=rho, seed=seed)
                else:
                    data, _ = generate_partial_coupling(T, [(0, 1)], rho=rho, seed=seed)

                detector = _run_mahalanobis_with_baseline_fallback(
                    data, baseline_range, calibration_range, test_range, W=W, S=S
                )

                aucs.append(float(detector["auc_test"]))
                fprs.append(float(np.mean(detector["d2_calibration"] > detector["theta_second"])))
                condition_numbers.append(float(detector["S_f_condition_number"]))
                n_eff_baseline_values.append(len(stride_sample(baseline_range, W, S)))
                n_eff_anomaly_values.append(len(stride_sample(test_range, W, S)))

            aucs_array = np.asarray(aucs, dtype=float)
            auc_mean = float(np.mean(aucs_array))
            auc_std = float(np.std(aucs_array, ddof=1)) if len(aucs_array) > 1 else 0.0
            auc_ci_half = 1.96 * auc_std / np.sqrt(len(aucs_array)) if len(aucs_array) > 0 else 0.0
            if auc_ci_half == 0.0:
                auc_ci_half = 1e-12

            results[condition][W] = {
                "auc_mean": auc_mean,
                "auc_std": auc_std,
                "auc_95ci_lower": float(auc_mean - auc_ci_half),
                "auc_95ci_upper": float(auc_mean + auc_ci_half),
                "fpr_mean": float(np.mean(fprs)),
                "condition_number_mean": float(np.mean(condition_numbers)),
                "n_eff_mean": float(np.mean(n_eff_baseline_values)),
                "n_eff_baseline_mean": float(np.mean(n_eff_baseline_values)),
                "n_eff_anomaly_mean": float(np.mean(n_eff_anomaly_values)),
                "overlap_ratio": float(overlap_ratio),
            }

        n_eff_anomaly_mean = results["B_1pair_12"][W]["n_eff_anomaly_mean"]
        if n_eff_anomaly_mean < 5:
            print(
                f"WARNING: W={W}, n_eff_anomaly≈{n_eff_anomaly_mean:.0f}, "
                "AUC may be unreliable"
            )
        if overlap_ratio > 0.95:
            print(
                f"WARNING: W={W}, overlap_ratio={overlap_ratio:.3f}, "
                "samples nearly non-independent"
            )

    return {"W_values": W_values, "conditions": conditions, "results": results}


def save_window_sweep_figures(results, output_dir="."):
    """Save AUC-vs-W and effective-sample diagnostics."""

    os.makedirs(output_dir, exist_ok=True)
    W_values = results["W_values"]
    conditions = results["conditions"]

    fig, ax = plt.subplots(figsize=(9, 5))
    style = {"B_1pair_12": "tab:blue", "B_global": "tab:green"}
    for condition in conditions:
        auc_mean = [results["results"][condition][W]["auc_mean"] for W in W_values]
        lower = [results["results"][condition][W]["auc_95ci_lower"] for W in W_values]
        upper = [results["results"][condition][W]["auc_95ci_upper"] for W in W_values]
        ax.plot(W_values, auc_mean, marker="o", color=style[condition], label=condition)
        ax.fill_between(W_values, lower, upper, color=style[condition], alpha=0.2)
    ax.axhline(0.65, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(0.75, color="black", linestyle=":", linewidth=1.0)
    ax.set_xlabel("W")
    ax.set_ylabel("AUC")
    ax.set_title("Window Length vs Detection AUC")
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "window_auc_vs_W.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    n_eff_global = [results["results"]["B_global"][W]["n_eff_mean"] for W in W_values]
    ax.plot(W_values, n_eff_global, marker="o", color="tab:blue")
    ax.set_xlabel("W")
    ax.set_ylabel("n_eff_baseline")
    ax.set_title("Baseline Effective Sample Count vs Window Length")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "window_neff_vs_W.png"), dpi=150)
    plt.close(fig)

    fig, ax1 = plt.subplots(figsize=(9, 5))
    n_eff_baseline = [results["results"]["B_global"][W]["n_eff_baseline_mean"] for W in W_values]
    n_eff_anomaly = [results["results"]["B_global"][W]["n_eff_anomaly_mean"] for W in W_values]
    overlap = [results["results"]["B_global"][W]["overlap_ratio"] for W in W_values]
    ax1.plot(W_values, n_eff_baseline, marker="o", color="tab:blue", label="n_eff_baseline")
    ax1.plot(W_values, n_eff_anomaly, marker="s", color="tab:orange", label="n_eff_anomaly")
    ax1.set_xlabel("W")
    ax1.set_ylabel("effective sample count")
    ax1.grid(alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(W_values, overlap, marker="^", color="tab:red", label="overlap_ratio")
    ax2.set_ylabel("overlap_ratio")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right")
    ax1.set_title("AUC Context: Effective Samples and Overlap")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "window_neff_breakdown.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "window_sweep_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "W",
                "condition",
                "auc_mean",
                "auc_std",
                "auc_95ci_lower",
                "auc_95ci_upper",
                "fpr_mean",
                "n_eff_mean",
            ]
        )
        for condition in conditions:
            for W in W_values:
                row = results["results"][condition][W]
                writer.writerow(
                    [
                        W,
                        condition,
                        row["auc_mean"],
                        row["auc_std"],
                        row["auc_95ci_lower"],
                        row["auc_95ci_upper"],
                        row["fpr_mean"],
                        row["n_eff_mean"],
                    ]
                )


class WindowSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_window_sweep(n_repeats=20)

    def test_global_auc_stays_above_chance(self):
        for W in self.results["W_values"]:
            self.assertGreater(self.results["results"]["B_global"][W]["auc_mean"], 0.5)

    def test_neff_decreases_with_large_window(self):
        self.assertGreater(
            self.results["results"]["B_global"][50]["n_eff_mean"],
            self.results["results"]["B_global"][800]["n_eff_mean"],
        )

    def test_all_window_keys_are_present(self):
        for condition in self.results["conditions"]:
            self.assertEqual(set(self.results["results"][condition].keys()), set(self.results["W_values"]))

    def test_auc_mean_is_inside_its_confidence_interval(self):
        for condition in self.results["conditions"]:
            for W in self.results["W_values"]:
                row = self.results["results"][condition][W]
                self.assertLess(row["auc_95ci_lower"], row["auc_mean"])
                self.assertLess(row["auc_mean"], row["auc_95ci_upper"])


if __name__ == "__main__":
    unittest.main()
