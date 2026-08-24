---
doc_id: DOC-HEX8-023-001
revision: 0.1
status: controlled
applicable_version: 0.2.3a0
reviewer: ""
approver: ""
---

# Plan d'implementation et V&V HEX8 - QF_solver 0.2.3 alpha

## Objet et regle de release

Cette campagne introduit un element solide isoparametrique HEX8 dans le
backend existant. Les lots H8 sont executes et leur [gate de release](qf_solver_0_2_3_alpha_hex8_release_gate.md)
est ferme par la decision Owner `accepted_for_release_0_2_3`.

Le perimetre exclut WEDGE, thermique, hyperelasticite, contact HEX8 et toute
nouvelle physique sans lien direct avec HEX8. Une eventuelle integration
reduite est un sous-perimetre distinct : la premiere formulation ne doit pas
etre presentee comme equivalente a `C3D8R`.

## Architecture cible

```text
Gmsh HEX8 / faces QUAD4
        -> importeur et modele standard
        -> HEX8: K, M, F, contraintes aux points de Gauss
        -> assemblage CSR commun et reduction des DDL
        -> solver_backend: auto | scipy | petsc
        -> statique | modal | Newmark | harmonique
        -> resultats, diagnostics, post-traitement et preuves V&V
```

HEX8 ne doit introduire ni solveur propre, ni assembleur dense, ni chemin
d'analyse special. Les options de solveur, metriques de convergence et
protections memoire sont celles de la couche commune. La cible de code est
`src/solveur/elements/solid/hex8.py`, avec des extensions limitees du modele,
de l'importeur et du post-traitement lorsque leurs contrats generiques sont
insuffisants.

## Lots d'implementation

| Lot | Resultat attendu | Conditions de fermeture |
| --- | --- | --- |
| H8-01 Formulation | Fonctions de forme trilineaires, derivees naturelles, Jacobien et gradients physiques. Integration Gauss `2x2x2` pour la formulation complete. | Partition de l'unite, propriete de Kronecker, gradients verifies et rejet explicite des Jacobiennes nulles ou negatives. |
| H8-02 Matrices | Matrice de rigidite elastique lineaire et masse coherente. Masse lumped seulement si le contrat de masse commun le permet. | Symetrie, energie positive apres conditions aux limites, somme de masse et comparaison analytique. |
| H8-03 Chargements | Force volumique, gravite, traction et pression sur les faces QUAD4. | Somme des forces et moments, orientation des normales, pression opposee et faces physiques importeuses testes. |
| H8-04 Post-traitement | Deformations et contraintes aux points de Gauss, puis extrapolation ou recuperation nodale documentee. | Cas affine exact, conventions Voigt identiques aux solides existants et aucun lissage qui masque une singularite. |
| H8-05 Analyses | Statique, modal, Newmark et harmonique consomment le meme contrat K/M/F que TET4/TET10. | Aucun branchement `if HEX8` dans les solveurs d'analyse; invariants de resultat et non-regressions existantes passent. |
| H8-06 Import Gmsh | HEX8 et ses faces QUAD4 / groupes physiques passent par l'importeur standard. | Type Gmsh `5` (hexaedre 8 noeuds), type `3` (quadrangle 4 noeuds), orientation et BC de faces verifies. |
| H8-07 Sparse/HPC | Reutilisation de SciPy/PETSc et des diagnostics existants. | Pas de second backend; pas de conversion dense involontaire; options `auto`, `scipy`, `petsc` preservees. |
| H8-08 V&V interne | Matrice de cas analytiques, de convergence et de robustesse. | Toutes les grandeurs d'ingenierie revendiquees ont une erreur finale `<= 1 %`. |
| H8-09 Correlation externe | Rejouage avec une reference externe sur meme geometrie, maillage, materiau et BC. | CalculiX ou Code_Aster obligatoire; Abaqus uniquement si disponible. Resultats archives et rejouables. |
| H8-10 Comparatif TET/HEX | Comparaison a DDL comparables des couts et de la precision. | Temps, RAM, DDL, nnz et erreurs publies; conclusion limitee au cas compare. |

## Matrice V&V obligatoire

Les seuils `1 %` concernent les grandeurs physiques revendiquees en fin de
raffinement. Les residus, orthogonalites et conservations conservent leurs
seuils numeriques propres, documentes par cas.

