"""Synthetic data generator for the second-order perception hypothesis experiment."""

from __future__ import annotations

import math
import unittest

import numpy as np
from scipy.stats import chi2_contingency, ttest_ind


def _equicorrelation_matrix(n_sensors, rho):
    """Create an equicorrelation matrix with diagonal 1 and off-diagonal rho."""

    if n_sensors <= 0:
        raise ValueError("n_sensors must be positive.")
    if rho < 0 or rho >= 1:
        raise ValueError("rho must satisfy 0 <= rho < 1.")

    matrix = np.full((n_sensors, n_sensors), rho, dtype=float)
    np.fill_diagonal(matrix, 1.0)
    return matrix


def _max_consecutive_true(mask):
    """Return the maximum run length of consecutive True values in a 1D mask."""

    max_run = 0
    current_run = 0
    for value in mask:
        if value:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
    return max_run


def _generate_rejection_correlated(n_samples, n_sensors, theta, rho, rng):
    """Generate correlated Gaussian samples with rejection on threshold exceedances."""

    if n_samples == 0:
        return np.empty((0, n_sensors), dtype=float), 1.0

    chol = np.linalg.cholesky(_equicorrelation_matrix(n_sensors, rho))
    accepted = []
    attempts = 0
    accepted_total = 0

    while len(accepted) < n_samples:
        draw_count = max(4 * (n_samples - len(accepted)), 128)
        raw = rng.standard_normal((draw_count, n_sensors))
        correlated = raw @ chol.T
        keep_mask = np.all(np.abs(correlated) <= theta, axis=1)
        accepted_batch = correlated[keep_mask]
        accepted_total += int(keep_mask.sum())
        accepted.extend(accepted_batch[: n_samples - len(accepted)])
        attempts += draw_count

    accepted_array = np.asarray(accepted, dtype=float)
    acceptance_rate = accepted_total / attempts
    return accepted_array, acceptance_rate


def _generate_correlated_shifted(n_samples, n_sensors, mean_shift, scale, rho, rng):
    """Generate correlated Gaussian samples with optional mean and variance shifts."""

    if n_samples == 0:
        return np.empty((0, n_sensors), dtype=float)

    chol = np.linalg.cholesky(_equicorrelation_matrix(n_sensors, rho))
    raw = rng.standard_normal((n_samples, n_sensors))
    correlated = raw @ chol.T
    return mean_shift + scale * correlated


def _trigger_rates(data, theta):
    """Compute per-sensor trigger rates for |epsilon| > theta."""

    return np.mean(np.abs(data) > theta, axis=0)


def _sensor_level_chi2_pvalue(normal_trigger_mask, anomaly_trigger_mask):
    """Compute sensor-level chi-square p-value from segment trigger masks."""

    n_sensors = normal_trigger_mask.shape[1]
    normal_sensor_triggered = np.any(normal_trigger_mask, axis=0)
    anomaly_sensor_triggered = np.any(anomaly_trigger_mask, axis=0)
    contingency = np.array(
        [
            [
                int(normal_sensor_triggered.sum()),
                int(n_sensors - normal_sensor_triggered.sum()),
            ],
            [
                int(anomaly_sensor_triggered.sum()),
                int(n_sensors - anomaly_sensor_triggered.sum()),
            ],
        ],
        dtype=float,
    )
    if np.any(contingency == 0):
        contingency += 0.5
    _, pvalue, _, _ = chi2_contingency(contingency, correction=True)
    return float(pvalue)


