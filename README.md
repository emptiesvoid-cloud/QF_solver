# QF Solver

Python FEM/FEA solver for structural mechanics and dynamics, with inspectable
formulations, bounded nonlinear mechanics, reproducible verification and
optional PETSc/MPI workflows for explicitly recorded routes.

QF Solver is a research and engineering-method development project. Its
capabilities are route-specific: an implemented or converged analysis is not
automatically verified, qualified or physically validated. It is not a
certified solver or a general-purpose replacement for industrial FEA software.

## Release status

| Item | Status |
| --- | --- |
| Release line | `0.2.10` |
| Source tag | [`v0.2.10`](https://github.com/emptiesvoid-cloud/QF_solver/tree/v0.2.10) |
| Selected PyPI distribution | `qf-solver==0.2.10` |
| Version DOI | [`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744) |
| Project concept DOI | [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897) |
| Citation metadata | [`CITATION.cff`](CITATION.cff) identifies release `0.2.10` |

QF Solver 0.2.10 is the first public release after 0.2.8. The intervening
`v0.2.9` tag is a source snapshot, not a PyPI, GitHub Release or Zenodo
version. The selected wheel and sdist have a bounded release audit; the
whole-repository G03 archive gate remains failed. GitHub-generated source
archives are not cleared distribution artifacts. See the
[0.2.10 verification summary](docs/verification/0_2_10/README.md) for scope
and limitations.

## 0.2.10 highlights

These are development-cycle results with their recorded scopes, not a blanket
qualification of nonlinear mechanics.

- A shared nonlinear architecture now provides a Newton engine, composite
  assembly protocol, accepted-state transaction and common diagnostics for
  selected material and geometric routes. Contact compatibility loops are
  not all migrated to that lifecycle.
- Trial/accepted state, commit/rollback, cutback/retry and schema-v2
  checkpoint/restart are covered for declared fixed, adaptive and arc-length
  paths; frictional contact and distributed restart are outside that scope.
- Line search, stagnation classification, adaptive increments and arc-radius
  policies have bounded robustness evidence. The arc-length correction
  kernel remains specialized; the work does not qualify general postbuckling.
- Total-Lagrangian StVK identities and structural campaigns were audited for
  TET4 and HEX8 within a frozen static, serial deformation envelope. The
  closure audit retained limitations and did not itself update the public
  maturity registry.
- Small-strain J2 retains its bounded TET4/TET10/HEX8/HEX20 scope. The
  owner-accepted corotational J2 qualification is HEX8-only; TET10/HEX20
  extensions are separately bounded evidence, not transitive qualification.
- Frictionless penalty contact remains experimental and bounded. Prior
  frictional-contact acceptance applies to a narrow serial linear-static
  route; current-source requalification is not established, and recent
  area-supported stick/slip evidence is experimental with mesh sensitivity.
- External Code_Aster evidence is a bounded same-mesh linear-static
  correlation for declared TET4, HEX8, TET10 and HEX20 cases. It is not
  experimental physical validation, nonlinear correlation or a second
  independent global FEM/Newton solve.
- PETSc/MPI evidence includes bounded two-rank linear-static cases with
  replicated inputs for four element families and separate historical
  structured-TET4 large-model workloads. It makes no general scaling,
  mixed nonlinear, GPU or cross-machine claim.
- Public documentation now separates implementation, verification,
  externally correlated evidence and maturity decisions; see [What's New in
  0.2.10](docs/whats-new/0.2.10.md).

For detailed scopes, links to the controlling records and known limitations,
start with the [capability index](docs/capabilities/index.md), [nonlinear
mechanics overview](docs/mechanics/nonlinear-overview.md), [known
limitations](docs/etat/limites.md), and [V&V summary](docs/verification/0_2_10/README.md).

### Published 0.2.8 carry-forward boundaries

The existing [0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
remains the source of truth for these published scopes; 0.2.10 does not
rewrite them:

| Route | Published status | Boundary |
| --- | --- | --- |
| WEDGE6 static | `QUALIFIED_BOUNDED` | Declared Gmsh Prism 6 static route only. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | Homogeneous consistent-mass scope and first three modes only. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | No validated generic mixed-distributed runtime claim. |

Historical structured-TET4 large-model evidence includes recorded ~1.029M,
~3M, ~5.01264M and bounded ~10M DOF observations. The two complete 5M Silver replays
were recorded on the declared eight-rank environment; these are
workload-specific observations, not general scaling evidence. No claim of GPU, general HPC, hardware-independent scaling, mixed-mesh support or
general nonlinear scaling is made. No claim of certification or universal
physical validation is made.

## Installation

Once the tagged release workflow has published the selected PyPI artifacts,
install the 0.2.10 package:

```bash
python -m pip install "qf-solver==0.2.10"
qf-solver --version
```

The unpinned command `python -m pip install qf-solver` installs the latest
version currently available from PyPI. The
[installation guide](docs/getting-started/installation.md) covers optional
extras and recorded native PETSc/MPI environment boundaries.

For a first calculation, see [Quick Start](docs/getting-started/quickstart.md).
A separate [nonlinear example](docs/getting-started/nonlinear-example.md)
uses a small existing TET4 input and intentionally reports the route's
engineering-profile warning.

## Citing QF Solver

For reproducibility, cite the exact version DOI for QF Solver 0.2.10:
[`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744). To cite
the project independent of a specific release, use the concept DOI
[`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897).
`CITATION.cff` is the machine-readable citation record.

## Verification and scope

The repository distinguishes:

- **implementation** — code exists;
- **testing** — an automated or controlled case ran;
- **verification** — a declared invariant or comparison was checked;
- **external correlation** — a declared observable was compared with another
  solver under a frozen, comparable setup;
- **qualification** — an Owner-accepted decision assigns maturity to a
  specific route and scope;
- **physical validation** — comparison with physical observations, which is
  not implied by numerical verification or solver-to-solver correlation.

The 0.2.10 release includes substantial bounded evidence, but its roadmap
score is internal and is not a public quality rating. WP14 remains `HOLD`;
neither that score nor a passing CI workflow closes the full-repository G03
archive gate. There is no certification, universal physical validation,
industrial equivalence or universal HPC claim.

## Project links

- [Documentation home](https://emptiesvoid-cloud.github.io/QF_solver/)
- [Capability index](docs/capabilities/index.md)
- [What's New in 0.2.10](docs/whats-new/0.2.10.md)
- [Release history](CHANGELOG.md)
- [Source repository](https://github.com/emptiesvoid-cloud/QF_solver)
- [Issue tracker](https://github.com/emptiesvoid-cloud/QF_solver/issues)
