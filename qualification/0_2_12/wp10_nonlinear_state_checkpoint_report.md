# WP10 — Nonlinear accepted states, checkpoint migration, and convergence

## Scope and baseline

WP10 is limited to accepted nonlinear state transactions, restart identity and migration, convergence truthfulness, and regression evidence. It does not change constitutive equations, contact formulations, the WP09 tangent, the Newton algorithm, or the dynamic routes. The implementation branch is based on WP09 commit `eb3dde63d487f5a88f9dd34e043ca561407018f7`; the published `v0.2.11` target remains `afd2efa469a18e66581720ff4801f50de7d29eb4`.

The work reuses `NonlinearStateTransaction`, schema-v2 `NonlinearCheckpointV2`, `NpzNonlinearCheckpointStore`, and existing Newton/continuation controllers. It introduces no replacement checkpoint framework.

## Confirmed defects and bounded corrections

1. The schema-v1 signature (`_signature_payload`) did not bind concentrated masses, springs, multipoint constraints, rigid links, contacts, or formulation state. Reconstructing a schema-v2 signature from the current model could therefore attach facts to a historical state that the file never proved. The v1 reader is now read-only; v1 promotion and restart fail closed as `IDENTITY_STATUS=UNPROVEN`. Valid v1 data remain inspectable through `read_legacy_v1()`.
2. New schema-v2 writes now require a transaction-attested `ACCEPTED` lifecycle marker and consistent accepted-step counters. A trial, unmarked state, or inconsistent composite state cannot be saved. Existing schema-v2 files with no lifecycle marker may still resume only under their original `accepted_state` declaration and after the full historical model signature and topology match; no new lifecycle attestation is written back into those files. Any subsequent checkpoint write must be newly attested.
3. New model-bound checkpoints record domain-separated physical, operator, constitutive, load, execution, and schema digests. The existing complete v2 model signature remains the compatibility authority. A load-only mutation changes load/execution identity without invalidating the operator identity; a physical mutation changes the physical signature. A checkpoint written without a bound model is explicitly `UNBOUND` and cannot satisfy a later model-bound identity check.
4. Corrected corotational-J2 checkpoint metadata also binds the WP09 tangent-strategy version. Corrected/legacy formulation and state versions remain non-interchangeable.
5. Adaptive load control and arc-length checkpoints now retain the already-existing compact rejection log with accepted state. Trial material/contact state is not added to that log. This preserves the rejected-increment reason across restart without changing acceptance criteria.

The Newton residual normalization and public tolerances were audited and intentionally left unchanged. The implementation uses the established absolute floor `max(||target_free||, force_scale, 1.0)` for relative residual reporting/acceptance; this avoids division by zero at zero load and reduces to an absolute residual criterion below unit force scale. This is unitful historical behavior, not a new scale-invariant criterion. No maximum-iteration or failed constitutive/linear-solver path is promoted to convergence.

## State lifecycle

`NonlinearStateTransaction` deep-detaches the accepted composite state, opens a detached trial marked `TRIAL`, checks that the accepted digest did not change while the trial was open, validates a detached candidate, and publishes it as a single accepted composite on commit. Rollback drops the trial and leaves the accepted digest unchanged. The Newton driver attaches the accepted step number before commit. Save paths merge continuation metadata rather than replacing the lifecycle marker and rejection history.

Checkpoint persistence is an accepted-state boundary, not a way to accept an iteration. `NonlinearCheckpointSession.save_state()` and the NPZ store validate the lifecycle marker, state, and step counters. The older scalar `save()` helper cannot attest transaction acceptance and now refuses with an explicit diagnostic; callers must provide the complete accepted `NonlinearState`.

See [the state transaction contract](wp10_state_transaction_contract.json) for the component mutation, commit, rollback, and persistence rules.

## Identity and migration policy

| Data | Verification source | Resume treatment |
|---|---|---|
| Schema v1 | Historical signature lacks discrete and formulation inputs | Read-only; `UNPROVEN`; restart/migration refused |
| Existing schema v2 | Full v2 model signature and topology; schema declares accepted-state payload | Readable/resumable only if the stored full signature/topology match; no retroactive component digests are invented |
| New schema v2 | Full v2 signature, topology, state digests, and explicit component identities | Resume only when all stored identities, formulation metadata, and counters match |
| Corrected J2 | Corrected formulation ID, constitutive-state version, and tangent strategy version | Cross-formulation/version restart refused |

