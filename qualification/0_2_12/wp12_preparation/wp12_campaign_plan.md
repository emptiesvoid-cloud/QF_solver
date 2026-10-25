# WP12-0 — Plan des campagnes WP12-1 à WP12-6

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Toutes les commandes de cette section sont des propositions, non exécutées. Les nœuds sont résolus par lecture de source. Les manifestes par lot sont `PREPARED_NOT_AUTHORIZED`. Une approbation Owner, la revue des limites du runner WP12-R, un mécanisme de confiance indépendant, une isolation des ressources adéquate et le gel de l'identité sont des prérequis distincts à toute exécution. WP12-R ne fournit pas le mode EXECUTE.

## Ordre et dépendances

```text
WP12-0 décisions + identité + runner contrôlé
       └── WP12-1 contrats / projection / refus
              ├── WP12-2 dynamique (réutilise les gates WP12-1)
              ├── WP12-3 non-linéaire et contact borné
              └── WP12-4 héritage / dispatch / API-CLI / IO
                     └── WP12-5 performance bornée (après correction des défauts)
                            └── WP12-6 consolidation Owner
```

### WP12-1 — Contrats et vérifications algébriques

- **Objectif** : traiter P1-02 par la nouvelle projection structurée, son fallback/refus, et ses consommateurs; contrôler identités, refus, sauvegarde/lecture et checkpoint, sans appeler ces vérifications une qualification FEM.
- **Prérequis** : décision Owner sur l'identité cible; hashes source/test/fixtures; runner qui n'écrit pas dans les archives historiques.
- **Nœuds prioritaires** : les cinq nœuds de `tests/unit/test_modal_symmetric_projection.py`; `tests/unit/test_prepared_dynamic_system.py::test_prepared_identity_is_deterministic_and_dof_maps_are_defensive`; `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators`; `tests/unit/test_prepared_dynamic_system.py::test_newmark_old_checkpoint_is_readable_but_not_safe_to_resume`; `tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_v2_checkpoint_metadata_identity_tampering_fails_integrity`; `tests/integration/test_api_and_cli.py::test_public_api_load_check_solve_save`.
- **Justification** : la méthode `Kr` change à `1f3148f`; les résultats WP05/WP06 aval lisent cette base. Les refus et identités montrent que la réutilisation cache/checkpoint ne masque pas un opérateur modifié. Le test API est un contrôle de route, pas un rejeu WP11.
- **Coût** : faible à moyen; nœuds exacts, certains construisent de petits modèles. Aucun temps mesuré sur le candidat.
- **Preuve attendue** : reçus source-liés par nœud, comparaison à oracles/critères du contrat WP04, refus/fallback attendus et logs sans sorties en historique.
- **Sortie** : les cinq nouvelles branches de projection démontrées, identité et tolérances conservées; tout échec arrête le lot et demeure visible. Aucun changement de statut D01.
- **Risque** : comparaison directe et oracle dense synthétique ne sont pas une preuve indépendante de l'ensemble de la physique.

### WP12-2 — Dynamique WP02–WP07 et D02

