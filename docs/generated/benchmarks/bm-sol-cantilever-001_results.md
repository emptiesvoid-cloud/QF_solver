## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | PASS |
| Noeuds | 597 |
| Elements | 252 |
| Amplification graphique | 4.988119e+04 |
| Empreinte maillage/source | `dc62d5c0acdda593b13eeb67435357ffbefeff20169547654c8afeced7f9d05e` |
| Empreinte configuration/source | `597b412f46090056677c869b5932c9f099b13deea5a3d09ad3406d73adbb1350` |
| Empreinte modele | `d1febcc79a027cc6d6f5b0299fdedadcc641623cfef10e5df467162fa35465e1` |
| Empreinte resultat | `f610d47bd41266777d9c8e9366d212e0cf4dc07959059489266397b0702cbfe0` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| tet10-tip-reference | <= | 0.0144244 | 0.05 | PASS |
| linear-method-agreement | <= | 1.427642e-12 | 1.000000e-08 | PASS |
| tet4-h-observed-order | >= | 1.10024 | 1 | PASS |
| tet4-h-finest-error | <= | 0.185056 | 0.2 | PASS |
| tet4-h-monotonicity | <= | 0 | 1.000000e-12 | PASS |
| tet4-h-max-residual | <= | 1.264181e-10 | 1.000000e-08 | PASS |
| tet4-free-residual | <= | 4.398517e-12 | 1.000000e-08 | PASS |
| tet10-free-residual | <= | 3.379510e-11 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| reference_tip_uz | -2.961371e-05 |
| tet4_tip_uz | -1.406980e-05 |
| tet10_tip_uz | -2.918655e-05 |
| tet10_relative_error | 0.0144244 |
| tet4_h_observed_order | 1.10024 |
| tet4_h_pair_orders | [-0.608982089172146, 1.2206385723303312, 1.2857479485043015, 0.9663457541418392, 1.1920526391449247] |
| tet4_h_finest_relative_error | 0.185056 |
| observed_order | 1.10024 |
| finest_relative_error | 0.185056 |
| asymptotic_levels | [4, 5, 6] |
| monotonicity_violation | 0 |
| max_free_relative_residual | 1.264181e-10 |

### Convergence h TET4 calculee

| Niveau | h nominal [m] | Noeuds | Elements | Uz bout [m] | Erreur relative | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.82 | 102 | 226 | -1.470659e-05 | 0.503386 | 6.374225e-11 |
| 2 | 0.68 | 116 | 252 | -1.290638e-05 | 0.564175 | 8.662287e-11 |
| 3 | 0.56 | 148 | 329 | -1.643170e-05 | 0.445132 | 7.139724e-11 |
| 4 | 0.46 | 270 | 679 | -1.937748e-05 | 0.345658 | 8.255638e-11 |
| 5 | 0.36 | 429 | 1182 | -2.153639e-05 | 0.272756 | 9.814925e-11 |
| 6 | 0.26 | 773 | 2509 | -2.413352e-05 | 0.185056 | 1.264181e-10 |

### Conclusion automatique

La fleche TET4 converge de facon monotone: l'erreur passe de `50.339%` a `18.506%` sur six maillages, avec un ordre observe de `1.100`. Le critere de deplacement est satisfait dans l'intervalle teste; cette conclusion ne qualifie pas une contrainte locale de bord.
