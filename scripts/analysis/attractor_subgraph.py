"""Attractor subgraph analysis from stationary-weighted transition mass."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from fault_stationary_scan import (
    FAULT_NUMBERS,
    build_transition_matrix,
    compute_stationary,
    _accumulate_counts_for_runs,
    _fault_label,
    _load_normal_runs,
)
from tep_experiment import PAIR_LABELS, _build_baseline_model, _load_all_fault_runs, _load_baseline_and_columns

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

SUMMARY_PATH = OUTPUT_ROOT / "csv" / "fault_stationary_summary.csv"
REPRESENTATIVE_FAULTS = [0, 13, 12, 14]
TYPICAL_MASS_TARGET = 0.80


def _edge_name(i, j):
    return f"{PAIR_LABELS[int(i)]} -> {PAIR_LABELS[int(j)]}"


def build_mass_matrix(trans_matrix, stationary):
    """Return stationary-weighted transition mass matrix M(i,j)=pi_i*P(i,j)."""

    stationary = np.asarray(stationary, dtype=float)
    trans_matrix = np.asarray(trans_matrix, dtype=float)
    mass = stationary[:, None] * trans_matrix
    total = float(mass.sum())
    if total > 0:
        mass = mass / total
    return mass


def extract_typical_edge_set(mass_matrix, target_mass=TYPICAL_MASS_TARGET):
    """Extract the minimal descending-mass edge set covering target cumulative mass."""

    n_states = mass_matrix.shape[0]
    flat = []
    for i in range(n_states):
        for j in range(n_states):
            mass = float(mass_matrix[i, j])
            if mass > 0:
                flat.append((i, j, mass))
    flat.sort(key=lambda item: item[2], reverse=True)

    selected = []
    cumulative = 0.0
    for i, j, mass in flat:
        selected.append((i, j, mass))
        cumulative += mass
        if cumulative >= target_mass:
            break
    return selected


def compute_typical_edge_entropy(typical_edges):
    """Compute normalized entropy over the masses of the typical edge set."""

    masses = np.asarray([mass for _i, _j, mass in typical_edges], dtype=float)
    if len(masses) <= 1:
        return 0.0
    masses = masses / max(float(masses.sum()), 1e-12)
    entropy = float(-np.sum(masses * np.log(masses + 1e-10)))
    return float(entropy / math.log(len(masses)))


def _plot_taxonomy(summary_df, output_path):
    fig, ax = plt.subplots(figsize=(10, 7))

    sizes = summary_df["max_edge_mass"].to_numpy(dtype=float) * 3000.0
    colors = summary_df["typical_edge_entropy"].to_numpy(dtype=float)
    normal_mask = summary_df["fault_number"] == 0
    other_mask = ~normal_mask

    scatter = ax.scatter(
        summary_df.loc[other_mask, "typical_edge_count"],
        summary_df.loc[other_mask, "cycle_mass"],
        s=sizes[other_mask.to_numpy()],
        c=colors[other_mask.to_numpy()],
        cmap="viridis",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.7,
    )
    ax.scatter(
        summary_df.loc[normal_mask, "typical_edge_count"],
        summary_df.loc[normal_mask, "cycle_mass"],
        s=sizes[normal_mask.to_numpy()],
        c=colors[normal_mask.to_numpy()],
        cmap="viridis",
        alpha=0.95,
        edgecolors="gray",
        linewidths=2.0,
    )

    for row in summary_df.itertuples(index=False):
        label = "NORMAL" if int(row.fault_number) == 0 else f"F{int(row.fault_number):02d}"
        ax.text(
            float(row.typical_edge_count) + 0.2,
            float(row.cycle_mass) + 0.005,
            label,
            fontsize=8,
        )

    ax.set_xlabel("typical_edge_count")
    ax.set_ylabel("cycle_mass")
    ax.set_title("Attractor subgraph taxonomy")
    ax.grid(alpha=0.3)
    fig.colorbar(scatter, ax=ax, label="typical_edge_entropy")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _plot_representative_subgraphs(graph_payloads, output_path):
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()

    for ax, fault_number in zip(axes, REPRESENTATIVE_FAULTS):
        payload = graph_payloads[fault_number]
        fault_label = _fault_label(fault_number)
        stationary = payload["stationary"]
        typical_edges = payload["typical_edges"]

        graph = nx.DiGraph()
        for idx, label in enumerate(PAIR_LABELS):
            graph.add_node(idx, label=label, weight=float(stationary[idx]))
        for i, j, mass in typical_edges:
            graph.add_edge(int(i), int(j), weight=float(mass))

        pos = nx.spring_layout(graph, seed=42)
        node_sizes = 500 + 3000 * stationary
        node_colors = stationary
        edge_weights = [graph[u][v]["weight"] for u, v in graph.edges()]
        max_edge = max(edge_weights) if edge_weights else 1.0
        widths = [1.0 + 12.0 * (w / max_edge) for w in edge_weights] if edge_weights else []

        nx.draw_networkx_nodes(
            graph,
            pos,
            ax=ax,
            node_size=node_sizes,
            node_color=node_colors,
            cmap="viridis",
            vmin=0.0,
            vmax=max(0.1, float(np.max(stationary))),
        )
        nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            width=widths,
            alpha=0.75,
            arrows=True,
            arrowsize=12,
            edge_color="black",
            connectionstyle="arc3,rad=0.08",
        )
        nx.draw_networkx_labels(
            graph,
            pos,
            ax=ax,
            labels={idx: label.replace("XMEAS", "") for idx, label in enumerate(PAIR_LABELS)},
            font_size=8,
        )

        ax.set_title(fault_label)
        ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    if not Path(SUMMARY_PATH).exists():
        raise FileNotFoundError(f"Missing input summary: {SUMMARY_PATH}")

    loaded = _load_baseline_and_columns(".")
    if loaded is None:
        return None
    _training_path, testing_path, selected_columns, usecols, baseline_data = loaded
    baseline_model = _build_baseline_model(baseline_data, W=100, S=10)
    normal_runs = _load_normal_runs(".", selected_columns)

    summary_rows = []
    graph_payloads = {}

    for fault_number in FAULT_NUMBERS:
        fault_label = _fault_label(fault_number)
        if fault_number == 0:
            runs = normal_runs
            prefix = "NORMAL"
        else:
            runs = _load_all_fault_runs(testing_path, usecols=usecols, fault_number=fault_number)
            prefix = f"F{fault_number:02d}"

        counts = _accumulate_counts_for_runs(runs, selected_columns, baseline_model, n_runs=500)
        trans_matrix = build_transition_matrix(counts)
        stationary = compute_stationary(trans_matrix)
        stationary = stationary / max(float(stationary.sum()), 1e-12)
        mass_matrix = build_mass_matrix(trans_matrix, stationary)
        typical_edges = extract_typical_edge_set(mass_matrix)

        typical_edge_count = int(len(typical_edges))
        typical_edge_entropy = compute_typical_edge_entropy(typical_edges)
        max_i, max_j = divmod(int(np.argmax(mass_matrix)), mass_matrix.shape[1])
        max_edge = _edge_name(max_i, max_j)
        max_edge_mass = float(mass_matrix[max_i, max_j])
        self_loop_mass = float(np.trace(mass_matrix))
        cycle_mass = float(1.0 - self_loop_mass)

        print(
            f"{prefix} | "
            f"edge_count={typical_edge_count} | "
            f"edge_H={typical_edge_entropy:.3f} | "
            f"self={self_loop_mass:.3f} | "
            f"cycle={cycle_mass:.3f} | "
            f"max_edge={max_edge} | "
            f"max_mass={max_edge_mass:.3f}"
        )

        summary_rows.append(
            {
                "fault_number": int(fault_number),
                "typical_edge_count": typical_edge_count,
                "typical_edge_entropy": typical_edge_entropy,
                "max_edge": max_edge,
                "max_edge_mass": max_edge_mass,
                "self_loop_mass": self_loop_mass,
                "cycle_mass": cycle_mass,
            }
        )
        graph_payloads[fault_number] = {
            "stationary": stationary,
            "typical_edges": typical_edges,
        }

    summary_df = pd.DataFrame(summary_rows)
    (OUTPUT_ROOT / "csv").mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_ROOT / "csv" / "attractor_subgraph_summary.csv", index=False, encoding="utf-8")
    _plot_taxonomy(summary_df, OUTPUT_ROOT / "taxonomy" / "attractor_taxonomy.png")
    _plot_representative_subgraphs(graph_payloads, OUTPUT_ROOT / "taxonomy" / "attractor_subgraphs.png")
    return summary_df


if __name__ == "__main__":
    main()
