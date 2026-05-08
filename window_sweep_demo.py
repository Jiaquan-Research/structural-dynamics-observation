"""Demo script for the window-length sweep experiment."""

from __future__ import annotations

from window_sweep_experiment import run_window_sweep, save_window_sweep_figures


def main():
    results = run_window_sweep()
    save_window_sweep_figures(results)

    print("Window sweep summary")
    for W in results["W_values"]:
        auc_1pair = results["results"]["B_1pair_12"][W]["auc_mean"]
        auc_global = results["results"]["B_global"][W]["auc_mean"]
        n_eff_b = results["results"]["B_global"][W]["n_eff_baseline_mean"]
        n_eff_a = results["results"]["B_global"][W]["n_eff_anomaly_mean"]
        overlap = results["results"]["B_global"][W]["overlap_ratio"]
        print(
            f"W={W}: AUC_1pair={auc_1pair:.3f}, AUC_global={auc_global:.3f}, "
            f"n_eff_baseline={n_eff_b:.0f}, n_eff_anomaly={n_eff_a:.0f}, "
            f"overlap={overlap:.3f}"
        )
        if n_eff_a < 5:
            print(f"WARNING: W={W}, n_eff_anomaly≈{n_eff_a:.0f}, AUC may be unreliable")

    best_W = max(
        results["W_values"],
        key=lambda W: results["results"]["B_1pair_12"][W]["auc_mean"],
    )
    auc_series = [results["results"]["B_1pair_12"][W]["auc_mean"] for W in results["W_values"]]
    monotonic = all(auc_series[i] <= auc_series[i + 1] for i in range(len(auc_series) - 1))

    print()
    print("Best W for 1pair:", best_W)
    print("AUC monotonic with W:", monotonic)


if __name__ == "__main__":
    main()
