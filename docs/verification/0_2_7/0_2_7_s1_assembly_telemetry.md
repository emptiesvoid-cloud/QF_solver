---
doc_id: DOC-027-S1-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
---

# S1 - 5M Assembly Telemetry Setup

S1 adds an optional, low-overhead progress log for the supervised LU2-WP04
retry. It does not run the 5M workload and does not change the frozen FEM
configuration, tolerances or numerical formulation.

## Contract

The machine-readable contract is
[`wp04_telemetry_contract.json`](../../../qualification/0_2_7/wp04_telemetry_contract.json).
The implementation is [`telemetry.py`](../../../src/solveur/large/telemetry.py),
and the WP04 runner enables it explicitly with:

```text
--telemetry-log qualification/0_2_7/wp04_runtime/wp04_5m_progress.jsonl
```

Without this option, existing runs remain unchanged. The file is append-only;
rank 0 is the only writer and flushes each JSONL checkpoint.

## Progress and phases

`elements_processed` is emitted after a completed insertion chunk and is
reported against the global element count. Ranks keep local counters and use a
small integer reduction only when their local checkpoint threshold is reached.
Checkpoints target approximately one percent of a local contiguous partition,
with a minimum interval of 100,000 elements. No per-element output or matrix
synchronization is introduced.

Each record includes rates, conservative ETA values when a rate exists, memory
when available, explicit `NOT_MEASURED` swap status, rank count and phase. The
phase vocabulary is `GENERATING`, `ASSEMBLING`, `MAT_ASSEMBLY`, `RHS`,
`PCSETUP`, `PC_READY`, `FAILED` and `COMPLETED`. One-million-element milestones
are recorded with their elapsed time and seconds per million.

## Failure and scope

An open/write/flush error changes telemetry status to `DEGRADED`, emits a
warning, and leaves the main FEM calculation running. It is never silently
ignored and never changes the solver result. Interrupted runs retain all
already flushed lines.

S1 status is `PASS`. WP04 remains
`USER_INTERRUPTED_INCONCLUSIVE`; S1 does not trigger C1 or claim 5M readiness.
No 5M, 1M, 3M, full-regression or numerical campaign was run for S1.
