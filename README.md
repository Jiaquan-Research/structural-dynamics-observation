# Structural Dynamics Observation Framework
## for Industrial Telemetry Systems

Research-stage framework for investigating relationship-dynamics anomalies in industrial systems.

## Core Hypothesis

The central working hypothesis is that some faults may first appear as changes in inter-variable relationship dynamics, before conventional alarm thresholds activate.

Current experiments use the Tennessee Eastman Process (TEP) benchmark as a controlled multivariate telemetry environment. The repository should therefore be read as a structural-dynamics research investigation, not as an industrial deployment package.

## Current Research Status

Current stage:

* hypothesis validation
* simulated telemetry only
* no industrial deployment claims

Current observations:

* diffuse wandering regime
* metastable basin regime
* single-edge attractor regime

## Repository Structure

* `scripts/`: experiment, analysis, visualization, and robustness scripts
* `docs/`: methodology notes, reports, and working documents
* `outputs/`: generated figures, CSV summaries, taxonomy plots, and trajectory artifacts
* `data/`: raw and processed datasets

## Key Documents

* [RESEARCH_AUDIT_PACKAGE_V1.md](RESEARCH_AUDIT_PACKAGE_V1.md)
  Defines the adversarial review boundary, open risks, and audit questions.
* [STRUCTURAL_DYNAMICS_TAXONOMY_V1.md](STRUCTURAL_DYNAMICS_TAXONOMY_V1.md)
  Summarizes the current structural-regime interpretation from TEP experiments.
* [MARINE_MAPPING_V1.md](MARINE_MAPPING_V1.md)
  Maps the current TEP-based framework toward future marine-engineering validation targets.

## Experimental Pipeline

```text
TEP telemetry
→ differencing
→ pair correlations
→ contribution dynamics
→ transition structure
→ attractor analysis
```

## Current Limitations

* TEP simulator only
* 5-variable pair-space
* discretized top-pair dynamics
* no marine telemetry validation
* no predictive maintenance claims

## Audit Orientation

This repository is intended to be inspectable, criticizable, and falsifiable.

Adversarial review is encouraged, especially around:

* subsystem selection bias
* discretization artifacts
* simulator-specific structure
* parameter sensitivity
* transferability beyond TEP

## Future Direction

* marine telemetry validation
* simulator comparison
* robustness expansion
* continuous-state representations
