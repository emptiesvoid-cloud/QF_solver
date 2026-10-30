# WP12-V2-R3 — Owner decision package, manifest revision 2

**PREPARED_NOT_AUTHORIZED · FORMAL_NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN · WP13_STATUS=OPEN**

## Decision requested

If formal R3 execution is still desired, review and issue a new authenticated Owner decision bound to this exact manifest SHA-256:

`c972688f78c3651ebd92f9121eb700d5b09cbb43d4580d1f135d336ad5a23ef1`

This SHA supersedes the previous R3 preparation SHA only as a proposed execution profile. It does not authorize execution. The original R3 manifest `081d97b0667877b4c778a09801b02ac35fe80a2327bf8dc7d8e66c0e641706a1`, the R2 decision, and the consumed R2 attempt remain preserved and do not transfer.

## Frozen scope and identities

- Campaign/case: `WP12-V2-R3-H1-OPERATOR-AUDIT-002` / `TET4-H1-OPERATOR-AUDIT-002`.
- Exact nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.
- Scientific checkout: commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.
- Test checkout: commit `77e83b53859d3ad1e13afded6335d29d2f8c4d27`, tree `78436375a7ef674dfd5130f55edbc0757f7f1056`.
- R3-compatible runner checkout: commit `8b78db0aa169e787f5f36d6f8a2fa909bdd61489`, tree `b969d1e892e82a2ee114876f8118da8ee2bcd2ac`.
- Inventory: 35 exact file entries; runner inventory includes the R3 allowlist revision and its synthetic regression test.

The R3 allowlist change preserves the exact command profile and nodeid and retains `-s`. Its dedicated synthetic test file returned 10 passing fake/lifecycle cases; no solveur, NumPy or SciPy was imported by that synthetic suite. This runner result is not H1 scientific evidence.

The revised manifest was also checked with the runner's read-only `VALIDATE` command: status `VALIDATED_NOT_AUTHORIZED`, manifest SHA matching the value above, all 35 inventory entries matched, all three checkout identities were clean and exact, the dedicated Python/dependency profile matched, and `solveur.__file__` resolved to the frozen science checkout. This validation imported `solveur`, NumPy, and SciPy only to inspect provenance; it did not collect or run pytest, invoke a solver, or perform a numerical calculation. It does not authorize execution.

## Proposed execution conditions to confirm

- One attempt only; no retry; timeout 300 seconds.
- One exact nodeid; no additional test or solver command.
- Dedicated Python 3.13.17 environment with the versions and source import in the manifest; recheck the complete environment and all hashes immediately before any launch.
- Per-stream output limit 16 MiB, software-polled only.
- Evidence under the exclusive R3 H1 namespace in the manifest; create a new run ID and refuse overwrite.
- Local non-attested execution remains subject to the explicitly listed limitations: current-user filesystem access, no filesystem sandbox, no hard CPU/RAM/disk quotas, no guaranteed descendant containment, no cryptographic process attestation, and no independent archive.
- Rounding-mode and reduction assumptions remain unverified unless the preflight demonstrates them. If still unverified, gamma and overall scientific statuses must remain `INCONCLUSIVE`; no fallback tolerance is allowed.

## Required authenticated Owner decision

The decision must bind the manifest SHA above, the three commit/tree identities, exact nodeid, environment, command, resources, attempt count, evidence destination, validity period, Owner identity, and the accepted local limitations. A plain JSON field marked `APPROVED`, an old R2 authorization, or the prior R3 package is insufficient. Use the configured trusted signature mechanism; do not place a private key in the repository or evidence logs.

After the decision is recorded, the operator must still perform a fresh preflight. Any identity, hash, environment, source-import, node-selection, or output-destination mismatch requires `DENY_EXECUTION` before consuming the attempt.

This package does not authorize WP12-W, additional nodeids, another H1 solve, mesh refinement, tolerance changes, maturity promotion, WP12 closure, merge, tag, or publication. WP12 and WP13 remain `OPEN`; U3's historical `FAIL` remains unchanged.
