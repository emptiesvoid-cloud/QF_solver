---
doc_id: DOC-027-023
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Large-Scale Readiness Evidence

## Status and scope

WP12 records bounded readiness evidence for the existing structured `TET4`
linear-static route. It does not add a new element or a new physical model,
and it does not claim universal one-million-DOF support. The measured source
snapshot is `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a`; the evidence was
collected on that snapshot before the governance commit containing this report.

The model is a connected structured block with six TET4 per hexahedral cell,
homogeneous isotropic linear elasticity, a uniform nodal UX dead load of 1000 N
on the x=length face, and linear-static boundary conditions from the existing
large-model generator. WEDGE6, nonlinear routes and post-buckling are out of
scope.

## Reproduction contract

```text
python scripts/run_wp12_scaling.py --output qualification/0_2_7/wp12_scaling_evidence.json --targets 100000 300000 500000 750000 1000000 --replay-target 100000 --timeout-seconds 600 --max-rss-gb 4
```

The campaign runs isolated child processes with a 600 second timeout and a
4 GiB RSS ceiling. It records topology, timing, memory, sparse non-zeros when
an assembled matrix exists, residuals, solution digests and environment
metadata. High-DOF SciPy cases are rejected by the existing 200000-DOF guard
before model allocation. The separate assembly-only 300k probe is recorded in
`qualification/0_2_7/wp12_assembly_probe_300k.json`.

Environment: Windows 10 build `10.0.19045`, Python `3.13.1`, NumPy `2.2.6`,
SciPy `1.15.2`, psutil `7.2.2`, 12 logical CPUs and approximately 103 GB RAM.
`mpi4py` was available; `petsc4py` and `slepc4py` were not available, so no
PETSc/SLEPc verdict is issued.

## Size ladder

| Target | Actual DOF | Elements | Matrix-free CG | SciPy CG | SciPy direct |
| ---: | ---: | ---: | --- | --- | --- |
| 100k | 107,811 | 196,608 | `PASS_ITERATIVE` | `PASS_FULL_SOLVE` | `RESOURCE_LIMITED_MEMORY` |
| 300k | 311,469 | 584,016 | `PASS_ITERATIVE` | `SOLVER_LIMITED` | `SOLVER_LIMITED` |
| 500k | 526,848 | 998,250 | `PASS_ITERATIVE` | `SOLVER_LIMITED` | `SOLVER_LIMITED` |
| 750k | 750,141 | 1,429,968 | `PASS_ITERATIVE` | `SOLVER_LIMITED` | `SOLVER_LIMITED` |
| 1M | 1,029,000 | 1,971,054 | `RESOURCE_LIMITED_TIME` | `SOLVER_LIMITED` | `SOLVER_LIMITED` |

`PASS_ITERATIVE` is a completed matrix-free solve with finite observables and
relative residual between `9.732e-09` and `9.898e-09`. The maximum completed
matrix-free solve is 750,141 DOF. The 1M probe reached the declared 600 second
limit at a peak sampled RSS of 557,006,848 bytes; it produced no numerical
failure and is not a successful 1M solve.

The 100k SciPy CG full solve completed in 6.611 s with 3,813,789 assembled
non-zeros, peak RSS 192,356,352 bytes and relative residual `1.169e-12`.
SciPy direct at the same size reached the 4 GiB RSS limit before completion.
The higher SciPy sizes are `SOLVER_LIMITED` by the explicit 200000-DOF guard;
no unbounded allocation was attempted.

## 300k assembly probe

The current-source assembly-only probe completed for 311,469 DOF and 584,016
TET4 elements. It measured 11,168,199 global non-zeros, 135,264,268 bytes of
CSR storage, 217.882 s wall time and peak RSS 1,466,396,672 bytes. Phase
timings were 158.609 s mesh validation, 10.554 s assembly planning, 45.662 s
assembly, 34.220 s element kernels, 4.036 s sparse conversion and 0.069 s
sparse finalization. The linear solve was deliberately `NOT_RUN`; this row is
assembly evidence, not a full-solve result.

## Numerical safety and replay

The 100k matrix-free replay produced the same input digest and result digest in
two isolated runs and was classified deterministic. Existing targeted tests
for matrix-free/SciPy equivalence and the no-dense-conversion guard pass. All
completed campaign rows had finite metrics; the report contains zero
numerical failures. The matrix-free residuals are consistent with its declared
`rtol=1e-8` contract, while the assembled SciPy CG residual is substantially
smaller.

No FEM formulation, material law, load convention or existing element kernel
was changed. The retained optimization `WP12-OPT-001` caches the already
grouped TET4 connectivity and flattened DOF indices in the matrix-free
operator. Targeted equivalence remained passing, and a separate 30k engineering
probe showed approximately 1.9x lower elapsed time after the cache change
with the same iteration count and residual. This is a local engineering
measurement, not a universal speedup claim.

## Profile and bottlenecks

The 10k matrix-free profile identifies element matvec and scatter accumulation
as the dominant solve work. The 300k assembly probe identifies generated-model
validation/materialization as the dominant wall-time component, followed by
element kernels and sparse conversion. The bounded ranking is:

1. matrix-free element matvec and scatter accumulation;
2. iteration count and preconditioner quality;
3. large-model validation and generated-model materialization;
4. assembled sparse storage and factorization for the SciPy direct route.

The recommended measured path is matrix-free CG for the high-DOF structured
TET4 route, with assembled SciPy CG limited to its explicit configured domain.
PETSc remains a future option only after its dependencies and reproducible
execution environment are available.

## Bounded conclusion

The campaign supports `PASS_WITH_LIMITATIONS` evidence for the declared
structured TET4 linear-static route and is ready for Owner review. It supports
completed iterative solves through 750,141 DOF, a characterized 311,469-DOF
assembly-only result, and a bounded 1M readiness attempt. It does not support
a public full-solve claim at 1M DOF, a multi-million-DOF claim, general
topology scaling, or a claim that direct SciPy is viable at the measured high
sizes.

Machine-readable records:

- [`wp12_state.json`](../../../qualification/0_2_7/wp12_state.json)
- [`wp12_scaling_evidence.json`](../../../qualification/0_2_7/wp12_scaling_evidence.json)
- [`wp12_assembly_probe_300k.json`](../../../qualification/0_2_7/wp12_assembly_probe_300k.json)

The campaign report and this document are `CONTROLLED_PROOF` records. The
Owner decision remains `PROPOSED_OWNER_REVIEW`; resource-limited and
solver-limited rows are preserved rather than converted to PASS.
