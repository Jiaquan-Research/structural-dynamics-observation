"""Partial coupling experiment with feature contribution analysis."""

from __future__ import annotations

import csv
import os
import unittest
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data, stride_sample
from task1_data_generator import generate_data
from task3_detectors import (
    _auc_against_baseline,
    _collect_window_features,
    _estimate_covariance,
    _roc_curve_from_scores,
    _upper_triangle_features,
    compute_correlation_audit,
    run_ocsvm_detector,
)

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


def _pair_to_feature_index():
    """Return the inverse mapping from sensor pair to feature index."""

    return {pair: idx for idx, pair in FEATURE_INDEX_TO_PAIR.items()}


def _partial_correlation_matrix(coupled_pairs, rho):
    """Build a 5x5 correlation matrix with rho only on selected pairs."""

    matrix = np.eye(5, dtype=float)
    for i, j in coupled_pairs:
        matrix[i, j] = rho
        matrix[j, i] = rho
    return matrix


def _generate_partial_rejection_correlated(n_samples, coupled_pairs, theta, rho, rng):
    """Generate partially coupled Gaussian samples with rejection sampling."""

    if n_samples == 0:
        return np.empty((0, 5), dtype=float), 1.0

    chol = np.linalg.cholesky(_partial_correlation_matrix(coupled_pairs, rho))
    accepted = []
    attempts = 0
    accepted_total = 0

    while len(accepted) < n_samples:
        draw_count = max(4 * (n_samples - len(accepted)), 128)
        raw = rng.standard_normal((draw_count, 5))
        correlated = raw @ chol.T
        keep_mask = np.all(np.abs(correlated) <= theta, axis=1)
        accepted_batch = correlated[keep_mask]
        accepted_total += int(keep_mask.sum())
        accepted.extend(accepted_batch[: n_samples - len(accepted)])
        attempts += draw_count

    return np.asarray(accepted, dtype=float), accepted_total / attempts


def generate_partial_coupling(T, coupled_pairs, rho=0.10, theta=3.0, seed=42):
    """Generate condition-B style data with coupling restricted to selected pairs."""

    if not isinstance(T, int) or T <= 0:
        raise ValueError("T must be a positive integer.")

    rng = np.random.default_rng(seed)
    anomaly_start = T // 2
    normal_len = anomaly_start
    anomaly_len = T - anomaly_start

    normal_data = rng.standard_normal((normal_len, 5))

    if not coupled_pairs:
        anomaly_data = rng.standard_normal((anomaly_len, 5))
        return data_with_metadata(
            normal_data,
            anomaly_data,
            anomaly_start,
            actual_rho=0.0,
            acceptance_rate=1.0,
            coupled_pairs=coupled_pairs,
        )

    requested_rho = float(rho)
    actual_rho = float(rho)
    pair_set = {tuple(pair) for pair in coupled_pairs}

    while True:
        candidate_data, candidate_rate = _generate_partial_rejection_correlated(
            anomaly_len, pair_set, theta, actual_rho, rng
        )
        sample_corr = np.corrcoef(candidate_data, rowvar=False)
        targeted_corr = np.mean([sample_corr[i, j] for i, j in pair_set])
        off_target_pairs = [
            sample_corr[i, j]
            for i in range(5)
            for j in range(i + 1, 5)
            if (i, j) not in pair_set
        ]
        off_target_corr = np.mean(np.abs(off_target_pairs)) if off_target_pairs else 0.0
        if candidate_rate >= 0.30 and targeted_corr >= max(actual_rho * 0.5, 0.02):
            anomaly_data = candidate_data
            acceptance_rate = candidate_rate
            break
        actual_rho = round(max(0.0, actual_rho - 0.05), 10)
        if actual_rho <= 0.0:
            anomaly_data = candidate_data
            acceptance_rate = candidate_rate
            break

    return data_with_metadata(
        normal_data,
        anomaly_data,
        anomaly_start,
        actual_rho=actual_rho,
        acceptance_rate=acceptance_rate,
        coupled_pairs=coupled_pairs,
        requested_rho=requested_rho,
    )


