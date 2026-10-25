# WP-E01-F3 — Corrected Global Assembly Verification Results

Date: 2026-10-21
Branch: `codex/qf-wp-e01-a-implementation-20261020`
Starting baseline: `458bf595877d8fe51ff5ce98f95835ec7ad1268e`

## Executive result

The test-only import correction was confirmed, hash-bound, frozen, and run through the reviewed Windows Job Object supervisor. Guarded collection observed the expected 20 cases. Execution completed within its enforced limits, with **14 passed and 6 failed**. No production source changed and no test was rerun after the failures.

The two elastic patch failures occur in a closed-form stress assertion before element assembly and are attributable to a truncated expected-value literal. Four fixed-history J2 tangent cases fail the current proposed directional sweep gate: the two TET4 cases fail the global window; the two HEX8 cases fail the eligible local window. These tangent findings remain unresolved and are not dismissed as test defects. The full per-direction dictionaries were truncated by pytest in the preserved failure trace, so this report does not invent missing metrics.

## Identity and correction

The clean starting checkout matched the requested worktree, branch and HEAD. The origin was the QF Solver repository recorded in the execution manifest. Historical D4R evidence remains **65 PASS** and was not rerun.

The production error module defines `NumericalConvergenceError`; it does not define `NonlinearConvergenceError`. The J2 state validator raises `InputValidationError`, and the nonlinear assembly path catches the `ValueError` base and exposes it as `NumericalConvergenceError`, preserving the J2 state-vector message. The test import and matching `pytest.raises` assertion therefore needed the same exception-name correction. No production alias was added.

The executable change was limited to:

```diff
-from solveur.core.errors import NonlinearConvergenceError
+from solveur.core.errors import NumericalConvergenceError
 ...
-with pytest.raises(NonlinearConvergenceError, match="J2 material state vector"):
+with pytest.raises(NumericalConvergenceError, match="J2 material state vector"):
```

The `NUMERICAL_UNIT` classification and deny rules were preserved. `tests/conftest.py` and the supervisor were updated only to bind the corrected test and registry hashes. The frozen manifest is [wp_e01_f3_execution_manifest_2026-10-21.json](wp_e01_f3_execution_manifest_2026-10-21.json).

| Artifact | SHA-256 |
|---|---|
| Corrected test module | `F726B9FA059C3782ED1CE4C6915CE1DAAAA20EDA726D39DA7DDEFA0B4A243528` |
| Test registry `tests/conftest.py` | `080B5527359F09CAB0F4F978AE429A593C7E4CBF8D526928D8DB680407B2973A` |
| Supervisor `experiments/wp_e01f_global_assembly_supervisor.py` | `7AEDC5FE3C654AB6C7A1576279A95394F6030F71A3B1A78BC91501A662F33F66` |
| Collection guard | `324D49F2542FAF2FBDD9B31DA2188EAB6FDEA5F512CC85A15FE26A7D42B36E24` |
| Frozen execution manifest | `C8391685520182C9FEBD237781357FCF0B74C8DB6F31F3F172FD01C86C5120C2` |

The manifest records the unchanged production-source hashes, including the error types, nonlinear assembly, TET4/HEX8 and total-Lagrangian element implementations, J2 state code, checkpoint modules, nonlinear driver/load-control code, solver, and audit code. It is committed at executable identity `b3ff58571a915c61b84a1b3f025e62293328031f`; the manifest-to-identity binding is recorded in `e2c78dfc696a14d5dceb7bee1406aa1190313797`.

## Safety and execution record

Static AST parsing, manifest validation, exact hash checks, and supervisor preflight passed. The reviewed classification remained `NUMERICAL_UNIT`. Collection and execution used one supervised pytest child and the collection-finish guard; it checked the selected module, test-function set, fixtures, and case count before entering the runtest loop. The reviewed test path did not reach native FEM, Gmsh, public solve APIs, test-side subprocesses, workers, or network access.

Parent command:

```text
C:\Python313\python.exe -m experiments.wp_e01f_global_assembly_supervisor
```

The supervisor launched exactly one child with the frozen command:

```text
C:\Python313\python.exe -S -m pytest -p no:cacheprovider -p experiments.wp_e01f_collection_guard -q -s --basetemp <isolated-output>\execution\pytest-tmp tests/unit/test_wp_e01e_global_assembly_vnv.py
```

