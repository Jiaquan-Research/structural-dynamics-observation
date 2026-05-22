# ES-v3.0b Synthetic Disturbance Replay
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Attack region: [trigger_window-10, trigger_window-1]
Only pre-trigger persistence formation is attacked.
Detector logic: unchanged (k=5 hard lock).

## Baseline
| mode | strength | n_eligible | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | none | 50 | 1.000000 | 110.000000 | 0.000000 | 0.000000 | 0.000000 | 0.633333 | ROBUST |

## Mode A: Single break
| mode | strength | n_eligible | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| single_break | 1 | 42 | 1.000000 | 150.000000 | 40.000000 | 0.000000 | 0.000000 | 0.500000 | ROBUST |

## Mode B: Double break
| mode | strength | n_eligible | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| double_break | 2 | 42 | 1.000000 | 165.000000 | 55.000000 | 0.000000 | 0.000000 | 0.450000 | ROBUST |

## Mode C: Noise (5%, 10%, 20%)
| mode | strength | n_eligible | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noise_replay | 10% | 42 | 1.000000 | 150.000000 | 40.000000 | 0.000000 | 0.000000 | 0.500000 | ROBUST |
| noise_replay | 20% | 42 | 1.000000 | 150.000000 | 40.000000 | 0.000000 | 0.000000 | 0.500000 | ROBUST |
| noise_replay | 5% | 42 | 1.000000 | 150.000000 | 40.000000 | 0.000000 | 0.000000 | 0.500000 | ROBUST |

## Robustness boundary
| mode | strength | status |
| --- | --- | --- |
| baseline | none | ROBUST |
| double_break | 2 | ROBUST |
| noise_replay | 10% | ROBUST |
| noise_replay | 20% | ROBUST |
| noise_replay | 5% | ROBUST |
| single_break | 1 | ROBUST |

## Interpretation
Pre-trigger formation robustness only.
Post-trigger lock maintenance not tested (ES-v3.1 scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.

---

## ES-v3.0b Final Result

Baseline:

trigger_rate:

1.000

median_delay:

110

NORMAL_FPR:

0

Single break:

trigger_rate:

1.000

delay_shift:

+40

status:

ROBUST

Double break:

trigger_rate:

1.000

delay_shift:

+55

status:

ROBUST

Interpretation:

Local pre-trigger disturbance does not destroy persistence trigger.

Observed effect:

delay increase

No miss observed.

---

## Noise Replay Note

Original noise replay:

5%

10%

20%

did not create effective strength separation.

Reason:

Most runs contained only about 4 TARGET windows
inside attack region.

Multiple noise levels frequently reduced to the same
effective replacement count.

Noise replay results should NOT be treated as
independent evidence.

This motivated:

ES-v3.0b++

Adaptive Local Exhaustion
