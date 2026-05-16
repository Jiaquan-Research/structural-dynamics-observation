# Research Log

## Representation Stability Audit (F01–F20, 500-run validation)

Date: 2026-05
Status: Task 1 complete, frozen before Transfer Entropy exploration

---

# 1. Objective

This stage aimed to answer a core question:

> Do fault representations in the geometry space exhibit stable statistical structure across runs?

More specifically:

* Is `top1_mass` sufficient to characterize representation behavior?
* Do some faults exhibit stable dominant-pair persistence?
* Can representation behavior be grouped into reproducible statistical classes?
* Are these classes robust under larger sample sizes?

The work evolved from local F02/F06/F14 inspection into a full F01–F20 representation stability audit.

---

# 2. Scope and Constraints

This work is strictly representation-level analysis.

The following are NOT claimed:

* physical mechanism
* causal structure
* attractor dynamics
* ontology-level fault hierarchy

All conclusions are limited to observable statistical structure in the current representation space.

---

# 3. Interpretation Safety Rule

When empirical patterns exist, descriptive taxonomy is allowed.

However, taxonomy does NOT automatically imply:

* physical mechanism
* causal explanation
* dynamical attractor
* ontology claim

unless supported by independent mechanism evidence.

This rule applies throughout the entire document.

---

# 4. Evidence Level (EL) System

To separate observation from interpretation, the following evidence hierarchy is adopted.

| Level | Definition                                                           |
| ----- | -------------------------------------------------------------------- |
| EL-1  | Single/small-sample observation, not validated                       |
| EL-2  | Repeated empirical pattern                                           |
| EL-3  | Large-sample statistically stable pattern with counterexample checks |
| EL-4  | Mechanism-supported interpretation independently validated           |

Examples in current work:

| Claim                                           | EL   |
| ----------------------------------------------- | ---- |
| F14 geometry-only archetype                     | EL-2 |
| Occupancy/entropy clustering (500 runs)         | EL-3 |
| ruptures_B failure                              | EL-3 |
| Representation regime above physical fault type | EL-1 |

---

# 5. Initial Observation: Archetype Triangle

Three faults emerged as early anchors:

| Fault | Initial characterization              |
| ----- | ------------------------------------- |
| F02   | Diffuse / transitional representation |
| F06   | Strong stable pair locking            |
| F14   | Geometry-only stable locking          |

Initial visual profiling showed:

* F06 and F14 both maintain dominant-pair persistence
* F02 exhibits pair switching across windows
* F14 maintains near-perfect top1 stability without clear ruptures_A detection

This led to the first hypothesis split:

| Hypothesis                                             | Result    |
| ------------------------------------------------------ | --------- |
| High top1_mass alone explains representation structure | Rejected  |
| Pair persistence may be more important than amplitude  | Supported |

---

# 6. Occupancy / Entropy Framework

To quantify representation stability, two metrics were introduced.

## 6.1 Occupancy

Definition:

```text
occupancy = fraction of windows occupied by dominant pair
```

Interpretation:

* high occupancy → stable dominant pair persistence
* low occupancy → frequent pair switching

---

## 6.2 Entropy

Definition:

```text
H = -Σ p_i ln(p_i)
```

where `p_i` is dominant-pair occupancy ratio.

Current implementation uses natural logarithm.

Important:

* entropy is currently NOT normalized
* current ceiling depends on pair-space size
* with 10 pairs, theoretical maximum entropy is:

```text
ln(10) ≈ 2.30
```

Observed diffuse faults (~1.4–1.6) therefore still retain partial pair preference rather than complete randomness.

Future experiments may migrate to base-2 entropy for interpretability.

---

# 7. Pair Persistence as Representation Structure

A key discovery emerged:

Two faults with similar `top1_mass` behavior may exhibit very different pair persistence structure.

Example:

| Fault | Occupancy | Entropy | Interpretation        |
| ----- | --------- | ------- | --------------------- |
| F06   | 1.0       | 0.0     | full pair persistence |
| F14   | 1.0       | 0.0     | full pair persistence |
| F02   | 0.286     | 1.35    | pair switching        |

This established:

> representation stability is not reducible to amplitude alone.

EL level: EL-3

---

# 8. Rolling Statistics Analysis

A deeper inspection compared:

* rolling std
* rolling mean
* rolling correlation
* ruptures_A changepoints

across F02/F06/F14.

---

# 9. Key Result: F06 vs F14 Separation

A critical distinction emerged.

## 9.1 F06

Observed behavior:

* strong XMEAS7 transition
* very high rolling std spike
* abrupt distribution shift
* ruptures_A detects changepoint

Interpretation:

```text
distribution transition type
```

EL: EL-2

---

## 9.2 F14

Observed behavior:

* stable dominant pair occupancy
* occupancy = 1.0
* entropy = 0.0
* no ruptures_A detection
* rolling std elevated but moderate
* stable representation persistence

Interpretation:

```text
representation stability without strong distribution transition
```

EL: EL-2

Importantly:

Current evidence does NOT support:

* collapse dynamics
* attractor claim
* absorbing-state claim

Only stable representation persistence is supported.

---

# 10. H4 Failure: ruptures_B

An important negative result.

Hypothesis:

```text
rolling correlation changepoints
may explain geometry concentration
```

Result:

```text
largely unsupported
```

Observed:

