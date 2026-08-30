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
| `026-G07` | Geometric nonlinear and arc-length review | NOT_STARTED |
| `026-G08` | Buckling maturity extension | PASS_WITH_LIMITATIONS |
| `026-G09` | Contact maturity extension | PASS_WITH_LIMITATIONS |
| `026-G10` | Existing coupled nonlinear review | NOT_STARTED |
| `026-G11` | Adversarial / failure / metamorphic | PASS_WITH_LIMITATIONS |
| `026-G12` | Performance / scalability | NOT_STARTED |
| `026-G13` | External correlation aggregation | NOT_STARTED |
| `026-G14` | Full regression / architecture freeze | NOT_STARTED |
| `026-G15` | Owner release review | NOT_STARTED |

G00 is a refactor guard with an explicit dirty-worktree limitation, not a replacement for immutable 0.2.5 evidence. G01-G03 close only audit, infrastructure and corpus design. Capability-gate outcomes are not implied by this foundation.

`026-G05` references the supplemental `G05-B` contract, registry and evidence, the all-family coverage record, the final-evidence pack and the Owner decision record. The controlled campaign reaches MOD `14/14`, DYN `32/16` and HAR `12/12` across eight family rows; its bounded refinement policies are Owner-approved. The gate is closed as `PASS_WITH_LIMITATIONS`: external correlation is bounded and not element-family complete.

`026-G06` is closed as `PASS_WITH_LIMITATIONS` by Owner decision. Small-strain J2 is qualified within the tested TET4/TET10/HEX8/HEX20 scope. The evidence is tied to execution source SHA `8bd0f2d8fdce7bf27ffc4c28e6aa26e69288fa63`; closeout documentation is separate. Algorithmic tangent symmetry is not independently qualified, increment-refinement independence is demonstrated only on TET4, and finite-kinematic J2 remains research-only and outside the qualified scope.

`026-G07` remains `NOT_STARTED`. Step 1 defines the controlled contract in
`qualification/0_2_6/g07_requirements.json` and the capability matrix in
`qualification/0_2_6/g07_capability_matrix.json`; these references do not
constitute numerical evidence or gate closure. The bounded candidate scope is
Total-Lagrangian elasticity on TET4 and HEX8. TET10 and HEX20 remain research
routes. Arc-length and snap-through remain `EXPERIMENTAL` / `PASS_INTERNAL_RESEARCH`
and cannot be promoted by this contract.

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

`026-G11` is closed as `PASS_WITH_LIMITATIONS` by Owner decision. The bounded
closeout covers 20 route-native runtime cases across linear static, nonlinear
static, geometric nonlinear static, modal, linear buckling and linear static
contact. All cases have deterministic replay, finite diagnostics and explicit
failure classification; mutable retry cases preserve committed state. DIAG-005
and DIAG-008 remain bounded because the evidence does not claim exhaustive
coverage of every public failure class, structured nonlinear reason or route
combination. The 18 historical full-regression failures remain release
blockers outside G11.
