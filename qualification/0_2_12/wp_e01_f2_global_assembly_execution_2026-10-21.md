# WP-E01-F2 — Controlled global-assembly execution and Newton sign review

**Date:** 2026-10-21
**Package status:** WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## Executive result

The reviewed Windows Job Object supervisor enforced the authorized process and committed-memory bounds. The exact global-assembly module did not reach test execution: its import references an exception class that does not exist in the current source API. The collection guard failed closed with zero collected items. No numerical element or assembly case ran.

The first supervised launch exposed a test-environment packaging issue (`pytest` was not visible when user-site loading was disabled). The wrapper was corrected to use the already-installed, explicitly approved package root under Python `-S`, and its safety checks were repeated. The second launch reached pytest collection and exposed the test-source import defect. No correction was made to the test module or its registry entry because the authorization was bound to its original digest.

| Status | Result |
|---|---|
| `RESOURCE_SUPERVISOR` | `VERIFIED_FOR_CAMPAIGN` |
| `GLOBAL_ASSEMBLY_EXECUTION` | `BLOCKED` — collection error, zero tests executed |
| `GLOBAL_RESIDUAL_JACOBIAN` | `INCOMPLETE` — no numerical evidence in this campaign |
| `J2_GLOBAL_HISTORY` | `INCOMPLETE` — no numerical evidence in this campaign |
| `GLOBAL_REACTION_BALANCE` | `INCOMPLETE` — no numerical evidence in this campaign |
| `TL_STVK_GLOBAL_TANGENT` | `INCOMPLETE` — no numerical evidence in this campaign |
| `WP10_CHECKPOINT_ROUNDTRIP` | `INCOMPLETE` — no numerical evidence in this campaign |
| `NEWTON_SIGN_CONTRACT` | `REVIEWED` by source inspection |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED`; registry remains empty |
| `INCREMENTAL_FEM_VNV` | `PREPARED_NOT_RUN` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

Historical evidence remains unchanged: D4R direct-element verification was 65 PASS for its historical test identity. That result was not rerun and does not establish global assembly or nonlinear solver behavior.

## Repository identity and commits

| Item | Verified value |
|---|---|
| Repository root | `C:\\wpc01-frictionless-public-integration-wt\\wp-e01` |
| Origin | `https://github.com/emptiesvoid-cloud/QF_solver.git` |
| Branch | `codex/qf-wp-e01-a-implementation-20261020` |
| Campaign starting HEAD | `595ce44c27142643336d160af7870cdb68fb7c6a` |
| HEAD before this report | `e8b105ac042163dc6d21b4fca1e5c706ad6a9d5c` |
| Working tree before this report | Clean |

Campaign commits:

1. `654cbf42dcc91204d203a5987a6393b1e4a4329e` — add bounded WP-E01-F2 supervisor.
2. `b3589753a31d3d0774286180e68924d720632068` — harden collection guard and supervisor checks.
3. `e8b105ac042163dc6d21b4fca1e5c706ad6a9d5c` — isolate approved Python package imports in the child.

No production solver file, authorized test, safety registry, canonical roadmap, or historical qualification record was modified. This report is the only additional change proposed by this document.

## Resource supervisor and preflight

The campaign-specific wrapper is `experiments/wp_e01f_global_assembly_supervisor.py`. It accepts no command-line arguments and fixes the interpreter, repository working directory, test path, hashes, pytest options, temporary directory, environment, and process limits. It uses the repository's existing Windows kill-on-close Job Object support. The child is created suspended, assigned to the Job Object before resuming, and verified as the only active process. Shell expansion is disabled (`shell=False`); breakaway is disabled; the Job Object has kill-on-close. BLAS and numerical-library thread variables are set to one. Plugin autoload and bytecode writes are disabled; Python `-S` is used with an explicit approved package root to avoid `.pth` and `sitecustomize` loading.

The Job Object limit flags were `8968`, including job committed-memory, per-process committed-memory, active-process, and kill-on-close limits. The job and per-process committed-memory caps were each `268435456` bytes; active process limit was `1`; breakaway was disabled. This is a **commit-memory limit**, not an RSS/working-set limit. Each phase had a 120-second wall-clock deadline and a five-second cleanup reserve. No automatic restart or retry was configured. The exact interpreter was `C:\\Python313\\python.exe`, Python `3.13.1`, pytest `8.4.1`, and psutil `7.2.2` on 64-bit Windows.

