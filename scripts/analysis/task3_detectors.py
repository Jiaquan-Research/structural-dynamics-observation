"""Second-order and baseline detectors for the simulation experiment."""

from __future__ import annotations

import unittest

import numpy as np
from scipy.stats import chi2, ttest_ind
from sklearn.covariance import LedoitWolf
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
from sklearn.svm import OneClassSVM

from task0_protocol import select_threshold, split_data, stride_sample
from task1_data_generator import generate_data


def _upper_triangle_features(window):
    """Extract upper-triangle off-diagonal correlation features from a window."""

    corr = np.corrcoef(window, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    tri_upper = np.triu_indices(corr.shape[0], k=1)
    return corr[tri_upper]


def _window_flatten(window):
    """Flatten a window into a 1D feature vector."""

    return window.reshape(-1)


def _collect_window_features(data, sample_times, W, feature_fn):
    """Collect feature vectors for a list of stride sample times."""

    if not sample_times:
        return np.empty((0, 0), dtype=float)
    features = [feature_fn(data[t - W : t]) for t in sample_times]
    return np.asarray(features, dtype=float)


def _calibration_threshold(scores):
    """Select a calibration threshold with a safe fallback for unlabeled calibration."""

    scores = np.asarray(scores, dtype=float)
    if scores.size == 0:
        raise ValueError("calibration scores must be non-empty.")
    labels = np.zeros(scores.shape[0], dtype=int)
    if np.unique(labels).size < 2:
        return float(np.max(scores))
    return float(select_threshold(scores, labels, method="f1_max"))


def _auc_against_baseline(baseline_scores, test_scores):
    """Compute ROC AUC using baseline as class 0 and test as class 1."""

    y_true = np.concatenate(
        [
            np.zeros(len(baseline_scores), dtype=int),
            np.ones(len(test_scores), dtype=int),
        ]
    )
    y_score = np.concatenate([baseline_scores, test_scores])
    if np.unique(y_true).size < 2:
        return 0.5
    return float(roc_auc_score(y_true, y_score))


def _estimate_covariance(features):
    """Estimate covariance with LedoitWolf or diagonal-regularized fallback."""

    try:
        return LedoitWolf().fit(features).covariance_
    except Exception:
        feature_dim = features.shape[1]
        variances = np.var(features, axis=0, ddof=1)
        return np.diag(variances + 0.01)


def _roc_curve_from_scores(baseline_scores, test_scores):
    """Return ROC curve arrays from baseline-vs-test scores."""

    y_true = np.concatenate(
        [
            np.zeros(len(baseline_scores), dtype=int),
            np.ones(len(test_scores), dtype=int),
        ]
    )
    y_score = np.concatenate([baseline_scores, test_scores])
    thresholds = np.r_[np.inf, np.sort(np.unique(y_score))[::-1]]
    tpr = []
    fpr = []
    positives = max(int(np.sum(y_true == 1)), 1)
    negatives = max(int(np.sum(y_true == 0)), 1)
    for threshold in thresholds:
        y_pred = y_score >= threshold
        tp = int(np.sum(y_pred & (y_true == 1)))
        fp = int(np.sum(y_pred & (y_true == 0)))
        tpr.append(tp / positives)
        fpr.append(fp / negatives)
    return np.asarray(fpr), np.asarray(tpr)


def compute_correlation_audit(data, baseline_range, anomaly_start, W=100, S=20):
    """Audit baseline vs anomaly correlation strength on stride windows."""

    baseline_times = stride_sample(baseline_range, W, S)
    anomaly_range = range(anomaly_start, data.shape[0])
    anomaly_times = [t for t in stride_sample(anomaly_range, W, S) if t > anomaly_start]

    def _mean_abs_corr(sample_times):
        if not sample_times:
            return 0.0, 0
        values = []
        for t in sample_times:
            features = _upper_triangle_features(data[t - W : t])
            values.append(float(np.mean(np.abs(features))))
        return float(np.mean(values)), len(values)

    baseline_mean_abs_corr, baseline_n = _mean_abs_corr(baseline_times)
    anomaly_mean_abs_corr, anomaly_n = _mean_abs_corr(anomaly_times)
    corr_ratio = (
        anomaly_mean_abs_corr / baseline_mean_abs_corr
        if baseline_mean_abs_corr > 0
        else np.inf
    )
    return {
        "baseline_mean_abs_corr": baseline_mean_abs_corr,
        "anomaly_mean_abs_corr": anomaly_mean_abs_corr,
        "corr_ratio": float(corr_ratio),
        "baseline_n_samples": int(baseline_n),
        "anomaly_n_samples": int(anomaly_n),
    }


def run_mahalanobis_detector(
    data, baseline_range, calibration_range, test_range, W=100, S=20
):
    """Run the correlation-feature Mahalanobis detector."""

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
    feature_dim = baseline_features.shape[1]
    covariance = _estimate_covariance(baseline_features)
    score_center = np.zeros(feature_dim, dtype=float)
    covariance_inv = np.linalg.pinv(covariance + 0.1 * np.eye(feature_dim))
    condition_number = float(np.linalg.cond(covariance))

    def _mahalanobis_sq(features):
        if features.size == 0:
            return np.asarray([], dtype=float)
        centered = features - score_center
        return np.einsum("ij,jk,ik->i", centered, covariance_inv, centered)

    d2_baseline = _mahalanobis_sq(baseline_features)
    d2_calibration = _mahalanobis_sq(calibration_features)
    d2_test = _mahalanobis_sq(test_features)

    theta_second = _calibration_threshold(d2_calibration)
    alarm_test = d2_test >= theta_second
    auc_test = _auc_against_baseline(d2_baseline, d2_test)
    detection_delay = int(np.argmax(alarm_test)) if np.any(alarm_test) else None

    probs = (np.arange(1, len(d2_baseline) + 1) - 0.5) / max(len(d2_baseline), 1)
    qqplot_data = {
        "d2_sorted": np.sort(d2_baseline),
        "chi2_quantiles": chi2.ppf(probs, df=feature_dim),
    }

    return {
        "scores_baseline": d2_baseline,
        "baseline_mu_f": mu_f,
        "baseline_S_f": covariance,
        "S_f_condition_number": condition_number,
        "d2_baseline": d2_baseline,
        "d2_calibration": d2_calibration,
        "d2_test": d2_test,
        "theta_second": float(theta_second),
        "alarm_test": alarm_test,
        "auc_test": auc_test,
        "detection_delay": detection_delay,
        "qqplot_data": qqplot_data,
    }


def run_pca_detector(
    data,
    baseline_range,
    calibration_range,
    test_range,
    W=100,
    S=20,
    n_components=3,
):
    """Run the PCA residual detector on sliding windows."""

    baseline_times = stride_sample(baseline_range, W, S)
    calibration_times = stride_sample(calibration_range, W, S)
    test_times = stride_sample(test_range, W, S)

    if len(baseline_range) == 0:
        raise ValueError("baseline_range must be non-empty.")

    pca = PCA(n_components=n_components)
    pca.fit(data[baseline_range.start : baseline_range.stop])

    def _window_residual_score(window):
        transformed = pca.transform(window)
        reconstructed = pca.inverse_transform(transformed)
        residual = window - reconstructed
        return float(np.sum(residual**2))

    baseline_scores = _collect_window_features(data, baseline_times, W, _window_residual_score)
    calibration_scores = _collect_window_features(
        data, calibration_times, W, _window_residual_score
    ).reshape(-1)
    test_scores = _collect_window_features(data, test_times, W, _window_residual_score).reshape(-1)

    baseline_scores = baseline_scores.reshape(-1)
    theta_pca = _calibration_threshold(calibration_scores)
    alarm_test = test_scores >= theta_pca
    auc_test = _auc_against_baseline(baseline_scores, test_scores)

    return {
        "scores_baseline": baseline_scores,
        "scores_calibration": calibration_scores,
        "scores_test": test_scores,
        "theta_pca": float(theta_pca),
        "alarm_test": alarm_test,
        "auc_test": auc_test,
    }


def run_ocsvm_detector(data, baseline_range, calibration_range, test_range, W=100, S=20):
    """Run the one-class SVM detector on flattened sliding windows."""

    baseline_times = stride_sample(baseline_range, W, S)
    calibration_times = stride_sample(calibration_range, W, S)
    test_times = stride_sample(test_range, W, S)

    baseline_features = _collect_window_features(
        data, baseline_times, W, _upper_triangle_features
    )
    calibration_features = _collect_window_features(
        data, calibration_times, W, _upper_triangle_features
    )
    test_features = _collect_window_features(data, test_times, W, _upper_triangle_features)

    if baseline_features.size == 0:
        raise ValueError("baseline segment does not contain enough samples for W and S.")

    ocsvm = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05)
    ocsvm.fit(baseline_features)

    baseline_scores = (-ocsvm.decision_function(baseline_features)).reshape(-1)
    calibration_scores = (-ocsvm.decision_function(calibration_features)).reshape(-1)
    test_scores = (-ocsvm.decision_function(test_features)).reshape(-1)

    theta_ocsvm = _calibration_threshold(calibration_scores)
    alarm_test = test_scores >= theta_ocsvm
    auc_test = _auc_against_baseline(baseline_scores, test_scores)

    return {
        "scores_baseline": baseline_scores,
        "scores_calibration": calibration_scores,
        "scores_test": test_scores,
        "theta_ocsvm": float(theta_ocsvm),
        "alarm_test": alarm_test,
        "auc_test": auc_test,
    }


