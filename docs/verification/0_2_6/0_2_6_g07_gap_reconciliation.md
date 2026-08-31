# 0.2.6 G07 Step A — Evidence Reconciliation and Gap Analysis

Evidence ID: `026-G07-STEP-A-RECONCILIATION-001`
Reviewed source SHA: `86467fd76a52512d7c9daabbc4d822ac99f96ad0`
Gate status preserved: `026-G07 = NOT_STARTED`
Functional source changed: `NO`

This document records Step A only. It does not execute a new external case,
change a formulation, promote TL or Arc-Length, or close G07. The complete
machine-readable matrix is
[`g07_gap_reconciliation.json`](../../../qualification/0_2_6/g07_gap_reconciliation.json).

## Scope

The candidate TL scope is the existing Total-Lagrangian elastic route on TET4
and HEX8, bounded to the tested domain. TET10 and HEX20 remain research-only.
Arc-Length remains a TET4 `PASS_INTERNAL_RESEARCH` candidate. Finite-kinematic
J2, coupled nonlinear workflows, contact qualification, new formulations and
new physics remain excluded.

## Reconciled route decisions

| Route | Historical state | G10 contribution | Maximum justified claim now | G07 status change |
| --- | --- | --- | --- | --- |
| TL TET4 | `PARKED_PENDING_EXTERNAL_EVIDENCE` | Code_Aster bounded stress-patch and four column points; column stops at 80% of same-mesh critical load | `BOUNDED_CANDIDATE` / `PASS_WITH_LIMITATIONS` pending G07 Owner review | None; no automatic departure from parked |
| TL HEX8 | `PARKED_PENDING_EXTERNAL_EVIDENCE` | Code_Aster path archived, but QF is compared at one matched first point only | Matched-point consistency only; no full-family TL qualification | None; no automatic departure from parked |
| Arc-Length TET4 | `EXPERIMENTAL_NOT_QUALIFIED` | 75 common interpolated points, one turning point per solver, complete selected paths | `PASS_INTERNAL_RESEARCH_BOUNDED` | None; sensitivity/restart evidence still required |

The single HEX8 matched point is sufficient for a local bounded consistency
observation, not for a complete response-history claim. The 75 Arc-Length
points and turning point support a bounded research comparison, but do not
establish production robustness or sensitivity independence.

## Blocking gaps

| Gap | Classification | Smallest future evidence |
| --- | --- | --- |
| `G07-TL-008-TET4-COMPLETE-HISTORY` | `BLOCKING` | Complete compatible QF/Code_Aster TET4 response history over the declared bounded domain |
| `G07-TL-008-HEX8-COMPLETE-HISTORY` | `BLOCKING` | Complete QF instrumented HEX8 path against the existing compatible external path |
| `G07-ARC-002-SENSITIVITY` | `BLOCKING` | Nominal/smaller/larger arc radii and at least two compatible mesh levels |
| `G07-ARC-003-RESTART-ROLLBACK` | `BLOCKING` | One checkpoint, controlled rejected step, digest equality after rollback and deterministic retry |

No blocking case was executed in Step A. The exact future case definitions,
all non-blocking gaps and the `FULL/BOUNDED/INTERNAL_ONLY/NOT_COMPARABLE/MISSING/
SUPERSEDED` classifications are in the JSON artifact.

## Non-blocking and deferred boundaries

The following remain explicit limitations rather than silent passes:

- case-defined small-strain, tangent-FD and mesh policies still require the
  applicable Owner governance; no null threshold was converted into a number;
- external per-step residuals and complete common field measures are valuable
  but not required to support the bounded research interpretation;
- no universal mesh/aspect-ratio threshold or unrestricted large-deformation
  claim is made;
- TET10/HEX20, finite-kinematic J2 and coupled nonlinear/contact claims remain
  outside the G07 candidate scope.

Historical `SKIPPED_NOT_COMPARABLE` external records remain valid descriptions
of their original runs. G10 supersedes only the current availability
observation by adding a pinned Code_Aster pack; it does not supersede the
historical Owner decision that TL promotion requires compatible external
evidence. Rescue/physical-branch diagnostics remain non-comparable to the
default qualification path where their own reports say so.

## Step A conclusion

`G07_STEP_A = PASS` means the reconciliation and gap analysis are complete;
it is not a gate decision. `CAN_PROCEED_DIRECTLY_TO_OWNER_CLOSEOUT = NO` and
`NEEDS_STEP_B = YES`. G07 remains `NOT_STARTED` pending the blocking evidence
and a separate Owner review.
