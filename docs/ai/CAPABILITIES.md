# QF Solver capability map

**Scope:** repository capability navigation, including the v0.2.12 integration candidate.
**Reviewed:** 2026-10-25.
**Not a release approval:** v0.2.11 is the last published release; v0.2.12 is an unreleased candidate.

For the release-specific inventory of v0.2.12 additions, boundaries, dispositions, and evidence, read [releases/v0.2.12.md](releases/v0.2.12.md). This page provides the cross-release map to source and the distinctions needed to interpret it.

## Read capability and evidence labels separately

- **Implemented** means source code, an API/CLI route, or a registered component exists.
- **Route-declared** means compatibility preflight or an analysis setting declares a technical route. It does not mean every material, load, or model combination works.
- **Test available** means a test file is present. It does not prove it has run on the checkout being inspected.
- **Evidence reported** means a report records a result on its named source, model, manifest, environment, and scope.
- **Maturity/decision** is the recorded disposition for a bounded scope. It does not transfer to adjacent configurations.

The [element descriptors](../../src/solveur/compatibility/descriptors.py) and [element registry](../../src/solveur/elements/registry.py) are technical implementation maps, not qualification registries. Read them with the [v0.2.12 roadmap](../../qualification/0_2_12/ROADMAP.md), relevant contracts, and the [qualification guide](QUALIFICATION.md). Do not form a supported Cartesian product from independent element, material, and analysis lists.

## Element and formulation families

| Family | Implemented model | Route declaration and important limits | Source and test entry points |
|---|---|---|---|
| TET4 | Four-node constant-strain solid; consistent mass and Gauss-point stress recovery | Descriptor declares linear static, modal, direct transient, harmonic, linear buckling, nonlinear static, and geometric nonlinear routes. Material and load availability remain route-specific. | [element source](../../src/solveur/elements/solid/tet4.py), [descriptor](../../src/solveur/compatibility/descriptors.py), [test](../../tests/unit/test_tet4_element.py) |
| TET10 | Ten-node quadratic solid; consistent mass and Gauss-point stress recovery | Same broad descriptor route family as TET4, with separate geometry, integration, material, and stress restrictions. | [element source](../../src/solveur/elements/solid/tet10.py), [test](../../tests/unit/test_tet10_element.py) |
| HEX8 | Eight-node trilinear solid; standard full integration plus a separate SRI implementation | Descriptor declares linear, modal, transient, harmonic, buckling, nonlinear-static, and geometric-nonlinear routes. The existence of SRI code or a test is not universal qualification. | [element source](../../src/solveur/elements/solid/hex8.py), [SRI source](../../src/solveur/elements/solid/hex8_sri.py), [test](../../tests/unit/test_hex8_element.py) |
| HEX20 | Twenty-node quadratic solid with separate geometry and integration checks | Broad solid route declaration is subject to compatibility, material, and qualification scope. | [element source](../../src/solveur/elements/solid/hex20.py), [test](../../tests/unit/test_hex20_element.py) |
| WEDGE6 | Six-node linear triangular prism; isotropic 3D material declaration and consistent mass | Static and modal support have dedicated scope. Transient/Newmark and harmonic entries are marked experimental internal candidates in the descriptor and require separate V&V/Owner gates; J2, total-Lagrangian, contact, external correlation, and robustness are deferred. | [element source](../../src/solveur/elements/solid/wedge6.py), [kernel test](../../tests/unit/test_wedge6_kernel.py), [capability descriptor](../../src/solveur/compatibility/descriptors.py) |
| BEAM2 | Two-node Timoshenko beam with UX/UY/UZ/RX/RY/RZ DOFs and beam resultants | Isotropic beam material; descriptor declares static, modal, transient, harmonic, rotating-modal, and Campbell routes. Nonlinear beam routes are not declared. | [element source](../../src/solveur/elements/beam/beam2.py), [test](../../tests/unit/test_beam2_element.py) |
| MITC3 | Three-node assumed-strain triangular shell | Descriptor declares static, modal, transient, and harmonic routes; shell stress/resultants and laminate/material axes are formulation-specific. No nonlinear shell route is declared. | [element source](../../src/solveur/elements/shell/mitc3.py), [test](../../tests/unit/test_mitc3_element.py) |
| MITC4 | Four-node assumed-strain quadrilateral shell | Descriptor declares static, modal, transient, and harmonic routes; mesh quality, local frames, laminate conventions, and stress/resultants matter. No nonlinear shell route is declared. | [element source](../../src/solveur/elements/shell/mitc4/element.py), [dynamics test](../../tests/unit/test_mitc4_dynamics.py) |
| Discrete entities | Concentrated masses, springs, and rotating rigid disks | Mass/spring entities participate in declared linear routes. RotatingDisk is accepted only for rotating_modal and campbell; it is not a generic mass option. | [entity definitions](../../src/solveur/elements/discrete.py), [router refusals](../../src/solveur/core/router.py), [gyro test](../../tests/unit/test_rotating_disk_gyro.py) |
| PYRAMID5 | Five-node collapsed-coordinate small-strain isotropic linear-elastic kernel is present and listed in ElementRegistry | It has no matching compatibility descriptor in the current descriptor table. Treat it as an internal bounded feasibility kernel, not as a generally supported public analysis route or a modal/dynamic capability. | [element source](../../src/solveur/elements/solid/pyramid5.py), [registry](../../src/solveur/elements/registry.py) |

