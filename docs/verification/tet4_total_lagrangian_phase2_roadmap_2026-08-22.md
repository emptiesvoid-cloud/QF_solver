---

doc_id: TET4-TL-2-ROADMAP-001
revision: 0.1
status: opened_ready_to_execute
date: 2026-08-22
scope: tet4-total-lagrangian-structural-v2
applicable_version: 0.2.1a0
reviewer: ""
approver: ""
---

# TET4 total-lagrangien - phase 2 de preuve et de promotion

## Objectif

Faire sortir le TET4 total-lagrangien du statut `research` uniquement si les
preuves de maillage, de chemin non lineaire, de ressources et de correlation
externe convergent dans le même domaine. Le raffinement à environ `1,2 million`
d'elements est une expérience de convergence, pas une garantie de passer sous
`1 %`.

Les tickets sont ouverts dans
`qualification/tickets/tet4_total_lagrangian_phase2_2026-08-22.json`.

## Execution du lot initial

Les campagnes suivantes ont ete relancees et passent : noyau, assemblage
Newton, sensibilite aux increments, contraintes/energie, correlation
CalculiX precritique, flambement Euler, raffinement `98 304` elements et
post-flambement sur trois imperfections.

La sonde cible `160x40x30`, soit `1 152 000` TET4, a ete tentee deux fois. Le
preflight etait favorable, mais le chemin actuel n'a produit aucun résumé
mécanique avant l'arrêt préventif : environ `47,85 Go` de mémoire privée lors
de la première tentative, puis `30,02 Go` lors de la seconde. Les deux verdicts
sont `RESOURCE_LIMIT_ABORTED`, pas `PASS` et pas `FAIL` mécanique. Les preuves
sont archivées dans `results/VNV-TET4-TL-PHASE2-LARGE-011/summary.json` et
`results/VNV-TET4-TL-PHASE2-LARGE-012/summary.json`, avec leurs rapports
associés.

Cette seconde tentative confirme que le chemin vectorisé actuel n'est pas
adapté à cette taille. Le périmètre reste donc explicitement
`research / more_evidence_required`, conformément à la décision de ne pas
promouvoir un calcul qui n'a pas produit de résultat mécanique vérifiable.

Cette observation ouvre le ticket d'optimisation tangent/matrix-free : le
raffinement à 1,2 million ne doit pas être relancé avec exactement la même
allocation dense par élément. Aucune nouvelle tentative n'est prévue avant ce
refactoring.

## Etat de depart

La campagne existante montre :

| Preuve | Resultat |
| --- | ---: |
| Flambement Euler, h5, 98 304 TET4 | erreur `1,8956 %` |
| Meme maillage, comparaison CalculiX | ecart `0,0343 %` |
| Post-flambement, 1 536 TET4, 120 pas | `PASS_POSTBUCKLING_RESEARCH` |
| Résidu post-flambement maximal | `9,52e-9` |
| `min det(F)` post-critique | `0,9832` |

La conclusion actuelle est techniquement positive mais ne permet pas une
promotion stable. L'accord avec CalculiX montre surtout que le chemin QF_solver
est reproductible sur le cas compare ; il ne remplace pas la reference Euler
ni une correlation de la branche post-critique.

## Lots de travail

### Lot A - Definition et reproductibilite

1. Figer la grandeur d'acceptation : charge critique, rapport charge-flèche ou
   branche post-critique. Ne pas changer de grandeur après le calcul.
2. Figer les conventions : encastrement, charge morte, imperfection, longueur,
   section, matériau et normalisation des erreurs.
3. Generer un manifeste d'entree, une empreinte du maillage et un résumé des
   options de résolution.

### Lot B - Raffinement et grand modele

1. Rejouer la suite existante `16x4x4`, `24x6x6`, `32x8x8`, `40x10x10` et
   `64x16x16`.
2. Ajouter un niveau proche de `1,2 million` d'elements, avec sortie compacte.
3. Mesurer la memoire de pointe, le temps d'assemblage, le temps de résolution,
   les iterations et le résidu final.
4. Vérifier que la baisse de l'erreur ne vient pas d'une tolérance relâchée ou
   d'un changement d'observable.

### Lot C - Robustesse non lineaire

1. Comparer Newton direct, Newton avec line-search et continuation arc-length.
2. Tracer à chaque pas le résidu, le determinant minimal de `F`, la plus petite
   valeur propre de la tangente et le nombre d'iterations.
3. Rejouer les imperfections `0,25 %`, `0,50 %` et `1,00 %`.
4. Verifier la sensibilité à `6`, `10` et `20` incréments ; `10` reste la valeur
   recommandee, `6` le minimum.

### Lot D - Correlation externe

La comparaison externe doit porter sur le même observable et le même chemin.
La branche précritique seule ne suffit pas pour accepter une revendication
post-critique. Les différences de formulation entre QF_solver, Code_Aster et
CalculiX seront indiquées dans le rapport, sans présenter un oracle comme une
identité de matrice.

### Lot E - Revue et decision

Le paquet final comprendra :

- le modèle d'entrée et le manifeste ;
- les résumés JSON par niveau ;
- les courbes de convergence et chemins charge-déplacement ;
- les figures de déformée et d'imperfection ;
- le bilan mémoire/temps ;
- la comparaison externe ;
- les limites et exclusions ;
- une revue indépendante.

## Gates de sortie

| Gate | Condition |
| --- | --- |
| G1 - Entree | modèle et unités vérifiés, empreinte disponible |
| G2 - Convergence | tendance documentée sur au moins cinq niveaux |
| G3 - Equilibre | résidu et determinant positifs sur le chemin accepte |
| G4 - Robustesse | résultat cohérent entre solveurs et réglages numeriques |
| G5 - Ressources | temps et mémoire publies pour le niveau large |
| G6 - Correlation | observable revendique compare sur la branche revendiquee |
| G7 - Revue | revue independante archivee |
| G8 - Promotion | tous les gates précédents PASS, sinon maintien `research` |

## Decision attendue

Trois decisions sont possibles :

1. `stable_bounded` si les gates passent uniquement dans le domaine teste ;
2. `accepted_for_bounded_engineering_use` si la mecanique est exploitable mais
   qu'une preuve de robustesse ou une revue manque ;
3. `research / more_evidence_required` si l'erreur, le chemin ou la correlation
   restent insuffisants.

Un résultat inférieur à `1 %` est nécessaire pour la cible proposée, mais il
n'est pas suffisant à lui seul. Le statut actuel reste donc inchangé tant que
la phase 2 n'est pas exécutée et relue.
