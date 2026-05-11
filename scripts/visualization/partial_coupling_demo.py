"""Demo script for the partial coupling experiment."""

from __future__ import annotations

from partial_coupling_experiment import run_partial_coupling, save_partial_coupling_figures


def main():
    results = run_partial_coupling()
    save_partial_coupling_figures(results)

    print("Partial coupling summary")
    for condition in results["conditions"]:
        row = results["results"][condition]
        print(
            f"{condition}: MahAUC={row['mah_auc_mean']:.3f}, "
            f"OCSVM_AUC={row['ocsvm_auc_mean']:.3f}, "
            f"loc_hit={row['localization_hit_rate']}"
        )

    one_pair_mean = (
        results["results"]["B_1pair_12"]["mah_auc_mean"]
        + results["results"]["B_1pair_45"]["mah_auc_mean"]
    ) / 2.0
    auc_2pair = results["results"]["B_2pair"]["mah_auc_mean"]
    auc_global = results["results"]["B_global"]["mah_auc_mean"]
    trend_up = one_pair_mean <= auc_2pair <= auc_global or one_pair_mean < auc_global

    hit_12 = results["results"]["B_1pair_12"]["top1_feature_distribution"].get(0, 0) / 100.0
    hit_45 = results["results"]["B_1pair_45"]["top1_feature_distribution"].get(9, 0) / 100.0
    sanity_gap = abs(
        results["results"]["B_1pair_12"]["mah_auc_mean"]
        - results["results"]["B_1pair_45"]["mah_auc_mean"]
    )

    print()
    print("A方向成立:", trend_up)
    print("B方向成立:", hit_12 > 0.5 and hit_45 > 0.5)
    print("Sanity check:", sanity_gap < 0.1)


if __name__ == "__main__":
    main()
