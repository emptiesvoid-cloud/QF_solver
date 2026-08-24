## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | WARNING |
| Noeuds | 68 |
| Elements | 140 |
| Amplification graphique | 3.60225 |
| Empreinte maillage/source | `cf3600914d19bcb66d2d2a0d644922fc67048fde124e70329c277cc15585248b` |
| Empreinte configuration/source | `1855b312d0919562e35b73f7a72ff58d52317b6da359ca0fd3fab768185e766a` |
| Empreinte modele | `573270442e4d309849ff33acaefbae30ad17286741eec704be347e8d37fa1826` |
| Empreinte resultat | `0ee865dd4f536e4863d5ccdbe16af956d3a20c31c93fdc8e2183ab2812da3bb9` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| uniaxial-stress | <= | 2.185504e-15 | 0.02 | PASS |
| uniaxial-plastic-strain | <= | 1.387779e-16 | 1.000000e-06 | PASS |
| load-step-sensitivity | <= | 1.138714e-11 | 1.000000e-06 | PASS |
| free-residual | <= | 1.194836e-13 | 1.000000e-07 | PASS |
| step-residual | <= | 1.206419e-13 | 1.000000e-07 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| applied_axial_stress | 3.000000e+08 |
| mean_axial_stress | 3.000000e+08 |
| relative_stress_error | 2.185504e-15 |
| expected_uniaxial_equivalent_plastic_strain | 0.05 |
| mean_equivalent_plastic_strain | 0.05 |
| relative_plastic_strain_error | 1.387779e-16 |
| load_step_sensitivity | 1.138714e-11 |
| load_step_counts | [3, 6, 12] |
| converged_steps | 6 |
| max_step_iterations | 6 |
| free_relative_residual | 1.194836e-13 |
