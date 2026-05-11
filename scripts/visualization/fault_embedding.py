"""Visualize structural fault fingerprints in a small handcrafted embedding."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

fault_data = {
    "F4": {
        "d2_trigger": 0.150,
        "switching": 0.410,
        "dominance": 0.814,
        "d2_ratio": 1.207,
        "pair_concentration": 0.306,
    },
    "F13": {
        "d2_trigger": 1.000,
        "switching": 0.094,
        "dominance": 0.955,
        "d2_ratio": 10.526,
        "pair_concentration": 0.992,
    },
    "F15": {
        "d2_trigger": 0.092,
        "switching": 0.414,
        "dominance": 0.811,
        "d2_ratio": 1.143,
        "pair_concentration": 0.404,
    },
    "F16": {
        "d2_trigger": 0.100,
        "switching": 0.404,
        "dominance": 0.816,
        "d2_ratio": 1.149,
        "pair_concentration": 0.402,
    },
    "F19": {
        "d2_trigger": 0.426,
        "switching": 0.348,
        "dominance": 0.871,
        "d2_ratio": 1.566,
        "pair_concentration": 0.854,
    },
}


def _normalized_metrics(data):
    """Return fault metrics transformed so that larger means more structural."""

    ratio_min = 1.0
    ratio_max = 10.526
    normalized = {}
    for fault, values in data.items():
        ratio_norm = (values["d2_ratio"] - ratio_min) / (ratio_max - ratio_min)
        normalized[fault] = {
            "d2_trigger": values["d2_trigger"],
            "switching_inv": 1.0 - values["switching"],
            "dominance": values["dominance"],
            "d2_ratio_norm": ratio_norm,
            "pair_concentration": values["pair_concentration"],
        }
    return normalized


def save_fault_embedding(output_path="fault_embedding.png"):
    """Save the requested 3-panel fault fingerprint visualization."""

    normalized = _normalized_metrics(fault_data)
    faults = list(fault_data.keys())
    metric_names = [
        "d2_trigger",
        "switching_inv",
        "dominance",
        "d2_ratio_norm",
        "pair_concentration",
    ]
    metric_labels = [
        "D2 trigger",
        "1 - switching",
        "dominance",
        "D2 ratio norm",
        "pair concentration",
    ]

    fig = plt.figure(figsize=(16, 6))

    ax_radar = fig.add_subplot(1, 3, 1, polar=True)
    angles = np.linspace(0, 2.0 * np.pi, len(metric_names), endpoint=False)
    angles_closed = np.r_[angles, angles[0]]
    colors = plt.cm.tab10(np.arange(len(faults)))
    for color, fault in zip(colors, faults):
        values = [normalized[fault][name] for name in metric_names]
        values_closed = np.r_[values, values[0]]
        ax_radar.plot(angles_closed, values_closed, linewidth=2.0, color=color, label=fault)
        ax_radar.fill(angles_closed, values_closed, alpha=0.08, color=color)
    ax_radar.set_xticks(angles)
    ax_radar.set_xticklabels(metric_labels)
    ax_radar.set_ylim(0.0, 1.05)
    ax_radar.set_title("Fault Fingerprint Radar")
    ax_radar.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15))

    ax_scatter = fig.add_subplot(1, 3, 2)
    x = np.array([fault_data[f]["switching"] for f in faults], dtype=float)
    y = np.array([fault_data[f]["dominance"] for f in faults], dtype=float)
    sizes = np.array([fault_data[f]["d2_trigger"] * 500.0 for f in faults], dtype=float)
    colors_scatter = np.array([fault_data[f]["d2_ratio"] for f in faults], dtype=float)
    scatter = ax_scatter.scatter(
        x,
        y,
        s=sizes,
        c=colors_scatter,
        cmap="viridis",
        alpha=0.85,
        edgecolors="black",
        linewidths=0.7,
    )
    for fault, x_val, y_val in zip(faults, x, y):
        ax_scatter.text(x_val + 0.004, y_val + 0.002, fault, fontsize=10)
    ax_scatter.set_xlabel("switching_mean")
    ax_scatter.set_ylabel("dominance_mean")
    ax_scatter.set_title("Switching vs Dominance")
    ax_scatter.grid(alpha=0.3)
    fig.colorbar(scatter, ax=ax_scatter, label="D2 ratio")

    ax_bar = fig.add_subplot(1, 3, 3)
    x_positions = np.arange(len(faults))
    width = 0.16
    for idx, (metric_name, metric_label) in enumerate(zip(metric_names, metric_labels)):
        values = [normalized[fault][metric_name] for fault in faults]
        ax_bar.bar(
            x_positions + (idx - 2) * width,
            values,
            width=width,
            label=metric_label,
            alpha=0.85,
        )
    ax_bar.set_xticks(x_positions)
    ax_bar.set_xticklabels(faults)
    ax_bar.set_ylim(0.0, 1.05)
    ax_bar.set_ylabel("normalized structural score")
    ax_bar.set_title("Grouped Metric Comparison")
    ax_bar.grid(axis="y", alpha=0.3)
    ax_bar.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    save_fault_embedding()
