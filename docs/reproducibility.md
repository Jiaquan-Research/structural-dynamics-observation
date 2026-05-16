# Reproducibility Guide

## Representation Stability Audit v1

Date: 2026-05
Snapshot: representation_stability_v1

---

# 1. Scope

This document records the reproducibility conditions for:

```text
Representation Stability Audit v1
```

including:

* occupancy / entropy analysis
* 20-run clustering
* 500-run validation
* detector comparison
* F02/F06/F14 archetype profiling

This document freezes:

* runtime environment
* benchmark conventions
* dataset assumptions
* parameter choices
* output conventions
* taxonomy evaluation order

---

# 2. Runtime Environment

## Python

Primary environment:

```text
Python 3.12.10
```

Virtual environment:

```text
.venv312
```

---

## Major Packages

Core packages:

```text
numpy
pandas
matplotlib
scipy
scikit-learn
ruptures==1.1.10
```

---

## Matplotlib Backend

Current plotting backend:

```python
matplotlib.use("Agg")
```

used to avoid:

```text
Tk/Tcl backend issues on Python 3.12
```

---

# 3. Dataset Assumptions

Current experiments assume:

```text
TEP simulated dataset
```

with:

* F01–F20 faults
* NORMAL runs
* 500 runs per fault
* trajectory-style time series

---

## Variable Subspace

Current geometry experiments primarily use:

```text
XMEAS7–XMEAS11
```

Important:

Current conclusions are conditional on this subspace.

No claim of global system behavior is made.

---

## Pair Space Definition

Current pair space consists of:

```text
all unordered variable pairs
inside XMEAS7–XMEAS11
```

Current pair count:

```text
C(5,2) = 10
```

This pair-space definition affects:

* entropy ceiling
* occupancy interpretation
* dominant-pair statistics

Future subspace expansion
will therefore change entropy scale.

---

# 4. Frozen Benchmark Conventions

The following conventions are frozen for Representation Stability v1.

---

## Windowing

```text
WINDOW = 100
STEP = 100
```

---

## Sample Filter

```text
SAMPLE_FILTER = 200
```

Meaning:

analysis starts after first 200 timesteps.

---

## Persistence Definition

Current persistence convention:

```text
K = 3
```

used for pair persistence logic.

---

# 5. Representation Metrics

## Occupancy

Definition:

```text
fraction of windows occupied
by dominant pair
```

Range:

```text
0.0 – 1.0
```

---

## Entropy

Definition:

```text
H = -Σ p_i ln(p_i)
```

where:

```text
p_i = dominant pair occupancy ratio
```

Current implementation:

```text
natural logarithm
```

NOT:

```text
base-2 entropy
```

Important:

Entropy values in current snapshot
must therefore NOT be interpreted as bits.

---

## Dominant Pair Consistency

Definition:

```text
fraction of runs sharing
same dominant pair identity
```

This metric is:

```text
cross-run
```

not within-run.

---

# 6. Representation Class Rules

Current taxonomy consists of:

```text
Locked
Stable
Transitional
Diffuse
```

These are:

```text
heuristic partitions
```

NOT:

```text
natural discontinuities
```

---

## Evaluation Order

Classification order is frozen as:

```text
Locked
→ Stable
→ Transitional
→ Diffuse
```

Rule:

```text
First match wins.
```

This ordering is required for deterministic reproduction.

---

## Locked

```text
occupancy >= 0.90
entropy <= 0.20
```

---

## Stable

```text
occupancy >= 0.70
entropy <= 0.60
```

but not Locked.

---

## Transitional

```text
(0.40 <= occupancy < 0.70)
OR
(0.60 < entropy <= 1.20)
```

but not Locked or Stable.

---

## Diffuse

All remaining faults.

Typical properties:

```text
occupancy < 0.40
high entropy
low consistency
```

---

# 7. Detector Conventions

## top1_mass

Measures dominant-pair concentration.

Interpretation is strictly:

```text
representation-level geometry concentration
```

NOT:

* physical causality
* control structure
* attractor dynamics

---

## ruptures_A

Input:

```text
XMEAS7 + XMEAS11
```

Current interpretation:

```text
distribution transition detector
```

---

## ruptures_B

Input:

```text
rolling correlation trajectory
```

Current result:

```text
weak detector performance
```

This result is frozen as a negative finding.

---

# 8. Determinism and Run Selection

Current experiments:

```text
do NOT globally freeze random seed
```

However:

run selection itself is deterministic.

---

## Full Benchmark Selection

Current convention:

```text
first N runs
by run_id sorted order
```

This is deterministic.

---

## Archetype Profile Selection

Current convention:

```text
p95 run selected by
mean top1_mass across runs
```

Given fixed input data,
this selection is deterministic.

---

## Determinism Policy

Current reproducibility relies on:

* deterministic run selection
* fixed benchmark conventions
* fixed variable subspace
* large sample size
* repeated structure

rather than single-seed replay.

---

# 9. Runtime Notes

Approximate runtime:

| Experiment                   | Runtime    |
| ---------------------------- | ---------- |
| representation_audit_500runs | ~548 sec   |
| ruptures full benchmark      | multi-hour |
| archetype profile generation | minutes    |

---

# 10. Output Conventions

## CSV

Stored under:

```text
outputs/csv/
```

---

## Figures

Stored under:

```text
outputs/taxonomy/
```

---

## Frozen Snapshot

Stable assets copied into:

```text
docs/frozen/representation_stability_v1/
```

---

# 11. Interpretation Boundary

All conclusions in Representation Stability v1 are limited to:

```text
representation-level statistical structure
```

Current work does NOT establish:

* physical mechanism
* causal graph
* attractor dynamics
* system ontology

---

# 12. Known Limitations

Current snapshot limitations:

* limited variable subspace
* top1-only geometry representation
* heuristic taxonomy thresholds
* no Transfer Entropy analysis yet
* no real industrial data validation

These limitations are intentionally retained.

---

# 13. Frozen Snapshot Policy

Representation Stability v1 is considered:

```text
frozen baseline
```

Future experiments:

* Transfer Entropy
* expanded subspaces
* alternative entropy definitions
* topology metrics

must NOT overwrite
current v1 conclusions.

Instead:

future work should create:

```text
v2 / TE-V1 / SUBSPACE-V1
```

style extensions.
