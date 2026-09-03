# QF Solver

**White-box finite-element tools for verifiable structural mechanics.**

QF Solver is an open-source Python finite-element solver for structural
mechanics, linear dynamics and selected nonlinear research paths. The project
keeps formulations, assumptions, diagnostics and verification evidence
inspectable. A capability is only considered qualified inside the scope and
configuration recorded by its evidence.

## Current maturity

- **Current version:** `0.2.7a0`
- **Release status:** Release candidate; not tagged or published on PyPI
- **Qualification status:** WP21 is `PASS_WITH_LIMITATIONS`; final release
  action remains governed by the 0.2.7 release criteria.
- **Qualification snapshot:** active evidence is indexed by
  [`qualification/0_2_7/manifest.json`](qualification/0_2_7/manifest.json);
  the parent 0.2.6 qualification snapshot is retained separately.

The parent tagged source release remains available at `v0.2.6a0`. The active
0.2.7 candidate is the current development checkout and has no 0.2.7 tag or
PyPI publication. Evidence packages record their own qualified source SHA and
artifact manifests; the active gate snapshot is maintained in
[`qualification/0_2_7/gates.json`](qualification/0_2_7/gates.json).

| Maturity | Meaning | Current examples |
| --- | --- | --- |
| **QUALIFIED_BOUNDED** | Evidence supports a declared, bounded scope with an explicit qualification boundary. | Linear static, small-strain J2, failure diagnostics. |
| **SUPPORTED_WITH_LIMITATIONS** | The route is usable in a documented scope, with active evidence or coverage limitations. | Modal, Newmark, harmonic, linear buckling, frictionless contact, measured performance. |
| **EXPERIMENTAL** | The route exists and has tests or research evidence, but is not a qualified general capability. | Total-Lagrangian research path, Arc-Length, selected shell/beam/laminate paths. |
| **RESEARCH / NOT QUALIFIED** | The route is exploratory or explicitly excluded from qualified claims. | Finite-kinematic J2, coupled nonlinear workflows, friction, optional HPC paths. |

The parent 0.2.6 gate status is preserved in its historical records. Current
0.2.7 Level-Up status is maintained in
[`qualification/0_2_7/gates.json`](qualification/0_2_7/gates.json): WP13 and
WP14 are `PASS`, WP15 is `PASS_WITH_LIMITATIONS`, WP16 is `PASS`, WP17-WP21
are `PASS_WITH_LIMITATIONS` within their declared scopes, and WP22 remains
`PLANNED`. Gate status does not expand the scope of an individual capability.

## Capability overview

| Capability | Public status | Bounded scope | Main evidence and limitations |
| --- | --- | --- | --- |
| Linear static | **QUALIFIED_BOUNDED** | Linear elastic cases in the recorded element-analysis matrix. | G04 evidence; orthotropic, laminate, shell, beam and discrete combinations remain case-dependent. |
| Small-strain J2 | **QUALIFIED_BOUNDED** | Homogeneous small-strain J2 on TET4, TET10, HEX8 and HEX20. | G06 evidence; algorithmic tangent symmetry is not independently qualified and increment-partition evidence is strongest for TET4. |
| Modal / Newmark / harmonic | **SUPPORTED_WITH_LIMITATIONS** | Controlled linear modal, transient and harmonic cases across the recorded family matrix. | G05 evidence; external coverage is representative rather than complete for every family. |
| Linear buckling | **SUPPORTED_WITH_LIMITATIONS** | First linearized tangent-instability factor and first mode for the family-specific bounded scope recorded by G08, using the sparse route. | TET4 is qualified within a bounded scope; TET10/HEX20 remain limited; HEX8 requires more evidence. No post-buckling, multi-mode or general physical-validation claim. |
| Frictionless contact | **SUPPORTED_WITH_LIMITATIONS** | Bounded node-to-triangle contact routes with documented activation and failure behavior. | G09 evidence; no friction, mortar, general surface-to-surface or universal conditioning claim. |
| WEDGE6 static vertical slice | **EXPERIMENTAL** | Technical small-strain elastic static workflow with the recorded import, face-load and post-processing cases. | WP07-WP09 evidence; no general WEDGE6 static qualification claim. |
| WEDGE6 modal | **QUALIFIED_BOUNDED** | Homogeneous isotropic consistent-mass route, first three modes, four-level refinement and four same-mesh PENTA6 comparisons. | WP10 Owner decision; modes four to six and other dynamics remain outside the bounded claim. |
| Failure diagnostics | **QUALIFIED_BOUNDED** | Recorded fail-closed, finite-diagnostic and state-transaction cases. | G11 evidence; coverage is bounded and not exhaustive for every future route. |
| Performance | **SUPPORTED_WITH_LIMITATIONS** | Measured solves on declared hardware and model topologies, including a bounded PETSc/MPI route. | WP16-WP18 evidence; 1.029M, 3M Silver/Gold Compute and 5M Silver are bounded results, not universal scaling claims. |

