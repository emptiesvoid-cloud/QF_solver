---
doc_id: DOC-STATE-001
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8

QF Solver is an inspectable Python finite-element solver for structural
mechanics. **Current development state:** `0.2.8`. **Publication status:**
`NOT_PUBLISHED_YET`. This site does not announce a tag or publication. Claims
are bounded by the active consolidated registry, separate workflow/capability
records and their linked evidence.

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
  the active 0.2.8 registry.
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

The source currently identifies as `0.2.8`; no 0.2.8 tag or publication is
claimed by this documentation update. See the [public roadmap](reference/feuille_de_route.md)
for product-level next steps. Historical qualification records remain
available for provenance and are labelled as historical in their own pages.

Read [What's New in 0.2.8](whats-new/0.2.8.md) for the current bounded
development summary.

## Performance and reproducibility

- [Benchmarks and reproducibility](benchmarks/index.md)

