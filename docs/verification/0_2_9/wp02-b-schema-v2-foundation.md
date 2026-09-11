---
doc_id: DOC-029-011
revision: 0.1
status: controlled
applicable_version: 0.2.9-development
---

# WP02-B — checkpoint schema v2 foundation

> Implementation evidence, not a release claim. The 0.2.8 release and its
> historical evidence remain unchanged.

## Scope and decision

WP02-B implements the persistence foundation only. It does not migrate full
fixed/adaptive solver restart ownership or the complete arc-length restart
path; those remain WP02-C and WP02-D. Owner decision OD-029-02 is closed as
`READ_V1_WRITE_V2_BOUNDED`:

- contact-free schema-v1 checkpoints may migrate;
- stateless-compatible penalty-contact v1 checkpoints may migrate only when
  compatibility is proven from the current model;
- ambiguous or stateful contact-history-dependent v1 checkpoints are rejected;
- no missing contact history is invented;
- all new writes are schema v2.

## Implemented boundary

`NonlinearCheckpointV2` stores exactly one accepted `NonlinearState` with:

- displacement and load factor;
- material, contact and continuation state;
- accepted-increment metadata;
- model signature and accepted-step number;
- state topology;
- six component digests and one composite digest.

The NPZ adapter uses a declared `schema_version`, tagged deterministic
serialization, NumPy dtype/shape/C-order bytes, and `allow_pickle=False`.
Mapping entries are canonically ordered, so insertion order and Python hash
randomization do not affect identity. Integer and string mapping keys remain
distinct.

On load, the adapter decodes and validates the state, recomputes all digests,
and rejects a mismatch as `STATE_CORRUPTION`. Invalid containers, unsupported
schemas, model mismatches and topology mismatches are input errors. A failure
while writing a valid accepted state is `CHECKPOINT_FAILURE`; it does not
trigger a physical cutback.

Canonical persistence is prepared in a same-directory temporary file, flushed
and fsynced where supported, then atomically replaced. Retained-step copies
are made only after the canonical file exists. A retained-copy failure reports
that canonical persistence succeeded.

## Targeted evidence

The focused WP02-B suite covers v2 round-trip, dtype/shape preservation,
nested material/contact/continuation payloads, component and composite digest
integrity, corruption and non-finite rejection, model/DOF/material topology,
bounded v1 migration/rejection, atomic-write failure, retained steps,
deterministic writes, pickle rejection and adversarial mapping keys.

Recorded targeted results at the implementation baseline are:

```text
python -m pytest -q tests/unit/test_wp02_b_checkpoint_v2.py
28 passed

python -m pytest -q tests/unit/test_nonlinear_checkpoint.py \
  tests/unit/test_nonlinear_contracts.py \
  tests/unit/test_nonlinear_failure_modes.py \
  tests/unit/test_unified_nonlinear_foundation.py \
  tests/unit/test_nonlinear_state_transaction_contract.py \
  tests/unit/test_nonlinear_composite_assembly.py \
  tests/unit/test_nonlinear_contact_composition.py
73 passed
```

The complete repository suite was not run. Solver-level fixed/adaptive and
arc-length restart equivalence are deliberately pending WP02-C/WP02-D.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G02-01 | PASS | v2 represents the accepted composite state and topology. |
| G02-02 | PASS | Round-trip component/composite digests are exact. |
| G02-03 | PENDING_WP02_C | Full fixed/adaptive interrupted-run equivalence. |
| G02-04 | PENDING_WP02_D | Full arc-length interrupted-run equivalence. |
| G02-05 | PASS | Integrity and failure distinctions are deterministic. |
| G02-06 | PASS | Canonical write is atomic at the storage boundary. |
| G02-07 | PASS_BOUNDED | v1 migration follows the closed Owner policy. |
| G02-08 | PASS_AT_PERSISTENCE_BOUNDARY | Legacy helpers do not define v2 identity. |
| G02-09 | PASS_AT_STORAGE_BOUNDARY | Only accepted composite state is serialized. |
| G02-10 | PENDING_LATER_MIGRATION | Existing route preservation remains a later closure gate. |

WP02 remains **0/6 points** and the validated roadmap total remains **16/100**.
No numerical formulation, maturity status or historical evidence changed.
