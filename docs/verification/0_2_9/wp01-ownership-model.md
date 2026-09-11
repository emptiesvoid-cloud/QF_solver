---
doc_id: DOC-029-WP01-002
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 ownership model

## Responsibilities

| Owner | Responsibilities | Explicit exclusions |
| --- | --- | --- |
| Authoritative nonlinear driver | Increment lifecycle, lambda, global residual/correction norms, linear solve, line search, cutback, retry, commit/rollback, terminal failure and diagnostics history | Constitutive law, contact geometry and physics-specific acceptance criteria |
| `MaterialContribution` | Material force/tangent, detached material trial state and material diagnostics | Global iteration or commit |
| `GeometricContribution` | Geometric force/tangent and declared kinematic trial metadata | Global iteration or commit |
| `ContactContribution` | Contact force/tangent, optional contact trial state, penetration/search/admissibility diagnostics | Global iteration, direct displacement commit or fallback solver selection |
| Checkpoint store | Persist/restore a fully accepted, validated state payload | Reconstruct missing state heuristically |

## Contribution response

A common contribution response must be able to carry internal force, tangent,
an optional detached trial-state update, namespaced diagnostics, a terminal
failure reason where applicable and an optional subsystem-admissibility result.
Stateless contributions are permitted and should not allocate unnecessary
history payloads.

## Convergence boundary

The driver always records free-DOF residual force norm, relative residual and
free-DOF correction norm. Energy/work is optional globally. Contact
penetration, active-set consistency, material admissibility and arc-length
constraint remain subsystem diagnostics that may veto acceptance but cannot
silently redefine a material-only global norm.

This ownership rule prevents another physics-specific global Newton API while
retaining compatibility wrappers during migration.
