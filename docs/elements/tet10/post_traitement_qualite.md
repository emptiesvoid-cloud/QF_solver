---
doc_id: DOC-ELEM-TET10-04
revision: 0.2
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# TET10 - Post-traitement et qualite geometrique

## Valeurs aux points de Hammer

Les deformations et contraintes sont calculees aux quatre points utilises pour
la rigidite. Ces valeurs constituent le niveau elementaire directement relie
a l'integration.

## Extrapolation nodale

En elasticite, QF_solver ajuste un champ lineaire en coordonnees
barycentriques aux quatre valeurs de Hammer, puis l'evalue aux dix noeuds. Ce
processus reproduit exactement une contrainte lineaire, mais peut amplifier
les oscillations sur element distordu.

En plasticite, les contraintes de post-traitement utilisent les etats
committes. Les variables internes ne sont pas extrapolees comme si elles
etaient un champ polynomial lisse.

## Invariants

Chaque point et chaque valeur extrapolee contient contraintes principales,
deformations principales, trace, pression hydrostatique, deviateur et von
Mises. Les valeurs non finies provoquent un echec numerique, pas un resultat
partiel silencieux.

## Mesures de qualite

- volume signe des quatre coins;
- ecart des noeuds d'arete au milieu geometrique attendu;
- minimum et maximum de $\det J$ sur le lattice;
- rapport $\max(\det J)/\min(\det J)$;
- longueurs d'arete et aspect ratio des coins.

Une arete volontairement courbe peut produire un avertissement de noeud milieu
sans etre invalide. La decision doit alors s'appuyer sur le Jacobien, la
geometrie CAO et une etude de convergence.

## Limites

Le TET10 ne doit pas etre considere comme une correction automatique de tout
maillage TET4. Une courbure excessive, une quadrature inadaptee au materiau ou
un mauvais conditionnement peuvent degrader le resultat.

