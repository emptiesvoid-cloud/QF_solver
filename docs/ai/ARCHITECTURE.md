# Software architecture map

**Scope:** source organization and route boundaries observed in the v0.2.12 repository.
**Revision:** 2026-10-25.
This is a navigation document, not an API guarantee.

## Package and public boundary

- [src/qf_solver/](../../src/qf_solver/__init__.py) provides the supported public facade and re-exports the API.
- [src/solveur/api/public.py](../../src/solveur/api/public.py) implements public application functions.
- src/solveur/ contains the implementation package, compatibility API, and internal modules.
- [src/solveur/core/model.py](../../src/solveur/core/model.py) defines the finite-element model; [analysis settings](../../src/solveur/core/analyses/settings.py) interprets analysis settings.
- CLI entry points are configured in pyproject.toml; primary command and legacy compatibility commands are separate entry points.

Use the documented facade for client code. Internal module paths are useful for repository work but are not automatically stable public API. Consult [API stability](../reference/api_stability.md) before changing externally visible behavior.

## Major layers

| Layer | Main location | Responsibility |
|---|---|---|
| Model and settings | [model.py](../../src/solveur/core/model.py), [settings.py](../../src/solveur/core/analyses/settings.py) | Model state and requested analysis parameters |
| Mesh and elements | [mesh](../../src/solveur/mesh/validation.py), [elements](../../src/solveur/elements/) | Mesh validation, element definitions and element-level operators |
| DOFs and constraints | [dofs.py](../../src/solveur/core/dofs.py), [constraints.py](../../src/solveur/core/constraints.py), [rbe.py](../../src/solveur/core/rbe.py) | Global degree-of-freedom mapping and constraint representations |
| Assembly | [assembly](../../src/solveur/core/assembly/assembler.py) | Global stiffness/mass and route-specific contributions |
| Compatibility preflight | [compatibility](../../src/solveur/compatibility/) | Reject unsupported model/route combinations before solving |
| Analysis dispatch | [router.py](../../src/solveur/core/router.py), [analyses](../../src/solveur/core/analyses/) | Explicit route selection and analysis-specific solvers |
| Linear solvers | [solvers](../../src/solveur/core/solvers/) | Backend and solver policy used by applicable routes |
| Results and post-processing | [results.py](../../src/solveur/core/results.py), [post](../../src/solveur/post/) | Route-specific result objects and derived fields |
| IO and checkpoints | [IO](../../src/solveur/io/) | Model/result serialization and restart/checkpoint formats |
| Verification infrastructure | [verification](../../src/solveur/verification/), [scripts](../../scripts/), [qualification](../../qualification/) | Verification tools, campaign controls, manifests and recorded evidence |

The table gives orientation. Inspect each implementation and contract before treating a layer boundary as universal.

## Representative execution flows

### Public solve

Application code calls qf_solver.solve_model or the compatibility API. The API resolves a model, then [AnalysisRouter](../../src/solveur/core/router.py) validates analysis settings, enforces selected cross-route restrictions, runs compatibility preflight, and dispatches to a dedicated solver. The solver may call mesh validation, DOF construction, shared or specialized assembly, backend policy, and result construction.

### Classical and reduced dynamics

[AnalysisRouter](../../src/solveur/core/router.py) dispatches harmonic_response to direct frequency response unless the explicit method is modal_superposition. transient_dynamic dispatches to direct Newmark unless the method is modal_newmark. These paths share some dynamic utilities but differ in their reduced operators, bases, output contracts, and post-processing.

### Rotating analysis

rotating_modal and campbell are separate routed analyses. They use [rotating-modal](../../src/solveur/core/analyses/rotating_modal.py), [gyro assembly](../../src/solveur/core/assembly/rotating_disk_gyro.py), [QEP](../../src/solveur/core/analyses/qep.py), and [Campbell tracking](../../src/solveur/core/analyses/campbell.py) components. Their accepted model restrictions are documented by the v0.2.11 contracts; they should not be described as ordinary modal analysis with a generic rotational option.

### Nonlinear analysis

Nonlinear routes assemble/update state through nonlinear solver and material interfaces. Constitutive state, tangent evaluation, global equilibrium, line-search/cutback behavior, and checkpoints are related but separate concerns. Point-material checks do not exercise the entire assembled solve path.

## Optional backends

SciPy is used for applicable sparse and complex linear-algebra routes. PETSc/MPI support is route- and configuration-specific; repository evidence for a selected large linear-static path must not be generalized to all analyses or distributed execution. Read the selected route, backend policy, and qualification record together.

## Navigation and dependency map

For feature entry points see [CAPABILITIES.md](CAPABILITIES.md); for change impact see [DEPENDENCIES.md](DEPENDENCIES.md); for source-first editing see [DEVELOPMENT.md](DEVELOPMENT.md). Normative input, refusal, and result behavior belongs to the relevant contract and API reference.
