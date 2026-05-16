"""Propagation-consistency / pair-switching audit within the XMEAS7-11 subspace."""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
for _name in ("analysis", "tep", "visualization", "robustness"):
    _path = str(SCRIPTS_ROOT / _name)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fault_stationary_scan import build_transition_matrix, compute_transition_entropy, _load_normal_runs
from tep_experiment import (
    PAIR_LABELS,
    _build_baseline_model,
    _compute_version_b_trajectory_series,
    _load_all_fault_runs,
    _load_baseline_and_columns,
)

WINDOW = 100
STEP = 100
SAMPLE_FILTER = 200
K_TOP = 3
N_HISTORY = 10
N_RUNS_PER_CONDITION = 20
LOCK_THRESHOLD = 0.95
CONDITIONS = ["NORMAL", "F06", "F08", "F12", "F14", "F01", "F03"]

CSV_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "csv"
TAXONOMY_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "taxonomy"
SUMMARY_OUTPUT = CSV_OUTPUT_DIR / "pair_switching_summary.csv"
EDGES_OUTPUT = CSV_OUTPUT_DIR / "pair_transition_edges.csv"
PATTERNS_OUTPUT = CSV_OUTPUT_DIR / "pair_sequence_patterns.csv"
ENTROPY_PLOT = TAXONOMY_OUTPUT_DIR / "transition_entropy_comparison.png"
SELF_RATIO_PLOT = TAXONOMY_OUTPUT_DIR / "self_transition_ratio.png"
HEATMAP_PLOT = TAXONOMY_OUTPUT_DIR / "pair_transition_heatmap.png"
LIFETIME_PLOT = TAXONOMY_OUTPUT_DIR / "pair_lifetime_distribution.png"


def _condition_fault_number(condition: str) -> int | None:
    if condition == "NORMAL":
        return None
    return int(condition[1:])


def _extract_sequences(run_data: np.ndarray, baseline_model: dict[str, object]) -> tuple[list[int], list[str]]:
    series = _compute_version_b_trajectory_series(
        run_data,
        WINDOW,
        STEP,
        K_TOP,
        N_HISTORY,
        baseline_model,
    )
    sample_times = np.asarray(series["sample_times"], dtype=int)
    top1_indices = np.asarray(series["top1_indices"], dtype=int)
    mask = sample_times > SAMPLE_FILTER
    eval_indices = top1_indices[mask]
    eval_pairs = [PAIR_LABELS[int(idx)] for idx in eval_indices]
    return eval_indices.tolist(), eval_pairs


def _sequence_lifetimes(pair_sequence: list[str]) -> list[int]:
    if not pair_sequence:
        return []
    lifetimes = []
    start = 0
    n = len(pair_sequence)
    while start < n:
        end = start
        while end + 1 < n and pair_sequence[end + 1] == pair_sequence[start]:
            end += 1
        lifetimes.append(end - start + 1)
        start = end + 1
    return lifetimes


def _row_normalized_edge_rows(condition: str, counts: np.ndarray, locked_top_pair: str | None = None) -> list[dict[str, object]]:
    rows = []
    if locked_top_pair is not None:
        total = float(np.sum(counts))
        rows.append(
            {
                "condition": condition,
                "source_pair": locked_top_pair,
                "target_pair": locked_top_pair,
                "transition_count": int(total),
                "transition_probability": 1.0,
            }
        )
        return rows

    probs = build_transition_matrix(counts)
    for i, src in enumerate(PAIR_LABELS):
        for j, dst in enumerate(PAIR_LABELS):
            count = int(counts[i, j])
            if count <= 0:
                continue
            rows.append(
                {
                    "condition": condition,
                    "source_pair": src,
                    "target_pair": dst,
                    "transition_count": count,
                    "transition_probability": float(probs[i, j]),
                }
            )
    return rows


