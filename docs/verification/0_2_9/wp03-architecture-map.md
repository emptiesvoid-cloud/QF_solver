---
doc_id: DOC-029-WP03-002
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03-A — current robustness architecture map

> **Read-only inventory.** This map describes the implementation at
> ecc09f0bae2dab867c12d7e471860887f6ef0548. It is not evidence that future
> WP03 gates already pass.

## Authority map

~~~
public fixed Newton entry points
  solve_full_newton
    -> UnifiedNewtonEngine
  NonlinearLoadControlMixin._solve_load_step
    -> UnifiedNewtonEngine
  GeometricNonlinearStaticSolver fixed path
    -> solve_full_newton
    -> UnifiedNewtonEngine

public adaptive entry points
  solve_adaptive_full_newton
    -> UnifiedContinuationController
    -> UnifiedNewtonEngine per attempt
  NonlinearLoadControlMixin._solve_adaptive_load_steps
    -> UnifiedContinuationController
    -> UnifiedNewtonEngine per attempt

public arc-length entry point
  NonlinearArcLengthMixin._solve_arc_length
    -> UnifiedContinuationController
    -> specialized solve_arc_length_correction
    -> arc radius policy

all migrated accepted-state publication
  NonlinearStateTransaction
    -> accepted composite state / rollback / deterministic digest
~~~

The target is one robustness/policy authority above these route-specific
correction kernels, not one algebraic correction equation for every route.

## Current public authority classification

| Area | Actual owner | Current classification | WP03 treatment |
| --- | --- | --- | --- |
| Fixed Newton lifecycle | UnifiedNewtonEngine | Public authority | Retain and make robustness policy explicit |
| Compatibility fixed entry | solve_full_newton | Public adapter | Delegate; no second loop |
| Accepted state | UnifiedContinuationController + NonlinearStateTransaction | Public state authority | Preserve |
| Stateful adaptive load control | _solve_adaptive_load_steps | Public policy surface | Consolidate in WP03-C |
| Stateless/geometric adaptive route | solve_adaptive_full_newton | Public policy surface | Consolidate in WP03-C |
| Arc correction | solve_arc_length_correction | Specialized public kernel | Retain; common lifecycle only |
| Arc radius adaptation | _solve_arc_length | Specialized continuation policy | Normalize diagnostics in WP03-D |
| Experimental solve/scaling controls | NonlinearRobustnessOptions | Explicit opt-in R&D | Keep experimental |
| Frictionless penalty contribution | assemble_penalty_contact | Bounded composition | Preserve scope |
| Active-set/friction/slip loops | contact solver/support/slip-root | Research/compatibility | Isolate; do not promote |

## Duplicate or competing policy surfaces

These are contract debt to resolve prospectively, not defects to hide by
changing a threshold:

1. Line-search helpers overlap:
   _line_search_assembly_with_diagnostics, line_search_factor and the
   geometric wrapper. WP03-B must define one authoritative dispatch and keep
   wrappers delegating.
2. Adaptive load policy exists in both solve_adaptive_full_newton and
   _solve_adaptive_load_steps. WP03-C must consolidate cutback/growth and
   terminal semantics while preserving route compatibility.
3. Arc-length has its own radius growth/shrink policy. This is an acceptable
   mathematical specialization, but it must publish through common retry and
   diagnostics contracts.
4. NonlinearRobustnessOptions can select experimental linear and
   line-search behavior. It must remain explicit opt-in and cannot silently
   redefine the public default.

No item above is a second accepted-state authority in the WP01/WP02 sense.
The contract phase records them so WP03 implementation can test and close
the policy boundary rather than claiming that the surfaces are already one.

## State and failure boundary

Contributions return force, tangent, trial-state response, diagnostics and
admissibility/failure information. They do not commit the global accepted
state. The transaction/controller owns acceptance and rollback. The
canonical failure/retry mapping is in
[the WP03 failure matrix](wp03-failure-retry-matrix.md).

Checkpoint persistence is governed by the WP02 accepted-state boundary. A
robustness failure may trigger a physical retry only when the failure matrix
allows it; a checkpoint failure remains an infrastructure failure.

## Research boundary

NonlinearStaticSolver rejects frictional contacts for the common nonlinear
route and requires frictionless penalty contact where contact is used. The
active-set/friction/slip-root implementation remains an isolated
linear-static/research compatibility family. No WP03 record treats it as a
public common robustness authority.
