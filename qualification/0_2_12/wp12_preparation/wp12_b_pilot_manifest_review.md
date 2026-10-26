# WP12-B — Revue de la révision du manifeste pilote

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Évolution des versions

Les versions précédentes sont conservées sans réécriture :

| Version | SHA-256 | État et portée |
|---|---|---|
| WP12-A v1 — `wp12_a_pilot_manifest_v1.json` | `45f63db5dbe2b2cb561de484444e8771840b69d1285b9fd3d2e6ff706886fbce` | Snapshot historique; cible Python/package et runner antérieurs; non autorisé |
| WP12-B v2 — `wp12_b_pilot_manifest_v2.json` | `f626bd68f53e075ac3c910ce6d42f2590c220552df43776c906db68bd9df80b9` | Révision préparatoire; runner `43068bd…`; conservée, non autorisée |
| WP12-B v3 — `wp12_b_pilot_manifest_v3.json` | `501d978557e6b45ee8fcebfd99de8d928af451b8bfa47dd9f970738ea83bdd01` | Révision courante; runner `782820fe…`; `FROZEN_NOT_AUTHORIZED` |

La révision v3 ne change pas l'identité scientifique de WP12-0 : commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. Elle épingle séparément l'infrastructure runner au commit `782820fe31fa8b69223bd368e39949fca325ba3e`, tree `100d7b3ca869cad267666337947f204c9c8bf31e`. La v2 reste inchangée pour sa traçabilité; la v3 tient compte du correctif de validation des checkouts séparés.

## Unité préparée

Campagne `WP12-1-PILOT-001`, unité `WP12-1-PILOT-001-UNIT-01`, tentative déclarée `attempt-001`, maximum 1, aucune relance automatique. Un seul nodeid est inclus :

`tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`

Il s'agit de l'invariant algébrique déjà écrit dans le test. Le fichier source du test est épinglé SHA-256 `9be78449948ebcdc9d577a8968b2dbacbc9b25015b4c9484ece8f91218e20d28`. L'identité déterministe `qf-wp12-inline-fixture-v1` extrait par AST les matrices littérales utilisées par ce nodeid; son SHA-256 est `5873637fc10c495c3cee53f41b9a3956565e07c295cb1a4b071f6dfae9dd6aff`. Les octets et valeurs du test n'ont pas été changés.

Les assertions existantes exigent les égalités exactes de symétrie et comparent la projection structurée à la forme bilinéaire dense avec `rtol=2e-16`, `atol=2e-16`. Aucune tolérance nouvelle n'a été introduite. Cet oracle n'est ni une validation FEM complète ni une qualification générale de WP04/WP12.

## Entrées et environnement épinglés

* 102 fichiers source scientifiques SHA-256; 2 fichiers de test/configuration; 1 entrée fixture fichier; 36 fichiers du runner.
* SHA-256 des 137 fichiers natifs NumPy/SciPy recensés dans le venv, plus leurs versions et chemins de métadonnées.
* Python 3.13.17, SHA-256 `4e67d9e9a3673aa7b6219f1280d5ec3f1b6c0d5bd98ea8688c72d0cb7582d664`.
* Python absolu et venv : `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe` et `E:\QFSolverWP12B\venv-3.13.17`.
* CWD et racine source : `E:\QFSolverWP12B\science`; plugin de provenance : checkout runner séparé; `PYTHONPATH` épingle le runner et `science\src`.
* La sonde d'import séparée a vérifié l'origine `science\src\solveur`; aucune distribution globale `qf-solver` n'est présente dans le venv.
* La commande prévue contient exactement le nodeid ci-dessus, `--noconftest`, le plugin d'origine et le JUnit dans la destination d'evidence externe. Aucun sélecteur large ni second test n'est listé.

Les valeurs de ressources reprises de la proposition antérieure sont 120 s wall, 120 s CPU, 1 GiB mémoire, 8 processus, 1 thread, 256 MiB temporaire et 1 MiB par journal. Elles ne sont **pas approuvées par cette révision**. Le runner déclare wall, CPU, mémoire, processus, arbre de processus et journaux comme contrôles durs; stockage et threads restent souples. La destination `E:\QFSolverWP12B\evidence\WP12-1-PILOT-001\attempt-001` est absente et non sécurisée à ce jour.

## Contrôle statique réel du manifeste v3

La CLI runner v3, exécutée depuis le checkout runner exact, a validé le manifeste v3 avec :

* `state=STRUCTURALLY_VALID_NOT_AUTHORIZED`;
* aucune erreur de schéma ni d'identité d'entrée;
* 141 empreintes contrôlées entre les deux checkouts;
* science propre au commit/tree attendu et runner propre au commit/tree attendu;
* quatre bloqueurs : `SEPARATE_OWNER_DECISION_REQUIRED`, `INDEPENDENT_EVIDENCE_ARCHIVE_NOT_CONFIGURED`, `WINDOWS_ISOLATION_NOT_VERIFIED`, `INDEPENDENT_SECURITY_REVIEW_NOT_RECORDED`;
* `execution_started=false`.

Cette commande n'a lancé ni pytest ni solveur. La validité structurelle ne rend pas le manifeste authentifié, autorisé ou prêt à exécuter.

## Décision de lancement manquante

Aucune clé Owner, trust store HKLM, pin, signature ou décision spécifique n'existe. Le statut reste `FROZEN_NOT_AUTHORIZED`. Le manifeste n'a pas été copié dans l'inbox protégée, son répertoire d'evidence n'a pas été créé, aucune tentative n'a été réservée au ledger et aucun reçu scientifique n'existe.

Le manifeste ne peut pas activer le code actuel : après les précontrôles, le dernier composant d'exécution refuse encore `SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED`. Les limites de l'hôte et les actions Owner sont détaillées dans [l'état de configuration Windows](wp12_b_configuration_report.md) et [la liste des actions Owner](wp12_b_owner_actions.md).
