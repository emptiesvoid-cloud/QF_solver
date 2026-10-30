# WP-C02-MERGE — Rapport d’intégration bornée

Date : 2026-10-23
Branche cible : `codex/v0.2.12-integration`
Verdict de branche : `WP_C02_INTEGRATION=MERGED_VERIFIED`

## Portée et décision

La clôture Owner N13 est intégrée uniquement pour le benchmark WP-C02-AR et
les critères prospectifs N03. Le statut scientifique demeure
`WP_C02_STATUS=CLOSED_BOUNDED` pour ce périmètre exact. Cette intégration ne
revendique aucune qualification générale du contact, aucune équivalence Docker,
aucune convergence asymptotique, ni disponibilité de release.

Les statuts conservés sont :

| Statut | Valeur |
|---|---|
| `WP_C02_STATUS` | `CLOSED_BOUNDED`, WP-C02-AR/N03 uniquement |
| `ACTIVE_FRONT_M2_M5` | `PASS_BOUNDED` |
| `N10_M4` / `N10_M5` | `PASS` / `PASS` |
| `GENERAL_CONTACT_QUALIFICATION` | `NOT_ACQUIRED` |
| `DOCKER_EQUIVALENCE` | `NOT_ACQUIRED` |
| Convergence asymptotique | Non démontrée et non revendiquée |
| N06/N08 | `FAIL` historiques conservés |
| Campagnes Docker | `FAIL_CLOSED` historiques conservés |

La marge du front reste nulle à `1 hx` sur les niveaux qui atteignent le
plafond. Le sens limité des brackets et les autres limites N12/N13 restent
divulgués. Aucun critère scientifique, seuil ou résultat n’a été recalculé ou
modifié pendant cette intégration.

## Identités source et cible

| Élément | Commit | Tree |
|---|---|---|
| Source Owner N13 | `976d2ecc7cce810889ae0568794cdd03b018a6c2` | `e00430895a72a8bc08eb32759390297dade5810b` |
| Décision N13 SHA-256 | `45DA7FC9CA96AD0C8210B4620302D2E74416A327B6787E124D9836ED0EF41E51` | — |
| Cible avant M-ERGE | `e906c97e065d92ec92935d0d7653e8086c941573` | `95d8ddd8e250df4edc6c3b21d1fbf1eb9c7413a4` |
| Merge-base source/cible | `1d7fef04094d2f4b920795b4b3c25f052fcf21c0` | — |

Le worktree cible était propre avant intégration. Il contenait déjà les
commits de WP-D02, WP-E01 et WP11. La branche source comptait 176 commits et
628 chemins absents de la cible; son diff complet introduisait 42 chemins
`src/solveur`, dont des prototypes de contact/assemblage FEM et des
modifications de solveurs non linéaires. Une fusion intégrale aurait donc
élargi le mandat et importé des travaux C01/GF, des campagnes Docker et des
travaux d’autres lots.

## Stratégie et inventaire Git

La stratégie est une sélection explicite de la chaîne N03→N13. Les six
commits sources suivants sont ancêtres directs successifs de N13 et ont été
cherry-pickés avec leurs auteurs d’origine et une référence `-x` :

| Commit source | Commit intégré | Objet |
|---|---|---|
| `3090742929527613ed07a0d2fdd3aa0096d901d1` | `541c13b04f9211638ec6d59d6ad98ee00da02ece` | Gel du contrat N03, scripts, tests et approbation prospective |
| `a0e0359f6cd4423e966a64ffde82bbad4dd20831` | `7a20f7c130a944c000fa2ca576e6c0518d7f35cc` | Collecte et rapport natifs N05 |
| `d517ddc53a871e3032ac82d2712076693e45220b` | `707bdd9aaf9f6a1736a9c917087074b15e80fb1e` | Conventions de contact et post-traitement N07 |
| `2ccd669cad8ba51baea475c4cb838b8c06426f4b` | `4c543b3a60e3d697863785917874c1aab0ed473f` | Stationnarité et énergie N09 |
| `244023a6b084597a333e39be20af9904b42b976f` | `33294d23620ac8fec02b5e55be8d354422e9970e` | Reconstruction historique du front N11 |
| `976d2ecc7cce810889ae0568794cdd03b018a6c2` | `fe8c8a8c2cb624d9c44a6d3e1285bdb0ade5de40` | Matrice, revue, évaluation et décision Owner N12/N13 |

