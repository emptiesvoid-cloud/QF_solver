---
doc_id: DOC-029-001
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# QF Solver 0.2.9 Unified Nonlinear Mechanics — master plan

> **Development planning record — not a release claim.** This page freezes the
> intended 0.2.9 scope before implementation begins. Existing 0.2.8 maturity,
> qualification evidence and published release artifacts remain authoritative
> for 0.2.8.

## Objective

0.2.9 develops one coherent nonlinear mechanics architecture around the
following canonical contract:

\[
R(u, \lambda, state)=\lambda F_{ext}-F_{material}-F_{geometric}-F_{contact}
\]

\[
K_T=K_{material}+K_{geometric}+K_{contact}.
\]

Material, geometric and contact routes must share state contracts,
residual/tangent assembly, Newton controls, accepted-increment transaction
semantics, diagnostics and restart rules. This plan does not imply that every
existing route already satisfies that architecture.

## Frozen 100-point roadmap

| Work package | Points |
| --- | ---: |
| WP00 — Baseline / architecture contracts | 4 |
| WP01 — Unified Nonlinear Core | 12 |
| WP02 — State Transactions & Rollback | 6 |
| WP03 — Newton Robustness / Adaptive Control | 7 |
| WP04 — Geometric Nonlinear Qualification | 12 |
| WP05 — High-order Geometric Nonlinear | 5 |
| WP06 — Arc-Length & Postbuckling | 8 |
| WP07 — Frictionless Contact Maturity | 10 |
| WP08 — Frictional Contact | 8 |
| WP09 — J2 + Geometry | 8 |
| WP10 — Coupled Nonlinear Mechanics | 6 |
| WP11 — Mixed PETSc/MPI Closure | 6 |
| WP12 — External V&V | 4 |
| WP13 — Performance / API / Diagnostics | 2 |
| WP14 — Qualification / Documentation / Release | 2 |
| **Total** | **100** |

Weights and work-package boundaries are frozen unless the Owner explicitly
approves a change. The machine-readable source is
`qualification/0_2_9/roadmap.json`.

## Boundaries

The primary scope is nonlinear mechanics maturity, not a broad feature
expansion. WEDGE15, PYRAMID5 promotion, a new general element catalogue, GPU,
GUI, multiphysics, neural operators, broad Abaqus compatibility, distributed
nonlinear mechanics and general nonlinear dynamics are out of primary scope.
MITC4 modal and HEX8-SRI may receive incidental fixes only.

The existing mixed distributed PETSc/MPI runtime remains `NOT_VALIDATED`.
0.2.9 may target a bounded **linear-static** runtime closure only; this plan
does not claim distributed nonlinear mechanics.

## Current owner-closure state

WP01 Unified Nonlinear Core is **CLOSED** at **12/12 points** following the
independent audit at SHA
`6876d867cdd845195e8946b05329b0bc82937fdc`. The accepted decision is
`GO_WITH_LIMITATIONS`; the combined validated total is **16/100** including
WP00 (4/4).

The controlled documentation view is [WP01 Owner closure](wp01-owner-closure.md);
the corresponding machine-readable record is
`qualification/0_2_9/wp01_owner_closure.json`.
WP02 is **CLOSED** at **6/6 points** after the independent WP02-E audit at
`c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5`, bringing the validated total to
**22/100**. The audit decision is `GO_WITH_LIMITATIONS`: restart closure is
bounded to supported single-process fixed/adaptive/arc paths and does not
claim frictional-contact, distributed, nonlinear-dynamics or adaptive
penalty-contact restart. Owner review remains required before independent
WP03-E closure. OD-029-01
remains **OPEN** and blocks WP09 only; OD-029-02 is **CLOSED** as
`READ_V1_WRITE_V2_BOUNDED`. This record does not promote maturity, alter
numerical formulations or change historical WP01-A/B/C/D evidence.

