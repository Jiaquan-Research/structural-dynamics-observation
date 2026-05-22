# ES-v3.1a Formation Boundary Scan
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Mode: exhaustion (remove all TARGET windows in attack region)
Attack sizes: 10, 20, 30, 40, 50, all_pre_trigger
Detector: ES-v2 hard lock k=5, unchanged.
no_target runs: replay original trace (not counted as miss)

## Baseline
| trigger_rate | median_delay | NORMAL_FPR |
| --- | --- | --- |
| 1.000000 | 110.000000 | 0.000000 |

## Results
| attack_size | mean_n_target | mean_effective_replace | n_no_target | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 3.620000 | 3.620000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| 20 | 3.740000 | 3.740000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| 30 | 3.740000 | 3.740000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| 40 | 3.740000 | 3.740000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| 50 | 3.740000 | 3.740000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| all_pre_trigger | 3.740000 | 3.740000 | 8 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |

## Robustness curve
| attack_size | trigger_rate | delay_shift | status |
| --- | --- | --- | --- |
| 10 | 0.840000 | 55.000000 | ROBUST |
| 20 | 0.840000 | 55.000000 | ROBUST |
| 30 | 0.840000 | 55.000000 | ROBUST |
| 40 | 0.840000 | 55.000000 | ROBUST |
| 50 | 0.840000 | 55.000000 | ROBUST |
| all_pre_trigger | 0.840000 | 55.000000 | ROBUST |

## Phase transition
No phase transition observed within tested range

## Interpretation
Formation robustness only.
Post-trigger maintenance not tested (ES-v3.1b scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.
