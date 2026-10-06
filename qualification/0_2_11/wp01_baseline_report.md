# QF Solver 0.2.11 — WP01 baseline record

## Baseline identity and preservation

- Approved development baseline: `c37179dae53604126aa6aa0d834770dfa4d2db37`.
- Fresh remote `main` at start: same SHA; no drift was found.
- Published baseline: annotated `v0.2.10` peels to `e535ff63464ddd7d76c2898df25470350b5154f1`; it remains immutable.
- Working branch: `codex/v0.2.11-wp01-baseline`, created from exactly the approved SHA.
- All WP01 additions are confined to `qualification/0_2_11/`. No solver, test, version, release artifact, prior decision, historical result, or tag has been modified.

## Capability and evidence baseline

The capability matrix covers **24** analysis, element, material, contact, backend,
API/IO, package, documentation, and V&V capabilities. Each row identifies
implementation, public entry points, tests, V&V cases, controlling records,
current runtime/record maturity, limitations, mandatory regression observables,
and requalification triggers. Record-level qualification is never inferred from
an implementation label or a neighboring family.

The evidence inventory has **29** source/decision/artifact entries:

| Classification | Count | Interpretation |
|---|---:|---|
| `AVAILABLE_AND_REPRODUCIBLE` | 2 | Framework tests selected in the normal test matrix; not the underlying historical calculation itself. |
| `AVAILABLE_HISTORICAL_ONLY` | 23 | Decision, contract, report, manifest, or immutable 0.2.10 package evidence; replay is record- and environment-dependent. |
| `AVAILABLE_LOCAL_ONLY` | 1 | WP08 R1.13 raw numerical sets were local/untracked at their execution; absent from this clean baseline checkout. |
| `RECONSTRUCTED` | 1 | WP04-D reproduced manifest/material; it is not the original missing capture. |
| `OPTIONAL_DEPENDENCY` | 1 | Code_Aster executable/raw gallery; not guaranteed on standard CI. |
| `MISSING` | 1 | WP06-D raw checkpoint payloads referenced by the tracked replay record are not in the baseline checkout. |

Every tracked evidence path listed in the inventory was checked for existence,
SHA-256, and latest modifying commit. All passed. A missing raw payload is not
counted as reproducible merely because a manifest or replay JSON exists.

## Mandatory 0.2.11 non-regression campaign

The matrix defines **71 named non-regression observables** across 24 capability
rows. `wp01_regression_campaign.json` pins the authoritative commands and
separates fast impact tests, PR-required checks, release-candidate evidence, and
optional evidence. The PR gate is the repository's actual quality workflow:
Ubuntu/Windows × Python 3.10/3.13, Ruff, the current progressive mypy gate,
unit/integration plus its existing coverage thresholds, P0 coverage,
compileall,
quick verification, and the Documentation tests workflow. Release candidates
add the existing WP14 recovered-evidence, full engineering, documentation
evidence, and frozen selected-package checks.

The standard PR matrix intentionally deselects `benchmark`, `large`, and
`evidence` markers. `tests/conftest.py` also explicitly skips archive-backed
cases when their controlled corpus is not mounted and skips two Gmsh mesh
modules when Gmsh is unavailable. Such results remain `SKIPPED`/deselected;
they are not PASS. Required release-candidate jobs run the controlled evidence
profiles with their declared inputs.

For floating-point results, comparisons use the existing case's frozen
reference, metrics, and tolerance. Modal clusters use subspace/MAC-style
comparison rather than eigenvector sign equality. Numerical outputs are not
required to be bitwise identical unless an existing record explicitly requires
byte identity. WP01 records observables and their authorities; it does not
recompute or retune historical thresholds.

## Historical open items (inventory only)

`wp01_historical_open_items.md` records the relevant retained failures,
holds, bounded/experimental scopes, rejected combinations, optional/missing
evidence, and prospective recommendations. In particular:

- G03 remains `FAIL_PRESERVED`; selected package/docs scans do not clear the
  whole-repository archive.
- WP14 remains `HOLD` with zero validated points; recovered targeted evidence
  does not close it.
- WP06 remains 4/8; WP06-D is experimental, 0/2 formal points, with no limit
  point or formal postbuckling claim; E/F remain blocked.
- WP08's accepted contact scopes remain bounded. R1.13 is diagnostic evidence
  with recorded mesh sensitivity and missing local-only raw bytes, not formal
  requalification; historical M4 failure remains.
