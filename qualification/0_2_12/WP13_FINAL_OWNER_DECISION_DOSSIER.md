# WP13 final Owner decision dossier

**Current engineering verdict:** `WP13_PARTIAL_OR_BLOCKED`

**CI matrix under the approved lightweight policy:** PASS, run #41328516423

**G03 whole-repository gate:** FAIL_PRESERVED pending history disposition

**Installed-package smoke tests v7:** `WP13_V7_INSTALLED_PACKAGE_SMOKES_PASS`; six execution and numerical-oracle PASS results, with `qualification_status=NOT_CLAIMED`

**Publication, tag, merge, release branch update:** not authorized and not performed

This dossier records only decisions that require Owner action. Supporting evidence and the precise technical limits are linked below.

## Current v7 smoke execution status

The v7 execution was authorized by `OWNER-WP13-V7-SIX-SMOKES-HEAD-D0A3-01` (decision SHA-256 `a692c5d65e18f806b655eb4cd1070c62627b976227f9e40a0fc574fb5ee1ee1c`). The HEAD-bound manifest SHA-256 is `4a9398df42b52d1e088d640a6896b6e00873f479f77cf8fdec01310809ffa9cb`; main preflight `01795a37ef09d67a4bd653fd34aca98d0aadee1eb23cec3ba826c63f0b20cd46`; synthetic report `7790f26725a4b9f56bcb6862de88952c279384b05e521d4b77b9908f8256187e`. All six pairs passed execution and numerical oracles. See [`WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md`](WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md) for per-attempt metrics and proof hashes. No qualification, release, tag or merge decision follows from these results.

The decision and candidate discussion below preserve the earlier v6/pre-execution checkpoint as history; they are superseded for current smoke status by the v7 report above. G03 remains `FAIL_PRESERVED` independently.

## Historical v6 smoke proposal — superseded

The three approved case definitions and frozen analytical checks are in [`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md). The candidate is the v6 package source `2865587a44f9e461a0b4e4286c912c17e4f04be5`, not a claim about a newly rebuilt package. A complete comparison against the v6 package and documentation selections found 585/585 package paths and 773/773 selected-document paths with identical Git blobs at current HEAD `3ced76d841402fc53e64545ebc37acb8361fa369`; the archive-only attributes and internal reports do not change the candidate artifacts.

Verified bindings:

| Input | SHA-256 / identity |
|---|---|
| Build contract | `QF-0212-WP13-SELECTED-CANDIDATE-20261031-06`; `f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9` |
| Controller | `scripts/wp13_package_smoke.py`; `16df6eba0f902c332cace9e9a5624d1b8b59c3e051bfcc4063782123cc9a7f2f` |
| Manifest | `wp13_p0_package_smoke_manifest_20261031_v1.json`; `dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b` |
| Persisted no-FEM preflight | `PASS_NO_FEM_PREFLIGHT`; `f2fb9a13986ab3d9ec95d91f645da973657ab02ae4f6ee261cfb5a50511ab610` |
| Synthetic no-FEM route report | `PASS_NO_FEM`; `2eac9b8eeb1635695f907ea4db977f0b223ac991667d786554d8ca8ed3addf6c` |
| Synthetic ledger | `5cb540211b529db1fbef1e55a5a303d8cd623e3695a8791cfbdecbd106c2639c`; two records, both `fem_executed=false` |
| Wheel | `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a` |
| Run-2 raw sdist | `15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5` |

The three installed input hashes were rechecked in both environments and match the manifest byte-for-byte. The real attempt ledger does not exist. Static inspection confirms that the controller requires a separate Owner decision bound to the manifest, preflight and synthetic report, fixes the six wheel-then-sdist pairs, allows one attempt per pair, serial execution, 30-second timeout, 1 MiB stdout/stderr caps, sampled 512 MiB RSS limit, no retry, and stop-on-first-failure. A successful smoke can report only execution and numerical-oracle status; the manifest prohibits a qualification claim.

### Ready-to-record Owner decision

To authorize exactly these six attempts, the Owner may provide the following decision record after reviewing the linked case dossier. The `approved_pairs` array must remain exact. Any changed identity requires a new review; this approval does not authorize any other calculation, qualification campaign or release action.

```json
{
  "schema": "qf-wp13-package-smoke-owner-decision-v1",
  "decision_id": "<owner-assigned-id>",
  "approval_status": "APPROVED",
  "authorization_scope": "SIX_INSTALLED_ARTIFACT_SMOKES_ONLY",
  "qualification_claim": "NOT_CLAIMED",
  "manifest_sha256": "dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b",
  "preflight_sha256": "f2fb9a13986ab3d9ec95d91f645da973657ab02ae4f6ee261cfb5a50511ab610",
  "synthetic_preflight_sha256": "2eac9b8eeb1635695f907ea4db977f0b223ac991667d786554d8ca8ed3addf6c",
  "approved_pairs": [
    {"artifact": "wheel", "case": "STATIC-01"},
    {"artifact": "wheel", "case": "MODAL-01"},
    {"artifact": "wheel", "case": "DYNAMIC-01"},
    {"artifact": "sdist", "case": "STATIC-01"},
    {"artifact": "sdist", "case": "MODAL-01"},
    {"artifact": "sdist", "case": "DYNAMIC-01"}
  ]
}
```

At that historical v6 checkpoint, no reservation or smoke execution was permitted. That statement does not describe the completed v7 execution above. The CI matrix authorization remains a separate gate.

## Decision 2 — G03 public-history disposition

The prospective archive rules now omit root `AGENTS.md` and the unreferenced `docs/generated/results/*.json` machine outputs while preserving the tracked files, scientific content, manifests, ledgers and history. The generated Markdown fragments used by the public documentation remain in the archive. This fixes the current archive path exposure only.

The history path prefilter still returns `WARNING` across 2,587 reachable commits with 1,429 findings: 1,346 commit-author identity flags, 59 historical `AGENTS.md` path events, and 24 other sensitive-path events. Those findings include historical WP12 result files and external-oracle outputs that must not be rewritten under the present mandate. `export-ignore` cannot remove historical paths or author metadata from GitHub's public Git history. G03 therefore remains `FAIL_PRESERVED` even if the prospective archive scan passes.

No history rewrite is authorized here. The choices for a later, separately scoped Owner review are:

1. Keep the present public history and retain G03 as FAIL_PRESERVED; do not describe full-repository or GitHub-generated source archives as cleared.
2. Commission a separate public-history plan that reviews author metadata and historical internal/evidence paths, preserves the existing history as a controlled internal archive, and proposes a clean public repository/history. Creating or replacing public refs requires a new explicit Owner authorization and is outside this WP13 task.

Neither choice changes WP12 findings, scientific maturity, the selected v6 package result, or the CI gate.

## Independent legal review

[`WP13_THIRD_PARTY_LICENSE_AUDIT.md`](WP13_THIRD_PARTY_LICENSE_AUDIT.md) records the technical metadata and license-file review. It identifies permissive default runtime terms, bundled native-component notices, and GPL/LGPL optional extras. The file `THIRD_PARTY_LICENSES.md` is a starting inventory rather than an exhaustive versioned schedule. Independent legal review remains `NOT_ACQUIRED`; no technical audit in this dossier substitutes for that review.
