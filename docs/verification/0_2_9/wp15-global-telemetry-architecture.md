---
doc_id: DOC-029-WP15-TELEMETRY-ARCHITECTURE-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP15 global telemetry architecture

## Status and scope

This document is a preparation artifact for WP15-A. It audits the telemetry
available at baseline 2c52bf8196a7d47d14ce1784290580160de26590 and freezes a
prospective architecture for Owner review. No production instrumentation,
numerical campaign, mechanics change, or solver-behaviour change is included.
WP15 remains 0/2 and the validated total remains 29/100.

The machine-readable companion is
[qualification/0_2_9/wp15_telemetry_architecture.json](../../../qualification/0_2_9/wp15_telemetry_architecture.json).

## 1. Existing inventory

| Module | Function/class and data | Caller/output | Execution/API | Classification |
|---|---|---|---|---|
| src/solveur/core/nonlinear/telemetry.py | NonlinearTelemetryObserver, JsonlNonlinearTelemetry, emit_telemetry, process_memory_bytes, telemetry_event; nonlinear mappings, RSS and USS/private samples | Nonlinear iteration/driver and WP04 C2 runners; append JSONL or in-process mapping | Synchronous callback; JSONL is opened append-only and flushed per event; opt-in internal callback | WRAP |
| src/solveur/core/nonlinear/driver.py | ITERATION, STEP_ACCEPTED, STEP_FAILED, SOLVE_FAILED, SOLVE_COMPLETED; residual/correction, line-search alpha, linear diagnostics, timing and memory | UnifiedNewtonEngine via solve_full_newton; observer and result diagnostics | Synchronous internal observer; WP04-shaped event keys | WRAP |
| src/solveur/large/telemetry.py | AssemblyTelemetry phase/checkpoint/rank markers, rates, ETA and RSS; RankPhaseTelemetry | PETSc large assembly runners; per-rank JSONL | Synchronous append/flush, rank-aware; WP04 large-run specific | WP04_SPECIFIC_KEEP |
| src/solveur/large/memory.py | Current/peak process RSS and source metadata | Large benchmark telemetry | Synchronous process query; no USS/private on all platforms | REUSE_AS_IS |
| src/solveur/verification/observatory.py | Canonical evidence records, finite checks, digests, timings, resources, rank aggregation and comparison | Verification runners and manifests; canonical JSON/result evidence | Synchronous evidence builder/validator, not a live event sink | GENERALIZE |
| src/solveur/core/solvers/linear.py | LinearSolveInfo, backend/method, callbacks, iteration count and residual history | Linear system solve paths | Internal solver diagnostics; direct and iterative backends | GENERALIZE |
| src/solveur/core/nonlinear/linear_solver.py | Matrix shape/nnz, backend, Krylov count, raw residual, backward error, fallback, time and memory | Newton linear adapter | Internal adapter result | GENERALIZE |
| src/solveur/execution/contract.py | ExecutionSession lifecycle, structured diagnostics and checkpoint/recovery state | Execution orchestration | State-machine contract; no universal event sink | WRAP |
| Checkpoint, audit, manifest modules | State digests, finite-state validation, mesh/equilibrium summaries, source/runtime provenance | Restart, failure evidence and reports | Structured files and result records | REUSE_AS_IS / WRAP |

Existing JSONL and result files are evidence of current WP04 behaviour, not
proof that all analysis routes have live, common telemetry.

## 2. WP04 monitoring trace

The current nonlinear path is:

run_wp04_linear_solver_r2.py::run_stage_c
→ JsonlNonlinearTelemetry and an in-memory observer
→ _newton_dead_load
→ solve_full_newton
→ UnifiedNewtonEngine
→ NonlinearLinearSolverAdapter
→ LinearSystemSolver
→ observer callback and JSONL
→ result/status JSON.

The Newton driver already reports step, iteration, residual, correction,
line-search alpha, matrix shape/nnz, linear backend/method, Krylov iterations,
linear residual, backward-error eta, fallback, assembly/linear/iteration time,
RSS and private/USS samples. Failure and terminal events are emitted before a
known numerical exception is re-raised. The geometric adaptive helper does not
currently forward the observer in every branch; this is a migration gap, not a
reason to alter the helper in preparation.

The independent large-run path is:

run_lu2_wp04_bronze.py
→ AssemblyTelemetry and RankPhaseTelemetry
→ PetscTET4Assembler
→ per-rank/aggregate JSONL
→ benchmark aggregation
→ result JSON and manifest.

Reusable pieces are the callback shape, immediate JSONL flush, finite/canonical
evidence validation, source/config/result digests, linear solve diagnostics,
checkpoint state and memory-source metadata. Tight coupling consists of legacy
event names/casing, absent common sequence/schema fields, no generic route
producers, and WP04-specific rank/assembly payloads. emit_telemetry currently
drops observer exceptions, so future sinks need explicit health accounting.
The Newton driver also samples process memory around events even when no
observer is installed; this is an overhead gap to measure before generalizing.

## 3. Proposed architecture

The target dependency direction is:

