---
doc_id: DOC-029-WP03-007
revision: 0.1
status: controlled
applicable_version: 0.2.9-development
---

# WP03-B — executed robustness baseline

This record freezes the targeted pre-edit baseline at
`9a97025670f7fbb28cbe4c6e2e76eacbf9fc5714`. The machine-readable record is
`qualification/0_2_9/wp03_b_baseline.json`.
The full WP03-A 16-case campaign remains a separate prospective record and is
not rewritten here.

## Results

| Scope | Result |
| --- | --- |
| B01/B06 contracts, sparse assembly and Newton helpers | 11 passed |
| B02 J2/material group | 35 passed, 1 pre-existing failure |
| B02 J2 control excluding that failure | 35 passed, 1 deselected |
| B03/B04 geometric nonlinear | 27 passed |
| B05 penalty/contact composition | 30 passed |
| B07/B12/B13/B14 robustness and failure modes | 28 passed |

The pre-existing B02 failure is
`test_adversarial_rollback_retries_from_clean_committed_state`. At this SHA it
raises `TypeError` because its injected solver override does not accept the
already-present `commit_to_inputs` keyword. This is adaptive signature
compatibility debt outside WP03-B's stagnation/line-search scope. It is not
silently counted as a pass.

## Diagnostic boundary

The selected existing tests assert outcomes and failure taxonomy but do not
emit one structured B01–B14 record containing every requested displacement,
load-factor, residual, reaction, state-digest and contact field. Those fields
are therefore explicitly marked `NOT_CAPTURED_BY_SELECTED_EXISTING_TESTS` in
the JSON record; no numerical value is inferred. Iteration and failure
information is retained where the tests expose it.

No full repository suite was run. No production source was modified while
capturing this baseline.
