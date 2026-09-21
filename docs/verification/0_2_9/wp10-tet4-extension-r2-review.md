# WP10-TET4 extension R2 — provenance remediation review

## Result

The previous HOLD findings were remediated in a new `r2` evidence directory.
The original evidence remains unchanged. No production mechanics, thresholds,
or HEX8 evidence were modified.

```text
BRANCH = codex/wp10-extension-preparation
EXECUTION_SHA = 4a8afdb0b3cf9c8a48202b850aed400737e387db
RUNNER_SHA = 08f267bbc9f23c24229d3cb61ae34ed0377c9953
CONTRACT_SHA256 = e86f7c6f2c6e6f4b46b004dd54e847fa197c72a2d62acaf621a53dd2346df7c1
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
```

## Remediation checks

- A versioned SHA-256 manifest now covers every R2 primary, reference, replay,
  and process-manifest artifact.
- M1, M2, and the replay outputs contain an explicit `fallback_count = 0`.
- M3 was launched by `record_wp10_tet4_replay.py` in a fresh child process;
  PID `55896`, return code `0`, and command line are recorded.
- M3 primary and reference hashes match M2 because the route is deterministic;
  this is now supported by the fresh-process manifest rather than inferred
  from byte identity alone.
- The reference coverage is explicitly declared: it recomputes the final
  saved displacement state; production contact gaps remain recorded for every
  increment. It is not an independent global FEM solve.
- The ledger discrepancy remains outside this extension and is not silently
  resolved here.

## Gate status

| Gate | Status |
|---|---|
| M1 TET4 production | PASS_CANDIDATE |
| M2 TET4 production | PASS_CANDIDATE |
| Independent observable recomputation | PASS_WITH_EXPLICIT_FINAL-STATE_SCOPE |
| Fresh replay | PASS |
| SHA-256 manifest | PASS |
| Fallback accounting | PASS, 0 |
| Targeted tests | 29 passed |
| Compileall | PASS |
| Git diff check | PASS |
| Ruff | NOT_EXECUTED_TOOL_UNAVAILABLE |

## Final classification

```text
WP10_TET4_STATUS = READY_FOR_OWNER_REVIEW
WP10_TET4_CANDIDATE_POINTS = 0/EXTENSION_PENDING
WP10_OFFICIAL_POINTS = UNCHANGED
MERGE = NOT_PERFORMED
PUSH = NOT_PERFORMED
```

The extension remains bounded TET4 evidence only. No general WP10 claim,
mesh-convergence claim, external-solver correlation, friction, finite sliding,
dynamics, or MPI/PETSc claim is made.
