# ES-v3.0b++ Adaptive Local Exhaustion
Status: EL-1 exploratory
Date: 2026-05-22

## Setup
Attack region: [trigger_window-10, trigger_window-1]
Modes: baseline, noise_1-4, exhaustion
no_target runs: replay original trace unchanged (not counted as miss)
Detector: ES-v2 hard lock k=5, unchanged.

## Baseline
| mode | requested_replace | mean_effective_replace | mean_exhausted_fraction | n_no_target | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0 | 0.000000 | 0.000000 | 0 | 1.000000 | 110.000000 | 0.000000 | 0.000000 | 0.000000 | 0.633333 | ROBUST |

## Results
| mode | requested_replace | mean_effective_replace | mean_exhausted_fraction | n_no_target | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0 | 0.000000 | 0.000000 | 0 | 1.000000 | 110.000000 | 0.000000 | 0.000000 | 0.000000 | 0.633333 | ROBUST |
| noise_1 | 1 | 0.840000 | 0.199167 | 0 | 0.840000 | 150.000000 | 40.000000 | 0.160000 | 0.000000 | 0.420000 | ROBUST |
| noise_2 | 2 | 1.680000 | 0.398333 | 0 | 0.840000 | 160.000000 | 50.000000 | 0.160000 | 0.000000 | 0.392000 | ROBUST |
| noise_3 | 3 | 2.520000 | 0.597500 | 0 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| noise_4 | 4 | 3.360000 | 0.796667 | 0 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |
| exhaustion | -1 | 3.620000 | 0.840000 | 0 | 0.840000 | 165.000000 | 55.000000 | 0.160000 | 0.000000 | 0.378000 | ROBUST |

## Robustness curve
exhausted_fraction vs trigger_rate and delay_shift

| mode | mean_exhausted_fraction | trigger_rate | delay_shift | status |
| --- | --- | --- | --- | --- |
| baseline | 0.000000 | 1.000000 | 0.000000 | ROBUST |
| noise_1 | 0.199167 | 0.840000 | 40.000000 | ROBUST |
| noise_2 | 0.398333 | 0.840000 | 50.000000 | ROBUST |
| noise_3 | 0.597500 | 0.840000 | 55.000000 | ROBUST |
| noise_4 | 0.796667 | 0.840000 | 55.000000 | ROBUST |
| exhaustion | 0.840000 | 0.840000 | 55.000000 | ROBUST |

## Verdict
ES-v2 hard lock: saturated local robustness CONFIRMED

## Interpretation
exhaustion mode = complete removal of TARGET_PAIR windows
in immediate pre-trigger region.
Result does NOT test post-trigger lock maintenance (ES-v3.1 scope).

## Restrictions
No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.

---

## ES-v3.0b++ Final Interpretation

Adaptive exhaustion:

effective_replace

=

min(
requested_replace,
n_target
)

Exhaustion mode:

effective_replace

=

n_target

Result:

baseline:

TPR = 1.00

median_delay = 110

exhaustion:

TPR = 0.84

median_delay = 165

delay_shift = +55

miss_rate = 0.16

NORMAL_FPR = 0

Interpretation:

Complete removal of TARGET windows
inside local pre-trigger attack region

does NOT fully destroy persistence trigger.

Observed survival:

84%

Observed failure:

16%

Conclusion:

Persistence trigger shows:

strong local robustness

with observed boundary

This is NOT:

infinite robustness

or

unbounded robustness

Scope:

local pre-trigger exhaustion only

Post-trigger lock maintenance:

not tested

ES-v3.1 scope

---

## ES-v3.0b Series Summary

single_break:

TPR = 1.00

ROBUST

double_break:

TPR = 1.00

ROBUST

adaptive_exhaustion:

TPR = 0.84

ROBUST

Boundary observed:

16% miss

Current status:

ES-v3.0b complete

ES-v3.1 pending
