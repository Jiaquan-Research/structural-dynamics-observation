"""TEP industrial-data validation experiment."""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from task0_protocol import stride_sample

VARIABLE_SPECS = [
    ("XMEAS_7", "reactor pressure"),
    ("XMEAS_8", "reactor level"),
    ("XMEAS_9", "reactor temperature"),
    ("XMEAS_10", "purge rate"),
    ("XMEAS_11", "separator temperature"),
]

PAIR_LABELS = [
    "XMEAS7-XMEAS8",
    "XMEAS7-XMEAS9",
    "XMEAS7-XMEAS10",
    "XMEAS7-XMEAS11",
    "XMEAS8-XMEAS9",
    "XMEAS8-XMEAS10",
    "XMEAS8-XMEAS11",
    "XMEAS9-XMEAS10",
    "XMEAS9-XMEAS11",
    "XMEAS10-XMEAS11",
]

variables = [name.replace("_", "") for name, _description in VARIABLE_SPECS]
expected_pairs = [
    f"{variables[i]}-{variables[j]}"
    for i in range(len(variables))
    for j in range(i + 1, len(variables))
]
assert PAIR_LABELS == expected_pairs, f"PAIR_LABELS mismatch: {PAIR_LABELS} vs {expected_pairs}"


def _resolve_paths(data_dir="."):
    """Resolve TEP CSV paths with case-insensitive fallbacks."""

    directory = Path(data_dir)
    training_candidates = [
        directory / "fault_free_training.csv",
        directory / "Fault_Free_Training.csv",
    ]
    testing_candidates = [
        directory / "faulty_testing.csv",
        directory / "Faulty_Testing.csv",
    ]
    training_path = next((path for path in training_candidates if path.exists()), None)
    testing_path = next((path for path in testing_candidates if path.exists()), None)
    return training_path, testing_path


def _resolve_variable_columns(columns):
    """Resolve requested variable names against CSV columns."""

    lower_to_original = {column.lower(): column for column in columns}
    resolved = []
    for requested, _description in VARIABLE_SPECS:
        if requested in columns:
            resolved.append(requested)
            continue
        lowered = requested.lower()
        if lowered in lower_to_original:
            resolved.append(lower_to_original[lowered])
            continue
        print(", ".join(columns))
        return None
    return resolved


