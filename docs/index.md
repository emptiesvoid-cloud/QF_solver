---
doc_id: DOC-STATE-001
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# QF Solver 0.2.7

QF Solver is an inspectable Python finite-element solver for structural
mechanics. This site is the user-facing entry point for the stable 0.2.7
source release. Claims are bounded by the active capability registry and its
linked evidence.

## Start here

1. [Install QF Solver](getting-started/installation.md).
2. Run the [first calculation](getting-started/quickstart.md).
3. Check [elements and maturities](elements/index.md).
4. Select an [analysis route](analyses/index.md) and [solver backend](solveurs/index.md).
5. Read the [known limitations](etat/limites.md) before using a result.

## Current scope

- Bounded linear static routes are available for the element combinations in
  the active 0.2.7 matrix.
- Small-strain J2 is bounded to TET4, TET10, HEX8 and HEX20.
- Modal, Newmark, harmonic, buckling and frictionless contact routes have
  route-specific limitations.
- WEDGE6 static is experimental. WEDGE6 modal is qualified only for its
  declared first-three-mode scope.
- PETSc/MPI large-model evidence is limited to recorded structured TET4
  workloads and environments.

## Verification

The [0.2.7 verification summary](verification/0_2_7/README.md) gives a public
overview and links to the detailed, immutable evidence records. Internal gate,
work-package and audit identifiers are kept there under an explicit
traceability section; they are not part of the user workflow.

The project distinguishes implementation, testing, verification, external
correlation and qualification. None of these labels is a claim of universal
physical validation or certification.

## Release and roadmap

The stable source release is `0.2.7`, frozen at tag `v0.2.7`. See the
[public roadmap](reference/feuille_de_route.md) for product-level next steps.
Historical qualification records remain available for provenance and are
clearly labelled as historical in their own pages.