## Element and analysis coverage

Element availability does not imply qualification for every analysis. The
following summary is intentionally conservative; the active detailed
machine-readable mapping is in
[`0_2_7_capability_matrix.md`](docs/verification/0_2_7/0_2_7_capability_matrix.md).
The 0.2.6 matrix remains a historical view only.

| Element family | Linear static | Modal / dynamic / harmonic | Small-strain J2 | TL / geometric nonlinear | Buckling | Contact |
| --- | --- | --- | --- | --- | --- | --- |
| TET4 | Bounded | Bounded with limitations | Qualified bounded | Bounded / G07 limitations | Qualified bounded | Bounded cases |
| TET10 | Bounded | Bounded with limitations | Qualified bounded | Research / not qualified | Bounded with limitations | Case-dependent |
| HEX8 | Bounded | Bounded with limitations | Qualified bounded | Not qualified / G07 limitation | More evidence required | Bounded cases |
| HEX20 | Bounded | Bounded with limitations | Qualified bounded | Research / not qualified | Bounded with limitations | Case-dependent |
| WEDGE6 | Experimental static slice | Qualified bounded modal route | Not qualified | Not qualified | Not qualified | Not qualified |
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
- WEDGE6 static remains experimental. WEDGE6 modal is qualified only within
  the first-three-mode consistent-mass scope recorded by WP10; this does not
  transfer to static, nonlinear or other dynamic routes.
- Existing Arc-Length, finite-kinematic J2 and coupled nonlinear routes remain
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

The active 0.2.7 evidence index, gate matrix and capability mapping are
available in [`docs/verification/0_2_7/README.md`](docs/verification/0_2_7/README.md),
[`0_2_7_gate_matrix.md`](docs/verification/0_2_7/0_2_7_gate_matrix.md) and
[`0_2_7_capability_matrix.md`](docs/verification/0_2_7/0_2_7_capability_matrix.md).
The parent 0.2.6 evidence remains available for historical provenance. External
correlation is representative and bounded; missing or non-comparable tools and
decks remain visible in the active evidence records.

## Performance boundaries

The performance evidence is a characterization, not a universal scaling law.
Results depend on hardware, sparsity, element topology, solver backend and
memory availability. The bounded evidence includes two replays at 1,029,000
true DOF, two 3M Silver replays plus a bounded 3M Gold Compute workload, and
two complete 5M Silver replays on the pinned PETSc/MPI structured TET4 route.
The 5M result is exactly 5,012,640 DOF and 9,773,946 TET4 elements; the
recorded 3M route used about 10.08 GB peak RSS. These are claims for the
recorded workload, hardware, container, MPI configuration and solver options
only. No claim of GPU, general HPC, hardware-independent scaling, 3M Gold
with restart, or universal 5M capacity is made.

## Experimental and research paths

The following routes are visible so that their limits are not mistaken for
missing functionality:

