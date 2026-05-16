# Representation Stability v1 Manifest

| Asset | Type | Meaning |
|---|---|---|
| report.md | Document | Frozen v1 narrative report and summary boundary |
| reproducibility.md | Document | Runtime, dataset, parameter, and output reproducibility guide |
| open_questions.md | Document | Unresolved questions preserved for future work |
| evidence_levels.md | Document | Evidence level definitions and current claim mapping |
| failed_hypotheses.md | Document | Failed and downgraded hypothesis archive |
| experiment_registry.md | Document | Registered experiments, status, conclusions, and EL labels |
| decision_log.md | Document | Research decisions that define the frozen interpretation |
| taxonomy_rules.md | Document | Frozen occupancy/entropy taxonomy rules |
| research_positioning.md | Document | Scope and positioning of the project |
| requirements_rs_v1.txt | Environment | Python package freeze from .venv312 |
| csv/representation_audit_500runs_summary.csv | CSV | 500-run occupancy/entropy summary statistics |
| csv/representation_audit_500runs_perrun.csv | CSV | Per-run raw representation stability metrics for 20 faults x 500 runs |
| csv/full_fault_representation_audit.csv | CSV | 20-run representation audit summary |
| csv/fault_detector_response_matrix.csv | CSV | Per-fault five-detector response matrix and descriptive fault pattern |
| csv/detector_comparison_summary_v2.csv | CSV | Five-detector operating point comparison summary |
| csv/ruptures_baseline_overall_summary.csv | CSV | Ruptures overall operating point summary |
| csv/ruptures_baseline_fault_summary.csv | CSV | Ruptures per-fault benchmark summary |
| csv/ruptures_penalty_table.csv | CSV | Ruptures penalty calibration table |
| csv/top1_mass_fault_summary.csv | CSV | top1_mass per-fault benchmark summary |
| csv/top1_mass_overall_summary.csv | CSV | top1_mass overall benchmark summary |
| csv/pca_baseline_fault_summary.csv | CSV | PCA T2/SPE per-fault benchmark summary |
| csv/pca_baseline_overall_summary.csv | CSV | PCA T2/SPE overall benchmark summary |
| csv/f01_amplitude_audit.csv | CSV | F01 sub-threshold activation amplitude audit |
| csv/f14_pair_persistence_metrics.csv | CSV | F02/F06/F14 pair persistence metrics for selected p95 runs |
| figures/representation_500runs_scatter.png | Figure | 500-run occupancy vs entropy scatter with class boundaries |
| figures/representation_occupancy_distribution.png | Figure | Per-fault occupancy distribution across 500 runs |
| figures/representation_occupancy_consistency.png | Figure | Occupancy vs dominant pair consistency scatter |
| figures/representation_20vs500_comparison.png | Figure | 20-run vs 500-run representation stability comparison |
| figures/representation_class_distribution.png | Figure | Representation class count summary |
| figures/f13_occupancy_histogram.png | Figure | F13 occupancy distribution and bimodality check |
| figures/archetype_triangle_comparison.png | Figure | F02/F06/F14 top1_mass vs ruptures_A contrast |
| figures/detector_disagreement_heatmap.png | Figure | Fault x detector detection-rate heatmap |
| figures/detector_pairwise_disagreement.png | Figure | Pairwise detector disagreement matrix |
| figures/per_fault_max_disagreement.png | Figure | Per-fault maximum detector disagreement |
| figures/f01_amplitude_distribution.png | Figure | F01/F06/NORMAL top1_mass amplitude distribution |
| figures/f14_rolling_std_comparison.png | Figure | F02/F06/F14 XMEAS7 rolling std comparison |
| figures/f14_pair_persistence_comparison.png | Figure | Pair persistence metrics comparison for archetype faults |
| figures/f14_rolling_stats_F02.png | Figure | F02 rolling statistics deep-dive panel |
| figures/f14_rolling_stats_F06.png | Figure | F06 rolling statistics deep-dive panel |
| figures/f14_rolling_stats_F14.png | Figure | F14 rolling statistics deep-dive panel |
| figures/archetype_profile_F02.png | Figure | F02 five-panel archetype profile |
| figures/archetype_profile_F06.png | Figure | F06 five-panel archetype profile |
| figures/archetype_profile_F14.png | Figure | F14 five-panel archetype profile |
| figures/ruptures_detection_rate.png | Figure | Ruptures detection-rate benchmark plot |
| figures/ruptures_operating_points.png | Figure | Ruptures operating-point comparison plot |
