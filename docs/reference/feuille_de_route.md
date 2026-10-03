---
doc_id: DOC-REF-004
revision: 1.1
status: controlled
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# Public roadmap

QF Solver 0.2.10 is the selected release line; check PyPI for publication. The 0.2.9 source was
integrated into `main` and tagged `v0.2.9` without a package or version DOI.
This roadmap describes product-level follow-up work; it is not a release gate
or a promise that an unqualified route is production-ready. The 0.2.10
distribution is limited to the audited selected package and documentation;
the whole-repository archive remains outside that scope.

## Current release

The scope below carries the bounded 0.2.8 evidence into the 0.2.10 package
without automatically promoting a route. The roadmap is forward-looking and
does not authorize distribution of the uncleared repository archive.

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