- **Objectif** : établir sur l'identité actuelle la cohérence des opérateurs/excitations, la réponse complexe réduite, le transitoire modal, la base uniforme et la récupération des contraintes dans leurs domaines gelés.
- **Prérequis** : WP12-1 projection passée ou diagnostic accepté; critères WP02–WP07 relus/hasés; fixtures autonomes recensées.
- **Nœuds ciblés** : `tests/unit/test_prepared_dynamic_system.py::test_prepared_operators_match_legacy_assembly_and_remain_sparse`; `tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe`; `tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase`; `tests/unit/test_reduced_harmonic.py::test_truncated_basis_records_observable_differences_without_claiming_error_bound`; `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`; `tests/unit/test_modal_newmark.py::test_coupled_tet4_full_basis_matches_independent_eigen_expansion`; `tests/unit/test_modal_newmark.py::test_second_order_time_refinement_for_smooth_free_vibration`; `tests/unit/test_modal_newmark.py::test_restart_matches_continuous_run_and_refuses_corrupt_or_incompatible_checkpoint`; `tests/unit/test_wp07_uniform_base_acceleration.py::test_full_mass_base_load_keeps_free_constrained_coupling_and_beam_rotations`; `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames`; `tests/unit/test_wp07_uniform_base_acceleration.py::test_transient_base_sdof_matches_independent_constant_acceleration_solution`; `tests/unit/test_wp_d02_dynamic_stress.py::test_tet4_complex_harmonic_stress_matches_independent_affine_reference`; `tests/unit/test_wp_d02_dynamic_stress.py::test_transient_tet4_free_vibration_matches_modal_oracle_and_independent_stress`; `tests/unit/test_wp_d02_dynamic_stress.py::test_dynamic_recovery_fails_closed_for_invalid_sources_and_incomplete_fields`.
- **Justification** : covers independent analytical/affine references, physical full-system residuals, time-order and refusal behavior; direct-vs-reduced comparisons are separately labeled as shared-code consistency. D02 stress cases do not validate every displacement solver.
- **Cost** : medium; bounded small/medium FE models and multiple time steps. High-order families may raise cost; preserve exact contracted families, not a broad Cartesian suite.
- **Preuve attendue** : expected/observed/error/threshold, unit and frame semantics, full list of skipped parameters and history/provenance hashes.
- **Sortie** : each in-scope DYN oracle satisfies its preregistered gate; time refinement has its frozen order; truncated-basis diagnostics remain explicitly non-boundants; stale source/checkpoint refusals pass.
- **Risque** : aucune nouvelle convergence spatiale générale n'est acquise par des cas analytiques ou de petits éléments.

### WP12-3 — Non-linéaire, états et contact

- **Objectif** : sentinelles actuelles des routes WP08–WP10, des changements J2/tangente/transaction, de la remédiation négative C01 et de C02 seulement AR/N03; vérifier l'isolation des options E01.
- **Prérequis** : lots de données/outils N10 externalisés non réutilisés pour écrire des résultats; nouveau manifeste et répertoire exclusif. Décision Owner sur rejouabilité de M4/M5 et limites.
- **Nœuds ciblés** : `tests/unit/test_corotational_j2_corrected.py::test_corrected_newton_plasticity_line_search_results_and_serialization`; `tests/unit/test_corotational_j2_corrected.py::test_corrected_tangent_matches_independent_directional_force_differences`; `tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_trial_state_cannot_be_checkpointed_and_commit_attests_atomically`; `tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_rollback_keeps_accepted_composite_and_retry_is_a_new_trial`; `tests/unit/test_wp10_nonlinear_state_checkpoints.py::test_max_iterations_is_reported_as_nonconvergence_not_acceptance`; `tests/unit/test_nonlinear_checkpoint.py::test_nonlinear_restart_matches_continuous_cyclic_solution`; `tests/unit/test_wp_e01_j2_global_phase2.py::test_j2_return_map_and_tangent_match_independent_tensor_oracle`; `tests/unit/test_wp_e01_j2_coro_phase8.py::test_phase8_inadmissible_guard_state_is_refused_without_retry`; `tests/verification/test_wpc02_ar_native_contact_convergence.py::test_wpc02_ar_native_m4`; `tests/verification/test_wpc02_ar_native_contact_convergence.py::test_wpc02_ar_native_m5`.
- **Sentinelles optionnelles C01/E01** : `tests/unit/test_wpc01_r13_small_rotation_transfer.py::test_default_and_explicit_legacy_are_identical`; `tests/unit/test_wpc01_r13_small_rotation_transfer.py::test_mode_validation_is_opt_in_and_excludes_updated_or_finite_sliding_routes`; `tests/unit/test_wp_c01_r19_example_contract.py::test_example_default_invocation_does_not_launch_a_calculation`; `tests/unit/test_wp_c01_r16_smoke_contract.py::test_smoke_payload_requires_active_contact_on_every_accepted_step`; `tests/unit/test_corotational_j2_corrected.py::test_polar_directional_derivative_matches_independent_sylvester_and_fd`; `tests/unit/test_wp_e01q_hencky_tangent.py::test_material_response_still_does_not_claim_a_verified_tangent`; `tests/unit/test_wp_e01q_hencky_tangent.py::test_directional_tangent_matches_multistep_centered_pk1_difference`. Elles ne promeuvent pas C01/E01; le nœud vérifiant le hash du fixture C01 est suspendu jusqu'à résolution de son digest divergent.
- **Prérequis C02 supplémentaire** : M4/M5 exigent `tests/unit/test_wpc02_aj_partial_active_contact.py`, absent du tree candidat. Son blob exact est récupérable dans l'historique local au commit `9e1cf9805b49c90a74006a39cb0ded640265f64f` (OID Git `c05a72879440081f0f4f725f72c0adaa09f66c99`, SHA-256 conforme au plan `7b14816b6ed6f6bed8aaa8e3bbde568251cf94332aa6c7b12765f389d6ae226e`). Exiger une décision Owner sur un overlay temporaire isolé et l'enregistrer dans le manifeste; ne jamais ajouter le helper au checkout candidat.
- **Justification** : WP08–WP10 sont positifs mais bornés; les opérations de stress/tangente/driver/identité de checkpoint sont des dépendances partagées. C02 M4/M5 sont les cas de bord acquis par N10 pour AR/N03; un éventuel rejeu mesure la non-régression actuelle, pas la clôture C02 une seconde fois. E01 reste expérimental; un test pointwise ne qualifie pas la chaîne globale.
- **Coût** : tests locaux faible à moyen; M4/M5 medium à high et dépendants des ressources/runner. Aucun budget temps/RAM n'est fixé dans ce dossier.
- **Preuve attendue** : références constitutives indépendantes et bilans contractuels pour NL; reçus M4/M5, fixtures et critères N12/N13 pour la route contact. Historiques FAIL, Docker `FAIL_CLOSED`, `GENERAL_CONTACT_QUALIFICATION=NOT_ACQUIRED` conservés.
- **Sortie** : pas de défaillance introduite sur les contrôles scoped; C02 revendiqué seulement AR/N03. C01, D01, E01 conservent leur statut actuel.
- **Risque** : les tests `tests/unit` peuvent exécuter des assemblages FEM; marqueur de dossier n'est pas une preuve d'absence de solveur. C01/E01 tests ne doivent pas être étendus à leur qualification générale.

