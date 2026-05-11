"""Data split and calibration protocol for the second-order perception experiment."""

from __future__ import annotations

import unittest

import numpy as np


def split_data(T, ratios=(0.25, 0.25, 0.5)):
    """Split ``T`` time steps into contiguous baseline, calibration, and test ranges.

    Parameters
    ----------
    T : int
        Total number of time steps. Must be a non-negative integer.
    ratios : tuple[float, float, float], optional
        Relative sizes of the baseline, calibration, and test segments.
        Values must be non-negative and have a positive sum.

    Returns
    -------
    tuple[range, range, range]
        Three contiguous, non-overlapping ``range`` objects whose union covers
        exactly ``range(0, T)``.
    """

    if not isinstance(T, int):
        raise TypeError("T must be an integer.")
    if T < 0:
        raise ValueError("T must be non-negative.")
    if len(ratios) != 3:
        raise ValueError("ratios must contain exactly three values.")

    ratios = np.asarray(ratios, dtype=float)
    if np.any(ratios < 0):
        raise ValueError("ratios must be non-negative.")

    total_ratio = ratios.sum()
    if total_ratio <= 0:
        raise ValueError("ratios must have a positive sum.")

    normalized = ratios / total_ratio
    boundaries = np.floor(np.cumsum(normalized[:-1]) * T).astype(int)
    b0, b1 = boundaries.tolist()

    return (range(0, b0), range(b0, b1), range(b1, T))


def stride_sample(indices, W, S):
    """Return valid sample times for sliding-window features inside a segment.

    Parameters
    ----------
    indices : range
        Contiguous index range for one data segment.
    W : int
        Window length. The earliest valid sample time is ``indices.start + W``.
    S : int
        Stride between adjacent sample times.

    Returns
    -------
    list[int]
        Valid sample times ``t`` satisfying ``t in indices`` and spaced by
        ``S``. The effective sample count is ``n_eff = len(output)``.
    """

    if not isinstance(indices, range):
        raise TypeError("indices must be a range object.")
    if indices.step != 1:
        raise ValueError("indices must have step size 1.")
    if not isinstance(W, int) or not isinstance(S, int):
        raise TypeError("W and S must be integers.")
    if W < 0:
        raise ValueError("W must be non-negative.")
    if S <= 0:
        raise ValueError("S must be positive.")
    if len(indices) < W:
        return []

    start_t = indices.start + W
    if start_t >= indices.stop:
        return []

    return list(range(start_t, indices.stop, S))


def select_threshold(d2_scores, labels, method="f1_max"):
    """Select a calibration threshold that maximizes F1 on D² scores.

    Parameters
    ----------
    d2_scores : array-like
        D² scores from the calibration segment only.
    labels : array-like
        Binary labels aligned with ``d2_scores`` from the calibration segment only.
    method : str, optional
        Threshold selection method. Currently only ``'f1_max'`` is supported.

    Returns
    -------
    float
        Threshold ``theta_second`` that maximizes F1 on the calibration data.

    Notes
    -----
    This function is intended strictly for calibration data. Do not call it on
    the test segment.
    """

    if method != "f1_max":
        raise ValueError("Only method='f1_max' is supported.")

    scores = np.asarray(d2_scores, dtype=float)
    y_true = np.asarray(labels)

    if scores.ndim != 1 or y_true.ndim != 1:
        raise ValueError("d2_scores and labels must be one-dimensional.")
    if len(scores) == 0:
        raise ValueError("d2_scores and labels must be non-empty.")
    if len(scores) != len(y_true):
        raise ValueError("d2_scores and labels must have the same length.")

    unique_labels = np.unique(y_true)
    if not np.all(np.isin(unique_labels, [0, 1])):
        raise ValueError("labels must be binary (0 or 1).")

    thresholds = np.unique(scores)
    best_threshold = float(thresholds[0])
    best_f1 = -1.0

    for threshold in thresholds:
        y_pred = (scores >= threshold).astype(int)
        tp = int(np.sum((y_pred == 1) & (y_true == 1)))
        fp = int(np.sum((y_pred == 1) & (y_true == 0)))
        fn = int(np.sum((y_pred == 0) & (y_true == 1)))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)

    return best_threshold


class SplitDataTests(unittest.TestCase):
    def test_ranges_are_contiguous_and_cover_total_length(self):
        baseline, calibration, test = split_data(2000)

        combined = list(baseline) + list(calibration) + list(test)
        self.assertEqual(len(baseline) + len(calibration) + len(test), 2000)
        self.assertEqual(combined, list(range(2000)))
        self.assertTrue(set(baseline).isdisjoint(calibration))
        self.assertTrue(set(baseline).isdisjoint(test))
        self.assertTrue(set(calibration).isdisjoint(test))


class StrideSampleTests(unittest.TestCase):
    def test_all_samples_stay_inside_range_with_fixed_stride(self):
        indices = range(500, 1000)
        samples = stride_sample(indices, W=50, S=25)

        self.assertTrue(all(t in indices for t in samples))
        self.assertEqual(samples[0], 550)
        self.assertTrue(all((b - a) == 25 for a, b in zip(samples, samples[1:])))
        self.assertEqual(len(samples), 18)

    def test_stride_sample_insufficient_length(self):
        result = stride_sample(range(0, 30), W=100, S=20)
        self.assertEqual(result, [])


class SelectThresholdTests(unittest.TestCase):
    def test_threshold_is_scalar_and_inside_score_range(self):
        scores = np.array([0.10, 0.20, 0.35, 0.80, 0.90, 0.95])
        labels = np.array([0, 0, 0, 1, 1, 1])

        threshold = select_threshold(scores, labels)

        self.assertTrue(np.isscalar(threshold))
        self.assertGreaterEqual(threshold, float(scores.min()))
        self.assertLessEqual(threshold, float(scores.max()))
        self.assertEqual(threshold, 0.80)


if __name__ == "__main__":
    unittest.main()
