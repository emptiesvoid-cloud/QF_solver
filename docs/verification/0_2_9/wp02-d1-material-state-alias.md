---
doc_id: DOC-029-014
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
---

# WP02-D1 — arc-length restart material-state ownership

> Focused remediation evidence. This record does not close WP02-D or award
> WP02 points. The 0.2.8 release, historical evidence and maturity records are
> unchanged.

## Finding reproduced

The issue was reproduced from
`13e378827a94eb909758c32d29b0757b3691c0c6` with a path-dependent
`total_lagrangian_j2` TET4 arc-length run restarted from accepted step 2.
The restarted displacement was identical to the continuous run and the final
checkpoint contained the correct accepted material digest, but the returned
`SolveResult.material_states` digest was stale.

Before the fix the observed values were:

| Observation | Digest |
| --- | --- |
| Continuous final material state | `71b080b614da0c58b890b8a2cdb35f32da4701587b2c127aea9111164e69af09` |
| Restarted caller-visible material state | `5460956c65025426774696b07a1408b0ddc0e193559737f600e26b75498a72b3` |
| Restarted final checkpoint material state | `71b080b614da0c58b890b8a2cdb35f32da4701587b2c127aea9111164e69af09` |
| Final displacement maximum difference | `0.0` |

This isolated the defect to the caller-visible material mirror, not to the
controller's accepted state, checkpoint content, or numerical displacement.

## Root cause and fix

During arc-length restore, `_solve_arc_length` rebound its local
`material_states` parameter to a detached copy. The outer
`NonlinearStaticSolver` therefore retained the pre-resume object while the
controller and checkpoint path advanced a different object.

The minimal fix in
`src/solveur/core/nonlinear/arc_length.py` updates the caller-owned mirror in
place with:

```python
commit_material_states(material_states, restored_state.material_state)
```

No constitutive law, geometric/contact formulation, tolerance, checkpoint
schema, maturity status or historical evidence was changed. Trial state
remains detached and the controller remains the accepted-state authority.

## D1 focused checks

`tests/unit/test_wp02_d1_arc_length_material_state.py` contains the ten
required checks:

```text
python -m pytest -q tests/unit/test_wp02_d1_arc_length_material_state.py
10 passed
```

The checks demonstrate caller synchronization after one and multiple accepted
increments, exact rollback across an injected rejection, path-dependent
continuous/restarted material equivalence, final post-processing and tangent
assembly inputs, final checkpoint identity, and elastic regression safety.

## Targeted regression inventory

The following targeted commands passed; the full repository suite was not run:

```text
python -m pytest -q tests/unit/test_wp02_b_checkpoint_v2.py
28 passed

python -m pytest -q tests/unit/test_wp02_c_restart_migration.py
25 passed

python -m pytest -q tests/unit/test_wp02_d_arc_length_restart.py
28 passed

python -m pytest -q tests/unit/test_analysis_features.py -k "arc_length"
3 passed, 27 deselected

python -m pytest -q tests/unit/test_nonlinear_checkpoint.py
10 passed

python -m pytest -q tests/unit/test_wp01_d_continuation.py
22 passed

python -m pytest -q tests/unit/test_nonlinear_failure_modes.py tests/unit/test_nonlinear_failure_campaign.py
21 passed

python -m pytest -q tests/unit/test_geometric_nonlinear_public.py
7 passed

python -m pytest -q tests/unit/test_nonlinear_contact_composition.py
11 passed

python -m pytest -q tests/unit/test_total_lagrangian_j2.py
21 passed
```

WP02 remains at `0/6` and the validated roadmap remains `16/100`. WP02-E
independent closure is still required. OD-029-01 remains OPEN; no WP03 work is
authorized by this record.

## Integrity boundary

`NUMERICAL_FORMULATION_CHANGED = NO`
`ELEMENT_FORMULATION_CHANGED = NO`
`MATURITY_CHANGED = NO`
`FULL_TEST_SUITE_RUN = NO`
