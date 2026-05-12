"""Mechanism audit for soft-state concentration on simple synthetic data."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from tep_experiment import _build_baseline_model, _compute_version_b_trajectory_series

W = 100
S = 100
K_TOP = 3
N_HISTORY = 10
SAMPLE_FILTER = 200
SOFTMAX_T = 1.0
N = 960
P = 5
SEED = 0
COLUMN_SHUFFLE_BASELINE = 0.92


def _softmax_rows(values, temperature=1.0):
    values = np.asarray(values, dtype=float) / float(temperature)
    shifted = values - np.max(values, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)


def _mean_top1_mass(x):
    baseline_model = _build_baseline_model(x, W, S)
    series = _compute_version_b_trajectory_series(
        x,
        W,
        S,
        K_TOP,
        N_HISTORY,
        baseline_model,
    )
    sample_times = np.asarray(series["sample_times"], dtype=int)
    mask = sample_times > SAMPLE_FILTER
    contributions = np.asarray(series["per_pair_contribution"], dtype=float)[mask]
    probs = _softmax_rows(contributions, temperature=SOFTMAX_T)
    return float(np.mean(np.max(probs, axis=1)))


def main():
    rng = np.random.default_rng(SEED)

    x_iid = rng.standard_normal((N, P))
    iid_mass = _mean_top1_mass(x_iid)

    x_var = rng.standard_normal((N, P))
    x_var[:, 0] *= 10.0
    var_mass = _mean_top1_mass(x_var)

    x_corr = rng.standard_normal((N, P))
    x_corr[:, 1] = x_corr[:, 0] + 0.1 * rng.standard_normal(N)
    corr_mass = _mean_top1_mass(x_corr)

    print(f"iid_gaussian mean_top1_mass = {iid_mass:.6f}")
    print(f"variance_imbalance mean_top1_mass = {var_mass:.6f}")
    print(f"pair_correlation mean_top1_mass = {corr_mass:.6f}")
    print(f"column_shuffle baseline = {COLUMN_SHUFFLE_BASELINE:.6f}")
    print()
    if abs(iid_mass - COLUMN_SHUFFLE_BASELINE) <= 0.05:
        print("softmax数学基准问题：测试1接近column_shuffle baseline")
    if var_mass > iid_mass:
        print("variance imbalance问题：测试2高于测试1")
    if corr_mass > iid_mass:
        print("correlation结构问题：测试3高于测试1")


if __name__ == "__main__":
    main()
