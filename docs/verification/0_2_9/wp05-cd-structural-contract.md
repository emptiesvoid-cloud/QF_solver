---
doc_id: DOC-029-WP05-CD-STRUCTURAL-CONTRACT-001
revision: 0.2
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP05-C/D — TET10 and HEX20 structural benchmark contract

**Preparation status:** `PREPARATION_VALIDATED_PENDING_STRUCTURAL_EXECUTION`

**Formal points:** `WP05-C 0/1`, `WP05-D 0/1`, `WP05 2/5`

**Validated release total:** `45/100`

This document freezes the prospective bounded structural benchmark for the
quadratic solid families.  It is a contract and mesh-quality record, not a
qualification result.  H2/H3 mechanical solves are intentionally not run
while the independent Agent A WP04-C2R6 campaign is active.  No production
source, mechanics formulation, maturity, or Owner decision was changed.

### Owner correction R1

The initial preparation artifact used equal force shares over all `x = L`
nodes.  That rule is retained here as historical provenance only: it was
Owner-rejected before any mechanical solve because it does not represent the
same uniform quadratic-face traction across TET10 and HEX20 topologies.  The
final contract below uses consistent equivalent nodal traction.  No prior
mechanical result is being rewritten.

## Bounded scope

The future cases are one homogeneous straight-sided family at a time:

- `TET10` for WP05-C, using the current Hammer-4 default;
- `HEX20` for WP05-D, using full 27-point Gauss integration;
- `linear_static`/small-strain material initialization followed by the
  existing canonical geometric-static route under the Owner-approved C2R6
  governing nonlinear policy;
- the same physical uniform traction for both families, represented by their
  family-specific consistent equivalent nodal forces;
- isotropic linear `SolidMaterial`, with `E = 1.0e6` and `nu = 0.30`;
- no curved TET10 claim, reduced-integration/hourglass claim, contact,
  plasticity, mixed mesh, mixed material, distributed-load route, or external
  correlation is included here.

