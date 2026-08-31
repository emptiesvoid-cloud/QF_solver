# QF Solver

**White-box finite-element tools for verifiable structural mechanics.**

QF Solver is an open-source Python finite-element solver for structural
mechanics, linear dynamics and selected nonlinear research paths. The project
keeps formulations, assumptions, diagnostics and verification evidence
inspectable. A capability is only considered qualified inside the scope and
configuration recorded by its evidence.

## Current maturity

- **Current version:** `0.2.6a0`
- **Release status:** Released on Git as `v0.2.6a0`; PyPI project: `qf-solver`
- **Qualification status:** bounded qualification is recorded within the
  documented scope; the individual gate and capability statuses remain
  authoritative.
- **Qualification snapshot:** `93561c2c0ae1c173deb81e47c3fa3852643275cb`

The Git release is available at `v0.2.6a0`. Check the `qf-solver` PyPI project
page for package availability and release history. Evidence packages record
their own qualified source SHA and artifact manifests; the current gate snapshot is maintained in
[`qualification/0_2_6/gates.json`](qualification/0_2_6/gates.json).

| Maturity | Meaning | Current examples |
| --- | --- | --- |
| **STABLE_BOUNDED** | Evidence supports a declared, bounded scope. | Linear static, small-strain J2, failure diagnostics. |
| **SUPPORTED_WITH_LIMITATIONS** | The route is usable in a documented scope, with active evidence or coverage limitations. | Modal, Newmark, harmonic, linear buckling, frictionless contact, measured performance. |
| **EXPERIMENTAL** | The route exists and has tests or research evidence, but is not a qualified general capability. | Total-Lagrangian research path, arc-length, selected shell/beam/laminate paths. |
| **RESEARCH / NOT QUALIFIED** | The route is exploratory or explicitly excluded from qualified claims. | Finite-kinematic J2, coupled nonlinear workflows, friction, optional HPC paths. |

Current gate status is maintained in
[`qualification/0_2_6/gates.json`](qualification/0_2_6/gates.json): G00-G03 are
`PASS`, G04-G13 are `PASS_WITH_LIMITATIONS`, G14 is
`PASS_WITH_LIMITATIONS`, and G15 is `PASS`.
G07 remains explicitly bounded by its Owner closeout; gate status does not
expand the scope of an individual capability.

## Capability overview

| Capability | Public status | Bounded scope | Main evidence and limitations |
| --- | --- | --- | --- |
| Linear static | **STABLE_BOUNDED** | Linear elastic cases in the recorded element-analysis matrix. | G04 evidence; orthotropic, laminate, shell, beam and discrete combinations remain case-dependent. |
| Small-strain J2 | **STABLE_BOUNDED** | Homogeneous small-strain J2 on TET4, TET10, HEX8 and HEX20. | G06 evidence; algorithmic tangent symmetry is not independently qualified and increment-partition evidence is strongest for TET4. |
| Modal / Newmark / harmonic | **SUPPORTED_WITH_LIMITATIONS** | Controlled linear modal, transient and harmonic cases across the recorded family matrix. | G05 evidence; external coverage is representative rather than complete for every family. |
| Linear buckling | **SUPPORTED_WITH_LIMITATIONS** | First linearized tangent-instability factor and first mode for the family-specific bounded scope recorded by G08, using the sparse route. | TET4 is qualified bounded; TET10/HEX20 remain limited; HEX8 requires more evidence. No post-buckling, multi-mode or general physical-validation claim. |
| Frictionless contact | **SUPPORTED_WITH_LIMITATIONS** | Bounded node-to-triangle contact routes with documented activation and failure behavior. | G09 evidence; no friction, mortar, general surface-to-surface or universal conditioning claim. |
| Failure diagnostics | **STABLE_BOUNDED** | Recorded fail-closed, finite-diagnostic and state-transaction cases. | G11 evidence; coverage is bounded and not exhaustive for every future route. |
| Performance | **SUPPORTED_WITH_LIMITATIONS** | Measured assembly and solve profiles on declared hardware and model topologies. | G12 evidence; approximately 300k DOF is assembly-only and 1M DOF is resource-limited. |

## Element and analysis coverage

Element availability does not imply qualification for every analysis. The
following summary is intentionally conservative; the detailed machine-readable
mapping is in [`capability_coverage.md`](docs/verification/0_2_6/capability_coverage.md).

