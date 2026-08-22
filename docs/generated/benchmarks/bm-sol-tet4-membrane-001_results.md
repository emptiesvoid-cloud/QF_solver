## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | PASS |
| Noeuds | 737 |
| Elements | 2402 |
| Amplification graphique | 1301.16 |
| Empreinte maillage/source | `1c499f5e23f879e0fbbe72b7140299808ff6584e62fc428f84af161ee235b708` |
| Empreinte configuration/source | `fab56b8adb4b37dbe4f0a1b405b64841a757f29c65c9fcbd16e853c75feb2995` |
| Empreinte modele | `1afb9afde99d1fc3ef9ff58c099dc48fe087113fc3e97c8290eb162066a946d8` |
| Empreinte resultat | `158787cb43946344de4f2dbda633aa2dd6f5b8e03a65b6c1cdd0feb6f5c6710c` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| membrane-displacement | <= | 3.604972e-15 | 1.000000e-09 | PASS |
| membrane-constant-stress | <= | 2.350059e-14 | 1.000000e-09 | PASS |
| membrane-free-residual | <= | 7.247104e-14 | 1.000000e-08 | PASS |
| compression-displacement | <= | 3.604972e-15 | 1.000000e-09 | PASS |
| compression-constant-stress | <= | 2.350059e-14 | 1.000000e-09 | PASS |
| compression-free-residual | <= | 7.247104e-14 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| reference_end_ux | 2.857143e-04 |
| membrane_resultant_nx | 2.000000e+06 |
| max_relative_displacement_error | 3.604972e-15 |
| max_relative_stress_error | 2.350059e-14 |

### Raffinement h du panneau membranaire

| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.34 | 88 | 208 | 2.857143e-04 | 2.466560e-15 | 7.437741e-15 | 1.655781e-14 |
| 2 | 0.24 | 170 | 431 | 2.857143e-04 | 9.486769e-16 | 8.374078e-15 | 2.809962e-14 |
| 3 | 0.17 | 254 | 640 | 2.857143e-04 | 3.604972e-15 | 1.033240e-14 | 3.030171e-14 |
| 4 | 0.13 | 419 | 1116 | 2.857143e-04 | 1.707618e-15 | 1.401359e-14 | 5.268071e-14 |
| 5 | 0.1 | 737 | 2402 | 2.857143e-04 | 3.604972e-15 | 2.350059e-14 | 7.247104e-14 |

### Raffinement h du panneau en compression

| Niveau | h [m] | Noeuds | Elements | Ux face libre [m] | Erreur Ux | Erreur contrainte | Residu libre |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.34 | 88 | 208 | -2.857143e-04 | 2.466560e-15 | 7.437741e-15 | 1.655781e-14 |
| 2 | 0.24 | 170 | 431 | -2.857143e-04 | 9.486769e-16 | 8.374078e-15 | 2.809962e-14 |
| 3 | 0.17 | 254 | 640 | -2.857143e-04 | 3.604972e-15 | 1.033240e-14 | 3.030171e-14 |
| 4 | 0.13 | 419 | 1116 | -2.857143e-04 | 1.707618e-15 | 1.401359e-14 | 5.268071e-14 |
| 5 | 0.1 | 737 | 2402 | -2.857143e-04 | 3.604972e-15 | 2.350059e-14 | 7.247104e-14 |

### Conclusion automatique

Les cinq maillages de traction et les cinq maillages de compression reproduisent le champ affine a l'arrondi pres: erreur deplacement maximale `3.605e-15` et erreur contrainte maximale `2.350e-14`. Il s'agit d'un patch d'exactitude, pas d'une estimation d'ordre asymptotique.
