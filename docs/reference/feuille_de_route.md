---
doc_id: DOC-REF-004
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# Public roadmap

QF Solver 0.2.8 is the current development candidate. This roadmap describes
product-level follow-up work; it is not a release gate, tag, publication or a
promise that an unqualified route is production-ready.

## Current release

This is the 0.2.8 development scope. A historical planning snapshot may retain
earlier scores or work-package wording, but it does not define the current
candidate.

The release focuses on inspectable formulations, bounded numerical evidence,
reproducible solver behavior and recorded large-model PETSc/MPI workflows.
TET4, TET10, HEX8 and HEX20 have the strongest solid-element coverage. WEDGE6
static and modal are qualified only within their separate bounded scopes.
Mixed static, modal, translational-MPC and multi-material workflows are
separately bounded; mixed Newmark and harmonic remain experimental bounded.

## Next technical themes

1. Extend comparable verification for selected element and analysis
   combinations without broadening claims prematurely.
2. Diagnose or redesign the mixed PETSc/MPI runtime without treating its
   architecture-only readiness as runtime qualification.
3. Expand external correlation only where meshes, loads, conventions and
   observables are demonstrably comparable.
4. Continue WEDGE15, PYRAMID5, HEX8R/B-bar, finite-kinematic J2 and any
   HEX8-SRI expansion as separate, evidence-led projects.

## Explicitly deferred

General nonlinear/contact production use, finite-sliding production support,
GPU claims, universal HPC scaling, 5M Gold and deeper 10M scaling analysis are
not part of the current public promise. They require new evidence and a
separate decision.

Historical plans and qualification records remain in
[`docs/verification/0_2_7/`](../verification/0_2_7/) for provenance. They are
not the active product roadmap. The mixed distributed PETSc/MPI runtime is
explicitly `NOT_VALIDATED` and is deferred beyond the 0.2.8 release gate.
