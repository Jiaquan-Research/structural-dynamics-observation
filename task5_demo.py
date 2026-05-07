"""Demo script for experiment two."""

from __future__ import annotations

from task5_experience import run_experiment_two, save_experiment_two_figures


def main():
    results = run_experiment_two()
    save_experiment_two_figures(results)

    print("Experiment two summary")
    for L in results["L_values"]:
        row = results["results"][L]
        print(
            f"L={L}: auc_mean={row['auc_mean']:.4f}, "
            f"95%CI=[{row['auc_95ci_lower']:.4f}, {row['auc_95ci_upper']:.4f}], "
            f"condition_number_mean={row['condition_number_mean']:.4f}, "
            f"silence_pass_rate={row['silence_pass_rate']:.4f}"
        )

    low = results["results"][50]
    high = results["results"][2000]
    ci_overlap = not (
        high["auc_95ci_lower"] > low["auc_95ci_upper"]
        or low["auc_95ci_lower"] > high["auc_95ci_upper"]
    )
    print()
    print("Trend judgment")
    print("AUC improves overall:", high["auc_mean"] > low["auc_mean"])
    print("95% CI overlap between L=50 and L=2000:", ci_overlap)


if __name__ == "__main__":
    main()
