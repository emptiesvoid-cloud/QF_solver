# 026-G08 Linear Buckling Contract

## Status

`026-G08` is **NOT_STARTED**. This document and the accompanying JSON files
define a controlled candidate contract; they are not numerical evidence and do
not close the gate.

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
`qualification/0_2_6/g08_case_registry.json`.

| Requirement | Evidence required | Policy status |
| --- | --- | --- |
| `G08-001` | input-scope and invalid-input matrix | existing implementation scope |
| `G08-002` | preload equilibrium and initial-stress tangent diagnostics | existing policy reference; no new numeric band |
| `G08-003` | analytical/reference critical factor | `PROPOSED_OWNER_REVIEW`, case-defined |
| `G08-004` | mode residual, norm and free-DOF mapping | `PROPOSED_OWNER_REVIEW` |
| `G08-005` | compatible mesh sequence and successive factor changes | `PROPOSED_OWNER_REVIEW`; candidate four-level sequence |
| `G08-006` | first-mode normalization and deterministic replay | `PROPOSED_OWNER_REVIEW` |
| `G08-007` | fail-closed structured failure behavior | existing exact invariant policy |
| `G08-008` | formulation-compatible external comparison | `PROPOSED_OWNER_REVIEW`; unavailable/non-comparable is skipped |
| `G08-009` | SHA, environment, command and artifact digest | existing V&V provenance contract |

No null or proposed policy may be converted into a numerical PASS by a runner.
The Owner must approve the case-specific analytical, mode, mesh and external
correlation bands before G08 closeout.

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
The contract itself cannot close G08; closeout requires archived results,
approved policies, final-SHA provenance and an explicit Owner decision.

Out of scope: nonlinear/post-buckling response, imperfection-sensitive
collapse, arc-length/path following, finite-kinematic J2, shell/beam/discrete
buckling through this route, and general physical validation.
