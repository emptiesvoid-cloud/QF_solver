# WP-E01-A Checkpoint Identity Stabilization and Integrated V&V

**Date:** 2026-10-20  
**Scope:** WP-E01-A only; bounded synthetic offline verification  
**Scientific status:** OPEN / EXPERIMENTAL_TARGET  
**Qualification status:** NOT ACQUIRED

## Executive result

The retry-checkpoint failure was caused by including `continuation_state.next_increment` in the accepted-state identity. A rejected increment leaves the accepted physical and constitutive state unchanged, then updates the retry schedule to the approved half increment. The digest therefore changed even though rollback was correct. The deterministic serializer and checkpoint payload were not the cause.

The accepted-state identity now binds displacement, accepted load coordinate, material/contact state, and continuation fields other than `next_increment`. Retry scheduling remains separately recorded and validated, including the exact half-step relation. The additive E01-A metadata identifier is now `qf-wp-e01-a-checkpoint/v2`; the outer WP10 `NonlinearCheckpointV2` format remains version 2.

Both authorized offline suites passed in each of two verification cycles. The final cycle passed 34 integrated synthetic cases and 25 policy/collection-safety cases. These results do not establish native FEM behavior, production retry coverage, production Armijo certification, crash durability, or scientific qualification.

## Baseline and provenance

- Repository: `C:/wpc01-frictionless-public-integration-wt/wp-e01`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Branch: `codex/qf-wp-e01-a-implementation-20261020`
- Verified starting HEAD: `76b6e2fe4dc792fa5af4ea4e8a1f90cea5ae512c`
- Starting worktree: clean
- The previous run's reported 22-pass / 1-fail result was not rerun or independently reproduced before this campaign. Its reported failure was `test_produced_wp10_v2_retry_record_validates_and_resumes_at_half_increment`, raising `InputValidationError: WP-E01-A uncommitted attempt base state identity is inconsistent.`

## Defect analysis and correction

The producer captures the accepted-state identity and persists an `IN_PROGRESS` attempt before trial-state creation. On retryable failure, execution rolls back and verifies the accepted-state digest, appends the rejection ledger entry, then sets `next_increment = 0.5 * rejected_increment` for retry. The accepted physical state is unchanged, but the old identity function included that mutable scheduling proposal. The validator recomputed the identity from the restored state and rejected the record.

The canonical serializer is deterministic by value: mapping keys are canonicalized, floats use `float.hex()`, and arrays include dtype, shape, and bytes. Material and contact state remain part of the accepted-state digest. There was no evidence of object-identity hashing, array-copy instability, dtype conversion, signed-zero instability, or trial-state contamination as the cause.

The correction is limited to identity scope. `next_increment` remains present in the E01-A record and continuation state and is equality-checked; retry records must still satisfy the exact approved `0.5` cutback relation and minimum-increment rule. The schema tag changed from E01-A subrecord `/v1` to `/v2` so the changed identity meaning cannot be silently confused with old records. The enclosing WP10 v2 format and historical WP10 v2 behavior are unchanged. Older E01-A `/v1` metadata fails closed; no migration or archive rewrite was performed.

Relevant source locations:

- `src/solveur/core/nonlinear/e01a.py:25` — additive E01-A checkpoint schema identifier.
- `src/solveur/core/nonlinear/e01a.py:545` — accepted-state identity excludes only retry scheduling metadata.
- `src/solveur/core/nonlinear/e01a.py:664` — continuation schedule is independently checked against the record.
- `src/solveur/core/nonlinear/e01a.py:789` — retry increment is validated against the frozen half-step rule.
- `src/solveur/core/nonlinear/load_control.py:497` — write-ahead E01-A record construction.
- `src/solveur/core/nonlinear/load_control.py:536` — persistence helper for accepted-state metadata.
- `src/solveur/core/nonlinear/load_control.py:666-673` — persist `IN_PROGRESS` intent before `begin_trial`.
- `src/solveur/core/nonlinear/load_control.py:744-824` — rollback verification, rejection-ledger update, and retry checkpoint creation.
- `src/solveur/core/nonlinear/load_control.py:854` — accepted-state record after increment acceptance.

## Regression coverage

The integrated module now has 32 test functions and 34 parameter-expanded cases. Added or extended coverage includes:

- Valid half-size retry checkpoint and restart from the accepted state.
- Rejection #25 recording and refusal to begin attempt #26.
- Fail-closed handling of obsolete E01-A `/v1` identity metadata.
- Identity invariance under retry-schedule changes while material-state changes remain identity-bound.
- Rejection of mutated material history, missing rejection history, and already-counted in-progress intent.
- Canonical mapping-order stability and integration-point ordering sensitivity.
- Rejection of mutated accepted numerical state, mismatched load-path identity, and impossible retry intervals.
- Duplicate commit/rollback refusal and accepted endpoint restart without repeating commits.
- Existing synthetic Newton, residual scaling, 25-correction/final-residual, retry classification, rollback, endpoint, and Armijo derivative-oracle cases remain in the reviewed module.

