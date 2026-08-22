---
doc_id: DOC-VNV-COMP-CODEASTER-NAFEMS-001
revision: 0.2
status: draft
applicable_version: 0.2.1-alpha
owner_review: pending
reviewer: ""
approver: ""
---

# Corrélation composite Code_Aster / NAFEMS R0031

**Étude :** `VNV-COMP-NAFEMS-R0031-CODEASTER-004`  
**Date d'exécution :** 2026-08-14  
**Statut automatique :** `PASS_EXTERNAL_CORRELATION`  
**Maturité :** expérimental, en attente de revue Owner

## Objet

Cette étude compare QF_solver et Code_Aster sur le benchmark publié NAFEMS
R0031/1 d'une bande stratifiée chargée en flexion trois points. Les deux
solveurs utilisent les mêmes niveaux de maillage et la même grandeur de
comparaison : le déplacement transverse `UZ` au point E. La comparaison des
contraintes `S11` est informative ; elle ne remplace pas une extraction
identique au point de référence NAFEMS.

Le calcul Code_Aster a été exécuté dans Docker avec la version et l'image
décrites dans le rapport généré. Le résultat est une corrélation externe
reproductible, pas une qualification automatique du stratifié.

## Résultats

| Maillage | Éléments | QF `UZ` [mm] | Code_Aster `UZ` [mm] | Écart QF/NAFEMS | Écart Code_Aster/NAFEMS | Écart QF/Code_Aster |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 × 2 | 20 | -1,050640 | -1,059952 | 0,883 % | 0,005 % | 0,879 % |
| 20 × 4 | 80 | -1,059397 | -1,063727 | 0,057 % | 0,352 % | 0,407 % |
| 40 × 8 | 320 | -1,062388 | -1,065414 | 0,225 % | 0,511 % | 0,284 % |
| 80 × 16 | 1 280 | -1,063822 | -1,066547 | 0,361 % | 0,618 % | 0,256 % |
| 160 × 32 | 5 120 | -1,064851 | -1,067529 | 0,458 % | 0,710 % | 0,251 % |

La référence NAFEMS utilisée est `UZ(E) = -1,06 mm`. L'incrément entre les
deux derniers niveaux est de `0,0967 %` pour QF_solver et `0,0920 %` pour
Code_Aster, sous le seuil de `0,2 %` de l'étude.

### Lecture de la référence NAFEMS

La valeur publique `UZ(E) = -1,06 mm` est une cible scalaire publiée, non une
solution continue fournie à chaque niveau de maillage. Après le niveau
`20 x 4`, QF_solver et Code_Aster s'en éloignent légèrement, alors que leurs
incréments finaux restent sous `0,1 %` et que leur écart mutuel vaut seulement
`0,2509 %` au niveau `160 x 32`. La figure ne doit donc pas être lue comme une
divergence de Code_Aster, ni comme une convergence monotone de QF_solver vers
une asymptote connue : elle montre une stabilisation des deux discrétisations
autour d'une cible publique de précision finie. Cette campagne ne permet pas
d'attribuer le décalage à une seule cause; les formulations MITC4 et DST/DSQ
restent différentes.

![Courbe de convergence NAFEMS R0031](../assets/reviews/nafems_r0031_convergence.png)

![Maillage et déformée NAFEMS R0031](../assets/reviews/nafems_r0031_deformation.png)

## Interprétation mécanique

La stabilisation des deux réponses et l'écart fin QF_solver / Code_Aster sous
`0,3 %` soutiennent la cohérence globale de la formulation stratifiée pour ce
cas borné. La contrainte `S11` QF_solver est échantillonnée aux centres
d'éléments voisins du point E ; elle reste donc une indication de champ et non
un critère d'acceptation ponctuel.

La récupération interlaminaire `S13` au point D n'est pas encore disponible
dans QF_solver. Le délaminage, la rupture progressive et la calibration sur
essais ne font pas partie de cette étude.

## Traçabilité

- Résumé : `qualification/vnv/external/code_aster_composite_nafems/reference/summary.json`
- Rapport généré : `qualification/vnv/external/code_aster_composite_nafems/reference/report.md`
- Manifeste : `qualification/vnv/external/code_aster_composite_nafems/reference/vnv_manifest.json`
- Archive de release : `qualification/evidence/release_vv_artifacts_2026-08-14-r14/`
- Exigence : `REQ-COMP-005`

Une décision Owner doit encore confirmer l'usage et les limites de cette
preuve avant toute évolution de maturité.
