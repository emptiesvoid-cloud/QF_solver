# HEX8-SRI refined 8×4×4 criteria proposal

Status: **PROPOSED — Owner criteria freeze required.** This document does not freeze criteria, authorize an attempt, reserve a ledger entry, or establish a qualification result.

Criteria revision: `refined3-8x4x4-nu04999-owner-criteria-2026-10-30-r1`.

## Closed case set

The proposed freeze applies only to these exact registered nodeids at `ν = 0.4999`:

1. `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-8x4x4]`
2. `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-8x4x4]`
3. `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-8x4x4]`

No other nodeid is included. Each case has an independent one-attempt limit. The registered per-case envelope is 300 seconds and 1,024 MiB sampled RSS; the existing campaign limit of 24 total attempts is unchanged. Sampled RSS is a soft observation, not an OS quota.

## Identical model inputs

The three cases use the same `20 m × 1 m × 1 m` domain, `8 × 4 × 4` HEX8 mesh, isotropic linear-elastic material (`E = 1,000,000 Pa`, `ν = 0.4999`), supports, and traction. The `x = 0` face is fixed in all three translations. The `x = 20 m` face receives uniform traction `(0, 0, −1) Pa` over `1 m²`, giving force resultant `(0, 0, −1) N` and moment about the global origin `(−0.5, 20, 0) N·m`.

The grid has 9 × 5 × 5 = 225 nodes, 675 total translational DDL, 25 fixed nodes (75 constrained DDL), and 600 free DDL. Only the formulation changes:

| Case | Operator identity |
| --- | --- |
| `hex8_standard` | Complete 2×2×2 Gauss integration. |
| `sri_historical` | Controlled ablation using central volumetric quadrature weight 1 instead of 8. This is **not** an exact reproduction of the old implementation's arithmetic. |
| `sri_corrected` | Corrected central volumetric integration with weight 8. |

## Proposed per-case gates

These are the metric definitions implemented by `experiments/hex8_sri_equilibrium/convergence.py`; limits below are prospective and still require Owner freeze.

| Metric | Proposed limit | Exact definition and units |
| --- | ---: | --- |
| Free residual | `≤ 1e−7` | `r = K u − F`; `||r_free||₂ / max(||F_free||₂, ||K_ff u_free||₂, 1 N)`. Dimensionless. `K_ff u_free` uses the reduced free-free stiffness and displacement. |
| Energy identity | `≤ 1e−8` | `|2 U_internal − W_external| / |W_external|`, with `U_internal = 0.5 uᵀKu` and `W_external = uᵀF`; both in joules. If external work is exactly zero, the implementation reports infinity and the gate fails. |
| Force closure | `≤ 1e−6` | `||ΣF_applied + ΣR_support||₂ / max(||ΣF_applied||₂, ||ΣR_support||₂, 1 N)`. Resultants in newtons; dimensionless ratio. |
| Moment closure | `≤ 1e−6` | `||ΣM_applied + ΣM_support||₂ / max(||ΣM_applied||₂, ||ΣM_support||₂, 1 N·m)`. Moments are `Σ(x × f)` about the global origin; moment resultants in N·m; dimensionless ratio. |

The same denominator floors and zero-work behavior are part of the frozen definitions; they must not be changed after results are observed. These four limits are case-level gates only. Stiffness condition estimates, formulation differences, stresses/strains, and displacement are reported diagnostics without new acceptance limits. They do not establish spatial convergence or agreement with a qualified independent 3-D reference.

## Provenance and gates

The source candidate is branch `research/hex8sri-equilibrium-8x4x4-20261030`, HEAD `e251883a0dd13e20628eb2ee229b630603af1efb`, tree `fdf9e76cff3293be3705cf29a3226fb480a928ad`, raw-source fingerprint `64d5760e1c904d110a1c1ce9bc490f3f64fdc5168b264de244a7cd878e6c4f2d`. These are prospective identities, not yet an execution authorization.

The existing `wp12_elements` ledger and `hex8sri-convergence24` campaign ledger are separate. The latter has no authoritative prior ledger file or attempt history at the reviewed stores; no history is inferred or fabricated. Its initial ledger must only be created through the controller's normal first valid reservation after all approvals, with zero prior attempts represented. No ledger is initialized by this criteria proposal.

At preparation time, the release branch still designates the prior controller at HEAD `8129335ed9e279544afd46f9e043fb54656e8216`. PR #92 proposes the reviewed, clean detached checkout at HEAD `b6682920b1b6e5201f99a6c61975fb9882a39e0e`, tree `eede464bd38433a8c3a7669c91b975e4dc953d41`, at `E:\QFSolverAgents\controllers\wp12b-hex8sri-controller-b668292\qf_solver`; its VV3D-scope fingerprint is `6b34560162b7c6b2735c3705b1ee87e9c5832b7b4b97b56a926d0784c3e70995`, and the generic controller fingerprint used by HEX8-SRI is `af40be03576d288d269c6fb8628ebde73fd9826cd1b8a5fe4c00f5acff48f13b`. Until PR #92 is approved and merged, the prior pin remains official. No official collect-only preflight, final case manifest, reservation, or FEM execution is produced by this proposal. After integration, the proposed pin will be official, but the Owner must still freeze these prospective criteria before fresh official preflights and controller-bound manifests are prepared. The prior `wp12_elements` mandate mismatch is unrelated to this separate campaign and does not authorize migration or mutation of that historical ledger.

No 16×8×8 case is included. This three-case campaign, if later approved and executed, remains bounded development evidence and is not general formulation qualification.
