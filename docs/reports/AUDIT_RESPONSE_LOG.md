# Audit Response Log

## 1. Purpose

This document records:

- external adversarial review feedback
- experimental responses
- current validation status
- unresolved methodological risks

This is not a rebuttal document.
It is an evolving falsification and validation ledger.

The intent is to preserve an inspectable trail of:

- criticism
- experiment
- result
- interpretation
- remaining uncertainty

Future validation work should extend this document rather than replace it.

---

## 2. External Review Summary

### 2.1 Gemini Audit Summary

The Gemini-style adversarial review raised the following main criticisms:

- overlap-induced persistence:
  high sliding-window overlap may inflate residence, escape, and persistence structure
- argmax discretization artifacts:
  top-pair winner-take-all compression may create unstable symbolic switching from near-ties
- Markov assumption violation:
  pooled trajectories after fault onset may not justify a time-homogeneous stationary chain
- topology hallucination risk:
  attractor subgraphs may be artifacts of thresholded graph compression rather than recovered process topology
- metastability may be boundary flipping:
  intermediate regimes may reflect discretization noise rather than genuine dynamical basins
- need for null hypothesis tests:
  surrogate or null data are required to test whether similar taxonomy appears without true cross-variable structure

These criticisms are methodologically relevant and remain active design constraints on the project.

### 2.2 ChatGPT Deep Review Summary

The strongest criticism from the deeper review was that the symbolic state variable is not a directly measured structural state. The state sequence is downstream of:

- diagonal-only per-pair attribution
- hard top-pair discretization
- pooled transition counting

That means:

- switching
- entropy
- transition structure
- stationary occupancy
- basin depth

all inherit potential attribution and discretization error.

The strongest support from the same review was narrower. It acknowledged that the repository is unusually auditable:

- explicit pipeline
- named variables
- repeatable runs
- explicit robustness sweeps
- self-stated scope limitations

Suggested validation directions were:

- non-overlap tests
- surrogate/null tests
- continuous or soft-state ablations
- variable-set expansion
- comparison against real alarm logic
- comparison against additional simulators or real telemetry

---

## 3. Validation Response Matrix

| Criticism | Validation Experiment | Current Status | Result | Remaining Risk |
| --- | --- | --- | --- | --- |
| Overlap-induced persistence | A1 Non-overlap Validation | Completed | Strong attractors survived under `S=W`; residence-time depth weakened substantially. | Temporal persistence metrics remain overlap-sensitive. |
| Metastable basins may be discretization artifacts | A1 Non-overlap Validation | Partially addressed | `F12/F17` survived weakly; residence and edge stability degraded. | Still vulnerable to discretization and boundary-flipping critique. |
| Strong attractors may be reproduced by simple stochastic null processes | A2 Null / Surrogate Validation | Completed | `WHITE_NOISE` and `CORRELATED_GAUSSIAN` remained diffuse wandering and did not reproduce `F13`-like attractor structure. | Richer surrogate processes remain untested. |
| Strong attractor structure may be a pure argmax / top-pair artifact | A3 Soft-State / Continuous Representation Validation | Completed | `F13` remained highly concentrated under a continuous soft-state representation; `NORMAL` remained diffuse; `F12` stayed intermediate. | Simulator-specific locking, richer surrogates, and limited pair-space remain unresolved. |
| Topology may be threshold-compression artifact | Existing robustness sweep over `typical_mass` | Partially addressed | Strong attractor class remained stable across `{0.75, 0.80, 0.90}`. | Compression still depends on a manually chosen cumulative-mass rule. |
| Small pair-space may exaggerate attractor hardness | A4 Variable Expansion | Completed | `F13` remained more concentrated than `NORMAL`, but the original low-dimensional strong-concentration picture weakened materially under 8- and 12-variable expansion. | Dimensional stability remains unresolved; topology is not scale-invariant over the tested range. |
| “Earlier than alarms” claim may be unsupported | Pending real alarm comparator | Open | Not yet tested against plant alarm logic. | Current comparison is against a detector baseline, not actual operational alarm rules. |

---

## 4. A1 Non-overlap Validation (Detailed)

### 4.1 Objective

A1 tested whether attractor structure survives after removing sliding-window overlap.

Original setting:

- `W = 100`
- `S = 10`

Validation sweep:

- `S ∈ {10, 50, 100}`

The non-overlap case is:

- `S = W = 100`

All other structural logic was held fixed:

- differencing
- pair contributions
- top-pair logic
- transition matrix construction
- stationary estimation
- taxonomy classification

The purpose was not to preserve prior conclusions, but to test whether previously observed structure collapses when overlap inertia is removed.

### 4.2 Key Results

The strongest-attractor set survived:

- `F06`
- `F08`
- `F13`
- `F14`

For these faults:

- taxonomy class remained `single_edge_attractor`
- occupancy remained near `1.0`
- `edge_count` remained approximately `1`

However, mean residence time decreased sharply:

- `F13: 40.2 -> 5.9`
- `F14: 65.9 -> 7.0`
- `F06: 55.5 -> 7.0`

Additional observations:

- `NORMAL` and `F04` remained diffuse wandering
- `F12` and `F17` remained metastable by class label
- `F18` strengthened toward attractor-like behavior under reduced overlap

### 4.3 Interpretation

This experiment weakens the strongest version of the pure overlap-artifact hypothesis.

Reason:

- the strongest attractors did not disappear under non-overlapping windows
- occupancy did not collapse
- edge-count concentration remained

However, the experiment also shows that time-based metrics were substantially amplified by overlap smoothing.

In particular:

- residence time
- escape dynamics
- inferred basin depth

all became much shallower once overlap was removed.

So the current interpretation should be split into two parts:

- structural locking appears at least partly real in the strongest TEP cases
- temporal depth and basin persistence were materially inflated by overlap

### 4.4 Metastable Basin Status

The metastable cases did not collapse completely, but they weakened materially.

Observed:

- `F12` and `F17` remained in the metastable class
- occupancy decreased or remained only moderate
- `edge_count` increased
- residence time dropped sharply

Examples:

- `F12 mean_residence_time: 9.9 -> 2.4`
- `F17 mean_residence_time: 6.8 -> 2.0`

Interpretation:

- the metastable label survives in a categorical sense
- the basin depth implied by the original overlapping pipeline does not survive intact

Current evidence for metastable basins should therefore be treated as provisional, not established.

---

## 5. A2 Null / Surrogate Validation (Detailed)

### 5.1 Objective

A2 tested whether strong attractor regimes can be reproduced by simple stochastic null processes.

The target failure mode was:

- apparent attractor structure emerging from random or surrogate data
- without real industrial control structure or fault dynamics

### 5.2 Null Sources Tested

Two null sources were evaluated:

- `WHITE_NOISE`
- `CORRELATED_GAUSSIAN`

Definitions:

- `WHITE_NOISE` = independent Gaussian noise
- `CORRELATED_GAUSSIAN` = covariance-matched Gaussian surrogate without temporal control structure

For the correlated Gaussian source, the covariance matrix was matched to the selected normal TEP variables, but no temporal dynamics, control logic, or fault onset structure were included.

### 5.3 Experimental Condition

A2 was run under the non-overlap validation setting:

- `W = 100`
- `S = 100`

The same pipeline as A1 was used for:

- differencing
- pair correlations
- pair contributions
- top-pair state extraction
- transition matrix construction
- stationary analysis
- taxonomy classification

### 5.4 Core Results

| Source | taxonomy_class | occupancy | edge_count | mean_residence_time |
| --- | --- | ---: | ---: | ---: |
| NORMAL | diffuse_wandering | 0.214 | 51 | 1.207 |
| F13 | single_edge_attractor | 0.968 | 1 | 5.860 |
| WHITE_NOISE | diffuse_wandering | 0.112 | 71 | 1.116 |
| CORRELATED_GAUSSIAN | diffuse_wandering | 0.129 | 63 | 1.145 |

### 5.5 Interpretation

Simple stochastic null processes did not reproduce `F13`-like attractor structure.

This weakens the hypothesis that the observed attractor is purely caused by random switching artifacts.

However, this does not yet eliminate:

- control-loop-induced locking
- autocorrelation-preserving surrogates
- phase-randomized surrogates
- argmax discretization artifacts

The current evidence suggests that strong attractor regimes are unlikely to emerge from simple stochastic null structure alone, but further validation against richer surrogate processes remains necessary.

Generated outputs:

- `outputs/csv/null_surrogate_validation.csv`
- `outputs/taxonomy/null_surrogate_taxonomy.png`
- `outputs/taxonomy/null_surrogate_metrics.png`

---

## 6. A3 Soft-State / Continuous Representation Validation

### 6.1 Objective

A3 directly tested the strongest discretization critique:
whether observed attractor structure is merely an argmax / top-pair artifact.

The question was whether pair-space concentration remains visible after removing hard discrete state selection.

### 6.2 Method

The A3 experiment used the same upstream structural pipeline as earlier validations:

- first-order differencing
- rolling pairwise correlations
- pair contribution computation

The validation was run in the non-overlap setting:

- `W = 100`
- `S = 100`

Instead of selecting:

- `top1 = argmax(pair_contribution)`

the experiment computed, for each window:

- a softmax-normalized continuous probability distribution over the 10-dimensional pair-space

with:

- `T = 1.0`

This produced a continuous soft-state vector for every window, without hard argmax state selection.

Metrics used:

- `mean_top1_mass`
- `mean_entropy`
- `concentration_ratio`
- `effective_pair_count = exp(entropy)`
- `temporal_stability` via cosine similarity between consecutive soft vectors

### 6.3 Data Sources

The A3 comparison used:

- `NORMAL`
- `F13`
- `F12`

with:

- `n_runs = 200`

Interpretive roles:

- `NORMAL` = diffuse reference
- `F13` = strongest attractor reference
- `F12` = metastable boundary case

### 6.4 Key Results

`NORMAL`

- `mean_top1_mass = 0.126750`
- `mean_entropy = 0.996295`
- `effective_pair_count = 9.916283`
- `temporal_stability = 0.983363`