The child was assigned to its Windows Job Object before resume. Job and per-process committed-memory limits were each 268,435,456 bytes, active-process limit was one, deadline was 120 seconds, kill-on-close was enabled, breakaway was disabled, and BLAS thread counts were set to one. Peak process and job commit were both 109,105,152 bytes. The run took 7.5326 seconds in the supervisor phase (pytest reported 6.71 seconds), did not time out, exited with code 1, and cleanup was `VERIFIED_WINDOWS_JOB_CLOSED`. These are committed-memory figures, not RSS claims.

Output directory: `<local-temp>\qf_wp_e01f_global_assembly_z7bq3wfx`.

| Captured evidence | SHA-256 |
|---|---|
| `execution/stdout.log` | `C2CC8404829349EEC9ED41913A87B13421CFA380053630FE34553C2AA086EA2B` |
| `execution/stderr.log` (empty) | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |
| `execution/phase_result.json` | `2F4A9EA21AD76E04BB22A8FE6217573DBB5D72EACABC8AC5CCB4343542340B4D` |
| `execution/collection_nodes.json` | `9D2BDFD1AE13B4599E0E86A6C9DC9BDE7D212A2B421D4DBD56523A02C9AE6594` |
| `summary.json` | `BFC12951B3D19602A628845D5AFD025C09812F51674ED9B7CCBA46B05615BFEB` |
| `preflight.json` | `19ADF718DB38C019A47CD7FD9AB39813744212FE219AC1B333A3A8B591A2FB00` |

## Collection and test results

Collection observed **20 cases** from the expected eight test functions. The only executed module was `tests/unit/test_wp_e01e_global_assembly_vnv.py`.

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

Actual counts: **14 passed, 6 failed, 0 skipped, 0 xfailed, 0 xpassed**.

### Failures

1. **TET4 and HEX8 affine elastic patch/reaction-reference cases** failed at test line 667, before `assemble_internal_tangent` is called. The analytic computation gives `sigma_yy = 12,115,384.615384614 Pa`; the expected literal `12.115384615e6` is truncated. With the unchanged relative tolerance `2e-11`, the discrepancy of about `3.85e-4 Pa` exceeds the allowed difference of about `2.42e-4 Pa`. This is a test-oracle precision defect; these failures provide no element assembly or reaction-balance evidence. A future test-only correction can retain the same formula and threshold while spelling the expected value at sufficient precision. No such correction or rerun was made here.

2. **TET4 J2 fixed-history tangent, `H=0` and `H=1.5e9 Pa**, failed `global_window_pass` at line 819. The assertion applies the proposed `1e-7` global stiffness-normalized gate to each point in a shared final-three-step plateau. The failure repr shows large coarse-step absolute differences tapering to small errors, but pytest truncated the complete report; the full failed direction and all plateau fields cannot be recovered from the captured assertion text. The source shows the final test direction is the near-translation weak mode, after three emitted direction reports. This is unresolved finite-difference evidence, not proof of a production tangent defect.

3. **HEX8 J2 fixed-history tangent, `H=0` and `H=1.5e9 Pa**, failed `local_window_pass` at line 821 for an eligible local directional comparison. The overall scaled-window assertion passed first; the proposed local threshold is `1e-5`. The failure repr shows small absolute force differences, but the full direction report is truncated, so its precise direction-local plateau values are unavailable. Do not discard it as a null-mode artifact without a complete independent analysis.

The proposed tangent thresholds remain proposals: global `1e-7`, direction-local `1e-5`, with finite-difference steps `(1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7)`. No threshold was changed or frozen.

### Passing scope

The four J2 monotone tensor-return cases passed for TET4/HEX8 and perfect-plastic/linear-hardening choices. The two helper-level trial/rollback/exactly-once-commit cases passed. The two WP10 v2 schema serialization round trips passed. Both StVK rigid-rotation/affine-patch cases passed. Both StVK residual/tangent/material-geometric-split cases passed. Both malformed J2 state-vector refusal cases passed. These results do not establish a production nonlinear solve, full load path, crash durability, or scientific qualification.

For the StVK tangent reports, the largest displayed global normalized error across all tested directions/steps was `3.723685797380157e-08`; the largest displayed error within the accepted final-three-step plateau was `1.3307535624298237e-10`. Both are below the test's proposed `1e-7` gate. Weak near-translation local comparisons were marked not applicable; global scaling remained the reported check. These are bounded results for the test's independent quadrature reference, not a general StVK FEM qualification.

