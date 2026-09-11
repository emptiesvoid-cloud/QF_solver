---
doc_id: DOC-029-WP03-006
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03 implementation decomposition

The machine-readable decomposition is
qualification/0_2_9/wp03_implementation_decomposition.json.

| Phase | Status | Scope |
| --- | --- | --- |
| WP03-A — contract | **CONTRACT_PHASE** | Inventory authorities, freeze equations, convergence/stagnation/line-search/retry contracts, baseline campaign and gates. |
| WP03-B — stagnation and line-search authority | **Implemented — targeted** | One deterministic policy/dispatch and delegating compatibility wrappers; 0/7 points pending WP03-E. |
| WP03-C — adaptive cutback consolidation | **Implemented — targeted** | One common increment/retry/cutback/growth/shrink policy for stateless and stateful load control; accepted state preserved. |
| WP03-D — arc-length robustness boundary | **Implemented — targeted** | One common radius/retry policy, rollback-before-retry and target-clipped progress guard around the unchanged specialized arc-length correction kernel; 0/7 points pending WP03-E. |
| WP03-E — independent closure audit | Not started | Adversarial replay of the frozen campaign, deterministic failures, easy-case preservation and difficult-case evidence. |

## Guardrails

The decomposition does not authorize a formulation change, finite-strain
plasticity, frictional-contact migration, distributed nonlinear mechanics,
nonlinear dynamics or maturity promotion. WP03 points remain **0/7** until
the independent closure policy permits an award. WP03-D leaves difficult-case
improvement and independent closure for WP03-E; the next step is Owner review
before WP03-E.
