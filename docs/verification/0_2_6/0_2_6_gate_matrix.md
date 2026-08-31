# Gate Matrix

| Gate | Purpose | Current status |
| --- | --- | --- |
| `026-G00` | Baseline / provenance | PASS |
| `026-G01` | Architecture audit | PASS |
| `026-G02` | V&V infrastructure | PASS |
| `026-G03` | Corpus design | PASS |
| `026-G04` | Linear / element robustness | PASS_WITH_LIMITATIONS |
| `026-G05` | Modal / dynamic / harmonic | PASS_WITH_LIMITATIONS |
| `026-G06` | J2 maturity extension | PASS_WITH_LIMITATIONS |
| `026-G07` | Geometric nonlinear and arc-length review | PASS_WITH_LIMITATIONS |
| `026-G08` | Buckling maturity extension | PASS_WITH_LIMITATIONS |
| `026-G09` | Contact maturity extension | PASS_WITH_LIMITATIONS |
| `026-G10` | Advanced Nonlinear / Research Audit | PASS_WITH_LIMITATIONS |
| `026-G11` | Adversarial / failure / metamorphic | PASS_WITH_LIMITATIONS |
| `026-G12` | Performance / scalability | PASS_WITH_LIMITATIONS |
| `026-G13` | External correlation aggregation | PASS_WITH_LIMITATIONS |
| `026-G14` | Full regression / architecture freeze | PASS_WITH_LIMITATIONS |
| `026-G15` | Owner release review | NOT_STARTED |

G00 is a refactor guard with an explicit dirty-worktree limitation, not a replacement for immutable 0.2.5 evidence. G01-G03 close only audit, infrastructure and corpus design. Capability-gate outcomes are not implied by this foundation.

`026-G05` references the supplemental `G05-B` contract, registry and evidence, the all-family coverage record, the final-evidence pack and the Owner decision record. The controlled campaign reaches MOD `14/14`, DYN `32/16` and HAR `12/12` across eight family rows; its bounded refinement policies are Owner-approved. The gate is closed as `PASS_WITH_LIMITATIONS`: external correlation is bounded and not element-family complete.

`026-G06` is closed as `PASS_WITH_LIMITATIONS` by Owner decision. Small-strain J2 is qualified within the tested TET4/TET10/HEX8/HEX20 scope. The evidence is tied to execution source SHA `8bd0f2d8fdce7bf27ffc4c28e6aa26e69288fa63`; closeout documentation is separate. Algorithmic tangent symmetry is not independently qualified, increment-refinement independence is demonstrated only on TET4, and finite-kinematic J2 remains research-only and outside the qualified scope.

`026-G07` is closed by Owner decision as `PASS_WITH_LIMITATIONS`. The bounded
scope is Total-Lagrangian elasticity on TET4, with compatible external evidence
over the recorded 16 points, plus the declared TET4 Arc-Length research
benchmark with bounded branch, turning-point and restart/rollback evidence.
HEX8 complete-history behavior and ARC-002 refined-mesh comparability remain
explicitly excluded or deferred. TET10 and HEX20 remain research routes; no
general TL, Arc-Length, finite-kinematic or production-wide claim is made. The
machine-readable closeout is `qualification/0_2_6/g07_owner_closeout.json`.

`026-G08` is closed as `PASS_WITH_LIMITATIONS` by the active Owner review in
`qualification/0_2_6/g08_owner_final_review.json`. The review preserves the
bounded first-factor/first-mode scope and records the later corrected evidence:
TET4 is `QUALIFIED_BOUNDED`, TET10 and HEX20 are
`PASS_WITH_LIMITATIONS`, and HEX8 is `MORE_EVIDENCE_REQUIRED`. The superseded
positive-load Euler screen is excluded from active metrics. No post-buckling,
multi-mode or general physical-validation claim is made.

`026-G09` is closed as `PASS_WITH_LIMITATIONS` by the Owner closeout in
`qualification/0_2_6/g09_owner_closeout.json`. Lots 1 and 2 provide internal
bounded node-to-triangle evidence for mesh, load paths, rollback and failures.
Lot 3 adds Code_Aster unilateral open/close and TET4 structural-path
comparisons, plus a CalculiX pre-contact tie-breaker. The external comparison
is intentionally limited because Code_Aster uses an exact unilateral
constraint while QF uses penalty contact; it does not qualify the penalty law
itself, finite sliding, general surface-to-surface contact, friction, or a
universal conditioning cutoff. The candidate `1e4..1e6` interval remains
`EXPERIMENTAL_ONLY`, and the mesh-dependent transition warning is retained
explicitly.

`026-G10` is `PASS_WITH_LIMITATIONS`. Lot 1 records a controlled audit of
existing nonlinear and research routes in
`qualification/0_2_6/g10_research_audit_matrix.json` and
`0_2_6_g10_lot1.md`; the adversarial review is recorded in
`0_2_6_g10_owner_review_lot1.md`. The selected external campaign and final
Owner classification are recorded in
`0_2_6_g10_selected_external_campaign.md` and
`0_2_6_g10_owner_closeout.md`. The closeout passed the applicable targeted
controls with no functional source change or numerical regression; full
regression was skipped by policy. Existing small-strain J2, transaction and
failure diagnostics retain their bounded ownership. Total-Lagrangian
elasticity and arc-length remain G07-owned and deferred; finite-kinematic J2
and the coupled routes remain experimental, deferred or not qualified under
their explicit classifications. G10 does not change G07, G08, G09, G11 or
G12.

`026-G12` is closed by Owner decision as `PASS_WITH_LIMITATIONS`. The final
campaign records 18/18 deterministic finite route measurements across nine
bounded rows, and the optimized scaling evidence records full solves through
107 811 actual DOF plus an assembly-only 300k probe. The 1M probe is
`RESOURCE_LIMITED` after the controlled timeout and is not a success claim.
The requirement is fully satisfied within this declared measured scope; no
universal route-by-family scaling law, general HPC qualification or global
solver speedup is claimed. The unique full regression produced 1849 passed,
184 skipped and 18 historical failures with zero fix-only failures; those
release blockers remain outside G12. The Owner record is
`qualification/0_2_6/g12_owner_closeout.json`.

`026-G11` is closed as `PASS_WITH_LIMITATIONS` by Owner decision. The bounded
closeout covers 20 route-native runtime cases across linear static, nonlinear
static, geometric nonlinear static, modal, linear buckling and linear static
contact. All cases have deterministic replay, finite diagnostics and explicit
failure classification; mutable retry cases preserve committed state. DIAG-005
and DIAG-008 remain bounded because the evidence does not claim exhaustive
coverage of every public failure class, structured nonlinear reason or route
combination. The 18 historical full-regression failures remain release
blockers outside G11.

`026-G14` closes the final capability-coverage audit with limitations. The
registry contains 33 public capabilities and 44 public element-analysis
mappings, with no unregistered implementation, duplicate capability or
unbounded public maturity claim found. The audit is recorded in
`qualification/0_2_6/g14_capability_coverage.json` and
`qualification/0_2_6/g14_owner_closeout.json`. Full regression is
`SKIPPED_BY_POLICY` here; the documented 18 historical failures and release
state findings remain cleanup items, and G15 remains the release Owner review.
