# WP12 closed — consolidation de branche et transmission à WP13

**Statut :** `WP12_CLOSED_AND_RELEASE_BRANCH_READY_FOR_WP13`<br>
**Projet :** QF Solver v0.2.12 alpha<br>
**Branche release :** `emptiesvoids-cloud/0.2.12`<br>
**HEAD distant revalidé au début de l’audit :** `24885ae7eec606c473328bece5be3310779e55a5` (PR #112)<br>
**Dossier de clôture global :** [PR documentaire #113](https://github.com/emptiesvoid-cloud/QF_solver/pull/113).

La publication v0.2.12 n’est pas autorisée. WP13 reste `OPEN`.

## 1. Clôture Owner et capacités

L’Owner a approuvé `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA` le 2026-10-31. La décision est archivée dans [WP12_GLOBAL_OWNER_BOUNDED_CLOSURE_DECISION_20261031.md](../WP12_GLOBAL_OWNER_BOUNDED_CLOSURE_DECISION_20261031.md) et consolidée dans [WP12-F](WP12F_FINAL_VV_CONSOLIDATION_AND_GLOBAL_DECISION.md).

La matrice reste à **62 capacités : 17 MUST, 39 SHOULD et 6 DEFERRED**. L’Owner accepte la disposition des 17 MUST (11 WP12-A, 6 WP12-B), sans les convertir en 17 PASS. Le CSV de la matrice n’a pas été modifié; son SHA-256 à la base vérifiée est `9E2EE230CBCF308C1E809426C1BA46EFAB42CB546875C3C2F17E95E19CAE8041` et celui du rapport d’audit Markdown est `2E5DFC1A41521DAD5762834E78FB572BED455F326CD9AFEC5107257BC7F00B63`.

Les statuts consolidés restent : TET4-L3 FAIL énergétique `0.0615360686 > 0.05`, aucun `CONVERGENCE_PASS`; deux FAIL HEX8-SRI et validation globale post-correction non acquise; HEX20 R4 FAIL et FEM QUAD8 post-correction `NOT_ACQUIRED`; C01 `CLOSED_NEGATIVE` avec remédiation ouverte; C02/D02 `CLOSED_BOUNDED`; D01 `INCONCLUSIVE`, C4 `NOT_ACQUIRED`; E01 `OPEN_WITH_BOUNDED_CERTIFICATES`; WP12-U contradictoire; aucun replay scientifique homogène sur le HEAD release. La clôture n’ajoute aucune qualification générale.

### Rapprochement des décisions et preuves D01/E01

La décision WP12-A et la matrice intégrée conservent D01 `INCONCLUSIVE` et D01-C4 `NOT_ACQUIRED` ([décision Owner WP12-A](../WP12A_OWNER_BOUNDED_CLOSURE_DECISION_20261029.md), blob `0cd2f225…`; [disposition WP12-A P0](../WP12A_P0_RELEASE_DISPOSITION_DECISION.md), blob `183c2cbe…`). Le rapport ultérieur d’intégration de la projection stable indique que le code a été intégré (`D01_STABLE_PROJECTION_MERGED`), tout en maintenant `WP_D01_STATUS=INCONCLUSIVE`, `C4=NOT_ACQUIRED`, `WP05_FEM_QUALIFICATION=NOT_EVALUATED` et `NEW_FEM_RUN=NOT_RUN` (blob `0f34db83…`). Il ne s’agit donc pas d’une qualification. Le [rapport de réconciliation Git D01](../wp_d01_git_reconciliation_report.md), qui disait que le merge sûr n’avait pas été réalisé, est conservé comme photographie antérieure à cette intégration; son historique n’a pas été réécrit. Les M1/M2 restent sans opérandes archivées suffisantes et aucun statut de qualification n’est promu.

Pour E01, la décision BC B intégrée demeure `OPEN_WITH_BOUNDED_CERTIFICATES`; les capacités retenues restent expérimentales et E01 n’est pas un gate autonome de publication ([rapport d’intégration BC](../wp_e01_bc_integration_report.md), blob `ac605350…`; [roadmap Owner originale conservée](../owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md), blob `3a887d04…`). La source Owner plus ancienne `OPEN — EXPERIMENTAL_TARGET` et le snapshot pré-BC restent des archives historiques, remplacées pour le statut opérationnel par le rapport BC, sans effacer leurs formulations antérieures. La qualification générale reste `NOT_ACQUIRED`, l’équilibre d’assemblage global `NOT_VERIFIED`, le FAIL global BA et le tangent J2 non résolu sont conservés. Le cas synthétique C4 d’E01 est distinct de D01-C4.

## 2. Contrôle de la release et des PR

La branche distante `origin/emptiesvoids-cloud/0.2.12` était exactement au HEAD `24885ae7eec606c473328bece5be3310779e55a5` après rafraîchissement. Le worktree de revue `E:\QFSolverAgents\wp12-global-closeout` était propre et basé sur ce HEAD. Aucun travail n’a été fait dans l’ancien checkout release local, qui est sale et 227 commits derrière le distant.

| PR | Résultat | Décision |
|---|---|---|
| #110 — VV3D | Fusionnée au `ee50684d3c146102b773f604e1625ba8c07348ca` | Clôture bornée VV3D conservée; TET4-L3 FAIL inchangé. |
| #111 — WP12-B | Fusionnée au `09f0810a39f9712044450c527d7613518d6bcea6` | Six MUST WP12-B acceptés dans leur périmètre. |
| #112 — WP12-F | Fusionnée au `24885ae7eec606c473328bece5be3310779e55a5` | Base documentaire de la décision globale. |
| [#70 — ancienne désignation du contrôleur HEX8-SRI](https://github.com/emptiesvoid-cloud/QF_solver/pull/70) | Fermée sans merge le 2026-10-31 | Supplantée : sa branche `a813c7b592939a1f25635c48c37ce79efae40d03` repointait `AGENTS.md` et son assertion vers le contrôleur historique `0d91fc5`; la release désigne `cda19da911217e2f302c295b380332d0fe34b95b`. Branche conservée pour audit. |
| [#113 — clôture globale WP12 et transmission WP13](https://github.com/emptiesvoid-cloud/QF_solver/pull/113) | PR documentaire ciblée sur `emptiesvoids-cloud/0.2.12` | Archive la décision Owner, les statuts, l’inventaire et le backlog WP13; aucun changement scientifique. |

À l’instantané de l’audit initial après fermeture de #70, l’inventaire GitHub contenait 111 PR : 106 `MERGED`, 5 `CLOSED` et 0 `OPEN`. Aucune PR de correctif indispensable à WP12 n’était en attente. L’intégration documentaire de clôture est portée par la PR #113; aucune PR de correctif scientifique n’a été intégrée.

## 3. Inventaire Git, divergences et worktrees

L’inventaire des références locales et de suivi distant, de leurs HEADs, du nombre de commits ahead/behind, de leur état d’ascendance, des associations PR et des worktrees est dans [WP12_BRANCH_INVENTORY_20261031.csv](WP12_BRANCH_INVENTORY_20261031.csv). Les 83 HEADs divergents distincts ont une annexe détaillée dans [WP12_DIVERGENT_HEADS_20261031.csv](WP12_DIVERGENT_HEADS_20261031.csv), avec merge-base, commits propres, listes exactes de chemins modifiés depuis le merge-base et par rapport à l’arbre release, identité d’arbre, worktrees et PR associées. Les références ont été rafraîchies sans force-push ni réécriture.

| Mesure | Résultat à l’audit |
|---|---:|
| Références locales | 127 |
| Références de suivi `origin/*` | 74 |
| Branches distantes vivantes (`git ls-remote --heads`) | 50 |
| Références de suivi devenues stale | 24; gardées, sans prune |
| Worktrees inscrits | 157 : 117 attachés à une branche, 40 détachés |
| Worktrees propres / sales | 145 / 12 |
| Références (noms) ancêtres ou égales au HEAD release | 71 |
| Références divergentes | 130, correspondant à 83 HEADs distincts |
| Commits propres aux 83 HEADs divergents (union) | 219 |
| Catégories des 201 références conservées (une disposition par référence) | `ARCHIVE_KEEP`: 173; `OBSOLETE_REVIEW`: 28 |

La divergence n’a pas été assimilée à un changement manquant. Les variantes issues de bases anciennes transportent de nombreux commits et fichiers historiques. Dix groupes de HEADs distincts ont des arbres finaux identiques malgré des SHA différents; exemples vérifiés : `24885ae` et `a05d621` (arbre `32f669b`), `0a2e813` et `bf8732c` (arbre WP07 `76ac5a92`), `ad6e980` et `ac0f185` (arbre VV3D R2 `39bf88be`). La comparaison exhaustive du contenu final est incluse dans l’annexe; une comparaison générale par patch-id/cherry-pick n’a pas été effectuée, les décisions d’équivalence étant limitées aux identités d’arbre et aux blobs précis cités ci-dessous. La branche `research/hex8-sri-equilibrium` à `5304e3f00e73a916d1af4c1d75375a9b051f0524` reste explicitement liée à ses preuves négatives et à sa campagne bloquée.

Les worktrees sales et leurs modifications préexistantes ont été laissés intacts. Aucun contrôleur, ledger, manifeste, résultat FEM ou archive scientifique n’a été supprimé ou réécrit.

## 4. Classification des branches et changements absents

| Catégorie | Conclusion auditée |
|---|---|
| `MERGED_SAFE_TO_DELETE` | Quatre références **locales seulement** ont été retirées après vérification, toutes ancestrales de la release, non attachées à un worktree, sans branche distante vivante ni PR ouverte. Leurs commits restent atteignables depuis la release et sont détaillés ci-dessous. Aucune autre référence conservée ne satisfait le contrôle de dépendance, de worktree et de preuve pour suppression automatique. |
| `PATCH_EQUIVALENT` | `fix/wp12-wp07-serialization` (`0a2e8135a9d4b6d80abf41dbdd9bf2aefa1cafd6`) : ses deux changements attendus, `src/solveur/core/results.py` et `tests/unit/test_result_serialization_contracts.py`, ont les mêmes blobs sur la release (`2c46b31…` et `596720f…`). Pas de correctif en double. La validation runtime v0.2.12 reste `WP13_REQUIRED`. |
| `INTEGRATE_REQUIRED` | Aucun changement fonctionnel indispensable à un MUST restant n’a été identifié dans les branches examinées. La décision Owner accepte explicitement les limites `NOT_ACQUIRED` et l’absence de replay release. |
| `ARCHIVE_KEEP` / `OBSOLETE_REVIEW` | Toutes les 201 références recensées ont une disposition dans le CSV : 173 gardées pour leur worktree, leur rôle ou leur source de preuve; 28 conservées en revue, notamment les refs `origin/*` périmées et des historiques divergents non encore purgés de dépendances. |
| `WP13_REQUIRED` | Validation runtime WP07, API/compatibilité, régressions/CI du candidat, installation et packaging, docs publiques, confidentialité/distribution et préparation de publication sont hors du périmètre WP12. |
| `DEFER_TO_0_3_0` | Qualification post-correction HEX8-SRI et HEX20 QUAD8; extensions adaptatives VV3D ou analyses non nécessaires à la portée bornée. Aucun nouvel FEM n’est demandé pour v0.2.12. |
| `ARCHIVE_KEEP` | Branches sources et historiques qui portent des preuves, états de campagne, ledgers, politiques ou worktrees encore utiles : `research/hex8-sri-equilibrium`, `experiment/wp12-tet4-convergence`, `test/wp12-fem-regressions`, `verify/wp12-elements-loads`, `fix/wp12-wp07-serialization`, les sources VV3D R1/R2/adaptative et HEX20, ainsi que les branches dynamiques/rotor référencées par leurs rapports et la politique. |
| `OBSOLETE_REVIEW` | Branche de l’ancienne désignation du contrôleur #70, HEAD `a813c7b592939a1f25635c48c37ce79efae40d03`: PR fermée, référence conservée et aucune suppression car un worktree y est encore attaché. |

Quatre branches locales intégrées ont été supprimées avec `git branch -d` après contrôle individuel. Aucun branchement divergent, aucune branche distante GitHub et aucune référence stale seule n’a été supprimée :

| Branche locale supprimée | HEAD conservé par la release | Justification |
|---|---|---|
| `codex/hex8sri-convergence24-canonical-58c8` | `58c8e989b543d638581052a566b8013c93a68e5a` | Merge PR #27, ancêtre de la release; aucun worktree ou PR actif. |
| `codex/hex8sri-freeze-execution-separation` | `ea99be8b99519a9cbe609612e9560e10beb38d95` | Merge PR #30, ancêtre de la release; aucun worktree ou PR actif. |
| `codex/wp12-shared-controller-switch-081d788` | `f8086be271d3cb26a5a7a620f0a59aec9ea4539c` | Merge PR #49, ancêtre de la release; aucun worktree ou PR actif. |
| `fix/wp12a-ledger-mandate-recovery` | `35203c31dd8238c59c67fc9e93320d9ac0730ec7` | Correctif PR #53, ancêtre de la release; rapport et commit restent accessibles. |

La branche locale `codex/wp12-policy-reconciliation` conserve deux commits absents (`71ca96dcc7302b08d332bd667e54948f10f3191f`, `aecddc6277a52789f2f3b34642393db344d87460`). Ils modifient le contrôleur et la politique pour des scopes exacts de diagnostic/éléments, mais ne sont ni un patch démontré nécessaire aux 17 MUST acceptés, ni une correction de release à intégrer après clôture. La branche reste conservée pour audit et report, sans suppression ni merge. Le classement `ARCHIVE_KEEP` de ses références est distinct de la décision de ne pas promouvoir ces travaux dans la 0.2.12.

Vingt-quatre références `origin/*` sont absentes des têtes GitHub actuelles. Vingt-trois ont une autre référence locale contenant le commit; `origin/emptiesvoids-cloud/wp12-dynamics-selective-integration` à `945d4351e2537334d8c9001afe64aeab4fa5a5eb` reste la seule référence locale de ce commit. Toutes ont été conservées; aucun `fetch --prune` n’a été exécuté.

## 5. Backlog obligatoire WP13 — non exécuté ici

1. Synchronisation de toutes les versions v0.2.12.
2. API et compatibilité.
3. Validation runtime de la sérialisation WP07; les deux blobs correctifs existent déjà sur la release.
4. Régressions et CI du candidat.
5. Installation propre, wheel et sdist.
6. Dépendances et packaging.
7. Audits de confidentialité et du canal de distribution sélectionné.
8. Changelog, README, documentation technique, limitations et notes de version.
9. Synchronisation du site public.
10. Préparation PyPI, GitHub Release et Zenodo.
11. Autorisations finales et publication.

Ce backlog n’est pas un nouveau travail WP12 et n’a pas été exécuté dans cette clôture.

## 6. Contrôles finaux et risques

- Branche release distante revalidée au HEAD indiqué ci-dessus avant création de cette PR; le worktree de revue était propre.
- Aucune branche contenant une disposition MUST acceptée n’a été intégrée en retard; aucune preuve source n’a été perdue.
- La matrice 62 capacités conserve ses dispositions et son CSV n’a pas été modifié.
- Aucune campagne, FEM, benchmark, retry, changement de code scientifique, seuil ou ledger n’a été exécuté ou modifié.
- Les 24 références distantes stale et la branche WP12 policy divergente restent préservées pour les preuves ou audits qu’elles peuvent porter.
- Risques scientifiques acceptés : absence de replay homogène release, FAIL TET4-L3, deux FAIL HEX8-SRI, HEX20 R4 FAIL, validation post-correction non acquise, C01 remediation open, D01 inconclusive, E01 open et registres WP12-U non concordants.
- Le checkout local historique release demeure sale et désynchronisé; le worktree propre d’audit a servi de référence. Ne pas confondre son HEAD local avec le HEAD distant.

**Conclusion :** les dispositions Owner clôturent WP12 dans la portée bornée alpha. La PR #113 porte l’intégration documentaire de cette décision et la transmission WP13. Après son intégration et le contrôle du HEAD release, la branche est prête pour la suite WP13. Aucune publication v0.2.12, création de tag, bascule vers `main` ou clôture de WP13 n’est autorisée par ce rapport.
