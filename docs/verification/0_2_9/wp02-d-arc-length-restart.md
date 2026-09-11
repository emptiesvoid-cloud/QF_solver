---
doc_id: DOC-029-013
revision: 0.1
status: controlled
applicable_version: 0.2.9-development
---

# WP02-D — arc-length restart migration

> Implementation evidence, not a release claim. The 0.2.8 release, its
> published artifacts, historical evidence and maturity records remain
> unchanged.

## Scope and baseline

The migration starts from `aafb164a4a20189dc27fb4c0968358d5463f13e6` on
`0.2.9-unified-nonlinear`. The targeted baseline is recorded in
`qualification/0_2_9/wp02_d_baseline.json`; inherited numeric/path records are
referenced from `qualification/0_2_9/wp01_d_baseline.json` rather than copied
or rewritten.

WP02-D changes only restart ownership and checkpoint integration for the
public arc-length route. It does not change the augmented arc-length
correction mathematics, element formulations, tolerances, maturity or the
0.2.8 evidence set.

## Accepted-state boundary

The public route now restores with
`NonlinearCheckpointSession.restore_state(...)` and receives one detached
accepted `NonlinearState`. Its continuation payload validates:

- accepted step and load factor;
- positive radius, maximum radius and load scale;
- finite `previous_du` with the free-DOF shape;
- finite `previous_dlambda`;
- target/stop/turning/control-DOF compatibility where stored.

The `UnifiedContinuationController` remains the only accepted-state authority.
The specialized `solve_arc_length_correction` kernel computes the augmented
correction but cannot publish a global state. After convergence, the order is:

```text
correction convergence
  -> trial continuation state finalized
  -> controller.commit()
  -> controller.accepted_state is authoritative
  -> save_state(step, accepted_state)
```

Rejected predictors and correctors are rolled back before radius shrink. A
retry radius is next-trial policy state; it never overwrites the last accepted
checkpoint. A checkpoint write failure is reported after physical acceptance
as `CHECKPOINT_FAILURE`; it does not trigger a physical radius cutback or
rollback.

## Restart and compatibility

Schema-v2 checkpoints carry displacement, load factor, material state, empty or
stateless contact state, continuation state, accepted metadata, topology and
component/composite digests. The accepted continuation fields are
`accepted_step`, `load_factor`, `radius`, `maximum_radius`, `load_scale`,
`previous_du` and `previous_dlambda`; policy fields are retained when
available for compatibility validation.

The legacy `restore_continuation` and `save` methods remain compatibility
delegates. They are not called by the public arc-length persistence path.
Schema-v1 arc checkpoints are accepted only when the required direction and
radius history is present and current contact compatibility is provable. An
incomplete or stateful-contact v1 checkpoint is rejected; missing history is
never synthesized. A resumed v1 run writes schema v2 on its next accepted
checkpoint.

## Targeted evidence

The focused WP02-D test file contains T02D-01 through T02D-28:

```text
python -m pytest -q tests/unit/test_wp02_d_arc_length_restart.py
28 passed
```

Separate regression groups were run without the full repository suite:

```text
python -m pytest -q tests/unit/test_wp02_b_checkpoint_v2.py
28 passed

python -m pytest -q tests/unit/test_wp02_c_restart_migration.py
25 passed

python -m pytest -q tests/unit/test_analysis_features.py -k "arc_length"
3 passed, 27 deselected

python -m pytest -q tests/unit/test_nonlinear_checkpoint.py
10 passed

python -m pytest -q tests/unit/test_wp01_d_continuation.py -k "arc_length"
7 passed, 15 deselected

python -m pytest -q tests/unit/test_nonlinear_failure_modes.py tests/unit/test_nonlinear_failure_campaign.py
21 passed

python -m pytest -q tests/unit/test_nonlinear_contact_composition.py
11 passed

python -m pytest -q tests/unit/test_analysis_features.py -k "tet4 or hex8 or j2 or geometric_nonlinear"
4 passed, 26 deselected
```

Qualification/documentation guards also passed (`12 passed` and `4 passed`).
Ruff and relevant `compileall` checks passed. Five qualification JSON files
validated, and `mkdocs build --strict -f .github/pages/mkdocs.yml` passed.
The targeted mypy command reports the same 15 pre-existing mixin/type-shape
diagnostics at the detached baseline and after WP02-D; no new diagnostics
were added in the checkpoint, solver or test files.

The focused tests cover composite restore/save ownership, commit-before-save
ordering, monotonic/turning/adaptive-radius/rejection restart paths, exact
continuation digests, v1 migration and rejection, retained accepted-step
files, checkpoint-failure semantics and legacy delegation. Physical/path
comparisons use relative `1e-9` with absolute floor `1e-12`; persisted
component and composite identities are compared exactly.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G02-01 | PASS | Arc-length accepted state is complete at the v2 boundary. |
| G02-02 | PASS | Component and composite digests are exact after restore. |
| G02-03 | PASS_BOUNDED | WP02-C fixed/adaptive restart evidence remains valid. |
| G02-04 | PASS_BOUNDED | Supported monotonic, turning-policy, adaptive-radius and rejection/retry paths restart equivalently. |
| G02-05 | PASS | Corruption, incomplete continuation and failure distinctions remain explicit. |
| G02-06 | PASS | Save occurs after commit and uses the atomic v2 store. |
| G02-07 | PASS_BOUNDED | Supported v1 arc input migrates; incomplete input is rejected. |
| G02-08 | PASS | Legacy arc helpers delegate and do not define persistence authority. |
| G02-09 | PASS | Rejected arc trials never produce retained checkpoint state. |
| G02-10 | PASS_BOUNDED | Targeted arc-length, fixed/adaptive, J2, geometric and contact regressions remain green. |

WP02 remains **0/6 points** and the validated roadmap remains **16/100**.
Final closure is intentionally deferred to the independent WP02-E audit.
Frictional-contact restart, distributed restart and nonlinear dynamics remain
out of scope. The next permitted step is Owner review followed by WP02-E;
WP03 must not start from this record.
