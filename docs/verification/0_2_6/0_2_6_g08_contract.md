# 026-G08 Linear Buckling Contract

## Status

`026-G08` is **PASS_WITH_LIMITATIONS** by explicit Owner closeout. This
document defines the contract and summarizes the archived evidence; the
machine-readable decision is recorded in
`qualification/0_2_6/g08_owner_closeout.json`.

## Audited route

The public route is `linear_buckling`, dispatched by
`src/solveur/core/router.py` to `LinearBucklingSolver` in
`src/solveur/core/analyses/buckling.py`. The current implementation:

- accepts one homogeneous family from `TET4`, `TET10`, `HEX8` or `HEX20`;
- requires one homogeneous `isotropic_3d` material;
- accepts nodal dead loads and rejects distributed loads;
- solves a proportional preload through the existing Full Newton path;
- forms the initial-stress geometric contribution through the existing
  Total-Lagrangian assembly;
- uses SciPy sparse eigen routes (`eigsh`, with the controlled `eigs`
  shift-invert fallback for an indefinite bracket);
- returns the first critical tangent-instability factor and one normalized mode.

This is a **linearized first-instability calculation**. It is not a
post-buckling, collapse, arc-length, physical-validation or general stability
claim. Beam, shell and discrete elements are not supported by this solid route.

## Historical evidence

The 0.2.5 record contains bounded TET4 Euler evidence, a bounded assembled-mesh
trend, and a CalculiX adapter that can generate same-model solid decks. Those
records remain historical and bounded. They are not silently promoted to a
0.2.6 gate result. The existing Code_Aster structural adapter explicitly
records that it has no equivalent 3D solid eigen-buckling modelisation for this
comparison; that row is `NOT_APPLICABLE`, not PASS.

## Requirements and policies

The machine-readable contract is `qualification/0_2_6/g08_requirements.json`.
The case-to-requirement mapping is
`qualification/0_2_6/g08_case_registry.json`. The Owner bounded policy review
is recorded in `qualification/0_2_6/g08_owner_contract_review.json`.

| Requirement | Evidence required | Policy status |
| --- | --- | --- |
| `G08-001` | input-scope and invalid-input matrix | existing implementation scope |
| `G08-002` | preload equilibrium and initial-stress tangent diagnostics | existing policy reference; no new numeric band |
| `G08-003` | analytical/reference critical factor | `OWNER_APPROVED_BOUNDED`; case-defined before execution, sign-consistent |
| `G08-004` | mode residual, norm and free-DOF mapping | `OWNER_APPROVED_BOUNDED`; normalized residual bands with near-zero rule |
| `G08-005` | compatible mesh sequence and successive factor changes | `OWNER_APPROVED_BOUNDED`; at least three levels and final adjacent change `<=1%` when eligible |
| `G08-006` | first-mode normalization and deterministic replay | `OWNER_APPROVED_BOUNDED`; first mode only |
| `G08-007` | fail-closed structured failure behavior | existing exact invariant policy |
| `G08-008` | formulation-compatible external comparison | `OWNER_APPROVED_BOUNDED`; CalculiX when comparable, Code_Aster non-comparable is skipped |
| `G08-009` | SHA, environment, command and artifact digest | existing V&V provenance contract |

The bounded policy review is approved, but case-specific analytical and
external tolerances must still be declared before execution and cannot be
changed after observing results. No policy may be converted into a numerical
PASS by a runner without its required evidence.

## Execution evidence

The controlled execution record is archived in
`qualification/0_2_6/g08_execution_evidence.json`, with the concise report in
`qualification/0_2_6/g08_execution_evidence.md`. On source SHA
`6589443e1404a2749ac6c0a9b911f00dd9cb8753`, the campaign executed 23 cases:
21 PASS, 2 controlled expected failures and 0 FAIL. All four families were
run on four mesh levels, and deterministic first-mode replay was checked for
each family within the declared floating-point tolerance.

The TET4 Euler record passed its existing case-specific analytical screen.
CalculiX completed comparable TET4, TET10 and HEX8 rows; the HEX20 deck
failed in the external tool and is retained as an explicit blocked row. This
is partial external evidence, not a universal correlation claim. The mesh
final-adjacent `<=1%` eligibility is reached by TET4 only in this campaign;
TET10, HEX8 and HEX20 remain bounded trend evidence.

## Supplemental mesh extension

