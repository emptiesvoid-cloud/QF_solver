---
doc_id: DOC-029-WP06D-R2-RUNNER-SAFETY-PREP
revision: 1.0
status: phase_0_preparation
applicable_version: 0.2.9-development
---

# WP06-D R2 runner safety preparation

## Outcome

WP06-A/B/C have been revalidated on the current governing source and remain a
4/8 technical candidate pending Owner review. WP06-D has not been requalified.
The historical R1 M2 failure remains authoritative and unchanged.

The old R1 command-line runner was found unsafe for another execution: it
uses the node-specific `arc_length_control_dof` output instead of the frozen
mean crown observable, and writes to shared historical files under
`qualification/0_2_9/`. Its normal entry point is now quarantined and returns
`BLOCKED_STALE_R1_RUNNER` before any solve or file write. The old R1 result
files themselves were not edited.

## Safety work completed

- Added a fail-closed Phase-1 authorization validator. It requires a frozen
  execution contract, an explicit Owner grant bound to the exact branch, HEAD,
  contract SHA-256 and policy digest, a clean worktree, conditional M3 scope,
  and a previously unused output directory.
- Added regression tests for missing contracts/grants, dirty state, branch/SHA
  drift, contract hash mismatch, output-directory reuse, and the quarantined
  R1 command entry point.
- Preserved the existing passive helpers for lossless accepted-state
  checkpoints, the frozen mean-crown observable, and independent vector
  force/moment reconstruction.

This is still preparation tooling, not an executable R2 campaign. The current
R1 contract remains `PHASE_0_PREPARATION`; no R2 frozen contract or Owner
authorization exists. The authorization helper is tested with synthetic
fixtures only and has not authorized or launched a real run. It receives
branch, SHA, and worktree-clean values from its caller rather than querying
Git itself, and no R2 runner currently invokes it. Therefore it is a tested
validation helper, not yet an effective execution gate.

## Historical D evidence retained

The R1 record remains `FAIL_CLOSED`: M1 passed; M2 reached 80 accepted steps
but did not demonstrate the required load-factor turning point, and its
reported moment-equilibrium relative error was `2.438196359642231e-05` against
the frozen `1e-8` gate. M3 was not run. The D1 diagnostic and all original raw
files remain untouched. This safety preparation does not reinterpret that
failure or claim a numerical correction.

## Verification

Focused continuation, checkpoint, radius-policy, WP06 contract, and runner
guard tests: **145 passed** in the final recorded run. The first run is
preserved separately: 144 passed and one failed because the quarantined runner
used a direct-script import path when loaded as a package. That import was
corrected, and the subsequent 145/145 XML is the passing evidence; the earlier
XML is classified as a superseded diagnostic failure, not silently discarded.

Documentation-generation/registry tests were reported as 17 passed and 2
skipped in the working session, but no separate machine-readable result was
retained, so this package does not treat that count as independently
verifiable evidence. Ruff and compileall passed for the touched runner,
guard, and test files. The complete repository test suite was not run.

Test output:
`qualification/0_2_9/wp06_abc_revalidation_r1/wp06d-guard-targeted-tests-r2.xml`

Superseded first attempt, retained for traceability:
`qualification/0_2_9/wp06_abc_revalidation_r1/wp06d-guard-targeted-tests.xml`

## Governance and next gate

```text
WP06_A_B_C_CANDIDATE = 4/8
WP06_OFFICIAL_POINTS = 0/8
GLOBAL_OFFICIAL_TOTAL = 66/100
WP06D_R1_HISTORICAL_STATUS = FAIL_CLOSED (preserved)
WP06D_R2_CONTRACT = NOT_CREATED / NOT_FROZEN
WP06D_OWNER_EXECUTION_AUTHORIZATION = NOT_PRESENT
STRUCTURAL_SOLVES_RUN = NO
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
FULL_TEST_SUITE_RUN = NO
```

Before any structural requalification, prepare and review an R2 contract
bound to the current governing policy without changing R1 physics or
thresholds. The executable runner must use per-accepted-step checkpoints and
the frozen mean-crown monitor, reconstruct equilibrium from each archived
state, query Git provenance itself, invoke the authorization validator before
any solve, and write only to a new SHA-specific directory. Then obtain a
separate Owner authorization bound to the final source/contract/policy
digests. M3 remains conditional on M1, M2, independent-reference, equilibrium,
and replay gates passing.
