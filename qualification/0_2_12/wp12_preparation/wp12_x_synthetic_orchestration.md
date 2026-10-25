# WP12-X — Orchestrateur SELF_TEST synthétique

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Objet et frontière de sécurité

WP12-X relie en une seule orchestration les cas factices existants du runner : lancement du processus fixe, captures, statut attendu, reçu de fichiers et journal de cycle de vie chaîné. Il ne consomme aucun manifeste WP12, décision Owner, nodeid ou commande arbitraire.

Le seul point d'entrée est scripts/run_wp12_qualification.py avec --mode SELF_TEST et --case all ou un cas fixe. Les cas admis proviennent exclusivement de FAKE_CASES dans scripts/wp12_runner/process.py. Le mode appelle run_fake_process; aucun sélecteur pytest n'est construit. Les résultats portent SYNTHETIC_RUNNER_SELF_TEST, scientific_execution=false et une empreinte du plan et des sources runner. Les journaux et reçus sont placés dans un répertoire temporaire puis supprimés après émission du rapport; ils ne sont pas des preuves WP12 durables.

L'orchestrateur refuse de démarrer si REAL_EXECUTION_ENABLED est vrai. Le mode CLI EXECUTE et le blocker inconditionnel REAL_EXECUTION_DISABLED_IN_WP12_R2 restent inchangés. Cette orchestration ne doit jamais être appelée pour exécuter les nodeids de WP12-1, WP12-2 ou WP12-3.

## Cycle synthétique

1. Sélectionner all ou un cas parmi success, exit, sleep, tree, flood et memory; tout autre identifiant est refusé.
2. Calculer le SHA-256 du plan fixe et les SHA-256 des modules d'orchestration, CLI, contrats runner, supervision, reçus, Job Object et fixture factice.
3. Créer un répertoire temporaire neuf, un run ID distinct par cas et un événement RUNNING.
4. Lancer uniquement l'enfant factice avec les limites déjà utilisées par SELF_TEST. Sous Windows, le cas memory demande le plafond Job Object de 64 MiB; ailleurs il est NOT_APPLICABLE.
5. Comparer le comportement observé à l'attendu du cas, produire et revérifier le reçu, puis consigner l'état terminal avec les hashes des journaux.
6. Vérifier la chaîne du journal temporaire et inclure son SHA-256 dans le rapport. Une erreur d'infrastructure arrête les unités suivantes; une divergence de résultat reste FAIL.

PASS dans ce rapport signifie seulement que le runner a observé le comportement prévu pour une fixture factice. Il ne signifie ni PASS scientifique ni preuve de qualification. Aucun seuil de solveur, oracle mécanique, statut de WP ou résultat historique n'est consommé.

## Transferts de scope proposés — décision Owner requise

La [revue WP12-S du manifeste](wp12_s_wp12_1_scope_review.md) trace les neuf nodeids de R2. Le tableau ci-dessous conserve ces identifiants et propose des destinations; il ne modifie pas les manifestes et n'autorise aucune exécution.

| # | Nodeid historique exact | Proposition de placement | Motif et décision à soumettre |
|---:|---|---|---|
| 1 | tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form | WP12-1 | Projection et invariant algébrique; conserver |
| 2 | tests/unit/test_modal_symmetric_projection.py::test_modal_basis_uses_structured_projection_for_exact_symmetric_k | WP12-1 | Intégration du chemin symétrique exact; conserver |
| 3 | tests/unit/test_modal_symmetric_projection.py::test_from_prepared_reuses_one_sparse_symmetry_difference | WP12-1 | Invariant de réutilisation; conserver |
| 4 | tests/unit/test_modal_symmetric_projection.py::test_tolerated_near_symmetric_k_falls_back_to_historical_bilinear_path | WP12-1 | Compatibilité du repli; conserver |
| 5 | tests/unit/test_modal_symmetric_projection.py::test_from_prepared_rejects_significantly_asymmetric_stiffness | WP12-1 | Refus contractuel; conserver |
| 6 | tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators | WP12-1 | Oracle numérique couplé 2 DDL; conserver sans le présenter comme validation physique indépendante |
| 7 | tests/unit/test_prepared_dynamic_system.py::test_prepared_identity_is_deterministic_and_dof_maps_are_defensive | WP12-2 | Identité d'un système préparé avec dépendance à l'assemblage partagé; transférer seulement si Owner approuve cette frontière |
| 8 | tests/unit/test_prepared_dynamic_system.py::test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume | WP12-2 | Appelle solve_model pour produire un checkpoint transitoire courant; ne pas lancer implicitement dans WP12-1 |
| 9 | tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_v2_checkpoint_metadata_identity_tampering_fails_integrity | WP12-3 | Intégrité de checkpoint non linéaire/WP10; transférer et compléter l'inventaire direct des modules/helper |

### Décisions et révisions préparatoires

- wp12_1_execution_manifest.json, revisions/wp12_1_execution_manifest.r2-prepared.json et revisions/manifest_revision_index.json restent inchangés; leurs hashes d'origine et R2 restent la trace historique.
- Après décision Owner, préparer une nouvelle révision WP12-1 qui garde les nodeids 1–6; une révision WP12-2 qui ajoute 7–8; et une révision WP12-3 qui ajoute 9. Chaque version doit rester PREPARED_NOT_AUTHORIZED, porter un SHA-256 propre, des dépendances/fixtures complètes, les budgets et l'environnement à résoudre, ainsi qu'une destination propre.
- Soumettre à l'Owner le retrait des trois nodeids du WP12-1 R2 et leur affectation aux lots proposés. Tant que cette décision n'est pas enregistrée, la proposition ne remplace aucun scope officiel.
- Les chemins modal_newmark_checkpoint.py et test_modal_newmark.py, déclarés dans l'inventaire WP12-1 R2 mais non couverts par ces neuf nodeids, doivent être retirés de l'inventaire ou associés à un nodeid sélectionné dans une révision future.

**État actuel :** aucun nodeid historique n'a été lancé; aucun nouveau manifeste n'est autorisé; WP11 reste CLOSED, WP12 et WP13 restent OPEN.

## Vérifications d'implémentation

Le 2026-10-25, la suite dédiée tests/unit/test_wp12_qualification_runner.py a réussi avec 40 tests. Ruff a réussi sur cli.py, synthetic_orchestrator.py et cette suite. Ces tests utilisent les processus factices et les refus statiques du runner; aucun test QF Solver, solveur, calcul FEM ou campagne WP12 n'a été exécuté. Ce résultat ne constitue pas une preuve scientifique.
