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
