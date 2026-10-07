---
doc_id: DOC-ARCH-001
revision: 3.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# QF Solver architecture

This page describes the QF Solver 0.2.11 architecture. Architecture diagrams describe implementation
boundaries; they do not establish capability maturity. See the
[capability index](capabilities/index.md) and [0.2.11 V&V summary](verification/0_2_11/README.md)
for evidence and scope.

## Public entry points and routing

New Python integrations should use the `qf_solver` namespace. The `solveur`
namespace remains the implementation and a compatibility facade for existing
0.2.x applications. The recommended command is `qf-solver`; legacy launchers
remain available during the 0.2.x compatibility period.

```text
qf_solver public API / qf-solver CLI
                  |
                  v
             AnalysisRouter
              /         \
       linear routes   nonlinear routes
           |                 |
           +------ assembly -+
                    |
     elements / materials / loads / contact
                    |
       SciPy default; PETSc/SLEPc optional
```

The CLI validates and translates input, calls the API, and writes result
artifacts. It is not the location of finite-element formulations. Core
calculation modules do not own command-line parsing or output serialization.

Rotating modal and Campbell are additional analysis routes, not alternative
implementations of classical modal analysis. They use the existing public
model workflow with separate input and result contracts.

## Rotating analysis flow

```text
campbell request + explicit ordered speeds
  -> fixed model / disk / tracking policy
  -> rotating_modal at each signed speed
       -> fail-closed BEAM2/disk input validation
       -> structural K/M + disk mass + unit-speed G
       -> common fixed-DOF reduction
       -> scaled dense generalized QEP
       -> RotatingModalResult (raw complex spectrum + residuals)
  -> modal_tracking (complex MAC / global assignment / subspaces)
  -> CampbellResult (lineage / scores / ambiguity / provenance)
  -> post/campbell (projection only; cannot assign tracks)
```

The responsibilities are implemented separately in
`solveur.core.analyses.rotating_modal`, `qep`, `modal_tracking`, `campbell`
and `solveur.post.campbell`. Campbell varies speed, not model properties or
`K/M/G`. Gyroscopic assembly is not activated for legacy analyses. These
internal modules are not stable public API. Both rotating capabilities
remain `EXPERIMENTAL`, serial and bounded; PETSc/SLEPc/MPI, distributed
shaft gyroscopy and speed-dependent physics are not enabled by this graph.

## Nonlinear analysis flow

Several bounded nonlinear routes share a driver foundation, Newton engine,
continuation/robustness policies, state transaction primitives, and a
residual/tangent assembly interface:

```text
Nonlinear analysis request
  -> nonlinear driver foundation
  -> continuation / robustness policy
  -> NonlinearStateTransaction
  -> CompositeNonlinearAssembly
       + material contribution
       + geometric contribution (selected routes)
       + contact contribution (route-dependent)
  -> residual + tangent
  -> UnifiedNewtonEngine
  -> convergence decision
       + accept / commit
       + reject / rollback / retry
```

The shared lifecycle provides a common integration point; it does not mean
all physics are composed in every route. Some contact active-set and recovery
loops remain specialized, and arc-length correction remains route-specific.
The state transaction separates accepted history from trial updates so a
rejected iteration can be rolled back before retry. Selected schema-v2
checkpoints support restart/replay; support is not universal across contact,
distributed, and nonlinear transient routes.

Relevant internal implementation modules include
`solveur.core.analyses.AnalysisRouter`, `solveur.core.nonlinear.driver`,
`solveur.core.nonlinear.state`, `solveur.core.nonlinear.iteration`, and
`solveur.core.nonlinear.robustness`. These internal names are explanatory,
not a promise that they are stable Python API.

## Package layers

```text
src/qf_solver/              public facade and version metadata
src/solveur/api/             API implementation and compatibility adapters
src/solveur/cli/             command parsing and orchestration
src/solveur/core/            analyses, routing, assembly and solver policies
src/solveur/elements/        element formulations
src/solveur/materials/       constitutive models, including J2 routes
src/solveur/contact/         route-specific contact implementation
src/solveur/mesh/loads/post/ validation, input mechanics and result processing
src/solveur/large/           bounded optional large-model routes
src/solveur/verification/    reproducible checks and evidence tooling
docs/                       public and engineering documentation sources
qualification/              scoped records, contracts and decisions
tests/                       unit, integration, documentation and V&V tests
```

The package layout keeps the public facade separate from implementation
modules. Optional PETSc/SLEPc integrations are loaded only when selected; the
standard runtime path uses SciPy and does not require Docker, PETSc or MPI.

## Backends and evidence boundaries

PETSc/MPI evidence accepted for 0.2.10 is bounded to recorded two-rank
linear-static one-element cases with replicated input and root-side assembly.
It does not establish distributed assembly, scaling, general nonlinear MPI,
contact, or dynamics. Historical structured-TET4 large-model observations
apply only to their recorded workload and environment.

Bounded nonlinear routes include selected small-strain and corotational J2,
Total-Lagrangian geometry, contact and continuation paths. Their exact
formulations and maturity differ. In particular, the geometric audit is
`GO_WITH_LIMITATIONS` without maturity promotion; corotational J2 has a
bounded HEX8 acceptance with small local strains; frictional contact
requalification against current source is not established. See
[known limitations](etat/limites.md).

## Documentation and evidence pipeline

```text
examples + API + evidence + benchmarks
  -> documentation model/assets builders
  -> generated tables and figures
  -> publication/status generator
  -> Markdown sources and optional PDF output
```

`python scripts/build_docs.py --profile engineering` builds the engineering
documentation and exposes an uncommitted tree as such. The `qualification`
profile has stricter source and page-status requirements. Generated
measurements are not manually transcribed as new qualification decisions.
The MkDocs site intentionally excludes the detailed `verification/0_2_9`
engineering archive from public navigation; concise 0.2.10 and 0.2.11 summaries
are served separately. Prospective execution identities, content hashes,
safe resume, structured expected failures and evidence availability are
documented in the [0.2.11 provenance summary](verification/0_2_11/README.md).
Numerical results and maturity decisions remain separate.

## Known architectural debt

The common nonlinear interfaces coexist with route-specific implementation
and specialized recovery code. That is current architectural debt, not a
reason to infer unsupported combinations or hide limitations. The docs do not
claim a general-purpose nonlinear framework, certified solver, or universal
HPC support.