Preflight confirmed the test and conftest digests, the test's `NUMERICAL_UNIT` digest binding, fixed source identities, and a fixed 20-case inventory guard. The reviewed test imports and calls in-memory TET4/HEX8 algebra only. No Gmsh initialization, native FEM executable, public solve, `solve_model`, worker, child process from the test, network access, or protected checkpoint write was present in the reviewed path. The checkpoint fixture is limited to the existing schema-v2 serialization helper under pytest `tmp_path`. The Job Object's active-process limit also prevents a second child while the pytest process is active.

Observed peak commit for both attempts was below the cap. The first attempt peaked at `5,341,184` bytes and the second at `77,275,136` bytes. Both runs reported `VERIFIED_WINDOWS_JOB_CLOSED`; neither timed out. These observations demonstrate enforcement and cleanup for these launches, not a numerical test result.

## Execution chronology and preserved failures

Authorized test identity:

```text
python -m pytest -q -s tests/unit/test_wp_e01e_global_assembly_vnv.py
```

The supervisor adds only the reviewed collection-guard plugin, disables the cache provider, gives pytest an isolated temporary root, and launches the exact target. Pytest's collection-finish guard records and checks the exact node IDs before the runtest loop. In the second attempt, module import failed before that record could be written.

| Attempt | Result | Runtime / peak commit | Evidence |
|---|---|---|---|
| 1 — initial child environment | Child exited 1 in `0.102 s`; no test collection. Error: `No module named pytest`, caused by hiding the user-site package root while not explicitly adding the approved installation. Cleanup verified; no timeout. | `5,341,184` bytes | Root `<local-temp>\\qf_wp_e01f_global_assembly_915gwzbu`; wrapper hash in this launch: `C6A5AEEDB47C00F823A168F46B129BAD437A0A4ED1347E4C7AA627606A50C96C`. `stderr.log` SHA-256 `3F0E89600E5BE59BFD224E67DBB861258674CBAAE2A12DDB46318EB665114F51`; `phase_result.json` SHA-256 `57F3F6EC3BFDACE4C18706CC05428A51E65498E826594166A0762992C90714CB`; `summary.json` SHA-256 `0B5F3679A9D9BA1055332FC4B70695A725B51762BABE890067A7395F5554A555`. |
| 2 — corrected child environment | Child exited 5 in `6.331 s`; pytest reported one collection error and zero collected test cases. The guard failed closed after the import error. No test body ran. Cleanup verified; no timeout. | `77,275,136` bytes | Root `<local-temp>\\qf_wp_e01f_global_assembly_6zsv9c6d`; final wrapper hash: `180F11C60A643537CE79BCF14CD2CD489B474800B4B2800710A74B0D7B858A58`. `stdout.log` SHA-256 `743567ECE91E640B8B39C9ADC90DB44CF70059A089FE0A7A37BB876E8EFB9C5D`; empty `stderr.log` SHA-256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`; `phase_result.json` SHA-256 `2B8127087338F5BFAB137E680323BBACD11DA7142F44CD0007E26217350AE7DC`; `summary.json` SHA-256 `D385B98579E5FF477CC31753B66996D102531B6E7181F0BD22CCD0E7E7A761CE`. |

Second-attempt pytest trace:

```text
tests/unit/test_wp_e01e_global_assembly_vnv.py:23
from solveur.core.errors import NonlinearConvergenceError
ImportError: cannot import name 'NonlinearConvergenceError'
Did you mean: 'NumericalConvergenceError'?
1 error in 4.71s
WP-E01-F collection inventory mismatch: count=0, functions=[]
```

There were `0 PASS`, `0 FAIL` test bodies, `0 SKIP`, `0 XFAIL`, `0 XPASS`, and `0/20` collected cases; pytest had one import/collection error. The exit code `5` includes the collection guard's fail-closed exit. It must not be described as a numerical failure or as 20 passing/failing cases.

## Collection defect and independent review

`src/solveur/core/errors.py` defines `NumericalConvergenceError`; it does not define `NonlinearConvergenceError`. The authorized test imports the nonexistent name at line 23 and also uses it in the negative assertion at line 991. Source inspection shows the malformed J2 integration-point state is rejected through `InputValidationError`, which the assembly boundary wraps as `NumericalConvergenceError`. The narrow test correction is therefore to import and assert the actual public error type, with the existing message assertion retained. This is a test-source defect; no production correction is indicated by the evidence.

A separate agent completed a read-only review of the failure and source conventions. That review did not edit files, collect tests, run tests, or execute numerical calculations. It independently identified the same bad test import and confirmed the source sign mapping below. It is an independent **source review**, not independent numerical V&V.

Findings:

* **P0:** None identified in the reviewed wrapper, collection guard, or source sign mapping.
* **P1:** The test import and matching exception assertion block all 20 prepared cases from collection. The test and registry identities must be updated together before another run.
* **P2:** The route-level sign mapping is internally consistent for fixed/dead loads, but the global assembly module could not provide numerical confirmation. The current fixture does not exercise general external loading or general constraint operators.

## Source hash inventory

The authorized test and registry remained exactly at their frozen digests. The wrapper preflight rechecked the production-source set against the WP-E01-E report.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01e_global_assembly_vnv.py` | `A6F6F104E331F1E9E09B384CF65B9FD49B783392C5B3C6002D67FE81A9ECEE45` |
| `tests/conftest.py` | `2A448E4070A8A441BFC0E3CE5B506E66CD104FB45A85DB7EDDF00D7A46A2FBAC` |
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
| `experiments/wp_e01f_collection_guard.py` | `324D49F2542FAF2FBDD9B31DA2188EAB6FDEA5F512CC85A15FE26A7D42B36E24` |
| `experiments/wp_e01f_global_assembly_supervisor.py` | `180F11C60A643537CE79BCF14CD2CD489B474800B4B2800710A74B0D7B858A58` |

