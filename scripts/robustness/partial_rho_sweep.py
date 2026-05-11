"""Sweep rho for partial coupling conditions using the sum_d2 statistic."""

from __future__ import annotations

import csv

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data
from task1_data_generator import generate_data
from task3_detectors import compute_correlation_audit
from partial_coupling_experiment import _condition_specs, generate_partial_coupling
from sparse_statistic_experiment import _manual_contributions, _stat_series


def main():
    rho_values = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
    conditions = ["B_1pair_12", "B_2pair", "B_global"]
    n_repeats = 50
    W = 100
    S = 20
    L_baseline = 500
    T = 2000

    baseline_range_full, calibration_range, test_range = split_data(T)
    baseline_range = range(baseline_range_full.start, min(baseline_range_full.stop, L_baseline))
    specs = _condition_specs()

    results = {rho: {} for rho in rho_values}

    print("rho | 1pair_12_AUC | 2pair_AUC | global_AUC")
    for rho in rho_values:
        print(f"rho={rho:.2f} running...")
        for condition in conditions:
            aucs = []
            corr_ratios = []
            actual_rhos = []
            loc_hits = []

            for repeat_idx in range(n_repeats):
                seed = repeat_idx
                spec = specs[condition]
                if spec["kind"] == "global":
                    data, metadata = generate_data("B", T=T, rho=rho, seed=seed)
                else:
                    data, metadata = generate_partial_coupling(
                        T, spec["coupled_pairs"], rho=rho, seed=seed
                    )

                manual = _manual_contributions(
                    data, baseline_range, calibration_range, test_range, W, S
                )
                calibration_scores = _stat_series(manual["calibration_contrib"])["sum_d2"]
                test_scores = _stat_series(manual["test_contrib"])["sum_d2"]

                y_true = np.concatenate(
                    [
                        np.zeros(len(calibration_scores), dtype=int),
                        np.ones(len(test_scores), dtype=int),
                    ]
                )
                y_score = np.concatenate([calibration_scores, test_scores])
                # Keep the exact sum_d2 AUC convention used in sparse_statistic_experiment.
                auc = float(
                    __import__("sklearn.metrics", fromlist=["roc_auc_score"]).roc_auc_score(
                        y_true, y_score
                    )
                )

                audit = compute_correlation_audit(
                    data, baseline_range, anomaly_start=metadata["anomaly_start"], W=W, S=S
                )
                top1_test = np.argmax(manual["test_contrib"], axis=1)
                if condition == "B_1pair_12":
                    loc_hit = float(np.mean(top1_test == 0))
                elif condition == "B_2pair":
                    loc_hit = float(np.mean(np.isin(top1_test, [0, 7])))
                else:
                    loc_hit = np.nan

                aucs.append(auc)
                corr_ratios.append(float(audit["corr_ratio"]))
                actual_rhos.append(float(metadata["actual_rho"]))
                loc_hits.append(loc_hit)

            results[rho][condition] = {
                "auc_mean": float(np.mean(aucs)),
                "corr_ratio_mean": float(np.mean(corr_ratios)),
                "actual_rho_mean": float(np.mean(actual_rhos)),
                "loc_hit_rate": float(np.nanmean(loc_hits)) if not np.all(np.isnan(loc_hits)) else np.nan,
            }

        print(
            f"{rho:.2f} | "
            f"{results[rho]['B_1pair_12']['auc_mean']:.3f} | "
            f"{results[rho]['B_2pair']['auc_mean']:.3f} | "
            f"{results[rho]['B_global']['auc_mean']:.3f}"
        )

    fig, ax = plt.subplots(figsize=(9, 5))
    for condition, color in zip(conditions, ["tab:blue", "tab:orange", "tab:green"]):
        ax.plot(
            rho_values,
            [results[rho][condition]["auc_mean"] for rho in rho_values],
            marker="o",
            label=condition,
            color=color,
        )
    ax.axhline(0.65, color="black", linestyle="--", linewidth=1.0)
    ax.set_xlabel("requested rho")
    ax.set_ylabel("AUC")
    ax.set_title("Partial coupling rho sweep (sum_d2)")
    ax.set_ylim(0.0, 1.05)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig("partial_rho_sweep.png", dpi=150)

    with open("partial_rho_sweep.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "requested_rho",
                "condition",
                "auc_mean",
                "corr_ratio_mean",
                "actual_rho_mean",
                "loc_hit_rate",
            ]
        )
        for rho in rho_values:
            for condition in conditions:
                row = results[rho][condition]
                writer.writerow(
                    [
                        rho,
                        condition,
                        row["auc_mean"],
                        row["corr_ratio_mean"],
                        row["actual_rho_mean"],
                        row["loc_hit_rate"],
                    ]
                )

    candidates = [
        rho
        for rho in rho_values
        if results[rho]["B_1pair_12"]["auc_mean"] > 0.65
        and abs(results[rho]["B_1pair_12"]["actual_rho_mean"] - rho) < 1e-9
    ]
    print()
    if candidates:
        print(f"Minimum requested rho meeting target: {min(candidates):.2f}")
    else:
        print("No rho met the 1pair_12 target.")


if __name__ == "__main__":
    main()
