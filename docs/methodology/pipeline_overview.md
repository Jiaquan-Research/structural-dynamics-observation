# Pipeline Overview

## Current TEP Pipeline

The current workflow starts from multivariate TEP telemetry, selects a small 5-variable subsystem window, and transforms it into a pair-space structural sequence.

Core steps:

1. Select a 5-variable subsystem window.
2. Apply first-order differencing:
   `Δx(t) = x(t) - x(t-1)`.
3. Compute rolling pairwise correlations on the differenced series.
4. Convert the correlation window into pair-space structural features.
5. Score deviations with Mahalanobis distance.
6. Decompose pair contributions and extract the top-pair sequence.
7. Build transition matrices, stationary distributions, and escape / residence summaries.

## Why Differencing

Differencing is used to reduce false structural signals caused by shared low-frequency drift and common operating trends. The intent is to emphasize dynamic coupling changes rather than slow co-movement.

## Pair-Space Concept

The framework does not attempt to reconstruct the full industrial state manifold. Instead, it uses a small, interpretable pair-space as a selective observation window over relational structure.

For a 5-variable subsystem:

* 5 variables
* 10 pair relations
* 10-state pair-space

## Attractor Taxonomy Summary

Current experiments suggest three broad regimes:

* Diffuse wandering: high transition entropy, low occupancy, short residence time.
* Metastable basin: partial locking, intermediate residence and escape behavior.
* Single-edge attractor: high occupancy, long residence, near-zero escape, near-self-loop collapse.
