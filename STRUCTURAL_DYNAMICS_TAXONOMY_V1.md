# Structural Dynamics Taxonomy v1

## Pair-Space Structural Dynamics on the Tennessee Eastman Process

---

# 1. Objective

This work explores whether industrial process faults can be characterized as distinct structural dynamics regimes in a low-dimensional pair-space representation.

The goal is not:

* supervised fault classification
* root-cause inference
* predictive maintenance benchmarking
* end-to-end industrial deployment

Instead, the goal is:

> to observe how multivariate correlation structure evolves over time, and whether industrial faults naturally form different attractor regimes in pair-space dynamics.

These limitations do not diminish the framework's value; they define its current scope.

The central hypothesis is:

```text
Industrial faults are not only changes in variable magnitude,
but also changes in relational structure dynamics.
```

---

# 2. Experimental Setup

## 2.1 Dataset

Experiments were conducted on the Tennessee Eastman Process (TEP) benchmark dataset.

The study used:

* fault-free testing runs
* fault runs F01–F20
* multiple simulation runs per fault
* batch-scale statistical evaluation

The TEP dataset is treated here as a controllable industrial dynamics sandbox rather than a deployment target.

---

## 2.2 Pair-Space Observation Window

A deliberately small observation window was used.

Selected variables:

* XMEAS7
* XMEAS8
* XMEAS9
* XMEAS10
* XMEAS11

This produces:

```text
5 variables
→ 10 pair relations
→ 10-state pair-space
```

This low-dimensional space is intentional.

The purpose is not full process reconstruction, but:

```text
to maximize structural interpretability.
```

The pair-space should therefore be interpreted as a selective structural observation window rather than a complete system state representation.

The advantage of this constrained representation is that dominant structural states remain physically interpretable at the pair level.

---

## 2.3 Structural Features

For each sliding window:

* differenced correlation matrices were computed
* pair contribution vectors were extracted
* dominant pair states were identified

From these sequences, the following structural dynamics metrics were derived:

| Metric             | Interpretation                              |
| ------------------ | ------------------------------------------- |
| occupancy          | time spent in dominant pair                 |
| switching          | top-pair transition frequency               |
| entropy            | distributional spread of pair contributions |
| transition entropy | unpredictability of pair transitions        |
| residence time     | duration inside dominant basin              |
| escape rate        | probability of leaving basin                |
| return probability | probability of re-entering basin            |

---

# 3. Structural Dynamics Hypothesis

The core hypothesis of this work is:

```text
Faults can alter the topology of relational dynamics,
not only the magnitude of process variables.
```

Under this view:

* normal operation corresponds to diffuse exploration of pair-space
* mild faults create metastable locking
* severe structural faults create deep attractor basins

This framing shifts the problem from:

```text
threshold detection
```

toward:

```text
structural dynamics observation.
```

---

# 4. Structural Taxonomy

Experiments consistently revealed three major structural regimes.

---

## 4.1 Diffuse Wandering

Representative faults:

* NORMAL
* F04
* F15
* F16

Characteristics:

* high transition entropy
* high edge count
* low occupancy
* short residence time
* high escape rate

Interpretation:

```text
The system continues to explore many relational configurations.
No dominant attractor forms.
```

Typical values:

```text
occupancy ≈ 0.20–0.25
mean residence ≈ 3
escape rate ≈ 0.30
typical edge count ≈ 35–40
```

---

## 4.2 Metastable Basin

Representative faults:

* F12
* F17
* F18

Characteristics:

* partial locking
* intermediate occupancy
* moderate residence time
* moderate escape rate
* nontrivial return probability

Interpretation:

```text
The system forms temporary structural basins,
but still escapes and re-enters dynamically.
```

Typical values:

```text
occupancy ≈ 0.40–0.75
mean residence ≈ 7–17
escape rate ≈ 0.04–0.13
typical edge count ≈ 2–4
```

---

## 4.3 Single-Edge Attractor

Representative faults:

* F06
* F08
* F13
* F14

Characteristics:

* near-single-edge topology
* extremely high occupancy
* long residence time
* near-zero escape rate
* high return probability

Interpretation:

```text
The system collapses into a dominant relational mode.
Pair-space exploration effectively disappears.
```

Typical values:

```text
occupancy ≈ 0.80–0.99
mean residence ≈ 40–60
escape rate ≈ 0.003–0.01
typical edge count = 1
```

This is quantitatively supported by:

