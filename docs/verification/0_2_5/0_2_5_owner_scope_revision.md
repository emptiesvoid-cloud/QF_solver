---
doc_id: DOC-NL-025-035
revision: 1.0
status: controlled_owner_decision
applicable_version: 0.2.5a0
reviewer: "Owner"
approver: "Owner"
---

# QF Solver 0.2.5a0 — Owner scope revision and final governance decision

Decision date: `2026-08-28`

This record is a governance decision for the release scope. It does not
rewrite historical evidence, change a numerical result or replace an open
functional gate with a PASS.

## Decision identity

| Field | Decision / value |
|---|---|
| Qualified numerical source SHA | `8047fb63c420609b510beaa1e30aa3ab31d9ad87` |
| Owner evidence SHA | `docs/generated/docs_manifest.json:source.revision` after the documentary commit; kept external to this file to avoid self-reference |
| Worktree contract | generated evidence is excluded from source-tree cleanliness; source changes are committed separately |
| Owner baseline decision | `ACCEPTED_HISTORICAL_BASELINE_LIMITATION` |
| Owner scope decision | `OWNER_SCOPE_REVISION = APPROVED` |
| Scope change | `SCOPE_CHANGE = YES` |
| Silent contract lowering | `CONTRACT_LOWERED = NO` |

`CONTRACT_LOWERED = NO` means that no test, tolerance or historical result was
relaxed. The release scope is explicitly narrowed and approved; the original
0.2.5 plan remains preserved in the requirements and gate history.

## G00 — historical 0.2.4 baseline

The isolated replay used the exact historical release source
`e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745`, with no 0.2.5 checkout or package
on the import path. It reported:

| Environment item | Recorded value |
|---|---|
| QF Solver version | `0.2.4a0` |
| Python | `3.12.3` |
| Replay command | `python qf_solver.py verify-all --profile engineering` |
| Result | `1440 passed, 1 failed, 32 skipped, 187 deselected` |
| Isolated worktree | clean |
| Numerical defect demonstrated | no |
| Failure | `test_release_readiness_remains_dry_run_and_reports_worktree_state` |

The single failure is a historical governance limitation. The readiness
calculation found two historical revisions of the RQ-G08 reference artifact:

```text
qualification/vnv/external/rqg08_j2_common_024/reference/summary.json
  821816f69ea14b88a7c58162f70e08f4edb8d45
  0ee6dbfe3d90920154bc6170901cc6eaec8a1fac
```

The failure does not demonstrate a solver regression and the 0.2.4 SHA is not
rewritten. G00 is therefore recorded as `PASS_WITH_HISTORICAL_LIMITATION` in
this Owner decision and as gate status `PASS` with the limitation retained in
the public record. The 0.2.5 qualified source is not claimed to reproduce the
historical baseline without this limitation.

## Final qualified release scope

The following claims are eligible for the 0.2.5a0 aggregate release scope,
within the exact bounded envelopes already documented and tested:

| Gate | Qualified claim |
|---|---|
| G01 | J2 small-strain qualification on the documented four-family bounded scope, including the recorded internal V&V and 64-check Code_Aster correlation |
| G02 | bounded elastic Total-Lagrangian finite-deformation scope for TET4/HEX8 in the recorded pre-limit positive-`det(F)` domain |
| G03 | bounded sparse first tangent-instability/buckling scope with the recorded Euler and external TET4 evidence |
| G05 | bounded frictionless node/patch-to-triangulated-surface contact contract with the documented external normal-contact correlation |
| G08 | reproducible bounded performance characterization; no general HPC or million-DOF nonlinear claim |
| G09 | structured internal failure-mode and rollback contract; no promotion of unrelated functional paths |
| G11 | full regression/package evidence recorded on qualified source SHA `8047fb63c420609b510beaa1e30aa3ab31d9ad87` |

## Explicitly excluded from qualified claims

| Gate | Final status | Claim classification | Reason retained |
|---|---|---|---|
| G04 | `NOT_IN_RELEASE_SCOPE` | `EXPERIMENTAL / NOT_QUALIFIED` | arc-length FEM branch evidence lacks the required independent compatible reference and final four-level closure under the original plan |
| G06 | `NOT_IN_RELEASE_SCOPE` | `CODE_COMPLETE / EXPERIMENTAL / QUALIFICATION_DEFERRED` | finite-kinematic J2 remains research and the required coupled Code_Aster correlations are incomplete/non-comparable |
| G07 | `NOT_IN_RELEASE_SCOPE` | `NOT_IN_RELEASE_SCOPE` | friction is not part of this alpha |

G04 and G06 are not PASS. Their former MUST requirements remain visible in
the historical requirements and V&V matrices, but are dispositioned as
excluded from the final qualified release scope by this explicit Owner
revision. No claim of external validation, general finite-strain J2, general
arc-length or triple coupling is made.

## G10 and G12 decision

`G10 = PASS` is evaluated only against the remaining MUST cells of the final
approved scope. The evidence is the archived Code_Aster J2 campaign, bounded
Total-Lagrangian and buckling correlations, bounded frictionless-contact
histories, and the corresponding source/digest records. CalculiX remains a
SHOULD/supporting comparison and is never promoted to a release-blocking MUST.
The G04 and G06 external cells are explicitly
`EXCLUDED_FROM_QUALIFIED_RELEASE_SCOPE`, not PASS.

`G12 = PASS` records aggregate readiness for this revised scope because G00 is
accepted with limitation, G10 is evaluated on the final scope, G11 is PASS on
the qualified source SHA, and the existing package, Twine, install-smoke,
documentation and coverage evidence are already recorded. This decision does
not authorize a tag, Git push, GitHub Release or PyPI upload; those remain a
separate Owner-controlled action.

## Signature

**Owner decision:** `APPROVED — OWNER_SCOPE_REVISION`

**G00:** `PASS_WITH_HISTORICAL_LIMITATION`

**G04:** `EXCLUDED_FROM_QUALIFIED_RELEASE_SCOPE`

**G06:** `EXCLUDED_FROM_QUALIFIED_RELEASE_SCOPE / QUALIFICATION_DEFERRED`

**G10:** `PASS` on the final qualified scope

**G12:** `PASS` for aggregate readiness on the final qualified scope

**Owner signature:** `APPROVED` — repository Owner, `2026-08-28`
