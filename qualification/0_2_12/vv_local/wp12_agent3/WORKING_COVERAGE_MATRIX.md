# WP12 Agent 3 working coverage matrix

**Development-only review; WP12/WP13 administrative statuses unchanged.**

Date: 2026-10-26; branch: test/wp12-fem-regressions; baseline: 6d8f140834db75ea9b968b055af23445261d0073.

This matrix records the bounded review and exact non-FEM sentinels completed in this worktree. It does not replace the official 62-capability matrix. No new FEM case was executed, so the task's 20-case development budget remains unused. No test source, solver source, runner, qualification evidence, threshold, or administrative status was changed.

## HEX8-SRI evidence and disposition

The WP10 record remains scoped to internal isotropic, small-strain, linear-static HEX8-SRI. Its frozen cases are structured cantilevers at ν=0.30 and ν=0.4999 with nx=4, 8, 16 and ny=nz=2. At ν=0.4999, the fine-level relative displacement errors were 0.3308208 for SRI and 0.8681885 for standard HEX8, a 0.6189528 error reduction. The recorded element probe had six rigid modes, no additional zero mode, constant-strain and patch errors of 3.33e-16, and an affine nodal-force-action difference of 0.8749535. The latter explicitly prevents a general affine patch-force claim. This evidence does not transfer to standard HEX8 or broaden the SRI formulation scope.

The later predeclared WP13-12 maturation record must also remain visible. Its decision is KEEP_EXPERIMENTAL, with equilibrium and energy gates FAIL and all other listed gates PASS. At ν=0.4999, the SRI force-balance residuals across nx=4, 8, 16 were 2.414e-9, 1.950e-9, and 2.085e-9; moment-balance residuals were 4.557e-9, 4.078e-9, and 4.924e-9. These exceed the frozen 1e-10 balance criteria. The near-degenerate valid-distortion energy error was 1.028e-9, above the frozen 1e-10 energy criterion. No gate was retuned.

The committed WP13-12 NPZ has eight summary arrays (patch eigenvalues, displacement-error summaries, and distortion summaries); it does not contain the assembled stiffness, displacement, load, or reaction vectors needed to independently recompute the failed balances. The report therefore preserves the recorded diagnosis but cannot isolate its root cause from the archived arrays alone. A minimal diagnostic should first reproduce the near-incompressible balance and near-degenerate energy failures, retaining K, u, F, reactions, and moment terms. It must not repeat the nx=4/8/16 campaign before that diagnostic or alter the existing gates.

## Capability coverage

