# Owner decision package — V2 H1 operator audit

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**
**Requested disposition: decide whether to authorize one attempt of one exact nodeid.**

## Proposed unit

- Campaign: `WP12-V2-H1-OPERATOR-AUDIT-002`
- Case: `TET4-H1-OPERATOR-AUDIT-002`
- Nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`
- Manifest: [`V2_MANIFEST.json`](V2_MANIFEST.json); SHA-256 `dd72bc80ff5dbae1d105bef5ad6f778eb9046335706697db0479b0764145d665`. The decision must bind this exact 64-character digest, not this document alone.
- Scientific checkout: commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.
- Test checkout: commit `653fc0b9895c24429c5605e05fabf604cc358f48`, tree `6f973c272a65b1a07aec7bf968e8539b8236ddf2`.
- Runner checkout: commit `9b1465d79cb19985c823c1329af2540de665a556`, tree `8b85486840de30f7e8ccd5cec1b5bc744c7fbcb0`.
- Interpreter/environment proposed: `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`, Python 3.13.17; pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, h5py 3.14.0 and threadpoolctl 3.6.0. These are prior WP12-U observations and must be revalidated before any decision is effective.
- Proposed timeout 300 seconds; one attempt only; automatic retry disabled. Proposed per-stream 16 MiB cap is polling-only. No hard CPU, RAM, disk or filesystem sandbox is provided by the local runner.
- Evidence namespace: `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<run_id>\`. The campaign destination must not already exist when a future run is approved.

## Scope approved for Owner review

The experiment captures the scalar and batch matrices for all 12 H1 elements, checks node/component maps and emitted CSR values/indices, compares the 36×36 global matrices to an exact-rational discrete reference, evaluates all 24 free canonical matrix-free vectors, and recomputes the two archived U3 fields' residuals and equilibrium/energy identities. It performs no new linear solve. The full proposed criteria and normalizations are in [V2_NUMERICAL_CRITERIA.md](V2_NUMERICAL_CRITERIA.md).

The values `1e-12`, `1e-8` and `1e-7` are carried forward from the U3 H1 criteria for Owner review. They are not automatically inherited as V2 approval. The gamma-bound result depends on finite binary64 round-to-nearest operations without overflow/underflow; runtime rounding mode and all internal summation intermediates are not independently observed. The Owner must accept this limitation or require a separately reviewed precondition before authorizing execution.

## Required preflight before a future run

1. Verify the final manifest SHA-256 and all three clean checkout identities, including the test checkout containing this exact nodeid and both fixture files.
2. Run the runner's `validate` operation only when preparing the decision. It checks file/tree identities, package versions, and a source-import probe; it is not the scientific test. Confirm the actual import origin is the frozen scientific checkout, not a globally installed distribution.
3. Confirm Python, NumPy/SciPy/h5py/pytest, native BLAS identity, thread settings and the exact node selection. The recorded 2026-10-26 environment values are inherited observations, not a guarantee of current state.
4. Confirm the evidence namespace is new and that only one case is being authorized.
5. Record a separate, explicit local Owner decision outside the manifest, bound to the exact manifest SHA, nodeid, three commit/tree identities, interpreter/environment, criteria, one-attempt budget, output namespace and the local non-attested limitations.

The local `QUALIFICATION_LOCAL_VV` runner checks that decision's fields but does not cryptographically authenticate the human author. A JSON status field is not proof of authorship. The Owner/operator must review and record the decision through the documented local process; no decision file or approval is created by this preparation.

## Explicit non-authorizations

This package does not authorize execution. It does not authorize H2/H3 reruns, TET4 refinement, W1/W2, any other pytest nodeid, solver, benchmark, package publication, maturity change or WP12 closure. Preserve U3 as FAIL even if V2 later passes. Stop before launch if any hash, identity, environment, node selection, criterion precondition or output path differs; do not silently edit the manifest after approval.