```text
typical_edge_count = 1
across essentially all parameter settings
for F06/F08/F13/F14.
```

These regimes emerged without supervised labeling.

---

# 5. Attractor Subgraphs

Transition matrices were converted into attractor subgraphs using adaptive typical-edge selection.

Instead of using a fixed probability threshold, each fault retained only the smallest edge subset covering 80% transition mass.

This avoided threshold arbitrariness and produced topology-adaptive graphs.

Observed structures:

| Regime                | Typical topology        |
| --------------------- | ----------------------- |
| diffuse wandering     | dense transition graph  |
| metastable basin      | sparse multi-edge basin |
| single-edge attractor | near-self-loop collapse |

Particularly:

```text
F06/F08/F13/F14
collapsed into near-single-edge self-loop attractors.
```

---

# 6. Robustness Validation

A robustness sweep was performed across:

* W ∈ {80, 100, 150}
* S ∈ {5, 10, 20}
* typical_mass ∈ {0.75, 0.80, 0.90}

Total:

```text
27 parameter combinations
```

Results:

| Fault Type          | Consistency |
| ------------------- | ----------- |
| F06/F08/F13/F14     | ≈ 1.00      |
| F18 (boundary case) | ≈ 0.74      |
| F17                 | ≈ 0.78      |
| F12                 | ≈ 0.52      |
| NORMAL/F04/F15/F16  | ≈ 0.89      |

Interpretation:

```text
Strong attractors were highly robust.
Diffuse wandering was also robust.
Metastable basins were partially parameter-sensitive.
F18 behaved as a boundary case between metastable and strong-locking regimes.
```

This suggests the taxonomy is not purely a parameter artifact.

---

# 7. Basin Escape Dynamics

The strongest evidence for genuine basin structure came from temporal escape dynamics.

Three quantities were especially informative:

* residence time
* escape rate
* return probability

Results showed:

```text
single-edge attractors
not only had high occupancy,
but also deep temporal persistence.
```

Representative examples:

| Fault  | occupancy | mean residence | escape |
| ------ | --------- | -------------- | ------ |
| F14    | 0.880     | 62.6           | 0.003  |
| F13    | 0.810     | 38.7           | 0.012  |
| NORMAL | 0.238     | 3.1            | 0.316  |

This supports the interpretation that some faults generate genuine dynamic basins rather than static statistical concentration.

---

# 8. Interpretation Boundary

Several important limitations must be stated clearly.

---

## 8.1 Small Pair-Space

The current system uses:

```text
5 variables → 10 pair states
```

This low-dimensionality improves interpretability but may also produce artificially “hard” attractors.

The current attractor geometry should therefore be interpreted as:

```text
a low-dimensional structural projection,
not a full industrial state manifold.
```

---

## 8.2 No Causal Inference

The framework observes:

```text
structural coupling dynamics
```

but does not establish:

```text
causal directionality.
```

Observed pair locking should not be interpreted as physical causation without additional engineering analysis.

---

## 8.3 TEP is a Simulator

The TEP benchmark lacks many realities of operational industrial systems:

* maintenance interventions
* sensor degradation
* operating mode switching
* startup/shutdown transients
* human operator actions

Real deployment validation remains future work.

---

# 9. Future Applications

The long-term motivation of this work is marine engine-room structural monitoring.

Potential target systems include:

* cooling loops
* scavenge air systems
* turbocharger dynamics
* fuel injection systems
* lube oil circulation systems

The intended role is not alarm replacement.

Instead:

```text
alarm-preceding structural monitoring
```

The hypothesis is:

```text
before conventional alarm thresholds are crossed,
pair-space structure may already enter abnormal basins.
```

This is especially relevant for:

* gradual cooling degradation
* air cooler fouling
* turbocharger efficiency loss
* combustion imbalance
* control-loop instability

Future validation must therefore occur on real marine subsystem telemetry.

---

# 10. Conclusion

This work demonstrates that industrial process faults can produce distinct pair-space structural dynamics regimes.

Across TEP experiments:

* diffuse wandering
* metastable basins
* single-edge attractors

emerged naturally from unsupervised transition dynamics.

The results suggest that:

```text
industrial faults may be interpretable
not only as variable deviations,
but also as attractor transitions
inside relational structure space.
```

The current work should be viewed as:

```text
a structural dynamics observation framework,
not yet an industrial deployment system.
```

The next major milestone is validation on real marine engineering telemetry.