def data_with_metadata(
    normal_data,
    anomaly_data,
    anomaly_start,
    actual_rho,
    acceptance_rate,
    coupled_pairs,
    requested_rho=None,
):
    """Package generated arrays and metadata consistently."""

    data = np.vstack([normal_data, anomaly_data])
    metadata = {
        "anomaly_start": anomaly_start,
        "actual_rho": float(actual_rho),
        "acceptance_rate": float(acceptance_rate),
        "coupled_pairs": list(coupled_pairs),
    }
    if requested_rho is not None:
        metadata["requested_rho"] = float(requested_rho)
    return data, metadata


def compute_feature_contributions(baseline_features, test_features, mu_f, S_f_inv):
    """Approximate per-feature D2 contributions using diagonal precision terms."""

    del baseline_features
    diagonal = np.diag(S_f_inv)
    centered = test_features - mu_f
    contributions = (centered**2) * diagonal
    mean_contributions = contributions.mean(axis=0)
    ranked = np.argsort(mean_contributions)[::-1]
    return {
        "mean_contributions": mean_contributions,
        "top1_feature_idx": int(ranked[0]),
        "top2_feature_idx": int(ranked[1]),
    }


def _run_manual_mahalanobis(data, baseline_range, calibration_range, test_range, W, S):
    """Run Mahalanobis scoring while exposing intermediate features."""

    baseline_times = stride_sample(baseline_range, W, S)
    calibration_times = stride_sample(calibration_range, W, S)
    test_times = stride_sample(test_range, W, S)

    baseline_features = _collect_window_features(data, baseline_times, W, _upper_triangle_features)
    calibration_features = _collect_window_features(
        data, calibration_times, W, _upper_triangle_features
    )
    test_features = _collect_window_features(data, test_times, W, _upper_triangle_features)

    if baseline_features.size == 0:
        raise ValueError("baseline segment does not contain enough samples for W and S.")

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
    auc_test = _auc_against_baseline(d2_calibration, d2_test)

    return {
        "baseline_features": baseline_features,
        "calibration_features": calibration_features,
        "test_features": test_features,
        "mu_f": mu_f,
        "S_f": S_f,
        "S_f_inv": S_f_inv,
        "condition_number": condition_number,
        "d2_baseline": d2_baseline,
        "d2_calibration": d2_calibration,
        "d2_test": d2_test,
        "auc_test": auc_test,
    }


def _localization_result(condition_name, top1_idx, top2_idx):
    """Evaluate localization success for each anomaly condition."""

    pair_to_idx = _pair_to_feature_index()
    if condition_name == "B_1pair_12":
        return "hit" if top1_idx == pair_to_idx[(0, 1)] else "miss"
    if condition_name == "B_1pair_45":
        return "hit" if top1_idx == pair_to_idx[(3, 4)] else "miss"
    if condition_name == "B_2pair":
        target = {pair_to_idx[(0, 1)], pair_to_idx[(2, 3)]}
        chosen = {top1_idx, top2_idx}
        if chosen.issubset(target):
            return "hit"
        if chosen & target:
            return "partial"
        return "miss"
    return "N/A"


def _condition_specs():
    """Return experiment condition specifications."""

    return {
        "A": {"kind": "normal", "coupled_pairs": []},
        "B_1pair_12": {"kind": "partial", "coupled_pairs": [(0, 1)]},
        "B_1pair_45": {"kind": "partial", "coupled_pairs": [(3, 4)]},
        "B_2pair": {"kind": "partial", "coupled_pairs": [(0, 1), (2, 3)]},
        "B_global": {"kind": "global", "coupled_pairs": list(_pair_to_feature_index().keys())},
    }


