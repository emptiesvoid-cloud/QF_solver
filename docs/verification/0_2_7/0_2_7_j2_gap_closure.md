---
doc_id: DOC-027-010
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 J2 Gap Closure

## Baseline boundary

The 0.2.6 Owner decision qualifies small-strain J2 only within its recorded
TET4/TET10/HEX8/HEX20 scope. Algorithmic tangent symmetry is not independently
qualified, increment-refinement evidence is strongest on TET4, and
finite-kinematic J2 remains research-only. This plan does not reopen or alter
that decision.

## Proposed work

WP11 may close only the evidence gaps that matter to the existing small-strain
claim:

1. repeatable stress/increment paths on all four solid families;
2. finite-difference tangent checks over declared states, directions and
   perturbation sizes;
3. increment-partition studies on families where the current evidence is thin;
4. unload/reload and rollback checks within the existing material model;
5. energy/residual diagnostics and explicit failure classifications;
6. comparable external correlation where the constitutive convention matches.

## Policy discipline

Existing policies are reused where applicable. A new tolerance, a change to
the tangent, finite-kinematic formulation, default Newton path or rescue
behavior requires an Owner decision and is outside this foundation plan.
`PROPOSED_OWNER_REVIEW` is the only valid state for an unsupported threshold.

## STOP/GO

GO requires all four families to have traceable cases, no unexplained
divergence, deterministic replay and preserved qualified scope. STOP on a
formulation change, a weakened criterion, or evidence that cannot distinguish
material behavior from a harness/model error.

## WP11 execution record

The targeted WP11 lot is recorded in
`qualification/0_2_7/wp11_j2_evidence.json` with case definitions in
`qualification/0_2_7/wp11_j2_cases.json`. It exercises the existing
small-strain radial-return material and connected nonlinear route on TET4,
TET10, HEX8 and HEX20. The lot covers elastic and plastic transitions,
unloading/reloading, a simple cycle, finite-difference tangent checks,
multi-element response, energy, rollback, increment characterization, Newton
behavior and explicit failure modes.

The result is `PASS_WITH_LIMITATIONS`: the existing qualified bounded J2 scope
is retained, with no promotion or demotion. Increment sensitivity is reported
for all four families without adding a universal threshold; tangent symmetry is
diagnostic only; modified Newton non-convergence is explicit and full Newton
remains the accepted route. Finite-kinematic J2 and dynamics gaps remain
outside WP11. The Code_Aster evidence is reused from the controlled 0.2.6
record and is not presented as a new WP11 external run.
