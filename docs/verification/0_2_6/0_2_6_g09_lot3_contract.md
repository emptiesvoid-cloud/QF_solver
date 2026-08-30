# 026-G09 Contact Lot 3 Contract

Lot 3 adds controlled external evidence and penalty-policy review to the
bounded Lot 1/Lot 2 contact scope. It does not add contact physics and does
not silently close the official gate.

## Bounded scope

- QF frictionless node-to-triangle penalty contact on the existing TET4 path.
- Initial-configuration contact search and the common static/nonlinear driver
  already covered by Lots 1 and 2.
- Code_Aster 18.1.0 is used as an exact unilateral-constraint comparator for
  normal kinematics and a controlled TET4 structural path.
- CalculiX 2.20 is used only as an independent elastic pre-contact tie-breaker.

The Code_Aster `LIAISON_UNIL` formulation is not numerically identical to the
QF penalty law. Therefore this lot qualifies only the declared unilateral
operator and bounded structural response; it does not qualify a penalty law,
contact tangent, general surface search or penalty selection universally.

## Requirements

| ID | Requirement | Policy | Status |
| --- | --- | --- | --- |
| `G09-L3-001` | Scalar unilateral open/close and active planar TET4 comparison | Existing adapter limits; active state distinction retained | PASS_WITH_LIMITATIONS |
| `G09-L3-002` | Ten-point bounded structural contact-path comparison | Full displacement/gap curves; transition mismatch retained | PASS_WITH_LIMITATIONS |
| `G09-L3-003` | CalculiX pre-contact tie-breaker | Pre-contact elastic displacement only | PASS_WITH_LIMITATIONS |
| `G09-L3-004` | Bounded penalty governance | Candidate `1e4..1e6` only in the tested Lot 2 TET4 domain | OWNER_REVIEW_REQUIRED |
| `G09-L3-005` | Lot aggregation and limitations | No unsupported capability is counted as PASS | PASS_WITH_LIMITATIONS |

The machine-readable contract and case map are
`qualification/0_2_6/g09_lot3_requirements.json` and
`qualification/0_2_6/g09_lot3_case_registry.json`.

## Execution and provenance

The final external runs were executed from a clean detached checkout at
source SHA `c76d4af39dc270a05596a53ef2d93baa9171c29b`, with generated output
outside the repository. Each external `vnv_manifest.json` reports
`source_dirty=false`. The pinned images are recorded in the evidence JSON.

## Owner policy point

Lots 1 and 2 support the experimental candidate interval `1e4..1e6` for the
tested TET4 initial-search benchmark. This is not a universal production
range, and no conditioning cutoff is approved. The candidate remains
`OWNER_REVIEW_REQUIRED` until the Owner explicitly accepts or rejects that
bounded governance statement.

## Explicit exclusions

Friction, finite sliding, general surface-to-surface contact, self-contact,
contact tangent qualification at active-set discontinuities, and universal
penalty/conditioning policies remain outside this lot. Official G09 closure
requires the Owner decision recorded separately from this contract.
