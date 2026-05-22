# ES-v3.2c Recovery / Relock Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Setup

Attack:

temporary contiguous maintenance disturbance

Recovery:

natural trace continuation

No synthetic recovery

Detector:

ES-v2 hard lock

k=5

## Results

| mode | requested_block | relock_rate | median_relock_time_windows | median_relock_time_samples | mean_recovered_lock | mean_residual_damage | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| block_3 | 3 | 0.840000 | 10.000000 | 100.000000 | 14.220000 | 0.707887 | ROBUST |
| block_5 | 5 | 0.840000 | 10.000000 | 100.000000 | 13.480000 | 0.724151 | ROBUST |
| block_10 | 10 | 0.840000 | 10.000000 | 100.000000 | 11.520000 | 0.767514 | ROBUST |

## Recovery metrics

relock_rate

relock_time

residual_damage

## Comparison

ES-v3.1c maintenance

vs

ES-v3.2c recovery

| mode | mean_locked_fraction | mean_max_locked_duration | maintenance_survival_rate | status |
| --- | --- | --- | --- | --- |
| block_3 | 0.597067 | 28.160000 | 0.840000 | ROBUST |
| block_5 | 0.574667 | 27.500000 | 0.820000 | ROBUST |
| block_10 | 0.519467 | 25.920000 | 0.780000 | ROBUST |

## Key question

Can lock state recover

after disturbance ends?

## Verdict

Recovery:

fast

## Restrictions

No soft lock

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only

## ES-v3.2c Interpretation Revision

Original observation:

relock_rate = 0.84
mean_residual_damage ~= 0.70

Follow-up diagnostics showed both are artifacts.

### Eligibility artifact

Observed:

no_relock runs = 8

These runs have:

baseline_locked_fraction = 0.88
baseline_duration = 66
attack_end_window = NaN

Interpretation:

These runs did not enter valid attack/recovery evaluation.

Therefore:

observed relock_rate

42 / 50

is not recovery failure.

Eligible recovery:

42 / 42

= 1.00

Revised conclusion:

eligible relock rate = 100%

---

### Horizon artifact

Observed:

remaining_windows after attack:

mean ~= 32

baseline duration:

~= 66

Therefore:

max_recovered_lock is constrained by short recovery horizon.

Residual damage based on:

max_recovered_lock / baseline_duration

cannot be interpreted as true recovery loss.

Revised interpretation:

mean_residual_damage

exploratory only

not used for conclusion.

---

### Updated ES-v3.2c conclusion

Recovery:

eligible relock rate = 100%

median relock time = 100 samples

Observed no_relock:

eligibility artifact

Residual damage:

horizon artifact

Recovery quality:

not resolved

Scope:

EL-1 exploratory only

No industrial claim

No early-warning claim

No taxonomy update

## Boundary Follow-up

ES-v3.2d-lite extended attack range:

block_15

block_20

block_30

Result:

No confirmed recovery boundary observed.

Observed no_relock:

split into:

horizon artifact

eligibility artifact

Recovery capability remains unresolved

beyond current trace horizon.
