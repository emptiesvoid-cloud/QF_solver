---
doc_id: DOC-029-WP07-D-STRUCTURAL-VNV-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-D structural and external V&V contract

This document freezes a prospective structural and external V&V campaign for
the bounded frictionless contact routes. It is a preparation artifact only:
no structural solve, mesh-refinement result, external solver run, formal
point or maturity change is claimed by this document.

Machine-readable contract:
[`wp07d_structural_vnv_contract.json`](../../../qualification/0_2_9/wp07d_structural_vnv_contract.json)

Source snapshot: `9bce66d5cfeeae4fdd66baf6c9652049e0038d40`
Owner status: `OWNER_FREEZE_CANDIDATE`
WP07-D formal points: `0/3`
WP07 technical candidate total: `5/10`
WP07 formal points: `0/10`
Validated total: `29/100`

## Scope and formulation separation

The future campaign contains two separate benchmarks and makes no claim that
their contact enforcement is interchangeable:

* `LINEAR_ACTIVE_SET_INITIAL_SEARCH`: `linear_static`, small displacement,
  frictionless node-to-triangle contact, one fixed initial master face and
  normal, serial direct sparse active-set/Lagrange route.
* `NONLINEAR_PENALTY_INITIAL_SEARCH`: `geometric_nonlinear_static`, fixed
  initial-search face and normal, frictionless node-to-triangle penalty,
  existing common Full Newton route and total-Lagrangian StVK material.

The qualified scope, if the future evidence passes, is limited to the exact
geometry, material, topology, loading, mesh recipe, settings and observable
policies in this contract. It is not a general industrial contact claim.

`UPDATED_SEARCH_FINITE_SLIDING` remains `RESEARCH_ONLY` with an
`APPROXIMATE_GEOMETRIC_CONTACT_TANGENT`, `NO_ENERGY_CLAIM` and
`UNQUALIFIED_RESTART`. Friction, surface-to-surface, mortar, self-contact,
impact, dynamics and MPI/PETSc contact are excluded.

## Common structural benchmark

Both formulations use the same physical body and the same downward uniform
traction. Only the nodal representation of that traction is produced by the
qualification harness.

| Quantity | Frozen definition |
| --- | --- |
| Body | rectangular TET4 block |
| Coordinates | `x=[0,1]`, `y=[0,0.5]`, `z=[0.01,0.21]` |
| Dimensions | length `1.0`, width `0.5`, height `0.2` |
| Initial clearance | `0.01` above the fixed master plane |
| Material | isotropic 3-D, `E=1.0e6`, `nu=0.30` |
| Body BCs | `UX=0` on `x=0`; `UY=0` on `y=0`; no body `UZ` clamp |
| Master | one fixed triangle `[(0,0,0),(2,0,0),(0,1,0)]`, ordered normal `+Z` |
| Contact | body bottom-face nodes to the fixed master triangle; frictionless |
| Constraints | no MPC or RBE links |
| Load | constant traction `[0,0,-100000]` on the full top rectangle |
| Resultant | `[0,0,-50000]` |
| Origin moment | `[-12500,25000,0]` |

The master face orientation is checked before any future solve. The top
rectangle is triangulated deterministically by the frozen TET4 boundary
connectivity. For every top T3 face, the harness integrates the constant
traction against the linear face shape functions, giving `traction*area/3`
to each face node and accumulating shared-node contributions. The public
solver receives only these nodal dead loads; no distributed-load production
feature is introduced. The total resultant and the moment about the global
origin are checked at every level with absolute tolerance `1e-12`.

This is a consistent equivalent nodal representation of the same physical
uniform traction for both formulations. The rule is intended for future
cross-family WP07-E comparison as well; equal sharing over all end nodes is
not the final qualification rule.

## Deterministic mesh series

Exactly three levels are frozen for each benchmark. Each structured base cell
is split into six TET4 elements using the diagonal `v0-v6` and the ordered
pattern below:

```text
(v0,v1,v2,v6) (v0,v2,v3,v6) (v0,v3,v7,v6)
(v0,v7,v4,v6) (v0,v4,v5,v6) (v0,v5,v1,v6)
```

The orientation policy is deterministic: compute signed reference volume,
reject zero or nonfinite values, and swap the last two local nodes if the
volume is negative. Mesh generation must report finite coordinates, positive
orientation, deterministic connectivity and positive boundary-face area
before a solve. Midside nodes are not applicable because the bounded
structural contract deliberately uses TET4 only.

| Level | Base cells | Body nodes | Total nodes | TET4 | DOFs | Contact nodes | Master facets | Top T3 faces | Planning class |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| M1 | `2x2x1` | 18 | 21 | 24 | 63 | 9 | 1 | 8 | TINY |
| M2 | `4x4x2` | 75 | 78 | 192 | 234 | 25 | 1 | 32 | LIGHT |
| M3 | `8x8x4` | 405 | 408 | 1536 | 1224 | 81 | 1 | 128 | MODERATE |

The planning sparse orders are approximately:

| Level | Active-set augmented dimension / nonzeros | Penalty tangent nonzeros |
| --- | ---: | ---: |
| M1 | `72 / 1260` | `1251` |
| M2 | `259 / 6815` | `6774` |
| M3 | `1305 / 43821` | `43668` |

These are topology/planning estimates, not measured solve-resource
qualification. They exclude Newton vectors, assembly overhead, Krylov or
factorization storage/fill-in, Python, telemetry and process contention.
M1/M2/M3 execution remains blocked while Agent A's WP04 campaign has CPU/RAM
priority.

## Benchmarks and observables

### Active-set benchmark

