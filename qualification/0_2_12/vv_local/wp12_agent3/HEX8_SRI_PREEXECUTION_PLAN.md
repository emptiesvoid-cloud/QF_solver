# WP12 Agent 3 — HEX8-SRI pre-execution plan

**State: preparation only / NOT_RUN.** No FEM case, solver test, or qualification check was run to create this plan. The development runner and policy are not changed. Existing commits and historical records remain untouched.

- Worktree: `worktree://vv-elements`
- Branch and starting commit: `test/wp12-fem-regressions` / `a873d6345d7435a932087abb3e799d3d342b9417`
- Existing case budget: at most 20 new cases; 300 s default per case, 900 s only exceptionally; selected model size at most 30,000 DDL.
- No proposed case is currently registered or authorized for execution. Exact nodeids must be implemented, inspected, and registered after the common configuration commit is supplied. Execution also waits for its exact approved manifest.

## Historical anchor and first diagnostic

The source record is `qualification/0_2_8/wp13_12_hex8_sri_maturation/manifest.json`, governed by `qualification/0_2_8/wp13_12_hex8_sri_maturation_contract.json`. Preserve both files and the original NPZ byte-for-byte. The decision was `KEEP_EXPERIMENTAL`; the frozen energy and equilibrium gates failed at `1e-10`, while the locking, patch, rank, refinement, and distortion gates passed.

The recorded near-incompressible SRI case uses `nu=0.4999`, `E=1e6`, a regular cantilever of length 20 and a `2 x 2` cross-section. Historical force-resultant residuals for `nx=4,8,16` were `2.414e-9`, `1.950e-9`, `2.085e-9`; moment residuals were `4.557e-9`, `4.078e-9`, `4.924e-9`. The finest SRI displacement error against the limited Timoshenko beam oracle was `0.3308208`; standard HEX8 was `0.8681885`. The SRI improvement does not establish general accuracy or qualification.

The valid near-degenerate SRI case used `nu=0.495`, `nx=4`; `detJ` was about `0.00625`. Its recorded energy error was `1.027753e-9`, force-resultant residual `7.258e-9`, and moment residual `1.715e-8`. These failures and the existing `1e-10` gates remain unchanged.

The archive contains eight compact arrays (eigenvalues and displacement/determinant/energy-error summaries), but no assembled `K`, `u`, applied `F`, reactions, or component-wise moment terms. It cannot independently reconstruct the failed balances. A new development diagnostic must retain those raw quantities, with hashes and its case inputs, in that run's durable evidence area before reducing them to summary metrics.

The first execution stage is deliberately only two cases, in this order:

| Case | Formulation and input | Selected DDL | Why first |
|---|---|---:|---|
| `sri-regular-nu04999-nx16` | HEX8-SRI, `nu=0.4999`, regular `nx=16, ny=nz=2`, `E=1e6` | 459 | Reproduce the largest recorded force/moment residual in the near-incompressible series while retaining raw system vectors. |
| `sri-near-degenerate-nu0495-nx4` | HEX8-SRI, `nu=0.495`, `nx=4, ny=nz=2`, `near_degenerate_valid` geometry from the historical generator | 135 | Reproduce the coupled energy, force, and moment failures with the smallest historical mesh. |

The exact independent nodeids are:

- `tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_incompressible_nu04999_nx16` — one SRI solve, preselected at 459 total DDL.
- `tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_degenerate_nu0495_nx4` — one SRI solve, preselected at 135 total DDL.

Each target represents one solve; neither node parametrizes multiple meshes or formulations. Both check the total-DOF formula and 30,000 DDL ceiling before mesh construction, and the common controller must independently apply that same pre-execution DDL selection when registering/launching each exact nodeid. Use the 300 s default. These small systems do not justify the exceptional timeout. After examining these two records, continue with matched formulation controls only if they answer a specific diagnostic question. Do not begin by replaying the whole old campaign.

Before checking the frozen numerical gates, each case writes `output/wp12-elements-<case-id>/numerical-state.npz` and `result.json` in the active attempt directory. This is the controller-inventoried output directory beside its `tmp/` directory, so raw arrays and structured metrics survive pytest stdout capture and remain associated with that single attempt. Files are created exclusively; no historical qualification evidence path is used. A direct pytest invocation without the active development-run environment is refused before mesh construction or element assembly. The first two nodeids run SRI only; standard HEX8 controls remain a later, separately selected matched comparison as described below.

## Matched HEX8 / HEX8-SRI comparison plan

After the first diagnostics are preserved and reviewed, the bounded comparison set is:

- Linear-elastic cantilever: `nu in {0.30, 0.4999}`, `nx in {4,8,16}`, `ny=nz=2`.
- Run standard HEX8 and HEX8-SRI on identical coordinates, connectivity, material, load vector, constraints, solver, and reference. This is 12 model solves; the `nu=0.4999, nx=16` SRI case is already in stage one.
- Pair the `nu=0.495, nx=4` near-degenerate SRI case with standard HEX8 only if a formulation comparison is useful: at most 14 distinct solves total, leaving six of the 20-case budget unallocated.
- Keep the Timoshenko expression labelled as a slender-beam diagnostic, not an external 3-D oracle. Report displacement trend and its limitations alongside force/moment/energy results. Do not infer that SRI dominates standard HEX8 outside the matched locking-sensitive cases.

