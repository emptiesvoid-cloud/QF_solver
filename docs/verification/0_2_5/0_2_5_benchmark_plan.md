---
doc_id: DOC-NL-025-009
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 benchmark plan

## Common protocol

Each benchmark stores mesh/input digests, SHA, machine/OS/Python/dependency
versions, warm-up policy, repetitions, CPU and wall time, peak/estimated memory,
DOF, nnz, Newton iterations, linear iterations, retries and residual histories.
Performance assertions use a frozen baseline and variability band from WP0.

| ID | Work package | Benchmark | Families / path | Primary outputs | Reference |
|---|---|---|---|---|---|
| BM-025-00 | WP0 | published 0.2.4 baseline replay | existing release suite | numerical snapshots, coverage, cost | v0.2.4a0 |
| BM-025-01 | WP1 | meshed elastoplastic bar/coupon | TET4/TET10/HEX8/HEX20 | F-u, reaction, VM, PEEQ, energy, iterations | analytical + external |
| BM-025-02 | WP1 | cyclic material/structure path | load/unload/reload/reversal | hysteresis path within isotropic law, state | analytical law + external |
| BM-025-03 | WP1 | rollback/cutback equivalence | forced large increment | final state, retries, digests | direct small-step run |
| BM-025-04 | WP2 | rigid rotation/objectivity | TET4/HEX8 | stress, force, energy | exact zero response |
| BM-025-05 | WP2 | large-rotation cantilever | TET4/HEX8, high order SHOULD | load-displacement, energy, mesh trend | published + external |
| BM-025-06 | WP3 | Euler column | verified solid discretization | critical factor/mode/cost | analytical Euler |
| BM-025-07 | WP3 | nontrivial buckling case | selected solid/plate case | factor/mode/mesh trend | external |
| BM-025-08 | WP4 | shallow arch snap-through | common nonlinear core | full lambda-u branch, limit point | published + external |
| BM-025-17 | WP4 | finite-kinematic adaptive arc-length path | TET4/TET10/HEX8/HEX20 `total_lagrangian_j2` | signed load factor, radius history, residual, steps | bounded internal research contract |
| BM-025-09 | WP5 | frictionless block/plane | finite sliding/open-close | reaction, gap, active set, penetration | analytical + external |
| BM-025-10 | WP5 | curved/recontact case | finite sliding | trajectory, contact pressure, convergence | external |
| BM-025-11 | WP6 | J2 + geometry | approved coupled model | F-u, VM, PEEQ, energy | external |
| BM-025-12 | WP6 | geometry + contact | deformable contact | load-gap-u, pressure, reaction | external |
| BM-025-13 | WP6 | triple coupling SHOULD | J2+geometry+contact | complete histories | external |
| BM-025-14 | WP7 | friction block cycle COULD | stick/slip/reversal | slip, traction, dissipation | analytical + external |
| BM-025-15 | WP8 | HEX20 cost decomposition | elastic/J2/geometric | Gauss, constitutive, assembly, copy, solve | frozen baseline |
| BM-025-16 | WP9 | adversarial suite | every mandatory solver | structured failure and state safety | contract |
| BM-025-18 | WP5/WP8 | bounded finite-sliding diagnostic path | TET4 opt-in common Newton | projection mode, face switch, gap, penetration, sparse tangent, timing/RSS | internal contract; no general contact claim |

The following bounded observations are now available in the internal robustness
campaign (they remain provisional evidence, not closed release gates):

- `BM-025-06`: TET4/HEX8 critical-factor and sparse tangent-bracket smoke;
- `BM-025-08`: proportional arc-length continuation to load factor one;
- `BM-025-08`: reduced shallow-arch branch following through the analytical
  limit point, with equilibrium error and branch-turn diagnostics. This is
  algorithmic internal evidence only; the FEM snap-through case remains open;
- `BM-025-17`: all four finite-kinematic solid families reach signed load
  factor `0.5` with the common driver and a bounded adaptive radius. This is
  monotone internal research evidence only; no FEM snap-through, post-buckling
  or external correlation claim is made. The opt-in performance path is
  `python scripts/benchmark_nonlinear_025.py --path arc_length_finite_kinematic`.
  The latest four-family replay is archived at
  `results/benchmark_0_2_5/arc_length_finite_kinematic_latest.json` and all
  four rows pass with residuals at or below `9.90e-08`. HEX20 required the
  explicit `max_arc_steps=512` benchmark budget and completed in `319` steps;
  this is a continuation-budget observation, not a performance target.
- `BM-025-09`: common penalty contact open/close activation and Newton smoke.
- `BM-025-18`: the explicit path
  `python scripts/benchmark_nonlinear_025.py --path finite_sliding` now runs a
  one-step common Newton contact case. The recorded smoke uses 15 DOF, one
  Newton iteration, one clamped projection with the serialized mode
  `bounded_closest_point_node_to_triangle`, nine sparse tangent entries and a
  finite residual. It is a bounded internal diagnostic, not a surface-to-
  surface or production finite-sliding qualification.
- `BM-025-15`: explicit profiling paths for load-control,
  `geometric_nonlinear_static`, arc-length, contact and coupled execution, with
  elapsed time, phase timings, allocations and optional RSS. A local HEX20
  load-control replay also measured the
  redundant geometry-validation hotspot: 114.288 s to 17.321 s total and
  96.639 s to 11.573 s assembly on the same 96-DOF case. This remains
  provisional until repeated on a clean SHA with numerical before/after
  comparison.
- `VV-061` / `BM-025-15` now also records component-level phase telemetry for
  the four-family load-control replay: element setup, element kernel,
  element scatter, sparse conversion, contact assembly, tangent `nnz`,
  nonlinear assembly-plan cache hits/misses, Python allocation peak and RSS
  samples. This identifies the current HEX20 hotspot and verifies reuse of
  immutable assembly objects without claiming a scaling law or a release
  performance target.
- The cache replay is archived at
  `results/benchmark_0_2_5/nonlinear_load_control_cache_latest.json`. It
  converged for all four families with zero cache misses during Newton
  assembly. The setup-time reduction is exploratory, single-run evidence on a
  dirty worktree and does not close G08.
- A two-repeat all-family replay is archived at
  `results/benchmark_0_2_5/nonlinear_load_control_all_families_repeats2.json`.
  It contains eight converged runs across TET4/TET10/HEX8/HEX20 and records
  phase timings, residuals, Newton counts, Python allocation peaks and RSS
  samples. It is still dirty-worktree characterization and does not close G08.
- `BM-025-07`: the first shared solid-family CalculiX buckling probe is archived
  at `results/vnv_0_2_5/calculix_buckling_solid_families_mode1_recorded/`.
  The deck uses a fixed boundary, one requested mode and a Lanczos subspace
  bounded by the free-equation count. It is still negative evidence: TET4,
  TET10 and HEX8 remain outside the 10 % band and C3D20 stops natively. No
  buckling correlation claim is made from it.

## Scale bands

- **CI-small:** seconds, deterministic contract tests.
- **Engineering-medium:** multi-element mesh/convergence, minutes.
- **Evidence-heavy:** external correlations and refined meshes, separately marked.

No million-DOF claim is planned. This release characterizes nonlinear costs at
engineering-medium scale and preserves existing sparse/HPC behavior.

## Acceptance discipline

Before changing a benchmarked path, WP0 records baseline repeatability and
freezes target/warning/reject bands. Faster execution cannot compensate for a
failed physical/numerical metric. Performance regressions may be accepted only
with an Owner-reviewed reason and an updated limitation.
