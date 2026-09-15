---
doc_id: DOC-029-WP08E-001
revision: 0.1
status: candidate_pending_owner_review
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08-E — bounded closure, replay and accepted-state restart

## Scope

This record implements and verifies the bounded WP08-E closure machinery for
the already-qualified frictional-contact route. It adds signed persistence of
an accepted friction state and fail-closed validation before a resumed solve.
It does not claim mid-Newton restart, updated-search friction, finite sliding,
or a general nonlinear checkpoint capability.

No M2 or M3 structural solve was relaunched by this task. The previously
authorized M2/M3 production, independent-reference and replay artifacts were
consumed read-only and their manifests were re-hashed.

## Provenance

```text
AUTHORIZED_BASE_SHA = 7b93e71bab06a0e58108bd2479cd46808d533b67
REMEDIATION_SHA = 794de436c13364c16aa85b2ae2c9e7bb09957829
EXECUTION_SHA = 794de436c13364c16aa85b2ae2c9e7bb09957829
EVIDENCE_COMMIT_SHA = PENDING_LOCAL_EVIDENCE_COMMIT
FINAL_SHA = PENDING_LOCAL_EVIDENCE_COMMIT
REMOTE_HEAD = NOT_PUSHED
BRANCH = 0.2.9-wp08d-m1-phase1
```

`REMEDIATION_SHA` identifies the local implementation commit that was tested;
`EXECUTION_SHA` is the exact source revision used for the WP08-E run. The
evidence commit and final SHA are intentionally resolved only after the
generated artifacts are committed. No remote head is asserted because no
push was requested.

## WP08-E evidence

The controlled seven-step local history was solved once without interruption.
A second run was stopped after accepted step 4, using an injected test
interruption. The accepted state was written atomically, then loaded into a
fresh solver and continued through steps 5–7.

| Check | Result |
| --- | --- |
| accepted checkpoint after step 4 | `PASS` |
| resumed steps | `3` |
| resumed terminal state vs uninterrupted state | `PASS` |
| maximum displacement absolute delta | `0.0` |
| cumulative dissipation delta | `0.0` |
| M2 replay evidence revalidated | `PASS` |
| M3 replay evidence revalidated | `PASS` |
| manifests and raw hashes | `PASS` |

Negative controls all fail closed:

- negative or non-finite friction coefficient: `PASS_FAIL_CLOSED`;
- frictional updated-search request: `PASS_FAIL_CLOSED`;
- missing restart checkpoint: `PASS_FAIL_CLOSED`;
- tampered physical-model checkpoint signature: `PASS_FAIL_CLOSED`.

The machine-readable result is
`qualification/0_2_9/wp08e_closure/wp08e_closure_final.json`.

## A→D closure audit

The existing bounded evidence was checked without rewriting historical
results or awarding points automatically:

| Component | Candidate result | Candidate points |
| --- | --- | ---: |
| WP08-A — formulation/input/state contract | bounded candidate with limitations | `1/1` |
| WP08-B — identities, state transactions and rollback | candidate with limitations | `2/2` |
| WP08-C — tangent and local dissipation V&V | candidate with limitations | `2/2` |
| WP08-D — M1/M2/M3 structural/reference/replay evidence | candidate with limitations | `2/2` |
| WP08-E — replay, restart and fail-closed closure | candidate | `1/1` |
| **WP08 total** | **candidate pending Owner review** | **`8/8`** |

WP08-D checks include M1, M2 and M3 production evidence, independent
references, replay comparisons, contract/policy digest consistency, and all
available manifests. The independent references are verified as not calling
production contact routines.

## Governance

The accepted-state checkpoint persistence is a production-scope change, but
it is limited to the new WP08-E restart contract and validation. No frozen
threshold, solver parameter, backend, fallback policy, load, mesh or contact
law was changed. The original M2/M3 evidence remains immutable evidence for
the source SHAs under which it was executed.

```text
PRODUCTION_MECHANICS_CHANGED = YES, WP08-E checkpoint persistence/validation only
THRESHOLDS_CHANGED = NO
SOLVER_PARAMETERS_CHANGED = NO
FALLBACK_CHANGED = NO
FULL_TEST_SUITE_RUN = NO
STRUCTURAL_SOLVES_RUN_BY_CLOSURE = NO
OFFICIAL_WP08_POINTS_BEFORE_OWNER_REVIEW = 0/8
CANDIDATE_WP08_POINTS = 8/8
FINAL_STATUS = PASS_CANDIDATE_OWNER_REVIEW_REQUIRED
NEXT_STEP = Owner review and explicit point attribution; do not self-merge
```

## Validation

The local-source targeted validation completed as follows:

```text
55 targeted tests passed
Ruff = PASS
mypy = PASS, 4 source files
compileall = PASS
JSON validation = PASS
git diff --check = PASS
```