## Newton sign and next integration boundary

For the assembly test convention,

```text
R(u) = F_int(u) - F_ext(u)
J_R  = dF_int/du - dF_ext/du
J_R Δu = -R(u)
```

For fixed dead loads, `dF_ext/du = 0`, so `K_t Δu = F_ext - F_int`. The production incremental driver forms `b = load_factor * external - internal` and applies the correction with `u <- u + Δu`; this matches the equation for the reviewed fixed-load route. Displacement-dependent/follower loads require their external-load derivative in `J_R`; no such route is certified by this review. Free-DOF reduction excludes prescribed DOFs from the solve and support reactions must be reconstructed from the full internal-minus-external imbalance.

The E01-A Armijo merit uses the target-minus-internal residual, so for fixed loads its directional derivative must use `-K_t p` with the same free-DOF restriction and residual scale. The production derivative-certificate registry remains empty at `src/solveur/core/nonlinear/e01a.py:38`; this campaign did not add a certificate. Element/global tangent tests alone do not establish an Armijo certificate, integrated Newton convergence, accepted-increment persistence, or restart fidelity.

Next bounded incremental campaign should use one existing small TET4 and one HEX8 mesh, with a staged elastic increment, first yield, plastic loading and unloading. Each trial must start from an immutable accepted material state; a deliberately rejected step must demonstrate rollback before a retry; the final accepted state must pass an independently computed free-DOF residual and reaction balance. Use the existing global assembly path and independent tensor return/quadrature references. Add checkpoint reconstruction only through the existing non-protected schema-v2 helpers, keeping it distinct from restart/crash durability. The exact path must first resolve the J2 derivative failures and obtain a route-specific Armijo derivative basis or have the Owner authorize a different experimental control path. Prepare a new hash-bound test identity and require exact-path execution authorization before running it. No integrated FEM case was executed in F3.

## Review and findings

This is the primary agent's read-only review of its own supervised run, not an independent review. The earlier independent J2 tangent review remains separate but did not review these F3 outputs.

* **P0:** None found in the supervised execution or test-only exception correction.
* **P1:** Four J2 global fixed-history tangent assertions fail candidate limits. Preserve these as unresolved scientific evidence; do not freeze the tangent gate or claim production Newton readiness.
* **P2:** The elastic patch expected-value literal has insufficient decimal precision for its stated assertion tolerance. The tangent failure traceback truncates the per-direction diagnostic record, limiting quantitative diagnosis.

## Final status

| Status | Result |
|---|---|
| `RESOURCE_SUPERVISOR` | `VERIFIED_FOR_CAMPAIGN` |
| `TEST_IMPORT_DEFECT` | `CORRECTED` |
| `GLOBAL_ASSEMBLY_COLLECTION` | `OBSERVED` — 20 reviewed cases |
| `GLOBAL_ASSEMBLY_VNV` | `PARTIAL` — 14 pass, 6 fail |
| `GLOBAL_RESIDUAL_JACOBIAN` | `INCOMPLETE` |
| `J2_GLOBAL_HISTORY` | `PARTIAL` |
| `GLOBAL_REACTION_BALANCE` | `INCOMPLETE` — patch reference cases failed before assembly |
| `TL_STVK_GLOBAL_TANGENT` | `VERIFIED_BOUNDED` for the two executed TET4/HEX8 cases |
| `WP10_CHECKPOINT_ROUNDTRIP` | `VERIFIED_BOUNDED` for schema-v2 serialization helpers only |
| `NEWTON_SIGN_CONTRACT` | `REVIEWED` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `INCREMENTAL_FEM_VNV` | `PREPARED_NOT_RUN` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Commits and remaining Owner decision

* `b3ff58571a915c61b84a1b3f025e62293328031f` — corrected test exception binding and updated exact hash bindings.
* `e2c78dfc696a14d5dceb7bee1406aa1190313797` — froze the corrected executable identity in the manifest.
* This report is documentation-only and records the actual failed run; it does not alter the executable identity.

The next Owner decision should authorize (1) the narrowly scoped expected-stress literal precision correction, and (2) a separate J2 tangent investigation with complete per-direction metrics and independent review. After the test identity changes, require fresh safety review and exact-path supervised execution authorization. Do not promote J2 tangent consistency, activate Armijo, or start integrated FEM execution from this report.
