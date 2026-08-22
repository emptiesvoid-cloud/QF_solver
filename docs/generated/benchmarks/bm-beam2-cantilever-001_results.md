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
| Empreinte resultat | `c4ea00e072667004323f55d0b302ba2e58b6c1bdc013c6ff5b2f873735b2c05f` |

### Criteres d'acceptation

| Critere | Operateur | Valeur | Limite | Verdict |
| --- | :---: | ---: | ---: | --- |
| beam2-static-compliance | <= | 8.352682e-14 | 1.000000e-10 | PASS |
| beam2-modal-reference | <= | 4.777935e-04 | 0.02 | PASS |
| beam2-modal-increment | <= | 3.108702e-06 | 0.005 | PASS |
| beam2-modal-residual | <= | 2.529658e-09 | 1.000000e-08 | PASS |
| beam2-static-residual | <= | 5.659281e-12 | 1.000000e-08 | PASS |

### Metriques principales

| Metrique | Valeur |
| --- | --- |
| static_reference | 0.00238318 |
| euler_bernoulli_frequency_hz | 10.2657 |
| final_modal_increment | 3.108702e-06 |

### Convergence BEAM2

| Elements | Erreur statique | Frequence 1 [Hz] | Reference [Hz] | Erreur modale | Residu modal |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5.459269e-16 | 10.3102 | 10.2657 | 0.00433255 | 1.281433e-14 |
| 2 | 1.819756e-16 | 10.266 | 10.2657 | 2.707556e-05 | 1.333912e-12 |
| 4 | 2.183708e-15 | 10.2612 | 10.2657 | 4.395747e-04 | 5.761961e-11 |
| 8 | 6.423740e-14 | 10.2608 | 10.2657 | 4.746863e-04 | 2.239790e-10 |
| 16 | 8.352682e-14 | 10.2608 | 10.2657 | 4.777935e-04 | 2.529658e-09 |
