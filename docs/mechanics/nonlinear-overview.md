---
title: Nonlinear mechanics overview
doc_id: DOC-MECH-NONLINEAR-001
revision: 1.0
applicable_version: 0.2.11
status: controlled_candidate
reviewer: ""
approver: ""
---

# Nonlinear mechanics overview

This page explains the nonlinear architecture retained in QF Solver 0.2.11. It is a mechanics
guide, not a verification report or a qualification decision. The
[0.2.10 V&V summary](../verification/0_2_10/README.md) explains what evidence
exists and what it does not establish.

## Assembly and Newton iteration

For a nonlinear equilibrium problem, the analysis evaluates an equilibrium
residual and a consistent route-specific tangent at the current trial state.
The Newton driver solves a correction equation, applies the selected update
policy, and evaluates convergence/stagnation diagnostics. A common composite
assembly interface can combine material, geometric, and contact contributions
where a route implements them. It does not imply that every contribution is
available for every element or analysis.

```text
Public API / CLI
  -> AnalysisRouter
  -> nonlinear analysis and driver
  -> continuation / robustness policy
  -> NonlinearStateTransaction
  -> CompositeNonlinearAssembly
       -> material response
       -> geometric response (selected routes)
       -> contact response (selected routes)
  -> residual + tangent
  -> Newton correction and convergence decision
```

The residual/tangent interface gives the driver a consistent way to request
assembly and diagnostics. Some contact active-set/recovery paths and the
arc-length correction remain specialized; this is not a claim that the
nonlinear implementation has no route-specific architecture.

## Accepted and trial state

Path-dependent analyses must not mutate the accepted history while merely
testing a Newton correction. The transaction model therefore distinguishes:

1. **Accepted state** — the last converged state and material history.
2. **Trial state** — a temporary evaluation for the current increment/iteration.
3. **Commit** — accept the trial state after the route's convergence checks.
4. **Rollback** — discard rejected trial changes before a cutback or retry.

Selected schema-v2 checkpoint routes can serialize and restore state for
restart/replay. State digests are recorded where supported to help detect
unexpected changes. The exact support depends on the route; do not infer
frictional-contact, distributed, or nonlinear-dynamics restart support from
the existence of the shared transaction primitives.

## Continuation and robustness policies

The implementation includes Full Newton, line-search support, stagnation
classification, handling for a numerical residual floor, adaptive increment
control with cutback/retry, and a specialized arc-length route. These are
robustness mechanisms, not proof that all nonlinear problems converge. The
recorded arc-length scope does not establish general bifurcation or
postbuckling tracking.

## Route boundaries

- **Small-strain J2:** use only the element-analysis combinations in the
  published 0.2.8 registry and their bounded decisions.
- **Corotational J2:** allows large rotations while retaining a small-local-
  strain assumption; the formal bounded acceptance is the documented HEX8
  route, not general finite-strain plasticity.
- **Total-Lagrangian geometry:** a St. Venant–Kirchhoff campaign was audited
  for selected static serial TET4/HEX8 cases. Its audit says
  `GO_WITH_LIMITATIONS` and explicitly records no maturity promotion.
- **Contact:** frictionless penalty contact remains experimental. Frictional
  stick/slip evidence is narrow and current-source formal requalification is
  not established.
- **Distributed execution:** recorded two-rank PETSc/MPI evidence is bounded
  to selected linear-static cases; general nonlinear distributed assembly is
  not validated.

See [known limitations](../etat/limites.md) before choosing a route.
