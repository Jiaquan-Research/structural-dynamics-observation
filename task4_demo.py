"""Demo runner for experiment one analysis."""

from __future__ import annotations

from task4_analysis import run_experiment_one, save_experiment_one_figures


def main():
    results = run_experiment_one()
    save_experiment_one_figures(results)

    print("Condition B detector AUCs")
    print("Mahalanobis:", results["mahalanobis_auc"]["B"])
    print("PCA:", results["pca_auc"]["B"])
    print("OCSVM:", results["ocsvm_auc"]["B"])
    print()
    print("Bootstrap significance")
    print("B vs C:", results["bootstrap_B_vs_C"])
    print("B vs D:", results["bootstrap_B_vs_D"])
    print("B vs Baseline1 (PCA):", results["bootstrap_B_vs_baseline1"])
    print("B vs Baseline2 (OCSVM):", results["bootstrap_B_vs_baseline2"])
    print()
    print("Condition B single-sensor silence check")
    print(results["single_sensor"]["B"]["passes_single_sensor_silence_check"])
    print()
    print("Hypothesis criteria")
    print(
        "1. Single-sensor silence check:",
        results["single_sensor"]["B"]["passes_single_sensor_silence_check"],
    )
    print("2. Mahalanobis AUC > 0.7:", results["mahalanobis_auc"]["B"] > 0.7)
    print(
        "3. Mahalanobis > PCA on B (bootstrap p < 0.05):",
        results["bootstrap_B_vs_baseline1"]["significant"],
    )
    print(
        "4. Mahalanobis > OCSVM on B (bootstrap p < 0.05):",
        results["bootstrap_B_vs_baseline2"]["significant"],
    )


if __name__ == "__main__":
    main()
