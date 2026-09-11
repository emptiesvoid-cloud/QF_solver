---
doc_id: DOC-029-012
revision: 0.1
status: controlled
applicable_version: 0.2.9-development
---

# WP02-C — fixed and adaptive restart migration

> Implementation evidence, not a release claim. The 0.2.8 release, its
> published artifacts and its historical evidence remain unchanged.

Baseline: `2e542d4beff9c0906f2125c62107d3f56b12ddf8`

Final implementation SHA: reported by the final gate record (not embedded
self-referentially in this evidence file).

The detached-start targeted baseline inventory is recorded in
`qualification/0_2_9/wp02_c_baseline.json`.
It covers the fixed/adaptive J2, geometric, contact and failure-control
regression contracts without claiming unrecorded displacement vectors.

## Scope

WP02-C moves fixed and adaptive nonlinear restart ownership to the schema-v2
accepted `NonlinearState` boundary. It does not redesign a mechanical
formulation, migrate frictional contact or close the complete arc-length
restart gate; those remain outside this step.

The migrated public routes are:

- fixed nonlinear static, including small-strain J2, modified Newton and
  frictionless penalty composition;
- adaptive nonlinear static with accepted load-factor and next-increment
  continuation state;
- fixed and adaptive public geometric nonlinear TET4/HEX8 routes, using the
  existing total-Lagrangian assembly and Newton kernels.

The arc-length route uses the shared checkpoint session compatibility boundary,
but complete interrupted/restarted arc-length equivalence remains WP02-D.

## Composite restore/save boundary

`NonlinearCheckpointSession.restore_state` first decodes and validates the
checkpoint, then returns one detached accepted `NonlinearState`. Signature,
DOF/material topology, contact compatibility, continuation requirements and
component/composite digests are checked before the solver receives the state.
Failed restore therefore cannot progressively mutate the active runtime state.

`NonlinearCheckpointSession.save_state` accepts only a detached, validated
accepted state and writes schema v2. The fixed and adaptive solver callbacks
run after the unified transaction has accepted the increment. Rejected trials
and failed cutback attempts are never passed to the checkpoint writer.

Legacy `restore`, `restore_continuation` and `save` methods remain as
compatibility wrappers delegating to the composite API. They are not a second
restart authority. `deterministic_state_digest` remains the persisted identity.

Adaptive accepted continuation metadata distinguishes physical accepted state
from next-trial policy state. It records the accepted step, current factor,
next proposed increment and policy identifier. A variable number of accepted
steps caused by cutbacks is valid; the completed step in the checkpoint is the
authoritative restart position.

## v1 solver compatibility

The bounded Owner decision remains `READ_V1_WRITE_V2_BOUNDED`:

- contact-free v1 solver restarts are read and migrated in memory;
- frictionless/stateless penalty routes are accepted only when the current
  model proves that no missing contact history is needed;
- ambiguous or stateful-contact v1 files are rejected;
- a resumed run writes schema v2 on its next checkpoint.

No historical contact state is invented. A checkpoint save failure is reported
as `CHECKPOINT_FAILURE` after physical acceptance and does not trigger a
physical load cutback. Wrong signatures/topologies remain input validation
errors; digest mismatches remain `STATE_CORRUPTION`.

## Targeted evidence

The focused WP02-C suite is:

```text
python -m pytest -q tests/unit/test_wp02_c_restart_migration.py
25 passed
```

The exact targeted regression groups were run separately:

```text
python -m pytest -q tests/unit/test_wp02_b_checkpoint_v2.py
28 passed

python -m pytest -q tests/unit/test_nonlinear_checkpoint.py
10 passed

python -m pytest -q tests/unit/test_analysis_features.py tests/unit/test_geometric_nonlinear_public.py -k "adaptive_load_steps or nonlinear_adaptive"
2 passed, 35 deselected

python -m pytest -q tests/unit/test_analysis_features.py tests/unit/test_total_lagrangian_j2.py -k "von_mises or j2 or elastoplastic"
22 passed, 29 deselected

python -m pytest -q tests/unit/test_geometric_nonlinear_public.py tests/unit/test_geometric_nonlinear_contracts.py
15 passed

python -m pytest -q tests/unit/test_nonlinear_contact_composition.py
11 passed

python -m pytest -q tests/unit/test_nonlinear_failure_modes.py
20 passed

python -m pytest -q tests/unit/test_unified_nonlinear_foundation.py tests/unit/test_nonlinear_state_transaction_contract.py tests/unit/test_wp01_d_continuation.py
46 passed
```

The fixed/adaptive comparisons use relative `1e-9` with absolute floor
`1e-12`; persisted state digest comparisons use exact equality. The complete
repository suite was not run.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G02-01 | PASS | Fixed/adaptive routes persist a complete accepted composite state. |
| G02-02 | PASS | Restart checkpoints preserve component and composite digests. |
| G02-03 | PASS_BOUNDED | Fixed and adaptive interrupted/restarted cases agree for J2, modified Newton, penalty composition and public geometric TET4/HEX8 routes. |
| G02-04 | PENDING_WP02-D | Complete arc-length path restart is not part of WP02-C. |
| G02-05 | PASS | Signature, topology, digest and v1 failure distinctions remain explicit. |
| G02-06 | PASS | Solver saves occur after acceptance and use the atomic v2 store. |
| G02-07 | PASS_BOUNDED | v1 solver read/migration and v2 resume output are covered. |
| G02-08 | PASS_FIXED_ADAPTIVE_BOUNDARY | Legacy solver helpers delegate; no second fixed/adaptive checkpoint authority exists. |
| G02-09 | PASS_FIXED_ADAPTIVE_BOUNDARY | Trial and rejected retry state never reaches the checkpoint callback. |
| G02-10 | PASS_BOUNDED_FIXED_ADAPTIVE_SCOPE | Existing targeted J2/geometric/contact/failure behavior remains within frozen thresholds. |

WP02 remains **0/6 points** pending WP02-D and independent WP02-E closure.
The validated roadmap remains **16/100**. OD-029-01 remains OPEN and blocks
WP09 only; OD-029-02 remains CLOSED. No numerical formulation, maturity or
historical evidence changed.
