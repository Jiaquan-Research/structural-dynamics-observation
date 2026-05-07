"""Single-sensor detector for the second-order perception hypothesis experiment."""

from __future__ import annotations

import unittest

import numpy as np
from scipy.stats import chi2_contingency

from task1_data_generator import generate_data


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


def _chi2_trigger_pvalue(normal_mask, anomaly_mask):
    """Return chi-square p-value for trigger counts on actual data."""

    normal_triggered = int(normal_mask.sum())
    anomaly_triggered = int(anomaly_mask.sum())
    contingency = np.array(
        [
            [normal_triggered, int(normal_mask.size - normal_triggered)],
            [anomaly_triggered, int(anomaly_mask.size - anomaly_triggered)],
        ],
        dtype=float,
    )
    if np.any(contingency == 0):
        contingency += 0.5
    _, pvalue, _, _ = chi2_contingency(contingency, correction=True)
    return float(pvalue)


def run_single_sensor_detector(data, metadata, theta=3.0):
    """Run per-sensor threshold detection on actual time-series data.

    Parameters
    ----------
    data : numpy.ndarray
        Time-series data of shape ``(T, N)``.
    metadata : dict
        Metadata returned by ``generate_data``. Must include ``anomaly_start``.
    theta : float, optional
        Absolute-value threshold for single-sensor alarms.

    Returns
    -------
    dict
        Detection outputs and summary statistics computed on actual data.
    """

    data = np.asarray(data, dtype=float)
    if data.ndim != 2:
        raise ValueError("data must be a 2D array of shape (T, N).")
    if "anomaly_start" not in metadata:
        raise ValueError("metadata must contain 'anomaly_start'.")
    if theta <= 0:
        raise ValueError("theta must be positive.")

    T, n_sensors = data.shape
    anomaly_start = int(metadata["anomaly_start"])
    if anomaly_start < 0 or anomaly_start > T:
        raise ValueError("metadata['anomaly_start'] must satisfy 0 <= anomaly_start <= T.")

    normal_slice = slice(0, anomaly_start)
    anomaly_slice = slice(anomaly_start, T)

    alarm_mask = np.abs(data) > theta
    normal_alarm_mask = alarm_mask[normal_slice]
    anomaly_alarm_mask = alarm_mask[anomaly_slice]

    trigger_rate_normal = np.mean(normal_alarm_mask, axis=0).tolist()
    trigger_rate_anomaly = np.mean(anomaly_alarm_mask, axis=0).tolist()
    mean_trigger_rate_normal = float(np.mean(trigger_rate_normal))
    mean_trigger_rate_anomaly = float(np.mean(trigger_rate_anomaly))
    chi2_pvalue = _chi2_trigger_pvalue(normal_alarm_mask, anomaly_alarm_mask)

    # Consecutive alarms are checked on raw time steps from the actual output data.
    max_consecutive_alarm_normal = max(
        _max_consecutive_true(normal_alarm_mask[:, sensor_idx]) for sensor_idx in range(n_sensors)
    )
    max_consecutive_alarm_anomaly = max(
        _max_consecutive_true(anomaly_alarm_mask[:, sensor_idx]) for sensor_idx in range(n_sensors)
    )
    has_stable_consecutive_alarm_anomaly = max_consecutive_alarm_anomaly >= 5

    normal_total = float(np.mean(normal_alarm_mask))
    anomaly_total = float(np.mean(anomaly_alarm_mask))
    chi2_significant = (chi2_pvalue < 0.05) and (anomaly_total > normal_total)
    tolerance = 0.002
    passes_rate_check = mean_trigger_rate_anomaly <= mean_trigger_rate_normal + tolerance
    passes_consec_check = max_consecutive_alarm_anomaly <= 2
    passes_single_sensor_silence_check = passes_rate_check and passes_consec_check

    return {
        "alarm_mask": alarm_mask,
        "trigger_rate_normal": trigger_rate_normal,
        "trigger_rate_anomaly": trigger_rate_anomaly,
        "mean_trigger_rate_normal": mean_trigger_rate_normal,
        "mean_trigger_rate_anomaly": mean_trigger_rate_anomaly,
        "chi2_pvalue": chi2_pvalue,
        "chi2_significant": chi2_significant,
        "max_consecutive_alarm_normal": int(max_consecutive_alarm_normal),
        "max_consecutive_alarm_anomaly": int(max_consecutive_alarm_anomaly),
        "has_stable_consecutive_alarm_anomaly": has_stable_consecutive_alarm_anomaly,
        "passes_single_sensor_silence_check": passes_single_sensor_silence_check,
    }


def validate_condition_b(data, metadata):
    """Validate whether condition B passes the single-sensor silence check."""

    result = run_single_sensor_detector(data, metadata)
    print(
        "passes_single_sensor_silence_check:",
        result["passes_single_sensor_silence_check"],
    )
    print("chi2_pvalue:", result["chi2_pvalue"])
    print("max_consecutive_alarm_anomaly:", result["max_consecutive_alarm_anomaly"])
    if not result["passes_single_sensor_silence_check"]:
        print("WARNING: condition B failed the single-sensor silence check")
    return result


class SingleSensorDetectorTests(unittest.TestCase):
    def test_condition_a_has_no_significant_trigger_difference(self):
        data, metadata = generate_data("A", T=2000, seed=13)
        result = run_single_sensor_detector(data, metadata)

        self.assertGreater(result["chi2_pvalue"], 0.05)

    def test_condition_b_passes_single_sensor_silence_check(self):
        data, metadata = generate_data("B", T=400, rho=0.4, seed=42)
        result = run_single_sensor_detector(data, metadata)

        self.assertTrue(result["passes_single_sensor_silence_check"])

    def test_condition_c_is_significant_and_not_silent(self):
        data, metadata = generate_data("C", T=40000, seed=19)
        result = run_single_sensor_detector(data, metadata)

        self.assertTrue(result["chi2_significant"])
        self.assertFalse(result["passes_single_sensor_silence_check"])

    def test_output_contains_required_fields(self):
        data, metadata = generate_data("A", T=200, seed=5)
        result = run_single_sensor_detector(data, metadata)

        required_fields = {
            "alarm_mask",
            "trigger_rate_normal",
            "trigger_rate_anomaly",
            "mean_trigger_rate_normal",
            "mean_trigger_rate_anomaly",
            "chi2_pvalue",
            "chi2_significant",
            "max_consecutive_alarm_normal",
            "max_consecutive_alarm_anomaly",
            "has_stable_consecutive_alarm_anomaly",
            "passes_single_sensor_silence_check",
        }
        self.assertTrue(required_fields.issubset(result.keys()))
        self.assertEqual(result["alarm_mask"].shape, data.shape)


if __name__ == "__main__":
    unittest.main()
