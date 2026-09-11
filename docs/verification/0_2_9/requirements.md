---
doc_id: DOC-029-003
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 nonlinear requirements

## Common architecture requirements

1. One public driver contract owns Newton iteration, convergence reporting,
   line search, increment acceptance, cutback/retry and failure diagnostics.
2. Material, geometric and contact components contribute through a shared
   residual/tangent interface.
3. Trial state is committed only at an accepted increment. Failure, rejected
   cutback and invalid restart roll back every participating mutable state.
4. Checkpoints are versioned and validate all declared state payloads before
   restart.
5. Every capability promotion has a prospective contract with frozen gates,
   evidence, failure cases, replay and a bounded scope.

## Mechanical gate themes

### Geometric nonlinear work

Rigid-body objectivity; small-displacement recovery; tangent finite-difference
agreement; residual convergence; reactions/equilibrium; energy/work
consistency; increment and mesh refinement; large rotations; `det(F)`
monitoring; controlled failures; and external correlation.

### Contact work

Open/contact, separation and recontact transitions; updated search and facet
transitions; penetration and penalty sensitivity; reaction equilibrium; mesh
sensitivity; finite sliding only where explicitly claimed; tangent consistency;
and state rollback.

### Friction work

Stick, slip, stick-to-slip, supported reversals, Coulomb cone,
non-negative dissipation, state commit/rollback and load-step sensitivity.

Numerical values, norm definitions and pass/fail thresholds are deliberately
not selected in this plan. They must be frozen before each prospective campaign
and may not be relaxed after observation.
