# ES-v3.4c Early-break Precursor Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Question

Can early-break behavior be seen

in the first few windows after relock?

## Setup

H:

3

5

10

Outcome:

early_break = relock_to_drop_latency <= 10

Unit:

window count

No model training.

Fixed rules only.

Population B:

n = 6 runs

Maximum evaluated:

30 run-mode samples

Rule scores:

order-of-magnitude indicators only

F1 thresholds:

exploratory labels

NOT statistical validation

## Population comparison

A

vs

B

| H | metric | A_mean | B_mean | A_minus_B | early_break_mean | non_early_break_mean | early_minus_non |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | early_locked_fraction | 0.992284 | 0.944444 | 0.047840 | 0.956140 | 1.000000 | -0.043860 |
| 3 | early_mean_run_length | 10.889660 | 10.355556 | 0.534105 | 10.432018 | 11.000000 | -0.567982 |
| 3 | early_state_drop | 0.013889 | 0.100000 | -0.086111 | 0.078947 | 0.000000 | 0.078947 |
| 5 | early_locked_fraction | 0.986111 | 0.886667 | 0.099444 | 0.915789 | 1.000000 | -0.084211 |
| 5 | early_mean_run_length | 11.766204 | 10.546667 | 1.219537 | 10.761842 | 12.000000 | -1.238158 |
| 5 | early_state_drop | 0.027778 | 0.200000 | -0.172222 | 0.157895 | 0.000000 | 0.157895 |
| 10 | early_locked_fraction | 0.965741 | 0.700000 | 0.265741 | 0.784211 | 1.000000 | -0.215789 |
| 10 | early_mean_run_length | 13.679167 | 9.773333 | 3.905833 | 10.301316 | 14.500000 | -4.198684 |
| 10 | early_state_drop | 0.083333 | 0.700000 | -0.616667 | 0.513158 | 0.000000 | 0.513158 |

## Early-break comparison

early_break

vs

non_early_break

## Rule scores

fixed rules

precision

recall

F1

| H | rule | precision | recall | f1 | tp | fp | fn | tn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | early_below_persistent_H == True | 1.000000 | 0.513158 | 0.678261 | 39 | 0 | 37 | 170 |
| 10 | early_min_run_length_H < 10 | 1.000000 | 0.513158 | 0.678261 | 39 | 0 | 37 | 170 |
| 10 | early_state_drop_H == True | 1.000000 | 0.513158 | 0.678261 | 39 | 0 | 37 | 170 |
| 10 | early_locked_fraction_H < 0.8 | 1.000000 | 0.355263 | 0.524272 | 27 | 0 | 49 | 170 |
| 5 | early_state_drop_H == True | 1.000000 | 0.157895 | 0.272727 | 12 | 0 | 64 | 170 |
| 5 | early_below_persistent_H == True | 1.000000 | 0.157895 | 0.272727 | 12 | 0 | 64 | 170 |
| 5 | early_min_run_length_H < 10 | 1.000000 | 0.157895 | 0.272727 | 12 | 0 | 64 | 170 |
| 5 | early_locked_fraction_H < 0.8 | 1.000000 | 0.131579 | 0.232558 | 10 | 0 | 66 | 170 |

## Interpretation

If fixed rules work:

precursor exists

If not:

early-break may require longer horizon

or richer state features.

## Verdict

weak_precursor

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

No detector modification

EL-1 exploratory only

## Final Interpretation

Best precursor:

H = 10

Rule:

early_below_persistent_H == True

precision = 1.000

recall = 0.513

F1 = 0.678

Population comparison:

H=10

early_locked_fraction:

A = 0.966

B = 0.700

early_mean_run_length:

A = 13.679

B = 9.773

early_state_drop:

A = 0.083

B = 0.700

Interpretation:

Weak precursor observed.

Recovery degradation path:

relock

↓

run_length decay

↓

below persistent

↓

early break

↓

oscillation

↓

quality floor

Important:

Population B:

n = 6

Rule scores:

exploratory indicators only

Not statistical evidence.

No taxonomy promotion.
