# Marine Structural Monitoring Mapping v1

## Pair-Space Structural Dynamics for Marine Engine Room Systems

---

# 1. Objective

This project explores whether marine engine-room systems exhibit detectable structural dynamics changes before conventional alarm thresholds are crossed.

The core idea is:

```text id="qk9m31"
industrial systems are not only collections of variables,
but also networks of dynamic relationships.
```

Traditional alarm systems mainly monitor:

* single-variable thresholds
* fixed safety limits
* direct parameter excursions

This project instead studies:

```text id="8vr1q7"
whether the relational structure
between variables
changes earlier than alarm activation.
```

The intended role is not alarm replacement.

Instead:

```text id="i4q9z2"
alarm-preceding structural monitoring
```

---

# 2. Motivation from Marine Engineering

In real engine-room operation, many failures develop gradually:

* air cooler fouling
* turbocharger efficiency degradation
* injector imbalance
* cooling performance decline
* lubrication deterioration

In many cases:

```text id="u9m3lp"
individual parameters may remain inside nominal limits,
while the coupling structure between subsystems
has already changed.
```

Example:

* exhaust temperature may remain below alarm level
* scavenge pressure may remain acceptable
* turbocharger rpm may still appear normal

but:

```text id="1x7lrm"
the dynamic relationship
between these variables
may already become abnormal.
```

This project investigates whether such structural transitions are observable.

---

# 3. Current Experimental Basis

Current experiments were conducted on the Tennessee Eastman Process (TEP) benchmark.

The experiments revealed several distinct structural dynamics regimes:

| Regime | Characteristics |
| --- | --- |
| diffuse wandering | weak structural locking |
| metastable basin | partial structural concentration |
| single-edge attractor | strong structural locking |

The key observation is:

```text id="x7m5dr"
faults may alter the pattern
of relationship dynamics,
not only variable magnitude.
```

The current framework uses:

* pair-space occupancy
* transition entropy
* residence time
* escape rate
* attractor subgraphs

to characterize structural behavior.

The TEP results are treated as:

```text id="l8q4yt"
proof-of-mechanism,
not industrial validation.
```

---

# 4. Proposed Marine Validation Target

The preferred first validation target is:

# Scavenge Air + Turbocharger System

Reason:

* strong subsystem coupling
* rich dynamic behavior
* gradual degradation patterns
* physically interpretable variable relationships

---

# 5. Candidate Variables

Initial variable candidates:

| Variable | Physical Meaning |
| --- | --- |
| main engine load | operating condition |
| engine rpm | propulsion state |
| scavenge air pressure | air supply condition |
| scavenge air temperature | thermal air state |
| turbocharger rpm | compressor efficiency |
| mean exhaust gas temperature | combustion output |
| cylinder exhaust temperature deviation | cylinder imbalance |
| air cooler seawater inlet/outlet temperature | cooling efficiency |
| air cooler differential pressure | fouling indicator |

Not all variables are required initially.

A small interpretable subsystem window is preferred for early-stage experiments.

---

# 6. Pair-Space Interpretation

The framework does not model the entire engine-room state.

Instead:

```text id="q1k8mn"
it constructs a selective structural observation window.
```

Examples of interpretable pair relationships:

| Pair | Possible Interpretation |
| --- | --- |
| TC rpm ↔ scavenge pressure | compressor effectiveness |
| load ↔ exhaust temperature | combustion thermal response |
| scavenge temperature ↔ exhaust deviation | air-combustion coupling |
| air cooler ΔT ↔ scavenge pressure | cooling-airflow interaction |

The purpose is to observe whether certain relationships become structurally dominant or dynamically trapped.

---

# 7. Proposed Validation Questions

The first-stage validation questions are intentionally simple.

---

## Q1

Can structural indicators change before conventional alarm activation?

Example:

```text id="4n2wlp"
Does occupancy / escape rate shift
before high-temperature alarms appear?
```

TEP experiments suggest that:

```text id="7q4mka"
strong-locking fault types
may produce detectable structural shifts
before conventional alarm thresholds.
```

---

## Q2

Do gradual degradations produce metastable structural basins?

Example:

* air cooler fouling
* turbocharger efficiency loss

---

## Q3

Do severe abnormalities produce strong attractor locking?

Example:

* major combustion imbalance
* severe airflow degradation

---

# 8. Data Requirements

Preferred data sources:

* AMS trend export
* K-Chief trend logs
* simulator telemetry
* teaching engine-room simulator data

Desired characteristics:

| Requirement | Importance |
| --- | --- |
| continuous time series | critical |
| multi-variable synchronization | critical |
| sampling interval consistency | important |
| known operating modes | important |
| known fault injection timing | highly valuable |
| repeated runs | highly valuable |

Simulator environments are especially attractive because:

```text id="z2q7wm"
fault injection timing can be controlled,
and experiments can be repeated consistently.
```

---

# 9. Current Scope Boundary

This framework currently does NOT provide:

* fault diagnosis
* causal inference
* maintenance recommendation
* certified industrial monitoring

The current stage is:

```text id="v9m1ra"
structural dynamics observation research.
```

The main objective is to determine whether marine systems exhibit observable attractor-like structural transitions.

---

# 10. Proposed Next Step

A realistic first-stage validation setup could be:

1. Select one subsystem
2. Export synchronized trend data
3. Build pair-space trajectories
4. Compare:

   * normal operation
   * gradual degradation
   * abnormal conditions
5. Observe:

   * occupancy
   * transition entropy
   * escape dynamics
   * attractor formation

The initial goal is not deployment.

The initial goal is:

```text id="8w4qmk"
to determine whether marine subsystem telemetry
contains measurable structural dynamics signatures.
```
