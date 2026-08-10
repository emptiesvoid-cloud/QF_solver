---
doc_id: DOC-VNV-MITC3-LAMINATE-DYN-001
revision: 0.3
status: draft
applicable_version: ">=0.3.0"
reviewer: ""
approver: ""
---

# V&V MITC3+ multicouche statique et dynamique

## Resultat de la campagne

`VNV-MITC3-LAMINATE-DYNAMIC-001` reunit une verification analytique du patch
membranaire, puis modal, Newmark et harmonique sur un porte-a-faux MITC3+
`8 x 2` en `[0/90/90/0]`. La campagne est interne et reproductible : elle
verifie la coherence de `K`, `M`, de la reduction du drilling et des trois
routes dynamiques. Elle ne remplace pas une correlation structurelle
independante.

Les resultats calcules sont conserves dans
`qualification/vnv/mitc3_laminate_dynamic/reference/summary.json`.

| Controle | Valeur observee | Limite | Verdict |
| --- | ---: | ---: | --- |
| Patch membranaire affine, maillage fin | `8.48e-13` | `1e-10` | PASS |
| Plis post-traites en statique | `4` | `4` | PASS |
| Residus propres relatifs | `2.40e-09` | `1e-07` | PASS |
| Orthogonalite masse | `5.24e-16` | `1e-07` | PASS |
| Orthogonalite raideur | `9.91e-12` | `1e-07` | PASS |
| DDL drilling condenses | `24` | `> 0` | PASS |
| Erreur Newmark T/80 | `2.62e-03` | `1e-02` | PASS |
| Derive energie Newmark | `1.65e-12` | `1e-04` | PASS |
| Erreur harmonique complexe | `1.84e-08` | `1e-06` | PASS |
| Limite statique harmonique | `< 1e-09` | `1e-09` | PASS |
| Post-traitement harmonique | `4` plis | `4` plis | PASS |

## Correlation externe de reponse

`VNV-MITC3-LAMINATE-DYNAMICS-CODEASTER-DST-019` compare le porte-a-faux
multicouche sur le meme maillage `12 x 3` TRIA3 a Code_Aster 18.1 DST. Les
ecarts maximaux observes sont `3,957 %` sur les quatre frequences, `2,318 %`
sur l'historique Newmark et `1,345 %` sur la reponse harmonique complexe,
tous sous les seuils traces. Les artefacts sont archives dans
`qualification/vnv/external/code_aster_mitc3_laminate_dynamic/reference/`.

Cette correlation porte sur des observables de reponse globale. Une campagne
CalculiX distincte couvre les contraintes planes par pli; elle ne transforme
pas les observables dynamiques globaux en preuve de contraintes dynamiques.

## Correlation externe des contraintes par pli

`VNV-MITC3-LAMINATE-PLY-STRESS-CALCULIX-S6-020` compare le patch membranaire
affine `[0/90/90/0]` a CalculiX 2.20 `S6 COMPOSITE`, aux points d'integration
et dans les axes materiau. Sur le maillage final `16 x 4` (128 triangles),
l'ecart L2 combine de `S11`, `S22`, `S12` des quatre plis est `0,09625 %`,
sous le seuil de `2 %`. Le dernier increment CalculiX est `0,07313 %`, sous
le seuil de stabilisation de `0,2 %`; l'erreur analytique du patch QF_solver
est `2,278e-13`.

![Correlation de contraintes par pli MITC3+](../assets/reviews/mitc3_laminate_ply_stress_calculix.png)

La comparaison exclut volontairement les bords libres, `S13`, `S23`, la
flexion, les contraintes interlaminaires et toute extrapolation nodale. Les
artefacts sont archives dans
`qualification/vnv/external/calculix_mitc3_laminate_ply_stress/reference/`.

## Decision de maturite

Les couples `MITC3 / laminate_linear_static` et `MITC3 / laminate_dynamic`
passent de `smoke_tested` a `verified_development_external_correlation`. Ils
restent hors scope Owner accepte tant que ne sont pas disponibles :

1. au moins un stratifie courbe/facettise avec axe materiau projete ;
2. une Owner review dediee fixant domaine d'emploi et tolerances.

Les chiffres, images et manifestes sont generes par le solveur. Aucun resultat
numerique n'est recopie manuellement dans cette page.
