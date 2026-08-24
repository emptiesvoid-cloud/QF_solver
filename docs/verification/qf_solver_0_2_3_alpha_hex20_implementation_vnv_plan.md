---
doc_id: DOC-HEX20-023-001
revision: 0.1
status: controlled
applicable_version: 0.2.3a0
reviewer: ""
approver: ""
---

# Plan d'implementation et V&V HEX20 - QF_solver 0.2.3 alpha

## Objet et regle de release

Cette campagne ajoute un element solide isoparametrique quadratique HEX20,
avec l'ordre de noeuds Gmsh type 17 : huit noeuds de sommet puis douze
noeuds de milieu d'arete. Elle reutilise l'assembleur sparse, les solveurs et
les contrats d'analyse existants.

La campagne est close pour la release `0.2.3a0` : les correlations externes,
la non-regression et la revue Owner sont archivees dans le gate de release.
Cette cloture ne vaut pas qualification stable generale.

Le perimetre exclut pour cette tranche WEDGE, thermique, hyperelasticite,
contact HEX20 et grandes transformations. La plasticite J2 petites
deformations est incluse comme gate experimental distinct.

## Architecture cible

```text
Gmsh HEX20 / faces QUAD8
        -> importeur et modele standard
        -> HEX20: fonctions de forme, Jacobien, K, M, charges, post-traitement
        -> assemblage CSR commun et reduction des DDL
        -> solveur_backend commun: SciPy / PETSc optionnel
        -> statique | modal | Newmark | harmonique | Newton-Raphson J2
        -> resultats, diagnostics et preuves V&V
```

HEX20 ne doit introduire ni assembleur, ni backend, ni chemin d'analyse
special. Les formulations lineaires et J2 passent par les interfaces
elementaires deja utilisees par TET4 et TET10.

## Lots obligatoires

| Lot | Contenu | Critere de fermeture |
| --- | --- | --- |
| H20-01 Formulation | Fonctions de forme serendipity, derivees naturelles, Jacobien, gradients physiques et integration de Gauss `3x3x3`. | Partition de l'unite, interpolation nodale Gmsh, Jacobien positif et rejet des geometries invalides. |
| H20-02 Matrices | Rigidite elastique, masse coherente et masse lumped par somme de lignes. | Matrices `60x60` symetriques, masse totale correcte, energie affine et modes rigides. |
| H20-03 Chargements | Force volumique, gravite, traction et pression sur faces QUAD8. | Resultantes et orientation des normales conservees; integration face quadratique testee. |
| H20-04 Post-traitement | Deformations et contraintes aux 27 points de Gauss, moyenne volumique et recuperation nodale. | 27 points publies, conventions Voigt identiques, aucune erreur de dimension. |
| H20-05 Analyses | Statique, modal, Newmark et harmonique via les chemins communs. | Les quatre analyses terminent `PASS` sans solveur HEX20 special. |
| H20-06 J2 | Plasticite de von Mises petites deformations avec Newton-Raphson et etats aux points de Gauss. | Quatre increments, etats commites, convergence et 27 etats material. |
| H20-07 Import Gmsh | HEX20 type 17 et faces QUAD8 type 16 via l'importeur standard. | Connectivite, faces, BC et pression importees puis resolues. |
| H20-08 Sparse/HPC | Reutilisation de l'assembleur et des backends SciPy/PETSc existants. | Aucun second backend et aucune conversion dense ajoutee. |
| H20-09 V&V multi-modele | Trois modeles : cube, poutre elancee et cube distordu. Comparaison TET4/TET10/HEX8/HEX20. | 12 cas, DDL, elements, temps, nnz, CSR, RSS et residus archives. |
| H20-10 CalculiX | Meme maillage HEX20/C3D20, meme materiau, BC et charge. | Deck reproductible et resultat externe `PASS_EXTERNAL_CORRELATION`. |
| H20-11 Code_Aster | Meme maillage HEX20/HEXA20, meme materiau, BC et charge. | Script reproductible et resultat externe `PASS_EXTERNAL_CORRELATION`. |
| H20-12 Owner et release | Limites, exclusions, environnement, preuves et decision. | Revue signee; aucun champ de decision pre-rempli par le generateur. |

## Etat des preuves locales au 2026-08-24

Les elements suivants sont deja executes localement et ne constituent pas
encore une certification externe :

- H20-01/H20-02 : 11 controles mecaniques `PASS`, dont interpolation Gmsh,
  energie affine, six modes rigides, masse et `nu=0.49/0.499`.
- H20-03 : resultantes body force, traction et pression QUAD8 `PASS`.
- H20-04 : 27 points de Gauss et 20 resultats nodaux `PASS`.
- H20-05 : statique, modal, Newmark et harmonique `PASS`.
- H20-06 : J2 Newton-Raphson sur quatre increments, etats commites et 27
  points material `PASS`.
- H20-07 : import manuel Gmsh HEX20/QUAD8 et resolution de la pression `PASS`.
- H20-09 : `PASS_INTERNAL` sur 3 modeles x 4 familles, soit 12 calculs.
- H20-10 : correlation CalculiX C3D20 executee; ecart global `8.50e-7` et
  ecart au noeud charge `7.04e-7`, seuil `1 %`.
- H20-11 : correlation Code_Aster `MECA_HEXA20` executee; ecart au noeud
  charge `5.42e-15`, seuil `1 %`.

Artefacts attendus :

```text
src/solveur/elements/solid/hex20.py
src/solveur/verification/hex20.py
src/solveur/verification/hex20_calculix.py
src/solveur/verification/hex8_tet_benchmark.py
scripts/run_code_aster_hex20_vnv.py
docs/assets/verification/hex20/internal/summary.json
docs/assets/verification/hex20/comparison/summary.json
```

## Etat de cloture

1. Les tests de non-regression, la documentation et les audits publics ont ete
   rejoues : le blocker engineering termine `PASS`.
2. Les correlations externes et la revue Owner sont archivees ; le statut
   `accepted_for_release_0_2_3` ne transforme pas le scope en `stable`.

## Definition de termine

Le plan est termine uniquement lorsque H20-01 a H20-12 sont documentes avec
des preuves rejouables, les deux correlations externes sont passees, la
non-regression pertinente est propre et la decision Owner est explicite.
