# WP06 — Campbell and modal tracking design freeze

Status: prospective contract frozen before WP06 benchmark execution. The machine-readable authority is [`wp06_campbell_contract.json`](wp06_campbell_contract.json). No result from GYRO-05 or GYRO-06 may be used to relax its policy.

## Scope and architecture

WP06 adds an experimental sweep over the already verified WP05 single-speed route. `rotating_modal` remains the one-speed physics solve; `modal_tracking` associates complex modes and records lineage/ambiguity; `campbell` invokes the fixed model at the explicit ordered speeds; `post/campbell` only projects a `CampbellResult` to tables or plots. This is not a new physical formulation or an independent physical validation.

The only changing sweep quantity is signed `Omega` in rad/s. The input model, disk definitions, axis/frame, reduced `K`, `M`, `G`, and QEP policy are invariant. Any speed-dependent property or out-of-scope WP05 model fails closed. The caller must provide 2–101 finite strictly increasing speeds; the API never creates a speed grid implicitly. RPM conversion, if provided, is named and explicit.

## Frozen association policy

The primary score is the Hermitian mass-weighted complex MAC. The modes remain complex; phase or nonzero scaling does not change MAC. The normalized frequency distance is divided by the maximum of the two absolute frequencies and 1 Hz. Polarization is the signed transverse descriptor from WP05 conventions; it contributes only when both classifications are defined.

Admissible edges require complex MAC at least 0.80 and normalized frequency distance at most 0.25. The predeclared edge cost is 0.65 times one minus MAC, 0.25 times capped frequency distance, and 0.10 times polarization distance; when polarization is unavailable, the remaining weights are renormalized. A global Hungarian assignment uses explicit dummy unmatched nodes at cost 0.40. Invalid edges have cost 1,000,000. A best/second-best admissible cost margin below 0.05 is ambiguous: candidate edges are recorded and the individual branch edge is not committed.

Modes within relative frequency gap `1e-8` form a degenerate cluster. Cluster bases are mass-whitened; principal-angle singular values compare subspaces, with a minimum singular value of `0.99999999` for a same-subspace match. A cluster split records parent/child lineage. Individual identity inside a degenerate eigenspace is not asserted. A weak, undefined, or station-inconsistent whirl estimate is retained as such and cannot be used to force a match.

Adaptive speed refinement is disabled in this WP06 contract (depth and additional solves are zero). Ambiguity therefore remains visible as an ambiguous record or a gap.

## Frozen verification cases

GYRO-05 uses the independent disk-oscillator formula and the WP05 parameters `m=1 kg`, `Jd=0.01 kg m2`, `Jp=0.02 kg m2`, and `kθ=100 N m/rad`. Speeds are the ordered list `[-100,-50,-25,-5,0,5,25,50,100] rad/s`. Relative frequency error is limited to `1e-10`. The benchmark also checks zero-speed clustering, split lineage, arbitrary complex phase invariance, input eigenpair permutation invariance, QEP residuals, and a symmetric two-dimensional controlled tie that must report ambiguity rather than continuity.

GYRO-06 uses one straight 1 m circular isotropic BEAM2 shaft, fixed at one end, carrying the WP05 centered disk at the other. The mesh levels are 4, 8, 16, and 32 elements; speeds are `[0,100,250] rad/s`; four positive-frequency modes are requested. The adjacent 16-to-32 element branch frequency change must be at most 0.5% under the frozen denominator definition, and QEP residuals must remain within `1e-8`. This is internal mesh-convergence evidence, not independent physical validation.

Each benchmark record stores expected and observed values, absolute/relative error, threshold, and PASS/FAIL. Tracking records additionally preserve MAC, frequency distance, assignment score, ambiguity margin, branch ID/lineage, candidates, and source result identity/hash. Execution identity and hashed provenance follow WP03 schema v2.

## Campbell projection and maturity

`CampbellResult` is the authoritative structured result. A reproducible frequency-versus-spin plot may display branches and an explicitly requested `1x` line. Missing and ambiguous points are not interpolated. Any crossing of `1x` is only a frequency coincidence or candidate critical-speed location within this linear modal model; it says nothing about forced-response amplitude, imbalance response, operational risk, or instability.

Maturity stays `EXPERIMENTAL`. No WP05 physics, QEP, result contract, historical record, release tag, or v0.2.10 artifact is changed by this work package.
