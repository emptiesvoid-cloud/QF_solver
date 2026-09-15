---
doc_id: DOC-029-WP08-OWNER-002
revision: 1.0
status: approved_with_limitations
applicable_version: 0.2.9
---

# WP08 Owner approval

## Decision

The Owner reviewed the frozen WP08 package and accepted **WP08-A through
WP08-E**. WP08 is therefore closed at **8/8 official points** and the official
0.2.9 total moves from **50/100** to **58/100**.

The Owner also authorized the governing push, official-ledger update and merge
of the reviewed lineage only. This record does not authorize a new numerical
run, a modification of gates, or a replacement of evidence.

## Reviewed evidence and provenance

| Item | Immutable reference |
| --- | --- |
| Authorized baseline | `7b93e71bab06a0e58108bd2479cd46808d533b67` |
| Reviewed source tree | `123c46eb6900647679c4b96350dafd4d05efa355` |
| Inspection package | `340a9be695d562dcfd75b5178bc641964795a9fa` |
| Historical M2 FAIL_CLOSED evidence | `45eadb3d9d2c8bc5649c81ec01d351be53e015dc` |
| M2 PASS/reference/replay evidence | `ab64fc5bc9373bb7c12e96d7259cc148a1fe1d8b` |
| M3 PASS/reference/replay evidence | `4f972b5db98cc9313bf0129adaeaa0b218da5375` |

The corresponding direct-inspection and closure records are
[`wp08_owner_review_inspection.json`](../../../qualification/0_2_9/wp08_closure/wp08_owner_review_inspection.json),
[`wp08abcd_closure_final.json`](../../../qualification/0_2_9/wp08_closure/wp08abcd_closure_final.json),
and [`wp08e_closure_final.json`](../../../qualification/0_2_9/wp08e_closure/wp08e_closure_final.json).
The old failure remains historical engineering evidence and is not relabelled
as a pass. No M1/M2/M3 raw evidence is regenerated or overwritten.

## Approved boundary

The approval is restricted to the serial/direct `linear_static`
frictional-contact route, small displacement, fixed initial search/face/normal,
and positive friction coefficient and tangential stiffness.

It explicitly excludes frictional updated search, finite sliding, general
nonlinear-friction qualification, mid-Newton restart, general nonlinear restart
capability, global pressure-coupled tangent consistency, complete global energy
decomposition, external-solver correlation, MPI/PETSc and dynamics
qualification.

## Controls retained

- Thresholds, loads, meshes, material settings, friction parameters, solver
  parameters, iteration limits and fallback policy are unchanged by this
  decision.
- The independent-reference source audit remains part of the reviewed package;
  the M1/M2/M3 references do not import production contact routines.
- The official machine-readable decision is
  [`wp08_owner_approval.json`](../../../qualification/0_2_9/wp08_closure/wp08_owner_approval.json).