def _correlation_features(window):
    """Compute raw-correlation feature vector for one window."""

    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(window, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    tri = np.triu_indices(corr.shape[0], k=1)
    return corr[tri]


def _differenced_correlation_features(window):
    """Compute differenced-correlation feature vector for one window."""

    diffed = np.diff(window, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(diffed, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    tri = np.triu_indices(corr.shape[0], k=1)
    return corr[tri]


def _collect_window_features(data, sample_times, W, feature_fn):
    """Collect sliding-window features for all sample times."""

    if not sample_times:
        return np.empty((0, 0), dtype=float)
    return np.asarray([feature_fn(data[t - W : t]) for t in sample_times], dtype=float)


def _score_features(features, mu_f, s_f_inv):
    """Compute Mahalanobis-like squared scores."""

    centered = features - mu_f
    return np.einsum("ij,jk,ik->i", centered, s_f_inv, centered)


def _window_single_var_max_z(window, train_mean, train_std):
    """Return the maximum absolute z-score inside one window."""

    z = np.abs((window - train_mean) / train_std)
    return float(np.max(z))


def _window_log_condition_number(window):
    """Return log condition number of the differenced correlation matrix."""

    diffed = np.diff(window, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(diffed, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    singular_values = np.linalg.svd(corr, compute_uv=False)
    sigma_max = float(np.max(singular_values))
    sigma_min = float(max(np.min(singular_values), 1e-8))
    return float(np.log(sigma_max / sigma_min))


def _first_persistent_crossing(sample_times, values, threshold, k_persist, onset):
    """Return the first sample index with k consecutive threshold exceedances."""

    streak = 0
    for sample, value in zip(sample_times, values):
        if sample < onset:
            streak = 0
            continue
        if value > threshold:
            streak += 1
        else:
            streak = 0
        if streak >= k_persist:
            return int(sample)
    return None


def _dominance_series(contributions, sample_times, k_top, n_history):
    """Compute per-time pair dominance over the recent top-k history."""

    topk_indices = np.argsort(contributions, axis=1)[:, ::-1][:, :k_top]
    dominance_values = []
    dominance_pairs = []
    for idx in range(len(sample_times)):
        start = max(0, idx - n_history + 1)
        recent = topk_indices[start : idx + 1]
        window_count = recent.shape[0]
        counts = np.zeros(contributions.shape[1], dtype=int)
        for row in recent:
            counts[row] += 1
        best_idx = int(np.argmax(counts))
        dominance_pairs.append(PAIR_LABELS[best_idx])
        dominance_values.append(float(counts[best_idx] / max(window_count, 1)))
    return dominance_pairs, np.asarray(dominance_values, dtype=float)


def _pair_switching_rate(top1_indices, sample_times, n_history):
    """Compute how often the top-1 pair switched over recent history."""

    switching_values = []
    for idx in range(len(sample_times)):
        start = max(0, idx - n_history + 1)
        recent = top1_indices[start : idx + 1]
        if len(recent) <= 1:
            switching_values.append(0.0)
            continue
        switches = int(np.sum(recent[1:] != recent[:-1]))
        switching_values.append(float(switches / (len(recent) - 1)))
    return np.asarray(switching_values, dtype=float)


def _load_baseline_and_columns(data_dir="."):
    """Load baseline once and resolve selected columns."""

    training_path, testing_path = _resolve_paths(data_dir)
    if training_path is None or testing_path is None:
        print("请先从Kaggle下载TEP CSV数据集")
        return None

    header = pd.read_csv(training_path, nrows=0).columns.tolist()
    selected_columns = _resolve_variable_columns(header)
    if selected_columns is None:
        return None

    usecols = ["faultNumber", "simulationRun", "sample", *selected_columns]
    baseline_df = pd.read_csv(training_path, usecols=usecols)
    baseline_data = baseline_df[selected_columns].to_numpy(dtype=float)
    return training_path, testing_path, selected_columns, usecols, baseline_data


def _build_baseline_model(baseline_data, W, S):
    """Build the shared Version B baseline model once."""

    baseline_range = range(0, len(baseline_data))
    baseline_times = stride_sample(baseline_range, W, S)
    baseline_features_b = _collect_window_features(
        baseline_data, baseline_times, W, _differenced_correlation_features
    )
    mu_b = baseline_features_b.mean(axis=0)
    s_b = LedoitWolf().fit(baseline_features_b).covariance_
    s_b_inv = np.linalg.pinv(s_b + 0.1 * np.eye(baseline_features_b.shape[1]))
    baseline_d2_b = _score_features(baseline_features_b, mu_b, s_b_inv)
    train_mean = baseline_data.mean(axis=0)
    train_std = baseline_data.std(axis=0, ddof=1)
    train_std = np.where(train_std == 0.0, 1.0, train_std)
    return {
        "mu_b": mu_b,
        "s_b_inv": s_b_inv,
        "baseline_d2_mean": float(np.mean(baseline_d2_b)),
        "baseline_d2_std": float(np.std(baseline_d2_b, ddof=1)),
        "baseline_sample_count": int(len(baseline_times)),
        "baseline_row_count": int(len(baseline_data)),
        "train_mean": train_mean,
        "train_std": train_std,
    }


def _stream_fault_run_csv(path, usecols, fault_number):
    """Stream the huge faulty-testing CSV and extract the first run for one fault."""

    frames = []
    target_run = None
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=200000):
        if target_run is None:
            fault_chunk = chunk.loc[chunk["faultNumber"] == fault_number]
            if fault_chunk.empty:
                continue
            target_run = int(fault_chunk.iloc[0]["simulationRun"])
        run_chunk = chunk.loc[
            (chunk["faultNumber"] == fault_number) & (chunk["simulationRun"] == target_run)
        ]
        if not run_chunk.empty:
            frames.append(run_chunk)
        if target_run is not None:
            other_run_chunk = chunk.loc[
                (chunk["faultNumber"] == fault_number) & (chunk["simulationRun"] != target_run)
            ]
            if not other_run_chunk.empty:
                break
    if not frames:
        raise ValueError(f"faultNumber={fault_number} not found in {path}.")
    return pd.concat(frames, axis=0, ignore_index=True), target_run


def _load_all_fault_runs(path, usecols, fault_number):
    """Load all rows for one fault number and group by simulation run."""

    frames = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=200000):
        fault_chunk = chunk.loc[chunk["faultNumber"] == fault_number]
        if not fault_chunk.empty:
            frames.append(fault_chunk)
    if not frames:
        raise ValueError(f"faultNumber={fault_number} not found in {path}.")
    combined = pd.concat(frames, axis=0, ignore_index=True)
    runs = {}
    for run_id, run_df in combined.groupby("simulationRun", sort=True):
        runs[int(run_id)] = run_df.sort_values("sample")
    return runs


def _run_version_b_on_fault_run(
    fault_data,
    fault_onset,
    W,
    S,
    K_persist,
    k_top,
    n_history,
    baseline_model,
    threshold_sigma=2.0,
):
    """Run Version B only for one fault run using a shared baseline."""

    fault_range = range(0, len(fault_data))
    fault_times = stride_sample(fault_range, W, S)
    sample_times = np.asarray(fault_times, dtype=int)
    if len(sample_times) == 0:
        raise ValueError("No valid fault windows.")

    fault_features_b = _collect_window_features(
        fault_data, fault_times, W, _differenced_correlation_features
    )
    d2_b = _score_features(fault_features_b, baseline_model["mu_b"], baseline_model["s_b_inv"])
    single_var_max_z = np.asarray(
        [
            _window_single_var_max_z(
                fault_data[t - W : t], baseline_model["train_mean"], baseline_model["train_std"]
            )
            for t in fault_times
        ],
        dtype=float,
    )
    log_condition_number = np.asarray(
        [_window_log_condition_number(fault_data[t - W : t]) for t in fault_times],
        dtype=float,
    )

    centered_b = fault_features_b - baseline_model["mu_b"]
    per_pair_contribution = (centered_b**2) * np.diag(baseline_model["s_b_inv"])
    dominance_pairs, top_pair_dominance = _dominance_series(
        per_pair_contribution, sample_times, k_top=k_top, n_history=n_history
    )
    top1_indices = np.argmax(per_pair_contribution, axis=1)
    pair_switching_rate = _pair_switching_rate(top1_indices, sample_times, n_history=n_history)

    relation_threshold = baseline_model["baseline_d2_mean"] + threshold_sigma * baseline_model["baseline_d2_std"]
    t_relation_detect = _first_persistent_crossing(
        sample_times, d2_b, relation_threshold, K_persist, fault_onset
    )
    t_single_alarm = _first_persistent_crossing(
        sample_times, single_var_max_z, 3.0, K_persist, fault_onset
    )
    lead_time = (
        None
        if t_relation_detect is None or t_single_alarm is None
        else int(t_single_alarm - t_relation_detect)
    )

    post_fault_mask = sample_times >= fault_onset
    pre_fault_mask = sample_times < fault_onset
    if not np.any(post_fault_mask) or not np.any(pre_fault_mask):
        raise ValueError("Fault run does not contain both pre-fault and post-fault windows.")

    dominance_post = top_pair_dominance[post_fault_mask]
    dominance_pairs_post = np.asarray(dominance_pairs, dtype=object)[post_fault_mask]
    dominant_pair = Counter(dominance_pairs_post.tolist()).most_common(1)[0][0]

    return {
        "sample_times": sample_times,
        "d2_b": d2_b,
        "single_var_max_z": single_var_max_z,
        "log_condition_number": log_condition_number,
        "per_pair_contribution": per_pair_contribution,
        "top_pair_dominance": top_pair_dominance,
        "pair_switching_rate": pair_switching_rate,
        "t_relation_detect": t_relation_detect,
        "t_single_alarm": t_single_alarm,
        "lead_time": lead_time,
        "switching_mean": float(np.mean(pair_switching_rate[post_fault_mask])),
        "dominance_mean": float(np.mean(dominance_post)),
        "dominant_pair": dominant_pair,
        "d2_post_mean": float(np.mean(d2_b[post_fault_mask])),
        "d2_pre_mean": float(np.mean(d2_b[pre_fault_mask])),
    }


def run_tep_experiment(
    data_dir=".",
    fault_number=13,
    fault_onset=160,
    W=100,
    S=10,
    K_persist=5,
    k_top=3,
    n_history=10,
    threshold_sigma=2.0,
):
    """Run the single-run TEP industrial-data validation experiment."""

    print("Loading data...")
    loaded = _load_baseline_and_columns(data_dir)
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded

    fault_df, fault_run = _stream_fault_run_csv(testing_path, usecols=usecols, fault_number=fault_number)
    fault_data = fault_df[selected_columns].to_numpy(dtype=float)

    baseline_range = range(0, len(baseline_data))
    baseline_times = stride_sample(baseline_range, W, S)

    print("Building baseline...")
    baseline_model = _build_baseline_model(baseline_data, W, S)
    baseline_features_a = _collect_window_features(baseline_data, baseline_times, W, _correlation_features)
    mu_a = baseline_features_a.mean(axis=0)
    s_a = LedoitWolf().fit(baseline_features_a).covariance_
    s_a_inv = np.linalg.pinv(s_a + 0.1 * np.eye(baseline_features_a.shape[1]))

    print("Running detection...")
    fault_range = range(0, len(fault_data))
    fault_times = stride_sample(fault_range, W, S)
    sample_times = np.asarray(fault_times, dtype=int)
    fault_features_a = _collect_window_features(fault_data, fault_times, W, _correlation_features)
    d2_a = _score_features(fault_features_a, mu_a, s_a_inv)
    version_b = _run_version_b_on_fault_run(
        fault_data,
        fault_onset,
        W,
        S,
        K_persist,
        k_top,
        n_history,
        baseline_model,
        threshold_sigma=threshold_sigma,
    )

    lead_time_minutes = (
        None if version_b["lead_time"] is None else int(version_b["lead_time"] * 3)
    )
    post_fault_mask = sample_times >= fault_onset

    results = {
        "selected_variables": [
            {"column": column, "description": description}
            for column, (_, description) in zip(selected_columns, VARIABLE_SPECS)
        ],
        "baseline_sample_count": baseline_model["baseline_sample_count"],
        "baseline_row_count": baseline_model["baseline_row_count"],
        "fault_run": int(fault_run),
        "fault_onset": int(fault_onset),
        "fault_number": int(fault_number),
        "sample_times": sample_times,
        "version_a": {
            "d2": d2_a,
            "mean_post_fault": float(np.mean(d2_a[post_fault_mask])),
            "mean_all": float(np.mean(d2_a)),
        },
        "version_b": {
            "d2": version_b["d2_b"],
            "mean_post_fault": float(np.mean(version_b["d2_b"][post_fault_mask])),
            "mean_all": float(np.mean(version_b["d2_b"])),
        },
        "baseline_d2_mean": baseline_model["baseline_d2_mean"],
        "baseline_d2_std": baseline_model["baseline_d2_std"],
        "single_var_max_z": version_b["single_var_max_z"],
        "log_condition_number": version_b["log_condition_number"],
        "per_pair_contribution": version_b["per_pair_contribution"],
        "top_pair_dominance": version_b["top_pair_dominance"],
        "pair_switching_rate": version_b["pair_switching_rate"],
        "t_relation_detect": version_b["t_relation_detect"],
        "t_single_alarm": version_b["t_single_alarm"],
        "lead_time": version_b["lead_time"],
        "lead_time_minutes": lead_time_minutes,
        "dominant_pair_postfault": version_b["dominant_pair"],
    }
    return results


def save_tep_figures(results, output_dir="."):
    """Save the requested TEP validation figures."""

    os.makedirs(output_dir, exist_ok=True)

    print("Saving figures...")
    sample_times = results["sample_times"]
    d2 = results["version_b"]["d2"]
    zmax = results["single_var_max_z"]
    log_cond = results["log_condition_number"]
    dominance = results["top_pair_dominance"]
    switching_rate = results["pair_switching_rate"]
    onset = results["fault_onset"]

    fig = plt.figure(figsize=(12, 8), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.15)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(sample_times, d2, color="tab:blue", linewidth=1.5, label="D2(t)")
    ax1.axvline(onset, color="black", linestyle="--", linewidth=1.2, label="fault onset")
    ax1.axhline(
        results["baseline_d2_mean"] + 2.0 * results["baseline_d2_std"],
        color="tab:blue",
        linestyle="--",
        linewidth=1.2,
        label="D2 baseline+2sigma",
    )
    ax1.set_ylabel("D2(t)")
    ax1.grid(alpha=0.3)

    ax1r = ax1.twinx()
    ax1r.plot(sample_times, zmax, color="tab:orange", linewidth=1.2, label="single_var_max_z(t)")
    ax1r.plot(
        sample_times,
        log_cond,
        color="tab:green",
        linewidth=1.2,
        label="log_condition_number(t)",
    )
    ax1r.axhline(3.0, color="tab:orange", linestyle="--", linewidth=1.2, label="z=3.0")
    ax1r.set_ylabel("z / log-cond")

    handles_l, labels_l = ax1.get_legend_handles_labels()
    handles_r, labels_r = ax1r.get_legend_handles_labels()
    ax1.legend(handles_l + handles_r, labels_l + labels_r, loc="upper left")
    ax1.set_title(f"TEP fault {results['fault_number']}, run 1: Version B main curves")

    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
    ax2.plot(sample_times, dominance, color="tab:red", linewidth=1.5)
    ax2.axvline(onset, color="black", linestyle="--", linewidth=1.2)
    ax2.set_ylabel("top pair dominance")
    ax2.set_xlabel("sample index")
    ax2.set_ylim(0.0, 1.05)
    ax2.grid(alpha=0.3)
    ax2.set_title(f"Post-fault dominant pair: {results['dominant_pair_postfault']}")

    fig.savefig(os.path.join(output_dir, "tep_main_curves.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 5))
    heatmap = results["per_pair_contribution"].T
    image = ax.imshow(heatmap, aspect="auto", cmap="viridis", origin="lower")
    onset_idx = int(np.searchsorted(sample_times, onset))
    ax.axvline(onset_idx, color="white", linestyle="--", linewidth=1.2)
    ax.set_yticks(np.arange(len(PAIR_LABELS)))
    ax.set_yticklabels(PAIR_LABELS)
    ax.set_xticks(np.linspace(0, len(sample_times) - 1, 8, dtype=int))
    ax.set_xticklabels([str(int(sample_times[idx])) for idx in ax.get_xticks().astype(int)])
    ax.set_xlabel("sample index")
    ax.set_ylabel("pair")
    ax.set_title("Pair contribution heatmap")
    axr = ax.twinx()
    axr.plot(np.arange(len(sample_times)), switching_rate, color="tab:red", linewidth=1.2)
    axr.set_ylabel("pair switching rate", color="tab:red")
    axr.tick_params(axis="y", colors="tab:red")
    axr.set_ylim(0.0, 1.05)
    fig.colorbar(image, ax=ax, label="contribution")
    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, "tep_heatmap.png"), dpi=150)
    plt.close(fig)


def run_batch(
    fault_number=4,
    n_runs=500,
    threshold_sigma=2.0,
    data_dir=".",
    fault_onset=160,
    W=100,
    S=10,
    K_persist=5,
    k_top=3,
    n_history=10,
):
    """Run Version B across all available runs for one TEP fault."""

    print("Loading data...")
    loaded = _load_baseline_and_columns(data_dir)
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded

    print("Building baseline...")
    baseline_model = _build_baseline_model(baseline_data, W, S)
    runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)

    print("Running detection...")
    rows = []
    skipped_runs = []
    for run_idx in range(1, n_runs + 1):
        if run_idx % 50 == 0:
            print(f"Progress: {run_idx}/500")
        run_df = runs.get(run_idx)
        if run_df is None:
            skipped_runs.append(run_idx)
            continue
        fault_data = run_df[selected_columns].to_numpy(dtype=float)
        try:
            version_b = _run_version_b_on_fault_run(
                fault_data,
                fault_onset,
                W,
                S,
                K_persist,
                k_top,
                n_history,
                baseline_model,
                threshold_sigma=threshold_sigma,
            )
        except ValueError:
            skipped_runs.append(run_idx)
            continue
        rows.append(
            {
                "run_id": int(run_idx),
                "t_single_alarm": version_b["t_single_alarm"],
                "t_relation_detect": version_b["t_relation_detect"],
                "lead_time": version_b["lead_time"],
                "switching_mean": version_b["switching_mean"],
                "dominance_mean": version_b["dominance_mean"],
                "dominant_pair": version_b["dominant_pair"],
                "d2_post_mean": version_b["d2_post_mean"],
                "d2_pre_mean": version_b["d2_pre_mean"],
            }
        )

    if not rows:
        print("No valid runs found.")
        return None

    results_df = pd.DataFrame(rows)
    results_df.to_csv("f4_batch_results.csv", index=False, encoding="utf-8")

    relation_trigger_mask = results_df["t_relation_detect"].notna()
    single_trigger_mask = results_df["t_single_alarm"].notna()
    both_trigger_mask = relation_trigger_mask & single_trigger_mask
    lead_valid = results_df.loc[both_trigger_mask, "lead_time"].to_numpy(dtype=float)
    switching_values = results_df["switching_mean"].to_numpy(dtype=float)
    dominance_values = results_df["dominance_mean"].to_numpy(dtype=float)
    d2_ratio = (results_df["d2_post_mean"] / results_df["d2_pre_mean"]).to_numpy(dtype=float)
    dominant_counts = Counter(results_df["dominant_pair"].dropna().tolist())

    print("-- 触发率 --")
    print(f"D2触发率 = {relation_trigger_mask.mean():.3f}")
    print(f"单变量触发率 = {single_trigger_mask.mean():.3f}")
    print(f"两者都触发率 = {both_trigger_mask.mean():.3f}")
    lead_positive = float(np.mean(lead_valid > 0)) if lead_valid.size > 0 else float("nan")
    print(f"lead_time>0的比例 = {lead_positive:.3f}")

    print("-- lead_time分布（只统计两者都触发的） --")
    if lead_valid.size > 0:
        print(
            f"均值={np.mean(lead_valid):.3f}, 中位数={np.median(lead_valid):.3f}, "
            f"标准差={np.std(lead_valid, ddof=1) if lead_valid.size > 1 else 0.0:.3f}, "
            f"最小值={np.min(lead_valid):.0f}, 最大值={np.max(lead_valid):.0f}"
        )
    else:
        print("无有效lead_time样本")

    print("-- switching_mean分布 --")
    print(
        f"均值={np.mean(switching_values):.3f}, 中位数={np.median(switching_values):.3f}, "
        f"标准差={np.std(switching_values, ddof=1) if switching_values.size > 1 else 0.0:.3f}"
    )

    print("-- dominance_mean分布 --")
    print(
        f"均值={np.mean(dominance_values):.3f}, 中位数={np.median(dominance_values):.3f}"
    )

    print("-- dominant_pair分布 --")
    for pair_name, count in dominant_counts.most_common(3):
        print(f"{pair_name}: {count}")

    print("-- D2提升比 --")
    print(f"d2_post_mean / d2_pre_mean 的均值 = {np.mean(d2_ratio):.3f}")
    if skipped_runs:
        print(f"Skipped runs: {len(skipped_runs)}")

    fig, axes = plt.subplots(3, 1, figsize=(10, 12))

    if lead_valid.size > 0:
        axes[0].hist(lead_valid, bins=30, color="tab:blue", alpha=0.85)
        axes[0].axvline(0.0, color="black", linestyle="--", linewidth=1.2)
        axes[0].axvline(np.mean(lead_valid), color="tab:red", linestyle="--", linewidth=1.2)
    axes[0].set_title("Lead time distribution")
    axes[0].set_xlabel("lead_time (samples)")
    axes[0].set_ylabel("count")
    axes[0].grid(alpha=0.3)

    colors = np.where(relation_trigger_mask.to_numpy(), "tab:blue", "lightgray")
    axes[1].scatter(switching_values, dominance_values, c=colors, alpha=0.8)
    axes[1].set_title("switching_mean vs dominance_mean")
    axes[1].set_xlabel("switching_mean")
    axes[1].set_ylabel("dominance_mean")
    axes[1].grid(alpha=0.3)

    pair_names = [pair for pair, _count in dominant_counts.most_common()]
    pair_counts = [count for _pair, count in dominant_counts.most_common()]
    axes[2].bar(pair_names, pair_counts, color="tab:orange", alpha=0.85)
    axes[2].set_title("dominant_pair distribution")
    axes[2].set_xlabel("pair")
    axes[2].set_ylabel("count")
    axes[2].tick_params(axis="x", rotation=45)
    axes[2].grid(axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig("f4_batch_distributions.png", dpi=150)
    plt.close(fig)

    return {
        "dataframe": results_df,
        "selected_columns": selected_columns,
        "baseline_sample_count": baseline_model["baseline_sample_count"],
        "relation_trigger_rate": float(relation_trigger_mask.mean()),
        "single_trigger_rate": float(single_trigger_mask.mean()),
        "both_trigger_rate": float(both_trigger_mask.mean()),
        "lead_time_positive_rate": lead_positive,
        "dominant_pair_counts": dominant_counts,
        "switching_mean_mean": float(np.mean(switching_values)),
    }


def run_tep_validation():
    """Compatibility alias for the single-run TEP validation entry point."""

    results = run_tep_experiment()
    if results is None:
        return None
    save_tep_figures(results)

    print("使用的变量列表")
    for item in results["selected_variables"]:
        print(f"- {item['column']}  {item['description']}")
    print(f"fault_number = {results['fault_number']}")
    print(f"baseline样本数 = {results['baseline_sample_count']}")
    print(f"t_relation_detect = {results['t_relation_detect']}")
    print(f"t_single_alarm = {results['t_single_alarm']}")
    print(f"lead_time = {results['lead_time']}")
    print(f"lead_time_minutes = {results['lead_time_minutes']}")
    print(f"fault后dominance最高的pair = {results['dominant_pair_postfault']}")
    post_fault_mask = results["sample_times"] >= results["fault_onset"]
    print(
        f"fault后pair_switching_rate均值 = "
        f"{float(np.mean(results['pair_switching_rate'][post_fault_mask])):.3f}"
    )
    print(
        "Version A vs Version B的D2均值对比"
        f" = {results['version_a']['mean_post_fault']:.3f} vs {results['version_b']['mean_post_fault']:.3f}"
    )
    if results["t_relation_detect"] is None:
        print("WARNING: relation detector did not trigger")
    if results["t_single_alarm"] is None:
        print("WARNING: single-variable detector did not trigger")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        run_batch()
    else:
        run_tep_validation()