`F13`

- `mean_top1_mass = 0.811523`
- `mean_entropy = 0.266106`
- `effective_pair_count = 2.893944`
- `temporal_stability = 0.903061`

`F12`

- `mean_top1_mass = 0.314233`
- `mean_entropy = 0.840027`
- `effective_pair_count = 8.063924`
- `temporal_stability = 0.888987`

### 6.5 Interpretation

`F13` remains highly concentrated even without hard-state discretization.

`NORMAL` remains diffuse under the same representation.

`F12` occupies an intermediate region between the two.

Therefore, the strongest attractor structure does not collapse under continuous representation.

However, several cautions remain necessary:

- metastable separation becomes weaker under soft-state analysis
- temporal stability is not a direct attractor-strength metric
- soft-state concentration does not prove physical causality

The A3 result weakens the strongest form of the pure argmax-artifact critique, but it does not eliminate concerns regarding:

- simulator-specific locking
- closed-loop controller dynamics
- richer surrogate explanations
- limited pair-space dimensionality

Generated outputs:

- `outputs/csv/soft_state_validation.csv`
- `outputs/taxonomy/soft_state_entropy.png`
- `outputs/taxonomy/soft_state_concentration.png`
- `outputs/taxonomy/soft_state_temporal_stability.png`

---

## 7. A4 Variable Expansion Validation

### 7.1 Objective

A4 tested whether the low-dimensional concentration picture survives pair-space expansion.

The purpose was to evaluate dimensional stability and address the critique that the observed topology may collapse once the pair-space grows beyond the original 5-variable / 10-pair observation window.

### 7.2 Experimental Setup

The A4 experiment compared three explicit variable configurations:

- `V5`: 5 variables
- `V8`: 8 variables
- `V12`: 12 variables

Corresponding pair counts:

- `10`
- `28`
- `66`

The experiment used:

- soft-state continuous representation
- non-overlap setting retained: `W = 100`, `S = 100`

The expanded variable windows were manually selected from coherent reactor / separator / stripper neighborhoods.

They were not random subsets.

### 7.3 Key Results

For `F13`:

- `top1_mass: 0.8115 → 0.4781 → 0.4166`
- `entropy: 0.266 → 0.430 → 0.459`
- `effective_pair_count: 2.89 → 7.84 → 18.11`

For `NORMAL`:

- entropy remained approximately `0.996`
- effective pair count tracked total pair count closely

For `F12`:

- entropy increased
- concentration weakened further under expansion

### 7.4 Interpretation

A4 weakened the framework relative to the original low-dimensional interpretation.

The strongest single-edge attractor picture is not dimension-stable.

However, `F13` still remains substantially more concentrated than `NORMAL` even at `V12`.

The framework therefore appears to capture:

- distributed structural concentration

rather than:

- single-edge locking

This is a more conservative interpretation of the current evidence.

### 7.5 Current Status After A4

Current evidence supports:

- low-dimensional structural concentration
- persistence of non-random concentration under expansion
- separation from diffuse null behavior

Current evidence does not support:

- stable single-edge attractors across variable scales
- topology invariance under dimensional expansion
- finalized industrial taxonomy claims

---

## 8. Current Confidence Levels

| Claim | Confidence |
| --- | --- |
| Faults alter relationship dynamics in the current TEP representation | strong |
| Strong attractor regimes exist in TEP under the current pair-space pipeline | moderate |
| Residence dynamics are physically meaningful rather than estimator-memory amplified | low-moderate |
| Metastable basins are robust | low |
| The framework generalizes to marine systems | unknown |

---

## 9. Next Validation Plan

Current validation sequence:

- `A1` = completed
- `A2` = completed
- `A3` = completed
- `A4` = completed

### A5 — Marine Telemetry Mapping

Goal:

- determine whether analogous relationship regimes exist in real marine engine systems
- test whether any pre-alarm structural shift is observable in real telemetry rather than simulator traces

---

## 10. Current Overall Status

Current evidence suggests:

- the strongest attractor regimes are not solely caused by overlap
- the strongest attractor regimes are unlikely to emerge from simple stochastic null structure alone
- the strongest attractor class currently survives:
  - overlap removal
  - null surrogate testing
  - continuous representation testing
- the strongest class does not remain topologically invariant under variable expansion
- but the framework remains vulnerable to:
  - discretization artifacts in weaker regimes
  - simulator-specific dynamics
  - small pair-space limitations
  - richer surrogate-process alternatives
  - dimensional instability under pair-space scaling

The strongest current statement that the project supports is:

- some TEP faults, under the current representation, produce stable and concentrated pair-space structure that survives removal of window overlap, is not reproduced by simple stochastic null sources, and remains visible under a continuous soft-state representation, but weakens materially under variable expansion

The project does not yet support stronger statements such as:

- industrial faults generally form attractor basins
- pre-alarm structural monitoring has been validated operationally
- the taxonomy is independent of representation choice
- the observed concentration has been causally tied to physical fault mechanisms

Therefore, the framework should currently be interpreted as an exploratory structural-observation methodology, not a validated industrial diagnostic system.
