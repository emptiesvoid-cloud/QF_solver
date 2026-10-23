# WP-E01-H — Supervised Global Assembly Verification and J2 Diagnostics

Date: 2026-10-21
Branch: `codex/qf-wp-e01-a-implementation-20261020`
Starting HEAD: `124d0d8b5312ffc2815af922d6eb5271bee19593`

## Executive result

The frozen 20-case global-assembly module was collected and executed once through the reviewed Windows Job Object supervisor. **16 passed and 4 failed** in 14.69 seconds. The two corrected affine elastic patch cases now pass. The four failures are the TET4/HEX8 J2 fixed-history tangent cases; each preserved its failure under the unchanged proposed gates.

The diagnostic evidence does **not** demonstrate a production constitutive or assembly tangent defect. It identifies two problems in the candidate finite-difference acceptance procedure:

1. For each TET4 `free-center-mixed` direction, the final-three window includes a truncation-dominated `h=3e-6` point just above the proposed global limit, while the two finer points are below it and the error decreases approximately quadratically.
2. For each TET4/HEX8 `weak-near-translation` direction, the force-difference derivative is at roundoff/cancellation scale. Its local relative error is therefore not evaluable. The current helper nevertheless calls it `ELIGIBLE` because the noisy derivative exceeds a constant, stiffness-based null floor; the global-scale plateau also marks a derivative as plateaued while its raw norm grows as `h` decreases.

These are candidate-gate/resolution findings, not tangent-consistency passes. The candidate thresholds remain **PROPOSED**, `J2_TANGENT_CONSISTENCY` remains **BLOCKED_PENDING_INDEPENDENT_EVIDENCE**, and no production Armijo route is certified. No production or test source was changed during or after the run. No tests were rerun.

An independent read-only reviewer, not involved in this execution, examined the raw output and helper source. The reviewer agreed that the TET4 global failures are caused by the proposed all-points-in-window rule interacting with truncation, and that the weak-direction local results are unresolved at the tested precision rather than evidence of a production tangent defect. Full review comments are summarized below.

## Identity and safety

The repository root was `C:/wpc01-frictionless-public-integration-wt/wp-e01`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch as above, and starting worktree clean at the required HEAD. The manifest SHA-256 was `0F609B4B51AE81A8FD2F2BD4233510D9002AD0A46404279D6532D19AE8E31E91`; all 17 production-source hashes listed in it matched immediately before execution. The frozen WP-E01-F report and the prior D4R 65-pass evidence were not modified or rerun.