SOLVER / ANALYSIS → TELEMETRY EVENTS → OBSERVER/SINK INTERFACE → console,
JSONL, or a future UI/consumer.

Numerical code emits a structured event and does not know which sink consumes
it. A sink may be absent. Route-native Python exceptions remain route-native;
the common envelope classifies observable behaviour without imposing one
exception hierarchy.

### Common event envelope

Mandatory fields:

| Field | Meaning |
|---|---|
| schema_version | Integer event-schema version |
| event_type | Controlled lifecycle/event identifier |
| analysis_id | Stable run identifier |
| analysis_type and route | Analysis family and concrete execution route |
| sequence_number | Strictly increasing per analysis stream |
| elapsed_time_s | Monotonic elapsed time from analysis start |
| status | Event status such as STARTED, RUNNING, ACCEPTED, REJECTED, FAILED, COMPLETED |
| metrics | JSON object of typed measurements; absent metrics are null with a reason |
| metadata | Provenance, rank, mesh, backend and compatibility metadata |

timestamp is optional wall-clock provenance and is never used for ordering.
Conditional fields include step, iteration, load_factor, physical_time,
solver_backend, and message. Numeric values must be finite or explicitly
represented as null with a machine-readable reason such as NOT_COMPUTABLE.
Non-finite JSON is never emitted. Bounded summaries and rank provenance are
required. Legacy WP04 fields may be preserved during migration, but the common
fields are authoritative.

### Event model and consumers

| Event | Decision | Consumer/use case |
|---|---|---|
| ANALYSIS_START, ANALYSIS_END, ANALYSIS_FAILED | ADOPT | Run lifecycle, status and failure provenance |
| MESH_READY | ADOPT | Mesh/DOF/quality and preflight observability |
| ASSEMBLY_START, ASSEMBLY_END | ADOPT | Assembly timing, nnz and memory |
| LINEAR_SOLVE_START, LINEAR_SOLVE_ITERATION, LINEAR_SOLVE_END | ADOPT; iteration requires backend callback | Backend, preconditioner, residual and convergence monitoring |
| STEP_START, STEP_ACCEPTED, STEP_REJECTED | ADOPT | Nonlinear/transient progression and retry accounting |
| NONLINEAR_ITERATION | ADOPT | Residual, correction, eta, Newton count and state |
| LINE_SEARCH_TRIAL, LINE_SEARCH_ACCEPTED, LINE_SEARCH_REJECTED | Conditional on a route with line search | Diagnose globalization and rejected trials |
| CHECKPOINT | ADOPT | Restart/recovery provenance and state digest |
| CONTACT_STATE | Conditional on contact route | Active set, penetration and contact-state changes |
| TIME_STEP_START, TIME_STEP_ACCEPTED, TIME_STEP_REJECTED | Conditional on transient route | Time-step, dt and stability/energy monitoring |
| MODAL_MODE_FOUND | Conditional on modal route | Mode index, eigenvalue/frequency and eigen residual |

No event is a claim that its producer exists on every route; unsupported
events remain absent or explicitly unavailable.

## 4. Analysis coverage

| Route | Meaningful telemetry | Baseline status | Future evidence |
|---|---|---|---|
| linear_static | Mesh, DOFs, nnz, assembly, setup/factorization, solve, residual, memory, reactions | PARTIAL; result/audit data exist, no common live producer | Add route wrapper and linear start/end events |
| modal | Mesh, matrix validity, mode index, eigenvalue/frequency, eigen residual, eigensolver iterations | PARTIAL; ModalResult has post-solve fields | Add modal lifecycle and mode events |
| geometric_nonlinear_static | Steps, Newton iterations, residual/correction, line search, linear solve, state/checkpoint | PARTIAL/PROTOTYPE through WP04 | Wrap existing observer and close adaptive forwarding gap |
| material_nonlinear_static | Steps, Newton/material updates, residual, rollback/checkpoint, linear solves | MISSING common live path | Instrument only after route contract review |
| contact | Contact state, active set, penetration, iterations, rollback, linear solve | PARTIAL/historical diagnostics; no common producer | Define contact event producer and failure evidence |
| arc_length | Step, signed/load factor, path coordinate, turning point and retry state | PARTIAL/historical G07 evidence | Add continuation-specific fields only when route is migrated |
| transient_dynamic | Time, dt, step acceptance, energies, dynamic residual, checkpoint/recovery | PARTIAL result/history/checkpoint data | Wrap history/checkpoint producers |
| harmonic_response | Frequency, complex solve, residual, factorization reuse and response metrics | PARTIAL result path | Define frequency-sweep events |

The matrix is intentionally bounded: a generic observer does not qualify a
route whose producers and failure policies have not been exercised.

## 5. Linear solver telemetry schema

LINEAR_SOLVE_START and LINEAR_SOLVE_END should expose:

backend (DIRECT, CG, MINRES, GMRES, PETSC_KSP), preconditioner,
matrix_rows, matrix_columns, matrix_nnz, method, rtol, atol, max_iterations,
iterations, raw_residual_norm, relative_residual_norm,
backward_error_eta_inf, converged, fallback_used, fallback_reason,
solve_time_s, setup_time_s, and status.

