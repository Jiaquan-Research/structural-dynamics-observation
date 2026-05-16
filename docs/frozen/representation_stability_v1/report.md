# Representation Stability v1 Frozen Snapshot

## Scope

This snapshot freezes the current TEP representation-stability results as of 2026-05.

It is a representation-level detector family study based on TEP simulation data.

It does not claim physical causality, attractor dynamics, physical locking, or process ontology.

## Frozen Results

### 500-Run Representation Classes

| Class | Faults |
|---|---|
| Locked | F06 F08 F13 F14 |
| Stable | F18 |
| Transitional | F11 F12 F17 F19 F20 |
| Diffuse | F01 F02 F03 F04 F05 F07 F09 F10 F15 F16 |

### Stability Check

The 500-run audit preserved 19/20 class identities from the 20-run audit.
F01 shifted from Transitional to Diffuse, consistent with its boundary status.

### Key Frozen Conclusions

1. Occupancy + entropy produce stable representation clustering.
2. Pair consistency is an independent representation dimension.
3. F06 and F14 have similar locked representation behavior but different ruptures_A response.
4. F13 does not show strong bimodal occupancy structure in the 500-run sample.
5. ruptures_B does not explain geometry persistence.
6. Diffuse faults retain weak pair preference rather than complete randomness.

## Snapshot Contents

- `taxonomy_rules.md`: frozen class rules and thresholds.
- `evidence_levels.md`: evidence hierarchy and claim levels.
- `failed_hypotheses.md`: rejected/downgraded hypotheses.
- `experiment_registry.md`: experiment list, status, conclusion, and EL.
- `figure_registry.md`: figure IDs and meanings.
- `decision_log.md`: research decisions that shaped the snapshot.
- `research_positioning.md`: project boundary and positioning.
- `csv/`: copied CSV outputs used by the snapshot.
- `figures/`: copied figure outputs used by the snapshot.

## Conservative Interpretation

All conclusions are conditional on:

- TEP simulation data
- current XMEAS7-11 subspace
- current windowing and geometry configuration
- current detector operating points
- current heuristic taxonomy thresholds

Domain expertise and independent mechanism validation are required before any physical interpretation can be claimed.
