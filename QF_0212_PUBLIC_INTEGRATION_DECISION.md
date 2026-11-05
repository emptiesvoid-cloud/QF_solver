# QF Solver 0.2.12 — décision d’intégration publique minimale

**Verdict : `PUBLIC_INTEGRATION_READY_FOR_CI`**
**Portée : préparation locale d’une branche d’intégration et validation non FEM ciblée. Ce verdict n’autorise ni PR, ni push, ni merge, ni publication.**

## Identités et état

| Élément | Identité vérifiée |
|---|---|
| Base `main` | `e367fe58b2b9ebb4aef321424ca775e80e82d9ca` — tree `0f10660178f005dc84da70771fb31362fe6c646a` |
| Candidate source examinée | `6a5ff4c648db4349561edaa2b82a5fec74322209` — tree `2edf9cd98bef6be8bc4392b3d0e5ea798905ca1e` |
| Candidate publique v0.2.12 déjà accessible | branche distante `emptiesvoids-cloud/0.2.12` à `06fce7a47d41223955755c34e7238376b3c4a7b5` |
| Commit local du contenu intégré | `6c3323dc82117978796e0d8f53e57c5d9d2cd04d` — tree `c8fb1e50ea680f9fb162b8af8d665a86998a5381` |
| Parent du commit local | `e367fe58b2b9ebb4aef321424ca775e80e82d9ca` |
| Branche locale | `emptiesvoids-cloud/qf0212-minimal-main-20261105` |

Le pointeur distant `origin/main` a été relu avant le commit local et correspondait à la base indiquée. Le commit `6a5ff4c…` n’a pas été modifié. Le worktree source candidat est resté distinct. Aucun transfert vers GitHub n’a été fait.

## Contenu réellement intégré

Le commit local contient 186 chemins sélectionnés (28 368 insertions, 964 suppressions), comparés octet pour octet à la candidate `6a5ff4c…` avant commit. 185 fichiers sont identiques; `docs/verification/qualification.md` remplace un chemin de preuve relatif par un lien au snapshot historique distant `06fce7a…`, vérifié dans le tree Git et conservant son avertissement de non-transfert. La comparaison candidate/main compte 1 078 chemins changés : 186 intégrés et 892 laissés hors branche. Les 74 chemins `src/` correspondent exactement aux blobs de cette candidate. Aucun seuil, oracle ou test n’a été édité pour faire passer un contrôle.

| Famille | Fichiers |
|---|---:|
| Code `src/` | 74 |
| Tests ordinaires, algébriques ou de compatibilité retenus | 64 |
| Documentation publique et index d’exemples | 19 |
| Exemples | 7 |
| Modules AQ-09 algébriques utilisés par les tests | 2 |
| Contrats/manifeste de tests sélectionnés sous `qualification/0_2_12` | 3 |
| Scripts de qualité, release et compatibilité | 6 |
| Workflows, packaging, métadonnées et configuration | 11 |
| **Total** | **186** |

Le README, le changelog, la citation et les pages de préparation distinguent explicitement la version publiée `0.2.11` de la candidate non publiée `0.2.12`. La matrice candidate `docs/qualification_matrix.md` n’a pas été importée : elle ajoutait une revendication C03 supplémentaire qui n’est pas nécessaire à la CI standard. `docs/verification/qualification.md` conserve la note C03 limitée et historique de la candidate, en remplaçant le chemin relatif absent de `main` par un lien vers le tree distant vérifié `06fce7a…`. Le record consulté a le SHA-256 `5c62a1a389c8afc4f048a0b9e4ec0ce6b09bdda58a590f9abc69b8db0e116757`. La note indique explicitement que le certificat ne s’applique pas au HEAD d’intégration; ce lien Git public n’est pas un archivage externe distinct.

## Différentiel de confidentialité des 52 chemins

Le rapport de scanner antérieur sur la candidate complète contre `main` compte 354 lignes ajoutées dans 52 chemins. Il utilise des règles heuristiques, pas un scanner général de secrets. La comparaison des blobs de ces 52 chemins avec le HEAD distant vérifié `06fce7a…` a donné :

- 47 chemins déjà présents à l’identique dans ce commit distant;
- 3 chemins présents avec un blob différent : `development_autonomous_policy.json`, `scripts/development_autonomous.py`, `tests/unit/test_development_autonomous_policy.py`;
- 2 absents de ce commit : `AQ09_NONDIAGONAL_VALIDATION.md`, `AQ09_REWORK_IMPLEMENTATION.md`.

