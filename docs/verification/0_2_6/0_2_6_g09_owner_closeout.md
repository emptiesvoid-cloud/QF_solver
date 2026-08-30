# 026-G09 Owner Closeout

## Decision

`026-G09` is closed as **PASS_WITH_LIMITATIONS** for the bounded contact
scope below. The decision does not promote friction, finite sliding, general
surface-to-surface contact, self-contact, a contact tangent across active-set
discontinuities, or any universal penalty policy.

The candidate penalty interval `1e4..1e6` is recorded as
**EXPERIMENTAL_ONLY**. No production interval and no conditioning cutoff are
approved by this closeout.

## Qualified bounded scope

| Item | Scope |
| --- | --- |
| Formulation | Frictionless node-to-triangle penalty |
| Family | TET4 |
| Routes | `linear_static`, `nonlinear_static`, `geometric_nonlinear_static` |
| Search | Initial configuration only |
| Evidence | Lots 1, 2 and 3; bounded Code_Aster unilateral and CalculiX pre-contact comparators |
| Claim | Unilateral contact behavior, load-path transitions, retry/rollback and fail-closed diagnostics for the tested route |

The internal evidence includes 9/9 mesh/penalty rows, 5/5 contact-cycle
paths, controlled retry/rollback, and 6/6 adversarial failure classifications
from Lot 2. Lot 3 adds scalar and TET4 Code_Aster comparisons plus a
CalculiX elastic pre-contact tie-breaker.

## Requirement decisions

| Requirement group | Full | Bounded | Deferred limitation | Blocking |
| --- | --- | --- | --- | --- |
| Lot 1/base | 2 | 5 | 1 | 0 |
| Lot 2 | 2 | 2 | 1 | 0 |
| Lot 3 | 0 | 4 | 1 | 0 |
| Total | 4 | 11 | 3 | 0 |

The complete machine-readable mapping is in
`qualification/0_2_6/g09_owner_closeout.json`.

## External evidence and limitations

Code_Aster agrees with the scalar and active-branch observables within the
declared adapter limits. On the deformable TET4 structural path, the active
branch remains within limits, but exact unilateral and penalty formulations
produce a complete-curve transition warning. The two recorded meshes are:

| Mesh | Overall U error | Overall gap error | Active U error | Transition warning |
| --- | ---: | ---: | ---: | ---: |
| `8x4x4` | `4.339979885207582 %` | `54.99121110155485 %` | `4.024558464266181e-13 %` | `4.339979885207582 %` |
| `6x4x4` | `5.25653195006103 %` | `57.00417573383535 %` | `7.216449660063467e-13 %` | `5.25653195006103 %` |

The second transition warning is above the predeclared `5 %` warning limit
and is retained as a mesh/formulation limitation. CalculiX remains a
pre-contact elastic tie-breaker; it is not a contact-law qualification.

## Explicit exclusions

Friction, finite sliding, general surface-to-surface contact, self-contact,
contact tangent qualification at active-set discontinuities, universal
penalty selection, and contact qualification beyond the tested TET4 route are
excluded. The candidate penalty range remains experimental and all later
contact capabilities require their own evidence.

## Provenance

- Lot 1 execution source: `341ff7111630f6244401ca82addc04414408b9b1`.
- Lot 2 execution source: `341e82d61a2074bd744c84c9c7a9140bd1ac0bb0`.
- Lot 3 execution source: `c76d4af39dc270a05596a53ef2d93baa9171c29b`.
- Evidence head before this closeout: `a4665c19ea5ec699db003686586dc4452b8df752`.
- External tool images and artifact digests are recorded in the Lot 3 manifest.

No functional solver code was modified for this closeout.
