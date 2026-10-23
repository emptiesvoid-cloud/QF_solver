# WP-E01-A integrated numerical V&V preparation

- **Date:** 2026-10-20
- **Scope:** preparation of bounded synthetic integrated tests for the frozen experimental E01-A route
- **Repository/worktree:** C:\wpc01-frictionless-public-integration-wt\wp-e01
- **Branch and reviewed baseline:** codex/qf-wp-e01-a-implementation-20261020 at 3065b2084672d031b22053c5e4a2436462c0e884
- **Preparation disposition:** test source and protocol prepared; execution not authorized in this record
- **Scientific status:** WP-E01 remains OPEN / EXPERIMENTAL_TARGET; no route certificate or qualification is created

## Prior focused unit evidence

The Owner reports the preceding focused run as 25/25: 20 tests in tests/unit/test_wp_e01a_policy.py and five in tests/unit/test_pytest_collection_safety.py. This preparation did not rerun them. The baseline source inputs match the reported digests:

| Input from the prior run | SHA-256 at the preparation baseline |
| --- | --- |
| tests/unit/test_wp_e01a_policy.py | D4D8DFCF6A61822F05B0E869409B00C3D671A0EF514F7E8262B1A56BA5D6D087 |
| tests/conftest.py before registering the new module | 0BAF0628D62F297D4F16A7A18D4C5A5D96C22B6377A1417F49E02F37AF411D98 |
| tests/unit/test_pytest_collection_safety.py | E7DD61C59DF67C65B877544254FA9F9C010B37AB5A24F17FF3258F666033ADCE |

This is prior unit evidence only. It does not establish integrated Newton behavior, checkpoint restart, native FEM accuracy, or production Armijo eligibility.

## Prepared test inventory

The new module contains 13 test functions. It is registered as a hash-bound NUMERICAL_UNIT module. One checkpoint-retry case is deliberately retained as a regression for a source-level contradiction found during this review; the campaign is blocked until that defect is resolved and reviewed.