Le scanner officiel de différentiel appliqué à `6a5ff4c…` relativement à `06fce7a…` a détecté six nouvelles correspondances de motifs dans les trois fichiers modifiés : deux du motif de profil local et quatre du motif de racine de contrôleur. Les deux rapports AQ-09 absents de `06fce7a…` portent aussi des chemins locaux. **Ces cinq chemins ne sont pas intégrés.** Aucune valeur de chemin détectée n’est reproduite dans ce rapport.

La sélection de 186 chemins a passé `python scripts/check_privacy_diff.py --cached` avec `Privacy diff check: PASS`. Ce résultat couvre les quatre motifs implémentés par ce script et le différentiel sélectionné seulement. Il ne résout pas G03, ne blanchit pas les branches ou l’historique déjà publics et ne constitue pas une garantie absolue contre secrets ou données personnelles.

Les 52 chemins concernés, par nom seulement, sont :

- `AGENTS.md`
- `AQ09_NONDIAGONAL_VALIDATION.md`
- `AQ09_REWORK_IMPLEMENTATION.md`
- `DEVELOPMENT_AUTONOMOUS.md`
- `development_autonomous_policy.json`
- `docs/development/HEX8SRI_REFINED3_8X4X4_CRITERIA.md`
- `docs/development/WP12A_LEDGER_MANDATE_RECOVERY.md`
- `docs/development/WP12A_POST_CAMPAIGN_INFRASTRUCTURE_RECOVERY.md`
- `docs/qualification/0_2_12/WP12A_EVIDENCE_MATRIX.md`
- `docs/qualification/0_2_12/WP12A_SCIENTIFIC_CLOSURE_REPORT.md`
- `docs/verification/wp12_b_elements_loads_audit.md`
- `experiments/wp12_tet4_convergence/case_metrics.csv`
- `experiments/wp12_tet4_convergence/report_consolide.md`
- `experiments/wp12_tet4_convergence/summary.json`
- `qualification/0_2_12/HEX20_CONTROLLER_DECISION_ID_ROOT_CAUSE_AND_FIX.md`
- `qualification/0_2_12/HEX20_FINAL_OWNER_EXECUTION_DOSSIER.md`
- `qualification/0_2_12/HEX20_PROSPECTIVE_EXECUTION_PREPARATION.md`
- `qualification/0_2_12/WP12A_P0_CONTROLLER_CONTRACT_AUDIT.md`
- `qualification/0_2_12/WP12A_P0_OWNER_BATCH_AUTHORIZATION_DOSSIER.md`
- `qualification/0_2_12/WP12A_P0_RELEASE_DISPOSITION_MATRIX.md`
- `qualification/0_2_12/WP12B_HEX8SRI_CORRECTION_AND_CAMPAIGN_STATUS.md`
- `qualification/0_2_12/WP12B_HEX8SRI_PROSPECTIVE_INVESTIGATION_20261029.md`
- `qualification/0_2_12/vv3d_bounded_closeout_0_2_12.md`
- `qualification/0_2_12/vv_local/WP12_BRANCH_INVENTORY_20261031.csv`
- `qualification/0_2_12/vv_local/WP12_CLOSED_AND_RELEASE_BRANCH_READY_FOR_WP13.md`
- `qualification/0_2_12/vv_local/WP12_CONSOLIDATION_INDEX.md`
- `qualification/0_2_12/vv_local/WP12_DIVERGENT_HEADS_20261031.csv`
- `qualification/0_2_12/vv_local/wp12_dynamics/DYNAMIC_HARMONIC_RESULTS_REPORT.md`
- `qualification/0_2_12/vv_local/wp12_dynamics/WP12A_AUTONOMOUS_CONTROLLER_RECOVERY_AND_EXECUTION.md`
- `qualification/0_2_12/vv_local/wp12_dynamics/WP12A_CI_RECOVERY_TO_SCIENTIFIC_EXECUTION.md`
- `qualification/0_2_12/vv_local/wp12_legacy_cross_route/LEGACY_CROSS_ROUTE_REPORT.md`
- `qualification/0_2_12/wp12_a_final_verification_audit.md`
- `qualification/0_2_12/wp12_a_phase2_owner_decision_dossier.md`
- `qualification/0_2_12/wp12_a_phase4_owner_authorization_dossier.md`
- `qualification/0_2_12/wp12_b_hex20_prospective_assertion_restoration_report.md`
- `qualification/0_2_12/wp12a_p0/WP12A_P0_BATCH_OWNER_CONTRACT_PROPOSAL.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-direct-harmonic-sdof-r2.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-direct-harmonic-sdof.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-direct-transient-sdof-r2.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-direct-transient-sdof.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-coupled-two-dof-r2.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-coupled-two-dof-r3.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-coupled-two-dof.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-degenerate-subspace-r2.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-degenerate-subspace.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-modal-rayleigh-projection.json`
- `qualification/0_2_12/wp12a_p0/case_manifests/wp12a-p0-an-prepared-operators.json`
- `qualification/0_2_12/wp12b_bounded_closeout_0_2_12.md`
- `scripts/development_autonomous.py`
- `scripts/wp12_vv3d_family_remainder_contract.py`
- `scripts/wp12_vv3d_tet4_l3_diagnostic.py`
- `tests/unit/test_development_autonomous_policy.py`

