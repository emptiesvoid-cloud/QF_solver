---
doc_id: DOC-029-WP15B-ROUTE-INSTRUMENTATION-PHASE1-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP15-B phase 1

## Status and bounded scope

This artifact records the first, non-heavy phase of WP15-B. The original
status was `WP15_B_PHASE1_PASS_CANDIDATE`; Owner Correction R1 is recorded
below as `OWNER_CORRECTION_R1`. The current status is
`WP15_B_PHASE1_PASS_CANDIDATE_WITH_OWNER_CORRECTION_R1`, pending Owner review
and integration. WP15-B remains 0/1, WP15 remains 0/2, and the validated total
remains 29/100.

The implementation is limited to:

* a backend-neutral text `ConsoleSink`;
* opt-in generic events on the public `linear_static` and `modal` routes;
* OFF/ON result-invariance fixtures;
* a synthetic `LegacyWP04Adapter` bridge test; and
* fan-out/failure-isolation tests.

No route is claimed qualified by the presence of telemetry. No heavy solve,
WP04-C2R6 campaign, WP05 structural campaign, overhead campaign, or full
test suite was run. The active WP04 nonlinear producer and its C2R6 behavior
are unchanged.

The machine-readable companion is
[qualification/0_2_9/wp15b_phase1_route_instrumentation.json](../../../qualification/0_2_9/wp15b_phase1_route_instrumentation.json).

## Console sink

`src/solveur/core/telemetry/console.py` implements a text-only,
backend-neutral sink with a caller-provided stream. The profiles are:

| Profile | Stable fields when available |
|---|---|
| `linear_static` | analysis, event, route, status, DOFs, elements, nnz, assembly time, backend, iterations, residual, solve time, RSS/private |
| `modal` | analysis, event, route, status, DOFs, requested modes, mode index, eigenvalue, frequency, eigen residual, iterations, backend, elapsed |
| `nonlinear` | analysis, event, route, status, step, iteration, load factor, residual, correction, alpha, backend, Krylov count, eta, solve time, RSS, elapsed |

Missing measurements render as `-`, or as `NA(REASON)` for the controlled
missing-value token. They are never rendered as zero.

Rate limiting is display-only. `every_n` and optional `min_interval_s` may
reduce high-frequency console lines, but canonical events remain delivered to
the JSONL and memory sinks. The lifecycle set
`ANALYSIS_START`, `ANALYSIS_END`, `ANALYSIS_FAILED`, `STEP_ACCEPTED`,
`STEP_REJECTED`, and `CHECKPOINT` always displays. Lifecycle display does not
alter event sequence or retention.

## Route instrumentation

The public `solve_model(..., telemetry=...)` argument is optional and is a
no-op when omitted or disabled. For the two Phase-1 routes, `AnalysisRouter`
normalizes the model analysis first, binds a route view to the actual
`model.analysis.type`, and owns the single `ANALYSIS_START` event. Caller
strings cannot make canonical events claim a different route; a mismatch is
retained in `telemetry_route_binding` metadata. Route-native solver
exceptions remain unchanged and the router emits best-effort
`ANALYSIS_FAILED` telemetry before re-raising the original exception.

The Phase-1 lifecycle is therefore exactly one start followed by either one
end or one failure. A preflight failure produces `ANALYSIS_START` followed by
`ANALYSIS_FAILED`, without `MESH_READY` or assembly events. The router passes
no generic Phase-1 telemetry view into non-instrumented routes, including
geometric/nonlinear routes; their legacy bridge remains external only.

### `linear_static`

The bounded route emits, when the corresponding phase is reached:

`ANALYSIS_START`, `MESH_READY`, `ASSEMBLY_START`, `ASSEMBLY_END`,
`LINEAR_SOLVE_START`, `LINEAR_SOLVE_END`, and `ANALYSIS_END`.

The events carry mesh/DOF counts, matrix shape and nnz, selected backend and
method, preconditioner where declared, iterations/residuals when supplied by
the backend, fallback information, and phase timings. Backward error is
explicitly `NOT_AVAILABLE` when this route/backend does not expose it. The
contact branch uses explicit `NOT_COMPUTABLE` residual tokens for metrics that
are not meaningful there; no contact formulation is changed.

### `modal`

The bounded route emits `ANALYSIS_START`, `MESH_READY`, assembly start/end,
one `MODAL_MODE_FOUND` per accepted positive mode, and `ANALYSIS_END`.
Each mode reports index, eigenvalue, frequency, and the solver diagnostic
residual. Eigensolver iterations are `NOT_AVAILABLE` when the current modal
backend does not expose them; no iteration count or residual is fabricated.

### Geometric nonlinear compatibility

The active geometric/nonlinear WP04 producer is not instrumented in this
phase, and the public router does not emit new generic events for that route.
Existing legacy payloads are passed through the external
`LegacyWP04Adapter` and demonstrated with `MemorySink`, `JsonlSink`, and
`ConsoleSink` for `ITERATION`, `STEP_ACCEPTED`, `STEP_FAILED`, `SOLVE_FAILED`,
and `SOLVE_COMPLETED`. This is a compatibility test, not active-path
qualification.

## Disabled path and result safety

`TelemetryEmitter(enabled=False)` returns before event construction,
serialization, sink fan-out, file access, and lazy metric-supplier
evaluation. The route fixtures compare telemetry OFF and ON mechanical
outputs for the same tiny TET4 models and require exact equality for the
deterministic displacement/eigenvalue arrays and route result fields.

Sink failures are isolated by `CompositeSink`: a broken console or JSONL
sink marks telemetry health `DEGRADED`, while sibling memory delivery and the
mechanical solve continue. The router's failure boundary preserves the
original solver exception. No telemetry failure can turn a route failure
into a successful result.

## Fan-out and JSONL

The tested topology is:

```text
TelemetryEmitter -> CompositeSink -> JsonlSink
                                  -> ConsoleSink
                                  -> MemorySink (test observer)
```

The WP15-A JSONL contracts remain in force: UTF-8 append mode, one valid JSON
object per line, immediate flush, `allow_nan=False`, fresh-session contiguous
per-analysis sequence validation, default fsync off, and boundary durability
only at checkpoint/terminal events. Console rate limiting never changes the
canonical JSONL event count.

## Overhead harness preparation

The future WP15-B overhead harness is prepared at
`scripts/benchmark_wp15b_overhead.py` but not executed. It will compare
repeated identical fixtures in `OFF`, `CONSOLE_ONLY`, `JSONL_ONLY`, and
`CONSOLE_PLUS_JSONL` modes, recording wall time, CPU time, peak RSS,
private/USS where available, event count, JSONL bytes, displayed console
events, and sink health. No numeric overhead threshold is frozen before that
measurement. The current boundary memory samples are deliberately labelled
as samples; a future qualification run may replace them with a continuous
sampler without changing the mode contract.

## Verification and governance

Targeted verification covers ConsoleSink rendering/rate limiting/lifecycle
visibility, route-bound provenance, exact success/failure lifecycle ownership,
linear and modal route event sequences, preflight failure behavior, the
non-instrumented route guard, OFF/ON invariance, disabled lazy suppliers, sink
failure isolation, JSONL+console fan-out, legacy WP04 adaptation, and
explicit missing values. WP15-A telemetry tests and the affected route tests
are run separately. Ruff, mypy, compileall, strict JSON validation, and the
document registry check are required.

Production infrastructure and the two bounded route call sites changed;
mechanics, formulations, convergence policy, linear numerical behavior,
modal numerical behavior, active WP04 behavior, and maturity did not change.

Formal point state:

* WP15-A = 0/1 pending integration/revalidation;
* WP15-B = 0/1; and
* WP15 = 0/2, validated total = 29/100.

## Owner Correction R1

R1 hardens only provenance and lifecycle ownership. It adds an immutable
route-bound telemetry view, prevents generic events on non-instrumented
routes, moves `ANALYSIS_START` ownership to the router for the two Phase-1
routes, and guarantees one terminal failure event at that boundary. It does
not alter mechanics, convergence policy, numerical algorithms, active WP04
behavior, or the overhead harness. Owner review remains required.

Nonlinear active-path integration and measured overhead qualification are
deferred until the independent Agent A campaign has completed and governance
permits the next phase.
