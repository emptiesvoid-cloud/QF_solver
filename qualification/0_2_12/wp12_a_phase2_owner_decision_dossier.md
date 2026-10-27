# WP12-A — Dossier de décision Owner, phase 2

Date : 2026-10-27\
Candidat : `emptiesvoids-cloud/wp12-dynamics-selective-integration`\
HEAD de réconciliation : `d73e21927c58938e9394f6b3b682a450b2ab9096`\
Base intégrée : `emptiesvoids-cloud/0.2.12` à `d64e6036a845e0b720dc9f2bd5a89076dbbc7d4c`

## Décision proposée

**`CONDITIONAL_GO` pour revue documentaire et synthétique seulement.** Maintenir `WP12=OPEN`, les maturités inchangées et toute qualification `NOT_ASSESSED`. Le statut de livraison proposé est `WP12A_REGRESSION_GAPS_ADDRESSED_EXECUTION_AUTHORIZATION_PENDING`.

Aucune exécution scientifique n’est autorisée par ce dossier. Aucun calcul FEM, modal, harmonique ou Newmark, aucune tentative n’a été réservé et aucune décision Owner n’a été créée.

## Matrice WP04–WP07 et statuts de preuve

La matrice détaillée contient maintenant 21 lignes, dont une nouvelle ligne de refus MPC/RBE synthétique : [COVERAGE_MATRIX.tsv](vv_local/wp12_legacy_cross_route/COVERAGE_MATRIX.tsv). La lire avec les distinctions suivantes :

| Catégorie | Portée conservée | Statut sur le candidat `d73e2192` |
|---|---|---|
| PASS historique | Rapports WP04–WP07, WP13 et preuves antérieures; chaque résultat reste lié à son HEAD et environnement d’origine. | `PASS_REPORTED_HISTORICAL`; pas une exécution candidate. |
| PASS de développement borné | Trois sentinelles dynamiques exécutées sur le snapshot `d9deddbd…`; WP04–WP07 restent expérimentaux. | `PASS_REPORTED_DEVELOPMENT_D9`; `NOT_RUN` sur `d73e2192`. |
| Qualification formelle | Les rapports/source historiques marquent les nouvelles routes `NOT_ASSESSED`. | `NOT_ASSESSED`; aucune promotion. |
| Échecs et indéterminés préservés | G03 et MITC4 restent en échec historique; WP-D01 reste inconclusif pour les vérifications structurelles manquantes; le rejeu WP07 historique demeure `FAIL`. | Inchangés; aucun résultat ne les remplace. |

Le lot MPC/RBE statique conserve ses contrats limités. Les 12 nouveaux tests appellent uniquement des validations de refus pour MPC, RBE2 et RBE3; ils ne vérifient pas les déplacements ou réactions d’une solution statique. Les campagnes statiques WP13 déjà rapportées ne sont pas rejouées ici.

## Trois manifestes en attente et un cas bloqué

Les quatre nodeids sont enregistrés sous le périmètre `wp12_dynamics`, qui impose un maximum de 10 tentatives par nodeid, une limite de 300 s par tentative et 4 096 MiB de RSS observé (limite souple). Les limites complémentaires sont 16 processus, 64 MiB de sortie totale / 32 MiB par flux, 512 MiB temporaires et 256 MiB d’archives. La limite de DDL est celle de la sélection enregistrée pour chaque cas.

