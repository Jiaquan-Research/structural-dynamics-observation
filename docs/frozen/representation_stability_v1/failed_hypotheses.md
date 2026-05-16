# Failed Hypotheses Archive

This archive records downgraded or rejected hypotheses.

## H1: global attractor hypothesis

**Hypothesis**

Fault trajectories converge toward a shared system-wide temporal geometry attractor.

**Why it seemed plausible**

Early trajectory visualizations suggested repeated transition structure across several faults.

**What disproved it**

Random subset audit showed strong dependence on variable subset selection. The apparent structure did not survive subset perturbation as a system-wide invariant.

**Current downgraded interpretation**

Fault-conditioned subspace geometry can appear in selected representations. There is no current evidence for a global attractor.

## H2: rolling correlation changepoint ≈ geometry concentration

**Hypothesis**

Persistent geometry concentration is equivalent to changepoints in rolling XMEAS7-XMEAS11 correlation.

**Why it seemed plausible**

top1_mass is built from correlation-derived pair contributions, so a rolling-correlation changepoint baseline appeared like a direct competing explanation.

**What disproved it**

ruptures_B failure. The rolling-correlation changepoint detector had low coverage and did not reproduce top1_mass behavior.

**Current downgraded interpretation**

Geometry concentration is not reducible to simple rolling-correlation changepoints. Pair persistence and allocation stability are distinct representation features.

## H3: F13 bimodal occupancy hypothesis

**Hypothesis**

F13 may contain hidden high-stability and low-stability run submodes.

**Why it seemed plausible**

F13 had high representation stability in the 20-run audit but comparatively lower top1_mass detection rate over 500 runs.

**What disproved it**

500-run occupancy audit showed mean occupancy around 0.956, p05 around 0.85, and no runs with occupancy below 0.5.

**Current downgraded interpretation**

F13 is globally high-stability in this representation. The amplitude/detection-rate gap is not explained by a simple high/low occupancy bimodality.

## H4: raising threshold removes FP floor

**Hypothesis**

Increasing top1_mass threshold should eliminate false positives.

**Why it seemed plausible**

If false positives were only marginal threshold crossings, higher thresholds should remove them.

**What disproved it**

Operating curve sweep showed a persistent false-positive floor. NORMAL data contains naturally high representation concentration windows.

**Current downgraded interpretation**

The false-positive floor is a background representation activity property under this subspace and metric, not only a threshold artifact.