## Newton residual and Jacobian sign contract

For the element fixture, use the documented convention

\[
R(u)=F_{\mathrm{int}}(u)-F_{\mathrm{ext}}(u),\qquad
J_R=\frac{\partial R}{\partial u}
=K_{\mathrm{int}}-\frac{\partial F_{\mathrm{ext}}}{\partial u}.
\]

For the reviewed fixed/dead-load route, the external vector is assembled once and scaled by the load coordinate, so it has no displacement derivative. Then `J_R = K_int`, with `K_int = dF_int/du`. Newton requires

\[
J_{R,ff}\,\Delta u_f=-R_f
=F_{\mathrm{ext},f}-F_{\mathrm{int},f}.
\]

The production driver forms `b = load_factor * external - internal` at `driver.py:825` and solves the reduced system with `K_ff` at approximately line 980. This is the same equation, `K_ff Δu_f = b_f`. The free DOFs are obtained by removing fixed indices; reactions on fixed DOFs are reported using `F_int - F_ext` in `solver.py:401` and `audit.py:1223`, with the audit's explicit sign-convention string at `audit.py:1252`.

There is a separate E01-A residual convention: `b = target - internal`. Along correction `p`, the residual derivative action is `-K_ff p` (`load_control.py:1062`), matching its candidate residual `target - candidate_internal` (`load_control.py:1074`). For the normalized merit `φ = 1/2 ||b/T_R||²`, an exact linear solve `K_ff p = b_f` gives `Dφ[p] = -(b_f/T_R)^T(b_f/T_R) < 0` for nonzero residual. This identity does **not** certify inexact solves, branch changes, trial-state consistency, or every material route. The registry `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` is empty (`e01a.py:38`), and missing certificates fail closed; no certificate was activated.

The currently reviewed solver load path uses a fixed assembled load vector. A follower or otherwise displacement-dependent load would require the external tangent contribution `-dF_ext/du`; the reviewed route does not assemble or verify that term. Prescribed-displacement DOFs are eliminated and reconstructed in the experimental scope; unsupported constraints such as MPC/RBE/contact remain outside it. The test module's analytical face traction is a reference, not an external vector assembled into a solve. Because its import failed, none of these sign equations received numerical confirmation in this campaign.

## Next incremental nonlinear FEM campaign proposal

No new integrated test module was created or executed. The following are proposed node IDs for a bounded later campaign, not registered or executable tests:

| Proposed node ID | Fixture |
|---|---|
| `test_tet4_elastic_increment_converges_to_affine_reference` | One constrained TET4 elastic increment; compare displacement, internal/external force, free residual, and support reaction with an independently derived affine reference. |
| `test_hex8_elastic_increment_converges_to_affine_reference` | Same observables for HEX8 with its actual quadrature and DOF ordering. |
| `test_tet4_j2_monotone_yield_and_accepted_history` | TET4 J2 loading from virgin state through first yield and a later accepted plastic increment; compare stresses and state variables with an independent tensor return. |
| `test_hex8_j2_monotone_yield_and_accepted_history` | Same history checks for HEX8, retaining per-integration-point states. |
| `test_tet4_failed_increment_rolls_back_before_retry` | Cause a typed retryable increment failure and verify that the retry starts from the exact accepted displacement and J2 state. |
| `test_hex8_failed_increment_rolls_back_before_retry` | Same rollback check with eight integration-point states. |
| `test_incremental_global_residual_jacobian_fixed_history` | For each permitted element family, compare the assembled fixed-history residual derivative to the assembled tangent along mixed, independent displacement directions. |
| `test_incremental_reactions_close_force_and_moment_balance` | Verify reaction reconstruction on constrained DOFs for accepted displacement-controlled increments. |
| `test_incremental_checkpoint_restart_preserves_accepted_state_and_ledger` | Restart only through an authorized non-protected API; compare accepted-state identity, load coordinate, and global rejection ledger. |
| `test_incremental_route_refuses_missing_armijo_certificate` | Verify fail-closed route behavior while the production derivative-certificate registry remains empty. |

Candidate file: `tests/unit/test_wp_e01f2_incremental_newton_vnv.py`. Intended classification is `NUMERICAL_UNIT` only if the final imports/call graph stay within the approved in-memory path. It has no current file, hash, registry binding, or safety approval. The checkpoint item cannot establish crash durability. Any public nonlinear solve, protected checkpoint path, or broader execution route needs explicit authorization and a fresh safety classification.

A bounded later campaign should proceed in this order:

1. Begin with one constrained TET4 and one constrained HEX8 using a linear-elastic limit with an independently computed affine displacement, stress, traction, free residual, and support reaction.
2. Add a small-strain J2 monotone history with separately declared virgin and accepted state. Compare initial yield and plastic stress against an independent tensor return; record the incoming state digest before each trial.
3. Add unload/reload only if the selected route can represent multiple accepted load segments; otherwise report that capability as unsupported rather than synthesizing an integrated-history claim.
4. Compare the global residual and assembled tangent with fixed-history directional differences, checking the residual sign, free-DOF reduction, and reaction closure. Retain absolute and normalized errors and report weak directions separately. Numerical tangent gates remain proposed and require Owner review.
5. Exercise a retryable failed increment and verify accepted-state rollback, then checkpoint/restart at an accepted state only through a non-protected interface. This cannot establish crash durability.
6. Keep Armijo disabled unless a route-specific derivative certificate is independently established and separately approved. The current empty certificate registry cannot be bypassed.

The proposed campaign should use the frozen E01-A equilibrium rule only when running that authorized route: `||R_f||_2 <= 1e-8 S_F + F_abs`, with a predeclared physical `F_ref`, `F_abs = 0 N` by default, and `S_F = max(||f_target,f||_2, F_ref)`. Missing/invalid scales or unsupported constraints fail closed. It should count at most 25 correction updates per attempted increment and verify the residual after the last correction. The approved load-step/cutback/checkpoint invariants apply; tangent error thresholds remain proposed. These are contract requirements, not solver accuracy or qualification evidence. The test suite must not evade the empty Armijo certificate registry; if no eligible non-Armijo experimental integration route exists, the integrated numerical campaign remains blocked until the route is separately authorized.

The initial stage should remain synthetic/in-memory and small. Any use of a protected public nonlinear solver route needs its own exact-path Owner authorization; this report authorizes no such execution.

## Exact next Owner decision

Authorize the following bounded correction and new executable identity before another test launch:

1. Correct the two test references to the solver's actual `NumericalConvergenceError` type, retaining the state-vector message check; do not change production code or numerical thresholds.
2. Recompute the test SHA-256, update the existing `NUMERICAL_UNIT` digest binding in `tests/conftest.py`, and update the wrapper's expected test digest. Keep the classification and deny rules unchanged.
3. Perform fresh source/hash/import/collection/supervisor review for the corrected identity.
4. If that review passes, authorize the corrected hash-bound module only through the same bounded Job Object supervisor; preserve the original collection failure and do not run other modules.

A later integrated Newton/FEM campaign is a separate decision after the assembly evidence is available. It must not activate the production Armijo certificate, assert J2 tangent qualification, or claim native FEM/overall qualification without the corresponding evidence and authorization.

## Final evidence boundary

This campaign verified repository/source identity, the bounded supervisor configuration and cleanup behavior, static import safety, the collection failure, and the source-level Newton sign mapping. It did not verify any numerical assembly result, material update, reaction value, tangent error, checkpoint round trip, integrated equilibrium, crash durability, Armijo route certificate, native FEM behavior, or scientific qualification.
