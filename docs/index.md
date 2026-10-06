---
doc_id: DOC-STATE-001
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.10
reviewer: ""
approver: ""
---

# QF Solver 0.2.10

**Current release:** [`0.2.10`](https://github.com/emptiesvoid-cloud/QF_solver/releases/tag/v0.2.10)<br>
**Next candidate:** `0.2.11` — not yet published<br>
**Selected PyPI distribution:** `qf-solver==0.2.10`<br>
**Version DOI:** [`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744)<br>
**Project concept DOI:** [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897)

QF Solver is an inspectable Python finite-element solver for structural
mechanics and dynamics. Version 0.2.10 is the first public release after
0.2.8 and documents the nonlinear-mechanics development from the intervening
source cycle. The 0.2.9 source snapshot was not a public package release.

Claims remain bounded by the exact element, formulation, material, loading,
mesh and solver route in their controlling record. The selected wheel and
sdist were audited; the full-repository G03 archive gate remains failed.
GitHub-generated source archives are not cleared distribution artifacts.
See the [0.2.10 V&V summary](verification/0_2_10/README.md).
The 0.2.11 candidate adds an experimental, bounded gyroscopic modal route and
Campbell tracking; it is not yet the current release. See its
[candidate V&V summary](verification/0_2_11/README.md).

## Start here

1. [Install the latest published package](getting-started/installation.md).
2. [Check whether QF Solver fits your problem](getting-started/when-to-use-qf-solver.md).
3. Run the [linear first calculation](getting-started/quickstart.md).
4. Try the separate [bounded nonlinear example](getting-started/nonlinear-example.md).
5. Check the [capability index](capabilities/index.md), [elements](elements/index.md)
   and [analysis routes](analyses/index.md).
6. Read [known limitations](etat/limites.md) before relying on a result.

## What changed since 0.2.8

The main documented development is a more common nonlinear execution
architecture: selected routes share a Newton engine, assembly protocol,
accepted-state transactions and robustness diagnostics. Evidence also covers
bounded Total-Lagrangian StVK checks, bounded J2/contact routes, selected
multi-family comparisons and a same-mesh Code_Aster correlation campaign.
Those are different evidence classes and do not imply general nonlinear
qualification, physical validation or unrestricted PETSc/MPI support.

Read [What's New in 0.2.10](whats-new/0.2.10.md) for the published release
and [What's New in 0.2.11](whats-new/0.2.11.md) for the unreleased candidate.
The 0.2.10 page gives the concise comparison with published 0.2.8. The
[nonlinear mechanics overview](mechanics/nonlinear-overview.md) explains its
implementation, scope and boundaries.

## Verification and maturity

The [capability index](capabilities/index.md) provides route-specific status
and evidence links. The [V&V and maturity model](verification/evidence-and-maturity.md)
explains the distinction between testing, verification, external correlation,
qualification and physical validation. The [0.2.10 verification summary](verification/0_2_10/README.md)
states the evidence provenance and open release limitations. The
[0.2.8 verification summary](verification/0_2_8/README.md) and [0.2.7
summary](verification/0_2_7/README.md) remain historical evidence.

No certification, universal physical validation, industrial equivalence or
general-purpose nonlinear-solver claim is made. The internal 95/100 roadmap
score is not a public quality rating. WP14 remains `HOLD`; passing a bounded
package scan or CI job does not clear the complete repository archive.

## Release and citation

The selected wheel and sdist are the audited Python distribution artifacts.
The full-repository G03 archive gate remains failed; automatic GitHub source
archives and a complete repository archive are not represented as cleared.

For reproducibility, cite the exact release DOI
[`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744). Use
[concept DOI `10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897)
to cite the project across versions. The machine-readable
[`CITATION.cff`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CITATION.cff)
records the 0.2.10 release citation.

See [Release history](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CHANGELOG.md), [API stability](reference/api_stability.md)
and the [public roadmap](reference/feuille_de_route.md) for more context.