Future structural execution is bound to governing SHA
`12b5331bcbec49e38145ba4a6263df60b8bf4575` and policy digest
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`:
canonical existing line search, floor-aware termination, MINRES plus Jacobi,
`rtol=1e-11`, `atol=1e-14`, `maxiter=10000`, and no direct fallback. This
integration does not authorize an H1/H2/H3 structural run or any policy change.

## Frozen physical benchmark

The rectangular domain is `L = 4.0`, `H = 0.5`, `D = 0.5`, with volume `1.0`.
All displacement DOFs on the `x = 0` face are fixed.  The physical load is a
uniform traction on the `x = L` face with total resultant `[0, -50, 0]`.
The public solver still receives nodal dead loads; only this qualification
harness performs the surface integration.

TET10 integrates quadratic T6 boundary faces with the three-point degree-2
triangle rule in barycentric coordinates.  HEX20 integrates quadratic Q8
boundary faces with tensor 2x2 Gauss.  Every boundary-face contribution is
assembled into the shared global node ids, including shared midside nodes.
The traction is computed from the integrated end-face area, so both families
represent the same physical load rather than the same topology-dependent
nodal weights.  The resultant is checked with an explicit absolute tolerance
of `1.0e-12`; this only accounts for floating-point summation.

The analytical uniform-traction moment about the global origin is computed at
the end-face centroid `(L, H/2, D/2)`.  For this benchmark it is
`[12.5, 0.0, -200.0]`, including the requested `Mz = -200` sign.  All three
force and all three moment components are recorded.  The moment check uses a
predeclared scale-aware relative tolerance of `1.0e-12` with an absolute
floor of `1.0e-12`.

The structured node id is
`i + (nx + 1) * (j + (ny + 1) * k)`, with `x` as the fastest index.  The
declared levels are:

| Level | Base cells `(nx, ny, nz)` |
|---|---:|
| H1 | `(4, 2, 2)` |
| H2 | `(8, 4, 4)` |
| H3 | `(16, 8, 8)` |

HEX20 uses the conventional eight-corner order and the twelve edge order
`(0,1),(0,3),(0,4),(1,2),(1,5),(2,3),(2,6),(3,7),(4,5),(4,7),(5,6),(6,7)`.
Midside nodes are globally keyed by sorted endpoint ids, so adjacent cells
are conforming and cannot create duplicate edge nodes.

TET10 splits every base hexahedral cell into the frozen six-tet pattern:

```text
(0,1,2,6), (0,2,3,6), (0,3,7,6),
(0,7,4,6), (0,4,5,6), (0,5,1,6)
```

The internal TET10 order is corners followed by edges
`(0,1),(1,2),(2,0),(0,3),(1,3),(2,3)`.  A non-positive corner orientation
causes the deterministic local swap of corners 2 and 3; a second non-positive
check rejects the mesh.  All generated meshes are straight-sided, with unique
global midside nodes.

## Prepared mesh inventory

These are mesh-generation results only; no H1/H2/H3 structural solve was
executed.

| Family | Level | Nodes | Elements | DOFs | Loaded-face nodes |
|---|---:|---:|---:|---:|---:|
| TET10 | H1 | 225 | 96 | 675 | 25 |
| TET10 | H2 | 1,377 | 768 | 4,131 | 81 |
| TET10 | H3 | 9,537 | 6,144 | 28,611 | 289 |
| HEX20 | H1 | 141 | 16 | 423 | 21 |
| HEX20 | H2 | 785 | 128 | 2,355 | 65 |
| HEX20 | H3 | 5,121 | 1,024 | 15,363 | 225 |

For every generated level, the harness checked finite coordinates, indexing,
local connectivity uniqueness, midside uniqueness/conformity, positive
orientation/Jacobian, volume, the resultant, and all three external-moment
components.  The checks passed.  H1 mesh generation and consistent load
assembly are deterministic on repeated construction.

For TET10 the minimum H1 Hammer-4 Jacobian is `6.2499999999999924e-2` and
the minimum H3 sampled Hammer-4 Jacobian is
`9.765624999999896e-4`; all sampled values are finite and positive.  For
HEX20 all 27 Gauss points per element are finite and positive; the minimum is
`7.812499999999967e-3` on H1 and `1.2207031249999574e-4` on H3.

## Frozen observables and policies

The future result schema contains:

1. mean `Y` displacement over all `x = L` face nodes;
2. three-component clamp reaction resultant, the sum over all `x = 0` face
   reaction rows;
3. three-component clamp reaction moment about the global origin;
4. strain energy;
5. reference-coordinate and reference-volume weighted Cauchy `sigma_xx` in
   `0.40 <= X/L <= 0.60`, `0.70 <= Y/H <= 0.95`, and
   `0.20 <= Z/D <= 0.80`; records must provide
   `reference_coordinates` and positive `reference_volume_weight = w_q det(J0)`.
   Deformed coordinates and current-volume weights are not used;
6. minimum `det(F)`;
7. minimum and maximum principal stretches from the singular values of `F`;
8. maximum Frobenius norm of Green--Lagrange strain;
9. accepted load-factor history;
10. total Newton iteration count from the route diagnostics.

The bounded deformation envelope is `det(F) >= 0.20`, principal stretches in
`[0.75, 1.30]`, and `||E_GL||_F <= 0.30`.  This is a scope boundary, not a
claim of universal Saint-Venant--Kirchhoff validity.

For each family, the prospective H2-to-H3 limits are displacement, reaction
resultant, reaction moment, and strain energy `<= 2%`, and representative
`sigma_xx <= 8%`.  Every converged mesh must also satisfy force and moment
equilibrium relative errors `<= 1.0e-8`.  These thresholds were frozen before
future H2/H3 results and must not be tuned after observation.

The harness `check_replay` requires every scalar above, all three components
of the reaction resultant and moment, the accepted load-factor history, and
the Newton iteration count.  Floating values use relative difference
`<= 1.0e-12` with absolute floor `1.0e-14`; histories require equal length and
elementwise tolerance; the Newton count requires exact equality.  Missing or
non-finite values fail closed.  Binary state hash equality is not required.

The harness `evaluate_equilibrium` checks vector force and vector origin
moment residuals using relative error `<= 1.0e-8`, and records all components.
The `evaluate_mesh_delta` helper applies the frozen H2-to-H3 thresholds for
displacement, reaction resultant, reaction moment, energy, and representative
stress.  Missing or non-finite observables are failures rather than skipped
checks.

## Resource estimate

The following preparation/storage estimates include coordinate/connectivity
storage, bounded staged triplets, and a raw tangent-entry CSR upper bound.
`MESH_RESOURCE_ESTIMATE = AVAILABLE`; these are not measured solve memory and
do not award qualification points.  They exclude Newton state vectors,
assembly runtime overhead, Krylov workspace, preconditioner storage, sparse
factorization fill-in, Python/SciPy overhead, telemetry, and process
overhead.  Consequently `SOLVE_RESOURCE_READINESS =
UNKNOWN_PENDING_MEASURED_H1` and no H2/H3 solve-resource claim is made.

| Family | Level | Raw tangent entries (upper bound) | Rough memory |
|---|---:|---:|---:|
| TET10 | H1 | 86,400 | 2.979 MiB |
| TET10 | H2 | 691,200 | 16.789 MiB |
| TET10 | H3 | 5,529,600 | 109.671 MiB |
| HEX20 | H1 | 57,600 | 1.983 MiB |
| HEX20 | H2 | 460,800 | 15.858 MiB |
| HEX20 | H3 | 3,686,400 | 84.648 MiB |

Mesh construction is practical on the current host.  H2/H3 qualification
solves remain blocked by WP04 governance and Agent A resource contention;
these estimates are not permission to start that campaign.

## Evidence and execution status

The preparation harness is
`scripts/wp05_cd_structural_harness.py`, with targeted tests in
`tests/verification/test_wp05_cd_structural_harness.py`.  It emits the
machine-readable contract/evidence schema in
`qualification/0_2_9/wp05_cd_structural_contract.json` and can evaluate future
precomputed solver outputs without invoking a solver.  The evidence records
the benchmark definition, mesh counts, quality checks, consistent load/moment
checks, reference-region policy, replay/equilibrium evaluators,
termination-policy provenance, execution flags, and the explicit fact that
Agent A's policy was not imported.

The authorized smoke solve and H1 replay were skipped while Agent A's
long-running campaign is active.  H2 and H3 qualification runs are `NO`.
WP05-C and WP05-D therefore remain `PASS_CANDIDATE_PENDING_WP04`, with formal
points `0/1` each and no maturity change.
