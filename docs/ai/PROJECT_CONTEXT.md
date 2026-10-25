# QF Solver — portable project context

**Scope:** technical summary of the repository as inspected on 2026-10-25.
**Version context:** v0.2.11 is the last published release identified by the changelog; v0.2.12 is an unreleased integration candidate.
**Authority:** orientation only; contracts, source, evidence records, and Owner decisions remain authoritative.

## What QF Solver is

QF Solver is a Python finite-element (FEM) library and analysis application for structural mechanics. It builds finite-element models, validates mesh and analysis compatibility, assembles operators, dispatches an explicitly selected analysis route, solves the resulting system, and exposes structured results and post-processing. It is a developing engineering tool, not a generally certified replacement for industrial solvers.

The implementation is organized around a public Python facade, a solveur implementation package, analysis-specific solvers, reusable mesh/element/assembly infrastructure, import and export code, and a substantial verification and qualification repository. The architecture does not imply that every element, material, and analysis combination is supported.

## Main technical areas

- **Elements and models:** solid TET4/TET10, HEX8/HEX20 and WEDGE6; BEAM2; MITC3/MITC4 shells; discrete masses, springs, and rotating disks; linear constraints and RBE2/RBE3 support. Availability is route-specific. See [capability map](CAPABILITIES.md) and [element tests](TESTING.md).
- **Materials:** isotropic and orthotropic elastic models, composite/laminate representations, and selected plasticity and geometric-nonlinearity paths. The existence of a material model does not establish that all element, loading, and analysis combinations are supported.
- **Linear analysis:** linear static, classical modal, direct frequency-domain harmonic response, and linear buckling are routed as distinct analysis types.
- **Dynamics:** the classical direct transient route uses Newmark integration. v0.2.12 also contains prepared dynamic operators, excitation channels, modal bases, reduced harmonic response, modal Newmark, uniform base acceleration, residual-flexibility work, and dynamic stress recovery. These newer paths have individual contracts and different evidence boundaries; WP-D01 remains INCONCLUSIVE and WP-D02 is CLOSED_BOUNDED in the recorded v0.2.12 roadmap.
- **Nonlinear analysis:** selected small-strain J2 plasticity, total-Lagrangian and corotational routes, nonlinear equilibrium iterations, line search/cutback controls, state transactions, and checkpoints exist. Material-point evidence is not equivalent to qualification of a complete assembled FEM route. WP-E01 remains OPEN_WITH_BOUNDED_CERTIFICATES.
- **Contact:** normal and frictional contact code and scoped verification exist. WP-C01 is CLOSED_NEGATIVE with remediation open. WP-C02 is CLOSED_BOUNDED for AR/N03 only; neither status is a general contact qualification.
- **Rotating machinery:** rotating_modal and campbell are inherited v0.2.11 experimental capabilities. They cover a bounded disk-gyroscopic BEAM2 model and explicit-speed Campbell tracking; they do not provide general rotor-dynamics qualification. Historical GYRO-01–06 results are not current-HEAD results.

## Interfaces and data

The supported Python facade is qf_solver; the solveur package remains the implementation namespace and a compatibility surface. The API exposes model loading, mesh inspection, solving, selected stress recovery, and result export. CLI entry points are declared in pyproject.toml. Input and output routes include native model data, a bounded .inp subset, Gmsh MSH 4.1 import, JSON, CSV, and VTU. Optional mixed HDF5 workflows are provisional and bounded.

Result types are heterogeneous and versioned by route. Several result classes expose to_dict; reduced harmonic and modal-Newmark results also have their own versioned decoding contracts. There is no universal result schema or generic load_result() promise. save_result refuses to overwrite by default; overwrite must be explicitly requested.

## Architecture in one view

FiniteElementModel carries mesh, material, load, constraint, and analysis settings. AnalysisRouter validates settings and compatibility, then chooses a specific solver route. Shared components include degree-of-freedom management, constraint handling, element registration, assembly, linear solver policies, result objects, IO, and post-processing. Some routes reuse common components, while others have dedicated formulation and execution paths. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPENDENCIES.md](DEPENDENCIES.md).

## Scientific evidence and version boundaries

The repository distinguishes implementation, tests, analytical or invariant checks, convergence studies, external solver comparisons, historical qualification, and bounded Owner decisions. A test file may be unexecuted. A historical PASS applies to its recorded source, manifest, environment, and scope; it does not prove the current checkout passed. Correlation with another solver is not automatically physical validation.

The v0.2.12 roadmap dated 2026-10-25 records 19 work packages: 14 positive closures, one historical negative closure, and four open. This is an administrative count, not a scientific coverage score. WP11 is CLOSED for API/integration only; WP12 and WP13 remain OPEN. The WP12-R2 runner state is RUNNER_READY_FOR_OWNER_SECURITY_REVIEW; scientific EXECUTE remains disabled. Consult the [roadmap](../../qualification/0_2_12/ROADMAP.md), [qualification guide](QUALIFICATION.md), and [WP12 preparation index](../../qualification/0_2_12/wp12_preparation/README.md) for current recorded details.

## Important boundaries

- Many capabilities are experimental, bounded, or route-specific; do not infer general applicability.
- Classical direct analyses and reduced/modal routes are distinct methods with different assumptions and result contracts.
- Contact, nonlinear materials, rotating machinery, large-model, sparse, and MPI evidence each has an explicit scope.
- No general unit-conversion system is implied. Interpret units from the model inputs and applicable contracts.
- Do not infer current validation, performance, or release readiness from this summary.

An AI can use this document to orient itself, but cannot determine from it alone whether a particular route is supported for a given model, whether a test passed on the current checkout, whether a scientific claim is qualified, or whether a campaign is authorized.

“This document is a context summary, not a substitute for checking the current source, applicable contracts and recorded evidence.”

## Ask for more context

For implementation locations start with [ARCHITECTURE.md](ARCHITECTURE.md); for actual route boundaries use [CAPABILITIES.md](CAPABILITIES.md); for the integrated v0.2.12 candidate use its [release-specific capability inventory](releases/v0.2.12.md); for formulation conventions use [MECHANICS.md](MECHANICS.md); and for a particular evidence claim use [QUALIFICATION.md](QUALIFICATION.md) and its linked release-specific records.
