# WP12-S Owner decision package

**Status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`

The prepared campaign manifest SHA-256 is **`df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`** (detached digest: [`WP12_S_QUANTITATIVE_MANIFEST.sha256`](WP12_S_QUANTITATIVE_MANIFEST.sha256)). It contains eight cases. Each case needs its own explicit decision bound to that exact hash, case ID and nodeid. No decision file or approval signature has been created.

The Owner decision supplied for manifest SHA-256 `ea8f32e24d9eaded198230b0bc5f8aab45ed76293c3e73bdf77533e0bf08a0db` applies to the four original WP12-R cases only. It does not authorize any instrumented WP12-S nodeid under this new manifest. No WP12-S scientific case is authorized by that earlier decision.

## Cases for individual decision

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
- Results remain internal evidence pending independent oracle review. No WP12 closure, maturity promotion, release, tag, main merge, or publication is authorized.

The existing local Owner decision format is non-cryptographic: it records the accepted decision but cannot prove the identity of its author. This package does not create an `APPROVED_FOR_EXECUTION` JSON or synthesize a signature. After the Owner explicitly approves chosen case IDs and this manifest hash, the operator may prepare the corresponding decision records outside the repository and run only those cases.
