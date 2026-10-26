# WP12-B — Demande d’inscription et dossiers de manifeste

## État

Cette demande vise les trois cas de premier lot préparés sur `verify/wp12-elements-loads`. Elle ne modifie pas la politique commune et ne constitue pas une inscription ou une autorisation d’exécution. Le HEAD de la branche doit être actualisé avec le commit de livraison avant toute inscription, car les empreintes de test sont liées au contenu ci-dessous.

Le worktree de cette mission est `C:\Users\fari\.codex\worktrees\verify-wp12-elements-loads\qf_solver`. La configuration connue du contrôleur `wp12_elements` pointe actuellement vers un autre worktree/une autre branche (`E:\QFSolverAgents\vv-elements`, `test/wp12-fem-regressions`). Le responsable du contrôleur doit décider de l’identité de worktree à enregistrer ou fournir le checkout scientifique enregistré correspondant. Aucun `register-nodeid`, `prepare-manifest` ou `test --execution-manifest` n’a été invoqué dans cette mission.

## Inscription proposée

Demande commune : **une première tentative par nodeid**, sans retry automatique, **300 s par tentative**, plafond observé de **4096 MiB RSS** par le contrôleur, limite de sélection WP12-B **30 000 DDL**. Total demandé : 3 des 20 tentatives/cas permises à la mission, soit 3 tentatives maximum. Ces budgets sont ceux proposés dans la limite de l’enveloppe, non une autorisation.

| Nodeid exact | DDL | Justification d’inscription | Oracle et critères pré-déclarés |
|---|---:|---|---|
| `tests/unit/test_wp12b_beam2_continuity.py::test_wp12b_beam2_rotated_uniform_line_load` | 12 | Un BEAM2, 2 nœuds × 6 DDL; racine encastrée (6) et bout libre (6); charge linéique uniforme en axe local `y`, axe de poutre tourné de 37°. | Déplacement de bout Timoshenko nodal exactement compatible avec la matrice d’extrémité et la charge cohérente d’un seul élément; résultante `qL e2`, moment `qL²/2 e3`; bilans de réactions, résidu libre et identité énergie-travail. Ce test porte sur les valeurs nodales, pas sur une déformée intérieure exacte.
| `tests/unit/test_wp12b_tet10_curved_load.py::test_wp12b_tet10_curved_face_pressure_solve` | 30 | TET10 courbe, 10 nœuds × 3 DDL; six nœuds de la face support encastrés (18 DDL); 12 DDL libres; pression de 2 Pa sur la face adjacente qui partage les nœuds 2, 3 et 9. | Oracle face/resultante/moment indépendant : interpolation quadratique écrite dans le test, dérivées de surface et intégration Duffy × Gauss-Legendre 8×8; ne réutilise pas les faces, fonctions ou intégrateurs de production. Valeurs indépendantes croisées avec les intégrales historiques déjà testées; réponse déplacée résolue avec réactions, résidu, énergie et équilibre archivés.
| `tests/unit/test_wp12b_hex20_affine_patch.py::test_wp12b_hex20_uniaxial_traction_patch` | 60 | HEX20 standard, 20 nœuds × 3 DDL; huit nœuds de la face `x=0` bloqués (24 DDL); 36 DDL libres; tractions exactes appliquées aux cinq faces restantes. | Patch de déformation affine `u=(εx,0,0)` et contrainte de Hooke correspondante (état uniaxial de déformation, avec tractions latérales). Comparer les 60 déplacements, contraintes, réactions et équilibres. Vérifier `U=0.5 σεV`, travail externe total `2U`; la face fixée ne travaille pas.

## Empreintes SHA-256

Les chemins sont relatifs à la racine Git du worktree. Tous ces fichiers contribuent à l’identité test/oracle/solveur; le contrôleur doit recalculer les empreintes depuis le checkout qu’il enregistre et comparer les empreintes avant de préparer les manifestes.

| Fichier | SHA-256 |
|---|---|
| `tests/unit/test_wp12b_beam2_continuity.py` | `7d0e63e2c7ce16692ac4bbe5c3556338e949374fe43a10b211c67f1f599c12e3` |
| `tests/unit/test_wp12b_tet10_curved_load.py` | `46f6fdd11d71854ecd89daaf0948834bc56b07b9adc7747391a84e25bde2c037` |
| `tests/unit/test_wp12b_hex20_affine_patch.py` | `1dfdd4918cbb6d7d03450c0703dd8805d2db9e954952682218719e2fb0e835a6` |
| `tests/unit/wp12b_test_support.py` | `0087286a3ee2fd0fcf818a9257c718a05aa98214b15d0270c0f0ccf09b0717f2` |
| `src/solveur/loads/integration.py` | `c30d5a6e53321d0a9f12bc3ac9c4d1b78e07a84f7d57b3532c0488eba3a3f2a9` |
| `src/solveur/core/solvers/static.py` | `f0efb9afe0a8f304faeacefcfc5d76fbb79057527f9f51c03bb9fa9e915363d7` |
| `src/solveur/elements/beam/beam2.py` | `1d109cb8a76022781fd372353d071eae547f84dc77bb7cb955d346db57cd1909` |
| `src/solveur/elements/solid/tet10.py` | `a29b8bb118c20ce4b78406b07829a3017357f467af4318b8b6e0ffa72c89bbc5` |
| `src/solveur/elements/solid/hex20.py` | `0b4de54be71ff59f1487eff9f22aacf19fcefa3c9c360045c04f2e323295744c` |

## Préparation des trois décisions Owner

Pour chaque nodeid, le contrôleur doit émettre un manifeste lié au commit final, à l’empreinte exacte du test et des dépendances ci-dessus, au modèle, au worktree enregistré, à l’environnement Python/solveur, au chemin de preuves, à l’oracle et aux critères indiqués dans la matrice. La décision Owner doit approuver exactement le hash de chaque manifeste avant `test --execution-manifest`. Toute modification du code après inscription invalide la demande et exige une nouvelle inspection source/inscription.

Les tests sont instrumentés pour écrire un sidecar JSON atomique sans écrasement avant assertions, incluant identité d’essai, modèle et code, unités, déplacements, réactions, résultantes/moments, résidu libre défini, énergie/travail, qualité de maillage et temps solveur. Les quatre contrôles synthétiques d’archivage/oracle passent. Le contrôleur doit encore confirmer que son archive conserve le sidecar et consigne les budgets/ressources. Aucun calcul FEM n’a été lancé.
