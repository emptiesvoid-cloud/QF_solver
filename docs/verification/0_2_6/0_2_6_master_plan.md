# 0.2.6a0 Master Plan

## Objective

0.2.6a0 is a maturity, reproducibility and architecture cycle. It makes the
qualification system executable as controlled work packages before any claim is
expanded. This foundation run adds no FEM physics and does not certify a new
release.

## Ordered Execution

1. G00 baseline and provenance.
2. G01 architecture audit.
3. G02 registry, runner and manifest contracts.
4. G03 corpus design.
5. G04-G13 controlled capability batches, each followed by evidence and gate
   review.
6. G14 full regression and architecture freeze.
7. G15 Owner review.

Every batch follows: audit, implement only the approved narrow change, verify,
benchmark where applicable, correlate, gate, then move to the next package.
An OPEN gate is recorded as OPEN; it is never converted to PASS by a new label.

## G07 Step 1 Contract Boundary

The official gate is `026-G07`, titled **Geometric nonlinear and arc-length
review**. Step 1 is governance and contract work only; it does not close the
gate and does not create numerical evidence.

The machine-readable contract is
`qualification/0_2_6/g07_requirements.json`; the capability-by-family matrix is
`qualification/0_2_6/g07_capability_matrix.json`. The candidate bounded
qualification scope is Total-Lagrangian elasticity on TET4 and HEX8. TET10 and
HEX20 remain `RESEARCH` for this gate. Existing finite-kinematic J2 and coupled
nonlinear workflows are excluded from G07.

The existing arc-length route is limited to `EXPERIMENTAL` /
`PASS_INTERNAL_RESEARCH`. A successful internal run cannot promote it to a
production-qualified capability. The contract requires branch, turning-point,
restart/rollback and sensitivity evidence, but unresolved acceptance bands are
marked `PROPOSED_OWNER_REVIEW` rather than assigned a new numerical threshold.

### Step 2 Execution Plan

Step 2 may start only after the Owner approves the policies marked
`PROPOSED_OWNER_REVIEW`:

1. Run bounded TL elasticity cases for TET4 and HEX8: small-strain limit,
   objectivity/rigid-body invariance, large-rotation domain, residual and
   equilibrium, tangent finite differences, mesh refinement at
   coarse/medium/fine/refined levels, increment refinement, and reproducibility.
2. Run high-order TET10 and HEX20 only as explicitly labelled research smoke
   cases; do not aggregate them into the qualified G07 claim.
3. Run the existing arc-length shallow-arch and common FEM snap-through cases
   with nominal, smaller and larger recorded arc-step settings, plus branch
   tracking, limit point, restart/rollback and controlled failure cases.
4. Use the existing analytical shallow-arch oracle and compatible Code_Aster
   or CalculiX comparisons when available. An unavailable or non-comparable
   external tool is `SKIPPED`, never `PASS`.
5. Emit per-case JSON, complete curves/diagnostics, environment and tool
   versions, `source_sha`, `dirty=false`, threshold source and artifact
   digests. Stop on unexplained divergence, a required new formulation, or a
   threshold change.

G07 remains `NOT_STARTED` until a separate evidence pack and Owner decision
meet the contract.
