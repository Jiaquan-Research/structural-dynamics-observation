"""Demo script for the TEP industrial-data validation experiment."""

from __future__ import annotations

from tep_validation_experiment import run_tep_validation, save_tep_validation_figures


def main():
    results = run_tep_validation()
    if results is None:
        return

    save_tep_validation_figures(results)

    print("TEP validation summary")
    print(f"fault_number={results['fault_number']}, fault_run={results['fault_run']}")
    print(
        "variables="
        + ", ".join(item["column"] for item in results["selected_variables"])
    )
    for version_name, version in results["versions"].items():
        print(version_name)
        print(
            f"  AUC={version['auc_pre_vs_post']:.3f}, "
            f"theta={version['theta']:.3f}, "
            f"delay={version['detection_delay_samples']}"
        )
        print(
            f"  n_eff_baseline={version['n_eff_baseline']}, "
            f"n_eff_pre={version['n_eff_pre_fault']}, "
            f"n_eff_post={version['n_eff_post_fault']}"
        )
        print(
            f"  dominant_pair={version['pair_summary']['dominant_pair_over_history']}"
        )


if __name__ == "__main__":
    main()
