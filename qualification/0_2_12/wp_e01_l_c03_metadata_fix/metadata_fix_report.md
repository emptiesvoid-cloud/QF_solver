# WP-E01-L-C03-METADATA-FIX

## Cause and decision lifecycle

`archive_inputs.py` creates an extraction-stage inventory before branch-linkage
proof evaluation. Its earlier provisional `reason` described that intermediate
state. `integrate_proofs.py` later derived the eight action proofs and a
technical aggregate `PASS`, but the extraction reason and action-level flags
were left stale. The Owner's promotion decision is a separate layer and is not
encoded as an automatic consequence of the proof evaluator's `PASS`.

The corrected inventory retains the extraction explanation under
`extraction_stage.reason`. The final technical `reason`, readiness flag, and
aggregate are derived from the same verified proof decision. Action-level
linkage and rounding-budget flags are derived from every point's production
gate. A partial set of known extraction actions is `INCONCLUSIVE`; duplicate
or unknown identities remain `INVALID_PROTOCOL`.

## Independent-review findings and fixes

The first targeted Sol 6.1 review blocked promotion on three metadata-control
gaps. The candidate now:

1. Binds current archive manifest hashes, file counts, paths, and campaign
   statuses to the identities preserved in the pre-fix inventory.
2. Binds current adapter commit/tree/file hashes and historical source-file
   hashes to the preserved capture identities.
3. Keeps missing extraction rows inconclusive and derives action flags from
   pointwise production evidence, avoiding a `true` flag beside an
   inconclusive action.

Regression tests cover each condition. A second independent review of these
changes is required before the separately authorized bounded promotion.

## Metadata-only finalization

`finalize_inventory.py` verifies the frozen archives and historical checkout,
both sets of 29 production pins, source and adapter identities, and the 16
hash-bound proof inputs/results. It validates serialized root inequalities,
point identities, branch records, and action counts, then regenerates
`archive_inventory.json`. It does not evaluate J2, run FEM, or alter a proof
input/result. Two successive runs produce the same inventory SHA-256.

The original proof directory remains unchanged: all 37 files match its
preserved manifest. The 16 proof input/result files in this candidate match
the originals byte-for-byte. The original manifest and extraction inventory
are preserved here as `artifact_manifest.pre_metadata_fix.json` and
`archive_inventory.pre_metadata_fix.json`.

## Verification

- Technical aggregate: `PASS`; 8/8 actions and 304/304 point proofs.
- Historical snapshot: commit `87e54913077c7d9fce6f259fb4a4a11f5295e6a5`,
  tree `c42e3c2241af1862d66cab51a38fda74a1167361`, clean checkout.
- Production pins: 29/29 verified in each archive; both archives and adapter
  captures are bound to the pre-fix identities.
- Tests: 57/57 isolated `unittest` tests passed, comprising the 44 existing
  mathematical regressions and 13 metadata regressions. No pytest, solver, or
  FEM campaign was run for this correction.
- The worker's earlier pytest deviation remains in `process_deviations.md`.
- Scientific scope remains exactly the eight archived actions, fixed incoming
  histories, and segments `[-1/10000, +1/10000] m`. No C04-C06 or global J2
  tangent claim is added.

## Status

The final independent review returned `ACCEPT`, and the Owner's previously
given conditional authorization is satisfied. The separate
`c03_certificate_promotion_record.json` records only
`C03_BRANCH_STABILITY=CERTIFIED_BOUNDED`.

`archive_inventory.json` intentionally retains the proof evaluator's
`certificate_status=PROPOSED_NOT_PROMOTED`: that output records the evaluator
stage and forbids automatic promotion. The separate Owner record is the
promotion layer. It does not change any proof, scientific identity, or scope.
The global J2 tangent qualification, C04-C06, RUN, merge, and release remain
unapproved or unauthorized as stated in the promotion record.
