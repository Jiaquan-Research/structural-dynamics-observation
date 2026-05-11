"""Sweep requested rho values for condition B detector analysis."""

from __future__ import annotations

import csv

import matplotlib.pyplot as plt
import numpy as np

from task0_protocol import split_data
from task1_data_generator import generate_data
from task2_single_sensor import run_single_sensor_detector
from task3_detectors import (
    compute_correlation_audit,
    run_mahalanobis_detector,
    run_ocsvm_detector,
)


def main():
    rho_values = [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30, 0.35, 0.40]
    T = 2000
    W = 100
    S = 20
    seed = 42

    baseline_range, calibration_range, test_range = split_data(T)
    rows = []

    print(
        "rho | Mah_AUC | OCSVM_AUC | corr_ratio | "
        "single_sensor_silence | actual_rho"
    )
    for rho in rho_values:
        print(f"rho={rho:.2f} running...")
        data, metadata = generate_data("B", T=T, rho=rho, seed=seed)
        mahalanobis = run_mahalanobis_detector(
            data, baseline_range, calibration_range, test_range, W=W, S=S
        )
        ocsvm = run_ocsvm_detector(
            data, baseline_range, calibration_range, test_range, W=W, S=S
        )
        single_sensor = run_single_sensor_detector(data, metadata)
        audit = compute_correlation_audit(
            data, baseline_range, anomaly_start=metadata["anomaly_start"], W=W, S=S
        )

        normal_rates = single_sensor["trigger_rate_normal"]
        anomaly_rates = single_sensor["trigger_rate_anomaly"]
        mean_normal = float(np.mean(normal_rates))
        mean_anomaly = float(np.mean(anomaly_rates))
        diff = mean_anomaly - mean_normal

        normal_steps = metadata["anomaly_start"]
        anomaly_steps = T - metadata["anomaly_start"]
        alarm_count_normal = int(round(mean_normal * normal_steps * 5))
        alarm_count_anomaly = int(round(mean_anomaly * anomaly_steps * 5))

        print(
            f"  normal_rate={mean_normal:.5f} "
            f"anomaly_rate={mean_anomaly:.5f} "
            f"diff={diff:.6f}"
        )
        print(
            f"  alarm_count_normal={alarm_count_normal} "
            f"alarm_count_anomaly={alarm_count_anomaly}"
        )
        print(
            f"  max_consec_anomaly="
            f"{single_sensor['max_consecutive_alarm_anomaly']} "
            f"chi2_p={single_sensor['chi2_pvalue']:.6f}"
        )
        print(
            f"  normal_slice=[0:{normal_steps}] "
            f"anomaly_slice=[{normal_steps}:{T}]"
        )

        row = {
            "requested_rho": rho,
            "actual_rho": metadata["actual_rho"],
            "mah_auc": mahalanobis["auc_test"],
            "ocsvm_auc": ocsvm["auc_test"],
            "corr_ratio": audit["corr_ratio"],
            "single_sensor_silence": single_sensor["passes_single_sensor_silence_check"],
            "d2_baseline_mean": float(mahalanobis["d2_baseline"].mean()),
            "d2_test_mean": float(mahalanobis["d2_test"].mean()),
        }
        rows.append(row)
        print(
            f"{rho:0.2f} | {row['mah_auc']:.3f} | {row['ocsvm_auc']:.3f} | "
            f"{row['corr_ratio']:.3f} | {row['single_sensor_silence']} | "
            f"{row['actual_rho']:.2f}"
        )

    valid_rows = [
        row
        for row in rows
        if 0.65 <= row["mah_auc"] <= 0.90
        and row["single_sensor_silence"]
        and row["actual_rho"] == row["requested_rho"]
    ]
    if valid_rows:
        print()
        print("Valid rho values meeting all criteria:")
        for row in valid_rows:
            print(
                f"requested_rho={row['requested_rho']:.2f}, "
                f"mah_auc={row['mah_auc']:.3f}, corr_ratio={row['corr_ratio']:.3f}"
            )
    else:
        print()
        print("No requested rho value met all criteria.")

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(
        [row["requested_rho"] for row in rows],
        [row["mah_auc"] for row in rows],
        color="tab:blue",
        marker="o",
        label="Mahalanobis AUC",
    )
    axes[0].plot(
        [row["requested_rho"] for row in rows],
        [row["ocsvm_auc"] for row in rows],
        color="tab:green",
        marker="s",
        label="OCSVM AUC",
    )
    axes[0].axhline(0.75, color="black", linestyle="--", linewidth=1.0)
    axes[0].axhline(0.90, color="black", linestyle=":", linewidth=1.0)
    axes[0].set_ylabel("AUC")
    axes[0].set_title("Detector AUC vs requested rho")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(
        [row["requested_rho"] for row in rows],
        [row["corr_ratio"] for row in rows],
        color="tab:red",
        marker="o",
    )
    axes[1].axhline(1.0, color="black", linestyle="--", linewidth=1.0)
    axes[1].set_xlabel("requested rho")
    axes[1].set_ylabel("corr_ratio")
    axes[1].set_title("Correlation audit vs requested rho")
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("rho_sweep.png", dpi=150)

    with open("rho_sweep.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "requested_rho",
                "actual_rho",
                "mah_auc",
                "ocsvm_auc",
                "corr_ratio",
                "single_sensor_silence",
                "d2_baseline_mean",
                "d2_test_mean",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row["requested_rho"],
                    row["actual_rho"],
                    row["mah_auc"],
                    row["ocsvm_auc"],
                    row["corr_ratio"],
                    row["single_sensor_silence"],
                    row["d2_baseline_mean"],
                    row["d2_test_mean"],
                ]
            )


if __name__ == "__main__":
    main()