LINEAR_SOLVE_ITERATION is optional and emitted only where a backend callback can
supply it. Absence is not convergence. Direct solves may report iterations as
null with NOT_APPLICABLE; PETSc-specific details stay in metadata.

## 6. Memory and timing schema

Memory fields retain the WP04 distinction:

| Field | Exact meaning |
|---|---|
| peak_rss_process | Peak resident set/working-set bytes for the process, from the platform source named in metadata |
| peak_private_or_uss_process | Peak private/USS bytes when the platform exposes it; null with reason otherwise |
| telemetry_sample_peak_rss | Maximum RSS value actually sampled by telemetry, not necessarily OS lifetime peak |
| telemetry_sample_peak_private | Maximum private/USS value actually sampled by telemetry |

For MPI, records must distinguish per-rank samples from aggregate peak and
identify the aggregation rule. No private/USS claim is made on platforms where
only RSS is available.

Timing fields are explicit and non-overlapping:
mesh_setup_time_s, assembly_time_s, factorization_setup_time_s,
linear_solve_time_s, postprocess_time_s, communication_time_s,
checkpoint_io_time_s, and total_analysis_time_s. A field is null rather than
silently reusing a differently scoped timer.

## 7. JSONL and console policy

The JSONL sink keeps one valid JSON object per line, append mode, UTF-8,
monotonic sequence numbers and immediate flush. allow_nan is disabled.
Default fsync remains off to avoid a hidden performance tax; an explicit
terminal/checkpoint durability mode may fsync at those boundaries. A sink
write/open/flush failure must mark telemetry health as degraded and must never
change mechanics, turn a solver failure into success, or replace the original
solver exception. A crash can leave the terminal event absent; readers classify
the stream as INCOMPLETE/UNKNOWN rather than PASS.

The text console is a rate-limited, stable-column view. For nonlinear runs it
shows analysis/mesh, DOFs, step/Newton, load factor, residual/correction,
alpha, linear backend/Krylov count, eta, solve time, RSS/private, elapsed and
status. It is not a GUI and is not the canonical evidence sink.

## 8. Failure safety

The future observer boundary must isolate sink failures from mechanics while
retaining sink-health evidence. Solver exceptions, KeyboardInterrupt,
numerical non-convergence, nonfinite state, disk-full and serialization
failures receive explicit terminal status when possible. The original
exception is re-raised unchanged after best-effort failure emission.
Nonfinite metrics are rejected before serialization. No missing metric is
converted to zero, no unsupported route is reported as success, and no
incomplete stream is a qualification PASS.

## 9. Overhead and verification plan

With monitoring disabled, the target is near-zero/minimal overhead: no
callback construction, serialization, file I/O, or unnecessary memory
sampling. With monitoring enabled, overhead must be bounded by measurement;
no percentage is frozen in this preparation.

WP15-B should benchmark identical representative solves in four modes:
OFF, console-only, JSONL-only, and console+JSONL. Record wall time, peak RSS,
private/USS where available, event count, file size and failure behaviour.
Use repeated runs and report distribution, platform, Python and backend
provenance.

## 10. Compatibility and WP15 split

| Existing component | Migration action |
|---|---|
| Nonlinear callback and JSONL keys | WRAP first; preserve C2R6 output, add envelope adapter |
| Newton lifecycle | GENERALIZE event names/sequence while retaining legacy fields |
| Linear solve info/adapter | GENERALIZE into backend-neutral start/iteration/end payloads |
| Large MPI telemetry | WP04_SPECIFIC_KEEP, then WRAP with rank metadata |
| Memory helpers | REUSE_AS_IS; add explicit source/availability fields |
| Verification observatory | REUSE_AS_IS for evidence; GENERALIZE only after separate contract review |
| Checkpoint/audit/manifest | REUSE_AS_IS and WRAP at lifecycle boundaries |
| Public route APIs | DEPRECATE_LATER only after compatibility tests; no change in WP15 prep |

The proposed two-point split is:

* WP15-A — 1 point: generic event schema, observer/sink interface, sequence
  and failure-safe serialization contract, compatibility adapter.
* WP15-B — 1 point: bounded route instrumentation, console/JSONL sinks,
  overhead benchmark and failure-safety qualification.

No point is awarded here. Production instrumentation and migration require a
separate Owner-approved implementation task after the WP04 campaign.

## 11. Owner decisions required

The following are intentionally PROPOSED_OWNER_REVIEW, not frozen policies:

1. Whether sequence numbers are per analysis stream or globally scoped.
2. Whether terminal/checkpoint fsync is enabled by an explicit durability mode.
3. The minimum event retention/rate for high-iteration runs.
4. The compatibility lifetime for legacy WP04 JSONL keys.
5. The overhead budget after the OFF/console/JSONL benchmark.
6. Which route subset is required for WP15-B points.

Current status is PREPARATION_ONLY_OWNER_REVIEW_REQUIRED; no maturity claim
is changed and no G04/G08/TL or Agent A artifact is touched.
