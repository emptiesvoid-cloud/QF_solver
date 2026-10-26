# WP12-S Owner decision package

**Status:** `OWNER_DECISION_RECORDED`<br>
**Numerical execution:** `PERFORMED_FOR_EIGHT_APPROVED_CASES`<br>
**WP12:** `OPEN`

The prepared campaign manifest SHA-256 is **`df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`** (detached digest: [`WP12_S_QUANTITATIVE_MANIFEST.sha256`](WP12_S_QUANTITATIVE_MANIFEST.sha256)). It contains eight cases. Each case required an individual decision bound to that exact hash, case ID and nodeid. The decisions were recorded as non-cryptographic local records; no approval signature was created.

The Owner subsequently approved all eight listed cases individually against the WP12-S manifest SHA-256 above. This approval was explicit in the conversation and accepted the local non-attested environment limits. It is not an Ed25519 signature; per-case local decision records and execution receipts are stored in the manifest-declared evidence archive. The older WP12-R decision remains limited to its four original nodes and was not reused.

## Approved cases and exact scope

| Case ID | Exact nodeid | Proposed scope | Oracle / criterion | Timeout / log limit |
|---|---|---|---|---|
| `ALG-PROJ-QUANT-001` | `test_wp12_s_alg_proj_001` | Q1 structured projection payload | Existing exact symmetry and dense comparison `rtol=atol=2e-16` | 120 s / 16 MiB soft per stream |
| `MODAL-DISCRETE-QUANT-001` | `test_wp12_s_modal_discrete_001` | Q2 ground spring + lumped mass | Existing frequency `rel=1e-12`, residual `<1e-12`; units remain undeclared | 120 s / 16 MiB soft per stream |
| `MODAL-2DOF-QUANT-001` | `test_wp12_s_modal_2dof_001` | Q3 same-backend modal extraction | Existing SciPy consistency/projection assertions; not independent eigenvalue validation | 120 s / 16 MiB soft per stream |
| `DYN-SDOF-QUANT-001` | `test_wp12_s_dyn_sdof_001` | Q4 Newmark history variant | Existing final response, projection and equilibrium criteria; one dt only | 180 s / 16 MiB soft per stream |
| `MODAL-2DOF-POLY-001` | `test_wp12_s_modal_2dof_poly_001` | Independent scalar characteristic roots | WP04 limits `1e-10` eigenvalue relative; `1e-8` residual/orthogonality | 120 s / 16 MiB soft per stream |
| `STAT-BEAM-UY-001` | `test_wp12_s_stat_beam_uy_001` | BEAM2 UY/RZ | Existing one-element Timoshenko comparison `rel=1e-12` | 180 s / 16 MiB soft per stream |
| `STAT-BEAM-UZ-001` | `test_wp12_s_stat_beam_uz_001` | BEAM2 UZ/RY | Existing one-element Timoshenko comparison `rel=1e-12` | 180 s / 16 MiB soft per stream |
| `FEM-TET4-H-001` | `test_wp12_s_fem_tet4_h_001` | Three TET4 resolutions, factors 1/2/4 | Characterization only: expected inventory and finite outputs; no convergence/physical PASS threshold | 1,800 s / 16 MiB soft per stream |

All nodeids are prefixed with `tests/unit/test_wp12_s_quantitative_extraction.py::` in the manifest. Each case is one invocation and one attempt. TET4's three mesh levels are one fixed, sequential protocol and will be written to one unique case output directory.

## Common conditions to accept or decline

- Scientific checkout: `00428adf38e9397340ac136f6f503a268eb671da` / `df4ec667bf746b042c900fad1f86bf542e1a437b`.
- Test checkout: exact manifest identity; contains fixed wrapper and pinned source test helpers.
- Runner: commit `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61`, tree `e31931fefb7012171e7e1a9f03511cd1c9987eda`; exact manifest identity, requiring schema `qf-wp12-s-observables-v1` and exact case binding for every prepared case.
- Python: dedicated `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`; Python and package versions are frozen in the manifest and must be revalidated.
- Evidence root: `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-S-QUANT-001`; destination must not exist for the selected attempt.
- Local limits: same-user process, no filesystem sandbox, no hard CPU/RAM/disk quota and no guaranteed descendant termination. Timeout and output cap are supervision controls; log cap is soft polling.
- No assertion, tolerance, reference, scientific source or historical receipt will be changed.
- Results remain internal evidence pending Owner review of the oracle interpretations. No WP12 closure, maturity promotion, release, tag, main merge, or publication is authorized.

The local decision records are non-cryptographic and cannot independently prove the author's identity. They record, but do not replace, the explicit Owner decision. The eight executions are complete; see [the execution report](WP12_S_EXECUTION_REPORT.md). This package does not authorize additional tests, retries, benchmarks, WP12 closure, maturity changes, or publication.
