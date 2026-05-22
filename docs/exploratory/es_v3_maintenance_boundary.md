# ES-v3.1b Maintenance Boundary Scan

Status: EL-1 exploratory
Date: 2026-05-22

## Setup

Attack region: post-trigger only [trigger_window+1, end]
Pre-trigger region: unchanged
Modes: 10%, 20%, 30%, 50%, 70%, maintenance_exhaustion
Detector: ES-v2 hard lock k=5, unchanged.

## Baseline

| baseline_trigger_rate | baseline_median_delay | baseline_mean_locked_fraction | baseline_mean_max_locked_duration | NORMAL_FPR |
| --- | --- | --- | --- | --- |
| 1.000000 | 110.000000 | 0.731467 | 50.860000 | 0.000000 |

## Results

| mode | n_no_post_target | trigger_rate | median_delay | mean_locked_fraction | mean_max_locked_duration | mean_n_locked_segments | locked_fraction_shift | duration_shift | mean_maintenance_damage | maintenance_survival_rate | NORMAL_FPR | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noise_10pct | 0 | 1.000000 | 110.000000 | 0.332800 | 19.940000 | 2.300000 | -0.398667 | -30.920000 | 0.567013 | 0.240000 | 0.000000 | COLLAPSED |
| noise_20pct | 0 | 1.000000 | 110.000000 | 0.198133 | 14.040000 | 1.340000 | -0.533333 | -36.820000 | 0.758885 | 0.160000 | 0.000000 | COLLAPSED |
| noise_30pct | 0 | 1.000000 | 110.000000 | 0.153067 | 11.400000 | 0.540000 | -0.578400 | -39.460000 | 0.822624 | 0.160000 | 0.000000 | COLLAPSED |
| noise_50pct | 0 | 1.000000 | 110.000000 | 0.141067 | 10.580000 | 0.180000 | -0.590400 | -40.280000 | 0.839692 | 0.160000 | 0.000000 | COLLAPSED |
| noise_70pct | 0 | 1.000000 | 110.000000 | 0.140800 | 10.560000 | 0.160000 | -0.590667 | -40.300000 | 0.840000 | 0.160000 | 0.000000 | COLLAPSED |
| maintenance_exhaustion | 0 | 1.000000 | 110.000000 | 0.140800 | 10.560000 | 0.160000 | -0.590667 | -40.300000 | 0.840000 | 0.160000 | 0.000000 | COLLAPSED |

## Maintenance curve

| mode | mean_locked_fraction | mean_maintenance_damage | maintenance_survival_rate | status |
| --- | --- | --- | --- | --- |
| noise_10pct | 0.332800 | 0.567013 | 0.240000 | COLLAPSED |
| noise_20pct | 0.198133 | 0.758885 | 0.160000 | COLLAPSED |
| noise_30pct | 0.153067 | 0.822624 | 0.160000 | COLLAPSED |
| noise_50pct | 0.141067 | 0.839692 | 0.160000 | COLLAPSED |
| noise_70pct | 0.140800 | 0.840000 | 0.160000 | COLLAPSED |
| maintenance_exhaustion | 0.140800 | 0.840000 | 0.160000 | COLLAPSED |

## Phase transition

Maintenance phase transition at: noise_10pct

## Interpretation

Formation robustness (ES-v3.1a): not the bottleneck.
F13 signal is globally strong; pre-trigger exhaustion cannot prevent trigger.
Maintenance robustness: this experiment tests post-trigger lock survival.

## Restrictions

No soft lock. No industrial claim.
No early-warning claim. No taxonomy update.
No frozen modification. EL-1 exploratory only.

## ES-v3.1c Contiguous Maintenance Follow-up

Reference results:

Sparse random attack:

noise_10pct
trigger_rate = 1.00
mean_locked_fraction = 0.333
maintenance_survival_rate = 0.24
status = COLLAPSED

Contiguous attack:

block_10
trigger_rate = 0.84
mean_locked_fraction = 0.519
maintenance_survival_rate = 0.78
status = ROBUST

Maintenance exhaustion:

trigger_rate = 0.84
mean_locked_fraction = 0.141
maintenance_survival_rate = 0.00
status = COLLAPSED

Interpretation:

Maintenance degradation depends strongly on attack structure.

Random sparse replacement causes severe collapse.

Contiguous short disturbance remains mostly survivable.

Current EL-1 conclusion:

maintenance = fragment-sensitive

NOT:

maintenance = uniformly fragile

Scope:

No physical claim.
No industrial transfer.
No early-warning claim.