Deux sources scientifiques préexistantes nécessaires à la vérification du
contrat N03 ont été reprises byte pour byte depuis le gel source :
`qualification/0_2_12/wp_c02_ar_mesh_plan.json` (SHA-256
`fa3806c842acefbe707499ffdec9f703bcedb5031962594df4c5293d0fbe6cfc`) et
`qualification/0_2_12/wp_c02_ar_spatial_convergence_protocol_report.md`
(SHA-256 `bf7535eb4028715071744a2b8cc119b828f0eae2129a8f6b05e588872fcbf58d`).
L’approbation N03 continue de vérifier ces empreintes. Leur commit d’origine
est `9023eeb32bc405b084a68b741cafc9195e762917`.

Les commits d’intégration complémentaires sont :

- `938668c16bc4d8b7a99616bd8af9904adf7f2136` : inclusion des deux sources de
  contrat exactes ci-dessus.
- `9e1cf9805b49c90a74006a39cb0ded640265f64f` : adaptation des tests de
  provenance aux snapshots archivés externes.
- `f2b0dbd727dd5ee1e82e97d33e63ad0347c5a6ec` et
  `2eff6b5ee2b4836591228b58ad617c5ee7865c74` : traitement explicite des
  fixtures et archives AJ/N04 externes, sans ajouter le solveur expérimental
  AJ à cette branche.

Le conflit de cherry-pick N13 sur
`wp_c02_unified_contact_vnv_report.md` était un conflit `modify/delete` : le
fichier n’existait pas sur la cible. La version présente dans l’arbre N13 a été
comparée au blob source (`e3ab747769afd677f4aefcf05c7513ac7ab4f9de`) puis
réintroduite sans modification de contenu. Aucun autre conflit n’a été
rencontré.

Les 170 autres commits source-only ont été exclus. Les prototypes et
modifications `src/solveur`, les travaux C01/GF et les campagnes Docker ne
sont pas importés. Aucun chemin `src/solveur` n’est modifié par le diff net
M-ERGE. Les sources N10 et critères N03 restent liées à leurs identités
historiques, non au nouveau HEAD d’intégration.

## Fichiers intégrés

Le diff net depuis la cible initiale couvre uniquement les groupes suivants :

- **Contrats et rapports C02** : protocole/plan AR, baseline historique,
  preuves de provenance N01, approbation N03, diagnostics/revues N07 et N09,
  reconstruction/revue N11, matrice/évaluation/revue N12, décision N13 et
  rapport unifié.
- **Archives versionnées** : archive de reconstruction front N11 (8 fichiers)
  et diagnostics hors ligne N07/N09 déjà commités à la source. L’archive N10,
  ses résultats et son manifeste ne sont pas copiés dans Git.
- **Scripts** : gel du manifeste, runner, collecte et rapport natifs, diagnostic
  hors ligne N09.
- **Tests** : contrats du manifeste, collecte/rapport et test de convergence
  N03. Les tests qui exigent l’archive N04 ou le snapshot source N10 utilisent
  des chemins explicites; ils SKIP si une preuve externe n’est pas fournie.
- **Documentation d’intégration** : cette feuille de route, la présente matrice
  C02 et le présent rapport.

Inventaire exact du diff net depuis le HEAD cible initial
`e906c97e065d92ec92935d0d7653e8086c941573` (ajouts, sauf mention M) :