The active-set case is one static compression case at load factor `1.0`.
The top-face displacement observable is the mean `UZ` of all loaded top-face
nodes. Evidence must include the displacement, support reaction resultant and
origin moment, active-contact count/area-weighted contact region, contact
pressure/resultant, minimum signed gap and normalized gap,
complementarity, and global force/moment equilibrium. No contact-edge point
stress is a primary observable.

The active-set restart claim is deliberately narrow: a fresh solve may
recompute route-local active-set state, but a mid-solve checkpoint/restart is
`UNSUPPORTED` under WP07-B.

### Nonlinear penalty benchmark

The penalty case uses `penalty=1.0e8`, penetration scale
`F_char/penalty=5.0e-4`, and load factors
`[0.125,0.25,0.375,0.5,0.625,0.75,0.875,1.0]`. Adaptive load steps are
disabled for this first frozen campaign. The existing canonical
geometric-static line-search policy is used without an experimental override;
Newton tolerance is `1e-9` with at most 30 iterations.

Evidence must include the same displacement/reaction/resultant/moment
observables, maximum and normalized penetration, fixed-normal penalty contact
energy where valid, global force/moment equilibrium, accepted load-factor
history, Newton iteration count and terminal status. A penalty checkpoint
restores accepted state and compatible WP07-B metadata; stateless penalty
contact is re-evaluated rather than serialized as independent history.

The optional stress observable is an averaged Cauchy `sigma_zz` over the fixed
reference-coordinate region
`0.40<=X/L<=0.60`, `0.20<=Y/W<=0.80`, `0.25<=Z/H<=0.75`, using reference-volume
weights. It is never sampled at the contact singularity.

## Scales and immutable candidate policies

The frozen scales are:

* `L_char = 1.0` (body length)
* `F_char = 50000` (norm of the total external resultant)
* `M_char = F_char*L_char = 50000`
* `U_char = F_char*body height = 10000`
* `E_char = 1.0e6`
* `P_char = F_char/top area = 100000`
* initial-gap scale `0.01`
* penalty penetration scale `0.0005`

Before any result exists, the Owner-candidate M2→M3 limits are frozen as
follows:

| Observable | Relative limit |
| --- | ---: |
| selected displacement | 3% |
| reaction resultant | 2% |
| reaction moment | 3% |
| contact resultant | 3% |
| active-set contact-region measure | 10% |
| penalty normalized penetration | 5% |
| penalty contact energy, when valid | 5% |
| optional averaged stress | 12% |

Force and moment equilibrium each require relative error `<=1e-8`. The
active-set identity limits are normalized gap `1e-10`, wrong-sign pressure
`1e-12`, complementarity `1e-10` and open contact force `1e-12`, inherited
from the bounded WP07-A/C contract. H1 replay requires relative difference
`<=1e-12`, absolute floor `1e-14`, equal load-history length and elementwise
history tolerance at the same limits, exact Newton-count equality and equal
qualitative contact status. These are prospective policies, not thresholds
tuned after results.

Missing or nonfinite required observables are failures. An open case is
recorded as `PASS_OPEN_NO_CONTACT` only for its negative-case purpose; it does
not infer a contact-qualification pass.

## Reference and external-comparison protocol

The primary independent comparison is a separately assembled reduced
reference implementation on the identical TET4 mesh, nodal loads, master
triangle, fixed normal and penalty value. It must not call the production
contact evaluator. A Code_Aster or other external comparison may be added
only after explicit mapping of units, geometry/nodes, BCs, load distribution,
contact enforcement, penalty/constraint parameters, normal orientation and
reported observables.

Displacement, reaction resultant/moment, active region/count, contact
resultant/penetration and path/status are compared only where the formulation
and load control are equivalent. Averaged stress may be compared only in the
declared reference region. Incompatible or unavailable references are
`EXTERNAL_REFERENCE_NOT_EQUIVALENT` and are not qualification evidence; no
external solver is run in this preparation task.

## Negative cases and fail-closed behavior

The future harness prepares typed guards for:

* reversed master-face orientation — preflight validation failure, no PASS;
* no actual contact — explicit `PASS_OPEN_NO_CONTACT`, with no contact claim;
* excessive penalty penetration — route-native
  `NumericalConvergenceError`/`CONTACT_PENETRATION_EXCESSIVE`;
* unsupported contact combination — `UNSUPPORTED_EXPLICIT`, with no fallback;
* nonfinite required observable — evidence-validation failure, never NaN/Inf;
* incompatible restart metadata — WP07-B `InputValidationError`, fail closed.

The negative cases are guards, not additional structural campaign results.

## Harness and provenance

`scripts/prepare_wp07d_structural_vnv.py` validates this contract and emits a
no-solve preflight plan for the six future cases:
`ACTIVE_SET/PENALTY × M1/M2/M3`. It provides deterministic output paths,
immediate-flush progress policy, source SHA, dirty-status and environment
capture, case definition provenance and placeholders for wall time, peak RSS,
private/USS, result JSON and evidence manifest. Its execution guard keeps
structural and external execution disabled until WP04 M3 completion.

The future execution must preserve the benchmark contract separately from
the nonlinear termination policy, so a later Owner-approved policy can be
supplied without rewriting the physics, mesh or load definition.

## Governance

This artifact is a contract freeze candidate only. It does not award WP07-D
points, promote either contact formulation, or change solver mechanics. No
structural solve, external solver, large Newton run, MPI/PETSc run or full
suite is authorized in this phase.

WP07-A technical candidate: `1/1` (formal `0/1`)
WP07-B technical candidate: `2/2` (formal `0/2`)
WP07-C technical candidate: `2/2` (formal `0/2`)
WP07-D formal points: `0/3`
WP07 points: `0/10`
Validated total: `29/100`

Next step: Owner freeze of this contract; execute M1/M2/M3 only after WP04
M3 completion and explicit authorization.
