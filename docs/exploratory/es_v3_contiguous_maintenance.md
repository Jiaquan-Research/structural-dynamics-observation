# ES-v3.1c Contiguous Maintenance Attack

Status: EL-1 exploratory
Date: 2026-05-22

## Setup

Attack: post-trigger only
Detector: ES-v2 hard lock k=5
Attack type: contiguous block removal
NOT random sparse deletion

## Results

| mode | requested_block | mean_actual_block | mean_block_fraction | trigger_rate | median_delay | mean_locked_fraction | mean_max_locked_duration | maintenance_survival_rate | maintenance_damage | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| block_1 | 1 | 0.840000 | 0.016940 | 0.840000 | 125.000000 | 0.619467 | 28.820000 | 0.840000 | 0.153117 | ROBUST |
| block_2 | 2 | 1.680000 | 0.033879 | 0.840000 | 125.000000 | 0.608267 | 28.540000 | 0.840000 | 0.168429 | ROBUST |
| block_3 | 3 | 2.520000 | 0.050819 | 0.840000 | 125.000000 | 0.597067 | 28.160000 | 0.840000 | 0.183740 | ROBUST |
| block_5 | 5 | 4.200000 | 0.084698 | 0.840000 | 125.000000 | 0.574667 | 27.500000 | 0.820000 | 0.214364 | ROBUST |
| block_10 | 10 | 8.400000 | 0.169397 | 0.840000 | 125.000000 | 0.519467 | 25.920000 | 0.780000 | 0.289829 | ROBUST |
| maintenance_exhaustion | -1 | 52.140000 | 0.840000 | 0.840000 | 125.000000 | 0.140800 | 10.560000 | 0.000000 | 0.807510 | COLLAPSED |

## Comparison

Sparse random attack vs contiguous attack

| source | mode | mean_locked_fraction | mean_max_locked_duration | maintenance_survival_rate | status |
| --- | --- | --- | --- | --- | --- |
| sparse_random | noise_10pct | 0.332800 | 19.940000 | 0.240000 | COLLAPSED |
| sparse_random | noise_20pct | 0.198133 | 14.040000 | 0.160000 | COLLAPSED |
| sparse_random | noise_30pct | 0.153067 | 11.400000 | 0.160000 | COLLAPSED |
| sparse_random | noise_50pct | 0.141067 | 10.580000 | 0.160000 | COLLAPSED |
| sparse_random | noise_70pct | 0.140800 | 10.560000 | 0.160000 | COLLAPSED |
| sparse_random | maintenance_exhaustion | 0.140800 | 10.560000 | 0.160000 | COLLAPSED |
| contiguous | block_1 | 0.619467 | 28.820000 | 0.840000 | ROBUST |
| contiguous | block_2 | 0.608267 | 28.540000 | 0.840000 | ROBUST |
| contiguous | block_3 | 0.597067 | 28.160000 | 0.840000 | ROBUST |
| contiguous | block_5 | 0.574667 | 27.500000 | 0.820000 | ROBUST |
| contiguous | block_10 | 0.519467 | 25.920000 | 0.780000 | ROBUST |
| contiguous | maintenance_exhaustion | 0.140800 | 10.560000 | 0.000000 | COLLAPSED |

## Key question

Does maintenance fail because of:

- fragmentation
- temporary contiguous disturbance
- mixed effects?

## Verdict

maintenance: fragment-sensitive

## Restrictions

No soft lock
No industrial claim
No early-warning claim
No taxonomy update
No frozen modification
EL-1 exploratory only

## ES-v3.1 Summary

Formation:

local exhaustion
TPR floor ~= 0.84
No attack-size dependence observed.

Maintenance (sparse):

noise_10pct
survival = 0.24
COLLAPSED

Maintenance (contiguous):

block_10
survival = 0.78
ROBUST

Maintenance (full exhaustion):

survival = 0.00
COLLAPSED

Working interpretation:

Formation robustness:
strong

Maintenance robustness:
fragment-sensitive

Open question:

ES-v3.2 mixed disturbance
(block + sparse)

Not started.

## Recovery Follow-up

ES-v3.2c indicates:

temporary contiguous maintenance disturbance

↓

eligible relock

100%

Recovery exists.

Recovery speed:

median 100 samples

Current interpretation:

maintenance

fragment-sensitive

contiguous disturbance tolerant

natural recovery observed

Recovery quality unresolved.