## Preuves et dépendances : 11 modules

Aucune preuve WP12 n’a été supprimée, déplacée ou modifiée. Les preuves intégrées ci-dessous ne remplacent pas un ledger ni un résultat FEM. L’URL de stockage privé n’est pas supposée : le ref distant `emptiesvoids-cloud/0.2.12` à `06fce7a…` a été vérifié par `git ls-remote`; les chemins et blobs indiqués existent dans ce commit. Il s’agit du dépôt Git public, pas d’une archive privée distincte.

| Module candidat | Dépendance et rôle | Décision dans la branche |
|---|---|---|
| `tests/synthetic/test_local_vv_provenance_hook_r2.py` | Manifeste R3 `qualification/0_2_12/vv_local/wp12_v2/r3/V2_R3_MANIFEST.json`; le test vérifie un runner de scope WP12. SHA-256 du manifeste `081d97b0667877b4c778a09801b02ac35fe80a2327bf8dc7d8e66c0e641706a1`. | Module et contrôleur omis; test synthétique non exécuté. Le manifeste reste référencé à `06fce7a…`. |
| `tests/verification/test_wpc02_ar_native_contact_convergence.py` | Plan C02 (`fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc`) et protocole (`ca17d8aff01ff90d5c5389060daeb11a1a4a6f4d0ec60be24403b50ce83fcda3`); M4/M5 réalisent des calculs FEM et passent par un ledger autorisé. Le manifeste d’exécution attendu n’est pas présent dans `6a5ff4c…`. | Module omis; préflight M4/M5 et calculs non exécutés; décision d’autorisation et manifeste restent requis. |
| `tests/unit/test_wp01_shared_contracts.py` | Contrat déclaratif `qualification/0_2_12/wp01_shared_contracts.json`, SHA-256 `c94b110850c2f5a93b3f5dd40462b5bcf029c78ef8620bd0dd690a3acb57d1b6`; ne contient pas de résultats de calcul. | Contrat et module inclus; 16 tests de contrat passés. |
| `tests/unit/test_wp07_uniform_base_acceleration.py` | Contrat WP07 SHA-256 `184a62802db0102cfd93c05da1408d35527ea524d6d7c86aa1da8f209e40c88b`. Le module prépare des systèmes à partir de modèles et écrit des observables WP12; il ne relève pas d’un test purement algébrique isolé. | Module et chemin WP12 omis; aucun test FEM ou ledger exécuté. Le JSON reste un contrat sélectionné, pas une preuve de résultat. |
| `tests/unit/test_wp12_process_attestation.py` | Tests synthétiques d’attestation; dépendent du runner, de la politique de worktree et de chemins de ledger. | Module/contrôleur omis; aucun ledger touché. |
| `tests/unit/test_wp12_qualification_runner.py` | Contrats de runner, provenance, confiance machine, réservations et tentatives; dépend des outils et règles WP12 non importés. | Module/contrôleur omis; aucune campagne lancée. |
| `tests/unit/test_wp12_vv3d_adaptive_prepared.py` | Le module mêle cas FEM préparés et tests synthétiques de runner; référence notamment `experiments/wp12_vv3d_adaptive/prepared_20261029/MATRIX_NOT_AUTHORIZED.json`, SHA-256 `013abf31c3876dcffd2a4128f804dc7f648121663f6b3b0757d0ca08ea702e9e`. | Module/corpus omis; cas FEM non exécutés. Le fichier est présent au ref distant `06fce7a…`. |
| `tests/unit/test_wp12_vv3d_controller_gate.py` | Liaison du contrôleur, du catalogue de cas, des autorisations et des ledgers; tests synthétiques ne remplacent pas les preuves de campagne. | Module/contrôleur omis; aucune réservation. |
| `tests/unit/test_wp12_vv3d_tet4_l3_optimized_controller.py` | Vérifie l’historique et les hashes de ledgers prédécesseurs, budgets et refus de retry. | Module et ledgers omis du contenu intégré; résultats historiques inchangés. |
| `tests/unit/test_wp12_vv3d_tet4_l3_diagnostic.py` | Vérifie les décisions Owner, l’append-only et les garde-fous du runner diagnostic. | Module/contrôleur omis; aucune tentative. |
| `tests/unit/test_wpc02_ar_native_manifest_contract.py` | Plan, approbation prospective, protocole et runner C02; le manifeste d’exécution C02 est absent de la candidate. Les nodeids M4/M5 sont dans l’autre module de vérification ci-dessus. | Module/runner omis; manifestes manquants et autorisation demeurent bloquants pour cette campagne seulement. |

