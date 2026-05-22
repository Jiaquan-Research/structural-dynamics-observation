# ES-v3.3a Recovery Quality Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Recovery region:

relock_window

↓

trace_end

No baseline normalization

No duration ratio

No horizon correction

Detector:

ES-v2 hard lock

## Metrics

post_relock_locked_fraction

secondary_lock_drop_rate

post_relock_max_duration

recovery_quality_score

## Results

| mode | n_relocked | mean_locked_fraction | mean_drop_rate | mean_post_duration | mean_quality_score | stable_fraction | fragile_fraction | collapse_fraction | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| block_3 | 42 | 0.845557 | 0.154443 | 16.928571 | 0.765055 | 0.666667 | 0.190476 | 0.142857 | ROBUST |
| block_5 | 42 | 0.847430 | 0.152570 | 16.047619 | 0.764229 | 0.666667 | 0.190476 | 0.142857 | ROBUST |
| block_10 | 42 | 0.834056 | 0.165944 | 13.714286 | 0.750047 | 0.642857 | 0.214286 | 0.142857 | ROBUST |

## Recovery classes

stable

fragile

collapse

## ES-v3.2c reference

| mode | relock_rate | median_relock_time_samples | status |
| --- | --- | --- | --- |
| block_3 | 0.840000 | 100.000000 | ROBUST |
| block_5 | 0.840000 | 100.000000 | ROBUST |
| block_10 | 0.840000 | 100.000000 | ROBUST |

## Key question

Does recovery preserve lock quality?

## Interpretation

Recovery existence

and

Recovery quality

are independent

## Verdict

ROBUST

## Restrictions

No soft lock

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only

## ES-v3.3a Follow-up Interpretation

ES-v3.3b and ES-v3.3c identified:

fixed collapse cluster:

15
22
23
24
30
48

Recovery quality:

collapse mean quality:

0.180

non-collapse mean quality:

0.856

Difference:

Recovery quality split observed.

Important:

Collapse group is not explained by:

late trigger

artifact overlap

horizon limitation

Observed mechanism:

weak_lock

+

recovery_fragile

Status:

EL-1 exploratory only.

No taxonomy promotion.
