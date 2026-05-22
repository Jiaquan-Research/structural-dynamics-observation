# ES-v3.3b Collapse Cluster Audit

Status: EL-1 exploratory
Date: 2026-05-23

## Collapse sets

| set | runs |
| --- | --- |
| C3 | 15, 22, 23, 24, 30, 48 |
| C5 | 15, 22, 23, 24, 30, 48 |
| C10 | 15, 22, 23, 24, 30, 48 |
| Intersection | 15, 22, 23, 24, 30, 48 |
| Union | 15, 22, 23, 24, 30, 48 |

## Persistence

| class | count |
| --- | --- |
| never | 36 |
| fixed | 6 |

## Artifact overlap

| metric | value |
| --- | --- |
| overlap_no_replacement | 0.000000 |
| overlap_no_replacement_jaccard | 0.000000 |
| overlap_horizon | 0.000000 |
| overlap_horizon_jaccard | 0.000000 |

## Baseline comparison

| ('collapse_class', '') | ('baseline_locked_fraction', 'mean') | ('baseline_locked_fraction', 'median') | ('baseline_duration', 'mean') | ('baseline_duration', 'median') | ('is_no_replacement', 'mean') | ('is_no_replacement', 'median') | ('is_horizon_overlap', 'mean') | ('is_horizon_overlap', 'median') |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | 0.528889 | 0.540000 | 34.833333 | 33.500000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| never | 0.732222 | 0.733333 | 50.166667 | 54.000000 | 0.000000 | 0.000000 | 0.222222 | 0.000000 |

## Key question

Fixed cluster?

or

attack dependent?

## Verdict

structural

## Restrictions

No TE

No taxonomy update

No industrial claim

No early-warning claim

EL-1 exploratory only

## ES-v3.3c Profile Follow-up

Collapse cluster:

[15,22,23,24,30,48]

Results:

weak_lock:

6 / 6

recovery_fragile:

6 / 6

fragmented:

2 / 6

late_trigger:

0 / 6

Interpretation:

Fragmentation exists

but is not dominant.

Primary signal:

low baseline lock

↓

fragile recovery

↓

fixed collapse cluster

Current interpretation:

population split

within recovery behavior.

Exploratory only.

No archetype promotion.
