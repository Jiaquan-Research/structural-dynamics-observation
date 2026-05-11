"""Demo script for task1_data_generator."""

from __future__ import annotations

import matplotlib.pyplot as plt

from task1_data_generator import generate_data


def main():
    configs = [("A", 400), ("B", 400)]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    for ax, (condition, T) in zip(axes, configs):
        data, metadata = generate_data(condition, T=T, seed=42)
        print(f"Condition {condition}")
        print(metadata)
        print(
            "chi2 p-values:",
            {
                "proposal": metadata["chi2_pvalue_proposal"],
                "actual": metadata["chi2_pvalue_actual"],
            },
        )
        if abs(metadata["chi2_pvalue_proposal"] - metadata["chi2_pvalue_actual"]) > 0.1:
            print(
                "WARNING: proposal vs actual p-value difference > 0.1, "
                "check rejection sampling distribution"
            )

        for sensor_id in range(data.shape[1]):
            ax.plot(data[:, sensor_id], linewidth=1.0, label=f"sensor_{sensor_id + 1}")

        ax.axvline(metadata["anomaly_start"], color="black", linestyle="--", linewidth=1.0)
        ax.set_title(f"Condition {condition}")
        ax.set_ylabel("error")
        ax.grid(alpha=0.3)

    axes[0].legend(loc="upper right", ncol=5, fontsize=8)
    axes[-1].set_xlabel("time step")
    fig.tight_layout()
    fig.savefig("task1_demo.png", dpi=150)


if __name__ == "__main__":
    main()
