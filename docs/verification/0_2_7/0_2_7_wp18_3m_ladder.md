---
doc_id: DOC-027-WP18-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
source_sha: 9c0605645fa60ef0d89f3ce98ca361a677f13d1d
reviewer: ""
approver: ""
---

# WP18 - 3M DOF Ladder

## Decision

WP18 is PASS_WITH_LIMITATIONS. The mandatory Silver target passed on a
real structured TET4 finite-element model with exactly 3,000,000 true
degrees of freedom. Bronze and Silver are separate claims. Gold is
NOT_ATTEMPTED and is not a 3M qualification claim.

The execution used the frozen WP14 acceptance contract and the validated
explicit PETSc route:

- image: qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e
- PETSc 3.25.1, MPICH 5.0.1, Python 3.12.3
- two MPI ranks, PETSc AIJ, CG, GAMG, contiguous partitioning
- internal solver tolerance 1e-10; WP14 acceptance tolerance remains 1e-8
- no implicit backend fallback

The execution source snapshot is
9c0605645fa60ef0d89f3ce98ca361a677f13d1d. The WP14 contract digest is
1236aaf8ddb0451ae5d3ddac02864ade3c54273da4a0e8064434ae0c11459ce3.

## Model and Bronze

The model is a unit cube with homogeneous isotropic material
(E=210 GPa, nu=0.3). All translations on x=0 are fixed and a uniform
nodal x-load with total 1,000,000 N is applied on x=1. Each structured
cell is decomposed into six TET4 elements.

The 3M model uses 99 x 99 x 99 cells, 1,000,000 nodes and 5,821,794
TET4 elements. The Bronze preflight recorded the model digest, disk and
memory envelope, dependency checks, PETSc backend selection and chunk
configuration. Bronze is a model/resource/preflight result only; it does not
authorize a solve claim.

## Ladder results

| Level | True DOF | Elements | Iterations | Total (s) | Setup (s) | Solve (s) | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5M | 1,536,000 | 2,958,234 | 494 | 393.36 | 269.72 | 115.62 | 5.22 GB |
| 2M | 2,044,416 | 3,951,018 | 539 | 1,098.98 | 910.71 | 173.71 | 6.91 GB |
| 2.5M | 2,572,125 | 4,983,504 | 583 | 1,612.63 | 1,358.46 | 235.98 | 8.66 GB |
| 3M run 1 | 3,000,000 | 5,821,794 | 619 | 2,659.82 | 2,329.82 | 305.15 | 10.08 GB |
| 3M run 2 | 3,000,000 | 5,821,794 | 619 | 2,670.26 | 2,344.79 | 301.92 | 10.08 GB |

Both 3M runs completed without timeout or resource-limited classification.
Their residual, equilibrium, energy, finite-output and SPD checks passed:

- residual relative: 9.5154e-11
- equilibrium relative: 1.2454e-9
- energy relative: 2.4122e-13
- displacement norm: 2.6853e-3
- strain energy: 2.3123

The replay comparison is recorded in
qualification/0_2_7/wp18_runtime/wp18_replay_comparison.json. It reports
identical DOF, matvec, residual, equilibrium and energy fields, with matching
source, input and configuration digests.

## Gold boundary

The Silver route is distributed PETSc/MPI evidence, but this does not satisfy
the complete Gold definition by itself. No restart/checkpoint artifact and no
distinct second physical case were executed. Gold therefore remains
NOT_ATTEMPTED; no restart, resilience or multi-case 3M claim is made.

The dominant measured cost is operator/preconditioner setup. From 1.5M to
3M, total time grew by about 6.76x, setup by about 8.64x, solve time by
about 2.64x, and peak RSS by about 1.93x. These are measurements of the
declared hardware, container, MPI size and topology, not universal scaling
guarantees.

## Evidence

Machine-readable summary:
qualification/0_2_7/wp18_runtime/wp18_summary.json.
State: qualification/0_2_7/wp18_state.json.
Bronze preflight:
qualification/0_2_7/wp18_runtime/wp18_bronze_preflight.json.
The five raw run records are stored beside the summary. Generated HDF5 models
and binary displacement outputs remain local run artifacts and are not part
of the tracked proof bundle.

WP18 changes no FEM formulation, WP14 contract or tolerance. No full
regression was run for this large benchmark work package.
