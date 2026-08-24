---
doc_id: DOC-HEX8-023-002
revision: 0.2
status: accepted_for_release_0_2_3
applicable_version: 0.2.3a0
date: 2026-08-24
reviewer: ""
approver: "Owner"
---

# Gate de release 0.2.3 alpha - chaine HEX8 complete

## Regle non negociable

La version `0.2.3a0` ne peut etre presentee comme complete que lorsque chaque
ligne obligatoire de cette page est `PASS` et que la revue Owner est signee.
Le gate est ferme par la decision `accepted_for_release_0_2_3`; les limites
de perimetre restent opposables apres fermeture.

Les campagnes externes ne sont pas toutes executees par la CI rapide. Leur
resultat archive, sa configuration et son test de lecture restent toutefois
obligatoires pour fermer ce gate.

## Perimetre accepte avant execution

| Sujet | Regle de perimetre |
| --- | --- |
| Formulation de base | HEX8 elastique lineaire, isoparametrique, integration complete `2x2x2`. |
| Masse | Masse coherente requise. Masse lumped seulement si implemente et valide comme option distincte. |
| Analyses | Statique, modal, Newmark et harmonique via les chemins communs. |
| Import | Gmsh HEX8 et faces QUAD4, y compris groupes physiques de charge/BC. |
| Backend | Sparse SciPy et PETSc optionnel; aucun backend propre a HEX8. |
| Exclusions initiales | WEDGE, thermique, contact HEX8, plasticite HEX8, hyperelasticite et integration reduite non implementee. |
| Erreur physique | `<= 1 %` finale pour toute grandeur revendiquee dans les cas de V&V. |

## Matrice des gates

| Gate | Preuve attendue | Statut initial | Condition de fermeture |
| --- | --- | --- | --- |
| H8-G01 | Formulation, fonctions de forme, Jacobien, gradients et Gauss | PASS_INTERNAL | `verify-hex8`, tests unitaires et rejet determinant nul/negatif `PASS`. |
| H8-G02 | K, masse coherente et masse lumped optionnelle | PASS_INTERNAL | Symetrie, masse totale, energie, masse lumped et regressions `PASS`. |
| H8-G03 | Forces volumiques, gravite, traction et pression QUAD4 | PASS_INTERNAL | Resultantes body/traction/pressure et orientation de face `PASS`. |
| H8-G04 | Contraintes/deformations Gauss et recuperation nodale | PASS_INTERNAL | Patch affine, 8 points de Gauss, recuperation nodale et finitude `PASS`. |
| H8-G05 | Statique, modal, Newmark et harmonique | PASS_INTERNAL | Les quatre chemins communs rejoues avec HEX8 `PASS`. |
| H8-G06 | Import Gmsh | PASS_INTERNAL | HEX8, QUAD4 et groupes physiques importes/rejoues `PASS`. |
| H8-G07 | Sparse et HPC | PASS_INTERNAL | Assemblage/backend communs reutilises; aucun backend HEX8 concurrent introduit. |
| H8-G08 | V&V interne severe | PASS_INTERNAL | Patch, traction, compression, cisaillement, flexion quadratique, distorsion, convergence h finale `0,735 %`, 5 modes, Newmark, harmonique et `nu=0.49/0.499` `PASS`; interpretation bornee. |
| H8-G09 | Correlation externe | PASS_EXTERNAL_CORRELATION | CalculiX 2.20/C3D8 et Code_Aster 18.1/HEXA8 sur meme maillage/BC/materiau/charge; erreurs CalculiX `1,20e-6`/`1,96e-6`, Code_Aster `4,18e-16`. |
| H8-G10 | Benchmark TET4/TET10/HEX8 | PASS_INTERNAL | 3 modeles x 3 familles; precision via residu, temps, nnz, CSR estime et delta RSS traces, avec planche comparative. |
| H8-G11 | Non-regression | PASS | `1429 passed, 14 skipped, 186 deselected` avec `verify-all --profile engineering`; verifications mecaniques et TET10 associees `GLOBAL STATUS: PASS`. |
| H8-G12 | Documentation et Owner review | PASS | Revue Owner signee le 2026-08-24 avec decision `accepted_for_release_0_2_3`; limites et recommandations conservees. |

## Conditions complementaires de release

1. Une preuve doit indiquer le commit, les versions des dependances, la
   plateforme, les parametres du solveur et les unites.
2. La correction numerique ne doit pas venir d'un changement de conventions,
   de charge, de BC ou de maillage non applique a la reference externe.
3. Le test Abaqus est supplementaire : son absence ne bloque pas la release
   si la correlation CalculiX ou Code_Aster obligatoire est complete. S'il est
   execute, `C3D8R` n'est comparable que si QF Solver fournit reellement une
   variante a integration reduite.
4. Tout echec de robustesse doit etre consigne. Il ne peut devenir une limite
   de domaine que par une decision Owner explicite, compatible avec les
   revendications de la release.
5. Les resultats de performance doivent etre reproductibles; aucune valeur
   isolee ne justifie une promesse generale de scalabilite.

## Paquet minimal de cloture

Le paquet de cloture contient :

- le tableau H8-G01 a H8-G12 complete avec liens vers les artefacts;
- les resultats detailles H8-VV-01 a H8-VV-10 et H8-XV-01;
- le comparatif TET4/TET10/HEX8 H8-PERF-01;
- la correlation complementaire Code_Aster `docs/assets/verification/hex8/code_aster/summary.json`;
- les rapports de non-regression et la liste des exclusions;
- les versions des outils et une empreinte de l'environnement;
- la [revue Owner](qf_solver_0_2_3_alpha_hex8_owner_review.md) renseignee et
  signee avec la decision `accepted_for_release_0_2_3`.

## Etat courant

Les gates H8-G01 a H8-G12 disposent maintenant de preuves internes, et H8-G09
dispose de deux correlations externes statiques : CalculiX C3D8 et Code_Aster
HEXA8. La preuve Code_Aster est archivee dans
`docs/assets/verification/hex8/code_aster/summary.json` et a ete executee dans
`simvia/code_aster:18.1.0`; elle reste bornee a un maillage structure et une
charge nodale. La non-regression complete est egalement `PASS`. H8-G12 est
ferme par la revue et la signature Owner du 2026-08-24 avec la decision
`accepted_for_release_0_2_3`. La publication PyPI et la GitHub Release restent
des decisions separees de l'Owner. Les correlations externes restent statiques;
les chemins modal, dynamique et les grandes tailles ne sont pas extrapoles.
