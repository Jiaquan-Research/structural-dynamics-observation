"""Variable-frequency analysis over random subset robustness results."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_CSV = PROJECT_ROOT / "outputs" / "csv" / "random_subset_robustness.csv"
OUTPUT_FIG = PROJECT_ROOT / "outputs" / "taxonomy" / "variable_importance.png"

STRONG_THRESHOLD = 0.3


def _parse_variables(series):
    return [item.strip() for item in str(series).split(",") if item.strip()]


def _top_variable_frequency(df_group):
    strong = df_group.loc[df_group["delta_mass"] > STRONG_THRESHOLD].copy()
    counter = Counter()
    for variables in strong["variables"]:
        counter.update(_parse_variables(variables))
    return counter, strong


def _average_delta_by_variable(df):
    accum = {}
    counts = {}
    for row in df.itertuples(index=False):
        variables = _parse_variables(row.variables)
        for variable in variables:
            accum[variable] = accum.get(variable, 0.0) + float(row.delta_mass)
            counts[variable] = counts.get(variable, 0) + 1
    rows = []
    for variable in sorted(accum):
        rows.append(
            {
                "variable": variable,
                "average_delta_mass": accum[variable] / max(counts[variable], 1),
                "count": counts[variable],
            }
        )
    return pd.DataFrame(rows).sort_values("average_delta_mass", ascending=False).reset_index(drop=True)


def _cooccurrence(strong_df):
    counter = Counter()
    for variables in strong_df["variables"]:
        parsed = sorted(_parse_variables(variables))
        for pair in combinations(parsed, 2):
            counter[pair] += 1
    return counter


def _plot_variable_importance(avg_df):
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.bar(avg_df["variable"], avg_df["average_delta_mass"], color="tab:blue", alpha=0.85)
    ax.set_ylabel("average delta_mass")
    ax.set_xlabel("xmeas variable")
    ax.set_title("Variable importance from random subset robustness audit")
    ax.tick_params(axis="x", rotation=90)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    OUTPUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FIG, dpi=150)
    plt.close(fig)


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    avg_df = _average_delta_by_variable(df)
    _plot_variable_importance(avg_df)

    for subset_size in sorted(df["subset_size"].unique()):
        group = df.loc[df["subset_size"] == subset_size].copy()
        counter, strong_df = _top_variable_frequency(group)
        print(f"Top 10 high-frequency variables in strong-separation subsets (V{subset_size})")
        for variable, count in counter.most_common(10):
            print(f"{variable}: {count}")
        if not counter:
            print("None")
        print()

        co_counter = _cooccurrence(strong_df)
        if co_counter:
            print(f"Top 10 co-occurring pairs in strong-separation subsets (V{subset_size})")
            for pair, count in co_counter.most_common(10):
                print(f"{pair[0]} + {pair[1]}: {count}")
            print()

    print("Top 10 variables by average delta_mass")
    print(avg_df.head(10).to_string(index=False))
    return avg_df


if __name__ == "__main__":
    main()
