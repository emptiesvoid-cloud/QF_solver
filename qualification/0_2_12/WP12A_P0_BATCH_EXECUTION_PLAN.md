# WP12-A P0 — Plan de campagne groupée

**État : `WP12A_P0_BATCH_CONTRACT_READY_FOR_OWNER_REVIEW` — proposition non exécutable.** Aucun corps scientifique, préflight officiel, manifeste d’exécution, réservation ou changement de ledger n’a été lancé dans cette mission.

## Périmètre fermé proposé

Les quatre expériences WP12-A déjà réussies et archivées ne sont pas rejouées. Le complément P0 est un ordre fermé de six nodeids, chaque cas comptant une tentative distincte et un plafond de 300 s. Le détail versionné et les SHA-256 sont dans [le contrat Owner proposé](wp12a_p0/WP12A_P0_BATCH_OWNER_CONTRACT_PROPOSAL.json) et les six manifestes scientifiques proposés dans `wp12a_p0/case_manifests/`.

| Ordre | Nodeid | Capacité | DDL sélectionnés | Oracle / assertions existantes |
|---:|---|---|---:|---|
| 1 | `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | AN-MODAL, AN-MODAL-BASIS | 2 | Système couplé analytique à 2 DDL, valeurs propres, orthogonalité massique et opérateurs projetés ; tolérances existantes 1e−12 à 1e−11. |
| 2 | `tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe` | AN-MODAL-BASIS | 3 | Invariance du sous-espace dégénéré après rotation/changement de signe et résidu ; tolérance existante 1e−12. |
| 3 | `tests/unit/test_modal_basis_damping.py::test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard` | AN-MODAL-BASIS, AN-PREPARED | 3 | Projection Rayleigh et garde de cluster ; assertions existantes rtol=atol=1e−10. |
| 4 | `tests/unit/test_analysis_features.py::test_transient_dynamic_sdof_matches_closed_form_initial_energy` | AN-DIRECT-TRANSIENT | 1 | SDOF temporel et énergie initiale/finale ; seuils 1e−12, 1e−10 et résidu/dérive <1e−10, inchangés. |
| 5 | `tests/unit/test_analysis_features.py::test_harmonic_sdof_matches_closed_form_amplitude_and_phase` | AN-DIRECT-HARMONIC | 1 | Réponse directe complexe SDOF, amplitude, phase, DC et résidu ; seuils existants inchangés. |
| 6 | `tests/unit/test_prepared_dynamic_system.py::test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators` | AN-PREPARED, AN-EXCITATION | 3 | Nombre d’assemblages et identité des opérateurs conservés lors d’un changement d’excitation. |

Les cas 2 à 6 sont les cinq nouvelles inscriptions proposées. Le premier est déjà dans les 13 inscriptions actives, mais n’est pas dans le préflight officiel actuel.

## Enveloppes et ordre Owner

L’extension demandée séparément est **13 → 18 nodeids**. Elle ajoute uniquement les cinq identités exactes ci-dessus et préserve les 13 inscriptions historiques dans le même ordre. Le plafond global reste 130 tentatives Dynamics, le maximum par nodeid reste 10, et chaque cas proposé conserve les enveloppes enregistrées : 300 s, RSS souple 4096 MiB, archive 256 MiB, stdout/stderr 32 MiB par flux, 64 MiB cumulés, arbre de processus 16 et temporaires 512 MiB. Les sélections de DDL restent indépendantes et ne sont pas fusionnées.

Deux décisions restent distinctes dans le temps :

1. **Décision préalable de politique :** accepter ou refuser la proposition 13 → 18. Aucune inscription nouvelle ne devient active avant approbation et intégration.
2. **Revue d’exécution unique :** après intégration, nouvelle désignation propre du contrôleur, inscriptions append-only, préflights JIT officiels et manifeste runtime final, l’Owner peut autoriser une fois le contrat exact des six cas. Cette décision ne se propage pas à un contrat modifié et ne permet aucun retry.

## Séquence lorsque les prérequis seront effectifs

1. Figer six manifestes scientifiques et un contrat ordonné, avec leurs hashes, critères, budget par nodeid, identité du contrôleur, identité source et état initial du ledger.
2. Obtenir le PASS collect-only officiel d’un seul nodeid juste avant sa réservation. Ce préflight doit attester un nodeid exact, zéro skip/corps/réservation, origine `solveur` correcte et ledger inchangé.
3. Sous verrou Dynamics, vérifier les identités, plafonds et hash du ledger. Réserver une fois, exécuter le nodeid et écrire un reçu/une archive propres au cas.
4. Sous le même verrou, vérifier que la transition ledger ne contient que cette tentative autorisée et sa finalisation. Relire le ledger réel et générer le préflight du cas suivant à partir de ce nouvel état.
5. Continuer automatiquement uniquement si le contrat autorise la classification du cas précédent. Une assertion pytest unique de type `AssertionError`, sans erreur/skip et rattachée au nodeid exact, peut continuer ; toute ambiguïté de JUnit, erreur de setup/infra, divergence de provenance ou transition étrangère arrête la campagne.
6. Reprise uniquement avec l’option explicite `--resume`, après validation du préfixe de ledger, des manifestes, des préflights historiques de campagne, du JUnit et des reçus. Une réservation interrompue est consommée et ne peut jamais être relancée.

Les quatre anciens PASS restent conservés, de même que les FAIL historiques. Ce lot est une campagne de développement bornée, sans qualification physique générale. La procédure demeure bloquée par l’absence d’enregistrement actif des cinq nodeids et par l’absence du préflight batch dans le contrôleur désigné ; aucune exécution n’est autorisée par ce plan.
