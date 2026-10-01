---
doc_id: DOC-029-WP08-AUTHORIZED-MERGE-001
revision: 0.1
status: merged_locally_pending_structural_requalification
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08 — authorized local merge report

## Result

`FINAL_STATUS = MERGED_LOCALLY_PENDING_PUSH_AND_WP08D_STRUCTURAL_QUALIFICATION`

The Owner explicitly authorized the contact-friction mechanics change. The
controlled WP08 branch was merged locally, without pushing to `origin`.

No H4 or WP08-D structural qualification was run. WP08 remains at `0/8`
formal points.

## Merge identity

| Field | Value |
| --- | --- |
| Governing base | `7b93e71bab06a0e58108bd2479cd46808d533b67` |
| Controlled source | `94ce29e8fd5348eff4db3752183a50e0a7da0673` |
| Owner decision commit | `b874f06dc8371f191032d63d93e94c9e014d0ad9` |
| Local merge commit | `37d22719bbbb11d8af012cf75245224cd97a5184` |
| Merge branch | `0.2.9-wp08-authorized-merge` |

The merge commit has exactly the governing base and Owner-decision commit as
parents. No additional controlled-branch commits existed after the Owner
decision commit.

## Authorized production change

`OWNER_AUTHORIZES_CONTACT_MECHANICS_CHANGE = YES`

The only production path changed relative to the governing base is:

`src/solveur/contact/support.py::_friction_update`

The authorized scope is limited to finite-state guards, explicit
`trial_norm == 0.0` handling on the existing slip branch, prevention of
`0/0` NaN propagation, and typed `NumericalConvergenceError` reporting.

No thresholds, solver parameters, fallback policy, Newton policy, loads,
boundary conditions, observables, rollback semantics or additional mechanics
files changed. WP06 was not touched.

## Provenance and validation

- Contract digest: `d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`.
- Governing policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`.
- Provenance rebound: `YES`.
- Targeted WP08 tests: `46 passed in 9.00s`.
- Frictionless regression: `19 passed in 2.01s`.
- Ruff: `PASS`.
- Mypy for new WP08 scope: `PASS`.
- The inherited `support.py:447` diagnostic remains unchanged from the
  governing base and is explicitly retained.
- Compileall: `PASS`.
- JSON validation: `PASS`.
- Git diff check: `PASS`.
- Full suite: `NO`.

## WP08 state after merge

| Area | Status |
| --- | --- |
| WP08-A | `PASS_TECHNICAL_CANDIDATE_REVALIDATED` |
| WP08-B | `PASS_CANDIDATE_WITH_LIMITATIONS_REVALIDATED` |
| WP08-C | `PASS_CANDIDATE_WITH_LIMITATIONS_REVALIDATED` |
| WP08-D | `PREPARATION_ONLY` |
| Formal points | `0/8` |
| H4 | `NOT_STARTED` |

The next authorized activity is a separate WP08-D structural qualification
decision. This merge does not qualify WP08-D and does not award points.

## Local finalization

The governing local ref may be advanced by a fast-forward from
`7b93e71...` to the post-merge report commit. No remote push, branch deletion,
or further merge is authorized in this step.
