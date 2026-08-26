---
doc_id: DOC-NL-025-016
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 release-readiness template

## Candidate identity

| Field | Value |
|---|---|
| Candidate version | `0.2.5a0` |
| Candidate SHA | PENDING |
| Tree clean | PENDING |
| Evidence manifest digest | PENDING |
| Wheel digest | PENDING |
| sdist digest | PENDING |
| Owner decision | PENDING |

## Mandatory gate status

| Gate | Status | Evidence | Blocker/limit |
|---|---|---|---|
| 025-G00 | OPEN | | |
| 025-G01 | OPEN | | |
| 025-G02 | OPEN | | |
| 025-G03 | OPEN | | |
| 025-G04 | OPEN | | |
| 025-G05 | OPEN | | |
| 025-G06 | OPEN | | |
| 025-G08 | OPEN | | |
| 025-G09 | OPEN | | |
| 025-G10 | OPEN | | |
| 025-G11 | OPEN | | |
| 025-G12 | OPEN | | |

G07 is optional unless the Owner promotes friction into release scope.

## Final checks

- [ ] Version, changelog, README, metadata and qualification registry agree.
- [ ] No mandatory `OPEN`, `BLOCKED`, `draft`, pending signature or stale SHA.
- [ ] Complete test/coverage policy passes on candidate SHA.
- [ ] Engineering/V&V and external correlation evidence matches candidate SHA.
- [ ] Documentation builds from a clean checkout.
- [ ] Wheel and sdist build and pass metadata checks.
- [ ] Wheel installs into a clean environment and public API smoke passes.
- [ ] Optional dependencies remain optional and are tested where available.
- [ ] Skips/deselections match the approved inventory.
- [ ] Known limitations are visible in public documentation.
- [ ] No unsupported physical-validation or scale claim remains.
- [ ] Owner explicitly authorizes tag/release/publication in a separate action.

The `sha_consistency` step in `scripts/release_readiness_pipeline_025.py` is
fail-closed: it emits `FINAL_SHA`, `TREE_CLEAN` and `EVIDENCE_SHA_MATCH`, and
returns a failure when the candidate has no resolvable Git revision, contains
source changes, or its generated `docs/generated/docs_manifest.json` does not
identify that same revision through `source_sha`. Generated documentation and
the readiness artifact directory are outputs produced after checkout; they are
excluded from the source-tree cleanliness decision. This prevents a manifest
from having to contain the SHA of the commit that contains the manifest itself.
The check is evaluated only during candidate readiness; it does not alter the
development workflow or publish anything.

The `gate_check` step is also fail-closed. It parses every mandatory row rather
than looking only for the literal `OPEN` marker: missing, malformed, `BLOCKED`
or otherwise non-closed mandatory rows are reported as `OPEN_GATES` and cause a
failure. G07 may remain `NOT_IN_RELEASE_SCOPE` because it is optional by policy.

## Verdict

`NOT READY` until every mandatory row is closed. This template does not authorize
tagging, GitHub Release creation or PyPI publication.