## Authorized test executions

All commands below were run sequentially after exact-path and execution-safety preflight. No tests or source were changed between the commands within a cycle.

| Cycle | Exact command | Result | Pytest duration | Tool wall time |
|---|---|---:|---:|---:|
| 1 | `python -m pytest -q tests/unit/test_wp_e01a_integrated_vnv.py` | 27 passed, 0 failed, 0 skipped | 3.87 s | 7.88 s |
| 1 | `python -m pytest -q tests/unit/test_wp_e01a_policy.py tests/unit/test_pytest_collection_safety.py` | 25 passed, 0 failed, 0 skipped | 1.42 s | 3.68 s |
| 2 | `python -m pytest -q tests/unit/test_wp_e01a_integrated_vnv.py` | 34 passed, 0 failed, 0 skipped | 1.79 s | 4.08 s |
| 2 | `python -m pytest -q tests/unit/test_wp_e01a_policy.py tests/unit/test_pytest_collection_safety.py` | 25 passed, 0 failed, 0 skipped | 1.37 s | 3.55 s |

No third cycle was required: all target synthetic acceptance criteria passed. Cycle 1 and cycle 2 are distinct recorded runs; the cycle 2 integrated suite includes the expanded boundary and checkpoint regressions.

## Execution-safety review

Before each authorized execution, the selected modules were checked against the hash-bound pytest safety registry and reachable imports. `test_wp_e01a_integrated_vnv.py` remained classified `NUMERICAL_UNIT`; `test_wp_e01a_policy.py` remained `NUMERICAL_UNIT`; `test_pytest_collection_safety.py` remained `PURE_UNIT`. The registry classifications were not broadened.

The selected synthetic paths use Python-level contributors, NumPy/SciPy algebra, and temporary checkpoint files. Collection-time Gmsh probing remains lazy and is not reachable for these selected modules. No selected test path reaches `solve_model`, public nonlinear solver execution, FEM assembly, Gmsh/native FEM loading, workers, or child processes. AST parsing and `git diff --check` passed. These checks are source/scope evidence, not runtime proof of native-code absence beyond the inspected paths.

## Independent review

A separate read-only review inspected producer/validator agreement, identity stability by canonical value, accepted-state isolation, rejection-ledger persistence, WP10 v2 compatibility, and fail-closed cases. It found no P0/P1 finding and made no changes or test runs.

The reviewer identified one nonblocking P2 hardening limit: the validator checks ledger length, ordering, unique attempt IDs, rollback verification, and active-attempt membership, but does not cross-check every historical ledger row's base-state identity, attempted coordinate, retryable flag, and failure reason against a corresponding attempt record. The checkpoint digest protects ordinary payload corruption, and the tested structural-corruption cases fail closed; adversarially modified and re-digested ledger semantics were not independently tested. This remains a residual risk, not a verified property.

## Evidence and file hashes

Source/test changes were committed as `289c43cf` (`fix(e01a): stabilize retry checkpoint identity`).

| File | SHA-256 |
|---|---|
| `src/solveur/core/nonlinear/e01a.py` | `E3BACB4961A28E2A1D37C47999CA14A0A950C7FA9A2829083AFE5E6159961308` |
| `tests/unit/test_wp_e01a_integrated_vnv.py` | `CF61980798C10D7426035A6265492C4030816ADE38ED167731835181F22D7E0B` |
| `tests/conftest.py` | `90331559307AAF507A8C81B0A2ECBD5DCFB71F2AEF92A575286A32A59D055530` |
| `tests/unit/test_wp_e01a_policy.py` (unchanged) | `D4D8DFCF6A61822F05B0E869409B00C3D671A0EF514F7E8262B1A56BA5D6D087` |
| `tests/unit/test_pytest_collection_safety.py` (unchanged) | `E7DD61C59DF67C65B877544254FA9F9C010B37AB5A24F17FF3258F666033ADCE` |

## Status and remaining limits

- Retry checkpoint identity and restart: `PASS_SYNTHETIC` on the tested WP10 v2 routes.
- Newton analytical reference: `PASS_SYNTHETIC`.
- Cutback and rollback invariants: `PASS_SYNTHETIC`.
- Synthetic Armijo derivative oracle and 13-trial schedule: `PASS` in the reviewed synthetic scope.
- Production Armijo route certificate: `NOT_VERIFIED`; registry remains empty.
- J2 tangent consistency: `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`.
- Production material/contact retry support: `NOT_VERIFIED`.
- Checkpoint abrupt-crash durability and filesystem atomicity: `NOT_VERIFIED`.
- Native FEM V&V and public-solver execution: `NOT_RUN`.
- Scientific qualification: `NOT_ACQUIRED`.
- WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

No canonical roadmap, historical qualification record, WP-D01/WP-D02 content, scientific threshold, production Armijo certificate, qualification, merge, or release state was changed.
