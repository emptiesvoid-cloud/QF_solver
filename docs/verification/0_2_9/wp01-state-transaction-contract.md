---
doc_id: DOC-029-WP01-003
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 accepted-increment state transaction contract

## State model

The future formulation-neutral `NonlinearState` concept contains an accepted
displacement, load factor, material state, contact state, continuation state
and accepted-increment metadata. A detached trial counterpart also carries
iteration metadata.

`begin_trial()` derives the trial view from one accepted state. `commit()`
publishes all components atomically only after global acceptance.
`rollback()` discards the full trial view. No material, contact or continuation
subsystem may publish a committed change by itself.

## Atomicity and failure

Commit is staged and validated before publication. A validation, copying or
persistence-preparation failure leaves the prior accepted composite digest
unchanged, reports `STATE_CORRUPTION` or `CHECKPOINT_FAILURE`, and rejects the
increment. It must not expose a partially committed material/contact state.

The canonical digest includes schema/version plus deterministic encoding of
array dtype, shape and bytes for displacement and each declared state payload.
Every rejected-increment fixture must prove exact equality of all component and
composite committed-state digests before trial and after rollback.

## Checkpoint direction

The later unified checkpoint schema must contain its schema version, model
signature, accepted step, load factor, displacement, material state, contact
state, continuation state, component/composite digests and accepted-increment
metadata. WP01-A does not change current persistence.
