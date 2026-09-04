---
doc_id: DOC-027-R0-RELEASE-001
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Historical 0.2.7a0 R0 release-readiness record

This page is a preserved pre-stable audit record. It is not the current public
release status; use the [active 0.2.7 verification summary](README.md) for the
current conclusion.

`R0_STATUS = PASS_WITH_LIMITATIONS`.

R0 starts from the clean F6 source commit
`5323a0996f214a3203f06b5bb468843b57c25270`. The release worktree initially
contained one unrelated modification to
`docs/verification/project_hygiene_architecture_audit_0_2_1.md`. It was
classified as `FOREIGN_CHANGE` and preserved in a targeted stash with commit
`a9e64d5e03ebadfcd1292ad3c5b04460761c10aa`; it is not part of the candidate.

The current candidate remains `0.2.7a0`, with no tag, GitHub release or PyPI
publication. The future tag/build source is the final local R0 closeout commit
reported with this record. The machine-readable record is
[`qualification/0_2_7/r0_release_readiness.json`](../../../qualification/0_2_7/r0_release_readiness.json).

## Gate result

| Area | Result | Evidence |
| --- | --- | --- |
| Source integrity | PASS | Clean release tree after foreign-change isolation; no numerical or baseline change |
| Qualification integrity | PASS_WITH_LIMITATIONS | F1-F6 closed; active accounting remains `96/100` |
| Audit closure | PASS_WITH_LIMITATIONS | Three unchanged F4/F6 failures remain outside the bounded public matrix |
| Test readiness | PASS | `138 passed, 2 skipped` targeted closeout battery; static checks pass |
| Packaging | PASS_WITH_LIMITATIONS | Rebuilt wheel/sdist pass distribution and `twine` checks; clean-install evidence is inherited from F5 |
| Documentation | PASS_WITH_LIMITATIONS | Candidate, boundaries and known limitations are explicit |
| Publication traceability | OWNER_ACTION_REQUIRED | Generic readiness script correctly remains `NOT_READY` before tag and manual history review |

The public source/archive audits pass. The generic readiness script still
reports `git_history_audit` and `version_tag` as failed checks. This is expected
before publication: the history prefilter requires a manual owner review of a
legitimate public controlled-proof path and a historical non-GitHub-no-reply
author identity, while R0 intentionally does not create the tag. No secret or
local credential was found in the flagged proof contents.

The 5M Silver evidence remains applicable to the recorded structured TET4
PETSc/MPI workload. The C3 10M evidence remains bounded and is not a universal
capacity or scaling claim. WEDGE6 static remains `EXPERIMENTAL`; WEDGE6 modal
retains only its separate bounded scope. CalculiX remains `NOT_COMPARABLE` for
the bounded WEDGE6 contract. Optional environments, macOS/Python-version
coverage, and the three experimental/stale nonlinear full-suite failures remain
known limitations.

R0 does not change numerical source, active baselines, maturity, historical
evidence or release version. It does not push, tag, publish, or create a GitHub
release. The owner may decide whether to proceed after the explicit manual
history and license review required by the publication tooling.

`RECOMMENDATION = RELEASE_WITH_KNOWN_LIMITATIONS`.
