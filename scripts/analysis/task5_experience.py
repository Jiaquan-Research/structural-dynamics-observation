"""Experience-dependence validation experiment (experiment two)."""

from __future__ import annotations

import csv
import os
import unittest

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data
from task1_data_generator import generate_data
from task2_single_sensor import run_single_sensor_detector
from task3_detectors import run_mahalanobis_detector


def run_experiment_two(rho=0.10, W=100, S=20, n_repeats=100, seed_base=0):
    """Run experiment two for baseline-length dependence under condition B.

    Parameters
    ----------
    rho : float, optional
        Correlation strength for condition B. Default is 0.10.
    W : int, optional
        Sliding-window length for the Mahalanobis detector.
    S : int, optional
        Stride between adjacent windows.
    n_repeats : int, optional
        Number of repeated simulations per baseline length.
    seed_base : int, optional
        Base seed. Repeat ``k`` uses ``seed_base + k``.

    Returns
    -------
    dict
        Summary statistics and per-repeat AUCs for each baseline length.
    """

    L_values = [50, 100, 200, 500, 1000, 2000]
    results = {}

    for L in L_values:
        print(f"L_baseline={L} running ({n_repeats} repeats)...")
        T = L + 400 + 800
        ratios = (L / T, 400 / T, 800 / T)
        baseline_range, calibration_range, test_range = split_data(T, ratios=ratios)
        effective_W = min(W, max(L - 1, 1))

        aucs = []
        condition_numbers = []
        silence_checks = []
        fprs = []
        d2_baseline_means = []
        d2_test_means = []

        for repeat_idx in range(n_repeats):
            seed = seed_base + repeat_idx
            data, metadata = generate_data("B", T=T, rho=rho, seed=seed)
            single_sensor = run_single_sensor_detector(data, metadata)
            detector = run_mahalanobis_detector(
                data,
                baseline_range,
                calibration_range,
                test_range,
                W=effective_W,
                S=S,
            )

            aucs.append(float(detector["auc_test"]))
            condition_number = float(detector["S_f_condition_number"])
            if not np.isfinite(condition_number):
                condition_number = 1e6
            condition_numbers.append(condition_number)
            silence_checks.append(bool(single_sensor["passes_single_sensor_silence_check"]))
            fprs.append(float(np.mean(detector["d2_baseline"] > detector["theta_second"])))
            d2_baseline_means.append(float(np.mean(detector["d2_baseline"])))
            d2_test_means.append(float(np.mean(detector["d2_test"])))

        aucs_array = np.asarray(aucs, dtype=float)
        condition_numbers_array = np.asarray(condition_numbers, dtype=float)
        silence_checks_array = np.asarray(silence_checks, dtype=float)
        fprs_array = np.asarray(fprs, dtype=float)

        auc_mean = float(np.mean(aucs_array))
        auc_std = float(np.std(aucs_array, ddof=1)) if len(aucs_array) > 1 else 0.0
        auc_ci_half = 1.96 * auc_std / np.sqrt(len(aucs_array)) if len(aucs_array) > 0 else 0.0

        results[L] = {
            "auc_mean": auc_mean,
            "auc_std": auc_std,
            "auc_95ci_lower": float(auc_mean - auc_ci_half),
            "auc_95ci_upper": float(auc_mean + auc_ci_half),
            "fpr_mean": float(np.mean(fprs_array)),
            "condition_number_mean": float(np.mean(condition_numbers_array)),
            "silence_pass_rate": float(np.mean(silence_checks_array)),
            "raw_aucs": aucs,
            "raw_condition_numbers": condition_numbers,
            "raw_fprs": fprs,
            "raw_silence_checks": silence_checks,
            "d2_baseline_mean": float(np.mean(d2_baseline_means)),
            "d2_test_mean": float(np.mean(d2_test_means)),
            "effective_W": effective_W,
        }

    return {"L_values": L_values, "results": results}


def save_experiment_two_figures(results, output_dir="."):
    """Save experiment-two figures and CSV summary."""

    os.makedirs(output_dir, exist_ok=True)

    L_values = results["L_values"]
    auc_means = [results["results"][L]["auc_mean"] for L in L_values]
    auc_lowers = [results["results"][L]["auc_95ci_lower"] for L in L_values]
    auc_uppers = [results["results"][L]["auc_95ci_upper"] for L in L_values]
    condition_numbers = [results["results"][L]["condition_number_mean"] for L in L_values]
    fprs = [results["results"][L]["fpr_mean"] for L in L_values]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, auc_means, color="tab:blue", marker="o")
    ax.fill_between(L_values, auc_lowers, auc_uppers, color="tab:blue", alpha=0.2)
    ax.axhline(0.75, color="black", linestyle="--", linewidth=1.0)
    ax.axhline(0.843, color="tab:orange", linestyle=":", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("AUC")
    ax.set_title("Mahalanobis AUC vs Baseline Experience")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "task5_auc_vs_L.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, condition_numbers, color="tab:green", marker="o")
    ax.axhline(1000.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("Mean condition number")
    ax.set_title("Covariance Stability vs Baseline Experience")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "task5_condition_number_vs_L.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(L_values, fprs, color="tab:red", marker="o")
    ax.axhline(0.1, color="black", linestyle="--", linewidth=1.0)
    ax.set_xscale("log")
    ax.set_xlabel("L_baseline")
    ax.set_ylabel("Mean FPR")
    ax.set_title("False Positive Rate vs Baseline Experience")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "task5_fpr_vs_L.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "task5_results.csv")
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
                "silence_pass_rate",
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
                    row["silence_pass_rate"],
                ]
            )


class ExperimentTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_experiment_two(n_repeats=10)

    def test_auc_mean_improves_from_l50_to_l2000(self):
        self.assertGreater(
            self.results["results"][2000]["auc_mean"],
            self.results["results"][50]["auc_mean"],
        )

    def test_condition_number_improves_with_more_data(self):
        self.assertLess(
            self.results["results"][2000]["condition_number_mean"],
            self.results["results"][50]["condition_number_mean"],
        )

    def test_silence_pass_rate_is_high_for_all_lengths(self):
        for L in self.results["L_values"]:
            self.assertGreaterEqual(self.results["results"][L]["silence_pass_rate"], 0.8)

    def test_all_baseline_lengths_are_present(self):
        self.assertEqual(set(self.results["results"].keys()), {50, 100, 200, 500, 1000, 2000})


if __name__ == "__main__":
    unittest.main()
