---
doc_id: DOC-027-011
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Large-Scale and 1M-DOF Plan

This plan characterizes resource boundaries. It does not promise that every
route can solve one million degrees of freedom.

## Size ladder

| Level | Purpose | Required interpretation |
| --- | --- | --- |
| 100k DOF | repeatable baseline | establish timing, memory and residual method |
| 300k DOF | large full-solve checkpoint where feasible | report full solve or resource limitation |
| 500k DOF | ambitious intermediate target | characterize bottleneck and resource context |
| 1M DOF | ambitious readiness probe | full solve, iterative/HPC result or characterized resource limit |

## Measurements

Record model creation/import, assembly, factorization or preconditioner setup,
solve/iterations, post-processing, peak RSS and Python allocation when
available, total wall time, nnz, residual, hardware/software and topology.
Separate warm-up, I/O and compute timings.

## Allowed verdicts

- `PASS_FULL_SOLVE`: the declared route completes with residual and resource
  evidence;
- `PASS_ITERATIVE_OR_HPC`: an explicitly supported iterative or HPC route
  completes with its own limitations;
- `RESOURCE_LIMITED_CHARACTERIZED`: the probe cannot complete, but the reason,
  resource boundary and partial measurements are reproducible.

The last verdict is not an automatic release blocker when no public full-solve
claim is made. It is also not a PASS for the missing capability.

## WP12 evidence checkpoint

The bounded campaign is recorded in
`qualification/0_2_7/wp12_scaling_evidence.json` and the separate 300k
assembly probe in `qualification/0_2_7/wp12_assembly_probe_300k.json`.
Matrix-free CG completed the declared structured TET4 route through 750141
DOF. The 300k probe reached 311469 DOF for assembly only. The 1M attempt was
`RESOURCE_LIMITED_TIME`; SciPy retained its explicit 200000-DOF guard and the
direct route was memory-limited at 107811 DOF. PETSc/SLEPc were unavailable in
the measured environment. WP12 status is `PASS_WITH_LIMITATIONS` with
`PROPOSED_OWNER_REVIEW` pending. No universal 1M or multi-million-DOF claim is
made.
