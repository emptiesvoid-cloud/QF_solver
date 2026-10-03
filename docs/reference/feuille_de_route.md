---
doc_id: DOC-REF-004
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# Public roadmap

0.2.8 is the latest published release. Version 0.2.10 is the
current source candidate and has not been published. Version 0.2.9 was a
development/source snapshot, not a PyPI package, GitHub Release, or version
DOI. 0.2.9 source is integrated into `main` and tagged `v0.2.9`; no
package or version DOI has been published. This roadmap is a product-level orientation; it is not a release gate,
tag, publication decision, or promise that an unqualified route is ready for
production.

## Current direction

The current development direction is to make bounded nonlinear structural
mechanics easier to inspect and reproduce while preserving the existing
linear element-analysis boundaries. Work includes common Newton and
residual/tangent infrastructure, transactional state management, bounded
geometric/J2/contact routes, and continuation diagnostics. The
[capability index](../capabilities/index.md) and
[candidate V&V summary](../verification/0_2_10/README.md) state what the
evidence accepts—and what it excludes.

## Follow-up themes

1. Re-freeze and audit the exact source candidate selected for publication;
   keep package-scoped and whole-repository archive gates distinct.
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
