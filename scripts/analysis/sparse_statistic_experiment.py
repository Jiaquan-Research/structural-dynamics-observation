"""Sparse statistic comparison for coupling-structure anomalies."""

from __future__ import annotations

import csv
import os
import unittest

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data, stride_sample
from task3_detectors import (
    _auc_against_baseline,
    _collect_window_features,
    _estimate_covariance,
    _upper_triangle_features,
)
from partial_coupling_experiment import (
    FEATURE_INDEX_TO_PAIR,
    _condition_specs,
    _pair_to_feature_index,
    generate_partial_coupling,
)
from task1_data_generator import generate_data


def _stat_series(contributions):
    """Compute sparse statistics from per-dimension contribution arrays."""

    sorted_desc = np.sort(contributions, axis=1)[:, ::-1]
    return {
        "sum_d2": np.sum(contributions, axis=1),
        "max_d2": sorted_desc[:, 0],
        "top2_d2": np.sum(sorted_desc[:, :2], axis=1),
        "top3_d2": np.sum(sorted_desc[:, :3], axis=1),
    }


def _select_threshold_from_negative(scores_negative):
    """Select a calibration threshold from negative-only scores."""

    scores_negative = np.asarray(scores_negative, dtype=float)
    if scores_negative.size == 0:
        raise ValueError("scores_negative must be non-empty.")
    return float(np.max(scores_negative))


def _loc_hit_from_top1(condition, top1_idx):
    """Return 1.0/0.0 localization hit score for the active top feature."""

    pair_to_idx = _pair_to_feature_index()
    if condition == "B_1pair_12":
        return 1.0 if top1_idx == pair_to_idx[(0, 1)] else 0.0
    if condition == "B_1pair_45":
        return 1.0 if top1_idx == pair_to_idx[(3, 4)] else 0.0
    if condition == "B_2pair":
        return 1.0 if top1_idx in {pair_to_idx[(0, 1)], pair_to_idx[(2, 3)]} else 0.0
    if condition == "B_global":
        return np.nan
    raise ValueError(f"Unsupported condition: {condition}")


def _manual_contributions(data, baseline_range, calibration_range, test_range, W, S):
    """Compute per-window diagonal contribution approximations."""

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
    diagonal = np.diag(S_f_inv)

    def per_dim(features):
        centered = features - mu_f
        return (centered**2) * diagonal

    return {
        "baseline_contrib": per_dim(baseline_features),
        "calibration_contrib": per_dim(calibration_features),
        "test_contrib": per_dim(test_features),
    }


def run_sparse_statistic_comparison(
    rho=0.25, W=100, S=20, L_baseline=500, n_repeats=100, seed_base=0
):
    """Compare sparse scoring statistics across coupling structures."""

    T = 2000
    baseline_range_full, calibration_range, test_range = split_data(T)
    baseline_range = range(baseline_range_full.start, min(baseline_range_full.stop, L_baseline))
    conditions = ["B_1pair_12", "B_1pair_45", "B_2pair", "B_global"]
    statistics = ["sum_d2", "max_d2", "top2_d2", "top3_d2"]
    specs = _condition_specs()

    results = {condition: {stat: {"raw_aucs": [], "raw_fprs": [], "raw_loc_hits": []} for stat in statistics} for condition in conditions}

    for condition in conditions:
        print(f"{condition} running...")
        for repeat_idx in range(n_repeats):
            seed = seed_base + repeat_idx
            spec = specs[condition]
            if spec["kind"] == "global":
                data, metadata = generate_data("B", T=T, rho=rho, seed=seed)
            else:
                data, metadata = generate_partial_coupling(T, spec["coupled_pairs"], rho=rho, seed=seed)

            contributions = _manual_contributions(
                data, baseline_range, calibration_range, test_range, W, S
            )
            calibration_stats = _stat_series(contributions["calibration_contrib"])
            test_stats = _stat_series(contributions["test_contrib"])

            top1_calibration = np.argmax(contributions["calibration_contrib"], axis=1)
            top1_test = np.argmax(contributions["test_contrib"], axis=1)
            del metadata

            for stat in statistics:
                calibration_scores = calibration_stats[stat]
                test_scores = test_stats[stat]
                theta = _select_threshold_from_negative(calibration_scores)
                auc = _auc_against_baseline(calibration_scores, test_scores)
                fpr = float(np.mean(calibration_scores > theta))
                loc_hits = [_loc_hit_from_top1(condition, idx) for idx in top1_test]
                loc_hits_clean = [x for x in loc_hits if not np.isnan(x)]
                loc_hit_value = float(np.mean(loc_hits_clean)) if loc_hits_clean else np.nan

                store = results[condition][stat]
                store["raw_aucs"].append(float(auc))
                store["raw_fprs"].append(fpr)
                store["raw_loc_hits"].append(loc_hit_value)

        for stat in statistics:
            store = results[condition][stat]
            aucs = np.asarray(store["raw_aucs"], dtype=float)
            fprs = np.asarray(store["raw_fprs"], dtype=float)
            loc_hits = np.asarray(store["raw_loc_hits"], dtype=float)
            auc_std = float(np.std(aucs, ddof=1)) if len(aucs) > 1 else 0.0
            auc_ci_half = 1.96 * auc_std / np.sqrt(len(aucs))
            results[condition][stat] = {
                "auc_mean": float(np.mean(aucs)),
                "auc_std": auc_std,
                "auc_95ci": [float(np.mean(aucs) - auc_ci_half), float(np.mean(aucs) + auc_ci_half)],
                "fpr_mean": float(np.mean(fprs)),
                "loc_hit_rate": float(np.nanmean(loc_hits)) if not np.all(np.isnan(loc_hits)) else np.nan,
                "raw_aucs": store["raw_aucs"],
            }

    return {"conditions": conditions, "statistics": statistics, "results": results}


