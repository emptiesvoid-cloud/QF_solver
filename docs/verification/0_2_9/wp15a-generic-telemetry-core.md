---
doc_id: DOC-029-WP15A-GENERIC-TELEMETRY-CORE-001
revision: 0.2
status: controlled_candidate
applicable_version: 0.2.9a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP15-A generic telemetry core

## Owner status and bounded scope

WP15 architecture is OWNER_FROZEN. This implementation is a
WP15_A_PASS_CANDIDATE_PENDING_INTEGRATION and is not an official point award.
The formal state remains WP15 = 0/2 and the validated total remains 29/100
until the active release branch integrates and revalidates this work.

Implementation baseline:
2c52bf8196a7d47d14ce1784290580160de26590 on branch 0.2.9-wp15-prep.
The package version observed at that baseline is 0.2.8; this preparation
targets the 0.2.9 roadmap without changing package metadata.

This task adds route-neutral infrastructure only. It does not instrument
analysis routes, change mechanics, convergence policy, linear numerical
behaviour, or active WP04/C2R6 telemetry. WP15-B owns route instrumentation,
console rendering and measured overhead qualification.

The companion machine-readable record is
[qualification/0_2_9/wp15a_generic_telemetry_core.json](../../../qualification/0_2_9/wp15a_generic_telemetry_core.json).

## Implemented package

The new package is src/solveur/core/telemetry:

| Module | Responsibility |
|---|---|
| events.py | EventType/EventStatus vocabulary, finite-only TelemetryEvent envelope, explicit missing-value token and deterministic JSON |
| observer.py | TelemetrySink protocol, thread-safe per-analysis sequences, TelemetryEmitter, CompositeSink, bounded MemorySink and solver-exception guard |
| health.py | HEALTHY/DEGRADED state and sink failure ledger with sink, error, event type and sequence |
| jsonl.py | UTF-8 append JSONL sink, immediate flush and optional terminal/checkpoint fsync |
| schemas.py | Backend-neutral linear, memory and timing field validation |
| legacy.py | External WP04 payload adapter preserving the complete legacy mapping under metadata |

No import or call site was added to the existing WP04 nonlinear driver, large
assembly telemetry, or any mechanical route.

## Event and envelope contract

The controlled event identifiers are:

ANALYSIS_START, ANALYSIS_END, ANALYSIS_FAILED, MESH_READY, ASSEMBLY_START,
ASSEMBLY_END, LINEAR_SOLVE_START, LINEAR_SOLVE_ITERATION, LINEAR_SOLVE_END,
STEP_START, STEP_ACCEPTED, STEP_REJECTED, NONLINEAR_ITERATION,
LINE_SEARCH_TRIAL, LINE_SEARCH_ACCEPTED, LINE_SEARCH_REJECTED, CHECKPOINT,
CONTACT_STATE, TIME_STEP_START, TIME_STEP_ACCEPTED, TIME_STEP_REJECTED and
MODAL_MODE_FOUND.

Mandatory envelope fields are schema_version, event_type, analysis_id,
analysis_type, route, sequence_number, elapsed_time_s, status, metrics and
metadata. Optional fields are timestamp, step, iteration, load_factor,
physical_time, solver_backend and message.

Event types and statuses are controlled vocabularies. All nested metrics and
metadata values are detached and checked for JSON compatibility; NaN, positive
infinity and negative infinity are rejected. A missing measurement uses
value = null with a controlled reason such as NOT_COMPUTABLE, NOT_AVAILABLE,
NOT_APPLICABLE, BACKEND_UNSUPPORTED or NOT_SAMPLED. Bare null metric values are
rejected so missing data cannot be confused with a zero measurement.

JSON uses sorted keys, compact separators and allow_nan = false. Wall-clock
timestamp is optional provenance only; elapsed_time_s and sequence_number are
the ordering fields.

## Sequence and observer contract

Sequence numbers are scoped per analysis_id and start at zero. Each
TelemetryEmitter owns or receives a SequenceGenerator. The generator is
thread-safe; the emitter lock serializes event construction and sink delivery
for one emitter. SequenceValidator rejects duplicate, skipped or backwards
numbers. There is no global cross-analysis or MPI ordering claim.

