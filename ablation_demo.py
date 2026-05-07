"""Demo script for the fixed-T ablation experiment."""

from __future__ import annotations

from ablation_experiment import (
    load_task5_results_csv,
    run_ablation,
    save_ablation_figures,
)


def main():
    ablation_results = run_ablation()
    task5_results = load_task5_results_csv("task5_results.csv")
    save_ablation_figures(ablation_results, task5_results=task5_results)

    print("Task5 vs ablation AUC comparison")
    for L in ablation_results["L_values"]:
        ablation_auc = ablation_results["results"][L]["auc_mean"]
        task5_auc = task5_results.get(L, {}).get("auc_mean")
        print(f"L={L}: task5_auc={task5_auc}, ablation_auc={ablation_auc:.4f}")

    auc_series = [ablation_results["results"][L]["auc_mean"] for L in ablation_results["L_values"]]
    peak_idx = max(range(len(auc_series)), key=auc_series.__getitem__)
    peak_is_interior = 0 < peak_idx < len(auc_series) - 1
    decreases_after_peak = all(
        auc_series[i] >= auc_series[i + 1] for i in range(peak_idx, len(auc_series) - 1)
    )

    print()
    print("Ablation trend judgment")
    print("Peak baseline length:", ablation_results["L_values"][peak_idx])
    print("Still inverted-U shaped:", peak_is_interior and decreases_after_peak)


if __name__ == "__main__":
    main()