def _top_patterns(pattern_counter: Counter[str], total_patterns: int, locked_pattern: str | None = None) -> list[dict[str, object]]:
    rows = []
    if locked_pattern is not None:
        rows.append(
            {
                "pattern": locked_pattern,
                "count": int(total_patterns),
                "frequency": 1.0 if total_patterns > 0 else float("nan"),
            }
        )
        return rows

    for pattern, count in pattern_counter.most_common(10):
        rows.append(
            {
                "pattern": pattern,
                "count": int(count),
                "frequency": float(count / max(total_patterns, 1)),
            }
        )
    return rows


def _cross_run_consistency(run_top_patterns: list[str]) -> str:
    if not run_top_patterns:
        return "no"
    counter = Counter(run_top_patterns)
    share = counter.most_common(1)[0][1] / len(run_top_patterns)
    if share >= 0.70:
        return "yes"
    if share >= 0.40:
        return "partial"
    return "no"


def _plot_entropy(summary_df: pd.DataFrame) -> None:
    df = summary_df.copy()
    df["condition"] = pd.Categorical(df["condition"], categories=CONDITIONS, ordered=True)
    df = df.sort_values("condition")
    colors = ["tab:red" if status == "locked" else "tab:blue" for status in df["geometry_status"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df["condition"].astype(str), df["transition_entropy"], color=colors, alpha=0.85)
    ax.set_xlabel("condition")
    ax.set_ylabel("transition_entropy")
    ax.set_title("Transition entropy comparison")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(ENTROPY_PLOT, dpi=150)
    plt.close(fig)


def _plot_self_ratio(summary_df: pd.DataFrame) -> None:
    df = summary_df.copy()
    df["condition"] = pd.Categorical(df["condition"], categories=CONDITIONS, ordered=True)
    df = df.sort_values("condition")
    colors = ["tab:red" if status == "locked" else "tab:green" for status in df["geometry_status"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(df["condition"].astype(str), df["self_transition_ratio"], color=colors, alpha=0.85)
    ax.axhline(LOCK_THRESHOLD, color="black", linestyle="--", linewidth=1.2)
    ax.set_xlabel("condition")
    ax.set_ylabel("self_transition_ratio")
    ax.set_title("Self-transition ratio")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(SELF_RATIO_PLOT, dpi=150)
    plt.close(fig)


def _plot_transition_heatmaps(transition_matrices: dict[str, np.ndarray]) -> None:
    switching_conditions = [condition for condition in CONDITIONS if condition in transition_matrices]
    if not switching_conditions:
        return
    n = len(switching_conditions)
    cols = min(3, n)
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows), squeeze=False, constrained_layout=True)
    for ax in axes.flat:
        ax.set_visible(False)

    image = None
    visible_axes = []
    for idx, condition in enumerate(switching_conditions):
        ax = axes[idx // cols][idx % cols]
        ax.set_visible(True)
        visible_axes.append(ax)
        matrix = transition_matrices[condition]
        image = ax.imshow(matrix, aspect="auto", cmap="viridis", origin="lower", vmin=0.0, vmax=1.0)
        ax.set_title(condition)
        ax.set_xticks(np.arange(len(PAIR_LABELS)))
        ax.set_xticklabels(PAIR_LABELS, rotation=90, fontsize=7)
        ax.set_yticks(np.arange(len(PAIR_LABELS)))
        ax.set_yticklabels(PAIR_LABELS, fontsize=7)
    if image is not None:
        fig.colorbar(image, ax=visible_axes, label="transition_probability", shrink=0.9)
    fig.savefig(HEATMAP_PLOT, dpi=150)
    plt.close(fig)


def _plot_lifetimes(lifetime_map: dict[str, list[int]]) -> None:
    switching_conditions = [condition for condition in CONDITIONS if condition in lifetime_map and lifetime_map[condition]]
    if not switching_conditions:
        return
    data = [lifetime_map[condition] for condition in switching_conditions]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(data, tick_labels=switching_conditions, showfliers=False)
    ax.set_xlabel("condition")
    ax.set_ylabel("pair_lifetime")
    ax.set_title("Pair lifetime distribution")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(LIFETIME_PLOT, dpi=150)
    plt.close(fig)


def main():
    CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TAXONOMY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        raise FileNotFoundError("TEP training/testing CSVs not found.")

    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, WINDOW, STEP)

    normal_runs_df = _load_normal_runs(".", selected_columns)
    run_maps: dict[str, dict[int, np.ndarray]] = {
        "NORMAL": {
            int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
            for run_id, run_df in normal_runs_df.items()
        }
    }
    for condition in CONDITIONS:
        fault_number = _condition_fault_number(condition)
        if fault_number is None:
            continue
        fault_runs_df = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
        run_maps[condition] = {
            int(run_id): run_df.sort_values("sample")[selected_columns].to_numpy(dtype=float)
            for run_id, run_df in fault_runs_df.items()
        }

    summary_rows = []
    edge_rows = []
    pattern_rows = []
    transition_matrices: dict[str, np.ndarray] = {}
    lifetime_map: dict[str, list[int]] = {}
    question_context: dict[str, dict[str, object]] = {}

    for condition in CONDITIONS:
        runs = run_maps[condition]
        selected_run_ids = sorted(runs)[:N_RUNS_PER_CONDITION]

        transition_counts = np.zeros((len(PAIR_LABELS), len(PAIR_LABELS)), dtype=float)
        all_pairs: list[str] = []
        all_lifetimes: list[int] = []
        pattern_counter: Counter[str] = Counter()
        total_patterns = 0
        run_top_patterns: list[str] = []

        for run_id in selected_run_ids:
            indices, pair_sequence = _extract_sequences(runs[run_id], baseline_model)
            if len(indices) >= 2:
                for src_idx, dst_idx in zip(indices[:-1], indices[1:]):
                    transition_counts[int(src_idx), int(dst_idx)] += 1.0
            all_pairs.extend(pair_sequence)
            lifetimes = _sequence_lifetimes(pair_sequence)
            all_lifetimes.extend(lifetimes)
            if len(pair_sequence) >= 3:
                run_patterns = [
                    "->".join(pair_sequence[i : i + 3]) for i in range(len(pair_sequence) - 2)
                ]
                counter = Counter(run_patterns)
                pattern_counter.update(counter)
                total_patterns += len(run_patterns)
                run_top_patterns.append(counter.most_common(1)[0][0])

        total_transitions = float(np.sum(transition_counts))
        if total_transitions > 0:
            self_transition_ratio = float(np.trace(transition_counts) / total_transitions)
        else:
            self_transition_ratio = float("nan")

        pair_counter = Counter(all_pairs)
        top_pair, top_pair_count = pair_counter.most_common(1)[0]
        top_pair_frequency = float(top_pair_count / max(len(all_pairs), 1))
        geometry_locked = bool(np.isfinite(self_transition_ratio) and self_transition_ratio >= LOCK_THRESHOLD)

        if geometry_locked:
            print(f"[LOCKED] {condition}: self_transition_ratio={self_transition_ratio:.6f}")
            print("No meaningful switching. Skipping sequence analysis.")
            transition_entropy = 0.0
            mean_lifetime = float(np.mean(all_lifetimes)) if all_lifetimes else float("nan")
            max_lifetime = float(np.max(all_lifetimes)) if all_lifetimes else float("nan")
            locked_count = int(total_transitions) if total_transitions > 0 else max(len(all_pairs) - 2, 0)
            edge_rows.extend(_row_normalized_edge_rows(condition, transition_counts, locked_top_pair=top_pair))
            locked_pattern = f"{top_pair}->{top_pair}->{top_pair}"
            for row in _top_patterns(pattern_counter, locked_count, locked_pattern=locked_pattern):
                pattern_rows.append({"condition": condition, **row})
            consistency = "yes"
        else:
            probs = build_transition_matrix(transition_counts)
            transition_matrices[condition] = probs
            transition_entropy = compute_transition_entropy(probs)
            mean_lifetime = float(np.mean(all_lifetimes)) if all_lifetimes else float("nan")
            max_lifetime = float(np.max(all_lifetimes)) if all_lifetimes else float("nan")
            edge_rows.extend(_row_normalized_edge_rows(condition, transition_counts))
            for row in _top_patterns(pattern_counter, total_patterns):
                pattern_rows.append({"condition": condition, **row})
            lifetime_map[condition] = all_lifetimes
            consistency = _cross_run_consistency(run_top_patterns)

        summary_rows.append(
            {
                "condition": condition,
                "geometry_status": "locked" if geometry_locked else "switching",
                "transition_entropy": float(transition_entropy),
                "self_transition_ratio": float(self_transition_ratio),
                "mean_lifetime": float(mean_lifetime),
                "max_lifetime": float(max_lifetime),
                "top_pair": top_pair,
                "top_pair_frequency": top_pair_frequency,
            }
        )
        question_context[condition] = {
            "geometry_locked": geometry_locked,
            "transition_entropy": float(transition_entropy),
            "self_transition_ratio": float(self_transition_ratio),
            "top_pair": top_pair,
            "top_pair_frequency": top_pair_frequency,
            "consistency": consistency,
        }

    summary_df = pd.DataFrame(summary_rows)
    summary_df["condition"] = pd.Categorical(summary_df["condition"], categories=CONDITIONS, ordered=True)
    summary_df = summary_df.sort_values("condition").reset_index(drop=True)
    summary_df["condition"] = summary_df["condition"].astype(str)
    edges_df = pd.DataFrame(edge_rows)
    patterns_df = pd.DataFrame(pattern_rows)

    summary_df.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8")
    edges_df.to_csv(EDGES_OUTPUT, index=False, encoding="utf-8")
    patterns_df.to_csv(PATTERNS_OUTPUT, index=False, encoding="utf-8")

    _plot_entropy(summary_df)
    _plot_self_ratio(summary_df)
    _plot_transition_heatmaps(transition_matrices)
    _plot_lifetimes(lifetime_map)

    print("=== CORE QUESTIONS ===")
    locked_flags = {condition: question_context[condition]["geometry_locked"] for condition in ("F06", "F08", "F14")}
    print(f"Q1 F06/F08/F14 geometry-locking: {locked_flags}")

    normal_entropy = float(question_context["NORMAL"]["transition_entropy"])
    compare_conditions = ["F06", "F08", "F12", "F14", "F01", "F03"]
    higher_than = [condition for condition in compare_conditions if normal_entropy > float(question_context[condition]["transition_entropy"])]
    print(f"Q2 NORMAL switching diversity higher than: {higher_than}")

    print(
        "Q3 F12 vs F06/F08/F14: "
        f"F12 status={question_context['F12']['geometry_locked']}, "
        f"entropy={question_context['F12']['transition_entropy']:.6f}, "
        f"top_pair={question_context['F12']['top_pair']}"
    )
    print(
        "Q4 F01 intermittent geometry locking: "
        f"status={question_context['F01']['geometry_locked']}, "
        f"self_transition_ratio={question_context['F01']['self_transition_ratio']:.6f}"
    )
    print(
        "Q5 F03 close to NORMAL: "
        f"F03 top_pair={question_context['F03']['top_pair']}, "
        f"NORMAL top_pair={question_context['NORMAL']['top_pair']}, "
        f"F03 entropy={question_context['F03']['transition_entropy']:.6f}, "
        f"NORMAL entropy={question_context['NORMAL']['transition_entropy']:.6f}"
    )

    switching_consistency = {
        condition: question_context[condition]["consistency"]
        for condition in CONDITIONS
        if question_context[condition]["geometry_locked"] is False
    }
    print(f"Q6 switching-condition ordering consistency: {switching_consistency}")

    print("=== INTERPRETATION ===")
    print("This audit analyzes geometry-state transition structure only within the XMEAS7-11 five-variable subspace.")
    print("It is not causal proof.")
    print("It does not imply physical causality or full-system propagation analysis.")

    generated = [str(SUMMARY_OUTPUT), str(EDGES_OUTPUT), str(PATTERNS_OUTPUT), str(ENTROPY_PLOT), str(SELF_RATIO_PLOT)]
    if transition_matrices:
        generated.append(str(HEATMAP_PLOT))
    if lifetime_map:
        generated.append(str(LIFETIME_PLOT))
    print(f"generated_files = {generated}")

    return summary_df, edges_df, patterns_df


if __name__ == "__main__":
    main()
