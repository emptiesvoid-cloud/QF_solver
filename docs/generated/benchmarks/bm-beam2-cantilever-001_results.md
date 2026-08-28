## Resultats regeneres

| Propriete | Valeur |
| --- | --- |
| Verdict | WARNING |
| Noeuds | 17 |
| Elements | 16 |
| Amplification graphique | 151.059 |
| Empreinte maillage/source | `87ce202f5a0b6155334c332432d383ae6c3b3b554995ab8a0e581b3119d1d1ba` |
| Empreinte configuration/source | `87ce202f5a0b6155334c332432d383ae6c3b3b554995ab8a0e581b3119d1d1ba` |
| Empreinte modele | `87ce202f5a0b6155334c332432d383ae6c3b3b554995ab8a0e581b3119d1d1ba` |
| Empreinte resultat | `66fa927c99db2dada9a3d07e9d6e716167463400cf4c1a12646387c3232c7bbd` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| beam2-static-compliance | <= | 8.352682e-14 | 1.000000e-10 | PASS |
| beam2-modal-reference | <= | 4.777935e-04 | 0.02 | PASS |
| beam2-modal-increment | <= | 3.108687e-06 | 0.005 | PASS |
| beam2-modal-residual | <= | 1.509774e-11 | 1.000000e-08 | PASS |
| beam2-static-residual | <= | 5.659281e-12 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| static_reference | 0.00238318 |
| euler_bernoulli_frequency_hz | 10.2657 |
| final_modal_increment | 3.108687e-06 |

### Convergence BEAM2

| Elements | Erreur statique | Frequence 1 [Hz] | Reference [Hz] | Erreur modale | Residu modal |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.459269e-16 | 10.3102 | 10.2657 | 0.00433255 | 1.884767e-15 |
| 2 | 1.819756e-16 | 10.266 | 10.2657 | 2.707556e-05 | 7.463063e-15 |
| 4 | 2.183708e-15 | 10.2612 | 10.2657 | 4.395747e-04 | 7.978053e-14 |
| 8 | 6.423740e-14 | 10.2608 | 10.2657 | 4.746863e-04 | 1.569872e-12 |
| 16 | 8.352682e-14 | 10.2608 | 10.2657 | 4.777935e-04 | 1.509774e-11 |
