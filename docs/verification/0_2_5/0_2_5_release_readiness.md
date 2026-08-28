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
| Qualified numerical source SHA | `8047fb63c420609b510beaa1e30aa3ab31d9ad87` |
| Qualified source tree clean | `true` under the generated-evidence provenance contract |
| Owner evidence SHA | Recorded by `docs/generated/docs_manifest.json` as `source.revision` after the documentary commit |
| Owner evidence manifest | `docs/generated/docs_manifest.json`, generated from the Owner-evidence revision above |
| Qualified source SHA for G02 | `fec5380db3bcdba13799ce31f3ed042ac5d2557b` |
| G02 source tree clean | `true` |
| G02 Owner-evidence manifest | `qualification/reviews/qf_solver_0_2_5_g02_owner_evidence_manifest.json` |
| Wheel/sdist digests | Recorded in the final packaging run; recompute when artifacts are archived |
| Final release Owner decision | `APPROVED` for the explicitly narrowed qualified scope; publication remains a separate Owner action |

## Owner scope decision

`OWNER_SCOPE_REVISION = APPROVED` and `SCOPE_CHANGE = YES` are recorded in the
controlled Owner decision `0_2_5_owner_scope_revision.md`. The original plan
made G04 and G06 MUST; this record preserves that history and explicitly
excludes their unqualified claims from the 0.2.5a0 release scope. No test,
tolerance or historical result was lowered, so `CONTRACT_LOWERED = NO`.

G04 remains `EXPERIMENTAL / NOT_QUALIFIED` and G06 remains
`CODE_COMPLETE / EXPERIMENTAL / QUALIFICATION_DEFERRED`. Their evidence is
not converted to PASS. G07 remains outside the release scope.

## Mandatory gate status

| Gate | Status | Evidence | Blocker/limit |
|---|---|---|---|
| 025-G00 | PASS | exact 0.2.4 replay on `e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745`; Owner decision `ACCEPTED_HISTORICAL_BASELINE_LIMITATION` | `1440 passed, 1 failed, 32 skipped, 187 deselected`; the single failure is limited to two historical RQ-G08 revisions and has no demonstrated numerical impact |
| 025-G01 | PASS | `results/vnv_0_2_5/g01_latest/summary.json`, `g01_code_aster_latest/summary.json`, `0_2_5_j2_qualification_report.md` | Bounded J2 qualification only |
| 025-G02 | PASS | `results/vnv_0_2_5/g02_latest/summary.json`, `0_2_5_g02_owner_review.md`, Owner-evidence manifest | Elastic Total-Lagrangian TET4/HEX8, bounded pre-limit domain only |
| 025-G03 | PASS | `results/vnv_0_2_5/g03_euler_final/summary.json`, `results/vnv_0_2_5/g03_final/summary.json`, `0_2_5_g03_owner_review.md`, Owner-evidence manifest | Bounded first tangent-instability scope: TET4 Euler and Code_Aster probe; high-order external buckling and post-buckling excluded |
| 025-G04 | NOT_IN_RELEASE_SCOPE | `results/vnv_0_2_5/g04_latest/summary.json`, `0_2_5_g04_owner_review.md`, `0_2_5_g04_external_branch_diagnostic.md` | `EXPERIMENTAL / NOT_QUALIFIED`; published compatible reference and final four-level closure remain future work |
| 025-G05 | PASS | `results/vnv_0_2_5/g05_latest/evidence_manifest.json`, `0_2_5_lot5a_contact_implementation_report.md` | Bounded node/patch-to-triangulated-surface frictionless contact; no general surface-to-surface, friction or unrestricted large sliding |
| 025-G06 | NOT_IN_RELEASE_SCOPE | `results/vnv_0_2_5/g06_latest/summary.json`, `report.md`, `evidence_manifest.json`, `coupled_histories.json`, `g06_diagnostic/summary.json`, `g06_geometry_contact_mesh/summary.json`, `g06_j2_geometry_code_aster/final_comparison.json`, `g06_j2_geometry_code_aster/green_lagrange/green_comparison.json`, `g06_geometry_contact_code_aster/summary_linear.json`, `g06_geometry_contact_code_aster/tet4_green_lagrange/comparison.json` | `CODE_COMPLETE / EXPERIMENTAL / QUALIFICATION_DEFERRED`; finite-kinematic J2 and coupled external correlation remain unqualified, including the 76.7% mapped-reaction deviation |
| 025-G07 | NOT_IN_RELEASE_SCOPE | optional friction policy | Owner promotion required before any release claim |
| 025-G08 | PASS | `results/vnv_0_2_5/g08_latest/summary.json` + manifest | Bounded performance characterization only |
| 025-G09 | PASS | `results/vnv_0_2_5/g09_latest/summary.json` + manifest | 22/22 failure cases; internal contract only |
| 025-G10 | PASS | `0_2_5_external_correlation_matrix.md`, G01/G02/G03/G05 evidence and final Owner scope decision | Evaluated only on the remaining qualified MUST cells; G04/G06 external rows are explicitly excluded, and CalculiX SHOULD remains non-blocking |
| 025-G11 | PASS | final controlled replay on `8047fb63c420609b510beaa1e30aa3ab31d9ad87` | `1719 passed, 183 skipped`; coverage `88.37 %`; external V&V `64 checks PASS`; docs, package build, Twine and wheel smoke pass |
| 025-G12 | PASS | this readiness record, gate matrix, Owner scope decision, final-SHA manifests and G11 replay | Aggregate readiness is closed for the approved bounded scope; tag, GitHub Release and PyPI publication remain separately Owner-controlled |

