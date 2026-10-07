# QF Solver

[![Python](https://img.shields.io/pypi/pyversions/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![PyPI](https://img.shields.io/pypi/v/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![License](https://img.shields.io/github/license/emptiesvoid-cloud/QF_solver.svg)](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-2f80ed.svg)](https://emptiesvoid-cloud.github.io/QF_solver/)
[![CI](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml/badge.svg)](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml)

QF Solver is an open-source Python finite-element solver for structural
mechanics and dynamics, designed for inspectable formulations,
engineering-method development and reproducible numerical verification. It
offers linear, dynamic and selected nonlinear analysis routes through a
Python API and command-line interface. Tests, benchmarks, evidence records and
explicit scope limits help users understand both what a result shows and what
it does not show.

QF Solver is intended for engineering-method development, research and
reproducible studies. An implemented route or a converged example is not
automatically qualified or physically validated. The project is not certified
and is not a general-purpose replacement for industrial FEA software.

On this page: [Capabilities](#capabilities) · [Modeling](#elements-materials-and-modeling) ·
[How it works](#how-qf-solver-works) · [Installation](#installation) ·
[Quick start](#quick-start) · [Analyses](#analysis-families) ·
[Nonlinear mechanics](#nonlinear-mechanics) · [Rotating dynamics](#rotating-dynamics) ·
[Results](#results-inspection-and-export) · [Larger models](#larger-models-and-performance-context) ·
[Verification](#verification-and-maturity) · [Limitations](#limitations) ·
[Current release](#current-release-and-citation).

## What QF Solver is for

Use QF Solver when you need to inspect how a structural finite-element model
is assembled and solved, develop a mechanical method, compare formulations,
or reproduce a numerical study from explicit inputs and evidence. Typical
starting points include solid stress/displacement problems, beam and shell
response, laminate studies, vibration, and selected nonlinear static cases.
The rotating-modal and Campbell routes add a separate experimental use case;
they do not replace the solver's existing structural capabilities.

The same model workflow is available from Python and the command line. Mesh
checks, assembly audits, solver diagnostics and result exports are part of the
tool, rather than just benchmark infrastructure. The code is intended to be
read and extended, but internal modules are not all stable public API.

For model selection, read [when to use QF Solver](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/when-to-use-qf-solver/)
and the scope of the specific route you intend to use.

## Capabilities

The capabilities below are cumulative, but maturity belongs to a specific
element, analysis, material, configuration and evidence record, not to the
solver as a whole. Use the [capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
and [element map](https://emptiesvoid-cloud.github.io/QF_solver/elements/)
before relying on a particular combination.

| Domain | Current capabilities | Evidence status and boundary |
| --- | --- | --- |
| Elements | TET4, TET10, HEX8, HEX20, WEDGE6, BEAM2, MITC3 and MITC4 routes | Family support and maturity vary by analysis and formulation; see the element-analysis records. |
| Materials and composites | Isotropic elasticity, oriented orthotropic solids, layered shells and first-ply indicators | Material orientations, element combinations and laminate analyses have separate scopes; failure indicators are experimental, not progressive damage. |
| Model composition | Discrete masses/inertias, linear springs, MPC, RBE2/RBE3 and selected conforming mixed-solid workflows | Individual entities do not establish qualification for arbitrary assemblies or interfaces. |
| Linear statics | Structural solves, reactions and selected stress/result fields | Bounded element, material, constraint and load combinations; not every combination is qualified. |
| Modal and dynamics | Classical modal analysis, Newmark transient response and harmonic response | Route-specific mass, damping, timestep, element-family and mixed-model limits apply. |
| Stability | Linear buckling | Does not establish postbuckling or general nonlinear stability behavior. |
| Material nonlinearity | Selected small-strain J2 plasticity routes | Bounded material/element evidence; this is not general finite-strain plasticity. |
| Geometric nonlinearity | Selected Total-Lagrangian and corotational routes | Formulation and element scopes are narrow; corotational J2 assumes small local strains. |
| Contact and constraints | RBE2-style constraints, frictionless contact, and bounded frictional stick/slip evidence | Contact search, sliding, mesh sensitivity and current-source requalification remain limited. |
| Nonlinear solution | Newton methods, line search, adaptive increments, cutback/retry, and selected continuation/arc-length routes | Shared infrastructure does not imply convergence or qualification for arbitrary models. |
| Larger models | Structured-TET4 workflows and selected PETSc/MPI linear-static cases | Optional dependencies and recorded configurations only; no general HPC or nonlinear distributed claim. |
| Rotating dynamics | Experimental disk-gyroscopic `rotating_modal` and Campbell analysis in 0.2.11 | Linear BEAM2 shaft with centered rigid axisymmetric disks; serial dense QEP and explicit scope limits. |
| I/O and interfaces | JSON models, public `qf_solver` Python namespace, CLI, Gmsh mesh import, bounded `.inp` import, JSON/CSV/VTU exports and optional mixed HDF5 results | Import/export formats and optional backends are not general-purpose interchange guarantees. |
| Inspection | Mesh/DOF checks, white-box audits, residuals, equilibrium checks and evidence bundles | Diagnostics describe the selected route and verification profile; they do not certify a model. |
| Verification and validation | Analytical checks, regression tests, controlled benchmarks, reproducible evidence and selected Code_Aster correlations | Numerical verification, external solver correlation and physical validation are distinct claims. |

Status terms such as `QUALIFIED_BOUNDED`, `EXPERIMENTAL_BOUNDED`,
`EXPERIMENTAL` and `NOT_VALIDATED` refer only to the scope documented by the
controlling record. The [published 0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
remains the authority for its historical element-analysis decisions; later
evidence does not silently rewrite those decisions.

## Elements, materials and modeling

### Element families

| Family | Modeling role | Important boundary |
| --- | --- | --- |
| TET4 / TET10 | Four-node and ten-node tetrahedral solids | Linear and selected material-nonlinear routes; higher-order support does not imply every geometric/contact coupling is available. |
| HEX8 / HEX20 | Eight-node and twenty-node hexahedral solids | Formulation, integration and nonlinear scope are route-specific. HEX8-SRI is a separate experimental capability, not a general HEX8R/B-bar/hourglass-control claim. |
| WEDGE6 | Six-node prism solid | Recorded bounded static and homogeneous consistent-mass modal scopes; these do not transfer automatically to other analyses. |
| BEAM2 | Two-node structural beams with axial, bending, shear and torsional response | Selected straight-beam static and dynamic evidence. The disk-gyroscopic route imposes additional straight-shaft/circular-section restrictions. |
| MITC3 / MITC4 | Triangular and quadrilateral shell routes for membrane, bending and transverse shear response | Isotropic and selected laminate workflows; planar, curved, modal and transient scopes must be checked separately. |
| Discrete entities | Concentrated mass and rotary inertia, linear springs and rigid disks | These are distinct from finite elements; their compatibility and mass ownership must be checked for the chosen analysis. |

WEDGE15 is unsupported. PYRAMID5 remains internal/research-only and is not a
supported public element. See the [element map](https://emptiesvoid-cloud.github.io/QF_solver/elements/)
for formulations and evidence rather than assuming a Cartesian product of
all elements, materials and analyses.

### Elastic materials and composites

- **Isotropic elasticity:** solid, beam and shell material definitions, with
  density and section/thickness data where the analysis requires them.
- **Oriented orthotropic solids:** TET4/TET10 routes with explicit material
  axes and nine-constant 3D elasticity. Homogenized composite definitions
  retain material provenance; selected cylindrical-tangent orientations are
  also implemented. This is not a general arbitrary fiber-field model.
- **Laminated shells:** orthotropic plies, ply angles and thicknesses,
  classical laminate `A/B/D` matrices, transverse shear terms, resultants
  and ply-level stresses. Selected MITC4 static scopes have bounded internal
  engineering acceptance; MITC3 and dynamic/curved extensions have their own
  development and review records, not blanket laminate qualification.
- **First-ply indicators:** maximum stress, maximum strain, Tsai-Hill and
  Tsai-Wu indices and reserve factors where material allowables are supplied.
  These indicators remain experimental. They do not degrade stiffness or
  simulate progressive failure, delamination or cohesive interfaces.

Implementation, runtime maturity labels and historical bounded acceptance
are separate. In particular, composite output is not a certification or a
general composite-design allowable. Read the [composite overview](https://emptiesvoid-cloud.github.io/QF_solver/composites/),
[orthotropic solid specification](https://emptiesvoid-cloud.github.io/QF_solver/composites/solides_orthotropes/)
and [first-ply criteria](https://emptiesvoid-cloud.github.io/QF_solver/composites/criteres_rupture/)
before interpreting those results. Plasticity is described under
[nonlinear mechanics](#nonlinear-mechanics).

### Loads, constraints and mixed models

The model can define nodal forces and moments on available DOFs, gravity,
body forces, pressure and surface traction, beam line loads and shell edge
tractions. Linear dynamic routes include documented time-dependent/tabulated
and harmonic loading. Load integration and local/global-axis conventions are
family-specific; input availability does not establish follower-load or
nonlinear-dynamics support.

Fixed DOFs, linear multi-point constraints, RBE2 rigid relations, weighted
RBE3 relations, springs to ground or between nodes, and concentrated
mass/inertia definitions are available within their route contracts. Named
DOFs and local frames matter, particularly where shells/beams introduce
rotations. RBE3 availability is not a general connection qualification, and
constraint/discrete entities can cause experimental runtime classifications.

Separate bounded records cover connected, conforming, shared-node
TET4/WEDGE6/HEX8 static and modal workflows, plus selected translational-MPC
and multi-material cases. The recorded mixed Newmark/harmonic workflows
remain `EXPERIMENTAL_BOUNDED` and serial. These records do not establish
arbitrary mixed meshes, hanging-node/nonconforming interfaces, or distributed
mixed solving. The [0.2.8 workflow summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_8/)
links the separate mixed-model decisions.

## How QF Solver works

The public API and CLI validate a model, route it to an analysis-specific
driver, assemble the required contributions and return results with
route-specific diagnostics. Not every analysis assembles or uses every
contribution shown here.

```text
Model / input
     ↓
Public qf_solver API or CLI
     ↓
AnalysisRouter
     ↓
Analysis driver
     ↓
Assembly: elements · materials · loads · constraints · contact · rotating terms
     ↓
Linear / nonlinear / eigenvalue solver
     ↓
Results · diagnostics · provenance
```

Linear, dynamic, nonlinear and rotating analyses have distinct contracts and
solver routes. SciPy provides the standard numerical stack; selected large
linear workflows can use optional PETSc/MPI components. Optional packages do
not expand the validated scope by themselves. See the [architecture](https://emptiesvoid-cloud.github.io/QF_solver/architecture/)
and [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
pages for implementation boundaries and compatibility status.

### Numerical methods and backends

An analysis type, a numerical method and an assembly contribution are
different choices. Combining element contributions into `K` and `M` does not
select a solver algorithm; adding disk gyroscopy supplies a separate `G` only
for the rotating route.

| Problem | Available method family | Selection boundary |
| --- | --- | --- |
| Sparse linear system | Direct sparse solve, CG, MINRES, GMRES and BiCGSTAB; explicit or `auto` selection | Matrix symmetry/definiteness, residuals, preconditioner compatibility and resource estimates matter. Available SciPy preconditioners include Jacobi and ILU where compatible. |
| Classical modal | Generalized real symmetric `eigh`, sparse `eigsh`/Lanczos and LOBPCG routes | Mass formulation, mode count and reduction contract matter; dense conversion is bounded. These are not gyroscopic QEP methods. |
| Linear transient / harmonic | Newmark time integration and direct complex frequency-domain solves | Timestep, frequency sampling, damping and load definitions belong to the model contract. |
| Nonlinear static | Newton, modified Newton, line search and specialized continuation | Method availability and state handling remain route-dependent. |
| Rotating modal | Dense generalized QEP with `scipy.linalg.eig(A, B)` | Complex spectrum and original-QEP residual checks; serial experimental scope only. |
| Campbell | Complex-MAC global assignment over single-speed rotating solves | Tracking is separate from the eigensolver and retains unresolved ambiguity. |

Use `qf-solver methods` or the public `list_methods()` function to inspect
analysis-method choices. Residual checks and diagnostics remain necessary
even when an algorithm reports convergence. Optional PETSc/MPI and SLEPc
integration does not imply that every analysis accepts those backends; see
[solver/backend notes](https://emptiesvoid-cloud.github.io/QF_solver/solveurs/).

## Installation

Python 3.10 or newer is required. The standard installation uses NumPy,
SciPy and Matplotlib and does not require Gmsh, HDF5, MPI, PETSc or SLEPc.
The recorded CI matrix covers Linux and Windows with Python 3.10 and 3.13;
it is not a claim that every Python/OS/backend combination has been tested.

```bash
python -m pip install "qf-solver==0.2.11"
qf-solver --version
```

| Optional extra | Purpose | Boundary |
| --- | --- | --- |
| `mesh` | Gmsh mesh tooling | Requires its runtime and a supported import/setup contract. |
| `hdf5` | Family-aware mixed HDF5 result storage | Opt-in, provisional storage; not a general restart or parallel-HDF5 contract. |
| `large` | HDF5 plus MPI/PETSc bindings for large-model workflows | Native runtimes and the recorded workload scope are still required. |
| `hpc` | MPI/PETSc/SLEPc bindings | Not general distributed or rotating-QEP support. |
| `docs` | MkDocs and controlled documentation tooling | For building documentation, not running standard analyses. |

For example, `python -m pip install "qf-solver[hdf5]==0.2.11"` adds the HDF5
dependency. Native MPI/PETSc/SLEPc environments are platform-dependent;
installing an extra does not make those runtimes universally available.
Missing optional runtimes are reported rather than treated as successful
backend evidence. See the [installation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/installation/)
for environment setup.

## Quick start

The current release is 0.2.11. With the maintained example inputs available
from a matching source checkout, run a small linear static case:

```bash
qf-solver check-mesh --input examples/tet4_static.json
qf-solver solve --input examples/tet4_static.json --output results/tet4.json
```

The equivalent public Python workflow is:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
if report.status == "FAIL":
    raise RuntimeError(report.errors)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

Inspect the result fields, residuals, reactions and route-specific diagnostics
before relying on an output. The [first-calculation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
explains the workflow. New integrations should use `qf_solver`; `solveur` and
the legacy launchers remain 0.2.x compatibility paths.

### Choose a maintained starting case

| Interest | Example input or guide |
| --- | --- |
| Solid statics and loads | [`tet4_static.json`](examples/tet4_static.json), [`tet4_pressure.json`](examples/tet4_pressure.json), [`tet4_body_force.json`](examples/tet4_body_force.json) |
| Beam or shell response | [`beam2_cantilever.json`](examples/beam2_cantilever.json), [`mitc4_shell_static.json`](examples/mitc4_shell_static.json) |
| Orthotropy or laminates | [`tet4_orthotropic_static.json`](examples/tet4_orthotropic_static.json), [`mitc4_laminate_static.json`](examples/mitc4_laminate_static.json) |
| Vibration and dynamics | [`tet4_modal_unit.json`](examples/tet4_modal_unit.json), [`tet4_dynamic_tabulated_load.json`](examples/tet4_dynamic_tabulated_load.json), [`tet4_harmonic_response.json`](examples/tet4_harmonic_response.json) |
| Material/geometric nonlinearity | [`tet4_elastoplastic_static.json`](examples/tet4_elastoplastic_static.json), [small nonlinear tutorial](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/nonlinear-example/) |
| Connections and contact | [`rbe2_rigid_arm.json`](examples/rbe2_rigid_arm.json), [`frictionless_contact_surface.json`](examples/frictionless_contact_surface.json) |
| Disk gyroscopy and speed sweeps | [Rotating-modal guide](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/rotating-modal/) and [Campbell guide](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/campbell/); see their structured verification fixtures rather than assuming a standalone example JSON is shipped. |

These inputs illustrate a workflow, not a qualification for all similar
models. The nonlinear tutorial's engineering-profile `WARNING` is an
expected scope warning, not something to hide after numerical convergence.

## Analysis families

| Analysis | Orientation | Documentation |
| --- | --- | --- |
| Linear static | Small-strain structural equilibrium and reactions | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/) |
| Modal | Classical structural eigenvalue analysis | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/) |
| Transient and harmonic | Newmark time integration and linear frequency response | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) |
| Buckling | Linearized eigenvalue buckling | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/) |
| Nonlinear mechanics | Material, geometric, continuation and contact routes | [Nonlinear overview](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/nonlinear-overview/) |
| Rotating modal | Experimental disk-gyroscopic eigenanalysis | [Model and limits](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/rotating-modal/) |
| Campbell | Experimental speed sweep and explicit modal tracking | [Tracking and limits](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/campbell/) |

The [examples index](examples/README.md) groups maintained inputs by the
mechanical problem they illustrate. It also identifies controlled verification
fixtures and intentionally invalid inputs.

## Nonlinear mechanics

Nonlinear statics uses residual/tangent assembly, Newton iteration,
convergence diagnostics and trial/accepted-state transactions. Selected
routes share a composite assembly interface for material, geometric and
contact contributions. This common core is an architectural foundation, not
a qualification of every possible combination.

| Route | What is available | Evidence and limit |
| --- | --- | --- |
| Small-strain J2 | Von Mises radial-return plasticity with linear isotropic hardening and integration-point history | Bounded decisions for recorded TET4/TET10/HEX8/HEX20 element-analysis combinations; no general finite-strain plasticity. |
| Total-Lagrangian geometry | Selected St. Venant–Kirchhoff static formulations | Selected serial TET4/HEX8 audit records `GO_WITH_LIMITATIONS`, without maturity promotion; not a general high-order/contact/dynamic route. |
| Corotational J2 | Large rotations with small local material strains | Formal bounded acceptance is the HEX8 scope; not multiplicative finite-strain plasticity or blanket higher-order acceptance. |
| Material + geometry | Selected coupled static workflows across TET4/TET10/HEX8/HEX20 | Owner-accepted bounded evidence, not general frictional, dynamic or distributed coupling. |
| Normal contact | Penalty node-to-triangle contact and selected contact-state/recovery paths | Frictionless capability remains experimental and bounded, with small-sliding/search limits. |
| Tangential contact | Selected frictional stick/slip and recovery evidence | Narrow serial prior acceptance; mesh sensitivity and missing current-source formal requalification remain visible. |

Path-dependent history is evaluated in a **trial state**, then **committed**
only after acceptance. Rejected increments can **roll back** before a cutback
or retry. Selected versioned checkpoint/restart routes and state digests
support replay; they do not imply universal restart for contact, distributed
or nonlinear transient models.

Full Newton, modified Newton, line search, stagnation classification,
numerical-residual-floor handling and adaptive increments are available where
their route supports them. Specialized arc-length evidence remains
experimental and bounded; it does not establish general bifurcation or
postbuckling tracking. A numerically converged increment is not by itself a
physically valid or qualified result.

Read the [mechanics overview](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/nonlinear-overview/)
for how the core works and the [0.2.10 V&V summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_10/)
for the separate material, geometric, coupled and contact evidence.

## Rotating dynamics

QF Solver 0.2.11 provides **experimental serial gyroscopic modal analysis for
linear BEAM2 structures carrying centered rigid axisymmetric disks**, plus
experimental Campbell diagrams using explicit complex-mode tracking. This is
a bounded extension to the solver, not a general rotating-machinery solver.

The initial model is a straight circular-isotropic BEAM2 shaft with centered
rigid axisymmetric disks, constant prescribed signed spin, small perturbations,
zero damping and no centrifugal prestress. The route uses a dense serial
quadratic eigenvalue solve. Distributed shaft gyroscopy, speed-dependent
bearings, centrifugal stress stiffening, unbalance response, rotor/stator
contact, nonlinear rotors, PETSc/SLEPc and MPI are outside this scope.

At 100 rad/s, the high-frequency pair in the bounded Campbell verification
remains ambiguous. The tracker preserves that gap instead of forcing branch
continuity. GYRO-06 provides **internal mesh-convergence evidence**, not
independent physical validation. Campbell frequencies are not a forced
response, amplitude, operational-danger or validated critical-speed
prediction. Both `rotating_modal` and Campbell remain `EXPERIMENTAL`.

The single-speed equation is `M q̈ + Ω G q̇ + K q = 0`, with signed `Ω`
in rad/s and a fixed global axis. `G` is the unit-speed disk contribution;
speed is applied once. The result retains complex eigenvalues and modes,
growth rates, mass normalization, original-QEP residuals and the raw
spectrum. It does not silently convert complex modes to real ones.

Campbell supplies an explicit ordered speed sweep over the same model,
mass-weighted complex MAC, global one-to-one association, degenerate-subspace
handling, branch lineage and polarization where meaningful. Its plotting
layer cannot decide or repair tracks. The optional `1×` line denotes
`|Ω|/(2π)`; a crossing is only a frequency coincidence within this linear
modal model, not a response-amplitude or operational critical-speed result.

The dense backend was characterized up to **1,000 physical DOFs** using
synthetic matrix pencils in a recorded environment. That measured bound is
not a practical-size or timing guarantee for every rotor; cost grows steeply
and larger domains were not characterized. See the
[WP05 measurements](qualification/0_2_11/wp05_gyroscopic_report.md#dense-backend-characterization),
[rotating-modal contract](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/rotating-modal/)
and [Campbell contract](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/campbell/).

## Results, inspection and export

Outputs are analysis-specific. Depending on the route, they include
displacements and rotations, reactions, stresses/strains and invariants,
modal frequencies and shapes, transient histories, harmonic complex response,
nonlinear material states, or rotating/Campbell complex spectra and tracks.
Do not assume that a field available in one result is available in every
other analysis.

For solids, recovery can include integration-point, element and nodal fields,
principal values and von Mises stress. For shells/laminates, outputs include
membrane, bending and shear resultants, face/section values and ply stresses
in the declared axes. Interface ply stresses are not artificially averaged
across a discontinuity. Nodal averaging is not a superconvergent stress
recovery or a global error estimator; see [result conventions](https://emptiesvoid-cloud.github.io/QF_solver/conventions_resultats/).

| Tool | Purpose | Scope |
| --- | --- | --- |
| `check_mesh` / `qf-solver check-mesh` | Geometry, connectivity and boundary-condition checks | Inspect `PASS`, `WARNING` and `FAIL`, not just whether parsing succeeded. |
| `inspect_model` / `qf-solver inspect` | White-box model, DOF, matrix and consistency audit | `summary`, `diagnostic` and `values` detail levels; full-value dumps can be large. |
| `assess_result` | Non-raising run/qualification summary | Numerical status and verification-profile acceptance are separate. |
| `save_result` | Structured JSON results | Available fields and complex serialization follow the result contract. |
| `save_result_csv` / `save_result_vtu` | Result tables and visualization fields | Export support is result/family-specific, not lossless export of every analysis; VTU can be viewed in a compatible visualization tool. |
| `save_audit_markdown` | Readable model/result audit | Compact reports retain warnings/failures; detail level does not change the solve. |
| `save_evidence` / `verify_evidence` | Evidence bundle and fingerprint verification | File integrity does not automatically establish scientific qualification. |
| Mixed HDF5 APIs | Family-aware storage and selective result reads | Opt-in/provisional; no general parallel-HDF5 or restart claim. |

For a supported static example, a CLI export workflow is:

```bash
qf-solver solve --input examples/tet4_static.json --output results/tet4.json \
  --csv-dir results/tet4_csv --vtu results/tet4.vtu --audit-md results/tet4_audit.md
```

Use [audit detail modes](https://emptiesvoid-cloud.github.io/QF_solver/reference/audit_detail_modes/)
and the [public API contract](https://emptiesvoid-cloud.github.io/QF_solver/reference/qf_solver_api/)
to choose the outputs you need. The `quick`, `engineering`, `strict` and
`qualification` profiles are acceptance/evidence policies, not different
physical formulations. Tightening a profile does not promote maturity.

### Input and mesh interchange

Strict JSON is the standard model interchange. It defines nodes, elements,
materials, constraints, loads, analysis settings, units and the verification
profile. Mechanical quantities must be dimensionally consistent; declaring
units does not mean arbitrary quantities are converted automatically.

Gmsh MSH 4.1 import uses physical groups and a companion setup to assign
materials, boundary conditions and loads for supported cell families. The
mesh alone is not a complete analysis definition. Coordinate scaling and
orientation repair, where supported, must be explicit and reported.
The [Gmsh guide](https://emptiesvoid-cloud.github.io/QF_solver/reference/import_gmsh/)
describes the workflow; later mixed-family evidence has separate contracts.
The provisional `.inp` reader covers a bounded Abaqus/CalculiX subset, not
general deck or solver compatibility. Large-model HDF5/NPZ storage is a
separate workflow from standard JSON inputs and mixed HDF5 result storage.

## Larger models and performance context

Large-model tooling includes structured TET4 generation, large-model
inspection/readiness, chunked assembly or matrix-free paths, benchmark
reports, selected PETSc preconditioner comparisons and chunked
postprocessing. These are specialized workflows, not a promise that every
model supported by the small serial API can run through them.

Historical evidence records structured-TET4 workloads at approximately
1.029M, 3M, 5.01264M and 10.125M DOFs. Their source, solver settings, rank
count, hardware and acceptance limits are part of the evidence. They do not
establish a hardware-independent speed or memory guarantee, nor general
strong/weak scaling. The
[historical large-model summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_7/)
and [bounded limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
provide the workload context.

Separate two-rank PETSc/MPI evidence covers selected linear-static cases
with replicated input and root-side assembly. That is not distributed
assembly or general nonlinear/dynamic/contact MPI support. Generic mixed
distributed runtime remains `NOT_VALIDATED`. No GPU claim is made, and the
rotating QEP is dense serial rather than part of these large-model routes.

## Verification and maturity

QF Solver distinguishes implementation, a passing test, numerical
verification, external solver correlation, maturity decisions and physical
validation. These are separate kinds of evidence. The [V&V and maturity guide](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
explains the labels; the [0.2.11 verification summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_11/)
links the gyro and Campbell records.

Selected Code_Aster 18.1 results provide same-mesh **linear-static solver
correlation** for declared cases and comparable observables. This is not
experimental physical validation or general nonlinear correlation. Internal
independent recomputation of selected observables is also not a second global
FEM/Newton solve. Large-model and PETSc/MPI evidence is tied to specific
workloads and environments; it does not establish general scalability or
distributed nonlinear support.

Verification covers analytical element/material identities, equilibrium and
energy checks, regression cases, mesh/time-grid convergence within declared
studies, solver residuals and selected external comparisons. Historical
composite/solid studies also contain bounded CalculiX correlations where the
formulations and observables are comparable; these must not be generalized
to every family or route.

New execution records bind scientific inputs, referenced file bytes,
resolved configuration, oracle, tolerance policy, code and relevant
environment to an execution identity. Safe resume checks identity and
artifact integrity; structured expected failures distinguish an intended
rejection from an unrelated exception. Evidence availability remains
separate from a numerical `PASS`: some historical payloads are local-only,
reconstructed, optional or missing. Historical schemas and decisions are
preserved rather than rewritten by newer tooling.

For method-development work, the public surface also exposes benchmark and
demonstration catalogs, evidence verification and controlled V&V/campaign
tools. These advanced interfaces are generally provisional. See
[benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/),
[demonstration API](https://emptiesvoid-cloud.github.io/QF_solver/reference/demonstrations_api/)
and the [public export inventory](https://emptiesvoid-cloud.github.io/QF_solver/reference/qf_solver_api/)
for their contracts. A benchmark `PASS` is never an automatic qualification
decision.

## Limitations

- General multiplicative finite-strain plasticity, nonlinear transient
  dynamics, universal postbuckling, finite-sliding/self-contact and
  impact/contact dynamics are outside the demonstrated scope.
- Corotational J2 permits large rotations only under a small-local-strain
  assumption. Higher-order nonlinear routes are narrower than linear element
  support.
- Frictional contact remains bounded and mesh-sensitive; general updated
  search, finite sliding and self-contact are not claimed.
- Optional PETSc/MPI workflows do not establish general HPC scaling, nonlinear
  distributed solving or a validated mixed-distributed runtime.
- Composite first-ply indicators are experimental, with no progressive
  damage/delamination model or universal design-validation claim. Laminate
  and orthotropic acceptance applies only to the recorded scopes.
- MITC4 modal historical issues, discrete Newmark replays and experimental
  mixed dynamics retain their separate records; a later retest does not
  automatically promote a family. HEX8-SRI remains separately bounded;
  WEDGE15 is unsupported and PYRAMID5 is internal/research-only.
- Importers, result recovery and export schemas have explicit subsets;
  neither a valid input nor a readable visualization proves model accuracy.
- Rotating modal and Campbell are experimental and restricted to the model
  described above; the 100 rad/s high-frequency branch ambiguity remains
  visible.
- QF Solver is not certified and has no universal physical-validation claim.

See the detailed [technical limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
and the controlling evidence record for the chosen analysis.

## Current release and citation

The current QF Solver release is `0.2.11`; it follows the published `0.2.10`
release. The [What's New in 0.2.11](docs/whats-new/0.2.11.md) page summarizes
the changes, while the [changelog](CHANGELOG.md) retains the full project
history.

Use a version DOI for exact-release reproducibility when one is assigned. Use
the version DOI for the preceding release, `10.5281/zenodo.23106744`, when
citing 0.2.10. Use the project concept DOI
[`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897) to cite
QF Solver as a project. The previous release used source tag
[`v0.2.10`](https://github.com/emptiesvoid-cloud/QF_solver/tree/v0.2.10).
[`CITATION.cff`](CITATION.cff) provides machine-readable citation metadata.
The whole-repository G03 archive gate remains **FAIL**, the full repository
archive is not cleared, and WP14 remains **HOLD_NOT_PROMOTED**. Selected
distribution checks do not change those states.

## Documentation and project

- [Documentation home](https://emptiesvoid-cloud.github.io/QF_solver/)
- [Capabilities](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/),
  [elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/) and
  [analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/)
- [Public API contract](https://emptiesvoid-cloud.github.io/QF_solver/reference/qf_solver_api/)
  and [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
- [Benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/) and
  [V&V evidence](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
- [Composite mechanics](https://emptiesvoid-cloud.github.io/QF_solver/composites/),
  [nonlinear mechanics](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/nonlinear-overview/)
  and [solver/backend notes](https://emptiesvoid-cloud.github.io/QF_solver/solveurs/)
- [Contributing](CONTRIBUTING.md) · [code license](LICENSE) ·
  [documentation/examples license](LICENSE-DOCS)

The solver code is licensed under Apache-2.0; documentation and original
examples are under CC BY 4.0. Third-party terms are listed in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