def run_partial_coupling(rho=0.10, W=100, S=20, L_baseline=500, n_repeats=100, seed_base=0):
    """Run the partial coupling experiment across five conditions."""

    T = 2000
    baseline_range_full, calibration_range, test_range = split_data(T)
    baseline_range = range(baseline_range_full.start, min(baseline_range_full.stop, L_baseline))
    conditions = list(_condition_specs().keys())
    specs = _condition_specs()
    results = {}

    for condition in conditions:
        print(f"{condition} running ({n_repeats} repeats)...")
        mah_aucs = []
        ocsvm_aucs = []
        corr_ratios = []
        actual_rhos = []
        acceptance_rates = []
        localization_hits = []
        top1_distribution = Counter()
        mean_contributions_accumulator = []
        roc_curves_mah = []
        roc_curves_ocsvm = []

        for repeat_idx in range(n_repeats):
            seed = seed_base + repeat_idx
            spec = specs[condition]
            if spec["kind"] == "normal":
                data, metadata = generate_data("A", T=T, seed=seed)
                metadata["coupled_pairs"] = []
            elif spec["kind"] == "global":
                data, metadata = generate_data("B", T=T, rho=rho, seed=seed)
                metadata["coupled_pairs"] = spec["coupled_pairs"]
            else:
                data, metadata = generate_partial_coupling(
                    T, spec["coupled_pairs"], rho=rho, seed=seed
                )

            mah = _run_manual_mahalanobis(data, baseline_range, calibration_range, test_range, W, S)
            ocsvm = run_ocsvm_detector(data, baseline_range, calibration_range, test_range, W=W, S=S)
            audit = compute_correlation_audit(
                data, baseline_range, anomaly_start=metadata["anomaly_start"], W=W, S=S
            )
            contributions = compute_feature_contributions(
                mah["baseline_features"],
                mah["test_features"],
                mah["mu_f"],
                mah["S_f_inv"],
            )

            localization = _localization_result(
                condition,
                contributions["top1_feature_idx"],
                contributions["top2_feature_idx"],
            )

            mah_aucs.append(float(mah["auc_test"]))
            ocsvm_aucs.append(float(ocsvm["auc_test"]))
            corr_ratios.append(float(audit["corr_ratio"]))
            actual_rhos.append(float(metadata.get("actual_rho", 0.0)))
            acceptance_rates.append(float(metadata.get("acceptance_rate", 1.0)))
            top1_distribution[contributions["top1_feature_idx"]] += 1
            mean_contributions_accumulator.append(contributions["mean_contributions"])
            if localization == "hit":
                localization_hits.append(1.0)
            elif localization == "partial":
                localization_hits.append(0.5)
            elif localization == "miss":
                localization_hits.append(0.0)

            roc_curves_mah.append(_roc_curve_from_scores(mah["d2_calibration"], mah["d2_test"]))
            roc_curves_ocsvm.append(
                _roc_curve_from_scores(ocsvm["scores_baseline"], ocsvm["scores_test"])
            )

        mah_array = np.asarray(mah_aucs, dtype=float)
        mah_std = float(np.std(mah_array, ddof=1)) if len(mah_array) > 1 else 0.0
        mah_ci_half = 1.96 * mah_std / np.sqrt(len(mah_array))
        mean_contributions_mean = np.mean(np.asarray(mean_contributions_accumulator), axis=0)
        top1_most_common = top1_distribution.most_common(1)[0][0]

        results[condition] = {
            "mah_auc_mean": float(np.mean(mah_array)),
            "mah_auc_95ci": [
                float(np.mean(mah_array) - mah_ci_half),
                float(np.mean(mah_array) + mah_ci_half),
            ],
            "ocsvm_auc_mean": float(np.mean(ocsvm_aucs)),
            "corr_ratio_mean": float(np.mean(corr_ratios)),
            "localization_hit_rate": float(np.mean(localization_hits)) if localization_hits else np.nan,
            "top1_feature_distribution": dict(top1_distribution),
            "raw_mah_aucs": mah_aucs,
            "raw_ocsvm_aucs": ocsvm_aucs,
            "mean_contributions": mean_contributions_mean.tolist(),
            "top1_most_common_feature": int(top1_most_common),
            "actual_rho_mean": float(np.mean(actual_rhos)),
            "acceptance_rate_mean": float(np.mean(acceptance_rates)),
            "roc_curve_mah": roc_curves_mah[-1],
            "roc_curve_ocsvm": roc_curves_ocsvm[-1],
        }

    return {"conditions": conditions, "results": results}


