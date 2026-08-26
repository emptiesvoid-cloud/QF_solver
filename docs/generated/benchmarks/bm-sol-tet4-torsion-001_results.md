## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | PASS |
| Noeuds | 892 |
| Elements | 3508 |
| Amplification graphique | 1.337999e+06 |
| Empreinte maillage/source | `d2f885ce72dd368aeb62ab7458e21bfb77bdf999c101f7078007493e232295e2` |
| Empreinte configuration/source | `df718595bf34a25452c0dc614546d3a1fc0a4262d69d26150888c523a3465881` |
| Empreinte modele | `2e73c903bd40c72f2ab771451aa5c9d4d254ad91bf27d5630821d8d5087e1806` |
| Empreinte resultat | `53cdca87c395b0ef68508abeb8215742024c457cfc70b8c7a81347348bafd856` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| torsion-finest-twist | <= | 0.103597 | 0.15 | PASS |
| torsion-observed-order | >= | 1.54754 | 0.5 | PASS |
| torsion-monotonicity | <= | 0 | 1.000000e-10 | PASS |
| torsion-load-resultant | <= | 2.273737e-16 | 1.000000e-12 | PASS |
| torsion-force-resultant | <= | 1.932885e-16 | 1.000000e-10 | PASS |
| torsion-free-residual | <= | 2.548105e-13 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| reference_twist_angle | 9.931268e-07 |
| shear_modulus | 3.076923e+10 |
| polar_moment | 0.0981748 |
| asymptotic_levels | [6, 7, 8] |
| observed_order | 1.54754 |
| finest_relative_twist_error | 0.103597 |
| monotonicity_violation | 0 |

### Convergence h en torsion

| Niveau | h [m] | Noeuds | Elements | Rotation [rad] | Erreur rotation | Erreur contraintes L2 | Couple [N.m] | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.48 | 72 | 158 | 6.344347e-07 | 0.361175 | 0.770799 | 1000 | 2.246134e-14 |
| 2 | 0.4 | 105 | 259 | 6.336996e-07 | 0.361915 | 0.830702 | 1000 | 2.452305e-14 |
| 3 | 0.34 | 140 | 335 | 6.690365e-07 | 0.326333 | 0.674713 | 1000 | 3.566780e-14 |
| 4 | 0.29 | 200 | 585 | 7.341196e-07 | 0.2608 | 0.691371 | 1000 | 6.322049e-14 |
| 5 | 0.25 | 285 | 898 | 7.986007e-07 | 0.195872 | 0.627185 | 1000 | 7.716529e-14 |
| 6 | 0.21 | 426 | 1462 | 8.211178e-07 | 0.1732 | 0.632112 | 1000 | 1.253511e-13 |
| 7 | 0.18 | 610 | 2257 | 8.396223e-07 | 0.154567 | 0.603138 | 1000 | 1.815173e-13 |
| 8 | 0.15 | 892 | 3508 | 8.902415e-07 | 0.103597 | 0.504079 | 1000 | 2.548105e-13 |

### Conclusion automatique

La rotation converge monotoniquement sur huit maillages: erreur de `36.117%` a `10.360%`, ordre observe `1.548`. L'erreur L2 des contraintes diminue de `77.080%` a `50.408%`, mais reste trop elevee pour qualifier les contraintes locales de torsion.
