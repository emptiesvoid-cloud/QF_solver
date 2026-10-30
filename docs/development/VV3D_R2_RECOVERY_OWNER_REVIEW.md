# VV3D R2 recovery controller review

## State

`PREPARED_NOT_AUTHORIZED`. This branch adds an isolated controller scope and
ledger for a new recovery campaign. It does not authorize a FEM attempt. The
final campaign contract, collect-only receipts, case manifests, and their hashes
must be generated only after the reviewed controller is integrated and a clean
controller checkout is designated in `AGENTS.md`.

PR #95 is already merged to `emptiesvoids-cloud/0.2.12` at `501fa8f52eecc0e9ab5bb37ee323bbb8af3d070b`; its fractional-seconds receipt correction is retained.

## R1 predecessor, preserved as-is

R2 binds the existing R1 ledger by raw SHA-256
`2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8`.
The observed closed history is:

| R1 case | Ledger status | Elapsed | Meaning |
|---|---:|---:|---|
| `VV3D-TET4-L1` | `PASS` | 15.81295399996452 s | FEM attempt completed and passed its recorded gates. |
| `VV3D-TET4-L2` | `INFRA_ERROR` | 2.8482145000016317 s | Attempt consumed; provenance was rejected before assembly. |

The second attempt remains an infrastructure/provenance failure; its pytest
record also says `PROVENANCE_MISMATCH` / `PYTEST_FAILED`. Neither result is
rewritten, copied into the R2 ledger, nor used as an R2 PASS. The R2 ledger is
currently absent, hence has no reservations or attempts. Its first reservation
must re-verify the exact R1 digest and both terminal R1 records.

The immutable proof references are:

| R1 case | Run receipt SHA-256 | Case manifest SHA-256 | Preflight / receipt SHA-256 | Runner reservation SHA-256 | Campaign assessment SHA-256 | Sidecar |
|---|---|---|---|---|---|---|
| TET4-L1 | `01e573446940385ec13c9ff451e8b3dc7cf55c237b16c6016adbc1f987868fad` | `e007def750c030c754e69a267deb56bb7d69bbf09908c8319da28a49a00d8c3a` | `pf-217d6cea7241` / `be7fb80cb074d35bd9fbbfc37394e4731aeef481b8a178fd8d60d6f90bf8edab` | `2230416793c05bbaa4f1778f72f5b0de470847d5a8cb4f2184ba7df3d76b9797` | `ccd71b62914ce9970f952945317bb2098474134319dcfc90b514a34788d1abf6` | `37f8be6b9d2a3ae9ef86466ef9436b8658ad6ed884aec1e53cb7282aad256515` |
| TET4-L2 | `2d9ccafae7dd4337caa0d1aba5e766225e97dff8fcb1d2805037c4ab6a0ea888` | `77f50690cea826c26aa7ce46d18e55d1acb8a4760acfd3668c7c4f4309d19e97` | `pf-9acefc5c2977` / `2d47ae8dde707cbd520560c03c04d12dbd3328ac796c6e1ee63bc3713f94391c` | `e0344ee2b0189cd7dc7462b72addc9ca5b4792c16262db41e1b3c9d47b6b0379` | `9d2d720df978a633fdbf83f797e557eb36c5bd0950d26017bbfa6a257395281b` | none; rejected before scientific observables |

R1's TET4-L1 contract bound the oracle at
`97a57660bd31d6f2ce112d07c554561da227b4e786ddfd7f66f1658427e2f4c5`. The
current scientific worktree's raw oracle bytes hash to
`1f0cddc469ff32d6f60590e451fe7256e0c505dbf0abde75a76c202fb71fe496`; its Git
blob hash is `9e6a8ee7af75e0515cc1bcdb0c3e0e8c49fa89ec487675436b8cd61395ae05d1`.
This historical byte-provenance discrepancy is recorded, not repaired in R1.
R2 binds the current raw oracle bytes and the per-family criteria bytes
explicitly; it does not claim that the old R1 oracle binding was identical.

Combined R1 elapsed time observed: `18.66116849996615 s`. The 28,800-second
ceiling therefore leaves `28,781.338831500034 s` before R2. Twelve full
1,200-second R2 reservations would use at most 14,400 seconds and leave at
least `14,381.338831500034 s`, assuming no other chargeable campaign operation.
The controller checks actual R1 time plus each R2 reservation before writing an
attempt record; the R2 ledger has a separate 12-attempt cap and retains the
24-attempt combined ceiling.

## R2 scope

Campaign: `WP12-VV3D-RECOVERY-20261030-R2`

Mandate: `DEVELOPMENT_AUTONOMOUS-WP12-VV3D-RECOVERY-2026-10-30-R2`

Scope: `wp12_vv3d_recovery_r2`

State: `execution_authorized=false`; adaptive FEM and QPOST are disabled.

Science source pinned by this candidate:

* Branch: `research/wp12-vv3d-recovery-r2`
* HEAD: `ba36860a156468dd7c54ee435a809222e227205a`
* Tree: `2f8c0d3cef5a6b07eac9ad48d0dcb1a311af72e2`
* Source fingerprint: `651bbacaf133106a6a8c8b2177e8741cf3fed9a9fdfc7f907d350484dfebd3ce`

The ordered catalogue is exactly:

1. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L1]`
2. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L2]`
3. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L3]`
4. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET10-L1]`
5. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET10-L2]`
6. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET10-L3]`
7. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX8-L1]`
8. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX8-L2]`
9. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX8-L3]`
10. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX20-L1]`
11. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX20-L2]`
12. `tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-HEX20-L3]`

H1, QLOAD, QPOST, retry, and implicit continuation after a non-PASS are
excluded. R2 is independent of R1 but the immutable R1 ledger is charged into
the combined time and attempt accounting. Every R2 attempt is serialized,
single-use, and bound to the exact campaign contract, Owner decision, case
manifest, preflight receipt, source fingerprint, controller fingerprint,
mesh, criteria, and oracle.

Per-case limits: one attempt; 1,200 seconds; sampled RSS soft limit 4,096 MiB;
30,000 DDL maximum; 256 MiB archive cap. A non-PASS, provenance/ledger error,
or budget incident stops R2. The RSS value is a sampled soft limit, not an OS
memory quota.

## Source and oracle bindings

R2 retains the prepared meshes, criteria files, and manufactured-solution
oracle. The R2 matrix and contract validate raw-byte SHA-256 values for each
case's mesh, criteria, and oracle. R1's historic contract and evidence remain
immutable, including any older byte-level oracle digest; R2 does not silently
rewrite or reuse that contract.

## Candidate validation

The branch tests are synthetic controller/policy/ledger tests only. They do
not execute a prepared test body, assemble a model, reserve an attempt, or run
an eigensolve. Before R2 can be offered for an exact execution decision, the
controller PR must be reviewed and integrated, the required clean controller
checkout must be designated and fingerprinted, then the 12 collect-only
preflights and source-bound manifests must be generated and verified. The
final Owner contract SHA is intentionally not asserted in this candidate
document because the controller identity depends on that post-integration
checkout path and runtime.
