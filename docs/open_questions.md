# Open Questions

## Representation Stability Audit v1

Date: 2026-05
Snapshot: representation_stability_v1

---

# 1. Purpose

This document records:

```text
unresolved questions
```

emerging from the Representation Stability Audit v1 snapshot.

These questions are intentionally preserved.

Current status of most items:

```text
EL-1 exploratory
```

or:

```text
EL-2 repeated empirical observation
```

They are NOT considered established conclusions.

---

# 2. Core Open Question

## Q1 — Why do some faults enter stable representation locking?

Current evidence shows:

```text
F06
F08
F13
F14
```

form a highly stable representation cluster:

* occupancy ≈ 1.0
* entropy ≈ 0.0
* high dominant-pair consistency

However:

their physical fault mechanisms differ substantially.

Current unknown:

```text
why different physical faults
converge toward similar representation stability regimes
```

Current interpretation remains descriptive only.

No mechanism explanation exists.

Status:

```text
EL-1
```

---

# 3. F06 vs F14 Separation

## Q2 — Why does ruptures_A detect F06 but not F14?

Observed:

| Fault | occupancy | entropy | ruptures_A   |
| ----- | --------- | ------- | ------------ |
| F06   | 1.0       | 0.0     | detected     |
| F14   | 1.0       | 0.0     | not detected |

Additional observation:

F06 exhibits:

```text
large rolling variance surge
```

while F14 remains comparatively stable.

Current hypothesis:

```text
ruptures_A
may respond to joint distribution transition structure
rather than pair persistence itself
```

However:

current data cannot isolate:

* covariance effects
* transition sharpness
* transient duration
* spectral structure

This remains unresolved.

Status:

```text
EL-2
```

---

# 4. Pair Persistence vs top1_mass

## Q3 — Is pair persistence more fundamental than top1_mass amplitude?

Current evidence suggests:

```text
occupancy / entropy
```

may separate faults more cleanly than:

```text
top1_mass amplitude alone
```

Example:

F13 shows:

* very high occupancy
* very high consistency
* moderate top1 detection rate

This suggests:

```text
representation stability
and geometry amplitude
may be partially decoupled
```

Most striking example:

```text
F13:
occupancy ≈ 0.957
consistency ≈ 1.0
top1_mass detection rate ≈ 0.35
```

This combination has not been clearly observed in other faults.

The mechanism of this amplitude-stability decoupling
is currently unknown.

Current unknown:

* which metric is more fundamental
* whether amplitude is secondary projection
* whether persistence generalizes better

Status:

```text
EL-2
```

---

# 5. Diffuse Fault Structure

## Q4 — Do Diffuse faults contain hidden higher-order structure?

Diffuse faults currently cluster around:

```text
entropy ≈ 1.4–1.6
occupancy ≈ 0.3–0.4
```

Interpretation:

* weak pair preference exists
* representation is not fully random
* dominant pair varies across runs

Current unknown:

```text
whether Diffuse faults
contain additional stable substructure
```

Whether such substructure exists
remains unknown.

Current data does not support
or deny these possibilities.

Current top1-only representation
has not revealed stable subgroup separation.

Status:

```text
EL-1
```

---

# 6. Representation Consistency

## Q5 — Why do some faults maintain high occupancy but weaker consistency?

Example:

```text
F18
```

shows:

* relatively high occupancy
* weaker cross-run consistency

Interpretation:

```text
individual runs remain stable
but dominant pair identity drifts between runs
```

Current unknown:

* why this regime exists
* whether it represents boundary behavior
* whether consistency is independent of stability
* whether consistency predicts fault family

Status:

```text
EL-1
```

---

# 7. Entropy Scale

## Q6 — Is current entropy formulation sufficient?

Current entropy:

```text
H = -Σ p_i ln(p_i)
```

using:

```text
top1 dominant pair only
```

Current unknown:

```text
whether current top1-only occupancy/entropy
provides sufficient resolution
to differentiate within the Diffuse regime
```

Future possibilities include:

* alternative entropy definitions
* normalized entropy
* pair-transition entropy
* persistence spectrum metrics

Current evidence is insufficient
to determine whether such extensions
are necessary.

Status:

```text
EL-1
```

---

# 8. Representation Stability Generalization

## Q7 — Does representation stability persist outside XMEAS7–11?

Current experiments are heavily conditioned on:

```text
XMEAS7–XMEAS11
```

Current unknown:

* whether stable representation regimes generalize
* whether locking depends on current subspace
* whether alternative variable subsets produce different taxonomies

Important:

Current conclusions are NOT global-system claims.

Status:

```text
EL-1
```

---

# 9. Transfer Entropy Directionality

## Q8 — Does directional information asymmetry co-occur with representation locking?

Planned next-stage experiment:

```text
Transfer Entropy pilot
```

Current motivation:

```text
representation locking
may co-occur with directional asymmetry
```

Current unknown:

* whether TE asymmetry exists
* whether asymmetry is stable
* whether TE distinguishes F06 vs F14
* whether directionality predicts occupancy structure

Important boundary:

Current TE work will initially be treated as:

```text
directional statistical dependence estimation
```

NOT:

* physical causality
* control hierarchy
* forcing mechanism

Status:

```text
EL-1
```

---

# 10. Detector Family Ontology

## Q9 — Do detector disagreements define stable detector families?

Current detector separation:

| Detector            | Main sensitivity            |
| ------------------- | --------------------------- |
| T² / SPE            | global trajectory deviation |
| ruptures_A          | transition structure        |
| top1_mass           | geometry concentration      |
| occupancy / entropy | representation stability    |

Current unknown:

```text
whether detector disagreement
defines stable statistical detector families
```

rather than:

```text
multiple noisy measurements
of the same phenomenon
```

This question became central after:

* ruptures_B failure
* F06/F14 separation
* occupancy/consistency decomposition

Status:

```text
EL-2
```

---

# 11. Interpretation Boundary

Current open questions are exploratory.

This document intentionally avoids:

* causal claims
* attractor narratives
* physical ontology
* generalized complexity theory

Current project scope remains:

```text
representation-level detector family study
```

All future mechanism claims require:

```text
independent validation
```

before promotion beyond EL-2.

---

# 12. Snapshot Policy

These open questions belong to:

```text
Representation Stability Audit v1
```

Future work:

* TE-V1
* SUBSPACE-V1
* TOPOLOGY-V1

should reference this document
rather than overwrite it.
