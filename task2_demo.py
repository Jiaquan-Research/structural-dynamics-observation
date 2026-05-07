"""Demo script for the single-sensor detector."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from task1_data_generator import generate_data
from task2_single_sensor import run_single_sensor_detector, validate_condition_b


def _format_summary_row(condition, result):
    """Format one terminal summary row for detector outputs."""

    return (
        f"{condition:>3} | "
        f"{result['chi2_pvalue']:.6f} | "
        f"{str(result['chi2_significant']):>5} | "
        f"{result['max_consecutive_alarm_anomaly']:>3} | "
        f"{str(result['passes_single_sensor_silence_check']):>5}"
    )


def main():
    data_a, metadata_a = generate_data("A", T=400, seed=42)
    data_b, metadata_b = generate_data("B", T=400, rho=0.4, seed=42)

    result_a = run_single_sensor_detector(data_a, metadata_a)
    result_b = validate_condition_b(data_b, metadata_b)

    print()
    print("Condition comparison")
    print("cond | chi2_pvalue | sig?  | max_alarm_anom | silent")
    print(_format_summary_row("A", result_a))
    print(_format_summary_row("B", result_b))

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    for sensor_id in range(data_b.shape[1]):
        axes[0].plot(data_b[:, sensor_id], linewidth=1.0, label=f"sensor_{sensor_id + 1}")
    axes[0].axvline(metadata_b["anomaly_start"], color="black", linestyle="--", linewidth=1.0)
    axes[0].set_title("Condition B time series")
    axes[0].set_ylabel("error")
    axes[0].grid(alpha=0.3)
    axes[0].legend(loc="upper right", ncol=5, fontsize=8)

    axes[1].imshow(
        result_b["alarm_mask"].T.astype(int),
        aspect="auto",
        cmap=plt.cm.Reds,
        interpolation="nearest",
        vmin=0,
        vmax=1,
    )
    axes[1].axvline(metadata_b["anomaly_start"], color="black", linestyle="--", linewidth=1.0)
    axes[1].set_title("Condition B alarm heatmap")
    axes[1].set_xlabel("time step")
    axes[1].set_ylabel("sensor")
    axes[1].set_yticks(np.arange(data_b.shape[1]))
    axes[1].set_yticklabels([str(i + 1) for i in range(data_b.shape[1])])

    fig.tight_layout()
    fig.savefig("task2_demo.png", dpi=150)


if __name__ == "__main__":
    main()
