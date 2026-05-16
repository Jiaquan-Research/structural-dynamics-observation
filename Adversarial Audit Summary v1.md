# Adversarial Audit of

## Executive Assessment

Audit scope follows the uploaded adversarial brief.
The repository itself describes the work as research-stage, simulated-only, TEP-only, limited to a 5-variable pair-space, and still missing simulator comparison and continuous-state representations. On that record, the current evidence is hypothesis-generating, not evidence-supporting: it shows that one chosen TEP projection can be made to produce stable symbolic trajectories, but it does not establish that real faults create attractor-like relational basins or that such basins precede conventional alarms.

The central methodological defect is that the reported “state” is not a measured structural state. The anomaly score (D^2) is computed with the full inverse covariance, but per-pair “contributions” are computed only from squared centered features times the diagonal of (\Sigma^{-1}), which discards all off-diagonal cross-terms. The top-pair state is then defined by argmax over that heuristic vector. Every downstream object—switching, entropy, transition matrix, stationary occupancy, basin depth, and attractor subgraph—is therefore downstream of a non-conservative attribution rule plus a hard winner-take-all discretizer.

The implementation also does not test “earlier than conventional alarm thresholds.” It compares a relation-score threshold based on baseline (D^2) mean + 2σ against a single-variable detector defined as max window z-score > 3 for (K_{\text{persist}}) windows. That is a comparison against another detector, not against actual alarm logic. The repo’s headline framing reaches beyond what the implemented benchmark actually measures.

## Strongest Contributions

The most useful contribution, stripped of interpretation, is auditability. The pipeline is explicit, the selected variables are named, the all-fault stationary scan iterates faults 0–20 using up to 500 runs, and the robustness sweep exposes exactly which parameters were varied and which faults were included. That makes the framework unusually easy to attack. It is not self-contained, though: the README advertises outputs/ and data/, while the visible repository tree only exposes docs/, scripts/, and markdown files, and the scripts explicitly require an external TEP CSV download.

A second real contribution is negative rather than positive: the repo already contains enough internal evidence to bound its own claims. The taxonomy document explicitly admits that the 5-variable, 10-state pair-space may create artificially hard attractors, that TEP lacks many realities of operational systems, and that marine transfer remains future work. Those admissions are methodologically more credible than the stronger causal language that sometimes appears elsewhere in the write-up.

## Most Serious Methodological Risks

Discretization artifact risk is the dominant failure mode. The code performs continuous differenced correlations, maps them to heuristic per-pair deviations, then collapses each window to a single winning pair by argmax. Even the “dominance” statistic is another count-on-top-of-counts reduction over recent top-k winners. When pair contributions are nearly equal, argmax is maximally unstable: tiny noise, covariance-estimation error, or control-action variability can flip the winner and manufacture switching, escape, and entropy structure out of near-ties. The repo itself lists continuous-state representations as future work, so there is currently no evidence that any regime survives removal of this discretizer.

The Markov interpretation is weak. Default windows use (W=100) and (S=10), so adjacent feature vectors share 90% of their raw samples; the robustness sweep stays in a heavily overlapping regime from 75% overlap ((80,20)) to about 96.7% overlap ((150,5)). On top of that, switching and dominance are smoothed over (n_{\text{history}}=10). Residence time, escape rate, and transition persistence can therefore arise from estimator memory before any genuine process-memory structure is demonstrated. This is not a minor caveat: process-monitoring literature treats serial correlation as a first-order confound, and non-overlapping moving windows are specifically used to reduce dependence induced by conventional windowing.

Stationary distributions are imposed more than justified. The chain is built from pooled post-filter transitions after sample > 200, row-normalized, zero rows are replaced by a uniform distribution, and a single stationary vector is extracted from the eigenvector nearest eigenvalue 1 after taking absolute values. That procedure assumes a time-homogeneous, interpretable long-run chain even though the underlying process is explicitly fault-onset driven and therefore nonstationary. In reducible or nearly reducible graphs—the exact cases being called “attractors”—a unique initialization-free stationary distribution is not guaranteed. The repo also computes transition_entropy by flattening all nonzero entries of the row-normalized matrix, so rarely visited rows count as much as dominant rows, and the taxonomy scan’s diagonal_mass is just trace(P)/N, not a visitation-weighted persistence measure.

TEP simulator bias is substantial. The chosen variables are reactor pressure, reactor level, reactor temperature, purge rate, and separator temperature: one tightly coupled reactor–separator slice of the benchmark. TEP literature treats reactor pressure and temperature as critical variables and documents regulatory structures in which reactor pressure, reactor level, reactor temperature, purge flow, and separator temperature are tightly coupled through control loops. The strong-locking exemplars are also not benchmark-neutral: F06, F08, F13, and F14 correspond to large step, random-variation, slow-drift, and sticking disturbances, while TEP literature repeatedly highlights other cases such as faults 3, 9, and 15 as difficult incipient faults. That is consistent with a subsystem chosen to make concentration visible on favorable fault classes.

The pair-space is too small to support strong geometric language. Five variables produce only ten pair states, and the taxonomy document itself concedes that this low-dimensional projection may create artificially hard attractors. In such a small state space, a “single-edge attractor” can be simple combinatorial collapse under a hard winner-take-all map. No variable-window expansion is tested; the only reported sweeps vary window size, stride, and mass threshold. Robustness to parameters is not robustness to dimensionality.