```text
qualification/0_2_12/provenance/wp_c02_ar_native_preparation_report_as_reviewed.md
qualification/0_2_12/wp_c02_ar_mesh_plan.json
qualification/0_2_12/wp_c02_ar_native_historical_baseline.json
qualification/0_2_12/wp_c02_ar_spatial_convergence_protocol_report.md
qualification/0_2_12/wp_c02_n01_provenance_remediation_report.md
qualification/0_2_12/wp_c02_n03_ar_prospective_criteria_approval.json
qualification/0_2_12/wp_c02_n07_contact_sign_convention_audit.md
qualification/0_2_12/wp_c02_n07_independent_review.md
qualification/0_2_12/wp_c02_n07_offline_diagnostic_report.md
qualification/0_2_12/wp_c02_n09_force_stationarity_energy_audit.md
qualification/0_2_12/wp_c02_n09_independent_review.md
qualification/0_2_12/wp_c02_n09_offline_diagnostic.md
qualification/0_2_12/wp_c02_n11_historical_front_evidence_audit.md
qualification/0_2_12/wp_c02_n11_independent_review.md
qualification/0_2_12/wp_c02_n11_m2m3_front_analysis.md
qualification/0_2_12/wp_c02_n12_closure_requirements_matrix.md
qualification/0_2_12/wp_c02_n12_independent_review.md
qualification/0_2_12/wp_c02_n12_scientific_qualification_assessment.md
qualification/0_2_12/wp_c02_n13_owner_bounded_closure_decision.md
qualification/0_2_12/wp_c02_unified_contact_vnv_report.md
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_collection_receipt.json
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_execution_manifest.json
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_frozen_test_source.py
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_run_receipt.json
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_stderr.log
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_stdout.log
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/aq_worker_run_result.json
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/archive_integrity_manifest.json
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/archive_integrity_manifest.sha256
qualification/0_2_12/wpc02_ar_front_n11_reconstruction_20261023_01/m2_m3_front_reconstruction.json
qualification/0_2_12/wpc02_n07_offline_diagnostics/m4_offline_diagnostics.json
qualification/0_2_12/wpc02_n07_offline_diagnostics/m5_offline_diagnostics.json
qualification/0_2_12/wpc02_n07_offline_diagnostics/offline_diagnostic_summary.json
qualification/0_2_12/wpc02_n09_offline_diagnostic.json
scripts/diagnose_wpc02_n08_force_energy_offline.py
scripts/freeze_wpc02_ar_native_manifest.py
scripts/report_wpc02_ar_native.py
scripts/run_wpc02_ar_native_pytest.py
scripts/wpc02_ar_native_collection.py
tests/unit/test_wpc02_ar_native_collection_reporting.py
tests/unit/test_wpc02_ar_native_manifest_contract.py
tests/verification/test_wpc02_ar_native_contact_convergence.py
qualification/0_2_12/ROADMAP.md [modifié pour l’état d’intégration/roadmap]
qualification/0_2_12/wp_c02_integration_merge_report.md [nouveau rapport]
```

Ce diff ne contient aucun changement de code du solveur ni de dépendance.

## Preuves N10/N11 et dépendances

Les résultats N10 restent dans le worktree source externe :
`<legacy-worktree>\.codex-worktrees\wp-c02-n09-remediation\qualification\0_2_12\wpc02_ar_native_campaign_n10_20261023_01`.
Ils ne sont pas inclus dans le commit d’intégration; ce chemin local n’est pas
portable vers un autre hôte.

Contrôles d’intégrité N10 effectués en lecture seule :

- Manifest d’exécution externe SHA-256 :
  `c6573776cb9811800e1fa242f6d9ad8a1acc0901d43bc6f81e0fc416b9d26c0e`.
- Manifest d’intégrité SHA-256 :
  `baa8822c7c078f89d1219445a034f579757eaf394ae4bde935b7a9bca7de74cc`;
  539/539 fichiers et tailles correspondent.
- Rapport scientifique N10 SHA-256 :
  `7a3e37396368c17f66c0c2b873d977229ca7556e720bd2eea998f96b8f2fdf2a`.
- N11 est intégré avec son manifeste de reconstruction 8/8; SHA-256 du
  manifeste d’intégrité :
  `864e108661eee3d4d9365d2d5798f85baa3f94048c8c039c771a1ca5bf442e80`.

Versions pendant les tests ciblés : Python 3.13.1, pytest 8.4.1, NumPy 2.2.6,
SciPy 1.15.2, threadpoolctl 3.6.0 et psutil 7.2.2. Aucun fichier de
dépendances n’a été modifié. `pyproject.toml` de la branche cible contient un
marqueur pytest WP11 absent du gel source; son hash n’est donc pas remplacé ni
réécrit. La vérification du manifeste N10 compare les 530 sources au snapshot
externe exact, et non au contenu administratif/intégratif courant.