For the historical mesh generator, total nodes are `9 * (nx+1)` and total model DDL before supports are `27 * (nx+1)`: 135, 243, and 459 for `nx=4,8,16`. With the `x=0` face fixed, the free equation counts are 108, 216, and 432. Use the total-model counts as the conservative preselection values and record that definition in the selection basis. All are below the 30,000 DDL ceiling. The case selector must check this count before any launch; it is not a post-run annotation.

## Force, moment, and energy conventions to record

The historical runner applies a total `1 N` force in global `-z`, shared equally over the nine nodes on the `x=20` end face. Their centroid is `(20, 0.5, 0.5)`. Therefore the expected applied resultant is `(0,0,-1) N` and its moment about the global origin is `(-0.5,20,0) N m`. Report all components, not only their vector norm. The total support reaction resultant and its origin moment should be the opposites within the observed numerical residual.

Use the historical sign convention for reactions: `r = K u - F`, with `R_i = r_i` on fixed DOFs and zero on free DOFs. Report both of these distinct quantities:

1. DOF equilibrium residual: `||K u - F - R||_2 / max(||F||_2, 1)`; also report its free-DOF part. This matches the contract's written `force_balance` formula.
2. External resultant closure: `||sum(F) + sum(R)||_2 / max(||F||_2, 1)`, plus component-wise resultants.

The historical runner's `force_balance_relative` is quantity 2 (`sum(F)+sum(R)`); its `free_residual_relative` is a separate free-DOF solve residual. Do not conflate or rename them in new output. The contract text and runner name different quantities, so the new record should expose both without rewriting the frozen WP13 record or its gates.

For small-strain linear elasticity with zero initial state and a load ramp from zero, preserve `U = 0.5 u^T K u` and `W = 0.5 u^T F`. Also retain `|U-W|`, the legacy scaled error `|U-W|/max(|W|,1)`, and a scale-free diagnostic `|U-W|/max(|U|,|W|,tiny)`. The historical code calls the scaled metric relative even when work is below 1; report this scale distinction, but do not replace the historical `1e-10` gate or use the extra diagnostic as a new gate.

For each run, retain case inputs and hashes, `K`, `u`, `F`, fixed mask, `R`, coordinates, `K u-F`, both balance definitions, component-wise applied/reaction/resultant moments about the origin, `U`, `W`, the two energy differences above, determinant range, and solver/runtime metadata. Preserve failing arrays and logs in the per-attempt development evidence; never write over the historical NPZ or manifest.

## Complementary element checks

These are candidates to select after the HEX8-SRI diagnostic and configuration activation, not runs performed by this preparation:

| Element | Existing exact node / evidence | Useful complement and limitation |
|---|---|---|
| BEAM2 | `tests/unit/test_beam2_element.py::test_beam2_uniform_line_load_matches_timoshenko_cantilever_solution` checks Timoshenko tip response and distributed-load resultant/moment. `...::test_beam2_postprocessing_reports_local_end_equilibrium` checks local end forces/moment for a point-loaded beam. | Run both as separate bounded sentinels. The line-load test does not replace a full support-reaction closure check for that same distributed-load case. |
| TET10 | `tests/unit/test_tet10_element.py::test_tet10_patch_test_reproduces_affine_strain_and_energy`; `tests/verification/test_wp09_tet10_r2_consistent_traction.py::test_consistent_tet10_surface_load_preserves_resultant_and_moment`. | Prioritize the curved-face consistent-traction resultant and moment with the existing curved-geometry reference. Preserve the Agent 2 TET4 work and avoid claiming TET4 convergence from this test. |
| HEX20 | `tests/unit/test_hex20_element.py::test_hex20_body_and_quad8_face_loads_preserve_resultants` checks force resultants for body, traction, and pressure loads. | Add or select a moment-closure companion for the quadratic face/body loads; the existing test's force-resultant assertions alone do not verify first moments or support reactions. |
| MITC4 | `tests/verification/test_mitc4_verification.py::test_structural_convergence_includes_cook_64_by_64_review` preserves a static Cook/scordelis/pinched review; the Cook record is `WARNING` at 4.521447% relative error. | Prefer one predeclared static bending/shear-sensitive plate case with an independent reference, reaction closure, and a short mesh trend. Do not substitute a zero-frequency dynamic consistency check or loosen the existing Cook result. |

## Deferred actions

Once the common configuration commit and exact Owner-approved commands/manifest are provided, retrieve it into this branch without resetting or rewriting `a873d6345d7435a932087abb3e799d3d342b9417`; inspect the exact test nodeids and DDL selections; register and freeze each case; then launch only the approved cases through the registered workflow. Record development failures as failures. No result from this plan is qualification evidence, and nothing here closes WP12/WP13, merges a scientific branch, changes public HEX8 behavior, or authorizes release.
