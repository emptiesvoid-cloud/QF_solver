---
doc_id: DOC-028-WP13-02A2-WEDGE6-DYNAMIC-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP13-02A2 WEDGE6 dynamic enablement

WP13-02A2 removes a compatibility-only blocker for the already implemented
generic Newmark and harmonic solvers. It does not modify the WEDGE6 FEM
formulation, add a maturity record, or qualify WEDGE6 dynamics.

The machine-readable evidence is
[`wp13_02a2_wedge6_dynamic_evidence.json`](../../../qualification/0_2_8/wp13_02a2_wedge6_dynamic_evidence.json).
The preceding frozen contracts remain unchanged:
[`Newmark`](../../../qualification/0_2_8/wp13_02a_newmark_contract.json) and
[`harmonic`](../../../qualification/0_2_8/wp13_02a_harmonic_contract.json).

## Root cause and minimal enablement

Before this step, WEDGE6 declared only `linear_static` and `modal` in its
technical descriptor. The router and the generic K/M-based dynamic solvers
already existed, but compatibility preflight returned
`UNSUPPORTED_ROUTE / ANALYSIS_NOT_SUPPORTED` before dispatch. No mass,
damping, post-processing or numerical formulation defect was found.

The descriptor now declares `transient_dynamic` and `harmonic_response` as
technical routes. Because no 0.2.7/0.2.8 maturity combination was added, both
routes return `EXPERIMENTAL_ROUTE / NO_REGISTRY_COMBINATION`. This enables an
explicit experimental route without promoting WEDGE6 or changing the 46
combination registry.

## Targeted evidence

The WEDGE6 consistent K/M checks pass: local K and M are symmetric, the free
mass is positive, the mass sum is `23400 kg` over translational components, and
rigid-body residuals are below `4.81e-18` relative. The existing modal route
remains unchanged; its first three frequencies are `592.6962`, `767.0890` and
`887.0670 Hz`, with maximum relative residual `1.35e-14`.

The pure Newmark micro-run uses the first dense K/M mode as an initial
condition. Four levels (`T1/20` through `T1/160`) converge; at `T1/80` and
`T1/160` the frozen amplitude/phase gates pass. Energy drift is `3.29e-13`
and the fine-level dynamic residual is `1.60e-8`. Two replays are identical
within the numerical replay gate.

The pure harmonic micro-run covers the static limit, off-resonance and the
first-mode neighborhood with 2% mass-proportional damping. The independent
dense complex reference agrees to `2.94e-16` relative response error, phase
error is zero in this case, and the maximum relative residual is `1.92e-15`.

A 48-DOF connected TET4/WEDGE6/HEX8 smoke also passes both routes. It contains
3 TET4, 2 WEDGE6 and 1 HEX8 in the path
`LOAD -> TET4 -> WEDGE6 -> HEX8 -> SUPPORT`; both dynamic routes retain all
families and use the generic assembly path. This smoke is not a mixed V&V
qualification campaign.

## Status and limits

`WEDGE6 Newmark = EXPERIMENTAL_INTERNAL_ROUTE_CANDIDATE` and
`WEDGE6 harmonic = EXPERIMENTAL_INTERNAL_ROUTE_CANDIDATE`. Full mixed dynamic
V&V, dt/frequency gates, interface conservation, replays and Owner decisions
remain WP13-02B and WP13-02C. No public maturity promotion or external
correlation claim is made.

The full suite remains deferred to the WP13 final gate.