* rolling correlation often changes smoothly
* geometry persistence exists without sharp correlation changepoints
* ruptures_B shows weak discriminative power

This formally separates:

```text
geometry concentration
≠
rolling-correlation changepoint detection
```

EL: EL-3

This negative result is retained intentionally.

---

# 11. Full F01–F20 Audit (20-run)

Initial clustering using first 20 runs:

| Class        | Faults                              |
| ------------ | ----------------------------------- |
| Locked       | F06 F08 F13 F14                     |
| Stable       | F18                                 |
| Transitional | F01 F11 F12 F17 F19 F20             |
| Diffuse      | F02 F03 F04 F05 F07 F09 F10 F15 F16 |

This clustering appeared visually robust.

However:

F01 sat near the Transitional/Diffuse boundary.

Important:

These boundaries are heuristic partitions rather than natural discontinuities.

EL: EL-2

---

# 12. 500-run Validation

A full 500-run audit was performed.

Dataset size:

```text
20 faults × 500 runs = 10,000 runs
```

---

# 12.1 Stability Result

500-run clustering:

| Class        | Faults                                  |
| ------------ | --------------------------------------- |
| Locked       | F06 F08 F13 F14                         |
| Stable       | F18                                     |
| Transitional | F11 F12 F17 F19 F20                     |
| Diffuse      | F01 F02 F03 F04 F05 F07 F09 F10 F15 F16 |

Only change:

```text
F01:
  Transitional → Diffuse
```

Interpretation:

F01 lies near the heuristic class boundary and is therefore more sensitive to sample size and threshold effects.

Core result:

```text
19/20 faults preserved class identity
under 500-run scaling
```

EL: EL-3

This is currently the strongest result in the project.

---

# 12.2 F13 Bimodal Hypothesis

A prior hypothesis suggested:

```text
F13 may contain hidden high/low occupancy submodes
```

500-run audit showed:

```text
mean occupancy = 0.956
std = 0.082
p05 = 0.85
n(occ < 0.5) = 0
```

Conclusion:

No evidence for strong bimodal structure.

F13 behaves as globally high-stability rather than mixed-mode.

Hypothesis formally rejected.

EL: EL-3

---

# 12.3 Dominant Pair Consistency

A second dimension was introduced:

```text
dominant_pair_consistency
```

Definition:

```text
fraction of runs sharing same dominant pair identity
```

This revealed:

occupancy alone is insufficient.

Example:

| Fault          | Occupancy   | Consistency |
| -------------- | ----------- | ----------- |
| F06            | high        | high        |
| F14            | high        | high        |
| F12            | medium-high | medium-high |
| F01            | low-medium  | high        |
| Diffuse faults | low-medium  | low         |

Interpretation:

* occupancy measures within-run persistence
* consistency measures cross-run pair identity stability

This became one of the most important outcomes of the audit.

EL: EL-3

---

# 12.4 F18 Interpretation

F18 occupies an intermediate region:

```text
occupancy ≈ 0.79
consistency ≈ 0.89
```

Interpretation:

* individual runs exhibit relatively strong persistence
* dominant pair identity shows limited drift across runs

No stronger dynamical interpretation is claimed.

EL: EL-2

---

# 12.5 Diffuse Fault Structure

Diffuse faults cluster around:

```text
entropy ≈ 1.4–1.6
occupancy ≈ 0.3–0.4
consistency ≈ 0.25–0.40
```

Interpretation:

* representation is not fully random
* weak pair preferences exist
* dominant pair identity varies substantially between runs

Current data supports:

```text
weakly biased but unstable pair structure
```

Current top1-only representation has NOT yet revealed stable higher-order subgroup structure inside Diffuse faults.

This is NOT interpreted as methodological failure.

EL: EL-2

---

# 12.6 Locked Cluster

The following faults consistently form a highly stable cluster:

```text
F06 F08 F13 F14
```

Properties:

* occupancy ≈ 1.0
* entropy ≈ 0.0
* high pair consistency

This structure survived:

* 20-run audit
* 500-run scaling
* counterexample checks

EL: EL-3

Current interpretation:

```text
stable statistical representation grouping
```

No ontology claim is made.

---

# 13. Current Interpretation Boundary

Supported:

* representation stability classes exist
* classes are statistically robust
* pair persistence is a meaningful axis
* consistency adds independent information
* geometry representation is not reducible to amplitude

NOT supported:

* physical mechanism equivalence
* causal hierarchy
* attractor dynamics
* representation ontology

---

# 14. Frozen Conclusions

The following conclusions are considered stable enough to freeze before Transfer Entropy work.

## Frozen Conclusions

1. Occupancy + entropy produce stable representation clustering

2. 500-run validation preserves 19/20 class identities

3. Pair consistency is an independent representation dimension

4. F06 and F14 represent distinct statistical behaviors

5. F13 does not exhibit strong bimodal occupancy structure

6. ruptures_B does not explain geometry persistence

7. Diffuse faults retain weak pair preference rather than complete randomness

All frozen conclusions currently remain within EL-3 or below.

---

# 15. Next Stage

Next planned direction:

```text
Transfer Entropy / directional information flow
```

Important:

This is currently exploratory.

Potential goals:

* identify directional asymmetry
* explain pair persistence emergence
* investigate locking formation conditions

Current status:

```text
mechanism unknown
```

No causal interpretation is currently justified.

Transfer Entropy work therefore begins as EL-1 exploratory analysis.
