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