| ID | Prepared test | Independent reference / behavior | Scope and disposition |
| --- | --- | --- | --- |
| N1 | test_synthetic_nonlinear_increment_matches_closed_form_root_and_free_dof_scale | Scalar equilibrium 10 u + 2 u^3 = 5.25 N, with exact root u = 0.5 mm; F_ref=10 N, so the frozen force limit is 1e-7 N. A very large constrained-DOF force/reaction is excluded from the free-DOF norm. | Direct private single-increment kernel; no public solve or assembly. The proposed displacement comparison tolerance is 1e-8 mm. |
| N2 | test_exactly_25_corrections_receive_a_26th_residual_evaluation | Synthetic R(u)=1-2u with deliberately inconsistent returned tangent 4 N/mm gives R_(n+1)=R_n/2. After 25 updates, the expected residual is 2^-25 N, above the 1e-8 N limit. | Confirms correction accounting, the final residual check, failure status, and no commit. The inconsistent tangent is a counting fixture only. |
| N3 | test_invalid_force_scale_and_constraint_scope_fail_closed | Missing/nonfinite predeclared scales, unsupported contact scope, and nonzero prescribed displacement are refused before contribution evaluation. | Policy and internal-kernel boundary checks. No public no-free-DOF solver call is made. |
| A1 | test_synthetic_residual_jacobian_matches_centered_difference_in_multiple_directions | For R_i(u)=F_i-(k_i u_i+c_i u_i^3), the exact J_R=diag(-k_i-3c_i u_i^2) is compared with centered directional differences for basis and mixed directions. Dφ[p]=RᵀJ_Rp/T_R² is checked for finite negative descent using the analytic Newton direction. | Test-only synthetic oracle; proposed error norm is ||FD-J_Rp||₂ <= 1e-9 N + 1e-7 ||J_Rp||₂. It does not register a production certificate. |
| A2 | test_test_only_armijo_oracle_visits_all_13_candidates_without_route_activation | Enumerates α_k=2^-k, k=0,…,12, ending at 1/4096, against a synthetic domain that excludes all candidates. | Test-only schedule oracle. The production certificate registry is asserted empty, and the production Armijo helper is not enabled. |
| C1 | test_synthetic_typed_failure_rolls_back_before_half_step_retry_and_commits_once | A synthetic finite increment bound rejects the full step, then accepts half steps to exactly λ=1. The fake contributor poisons its trial before rejection; the next call must see the unchanged accepted state. | Exercises E01-A load-control orchestration through a fake _solve_load_step; not production material/contact retry coverage. |
| C2 | test_untyped_increment_failure_is_terminal_after_rollback | An untyped material failure with copied diagnostic labels must not be treated as retry evidence. | Checks terminal refusal, rollback and unchanged caller-owned state. |
| C3 | test_minimum_increment_stops_typed_cutbacks_without_contaminating_accepted_state | Repeated synthetic typed failures apply β=0.5 until the case-declared relative minimum disallows another retry. | Checks bounded stopping, rollback and no accepted commit. |
| C4 | test_global_rejection_boundary_stops_before_another_attempt | A synthetic accepted checkpoint boundary state is seeded with a 25-entry rejection ledger. | Verifies the no-26th-attempt guard. This boundary fixture is not evidence that 25 rejections are reachable from a fresh path before the minimum-increment rule stops progress. |
| C5 | test_exact_lambda_one_endpoint_and_positive_clipped_tail | Successful synthetic load path must commit at literal λ=1; the separate increment helper checks a positive clipped remainder below the ordinary minimum. | Exercises exact endpoint acceptance without claiming a physical model result. |
| K1 | test_wp10_v2_checkpoint_recovers_last_accepted_state_and_counts_interruption_once | Writes one accepted synthetic increment to a temporary WP10 v2 NPZ, simulates interruption during the next trial with an in-process test sentinel, restores the last accepted state, and verifies the global rejection ledger is incremented once. Also checks inconsistent E01-A metadata mirror refusal. | All writes are confined to tmp_path. This checks container/route semantics, not power-loss durability or filesystem atomicity. |
| K2 | test_missing_and_corrupted_checkpoint_files_fail_closed | Missing and malformed NPZ records must be refused. | Temporary-file check only. |
| K3 | test_retry_checkpoint_record_matches_half_step_contract | A REJECTED_RETRYABLE record retains the failed increment Δλ and declares next_increment=0.5 Δλ; these are both required by the frozen contract. | BLOCKED by the source contradiction below. The test is prepared but was not run. |

The historical focused policy suite already covers individual residual-policy helpers, route-certificate refusal, typed-evidence construction, checkpoint identity helper behavior, and static correction-count ordering. The new module adds synthetic internal-kernel and load-control integration cases without duplicating or changing those frozen criteria.

## Independent reference definitions

### Nonlinear equilibrium

The main reference uses force in N and displacement in mm:

    f_int(u)=10 u+2 u^3,    f_target=5.25 N.

The closed-form root is u*=0.5 mm; the tangent used by the fixture is 10+6u² N/mm. For the free DOF, the predeclared scale is

    S_F=max(|5.25 N|,10 N)=10 N,
    T_R=10^-8 S_F+0 N=10^-7 N.

The constrained coordinate has a synthetic reaction much larger than the free residual. It is present to verify that the equilibrium norm and target scale use only free DOFs. The proposed 1e-8 mm root comparison is a diagnostic acceptance target for this synthetic fixture; it is not a new frozen solver tolerance and does not establish general FEM accuracy.

### Correction limit

The boundary fixture uses f_int=2u but supplies the intentionally incorrect tangent 4 N/mm. The update is u_(n+1)=u_n+R_n/4, hence R_(n+1)=R_n/2. Its test asserts exactly 25 applied corrections, one residual evaluation after correction 25, the resulting nonconverged status, and no accepted-state commit. It is not a material formulation or tangent-validation case.

### Residual derivative and Armijo oracle

For the two-coordinate synthetic cubic law,

    R_i(u)=F_i-(k_i u_i+c_i u_i^3),
    (J_R)_ii=-(k_i+3c_i u_i^2).

For direction p, the independent reference is J_R p; the numerical derivative is

    [R(u+h p)-R(u-h p)]/(2h).

