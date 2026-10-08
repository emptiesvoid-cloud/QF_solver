# WP10 — Legacy nonlinear checkpoint security

## Finding

Schema-v1 checkpoints are decodable and structurally validated, but the v1 model signature is not a complete physical identity. In the inspected implementation, `_signature_payload()` omits concentrated masses and springs, as well as MPC/RBE/contact definitions and a formulation/state version. A match against the current model's v1 signature therefore cannot prove what physical model produced the saved state. For example, adding a concentrated mass or spring leaves the old signature unchanged.

## Policy applied

- `NpzNonlinearCheckpointStore.read_legacy_v1()` is an inspection-only path.
- `load()` rejects v1 restart with the explicit diagnostic `IDENTITY_STATUS=UNPROVEN; FAIL_CLOSED=YES` after structural validation.
- `migrate_v1_checkpoint()` no longer creates a v2 signature using the current model.
- Writing a legacy v1 object through the v2 writer is rejected.
- Existing v1 files are never rewritten, deleted, or modified.
- Corruption, incomplete shape, and identity uncertainty remain distinguishable diagnostics; readable does not imply migratable or resumable.

This is an intentional compatibility boundary, not a claim that every v1 checkpoint is physically wrong. Their original identity is simply not proven strongly enough for scientific continuation.

## Current schema-v2 behavior

The historical full v2 model signature and state topology remain the compatibility authority for existing v2 files. New v2 records additionally bind explicit component identities and corrected-J2 formulation/state/tangent-strategy versions. A legacy v2 record without those new component digests is not retroactively upgraded or described as carrying them.

The NPZ writer retains its temporary-file/atomic-replace path and `allow_pickle=False`. New schema-v2 records also carry a canonical metadata digest over the complete metadata object, including identity digests and formulation provenance. Tampering with or removing those claims without a matching digest is detected. Existing v2 files without the metadata digest remain governed by their original state digests, full model signature, and topology contract; no retroactive metadata digest is claimed. SHA-based digests detect accidental corruption; they are not keyed signatures and do not establish authenticity against a maliciously edited checkpoint.

## Evidence and tests

The WP10 tests construct v1 files, demonstrate that mass/spring mutations preserve the incomplete v1 hash, and assert that resume is refused. v1 inspection remains available. Existing arc-length tests that formerly expected transparent v1 promotion now assert that the file remains untouched and no v2 output is written. v2 tests exercise mutations of masses, springs, materials, BCs, mesh, and loads.

See `wp10_checkpoint_identity_migration_contract.json`, `wp10_restart_equivalence_evidence.json`, and `tests/unit/test_wp10_nonlinear_state_checkpoints.py`.

## Operational consequence

If a user has only a v1 checkpoint, safe options are to inspect it read-only and restart from an earlier known-good accepted state or rerun the analysis. WP10 intentionally does not guess missing masses, springs, contact history, or formulation identity.
