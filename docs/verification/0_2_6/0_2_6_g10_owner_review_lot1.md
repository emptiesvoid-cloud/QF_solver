# 0.2.6 G10-LOT1 - Adversarial Owner Review

Review state: `PARTIAL`; formal Owner closeout remains pending.

Execution source SHA: `51b3a7c8ace6731830109984a01ce31f79c44401`.
The review evidence is documentary and may be committed at a later SHA. It
does not replace the execution source SHA or alter any numerical result.

## Review conclusion

The ten Lot 1 route records were reviewed against their implementation path,
existing tests, maturity, ownership and evidence boundary. The review found no
real bug, no numerical regression and no reason to change G07, G08, G09, G11 or
G12. Internal tests alone do not promote a research route.

The existing bounded small-strain J2 classification remains owned by G06.
Transaction/checkpoint/retry and structured failure diagnostics retain their
bounded G09/G11 ownership. Total-Lagrangian, arc-length, finite-kinematic J2
and coupled routes remain outside a new G10 qualified claim.

## Route decisions

| Route | Review classification | Reason and boundary |
| --- | --- | --- |
| Small-strain nonlinear static | `OWNER_KEEP_EXISTING` | Retain the existing bounded G06 scope; no G10 expansion. |
| Total-Lagrangian elasticity | `OWNER_NEEDS_EXTERNAL_EVIDENCE` | G07 remains parked; compatible external evidence would directly address its existing blocker. |
| Arc-length continuation | `OWNER_NEEDS_EXTERNAL_EVIDENCE` | Internal branch evidence is insufficient; comparable continuation evidence has high value. |
| Finite-kinematic J2 | `OWNER_NOT_QUALIFIED` | Available external J2 decks are small-strain and are not an equivalent finite-kinematic oracle. |
| J2 plus geometry | `OWNER_BLOCKED` | No external deck currently separates constitutive and kinematic differences. |
| Geometry plus frictionless contact | `OWNER_EXPERIMENTAL_ONLY` | Existing contact comparisons use a different enforcement or surface model. |
| J2 plus geometry plus contact | `OWNER_BLOCKED` | It inherits unresolved finite-kinematic J2 and contact-equivalence blockers. |
| Modified Newton on finite routes | `OWNER_NOT_QUALIFIED` | The existing scope validator rejects this path for qualified finite-kinematic use. |
| Transaction/checkpoint/retry | `OWNER_KEEP_EXISTING` | Retain the bounded G09/G11 evidence and its stated coverage limit. |
| Structured failure diagnostics | `OWNER_KEEP_EXISTING` | Retain the bounded G11 evidence; exhaustive route coverage is not claimed. |

## External evidence selected

Only two routes are selected for a future targeted campaign. They are routed
to G07 ownership and selection does not reopen or close G07:

1. **Arc-length continuation**: use the existing two-TET4 shallow-arch/
   snap-through case and a Code_Aster `LONG_ARC` deck with the same geometry,
   load convention, control variable and continuation direction. Compare the
   complete load-factor/displacement and reaction curves, turning point,
   residual history and restart branch. Existing G07 policies must be used;
   no new tolerance is approved by this review.
2. **Total-Lagrangian elasticity**: use a same-mesh TET4/HEX8 structural case
   with equivalent Green-Lagrange/PK2 measures and a positive `det(F)` domain.
   Use Code_Aster or CalculiX only when the kinematics, material, loads,
   constraints and output measure are genuinely comparable. Compare complete
   load-displacement and reaction curves, stress/strain measure, energy,
   `det(F)` and residual. Non-comparable decks remain skipped.

These are the only selected routes because their existing external paths can
test the unresolved question without changing QF Solver. The selection is a
campaign recommendation, not a PASS and not an Owner approval of a new
threshold.

## Routes deliberately not selected

- Finite-kinematic J2: the available Code_Aster structural J2 decks use
  `DEFORMATION="PETIT"`; the available CalculiX J2 check is a small-strain
  material-point comparison. A new external run would be misleading until a
  compatible finite-kinematic constitutive reference is identified.
- J2 plus geometry: combining the existing small-strain J2 deck with the TL
  elastic deck would hide the formulation difference rather than measure it.
- Geometry plus contact: the existing comparisons do not share an identical
  penalty/contact surface formulation, so a scalar reaction comparison would
  not isolate the coupled route.
- Triple coupling: it inherits both unresolved blockers and is not a useful
  first external experiment.

## Acceptance boundary

The selected campaigns must declare geometry, units, kinematics, material,
loads, constraints, continuation controls, observables, tolerances and output
digests before execution. Any missing or non-comparable condition is `SKIP` or
`OWNER_REVIEW_REQUIRED`, never an inferred PASS. No universal tolerance is
introduced here.

## G10 disposition

`026-G10` remains `IN_PROGRESS`. Lot 1 can be closed as an audit checkpoint,
but the gate cannot be closed without a formal Owner decision and the evidence
requested for any route that is to receive a stronger maturity classification.
The next action is the two selected, G07-routed external campaigns, subject to
Owner acceptance. Full regression remains skipped by the Lot 1 policy.