| Capability | Historical/current tests or records | Tests run in this mission | Numeric observations and verdict | Limits and remaining priority |
|---|---|---|---|---|
| EL-HEX8-SRI | WP10 contract, V&V, and Owner gate; WP13-12 contract and maturation manifest; existing tests are record guards, not a current numerical node | None; NOT_RUN | Historical WP10 locking reduction 0.6189528 at ν=0.4999. WP13-12 keeps the capability experimental after equilibrium and energy failures. No new verdict. | P1: diagnose the frozen failures from a new minimal reproduction with full raw vectors. Do not infer standard HEX8 results or claim general patch-force validity. |
| EL-BEAM2 | Accelerated report selected the frozen WP03 BEAM2_STATIC analytic case, PASS | None; NOT_RUN | Historical bounded PASS; the report does not publish its measured error. | P2: transverse uniform line-load cantilever against the Timoshenko closed form, including load resultant and moment. Keep this separate from the prior static case. |
| EL-TET10 | tests/unit/test_tet10_element.py::test_tet10_patch_test_reproduces_affine_strain_and_energy, PASS in the accelerated report | None; NOT_RUN | Historical affine patch PASS; the report does not publish the error. | P2: curved-face traction/resultant and moment or a curved-geometry structural reference. Do not modify or repeat the Agent 2 TET4 work. |
| EL-HEX8 | tests/unit/test_hex8_element.py rigid-mode/stiffness and affine-field nodes, 2/2 PASS in the accelerated report | Gmsh import sentinel only; no solve | Import route PASS. No new stiffness or response observation. | P2: a distorted-geometry patch or bounded bending response with reactions and energy. Keep all standard HEX8 claims separate from SRI. |
| EL-HEX20 | tests/unit/test_hex20_element.py affine field and body/face resultant nodes, 2/2 PASS in the accelerated report | None; NOT_RUN | Historical interpolation and load-resultant checks PASS; no curved structural convergence claim. | P2: bounded cantilever/refinement or curved geometry with independent displacement and reaction references. |
| EL-MITC4 | tests/unit/test_mitc4_dynamics.py zero-Hz harmonic/static consistency with drilling condensation, PASS in the accelerated report | None; NOT_RUN | Historical dynamic/static consistency PASS; no new static plate error. | P2: static bending/shear-sensitive plate benchmark with a predeclared analytic/reference and mesh trend. |
| BACKEND-SPARSE / ASM-STATIC | Existing sparse aggregation implementation | Sparse accumulator exact-node sentinel, PASS | The accumulated 2x2 matrix matched the direct sparse sum; source inputs imply [[6,3],[4,8]]. This is an algebraic sparse-aggregation check, not global FEM assembly evidence. | P2: compare sparse global element assembly and matvec against a dense oracle on one explicitly authorized tiny model. |
| CON-MPC | Existing sparse affine MPC reduction | Elimination vs. Lagrange-multiplier sentinel, PASS | Constrained solution agreed within the test's 1e-12 absolute tolerance. This is a small algebraic system, not a structural-model RBE/MPC campaign. | P2: one supported assembled-model MPC or RBE2 case with full force and moment closure. |
| LOADS-REACTIONS | Existing distributed-load and support-reaction tests; accelerated report classifies this area as partial | None; no element-load integration or FEM solve run | No mission measurements. | P1: one bounded load case with independently computed resultant, moment, and support reactions. Preserve any mismatch. |
| POST-STRESS | Existing post-processing tests; accelerated report includes only bounded element-family samples | Synthetic DTO and JSON writer sentinels, PASS; no stress solve/export | Serializer contracts and a synthetic result write passed. No stress-field values were measured. | P2: compare selected integration-point and nodal stress fields against a hand-calculated patch and check CSV/VTU output fields. |
| API-IO / IO-MESH / result formats | Existing JSON, Gmsh, DTO, and export paths | JSON model read, synthetic JSON result write, Gmsh HEX8 import, and versioned DTO round-trip sentinels, all PASS | Import test confirmed HEX8 family and pressure-face mapping. The tested paths do not invoke a solve. | P2: add a no-solve exporter fixture for CSV/VTU field schemas, then separately verify solved-result export after FEM execution is authorized. |

## Exact non-FEM runs

Each run selected one test-function nodeid through scripts/development_autonomous.py under a generic unit/integration scope. The runner marked every record DEVELOPMENT_ONLY with qualification NOT_APPLICABLE. Raw run.json, stdout.log, and stderr.log copies are in external-evidence://vv-elements/development\2026-10-26; the original runner records remain under this worktree's .codex/development-runs directory.

| Nodeid | Scope | Result | Elapsed (s) | Run ID |
|---|---|---:|---:|---|
| tests/unit/test_sparse_accumulator.py::test_sparse_accumulator_matches_direct_sparse_sum | unit | PASS | 7.071 | dev-c3291e03a07a |
| tests/unit/test_mpc_reduction.py::test_elimination_matches_lagrange_multiplier_solution | unit | PASS | 5.157 | dev-b8edd8dc2008 |
| tests/unit/test_result_serialization_contracts.py::test_versioned_experimental_result_dtos_round_trip_without_solver_execution | unit | PASS | 4.544 | dev-f027be54e523 |
| tests/unit/test_json_io.py::test_json_reader_loads_tet4_model | unit | PASS | 3.103 | dev-fab79b4733c5 |
| tests/unit/test_json_io.py::test_json_writer_saves_result | unit | PASS | 3.124 | dev-734d5bfbfdf7 |
| tests/integration/test_hex8_gmsh_import.py::test_gmsh_hex8_and_quad4_faces_use_the_standard_import_path | integration | PASS | 3.129 | dev-b60c5034dda4 |

## Execution boundary and next action

The repository AGENTS.md requires monitored FEM exploration to use the development launcher with a registered worktree ID and exact allowed nodeid. development_autonomous_policy.json registers D01, C01, and E01 only; the launcher hard-codes that exact registry and rejects other worktree IDs. The Agent 3 brief separately requests a new WP12 worktree and says not to modify the runner. Therefore this pass did not run direct pytest, local element stiffness probes, or solver-backed cases. The non-FEM generic tests above do not consume the FEM case budget.

Before any new FEM run, resolve this policy conflict explicitly. Then freeze the exact nodeids and case list, source/test identity, per-case timeout and DDL limits, numerical references, and acceptance criteria before observing results. Preserve WP10 and WP13-12 records unchanged. This pass remains incomplete; it does not authorize a qualification claim, release, or merge.
