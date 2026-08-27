---
doc_id: DOC-NL-025-016
revision: 0.2
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
| Final release candidate SHA | PENDING (G11/G12) |
| Final release tree clean | PENDING (G11/G12) |
| Final release evidence manifest digest | PENDING (G12) |
| Qualified source SHA for G02 | `fec5380db3bcdba13799ce31f3ed042ac5d2557b` |
| G02 source tree clean | `true` |
| G02 Owner-evidence manifest | `qualification/reviews/qf_solver_0_2_5_g02_owner_evidence_manifest.json` |
| Wheel digest | PENDING |
| sdist digest | PENDING |
| Final release Owner decision | PENDING (G12); G02 is `APPROVED` |

## Mandatory gate status

| Gate | Status | Evidence | Blocker/limit |
|---|---|---|---|
| 025-G00 | OPEN | | |
| 025-G01 | PASS | `results/vnv_0_2_5/g01_latest/summary.json`, `g01_code_aster_latest/summary.json`, `0_2_5_j2_qualification_report.md` | Bounded J2 qualification only |
| 025-G02 | PASS | `results/vnv_0_2_5/g02_latest/summary.json`, `0_2_5_g02_owner_review.md`, Owner-evidence manifest | Elastic Total-Lagrangian TET4/HEX8, bounded pre-limit domain only |
| 025-G03 | OPEN | | |
| 025-G04 | OPEN | `results/vnv_0_2_5/g04_latest/summary.json`, `0_2_5_g04_owner_review.md`, `0_2_5_g04_external_branch_diagnostic.md` | External deck mismatch resolved; custom benchmark still lacks a published FEM reference and required four-level arc-length mesh study |
| 025-G05 | OPEN | | |
| 025-G06 | OPEN | | |
| 025-G07 | NOT_IN_RELEASE_SCOPE | optional friction policy | Owner promotion required before any release claim |
| 025-G08 | PASS | `results/vnv_0_2_5/g08_latest/summary.json` + manifest | Bounded performance characterization only |
| 025-G09 | PASS | `results/vnv_0_2_5/g09_latest/summary.json` + manifest | 22/22 failure cases; internal contract only |
| 025-G10 | OPEN | | |
| 025-G11 | OPEN | | |
| 025-G12 | OPEN | | |

G07 is optional unless the Owner promotes friction into release scope. G02 is
closed independently of the source-pack's pre-Owner `OPEN` decision: the
qualified numerical source SHA and the documentary Owner-evidence SHA are
intentionally distinct.

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
