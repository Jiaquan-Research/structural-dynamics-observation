# TEP Geometry / Representation Stability Research Log
## Exploratory Research Notes — Version 0.3
## Date: 2026-05

---

# 0. Scope Boundary

This document records exploratory statistical observations
derived from TEP simulation data.

All interpretations are strictly limited to:

- representation-level statistics
- detector behavior
- subspace structure
- statistical stability patterns

This document does NOT claim:

- physical causality
- attractor dynamics
- system ontology
- generalized intelligence theory
- consciousness-like behavior

All conclusions remain conditional on:
current detector configuration,
current variable subset,
and current benchmark methodology.

---

# 1. Initial Motivation

The original objective was simple:

Can geometry-based detectors
observe fault structure
that traditional trajectory detectors miss?

The initial detector family included:

- T²
- SPE
- top1_mass
- rolling correlation structure
- changepoint detectors

At the beginning,
the working assumption was:

```text
fault severity ≈ anomaly amplitude
```

The experiments eventually showed:
this assumption is incomplete.

Different faults appear to produce
different statistical structure families.

---

# 2. Detector Families

## 2.1 Classical Trajectory Detectors

### T²

Measures global trajectory deviation.

### SPE

Measures reconstruction residual magnitude.

These detectors respond strongly to:

- global trajectory drift
- large state deviation
- broad statistical change

---

## 2.2 Geometry Concentration Detector

### top1_mass

Measures whether
a dominant variable pair
captures most geometry contribution.

High top1_mass means:

```text
representation concentrated
into a small pair subspace
```

Important:

This is NOT physical causality.

It only describes
representation allocation behavior.

---

## 2.3 Representation Stability Metrics

### Occupancy

Fraction of windows
occupied by dominant pair.

### Entropy

Shannon entropy
over dominant pair switching.

These metrics describe:

```text
representation switching behavior
```

not physical system state.

---

# 3. Early False Directions

Several early hypotheses failed.

---

## 3.1 Global Attractor Hypothesis Failed

Early observations suggested:

```text
all faults converge toward
a shared temporal geometry structure
```

Random subset audits disproved this.

Result:

geometry concentration
depends heavily on variable subset selection.

Conclusion:

```text
no evidence for system-wide attractor
```

Current interpretation:

```text
fault-conditioned subspace structure
```

---

## 3.2 Correlation Shift ≠ Geometry Concentration

ruptures_B
(using rolling correlation changepoints)
almost completely failed.

Observed:

```text
detection ≈ 4.9%
```

This showed:

```text
geometry concentration
cannot be reduced
to simple correlation regime shifts
```

---

## 3.3 Threshold Scaling Did Not Remove FP Floor

Increasing top1_mass threshold:

```text
0.80 → 0.90 → 0.95
```

did NOT eliminate FP floor.

Observed:

```text
FP remained ≈ 2.5%
```

Interpretation:

NORMAL data itself contains
persistent geometry activity.

This was an important negative result.

---

# 4. Detector Space Interpretation

Current results suggest:

different detectors observe
different statistical structures.

---

## T² / SPE

Primarily respond to:

```text
global trajectory deviation
```

---

## ruptures_A

Primarily responds to:

```text
distribution transition
variance structure change
```

---

## top1_mass

Primarily responds to:

```text
pair dominance concentration
```

---

## occupancy / entropy

Primarily respond to:

```text
representation stability
```

---

Therefore:

```text
detector disagreement
may reflect different statistical projections
of the same fault
```

rather than simple detector quality differences.

This became a major conceptual shift.

---

# 5. Archetype Triangle

Three representative archetypes emerged.

---

## 5.1 F02 — Raw-Shift Dominant

Observed:

- high T²/SPE
- high ruptures_A
- low occupancy
- high entropy
- switching dominant pairs

Interpretation:

```text
representation remains diffuse
while trajectory distribution changes strongly
```

---

## 5.2 F06 — Locked + Transition Structure

Observed:

- occupancy = 1.0
- entropy = 0.0
- strong top1_mass
- strong ruptures_A
- persistent dominant pair

Interpretation:

```text
representation highly constrained
with strong transition evidence
```

---

## 5.3 F14 — Locked Without Strong Transition Evidence

Observed:

- occupancy = 1.0
- entropy = 0.0
- strong top1_mass
- no ruptures_A detection

F14 did NOT exhibit
the large transition-like variance surge
seen in F06.

Under current:

- penalty
- rbf cost
- detector configuration

ruptures_A detected no changepoint.

Current evidence supports:

```text
F14 geometry concentration
does not depend on
F06-like strong transition structure
```

However:

Current evidence does NOT prove:

```text
absence of distribution transition
```

Only:

```text
current detector configuration
did not observe sufficiently strong
transition evidence
```

This distinction is important.

---

# 6. Rolling Statistics Deep Dive

Detailed rolling statistics were compared for:

- F02
- F06
- F14

using:

