---
doc_id: DOC-029-002
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 nonlinear architecture baseline

> **Planning baseline.** This is an inventory of the tracked 0.2.8 code at
> `032c8602e9bb3d7033f0fd696bf0ca7d82257e10`; it is not a maturity change.

## Existing execution paths

| Area | Current tracked seam | Baseline observation |
| --- | --- | --- |
| Common assembly composition | `core/nonlinear/iteration.py`: `NonlinearAssemblyProtocol`, `CompositeNonlinearAssembly` | A useful common composition seam already exists. |
| Small-strain nonlinear statics | `core/nonlinear/solver.py`, `load_control.py`, `assembly/nonlinear.py` | Material trial responses are assembled without mutating the committed table; load-control owns a separate Newton loop. |
| Shared full Newton | `core/nonlinear/iteration.py`: `solve_full_newton` | Used by the geometric dead-load path, with sparse solve, line search and structured diagnostics. |
| Geometric nonlinear route | `core/analyses/geometric_nonlinear.py`, `assembly/geometric.py` | Total-Lagrangian assembly for TET4/TET10/HEX8/HEX20 composes material/geometric/contact contributions through the shared protocol. It remains research-only. |
| Arc length | `core/nonlinear/arc_length.py` | Predictor/corrector, radius control and its own convergence policy live in a mixin, with material commit at accepted steps. |
| Material state | `core/nonlinear/material_state.py` | Generic `StateTransaction` and specialized `MaterialStateSession` provide useful but partially overlapping transaction abstractions. |
| Checkpoint/restart | `core/nonlinear/checkpoint.py` | Persists model signature, displacement, material state and generic continuation data; no declared contact-state payload exists. |
| Frictionless penalty contact | `contact/solver.py`: `assemble_penalty_contact` | A stateless penalty contribution supports initial/updated search and can compose in the common assembly; its bounded scope remains experimental. |
| Active-set/friction contact | `contact/solver.py`, `contact/support.py`, `contact/slip_root.py` | Separate active-set, fixed-point and semi-smooth slip loops remain independent from the common driver. |
| Coupling exercises | `verification/robustness_coupling.py` | Internal coupled geometry/contact benchmarks exist; they are not a public maturity basis by themselves. |

## Baseline architecture decision

`CompositeNonlinearAssembly` is retained as the primary contribution seam.
WP01 must create one authoritative nonlinear-driver contract around it rather
than adding another public Newton implementation. Existing residual signs are
algebraically equivalent in places (`internal - external` versus the canonical
`external - internal` form); WP01 must normalize the contract and diagnostics,
not alter physical K/F definitions to change a sign convention.

## Debt to resolve prospectively

| Classification | Item | Required treatment |
| --- | --- | --- |
| **BLOCKER** | No atomic transaction spans displacement, material history, contact history and continuation state. | Define a composable accepted-increment transaction before migration. |
| **MAJOR** | Full Newton, material load-control, arc-length and active-set/friction retain separately owned loops and convergence scales. | Make one driver contract authoritative; preserve compatibility adapters only where justified. |
| **MAJOR** | Contact state/search and friction history do not participate in the common state/checkpoint schema. | Add explicit state, digest, trial/commit/rollback and restart contracts before maturity work. |
| **MAJOR** | `total_lagrangian_j2` has no approved public finite-kinematic interpretation. | Resolve [OD-029-01](owner-decisions.md) before WP09. |
| **MINOR** | Line-search helpers and compatibility wrappers are duplicated. | Consolidate semantics in WP03 after the driver contract is frozen. |
| **MINOR** | Assembly has chunking/counters but no frozen nonlinear performance characterization contract. | Cover in WP13; do not optimize before measured bottlenecks exist. |
| **ACCEPTABLE** | Immutable nonlinear assembly plans are separated from trial material history. | Retain as a foundation. |

## Safety properties to preserve

- Assembly returns trial material state rather than mutating committed state.
- A rejected increment must retain the previous accepted displacement and all
  declared state families.
- The frictionless penalty path must not silently become a frictional,
  finite-sliding, or general surface-to-surface capability.
- Legacy active-set/friction routines may remain compatibility/research paths
  until their state and diagnostics can be adapted safely.
