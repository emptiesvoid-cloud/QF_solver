---
doc_id: DOC-029-WP03-009
revision: 0.1
status: controlled
applicable_version: 0.2.9-development
---

# WP03-C — adaptive policy baseline

> **Pre-edit baseline, not a release claim.** This record freezes adaptive
> increment/retry observations at `e2f3e07310b4348c01ee68f764de0f986436995e`.
> Arc-length radius policy is outside WP03-C.

## Structured observations

The stateful easy case used the existing controls and produced accepted
increments `[0.25, 0.5, 0.25]` at load factors `[0.25, 0.75, 1.0]`, with zero
rejections. A stateless linear control case accepted `[1.0]` directly.

The one-failure stateful and stateless cases both cut back
`1.0 -> 0.5`, then accepted `[0.5, 0.5]` to reach load factor `1.0`.

Three deterministic failures produced retry candidates
`1.0 -> 0.5 -> 0.25 -> 0.125`, followed by eight accepted `0.125`
increments to load factor `1.0` in both adaptive surfaces. The minimum
increment case returned `MIN_INCREMENT_REACHED` when `0.5 < 0.75`. An
always-failing case with `max_cutbacks=2` returned `MAX_ITERATIONS` after the
second rejected attempt, with no third attempt.

Current result envelopes do not expose accepted composite/material digests for
all selected cases; those fields are explicitly `NOT_EXPOSED_BY_CURRENT_RESULT`
in the machine-readable record rather than inferred.

## Baseline commands

| Scope | Result |
| --- | --- |
| `test_nonlinear_load_path.py -k adaptive` | `11 passed, 14 deselected` |
| `test_geometric_nonlinear_adaptive.py` | `5 passed` |
| `test_wp01_d_continuation.py -k adaptive` | `4 passed, 18 deselected` |
| stateful rollback test | `1 passed` |
| WP02-C adaptive restart subset | `3 passed, 22 deselected` |
| adversarial multielement B16 | `1 failed` — pre-existing signature mismatch |

## B16 signature finding

`test_adversarial_rollback_retries_from_clean_committed_state` fails before
its intended retry assertions because its verification subclass override does
not accept the existing internal `commit_to_inputs` keyword. The production
adaptive route already uses this keyword to prevent premature mirror
publication. WP03-C will classify and repair this stale verification seam
without weakening the accepted-state contract.

The complete machine-readable observations are in
`qualification/0_2_9/wp03_c_baseline.json`.

No production source was changed while capturing this baseline, and the full
repository suite was not run.