### WP12-4 — Non-régression transversale et capacités héritées

- **Objectif** : vérifier les chemins accessibles affectés indirectement : rotor/Campbell expérimental, MPC/RBE bornés, routes API/CLI, IO/complexes, méthodes héritées et dispatch/backends.
- **Prérequis** : identité propre; clarifier les tests API/CLI qui sont des solves, environnement optionnel identifié; préparer sorties temporaires exclusives.
- **Nœuds ciblés** : `tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces`; `tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract`; `tests/unit/test_rotating_disk_gyro.py::test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work`; `tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual` (paramètres explicitement listés au manifeste); `tests/unit/test_rotating_qep.py::test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies`; `tests/unit/test_rotating_qep.py::test_rotating_modal_complex_serialization_round_trip_preserves_all_roots`; `tests/unit/test_campbell.py::test_implementation_hash_paths_support_installed_wheel_layout`; `tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results`; `tests/unit/test_campbell.py::test_campbell_is_exposed_through_model_schema_and_analysis_router`; `tests/unit/test_rbe_links.py::test_rbe2_multiple_arms_transfer_combined_wrench_and_match_condensed_reference`; `tests/unit/test_rbe_links.py::test_rbe3_projection_matches_independent_weighted_least_squares_and_wrench`; `tests/unit/test_mpc_reduction.py::test_elimination_matches_lagrange_multiplier_solution`; `tests/integration/test_api_and_cli.py::test_rbe2_example_runs_through_api_cli_audit_and_vtu_export`; `tests/integration/test_api_and_cli.py::test_cli_methods_and_modal_solve`; `tests/unit/test_linear_buckling.py::test_linear_buckling_is_routed_through_sparse_eigensolver`; `tests/unit/test_solver_backend.py::test_explicit_scipy_never_falls_back`.
- **Justification** : Campbell a un changement de chemin de provenance wheel après sa preuve; APIs/CLI/IO/dispatch sont partagés; RBE/MPC et solveurs classiques sont des routes exposées. Les tests MPI disponibles vérifient des garde-fous, pas une exécution MPI distribuée.
- **Coût** : faible pour refus/schéma/algebra; moyen pour API/CLI et petits solves; élevé si campagne GYRO-06 multi-maillage ou environnement backend externe.
- **Preuve attendue** : résultats courants liés au code; conservation de l'ambiguïté 100 rad/s; aucune mutation de statut; résultats complexes/branches/hashes vérifiables.
- **Sortie** : sentinelles minimales des routes affectées passées ou exclusion Owner documentée. Rejouer l'intégralité GYRO-05/GYRO-06 seulement si la modification dépendante, l'écart ou le gate Owner le justifie; pas par défaut.
- **Risque** : pas de nœud rotor CLI spécifique; un test public JSON ne couvre pas le CLI rotor. La maturité rotor reste `EXPERIMENTAL`.