class DetectorTests(unittest.TestCase):
    def test_mahalanobis_condition_b_test_mean_exceeds_baseline(self):
        data, _ = generate_data("B", T=2000, rho=0.4, seed=42)
        baseline_range, calibration_range, test_range = split_data(2000)
        result = run_mahalanobis_detector(
            data, baseline_range, calibration_range, test_range, W=100, S=20
        )

        _, pvalue = ttest_ind(
            result["d2_baseline"], result["d2_test"], equal_var=False
        )
        self.assertLess(pvalue, 0.05)
        self.assertGreater(result["d2_test"].mean(), result["d2_baseline"].mean())

    def test_mahalanobis_condition_a_has_no_significant_mean_difference(self):
        data, _ = generate_data("A", T=2000, seed=42)
        baseline_range, calibration_range, test_range = split_data(2000)
        result = run_mahalanobis_detector(
            data, baseline_range, calibration_range, test_range, W=100, S=20
        )

        _, pvalue = ttest_ind(
            result["d2_baseline"], result["d2_test"], equal_var=False
        )
        self.assertGreater(pvalue, 0.05)

    def test_all_detectors_return_auc_test(self):
        data, _ = generate_data("B", T=2000, rho=0.4, seed=42)
        baseline_range, calibration_range, test_range = split_data(2000)

        mah = run_mahalanobis_detector(data, baseline_range, calibration_range, test_range)
        pca = run_pca_detector(data, baseline_range, calibration_range, test_range)
        ocsvm = run_ocsvm_detector(data, baseline_range, calibration_range, test_range)

        self.assertIn("auc_test", mah)
        self.assertIn("auc_test", pca)
        self.assertIn("auc_test", ocsvm)

    def test_condition_number_is_finite_positive(self):
        data, _ = generate_data("B", T=2000, rho=0.4, seed=42)
        baseline_range, calibration_range, test_range = split_data(2000)
        result = run_mahalanobis_detector(
            data, baseline_range, calibration_range, test_range, W=100, S=20
        )

        self.assertTrue(np.isfinite(result["S_f_condition_number"]))
        self.assertGreater(result["S_f_condition_number"], 0.0)


if __name__ == "__main__":
    unittest.main()
