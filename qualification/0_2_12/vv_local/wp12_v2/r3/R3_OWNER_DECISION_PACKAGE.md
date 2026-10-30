# WP12-V2-R3 — Owner decision package

**PREPARED_NOT_AUTHORIZED · NUMERICAL_EXECUTION_NOT_PERFORMED (FORMAL R3) · WP12_STATUS=OPEN · WP13_STATUS=OPEN**

## Current state

The prospective H1 test revision is stable in development: attempts 2 and 3 passed pytest and were scientifically classified `INCONCLUSIVE` because the gamma-rounding assumptions remain unverified. The development allowance used 3 of 10 attempts. The original R2 formal attempt, decision, manifest and evidence remain separate and unchanged.

The candidate manifest is [V2_R3_MANIFEST.json](V2_R3_MANIFEST.json), SHA-256:

`081d97b0667877b4c778a09801b02ac35fe80a2327bf8dc7d8e66c0e641706a1`

It fixes the exact nodeid, science/test/runner commits and trees, 35 input inventory entries, Python 3.13.17 environment, dependency versions, source import, command with `-s`, one-attempt formal limit, 300-second timeout, 16 MiB software-polled per-stream log cap, and a new evidence namespace. It remains explicitly `PREPARED_NOT_AUTHORIZED`; no R3 Owner decision or signature exists.

## Compatibility blocker — preserve R2 runner

The frozen R2 runner is intentionally restricted to campaign IDs `WP12-V2-R1-H1-OPERATOR-AUDIT-002` and `WP12-V2-R2-H1-OPERATOR-AUDIT-002`. Its shape validator and command builder reject a new R3 campaign ID. This is a deliberate allowlist boundary, not an implementation defect. The R2 runner was not edited.

Therefore this manifest is a traceable R3 preparation but is **not executable with the pinned runner identity**. Do not sign or treat this SHA as a usable execution authorization. Before formal R3 qualification, prepare a separately reviewed R3 runner revision that explicitly binds the R3 campaign and nodeid, or obtain an independently approved runner profile. That changes the runner identity, so regenerate the 35-entry inventory as applicable, revise and re-hash the manifest, and obtain a new Owner decision. R2 approval cannot transfer.

## Scientific and operational scope proposed for a future decision

- Campaign/case: `WP12-V2-R3-H1-OPERATOR-AUDIT-002` / `TET4-H1-OPERATOR-AUDIT-002`.
- Exact nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.
- Science: commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.
- Tests: commit `77e83b53859d3ad1e13afded6335d29d2f8c4d27`, tree `78436375a7ef674dfd5130f55edbc0757f7f1056`.
- Current pinned runner: commit `731fd9d6b05efe227de60e8cb19ba095cc8b29d9`, tree `19b775be2d49890b890c41b6d56f5b1be082279b`; incompatible with R3 campaign ID as described above.
- Environment proposed: dedicated Python 3.13.17 at `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`; pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, h5py 3.14.0, threadpoolctl 3.6.0; `solveur` imported from the frozen science checkout; six thread environment variables set to one.
- Proposed formal execution: one attempt, exact nodeid only, 300 seconds, 16 MiB per-stream soft-polled output cap, sequential, stop on first unexplained anomaly, preserve all outcomes.
- Evidence namespace: `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R3-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<new_run_id>\`.
- Existing criteria and gamma treatment are unchanged. If rounding-mode/reduction assumptions remain unverified, the gamma and overall scientific status remain `INCONCLUSIVE`; no fallback threshold is permitted.
- Accepted local limitations need a fresh R3 decision: no filesystem sandbox, hard CPU/RAM/disk quotas, guaranteed descendant containment, cryptographic process attestation or independent archive.

## Owner action after runner compatibility is resolved

Review the new runner candidate and its exact inventory, confirm the environment and destination above, review the H1 oracle and local limitations, then issue a separate decision bound to the **new** final manifest SHA-256 and runner identity. The current manifest hash is for traceability only and must not be approved for execution.

This package does not authorize formal R3 execution, WP12-W, additional nodeids, new solves, mesh refinement, maturity promotion, WP12 closure, merge, tag or release.