The prepared geometric sweep is h = 1e-2, 1e-3, 1e-4, 1e-5. The proposed norm threshold is 1e-9 N + 1e-7 max(||J_Rp||₂, K_ref ||p||₂), where K_ref=max_i |k_i+3c_i u_i²| in N/mm. The proposed plateau rule requires the two finest consecutive perturbations to satisfy that bound while the coarsest remains truncation-dominated. These values require Owner approval before execution. The Armijo schedule case is an independent test-only enumeration. It does not add a route id or certificate to E01A_VERIFIED_DERIVATIVE_CERTIFICATES, which remains empty.

### Load-path and state scenarios

Synthetic _solve_load_step overrides exercise only the E01-A load-control orchestration, transaction, typed-error classification, attempt ledger and endpoint logic. They do not call _MaterialLoadControlContribution, element assembly, a material routine, or contact. This can verify orchestration around typed evidence, but cannot establish that production contributions emit valid increment-dependent evidence.

The checkpoint scenario uses NpzNonlinearCheckpointStore in tmp_path, the existing WP10 v2 envelope, and a fake model signature. It verifies an accepted state survives a simulated interrupted trial and the E01-A rejection record is not double-counted on restart. A same-process interruption sentinel is not a power-loss test. The test does not establish hardware/filesystem crash durability, directory-sync behavior, or power-failure atomicity.

## Source and execution-safety review

### Internal execution boundaries

- UnifiedNewtonEngine.solve has @guarded_solver_entry at src/solveur/core/nonlinear/driver.py:459. The synthetic Newton tests call only the private _solve_increment at line 628, with a hand-supplied scalar solve and fake contribution.
- The E01-A load-control method begins at src/solveur/core/nonlinear/load_control.py:417. In production it calls _solve_load_step; the prepared harness overrides that method, so the test cannot reach the production assembly/contribution code through this route.
- The E01-A production path persists IN_PROGRESS intent before opening its trial at load_control.py:668-673; the existing policy test checks that write-ahead ordering.
- E01A_VERIFIED_DERIVATIVE_CERTIFICATES remains an empty immutable mapping at src/solveur/core/nonlinear/e01a.py:35. No certificate is added or activated here.
- The checkpoint tests write only under pytest tmp_path; they do not call a public solver, solve_model, worker, subprocess, or native backend.

### Import and native-library audit

The selected module imports NumPy, SciPy sparse algebra, the internal driver/policy/state/load-control/checkpoint modules, and the NPZ checkpoint store. Static inspection of that closure and a repository-wide search for import gmsh, ctypes.CDLL, ctypes.cdll, and load_library found no Gmsh/native FEM load on this selected path. The pytest collection hook probes Gmsh only for the separately listed optional mesh modules; this module is not in that set. This is a source audit only; runtime isolation remains unverified until separately authorized execution.

The new module is explicitly hash-bound in tests/conftest.py as NUMERICAL_UNIT. Hash mismatch must remain fail-closed. The registry entry does not grant public-solver or native execution.

## Concrete source blocker: retry checkpoint interval validation

Static inspection found a contradictory pair of checks for a valid retry checkpoint:

1. load_control.py:802 computes retry_increment = 0.5 * proposed; the REJECTED_RETRYABLE metadata is persisted at lines 824-830 with the original failed attempt and the half-size next_increment.
2. e01a.py:759 unconditionally rejects when raw_increment > next_increment.
3. e01a.py:767-770 requires next_increment == 0.5 * raw_increment for REJECTED_RETRYABLE.

For every positive retry, conditions 2 and 3 conflict. Thus a checkpoint produced after a retryable rejection cannot pass the current metadata validator on restart. The prepared K3 case captures the valid Δλ/0.5 Δλ relation. No production change was authorized, so this defect remains unresolved and integrated checkpoint/restart acceptance is blocked.

The minimum corrective contract is to validate the failed-attempt interval against the original request and validate the retry interval separately for REJECTED_RETRYABLE; other statuses retain their applicable bounds. This is a remediation recommendation only, not an implementation performed here.

