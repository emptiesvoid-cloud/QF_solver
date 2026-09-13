# QF Solver 0.2.9 qualification planning

This directory is the prospective, machine-readable planning and controlled
closure record for the 0.2.9 **Unified Nonlinear Mechanics** development
cycle. The Owner-approved WP01 closure is recorded in
`wp01_owner_closure.json`; it does not change any 0.2.8 maturity record.

The baseline commit is recorded in `baseline.json`. Work packages may only
add prospective contracts and evidence beneath this directory; historical
0.2.8 evidence remains immutable.

WP03 Newton Robustness / Adaptive Control is **CLOSED** at 7/7 points after
the independent WP03-E audit at `4ca71d549ea13460086f52670baa42c74d9ac1aa`.
The `GO_WITH_LIMITATIONS` decision confirms the four bounded policy
authorities, exact retry rollback and numerical preservation. It also records
the same-model target-clipped arc retry challenge: the final policy reaches
the unchanged physical solution with one rejection where the pre-WP03 route
repeated the same effective radius five times.

WP04 Geometric Nonlinear Qualification is now **CLOSED — 12/12** after the
independent WP04-F evidence-only audit at
`70e1bf953c8e6f37b8070e78ca97e58b21499291`, with a
`GO_WITH_LIMITATIONS` decision. WP04-B independently demonstrates the bounded TET4/HEX8
Total-Lagrangian Saint-Venant-Kirchhoff objectivity, affine patch,
energy-gradient, tangent and accepted-path work identities. WP04-C then ran a
frozen TET4 cantilever campaign. Its small-load, force/moment balance,
load-step, replay, envelope and failure checks pass, but its M3-vs-M2
displacement/energy/stress mesh differences (16.4%/16.4%/24.3%) exceed the
frozen 2%/2%/10% limits. Neither family is promoted. See the controlled
WP04-C record at `../docs/verification/0_2_9/wp04-c-tet4-structural-qualification.md` and
`wp04_c_tet4_structural_summary.json`. WP04-C1 reproduces that failed campaign
and finds the same slow linear/nonlinear TET4 compliance trend with invariant
load and mesh checks; it does not change G04-10, maturity, or the roadmap. The
owner-aborted C2-M3 process remains classified as an owner abort, not as a
resource failure. R2 records the original strict residual failure, adds
scale-aware backward-error diagnostics and bounded SciPy-local iterative
support, and shows that the selected CG+Jacobi candidate fails nonlinear M1
at load step 4; no M2 run or qualification promotion is claimed.

R2B independently reproduces and captures the failing M1 tangent. Same-matrix
MINRES+Jacobi passes the scale-aware contract, and full M1 MINRES completes
with zero fallback and direct-equivalent observables. WP04 remains HOLD;
G04-10 is unresolved and no M2 run is authorized. The controlled R2B record is
`../docs/verification/0_2_9/linear-solver-remediation-r2b.md`, with machine-
readable evidence in `wp04_linear_solver_r2b.json`.

The owner-authorized C2R3 campaign subsequently ran M2 and a fresh-process M3
with the identical MINRES+Jacobi route. Both returned normally but terminated
with numerical `CONVERGENCE_STAGNATION` before the final load factor, so
G04-10 remains unresolved and no pair delta is claimed. The consolidated
master record is `linear_solver_remediation_master.json`; live JSONL and
terminal case records are retained under `c2r3/`.

C2R4 then reproduces the M2 near-tolerance stagnation and captures one
step-3 plateau system outside Git. Same-state direct and tighter-MINRES
corrections are machine scale and both remain above the frozen nonlinear
tolerance, so the evidence is classified as a nonlinear residual numerical
floor rather than a linear-solver failure. It also identifies that C2R3
explicitly disabled the line search used by original C2/R2B. The one
M2-only canonical-line-search comparison accepts step 3 but terminates at
step 4 with `LINE_SEARCH_FAILURE`; it is a protocol diagnostic, not a
qualification rerun. Controlled evidence is in `c2r4/` and
`../docs/verification/0_2_9/wp04-c2r4-near-tolerance-audit.md`.

C2R5 reran only canonical M2 with the existing line search enabled and
reproduced the step-4 `LINE_SEARCH_FAILURE` at
`1.0411047989090212e-10`. Direct, tighter MINRES, repeated reassembly,
pairwise, compensated and platform-longdouble accumulation diagnostics all
support a bounded `NONLINEAR_RESIDUAL_NUMERICAL_FLOOR` diagnosis with strong
force cancellation; no accumulation-only remediation was demonstrated. A
future floor-aware termination policy is recommended for Owner review, but no
threshold or convergence policy was changed. M3/M4 and qualification reruns
remain prohibited. See `c2r5/` and
`../docs/verification/0_2_9/wp04-c2r5-residual-precision-audit.md`.

