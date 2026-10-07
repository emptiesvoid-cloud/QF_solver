---
doc_id: DOC-REF-004
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Public roadmap

QF Solver 0.2.11 is the current documentation baseline. QF Solver 0.2.11 is
the current published release. It was published on 2026-10-07 with version DOI
[`10.5281/zenodo.23214487`](https://doi.org/10.5281/zenodo.23214487). Version
0.2.9 was a development/source snapshot, not a PyPI package, GitHub Release,
or version DOI. This roadmap is a product-level orientation; it is not a release gate,
tag, publication decision, or promise that an unqualified route is ready for
production.

## Current direction

Version 0.2.11 includes prospective V&V consolidation and experimental
gyroscopic modal/Campbell routes within a bounded BEAM2-and-disk scope.
Neither route is promoted beyond `EXPERIMENTAL`. The
[verification summary](../verification/0_2_11/README.md) records its evidence
and limitations. The selected 0.2.11 distribution has been published after
exact-source release gates; this does not clear the whole-repository archive
or broaden any technical claim.

Follow-up work will extend evidence and reproducibility without
generalizing the existing bounded nonlinear routes or changing the linear
element-analysis boundaries. The current release already includes common
Newton and residual/tangent infrastructure, transactional state management,
bounded geometric/J2/contact routes, and continuation diagnostics. The
[capability index](../capabilities/index.md) and
[0.2.10 V&V summary](../verification/0_2_10/README.md) state what the
evidence accepts and what it excludes. The
[0.2.11 summary](../verification/0_2_11/README.md) adds the experimental
rotating evidence without rewriting those earlier decisions.

## Follow-up themes

1. Keep each future source and package audit bound to exact Git blobs; keep
   package-scoped and whole-repository archive gates distinct.
2. Extend nonlinear evidence only through separately declared, reproducible
   scopes; do not generalize beyond the families, formulations, or loads tested.
3. Requalify current-source frictional contact and preserve its observed mesh
   sensitivity until a new decision changes that scope.
4. Improve the distributed PETSc/MPI path before making general nonlinear or
   scaling claims.
5. Extend external numerical correlation only for comparable meshes,
   formulations, conventions, and observables; keep it distinct from physical
   validation.

## Deferred or outside the current claim

General finite-strain plasticity, general finite-sliding/self-contact,
nonlinear transient dynamics, broad postbuckling/bifurcation, nonlinear
distributed MPI/PETSc, universal scaling, GPU support, and certification are
not current public claims. Each requires its own technical evidence and
decision. Historical plans and qualification records remain in the archive
for provenance; they are not the active product roadmap and do not
automatically become current claims.