- The MITC4 large modal failure, discrete-Newmark owner rejection, historical
  solver/convergence failures, WP04-D reconstructed evidence, and bounded
  PETSc/MPI/Code_Aster claims remain unchanged.
- Prospective low numerical-risk V&V identity/expected-failure semantics are
  recommendations for later WP03/WP04 planning only. No remediation is started
  by WP01.

## Baseline execution

| Workflow | Run | SHA | State |
|---|---:|---|---|
| Documentation tests | [run `37217513498`](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/37217513498) | `c37179dae53604126aa6aa0d834770dfa4d2db37` | `SUCCESS`: docs-generation tests **37 passed, 2 skipped**; strict MkDocs build passed; packaging integration tests **13 passed**. The two skips are the optional controlled V&V corpus checks (`optional controlled V&V evidence corpus is not installed`), not PASS. |
| Quality and verification | [run `37217513570`](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/37217513570) | `c37179dae53604126aa6aa0d834770dfa4d2db37` | `SUCCESS`, all seven jobs passed. |

Quality run results (all on the exact baseline SHA):

- Ubuntu Python 3.10 and 3.13; Windows Python 3.10 and 3.13: each **3316 passed, 22 skipped, 107 deselected**. Branch coverage was **85.47%** on Ubuntu and **85.49%** on Windows against the unchanged 80% gate. Ruff, progressive mypy, P0 coverage, compileall, and quick verification passed in each matrix job.
- WP14 recovered-evidence targeted job: **9 passed** against its verified archive. This result is scoped to those checks only; global WP14 remains `HOLD_NOT_PROMOTED`.
- Documentation evidence job: controlled meshed profile **23 passed, 1 skipped, 3959 deselected**; Markdown/PDF checks **63 passed, 6 skipped**. Job conclusion `SUCCESS`.
- Full engineering campaign: **3672 passed, 36 skipped, 206 deselected**; `Full MITC4 benchmarks` reported `GLOBAL STATUS: PASS`; engineering profile reported `GLOBAL STATUS: PASS` and `VERIFY-ALL PASS: profile=engineering`.

### Skip, deselection, and failure classification

- No failed tests or failed jobs: `NEW_FAILURES = none`.
- Standard-matrix skips (**22/job**) and engineering-profile skips (**36**) are retained as `SKIPPED`, not PASS. The authoritative default logs expose aggregate counts, not a complete per-node skip list; repository guards identify optional dependency/host-capability and external-evidence cases. No per-test breakdown is claimed where the workflow did not emit one.
- Standard-matrix deselections (**107/job**) and engineering deselections (**206**) are the test-selection effects of the unchanged `not benchmark and not large and not evidence` expression. They are outside the selected pytest invocation, not successes.
- Documentation workflow’s two skips are identified as unavailable archive-backed controlled V&V corpus checks. The documentation evidence job separately reports one skipped controlled-profile item and six skipped Markdown/PDF items; these remain `SKIPPED` and do not raise evidence maturity.
- Non-blocking infrastructure annotations: GitHub Actions’ Node.js 20→24 migration and the announced future `ubuntu-latest` image migration. No test or quality gate failed because of these warnings.
- Optional Code_Aster runtime/raw gallery, local-only WP08 raw payloads, and missing WP06-D original checkpoint payloads remain unavailable as specified in the evidence inventory. WP14 targeted PASS does not promote WP14; `G03 = FAIL_PRESERVED` and `WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO` remain unchanged.

## WP01 exit checklist

| Criterion | State |
|---|---|
| Approved baseline refs verified | `YES` |
| Capability matrix complete and referenced paths checked | `YES` |
| Evidence inventory and hashes/source commits checked | `YES`, with explicit missing/local/optional classifications above |
| Mandatory campaign defined | `YES` |
| Baseline campaign terminally executed | `YES`; Quality `37217513570` and Documentation `37217513498` are terminal `SUCCESS` on the exact baseline SHA |
| Failures and skips classified | `YES`; no failures; skips/deselections separated and classified with aggregate-log limitation disclosed |
| Requalification triggers defined | `YES` |
| Historical maturity/status unchanged | `YES` (WP01 is additive only) |
| v0.2.10 tag/artifacts/source unchanged | `YES` |

## WP01 closure decision

All baseline and workflow gates are green on the approved source SHA. Historical
open items, absent/local-only evidence, optional dependencies, skips, and
previous failures remain explicitly visible; no old result or maturity has
been altered. The result is `PASS_WITH_RECORDED_LIMITATIONS` for WP01 only.
