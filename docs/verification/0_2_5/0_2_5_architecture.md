---
doc_id: DOC-NL-025-003
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 target architecture

## Architectural objective

Separate element kinematics, constitutive integration, state transactions and
global nonlinear algorithms while preserving the existing linear backend.

```text
Analysis request
  -> NonlinearAnalysisOptions
  -> IncrementController / ContinuationController
  -> NonlinearDriver (Full Newton)
       -> GlobalNonlinearAssembler
            -> NonlinearElementContribution
                 -> KinematicsModel
                 -> ConstitutiveModel
                 -> IntegrationPointState
            -> ContactContribution
       -> Residual + tangent + diagnostics
       -> LinearSolverBackend
       -> ConvergencePolicy
  -> StateTransaction commit / rollback
  -> NonlinearResult
```

## Contracts to converge toward

| Contract | Responsibility | Must not own |
|---|---|---|
| `KinematicsModel` | deformation measures, strain-displacement operators and frame transformations | constitutive return mapping or global Newton |
| `ConstitutiveModel` | stress, consistent material tangent and trial state from a declared measure pair | element topology or global state commit |
| `StateTransaction` | begin trial, snapshot, commit and exact rollback for material/contact state | convergence decisions |
| `NonlinearElementContribution` | internal force, material/geometric tangent and integration-point updates | linear solver selection |
| `ContactContribution` | gap, active state, traction, residual and contact tangent | separate global nonlinear loop |
| `GlobalNonlinearAssembler` | sparse global residual/tangent assembly and metrics | constitutive formulas |
| `NonlinearDriver` | Full Newton iterations, accepted-step lifecycle and failure taxonomy | element-specific physics |
| `IncrementController` | load step, cutback, retry and growth | material-state mutation outside transaction |
| `ContinuationController` | load factor, signed target, bounded max-step window, arc-length constraint and continuation checkpoint state | FEM snap-through branch policy and external path validation |
| `ConvergencePolicy` | force, displacement and optional energy criteria | silent acceptance |
| `NonlinearResult` | inspectable increments, histories, reactions, fields and failure reason | console-only diagnostics |

Names are provisional; existing public types should be reused when they satisfy
the contract. New abstractions require a demonstrated duplication or safety
problem.

## Reuse decisions from the audit

- Keep `ConstitutiveModel`, `ConstitutiveResponse` and the J2 implementation as
  the starting constitutive core.
- Extend rather than replace `MaterialStateSession`; first measure its deep-copy
  memory cost and add contact-state support through a common transaction model.
- Keep `LinearSolverBackend` and sparse assembly ownership outside elements.
- Use `NonlinearStaticSolver` as the candidate common driver after behavior is
  frozen by tests.
- Extract reusable TET4/HEX8 Total-Lagrangian kernels from the research driver rather
  than moving its separate Newton loop into production.
- Adapt contact residual/tangent/state contributions into the common assembler;
  do not preserve an independent contact Newton engine as the final design.

## Couplings to eliminate

1. Separate Newton/convergence loops in small-strain, geometric and contact paths.
2. Contact state changes that do not participate in the common transaction.
3. Element-specific direct calls to sparse linear solvers.
4. Arc-length corrections that bypass the sparse augmented-system contract.
5. Kinematics tied directly to a J2 stress/strain measure without an explicit
   measure contract.
6. Failure reporting that exists only as an exception string or console line.

## Acceptable couplings

- An element topology may own shape functions, quadrature and B-operators.
- A kinematics implementation may define the compatible stress/strain measure
  pair required from a constitutive model.
- A contact formulation may own surface projection and local active-state rules.
- A solver backend may own factorization/preconditioner reuse, but not physics.

## Key unresolved formulation decision

The current J2 law is small-strain. It cannot be combined with arbitrary
finite-deformation Total-Lagrangian kinematics by merely reusing arrays. Before
WP6, the Owner must approve one bounded model:

1. a corotational small-strain J2 formulation with explicit applicability
   limits; or
2. a finite-strain plasticity formulation, which would materially enlarge scope
   and requires a revised plan.

Until that decision is verified, `J2 + geometric nonlinearity` remains a target,
not a supported capability.

The current working tree now contains a bounded research candidate selected by
`analysis.parameters.kinematics = "total_lagrangian_j2"` for homogeneous TET4 or
HEX8 meshes. It evaluates the existing J2 law on Green-Lagrange strain, treats
the returned stress as second Piola stress, forms `P = F S`, and assembles the
material plus geometric tangent through the common nonlinear driver. This is
an implementation experiment, not an approved finite-strain plasticity model:
G02 and G06 remain open until objectivity, energy, tangent, mesh sensitivity
and external correlation evidence are archived.

For contact, the current common-driver experiment is selected with
`analysis.parameters.contact_mode = "penalty"`. It contributes a sparse
frictionless node-to-triangle penalty residual and tangent to the same global
assembly. `contact_search_mode = "initial" | "updated"` selects whether the
local geometry is frozen or rebuilt from the current displacement. The opt-in
`contact_finite_sliding = true` mode uses the same updated search with a
bounded closest-point projection when a slave leaves the current triangle; it
remains a node-to-triangle approximation and does not claim general
surface-to-surface or friction qualification. The path does not replace the
historical exact active-set solver; general finite sliding and external
correlation remain open under G05/G10.

## Sparse and state invariants

- Global tangent and contact contributions remain sparse through assembly and
  solve; no `.toarray()` in a qualified large-system path.
- A rejected iteration or increment leaves committed material and contact state
  bitwise or numerically identical according to the state contract.
- Every accepted increment records convergence criteria and failure taxonomy.
- The existing linear path does not instantiate nonlinear state machinery.
