# WP12-A P0 — Dossier Owner de revue du contrat

## État

**`WP12A_P0_BATCH_CONTRACT_READY_FOR_OWNER_REVIEW`**, proposition technique seulement. **Aucune exécution n’est encore autorisée ni disponible.** Ce dossier ne contient aucun reçu officiel de préflight, manifeste runtime, décision Owner d’exécution ou réservation réelle.

## Identités et hashes proposés

- Dépôt de préparation : branche `fix/wp12a-p0-batch-preparation-20261029`; prototype préparé dans `224b5c90`, synchronisé avec le correctif déjà intégré #72 (`aea4ce54`, merge local `77859da4`). Le diff proposé est calculé contre la branche release actuelle; aucun changement n’est encore intégré à cette branche.
- Source scientifique propre : `E:\QFSolverAgents\wp12-dynamics`, `codex/wp12-dynamic-harmonic-verification`, HEAD `7406e34efc28ed8f18c15440115595dfa3dd9ca5`, tree `a618d0d1790ab8642f408a78b2d2856debcc60c0`.
- Contrôleur canonique actuel : HEAD `0d91fc5a9bc09875526af6f17cf42c3ac666c5b7`, tree `3d57c36c948c9cc3fbc8a5d399fc465245c54a11`, fingerprint `4fdbd810091de83ff5f729edfb4b9a20b660156e60dfa136c50eab97350e6afb`. Il ne reconnaît pas encore le protocole batch et n’offre pas les six préflights proposés.
- Contrat Owner de proposition : [WP12A_P0_BATCH_OWNER_CONTRACT_PROPOSAL.json](wp12a_p0/WP12A_P0_BATCH_OWNER_CONTRACT_PROPOSAL.json), SHA-256 `c96974b3764b2222705fd13bf048c85016593f978316f9e136d0cf44e5935dd8`. Ce JSON est `PROPOSAL_ONLY`; son SHA n’autorise aucune exécution.
- Ledger lu en lecture seule au `2026-10-29` : v2 `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88` (5 tentatives Dynamics v2, 4 PASS, 1 PYTEST_FAILED), plus v1 immuable `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37` (5 tentatives, 4 PASS, 1 PYTEST_FAILED) = 10/130 observées. Cette identité est un constat de revue seulement : la préparation réelle devra en relire une nouvelle sous verrou.

## Six cas proposés

Les SHA de manifestes scientifiques ci-dessous sont les SHA bruts des fichiers du dépôt; ils sont encore `PROPOSED_NOT_AUTHORIZED`. Les SHA de préflight et manifestes runtime n’existent pas car le contrôleur canonique ne supporte pas encore ces cas dans le chemin batch.