Les trois fichiers de qualification sélectionnés sont :

- `wp01_shared_contracts.json`, blob Git `b755adecb0003e93fe11ef925ac64c1abda309b3`, SHA-256 `c94b110850c2f5a93b3f5dd40462b5bcf029c78ef8620bd0dd690a3acb57d1b6`;
- `wp07_uniform_base_acceleration_contract.json`, blob Git `c684d724ea8323ced33320946970dfe3bb3efc5b`, SHA-256 `184a62802db0102cfd93c05da1408d35527ea524d6d7c86aa1da8f209e40c88b`;
- `wp13_compatibility_nodeids.json`, blob Git `8375a013d5c0e9ce3e9bed0404112cc981c14533`, SHA-256 `0fb5add51545ce77e0ce93ddc5c7c1cb20cff2d74f554136c47f24cf423156ba`.

Les trois blobs existent déjà dans le commit distant `06fce7a…` avec les mêmes identités. Le manifeste WP13 énumère 15 contrats non scientifiques d’import, CLI, validation, écriture et sérialisation; les 15 ont passé. Les JSON WP01/WP07 sont des contrats, pas des substituts aux résultats WP12. Aucun ledger de campagne n’est intégré à cette branche ni modifié.

Autres dépendances de données présentes dans le même ref distant et inchangées dans `6a5ff4c…` :

- `experiments/wp12_vv3d_adaptive/field_error_draft.py`, SHA-256 `1e715a763920adab54ef18b2c6f278893eef6bc64fc4373e46e2b9f348b697d4`;
- `experiments/wp12_vv3d_adaptive/quadrature.py`, SHA-256 `15e0d602cdedb8d95ae7788b97321f436a273f0999dd8cde6be5a0a227265b00`;
- `qualification/0_2_12/wp12_preparation/wp12_a_isolation_attestation.json`, SHA-256 `b1b3842bebcce5235dc0b73d13e1a3616da4ca3b9736bb18b7ab0e6c35c426b3`;
- `qualification/0_2_12/wp_c02_ar_mesh_plan.json`, SHA-256 `fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc`;
- `qualification/0_2_12/wp_c02_ar_spatial_convergence_protocol_report.md`, SHA-256 `ca17d8aff01ff90d5c5389060daeb11a1a4a6f4d0ec60be24403b50ce83fcda3`;
- `qualification/0_2_12/wp_c02_n03_ar_prospective_criteria_approval.json`, SHA-256 `e27403b8d98dfee9d98733c4b6c3faef022ac79fbfa0296dc746d5070fdd6c0a`.

Ils restent dans le commit source public vérifié, hors branche d’intégration. Les manifestes et décisions non présents, notamment le manifeste d’exécution C02, ne sont ni inférés ni déclarés archivés. Aucun stockage privé externe n’a été créé ou vérifié.

## Autres tests non intégrés

Sur les 120 chemins de tests/fixtures modifiés par `6a5ff4c…` par rapport à `main`, 64 sont sélectionnés ci-dessus et 56 sont laissés hors de cette branche. Ce n’est pas un effacement : ils restent dans le commit source et la candidate. Ils relèvent d’infrastructure/corpus/campagnes ou de contrats non nécessaires à la suite publique sélectionnée. Leur absence n’est pas comptée comme PASS ni comme SKIP. Les familles laissées hors branche comprennent les fixtures `wp12_runner`, `wp12_u` et `wp12_v2`, les suites `test_wp12*`, `test_wp12a*`, `test_wp12b*`, WP-C01/WP-C02, WP-D01/WP-D02, WP-E01 et `test_wp13_package_smoke.py`, ainsi que les tests AQ-09 de ledger et de validation FEM. Les sept tests `test_wp12*` de réponse modale/dynamique nommément filtrés dans `quality.yml` gardent leur statut de campagne; la matrice standard ne les présente pas comme PASS.

