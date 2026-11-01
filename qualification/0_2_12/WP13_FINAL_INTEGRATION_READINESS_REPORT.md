# WP13 — rapport final de préparation à l’intégration

- Dépôt : `emptiesvoid-cloud/QF_solver`
- PR : [#114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
- Branche source examinée : `codex/wp13-release-engineering-20261031`
- HEAD source au début de la revue : `e180969645f19fead1564834ad028a55d7e590e0`
- HEAD PR validé par le contrôle GitHub #41347863345 : `4d192a6fd9dae26089c67644c2b342cef9708c3b` (rapports WP13 et corrections de whitespace uniquement; ce rapport reçoit ensuite une mise à jour documentaire du résultat CI)
- Branche cible : `emptiesvoids-cloud/0.2.12`
- HEAD cible vérifié sur GitHub : `ab137051d920d7fa9aae9a3012a48b2b26e2198b`
- Contrat package v7 : `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43`

## Synthèse de la décision

L’intégration de code dans la branche de candidate 0.2.12 est distincte de la validation d’une candidate, de la publication des packages et de la publication d’un export Git complet. La sélection package v7 reste identique, les six smoke tests autorisés ont passé leurs oracles dans leur portée, et les gates de publication G03 et revue juridique restent ouverts sans être reclassés.

À l’instantané initial `e180969`, la PR était ouverte et GitHub indiquait `mergeable=true`, mais `mergeStateStatus=UNSTABLE` à cause d’un contrôle WP12 qui échouait uniquement sur `git diff --check` pour des espaces de fin dans cinq rapports. Les 12 lignes signalées ont été corrigées. Après push des rapports, le contrôle GitHub #41347863345 sur `4d192a6` a terminé `SUCCESS` en 2 min 9 s, y compris Ruff, compilation, JSON, whitespace et contrats synthétiques. GitHub indique maintenant `mergeable=true` et `mergeStateStatus=CLEAN`. Un contrôle distinct des contenus ajoutés a aussi trouvé des chemins absolus de poste de travail dans deux anciens fichiers WP13 hash-bound; ils restent dans l’historique de la PR et ne sont pas modifiés ici.

**Verdict : `WP13_MERGE_BLOCKED`** — les chemins privés présents dans le diff PR ne sont pas une simple réserve de publication, et leur retrait du tip ne purgerait pas les commits existants. Aucune fusion n’est effectuée.

## Références et intégrité des branches

| Contrôle | Résultat | Preuve |
|---|---|---|
| PR source | OPEN | Snapshot vérifié par CI : HEAD `4d192a6fd9dae26089c67644c2b342cef9708c3b`, base `ab137051d920d7fa9aae9a3012a48b2b26e2198b`; le code audité est celui de `e180969`, puis seuls les rapports et la mise en forme ont changé. |
| HEAD destination | PASS | Référence distante et API GitHub concordent sur `ab137051d920d7fa9aae9a3012a48b2b26e2198b`. Aucun commit ni fichier de la branche cible n’a été modifié. |
| Ancestry | PASS | Le merge-base source/destination est le HEAD cible; la source descend directement de la destination. |
| Simulation de fusion | PASS sans conflit | `git merge-tree --write-tree` sur le snapshot source `e180969` a produit l’arbre `b7f4fd8550c93b4bea5220ed12623461a475aadd`, identique à l’arbre source. Les commits ultérieurs sont seulement des rapports; la branche cible demeure l’ancêtre direct et inchangé. L’opération n’a pas créé de commit ni touché de branche. |
| Worktree source avant corrections documentaires | PASS | HEAD propre `e180969`; le diff de préparation ajoute uniquement les rapports et corrige la mise en forme des rapports WP13 existants. |

Le commit de rapport et les corrections d’espaces sont documentaires. Ils ne modifient ni le code de calcul, ni le contrat, ni les fichiers sélectionnés du candidat. Le contrôle ciblé sur le HEAD courant a passé; le HEAD à réexaminer après résolution du blocage de confidentialité est `4d192a6fd9dae26089c67644c2b342cef9708c3b`.

## Diagnostic de traçabilité

Le verdict est `EXPECTED_CONTRACT_BEHAVIOR`; voir le [diagnostic détaillé](WP13_TRACEABILITY_DIAGNOSTIC.md). Les scopes TET4 et leurs 6, 6 et 7 formules existent dans les registres du dépôt et passent quand les chemins du dépôt sont disponibles. Les packages installés v7 omettent, comme le prévoit leur sélection, les sources de preuves `docs/` et `tests/` ainsi que les chemins de dépôt `src/solveur/...` référencés par les formules. Les six sorties conservent donc `traceability.status=FAIL`, zéro formule couverte et un résumé d’ingénierie `WARNING`.

Ce statut est conservé. Il concerne la readiness et les métadonnées d’audit, ne change pas les calculs ni les valeurs comparées aux oracles smoke et ne devient pas une qualification globale. Aucun changement de solveur ou nouvelle tentative scientifique n’est effectué.

## Inventaire complet du diff PR #114

Le diff intégral de la base cible vers le HEAD source examiné contient 48 commits, 101 chemins, 40 691 insertions et 244 suppressions. Les principaux groupes sont :

| Groupe | Changements examinés | Conclusion |
|---|---|---|
| README, CHANGELOG, citation, métadonnées package et MkDocs | Porte d’entrée générale, version 0.2.12 candidate, 0.2.11 dernière version publiée, liens officiels et règles de publication documentaire. | Cohérents; aucune annonce de publication, date ou DOI de version v0.2.12. |
| Code produit et interfaces | Seul fichier sous `src/` modifié : `src/solveur/version.py`, version `0.2.12`. | Aucun changement de fonction API/CLI, algorithme, assemblage, oracle ou seuil numérique. Compatibilité historique non modifiée. |
| Workflows | `quality.yml` applique la matrice légère approuvée par l’Owner; un workflow distinct exécute le diagnostic Windows synthétique borné. | Suite de référence Ubuntu/Python 3.13 et nodeids ciblés sur les trois autres cellules; seuils et exclusion des tests scientifiques contrôlés conservés. Jobs étendus non lancés par le dispatch WP13 approuvé. |
| Scripts et contrôleurs | Audits et readiness, diagnostic Windows de chemin absent, sélection de compatibilité et contrôleur package smoke v7. | Changements d’infrastructure contrôlés; contrôleur v7 hash-pinné, déjà utilisé pour les six essais autorisés. |
| Tests | Tests de version candidate, de politique Windows, de contrats WP12/WP13, de packaging et de documentation mis à jour; aucun fichier de test supprimé. | Aucune tolérance ou oracle numérique scientifique n’a été abaissé. Le test du publisher de documentation de contact isole maintenant son câblage avec des campagnes simulées; les campagnes numériques contrôlées restent séparées. Les tests d’audit à scan coûteux utilisent des scanners simulés pour tester la composition du rapport; leurs statuts G03 acquis restent FAIL. |
| Contrats, manifests et rapports WP13 | Snapshots versionnés des contrats de candidat, scans, inventaire de tests, rapports CI, privacy, G03, artefacts et smoke. | Snapshots historiques conservés; aucun ledger ou résultat scientifique WP12 modifié. Le `targeted_release_readiness_initial_failure.log` est un log de vérification, pas un résultat scientifique. |
| Licence et dépendances | Fichiers de licence inchangés; un pin `cryptography==48.0.0` ajouté au baseline standard des tests, utilisé par les tests de signature/attestation WP12. `pyproject.toml` ne change pas les dépendances runtime de base; cryptography est déjà déclarée dans les extras concernés. | L’inventaire technique est conservé. L’avis juridique tiers indépendant reste `NOT_ACQUIRED` et n’est pas prétendu acquis par ce changement de lock CI. |
| Archive et sélection publique | `.gitattributes` exclut du `git archive` quelques chemins internes/générés connus. | Ne purge pas l’historique et ne reclasse pas G03; cette règle seule n’établit pas la publication d’une archive complète sûre. |

### Traces de chemins locaux dans les changements PR

Le contrôle des ajouts a trouvé 14 valeurs de chemins de poste de travail réparties entre [`wp13_candidate_build_run1_failure_20261031_v5.json`](wp13_candidate_build_run1_failure_20261031_v5.json) et [`wp13_p0_package_smoke_manifest_20261031_v1.json`](wp13_p0_package_smoke_manifest_20261031_v1.json). Le second fichier possède un sidecar SHA-256; les deux fichiers sont des preuves historiques de versions antérieures, hors sélection package v7. Les valeurs exactes ne sont pas recopiées dans ce rapport.

Le contrôle `check_privacy_diff.py` passe, mais il ne détecte pas ces racines de poste de travail. Le scan additionnel les a donc signalées séparément. Elles appartiennent aux constats déjà préservés par G03; aucune réécriture historique ni modification des manifests n’est autorisée dans cette revue. Comme ces deux fichiers sont suivis par Git et présents dans les commits de la PR, l’intégration en fast-forward porterait leurs chemins dans l’historique de la branche cible. L’état G03 demeure `FAIL_PRESERVED`.

L’examen des assertions supprimées montre des mises à jour de version/statut vers la candidate, le remplacement d’un test de métadonnées « postpublication » par un contrat prépublication, et des refactorisations de tests de composition/scaffolding. Il n’y a pas de fichier de test supprimé, ni de changement à `qualification/formulas.json`, `qualification/requirements.json`, `qualification/campaign.json`, aux entrées TET4 du smoke ou aux résultats WP12. Les tests scientifiques ne sont pas relancés.

## Candidate v7 et compatibilité des preuves

Le candidat distribué est lié au commit source `7a78cc673da2abb7c3d0afd6cabd378aa327f424`. Une comparaison Git des 585 chemins sélectionnés par le contrat v7 entre ce commit et `e180969` n’a trouvé aucun ajout, retrait ou blob modifié. Les rapports de cette revue sont dans `qualification/0_2_12/`, hors sélection package et hors `docs/`; ils ne changent pas les octets des artefacts v7.

| Élément | Identité vérifiée |
|---|---|
| Wheel | SHA-256 `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518` |
| Sdist normalisée | SHA-256 `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174` |
| Contrat | SHA-256 `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43` |
| Smoke v7 | Six `EXECUTION_PASS`, six `NUMERICAL_ORACLE_PASS`; ledger `62c2c843e3cd5c80a2098efef97ca146a332c9a4375df549542d2593522bb67f`. Aucune nouvelle tentative. |

Les six rapports et leurs limites sont dans [WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md](WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md). Les hashes v7 restent historiques et valides pour leurs octets exacts; ils ne sont pas revendiqués pour des sources différentes.

## Contrôles effectués pour cette revue

| Contrôle | Résultat |
|---|---|
| Traceabilité sans FEM, trois scopes depuis chacun des contextes source et installé wheel/sdist | PASS pour la comparaison diagnostique; statuses installés `FAIL` préservés comme attendu. |
| `test_tet4_scope_has_no_orphan_requirement` | PASS, 1 test. |
| `test_all_controlled_formulas_are_linked_by_requirements` | PASS, 1 test. |
| `test_model_scope_mapping` | PASS, 21 cas de mapping, sans solveur. |
| `test_package_smoke_oracles_and_one_shot_reservation_are_fail_closed` | PASS, test synthétique sans FEM. |
| Contrat métadonnées prépublication candidate | PASS, test ciblé. |
| Composition release-readiness avec scanners synthétiques | PASS, test ciblé. |
| Refus du chemin Windows absent sans boucle | PASS, test ciblé simulé. |
| Ruff sur tous les fichiers Python modifiés par la PR | PASS. |
| Compilation des fichiers Python modifiés | PASS. |
| Parsing JSON des 15 fichiers modifiés et YAML de 3 configurations | PASS. |
| Scan privacy additions du diff | PASS. |
| Scan complémentaire des racines de poste de travail dans les ajouts | FAIL — 14 valeurs dans deux manifests/rapports WP13 historiques; elles ne sont pas dans la sélection v7 et ne sont pas supprimées dans ce mandat. |
| `git diff --check` | PASS localement après correction; confirmé par le contrôle GitHub #41347863345 sur `4d192a6`. |
| MkDocs strict et vérification des liens README | PASS aux contrôles documentaires précédents; aucun contenu `docs/`, README ou métadonnée publique n’a changé après le commit source du candidat v7. |
| Tests complets, matrice CI complète, campagnes FEM/WP12 | NOT_RUN dans cette revue; aucune nécessité démontrée, aucune autorisation de nouvelle campagne. |

Le contrôle de matrice de release approuvé avait déjà passé son unique exécution, run #41328516423. Le contrôle `WP12 controller / synthetic contracts` sur `e180969` (#41346306199) avait échoué à `git diff --check` sur les mêmes espaces finaux; le contrôle suivant, #41347863345 sur `4d192a6`, a réussi toutes les étapes. L’avertissement Actions sur la migration de Node.js et `ubuntu-latest` ne fait pas échouer le job.

## Critères d’intégration et critères réservés à la publication

| Activité | État | Conséquence |
|---|---|---|
| Intégrer le code WP13 à la branche candidate 0.2.12 | `WP13_MERGE_BLOCKED` par les chemins locaux présents dans les fichiers suivis et l’historique source. | La prochaine décision Owner doit traiter explicitement cette exposition avant d’autoriser l’intégration. Le merge ne doit pas créer de tag, release ou publication. |
| Valider la candidate v0.2.12 | PASS uniquement pour la politique CI Owner approuvée, les contrôles package v7, les installations et les six smoke tests bornés. | La traçabilité installée reste FAIL/WARNING; cela ne vaut pas une qualification scientifique globale. Les autres gates restent distincts. |
| Publier wheel ou sdist | Non autorisé; revue juridique indépendante `NOT_ACQUIRED`. | Ne pas téléverser ni annoncer la candidate. L’inventaire technique de licence n’est pas une clearance juridique. |
| Publier un export Git complet / historique public | Bloqué par `G03=FAIL_PRESERVED`. | Les exclusions d’archive ne purgent pas les constats de contenu/historique. Ne pas reclasser G03 ou publier une archive complète. |

G03 et la revue juridique sont maintenus exactement à leur état acquis. La revue ne traite pas automatiquement l’échec global G03 ou l’absence d’avis juridique comme des blocages d’intégration puisqu’ils concernent les publications d’archives/packages. Le blocage ci-dessus est distinct : des chemins de poste de travail sont explicitement présents dans les fichiers suivis de cette PR et dans les commits qu’un fast-forward transférerait.

## Actions laissées à la prochaine décision Owner

1. Décider explicitement du traitement des deux fichiers historiques contenant des chemins locaux et de l’exposition de ces commits. Leur suppression du tip ne modifierait pas l’historique existant; aucune réécriture n’est effectuée ni proposée dans ce mandat.
2. Après décision Owner et levée du blocage d’intégration, examiner le HEAD source final et revalider le HEAD cible avant le merge.
3. Après intégration, mener l’audit approfondi indépendant prévu sur la branche consolidée.
4. Décider séparément des gates nécessaires avant publication, notamment l’avis légal et le traitement de G03.

## Verdict

**`WP13_MERGE_BLOCKED`** par les chemins locaux contenus dans deux fichiers de preuve historiques présents dans la PR. G03 reste aussi `FAIL_PRESERVED` pour les archives complètes; la revue juridique reste `NOT_ACQUIRED` pour la redistribution. Le contrôle GitHub ciblé #41347863345 est vert, mais ne lève pas le blocage de confidentialité/historique. Aucun merge, tag, publication ou déploiement n’a eu lieu.
