---
doc_id: DOC-HEX20-023-003
revision: 0.2
status: owner_accepted_with_recommendations
applicable_version: 0.2.3a0
date: 2026-08-24
owner_review: signed_by_owner
decision: accepted_with_recommendations
reviewer: "Owner"
approver: "Owner"
---

# Revue Owner - HEX20 lineaire et J2 - 0.2.3 alpha

## Regle de soumission

Cette fiche a ete acceptee par l'Owner apres execution et archivage des gates
H20-G01 a H20-G12. La decision est `accepted_with_recommendations` et conserve
les limites et exclusions du domaine HEX20 documente.

La branche de travail reste non publiee : aucun commit, push, tag ou paquet
PyPI n'est autorise par cette etude.

## Dossier de preuves

- plan V&V : `docs/verification/qf_solver_0_2_3_alpha_hex20_implementation_vnv_plan.md` ;
- registre de gates : `docs/verification/qf_solver_0_2_3_alpha_hex20_release_gate.md` ;
- campagne interne : `results/hex20_internal/summary.json` et `report.md` ;
- comparaison trois modeles : `results/hex20_tet_multi_model/summary.json` ;
- deck externe CalculiX : `results/hex20_external_calculix/` ;
- resultat externe Code_Aster : `results/hex20_external_code_aster/` ;
- tests unitaires et integration HEX20 ;
- rapport de non-regression et environnement a joindre avant signature.

## Questions de decision

| ID | Question | Reponse Owner | Observation et preuve |
| --- | --- | --- | --- |
| Q1 | Les fonctions de forme HEX20, le Jacobien, les gradients, l'integration 3x3x3 et le rejet des geometries invalides couvrent-ils le domaine revendique ? | `OUI` | Interpolation Gmsh, Jacobien positif, 27 points et geometries invalides : `PASS_INTERNAL`. |
| Q2 | Les matrices K, masse coherente et masse lumped restent-elles coherentes, symetriques et compatibles avec les modes rigides ? | `CONDITIONNEL` | K, masse coherente, energie et modes rigides passent ; la masse lumped reste une option disponible mais non qualifiee pour cette release. |
| Q3 | Les forces volumiques, la gravite, les tractions et les pressions sur faces QUAD8 preservent-ils resultantes, normales et conventions de signe ? | `OUI` | Body force, traction, pression QUAD8, normales et signes : `PASS_INTERNAL`. |
| Q4 | Le post-traitement aux 27 points de Gauss et la recuperation des champs aux 20 noeuds sont-ils suffisamment verifies ? | `OUI` | 27 points de Gauss, 20 noeuds, moyenne volumique, recuperation nodale et export VTK : `PASS_INTERNAL`. |
| Q5 | Les analyses statique, modale, Newmark et harmonique reutilisent-elles les chemins communs sans backend ou assembleur HEX20 special ? | `OUI` | Les quatre analyses passent par l'assembleur et le backend communs : `PASS_INTERNAL`. |
| Q6 | Le chemin non lineaire J2 reutilise-t-il le Newton-Raphson et le stockage d'etat communs, avec une convergence explicite a chaque increment ? | `OUI borne` | Quatre increments, états commités, 27 points et résidu relatif maximal `1,672e-10` ; preuve interne seulement. |
| Q7 | L'import Gmsh type 17 avec faces QUAD8 type 16 preserve-t-il connectivite, orientation, groupes physiques, chargements et conditions aux limites ? | `OUI` | Types 17/16, connectivité, groupes, pression et résolution par l'importeur commun : `PASS`. |
| Q8 | Les cas internes de traction, compression, flexion, cisaillement, distorsion et `nu=0.49/0.499` sont-ils couverts sans extrapolation ? | `OUI` | Les cas internes et les contrôles `nu=0.49/0.499` passent ; le domaine reste linéaire et borné. |
| Q9 | La comparaison TET4/TET10/HEX8/HEX20 sur trois modeles fournit-elle des metriques de precision, DDL, temps, nnz, CSR et RSS interpretees avec prudence ? | `CONDITIONNEL` | 12 cas et métriques archivés ; maillages et ordres diffèrent, donc aucun classement universel ni scaling général. |
| Q10 | Les correlations CalculiX C3D20 et Code_Aster HEXA20 ont-elles ete executees sur le meme maillage, materiau, chargement et conditions aux limites ? | `OUI` | CalculiX : `8,50e-7` global et `7,04e-7` au noeud ; Code_Aster : `5,42e-15` ; seuil `1 %`. |
| Q11 | Les limites, exclusions J2, limites de taille, resultats non favorables et gates encore ouverts sont-ils visibles dans la documentation publique ? | `OUI` | Contact, grandes transformations, rupture, dommage, modal/dynamique externe, scaling multi-million et masse lumped sont explicitement bornés ou exclus. |

## Decision finale

| Champ | Valeur |
| --- | --- |
| Decision Owner | `accepted_with_recommendations` - acceptee et signee par l'Owner |
| Justification | H20-G01 à H20-G11 sont PASS, les deux corrélations statiques externes sont PASS et la non-régression complète est PASS. |
| Conditions ou recommandations | Maintenir J2 comme preuve interne bornée ; qualifier séparément la masse lumped, la dynamique/modal externe et les grandes tailles avant toute extension. |
| Nom / role | Quentin Farinazzo / Owner |
| Date | 2026-08-24 |
| Signature | Validation Owner approuvee dans le cadre de la release 0.2.3a0 |

Decisions possibles : `accepted_for_release_0_2_3`,
`accepted_with_recommendations` ou `more_evidence_required`. Une decision de
release ne peut etre proposee que lorsque H20-G01 a H20-G12 sont fermes et que
les deux correlations externes sont archivees.
