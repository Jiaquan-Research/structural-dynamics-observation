# Experiment Registry

| Experiment | Purpose | Status | Main Conclusion | EL |
|---|---|---|---|---|
| top1_operating_curve_sweep | Evaluate top1_mass threshold/FP tradeoff. | confirmed | Threshold scaling does not remove the FP floor. | EL-3 |
| random_subset_robustness_audit | Test whether geometry structure survives variable subset perturbation. | confirmed | Global attractor narrative is not supported; subspace choice matters. | EL-3 |
| f01_amplitude_audit | Diagnose F01 weak top1_mass detection despite pair activation. | confirmed | F01 is weak/sub-threshold geometry activation near the class boundary. | EL-2 |
| ruptures_baseline_benchmark | Establish raw and rolling-correlation changepoint baselines. | frozen | ruptures_A captures raw shifts; ruptures_B does not explain geometry persistence. | EL-3 |
| full_fault_representation_audit | First 20-run occupancy/entropy audit across F01-F20. | confirmed | Initial locked/stable/transitional/diffuse structure appears. | EL-2 |
| representation_audit_500runs | Validate representation classes on 500 runs per fault. | frozen | 19/20 classes stable; F01 shifts to Diffuse. | EL-3 |
| detector_disagreement_heatmap | Visualize detector disagreement across faults. | confirmed | Detector disagreement is systematic and structurally informative. | EL-3 |
| fault_archetype_profiles | Visual compare F02/F06/F14 archetype triangle. | exploratory | F14 shows locked representation without ruptures_A changepoint under current detector. | EL-2 |
| f14_deep_dive | Compare rolling statistics and pair persistence for F02/F06/F14. | confirmed | Pair persistence separates locked vs diffuse behavior; rolling std alone does not explain F14/F06. | EL-3 |