The descriptor also distinguishes load categories: nodal loads, gravity/body force, solid pressure and surface traction, shell edge traction, and beam line load. These declarations do not make every load available on every route.

## Material families

The JSON/API `MaterialFactory` accepts `beam_isotropic`, `isotropic_3d`, `orthotropic_3d`, `composite_orthotropic_3d`, `nonlinear_isotropic_3d`, `von_mises_elastoplastic_3d`, `shell_isotropic`, `orthotropic_lamina`, and `shell_laminate`. Element compatibility and analysis preflight restrict which combinations may be assembled; this list is not a support matrix.

Source-level material capabilities include:

- **Elastic solids:** isotropic, orthotropic, and provenance/homogenization-tagged composite-orthotropic records; orthotropic orientation and optional cylindrical-tangent orientation fields.
- **Shells and laminates:** isotropic shell material, orthotropic lamina data, classical laminate stacks, layer stress/recovery and first-ply indicators.
- **Beams:** isotropic Timoshenko beam section material.
- **Small-strain nonlinear solids:** nonlinear isotropic material and von Mises/J2 elastoplasticity with radial return and isotropic hardening; the corrected corotational J2 path is selected explicitly and remains bounded/experimental.
- **Geometric nonlinear solids:** total-Lagrangian StVK and selected corotational element routes, distinct from the standalone finite-strain material-point kernels below.
- **Experimental finite-strain material-point kernels:** internal `StVenantKirchhoff` and `CompressibleNeoHookean` evaluations return energy, strain, PK2/PK1/Cauchy stress and tangents. They are not JSON `MaterialFactory` types or a general assembled route.
- **Experimental Hencky code:** Hencky kinematics and material-point response, TET4/HEX8 deformation-gradient helpers and force-only element adapters, plus a directional material-point tangent. The force adapters have no element tangent/global assembly/Newton integration. WP-E01 remains OPEN_WITH_BOUNDED_CERTIFICATES; general production material-factory/assembly support is not established.
- **Finite-kinematic J2 research path:** the identifier is marked NOT_QUALIFIED by compatibility preflight and appears in a bounded verification benchmark; it is not a generally qualified JSON material/analysis route.
- **Composite failure indicators:** maximum stress, optional maximum strain, Tsai-Hill and Tsai-Wu first-ply indicators in laminate material axes. They do not degrade material state and do not implement progressive damage.

See [material factory](../../src/solveur/materials/factory.py), [materials](../../src/solveur/materials/), [compatibility descriptors](../../src/solveur/compatibility/descriptors.py), [composite failure implementation](../../src/solveur/materials/failure.py), [finite-strain material tests](../../tests/unit/test_wp_e01c_finite_strain_material.py), [Hencky tests](../../tests/unit/test_wp_e01m_hencky_material_point.py), [first-ply indicator tests](../../tests/unit/test_composite_failure.py), [nonlinear mechanics overview](../mechanics/nonlinear-overview.md), and the release-specific records in [v0.2.12](releases/v0.2.12.md). A material class being constructible does not prove its compatibility with every element or analysis.

## Analysis routes

