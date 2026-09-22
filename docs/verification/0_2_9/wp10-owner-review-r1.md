---
doc_id: DOC-029-WP10-OWNER-REVIEW-R1
revision: 1.0
status: ready-for-owner-review
---

# WP10 Owner review R1 — provenance-corrected bounded coupled mechanics

## Verdict

```text
WP10_OWNER_REVIEW_STATUS = READY_FOR_OWNER_REVIEW
WP10_CANDIDATE_POINTS = PENDING_OWNER
WP10_OFFICIAL_POINTS = 0/6
```

The previous package remains historical and fail-closed. It is not relabeled.
This R1 package was executed prospectively after the corrected contract was
committed on a clean checkout.

## Provenance

```text
BRANCH = codex/wp10-provenance-requalification
AUTHORIZED_BASE_SHA = 22f1adb85d47c87d3c09b6607de170a6b4c20269
RUNNER_SHA = 2d87bc80b2875251ff093eaa76bee0020b4a48fd
CONTRACT_SHA = 38029b5e3fa9a063cc272b5d6c0510bb3687df35
EXECUTION_SHA = 38029b5e3fa9a063cc272b5d6c0510bb3687df35
CONTRACT_SHA256 = 3906d61d7d75edfdb6bb6400772fa9b4ede88fd6ca36d84a81ddbc56dc6c842c
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
ROUTE = frictionless_penalty_initial_search
WORKING_TREE = CLEAN_BEFORE_EXECUTION
```

The contract and evidence now agree on the penalty route. M1, M2 and replay
artifacts each persist the policy digest and contract hash. The replay was run
in a fresh process and its complete JSON is identical to M2.

## Results

| Gate | Production | Independent evidence | Status |
|---|---|---|---|
| M1 no-contact HEX8 corotational J2 | PASS_CANDIDATE | PASS observable recomputation | PASS candidate |
| M2 penalty contact + J2 HEX8 | PASS_CANDIDATE | PASS gap/penalty recomputation | PASS candidate |
| M3 fresh-process replay | PASS | complete JSON equal, displacement delta 0 | PASS replay |

The independent reference recomputes saved observables without importing
production contact routines. It is not an independent global FEM/Newton solve.

## Validation

```text
TARGETED_TESTS = 34 passed
JSON_VALIDATION = PASS
GIT_DIFF_CHECK = PASS
FULL_TEST_SUITE = NOT_RUN
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

## Limitations retained

- HEX8 only and one-element benchmark; no mesh-convergence gate;
- frictionless penalty contact with fixed initial search;
- no friction, finite sliding, updated search, MPI/PETSc or dynamics;
- no independent global FEM/Newton solve and no Code_Aster coupled correlation;
- no general finite-strain plasticity claim.

## Owner decision requested

```text
OWNER_ACCEPTS_WP10_M1 = PENDING
OWNER_ACCEPTS_WP10_M2 = PENDING
OWNER_ACCEPTS_WP10_M3_REPLAY = PENDING
OWNER_AWARDS_WP10_POINTS = PENDING
```

No merge, push or official point award was performed.
