# WP09 HEX8 isotropic 3-D refinement study

Status: `PASS_DIAGNOSTIC_RUNS`
Load scale: `0.25`
Execution SHA: `7553d4c6b776db2296c6d6eb437e9dbb1dee9ea4`

| Family | Level | Nodes | Elements | DOFs | Status |
|---|---:|---:|---:|---:|---|
| HEX8 | 1x1x1 | 8 | 1 | 24 | PASS |
| HEX8 | 2x2x2 | 27 | 8 | 81 | PASS |
| HEX8 | 4x4x4 | 125 | 64 | 375 | PASS |
| HEX8 | 8x8x8 | 729 | 512 | 2187 | PASS |

HEX8 1x1x1 → 2x2x2: `{'selected_displacement': 0.8559640497391776, 'reaction_norm': 2.936737519706286e-10, 'energy': 0.7837583578129694, 'von_mises_max': 0.6514314610550903, 'equivalent_plastic_strain_max': 0.8874155595692909}`
HEX8 2x2x2 → 4x4x4: `{'selected_displacement': 0.5096327027048942, 'reaction_norm': 3.7327729794435913e-10, 'energy': 0.5214706688317524, 'von_mises_max': 0.5991135082938144, 'equivalent_plastic_strain_max': 0.5746440621109667}`
HEX8 4x4x4 → 8x8x8: `{'selected_displacement': 0.2891386683851973, 'reaction_norm': 5.955643368219414e-07, 'energy': 0.3481920825152557, 'von_mises_max': 0.329527005934399, 'equivalent_plastic_strain_max': 0.31875411965065653}`

This study is diagnostic only. It does not rebind the formal contract or award WP09 points.
