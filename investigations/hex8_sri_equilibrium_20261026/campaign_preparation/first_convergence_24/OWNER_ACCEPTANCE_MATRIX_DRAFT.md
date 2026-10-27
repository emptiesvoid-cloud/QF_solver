# HEX8-SRI first-six acceptance matrix — Owner review draft

**State:** `PREPARED_NOT_AUTHORIZED`. These proposed criteria are not an Owner
decision and must not be used to launch a case. No value below was selected by
trying to reproduce the six historical PASS results. Existing proposed
thresholds are transcribed unchanged from the registered case drafts; new
checks are explicitly marked as requiring Owner review.

## Fixed scope and model

The first tranche is the six exact `4×2×2` nodeids: HEX8 standard, SRI
historical and SRI corrected, each at `ν = 0.3` and `ν = 0.4999`. Every case
uses the same `20×1×1 m` beam, `E = 1.0e6 Pa`, the `x=0` face fixed in all
translations, and a uniform end-face traction with resultant `(0, 0, -1) N`.
The mesh has 16 elements, 45 nodes, 135 total DDL, 27 constrained DDL and 108
free DDL. No formulation equations or thresholds are changed here.

## Per-case numerical validity and equilibrium

| Check | Definition | Units | Proposed threshold | Basis and status |
|---|---|---|---|---|
| Finite state | All entries of `K`, `u`, `Ku-f`, free residual, reactions, sampled strains, sampled `det(J)`, `U`, `Wext`, and reported scalar observables are finite. | Mixed physical units; finite predicate is unit independent | No NaN or infinity | Hard validity condition; existing driver already records a finite-state verdict. |
| Positive Jacobians | `min(det J_e(ξ))` over all elements and the center plus eight Gauss points. Also compare each affine-element sample against `det(J)=0.15625 m³`. | `m³` | `det J > 0`; geometry reproduction `|det J−0.15625|/0.15625 ≤ 1e-12` | Positive orientation is mandatory. The relative check verifies the known affine mesh mapping and is a new proposed geometry check, not a result. |
| Free equilibrium residual | `r_f=(Ku−f)_f`; `ρ_f=||r_f||₂ / max(||f_f||₂, ||(K_ff u_f)||₂, 1 N)`. | `N` for `r_f`; dimensionless `ρ_f` | `ρ_f ≤ 1e-7` | Existing registered proposal; denominator and threshold are unchanged. |
| Energy identity | `U=0.5 uᵀKu`, `Wext=uᵀf`; `η_E=|2U−Wext|/|Wext|` for nonzero work. | `J` for energies; dimensionless `η_E` | `η_E ≤ 1e-8` | Existing registered proposal for the linear, unprestressed system. `U` and work are archived separately. |
| Stiffness symmetry | `η_K=||K−Kᵀ||_F / ||K||_F`. | Dimensionless | `η_K ≤ 1e-12` | New proposed numerical-algebra check for a linear elastic symmetric operator. Requires Owner acceptance before it becomes a frozen gate. |
| Elastic energy sign | `U=0.5uᵀKu` for nonzero applied load and nonzero displacement. | `J` | `U>0` | Basic positivity sanity check; no arbitrary positive floor is proposed. It is not a spectral stability proof. |
| Force closure | `c_F=F_applied+R_support`; `ρ_F=||c_F||₂/max(||F_applied||₂,||R_support||₂,1 N)`. | `N` and dimensionless | `ρ_F ≤ 1e-6` | Existing registered proposal; retain the 1 N floor and do not retune it. |
| Moment closure | About the documented global origin: `c_M=Σ(r_i×F_i)+Σ(r_i×R_i)`; `ρ_M=||c_M||₂/max(||M_applied||₂,||M_support||₂,1 N·m)`. | `N·m` and dimensionless | `ρ_M ≤ 1e-6` | Existing registered proposal. Applied resultant moment for the stated load is `(-0.5, 20, 0) N·m`; the support resultant must close it. |
| Signed loaded-face displacement | Area-weighted face integral `UZ̄=A⁻¹∫_A u_z dA`, evaluated with the Q1 face weights. | `m` | Finite and negative under the stated sign convention; magnitude is reported, not gated on this tranche | Confirms sign and definition only. A more compliant value is not automatically more accurate. |

All quantities, raw norms, denominators and verdicts must be preserved before
assertions. A failing numerical check remains a failure with its evidence; it
does not authorize a threshold change.

## Provenance and reproducibility

These are exact-match controls rather than tolerance-based numerical criteria:

| Control | Required evidence | Acceptance rule |
|---|---|---|
| Node and scope | Nodeid, `hex8sri-convergence24` scope, mandate, campaign and case ID | Exact match across runner, execution manifest, case manifest, receipt and test request |
| Science identity | Branch, commit, tree and source fingerprint | Exact match; fingerprint recomputed by the runner and independently by the test before assembly |
| Controller identity | Root, branch, HEAD, tree, runner/policy/pytest-plugin SHA-256 | Exact match across runtime environment, Owner manifest, case registration and preflight |
| Solver origin | Resolved `solveur.__file__` | Must equal the registered science worktree’s `src/solveur/__init__.py` |
| Owner decision | Separate decision JSON, `APPROVED` state, exact authorized node list, matching SHA-256 | Must bind this case, scope, mandate, science/controller identities and unchanged limits. This is an auditable record, not a cryptographic signature. |
| Collect-only receipt | Receipt SHA-256, exact collected nodeid, no skip markers, `bodies_executed=false`, `attempt_reserved=false` | All exact; a preflight is not an execution authorization. |
| Attempt and resources | One attempt maximum; 180 s timeout; 512 MiB sampled RSS ceiling; 256 MiB archive ceiling | Enforce the existing manifest values without modification. RSS/archive observations remain soft controls as defined by the runner. |
| Evidence integrity | Start record, compressed state, sidecar, final/failure record and SHA-256 values | Create new files without replacement and preserve them before verdict assertions. |

