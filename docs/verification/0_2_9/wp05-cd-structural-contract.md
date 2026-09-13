---
doc_id: DOC-029-WP05-CD-STRUCTURAL-CONTRACT-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP05-C/D — TET10 and HEX20 structural benchmark contract

**Preparation status:** `PREPARATION_ONLY_PENDING_WP04`

**Formal points:** `WP05-C 0/1`, `WP05-D 0/1`, `WP05 0/5`

**Validated release total:** `29/100`

This document freezes the prospective bounded structural benchmark for the
quadratic solid families.  It is a contract and mesh-quality record, not a
qualification result.  H2/H3 mechanical solves are intentionally not run
while the independent Agent A WP04-C2R6 campaign is active.  No production
source, mechanics formulation, maturity, or Owner decision was changed.

## Bounded scope

The future cases are one homogeneous straight-sided family at a time:

- `TET10` for WP05-C, using the current Hammer-4 default;
- `HEX20` for WP05-D, using full 27-point Gauss integration;
- `linear_static`/small-strain material initialization followed by the
  existing canonical geometric-static route, subject to the separately
  supplied approved nonlinear termination policy;
- isotropic linear `SolidMaterial`, with `E = 1.0e6` and `nu = 0.30`;
- no curved TET10 claim, reduced-integration/hourglass claim, contact,
  plasticity, mixed mesh, mixed material, distributed-load route, or external
  correlation is included here.

The benchmark contract is deliberately independent from nonlinear termination:
the harness accepts a future policy object and does not import Agent A's
experimental floor-aware C2R6 policy.

## Frozen physical benchmark

The rectangular domain is `L = 4.0`, `H = 0.5`, `D = 0.5`, with volume `1.0`.
All displacement DOFs on the `x = 0` face are fixed.  A total nodal dead load
of `[0, -50, 0]` is applied on the `x = L` face.

Nodes on the loaded face are selected by finite-coordinate `x == L`, sorted by
global node id, and receive equal shares of the declared total vector.  The
resultant is checked with an explicit absolute tolerance of `1.0e-12`; this
only accounts for floating-point summation and is not a post-result numerical
qualification threshold.  The rule is identical for every mesh level and
therefore keeps the physical resultant mesh-independent.

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
orientation/Jacobian, volume, and the load resultant.  The checks passed.  H1
mesh generation is deterministic on repeated construction.

For TET10 the minimum H1 Hammer-4 Jacobian is `6.2499999999999924e-2` and
the minimum H3 sampled Hammer-4 Jacobian is
`9.765624999999896e-4`; all sampled values are finite and positive.  For
HEX20 all 27 Gauss points per element are finite and positive; the minimum is
`7.812499999999967e-3` on H1 and `1.2207031249999574e-4` on H3.

## Frozen observables and policies

The future result schema contains:

1. mean `Y` displacement over all `x = L` face nodes;
2. clamp reaction resultant, the sum over all `x = 0` face reaction rows;
3. clamp reaction `Mz = sum(x*Ry - y*Rx)` about the global origin;
4. strain energy;
5. volume/integration-point weighted Cauchy `sigma_xx` in
   `0.40 <= x/L <= 0.60`, `0.70 <= y/H <= 0.95`, and
   `0.20 <= z/D <= 0.80` (only finite positive integration weights count);
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

H1 replay will compare the declared observables with relative difference
`<= 1.0e-12` and an absolute floor of `1.0e-14` where applicable.  Binary state
hash equality is not required by this contract.

## Resource estimate

The following conservative estimates include coordinate/connectivity storage,
bounded staged triplets, and a raw tangent-entry CSR upper bound.  They are
not measured solve memory and do not award qualification points.

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
the benchmark definition, mesh counts, quality checks, load/volume checks,
termination-policy provenance, execution flags, and the explicit fact that
Agent A's policy was not imported.

The authorized smoke solve and H1 replay were skipped while Agent A's
long-running campaign is active.  H2 and H3 qualification runs are `NO`.
WP05-C and WP05-D therefore remain `PASS_CANDIDATE_PENDING_WP04`, with formal
points `0/1` each and no maturity change.
