# G08 Euler pre-validation and HEX8 root-cause evidence

Status: **PASS_WITH_LIMITATIONS**. G08 remains **PASS_WITH_LIMITATIONS**.

Execution source SHA: `75fbe03a414969d26dee9f0df84ff1c5dcd1661e`; dirty: `False`.
Corrected analytical evidence SHA: `4c45b46cfa7c9a664986bb49a53ef25fa570c030`.

## Active evidence matrix

| Family | Mesh | Analytical | External | Eigenpair | Mode | Determinism | Provisional decision |
|---|---|---|---|---|---|---|---|
| TET4 | PASS historical bounded | PASS historical case-specific | BOUNDED historical | PASS | PASS | PASS | PREQUALIFIED_BOUNDED |
| TET10 | PASS bounded (0.081448%) | PASS at final axial level; 3.269% | PASS bounded historical | PASS | PASS | PASS | PASS_WITH_LIMITATIONS |
| HEX8 | PASS bounded (0.167113%), absolute Euler gap remains | LIMITATION; 298.413% final axial error | PASS same-model C3D8 cross-check | PASS | PASS global-bending candidate | PASS | MORE_EVIDENCE_REQUIRED |
| HEX20 | PASS bounded (0.912621%) | PASS at final axial level; 3.622% | PASS bounded C3D20, 3 levels | PASS | PASS | PASS | PASS_WITH_LIMITATIONS |

The superseded positive-load Euler comparison is retained only as a historical record and is excluded from the active interpretation. The active comparison uses signed compression with `F_REFERENCE_TOTAL=-1.0` and `Pcr_QF=abs(lambda*F_REFERENCE_TOTAL)`.

## HEX8 diagnosis

Classification: **LOCKING_LIKELY**.

| Axial cells | Transverse cells | Pcr QF | Euler error | Aspect ratio | Jacobian min/max | Kt condition | Kg symmetry | Kg eigenvalue range |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 26084.67 | 3147.632% | 8 | 0.125/0.125 | 1665.2 | 0.000e+00 | -6.250e-02/3.339e-01 |
| 2 | 1 | 6236.7816 | 676.501% | 4 | 0.0625/0.0625 | 7114.06 | 0.000e+00 | -3.273e-01/1.368e-01 |
| 3 | 1 | 3200.0167 | 298.413% | 2.66667 | 0.0416667/0.0416667 | 12321.3 | 0.000e+00 | -6.088e-01/5.630e-02 |
| 2 | 2 | 6177.3542 | 669.102% | 8 | 0.015625/0.015625 | 28109.5 | 0.000e+00 | -1.692e-01/4.921e-01 |
| 2 | 3 | 6165.3555 | 667.608% | 12 | 0.00694444/0.00694444 | 62309.8 | 0.000e+00 | -1.045e-01/5.523e-01 |

All HEX8 modes are classified as global-bending candidates; lateral mode amplitude grows toward the free end and no mode switching was observed in this screen. The geometric tangent is symmetric and has a negative destabilizing direction under the signed compressive preload, consistent with the TET10/HEX20 route diagnostics.

## Same-model C3D8 cross-check

| Axial cells | QF factor | CalculiX factor | Relative difference | Status |
|---:|---:|---:|---:|---|
| 1 | 26084.67 | 26084.77 | 3.835270596059029e-06 | PASS |
| 2 | 6236.7816 | 6236.807 | 4.065370529027124e-06 | PASS |

QF and C3D8 agree within the same low-order solid model, while both remain far above the Euler slender-column value. This supports a low-order HEX8/C3D8 locking or solid-discretization limitation for this benchmark, not a QF-specific load-factor or geometric-tangent defect. This conclusion is diagnostic and does not change the G08 contract.