def save_partial_coupling_figures(results, output_dir="."):
    """Save summary figures and CSV for the partial coupling experiment."""

    os.makedirs(output_dir, exist_ok=True)
    conditions = results["conditions"]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(conditions))
    width = 0.35
    mah_aucs = [results["results"][cond]["mah_auc_mean"] for cond in conditions]
    ocsvm_aucs = [results["results"][cond]["ocsvm_auc_mean"] for cond in conditions]
    ax.bar(x - width / 2, mah_aucs, width=width, label="Mahalanobis")
    ax.bar(x + width / 2, ocsvm_aucs, width=width, label="OCSVM")
    ax.axhline(0.75, color="black", linestyle="--", linewidth=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=15)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("AUC")
    ax.set_title("Partial Coupling AUC Comparison")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "partial_auc_comparison.png"), dpi=150)
    plt.close(fig)

    anomaly_conditions = [cond for cond in conditions if cond != "A"]
    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    highlight_map = {
        "B_1pair_12": {0},
        "B_1pair_45": {9},
        "B_2pair": {0, 7},
        "B_global": set(),
    }
    for ax, condition in zip(axes, anomaly_conditions):
        contributions = results["results"][condition]["mean_contributions"]
        bars = ax.bar(range(10), contributions, color="tab:blue")
        for idx in highlight_map[condition]:
            bars[idx].set_color("tab:red")
        ax.set_ylabel("mean contrib")
        ax.set_title(condition)
        ax.grid(axis="y", alpha=0.3)
    axes[-1].set_xlabel("feature index")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "partial_feature_contribution.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    localization_rates = [
        0.0 if np.isnan(results["results"][cond]["localization_hit_rate"]) else results["results"][cond]["localization_hit_rate"]
        for cond in conditions
    ]
    ax.bar(conditions, localization_rates, color="tab:purple")
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("localization hit rate")
    ax.set_title("Partial Coupling Localization")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "partial_localization.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "partial_coupling_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "condition",
                "mah_auc_mean",
                "ocsvm_auc_mean",
                "corr_ratio_mean",
                "localization_hit_rate",
                "top1_most_common_feature",
            ]
        )
        for condition in conditions:
            row = results["results"][condition]
            writer.writerow(
                [
                    condition,
                    row["mah_auc_mean"],
                    row["ocsvm_auc_mean"],
                    row["corr_ratio_mean"],
                    row["localization_hit_rate"],
                    row["top1_most_common_feature"],
                ]
            )


class PartialCouplingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_partial_coupling(n_repeats=20)

    def test_global_auc_not_lower_than_one_pair_auc(self):
        global_auc = self.results["results"]["B_global"]["mah_auc_mean"]
        one_pair_auc = self.results["results"]["B_1pair_12"]["mah_auc_mean"]
        self.assertGreaterEqual(global_auc, one_pair_auc)

    def test_one_pair_12_localization_is_better_than_random(self):
        top1_dist = self.results["results"]["B_1pair_12"]["top1_feature_distribution"]
        idx0_count = top1_dist.get(0, 0)
        self.assertGreater(idx0_count / 20.0, 0.3)

    def test_condition_a_auc_is_near_chance(self):
        auc = self.results["results"]["A"]["mah_auc_mean"]
        self.assertGreaterEqual(auc, 0.3)
        self.assertLessEqual(auc, 0.7)

    def test_empty_coupling_matches_condition_a_generation(self):
        data_partial, metadata_partial = generate_partial_coupling(2000, [], seed=123)
        data_a, metadata_a = generate_data("A", T=2000, seed=123)
        self.assertTrue(np.allclose(data_partial, data_a))
        self.assertEqual(metadata_partial["anomaly_start"], metadata_a["anomaly_start"])


if __name__ == "__main__":
    unittest.main()