def generate_data(condition, T, N=5, theta=3.0, rho=0.4, seed=42):
    """Generate multi-sensor error time series under experimental conditions A-E.

    Parameters
    ----------
    condition : str
        Experiment condition in {'A', 'B', 'C', 'D', 'E'}.
    T : int
        Total number of time steps.
    N : int, optional
        Number of independent sensor modules.
    theta : float, optional
        Single-sensor alarm threshold used for metadata statistics.
    rho : float, optional
        Requested cross-module correlation for correlated anomaly conditions.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    tuple[numpy.ndarray, dict]
        ``data`` has shape ``(T, N)``. ``metadata`` contains generation and
        diagnostic statistics for the requested condition.
    """

    if condition not in {"A", "B", "C", "D", "E"}:
        raise ValueError("condition must be one of {'A', 'B', 'C', 'D', 'E'}.")
    if not isinstance(T, int) or T <= 0:
        raise ValueError("T must be a positive integer.")
    if not isinstance(N, int) or N <= 0:
        raise ValueError("N must be a positive integer.")
    if theta <= 0:
        raise ValueError("theta must be positive.")
    if rho < 0 or rho >= 1:
        raise ValueError("rho must satisfy 0 <= rho < 1.")

    rng = np.random.default_rng(seed)
    anomaly_start = T // 2
    normal_len = anomaly_start
    anomaly_len = T - anomaly_start

    normal_data = rng.standard_normal((normal_len, N))
    anomaly_data = None
    anomaly_trigger_source = None
    requested_rho = float(rho)
    actual_rho = float(rho)
    acceptance_rate = 1.0

    if condition == "A":
        anomaly_data = rng.standard_normal((anomaly_len, N))
        anomaly_trigger_source = anomaly_data
    elif condition == "B":
        while True:
            anomaly_data, acceptance_rate = _generate_rejection_correlated(
                anomaly_len, N, theta, actual_rho, rng
            )
            if acceptance_rate >= 0.30 or actual_rho <= 0.0:
                break
            # actual_rho is updated only when retrying; on exit it is the final accepted rho.
            actual_rho = round(max(0.0, actual_rho - 0.05), 10)
        anomaly_trigger_source = _generate_correlated_shifted(
            anomaly_len, N, mean_shift=0.0, scale=1.0, rho=actual_rho, rng=rng
        )
    elif condition == "C":
        anomaly_data = 0.5 + rng.standard_normal((anomaly_len, N))
        anomaly_trigger_source = anomaly_data
    elif condition == "D":
        anomaly_data = math.sqrt(1.5) * rng.standard_normal((anomaly_len, N))
        anomaly_trigger_source = anomaly_data
    else:
        anomaly_data = _generate_correlated_shifted(
            anomaly_len, N, mean_shift=0.5, scale=math.sqrt(1.5), rho=actual_rho, rng=rng
        )
        anomaly_trigger_source = anomaly_data

    data = np.vstack([normal_data, anomaly_data])

    normal_trigger_mask = np.abs(normal_data) > theta
    anomaly_trigger_mask_proposal = np.abs(anomaly_trigger_source) > theta
    normal_trigger_rates = _trigger_rates(normal_data, theta)
    anomaly_trigger_rates = _trigger_rates(anomaly_trigger_source, theta)

    actual_anomaly_alarm_mask = np.abs(anomaly_data) > theta
    chi2_pvalue_proposal = _sensor_level_chi2_pvalue(
        normal_trigger_mask, anomaly_trigger_mask_proposal
    )
    chi2_pvalue_actual = _sensor_level_chi2_pvalue(
        normal_trigger_mask, actual_anomaly_alarm_mask
    )
    # Consecutive alarm runs are checked on the raw per-time-step alarm sequence, not on stride samples.
    normal_max_run = max(_max_consecutive_true(normal_trigger_mask[:, i]) for i in range(N))
    anomaly_max_run = max(_max_consecutive_true(actual_anomaly_alarm_mask[:, i]) for i in range(N))

    metadata = {
        "condition": condition,
        "T": T,
        "requested_rho": requested_rho,
        "actual_rho": actual_rho,
        "acceptance_rate": float(acceptance_rate),
        "anomaly_start": anomaly_start,
        "single_sensor_trigger_rate_normal": normal_trigger_rates.tolist(),
        "single_sensor_trigger_rate_anomaly": anomaly_trigger_rates.tolist(),
        "chi2_pvalue_proposal": chi2_pvalue_proposal,
        "chi2_pvalue_actual": chi2_pvalue_actual,
        "has_consecutive_single_sensor_alarm_normal": normal_max_run >= 5,
        "has_consecutive_single_sensor_alarm_anomaly": anomaly_max_run >= 5,
        "max_consecutive_single_sensor_alarm_normal": int(normal_max_run),
        "max_consecutive_single_sensor_alarm_anomaly": int(anomaly_max_run),
    }
    return data, metadata


class GenerateDataTests(unittest.TestCase):
    def test_condition_a_trigger_rate_is_near_three_sigma_rate(self):
        data, metadata = generate_data("A", T=100000, seed=7)

        self.assertEqual(data.shape, (100000, 5))
        expected_rate = 2.0 * (1.0 - 0.9986501019683699)
        observed = np.array(
            metadata["single_sensor_trigger_rate_normal"]
            + metadata["single_sensor_trigger_rate_anomaly"]
        )
        self.assertTrue(np.all(np.abs(observed - expected_rate) < 0.0015))

    def test_condition_b_respects_rho_acceptance_and_trigger_stability(self):
        data, metadata = generate_data("B", T=1200, rho=0.8, seed=11)

        self.assertEqual(data.shape, (1200, 5))
        self.assertLessEqual(metadata["actual_rho"], metadata["requested_rho"])
        self.assertGreaterEqual(metadata["acceptance_rate"], 0.30)
        self.assertGreater(metadata["chi2_pvalue_proposal"], 0.05)
        self.assertIn("chi2_pvalue_actual", metadata)

    def test_condition_c_has_significant_mean_shift(self):
        data, _ = generate_data("C", T=4000, seed=19)
        normal = data[:2000].reshape(-1)
        anomaly = data[2000:].reshape(-1)
        _, pvalue = ttest_ind(normal, anomaly, equal_var=False)

        self.assertLess(pvalue, 1e-6)
        self.assertGreater(anomaly.mean(), normal.mean())

    def test_all_conditions_have_expected_shape(self):
        for condition in ["A", "B", "C", "D", "E"]:
            data, _ = generate_data(condition, T=250, N=5, seed=3)
            self.assertEqual(data.shape, (250, 5))


if __name__ == "__main__":
    unittest.main()
