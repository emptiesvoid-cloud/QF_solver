---
doc_id: DOC-VV-002
revision: 0.1
status: draft controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Verification du maillage

Les erreurs bloquantes couvrent indices invalides, noeuds repetes dans un
element, materiau absent, element inverse ou degenere et ddl incompatible.

## Tetraedres

Les statistiques incluent volume, aretes min/max, aspect ratio, rayon inscrit
sur rayon circonscrit et indicateurs de distorsion. Un TET10 ajoute la position
des noeuds d'arete et les determinants du Jacobien echantillonnes.

## Coques

Les controles MITC4 couvrent aire projetee, Jacobien aux points de Gauss,
angles, ratio d'aretes, planeite et gauchissement par rapport au repere local.

## Blocages

La connectivite est decomposee en composantes. Une composante sans contrainte
est signalee. Pour les petits modeles, une estimation de rang de la matrice
reduite recherche des modes rigides restants.

Les seuils courants et leur statut sont detailles dans
[la documentation de qualite](../qualite_maillage.md). Une alerte de qualite
n'est pas automatiquement un echec: elle impose une etude de sensibilite.