| # | Nodeid exact | DDL | Timeout / tentative / retry | Fingerprint source | SHA-256 manifeste proposé |
|---:|---|---:|---|---|---|
| 1 | `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | 2 | 300 s / 1 / 0 | `f590849467f9fadf10e871c053d0f369e8e2a095a6ef99ddc452a9d6128b0262` | `8bce34df8962a2d8f1be2fa456bee04e1525d7cf427c443c470ebf546199e45a` |
| 2 | `tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe` | 3 | 300 s / 1 / 0 | `f590849467f9fadf10e871c053d0f369e8e2a095a6ef99ddc452a9d6128b0262` | `deba11dc927c0e042833b3c5d816041c49d01b7f34cfec97020bbd2a3739919e` |
| 3 | `tests/unit/test_modal_basis_damping.py::test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard` | 3 | 300 s / 1 / 0 | `f590849467f9fadf10e871c053d0f369e8e2a095a6ef99ddc452a9d6128b0262` | `97a2174179407acbe1bc8e0131af60e321cc54562a6d746f7d2a1c941321c53e` |
| 4 | `tests/unit/test_analysis_features.py::test_transient_dynamic_sdof_matches_closed_form_initial_energy` | 1 | 300 s / 1 / 0 | `f314c4d8011f9b9b815ee92ddc04d4386798a5a104bed528122649b2067efec1` | `9c5d202089f9927b2d1e76057b57ee70208cfde8175c4b201a69e6f9ed462fb4` |
| 5 | `tests/unit/test_analysis_features.py::test_harmonic_sdof_matches_closed_form_amplitude_and_phase` | 1 | 300 s / 1 / 0 | `f314c4d8011f9b9b815ee92ddc04d4386798a5a104bed528122649b2067efec1` | `2bfb446bf26575cb076334056c56bd217a149e018427b0f0619d95fdf366dc88` |
| 6 | `tests/unit/test_prepared_dynamic_system.py::test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators` | 3 | 300 s / 1 / 0 | `2604e9d0d837a9860f70210be2fc96da1d124cb063d896884dc9033b96a30f23` | `859936d38402223d31428193e2c50d44af4feffa28a9ff0f5af4d72511a306ba` |

Les critères sont copiés des tests inchangés et hashés dans chaque manifeste : aucune assertion, tolérance, fréquence ni donnée physique n’a été ajustée. Le lot ne revendique qu’une preuve bornée sur ces fixtures et leur oracle déclaré. Chaque exécution conserve les enveloppes courantes (RSS souple 4096 MiB, archive 256 MiB, stdout/stderr 32 MiB par flux / 64 MiB total, 16 processus, temporaires 512 MiB) ; aucun budget n’est mutualisé entre cas.

## Décisions à prendre

**Décision de capacité préalable :** approuver ou refuser séparément le passage du plafond d’inscription Dynamics de 13 à 18 pour ajouter exactement les cinq nodeids 2–6 (le nodeid 1 est déjà enregistré). Préserver l’ordre, les fingerprints et l’historique des 13 existants. Le plafond 130, le maximum 10 par nodeid, les délais, ressources et budgets restent inchangés. La proposition locale n’est pas intégrée et ne doit pas être activée avant approbation explicite.

**Décision d’exécution ultérieure :** après intégration revue, contrôleur propre officiellement désigné, registrations actives, six préflights officiels collect-only réussis, ledger courant revalidé et vrai contrat runtime préparé, une seule décision Owner peut couvrir l’ensemble ordonné et leurs transitions autorisées. L’approbation sera liée au SHA brut final du contrat, aux six manifests, identités, critères, budgets, registre et état de ledger. Elle permettra au contrôleur de renouveler techniquement chaque préflight après la mutation légitime du ledger sans redemander l’approbation entre les cas. Elle ne couvrira ni modification d’identité/critère/budget, ni retry.

La procédure `run-wp12a-p0-batch` refuse si une identité change, si un préflight skippe ou collecte un autre nodeid, si le ledger a une écriture étrangère, si le JUnit ne démontre pas un seul cas/assertion pour la continuation, ou si une réservation reste `RESERVED`. Une réservation interrompue est consommée et bloque la reprise du cas. Le cas scientifique suivant ne démarre qu’après archivage et vérification du précédent.

## Réserves de revue

- L’extension de registre et le runner local sont en branche de proposition; aucune fusion ni pin canonique n’a eu lieu.
- Les tests synthétiques n’exécutent aucun corps scientifique et ne constituent pas des préflights officiels.
- Le snapshot de ledger dans le JSON est périssable et explicitement non-runtime. Le helper devra créer un nouveau contrat/hashes après integration et vérifier le ledger sous verrou.
- L’autorisation et les fichiers hashes ne sont pas une signature cryptographique ni une frontière OS contre un processus local arbitraire.
- **Aucun test P0 n’est encore `PASS` : les six sont `NOT_RUN`; aucun résultat scientifique n’est inféré de la préparation.**

## Vérifications synthétiques de cette proposition

- `py -m pytest -q tests/unit/test_wp12a_p0_batch.py tests/unit/test_development_autonomous_policy.py` : **269 PASS**.
- `py -m pytest -q tests/unit/test_wp12b_owner_decision_contract.py tests/unit/test_wp12b_diagnostic_provenance.py tests/unit/test_wp12b_hex20_diagnostic_support.py tests/unit/test_wp12b_hex20_quadrature_math.py tests/unit/test_hex8sri_manifest_refresh.py tests/unit/test_wp12a_mpc_rbe_route_preflight.py` : **51 PASS**.
- `py scripts/run_wp12_controller_synthetic.py` : **320 PASS, 0 FAIL, 0 skip, 0 erreur**. La liste du script ne contient que des modules de contrôleur et des doubles synthétiques; elle n’inclut pas les corps des tests Newmark, harmonique ou base-motion.
- Ruff sur les cinq fichiers Python modifiés : **PASS**.
- `py_compile` des cinq fichiers Python : **PASS**.
- Validation JSON : **8 fichiers PASS** ; `git diff --check` : **PASS**.

Les deux sélections pytest utilisent des fichiers temporaires, un faux contrôleur et des reçus/JUnit synthétiques; elles couvrent 320 tests avec paramètres au total, sans additionner une seconde fois l’exécution du script CI qui rejoue les contrats synthétiques un par un. Elles ne lancent aucun nodeid scientifique et n’écrivent pas dans les ledgers officiels. Aucun préflight officiel n’a été effectué. Le workflow GitHub déclenché sur PR vers la branche release exécute cette seule suite synthétique, Ruff, compilation, validation JSON et `git diff --check`; le gate général qui inclut des vérifications d’ingénierie cible `main` et ne s’exécute pas sur cette PR. La PR reste à revoir, et la proposition de plafond 18 ne doit pas être activée avant l’approbation Owner correspondante.