| ID | Cas | Observables et criteres minimum |
| --- | --- | --- |
| H8-VV-01 | Patch 3D affine | Champ `u = A x + b`, deformations constantes, reactions et energie. Erreur au niveau de l'arrondi machine pour le champ representable. |
| H8-VV-02 | Traction / compression | Deplacement, contrainte moyenne et reaction; comparaison analytique et correlation externe; erreur finale `<= 1 %`. |
| H8-VV-03 | Flexion | Fleche, contrainte et reactions; au moins quatre maillages; erreur finale `<= 1 %` dans le domaine declare. |
| H8-VV-04 | Cisaillement | Champ de cisaillement, reactions et diagnostic de verrouillage; erreur finale `<= 1 %` ou domaine clairement exclu. |
| H8-VV-05 | Distorsion | Distorsions progressives, controle `det(J)`, comparaison a une reference et rejet des elements invalides. |
| H8-VV-06 | Convergence h | Au moins quatre niveaux, taille caracteristique, DDL, erreur et pente publies. Une valeur finale `<= 1 %` est obligatoire. |
| H8-VV-07 | Modal | Cinq premiers modes minimum, residu modal, orthogonalite de masse et frequences externes; erreur finale `<= 1 %`. |
| H8-VV-08 | Newmark | Raffinement temporel, deplacement/reaction ou energie, residu et correlation; erreur finale `<= 1 %`. |
| H8-VV-09 | Harmonique | Point basse frequence coherent avec statique, pic ou bande frequencielle definie, correlation et erreur finale `<= 1 %`. |
| H8-VV-10 | Quasi-incompressible | `nu=0.49` et `nu=0.499`, conditionnement, convergence et erreur. Aucun resultat ne peut etre generalise a des incompressibilites plus fortes. |
| H8-XV-01 | Correlation externe | Memes noeuds, elements, BC, charges et unites avec CalculiX `C3D8` ou Code_Aster; jeux et sorties archives. |
| H8-XV-02 | Abaqus supplementaire | `C3D8` pour la formulation complete, `C3D8R` seulement si une integration reduite QF est implementee; non bloquant si Abaqus indisponible. |
| H8-PERF-01 | TET vs HEX | Au moins trois modeles mecaniques (cube, poutre, distorsion), trois familles, erreur, nnz, temps assemblage, temps resolution, RAM et diagnostics. |

## Contrats de tests et d'artefacts

Les contrats ci-dessous sont implementes et leurs preuves archivees dans le
paquet de release. La decision de release conserve les exclusions ci-dessus :

```text
tests/unit/test_hex8_element.py
tests/unit/test_hex8_calculix.py
tests/integration/test_hex8_gmsh_import.py
tests/integration/test_hex8_workflow.py
src/solveur/verification/hex8.py
src/solveur/verification/hex8_campaign.py
src/solveur/verification/hex8_calculix.py
src/solveur/verification/hex8_tet_benchmark.py
docs/assets/verification/hex8/internal/summary.json
docs/assets/verification/hex8/internal/summary.json (correlation CalculiX)
docs/assets/verification/hex8/code_aster/summary.json
```

Chaque campagne archive le commit, la version Python, SciPy, PETSc/petsc4py
si employes, Gmsh, la plateforme, les options de solveur, les DDL, les nnz,
le temps d'assemblage, le temps de resolution, la RAM observee ou estimee et
les residus. Les references externes peuvent etre archivees; leur outil n'a
pas a etre execute dans la CI standard.

## Politique de non-regression et d'execution

1. Capturer une baseline des analyses statiques, modales, Newmark et
   harmoniques existantes avant chaque lot numerique.
2. Executer les tests unitaires et d'integration rapides a chaque changement.
3. Marquer les cas de grande taille et de preuve avec les marqueurs existants
   afin de ne pas ralentir la CI rapide.
4. Avant le gate de release, executer la campagne HEX8 complete, les preuves
   externes archivees, la documentation et les non-regressions pertinentes.
5. Comparer resultats, residus et metriques aux baselines; une acceleration
   ne compense jamais une degradation numerique.

## Decisions techniques anticipees

- Le point de depart est HEX8 a integration complete `2x2x2`. Le risque de
  verrouillage volumique ou de cisaillement doit etre mesure, pas masque.
- La masse coherente est la reference pour la modal et la dynamique. La masse
  lumped, si exposee, recoit sa propre V&V et ne remplace pas silencieusement
  la masse coherente.
- La comparaison TET/HEX ne cherche pas un vainqueur absolu : elle mesure le
  compromis sur les geometries et conditions documentees.
- Un echec a `nu=0.499`, sous forte distorsion ou sur un cas externe ne peut
  etre converti en exclusion implicite. Il bloque le gate ou devient une
  limite explicitement votee par l'Owner avant toute release.

## Definition de termine

Ce plan est termine uniquement lorsque les lots H8-01 a H8-10 sont `PASS`,
que le [registre de gate](qf_solver_0_2_3_alpha_hex8_release_gate.md) est
ferme, que les preuves sont rejouables, que les regressions applicables sont
propres et qu'une revue Owner enregistre une decision explicite.
