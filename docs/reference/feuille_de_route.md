---
doc_id: DOC-REF-004
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Public roadmap

QF Solver 0.2.7 is the current stable source release. This roadmap describes
product-level follow-up work; it is not a release gate or a promise that an
unqualified route is production-ready.

## Current release

This is the 0.2.7 active scope. A historical planning snapshot may retain
earlier scores or work-package wording, but it does not define the current
release.

The release focuses on inspectable formulations, bounded numerical evidence,
reproducible solver behavior and recorded large-model PETSc/MPI workflows.
TET4, TET10, HEX8 and HEX20 have the strongest solid-element coverage. WEDGE6
static remains experimental, while its modal claim is limited to the declared
first-three-mode scope.

## Next technical themes

1. Extend comparable verification for selected element and analysis
   combinations without broadening claims prematurely.
2. Improve the usability and portability of optional PETSc/MPI workflows.
3. Expand external correlation only where meshes, loads, conventions and
   observables are demonstrably comparable.
4. Investigate deferred mixed-mesh, WEDGE15, PYRAMID5, HEX8R/SRI/B-bar and
   finite-kinematic J2 work as separate, evidence-led projects.

## Explicitly deferred

General nonlinear/contact production use, finite-sliding production support,
GPU claims, universal HPC scaling, 5M Gold and deeper 10M scaling analysis are
not part of the current public promise. They require new evidence and a
separate decision.

Historical plans and qualification records remain in
[`docs/verification/0_2_7/`](../verification/0_2_7/) for provenance. They are
not the active product roadmap.
