# WP12-S — Revue de périmètre du manifeste WP12-1

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**
Campagne examinée : `WP12-1-MODAL-PROJECTION-CONTRACTS` · Révision R2 préparée le 2026-10-25

## Références et identité

Les deux sources de préparation examinées sont [le manifeste original WP12-0](wp12_1_execution_manifest.json) et [sa révision R2](revisions/wp12_1_execution_manifest.r2-prepared.json); l'[index des révisions](revisions/manifest_revision_index.json) conserve leurs hashes et liens. Le SHA-256 original est `70ff305a584fdd5334fdc3cdc3e03afc7fa9efe71abb866a4937626127a8b70c`; celui de R2 est `1b61f4de19e46d933fc825a1eb1525aaf14d43e8ebade21e0c1b1f0bf010cf0b`.

Les deux ciblent le commit scientifique `00428adf38e9397340ac136f6f503a268eb671da` / tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. R2 ne remplace aucun chemin déclaré pour WP12-1, ne laisse aucun chemin non résolu, OID périmé ou nodeid manquant dans son index. L'inventaire ajoute les blobs et SHA-256 pour les chemins source/test déclarés. Leur présence dans l'index est confirmée statiquement au candidat. Cette continuité d'identité ne démontre pas l'exécution ni la couverture des dépendances par fichier.

Les deux manifestes sont `PREPARED_NOT_AUTHORIZED`; le manifeste R2 porte `NUMERICAL_EXECUTION_NOT_PERFORMED` et `WP12_STATUS=OPEN`. Aucun nodeid n'a été exécuté pendant cette revue.

## Inventaire des fichiers déclarés par R2

Les OID sont des Git blob SHA-1; les empreintes longues sont SHA-256 des octets du fichier. Les révisions les lient aussi au commit/tree scientifique indiqué plus haut.

| ID | Fichier | Git blob OID | SHA-256 | Usage dans les sélections |
|---|---|---|---|---|
| S1 | `src/solveur/core/analyses/modal_basis.py` | `e363e0b35e8a628dcd63fa8d18fb97fd8b1534db` | `da677b109e96a23ec6b72ac5087d7a6f67d0f2991d74ddd39a2a1acbd84ed485` | Construction et consommation de la base modale |
| S2 | `src/solveur/core/analyses/modal_basis_numerics.py` | `3f333730620246110e5e51ceb91ddc3cd2cec642` | `c61689651a6a5204aa74725b83e75f3979bb280337d961403df1cf71644e6512` | Symétrie et projection bilinéaire structurée |
| S3 | `src/solveur/core/analyses/prepared_dynamic_system.py` | `a55ba5b5b117574294db95ceccc8c68352172100` | `b0589dbf124d4702535907d3db9342eaee07771d82292afa9bdac191c0bea9a4` | Identité physique/opérateur et système préparé |
| S4 | `src/solveur/core/analyses/modal_newmark_checkpoint.py` | `4eefb7d67dd602057492a38a703dfc048d56ca66` | `9491acc6cd51a354c534b2d3bde9473027d19a81752db9b52865103f8a6ab127` | Checkpoints Newmark modal; aucun nodeid sélectionné ne l'exerce directement |
| T1 | `tests/unit/test_modal_symmetric_projection.py` | `20889499b60cdd4fa79b2a2d2f76626279ed3e8e` | `12acd147e72310c01311a68bbb4b85abd6b8d3dbab1888bc80f43f77c1520308` | Projection symétrique, chemin historique et refus |
| T2 | `tests/unit/test_modal_basis_damping.py` | `9710c3faa55c0859047cd748f39acc0979a5efb0` | `24bba2ab2fbcd046265577e2c7ad53f51a2edde7e55039e376d2b21c4e844f8a` | Base modale et oracle analytique couplé |
| T3 | `tests/unit/test_modal_newmark.py` | `d6195e2b709853853fc24380c6c7c0029ecff290` | `7adef74af76bf032f8d40baa0e6f8a52b32de6f0429d84d461d3015b5d585ed6` | Enregistré dans le dossier, aucun nodeid R2 sélectionné |
| T4 | `tests/unit/test_prepared_dynamic_system.py` | `44f758e8429a3e93e981804b3bd22ade57fba386` | `aaadae37953e8e7601a49cee46b377c85c9180a07cb9ee5e59aa3ab4679ad16b` | Préparation/identité et refus de checkpoint legacy |
| T5 | `tests/unit/test_wp10_nonlinear_state_checkpoints.py` | `778301bf10a61da078cfb1da842a3814545e9877` | `f4ba738a6c804f6b7305a1c0154c066d7ba6fcb808597b8dda80d333c73f62f5` | Intégrité metadata checkpoint non linéaire |

