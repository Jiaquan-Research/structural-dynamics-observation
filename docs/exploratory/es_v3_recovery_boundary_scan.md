# ES-v3.2d-lite Recovery Boundary Scan

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Attack:

contiguous maintenance disturbance

Recovery:

natural trace continuation

Detector:

ES-v2 hard lock

k=5

## Results

| mode | requested_block | relock_rate | median_relock_time_windows | median_relock_time_samples | mean_recovery_horizon | mean_horizon_margin | n_horizon_limited | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| block_15 | 15 | 0.820000 | 10.000000 | 100.000000 | 26.428571 | 2.642857 | 3 | ROBUST |
| block_20 | 20 | 0.780000 | 10.000000 | 100.000000 | 23.809524 | 2.380952 | 5 | ROBUST |
| block_30 | 30 | 0.680000 | 10.000000 | 100.000000 | 18.904762 | 1.890476 | 8 | DEGRADED |

## Horizon diagnostics

mean_recovery_horizon

mean_horizon_margin

horizon_limited count

## Key question

When does recovery fail?

Recovery failure

or

observation horizon limit?

## Comparison

ES-v3.2c

block_3

block_5

block_10

vs

extended attack

block_15

block_20

block_30

| mode | requested_block | relock_rate | median_relock_time_windows | median_relock_time_samples | status |
| --- | --- | --- | --- | --- | --- |
| block_3 | 3 | 0.840000 | 10.000000 | 100.000000 | ROBUST |
| block_5 | 5 | 0.840000 | 10.000000 | 100.000000 | ROBUST |
| block_10 | 10 | 0.840000 | 10.000000 | 100.000000 | ROBUST |

## Verdict

DEGRADED

## Restrictions

No soft lock

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only

## Interpretation Revision

Original observation:

block_30

relock_rate = 0.68

status = DEGRADED

Follow-up diagnostics showed:

this is NOT confirmed recovery failure.

---

### Horizon artifact group

Observed:

n_horizon_limited = 8

Recovery horizon:

min = 1 window

median = 5 windows

max = 9 windows

Reference relock time:

10 windows

Interpretation:

These runs ended before enough recovery horizon existed.

Therefore:

no relock was not observed,

but recovery failure was not demonstrated.

Classification:

horizon artifact

not recovery failure

---

### Eligibility artifact group

Observed:

n_no_replacement = 8

Runs:

8
17
20
31
33
37
45
46

Properties:

attack_end_window = NaN

recovery_horizon = NaN

Interpretation:

These runs never entered valid attack evaluation.

Classification:

eligibility artifact

not recovery failure

---

### Revised block_30 interpretation

Total runs:

50

Eligible runs:

42

Observable recovery runs:

34

Horizon-limited:

8

Eligible observable relock:

34 / 34

= 100%

Revised conclusion:

No recovery boundary observed

within current trace horizon.

block_30 degradation

is not confirmed.

---

### Updated ES-v3.2d-lite conclusion

block_15:

eligible relock observed

block_20:

eligible relock observed

block_30:

no confirmed recovery failure

Current limit:

trace horizon

Scope:

EL-1 exploratory only

No industrial claim

No early-warning claim

No taxonomy update
