## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | PASS |
| Noeuds | 737 |
| Elements | 2402 |
| Amplification graphique | 1398.08 |
| Empreinte maillage/source | `44f70b40993264088934c890dba30a9ebe9701f668cb44c667cc3b8017ddb656` |
| Empreinte configuration/source | `fab56b8adb4b37dbe4f0a1b405b64841a757f29c65c9fcbd16e853c75feb2995` |
| Empreinte modele | `85730b802dc8bd1bf3a4eb8eb245616aaf82c1b2843379fbdbf1f2329255d204` |
| Empreinte resultat | `15d425fe08a9d0930fc99056ea45f901f14742e3040cf7d5ae399ba979c1d322` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| membrane-displacement | <= | 8.917563e-15 | 1.000000e-09 | PASS |
| membrane-constant-stress | <= | 3.426641e-14 | 1.000000e-09 | PASS |
| membrane-free-residual | <= | 7.175396e-14 | 1.000000e-08 | PASS |
| compression-displacement | <= | 8.917563e-15 | 1.000000e-09 | PASS |
| compression-constant-stress | <= | 3.426641e-14 | 1.000000e-09 | PASS |
| compression-free-residual | <= | 7.175396e-14 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| reference_end_ux | 2.857143e-04 |
| membrane_resultant_nx | 2.000000e+06 |
| max_relative_displacement_error | 8.917563e-15 |
| max_relative_stress_error | 3.426641e-14 |

### Raffinement h du panneau membranaire

| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.34 | 88 | 208 | 2.857143e-04 | 3.225501e-15 | 8.078248e-15 | 1.761019e-14 |
| 2 | 0.24 | 170 | 431 | 2.857143e-04 | 7.589415e-16 | 7.831291e-15 | 2.859552e-14 |
| 3 | 0.17 | 254 | 640 | 2.857143e-04 | 2.846031e-15 | 1.575728e-14 | 3.348023e-14 |
| 4 | 0.13 | 419 | 1116 | 2.857143e-04 | 8.917563e-15 | 2.647163e-14 | 5.742590e-14 |
| 5 | 0.1 | 737 | 2402 | 2.857143e-04 | 8.727827e-15 | 3.426641e-14 | 7.175396e-14 |

### Raffinement h du panneau en compression

| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.34 | 88 | 208 | -2.857143e-04 | 3.225501e-15 | 8.078248e-15 | 1.761019e-14 |
| 2 | 0.24 | 170 | 431 | -2.857143e-04 | 7.589415e-16 | 7.831291e-15 | 2.859552e-14 |
| 3 | 0.17 | 254 | 640 | -2.857143e-04 | 2.846031e-15 | 1.575728e-14 | 3.348023e-14 |
| 4 | 0.13 | 419 | 1116 | -2.857143e-04 | 8.917563e-15 | 2.647163e-14 | 5.742590e-14 |
| 5 | 0.1 | 737 | 2402 | -2.857143e-04 | 8.727827e-15 | 3.426641e-14 | 7.175396e-14 |

### Conclusion automatique

Les cinq maillages de traction et les cinq maillages de compression reproduisent le champ affine a l'arrondi pres: erreur deplacement maximale `8.918e-15` et erreur contrainte maximale `3.427e-14`. Il s'agit d'un patch d'exactitude, pas d'une estimation d'ordre asymptotique.
