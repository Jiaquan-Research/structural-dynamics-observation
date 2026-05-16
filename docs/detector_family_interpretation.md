# Detector Family Interpretation
## Project: D:/Thinking — TEP Geometry Analysis
## Date: 2026-05
## Status: Working document, based on TEP simulation data only

---

## Current Positioning

This project should currently be interpreted as:

- a detector-family analysis study
- a representation-geometry study
- a statistical structure comparison framework

The project does NOT currently establish:

- physical attractors
- causal propagation mechanisms
- control-theoretic stability structure
- physical locking phenomena

All findings are representation-level observations
derived from TEP simulation data.
Domain expert validation is required before
any physical interpretation can be claimed.

---

## 1. Overview

This document records the interpretation of five detectors
evaluated on the Tennessee Eastman Process (TEP) benchmark.

The core finding is not that any single detector is superior,
but that different detectors observe fundamentally different
statistical structures in the same fault data.

This is referred to as **detector disagreement structure**,
and is the central result of this project.

---

## 2. Representation-Level Interpretation

The current project does not claim discovery of
physical attractors or causal propagation mechanisms.

The detectors operate on statistical representations
(windowed trajectories, correlation geometry,
changepoint structure) derived from TEP simulation data.

Therefore:

- "geometry concentration" refers to concentration
  in representation space,
  not proof of physical state trapping.

- "dominant-pair concentration" means that
  a specific variable pair dominates the
  correlation energy within the XMEAS7-11 subspace.
  It does not imply physical causality between
  those variables.

- detector disagreement indicates that different
  statistical projections emphasize different
  structures in the same fault trajectories.

- all findings should currently be interpreted as
  representation-level phenomena,
  not physical-system-level claims.

---

## 3. Detector Family Summary

| detector   | input signal                   | what it observes                         | FP rate | mean detection |
|------------|--------------------------------|------------------------------------------|---------|----------------|
| T²         | trajectory window (52 vars)    | global variance deviation in PCA space   | 0.09%   | 61.9%          |
| SPE        | trajectory window (52 vars)    | residual amplification outside PCA space | 32.1%   | 85.9%          |
| top1_mass  | XMEAS7-11 correlation (5 vars) | persistent dominant-pair concentration   | 4.5%    | 25.2%          |
| ruptures_A | XMEAS7 + XMEAS11 raw (2 vars)  | piecewise-stationary regime shift        | 0.4%    | 31.5%          |
| ruptures_B | XMEAS7-XMEAS11 rolling corr    | coupling statistics changepoint          | 1.4%    | 4.9%           |

---

## 4. Detector Interpretation

### T²
**Observes:** deviation in the principal component
score space.
Sensitive to faults that shift the global mean
or variance of the trajectory window.

**Failure mode:** TEP violates the Gaussian assumption
underlying T². Hard faults (F03/F09/F15) that do not
produce large global variance shifts are missed entirely.
Detection rate on hard faults: <1%.

**Key constraint:** This is a trajectory-window PCA,
not classical per-timestep PCA. n_components=254 retained.
Results are not directly comparable to textbook T² on TEP.

---

### SPE
**Observes:** energy in the residual space after
PCA projection.
More sensitive than T² because it captures variance
not explained by principal components.

**Failure mode:** FP=32% makes it engineering-unusable
at the current operating point. The high FP is likely
caused by trajectory flattening
(100-step windows × 52 vars = 5200-dim vectors),
which makes SPE hypersensitive to normal variation.

**Key insight:** High detection rate (85.9%) is purchased
at the cost of persistent false alarms.
Coverage ≠ reliability.

---

### top1_mass
**Observes:** concentration of correlation energy
into a single dominant variable pair within
the XMEAS7-11 subspace.

Under normal conditions, correlation energy is distributed
across multiple pairs. Under certain faults, it concentrates
persistently into a single pair
(persistent dominant-pair concentration).

**Failure mode:** Only sensitive to faults that alter
coupling structure within the XMEAS7-11 subspace.
Faults that produce global trajectory shifts
without changing this specific coupling structure
are missed (e.g. F02, F11, F17, F18, F19, F20).

**FP floor:** 2.5% irreducible FP from NORMAL windows
with naturally high concentration.
Cannot be eliminated by threshold adjustment.

**Key constraint:** 5-variable subspace only.
Results do not generalize to the full 41-variable system.

---

### ruptures_A
**Observes:** piecewise-stationary regime shifts
in the raw XMEAS7 + XMEAS11 joint signal.
Detects when the joint distribution of these two variables
changes abruptly.

**Failure mode:** Structurally biased toward large,
abrupt shifts. Faults with gradual onset or
representation-geometry-only effects are missed.
F14 detection rate = 0.4% despite F14 having
strong geometry concentration signal.

**Key insight:** ruptures_A strongly detects
F02/F07/F18 (raw shift family) but completely misses F14
(geometry-only family).
This separation is the strongest evidence that
top1_mass and ruptures_A observe different
statistical structures.

---

### ruptures_B
**Observes:** changepoints in the rolling correlation
between XMEAS7 and XMEAS11 (window=100 steps).

**Failure mode:** Very low coverage (mean detection=4.9%).
Rolling correlation changepoint is not equivalent to
persistent geometry concentration.
A fault can produce persistent dominant-pair concentration
(top1_mass=1.0) without producing a detectable changepoint
in rolling correlation.

**Key insight:** ruptures_B and top1_mass have the lowest
pairwise disagreement (mean_delta=0.221),
but this reflects shared input constraints
(both limited to XMEAS7-11 subspace),
not mechanistic similarity.
The agreement reflects common failure modes,
not common detection mechanisms.

---

## 5. Detector Disagreement Structure

