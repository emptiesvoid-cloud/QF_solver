---
doc_id: DOC-STATE-001
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# QF Solver

**Current release documentation:** `0.2.11`<br>
**Published:** 2026-10-07<br>
**Version DOI:** [`10.5281/zenodo.23214487`](https://doi.org/10.5281/zenodo.23214487)<br>
**Project concept DOI:** [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897)

QF Solver is an inspectable Python finite-element solver for structural
mechanics and dynamics, intended for engineering-method development,
research and reproducible FEM studies. It combines solid, beam and shell
formulations, linear and dynamic analyses, selected nonlinear routes, and
experimental disk-gyroscopic modal analysis and Campbell diagrams.

Claims remain bounded by the exact element, formulation, material, loading,
mesh and solver route in their controlling record. Distribution audits are
bound to exact source and artifact bytes; the full-repository G03 archive gate remains failed.
GitHub-generated source archives are not cleared distribution artifacts.
See the [0.2.11 V&V summary](verification/0_2_11/README.md) and the separate
[0.2.10 evidence](verification/0_2_10/README.md).

## Start here

1. [Install QF Solver](getting-started/installation.md).
2. [Check whether QF Solver fits your problem](getting-started/when-to-use-qf-solver.md).
3. Run the [linear first calculation](getting-started/quickstart.md).
4. Try the separate [bounded nonlinear example](getting-started/nonlinear-example.md).
5. Check the [capability index](capabilities/index.md), [elements](elements/index.md)
   and [analysis routes](analyses/index.md).
6. Read [known limitations](etat/limites.md) before relying on a result.

## Explore the solver

- [Elements](elements/index.md) and [analyses](analyses/index.md): solid,
  beam, shell, static, modal and linear dynamic workflows.
- [Composites](composites/index.md): orthotropy, laminates, ply-level output
  and experimental first-ply indicators.
- [Nonlinear mechanics](mechanics/nonlinear-overview.md): selected J2,
  geometric/contact routes, Newton iteration and transactional state.
- [Rotating modal](mechanics/rotating-modal.md) and [Campbell](mechanics/campbell.md):
  experimental serial BEAM2/disk scope with complex modes and explicit tracking.
- [Solvers and backends](solveurs/index.md), [model audits](reference/audit_detail_modes.md)
  and [public API](reference/qf_solver_api.md): calculation and inspection tools.

Read [What's New in 0.2.11](whats-new/0.2.11.md) for changes in this version.
The historical [0.2.10 release notes](whats-new/0.2.10.md) describe the first
public release after 0.2.8; the intervening 0.2.9 tag is a source snapshot,
not a public package release.

## Verification and maturity

The [capability index](capabilities/index.md) provides route-specific status
and evidence links. The [V&V and maturity model](verification/evidence-and-maturity.md)
explains the distinction between testing, verification, external correlation,
qualification and physical validation. The [0.2.11 verification summary](verification/0_2_11/README.md)
states the current evidence provenance and limitations. The separate
[0.2.10 summary](verification/0_2_10/README.md),
[0.2.8 verification summary](verification/0_2_8/README.md) and [0.2.7
summary](verification/0_2_7/README.md) remain historical evidence.

No certification, universal physical validation, industrial equivalence or
general-purpose nonlinear-solver claim is made. The internal 95/100 roadmap
score is not a public quality rating. WP14 remains `HOLD_NOT_PROMOTED`; passing a bounded
package scan or CI job does not clear the complete repository archive.

## Release and citation

Only wheel/sdist bytes bound to the matching selected-release contract can
be represented as audited Python distribution artifacts.
The full-repository G03 archive gate remains failed; automatic GitHub source
archives and a complete repository archive are not represented as cleared.

For exact-version reproducibility, cite the 0.2.11 version DOI
[`10.5281/zenodo.23214487`](https://doi.org/10.5281/zenodo.23214487). The
preceding 0.2.10 release has version DOI
[`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744). Use the
project concept DOI [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897)
to cite QF Solver across versions. The machine-readable
[`CITATION.cff`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CITATION.cff)
records the 0.2.11 version DOI and publication date.
Release availability is authoritative on [PyPI](https://pypi.org/project/qf-solver/)
and [GitHub Releases](https://github.com/emptiesvoid-cloud/QF_solver/releases).

See [Release history](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CHANGELOG.md), [API stability](reference/api_stability.md)
and the [public roadmap](reference/feuille_de_route.md) for more context.
