---
doc_id: DOC-029-WP08-CONTROLLED-001
revision: 0.1
status: ready_for_owner_review
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP08 — controlled reconstruction and revalidation review

## Decision summary

**Final status:** `READY_FOR_OWNER_REVIEW`

This branch reconstructs the WP08 preparation/evidence inputs from the
governing baseline without merging the divergent WP08 history. The only
production change is the explicitly authorized contact-friction correction in
`src/solveur/contact/support.py::_friction_update`. WP08-D remains
`PREPARATION_ONLY`; no structural WP08 solve, H4 run, or formal point award was
performed.

Formal WP08 points remain `0/8`. The governing branch was not modified.

## Provenance and base

| Item | Value |
| --- | --- |
| Governing base | `7b93e71bab06a0e58108bd2479cd46808d533b67` |
| Expected WP08 source | `502dd1f7b1f19f37e1929ae9a6107ee1a4f9e514` |
| Actual WP08 source | `7712af3f0755260cd2bc588e2c45ea7da241b60f` |
| Merge base | `2c52bf8196a7d47d14ce1784290580160de26590` |
| Controlled branch | `0.2.9-wp08-controlled-integration` |
| Controlled port commit | `604d3a4a6d533c3b12642c0d00b0fa75e9cd033f` |

The BASE→ACTUAL history contains 133 changed paths (12 added, 100 deleted,
21 modified). That divergent history was not imported. The EXPECTED→ACTUAL
delta was restricted to the WP08-D registry, documentation, contract, helper
script and test paths. The exact selected-path list and classifications are
stored in
`qualification/0_2_9/wp08_controlled_integration/wp08_provenance_report.json`.

The controlled port started from the exact governing SHA. The pre-existing
dirty worktree was audited before staging and contained only the explicitly
listed WP08 inputs.

## Production mechanics change

The change is intentionally classified as:
`PRODUCTION_CONTACT_FRICTION_MECHANICS_CHANGE`.

The patch is limited to `_friction_update` and implements:

- finite-state guards for `trial_norm` and the Coulomb limit;
- explicit handling of `trial_norm == 0.0` on the existing slip branch;
- prevention of the `0/0` NaN projection;
- explicit `NumericalConvergenceError(..., reason=NAN_DETECTED)` for invalid
  non-finite states.

No Newton or convergence policy, linear backend, fallback, contact search,
active set, penalty, load, boundary condition, observable, rollback policy or
qualification threshold was changed. No other production mechanics file was
modified.

## Controlled provenance rebinding

WP08-A/B/C historical source values remain available in their JSON records as
explicit `historical_source_sha` fields. Their active `source_sha` identifies
the controlled port commit, so no old branch is silently presented as the
current branch. WP08-D is similarly rebound as a controlled preparation
contract while retaining its historical source SHA.

The governing C2R6 policy digest is the existing documented value:
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`, sourced
from the governing WP07 integration record. The controlled WP08-D contract
canonical JSON digest is:
`d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`.
The historical contract blob digest is preserved as
`f1af8d2b8135e423926ab11ee0eb50c7527a29afc16d9534cf8f1f014f54b5c9`.

The contract payload is unchanged outside provenance/revalidation metadata;
thresholds remain unchanged. WP08-D continues to forbid structural execution
without explicit Phase-1 authorization.

## Targeted validation

The targeted WP08/contact validation command covered WP08-B, WP08-C, WP08-D,
the WP08 contract, frictional contact unit/V&V tests, and the direct contact
regression set:

`46 passed in 6.97s`

Additional results:

- Ruff: `PASS`.
- Targeted mypy for new WP08 files: `PASS` with imports skipped.
- Direct mypy of `support.py`: one inherited diagnostic at line 447, present
  on the governing baseline and not introduced by the authorized patch; it was
  not changed in this task.
- Targeted `compileall`: `PASS`.
- JSON and document-registry validation: `PASS`.
- `git diff --check`: `PASS`.

The single type annotation added to the WP08-C test is test-only and removes a
new diagnostic without changing numerical behavior.

## WP08 status

| Area | Controlled status |
| --- | --- |
| WP08-A | Technical candidate revalidated; no formal points |
| WP08-B | Candidate with limitations revalidated; no formal points |
| WP08-C | Candidate with limitations revalidated; no formal points |
| WP08-D | Preparation-only contract revalidated; no structural result |
| Formal WP08 | `0/8` |
| H4 | `NOT_STARTED` |

No qualification record claims a WP08 structural result. No maturity change is
made. WP06 is untouched.

## Controlled stop point

No merge to `0.2.9-unified-nonlinear` was performed, no H4 was launched, and
no push to the governing branch was performed. The controlled branch is ready
for Owner review of the exact mechanics patch, provenance rebinding, inherited
mypy diagnostic, and the authorization required before any WP08-D structural
execution.
