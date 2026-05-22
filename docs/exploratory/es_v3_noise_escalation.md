# ES-v3.0b+ Noise Escalation

Status:

EL-1 exploratory

Date:

2026-05-22

## Setup

Detector:

ES-v2 hard lock

k=5

Attack:

pre-trigger persistence formation only

Attack region:

[trigger_window-10,
 trigger_window-1]

Noise type:

fixed replacement count

1

2

3

4

## Results

| mode | replace_count | n_eligible | trigger_rate | median_delay | delay_shift | miss_rate | NORMAL_FPR | survival_score | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0 | 50 | 1.000000 | 110.000000 | 0.000000 | 0.000000 | 0.000000 | 0.633333 | ROBUST |
| noise_1 | 1 | 42 | 1.000000 | 150.000000 | 40.000000 | 0.000000 | 0.000000 | 0.500000 | ROBUST |
| noise_2 | 2 | 42 | 1.000000 | 160.000000 | 50.000000 | 0.000000 | 0.000000 | 0.466667 | ROBUST |
| noise_3 | 3 | 42 | 1.000000 | 165.000000 | 55.000000 | 0.000000 | 0.000000 | 0.450000 | ROBUST |
| noise_4 | 4 | 42 | 1.000000 | 165.000000 | 55.000000 | 0.000000 | 0.000000 | 0.450000 | ROBUST |

## Robustness boundary

| mode | replace_count | status |
| --- | --- | --- |
| baseline | 0 | ROBUST |
| noise_1 | 1 | ROBUST |
| noise_2 | 2 | ROBUST |
| noise_3 | 3 | ROBUST |
| noise_4 | 4 | ROBUST |

## Interpretation

Detector unchanged.

Observation attacked.

No soft lock.

## Restrictions

No industrial claim

No early-warning claim

No taxonomy update

No frozen modification

EL-1 exploratory only
