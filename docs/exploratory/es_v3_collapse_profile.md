# ES-v3.3c Collapse Run Profile

Status: EL-1 exploratory
Date: 2026-05-23

## Collapse cluster

15
22
23
24
30
48

## Baseline comparison

| metric | group | mean | median | p25 | p75 |
| --- | --- | --- | --- | --- | --- |
| baseline_locked_fraction | non-collapse | 0.759091 | 0.793333 | 0.686667 | 0.856667 |
| baseline_locked_fraction | collapse | 0.528889 | 0.540000 | 0.463333 | 0.626667 |
| baseline_max_duration | non-collapse | 53.045455 | 59.500000 | 40.500000 | 64.250000 |
| baseline_max_duration | collapse | 34.833333 | 33.500000 | 30.750000 | 43.000000 |
| n_locked_segments | non-collapse | 1.318182 | 1.000000 | 1.000000 | 2.000000 |
| n_locked_segments | collapse | 2.166667 | 2.000000 | 2.000000 | 2.750000 |
| mean_locked_duration | non-collapse | 49.375000 | 59.500000 | 26.750000 | 64.250000 |
| mean_locked_duration | collapse | 21.861111 | 17.750000 | 15.250000 | 22.625000 |
| target_pair_frequency | non-collapse | 0.928788 | 0.940000 | 0.890000 | 0.976667 |
| target_pair_frequency | collapse | 0.824444 | 0.826667 | 0.756667 | 0.876667 |

## Trigger comparison

| metric | group | mean | median | p25 | p75 |
| --- | --- | --- | --- | --- | --- |
| trigger_window | non-collapse | 19.090909 | 17.500000 | 15.000000 | 22.000000 |
| trigger_window | collapse | 16.666667 | 15.000000 | 15.000000 | 17.250000 |
| trigger_delay | non-collapse | 130.909091 | 115.000000 | 90.000000 | 160.000000 |
| trigger_delay | collapse | 106.666667 | 90.000000 | 90.000000 | 112.500000 |

## Recovery comparison

| metric | group | mean | median | p25 | p75 |
| --- | --- | --- | --- | --- | --- |
| quality_score | non-collapse | 0.856421 | 1.000000 | 0.755276 | 1.000000 |
| quality_score | collapse | 0.179914 | 0.179745 | 0.156058 | 0.230758 |
| drop_rate | non-collapse | 0.085928 | 0.000000 | 0.000000 | 0.131114 |
| drop_rate | collapse | 0.588000 | 0.584259 | 0.520936 | 0.614695 |
| mean_post_duration | non-collapse | 16.518519 | 17.666667 | 12.333333 | 21.416667 |
| mean_post_duration | collapse | 9.833333 | 8.500000 | 7.416667 | 12.333333 |

## Labels

| label | count |
| --- | --- |
| fragmented | 2 |
| recovery_fragile | 6 |
| weak_lock | 6 |

weak_lock

late_trigger

fragmented

recovery_fragile

Note:

Threshold labels are exploratory only.

Derived from non-collapse quantiles.

Not statistically validated.

## Key question

Why do collapse runs collapse?

## Verdict

population split

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

EL-1 exploratory only

## ES-v3 Final Interpretation

Population A

n = 44

baseline lock high

stable recovery

quality mean ~=0.856

Population B

n = 6

baseline lock low

fragile recovery

quality mean ~=0.180

Mechanism:

weak_lock

+

recovery_fragile

Rejected explanations:

late trigger

artifact overlap

horizon artifact

Boundary:

not observed

within current trace horizon

Status:

EL-1 exploratory

No taxonomy update

No industrial claim

No early-warning claim