The canonical runner validates an Owner decision record and its hash binding,
but the local JSON workflow does not authenticate the human author
cryptographically. Owner-controlled review/storage remains necessary.

## Comparison among formulations

For each matched pair `(a,b)` at the same `ν` and mesh, report the signed and
absolute `UZ̄`, internal energy, applied work, reaction resultant, residual,
symmetry defect and condition estimate. For a scalar observable `q`, report
`Δ_rel(a,b)=|q_a−q_b|/max(|q_a|,|q_b|)` when the denominator is nonzero; also
report the dimensional `Δ_abs=|q_a−q_b|` in that observable’s unit. For vector
observables, report both the signed components and Euclidean norm difference.

**No pairwise pass threshold is proposed.** These differences describe the
formulation effect; they do not rank accuracy and do not presume the corrected
SRI or the more compliant operator is closer to truth.

## Spatial convergence and independent reference

These gates are **not evaluable on the first six cases**, which share one mesh.
They remain proposed for the four matched levels `4×2×2`, `8×4×4`, `16×8×8`
and `32×16×16`:

| Check | Definition | Units | Existing proposed threshold | Status |
|---|---|---|---|---|
| Last-two-level mean displacement change | `|UZ̄_n−UZ̄_{n−1}|/max(|UZ̄_n|,|UZ̄_{n−1}|)` at the last two levels | Dimensionless; `UZ̄` itself in `m` | `≤ 0.02` | Preserve the registered proposal; cannot be evaluated with one level. |
| Last-two-level energy change | `|U_n−U_{n−1}|/max(|U_n|,|U_{n−1}|)` at the last two levels | Dimensionless; `U` itself in `J` | `≤ 0.02` | Preserve the registered proposal; this is an empirical stabilization check, not an assumed order of convergence. |
| Finest-level independent 3D displacement error | `|UZ̄_h−UZ̄_ref|/|UZ̄_ref|` | Dimensionless | `≤ 0.05` | Existing proposal only. The mixed displacement-pressure P2/P1 tetrahedral reference is `NOT_IMPLEMENTED_OR_QUALIFIED`; do not evaluate until its code/version, mesh study, and uncertainty are frozen independently. |
| Finest-level independent 3D energy error | `|U_h−U_ref|/|U_ref|` | Dimensionless | `≤ 0.05` | Existing proposal only; same independent-reference limitation. |

The existing reference plan targets relative uncertainty at or below 0.5%,
but currently has no frozen backend or version. No convergence or independent
accuracy claim follows from the six first-level cases.

## Timoshenko beam indicator

For a prismatic cantilever with centroidal transverse resultant `P`,
`w_T = P L³/(3 E I_y) + P L/(κ G A)`, with `I_y=bh³/12`, `A=bh`,
`G=E/[2(1+ν)]`, `L=20 m`, `b=h=1 m`, `E=1.0e6 Pa`, `|P|=1 N`, and the
common rectangular-section `κ=5/6`. The magnitude is `32.0624 mm` at `ν=0.3`
and `32.0719952 mm` at `ν=0.4999`. The Cowper ν-dependent shear coefficient
gives `32.0612 mm` and `32.0699956 mm`, respectively.

This reference uses a centroidal point-resultant beam idealization. It is
consistent in resultant, support, span and section scale with the solid test,
and `L/h=20` makes it useful for scale and sign. It does not capture local 3D
end effects, the face-average observation exactly, or the quasi-incompressible
solid field. **No pass/fail error threshold is assigned to Timoshenko.**

## Owner decisions still required

1. Freeze the existing registered numerical thresholds verbatim or reject
   them with a separately documented scientific rationale.
2. Decide whether to add the `1e-12` stiffness-symmetry criterion and the
   affine-Jacobian reproduction check to the case contract.
3. Approve an independent 3D reference implementation and its uncertainty
   evidence before applying the existing 5% comparison gates.
4. Keep all spatial-convergence decisions deferred until the paired levels
   have been run under separately authorized manifests.

## Current controller-binding blocker

The merged controller policy still pins source fingerprint
`1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555` and the
24 existing case registration digests. The updated science test necessarily
changes the source fingerprint; the current registered value therefore cannot
validate new manifests or preflights. The controller also hardcodes this source
fingerprint in its runner. A separate reviewed controller refresh must bind
the new source fingerprint and regenerated case registration digests while
keeping `execution_authorized=false`; the existing campaign mandate and
budgets must remain unchanged. The old case manifests and preflight receipts
remain historical and must not be overwritten or rebound.

The designated shared execution-controller checkout
(`E:/QFSolverAgents/wp12-policy-final`) was observed at branch
`codex/wp12-policy-finalization`, HEAD `4bf52792f46988b84fecf11ebe3bd5fe078975ef`,
22 commits behind the current canonical controller and with a modified
`development_autonomous_policy.json`. It is not a clean checkout of merged
controller HEAD `f5a1a4284fb0cc56dd909ce455981f08a9d26ad1` and was not changed.
Consequently no final controller-bound case manifests or new preflight
receipts are issued by this science change. The exact source identity and
criteria below are prepared for review; preflight renewal awaits the separate
controller registration refresh and a clean definitive controller checkout.