A central finding of this project is that
different detectors disagree systematically,
not randomly.

This disagreement is itself informative.

**Pairwise disagreement summary
(mean absolute delta over F01-F20):**

| pair                    | mean delta |
|-------------------------|------------|
| SPE vs ruptures_B       | 0.810      |
| top1_mass vs SPE        | 0.607      |
| ruptures_A vs SPE       | 0.544      |
| T2 vs ruptures_B        | 0.575      |
| top1_mass vs T2         | 0.404      |
| ruptures_A vs T2        | 0.323      |
| ruptures_B vs ruptures_A| 0.271      |
| top1_mass vs ruptures_A | 0.271      |
| top1_mass vs ruptures_B | 0.221      |
| T2 vs SPE               | 0.241      |

**Key separations:**

F14: top1_mass=0.974, ruptures_A=0.004.
Strong geometry concentration,
almost no raw signal regime shift.
This is the strongest evidence that
persistent dominant-pair concentration
is not equivalent to raw trajectory change.

F02: top1_mass=0.064, ruptures_A=0.998.
Strong raw regime shift,
almost no geometry concentration.
Confirms that raw shift and geometry concentration
are separable phenomena.

F06 vs F14 contrast:
Both show strong dominant-pair concentration
(top1_mass ≈ 1.0),
but F06 also shows strong ruptures_A (1.0)
while F14 does not (0.004).
Same representation-geometry output,
potentially different underlying structure.

These disagreements suggest that different detectors
observe different statistical structures
rather than providing noisy approximations
of the same underlying signal.

---

## 6. Fault Archetype Structure

Based on the detector response matrix,
four fault archetypes are visible in the data.

**Response levels:**
Strong: detection_rate ≥ 0.70
Moderate: 0.20 ≤ detection_rate < 0.70
Weak: 0.05 ≤ detection_rate < 0.20
Insensitive: detection_rate < 0.05

### Archetype A: Classical-Global
**Faults:** F11, F17, F19, F20
**Pattern:** T²=Strong, SPE=Strong,
top1_mass=Weak, ruptures_A=Weak
**Interpretation:** Fault produces global trajectory
deviation detectable by covariance-based methods,
but does not alter XMEAS7-11 correlation structure.

### Archetype B: Raw-Shift
**Faults:** F02, F07, F18
**Pattern:** ruptures_A=Strong, top1_mass=Weak
**Interpretation:** Fault produces abrupt regime shift
in XMEAS7+XMEAS11 raw signal,
but does not produce persistent geometry concentration.

### Archetype C: Geometry-Only
**Faults:** F14
**Pattern:** top1_mass=Strong (0.974),
ruptures_A=Insensitive (0.004)
**Interpretation:** Fault produces persistent
dominant-pair concentration
without comparable raw signal shift.
This is the strongest evidence for a
representation-geometry-specific detection mechanism.

### Archetype D: Mixed-Coupled
**Faults:** F06, F08, F12, F13
**Pattern:** Multiple detectors respond simultaneously
with different strengths.
**Interpretation:** Fault affects multiple statistical
structures simultaneously.
F06 shows dominant-pair concentration AND raw shift.
F14 shows dominant-pair concentration WITHOUT raw shift.
This contrast suggests that geometry concentration
can arise from different underlying representation
structures.

---

## 7. Open Questions

**Q1: What causes F14's geometry-only pattern?**
F14 (reactor cooling water valve sticking) produces
strong dominant-pair concentration without raw signal shift.
The representation-level observation is clear,
but the physical mechanism is unknown.
Domain expert validation needed.

**Q2: Is geometry concentration related to
effective dimensionality reduction
in representation space?**
top1_mass measures correlation energy concentration.
An alternative framing: fault reduces the effective
dimensionality of the windowed correlation representation.
These two framings may be equivalent or may diverge
for certain fault types.
This is an open question, not yet tested.

**Q3: Would Transfer Entropy resolve the F14 pattern?**
F14's geometry signal involves XMEAS7-XMEAS11.
Transfer Entropy could determine whether this pair
shows directional information flow during F14,
which would provide additional characterization
of the representation structure.
Note: Transfer Entropy result would still be
a representation-level finding,
not a physical causality proof.

**Q4: Does the XMEAS7-11 subspace generalize?**
All geometry results are limited to 5 variables.
The same analysis on a different variable subset
might reveal different fault sensitivities.
Variable subset selection remains an open problem.

---

## 8. Limitations

1. All results based on TEP simulation data only.
   Real industrial systems will have different noise
   characteristics, sensor configurations,
   and fault modes.

2. top1_mass and ruptures_A/B are limited to
   the XMEAS7-11 subspace (5 of 41 variables).
   Coverage does not represent full system behavior.

3. Fault archetypes are descriptive classifications,
   not proof of physical causality.

4. PCA baseline uses trajectory-window flattening,
   not classical per-timestep PCA.
   Results are not directly comparable to
   standard TEP benchmark literature.

5. Detector disagreement structure is a
   representation-level finding.
   It does not establish that different physical
   mechanisms are operating.

6. Domain expert validation is required before
   any of these findings can be claimed as
   physically meaningful.

---

## 9. Next Steps

**Immediate:**
- F14 geometry profile
  (pair persistence, raw traces,
  rolling correlation, comparison with F06)
- Fault archetype visualization
  (F14 vs F06 vs F02 three-way contrast)

**Medium term:**
- Transfer Entropy analysis on F14
- Variable subset expansion beyond XMEAS7-11
- Classical per-timestep PCA baseline
  for literature comparison

**Longer term:**
- Effective dimensionality analysis
  in representation space
- Marine system mapping (MAN S50MC6)
- Real data validation