| Executable or record | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01e_global_assembly_vnv.py` | `8FA46D1D2FF402C72E0D85851EB57307173FBA3D37A39567E3678608FE818296` |
| `tests/conftest.py` | `CC54ADD4E7521762ECAD97E7CF0B19579AB898FE79CFF25319D889BEC2F081A2` |
| `experiments/wp_e01f_global_assembly_supervisor.py` | `06FE16E642CA8FEFE850B92DD41F30128C84A96712E1CBA954272AE23EFAE79B` |
| `experiments/wp_e01f_collection_guard.py` | `324D49F2542FAF2FBDD9B31DA2188EAB6FDEA5F512CC85A15FE26A7D42B36E24` |
| WP-E01-G report | `8E784E53DE4289DD282F9ECABAB3D79460C122EC717EAE3268DE652B241D697B` |
| WP-E01-G execution manifest | `0F609B4B51AE81A8FD2F2BD4233510D9002AD0A46404279D6532D19AE8E31E91` |

The target remains registered as `NUMERICAL_UNIT`. The safety registry, collection guard and supervisor hashes matched the GO. Source inspection found no public solver, `solve_model`, native FEM, Gmsh, worker, child-process, or network path in the selected tests/import closure. Gmsh probing is not selected for this module. Pytest used `-S`, disabled the cache provider, loaded only the hash-bound guard, and ran the fixed module. The supervisor provided one BLAS thread and no parallel workers.

The parent command was exactly:

```text
C:\Python313\python.exe -m experiments.wp_e01f_global_assembly_supervisor
```

The supervisor launched one `shell=False` pytest child. Its collection-finish guard observed and validated the exact 20 nodes, function set, fixtures, markers and module identity before entering pytest's test loop. Collection and execution occurred in that one supervised pytest phase; there was no separate collection-only child. The child command and Job Object settings are preserved in the phase record.

Windows Job Object evidence: one active process permitted, per-process and job committed-memory limits each `268435456` bytes, kill-on-close enabled, breakaway disabled, and parent phase deadline 120 seconds. The child PID was `33752`; it exited `1` because pytest reported assertions, not due to timeout. Execution phase elapsed `15.4274319` seconds; pytest reported `14.69s`. Peak process and job commitment were both `109842432` bytes (about `104.8 MiB`), below the 256 MiB limits. Cleanup status was `VERIFIED_WINDOWS_JOB_CLOSED`. `stderr.log` was empty. The supervisor's top-level label `FAILED_CLOSED` reflects the nonzero test exit; the recorded resource and safety checks passed.

## Collection and results

Actual collection matched the expected count exactly: 20 cases, with no skipped, xfailed or xpassed tests.

| Result | Count |
|---|---:|
| PASS | 16 |
| FAIL | 4 |
| SKIP | 0 |
| XFAIL | 0 |
| XPASS | 0 |
| Total collected | 20 |

The four failures were:

```text
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-1500000000.0]
```

The other 16 passed cases were:

```text
test_j2_global_affine_elastic_patch_and_reaction_reference[TET4]
test_j2_global_affine_elastic_patch_and_reaction_reference[HEX8]
test_j2_global_monotone_path_matches_tensor_return[TET4-0.0]
test_j2_global_monotone_path_matches_tensor_return[TET4-1500000000.0]
test_j2_global_monotone_path_matches_tensor_return[HEX8-0.0]
test_j2_global_monotone_path_matches_tensor_return[HEX8-1500000000.0]
test_j2_global_accepted_state_trial_rollback_and_exactly_once_commit[TET4]
test_j2_global_accepted_state_trial_rollback_and_exactly_once_commit[HEX8]
test_j2_global_accepted_state_wp10_v2_checkpoint_serialization_roundtrip[TET4]
test_j2_global_accepted_state_wp10_v2_checkpoint_serialization_roundtrip[HEX8]
test_stvk_global_rigid_rotation_and_affine_patch[TET4]
test_stvk_global_rigid_rotation_and_affine_patch[HEX8]
test_stvk_global_residual_tangent_and_material_geometric_split[TET4]
test_stvk_global_residual_tangent_and_material_geometric_split[HEX8]
test_j2_global_assembly_rejects_wrong_integration_point_state_vector[TET4]
test_j2_global_assembly_rejects_wrong_integration_point_state_vector[HEX8]
```

The guarded collection returned these exact 20 `nodeid` values:

```text
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_affine_elastic_patch_and_reaction_reference[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_affine_elastic_patch_and_reaction_reference[HEX8]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_monotone_path_matches_tensor_return[TET4-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_monotone_path_matches_tensor_return[TET4-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_monotone_path_matches_tensor_return[HEX8-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_monotone_path_matches_tensor_return[HEX8-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_accepted_state_trial_rollback_and_exactly_once_commit[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_accepted_state_trial_rollback_and_exactly_once_commit[HEX8]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_accepted_state_wp10_v2_checkpoint_serialization_roundtrip[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_accepted_state_wp10_v2_checkpoint_serialization_roundtrip[HEX8]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_stvk_global_rigid_rotation_and_affine_patch[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_stvk_global_rigid_rotation_and_affine_patch[HEX8]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_stvk_global_residual_tangent_and_material_geometric_split[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_stvk_global_residual_tangent_and_material_geometric_split[HEX8]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_assembly_rejects_wrong_integration_point_state_vector[TET4]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_assembly_rejects_wrong_integration_point_state_vector[HEX8]
```

Full fixture inventory, original stdout and supervisor records are preserved in [`wp_e01_h_execution_2026-10-21/`](wp_e01_h_execution_2026-10-21/).

The elastic tests passed their corrected analytical stress reference and the test's assembly/patch/reaction assertions. Exact reaction and residual error magnitudes were not emitted (`NOT_RECORDED`); the result establishes only that the assertions passed for these two bounded fixtures. It is not broad global FEM qualification.

The two J2 monotone-path comparisons passed. The rollback/commit helper cases, WP10 v2 serialization round trips, StVK rigid-rotation/affine cases, StVK residual/tangent split cases and malformed integration-point-state refusals all passed at the exact tested API scope. Checkpoint tests did not exercise abrupt process-crash durability or production nonlinear restart.

## J2 fixed-history fixture and measurements

The four tangent cases used `E=210 GPa`, `nu=0.30`, yield stress `250 MPa`, and `H=0` or `1.5 GPa`. Each material point was preloaded to `epsilon_x=0.0016`; the accepted state was then frozen while testing the trial field `epsilon_x=0.003` plus center offset `[2e-5,-1e-5,1.5e-5] m`. TET4 used 12 elements and 12 centroid points; HEX8 used 8 elements and 64 Gauss points. Every accepted point was plastic, with the following accumulated equivalent plastic strain:

| Family | H (Pa) | Accepted alpha min = max | Plastic points |
|---|---:|---:|---:|
| TET4 | 0 | `3.49206349206348e-5` | 12/12 |
| TET4 | `1.5e9` | `3.47057895567123e-5` | 12/12 |
| HEX8 | 0 | approximately `3.4920634920635e-5` | 64/64 |
| HEX8 | `1.5e9` | approximately `3.47057895567124e-5` | 64/64 |

| Family / H (Pa) | Base independent reference force norm (N) | Production/reference base force difference (N) |
|---|---:|---:|
| TET4 / 0 | `694732405.2644703` | `6.495265578539184e-8` |
| TET4 / `1.5e9` | `694925928.9644684` | `1.5123026915031998e-7` |
| HEX8 / 0 | `494260573.34404474` | `1.1903453848265453e-7` |
| HEX8 / `1.5e9` | `494397938.0913787` | `7.706940496555419e-8` |

The trial state was smooth plastic. All production `+/-` perturbations retained the base elastic/plastic identity; independent continuous yield margins were positive for every tested perturbation. Across the 16 direction sweeps, the minimum recorded margin was approximately `200.154 MPa`; direction minima ranged up to approximately `219.719 MPa`. The accepted-state digest was unchanged. These observations exclude branch switching and accepted-state mutation as causes in these fixtures.

For the independent and production force mappings, the base force norms were approximately `694.7 MN` (TET4) and `494.3 MN` (HEX8). Base production/reference force differences were `6.50e-8` to `1.51e-7 N` for TET4 and `7.71e-8` to `1.19e-7 N` for HEX8, about `1e-16` relative to the recorded reference norms. The recorded production-versus-independent finite-difference comparisons were at most `5.4e-13` under the global stiffness normalization. This is strong agreement at global scale, but that normalization cannot certify a nearly null local action.

For each row below, the global and local triplets correspond to the candidate final window `h=(3e-6,1e-6,3e-7)`. `G` is the independent-reference global error; `L` is the local error. `Kp` is the norm of the production tangent action in N. `m_y` is the minimum positive branch margin in Pa. All direction vectors had norm approximately 1 m; all sweeps used six dimensionless `h` values `(1e-4,3e-5,1e-5,3e-6,1e-6,3e-7)`. Every row's plateau flag was `True`; all production branch-match flags were `True`.

| Family / H (Pa) | Direction | `||Kp||` (N) | `m_y` (MPa) | G, final window | L, final window | Candidate gate |
|---|---|---:|---:|---|---|---|
| TET4 / 0 | free-center-mixed | `3.9573e11` | 208.822 | `(2.0357e-7, 2.2619e-8, 2.0358e-9)` | `(2.7007e-7, 3.0008e-8, 2.7008e-9)` | **FAIL global** |
| TET4 / 0 | full-shared-node-mixed | `1.7821e11` | 215.394 | `(2.7476e-8, 3.0529e-9, 2.7490e-10)` | `(8.0943e-8, 8.9935e-9, 8.0981e-10)` | PASS |
| TET4 / 0 | boundary-shared-node | `1.4567e11` | 209.349 | `(1.2005e-8, 1.3338e-9, 1.2037e-10)` | `(4.3268e-8, 4.8073e-9, 4.3381e-10)` | PASS |
| TET4 / 0 | weak-near-translation | `1.9900e-4` | 219.719 | `(6.0869e-14, 1.8236e-13, 6.0732e-13)` | `(1.0020, 1.0007, 0.9998)` | **FAIL local; unresolved** |
| TET4 / `1.5e9` | free-center-mixed | `3.9695e11` | 208.822 | `(2.0230e-7, 2.2477e-8, 2.0231e-9)` | `(2.6755e-7, 2.9728e-8, 2.6756e-9)` | **FAIL global** |
| TET4 / `1.5e9` | full-shared-node-mixed | `1.7862e11` | 215.394 | `(2.7304e-8, 3.0337e-9, 2.7318e-10)` | `(8.0253e-8, 8.9168e-9, 8.0294e-10)` | PASS |
| TET4 / `1.5e9` | boundary-shared-node | `1.4618e11` | 209.349 | `(1.1930e-8, 1.3255e-9, 1.1980e-10)` | `(4.2844e-8, 4.7602e-9, 4.3024e-10)` | PASS |
| TET4 / `1.5e9` | weak-near-translation | `1.7948e-4` | 219.719 | `(6.7223e-14, 2.0154e-13, 6.7154e-13)` | `(1.0009, 1.0003, 0.9999)` | **FAIL local; unresolved** |
| HEX8 / 0 | free-center-mixed | `1.3191e11` | 200.154 | `(5.8979e-8, 6.5533e-9, 5.8987e-10)` | `(2.3474e-7, 2.6082e-8, 2.3477e-9)` | PASS |
| HEX8 / 0 | full-shared-node-mixed | `6.9160e10` | 216.172 | `(6.7989e-9, 7.5544e-10, 6.7948e-11)` | `(5.1611e-8, 5.7346e-9, 5.1580e-10)` | PASS |
| HEX8 / 0 | boundary-shared-node | `2.8455e10` | 215.014 | `(5.0037e-10, 5.5551e-11, 4.9952e-12)` | `(9.2319e-9, 1.0249e-9, 9.2163e-11)` | PASS |
| HEX8 / 0 | weak-near-translation | `6.7201e-5` | 219.648 | `(4.2155e-14, 8.3959e-14, 2.0451e-13)` | `(1.0014, 1.0000, 1.0000)` | **FAIL local; unresolved** |
| HEX8 / `1.5e9` | free-center-mixed | `1.3232e11` | 200.154 | `(5.8610e-8, 6.5122e-9, 5.8609e-10)` | `(2.3255e-7, 2.5839e-8, 2.3255e-9)` | PASS |
| HEX8 / `1.5e9` | full-shared-node-mixed | `6.9257e10` | 216.172 | `(6.7562e-9, 7.5069e-10, 6.7677e-11)` | `(5.1215e-8, 5.6906e-9, 5.1302e-10)` | PASS |
| HEX8 / `1.5e9` | boundary-shared-node | `2.8547e10` | 215.014 | `(4.9723e-10, 5.5167e-11, 4.7859e-12)` | `(9.1443e-9, 1.0146e-9, 8.8015e-11)` | PASS |
| HEX8 / `1.5e9` | weak-near-translation | `6.9357e-5` | 219.648 | `(4.6078e-14, 9.2811e-14, 2.7664e-13)` | `(1.0013, 1.0002, 1.0002)` | **FAIL local; unresolved** |

The global and local candidate limits remain `1e-7` and `1e-5`; the plateau limit remains `1e-6`. All are proposed, not frozen. The complete six-step absolute errors, every derivative vector, production tangent actions, per-step production/independent derivative comparisons, and margins are in the raw stdout record.

### Root-cause analysis by failed parameter case

| Failed node | Exact failed directions / conditions | Strongest supported classification | Confidence and limitation |
|---|---|---|---|
| TET4, `H=0` | `free-center-mixed`: global window; `weak-near-translation`: local window | `PROPOSED_GATE_DEFECT` for the free direction; `FINITE_DIFFERENCE_RESOLUTION_DEFECT` for the weak direction | High confidence about the observed gate mechanics. Free-direction global errors fall from `2.04e-7` to `2.04e-9` over the final window, and production/reference FD mappings agree globally. Weak local derivative is below finite-difference resolution. Neither result establishes a production tangent defect. |
| TET4, `H=1.5e9 Pa` | Same two directions and conditions | Same two classifications | Same evidence pattern; branch margins remain positive. |
| HEX8, `H=0` | `weak-near-translation`: local window | `FINITE_DIFFERENCE_RESOLUTION_DEFECT`; contributing `PROPOSED_GATE_DEFECT` | High confidence that this local numerical derivative is unresolved; it is not a tangent PASS or production FAIL. |
| HEX8, `H=1.5e9 Pa` | Same weak direction and condition | Same classification | Same evidence pattern; branch margins remain positive. |

#### Why the free-center TET4 gate fails

The candidate requires **each** of the final three centered-difference points to satisfy the `1e-7` global error limit. At the coarsest final point `h=3e-6`, the errors are `2.0357e-7` and `2.0230e-7`; at `h=1e-6` they are `2.2619e-8` and `2.2477e-8`, and at `h=3e-7` they are `2.0358e-9` and `2.0231e-9`. The adjacent changes are below the proposed plateau limit, and the error sequence is consistent with centered-difference truncation decreasing approximately as `h^2`. Production-tangent-versus-production-FD errors track the independent-reference errors; the production and independent finite-difference derivatives agree to at most roughly `3.2e-13` on the global scale.

Thus the failure is the proposed all-points-in-window acceptance rule applied to a window whose coarsest member has visible truncation error. It does not show a stable nonzero derivative mismatch. A future proposal could use a branch-preserving Richardson estimate or require the error condition at the finest resolvable points while separately demonstrating a plateau. That would be a **new proposed gate**, not an approved correction; no threshold or test was changed here.

#### Why the local near-translation gate is not evaluable

The near-translation vectors are a rigid translation plus a `1e-15` mixed perturbation. Their tangent actions are only `6.72e-5` to `1.99e-4 N`, versus a global stiffness reference of `5.25e11 N/m` for a 1 m vector. In the final window, the independent finite-difference action norms are:

| Family / H | `h=3e-6` | `h=1e-6` | `h=3e-7` |
|---|---:|---:|---:|
| TET4 / 0 | `0.031891 N` | `0.095673 N` | `0.318909 N` |
| TET4 / `1.5e9` | `0.035259 N` | `0.105778 N` | `0.352593 N` |
| HEX8 / 0 | `0.022100 N` | `0.044078 N` | `0.107360 N` |
| HEX8 / `1.5e9` | `0.024159 N` | `0.048714 N` | `0.145212 N` |

These noisy derivative norms increase as `h` decreases, with local errors approximately one. A scalar cancellation indicator `eps*||F_base||/h` is approximately `0.04–0.52 N` over these cases and steps, the same scale as the measured finite differences. This is consistent with subtracting nearly equal nodal-force vectors of hundreds of meganewtons and then dividing by a small step. The helper's constant null floor is `64*eps*K_ref*||p|| ~= 0.00746 N`; the noise rises above that floor, causing a false `ELIGIBLE` classification. Its adjacent-change plateau is normalized by the much larger global stiffness scale, so it reports `True` despite the raw weak response changing by factors of roughly 2–3. These local values must be treated as **NOT EVALUABLE**, while the recorded test outcomes remain failures under the proposed rule.

The global errors near `1e-13` are not evidence that the weak local action is accurate; they result from dividing by `K_ref||p||` and mask the unresolved signal. A future gate should estimate a step-dependent force-difference noise floor, classify directions whose derivative is below that resolution as `NOT_EVALUABLE`, and use a direction-local plateau criterion only where the response is resolved. An exact rigid-translation null check can independently assess translation invariance. Any such changes need Owner review and a new executable identity.

## What the run establishes—and does not

Established within this synthetic in-memory scope:

* The corrected TET4 and HEX8 J2 affine elastic references reach and pass their assembly and reaction assertions.
* The bounded monotone J2 path comparisons, fixed-history normal-direction checks that pass candidate gates, helper-level rollback/commit, WP10 v2 serialization round trips, malformed state-vector refusal, and StVK assembly/objectivity/tangent cases pass.
* The fixed accepted material state remains unchanged, all checked production perturbations preserve production branch identity, and independent yield margins remain positive.
* No selected case invokes a production nonlinear solve, public API route, native FEM backend or Gmsh.

Not established:

* J2 tangent consistency in the near-null translation directions.
* A frozen or Owner-approved J2 tangent criterion.
* Full production Newton convergence, production Armijo route certification, or complete follower-load linearization.
* Crash durability or filesystem atomicity of checkpoints.
* Native FEM V&V or scientific qualification.

The test residual is `R=F_int-F_ext`; for fixed external loads `J_R=K_int` and the Newton equation is `K_ff*delta_u_f=-R_f=F_ext,f-F_int,f`. Displacement-dependent external loads require their own derivative in `J_R`; the fixed-load fixture does not test that case. This run did not execute E01-A's production Newton driver.

## Independent review and next work

The separate reviewer read the preserved H stdout and `_directional_sweep` source without editing files or running tests. The reviewer agreed:

* TET4 free-center failures are explained by the strict all-points final-window gate meeting a truncation-dominated coarse point; the finer points and production/reference derivative agreement do not support a production defect.
* Near-translation local values are unresolved because finite-difference cancellation dominates the true response; global normalization cannot establish local accuracy.
* No result should be promoted to a tangent pass, Newton certificate, or scientific qualification.

This is an independent read-only review of the execution evidence, not a second numerical execution. The four exact failures remain intact.

Recommended next Owner decision: authorize one focused, hash-bound numerical follow-up that (1) uses a high-precision independent force reference or an exact rigid-translation invariance oracle for the near-null direction, and (2) evaluates a branch-preserving Richardson/truncation estimate for the TET4 mixed direction. Keep all existing candidate criteria and thresholds unchanged in that study; use its measured evidence to decide whether a revised candidate gate is scientifically justified. Do not activate production Armijo or claim J2 tangent consistency.

## Frozen evidence and hashes

The following 17 production source hashes matched the H manifest immediately before execution:

| Production source | SHA-256 |
|---|---|
| `src/solveur/core/errors.py` | `9281DC8F2E320E37DD26DA0F4504C343AAA54376D5F80FD03EC9294F9C01A943` |
| `src/solveur/core/assembly/nonlinear.py` | `C5C6E1953C3B08C30397F18F8DF07FB8D355216BF372C45CEE5695FCE7BC65E1` |
| `src/solveur/core/assembly/assembler.py` | `23E0702165A65AFB2108670B2F140B8173F4857134A4E1461C5D75E8333B30CB` |
| `src/solveur/core/assembly/geometric.py` | `B81454F32F8A824725F3E0902871EB5394BB0A4D83BD4709D9DC626A3108A22C` |
| `src/solveur/elements/solid/tet4.py` | `5DAA0CDECE28F0C352649607872EED2A49900ACF7BE76BCC11EB98A8C9181B59` |
| `src/solveur/elements/solid/hex8.py` | `E4D37B19268BD7FCE81F270E17BA314CE8390667B19685CC982F514802E13A3F` |
| `src/solveur/elements/solid/j2_state.py` | `1DD85418DF2026D3A9E3DE4F8DA5FCA30021E85882F0606290F083C0D23C26A4` |
| `src/solveur/elements/solid/tet4_total_lagrangian_batch.py` | `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `95DF9E1895BB631D598FA52FD22986E153C865F77C91557E904FF0AF766451A6` |
| `src/solveur/core/nonlinear/checkpoint.py` | `EB2B320537D45B3AFD012E143B248237175D7528F7628FDA84E9D64E95885C81` |
| `src/solveur/io/nonlinear_checkpoint.py` | `69983B613DF6A4ECC16183D45AD67EC55BAFA2857043278CFA4B77026DC19709` |
| `src/solveur/core/nonlinear/driver.py` | `B2C6FF6C37581EDCE2019EC700C78F2BD04383C6D4D0BD4602A31F58BCBF1866` |
| `src/solveur/core/nonlinear/load_control.py` | `4DB5F31AC68E07E1C469F4AD93FFBA75FD4CFA239A6A40B3B9791CEEFA07AFBC` |
| `src/solveur/core/nonlinear/e01a.py` | `C0DC0EBFB56FC2DA52AFCA89550ADC922E2A52ED04C0B53A2F4A9022CC7BC139` |
| `src/solveur/core/nonlinear/solver.py` | `8FBAAB82BD4EDDF721AA48BBFBEA6CA5024C9BB7E6ED3B1E3B0E9DD620C8C6F8` |
| `src/solveur/core/audit.py` | `C214661599FCF58AB0B76C7ABA7B3180D6C7A74DA25ECFCB2CC0AC82DB0A1AF8` |
| `experiments/wpc01_exploratory_supervisor.py` | `9BD8C75B19B49C758F9558CF9299EEEDC18762B1E40DBD69968377A94D6C9090` |

The raw evidence hashes are:

| Artifact | SHA-256 |
|---|---|
| `wp_e01_h_execution_2026-10-21/preflight.json` | `8479396B9D2CCFA6305CCB51E9368906DB339E70EC5886C579766A9D8065B336` |
| `wp_e01_h_execution_2026-10-21/summary.json` | `612AD18298EA2CCEB51F46B0C2E626C5D0B6CFF28ED06F922FE24FDC0A62B1E7` |
| `wp_e01_h_execution_2026-10-21/collection_nodes.json` | `9D2BDFD1AE13B4599E0E86A6C9DC9BDE7D212A2B421D4DBD56523A02C9AE6594` |
| `wp_e01_h_execution_2026-10-21/phase_result.json` | `AD53CC594D9A8A081669C419065AAB6B33EC8723E982F3772050EFBDD55E2C06` |
| `wp_e01_h_execution_2026-10-21/stdout.log` | `7B81B48606B2C7FE6F8971AE3DA3832B405752FE38EAAFA6740755DC94FA43FF` |
| `wp_e01_h_execution_2026-10-21/stderr.log` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

No test thresholds, source, safety classification or production behavior changed. The only new repository files are this report and byte-for-byte copies of supervisor evidence. Final commit and clean HEAD are recorded in the delivery accompanying this report.

## Required status

| Status | Result |
|---|---|
| `RESOURCE_SUPERVISOR` | `VERIFIED_FOR_CAMPAIGN` |
| `ELASTIC_PATCH_VNV` | `VERIFIED_BOUNDED` |
| `GLOBAL_ASSEMBLY_VNV` | `PARTIAL` |
| `J2_TET4_GLOBAL_TANGENT` | `FAIL` under proposed gate; production defect not demonstrated |
| `J2_HEX8_LOCAL_TANGENT` | `FAIL` under proposed gate; local derivative not evaluable at tested resolution |
| `J2_TANGENT_ROOT_CAUSE` | `PARTIAL` — false gate failures diagnosed; consistency still unresolved |
| `J2_TANGENT_SCIENTIFIC_GATE` | `NOT_APPROVED` |
| `STVK_GLOBAL_TANGENT` | `PREVIOUS_PASS_BOUNDED`; also passed in this run |
| `WP10_SCHEMA_V2_ROUNDTRIP` | `PREVIOUS_PASS_BOUNDED`; also passed in this run at serialization helper scope |
| `INCREMENTAL_NEWTON_FEM` | `NOT_RUN` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |
