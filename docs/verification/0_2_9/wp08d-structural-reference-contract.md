---
doc_id: DOC-029-WP08D-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-D — Frictional structural and independent-reference contract

This is a preparation-only contract. It freezes one bounded structural
qualification problem before any contact result is generated. WP08-D remains
`0/2` formal points; the preparation evidence does not qualify frictional
structural behavior and does not change maturity.

## Bounded scope

The future campaign is restricted to:

- `linear_static`, small displacement, serial direct execution;
- TET4 solid elements and node-to-triangle contact;
- fixed initial master face and fixed normal;
- Lagrange normal active set with the existing regularized Coulomb tangential
  law;
- positive `mu` and positive `tangential_stiffness`.

Updated search, finite sliding, geometric/material nonlinear friction,
dynamics, surface-to-surface or mortar contact, augmented Lagrangian,
friction restart qualification and MPI/PETSc are excluded. The campaign must
not silently broaden this list after results exist.

## Benchmark and supports

The benchmark is an elastic 3-D block above a rigid two-facet planar master
surface:

| quantity | frozen value |
| --- | ---: |
| body length `Lx` | `2.0 m` |
| body width `Ly` | `1.0 m` |
| body height `Lz` | `0.5 m` |
| master plane | `z = 0 m` |
| initial body clearance | `0.02 m` |
| reference volume | `1.0 m³` |
| material | isotropic 3-D |
| `E` | `1.0e6 Pa` |
| `nu` | `0.30` |

The body nodes on the `x=0` face are fully clamped in `UX/UY/UZ`. The four
rigid master nodes are also fixed in the future model. This removes rigid-body
modes before contact activates. Bottom body nodes with `x>0` are the slave
region. The bottom row on the clamped `x=0` face is deliberately excluded:
those nodes remain at positive initial clearance and cannot become active.

The master plane is the rectangle with local nodes
`[(0,0,0), (2,0,0), (2,1,0), (0,1,0)]` and faces `(0,1,2)` and `(0,2,3)`.
The normal is `[0,0,1]`. A slave on the diagonal is assigned to face 0 when
`y/Ly <= x/Lx + 1e-12`; otherwise it is assigned to face 1. The assigned
triangle barycentric coordinates must be non-negative within `1e-12`.

## Friction and frozen load path

The frozen contact parameters are:

```text
mu                    = 0.30
tangential_stiffness  = 1.0e6 N/m
gap_tolerance         = 1.0e-10 m
friction_tolerance    = 1.0e-9 N
search                = initial_fixed_face_normal
```

The physical top-face loads are separate from the contact response:

```text
F_normal       = [0, 0, -1000] N
F_tangential*  = [300, 0, 0] N
```

The future load history keeps the normal factor at `1.0` and uses tangential
factors `[0, 0.25, 0.75, 1.0, 1.25, 0.25, -0.5]`. The names are respectively
normal preload, clear stick, stick regime, nominal crossing, established
slip, unload and bounded reversal. This is a prospective path: actual
stick/slip status is an observation, never an assumed PASS.

The load is integrated on every top T3 boundary face using constant traction
and the consistent `area/3` contribution to each face vertex. This is the
same physical uniform traction at every level; only the TET4 representation
changes. The top-face centroid is `[1.0, 0.5, 0.52] m`. Expected moments about
the global origin are:

```text
normal load       [-500, 1000,   0] N m
tangential load*  [   0,  156, -150] N m
```

The declared vector check is relative `1e-12` with an absolute floor of
`64 * machine_epsilon * max(norm(expected), 1)`. Force and moment vectors,
not only a scalar component, are recorded.

## Exact mesh series

Each structured hexahedral cell is split into six TET4 elements along the
`v000-v111` body diagonal. Traversal is lexicographic `k,j,i`. If a generated
tetrahedron has negative signed volume, the last two local nodes are swapped;
zero or non-finite volume fails closed. The model node count includes the
four rigid master nodes; `body_nodes` is reported separately.

| level | subdivision `(nx,ny,nz)` | body nodes | model nodes | TET4 | model DOFs | slave nodes | master facets | top T3 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M1 | `(2,1,1)` | 12 | 16 | 12 | 48 | 4 | 2 | 4 |
| M2 | `(4,2,2)` | 45 | 49 | 96 | 147 | 12 | 2 | 16 |
| M3 | `(8,4,4)` | 225 | 229 | 768 | 687 | 40 | 2 | 64 |

The expected volume is `1.0 m³` at all levels. The generator checks finite
coordinates, positive reference volumes, deterministic connectivity, unique
master nodes, top/bottom boundary extraction and master projection coverage.
No fourth mesh is declared; `M4` is not an implicit rescue option.

## Scales and observables

The prospective physical scales are:

```text
L_char             = 2.0 m
F_char             = 1000 N
M_char             = F_char * L_char = 2000 N m
P_char             = 500 Pa
penetration_scale  = 0.02 m
energy_scale       = 2000 J
```

The structural result record must contain selected displacement, support
reaction vector/resultant and moment vector, normal and tangential contact
resultants, active count/region measure, mean and maximum pressure, global
stick/slip fractions, representative tangential slip, cumulative local
dissipation and vector force/moment equilibrium. Any stress diagnostic must be
an averaged reference-coordinate region away from the contact singularity.

## Refinement and equilibrium gates

