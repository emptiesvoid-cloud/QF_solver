---
doc_id: DOC-VNV-ORTHOTROPIC-LARGE-008
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.1-alpha
owner_review: pending
reviewer: ""
approver: ""
---

# V&V TET4 orthotrope grand modele

**Etude :** `VNV-ORTHOTROPIC-LARGE-STATIC-008`  
**Statut automatique :** `PASS_TECHNICAL_VERIFICATION`  
**Maturite :** `experimental`  
**Perimetre :** statique lineaire, TET4, materiau orthotrope homogene, chemin large modele.

## Objet

Cette etude verifie que le chemin large modele conserve la reponse du solveur
standard sur un meme bloc TET4 orthotrope. Le meme modele est traite par
l'assembleur large SciPy, par le chemin matrix-free et par le solveur standard.
La comparaison est interne et independante entre chemins numeriques; elle ne
constitue pas une correlation externe Code_Aster.

## Modele

Le bloc comporte `8 x 4 x 3` cellules, `576` TET4, `180` noeuds et `540` DDL.
Le materiau utilise `E1=145 GPa`, `E2=12 GPa`, `E3=9 GPa`, les constantes de
Poisson `0,24 / 0,21 / 0,28`, les cisaillements `G12=5,5 GPa`,
`G13=4,8 GPa`, `G23=3,9 GPa` et une orientation materiau tournee de 45 degres
dans le plan XY. La face gauche est bloquee et une force repartie est appliquee
sur la face droite.

## Resultats

| Verification | Valeur | Limite | Verdict |
| --- | ---: | ---: | --- |
| Deplacement large / standard | `1,06e-11` | `1,00e-09` | PASS |
| Deplacement matrix-free / assemble | `1,38e-12` | `1,00e-07` | PASS |
| Energie interne / travail externe | `4,59e-15` | `1,00e-08` | PASS |
| Deplacements finis | oui | obligatoire | PASS |

Les chemins SciPy large et matrix-free convergent respectivement en `220` et
`219` iterations. Le residu solveur large est `1,79e-08`; l'audit de maillage,
de matrice et de solution retourne `PASS`.

## Interpretation

La comparaison montre que la materialisation HDF5 et le chemin large ne changent
pas la solution sur ce cas borne. La limite isotrope et l'orientation constante
sont couvertes par les tests unitaires associes. Cette preuve ne permet pas de
conclure sur un modele orthotrope a un million de DDL : la campagne PETSc a un
million de DDL disponible dans le projet est isotrope.

La correlation Code_Aster des solides orthotropes est disponible sur une
eprouvette perforee et une equerre 3D dans
`qualification/vnv/external/orthotropic_solids/reference/summary.json`.
Elle ne remplace pas une correlation Code_Aster du chemin large orthotrope.

## Limites et actions ouvertes

- `orientation_field` element par element reste hors du chemin large v1.
- La dynamique orthotrope distribuee reste hors scope.
- La correlation Code_Aster du MITC3 multicouche courbe a orientation projetee
  reste ouverte; la preuve MITC3/DST actuelle est plane.
- Une revue Owner est necessaire avant toute promotion de maturite.

## Artefacts et tracabilite

- Etude : `qualification/vnv/orthotropic_large_static/study.json`
- Resultats : `qualification/vnv/orthotropic_large_static/reference/summary.json`
- Rapport : `qualification/vnv/orthotropic_large_static/reference/report.md`
- Manifeste : `qualification/vnv/orthotropic_large_static/reference/vnv_manifest.json`
- Exigence : `REQ-COMP-008`
- Archive active : `qualification/evidence/release_vv_artifacts_2026-08-14-r14/`
