"""Demo script for sparse statistic comparison."""

from __future__ import annotations

from sparse_statistic_experiment import run_sparse_statistic_comparison, save_sparse_figures


def main():
    results = run_sparse_statistic_comparison()
    save_sparse_figures(results)

    print("AUC heatmap (text)")
    for condition in results["conditions"]:
        values = {
            stat: round(results["results"][condition][stat]["auc_mean"], 3)
            for stat in results["statistics"]
        }
        print(condition, values)

    print()
    print("Best statistic by condition")
    for condition in results["conditions"]:
        best = max(
            results["statistics"],
            key=lambda stat: results["results"][condition][stat]["auc_mean"],
        )
        print(condition, best)

    max_d2_1pair_auc = results["results"]["B_1pair_12"]["max_d2"]["auc_mean"]
    sum_d2_1pair_auc = results["results"]["B_1pair_12"]["sum_d2"]["auc_mean"]
    top2_2pair_auc = results["results"]["B_2pair"]["top2_d2"]["auc_mean"]
    sum_d2_2pair_auc = results["results"]["B_2pair"]["sum_d2"]["auc_mean"]
    global_sum = results["results"]["B_global"]["sum_d2"]["auc_mean"]
    global_best_other = max(
        results["results"]["B_global"][stat]["auc_mean"]
        for stat in ["max_d2", "top2_d2", "top3_d2"]
    )
    sparse_loc_best = max(
        results["results"]["B_1pair_12"][stat]["loc_hit_rate"]
        for stat in ["max_d2", "top2_d2", "top3_d2"]
    )
    sparse_loc_best = max(
        sparse_loc_best,
        max(
            results["results"]["B_1pair_45"][stat]["loc_hit_rate"]
            for stat in ["max_d2", "top2_d2", "top3_d2"]
        ),
    )
    loc_hit_sum = max(
        results["results"]["B_1pair_12"]["sum_d2"]["loc_hit_rate"],
        results["results"]["B_1pair_45"]["sum_d2"]["loc_hit_rate"],
    )

    print()
    print("1pair max_d2 > sum_d2:", max_d2_1pair_auc > sum_d2_1pair_auc)
    print("2pair top2_d2 > sum_d2:", top2_2pair_auc > sum_d2_2pair_auc)
    print("global sum_d2 competitive:", global_sum >= global_best_other)
    print("loc_hit improves with sparse stat:", sparse_loc_best > loc_hit_sum)


if __name__ == "__main__":
    main()
