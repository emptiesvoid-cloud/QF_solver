# V2 numerical criteria and interpretations

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**
Every V2 threshold and the single attempt still require a new, case-specific Owner decision. The earlier U3 decision does not authorize V2.

## Reference and arithmetic

The discrete reference is formed with exact rational arithmetic from the binary64 H1 coordinates, E and nu and the linear isotropic TET4 small-strain formulation. The input values are rationalized exactly as stored; the reference is independent of the scalar, batch and matrix-free floating kernels, but it is not an independent continuum solution or external code comparison.

For `m` terms, use `u=2^-53` and `γ_p=pu/(1-pu)`, with `p=m-1`. Bound sums are exact sums of rationalized binary64 contributions. Any overflow/underflow or non-round-to-nearest behavior invalidates the standard bound's assumptions. The runtime rounding mode and every internal intermediate are not independently observed by this test; until that gap is accepted or resolved, the affected gamma-bound outcome is conditional/INCONCLUSIVE.

## Proposed acceptance gates

These numerical values are inherited from the WP12-U H1 manifest/oracle proposal for review; they are not silently promoted to V2 authorization. The new Owner decision must explicitly bind this manifest SHA and accept the V2 use of each criterion.

| Gate | Proposed criterion | Meaning and limit |
|---|---:|---|
| Scalar assembled global matrix vs exact rational matrix | relative Frobenius error ≤ `1e-12` | Whole 36×36 matrix; detects symmetric-but-wrong matrices. Reused from WP12-U H1 proposal. |
| Batch assembled global matrix vs exact rational matrix | relative Frobenius error ≤ `1e-12` | Same denominator and reference as scalar. |
| Scalar and batch componentwise global symmetry | every `|Kij-Kji|` ≤ captured local-mirror term plus both gamma aggregation bounds | No arbitrary absolute symmetry tolerance; local asymmetry is reported separately. |
| Matrix-free operator vs exact matrix | full 24×24 relative Frobenius error ≤ `1e-12`; every column error normalized by exact full-matrix Frobenius norm ≤ `1e-12` | The same bound is applied over all 24 canonical inputs, not a sample. This does not generalize beyond H1. |
| Assembled-direct operator vs exact matrix | full 24×24 relative Frobenius error ≤ `1e-12` | Each direct column is captured from the complete matrix. |
| Matrix-free vs direct operator | full 24×24 relative Frobenius difference normalized by exact full-matrix Frobenius norm ≤ `1e-12` | Matrix infinity/max-entry metrics are reported, not assigned new pass/fail thresholds. |
| Matrix-free archived-field residual | `||r_free||₂/||f_free||₂ ≤ 1e-8` | U3 normalization; the field is historical and is not resolved again. |
| Direct archived-field residual | `||r_free||₂/max(||f_free||₂, ||(Ku)_free||₂, 1) ≤ 1e-7` | U3 normalization; no new threshold. |
| Energy/work identity | exact equality `2U-W=u_freeᵀr_free` under the exact rational discrete reference | Identity check, not a physical-energy accuracy claim. |
| Force/moment identities | exact residual-projection identities and their Cauchy bounds | Discrete equilibrium diagnostics; not an external load validation. |
| Negative controls | every named control reports detected | Synthetic predicate checks only. They must not change production code, historical data or thresholds. |

## Diagnostic-only quantities

Report local exact-symmetry booleans, global relative symmetry Frobenius ratios, number of nonzero asymmetric pairs, exact contribution lists, maximum error-to-bound ratios, matrix difference Frobenius/infinity/max norms, archived terminal UZ, work-conjugate displacement, recalculated reactions/moments and their exact differences from archived summaries, strain energy, external work and archived-field differences. Reaction/moment archive deltas are diagnostic; the infinity and maximum metrics are also diagnostic. No separate limits are introduced for them.

The CSR input arrays show generation order and order passed to SciPy. They do not expose SciPy's internal duplicate reduction order. A one-ULP historical difference alone is not an acceptance tolerance.

## Negative controls and decision meaning

On synthetic copies, require detection of: a missing element matrix; a shifted DDL map; a perturbed mirrored local entry; a symmetric matrix with incorrect values; a perturbed matrix-free column; an inconsistent archived residual; and a nonfinite value. A failed negative control invalidates the test's discrimination logic even if the unperturbed numerical comparisons pass.

At most, a future pytest pass means the assertions in this exact H1 audit ran and passed in its pinned environment. It does not erase U3's FAIL, establish general sparse reduction order, qualify other meshes/elements, prove convergence, validate a 3D beam continuum response, promote TET4 maturity, or close WP12.
