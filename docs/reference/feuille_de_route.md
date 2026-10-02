---
doc_id: DOC-REF-004
revision: 1.1
status: controlled
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# Public roadmap

QF Solver 0.2.8 is the current published release. The 0.2.9 source is
integrated into `main` and tagged `v0.2.9`; no package or version DOI has been
published. This roadmap describes product-level follow-up work; it is not a
release gate, tag, publication or a promise that an unqualified route is
production-ready.
The development package version `0.2.10` is a publication candidate, not a
tagged or published release. Its selected distribution and documentation must
be re-audited at the final frozen source revision before a release decision.

## Current release

The scope below describes the published 0.2.8 release. The roadmap is
forward-looking and does not change that release scope or authorize publication
of the tagged 0.2.9 source.

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
[`docs/verification/0_2_7/`](../verification/0_2_7/README.md) for provenance. They are
not the active product roadmap. The mixed distributed PETSc/MPI runtime is
explicitly `NOT_VALIDATED`; its presence in the 0.2.9 development source does
not constitute runtime qualification.
