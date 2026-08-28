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
| Final release candidate SHA | `8047fb63c420609b510beaa1e30aa3ab31d9ad87` (qualified source) |
| Final release source tree clean | `true` under the generated-evidence provenance contract |
| Final release evidence SHA | Recorded by `docs/generated/docs_manifest.json` as `source.revision` |
| Final release evidence manifest | `docs/generated/docs_manifest.json`, generated from the evidence SHA above |
| Qualified source SHA for G02 | `fec5380db3bcdba13799ce31f3ed042ac5d2557b` |
| G02 source tree clean | `true` |
| G02 Owner-evidence manifest | `qualification/reviews/qf_solver_0_2_5_g02_owner_evidence_manifest.json` |
| Wheel/sdist digests | Recorded in the final packaging run; recompute when artifacts are archived |
| Final release Owner decision | PENDING (G12); G02 is `APPROVED` |

## Mandatory gate status

| Gate | Status | Evidence | Blocker/limit |
|---|---|---|---|
| 025-G00 | OPEN | candidate source `8047fb63c420609b510beaa1e30aa3ab31d9ad87`; architecture audit and SHA consistency pass under the provenance contract | The historical 0.2.4 baseline approval remains a separate Owner decision; no closure is inferred from the corrective replay |
| 025-G01 | PASS | `results/vnv_0_2_5/g01_latest/summary.json`, `g01_code_aster_latest/summary.json`, `0_2_5_j2_qualification_report.md` | Bounded J2 qualification only |
| 025-G02 | PASS | `results/vnv_0_2_5/g02_latest/summary.json`, `0_2_5_g02_owner_review.md`, Owner-evidence manifest | Elastic Total-Lagrangian TET4/HEX8, bounded pre-limit domain only |
| 025-G03 | PASS | `results/vnv_0_2_5/g03_euler_final/summary.json`, `results/vnv_0_2_5/g03_final/summary.json`, `0_2_5_g03_owner_review.md`, Owner-evidence manifest | Bounded first tangent-instability scope: TET4 Euler and Code_Aster probe; high-order external buckling and post-buckling excluded |
| 025-G04 | OPEN | `results/vnv_0_2_5/g04_latest/summary.json`, `0_2_5_g04_owner_review.md`, `0_2_5_g04_external_branch_diagnostic.md` | External deck mismatch resolved; custom benchmark still lacks a published FEM reference and required four-level arc-length mesh study |
| 025-G05 | PASS | `results/vnv_0_2_5/g05_latest/evidence_manifest.json`, `0_2_5_lot5a_contact_implementation_report.md` | Bounded node/patch-to-triangulated-surface frictionless contact; no general surface-to-surface, friction or unrestricted large sliding |
| 025-G06 | OPEN | `results/vnv_0_2_5/g06_latest/summary.json`, `report.md`, `evidence_manifest.json`, `coupled_histories.json`, `g06_diagnostic/summary.json`, `g06_geometry_contact_mesh/summary.json`, `g06_j2_geometry_code_aster/final_comparison.json`, `g06_j2_geometry_code_aster/green_lagrange/green_comparison.json`, `g06_geometry_contact_code_aster/summary_linear.json`, `g06_geometry_contact_code_aster/tet4_green_lagrange/comparison.json` | Internal tangent FD and geometry+contact mesh sub-proofs are archived on source SHA `8df4b4ac32e9416e89fe342871aab6e75cdd245c`; Green-Lagrange Code_Aster J2 replay still has TET10 non-convergence and measured convention deviations; the TET4 Green-Lagrange contact comparison is bounded but has a mapped reaction deviation up to 76.7% and is not a qualifying external PASS |
| 025-G07 | NOT_IN_RELEASE_SCOPE | optional friction policy | Owner promotion required before any release claim |
| 025-G08 | PASS | `results/vnv_0_2_5/g08_latest/summary.json` + manifest | Bounded performance characterization only |
| 025-G09 | PASS | `results/vnv_0_2_5/g09_latest/summary.json` + manifest | 22/22 failure cases; internal contract only |
| 025-G10 | BLOCKED | `0_2_5_external_correlation_matrix.md`, G04/G06 evidence and gate rows | Blocked by mandatory external cells for still-open G04 and G06; CalculiX SHOULD evidence is non-blocking and is not promoted to MUST |
| 025-G11 | PASS | final controlled replay on `8047fb63c420609b510beaa1e30aa3ab31d9ad87` | `1719 passed, 183 skipped`; coverage `88.37 %`; external V&V `64 checks PASS`; docs, package build, Twine and wheel smoke pass |
| 025-G12 | OPEN | readiness evidence and gate matrix | Aggregate readiness is not closed while G00, G04, G06 and G10 remain open/blocked; Owner release decision is still required |

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

- [ ] Version, changelog, README, metadata and qualification registry agree.
- [ ] No mandatory `OPEN`, `BLOCKED`, `draft`, pending signature or stale SHA.
- [x] Complete test/coverage policy passes on candidate SHA.
- [x] Engineering/V&V and external correlation evidence matches candidate SHA.
- [x] Documentation builds from a clean source checkout.
- [x] Wheel and sdist build and pass metadata checks.
- [x] Wheel installs into a clean target and public API/CLI smoke passes.
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

`NOT READY` until aggregate gate closure. The corrective sprint does not
authorize tagging, GitHub Release creation or PyPI publication.