## Tests et contrôles

Commande exécutée dans le worktree d’intégration avec ces chemins externes :

- `WPC02_AR_NATIVE_MANIFEST_PATH=<legacy-worktree>\.codex-worktrees\wp-c02-n09-remediation\qualification\0_2_12\wp_c02_ar_native_n09_execution_manifest.json`
- `WPC02_AR_NATIVE_SOURCE_ROOT=<legacy-worktree>\.codex-worktrees\wp-c02-n09-remediation\qualification\0_2_12\wpc02_ar_native_campaign_n10_20261023_01\snapshot`
- `WPC02_AR_N04_ARCHIVE_PATH=<legacy-worktree>\.codex-worktrees\wp-c02-n01-remediation\qualification\0_2_12\wpc02_ar_native_campaign_n03_20261023_01`

```text
python -m pytest tests/unit/test_wpc02_ar_native_manifest_contract.py tests/unit/test_wpc02_ar_native_collection_reporting.py -q
```

Résultat : **61 passed, 1 skipped**. Les assertions vérifient les empreintes
N03, le manifeste externe, les helpers de collecte/rapport et les deux gardes
M4/M5 sans token Owner et avec un hash de manifeste incorrect. Certaines
fixtures vérifient aussi des opérations vectorielles et énergétiques
synthétiques; elles ne constituent pas une validation FEM. Le test sauté
utilise l’aide de front AJ, qui dépend d’un module de solveur
expérimental non intégré; le skip est explicite et n’est pas compté comme
PASS. Le contrôle d’intégrité N04 est passé avec le chemin d’archive externe
explicite; les chemins de ces archives restent propres à cet hôte. Aucun
nodeid M4/M5, aucun solveur FEM, assemblage FEM, calcul Docker ou campagne
qualifiante n’a été exécuté.

`git diff --check` ne relève aucun problème dans les modifications
d’intégration; il signale uniquement la ligne vide finale du fichier de
protocole N03 préservé. Elle était déjà présente dans le blob gelé et reste
inchangée pour préserver la SHA-256 approuvée.

## Revue indépendante

La première revue indépendante a conclu `NO-GO` pour une fusion complète,
compte tenu des 176 commits/628 chemins source-only et des changements
scientifiques hors C02. La présente sélection évite cet élargissement.

Revue indépendante finale du diff sélectif : favorable à l’intégration sur
cette branche uniquement. L’auditeur indépendant a examiné le snapshot
`2eff6b5ee2b4836591228b58ad617c5ee7865c74` / tree
`f35588bfe3e915192e392ff00a02d709f3527ecd` ainsi que les notes documentaires
en attente. Finding initial : 1 P2 de traçabilité sur un doublon/omission dans
l’inventaire; après correction, **0 P0, 0 P1 et 0 P2 ouverts**. L’inventaire
final a été comparé aux changements Git et contient 44 chemins uniques. La
revue ne valide ni `main`, ni une publication, ni un RUN scientifique. Aucune
commande de test, FEM ou Docker n’a été lancée par l’auditeur.

## Roadmap, limites et état Git

L’overlay de roadmap indique 19 lots, 13 clôtures positives, 1 négative et 5
ouverts, soit 68,4 %. C03 est hors du dénominateur; les états
`CLOSED_BOUNDED` comptent comme clôtures positives dans ce seul indicateur
opérationnel. Ce ratio n’est ni une métrique de maturité scientifique ni une
décision de release. La roadmap Owner fournie reste inchangée.

La branche `codex/v0.2.12-integration` est la seule cible modifiée. Aucun merge
vers `main`, aucune publication et aucun nouveau RUN FEM/Docker n’ont été
effectués. Le statut d’intégration autoritative vers `main` reste en attente.
L’identité Git finale est portée par le commit qui ajoute ce rapport et les
notes de roadmap; elle est fournie avec le résultat de la tâche.
