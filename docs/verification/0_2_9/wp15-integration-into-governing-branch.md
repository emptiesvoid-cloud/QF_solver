---
doc_id: DOC-029-WP15-INTEGRATION-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.9-development
---

# QF Solver 0.2.9 — WP15 governing-branch integration audit

## Decision

The Owner-frozen WP15 telemetry candidate was integrated by explicit
non-fast-forward merge into `0.2.9-unified-nonlinear`. The protected WP04
mechanics paths remain byte-identical to the WP04-F audit baseline. Targeted
telemetry, routing, API, state, termination, and WP04-F governance checks pass.

The formal recommendation is **WP15-A PASS**, **WP15-B PASS**, and **WP15
CLOSED — 2/2**, taking the validated total from 41/100 to **43/100**. This is
bounded Phase-1 instrumentation: only `linear_static` and `modal` emit generic
route telemetry. Geometric nonlinear routes are deliberately uninstrumented.

## Provenance and merge

| Item | Value |
| --- | --- |
| Governing pre-merge SHA | `67375559c1f4aba651bb081d475bd9c867fe4232` |
| Child head | `f93bdb5395be513fe09cfc9b52f0b1d2cb9f32db` |
| Merge base | `2c52bf8196a7d47d14ce1784290580160de26590` |
| Merge commit | `a76afd2310e28fc2eb3578200e788bf5ca8f0149` |
| Conflict | `docs/document_registry.json` only |

The registry conflict was resolved manually: the governing WP04-F record and
all three valid WP15 records are retained. No whole-file “ours” or “theirs”
resolution was used.

## Protected WP04 scope

The following WP04-F audited production paths were checked against audit SHA
`70e1bf953c8e6f37b8070e78ca97e58b21499291` and have no merge diff:

- `src/solveur/core/analyses/geometric_nonlinear.py`
- `src/solveur/core/assembly/geometric.py`
- `src/solveur/core/assembly/nonlinear.py`
- `src/solveur/elements/solid/tet4_total_lagrangian.py`
- `src/solveur/elements/solid/hex8_total_lagrangian_batch.py`
- `src/solveur/elements/solid/common.py`

The only merged source surfaces are the generic telemetry package plus
`api/public.py`, `core/router.py`, `core/solvers/static.py`, and
`core/analyses/modal.py`. The C2R6 floor-aware termination, MINRES+Jacobi
policy, canonical line search, `NonlinearStateTransaction`, and
`UnifiedContinuationController` are unchanged.

## Integrated bounded behavior

- WP15-A: schema-validated events, bound emitters, sequencing, health,
  failure-isolated Memory/JSONL/Console/Composite sinks, disabled fast path,
  and `LegacyWP04Adapter`.
- WP15-B Phase 1: router-bound `linear_static` and `modal` lifecycle events;
  one `ANALYSIS_START` and one terminal `ANALYSIS_END` or `ANALYSIS_FAILED`;
  preflight failures do not produce mesh/assembly events; uninstrumented
  routes emit no generic Phase-1 events.
- Optional `solve_model(..., telemetry=...)` is an additive public API
  parameter. Telemetry omission remains a numerical no-op.

## Validation

The targeted WP15 suites report **47 passed**. The WP04 C2R6/state/geometric/
public API set reports **41 passed** after explicitly updating the public API
contract for the additive optional telemetry parameter. The WP04-F evidence
regression reports **5 passed** after it was narrowed from a global post-audit
source freeze to the six actual mechanics paths protected by its source digest.

Ruff and compileall pass. Targeted mypy has **zero new diagnostics**: its 38
remaining diagnostics are the same pre-existing broadly typed `modal.py`
diagnostics measured at the governing baseline. JSON validation covers the
registry and 112 qualification records; the controlled-document registry test
passes; MkDocs strict passes with its existing unlisted-page/non-doc-JSON-link
notices. No structural solve, H4, PETSc run, or full repository suite is part
of this integration.

## Deferred telemetry debt

The known C2R6 `SOLVE_COMPLETED.newton_iterations` aggregate undercount remains
**DEFERRED**. WP15 Phase 1 covers generic static/modal telemetry while C2R6
uses the established nonlinear JSONL observer. A change to that legacy
nonlinear aggregate has no WP15 integration test coverage and is not needed to
preserve route correctness, so it was not changed opportunistically.

## Next step

The governing branch may proceed only with the next separately Owner-frozen
child branch. This integration does not authorize merging `0.2.9-wp06-prep`.
