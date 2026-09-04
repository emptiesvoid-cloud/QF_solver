---
doc_id: DOC-027-LU2-WP02-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# LU2-WP02 - CPU/MPI/GAMG readiness and configuration freeze

Status: `PASS_WITH_LIMITATIONS`

Execution source snapshot: `3cb817c9391ef7998c5950d3071c8d9ce1be5dd8`

This closeout records the configuration used to prepare LU2-WP03 through
LU2-WP05. It does not claim universal 3M performance and does not change the
WP14 acceptance contract.

## Controlled records

- Contract: `qualification/0_2_7/wp02_execution_contract.json`
- Evidence index: `qualification/0_2_7/wp02_runtime/wp02_evidence_index.json`
- Freeze: `qualification/0_2_7/wp02_runtime/wp02_config_freeze.json`
- State: `qualification/0_2_7/wp02_state.json`
- Collector: `scripts/collect_lu2_wp02_evidence.py`
- Targeted tests: `tests/unit/test_lu2_wp02.py`

## Frozen runtime

The controlled workload is the existing 3,000,000-true-DOF structured TET4
linear-static FEM model. Its input digest is
`084a471b1caab628e8558c65b1777692ed53d504baad681bf0985c411a33671b`.

The selected route is PETSc AIJ with CG and GAMG, contiguous partitioning,
eight MPI ranks and one thread per rank. The runtime is Docker image
`qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e`,
PETSc/petsc4py 3.25.1, MPICH 5.0.1, Python 3.12.3, NumPy 2.4.6 and SciPy
1.17.1. The frozen configuration is identified by
`LU2-WP02-FREEZE-bfd1975b012453a3` and digest
`bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1`.

WP14 acceptance remains relative tolerance `1e-8`; the explicit PETSc solver
relative tolerance is `1e-10`, with maximum 10,000 iterations. No tolerance
was changed after observation.

## MPI evidence

| ranks | run | status | iterations | total seconds | peak RSS bytes | residual | equilibrium |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2 | `r2_replay1` | PASS | 619 | 2638.165 | 10076241920 | 9.52e-11 | 1.25e-9 |
| 2 | `r2_replay2` | PASS | 619 | 2660.000 | 10076286976 | 9.52e-11 | 1.25e-9 |
| 4 | `r4_run1` | PASS | 598 | 1612.001 | 5373222912 | 1.01e-10 | 3.32e-9 |
| 8 | `r8_replay1` | PASS | 598 | 1568.651 | 2925957120 | 9.93e-11 | 2.52e-9 |
| 8 | `r8_replay2` | PASS | 598 | 1596.150 | 2925043712 | 9.93e-11 | 2.52e-9 |

The same input and solver configuration were used for all large-model runs.
The 4-rank run is a single recorded run; the required two-replay coverage is
present at 2 and 8 ranks. Strong-scaling speedups versus the first 2-rank run
are 1.64x at 4 ranks and 1.68x at 8 ranks, with corresponding efficiencies of
0.82 and 0.42. These are measurements for this host and workload only.

## Selection evidence

GAMG and HYPRE/BoomerAMG both passed the subscale numerical invariants. GAMG
was selected because its recorded total time was 5.54 s versus 60.26 s for
HYPRE and its peak RSS was 474 MB versus 1170 MB. This is not a universal
preconditioner ranking. Contiguous and graph/PTScotch partitioning also both
passed; contiguous was selected because it was faster on the recorded
subscale (5.54 s versus 6.56 s).

## Phase measurement boundary

The observatory records model setup, operator/assembly, preconditioner setup,
KSP solve, reactions post-processing, energy post-processing and total time,
plus iterations, residual, equilibrium, energy, peak RSS and RSS imbalance. The legacy runner does not
expose separate preflight, redistribution, communication or I/O boundaries.
Those fields are therefore explicitly `null`; no time is inferred from the
total. LU2-WP06 remains the place to improve execution-phase diagnostics.

## Freeze policy and limitations

The frozen configuration applies to LU2-WP03, LU2-WP04 and LU2-WP05. After
this closeout, changing ranks, partitioning, matrix format, KSP, preconditioner,
PETSc options, tolerances or runtime requires a documented blocker and Owner
review. PETSc remains optional at runtime and must fail closed when unavailable;
the legacy SciPy/matrix-free route remains preserved.

This evidence is bounded to one single-host Docker environment, the structured
TET4 3M input and the frozen AIJ/CG/GAMG route. It is not a 5M result, a weak
scaling result, an HPC portability claim or a universal performance claim.

## Decision

`LU2-WP02 = PASS_WITH_LIMITATIONS`.

The next active work package is LU2-WP03. No solver or FEM formulation source,
Owner maturity decision, tag, release or PyPI state was changed by this
closeout.
