---
doc_id: DOC-029-WP06-ABC-REVALIDATION-R1
revision: 1.0
status: ready_for_owner_review
applicable_version: 0.2.9-development
---

# WP06-A/B/C current-source revalidation R1

## Result

The existing A/B/C technical candidates were rechecked against the current
governing source without changing solver mechanics. Their listed nonlinear
source files are byte-for-byte unchanged from the source revision used by the
original candidate contracts (`03166e98a9a0b8cc7978c7ad2a370e441aefdc1e`),
and the current focused regression set passes.

| Item | Candidate weight | Revalidation | Boundary |
| --- | ---: | --- | --- |
| WP06-A — formulation/route contract | 1 | PASS_CANDIDATE | Source/formulation audit; no claim that arc-length equals Crisfield or Riks |
| WP06-B — state/rollback/restart | 1 | PASS_CANDIDATE_WITH_LIMITATIONS | Unit and checkpoint/restart regressions pass; no structural suffix or distributed restart claim |
| WP06-C — identities/radius/corrector | 2 | PASS_CANDIDATE | Algebraic/toy and policy tests only; no structural postbuckling claim |
| **A/B/C candidate** | **4/8** | **READY_FOR_OWNER_REVIEW** | Candidate points only; not an official award |

**Official WP06 remains 0/8** until explicit Owner acceptance. The project
ledger remains 66/100. No WP06-D or WP06-E structural campaign was started.

## Provenance

```text
BRANCH = codex/wp06-score-requalification
EXECUTION_SHA = 915d0d4e8a8df462d7928f77b96f4480f53fbae7
GOVERNING_BASE_SHA = 915d0d4e8a8df462d7928f77b96f4480f53fbae7
SOURCE_COMPARISON_BASE = 03166e98a9a0b8cc7978c7ad2a370e441aefdc1e
SOURCE_COMPARISON = PASS — listed arc-length/state/checkpoint implementation files unchanged
WORKTREE_SOURCE_CHANGES = NONE
```

The historical A/B/C contract JSON files are retained unchanged. Their
SHA-256 digests in this revalidation are recorded in
`qualification/0_2_9/wp06_abc_revalidation_r1.json`; the original contracts
remain identifiable as historical technical candidates rather than being
rewritten to pretend they were authored at the current SHA.

## Targeted verification

Command:

```text
python -m pytest -q --junitxml=qualification/0_2_9/wp06_abc_revalidation_r1/targeted-tests.xml tests/unit/test_wp06_ab_arc_length_contract.py tests/unit/test_wp06c_arc_length_predictor_corrector_identities.py tests/unit/test_wp01_d_continuation.py tests/unit/test_wp02_d_arc_length_restart.py tests/unit/test_wp02_d1_arc_length_material_state.py tests/unit/test_wp03_d_arc_radius_policy.py
```

Result: **118 passed, 0 failures, 0 errors**. The JUnit XML is retained as
machine-readable test output and hashed by the revalidation record. No full
repository suite was run.

## D/E remain separate gates

The historical WP06-D Phase-1 M2 failure remains immutable and fail-closed.
It cannot be converted to PASS by this A/B/C test result. Any new D execution
must first bind its contract and the exact arc-length execution policy to the
current source, preserve the historical R1 threshold/physics choices unless
the Owner explicitly revises them, use the frozen mean-crown observable, and
archive every accepted full displacement state for independent equilibrium
reconstruction. A new structural execution still requires explicit Owner
authorization. M3 remains gated on successful M1 and M2 production,
equilibrium, independent-reference, and replay checks.

```text
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
STRUCTURAL_SOLVES_RUN = NO
WP06_A_CANDIDATE_POINTS = 4/4
WP06_OFFICIAL_POINTS = 0/8
WP06_CANDIDATE_POINTS_AFTER_OWNER_REVIEW = up to 4/8
GLOBAL_OFFICIAL_TOTAL = 66/100
```