Statistical robustness is narrower than the narrative suggests. A limited claim is justified: F06/F08/F13/F14 appear stable inside the tested grid, and diffuse cases are reasonably stable. The metastable class is not comparably secure: the repo’s own table reports about 0.52 consistency for F12 and only about 0.74–0.78 for F18/F17. That is not enough to treat metastability as a validated structural regime. It is enough to say there may be parameter-sensitive intermediate behavior under this representation. Nothing stronger is earned.

## Likely Artifact Sources

The first likely artifact source is misattributed pair importance. Because the winning pair ignores Mahalanobis cross-terms, the top-pair label need not correspond to the pair that actually contributes most to the anomaly score. In correlated feature spaces, omitted cross-terms can dominate the quadratic form, so the symbolic state sequence can rotate among pairs that are merely recipients of diagonal weighting rather than carriers of the anomaly. If the state variable is wrong, the topology built on it is wrong in a structural way.

The second likely artifact source is noise amplification in a closed-loop system. TEP measurements are sampled every three minutes and include Gaussian measurement noise; the repository then differences each window before computing pairwise correlations. Differencing can remove level drift, but it also suppresses slow accumulation and amplifies high-frequency noise and controller action. In a feedback-dominated subsystem, that makes it entirely plausible that the symbolic regime is tracking control chatter or noise-shaping rather than incipient structural change.

The third likely artifact source is post hoc topology compression. Attractor subgraphs are not recovered from a principled graph model; they are the minimal edge subset required to cover a chosen mass target, default 0.80. The docs claim this “avoided threshold arbitrariness,” but 80% cumulative mass is itself a threshold, and the robustness sweep explicitly varies that threshold. The regime classifier then labels faults by hand using edge-count and self-loop rules such as edge_count <= 2 and self_loop_mass >= 0.9, while the taxonomy document says the regimes “emerged without supervised labeling.” That is not unsupervised discovery; it is post hoc thresholding on summary statistics.

The presentation layer introduces a fourth over-interpretation channel. One visualization script explicitly describes itself as a “small handcrafted embedding” and hard-codes structural metrics for a selected fault subset. That is acceptable as an illustration, but it is unusable as evidence that the fault manifold itself was discovered geometrically from data.

A fifth likely artifact source is pooled-run mixture masquerading as metastability. Transition counts are aggregated over many runs before building a single chain. If different runs each lock into different single pairs, the pooled matrix can look like a sparse multi-basin system even when no single run exhibits the claimed exploratory basin dynamics. The within-run escape analysis is also selective: it focuses on faults [0, 4, 12, 13, 14], while the taxonomy’s metastable exemplars include F17 and F18 and the robustness table already shows F12 is the weakest member of that class. The strongest claimed evidence is therefore not evaluated on the full metastable set.

## Claim Boundary

What is currently defensible is narrow. Within this one Tennessee Eastman Process subsystem, some faults generate strongly concentrated top-pair sequences under the chosen representation, and the strong-locking class around F06/F08/F13/F14 appears stable inside the tested grid of (W), (S), and typical_mass. It is also defensible to describe the repo as simulator-only, proof-of-mechanism work rather than industrial validation; both the README and the marine-mapping document say that directly.

What is overstated is everything beyond that narrow claim. “Attractors” are not validated physical structures; “emerged naturally from unsupervised transition dynamics” overstates a pipeline that contains manual state compression and rule-based taxonomy; “before conventional alarm thresholds” is unsupported because the comparator is a 3σ detector rather than plant alarms; and transfer to marine systems is aspirational only, with the marine document explicitly calling TEP a proof-of-mechanism rather than industrial validation.

## Critical Missing Experiments

The missing experiments are not optional polish. They are the tests that distinguish mechanism from artifact. The current sweep varies only window size, stride, and mass threshold. It does not vary representation, dimensionality, null model, or alarm definition.

- Continuous-state ablation: compare full continuous contribution vectors, soft assignments, and rank-k occupancy against hard argmax; the regime taxonomy must survive.
- Null surrogates: use surrogates that preserve marginal spectra and autocorrelation but destroy cross-variable structure; if basins persist, the topology is an artifact.
- Non-overlap tests: rerun with (S=W) and then modest overlap only; recompute switching, residence, escape, and stationary occupancy.
- Variable-set expansion: sweep many 5-variable subsets and larger windows of 6–10 variables; test whether strong attractors persist or dissolve.
- Real comparator tests: benchmark against actual alarm logic, then against at least one non-TEP simulator and one real telemetry source.

## What Would Falsify the Framework

The framework would be falsified, not merely weakened, by any of the following outcomes.

- The same taxonomy appears on surrogate data that preserve univariate behavior and autocorrelation while breaking cross-variable coupling.
- The regimes disappear once hard top-pair discretization is replaced by continuous or soft state representations.
- Non-overlapping windows remove most residence, escape, and basin structure.
- Different variable subsets or larger pair spaces collapse the taxonomy or reassign the supposed attractor faults.
- Actual plant or simulator alarm logic fires earlier than the relation detector, or no earlier relational shift replicates across simulators and real data.

## Overall Verdict

Current status: this is a symbolic-telemetry hypothesis on one favorable TEP slice, not a validated discovery about structural dynamics. The strongest observed phenomena are at least equally explainable by a stack of artifacts—diagonal-only attribution, hard top-pair discretization, extreme window overlap, rule-based topology compression, pooled-run aggregation, and the unusually favorable reactor–separator control architecture of TEP. Until the missing ablations and falsifiers are passed, “diffuse wandering,” “metastable basin,” and especially “single-edge attractor” should be treated as descriptive labels for one discretized proxy on one simulator, not as evidence that industrial faults genuinely enter relational attractor basins before conventional alarms.
