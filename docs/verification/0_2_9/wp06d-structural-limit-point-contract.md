---
doc_id: DOC-029-WP06D-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-D — Structural Limit-Point and Snap-Through Contract

## Status and execution boundary

This document hardens the prospective WP06-D structural qualification
contract under Owner correction R1. It contains no structural result and
awards no point. WP06-D formal points remain 0/2, WP06 formal points remain
0/8, and the validated total remains 29/100.

The source baseline for this preparation is
0297105de78a846b0424d052c5323858db23b7c5 on branch `0.2.9-wp06-prep`.
The machine-readable contract is
`qualification/0_2_9/wp06d_structural_limit_point_contract.json`.

Phase 0 is fail-closed:

- `STRUCTURAL_SOLVES_ENABLED = FALSE`;
- `EXTERNAL_SOLVER_ENABLED = FALSE`;
- Phase 1 requires Owner authorization and integration of the governing
  0.2.9 nonlinear policy;
- no FE snap-through, post-limit, external or heavy solve was run here.

No production mechanics, element formulation, convergence algorithm or
arc-length implementation was changed.

R0 history is preserved: the initial preparation described one-third loads on
three crown nodes. That rule was never used in a mechanical solve and is
Owner-rejected as the final contract. R1 freezes the physical load as a point
load at the persistent geometric crown node 4.

## Canonical benchmark

The selected case is the existing common-driver two-element volumetric TET4
snap-through model in
`src/solveur/verification/robustness_arc_length_extended.py`, refined only
for the future contract. It is a real FE benchmark and is separate from the
WP06-C scalar equation `lambda = u - u**3`.

The frozen formulation is:

- `geometric_nonlinear_static`;
- total-Lagrangian StVK elasticity;
- displacement-only TET4 DOFs;
- serial spherical custom arc length;
- dead/reference load vector;
- no contact, plasticity, dynamics, bifurcation detection or branch
  switching;
- no MPI/PETSc or finite-strain material claim.

M1 parent nodes are:

| node | X | Y | Z |
|---:|---:|---:|---:|
| 0 | -1.00 | 0.00 | 0.00 |
| 1 | 1.00 | 0.00 | 0.00 |
| 2 | 0.00 | -0.05 | 0.20 |
| 3 | 0.00 | 0.05 | 0.20 |
| 4 | 0.00 | 0.00 | 0.25 |

M1 elements are `[0,2,3,4]` and `[1,3,2,4]`. The material is isotropic
StVK with `E = 100.0`, `nu = 0.30` in consistent nondimensional units.

Nodes 0 and 1 are fully fixed point supports. The shared parent face (2,3,4)
is the symmetry face and has `UY = 0`; every generated node in its closed
triangle inherits that condition. No coordinate-tolerance support expansion
is permitted.

The final reference load is a fixed geometric point load at parent node 4:
`[0,0,-1]`. Node 4 persists at every refinement level, so no arbitrary equal
share is introduced on refined nodes. The target resultant is `[0,0,-1]` and
the target moment about the global origin `[0,0,0]`. Phase 0 assembles only
this nodal vector and its resultant/moment; it does not assemble a tangent or
solve a structural problem.

The monitored quantity is the downward crown displacement
`q = -mean(UZ at nodes 2,3,4)`. Secondary quantities are lambda, support
reaction vector/resultant, strain energy where available, arc radius, Newton
iterations, constraint residual and mechanical residual.

## Mesh contract

Exactly three levels are declared; no M4 is part of this contract.

| level | construction | nodes | TET4 | DOFs | minimum reference volume | class |
|---|---|---:|---:|---:|---:|---|
| M1 | two parent TET4 | 5 | 2 | 15 | 8.333333333333333e-4 | TINY |
| M2 | one conforming 8-subtet refinement | 14 | 16 | 42 | 1.0416666666666667e-4 | LIGHT |
| M3 | two conforming 8-subtet refinements | 55 | 128 | 165 | 1.302083333333333e-5 | LIGHT |

Each TET4 is split into four corner tetrahedra and four central tetrahedra
using the midpoint of the `ab` edge to the midpoint of the `cd` edge as the
central diagonal. At each level, all parent edges are sorted lexicographically
by `(min(parent_id), max(parent_id))`; parent nodes remain first and one
midpoint is appended per unique edge key. Shared edges reuse that exact node,
and no coordinate-tolerance merge is allowed. Zero-volume children fail
closed; negative signed children are repaired by swapping the final two
connectivity entries. The same rule must be used in Phase 1. Exact counts,
positive volumes, deterministic connectivity digest, support/symmetry/load
boundary membership and persistent load node 4 are mandatory preflight
checks.

The primary comparison is M2 to M3. The frozen candidate limits are:

- monitored displacement: 3%;
- limit-point lambda: 3%;
- post-limit monitored displacement/path: 3%;
- support reaction: 3%;
- strain energy: 5%.