def save_sparse_figures(results, output_dir="."):
    """Save sparse statistic comparison figures and CSV."""

    os.makedirs(output_dir, exist_ok=True)
    conditions = results["conditions"]
    statistics = results["statistics"]

    heatmap = np.array(
        [[results["results"][condition][stat]["auc_mean"] for stat in statistics] for condition in conditions]
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    image = ax.imshow(heatmap, cmap="viridis", aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_xticks(np.arange(len(statistics)))
    ax.set_xticklabels(statistics)
    ax.set_yticks(np.arange(len(conditions)))
    ax.set_yticklabels(conditions)
    ax.set_title("AUC Heatmap by Coupling x Statistic")
    for i in range(len(conditions)):
        for j in range(len(statistics)):
            ax.text(j, i, f"{heatmap[i, j]:.3f}", ha="center", va="center", color="white")
    fig.colorbar(image, ax=ax)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "sparse_auc_heatmap.png"), dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(4, 1, figsize=(8, 12), sharex=True)
    for ax, condition in zip(axes, conditions):
        auc_means = [results["results"][condition][stat]["auc_mean"] for stat in statistics]
        auc_err = []
        for stat in statistics:
            lower, upper = results["results"][condition][stat]["auc_95ci"]
            auc_err.append(upper - results["results"][condition][stat]["auc_mean"])
        ax.bar(statistics, auc_means, yerr=auc_err, color="tab:blue", alpha=0.8)
        ax.axhline(0.5, color="black", linestyle="--", linewidth=1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("AUC")
        ax.set_title(condition)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "sparse_auc_by_condition.png"), dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(4, 1, figsize=(8, 12), sharex=True)
    for ax, condition in zip(axes, conditions):
        loc_hits = [results["results"][condition][stat]["loc_hit_rate"] for stat in statistics]
        ax.bar(statistics, loc_hits, color="tab:orange", alpha=0.8)
        ax.axhline(0.1, color="black", linestyle="--", linewidth=1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_ylabel("loc hit")
        ax.set_title(condition)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "sparse_localization.png"), dpi=150)
    plt.close(fig)

    csv_path = os.path.join(output_dir, "sparse_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["condition", "statistic", "auc_mean", "auc_std", "fpr_mean", "loc_hit_rate"])
        for condition in conditions:
            for stat in statistics:
                row = results["results"][condition][stat]
                writer.writerow(
                    [
                        condition,
                        stat,
                        row["auc_mean"],
                        row["auc_std"],
                        row["fpr_mean"],
                        row["loc_hit_rate"],
                    ]
                )


class SparseStatisticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n_repeats = 20
        cls.results = run_sparse_statistic_comparison(n_repeats=cls.n_repeats)

    def test_all_raw_auc_lengths_match_repeats(self):
        for condition in self.results["conditions"]:
            for stat in self.results["statistics"]:
                self.assertEqual(
                    len(self.results["results"][condition][stat]["raw_aucs"]),
                    self.n_repeats,
                )

    def test_fpr_values_are_in_unit_interval(self):
        for condition in self.results["conditions"]:
            for stat in self.results["statistics"]:
                fpr = self.results["results"][condition][stat]["fpr_mean"]
                self.assertGreaterEqual(fpr, 0.0)
                self.assertLessEqual(fpr, 1.0)

    def test_localization_values_are_in_unit_interval(self):
        for condition in self.results["conditions"]:
            for stat in self.results["statistics"]:
                loc = self.results["results"][condition][stat]["loc_hit_rate"]
                if np.isnan(loc):
                    continue
                self.assertGreaterEqual(loc, 0.0)
                self.assertLessEqual(loc, 1.0)

    def test_sum_d2_is_reasonable_for_global_condition(self):
        self.assertGreater(self.results["results"]["B_global"]["sum_d2"]["auc_mean"], 0.6)


if __name__ == "__main__":
    unittest.main()
