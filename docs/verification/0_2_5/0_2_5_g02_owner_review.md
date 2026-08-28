---
doc_id: DOC-NL-025-028
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: "Owner"
approver: "Owner"
---

# QF Solver 0.2.5a0 Owner review: 025-G02

## Decision identity

| Field | Value |
|---|---|
| Gate | `025-G02` |
| Owner decision | `APPROVED` |
| Mesh decision | `APPROVED_BOUNDED_REFINEMENT` |
| Qualified source SHA | `fec5380db3bcdba13799ce31f3ed042ac5d2557b` |
| Qualified source worktree | `CLEAN` |
| Numerical evidence pack | `results/vnv_0_2_5/g02_latest/` |
| Owner-evidence manifest | `qualification/reviews/qf_solver_0_2_5_g02_owner_evidence_manifest.json` |
| Contract lowered | `NO` |

This is a bounded engineering decision based on the controlled source evidence.
It records the explicit Owner authorization for this gate; it is not a physical
validation, a whole-release decision, or authorization to publish.

## Contract audit

The G02 contract consists of 025-REQ-009 through 025-REQ-013:

- the common Full Newton residual/tangent driver;
- objective geometric kinematics;
- a consistent geometric tangent;
- sparse material and geometric tangent assembly; and
- a large-deformation core for TET4 and HEX8.

The contract assigns TET10/HEX20 to 025-REQ-013A as research evidence and does
not require their qualification for G02. It does not require universal mesh
convergence, a physical-validation claim, or traversal of a load-control limit
point. Post-limit branch following is expressly G04. 025-REQ-030 aggregates
external correlations under G10; the bounded Code_Aster history here is the
supporting G02 external check for the low-order scope, not a closure of G10.

## Evidence assessment

The source pack contains 25 digest-verified artifacts on the qualified source
SHA with `dirty=false`:

- four-family rigid translation, 0.7 rad rotation and combined-motion
  objectivity checks;
- four-family sparse tangent finite-difference checks, including TET4 relative
  error `3.90e-10` and HEX8 relative error `1.13e-09` against their existing
  unit-test contracts;
- TET4 and HEX8 Full-Newton large-rotation paths above 0.5 rad, with positive
  `det(F)` and maximum relative residuals below `4.2e-14`;
- four pre-limit mesh levels for TET4 and HEX8, with every solve successful,
  positive `det(F)`, stable reactions and decreasing late-refinement changes;
- small-strain-limit recovery for all four families; and
- twelve-step, pinned Code_Aster 18.1 histories for TET4 and HEX8. The maximum
  relative errors are below `1.3e-8` for displacement, reaction, stress and
  strain observables.

The Code_Aster deck does not export one common portable energy field. QF strain
energy and internal work are archived internally, but no external energy claim
is made.

## Mesh decision

**`APPROVED_BOUNDED_REFINEMENT`**

The evidence demonstrates a coherent trend in the tested pre-limit domain, not
universal mesh convergence. Both low-order families solved at all four levels;
reaction equilibrium remained stable to numerical precision and the latest
refinement changes decreased to 2.71 percent / 3.54 percent for TET4
displacement / energy and 1.75 percent / 1.75 percent for HEX8. This permits a
bounded use decision without adding an a-posteriori universal acceptance band.

The decision applies only to the recorded geometry, load path, positive-
Jacobian domain and response quantities. It does not imply a convergence result
for arbitrary meshes, loads, material models, instability paths or scales.

## Qualified scope

`owner_accepted_experimental_bounded_use`:

- elastic Total-Lagrangian finite-deformation statics;
- common Full Newton with sparse tangent assembly;
- TET4 and HEX8;
- the documented monotonic, pre-limit test envelope with positive `det(F)`.

The following remain outside this decision: TET10/HEX20 finite-kinematic
behavior, `total_lagrangian_j2`, all finite-kinematic plasticity, post-limit
load control, buckling, arc-length, contact, coupled paths, friction,
multi-million-DOF claims and physical validation.

## Gate decision

`025-G02 = PASS` for the qualified scope above. The source evidence is not
rewritten after the Owner decision, so its pre-Owner `OPEN` status remains part
of the provenance record. The final Owner-evidence manifest identifies the
documentation commit separately from the qualified numerical source SHA.

No other functional gate is closed or promoted by this decision.