For any scalar or vector observable the relative change is
`abs(M3-M2) / max(abs(M3), abs(M2), scale_floor)`, with Euclidean norm for
vectors. The scale floor is
`max(1e-14, 64 * machine_epsilon * declared_physical_scale)`. Missing or
non-finite values fail closed.

## Path and limit-point gates

The expected path has a pre-limit branch where lambda increases, followed by
the first local maximum of lambda as a function of q. The post-limit branch
must continue along the selected displacement direction while lambda
increments reverse. Detection uses three consecutive accepted points and
does not require a step to land exactly on the theoretical extremum. Branch
switching and bifurcation detection are excluded.

The required limit/reference checks are:

- reference limit displacement error <= 3%;
- reference limit lambda error <= 3%;
- post-limit reference path error <= 5%;
- vector force equilibrium <= 1e-8;
- vector moment equilibrium about `[0,0,0]` <= 1e-8;
- geometric envelope: `det(F) >= 0.20`, principal stretches in `[0.75,1.30]`
  and `||E_GL||_F <= 0.30`.

Path stations are fixed at 20%, 40%, 60%, 80% and 100% of normalized
cumulative accepted-path arc measure. With `s_0=0`,
`s_i=s_(i-1)+sqrt(||delta_u_i||²+(load_scale*delta_lambda_i)²)` and
`load_scale=1`, `s_norm=s_i/s_final`. Reference and QF paths are piecewise
linearly interpolated in this parameter. `q_limit` and `lambda_limit` are the
values at the first accepted local maximum event; `post_limit_displacement`
is `q(s_norm=1)-q_limit`, and `post_limit_lambda` is retained as a secondary
endpoint value. Endpoint-only or cherry-picked comparisons are not valid.

## Continuation and linear solver policy

The future run uses the current governing policy after integration. The
benchmark-specific frozen settings are:

| setting | value |
|---|---:|
| initial/max radius | 0.02 |
| minimum radius | 2e-6 |
| growth/shrink factors | 1.5 / 0.5 |
| adaptive radius | false |
| nominal iteration range | 1–40 |
| hard Newton maximum | 80 |
| accepted steps | 80 |
| retry budget | 8 |
| mechanical/constraint tolerance | 1e-8 / 1e-8 |
| load-factor limit | 5.0 |

The orientation policy is the existing deterministic policy: target-load
direction initially, previous displacement projection first, previous load
increment only as a near-zero tie-breaker, and preservation of the
displacement branch through a load-factor reversal. Rejected state is rolled
back before retry and no retry may alter the physics contract.

The predictor and augmented corrector use serial sparse direct solves. There
is no silent fallback; a failed or unsupported augmented solve is typed and
fail-closed. CG/MINRES are not default-valid for the generally nonsymmetric
augmented matrix.

## Independent reference

The primary reference is a future independent direct implementation of the
same TET4 geometry, connectivity, StVK internal energy/tangent, BCs, load,
monitor and spherical constraint. It may use NumPy/SciPy primitives, but it
must not import QF production arc-length routines, nonlinear continuation
kernels, residual/tangent helpers or TET4 geometric-nonlinear element
routines. A reduced shallow-arch/two-bar relation may provide an analytical
sanity check for scale and turning direction, but cannot be used as a TET4
acceptance oracle.

The reference plan is currently `PLAN_ONLY_NO_REFERENCE_RESULT`.
Formulation mapping must be `YES` before any comparison evidence can qualify.

## Replay and failures

The replay case is M1. Accepted displacement and lambda paths, radius and
orientation histories, step acceptance/rejection history, Newton iteration
counts and terminal classification must match with relative tolerance
`1e-12` and absolute floor `1e-14`, with the same qualitative limit-point and
reversal classification.

The controlled failure taxonomy is:

`PREDICTOR_FAILURE`, `CORRECTOR_FAILURE`, `ARC_LENGTH_CONSTRAINT_FAILURE`,
`AUGMENTED_LINEAR_SOLVE_FAILURE`, `STEP_RADIUS_EXHAUSTED`,
`LIMIT_POINT_TRACKING_FAILURE`, `EQUILIBRIUM_FAILURE`, `REFINEMENT_FAILURE`,
`REFERENCE_MISMATCH`, `NONFINITE_STATE`, `RESOURCE_LIMIT`, and `UNKNOWN`.

Future negative controls cover singular predictor/augmented systems,
non-finite state, radius exhaustion, equilibrium/refinement/reference
violations and resource exhaustion. Negative cases are safety evidence only;
they are not structural qualification passes.

## Governance and validation

This Phase-0 change adds only the contract, a fail-closed preparation guard,
tests and registry entry. No structural, external, heavy or full-suite run is
authorized. WP06-D remains 0/2 and the technical candidate total remains
4/8.

The next step is Owner contract freeze. After WP04 governing-policy closure
and the integration train, Phase 1 may execute the three structural levels,
the independent reference, replay and the frozen closure gates.