| Element family | Linear static | Modal / dynamic / harmonic | Small-strain J2 | TL / geometric nonlinear | Buckling | Contact |
| --- | --- | --- | --- | --- | --- | --- |
| TET4 | Bounded | Bounded with limitations | Qualified bounded | Bounded / G07 limitations | Qualified bounded | Bounded cases |
| TET10 | Bounded | Bounded with limitations | Qualified bounded | Research / not qualified | Bounded with limitations | Case-dependent |
| HEX8 | Bounded | Bounded with limitations | Qualified bounded | Not qualified / G07 limitation | More evidence required | Bounded cases |
| HEX20 | Bounded | Bounded with limitations | Qualified bounded | Research / not qualified | Bounded with limitations | Case-dependent |
| BEAM2 | Experimental or case-bounded | Controlled G05 cases | Not claimed | Not claimed | Not claimed | Not claimed |
| MITC3 / MITC4 | Experimental or case-bounded | Controlled G05 cases | Not claimed | Not claimed | Not claimed | Not claimed |
| Discrete | Experimental or case-bounded | Controlled G05 cases | Not claimed | Not claimed | Not claimed | Not claimed |

## Materials and nonlinear capabilities

- Isotropic linear elasticity is the principal bounded material scope for
  linear analyses.
- Small-strain J2 is bounded to the four solid families listed above. It is
  not a finite-strain plasticity claim.
- Total-Lagrangian elasticity is bounded and Owner-reviewed for TET4 under G07;
  HEX8 complete-history behavior is not qualified. TET10 and HEX20 remain
  research routes for this capability.
- Existing arc-length, finite-kinematic J2 and coupled nonlinear routes remain
  experimental, deferred or not qualified according to their gate evidence.
- Friction is outside the current release scope. No Coulomb, mortar or
  augmented-Lagrangian capability should be inferred from the presence of
  contact-related code.

## Verification and external correlation

QF Solver separates:

- **Verification:** analytical relations, invariants, residuals, tangents,
  convergence, mesh studies and deterministic replay.
- **External correlation:** bounded numerical comparisons with Code_Aster or
  CalculiX when the formulation, mesh, loading and observable are comparable.
- **Validation:** a separate engineering judgement about fitness for a
  physical application; it is not established by a code-to-code comparison.

The 0.2.6 evidence index, gate matrix and capability mapping are available in
[`docs/verification/0_2_6/README.md`](docs/verification/0_2_6/README.md),
[`0_2_6_gate_matrix.md`](docs/verification/0_2_6/0_2_6_gate_matrix.md) and
[`capability_coverage.md`](docs/verification/0_2_6/capability_coverage.md).
The external-correlation aggregation is representative and bounded; missing
or non-comparable tools and decks remain visible in
[`0_2_6_g13_external_correlations.md`](docs/verification/0_2_6/0_2_6_g13_external_correlations.md).

## Performance boundaries

The performance evidence is a characterization, not a universal scaling law.
Results depend on hardware, sparsity, element topology, solver backend and
memory availability. The current evidence includes full measured solves up to
the declared bounded range, an approximately 300k-DOF assembly-only probe and
a 1M-DOF resource-limited probe. No claim of general HPC support or guaranteed
multi-million-DOF solving is made.

## Experimental and research paths

The following routes are visible so that their limits are not mistaken for
missing functionality:

- G07 geometric nonlinear and arc-length review is
  `PASS_WITH_LIMITATIONS`: the bounded TET4 TL and Arc-Length claims are
  limited to the Owner closeout scope; HEX8 complete history and refined
  Arc-Length comparability remain excluded/deferred.
- Finite-kinematic J2 and coupled nonlinear workflows are research or
  experimental routes under G06/G10, not qualified release capabilities.
- Orthotropic/laminate, shell/beam/discrete extensions, PETSc/SLEPc and large
  model paths have route-specific evidence and are not blanket-qualified.

## Known limitations

- Every claim is bounded by element family, formulation, mesh quality, loading,
  boundary conditions, solver route and deformation domain.
- A passing case does not qualify an untested combination of element, material
  and analysis.
- External correlation can be unavailable or non-comparable and must then be
  recorded as such; it is not silently treated as a pass.
- The current 0.2.6 cycle has completed the G14 capability-coverage audit and
  the G15 Owner release review; the release remains bounded by the documented
  gate and capability limitations.
