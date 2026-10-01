# WP09 isotropic 3-D remesh study

Status: `FAIL_DIAGNOSTIC_RUN`
Load scale: `0.25`
Execution SHA: `1bc884e927fb2a7d554da53bc3953d5719bd4914`

| Family | Level | Nodes | Elements | DOFs | Status |
|---|---:|---:|---:|---:|---|
| TET4 | 1x1x1 | 8 | 5 | 24 | PASS |
| TET4 | 2x2x2 | 27 | 40 | 81 | FAIL_EXCEPTION |
| TET4 | 4x4x4 | 125 | 320 | 375 | FAIL_EXCEPTION |

TET4 1x1x1 → 2x2x2: `{}`
TET4 2x2x2 → 4x4x4: `{}`
| HEX8 | 1x1x1 | 8 | 1 | 24 | PASS |
| HEX8 | 2x2x2 | 27 | 8 | 81 | PASS |
| HEX8 | 4x4x4 | 125 | 64 | 375 | PASS |

HEX8 1x1x1 → 2x2x2: `{'selected_displacement': 0.8559640497391776, 'reaction_norm': 2.936737519706286e-10, 'energy': 0.7837583578129694, 'von_mises_max': 0.6514314610550903, 'equivalent_plastic_strain_max': 0.8874155595692909}`
HEX8 2x2x2 → 4x4x4: `{'selected_displacement': 0.5096327027048942, 'reaction_norm': 3.7327729794435913e-10, 'energy': 0.5214706688317524, 'von_mises_max': 0.5991135082938144, 'equivalent_plastic_strain_max': 0.5746440621109667}`

This study is diagnostic only. It does not rebind the formal contract or award WP09 points.