### WP12-5 — Performances bornées

- **Objectif** : obtenir des mesures reproductibles sur assemblage, projection/eigensolve, harmonique par fréquence, factorisation/transitoire, stockage historique/checkpoint, tangent NL et cas contact seulement si ce dernier est autorisé.
- **Prérequis** : aucune correction fonctionnelle en attente; futur harness versionné et audité; environnement fixé; charge/maille et répétitions prédéclarées par Owner; mesure mémoire incluant RSS processus natifs.
- **Commande** : aucun script de performance v0.2.12 prêt à être invoqué n'a été trouvé. `scripts/run_wp12_scaling.py` appartient au WP12 v0.2.7 et n'est pas un runner v0.2.12; ne pas le réutiliser pour ce gate. Le futur harness et sa commande restent `PROPOSED — OWNER_APPROVAL_REQUIRED`.
- **Justification** : caractériser croissance avec DDL, nombre de modes/fréquences/pas et taille d'historique. Les mesures v0.2.11 et les microbenchmarks antérieurs décrivent seulement leurs machines/scénarios historiques.
- **Coût** : élevé et incertain; commencer par 2–3 tailles bounded et arrêter si mémoire/temps dépassent les limites Owner. Aucune extrapolation vers des tailles industrielles.
- **Preuve attendue** : temps par étape, factorisations/solves, peak RSS OS, compte DDL/modes/fréquences/pas, environnement et dispersion; distinguer temps mesuré d'estimation.
- **Sortie** : limites de performance requises évaluées si elles sont déjà contractualisées; sinon fournir une caractérisation descriptive sans inventer de PASS/FAIL. Pas de gros MPI/HPC par défaut.

### WP12-6 — Consolidation et décision Owner

- **Objectif** : joindre manifestes gelés, résultats réussis/échoués/skippés, identités, verdicts scientifiques séparés, limites, écarts et recommandation.
- **Prérequis** : lots requis terminés, toute anomalie triée, aucune preuve historique remplacée, hashes finaux calculés.
- **Tests** : aucune nouvelle campagne. Contrôles documentaires de cohérence/hash et inspection de provenance uniquement.
- **Coût** : bas à moyen, dépend du volume de résultats.
- **Preuve attendue** : rapport versionné plus inventaire sha256 final, index des dossiers de campagne, décisions Owner et non-conformités ouvertes.
- **Sortie** : dossier qui permet une décision `CLOSE` ou `OPEN_WITH_ACTIONS`; WP12 reste officiellement OPEN jusqu'à décision Owner séparée.

## MUST / SHOULD / DEFERRED

- **MUST** : WP12-1 projection et identité; oracles indépendants ciblés WP04–WP07 affectés; refus et compatibilités des chemins de résultats; tests bornés NL WP08–WP10; route C02 M4/M5 si C02 est incluse dans la revendication G05 courante; sentinelles des interfaces/dispatch effectivement changés; identités exactes et traitement de tous résultats.
- **SHOULD** : mesure descriptive de performance v0.2.12, campagne ciblée supplémentaire sur E01 si cette voie est revendiquée comme distribuée, compatibilité API/CLI rotor au-delà du routeur JSON, cas de plus grande taille pour confirmer une suspicion de coût.
- **DEFERRED** : qualification générale des routes E01/C01/C02, FSI/contact avec frottement/glissement fini, rotor industriel, réponse balourd, paliers variables, QEP sparse/MPI, benchmarks industriels/HPC, campagnes de convergence générales non exigées par un contrat v0.2.12.

`MUST` est lié à un contrat de portée, à un changement de code ou à une revendication de non-régression explicite; toute exclusion correspondante nécessite une décision Owner explicite. `SHOULD` ne devient pas un gate sans justification et décision. Aucun résultat de ces lots n'est disponible à WP12-0.