Only the declared M2-to-M3 comparison is used for primary refinement. For a
scalar or vector norm `q`:

```text
delta(q) = abs(q_M3 - q_M2)
           / max(abs(q_M3), abs(q_M2), scale_floor)
scale_floor = max(1e-14, 64 * machine_epsilon * declared_physical_scale)
```

Missing or non-finite values are `FAIL_CLOSED`. Owner-candidate limits,
frozen before execution, are:

| observable | limit |
| --- | ---: |
| selected displacement | 3% |
| reaction resultant | 2% |
| reaction moment | 3% |
| normal contact resultant | 3% |
| tangential contact resultant | 3% |
| active-contact region measure | 10% |
| stick/slip region measure | 10% |
| cumulative dissipation | 5% |
| optional averaged stress | 12% |

Every converged level must independently satisfy:

```text
force  = ||R_support + F_external|| / max(||R_support||, ||F_external||, F_char, floor) <= 1e-8
moment = ||M_reaction + M_external|| / max(||M_reaction||, ||M_external||, M_char, floor) <= 1e-8
```

For closed contacts, the future record checks the existing WP07 normalized
gap/complementarity contract, non-negative compression pressure, and
`||t|| <= mu*p` for stick or `||t|| ~= mu*p` for slip. Not every contact is
required to slide.

## Dissipation and replay

The local dissipation convention is the WP08-C convention:

```text
D_increment = sum(force dot delta_slip_reference)
```

Values must be finite; cumulative dissipation must not decrease beyond
`-1e-14 * max(energy_scale, 1)`; open/stick increments are zero where
applicable; and a path with actual slip must have positive total dissipation.
No global energy decomposition is claimed.

The independent replay is planned on M1 with relative tolerance `1e-12` and
absolute floor `1e-14`. It compares final displacement, reaction and moment
vectors, normal/tangential contact resultants, active count, qualitative
stick/slip state, history length and load factors, cumulative dissipation and
terminal classification.

## Independent reference

The primary reference is an independently assembled small KKT plus Coulomb
return-map implementation. It must set:

```text
INDEPENDENT_IMPLEMENTATION = YES
PRODUCTION_CONTACT_ROUTINES_CALLED = NO
FORMULATION_MATCH_REQUIRED = YES
```

It matches geometry or a declared reduced equivalent, `mu`, tangential
stiffness, fixed normal/initial face, normal Lagrange contact, load path and
supports. An external solver is optional and usable only if the mapping is
explicitly exact. The comparison limits are displacement 2%, reaction 2%,
reaction moment 2%, normal contact resultant 3%, tangential contact
resultant 3%, slip measure 5% and cumulative dissipation 5%. No reference
result is generated in Phase 0.

## Negative cases and failure classification

The future safety controls are `mu<0`, non-finite `mu`, non-positive
tangential stiffness with friction active, open/no-contact, zero normal
pressure, reversed master orientation, unsupported updated-search friction,
non-finite state, forced rejected increment and restart without qualified
friction state. These are safety evidence only and never structural
qualification passes.

Controlled failure classes are:
`FORMULATION_FAILURE`, `CONTACT_ACTIVE_SET_FAILURE`,
`FRICTION_RETURN_MAP_FAILURE`, `EQUILIBRIUM_FAILURE`, `REFINEMENT_FAILURE`,
`REFERENCE_MISMATCH`, `REPLAY_FAILURE`, `RESOURCE_LIMIT`, `INVALID_INPUT`,
`UNSUPPORTED_EXPLICIT`, `NONFINITE_STATE` and `UNKNOWN`. The harness fails
closed and must not silently retry with altered physics.

## Resource and execution guard

Planning-only estimates are:

| level | rough nnz | memory class | runtime class |
| --- | ---: | --- | --- |
| M1 | 400 | TINY | TINY |
| M2 | 7,000 | LIGHT | LIGHT |
| M3 | 110,000 | MODERATE | MODERATE |

These estimates exclude Newton state, Krylov/preconditioner storage,
factorization fill-in, process/Python overhead and telemetry. Solve readiness
is `UNKNOWN_PENDING_PHASE1_MEASURED_M1`. Agent A retains CPU/RAM priority.

The preparation helper defaults both `STRUCTURAL_SOLVES_ENABLED` and
`EXTERNAL_SOLVER_ENABLED` to `FALSE`. Requesting either without explicit
Owner Phase-1 authorization raises a deterministic guard error. Phase 0
performs only mesh/load checks and the permitted M1 no-contact stiffness
precheck; it does not call the contact or structural solver.

The M1 precheck assembled a finite reduced no-contact stiffness with 24 free
DOFs, minimum eigenvalue approximately `4.9505068683e3`, above the numerical
zero threshold `4.6261676093e-8`. This is well-posedness preflight evidence,
not a contact qualification result.

## Governance and artifacts

The controlled artifacts are:

- `qualification/0_2_9/wp08d_structural_reference_contract.json`;
- `scripts/prepare_wp08d_structural_reference.py`;
- `tests/unit/test_wp08d_structural_reference_contract.py`.

WP08-A/B/C remain technical candidates `1/1`, `2/2`, `2/2`; WP08-D formal
points remain `0/2`, WP08 remains `0/8`, and `VALIDATED_TOTAL` remains `29/100`.
Structural and external execution require the WP04 governing-policy
integration train and explicit Owner Phase-1 authorization.