The supplemental extension is archived in
`qualification/0_2_6/g08_mesh_extension_evidence.json` and
`qualification/0_2_6/g08_mesh_extension_evidence.md`. It reuses the historical
levels 1/2/4/8 and executes levels 16 and 32 for TET10, HEX8 and HEX20 on
source SHA `151662ac4781718a7fbe3d1e527675ec9e513ad4`, with `dirty=false`.
All 12 extension observations, including deterministic replays, passed. The
direct level-16-to-level-32 changes are TET10 `0.081448%`, HEX8 `0.167113%`
and HEX20 `0.912621%`, classified `CONVERGED_BOUNDED` under the unchanged
Owner policy. This supplemental evidence does not alter the historical Owner
closeout or promote any family retrospectively. HEX20 remains bounded evidence
with strong coarse-history sensitivity, no comparable high-order analytical
oracle, and a `BLOCKED_EXTERNAL_TOOL` CalculiX retry.

## Targeted HEX20 CalculiX rescue

The blocked HEX20 buckling retry was reproduced as a verification-deck defect:
the C3D20 continuation line began with an empty field. The correction is limited
to `src/solveur/verification/calculix_buckling_025.py`; no FEM formulation,
eigensolver or solver behavior changed. The regression test is
`tests/unit/test_calculix_buckling_025.py`.

The controlled rescue evidence is archived in
`qualification/0_2_6/g08_hex20_calculix_rescue_evidence.json` and
`qualification/0_2_6/g08_hex20_calculix_rescue_evidence.md`. It runs the same
HEX20/C3D20 model at one and two cells, with deterministic replays. The QF /
CalculiX factor differences are `1.696%` and `2.094%`, respectively, inside
the pre-existing 10% bounded correlation screen. First-mode comparisons are
reported after arbitrary eigenvector sign alignment without inventing an
external MAC threshold.

This rescue resolves the malformed-deck blocker for the tested cases, but it
does not rewrite the historical closeout, promote HEX20 automatically, or
change the G08 status from `PASS_WITH_LIMITATIONS`. Mesh-sensitivity limits,
absence of a high-order analytical oracle and the lack of a Code_Aster
equivalent remain explicit.

## Owner closeout

The Owner decision is `PASS_WITH_LIMITATIONS`, with no solver or numerical
formulation change. TET4 is `QUALIFIED_BOUNDED` for the tested first
linearized tangent-instability factor and first mode. TET10 and HEX8 are
`PASS_WITH_LIMITATIONS`: their routes and CalculiX rows passed, but their final
mesh changes are 3.177% and 2.636%, respectively, above the quantitative 1%
eligibility band. HEX20 is `MORE_EVIDENCE_REQUIRED` because its final mesh
change is 13.940% and its CalculiX row is `BLOCKED_EXTERNAL_TOOL`.

Requirement disposition is six fully satisfied and three satisfied only within
bounded limitations (`G08-003`, `G08-005`, `G08-008`). The qualified bounded
scope is therefore TET4, homogeneous isotropic 3D material, nodal dead loads,
sparse SciPy, first factor and first mode. TET10/HEX8 evidence remains
explicitly limited, and HEX20 is not qualified.

The numerical evidence is tied to `EXECUTION_SOURCE_SHA =
6589443e1404a2749ac6c0a9b911f00dd9cb8753` with `dirty=false`. The later
documentation/Owner commit is separate and does not replace that execution
SHA. This closeout does not claim post-buckling, multi-mode qualification,
Code_Aster correlation, or general physical validation.

## Case plan

The registry deliberately separates executable definitions from results:

| State | Meaning | Count |
| --- | --- | ---: |
| `READY` | controlled definition exists and may be executed by the future G08 runner | 3 |
| `PLANNED` | evidence definition exists but execution is deferred to G08 | 9 |
| `NOT_APPLICABLE` | outside the current contract or no comparable formulation exists | 2 |
| `NOT_SUPPORTED` | current route explicitly does not support the requested combination | 2 |

The planned mesh work uses coarse/medium/fine/refined where a compatible
factory can provide those levels. A future campaign must record DOF, critical
factor, mode diagnostics, residuals, mesh quality, timing and provenance at
each level. The four-level sequence is a plan, not a claim of convergence.

## External correlation

CalculiX is an available supporting route for comparable solid decks and
remains subject to the external policy. Code_Aster is retained in the matrix,
but the controlled audit currently identifies no equivalent 3D solid
eigen-buckling modelisation. Any unavailable or non-comparable external case
must be recorded as `SKIPPED_NOT_COMPARABLE` or an equivalent explicit skip;
it cannot be counted as PASS.

## Dependencies and closure boundary

G08 execution depends on the clean baseline and V&V foundation gates
`026-G00` through `026-G03`. It does not require `026-G07` to be silently
closed, and G07 evidence cannot be used as a substitute for buckling evidence.
The contract itself did not close G08; closeout required archived results,
approved policies, final-SHA provenance and the explicit Owner decision now
recorded in the closeout artifact.

Out of scope: nonlinear/post-buckling response, imperfection-sensitive
collapse, arc-length/path following, finite-kinematic J2, shell/beam/discrete
buckling through this route, and general physical validation.