The router selects an explicit analysis family and method. The current settings table is in [analysis settings](../../src/solveur/core/analyses/settings.py); the actual dispatch and cross-route refusals are in [AnalysisRouter](../../src/solveur/core/router.py).

| Analysis family | Methods declared in settings | Implementation entry point | Scope cue |
|---|---|---|---|
| Linear static | auto, direct, spsolve, cg, conjugate_gradient, gmres, bicgstab, minres | [static solver](../../src/solveur/core/solvers/static.py) | Backend, constraints, loads, element/material combination govern applicability. |
| Modal | eigh, eigsh, lanczos, lobpcg | [modal solver](../../src/solveur/core/analyses/modal.py) | Classical generalized eigenproblem; route-specific mass and normalization semantics. |
| Nonlinear static | newton_raphson, modified_newton, newton_line_search, arc_length | [nonlinear solver](../../src/solveur/core/nonlinear/solver.py) | Method and formulation maturity vary; convergence is not guaranteed for arbitrary models. |
| Geometric nonlinear static | newton_raphson | [geometric nonlinear solver](../../src/solveur/core/analyses/geometric_nonlinear.py) | Selected total-Lagrangian/corotational domains; not a general large-deformation framework. |
| Linear buckling | eigsh | [buckling solver](../../src/solveur/core/analyses/buckling.py) | Linearized eigenvalue buckling; not general post-buckling. |
| Transient dynamic | newmark, newmark_average_acceleration, modal_newmark | [direct Newmark](../../src/solveur/core/analyses/dynamic.py), [modal Newmark](../../src/solveur/core/analyses/modal_newmark.py) | Full-order and reduced/modal state spaces are separate routes. |
| Harmonic response | direct_frequency, harmonic_direct, modal_superposition | [direct harmonic](../../src/solveur/core/analyses/harmonic.py), [reduced harmonic](../../src/solveur/core/analyses/reduced_harmonic.py) | Complex frequency response; direct and reduced routes have separate assumptions and result contracts. |
| Rotating modal | dense_qep | [rotating modal](../../src/solveur/core/analyses/rotating_modal.py) | Inherited v0.2.11 EXPERIMENTAL route; bounded rotating-disk BEAM2 model. |
| Campbell | complex_mac_hungarian | [Campbell](../../src/solveur/core/analyses/campbell.py) | Inherited v0.2.11 EXPERIMENTAL explicit-speed sweep; ambiguity is retained. |

Backend choice is separate from the method string. SciPy sparse/dense solvers serve the ordinary routes; optional PETSc linear solves and a SLEPc modal path are available only on selected configurations and size envelopes. Direct complex harmonic response explicitly refuses PETSc. The inherited rotor QEP is dense/serial and has no sparse PETSc/SLEPc route. Additional PETSc/SLEPc TET4 modal and Newmark functions exist in `solveur.large.dynamic`, but are not exported by the large-model package or the public API/CLI; treat them as internal implementation code, not a supported large-model workflow.

Contact is composed into the nonlinear/contact model path rather than exposed as a universal new top-level analysis family. The API may also expose specialized large-model and V&V operations outside AnalysisRouter.

## Constraints and contact

