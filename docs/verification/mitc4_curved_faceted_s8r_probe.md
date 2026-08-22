# MITC4 multicouche courbe - sonde S8R sur surface facettisée

**Etude** : `VNV-COMP-CURVED-ORIENTATION-008`  
**Date** : 2026-08-21  
**Statut** : `PASS_EXTERNAL_CORRELATION`, mais **non-promouvable stable**

## Objet

La comparaison initiale utilisait une surface cylindrique quadratique exacte
pour CalculiX `S8R`, alors que MITC4 représente la coque par facettes planes.
Cette campagne place les nœuds milieux S8R sur la même surface bilinéaire
facettisée que les quatre nœuds MITC4. Elle isole donc mieux la différence entre
les formulations élémentaires.

## Résultats

| Niveau | Éléments | Écart vectoriel | Écart UZ |
| --- | ---: | ---: | ---: |
| 8x4 | 32 | 10,3088 % | 10,3274 % |
| 16x8 | 128 | 3,3206 % | 3,3268 % |
| 24x12 | 288 | 0,9723 % | 0,9741 % |
| 48x24 | 1 152 | 1,1099 % | 1,1119 % |
| 96x48 | 4 608 | 1,8296 % | 1,8330 % |

La série n'est pas monotone autour de 1 %. Le dernier niveau reste à
`1,829575 %`, malgré cinq niveaux et une orientation orthonormale à moins de
`6e-16`. Le résultat ne satisfait donc pas le critère `STABLE-1PCT-POLICY`.

## Conclusion mécanique

La suppression de la différence de géométrie exacte/facettisée ne suffit pas à
fermer l'écart. La preuve indique une différence résiduelle de formulation,
de chargement ou de traitement de coque qui doit être analysée séparément. Elle
ne justifie ni une tolérance à 3 %, ni une promotion automatique.

Le scope `mitc4-laminate-static` reste donc
`accepted_for_bounded_engineering_use`. Une promotion `stable` demande encore
une référence analytique adaptée ou une analyse formelle de l'observable avec
une décision Owner datée, sans supprimer la règle de 1 %.

**Artefacts contrôlés** :

`qualification/vnv/external/calculix_curved_orientation_faceted_004/reference/`
