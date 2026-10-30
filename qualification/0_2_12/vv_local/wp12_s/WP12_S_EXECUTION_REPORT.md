# WP12-S — quantitative execution report

**Execution status:** `WP12_S_QUANTITATIVE_CAMPAIGN_COMPLETED` — 8/8 authorized cases ran; 7 receipts are `PYTEST_PASS_ONLY`, one is `FAIL`.<br>
**Scientific qualification:** `NOT_ASSIGNED` — no `PYTEST_PASS_ONLY` receipt is an oracle verdict or WP12 qualification decision.<br>
**WP12:** `OPEN`<br>
**WP11:** `CLOSED` (unchanged) · **WP13:** `OPEN` (unchanged)

## Frozen authorization and execution identity

The Owner explicitly approved all eight cases against manifest SHA-256 `df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`. One non-cryptographic local decision record was written per exact case under the evidence root. These records preserve the explicit decision; they are not signatures. The manifest itself remains unchanged, with its historical `PREPARED_NOT_AUTHORIZED` state, so its approved digest remains stable.

| Role | Commit | Tree |
|---|---|---|
| Scientific source | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` |
| Runner | `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61` | `e31931fefb7012171e7e1a9f03511cd1c9987eda` |
| Tests and fixed wrappers | `cb445462e3e59fa487c28a0914d8d23ad47205e6` | `92feabc4dc86f142e5c042a232c9c529ec6210bf` |

The dedicated interpreter was Python 3.13.17 at `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`; pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, threadpoolctl 3.6.0 and h5py 3.14.0 were recorded by the manifest. The import probe and each receipt resolved `solveur` from the frozen scientific checkout. Execution was local and non-attested, without a filesystem sandbox or hard CPU/RAM limits; the Owner accepted those stated limits for this case set.

Raw stdout, stderr, JUnit, selection records, payloads, TET4 summaries/CSV/HDF5 models, receipts and one-attempt records are preserved under the manifest's evidence root, outside the checkout. The derived results index records every receipt SHA-256. The source, original WP12-R evidence, manifest, criteria and scientific assertions were not changed during execution.

## Case results

| Case | Run ID | Test status | Observed values and reference | Result interpretation |
|---|---|---|---|---|
| `ALG-PROJ-QUANT-001` | `20261026T095314Z-055befad2e0f` | `PYTEST_PASS_ONLY` | Structured and dense matrices both `[[4.765625, -0.5703125], [-0.5703125, 2.75]]`; max absolute difference `0`; relative Frobenius error `0`; symmetry defect `0`. | Recorded algebraic identity for synthetic operators; not FEM validation. Receipt SHA-256 `e3619afc337032d81ba94d05251885106bf100c86c0cc499f0eb9ff083f33fa6`. |
| `MODAL-DISCRETE-QUANT-001` | `20261026T095339Z-b7d9aa4d4af6` | `PYTEST_PASS_ONLY` | `k_eff=1000`, `m_eff=10`; computed/reference frequency `1.5915494309189535` cycles per consistent time unit; relative frequency error `0`; modal residual `1.7975467359112705e-16`. | Matches the spring/mass formula within existing criteria. The source does not declare a physical unit system. Receipt SHA-256 `d990d00fd509b21ee85aef000c0c2b4db7df73ee6496a1fd208db336b8a8efe5`. |
| `MODAL-2DOF-QUANT-001` | `20261026T095413Z-3eb40e52bb70` | `PYTEST_PASS_ONLY` | Eigenvalues `[4.699452011971862, 11.300547988028141]`; same-SciPy reference `[4.699452011971861, 11.300547988028136]`; frequencies `[0.3450195792717258, 0.535019835602861]` Hz; mass-orthogonality Frobenius error `3.5390820700439226e-16`; maximum modal residual `1.0102270089540443e-16`. | Same-backend consistency only; not an independent modal eigenvalue oracle. Maturity remains `EXPERIMENTAL`. Receipt SHA-256 `1997759f09a4b4d2a19d65f8a641bc3d82e4b775c751810745f5e5fcddf30507`. |
| `DYN-SDOF-QUANT-001` | `20261026T095436Z-f319a5e2c49f` | `PYTEST_PASS_ONLY` | Final computed/reference displacement `0.001952191752583705` / `0.001952191693063174`; max absolute error `5.952053108194966e-11`; RMS absolute error `2.6926924777587392e-11`; 81 samples, `dt=5e-5 s`, 80 steps; max relative energy drift `7.108029442814965e-13`; reduced equilibrium error `5.546612883411229e-11`. | One Newmark time step. The analytic frequency is derived from prepared FE `K/M`; no temporal convergence is established. Receipt SHA-256 `7aebadda2077f004aa13b6d50e7047035ebc09714d0c64b3611c44befbbe87e0`. |
| `MODAL-2DOF-POLY-001` | `20261026T095500Z-0494258ea65e` | **`FAIL`** | Polynomial roots `[4.699452011971861, 11.300547988028141]`; computed eigenvalues `[4.699452011971862, 11.300547988028141]`; relative errors `[1.8899616751857226e-16, 0]`; residuals `[1.0102270089540443e-16, 5.941302823469593e-17]`; mass-orthogonality error `3.5390820700439226e-16`. | The test failed at its additional projected-stiffness assertion (`rtol=1e-10, atol=0`): computed off-diagonal terms are about `−4.4408921e-16`, while the reference terms are exactly zero. The scalar-root comparison meets its stated limits, but the test remains `FAIL`; no tolerance was changed and no retry was made. This does not by itself demonstrate a physical solver defect. Receipt SHA-256 `a46d0d62740f79128552982ffd9c1835d458307bf6f9b261ba40320b02d3fd31`. |
| `STAT-BEAM-UY-001` | `20261026T095548Z-9826f4c65bbb` | `PYTEST_PASS_ONLY` | UY displacement `0.004235775661375659 m` vs Timoshenko `0.0042357756613756615 m` (relative error `6.143113852068658e-16`); RZ `0.003174603174603173 rad` vs `0.0031746031746031746 rad` (relative error `5.464378949326942e-16`). | One straight uniform BEAM2 element, UY/RZ plane; not mesh convergence or 3-D validation. Receipt SHA-256 `8bb8d1959ef87eb5ab061c0a17afeec812dc729e1e3015c357da948d51e48d30`. |
| `STAT-BEAM-UZ-001` | `20261026T095608Z-1f7fc4b8fe3b` | `PYTEST_PASS_ONLY` | UZ displacement `0.006352177777777781 m` vs Timoshenko `0.006352177777777778 m` (relative error `5.461822816248938e-16`); RY `−0.004761904761904765 rad` vs `−0.004761904761904762 rad` (relative error `5.464378949326942e-16`). | One straight uniform BEAM2 element, UZ/RY plane; sign agrees with the fixture convention. Not mesh convergence or 3-D validation. Receipt SHA-256 `2471a20b895bd4449ddb6603d8445c6a181a57346db606ce0b3fd4d292b0e257`. |
| `FEM-TET4-H-001` | `20261026T095627Z-aedceeb89280` | `PYTEST_PASS_ONLY`; helper `WARNING` | 12/96/768 TET4; 12/45/225 nodes; 36/135/675 DDL. Tip UZ `−5.14927314061041e-9`, `−1.6781818466340907e-8`, `−4.795612893178559e-8 m`; relative error to the 1-D beam diagnostic `0.964234`, `0.883436`, `0.666905`; residuals `4.009e-9`, `2.668e-9`, `2.140e-9`. | Bounded three-level characterization only. The utility's provisional 1% reference-error diagnostic is not met, giving `WARNING`. The reported orders `0.1263` and `0.4056` are not an asymptotic convergence claim. No independent 3-D reference or physical validation. `operator_memory_bytes` is an estimate; solve times are reported by the utility. Receipt SHA-256 `e8d93fae9cc07021e89444727551e39313a59c292305f7d0643dd27e2b23f8be`. |

Machine-readable values, the full Newmark history, and per-level TET4 results are linked in the [publication data index](PUBLICATION_DATA_INDEX.md) and included under [`results/WP12-S-QUANT-001-20261026T095251Z/`](results/WP12-S-QUANT-001-20261026T095251Z/). The SVGs are internal figures generated only from these verified payloads; they are not publication approval.

## Independent review and operational notes

An independent read-only review confirmed the eight receipt identities and output hashes and agreed with the interpretations above. It confirmed that the polynomial failure is specifically the zero-absolute-tolerance comparison of roundoff-sized off-diagonal terms, and that the TET4 `WARNING` reflects a diagnostic beam-reference limit, not a qualification threshold approved for WP12.

An initial CLI invocation for `MODAL-2DOF-QUANT-001` used an incorrect manifest path and exited before runner preflight. The attempt ledger and case output were checked and absent; the corrected command then created the only scientific attempt for that case. No scientific process ran during the failed invocation.

## Disposition

The eight authorized executions are complete, including the recorded failure. Preserve the polynomial `FAIL` and TET4 `WARNING`; neither may be converted to `PASS` by changing an assertion or diagnostic threshold. No additional tests, convergence campaign, external-solver correlation, performance campaign, maturity promotion, WP12 closure, release, or publication was authorized or performed. Further work on the polynomial assertion, higher-level modal validation, TET4 reference correlation, temporal convergence, or performance requires a separately reviewed scope and authorization.
