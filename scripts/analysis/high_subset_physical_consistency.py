"""Physical-consistency audit for strong random subsets."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "random_subset_robustness.csv"
OUTPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "high_subset_physical_consistency.csv"
OUTPUT_REGION = PROJECT_ROOT / "outputs" / "taxonomy" / "high_subset_region_frequency.png"
OUTPUT_CHAIN = PROJECT_ROOT / "outputs" / "taxonomy" / "high_subset_chain_score.png"
OUTPUT_NETWORK = PROJECT_ROOT / "outputs" / "taxonomy" / "high_subset_variable_network.png"

TEP_VARIABLE_MAP = {
    "xmeas_1": "A feed",
    "xmeas_2": "D feed",
    "xmeas_3": "E feed",
    "xmeas_4": "A+C feed",
    "xmeas_5": "recycle flow",
    "xmeas_7": "reactor pressure",
    "xmeas_8": "reactor level",
    "xmeas_9": "reactor temperature",
    "xmeas_10": "purge rate",
    "xmeas_11": "separator temperature",
    "xmeas_14": "separator underflow",
    "xmeas_16": "stripper underflow",
    "xmeas_18": "stripper temperature",
    "xmeas_19": "stripper steam flow",
}

REGION_MAP = {
    "reactor": {7, 8, 9},
    "separator": {10, 11, 14},
    "stripper": {16, 18, 19},
    "feed/recycle": {1, 2, 3, 4, 5},
}

HIGHLIGHT_VARS = {"xmeas_7", "xmeas_11", "xmeas_18", "xmeas_19"}


def _parse_variables(text):
    return [item.strip() for item in str(text).split(",") if item.strip()]


def _variable_region(variable):
    if "_" not in variable:
        return "other"
    try:
        idx = int(variable.split("_")[1])
    except ValueError:
        return "other"
    for region, ids in REGION_MAP.items():
        if idx in ids:
            return region
    return "other"


def _regions_present(variables):
    regions = sorted({_variable_region(variable) for variable in variables if _variable_region(variable) != "other"})
    return regions


def _propagation_chain_score(regions):
    key_regions = {"reactor", "separator", "stripper"}
    count = len(key_regions.intersection(regions))
    if count >= 3:
        return 3
    if count == 2:
        return 2
    if count == 1:
        return 1
    return 0


def _plot_region_frequency(region_counter):
    labels = list(region_counter.keys())
    values = [region_counter[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values, color="tab:blue", alpha=0.85)
    ax.set_xlabel("region")
    ax.set_ylabel("frequency")
    ax.set_title("Region frequency in strong subsets")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    OUTPUT_REGION.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_REGION, dpi=150)
    plt.close(fig)


def _plot_chain_scores(scores):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(scores, bins=[-0.5, 0.5, 1.5, 2.5, 3.5], color="tab:orange", alpha=0.85, rwidth=0.9)
    ax.set_xlabel("propagation_chain_score")
    ax.set_ylabel("count")
    ax.set_title("Propagation chain score distribution")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_CHAIN, dpi=150)
    plt.close(fig)


def _plot_variable_network(pair_counter, variable_counter):
    graph = nx.Graph()
    for variable, count in variable_counter.items():
        graph.add_node(variable, weight=count)
    for (v1, v2), count in pair_counter.items():
        graph.add_edge(v1, v2, weight=count)

    pos = nx.spring_layout(graph, seed=42)
    node_sizes = [500 + 120 * variable_counter[node] for node in graph.nodes()]
    node_colors = []
    for node in graph.nodes():
        if node in HIGHLIGHT_VARS:
            node_colors.append("tab:red")
        else:
            node_colors.append("tab:blue")

    edge_weights = [graph[u][v]["weight"] for u, v in graph.edges()]
    max_weight = max(edge_weights) if edge_weights else 1.0
    widths = [1.0 + 5.0 * (w / max_weight) for w in edge_weights] if edge_weights else []

    fig, ax = plt.subplots(figsize=(12, 10))
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.85,
        ax=ax,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        width=widths,
        alpha=0.5,
        edge_color="gray",
        ax=ax,
    )
    nx.draw_networkx_labels(graph, pos, font_size=8, ax=ax)
    ax.set_title("Variable co-occurrence network in strong subsets")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(OUTPUT_NETWORK, dpi=150)
    plt.close(fig)


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    strong_df = df.loc[(df["delta_mass"] > 0.30) | (df["f13_mass"] > 0.50)].copy()
    if strong_df.empty:
        raise ValueError("No strong subsets found.")

    variable_counter = Counter()
    region_counter = Counter()
    cross_region_counter = Counter()
    pair_counter = Counter()
    scores = []
    output_rows = []

    for row in strong_df.itertuples(index=False):
        variables = _parse_variables(row.variables)
        variable_counter.update(variables)

        regions = _regions_present(variables)
        for region in regions:
            region_counter[region] += 1

        region_set = set(regions)
        if "reactor" in region_set and "separator" in region_set:
            cross_region_counter["reactor + separator"] += 1
        if "separator" in region_set and "stripper" in region_set:
            cross_region_counter["separator + stripper"] += 1
        if "reactor" in region_set and "stripper" in region_set:
            cross_region_counter["reactor + stripper"] += 1

        for pair in combinations(sorted(variables), 2):
            pair_counter[pair] += 1

        score = _propagation_chain_score(region_set)
        scores.append(score)
        output_rows.append(
            {
                "subset_id": int(row.subset_id),
                "subset_size": int(row.subset_size),
                "variables": row.variables,
                "delta_mass": float(row.delta_mass),
                "f13_mass": float(row.f13_mass),
                "regions_present": ",".join(regions) if regions else "none",
                "propagation_chain_score": int(score),
            }
        )

    output_df = pd.DataFrame(output_rows).sort_values(["subset_size", "subset_id"]).reset_index(drop=True)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

    _plot_region_frequency(region_counter)
    _plot_chain_scores(scores)
    _plot_variable_network(pair_counter, variable_counter)

    mean_score = float(pd.Series(scores, dtype=float).mean())
    high_chain_rate = float((pd.Series(scores) >= 2).mean())

    print("=== HIGH SUBSET PHYSICAL CONSISTENCY SUMMARY ===")
    print(f"strong subset count = {len(strong_df)}")
    print(f"mean propagation_chain_score = {mean_score:.6f}")
    print(f"high_chain_rate = {high_chain_rate:.6f}")
    print()
    print("Top variables:")
    for variable, count in variable_counter.most_common(10):
        label = TEP_VARIABLE_MAP.get(variable, "other")
        print(f"{variable} ({label}): {count}")
    print()
    print("Top co-occurring pairs:")
    for (v1, v2), count in pair_counter.most_common(10):
        print(f"{v1} + {v2}: {count}")
    print()
    print("Region frequencies:")
    for region, count in region_counter.items():
        print(f"{region}: {count}")
    print()
    print("Cross-region combinations:")
    for combo, count in cross_region_counter.items():
        print(f"{combo}: {count}")
    print()
    print("Conservative interpretation:")
    print("If strong subsets are repeatedly enriched for reactor, separator, and stripper variables together,")
    print("that is more consistent with a propagation-aligned observability subspace than with a random variable artifact.")
    print("This remains a physical-consistency check only, not a proof of system-level dynamics.")
    return output_df


if __name__ == "__main__":
    main()
