---
doc_id: DOC-027-LU2-WP01-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# LU2-WP01 - Evidence and Performance Observatory

LU2-WP01 installs a small, opt-in observatory for the large-model and
performance work packages. It records evidence; it does not execute a solver
and it does not change any FEM formulation or maturity decision.

## Source of truth

The record implementation and validation contract are in
`src/solveur/verification/observatory.py` and
`qualification/0_2_7/observatory_contract.json`. The controlled fixture is
`qualification/0_2_7/wp01_observatory_sample.json`.

Each record carries the case/requirement, workload, source SHA and clean-state
flag, environment, route/backend/solver/preconditioner/rank count, input,
configuration and result digests, tolerances, observables, phase timings and
resource metrics.
Optional PETSc, MPI, container and GPU fields are explicit and may be null;
they are never inferred as available.

## Performance vocabulary

Phase timing names are stable and expressed in seconds:

`model_setup`, `preflight`, `assembly_operator`, `redistribution`, `pc_setup`,
`ksp_solve`, `communication`, `io`, `post_processing`, `total`.

Resource fields are `peak_rss_total_bytes`, `peak_rss_per_rank_bytes`, `imbalance`
and `gpu_vram_bytes`. MPI-like rank rows can be summarized with
`aggregate_rank_metrics` without requiring MPI in the test environment.

## Verdicts and fail-closed rules

The accepted classifications are `PASS`, `PASS_WITH_LIMITATIONS`, `FAIL`,
`EXPECTED_FAILURE`, `NOT_COMPARABLE`, `UNAVAILABLE` and `RESOURCE_LIMITED`.
Positive evidence requires a committed clean source, a SHA-256 input digest,
a SHA-256 result digest, a non-empty command and declared environment. Missing
or non-finite data is rejected. An unavailable backend is represented as an
explicit failure/unavailable classification; it is never a silent fallback.

## Replay and comparison

`canonical_json_bytes` and `canonical_digest` use sorted compact JSON encoded
as UTF-8. `read_observatory_record` rejects duplicate JSON keys. Comparison
requires the same case, workload/input digest, execution route and declared
tolerances; it reports timing, metric and environment differences only. It
does not label a run as a regression or an improvement automatically.

The legacy `BenchmarkRunner.run` path is unchanged. New code can opt in with
`BenchmarkRunner.run_observed` or adapt an existing `BenchmarkRun` through
`record_benchmark_run`. If the legacy run has no input digest, the observation
is downgraded to `NOT_COMPARABLE` rather than inventing provenance.

## Governance state

The sample record is a controlled T1 fixture only. No 1M, 3M or 5M benchmark
was run for this work package. LU2-WP01 is `PASS`; LU2 remains open and its
next active work package is LU2-WP02.