C2R6 subsequently completed the frozen floor-aware M2/M3 campaign. This audit
recovers the existing result, status and JSONL files without rerunning either
case. Both meshes reached the final load factor with 12 accepted steps, zero
fallbacks and complete terminal records. The original M2-to-M3 displacement,
reaction, energy and representative-stress thresholds all pass; the raw
runner's top-level `G04-10=UNRESOLVED` placeholder is preserved and the
derived status is `PASS_CANDIDATE_PENDING_OWNER_REVIEW`. See
`c2r6/frozen_threshold_audit.json` and
`../docs/verification/0_2_9/wp04-c2r6-floor-aware-termination.md`.

WP04-D freezes and executes the HEX8 structural contract in `wp04d/`. H1,
H2 and H3 complete under the frozen C2R6 MINRES+Jacobi route with consistent
face loading, equilibrium, envelope and H1 replay evidence. The H2→H3
displacement, reaction, energy and representative-stress deltas pass the
frozen thresholds, so `g04_11_audit.json` records `G04-11=PASS` pending Owner
review. H4 is not run because its predeclared rescue condition is not
triggered. G04-12 is only prepared, and the explicit small-load reaction
support limitation is retained in the campaign result.

WP04-E then performs the frozen G04-12 cross-family audit from existing
evidence only. The approved TET4 C2R6 M3 and HEX8 H3 physical definitions are
matched at geometry, material, constraints, physical resultant/moment and
observable conventions. The frozen displacement, reaction, energy and
representative-stress deltas pass at `0.004566585385421973`,
`7.105427357601005e-16`, `0.004553762679948579` and
`0.05163720669059609`, respectively. The family-specific discrete boundary
load representations are disclosed; the governing resultant and first moment
match. The HEX8 small-load reaction support limitation is carried forward to
WP04-F. The derived status is now `G04-12=PASS`; WP04-F independently verifies
all twelve gates, preserves the original G04-10 failure, and raises the
validated total to **41/100**. Public maturity remains Owner-pending and the
registry is unchanged. See
`../docs/verification/0_2_9/wp04-e-g04-12-cross-family-closure.md`,
`wp04e/g04_12_cross_family_audit.json`, and
`../docs/verification/0_2_9/wp04-f-final-closure-audit.md`.

## Current planning status

- WP00: `CLOSED`, 4/4 points.
- WP01 Unified Nonlinear Core: `CLOSED`, 12/12 points after independent
  Owner closure at audit SHA `6876d867cdd845195e8946b05329b0bc82937fdc`.
- Validated total: `41/100`.
- WP02 State Transactions & Rollback: `CLOSED`, 6/6 points after the
  independent WP02-E audit at `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5`.
  The decision is `GO_WITH_LIMITATIONS`; Owner review is required before the
  independent WP03-E closure audit.
- OD-029-01: **OPEN**; it blocks WP09 only.
- OD-029-02: **CLOSED** as `READ_V1_WRITE_V2_BOUNDED`; ambiguous/stateful
  contact-bearing v1 checkpoints are rejected.

WP04-F is the completed phase: the evidence-only independent audit records
G04-01..G04-05, G04-07..G04-08 and G04-10..G04-12 as PASS, with G04-06 and
G04-09 as PASS_WITH_LIMITATION. WP04 is CLOSED at 12/12 and the validated
total is 41/100. Owner approval is required before sequential child-branch
integration; WP05 has not started.

WP03-C preserves the accepted-state authority and all existing numerical and
maturity boundaries. WP03-D adds the single `UnifiedArcLengthRadiusPolicy`,
preserves the specialized arc-length correction kernel and fixes the
target-clipped retry stall boundary. The independent closure record is
`wp03_e_independent_closure.json`; it awards WP03 7/7 without promoting
maturity or changing a numerical formulation.

WP02-A is recorded in the `wp02_*` planning records. WP02-B adds the schema-v2
checkpoint and deterministic serialization foundation without changing
numerical formulations or maturity claims.

WP04-A freezes the objectivity, affine finite-deformation patch, energy
gradient, tangent, accepted-path work, small-limit, equilibrium, mesh,
cross-family and replay gates before implementation. Historical WP13-11
energy/work evidence is retained unchanged: its coarse 24-sample work path
failed the old discovery threshold. WP02/WP03 now provide an authoritative
accepted-state callback seam for a correct future refinement study, but that
study is deliberately not claimed complete in WP04-A.

The R2 linear-solver remediation evidence is recorded in
`wp04_linear_solver_r2.json` and the companion controlled record
`../docs/verification/0_2_9/linear-solver-remediation-r2.md`.
The R2B forensic and MINRES evidence is recorded in
`wp04_linear_solver_r2b.json` and
`../docs/verification/0_2_9/linear-solver-remediation-r2b.md`.