- rolling std
- rolling mean
- rolling correlation
- changepoints

---

## 6.1 Key Observation

Rolling std alone
could NOT fully explain
F06 vs F14 detector difference.

Observed:

| Fault | Rolling Std Max |
| ----- | --------------- |
| F02   | ~21             |
| F06   | ~74             |
| F14   | ~13             |

F06 clearly exhibited:

```text
large transient variance surge
```

But F14 still showed
nontrivial rolling std structure.

Conclusion:

```text
ruptures_A behavior
likely depends on joint distribution structure
not only variance magnitude
```

---

## 6.2 Pair Persistence

F06 and F14 both showed:

```text
occupancy = 1.0
entropy = 0.0
```

while F02 showed:

```text
occupancy ≈ 0.29
entropy ≈ 1.35
```

This strongly separated:

```text
locked representation
vs diffuse representation
```

---

# 7. Full F01–F20 Representation Audit

A full audit
across F01–F20
(first 20 runs per fault)
was performed.

Metrics:

- occupancy
- entropy
- dominant pair persistence

---

## 7.1 Representation Classes

### Locked

```text
F06 F08 F13 F14
```

Characteristics:

- occupancy ≈ 1.0
- entropy ≈ 0
- highly stable representation

---

### Stable

```text
F18
```

Characteristics:

- high occupancy
- moderate entropy
- stable but not locked

---

### Transitional

```text
F01 F11 F12 F17 F19 F20
```

Characteristics:

- moderate occupancy
- moderate entropy
- persistent switching

---

### Diffuse

```text
F02 F03 F04 F05 F07 F09 F10 F15 F16
```

Characteristics:

- low occupancy
- high entropy
- unstable dominant pair structure

---

## 7.2 Important F13 Observation

F13 showed:

```text
high representation stability
but relatively low top1_mass detection rate
```

This may indicate:

1. significant run-to-run heterogeneity
2. decoupling between amplitude and stability
3. some runs near locking,
   others closer to transitional behavior

Whether true bimodal structure exists
requires future distribution analysis.

---

# 8. Detector Disagreement

Pairwise detector disagreement analysis showed:

```text
SPE vs ruptures_B
= largest disagreement
```

while:

```text
top1_mass vs ruptures_B
= strongest agreement
```

Interpretation:

different detectors
may be observing fundamentally different
statistical phenomena.

---

# 9. Current Confirmed Findings

Current evidence supports:

---

## 9.1

Geometry concentration exists
in multiple TEP faults.

---

## 9.2

Representation stability
can be quantified using:

- occupancy
- entropy

---

## 9.3

Faults appear to separate into:

- locked
- stable
- transitional
- diffuse

representation families.

---

## 9.4

top1_mass amplitude
and representation stability
are related but not identical.

---

## 9.5

F06:

```text
distribution transition evidence
+ geometry concentration
```

F14:

```text
geometry concentration
without strong ruptures_A-visible transition structure
```

---

## 9.6

Detector disagreement
contains meaningful structural information.

---

# 10. Current Explicit Non-Claims

Current work does NOT support:

- attractor dynamics claims
- physical locking claims
- causal graph interpretation
- generalized complexity theory
- consciousness-like interpretation

Terms such as:

- locking
- stability
- concentration

describe ONLY:

```text
representation-level statistical behavior
```

They do NOT imply
physical system attractors
or dynamical fixed points.

---

# 11. Negative Results That Changed Direction

---

## 11.1 Random Subset Audit Rejected Global Attractor Narrative

Early interpretation drifted toward:

```text
system-wide temporal attractor
```

Random subset audit disproved this.

Project direction changed toward:

```text
fault-conditioned subspace geometry
```

This was the first major hypothesis downgrade.

---

## 11.2 ruptures_B Failed

rolling-correlation changepoints
did not reproduce geometry concentration behavior.

This ruled out:

```text
simple correlation-regime explanation
```

---

## 11.3 Threshold Scaling Could Not Remove FP Floor

False positives persisted
despite threshold increases.

This suggested:

```text
background geometry activity
exists in NORMAL data
```

This became an important boundary condition.

---

# 12. Current Research Direction

Most promising next directions:

---

## 12.1 Full 500-run Occupancy Audit

Current representation audit
used first 20 runs only.

Need:

```text
full F01–F20
500-run occupancy/entropy distributions
```

---

## 12.2 Distribution Structure Analysis

Current results suggest:

```text
transition structure matters
```

Need future work on:

- rolling covariance
- local density evolution
- spectral structure
- transition persistence

---

## 12.3 Cross-Detector Structure Mapping

Goal:

```text
map detector families
to statistical structure families
```

rather than treating all detectors
as equivalent anomaly scores.

---

# 13. Meta-Methodological Note

During this research:

```text
hypothesis downgrade
was treated as progress
```

Priority remained:

```text
reduce incorrect interpretation
rather than expand narrative scope
```

This constraint remains active.
