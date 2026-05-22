# ES-v3.4a Recovery Stress Separation

Status: EL-1 exploratory
Date: 2026-05-23

## Populations

A:

44 runs

stable recovery

B:

6 runs

collapse cluster

Population B:

small sample

n = 6

Indicators only

Not statistically validated

## Stress levels

block_3

block_5

block_10

block_15

block_20

## Results

| population | attack_mode | mean_quality | mean_locked_fraction | mean_drop_rate | stable_fraction | fragile_fraction | collapse_fraction | mean_relock | delta_quality | delta_relock | labels |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | block_3 | 0.887438 | 0.933323 | 0.066677 | 0.818182 | 0.181818 | 0.000000 | 1.000000 | 0.706593 | 0.000000 | persistent_separation |
| B | block_3 | 0.180844 | 0.407862 | 0.592138 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.706593 | 0.000000 | persistent_separation |
| A | block_5 | 0.884287 | 0.931030 | 0.068970 | 0.818182 | 0.181818 | 0.000000 | 1.000000 | 0.686123 | 0.000000 | persistent_separation |
| B | block_5 | 0.198164 | 0.437794 | 0.562206 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.686123 | 0.000000 | persistent_separation |
| A | block_10 | 0.875854 | 0.924733 | 0.075267 | 0.795455 | 0.204545 | 0.000000 | 1.000000 | 0.715119 | 0.000000 | persistent_separation |
| B | block_10 | 0.160735 | 0.390344 | 0.609656 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.715119 | 0.000000 | persistent_separation |
| A | block_15 | 0.842845 | 0.893898 | 0.106102 | 0.772727 | 0.159091 | 0.068182 | 0.977273 | 0.714441 | -0.022727 | persistent_separation |
| B | block_15 | 0.128404 | 0.344413 | 0.655587 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.714441 | -0.022727 | persistent_separation |
| A | block_20 | 0.800152 | 0.847652 | 0.152348 | 0.727273 | 0.090909 | 0.181818 | 0.931818 | 0.707854 | -0.068182 | persistent_separation |
| B | block_20 | 0.092298 | 0.281648 | 0.718352 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.707854 | -0.068182 | persistent_separation |

## Interpretation

Population B:

small sample

n = 6

Indicators only

Not statistically validated

Expected pattern:

B may remain near recovery floor

A may degrade gradually

## Labels

persistent_separation

weak_separation

merged

A_degradation

B_floor_effect

## Key question

Stress response split?

## Optional references

es_v3_recovery_quality_summary.csv loaded
es_v3_recovery_boundary_summary.csv loaded

## Final verdict

B_floor_effect;persistent_separation

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

No frozen modification

EL-1 exploratory only

## ES-v3.4b + ES-v3.4c Integration

Population A:

high recovery quality

slow degradation

stable persistence

Population B:

low recovery quality

floor effect

early break

oscillatory persistence

Observed pattern:

persistent separation

+

B floor effect

+

weak precursor

Current scope:

EL-1 exploratory only.

No archetype promotion.