TelemetryEmitter accepts one sink or a fan-out. Metric suppliers are evaluated
only after the enabled check. When disabled, no event is constructed, no sink
is called and no lazy metric supplier runs. The bounded MemorySink defaults to
10,000 events; an explicit max_events = None is required for an unbounded debug
sink.

## Sink health and failure isolation

CompositeSink calls every sink and records ordinary sink exceptions as
DEGRADED with sink identifier, exception type/message and event context. A
failed sink does not stop sibling sinks. Child sink health ledgers are
aggregated by CompositeSink after construction, emit, flush and close, so a
degraded child is visible through both the composite and TelemetryEmitter.
Each copied child failure retains its original context and is marked with
CHILD_SINK_REPORTED_FAILURE; direct fan-out exceptions are marked with
DIRECT_COMPOSITE_FAILURE. The same child ledger entry is not copied repeatedly
on later events.

JSONL open/write/flush/fsync failures are recorded in the sink health ledger
and stop that sink safely. A child health object with no readable failure
ledger can still degrade the parent through an explicit accounting entry;
sinks without a health object retain exception-based isolation.

JsonlSink writes one UTF-8 object per line in append mode and flushes after each
event. Within a fresh sink session it independently validates contiguous
per-analysis sequences beginning at zero. Duplicate, skipped and backwards
events are rejected, marked DEGRADED and never written. Independent analysis
streams may be interleaved. Append mode is not automatic cross-process
continuation: existing file history is not inspected to infer sequence state,
and there is no MPI/global ordering claim. Default fsync is disabled. Explicit fsync is allowed only after
CHECKPOINT, ANALYSIS_END or ANALYSIS_FAILED. Existing flushed history remains
readable after an abort; absence of a terminal event is INCOMPLETE/UNKNOWN, not
PASS.

preserve_solver_exception and emit_analysis_failed_best_effort provide the
failure pattern for numerical callers: best-effort ANALYSIS_FAILED telemetry
is attempted, but the original solver exception, KeyboardInterrupt or
SystemExit is re-raised unchanged. Telemetry failures cannot become mechanics
results or replace the original exception.

## Compatibility and schema helpers

LegacyWP04Adapter maps ITERATION, STEP_ACCEPTED, STEP_FAILED, SOLVE_FAILED and
SOLVE_COMPLETED to common event identifiers while retaining the entire original
payload under metadata. It is external to the active WP04 path and removes no
legacy key.

Linear schema helpers support DIRECT, CG, MINRES, GMRES and PETSC_KSP and
validate backend, preconditioner, matrix dimensions/nnz, method, tolerances,
iteration count, raw/relative residuals, backward error, convergence,
fallback and setup/solve timing. Direct methods may use an explicit missing
iteration token; iteration events are not required from a direct backend.

Memory names are peak_rss_process, peak_private_or_uss_process,
telemetry_sample_peak_rss and telemetry_sample_peak_private. Timing names are
mesh_setup_time_s, assembly_time_s, factorization_setup_time_s,
linear_solve_time_s, communication_time_s, checkpoint_io_time_s,
postprocess_time_s and total_analysis_time_s. Values are not inferred across
scopes or platforms.

## Verification and limitations

The targeted WP15-A suite covers envelope fields and event vocabulary,
finite/nested validation, explicit missing values, deterministic JSON,
independent sequences, JSONL flush, durability boundaries and per-analysis
duplicate/skip/backwards rejection, child-health aggregation, composite
partial failure, bounded memory, original-exception preservation,
KeyboardInterrupt semantics, disabled/lazy execution, legacy adaptation and
linear/memory/timing schemas.

This is infrastructure evidence, not route qualification. There is no console
sink, no broad route instrumentation, no distributed sequence contract, no
measured overhead percentage and no maturity change in WP15-A. Those items
remain WP15-B or Owner-review dependencies.

## Owner correction history

The initial WP15-A candidate was recorded at the preceding revision with
generic sink health and emitter exposure in place, but without complete child
ledger aggregation or an independent JsonlSink stream-order guard. Owner
Correction R1 is recorded here as OWNER_CORRECTION_R1. It hardens only those
two infrastructure contracts; it does not rewrite the candidate history,
change WP04/C2R6 telemetry, instrument routes, or alter numerical behavior.