- G07 geometric nonlinear and Arc-Length review is
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
- The current 0.2.7 candidate has bounded Level-Up evidence through WP21;
  final release action remains separate from this development checkout.
- PETSc/MPI is optional at runtime. The bounded 1.029M, 3M and 5M results
  apply only to the recorded structured TET4 route and pinned environment;
  they do not qualify other element families, nonlinear analyses or dynamics.
- No claim of certification, general physical validation, production
  readiness, industrial equivalence or replacement of another solver is made.

See the detailed 0.2.6 evidence and limitations in
[`docs/verification/0_2_6/`](docs/verification/0_2_6/).
The active 0.2.7 evidence and deferred Level-Up 2 scope are indexed in
[`docs/verification/0_2_7/`](docs/verification/0_2_7/).

## Installation

### 0.2.7a0 release candidate

The current `0.2.7a0` checkout is a release candidate under review. It is not
yet tagged or published on PyPI. Install it from the active branch when
reproducing the candidate locally:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout codex/0.2.7-foundation
python -m pip install -e ".[test]"
qf-solver --version
```

The candidate's release truth, evidence heads and claim boundaries are in
[`qualification/0_2_7/manifest.json`](qualification/0_2_7/manifest.json).

### PyPI package

Check the [`qf-solver` PyPI project page](https://pypi.org/project/qf-solver/)
for currently published versions and release history. Install the published
package selected from that page:

```powershell
python -m pip install qf-solver
qf-solver --version
```

### 0.2.6a0 tagged source release

The `0.2.6a0` tagged source release is available at tag `v0.2.6a0`. For a
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

The active `0.2.7a0` candidate has a bounded scope focused on reproducible
large-model solving and numerical trust. The `qf-solver` PyPI project page is
the reference for published package availability and release history. The
parent `v0.2.6a0` release remains the latest tagged historical baseline until
the 0.2.7 release action is completed.

Current release state:

```text
Current version: 0.2.7a0
Release status: Release candidate; not tagged or published
Parent tag: v0.2.6a0
WP21 status: PASS_WITH_LIMITATIONS
PyPI project: qf-solver
PyPI availability: 0.2.7a0 not published; check the project page for history
```

The authoritative 0.2.7 release truth is identified by its manifest and each
evidence package's recorded source SHA and artifact manifests. The parent
0.2.6 qualification snapshot remains `93561c2c0ae1c173deb81e47c3fa3852643275cb`.

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
| `0.2.7a0` | Reproducible large-model solving and numerical trust; release candidate under review. |
| `0.2.2a0` | Sparse backend and diagnostics strengthening, with optional HPC preparation. |
| `0.2.3a0` | HEX8/HEX20, Gmsh import and expanded TET/HEX benchmarks. |
| `0.2.4a0` | Shared small-strain J2, Full Newton, consistent tangent and state transactions. |
| `0.2.5a0` | Historical bounded qualification work for J2, TL elasticity, buckling, contact and failure modes. |
| `0.2.6a0` | Maturity, reproducibility, controlled V&V and architecture foundation. |

See [`CHANGELOG.md`](CHANGELOG.md) for the detailed release history.

## Documentation and license

- [`docs/verification/0_2_7/README.md`](docs/verification/0_2_7/README.md):
  active 0.2.7 V&V foundation and evidence index.
- [`qualification/0_2_7/capability_registry_v2.json`](qualification/0_2_7/capability_registry_v2.json):
  active machine-readable capability inventory and maturity mapping.
- [`docs/verification/0_2_6/README.md`](docs/verification/0_2_6/README.md):
  historical 0.2.6 V&V foundation and evidence index.
- [`docs/architecture.md`](docs/architecture.md): architecture overview.
- [`prochaines_etapes.md`](prochaines_etapes.md): roadmap and next steps.

The software is distributed under the
[Apache License 2.0](LICENSE). Documentation and original examples are under
[CC BY 4.0](LICENSE-DOCS). Third-party components remain subject to the terms
listed in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
