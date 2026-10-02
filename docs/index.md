---
doc_id: DOC-STATE-001
revision: 1.1
status: controlled
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# QF Solver 0.2.10

QF Solver is an inspectable Python finite-element solver for structural
mechanics. **Current release:** [`0.2.10`](https://pypi.org/project/qf-solver/0.2.10/).
The package is available on [PyPI](https://pypi.org/project/qf-solver/), and
the selected distribution archive is preserved at [Zenodo](https://doi.org/10.5281/zenodo.23106744).
Claims are bounded by the active consolidated registry, separate
workflow/capability records and their linked evidence.

## Start here

1. [Install QF Solver](getting-started/installation.md).
2. [Check whether QF Solver fits your problem](getting-started/when-to-use-qf-solver.md).
3. Run the [first calculation](getting-started/quickstart.md).
4. Check [elements and maturities](elements/index.md).
5. Select an [analysis route](analyses/index.md) and [solver backend](solveurs/index.md).
6. Read the [known limitations](etat/limites.md) before using a result.
7. Use the [central capability index](capabilities/index.md) for current
   maturity and record links.

   
## Choosing a FEM solver

If you are evaluating QF Solver against other open-source finite-element
tools, start with the solver-selection and comparison guides:

- [Compare open-source FEM solvers](comparisons/index.md)
- [Python FEM solvers: which one should you use?](comparisons/python-fem-solvers.md)

## Current scope

- Bounded linear static routes are available for the element combinations in
  the carried 0.2.8 registry; the new package version does not promote them.
- Small-strain J2 is bounded to TET4, TET10, HEX8 and HEX20.
- Modal, Newmark, harmonic, buckling and frictionless contact routes have
  route-specific limitations.
- WEDGE6 static is `QUALIFIED_BOUNDED` only for its approved linear-elastic
  scope. WEDGE6 modal has its own bounded first-three-mode scope.
- Connected conforming mixed TET4/WEDGE6/HEX8 static, modal, translational-MPC
  and multi-material workflows are `QUALIFIED_BOUNDED` within their separate
  records. Mixed Newmark and harmonic workflows are `EXPERIMENTAL_BOUNDED`.
- The `.inp` subset, family-aware mixed HDF5 storage, bounded frictionless
  contact and HEX8-SRI are separate `EXPERIMENTAL_BOUNDED` capabilities.
- PYRAMID5 remains internal/research-only, and MITC4 modal remains
  `EXPERIMENTAL`.
- PETSc/MPI large-model evidence is limited to recorded structured TET4
  workloads and environments. The generic mixed PETSc/MPI runtime is
  `NOT_VALIDATED`.

## Verification

The [central capability index](capabilities/index.md) gives the current public
status. The [V&V and maturity model](verification/evidence-and-maturity.md)
explains contracts, frozen gates, evidence and replays. The [0.2.8 verification
summary](verification/0_2_8/README.md) gives the chronological development
overview, while the [0.2.7 summary](verification/0_2_7/README.md) remains
immutable historical evidence. Internal gate,
work-package and audit identifiers are kept there under an explicit
traceability section; they are not part of the user workflow.

The project distinguishes implementation, testing, verification, external
correlation and qualification. None of these labels is a claim of universal
physical validation or certification.

## Release and roadmap

The `0.2.9` source was integrated into `main` at merge commit
`765bbe4`; its required `Quality and verification` and `Documentation tests`
workflows passed on candidate commit `ea28165`. This confirms those CI checks,
not qualification of the whole repository or any broader solver-route claim.
The `v0.2.9` tag identifies the source snapshot; no 0.2.9 GitHub Release,
version DOI, Zenodo archive or PyPI package has been published. The
[earlier bounded review of selected installable sources and public documents](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.9/qualification/0_2_9/wp14/g03_bounded_public_surfaces_r4_7/owner-review.md)
passed at its frozen source revision, while the full repository archive remains
outside that scope and fails the public-content scan. The source tag does not
clear the full archive for distribution. The
[known limitations](etat/limites.md) and recorded failures remain visible.
The current published release is `0.2.10` as linked above. See the
[public roadmap](reference/feuille_de_route.md) for product-level next steps.
The Zenodo version DOI is `10.5281/zenodo.23106744`; that record preserves
the selected distribution artifacts and checksums. The whole-repository
archive still fails G03 and is not a release artifact. The `v0.2.9` source
tag remains unchanged, and WP14 has not been promoted.
Historical qualification records remain available for provenance and are
labelled as historical in their own pages.

Read [What's New in 0.2.10](whats-new/0.2.10.md) for the published release
summary.

## Performance and reproducibility

- [Benchmarks and reproducibility](benchmarks/index.md)

