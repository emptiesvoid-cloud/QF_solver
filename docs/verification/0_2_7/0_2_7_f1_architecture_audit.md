---
doc_id: DOC-027-F1-ARCH-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 F1 Architecture Audit

## Decision

`F1_STATUS = PASS_WITH_LIMITATIONS`

The audit found no P0 or P1 architecture defect at `995531841c5203144889aaebd7fcfd906cc0622b`. The release architecture is usable for the next audit, with P2/P3 debt explicitly retained for F2. This report does not change numerical code, capability maturity, or historical evidence.

## Scope and baseline

F1 covers package boundaries, public API surfaces, solver and element routing, optional MPI/PETSc execution, error and state contracts, legacy entry points, and verification ownership. It does not perform a mass refactor, numerical change, maturity promotion, historical evidence rewrite, full regression, or heavy benchmark.

The source tree contains 448 Python modules and 95,698 source lines. There are 315 script files, 468 test files, and 204 verification modules. The largest source file is 697 lines against the existing 700-line architecture guard.

## Architecture map

| Layer | Main ownership | Result |
| --- | --- | --- |
| User facade | `src/qf_solver`, `src/solveur/api`, `src/solveur/cli` | PASS_WITH_LIMITATIONS |
| Orchestration | `src/solveur/core/router.py`, `src/solveur/execution` | PASS |
| Solver routes | `src/solveur/core/analyses`, `src/solveur/core/solvers`, `src/solveur/core/nonlinear` | PASS_WITH_LIMITATIONS |
| FEM elements | `src/solveur/elements`, `src/solveur/compatibility` | PASS_WITH_LIMITATIONS |
| Large linear algebra | `src/solveur/large` | PASS_WITH_LIMITATIONS |
| IO and provenance | `src/solveur/io` | PASS_WITH_LIMITATIONS |
| Verification | `src/solveur/verification` | PASS_WITH_LIMITATIONS |

`core.router` validates the model before dispatch and uses deferred imports for optional or heavier routes. The large route requires explicit PETSc selection and reports unavailable dependencies as structured infrastructure errors. Existing MPI guardrails synchronize rank failures and global readiness before later collectives.

## Public API

`qf_solver` is the documented facade with 70 exports and `solveur.api` exposes 69. The root `solveur` namespace has a smaller lazy compatibility surface with 45 exports. The three console entry points are `qf-solver`, `solveur-ef`, and `mitc4-solver`. Runtime import probes and packaging API tests pass. The two facades are intentionally different; no missing documented export was demonstrated.

Legacy launcher scripts remain active compatibility surfaces and are covered by packaging/tests. Their repository-path bootstrap is tooling debt, not a package-runtime defect.

## Dependency findings

The static graph contains 1,798 internal edges and two module-level strongly connected components. Both are deferred execution cycles with local imports, not import-time failures:

1. `solveur.api.public` and `solveur.verification.mitc4_campaign`, at `src/solveur/api/public.py:57` and `src/solveur/verification/mitc4_campaign.py:601-605`.
2. `solveur.verification.nonlinear_failure_runner` and `solveur.verification.nonlinear_failure_campaign`, at `src/solveur/verification/nonlinear_failure_runner.py:8-15` and `src/solveur/verification/nonlinear_failure_campaign.py:639-642`.

There are 15 bidirectional package pairs, principally around `core`, `verification`, `elements`, `mesh`, and infrastructure services. Existing import restrictions pass, and the runtime import probe passes. The coupling is therefore P2 maintainability debt rather than a release blocker.

## Finding register

| ID | Priority | Finding | F1 decision |
| --- | --- | --- | --- |
| F1-P2-001 | P2 | Deferred verification orchestration cycles | Defer to F2 |
| F1-P2-002 | P2 | Bidirectional package coupling | Incremental boundary work later |
| F1-P2-003 | P2 | Verification concentration and runner duplication | Defer to F2 |
| F1-P2-004 | P2 | Legacy maturity map duplicates registry v2 | Keep conservative behavior; resolve semantics in F2 |
| F1-P2-005 | P2 | Launcher `sys.path` bootstrap | Defer launcher cleanup |
| F1-P2-006 | P2 | Broad modal diagnostic exception | Defer narrower diagnostics |
| F1-P2-007 | P2 | Snapshot fields have current-like names | Preserve snapshots; clarify in F2 |
| F1-P3-001 | P3 | Root export ordering is not a contract | Defer unless required |

Counts: `P0 = 0`, `P1 = 0`, `P2 = 7`, `P3 = 1`. No P0/P1 fix is required.

## Route, element, and maturity boundary

The router preflight is before solver dispatch. Unsupported routes fail closed, while experimental and not-qualified routes are reported explicitly. The large PETSc path does not silently fall back when explicitly requested; SciPy/matrix-free legacy routes remain separately available.

The combination registry remains the source of maturity for exact combinations. WEDGE6 static remains `EXPERIMENTAL` and WEDGE6 modal remains `QUALIFIED_BOUNDED` in registry v2. The legacy generic `model_maturity` layer still defaults WEDGE6 to `research`. That result is conservative and was not “fixed” by promoting or rewriting anything. It is the highest-priority P2 item for F2 because two maturity authorities should eventually be reconciled by an explicit semantics decision.

No finite-kinematic J2, mixed mesh, HEX8 next-generation formulation, WEDGE15, PYRAMID5, GPU, or other deferred capability was promoted.

## MPI/PETSc, error, and state contracts

The optional large route has explicit backend selection, structured missing-dependency behavior, and readiness/failure synchronization. PETSc matrix diagnostics are best-effort and do not silently turn an unavailable measurement into a pass. Checkpoint writes are atomic and schema/model validated; corruption is rejected.

Error handling is fail-closed for unsupported combinations, backend failures, convergence failures, and invalid checkpoints. A broad catch in modal eigenpair refinement is diagnostic-only: it records an invalid correction and later residual validation prevents a valid pass. It remains P2 because preserving the original exception more directly would improve diagnosis.

No module-level `global` statements were found. Caches and checkpoint state are deterministic in the current process model, but concurrent execution and cache invalidation semantics are not a claimed contract.

## Validation

The audit reused the following targeted evidence:

- architecture and route/preflight/large execution checks: `50 passed`;
- public/release/safety checks: `52 passed, 35 skipped`;
- packaging and public facade checks: `11 passed`;
- registry, descriptor, and WEDGE6 checks: `55 passed`;
- runtime source import probe: PASS;
- F1 architecture invariants: PASS;
- Ruff, compileall, and `git diff --check`: PASS.

No full regression or heavy benchmark was run for F1. No numerical source was changed, no requalification is required, and no historical evidence was modified.

## Release decision

F1 is `PASS_WITH_LIMITATIONS`. The architecture is release-safe for F2 because there are no P0/P1 findings, public and optional runtime boundaries are explicit, and fail-closed behavior is covered. The deferred debt must remain visible: registry-v2/legacy maturity reconciliation, verification coupling, diagnostic exception narrowing, snapshot naming clarity, and concurrency/cache semantics.

`READY_FOR_F2 = YES`

The next audit is F2. No F2 implementation was started here.