WP03 is **CLOSED at 7/7** after the independent WP03-E audit at
`4ca71d549ea13460086f52670baa42c74d9ac1aa`, bringing the roadmap to
**29/100**. The `GO_WITH_LIMITATIONS` decision confirms the common stagnation,
line-search, adaptive-step and arc-radius authorities without a maturity or
formulation change. It independently demonstrates the target-clipped retry
improvement: five repeated effective attempts before WP03 become one rejection
at the final SHA, while the physical result is identical.

WP04 is **HOLD — TET4 mesh convergence** at 0/12. WP04-B demonstrates the bounded
TET4/HEX8 Total-Lagrangian StVK objectivity, affine finite-deformation patch,
energy-gradient, consistent-tangent and accepted-path work identities. The
frozen WP04-C TET4 structural campaign passes its small-load, equilibrium,
load-step, replay and envelope checks, but fails G04-10 mesh convergence:
M3-vs-M2 displacement/energy/stress differences are 16.4%/16.4%/24.3%, above
the frozen 2%/2%/10% limits. The contract does not promote current
`RESEARCH_ONLY` maturity; Owner direction is required before any re-scope or
remediation.

WP02-B established checkpoint-v2 serialization, WP02-C migrated fixed and
adaptive restart ownership, and WP02-D migrated the public arc-length restart
path to the accepted composite state. The audit is recorded in the
[WP02-E independent closure](wp02-e-independent-closure.md), following the
[WP02-D arc-length restart evidence](wp02-d-arc-length-restart.md) and
[WP02-D1 material-state alias remediation](wp02-d1-material-state-alias.md).
The bounded v1 compatibility policy and its contact-bearing rejection are
recorded in [OD-029-02](owner-decisions.md).

## Planning records

- [Architecture baseline](architecture-baseline.md)
- [Requirements and frozen gate themes](requirements.md)
- [Gate matrix](gate-matrix.md)
- [Known inherited limitations](known-limitations.md)
- [Progress tracker](progress.md)
- [Owner decision log](owner-decisions.md)
- [WP01 Owner closure](wp01-owner-closure.md)
- [WP01 Unified Nonlinear Core prospective contract](wp01-unified-nonlinear-core-contract.md)
- [WP01-B implementation foundation evidence](wp01-b-foundation-evidence.md)
- [WP02 state and checkpoint contract](wp02-state-checkpoint-contract.md)
- [WP02 compatibility matrix](wp02-compatibility-matrix.md)
- [WP02 failure matrix](wp02-failure-matrix.md)
- [WP02 gate matrix](wp02-gate-matrix.md)
- [WP02 implementation plan](wp02-implementation-plan.md)
- [WP02-B schema-v2 foundation](wp02-b-schema-v2-foundation.md)
- [WP02-D arc-length restart](wp02-d-arc-length-restart.md)
- [WP02-D1 material-state alias remediation](wp02-d1-material-state-alias.md)
- [WP02-E independent closure audit](wp02-e-independent-closure.md)
- [WP03-A robustness contract](wp03-robustness-contract.md)
- [WP03-A architecture map](wp03-architecture-map.md)
- [WP03-A failure/retry matrix](wp03-failure-retry-matrix.md)
- [WP03-A baseline campaign](wp03-baseline-campaign.md)
- [WP03-B executed baseline](wp03-b-baseline.md)
- [WP03-B robustness authority evidence](wp03-b-robustness-authority.md)
- [WP03-A prospective gate matrix](wp03-gate-matrix.md)
- [WP03 implementation decomposition](wp03-implementation-plan.md)
- [WP03-D arc-length radius policy](wp03-d-arc-radius-policy.md)
- [WP03-E independent closure audit](wp03-e-independent-closure.md)
- [WP04 geometric qualification contract and baseline](wp04-geometric-qualification-contract.md)
- [WP04-B mechanics identities](wp04-b-mechanics-identities.md)
- [WP04-C TET4 structural qualification — HOLD](wp04-c-tet4-structural-qualification.md)

WP01 implementation and continuation migration are closed under the recorded
Owner decision. WP02 and WP03 are closed under their independent audit
records; WP04-C is on HOLD after its frozen TET4 mesh-convergence gate failed.
OD-029-01 remains open and blocks WP09; WP01 remains formulation-neutral.
