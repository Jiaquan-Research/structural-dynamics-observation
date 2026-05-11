"""Demo script for task3 detectors."""

from __future__ import annotations

import matplotlib.pyplot as plt

from task0_protocol import split_data
from task1_data_generator import generate_data
from task3_detectors import (
    _roc_curve_from_scores,
    compute_correlation_audit,
    run_mahalanobis_detector,
    run_ocsvm_detector,
    run_pca_detector,
)


def main():
    T = 2000
    W = 100
    S = 20
    rho = 0.4
    seed = 42

    baseline_range, calibration_range, test_range = split_data(T)
    data_a, _ = generate_data("A", T=T, rho=rho, seed=seed)
    data_b, _ = generate_data("B", T=T, rho=rho, seed=seed)

    result_a = run_mahalanobis_detector(data_a, baseline_range, calibration_range, test_range, W, S)
    result_b = run_mahalanobis_detector(data_b, baseline_range, calibration_range, test_range, W, S)
    pca_b = run_pca_detector(data_b, baseline_range, calibration_range, test_range, W, S)
    ocsvm_b = run_ocsvm_detector(data_b, baseline_range, calibration_range, test_range, W, S)
    audit_a = compute_correlation_audit(data_a, baseline_range, anomaly_start=T // 2, W=W, S=S)
    audit_b = compute_correlation_audit(data_b, baseline_range, anomaly_start=T // 2, W=W, S=S)

    print("Condition B detector comparison")
    print(
        "Mahalanobis:",
        {
            "d2_mean_baseline": float(result_b["d2_baseline"].mean()),
            "d2_mean_test": float(result_b["d2_test"].mean()),
            "auc_test": result_b["auc_test"],
            "S_f_condition_number": result_b["S_f_condition_number"],
            "detection_delay": result_b["detection_delay"],
        },
    )
    print(
        "PCA:",
        {
            "score_mean_test": float(pca_b["scores_test"].mean()),
            "auc_test": pca_b["auc_test"],
        },
    )
    print(
        "OCSVM:",
        {
            "score_mean_test": float(ocsvm_b["scores_test"].mean()),
            "auc_test": ocsvm_b["auc_test"],
        },
    )
    print(
        "Condition A Mahalanobis:",
        {
            "d2_mean_baseline": float(result_a["d2_baseline"].mean()),
            "d2_mean_test": float(result_a["d2_test"].mean()),
            "auc_test": result_a["auc_test"],
        },
    )
    print("Condition A correlation audit:", audit_a)
    print("Condition B correlation audit:", audit_b)

    d2_series = list(result_b["d2_baseline"]) + list(result_b["d2_calibration"]) + list(result_b["d2_test"])
    stride_times = list(range(W, baseline_range.stop, S)) + list(
        range(calibration_range.start + W, calibration_range.stop, S)
    ) + list(range(test_range.start + W, test_range.stop, S))

    fig, axes = plt.subplots(3, 1, figsize=(12, 12))

    axes[0].plot(stride_times, d2_series, color="tab:blue", linewidth=1.5)
    axes[0].axvline(baseline_range.stop, color="black", linestyle="--", linewidth=1.0)
    axes[0].axvline(calibration_range.stop, color="black", linestyle="--", linewidth=1.0)
    axes[0].axhline(result_b["theta_second"], color="tab:red", linestyle=":", linewidth=1.2)
    axes[0].set_title("Condition B Mahalanobis D2(t)")
    axes[0].set_ylabel("D2")
    axes[0].grid(alpha=0.3)

    qq = result_b["qqplot_data"]
    axes[1].scatter(qq["chi2_quantiles"], qq["d2_sorted"], s=18, color="tab:green")
    max_axis = max(float(qq["chi2_quantiles"].max()), float(qq["d2_sorted"].max()))
    axes[1].plot([0, max_axis], [0, max_axis], color="black", linestyle="--", linewidth=1.0)
    axes[1].set_title("Condition B QQ-plot")
    axes[1].set_xlabel("chi2(10) theoretical quantiles")
    axes[1].set_ylabel("empirical D2 quantiles")
    axes[1].grid(alpha=0.3)

    mah_fpr, mah_tpr = _roc_curve_from_scores(result_b["scores_baseline"], result_b["d2_test"])
    pca_fpr, pca_tpr = _roc_curve_from_scores(pca_b["scores_baseline"], pca_b["scores_test"])
    ocsvm_fpr, ocsvm_tpr = _roc_curve_from_scores(
        ocsvm_b["scores_baseline"], ocsvm_b["scores_test"]
    )
    axes[2].plot(mah_fpr, mah_tpr, label=f"Mahalanobis AUC={result_b['auc_test']:.3f}")
    axes[2].plot(pca_fpr, pca_tpr, label=f"PCA AUC={pca_b['auc_test']:.3f}")
    axes[2].plot(ocsvm_fpr, ocsvm_tpr, label=f"OCSVM AUC={ocsvm_b['auc_test']:.3f}")
    axes[2].plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1.0)
    axes[2].set_title("Condition B ROC curves")
    axes[2].set_xlabel("False positive rate")
    axes[2].set_ylabel("True positive rate")
    axes[2].legend(loc="lower right")
    axes[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig("task3_demo.png", dpi=150)


if __name__ == "__main__":
    main()