- No claim of certification, general physical validation, production
  readiness, industrial equivalence or replacement of another solver is made.

See the detailed 0.2.6 evidence and limitations in
[`docs/verification/0_2_6/`](docs/verification/0_2_6/).

## Installation

### Stable published package

The stable published alpha remains `0.2.5a0`:

```powershell
python -m pip install qf-solver==0.2.5a0
qf-solver --version
```

### 0.2.6a0 Git release

The `0.2.6a0` release is available from Git at tag `v0.2.6a0`. For a
reproducible source install, use the exact tagged source:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.6a0
python -m pip install -e ".[test]"
qf-solver --version
```

The tagged release state is identified by the qualification snapshot
`93561c2c0ae1c173deb81e47c3fa3852643275cb` and its evidence manifests. For a
published-package install, use:

```powershell
python -m pip install "qf-solver==0.2.6a0"
```

Check the `qf-solver` PyPI project page for current availability and release
history.

Optional extras are available for mesh tooling, documentation and optional
PETSc/SLEPc/MPI environments:

```powershell
python -m pip install -e ".[mesh]"
python -m pip install -e ".[docs]"
python -m pip install -e ".[hpc]"
```

The optional HPC stack is not required for the standard installation and is
not a general scalability guarantee.

## Minimal usage

The maintained example is
[`examples/tet4_static.json`](examples/tet4_static.json).

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4.json
```

The same workflow is available through the public `qf_solver` namespace:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

## API, CLI and examples

The public Python namespace is `qf_solver`; the historical `solveur` namespace
is retained for compatibility. Useful CLI entry points include `solve`,
`check-mesh`, `inspect`, `evidence`, `import-mesh`, `methods`, `benchmarks`,
`benchmark`, `verify` and the controlled V&V commands. See:

- [`examples/README.md`](examples/README.md)
- [`docs/reference/api_stability.md`](docs/reference/api_stability.md)
- [`docs/demarrage/installation.md`](docs/demarrage/installation.md)
- [`docs/verification/0_2_6/`](docs/verification/0_2_6/)

## Release status and finalization

`0.2.6a0` is released on Git as `v0.2.6a0`, with a bounded scope focused on
maturity, reproducibility, architecture and controlled V&V. The `qf-solver`
PyPI project page is the reference for package availability and release history.

Current release state:

```text
Release status: Released
Tag: v0.2.6a0
Qualification SHA: 93561c2c0ae1c173deb81e47c3fa3852643275cb
PyPI project: qf-solver
PyPI availability: Check the project page
```

The authoritative qualification snapshot is identified by each evidence
package's recorded source SHA and artifact manifests.

For local checks and contribution guidance, see
[`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/architecture.md`](docs/architecture.md)
and the [0.2.6 V&V foundation](docs/verification/0_2_6/README.md).

Typical local documentation and quality checks are:

```powershell
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
python -m ruff check src scripts tests
python -m compileall -q src scripts tests qf_solver.py
```

## Version history

| Version | Main direction |
| --- | --- |
| `0.2.0a0` | Open-source foundation, initial packaging and V&V structure. |
| `0.2.1a0` | Qualification registry, release V&V automation and traceability. |
| `0.2.2a0` | Sparse backend and diagnostics strengthening, with optional HPC preparation. |
| `0.2.3a0` | HEX8/HEX20, Gmsh import and expanded TET/HEX benchmarks. |
| `0.2.4a0` | Shared small-strain J2, Full Newton, consistent tangent and state transactions. |
| `0.2.5a0` | Historical bounded qualification work for J2, TL elasticity, buckling, contact and failure modes. |
| `0.2.6a0` | Git release for maturity, reproducibility, controlled V&V and architecture. |

See [`CHANGELOG.md`](CHANGELOG.md) for the detailed release history.

## Documentation and license

- [`docs/verification/0_2_6/README.md`](docs/verification/0_2_6/README.md):
  current V&V foundation and evidence index.
- [`qualification/capability_registry.json`](qualification/capability_registry.json):
  machine-readable capability inventory and maturity mapping.
- [`docs/architecture.md`](docs/architecture.md): architecture overview.
- [`prochaines_etapes.md`](prochaines_etapes.md): roadmap and next steps.

The software is distributed under the
[Apache License 2.0](LICENSE). Documentation and original examples are under
[CC BY 4.0](LICENSE-DOCS). Third-party components remain subject to the terms
listed in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