## Vérifications exécutées sur le contenu sélectionné

- Comparaison des 186 chemins intégrés avec l’arbre `6a5ff4c…` : mêmes octets; sortie `git diff --cached --quiet` = 0 avant commit.
- Ruff sur les packages, tests, scripts et modules AQ-09 sélectionnés : PASS.
- Compilation Python ciblée : PASS.
- Mypy selon le gate de `quality.yml` (4 fichiers source) : PASS. Une commande locale plus large englobant les deux `conftest.py` s’est arrêtée sur `Duplicate module named "conftest"`; ce n’est pas le gate CI, et le gate CI exact a ensuite réussi.
- `mkdocs build --strict -f .github/pages/mkdocs.yml` : PASS; MkDocs a émis des avis d’information sur des pages non liées dans la navigation.
- Contrôle `git diff --check` du commit d’intégration : PASS.
- Scanner de différentiel officiel sur la sélection pré-rapport : PASS. Il couvre ses motifs codés, pas G03 global.
- 105 résultats de tests exacts non FEM passés : 74 algébriques AQ-09/modal, 16 contrats déclaratifs WP01, 15 nodeids WP13 de compatibilité. Les fonctions ont été lancées individuellement. Aucun assemblage FEM, solve de modèle, campagne, réservation ou écriture de ledger n’a été fait.
- 12 autres nodeids isolés passés individuellement : 9 fonctions AQ-15 provenance et 3 contrôles du scanner de différentiel; un cas parametré AQ-15 exerce les deux routes synthétiques. Aucun solver n’a été appelé.

Une commande mypy exploratoire plus large a échoué avec le doublon `conftest`; elle n’a pas conduit à un changement. Aucune suite complète n’a été exécutée.

## CI, Pages et limites

Une PR vers `main` déclencherait `quality.yml` (quatre cellules : Ubuntu/Windows, Python 3.10/3.13) et `docs-tests.yml`. Le gate standard couvre Ruff, mypy ciblé, tests unit/intégration filtrés, couverture et compilation. Les campagnes étendues WP14/documentation/engineering du workflow qualité exigent `workflow_dispatch` et `include_extended_jobs=true`; elles ne sont pas incluses dans le présent résultat. Aucun run GitHub Actions n’a été déclenché.

Le workflow Pages retenu n’a pas de trigger PR. Un push `main` sur les chemins documentaires construit et téléverse l’artefact Pages; le job de déploiement est conditionné à un `workflow_dispatch` avec `deploy_public_site=true` et l’environnement `github-pages`. Aucune approbation d’environnement distante n’a été vérifiée. Aucun déploiement ne s’est produit. Le scénario automatique de fusion ne lance pas le job `deploy` selon le YAML retenu.

Aucun build de package, installation, calcul FEM, campagne WP12, reservation, modification de ledger, CI complète, push, PR, merge, tag ou publication n’a eu lieu. L’ancienne note `QF_0212_MINIMAL_MAIN_INTEGRATION.md`, préexistante et non suivie, n’a pas été modifiée ni incluse.

## Conclusion

La branche locale contient effectivement les changements nécessaires au périmètre public sélectionné de la 0.2.12, y compris tout le code `src/` de la candidate, les corrections modales, les interfaces/configurations retenues et un ensemble de tests ordinaires non FEM. Les 52 chemins de confidentialité et les infrastructures de campagne associées sont absents de la branche. Les preuves originales restent liées à leur commit public exact; aucun archivage privé séparé n’est revendiqué.

**`PUBLIC_INTEGRATION_READY_FOR_CI`** signifie ici que le prochain contrôle CI peut être demandé sur ce commit local après autorisation distincte de transfert/ouverture de PR. Cela ne signifie ni CI verte, ni conformité G03, ni qualification complète, ni disponibilité de toutes les campagnes contrôlées, ni autorisation de fusion ou de release.

Statuts maintenus : `G03 = FAIL_PRESERVED`; `LEGAL_REVIEW = NOT_ACQUIRED`; `RELEASE = BLOCKED`; `AQ09 = AQ09_CLOSED_SCIENTIFIC_BOUNDED_WITH_DEVIATIONS`.
