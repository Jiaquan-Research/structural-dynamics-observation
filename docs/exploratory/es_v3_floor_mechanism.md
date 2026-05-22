# ES-v3.4b Floor Mechanism Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Question

Why does Population B relock

but remain near quality floor?

## Metrics

relock_to_drop_latency

drop_position_fraction

post_relock_max_duration

secondary_drop_rate

## Population comparison

| population | relock_to_drop_latency | drop_position_fraction | post_relock_max_duration | secondary_drop_rate |
| --- | --- | --- | --- | --- |
| A | 15.393519 | 0.884404 | 15.681818 | 0.010118 |
| B | 7.800000 | 0.290785 | 8.133333 | 0.043593 |

A

vs

B

## Labels

| label | count |
| --- | --- |
| early_break | 29 |
| none | 4 |
| oscillatory | 84 |
| persistent_floor | 17 |
| stable_floor | 179 |

stable_floor

early_break

oscillatory

persistent_floor

## Interpretation

Recovery existence

and

Recovery persistence

are separate properties

Population B:

small sample

n = 6

Indicators only

## Summary

| metric | A_mean | B_mean | delta |
| --- | --- | --- | --- |
| latency | 15.393519 | 7.800000 | 7.593519 |
| drop_position | 0.884404 | 0.290785 | 0.593619 |
| post_duration | 15.681818 | 8.133333 | 7.548485 |
| drop_count | 0.250000 | 1.166667 | -0.916667 |
| drop_rate | 0.010118 | 0.043593 | -0.033474 |

## Verdict

B_drops_earlier;B_drops_more;B_shorter_persistence

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

EL-1 exploratory only

## ES-v3.4c Follow-up

ES-v3.4b identified:

Population A

latency ~=15.39

drop_rate ~=0.010

post_duration ~=15.68

Population B

latency ~=7.80

drop_rate ~=0.044

post_duration ~=8.13

Interpretation:

Population B:

relock exists

but:

drops earlier

drops more often

shorter persistence

Mechanism path:

weak_lock

↓

early_break

↓

oscillation

↓

persistent floor

Status:

EL-1 exploratory only.

No taxonomy update.