New v2 metadata has a canonical digest binding the full checkpoint metadata, including identity records, in addition to the accepted-state component/composite digests. Existing v2 files without this metadata digest remain readable under their original full model signature/topology contract and do not gain a retroactive digest. These SHA-based digests detect accidental/corrupt content changes; they are not keyed authenticity signatures. Atomic temp-file replacement is preserved. No historical checkpoint is rewritten or deleted.

Full identity and migration rules are in [the identity contract](wp10_checkpoint_identity_migration_contract.json) and [the legacy security report](wp10_legacy_checkpoint_security_report.md).

## Convergence and failure reporting

Newton convergence remains governed by the existing residual/increment rules and tolerances. On success, the accepted composite is committed before a checkpoint is emitted. At maximum iterations, constitutive failure, tangent failure, or linear-solver failure, the failure status remains non-converged. A cutback may later accept a smaller increment, but the rejected attempt remains in the rejection diagnostics. Restart restores those diagnostics so it does not erase the failed attempt's provenance.

Zero load uses a finite residual denominator with the pre-existing unit floor. A zero residual can converge; a nonzero residual is judged against the configured absolute tolerance in that scale regime. No change to public convergence thresholds was made.

## Validation evidence

The final complete unit suite reports **3346 passed, 93 skipped, 0 failed** in 1360.59 s. The documentation suite reports **88 passed, 6 skipped**. A separate impact-focused regression set reports **221 passed**, and the final WP10 checkpoint/continuation matrix reports **241 passed**. Exact commands/statuses are listed in `wp10_nonlinear_regression_matrix.json`.

The bounded before/after microbenchmark uses the same single TET4 fixture, 12 physical DOFs, empty material-state payload, 100 snapshot/transaction samples and 30 signature/save/load samples. Medians (ms) were: detached snapshot `0.0203 → 0.0175`; begin-trial/rollback `0.1883 → 0.1987`; model signature `0.0705 → 0.0685`; checkpoint save `4.0195 → 4.4482`; checkpoint load `0.8360 → 1.1954`. The file grew `1300 → 1917` bytes. These tiny local measurements are noisy and only expose the identity/integrity-digest overhead; they do not establish scaling or global Newton cost. Detailed context is in `wp10_performance_characterization.md`.

Ruff lint and formatting pass on changed Python files. Targeted mypy reports 27 existing diagnostics versus 30 at the exact WP09 baseline; no new diagnostic was introduced, and three old diagnostics concerning `_rejection_log` initialization or the removed scalar writer disappeared. The targeted type check is therefore **not clean**, despite no WP10-added errors. Full counts and classifications are recorded in the regression matrix.

## Roadmap and preserved decisions

Owner-approved expanded order is recorded separately in `wp10_roadmap_amendment_owner_approved.md`; WP00/WP01 historical records are not edited. WP10 creates a handoff for WP-C01 only. It does not start WP-C01, WP-D01, WP-D02, WP11, WP12, or WP13.

The following remain unchanged: `WP08_STATUS=PASS_BOUNDED`, `WP09_STATUS=PASS_BOUNDED`, `CORRECTED_J2_MATURITY=EXPERIMENTAL`, `HISTORICAL_G03=FAIL_PRESERVED`, `HISTORICAL_WP14=HOLD_NOT_PROMOTED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED=NO`, and `RELEASE_PUBLICATION_AUTHORIZED=NO`. Release-wide QF0212 gates remain open.

## Residual limitations

- Schema-v1 checkpoints are readable but cannot safely restart; users must restart from an accepted schema-v2 checkpoint or rerun from an earlier trustworthy state.
- Schema-v2 content digests are integrity checks, not signatures against a maliciously edited file.
- Existing schema-v2 checkpoints predate explicit component identity digests; their resume remains governed by the complete historical v2 model signature and topology and does not gain retroactive identity claims.
- The residual log is persisted with each accepted continuation state; long runs with many rejections may increase checkpoint payload and copy cost.
- Convergence tolerances remain existing unitful contracts; WP10 did not redesign scaling or general nonlinear convergence theory.
- No global qualification or general Newton/contact robustness claim follows from these bounded checks.
