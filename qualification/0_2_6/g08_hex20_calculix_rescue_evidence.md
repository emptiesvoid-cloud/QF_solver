# G08 HEX20 CalculiX Rescue Evidence

Status: **PASS_EXTERNAL_CORRELATION_BOUNDED**; official G08 status remains **PASS_WITH_LIMITATIONS**.

Execution source SHA: `7b944a5741eca43d7cf97f013a037c398363878a`; dirty: `False`.

## Root-cause correction

The buckling deck writer emitted a C3D20 continuation line with a leading empty field. The corrected writer starts the continuation with the next node, matching the existing HEX20 static writer and CalculiX input contract. No FEM formulation, eigensolver or numerical solver code was changed.

| Mesh | QF factor | CalculiX factor | Relative difference | Replay difference | Correlation |
|---:|---:|---:|---:|---:|---|
| 1 | 12.50453659 | 12.71666 | 1.696372% | 0.000e+00 | PASS |
| 2 | 10.98539335 | 11.21546 | 2.094296% | 0.000e+00 | PASS |
| 4 | 9.960021406 | 10.03357 | 0.738438% | 0.000e+00 | PASS |

## Mode comparison

The FRD first eigenmode is compared after arbitrary eigenvector sign alignment. The G08 contract has no external MAC acceptance threshold, so these values are reported diagnostically and are not converted into an invented PASS criterion.

| Mesh | Raw cosine | Sign-aligned cosine | MAC | Status |
|---:|---:|---:|---:|---|
| 1 | -0.935479008 | 0.935479008 | 0.875120975 | RECORDED_NO_OWNER_MAC_THRESHOLD |
| 2 | -0.890655928 | 0.890655928 | 0.793267982 | RECORDED_NO_OWNER_MAC_THRESHOLD |
| 4 | -0.631466867 | 0.631466867 | 0.398750404 | RECORDED_NO_OWNER_MAC_THRESHOLD |

## Scope and limitations

- Same QF HEX20 mesh factory, C3D20 mapping, homogeneous isotropic material and nodal dead load.
- Mesh levels executed: 1-cell, 2-cell, 4-cell; each level has a deterministic replay.
- The existing 10% correlation band was declared before execution and is reused unchanged.
- This is numerical external correlation only; it is not physical validation.
- The official G08 family decision and gate remain unchanged pending Owner review.
- No post-buckling, multi-mode or general high-order qualification claim is added.