## Safety and result boundaries

- **Prepared campaign:** 13 test functions, all unexecuted.
- **Synthetic-only coverage:** nonlinear equilibrium reference, iteration-limit boundary, load-control retries, rollback, cutback floor and endpoint.
- **Checkpoint limitation:** temporary-file serialization/restart behavior only; no crash-durability claim.
- **Armijo limitation:** independent synthetic derivative and schedule oracles only; no production route certificate and no route-level Armijo validity claim.
- **J2:** tangent consistency remains BLOCKED_PENDING_INDEPENDENT_EVIDENCE; no tangent promotion is made.
- **Native FEM:** not invoked or authorized.
- **Qualification:** no scientific PASS or WP-E01 status promotion.

## Separate execution proposal

Do not execute the prepared module until the retry-checkpoint contradiction is corrected under its own authorization and the test/registry digests are refreshed. After that, request a separate Owner GO for exactly:

~~~text
python -m pytest -q tests/unit/test_wp_e01a_integrated_vnv.py
~~~

Proposed execution envelope: one in-process pytest invocation, 60-second wall-clock cap, 512 MiB process-memory cap, filesystem writes limited to pytest tmp_path; no subprocess, network, Gmsh, FEM assembly, public solver entry, or backend. These are operational bounds proposed for the future authorization, not a record of an executed run. Recheck branch/HEAD, file digests, hash-bound tier and call paths immediately before that authorization is exercised. Preserve every failure.

## Artifact integrity and static checks

| Prepared file | SHA-256 |
| --- | --- |
| tests/unit/test_wp_e01a_integrated_vnv.py | B15CC1A8D4B3F3FFA83F712CB5D3D364A848699F8682AF981A7EA9C6F04C4E83 |
| tests/conftest.py after the exact NUMERICAL_UNIT registration | AA72FAF3F317C7D445EE865D23D367C8B7815AF872029459133588C868F9BE4D |

Static validation completed without importing or executing the prepared module:

- Python AST parsing succeeded for the new test module and tests/conftest.py.
- The module contains 13 test functions.
- The registry digest matches the new test-module digest.
- git diff --check reported no whitespace errors.
- Source search found no public solver call, solve_model, subprocess, multiprocessing, ctypes native-load call, or Gmsh import in the prepared module.
- No pytest collection or test body was executed.

## Final status

- E01_A_UNIT_VERIFICATION: PASS_25_OF_25 — prior authorized result as reported by the Owner; not rerun here.
- INTEGRATED_NEWTON_TESTS: PREPARED
- CUTBACK_TRANSACTION_TESTS: PREPARED — synthetic orchestration only.
- CHECKPOINT_RESTART_TESTS: BLOCKED — retry metadata validation contradiction.
- ARMIJO_DERIVATIVE_ORACLE: PREPARED — independent synthetic reference only; production certificate remains absent.
- TEST_EXECUTION: NOT_RUN
- NATIVE_FEM_VNV: NOT_RUN
- WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET

No production code, scientific criteria, Armijo registry, WP-D01/WP-D02 files, canonical roadmap, or historical qualification record was modified.

## Follow-up checkpoint retry remediation — 2026-10-20

This section records the narrowly authorized correction at the verified retry-remediation baseline. It does not change the frozen E01-A contract or constitute checkpoint runtime evidence.

### Attempt and retry meanings

- `attempt.increment` is the increment of the attempted load interval. Once rejected, it is also the rejected increment retained in the write-ahead attempt record.
- `attempt.target_load_factor` is the target of that failed attempt; the accepted state remains at `attempt.base_load_factor` after rollback.
- `next_increment` is the next proposed increment. For `REJECTED_RETRYABLE`, it must equal `0.5 * attempt.increment` and satisfy the frozen minimum-increment rule.
- `accepted_lambda` and the state load factor remain the last accepted coordinate; rejection does not advance either value.
- `global_rejections` and `rejection_ledger` persist the rejection exactly once. The checkpoint attempt status distinguishes `IN_PROGRESS`, `REJECTED_RETRYABLE`, terminal rejection, and accepted states.

### Correction

