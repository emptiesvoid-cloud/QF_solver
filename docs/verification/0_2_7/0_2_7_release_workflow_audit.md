---
doc_id: DOC-027-015
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Release Workflow Audit

## WP01 result

WP01 is `PASS` for the release-truth foundation. The 0.2.6 qualification
snapshot, tagged source snapshot and current 0.2.7 development source snapshot
are separate identifiers. Documentation and evidence commits may be newer than
the source snapshot they describe.

| Role | Value | Meaning |
| --- | --- | --- |
| Qualification snapshot for 0.2.6 | `93561c2c0ae1c173deb81e47c3fa3852643275cb` | Historical G15 qualification source |
| Release source snapshot for 0.2.6 | `e839373b6aef291a93292186d7553ba5cd12af55` | Actual `v0.2.6a0` tag target |
| Current 0.2.7 development source | `e99289aca40011ca0424944099e2d2093cf21a65` | Source snapshot at WP01 start |

At the audit date, `v0.2.6a0` was present on Git, the GitHub release page was
published, and `qf-solver==0.2.6a0` was present on PyPI. The historical G15
record remains unchanged and is classified as historical evidence; it is not a
current publication-state record.

## Publication workflow

`.github/workflows/publish-pypi.yml` accepts a published GitHub Release or an
explicitly confirmed manual dispatch. The build now validates the tag for both
paths and requires a `refs/tags/` ref whose `v`-prefixed name matches the
package version. The publish job repeats the tagged-ref guard, so confirming a
manual dispatch from a branch cannot publish an untagged source tree.

The workflow currently uses the `PYPI_API_TOKEN` GitHub secret. The token is
not recorded in this repository. Trusted Publishing/OIDC is a future
release-engineering option and is not partially configured here. A repeated
upload of an existing version remains an explicit PyPI failure; the workflow
does not silently skip it.

## Artifact and digest policy

| Classification | Rule |
| --- | --- |
| `SOURCE` | Tracked implementation/configuration used by an execution. |
| `CONTROLLED_PROOF` | Versioned evidence with source SHA, policy, result and digest. |
| `GENERATED_VIEW` | Reader-facing material derived from controlled records. |
| `HISTORICAL_EVIDENCE` | Immutable prior-release evidence retained for provenance. |
| `BUILD_ARTIFACT` | Wheel, sdist or local build output; not a proof source. |

Text digests use canonical UTF-8 bytes with LF newlines and SHA-256. Binary
artifacts are hashed byte-for-byte without text normalization.

The machine-readable records are
[`release_truth.json`](../../../qualification/0_2_7/release_truth.json) and
[`release_workflow_audit.json`](../../../qualification/0_2_7/release_workflow_audit.json).