G07 is optional unless the Owner promotes friction into release scope. G02 is
closed independently of the source-pack's pre-Owner `OPEN` decision: the
qualified numerical source SHA and the documentary Owner-evidence SHA are
intentionally distinct.

The final replay was executed with the candidate checkout explicitly first on
`PYTHONPATH`; this was required because the machine also contains a neighboring
`QF_solver_public` checkout. The replay reached tests, coverage, external V&V,
documentation, provenance, package build, Twine and wheel smoke. The complete
technical replay is qualified on source SHA
`8047fb63c420609b510beaa1e30aa3ab31d9ad87`. The documentary evidence revision
is recorded by `docs/generated/docs_manifest.json`; it does not change
numerical behavior. The generated manifest records its exact `source_sha` and
`source.dirty=false`; generated outputs are excluded from source-tree
cleanliness by the documented provenance contract.

### Corrective sprint result

The architecture blocker was resolved by splitting the evidence builder into
focused orchestration, study and publication modules. The entry point now has
147 lines and all source files satisfy the 700-line rule.

The buckling blocker was resolved without changing the physical buckling
contract: indefinite shift-invert now tries deterministic strictly interior
bracket-derived shifts, records attempted shifts and retains an explicit
diagnostic fallback. Exact-singular, near-eigenvalue, multiple-mode and
near-zero-mode cases are covered by focused tests; the G03 targeted suite
remains green.

## Final checks

- [x] Version, changelog, README, metadata and qualification registry agree.
- [x] No mandatory `OPEN`, `BLOCKED`, `draft`, pending signature or stale SHA; G04/G06 are explicitly Owner-excluded from the final qualified scope.
- [x] Complete test/coverage policy passes on candidate SHA.
- [x] Engineering/V&V and external correlation evidence matches candidate SHA.
- [x] Documentation builds from a clean source checkout.
- [x] Wheel and sdist build and pass metadata checks.
- [x] Wheel installs into a clean target and public API/CLI smoke passes.
- [ ] Optional dependencies remain optional and are tested where available.
- [x] Skips/deselections match the approved inventory.
- [x] Known limitations are visible in public documentation.
- [x] No unsupported physical-validation or scale claim remains.
- [ ] Owner explicitly authorizes tag/release/publication in a separate action.

The `sha_consistency` step in `scripts/release_readiness_pipeline_025.py` is
fail-closed: it emits `FINAL_SHA`, `TREE_CLEAN` and `EVIDENCE_SHA_MATCH`, and
returns a failure when the candidate has no resolvable Git revision, contains
source changes, or its generated `docs/generated/docs_manifest.json` does not
identify the qualified source through `source_sha`. Generated documentation
and the readiness artifact directory are outputs produced after checkout and
are excluded from the source-tree cleanliness decision. A manifest archived by
a later release commit may therefore identify an ancestor SHA, but only when
every intervening path is explicitly documentation/governance-only; any change
under `src`, `examples` or qualification data fails the check. This prevents a
manifest from having to contain the SHA of the commit that contains the
manifest itself without allowing numerical changes to hide behind it. The
check is evaluated only during candidate readiness; it does not alter the
development workflow or publish anything.

The `gate_check` step is also fail-closed. It parses every mandatory row rather
than looking only for the literal `OPEN` marker: missing, malformed, `BLOCKED`
or otherwise non-closed mandatory rows are reported as `OPEN_GATES` and cause a
failure. A mandatory `NOT_IN_RELEASE_SCOPE` row is accepted only when the gate
matrix contains the explicit `OWNER_SCOPE_REVISION = APPROVED` and
`SCOPE_CHANGE = YES` markers. This makes the G04/G06 exclusion auditable rather
than implicit.

## Verdict

`READY FOR OWNER-CONTROLLED RELEASE` for the explicitly narrowed 0.2.5a0
qualified scope. This record does not authorize tagging, GitHub Release
creation or PyPI publication.