`validate_e01a_checkpoint_record` now applies the generic `attempt.increment <= next_increment` bound only outside `REJECTED_RETRYABLE`. Retry records instead retain the original rejected increment and are validated by the existing exact `next_increment == 0.5 * attempt.increment` check plus the minimum-increment check. All statuses still validate the attempted target against its accepted base coordinate, the initial-increment bound, accepted-state identity, attempt identity, and ledger membership. `load_control.py` continues to persist the failed attempt and half-step proposal only after trial rollback; the writer and validator now agree on those distinct meanings.

WP10 v2 remains the outer checkpoint container. E01-A metadata stays additive; missing, corrupt, incompatible, or untrusted metadata remains fail-closed. This change does not reset or relax the global rejection budget and does not alter accepted-state commit or rollback behavior.

### Regression preparation

The synthetic checkpoint regression now covers a valid half-step record, a v2 temporary-file restart from the last accepted state using the half-size retry, a producer-generated retry checkpoint validated and resumed through the synthetic load-control harness, malformed cutback ratios, corrupted rejection ledger, missing attempt/write-ahead metadata, inconsistent accepted coordinate, impossible attempt interval, repeated restart after an interruption, and historical WP10 v2 state without E01-A metadata failing closed. Existing tests retain checks for v2 envelope compatibility and recovery of accepted displacement/material history. Fixtures use only the validator's supported provenance values; no validation rule is relaxed to accommodate a fixture. The module now has 21 test functions and 23 parameter-expanded cases.

These tests remain **PREPARED_NOT_RUN**. The temporary-file scenarios do not prove crash durability or filesystem atomicity. No test demonstrates production contributor retry evidence, public solver behavior, Armijo route certification, or numerical qualification.

### Remediation status

- `E01_A_CHECKPOINT_CONTRADICTION: FIXED_BY_SOURCE`
- `RETRY_CHECKPOINT_INVARIANTS: PRESERVED_BY_SOURCE; TESTS_NOT_RUN`
- `GLOBAL_REJECTION_LEDGER: PRESERVED_BY_SOURCE; TESTS_NOT_RUN`
- `WP10_V2_COMPATIBILITY: VERIFIED_BY_SOURCE_ONLY`
- `CHECKPOINT_RESTART_RUNTIME: NOT_VERIFIED`
- `INTEGRATED_TESTS: PREPARED_NOT_RUN`
- `E01_A_STATUS: OPEN / EXPERIMENTAL_TARGET`

The change is limited to status-aware retry interval validation and regression preparation. A separate Owner GO is required before executing the prepared test module.

### Static integrity record

- Validator: `src/solveur/core/nonlinear/e01a.py:615-785`; the status-aware bound is at lines 756-768 and the exact retry half-step/minimum check remains at lines 777-778.
- Existing producer: `src/solveur/core/nonlinear/load_control.py:745-762` rolls back, verifies the accepted-state digest, and records the rejection; lines 802-830 compute and persist the half-size retry; line 668 persists `IN_PROGRESS` intent before opening the trial. The producer was inspected and not changed.
- Test source: `tests/unit/test_wp_e01a_integrated_vnv.py` (20 functions / 22 parameter-expanded cases), tier `NUMERICAL_UNIT`.
- `python -S` AST parsing passed for `e01a.py`, the test module, and `tests/conftest.py`. Static registry parsing confirmed the test's tier and exact digest. A targeted source scan found no public solver, subprocess, native-library, or Gmsh call in the test module. `git diff --check` passed. These are source checks only; no test collection or execution occurred.

| File | SHA-256 |
| --- | --- |
| `src/solveur/core/nonlinear/e01a.py` | `65277EB7C1049BE355E67E536495FC436B6C784CB7F3354CE57903040E77FEF8` |
| `tests/unit/test_wp_e01a_integrated_vnv.py` | `4EF703869D4A14F9F7BE81B4954764B70440F8CF51CCFA856F7A6C26BBA65975` |
| `tests/conftest.py` | `BB478DC8DB94E6C82D98070D24E235342A30496176DB3C3923450E4BFAB714F8` |