- Linear MPC reduction, RBE2 rigid-arm constraints, and two RBE3 modes are present in source and the public model/API definitions. Their bounded decisions are in a separate historical RBE integration stream named `WP13-RBE`; this is not the current operational v0.2.12 WP13, which is release engineering and publication. See [RBE source](../../src/solveur/core/rbe.py), [constraint reduction](../../src/solveur/core/constraints.py), the [RBE decision](../../qualification/0_2_12/wp13_rbe_owner_maturity_decision.json), and the [WP-numbering map](QUALIFICATION.md#release-specific-work-package-identities).
- Normal/frictionless and frictional contact components, search/evaluation and restart state exist. C01 remains CLOSED_NEGATIVE with remediation open. C02 is CLOSED_BOUNDED for AR/N03 only. Neither result qualifies general contact, arbitrary finite sliding, or arbitrary mesh/search configurations.
- Read [contact source](../../src/solveur/contact/), [C01 status](../../qualification/0_2_12/wp_c01_r19_status_register.json), [C02 Owner decision](../../qualification/0_2_12/wp_c02_n13_owner_bounded_closure_decision.md), and [roadmap](../../qualification/0_2_12/ROADMAP.md).

## Python API, CLI, results, and data

The public facade is [qf_solver](../../src/qf_solver/__init__.py); its implementation and exported functions are in [solveur.api.public](../../src/solveur/api/public.py). The [versioned API contract](../reference/qf_solver_api.md) inventories all public symbols and stability categories. The WP11 assessment records the candidate API inventory and its targeted contract coverage; API stability is not scientific qualification.

The public surface supports:

- **Model creation and inspection:** JSON model load/save, Gmsh MSH 4.1 plus companion setup import, bounded Abaqus/CalculiX INP subset, mesh quality validation, model audit, and method listing.
- **Solve and result handling:** solve an explicitly selected route; result assessment; JSON result saving; selected static-result CSV/VTU exports; audit Markdown; evidence-bundle writing and verification.
- **Post-processing:** solid recovery, shell/laminate result fields and first-ply indicators, Campbell plotting, plus the three WP-D02 wrappers for full-order solid, selected harmonic, and selected modal-transient stress recovery. WP-D02 wrappers are provisional and bounded; see the [v0.2.12 inventory](releases/v0.2.12.md).
- **V&V and demonstrations:** controlled benchmark and demonstration catalogs, study import/comparison, linear solver/contact/MITC4 checks, structured TET4 studies, release V&V readiness and manifest-based qualification APIs. These are tools that can execute work; their existence is not authorization to run it.
- **Results:** ordinary SolveResult, ModalResult, DynamicResult, and HarmonicResult are heterogeneous DTOs. Reduced harmonic, modal Newmark, and other scoped outputs carry separate schemas. There is no universal result schema or generic result loader. save_result refuses replacement unless overwrite is explicitly enabled.
- **Mixed HDF5:** experimental/provisional family-aware result storage and selection for schema v1.0 TET4/WEDGE6/HEX8 only; semantic digest support does not imply a universal result format.

The main CLI command groups include solve/check/inspect, evidence, Gmsh mesh import, benchmark/V&V, large-model operations, selected mechanical verification, qualification readiness/manifest operations, release-V&V readiness, and method listing. The registered commands and exact flags are in [src/solveur/cli/main.py](../../src/solveur/cli/main.py). Legacy solveur-ef and mitc4-solver entry points remain in pyproject.toml; the API stability reference identifies their compatibility status.

## Large-model and optional HPC capabilities

The public specialized large-model API is primarily a structured/partitioned TET4 linear-static path. It includes HDF5/NPZ model storage, model conversion and inspection, structured block/cantilever generators, solving, bounded-memory chunked post-processing with checkpoints, runtime/readiness reports, benchmark campaigns, scaling analysis, PETSc profile/tuning analysis, and qualification verification. Internal PETSc/SLEPc modal/Newmark helpers are not exported as public large-model or CLI routes.

Optional dependency groups include HDF5, large-model PETSc/MPI, and broader HPC/SLEPc dependencies. Runtime availability and supported route are separate: PETSc/MPI does not apply to all analyses, and the evidence recorded for selected linear-static workloads does not prove general scaling, nonlinear distribution, or general MPI support. See [large-model implementation](../../src/solveur/large/), [public API contract](../reference/qf_solver_api.md), and [capability index](../capabilities/index.md).

## Verification entry points

Unit, integration, verification, and qualification artifacts are separated under tests and qualification. Tests cover element kernels, algebraic identities, selected analytic references, mesh/time refinement, external comparisons, API/IO contracts, and refusals. A test path is not a run result. Historical campaign evidence is source- and manifest-bound. See [TESTING.md](TESTING.md), [QUALIFICATION.md](QUALIFICATION.md), and the detailed [v0.2.12 release inventory](releases/v0.2.12.md).

## Inherited rotating capabilities

Rotating modal and Campbell were introduced in v0.2.11 and remain EXPERIMENTAL. Their historical GYRO-01–06 reports are not tests on a current v0.2.12 HEAD. They use a bounded disk-gyroscopic BEAM2 model, dense QEP and explicit signed-speed Campbell tracking; distributed shaft gyros, forced unbalance response, speed-dependent bearings, general rotor damping, centrifugal prestress, sparse QEP, and general rotating-machine qualification are outside scope. See the [rotating-modal guide](../mechanics/rotating-modal.md), [Campbell guide](../mechanics/campbell.md), and [v0.2.12 inventory](releases/v0.2.12.md).
