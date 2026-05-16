# Taxonomy Rules Freeze

This document freezes the Representation Stability v1 taxonomy rules.

These boundaries are heuristic partitions,
not natural discontinuities.

## Metrics

### occupancy_ratio

The fraction of evaluation windows occupied by the most frequent dominant pair.

### pair_entropy

Shannon entropy of the dominant-pair frequency distribution using natural logarithm.

### mean_run_length

The unweighted mean of consecutive same-pair run lengths within a run.

### dominant_pair_consistency

Across runs for the same fault, the fraction of runs whose dominant pair matches the most common dominant pair.

## Representation Classes

Classification is applied in priority order.

1. **Locked**
   - `mean_occupancy >= 0.90`
   - `mean_entropy <= 0.20`

2. **Stable**
   - `mean_occupancy >= 0.70`
   - `mean_entropy <= 0.60`

3. **Transitional**
   - `0.40 <= mean_occupancy < 0.70`
   - OR `0.60 < mean_entropy <= 1.20`

4. **Diffuse**
   - `mean_occupancy < 0.40`
   - OR `mean_entropy > 1.20`

## Frozen 500-Run Classes

| Class | Faults |
|---|---|
| Locked | F06 F08 F13 F14 |
| Stable | F18 |
| Transitional | F11 F12 F17 F19 F20 |
| Diffuse | F01 F02 F03 F04 F05 F07 F09 F10 F15 F16 |

## Interpretation Boundary

The taxonomy describes representation-space stability only.
It does not imply physical locking, attractors, causal mechanisms, or process ontology.