| Cas | Nodeid exact | DDL sélectionnés | Fingerprint de politique/contenu | Oracle et observables | Manifest / décision |
|---|---|---:|---|---|---|
| Rejeu WP07 historique | `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames` | 1 libre (12 DDL physiques) | Registre historique : `6db5b4597252082012fa38b1ed3ad8859befb7ec9a99bd7d54dd6cf486ae4d56`; fingerprint courant : `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | Équation libre SDOF indépendante, repères relatifs/absolus et round-trip `frequency_response`; le FAIL antérieur est préservé. | Refus contrôleur : `WP12 source fingerprint changed`; manifeste absent. |
| Newmark modal | `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables` | 1 | `65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8` | SDOF BEAM2; raffinement de pas, solution analytique, résidu réduit, énergie, états u/v/a et sidecar pré-assertion. | [Manifeste](<E:/QFSolverAgents/evidence/dynamics/authorizations/wp12_dynamics/wp12a-newmark-20261027-p2-01.json>) — SHA-256 `c657172d03d94f53cb95231dae795041c2131c7bf2aaf651fe4de7b31ae8098d`; `PREPARED_NOT_AUTHORIZED` |
| Harmonique réduit | `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation` | 3 | `bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c` | Balayage TET4; comparaison base complète/directe et observables de troncature; données complexes et conditionnement archivés. | [Manifeste](<E:/QFSolverAgents/evidence/dynamics/authorizations/wp12_dynamics/wp12a-harmonic-20261027-p2-01.json>) — SHA-256 `e649468cfbd4374e4936e8068be9771cf31cc9f9e283f953861816e011b30184`; `PREPARED_NOT_AUTHORIZED` |
| Accélération de base | `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` | 1 | `969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6` | Balayage complexe BEAM2; signes, réponses relatives/absolues, identités cinématiques et sérialisation. | [Manifeste](<E:/QFSolverAgents/evidence/dynamics/authorizations/wp12_dynamics/wp12a-base-motion-20261027-p2-01.json>) — SHA-256 `6d9bff0e84e3b0b4c4a5f4bd9f8228eb90998ec72bbea03969b357f38b106d99`; `PREPARED_NOT_AUTHORIZED` |

Les trois empreintes des sentinelles WP12 correspondent aux entrées actives de la politique et aux fonctions présentes dans l’arbre réconcilié. Le nodeid WP07 historique est allowlisté dans `wp12_dynamics`, mais son enregistrement ciblé conserve `6db5…`, alors que le contrôleur recalcule `969dd…` pour son module actuel. Il est refusé comme stale source. Aucun manifeste n’a été produit pour ce nodeid.

## Identité du contrôleur et blocage des manifestes

Empreintes du contrôleur et de la politique dans le checkout détaché propre au commit `d64e6036` :

| Fichier | SHA-256 |
|---|---|
| `scripts/development_autonomous.py` | `e307547a47e7d1c58224eb74a52211c47bc4270a86e875a6af0d56496bfc4500` |
| `scripts/development_autonomous_pytest_plugin.py` | `9b8fd647434469b1f6e26085d148bb81f22d5a87b4dbaac11c087173e5577df5` |
| `development_autonomous_policy.json` | `cdcdda2b9dc6cb0a23241b7d62ccd56403a76a731d022c6e86f37c3cb82245d0` |

Fingerprint commun du contrôleur dans les trois manifestes : `5e8225187fe9495a0c4d8516ec11323432ca0aa50ce38bf65ed66a0999a74e08`.

Le mandat applicable est `DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1`. Le contrôleur exige un worktree scientifique enregistré et propre : `E:\QFSolverAgents\wp12-dynamics`, branche `codex/wp12-dynamic-harmonic-verification`, HEAD `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`, arbre `a6bcf6a3cea4bdc9ab17adcf53ce2151a2bc4758`. Les trois manifestes sont liés à cette identité exacte; les fichiers scientifiques et les modules de sentinelles sont identiques à ceux du candidat intégré `d73e2192…`. Le contrôleur utilisé est le checkout détaché propre `C:\Users\fari\.codex\worktrees\wp12a-controller-canonical\qf_solver`, HEAD `d64e6036`; il doit rester disponible pour préserver la même identité du contrôleur lors du preflight ultérieur. Le checkout existant `E:\QFSolverAgents\wp12-policy-final` reste à `4bf52792`, en retard de 36 commits et avec ses modifications locales préexistantes de politique; il n’a pas été utilisé ni modifié.

En conséquence : trois manifestes inédits existent en état `PREPARED_NOT_AUTHORIZED`, sans décision Owner ni réservation d’essai. Le nodeid historique WP07 est refusé pour fingerprint source périmé et son manifeste n’existe pas. Les anciens manifestes et leurs décisions, notamment `OWNER_AUTHORIZED`, restent intacts et ne sont pas réutilisés. Aucun lancement ou ledger d’essais n’a eu lieu. Les manifestes ciblent l’identité scientifique enregistrée `630d22b…`, et non le HEAD Git d’intégration `d73e2192…`.

## Vérifications effectuées, sans calcul scientifique

| Vérification | Résultat |
|---|---|
| Tests synthétiques MPC/RBE (3 fonctions, variantes modal/transitoire/harmonique et MPC/RBE2/RBE3) | 12 PASS / 0 FAIL |
| Archivage synthétique d’observables | 18 PASS / 0 FAIL |
| DTO et sérialisation | 4 PASS / 0 FAIL |
| Contrôles synthétiques de politique et manifeste | 3 PASS / 0 FAIL |
| Total exécuté dans cette phase | **37 PASS / 0 FAIL** |
| Collecte WP07 historique + trois sentinelles | 4 collectés, aucun exécuté |
| Ruff, compilation Python, parsing JSON de politique | PASS |
| FEM, modal, harmonique, Newmark, benchmark | **NOT_RUN** |

Ces tests ne changent ni oracle, ni seuil, ni formulation. Les preuves historiques et les dossiers d’échecs restent hors modification. Aucun statut officiel WP12/WP13, niveau de maturité, merge ou publication n’est modifié.

## Actions Owner requises avant toute exécution

1. Examiner et signer ou refuser séparément les trois manifestes fournis; ils ciblent le worktree scientifique enregistré `630d22b…`, aux mêmes fichiers de source et test que le candidat d’intégration.
2. Décider de la voie conforme pour rafraîchir l’enregistrement source du nodeid WP07 historique, ou le laisser différé; ne pas réutiliser son ancienne décision.
3. Si le HEAD Git `d73e2192…` doit être la cible d’exécution explicite, faire inscrire cette identité selon la procédure canonique et préparer de nouveaux manifestes liés à ses enregistrements.
4. Exécuter séquentiellement uniquement après les états `OWNER_AUTHORIZED` retournés par le contrôleur et archiver chaque résultat même en cas d’échec.

Jusqu’à ces actions, le rejeu WP07 historique reste `PREPARATION_BLOCKED`; les trois sentinelles ont des manifestes officiels `PREPARED_NOT_AUTHORIZED`, sans autorisation d’exécution.
