---
doc_id: DOC-HEX8-023-003
revision: 0.2
status: accepted_for_release_0_2_3
applicable_version: 0.2.3a0
date: 2026-08-24
release_source_sha: 18884d9
owner_review: signed_by_owner
decision: accepted_for_release_0_2_3
reviewer: "Owner"
approver: "Owner"
---

# Revue Owner - HEX8 et gate 0.2.3 alpha

## Usage du document

Cette revue a ete acceptee par l'Owner apres fermeture technique des gates
H8-G01 a H8-G12. La decision est `accepted_for_release_0_2_3` et couvre
uniquement le perimetre HEX8 lineaire documente.

## Contexte de preuve a joindre

- commit examine : `18884d9` (source poussee sur GitHub et verifiee par le
  blocker engineering final; le tag de release sera aligne sur le commit
  final contenant les artefacts documentaires);
- plateforme et versions : `Windows, Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, psutil 7.2.2; PETSc/Gmsh non requis pour cette campagne; CalculiX 2.20; Code_Aster 18.1`;
- dossier V&V HEX8 : `docs/assets/verification/hex8/internal/summary.json` genere par `verify-hex8-campaign --external`;
- correlation externe obligatoire : `docs/assets/verification/hex8/internal/summary.json` (section CalculiX C3D8), ecarts 1.20e-6 et 1.96e-6;
- correlation externe complementaire : `docs/assets/verification/hex8/code_aster/summary.json`, HEXA8, ecart 4.18e-16 sur le noeud charge;
- comparaison TET4/TET10/HEX8 : section `tet_hex_benchmark` du meme summary, 81 DDL par cas, nnz/temps/CSR/delta RSS;
- rapport de non-regression : `1429 passed, 14 skipped, 186 deselected` avec
  `python qf_solver.py verify-all --profile engineering` ; les verifications
  mecaniques et TET10 associees terminent egalement `GLOBAL STATUS: PASS`.

## Questions de decision

| ID | Question | Reponse Owner | Observation et lien de preuve |
| --- | --- | --- | --- |
| Q1 | Les fonctions de forme, Jacobien, gradients, Gauss et le rejet des orientations invalides couvrent-ils le domaine HEX8 revendique ? | `OUI` | Kernel HEX8, Jacobien invalide et integration `2x2x2` : `PASS_INTERNAL`. |
| Q2 | Les matrices K/M et les chargements volumiques ou de faces QUAD4 sont-ils coherents avec les resultantes et conventions documentees ? | `OUI` | Rigidite, masse coherente, body force, traction et pression QUAD4 : `PASS_INTERNAL`. |
| Q3 | L'import Gmsh HEX8/QUAD4 et les groupes physiques preservent-ils connectivite, orientation et BC ? | `OUI` | Import standard Gmsh, groupes physiques, orientation et workflow de resolution : `PASS`. |
| Q4 | Le post-traitement Gauss et la recuperation nodale sont-ils verifies sans masquer les singularites ? | `OUI` | Huit points de Gauss, champs finis, recuperation nodale et export VTK : `PASS_INTERNAL`. |
| Q5 | Les analyses statique, modale, Newmark et harmonique reutilisent-elles les contrats d'analyse communs sans chemin HEX8 special ? | `OUI` | Les quatre analyses passent par l'assembleur et le backend communs : `PASS_INTERNAL`. |
| Q6 | La couche sparse/HPC commune et les diagnostics de convergence restent-ils utilises, avec SciPy fonctionnel sans PETSc ? | `OUI` | SciPy reste autonome ; PETSc est optionnel ; aucune branche de solveur HEX8 n'est introduite. |
| Q7 | Les cas V&V severes, y compris distorsion et `nu=0.49/0.499`, ont-ils des erreurs physiques finales `<= 1 %` dans le domaine declare ? | `OUI` | Convergence h finale `0,735 %`, distorsion, modes, Newmark, harmonique et `nu=0.49/0.499` passent dans le périmètre documenté. |
| Q8 | Les correlations externes CalculiX C3D8 et Code_Aster HEXA8 sont-elles faites sur geometrie, maillage, materiau, BC et charge identiques ? | `OUI` | CalculiX : `1,20e-6` et `1,96e-6` ; Code_Aster : `4,18e-16` ; mêmes cas de référence. |
| Q9 | Le comparatif TET4/TET10/HEX8 publie-t-il precision, temps, RAM, DDL et nnz sans extrapolation abusive ? | `CONDITIONNEL` | Trois modèles et métriques publiés ; conclusion descriptive uniquement, sans classement universel ni promesse de scaling. |
| Q10 | Les exclusions, limitations et resultats non favorables sont-ils visibles dans la documentation publique ? | `OUI` | Contact, plasticité HEX8, grandes transformations, WEDGE, thermique, intégration réduite et limites de taille sont explicitement exclus. |

## Decision finale

| Champ | Valeur |
| --- | --- |
| Decision Owner | `accepted_for_release_0_2_3` - acceptee et signee par l'Owner |
| Justification | Les gates techniques H8-G01 à H8-G12 sont PASS, les corrélations statiques externes sont PASS et la non-régression complète est PASS. |
| Conditions ou recommandations | Maintenir les exclusions publiées ; ne pas extrapoler aux contacts, grandes transformations, intégration réduite ou multi-million de DDL. |
| Nom / role | Quentin Farinazzo / Owner |
| Date | 2026-08-24 |
| Signature | Validation Owner approuvee dans le cadre de la release 0.2.3a0 |

Les decisions possibles sont `accepted_for_release_0_2_3`,
`accepted_with_recommendations` ou `more_evidence_required`. La decision
`accepted_for_release_0_2_3` ferme le gate de release lorsque tous les H8-G01 a
H8-G12 sont `PASS`; elle ne leve aucune exclusion de perimetre.