R2 fixe aussi les racines Git `src=3fd84f22c35aaecd989f2fe614e0b3fd9d7fbc6e`, `tests=25ac8dad53b310407385353373db7886b8823ceb`, `examples=199741620aeec02ad4342d55dd361210a766d885`. Ces racines et le commit exact apportent une identité globale; elles ne remplacent pas l'inventaire sémantique des dépendances de chaque nodeid.

## Revue des nodeids exacts

| Nodeid présent | Capacité réellement exercée | Module principal | Oracle et contrat | Entrée/identité | Risque et décision Owner |
|---|---|---|---|---|---|
| `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form` | Projection symétrique structurée égale à la forme bilinéaire dense et résultat symétrique | S2 | Invariant algébrique + petite matrice dense; WP04 | Fixture inline `projection-matrices`; fichier T1 | Faible coût; unité cohérente WP12-1 après extraction/hash déterministe |
| `tests/unit/test_modal_symmetric_projection.py::test_modal_basis_uses_structured_projection_for_exact_symmetric_k` | Intégration du chemin symétrique exact par `ModalBasis` | S1, S2 | Assertions existantes sur dispatch, symétrie, masse projetée et valeurs propres; WP04 | Matrices inline dans T1 | Pas de campagne FEM générale; conserver seuils contractuels et classifier algébrique |
| `tests/unit/test_modal_symmetric_projection.py::test_from_prepared_reuses_one_sparse_symmetry_difference` | Réutilisation du calcul de différence de symétrie sur un système préparé | S1, S2, S3 | Invariant de nombre d'appels + identité factice; WP04 | Données synthétiques inline dans T1 | Confirme un chemin et un coût local, pas un benchmark; hash fichier présent |
| `tests/unit/test_modal_symmetric_projection.py::test_tolerated_near_symmetric_k_falls_back_to_historical_bilinear_path` | Repli bilinéaire historique lorsque la symétrie est tolérée mais non exacte | S1, S2 | Oracle de comportement/refus du chemin de repli; WP04 | Matrice inline dans T1 | MUST pour préserver la compatibilité; ne pas changer la tolérance |
| `tests/unit/test_modal_symmetric_projection.py::test_from_prepared_rejects_significantly_asymmetric_stiffness` | Refus d'une rigidité significativement asymétrique | S1, S2, S3 | Refus `InputValidationError`; WP04 | Matrice inline dans T1 | MUST pour préserver le fail-closed; aucune promotion scientifique |
| `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | Valeurs propres généralisées de deux DDL; masse et rigidité projetées, reconstruction, disponibilité des résultats | S1 et référence `scipy.linalg.eigh` du test | Comparaison à une résolution généralisée 2×2 via SciPy; WP04 | Fixture inline `coupled-modal-model`; T2 | Référence numérique utile, mais pas une solution fermée ni une validation physique indépendante d'une chaîne éléments finis; maturité de résultat reste EXPERIMENTAL dans le test |
| `tests/unit/test_prepared_dynamic_system.py::test_prepared_identity_is_deterministic_and_dof_maps_are_defensive` | Identité préparée stable, sensibilité à `source_sha`, DDL défensifs | S3 et assemblage `GlobalAssembler` appelé par préparation | Invariants d'identité et d'immutabilité; contrat d'identité WP04/WP06 selon scope | Modèle créé dans T4 avec éléments/discrets | Dépend de l'assemblage partagé; Owner doit confirmer ce périmètre transversal ou déplacer vers WP12-2 |
| `tests/unit/test_prepared_dynamic_system.py::test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume` | Lecture d'un vieux checkpoint et refus de reprise | T4; imports explicites `solveur.api.solve_model`, `solveur.core.analyses.dynamic_checkpoint.DynamicCheckpoint`, `solveur.io.dynamic_checkpoint.NpzDynamicCheckpointStore`; dispatch Newmark | Test de compatibilité/refus; WP06 checkpoint | Fichier temporaire construit dans T4 | **Hors unité purement algébrique** : le test appelle `solve_model(model)` pour créer un checkpoint courant avant le refus legacy. Déplacer à WP12-2 ou approuver explicitement une unité de transitoire; jamais le lancer par WP12-1 implicitement |
| `tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_v2_checkpoint_metadata_identity_tampering_fails_integrity` | Tampering du metadata d'identité et refus d'intégrité d'un checkpoint non linéaire | T5 importe `solveur.core.nonlinear.checkpoint`, `state`, `contracts`, `solveur.io.nonlinear_checkpoint` et helper `tests.unit.test_analysis_features` | Refus d'intégrité; WP10 checkpoint | Modèle/helper et NPZ temporaire dans T5 | Les modules et helper directs ne sont pas listés individuellement; le tree racine exact les épingle, mais la traçabilité par nodeid est incomplète. Déplacer à WP12-3 ou ajouter les dépendances et approuver le scope transversal |

Les neuf nodeids sont retrouvés par inspection statique des définitions; aucun `pytest --collect-only` n'a été exécuté. Les cinq premiers ont des identifiants exacts non paramétrés; les autres nodeids listés sont également sans paramètre. Si l'AST change au gel, toute expansion des IDs est à faire avant signature, non après autorisation.

L'inventaire R2 comprend `modal_newmark_checkpoint.py` et `test_modal_newmark.py`, alors qu'aucun des neuf nodeids sélectionnés n'exerce ce checkpoint modal. À l'inverse, le nodeid legacy appelle le checkpoint transitoire classique. L'Owner doit retirer ces fichiers non exercés de l'inventaire de l'unité ou sélectionner explicitement des tests qui les couvrent; leur seule présence dans la liste ne constitue pas une couverture. Le commit/tree et les racines Git source/test épinglent globalement les dépendances non listées; le défaut constaté est la traçabilité explicite des dépendances et l'alignement du scope, pas une modification non détectée du tree exact.

## Fixtures, oracle, environnement et ressources

| Sujet | État R2 | Conclusion |
|---|---|---|
| Fixture `projection-matrices` | Inline dans T1; Git OID T1; `byte_sha256` est le texte `Compute for extracted bytes at freeze` | Pas un SHA-256 effectif; définir une extraction canonique et versionnée avant gel |
| Fixture `coupled-modal-model` | Inline dans T2; Git OID T2; `byte_sha256` non calculé | Même lacune; les valeurs inline sont couvertes par le hash du fichier, mais l'identité matérialisée/entrée d'exécution reste à figer |
| Tolérances existantes | symétrie relative `1e-12`; résidu modal `1e-08`; orthogonalité masse `1e-08`; gap cluster `1e-08` | Reprendre exclusivement les valeurs contractuelles déjà consignées; aucun seuil nouveau |
| Environnement | OS, Python, NumPy/SciPy/pytest proposés; lock env null; threads nuls | Versions/chemins d'interpréteur absolu, packages/native libs et variables threads à approuver |
| Commande | `python -m pytest -q <un nodeid exact>` | `python` non lié à un venv/interpréteur exact; ne pas utiliser cette chaîne telle quelle pour preuve |
| Budgets | CPU, RAM, threads, timeouts et stockage sont `null`; 1 tentative est proposé | Aucun budget effectif; le maximum de tentatives n'est pas une décision tant que le champ reste `PROPOSED` |
| Destination | `qualification/0_2_12/wp12_evidence/WP12-1-MODAL-PROJECTION-CONTRACTS/<run_id>/`, refus de collision | Définir un identifiant/run ID, permissions dédiées et ancrage externe; aucun droit d'écriture sur archive historique |

## Proposition de scope figé

1. **WP12-1 candidat minimal :** les cinq nodeids de `test_modal_symmetric_projection.py` et l'oracle analytique couplé de `test_modal_basis_damping.py`, sous une unité séparée pour chaque nodeid et avec les hashes/fichiers d'entrée figés.
2. **Décision Owner requise sur `test_prepared_identity...` :** le garder comme test de dépendance d'identité/assemblage ou le transférer vers la dynamique/transversalité.
3. **WP12-2 recommandé :** déplacer `test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume`, car son prérequis appelle `solve_model` sur un modèle dynamique.
4. **WP12-3 recommandé :** déplacer `test_v2_checkpoint_metadata_identity_tampering_fails_integrity`, ou faire approuver un lot checkpoint transversal et ajouter tous ses modules/helpers directs à l'inventaire fichier.
5. Chaque unité doit être une nouvelle révision traçable avec un hash de manifeste exact, chemin absolu du Python, inventaire complet des dépendances directes, fixtures gelées, budgets approuvés et destination neuve. Le R2 et les manifestes WP12-0 restent préservés et non autorisés.

Cette proposition ne clôt pas les tests, ne constitue pas un plan d'exécution approuvé et ne crée aucun PASS. Les tolérances et oracles restent ceux des contrats et assertions existants.
