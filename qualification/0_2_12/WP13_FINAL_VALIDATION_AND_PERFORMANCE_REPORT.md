# WP13 — Rapport final de validation et de performance

Date de l’audit : 1 novembre 2026
Dépôt : emptiesvoid-cloud/QF_solver
PR : [#114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
Branche de travail : branche WP13 de la PR #114, distincte de la branche release
Branche de release examinée : emptiesvoids-cloud/0.2.12

## Verdict exécutif

**WP13_PARTIAL_OR_BLOCKED**

Les correctifs d’infrastructure autorisés et les diagnostics Windows bornés sont vérifiés. Les preuves v6 d’artefact restent applicables aux fichiers sélectionnés par le contrat de distribution : les changements WP13 ultérieurs concernent les workflows, scripts de diagnostic, tests et rapports internes, sans modifier les blobs distribués. Le correctif de scan source intégré via #118 réduit le travail répété, et le test de câblage documentaire ne lance plus les campagnes FEM.

La politique de quatre suites complètes a été explicitement remplacée par décision Owner le 1 novembre 2026. La nouvelle matrice a passé son unique exécution autorisée (#41328516423) : suite complète Ubuntu/Python 3.13 et 15 nodeids ciblés sur chaque cellule secondaire. Le gate de validation CI est donc PASS selon cette politique, sans transformer l’ancien critère en PASS. WP13 reste néanmoins PARTIAL_OR_BLOCKED : les six smoke tests installés sont toujours PREPARED_NOT_AUTHORIZED, G03 reste FAIL_PRESERVED, l’examen juridique indépendant des licences n’est pas acquis, et les gates scientifiques/distribution distincts restent ouverts.

## 1. État initial vérifié

- Le HEAD initial de la PR, rafraîchi depuis GitHub, était c06a669180d1e5e7545b1a48aa5e904f2f45539d, identique à celui indiqué dans le mandat.
- À l’ouverture de la phase de matrice approuvée, le HEAD de PR #114 était 26d12db7621ba746db10b8588d0c09d759e7e97d, identique à celui fourni par l’Owner. Le workflow corrigé et sa sélection exacte ont été poussés dans 698e858e79d6b6ded7cdf764f5e0dd26c710c301.
- Le commit de finalisation 0538d3d91022793a1ca4a79aa4b972628cb5bc62 a été poussé après l’unique run #41328516423 au commit workflow 698e858e. Les commits de finalisation ajoutent les règles d’archive, le test ciblé et les rapports; ils ne changent pas `quality.yml`, le manifeste de compatibilité, les dépendances ou les tests numériques. Le contrôle ciblé a passé; aucun second dispatch n’a été lancé.
- Le worktree WP13 était propre à 67adffbe3 avant rafraîchissement. Le worktree release et ses modifications locales WP12 n’ont pas été touchés.
- La base de PR #114 est emptiesvoids-cloud/0.2.12, commit ab137051d920d7fa9aae9a3012a48b2b26e2198b.
- Les correctifs des PR #115 et #116 sont présents dans le commit intégré #118, 0a736a47d4e9980020970f30c973c6acca4098c1. Le test de câblage des documents remplace les exécutions FEM par des mocks à la frontière de campagne; la fixture de scan réutilise un audit uniquement quand son identité d’entrée Git et son état de worktree correspondent.
- Les rapports exigés ont été relus : matrice de gates, validation P0, optimisation phase 2, correctif Windows, vérification d’artefacts v6, dossier de décision smoke et optimisation de la suite.
- Le HEAD des correctifs code/CI vérifiés est d4761299fe93a1221eb798e6cd37bc5582538b9d. Les changements poussés sont b481ad96c, 8a8ed9b72 et d4761299f. Le diagnostic du HEAD code/CI a passé sur les deux cellules dans le run #41326063607.

## 2. Correctifs réalisés

1. Le workflow de diagnostic Windows vérifie maintenant le même ensemble borné sur Python 3.10 et 3.13. La garde de version du contrôleur a été alignée sur ces deux interpréteurs.
2. Le nom d’artefact distingue la version Python, de sorte que les deux cellules ne partagent plus le même nom logique.
3. Le workflow de qualité conserve les 20 durées pytest les plus longues et le rapport JUnit avec les artefacts de couverture, même lorsque des contrôles échouent. Cette instrumentation n’a pas modifié la suite de référence, ses exclusions, seuils ou oracles. La phase Owner a ensuite explicitement modifié les trois cellules secondaires vers la sélection approuvée de 15 nodeids chacune; aucune cible standard complète n’a été retirée de la référence.
4. L’identité Git du workflow de qualité est épinglée dans le diagnostic Windows et correspond au blob effectivement poussé; le run #41326063607 a validé cette combinaison sur le HEAD d4761299f.
5. .gitattributes marque les CRLF du test WP12 concerné comme espaces CR de fin de ligne pour que le contrôle Git diff --check puisse valider le blob existant sans réécrire ses octets ni son oracle.

Ces modifications ajoutent de l’observabilité et permettent le diagnostic ciblé. Elles ne démontrent pas à elles seules le temps d’une future suite de référence.

## 3. Causes des durées excessives

Les rapports et profils disponibles attribuent l’essentiel du coût aux opérations suivantes :

- Les audits publics reparcouraient les sources à plusieurs reprises dans la même session pytest. Le correctif #116 les partage dans une fixture session avec identité d’entrée vérifiée; tout doute invalide la réutilisation.
- Le test de câblage de documentation exécutait auparavant des calculs de campagne FEM alors qu’il vérifiait seulement la copie des entrées. Le test mocke maintenant les trois frontières de campagne; les tests numériques réels restent séparés.
- L’audit réel d’archive Git reste le poste dominant mesuré : après un ancien diagnostic borné interrompu à 456 s, un scan complet ciblé a pris 1 040,44 s murales, 1 030,03 s CPU et 148,29 Mio RSS maximale pour 6 711 fichiers et 7 060 constats. Les règles de chemin ont passé, mais 618 chemins gardent des constats de contenu; aucun cache ni relancement ne supprime ce résultat FAIL.
- Les fichiers comportant des calculs FEM, non-linéaires ou de contact restent coûteux par conception. Aucun de ces tests n’a été supprimé ni remplacé par un mock dans le but d’accélérer la suite.
- Un profil de scan d’architecture sur le poste de mesure a dépassé 169,064 s murales pour 3,016 s CPU avec 87,4 Mio RSS; le stall dépendait du parcours récursif d’un volume local. Cette observation n’est pas une durée portable du runner Ubuntu.
- Chaque cellule CI doit installer ses dépendances adaptées à son OS et à sa version Python. Le cache pip est déjà activé dans les workflows concernés; partager un environnement entre ces cellules n’est pas équivalent.
- Le démarrage et la collecte pytest représentent environ 1,9 à 2,7 s sur les nodeids de gouvernance mesurés. Les diagnostics Windows lancent séparément trois processus pytest pour isoler le cas rotor, les autres paramètres et la séquence de prédécesseurs.

Les anciens journaux de suite n’exposaient ni durée par nodeid, ni CPU, ni RSS. Les durées de fichier ci-dessous sont des intervalles de progression historiques sur Ubuntu/Python 3.13, pas des profils exacts par test et pas un classement actuel après optimisation.

## 4. Dix principaux postes de coût restant à examiner

Le classement ci-dessous réutilise les plus longues durées de fichier disponibles. Il sert à prioriser des mesures ciblées; il ne prétend pas que les rangs 1 à 10 sont encore les plus lents après #115/#116.

| Rang | Fichier / poste | Durée historique | État après les changements et décision |
|---:|---|---:|---|
| 1 | tests/unit/test_release_readiness.py | 2 413,651 s | Les tests de composition utilisent des scanners mockés; les commandes utilisent un petit dépôt synthétique. Les nodeids locaux concernés passent en 1,23 à 3,41 s. La durée complète du fichier n’a pas été remesurée. |
| 2 | tests/integration/test_release_readiness_pipeline.py | 1 229,360 s | La composition reste vérifiée avec scanners mockés; nodeid ciblé PASS en 2,07 s localement. Suite complète non relancée. |
| 3 | tests/unit/test_public_release_audit.py | 1 226,984 s | Les scans de sources identiques restent partagés sous contrôle d’identité. Le scan d’archive réel final est mesuré à 1 040,44 s murales / 1 030,03 s CPU et 148,29 Mio RSS max; il échoue avec 7 060 constats de contenu. Pas de cache d’archive ni de relance. |
| 4 | tests/unit/test_wp_e01_j2_corotational_global.py | 504,639 s | Assemblage/global FEM; aucune exécution dans ce mandat. À profiler uniquement dans le cadre et le budget scientifiques autorisés. |
| 5 | tests/unit/test_nonlinear_multielement.py | 337,249 s | Cas non-linéaires; nodeid exact et classification nécessaires avant toute exécution. Aucune tentative dans ce mandat. |
| 6 | tests/unit/test_public_document_audit.py | 309,638 s | Le scan réel est conservé et mutualisé. Dans le test apparié, lectures mesurées réduites de 1 287 881 919 à 652 587 121 octets. |
| 7 | tests/integration/test_contact_verification_cli.py | 152,604 s | Exécute une campagne de contact réelle. Non exécuté ici; conserver un test réel de ce comportement. |
| 8 | tests/unit/test_corotational_j2_corrected.py | 71,366 s | Un nodeid math ciblé a passé en 4,508 s murales, 3,906 s CPU, RSS max observé 152,5 Mio. |
| 9 | tests/integration/test_examples.py | 61,737 s | Mélange solveur, conversion et CLI; pas de réduction de portée décidée. Suite non exécutée. |
| 10 | tests/unit/test_wp_e01_j2_coro_phase8.py | 58,202 s | Portée FEM exacte non établie dans ce profil; non exécuté et non promu en campagne E01. |

Autres postes observés : architecture_rules 56,963 s, WP12 divers modèles 51,157 s, nonlinearity performance 40,334 s, campagne HEX20 34,971 s, API/CLI 34,153 s, famille friction 33,064 s. Ces chiffres héritent de la même limite de granularité fichier.

### Dix nodeids les plus coûteux dans le run de référence #41328516423

Les durées ci-dessous proviennent du JUnit de la suite Ubuntu/Python 3.13. Elles donnent une mesure par test sur le candidat actuel, contrairement au classement historique par fichier ci-dessus. GitHub Actions n’a pas enregistré le CPU ni le RSS par nodeid/job pour cette suite; ces colonnes restent non mesurées et ne sont pas déduites du temps mural.

| Rang | Nodeid | Durée JUnit (s) | Observation |
|---:|---|---:|---|
| 1 | `tests/unit/test_public_release_audit.py::test_current_git_archive_keeps_whole_repository_hygiene_findings_visible` | 695,367 | Scan réel de l’archive Git; reste le plus gros poste et conserve G03 visible. |
| 2 | `tests/unit/test_wp_e01_j2_corotational_global.py::test_newton_analytic_experimental_vs_corrected_fd[HEX20]` | 290,334 | Calcul FEM; pas remplaçable par mock pour cette preuve numérique. |
| 3 | `tests/unit/test_nonlinear_multielement.py::test_finite_kinematic_arc_length_uses_common_adaptive_four_family_driver` | 145,830 | Calcul non linéaire réel. |
| 4 | `tests/integration/test_contact_verification_cli.py::test_contact_verification_api_and_cli_write_reviewable_evidence` | 101,581 | Vérifie une vraie campagne de contact et son parcours API/CLI. |
| 5 | `tests/unit/test_public_document_audit.py::test_whole_repository_document_audit_keeps_the_unresolved_public_hygiene_gate_visible` | 98,094 | Audit documentaire réel. |
| 6 | `tests/unit/test_wp12_diverse_models.py::test_diverse_catalog_has_144_unique_cases_and_broad_topology_coverage` | 32,742 | Assemblage/exécution du catalogue de modèles. |
| 7 | `tests/unit/test_nonlinear_multielement.py::test_euler_buckling_reference_is_recorded_as_bounded_research` | 26,202 | Cas de référence non linéaire. |
| 8 | `tests/unit/test_nonlinear_multielement.py::test_multifamily_coupled_contact_campaign_uses_the_common_driver` | 23,906 | Cas de campagne de contact multi-famille. |
| 9 | `tests/unit/test_hex20_campaign.py::test_hex20_internal_campaign_covers_analysis_j2_and_three_model_comparison` | 22,897 | Campagne de comparaison HEX20 existante dans la suite standard. |
| 10 | `tests/integration/test_examples.py::test_official_examples_solve_through_cli` | 21,072 | Exemples officiels parcourus par la CLI. |

## 5. Comparatif avant/après mesuré

### Mutualisation du scan source (#116 intégré par #118)

Deux mesures appariées sur Windows, Python 3.13.1, pytest 8.4.1, sans couverture :

| Groupe ciblé | Avant | Après | Variation |
|---|---:|---:|---:|
| Deux tests documentaires, temps pytest | 270,49 s | 119,99 s | −55,6 % |
| Deux tests documentaires, temps mural | 272,46 s | 121,94 s | −55,2 % |
| Deux tests documentaires, CPU | 243,84 s | 120,92 s | −50,4 % |
| Deux tests documentaires, RSS max | 200 392 704 o | 197 554 176 o | −1,4 % |
| Deux tests documentaires, octets lus | 1 287 881 919 o | 652 587 121 o | −49,3 % |
| Trois tests readiness/audit, temps pytest | 238,05 s | 132,14 s | −44,5 % |
| Trois tests readiness/audit, temps mural | 241,72 s | 135,68 s | −43,9 % |
| Trois tests readiness/audit, CPU | 239,08 s | 123,25 s | −48,4 % |
| Trois tests readiness/audit, RSS max | 200 441 856 o | 196 747 264 o | −1,8 % |
| Trois tests readiness/audit, octets lus | 977 317 179 o | 655 389 257 o | −32,9 % |

La fixture ne renvoie un résultat mémorisé que si HEAD, arbre, statut/diff suivi, contenu non suivi et drapeaux de l’index correspondent; elle vérifie aussi l’identité après le scan. Sinon, elle refait l’audit réel. L’archive Git n’est pas mise en cache.

### Test de câblage de documentation (#115 intégré par #118)

Le test de copie des assets est passé après remplacement des appels FEM par des mocks aux trois méthodes run(). Le temps d’appel pytest local est 0,02 s; session 1,86 s; temps de l’outil 4,18 s. L’ancien appel de test était mesuré à 41,10 s, 39,438 s CPU et 476,4 Mio RSS, avec une ancienne campagne non autorisée. Le temps d’appel ciblé a diminué d’environ 99,95 %. Les calculs de campagne n’ont pas été supprimés : ils demeurent couverts par leurs tests propres. Les économies CI post-correctif ne sont pas extrapolées sans nouvelle suite complète.

### Diagnostic Windows et coûts de lancement

Le run #41291708923 avait déjà vérifié 65 exécutions ciblées sur Python 3.13 en 85 s de workflow. Le run #41325510873 a ensuite vérifié les mêmes 64 nodeids distincts / 65 occurrences sur Python 3.10.11 et 3.13.17. Le run #41325192627 avait d’abord échoué avant les tests car la garde runtime n’acceptait que 3.13; le commit 8a8ed9b72 a corrigé cette incompatibilité.

Pour chaque version, le contrôleur a collecté 64 nodeids et lancé trois processus pytest. Les groupes ont tous fini code 0; le compteur de processus dans chaque échantillon final est 1. Ce compteur d’échantillonnage n’est pas un compteur exhaustif de tous les processus du job et ne doit pas être interprété comme tel.

| Python | Groupe isolé rotor : mur / CPU / RSS max | 8 autres paramètres : mur / CPU / RSS max | Séquence : mur / CPU / RSS max |
|---|---|---|---|
| 3.10.11 | 2,031 s / 1,531 s / 67 690 496 o | 2,516 s / 2,016 s / 75 452 416 o | 6,093 s / 5,156 s / 78 094 336 o |
| 3.13.17 | 2,017 s / 1,469 s / 110 002 176 o | 2,017 s / 1,500 s / 111 972 352 o | 4,028 s / 3,109 s / 92 958 720 o |

Ces mesures comprennent le temps mural de chaque invocation bornée tel que mesuré par le contrôleur, pas le setup Python ni l’installation des dépendances. Sur le run #41326063607, l’installation a pris 38 s en Python 3.10 et 63 s en Python 3.13; les durées totales des jobs étaient 2 min 12 s et 1 min 47 s respectivement. Les artefacts sont distincts : wp13-windows-diagnostic-py3.10-41326063607 (ID 13091810399) et wp13-windows-diagnostic-py3.13-41326063607 (ID 13091327030). Ces temps ne sont pas comparables aux milliers de secondes d’une suite complète.

### Run CI de la matrice approuvée — #41328516423

Sur Ubuntu/Python 3.13, pytest a terminé en 2 097,90 s (34 min 57,90 s), contre 7 120,37 s dans l’ancien run de référence Ubuntu/Python 3.13 #41225195330, soit une réduction de temps mural de test de 70,5 %. Le candidat actuel a 4 679 tests passés contre 4 676 dans l’ancien rapport; la comparaison est donc de même portée de suite, mais pas une identité parfaite de l’inventaire des tests. La durée complète du job Ubuntu/Python 3.13, installation et contrôles post-suite compris, est de 35 min 55 s. Le run entier s’est achevé en 36 min 02 s, les cellules étant parallèles.

Les trois cellules ciblées ont exécuté les mêmes 15 sélecteurs explicites. Durées pytest rapportées : Ubuntu/Python 3.10, 3,39 s; Windows/Python 3.10, 6,23 s; Windows/Python 3.13, 4,38 s. JUnit donne respectivement 2,724 s, 5,327 s et 3,681 s pour les suites; les durées totales de jobs, incluant l’installation, sont 53 s, 2 min 19 s et 1 min 09 s. Tous les quatre emplois ont réussi Ruff, mypy progressif, confidentialité et compileall. Le téléchargement des dépendances adapté à chaque OS/Python reste inclus dans le temps de job et n’est pas supprimé.

Le JUnit de référence consigne 4 679 réussites, 0 échec, 32 tests ignorés et le temps de suite; les 150 tests désélectionnés ne figurent pas comme testcase JUnit. Les cellules ciblées ont chacune 15 réussites, 0 échec et 0 ignoré. Le fichier de workflow ne recueille pas le temps CPU ni le RSS de la suite complète : ces ressources sont donc NOT_ACQUIRED pour le run CI. Les mesures CPU/RSS appariées des audits et tests ciblés consignées dans les tableaux précédents restent valables pour leur seule portée.

## 6. Tests réellement exécutés et non exécutés

Résultats PASS réalisés dans ce mandat ou vérifiés sur le candidat :

- Nodeids exacts Windows du correctif de racine absente, deux versions Python, workflow #41325510873; 64 nodeids distincts, 65 occurrences par cellule.
- Workflow de contrats synthétiques WP12 #41325515653 sur 8a8ed9b72 : lint, compilation, validation JSON, diff whitespace et contrats synthétiques PASS.
- Tests locaux ciblés du câblage documentaire, de la composition readiness, des commandes sur dépôt synthétique et du pipeline readiness : PASS.
- Ruff et py_compile sur le contrôleur de diagnostic; parsing YAML, validation des matrices, vérification du pin de blob et git diff --check : PASS.
- Run #41325197449 pour les contrôles rapides de workflow : Ruff, compilation, JSON, diff whitespace et contrats synthétiques PASS. L’échec Python 3.10 du diagnostic dans #41325192627 est expliqué et corrigé; les runs post-correctif #41325510873 et #41326063607 ont passé en 3.10 et 3.13. Le dernier a vérifié le pin de workflow et les artefacts séparés sur le HEAD d4761299f.
- Le run #41326438148 a ensuite échoué uniquement au contrôle git diff --check : des espaces de fin de ligne dans les métadonnées du présent rapport. Ils ont été supprimés; le contrôle local du diff complet passe. Le run a échoué avant les contrats synthétiques et n’a révélé aucun défaut du contrôleur.

Non exécutés ou non acquis :

- Suites complètes sur les trois cellules secondaires : elles ont été remplacées pour v0.2.12 par décision Owner par 15 nodeids ciblés chacune. L’ancien critère de quatre suites complètes est `REPLACED_BY_OWNER_DECISION`, jamais PASS; les deux suites Windows complètes restent historiquement non acquises.
- Six calculs smoke depuis package installé. Ils restent PREPARED_NOT_AUTHORIZED; aucun résultat n’est attribué.
- FEM, campagne de contact, benchmarks, convergence, qualification scientifique, ou tout résultat de smoke qualifié comme preuve scientifique globale.
- Vérification légale indépendante des licences tierces.
- CPU/RSS de la suite complète du run #41328516423; GitHub n’a pas émis ces métriques. Le temps par nodeid, la durée pytest et les artefacts JUnit/coverage sont acquis.

## 7. Architecture CI recommandée et compromis

L’Owner a accepté explicitement le niveau Release Validation B le 1 novembre 2026 pour v0.2.12, selon la matrice mesurée du run #41328516423. La cible FAST PR de moins de 10 minutes demeure un objectif de conception, pas une garantie mesurée.

| Niveau | Contenu recommandé | Ce que cela prouve | Limite |
|---|---|---|---|
| A — FAST PR | Ruff, mypy configuré, compilation Python, contrats API/CLI et sérialisation non scientifique, gouvernance synthétique, tests exacts des fichiers modifiés, confidentialité et métadonnées. Conserver les traces pytest/JUnit. | Défauts syntaxiques, de style, de typage configuré, de contrat et de gouvernance les plus fréquents. Cible de conception : moins de 10 min sur un changement ordinaire. | La cible de 10 min n’est pas mesurée comme garantie. Les tests ciblés ne démontrent pas le comportement complet ni la couverture globale. |
| B — RELEASE VALIDATION | Suite standard complète Ubuntu/Python 3.13 et seuils inchangés : branches globales ≥80 %, modules P0 ≥90 %. Les cellules Ubuntu/Python 3.10, Windows/Python 3.10 et Windows/Python 3.13 exécutent les 15 nodeids non scientifiques figés; les quatre cellules conservent les contrôles lint, typing, confidentialité, traçabilité et compilation. La compatibilité d’artefact v6 reste liée à son identité sélectionnée. | Référence complète et mesures de couverture sur Ubuntu/Python 3.13; signal ciblé de compatibilité sur les trois autres cellules, avec JUnit et provenance. | Une défaillance qui ne se manifeste que dans un test omis sur les cellules secondaires peut échapper à la matrice approuvée. Ce compromis est accepté explicitement par l’Owner pour v0.2.12. |
| C — SCIENTIFIC V&V | Circuit séparé avec manifeste exact, contrôleur, entrées/oracles figés, budget, ledger et autorisation Owner. | Résultats scientifiques dans la portée exacte du manifeste. | Aucun déclenchement automatique de campagnes FEM depuis une validation PR. |

Comparaison des politiques :

| Politique | Couverture | Coût/temps connu | Défauts possibles non détectés |
|---|---|---|---|
| Historique : quatre suites complètes Ubuntu/Windows × Python 3.10/3.13 | Politique plus large; elle produit un signal de suite sur les quatre cellules. Le run de référence historique a mesuré 84,75 % de couverture par branches, modules P0 à 100,00 % et 92,16 %. | Ubuntu 3.10 : 7 537,95 s; Ubuntu 3.13 : 7 120,37 s. Chaque Windows a atteint environ 10 682–10 725 s avant annulation à 180 min. Environ 10 h de temps d’exécution de cellules additionné (calculé depuis des durées murales, pas une mesure CPU), autour de 3 h murales parallèles. | Les deux suites Windows complètes ne se sont pas terminées; l’ancien critère n’a donc pas atteint un PASS complet. |
| Politique Owner approuvée : suite complète Ubuntu/Python 3.13, trois cellules de compatibilité ciblées | La couverture globale et P0 est mesurée uniquement par la référence Ubuntu 3.13; chaque cellule secondaire exécute exactement 15 nodeids. Ce n’est pas équivalent à quatre suites complètes. | Mesuré dans #41328516423 : 2 097,90 s de suite de référence; jobs compatibilité 53 s à 2 min 19 s. | Des défauts uniquement déclenchés par des tests omis des cellules secondaires peuvent échapper à ces contrôles. Ce risque est accepté par l’Owner pour cette release. |

**Disposition de l’ancien critère : `REPLACED_BY_OWNER_DECISION`, non PASS.** Les quatre suites complètes n’ont pas toutes été acquises historiquement. L’Owner a accepté la politique de remplacement pour v0.2.12 et le run #41328516423 en a validé les quatre cellules selon cette nouvelle politique; ceci n’efface pas l’historique des deux cellules Windows complètes non acquises.

## 8. Matrice actualisée des gates

Les statuts sont utilisés strictement : PASS = preuve dans la portée revendiquée; FAIL = critère échoué; BLOCKED = la clôture ne peut avancer sans l’action indiquée; NOT_RUN = aucune exécution revendiquée; NOT_ACQUIRED = preuve ou autorisation requise absente.

Le tableau ci-dessous est le statut consolidé après la décision Owner et le run #41328516423. `REPLACED_BY_OWNER_DECISION` est une disposition du critère, non un état PASS; les résultats complets historiques des cellules Windows restent non acquis.

| Gate | Statut | Preuve | Blocage | Action nécessaire |
|---|---|---|---|---|
| Identité initiale PR #114 / HEAD c06a669 | PASS | Fetch exact de la tête PR, identique au SHA fourni; base release ab137051. | Aucun pour l’identité initiale. | Garder l’identité de tête/artefacts dans les traces de suite. |
| HEAD initial de la phase Owner / PR #114 | PASS | `26d12db7621ba746db10b8588d0c09d759e7e97d` vérifié avant implémentation; le dispatch utilise exactement `698e858e79d6b6ded7cdf764f5e0dd26c710c301`. | Aucun pour l’identité du run. | Ne pas confondre l’identité initiale avec celle testée. |
| Décision Owner sur matrice CI | PASS | Décision explicite du 2026-11-01 : Ubuntu/Python 3.13 complet, trois sélections ciblées, seuils inchangés. | Aucun sur cette décision. | Respecter son périmètre uniquement. |
| Ancienne exigence quatre suites complètes | REPLACED_BY_OWNER_DECISION (not PASS) | La décision Owner remplace ce critère pour v0.2.12. Les deux suites Windows complètes historiques restent interrompues/non acquises. | Aucun sous la nouvelle politique. | Ne jamais afficher l’ancien critère comme PASS. |
| Matrice de release selon la politique Owner | PASS | Run #41328516423, branche WP13, HEAD exact, `include_extended_jobs=false`, base confidentialité `ab137051d920d7fa9aae9a3012a48b2b26e2198b`; conclusion globale `success`. | Aucun dans la portée approuvée. | Garder les JUnit, couverture et provenance attachés au run. |
| Suite complète Ubuntu/Python 3.13 | PASS | Python 3.13.17; 4 679 passed, 0 failed, 32 skipped, 150 deselected; 2 097,90 s; 4 warnings; JUnit et couverture. | Aucun pour la suite de référence. | Seule cette cellule fournit la couverture de la matrice. |
| Couverture globale et P0 | PASS | Global 84,75 % avec branches; `solveur/core/errors.py` 100,00 %, `solveur/verification/traceability.py` 92,16 %; contrôle de couverture P0 réussi. | Aucun pour les seuils courants. | Les cellules ciblées ne produisent pas de couverture représentative. |
| Compatibilité ciblée — Ubuntu/Python 3.10 | PASS | Python 3.10.22; 15/15, 0 fail, 0 skipped; 3,39 s pytest; JUnit artifact 13092317209. | Limité aux 15 nodeids manifestés. | Ne pas extrapoler à la suite complète. |
| Compatibilité ciblée — Windows/Python 3.10 | PASS | Python 3.10.11; 15/15, 0 fail, 0 skipped; 6,23 s pytest; JUnit artifact 13092775721. | Limité aux 15 nodeids manifestés. | Ne pas extrapoler à la suite complète. |
| Compatibilité ciblée — Windows/Python 3.13 | PASS | Python 3.13.16; 15/15, 0 fail, 0 skipped; 4,38 s pytest; JUnit artifact 13091563751. | Limité aux 15 nodeids manifestés. | Ne pas extrapoler à la suite complète. |
| Ruff, mypy progressif, confidentialité, compileall | PASS | Les quatre jobs terminent chacun ces contrôles avec succès. | Aucun dans les contrôles exécutés. | Aucune. |
| Quick verification et jobs étendus | NOT_RUN | Quick verification est skipped pour le dispatch WP13; les jobs documentation, engineering et WP14 sont skipped par l’input approuvé `false`. | Hors de cette exécution de matrice. | Ne pas en déduire PASS. |
| Correctifs #115/#116 intégrés par #118 | PASS | Commit intégré 0a736a47; changements observés dans l’arbre WP13. | Aucun dans leur portée. | Conserver les tests réels de scan/archive et les cas numériques distincts. |
| Correctif de boucle Windows, Python 3.10 et 3.13 | PASS | Run #41325510873; chaque cellule a collecté les 64 nodeids épinglés et réussi les 65 occurrences bornées. | Ne couvre que les nodeids de gouvernance inscrits. | Utiliser le résultat pour ce correctif uniquement. |
| Contrats synthétiques du contrôleur WP12 | PASS | Run #41325515653, commit 8a8ed9b72. | Ne vaut pas suite WP12 ou qualification. | Aucune action additionnelle pour ce gate ciblé. |
| Instrumentation de diagnostics Windows | PASS | Ruff, py_compile, parsing/matrices, pin de blob; run #41326063607 PASS sur Python 3.10 et 3.13 au HEAD d4761299f; deux artefacts nommés par version. | Aucun dans la portée de ce diagnostic. | Garder les logs avec leur commit et leur version Python. |
| Rapport complet avec preuves de ce mandat | PASS | Ce rapport assemble les preuves relues, mesurées et les gates non acquis; les runs #41326063607 et #41328516423 sont inclus. | Les gates explicitement NOT_RUN/NOT_ACQUIRED/FAIL restent ouverts. | Conserver le statut WP13_PARTIAL_OR_BLOCKED; ne pas inférer une clôture. |
| Candidat de distribution, sélection v6 | PASS | SHA source v6 2865587a; aucun chemin sélectionné ni blob de contrat modifié par les changements WP13; détails §9. | N’englobe ni G03, ni licence, ni smoke calculatoire. | Garder le contrat v6 associé à ses artefacts. |
| Builds v6 wheel/sdist et contrôles d’archive | PASS | Wheel/sdist v6, scans sélectionnés, Twine et contrôles d’installation Windows/Python 3.13.1 consignés dans le rapport v6. | Pas de nouvel OS/Python d’installation; pas de licence indépendante. | Réutiliser uniquement pour l’identité de sélection inchangée. |
| Candidats smoke wheel/sdist (six tentatives) | NOT_ACQUIRED | Contrôleur et manifestes préparés; le dossier indique PREPARED_NOT_AUTHORIZED. | Autorisation distincte de la campagne absente. | Décision exacte Owner décrite §10; ne pas lancer sans elle. |
| Documentation publique sélectionnée | PASS | Sélection v3 : 773 documents, zéro constat de sélection; contenus inchangés depuis la preuve. | Ne purge pas les archives ni les fichiers hors sélection. | Maintenir la sélection et les contrôles de confidentialité. |
| Sélection de chemins d’archive prospective | PASS (contrôle ciblé) | La règle `/AGENTS.md` et `docs/generated/results/**` est `export-ignore`; `git check-attr` confirme l’exclusion de la racine et des JSON, tout en conservant le Markdown généré référencé. Le test ciblé de règle passe. | Contrôle de chemins seulement; le contenu complet et l’historique Git restent distincts. | Vérifier la liste de chemins de l’archive finale après commit. |
| G03, critère indépendant archive/dépôt | FAIL_PRESERVED | Audit prospectif FAIL au snapshot `3ced76d`: 6 711 fichiers, 7 060 constats sur 618 chemins (822 `internal_workflow`, 3 130 `private_environment`, 3 098 `workstation_path`, 10 `private_email`), aucun `forbidden_path`. La liste finale a 6 714 chemins (+3 rapports scannés individuellement, 0 constat chacun), sans préfixe interdit. Préfiltre historique WARNING (2 587 commits, 1 429 événements). Détails dans [`WP13_G03_REMEDIATION_REPORT.md`](WP13_G03_REMEDIATION_REPORT.md). | Contenu d’archive et historique non conformes; le filtrage ne purge pas les commits. L’audit complet de la source suivie n’a pas été lancé, car il ne peut pas lever les bloqueurs connus. | Conserver FAIL_PRESERVED; aucune réécriture n’est autorisée dans ce mandat. |
| Audit complet du contenu source suivi | NOT_RUN | L’audit d’archive a déjà 7 060 constats et le préfiltre historique reste WARNING; un second scan global ne peut pas lever ces bloqueurs. Les sélections package/docs v6 restent PASS séparément. | Résultat du scan complet des sources non acquis. | Réexaminer après plan borné de remédiation de contenu et décision séparée sur l’historique. |
| Inventaire technique des licences v6 | PASS (portée bornée) | Graphe runtime par défaut et fichiers de licence wheel/sdist inventoriés dans [`WP13_THIRD_PARTY_LICENSE_AUDIT.md`](WP13_THIRD_PARTY_LICENSE_AUDIT.md). | N’est pas un avis juridique et ne couvre pas chaque version autorisée ni l’installation de tous les extras. | Préserver les notices et demander la revue indépendante. |
| Ancienne obligation de quatre suites complètes | REPLACED_BY_OWNER_DECISION (not PASS) | Décision Owner explicite du 2026-11-01; les deux anciennes suites Windows complètes restent non acquises. | Aucun sous la politique de release actuelle. | Ne pas reclasser l’ancien critère comme PASS. |
| Matrice CI selon la politique Owner | PASS | Run #41328516423, exact HEAD 698e858e79d6b6ded7cdf764f5e0dd26c710c301; quatre jobs succès. | Aucun dans la portée approuvée. | Conserver les artefacts et ce lien. |
| Suite de référence et couverture sur le HEAD de matrice | PASS | Ubuntu/Python 3.13.17 : 4 679 passés, 32 ignorés, 150 désélectionnés, zéro échec; 84,75 % branches; P0 modules 100,00 % et 92,16 %. | Aucune pour ces seuils. | Les couvertures acquises ne s’étendent pas aux cellules ciblées. |
| Compatibilité ciblée OS/Python | PASS (portée ciblée) | Les trois cellules secondaires ont passé les 15 nodeids exacts, 0 échec, 0 ignoré. | Les suites complètes secondaires et les installations d’artefacts dans ces cellules ne sont pas démontrées. | Maintenir la liste et son hash; ne pas extrapoler à toute la suite. |
| Compatibilité complète OS/Python et installations wheel/sdist dans la matrice | NOT_ACQUIRED | La politique approuvée exige les sélections ciblées sur les cellules secondaires; v6 comporte une installation wheel/sdist fraîche sur Windows/Python 3.13.1. | Aucune installation de wheel/sdist n’a été faite dans les quatre cellules du run #41328516423. | Réutiliser la preuve v6 pour les blobs identiques; ne pas revendiquer d’autres installations. |
| Audit juridique indépendant des licences | NOT_ACQUIRED | Aucune détermination indépendante de compatibilité de redistribution n’est enregistrée. | La revue technique n’est pas une clearance juridique. | Obtenir la revue de la candidate exacte et de la politique d’extras avant publication. |
| V&V scientifique / FEM / benchmarks / convergence | NOT_RUN | Aucune campagne scientifique lancée dans ce mandat. | Manifeste et autorisation campagne absents. | Circuit distinct avec gate Owner exact avant toute campagne. |
| Publication, tag, merge release/main | NOT_RUN | Aucun acte de publication, tag ou merge effectué. | Autorisation volontairement absente du mandat. | Une décision de release distincte reste nécessaire. |

**WP13 P0 demeure PARTIAL_OR_BLOCKED.** Les PASS limités ci-dessus ne constituent ni un P0 validé ni un feu vert de publication.

## 9. Compatibilité et identité des packages

La comparaison des blob Git entre la source v6 `2865587a44f9e461a0b4e4286c912c17e4f04be5` et le commit WP13 de vérification `62bd4f0d31161bb1b35b320c9f96c25f90cc0d54` donne 585/585 chemins de package identiques et 773/773 chemins de documentation sélectionnée identiques : aucun ajout, retrait ou blob modifié dans ces sélections. Les modifications suivantes ne concernent que les rapports de qualification, hors de ces ensembles; elles ont été vérifiées sans constat par le scanner ciblé. Les hashes et vérifications du wheel/sdist v6 restent donc applicables; aucune reconstruction n’est justifiée.

Le contrat de sélection public v6 est lié à la source 2865587a44f9e461a0b4e4286c912c17e4f04be5, contrat QF-0212-WP13-SELECTED-CANDIDATE-20261031-06, SHA-256 f33a72b… Les diffs Git entre ce snapshot et le candidat WP13 audité ne montrent aucun changement dans les chemins sélectionnés par le contrat. La phase de matrice (workflow `quality.yml`, script de sélection, manifeste de nodeids, tests et rapports) n’a modifié aucun fichier distribué ni aucune documentation publique sélectionnée; ces blobs demeurent donc identiques au contrat v6. Le run CI installe le baseline verrouillé, pas le wheel/sdist v6.

Les sept outils épinglés par le contrat — audit_public_release.py, audit_release_archive.py, git_tools.py, plan_public_package.py, probe_installed_package.py, review_vocabulary.py et verify_public_package.py — ont les mêmes blobs Git attendus qu’au snapshot v6. L’identité des fichiers distribués est donc compatible avec les preuves v6 sans reconstruire les artefacts à partir d’une source différente.

Artefacts v6 consignés :

- Wheel : 1 689 662 octets, SHA-256 ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a.
- Sdist normalisée : 1 294 049 octets, SHA-256 183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde.
- 585 fichiers dans le wheel, 593 dans la sdist; zéro finding dans les surfaces sélectionnées; Twine 7.0 PASS.
- Installation fraîche Windows/Python 3.13.1 pour wheel et sdist; 501 fichiers source installés, version/aide CLI et six vérifications non résolvantes check-mesh PASS.
- Les octets bruts de sdist varient avec les métadonnées gzip; la comparaison documentée porte sur la sdist normalisée.

La version v6 de l’inventaire de dépendances a des versions différentes de la v4. Cela ne fournit pas de clearance juridique indépendante. Il n’y a ni smoke de solveur installé, ni nouvelle preuve Ubuntu ou Python 3.10. Le dossier smoke fixe un contrôleur (SHA-256 16df6eba0f902c332cace9e9a5624d1b8b59c3e051bfcc4063782123cc9a7f2f) et un manifeste (SHA-256 dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b); ils n’ont pas été modifiés. Les six tentatives statique, modale et dynamique × wheel/sdist restent préparées sans autorisation d’exécution.

## 10. Décisions Owner (résolue et en attente)

1. **Politique Release Validation — résolue** — le 2026-11-01, l’Owner a explicitement remplacé les quatre suites complètes par la suite complète Ubuntu/Python 3.13 et les 15 nodeids de compatibilité dans les trois cellules secondaires. La politique a passé le run #41328516423. L’ancienne obligation est remplacée, pas déclarée PASS. Le coût historique d’environ 10 h additionnées était un total des durées de tests par cellule, pas une mesure CPU; la nouvelle suite de référence a pris 2 097,90 s.
2. **Six smoke tests installés** — autoriser séparément les six tentatives serialisées exactement prévues au dossier, sur les wheels/sdists et entrées/oracles figés, avec leur budget/contrôleur/ledger prescrits. Sans cette autorisation exacte, aucun calcul ne sera lancé. Ces résultats ne seraient que des smoke d’installation/correctness dans leur portée, jamais une qualification scientifique globale.
3. **Disposition G03 / historique public** — la correction prospective retire les chemins visés de l’archive `git archive`, mais le préfiltre de l’historique public signale toujours des événements historiques. Le choix entre conserver cet historique avec G03 en FAIL_PRESERVED et ouvrir une revue séparée pour une éventuelle histoire publique propre doit être traité dans un mandat ultérieur. Aucune réécriture n’est autorisée ici.
4. **Revue juridique des licences** — le dossier technique est livré comme inventaire limité; une détermination indépendante de compatibilité de redistribution reste à acquérir avant publication.

Les décisions Owner encore nécessaires sont l’autorisation distincte des six smoke tests installés, la disposition du risque de l’historique public G03 dans un mandat séparé, et l’acceptation d’une revue juridique indépendante. G03 reste un échec conservé jusqu’à satisfaction de son critère indépendant. La décision sur les suites complètes ne modifie ni G03, ni les résultats WP12, ni les critères scientifiques.

## 11. Risques résiduels

- Les durées JUnit par nodeid sont disponibles pour la suite Ubuntu/Python 3.13, mais CPU et RSS de cette suite ne sont pas collectés par le workflow.
- Le nodeid d’archive du run CI a pris 695,367 s et le test d’audit documentaire 98,094 s. Le scan local complet ultérieur a pris 1 040,44 s murales, 1 030,03 s CPU et 148,29 Mio RSS max; il garde le contrôle réel et rend FAIL, sans résultat susceptible d’être accéléré par cache.
- La matrice approuvée ne détectera pas nécessairement les défauts qui n’apparaissent que dans les tests omis des trois cellules ciblées.
- Les suites complètes secondaires, les installations wheel/sdist dans les quatre cellules et la couverture sur les cellules ciblées ne sont pas acquises. Elles ne font pas partie du critère CI accepté par l’Owner.
- Le smoke package, G03, les licences et toute qualification scientifique restent des gates indépendants.
- Le correctif `.gitattributes` cible uniquement `AGENTS.md` à la racine et les JSON de résultats générés; il ne retire aucun contenu des commits ni de l’historique Git.
- Le scan complet d’archive est une opération coûteuse en CPU, sans cache partagé; sa mesure et son résultat finaux sont consignés dans le rapport G03. Aucun scan global n’est relancé automatiquement.
- Les durées de scans sur le volume local et les temps locaux de tests ne prédisent pas directement les runners GitHub.
- Le résultat de test ne permet pas de publier, taguer ou fusionner dans la branche release.

## 12. Références de validation

- [PR #114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114).
- [Run Windows matrix #41325510873](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41325510873).
- [Run Windows final #41326063607 sur le HEAD d4761299f](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41326063607).
- [Run synthétique WP12 #41325515653](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41325515653).
- [Ancien run de référence complet/partiel #41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330).
- [Matrice approuvée et run unique #41328516423](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423).
- [Artefact de référence JUnit/couverture 13093243065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423/artifacts/13093243065).
- [Artefact JUnit Ubuntu/Python 3.10 — 13092317209](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423/artifacts/13092317209).
- [Artefact JUnit Windows/Python 3.10 — 13092775721](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423/artifacts/13092775721).
- [Artefact JUnit Windows/Python 3.13 — 13091563751](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423/artifacts/13091563751).
- [Rapport candidat v6](./WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md).
- [Dossier smoke package](./WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md).
- [Rapport d’optimisation des tests](./WP13_TEST_SUITE_OPTIMIZATION_REPORT.md).
- [Rapport de remédiation G03](./WP13_G03_REMEDIATION_REPORT.md).
- [Audit technique des licences tierces](./WP13_THIRD_PARTY_LICENSE_AUDIT.md).
- [Dossier des décisions finales Owner](./WP13_FINAL_OWNER_DECISION_DOSSIER.md).

## 13. Détail de la matrice approuvée

L’unique dispatch `quality.yml` a été exécuté le 2026-11-01 pour la PR #114, commit `698e858e79d6b6ded7cdf764f5e0dd26c710c301`. Les paramètres correspondent à la décision : `include_extended_jobs=false`, `privacy_base_sha=ab137051d920d7fa9aae9a3012a48b2b26e2198b`. Chaque job a enregistré le même HEAD, son OS et sa version Python exacte.

| Cellule | Python exact | Résultat/tests | Durée pytest | Durée du job | JUnit / couverture |
|---|---|---|---:|---:|---|
| Ubuntu / 3.13 référence | 3.13.17 | PASS; 4 679 passed, 0 failed, 32 skipped, 150 deselected, 4 warnings | 2 097,90 s (34:57,90); JUnit suite 2 096,865 s | 35:55 | Artefact 13093243065 : JUnit, coverage.json/xml, coverage-p0.json. |
| Ubuntu / 3.10 compatibilité | 3.10.22 | PASS; 15 passed, 0 failed, 0 skipped | 3,39 s; JUnit suite 2,724 s | 0:53 | Artefact 13092317209 : JUnit. |
| Windows / 3.10 compatibilité | 3.10.11 | PASS; 15 passed, 0 failed, 0 skipped | 6,23 s; JUnit suite 5,327 s | 2:19 | Artefact 13092775721 : JUnit. |
| Windows / 3.13 compatibilité | 3.13.16 | PASS; 15 passed, 0 failed, 0 skipped | 4,38 s; JUnit suite 3,681 s | 1:09 | Artefact 13091563751 : JUnit. |

La suite Ubuntu/Python 3.13 a produit 84,75 % de couverture globale avec branches (seuil ≥80 %). Le contrôle P0 a réussi : `solveur/core/errors.py` à 100,00 % et `solveur/verification/traceability.py` à 92,16 % (seuil ≥90 %); le contrôle P0 a exécuté 37 tests passés et 2 ignorés en 1,22 s. Le JUnit et les logs contiennent les 20 durées les plus longues; les dix premières figurent en §4.

Les quatre jobs ont passé Ruff, mypy progressif, le contrôle de confidentialité et `compileall`. Quick verification et les jobs étendus ont été `NOT_RUN`/skipped par conception pour le dispatch approuvé; aucune campagne FEM distincte ni aucun smoke installé n’a été lancé. Il n’y a eu ni timeout, ni test échoué, ni relance automatique. Le run entier s’est achevé en 36 min 02 s; sa conclusion GitHub est `success`.

La sélection secondaire est le manifeste de 15 nodeids `wp13_compatibility_nodeids.json`, SHA-256 `0fb5add51545ce77e0ce93ddc5c7c1cb20cff2d74f554136c47f24cf423156ba`. Les tests ont été vérifiés par nodeid avant inclusion. Aucun des 15 tests ne lance de solveur/assemblage; la preuve du correctif de boucle Windows est portée séparément par le run ciblé #41325510873 sur Python 3.10 et 3.13.

## Verdict final

**WP13_PARTIAL_OR_BLOCKED**

Le gate CI de la politique explicitement approuvée par l’Owner est PASS sur le commit exact de workflow : suite de référence complète, seuils de couverture et trois cellules ciblées ont tous passé. L’ancienne exigence de quatre suites complètes est `REPLACED_BY_OWNER_DECISION`, non PASS; ses deux cellules Windows complètes historiquement interrompues restent ainsi documentées. WP13 n’est pas terminée : les six smoke tests installés demeurent PREPARED_NOT_AUTHORIZED, G03 reste FAIL_PRESERVED, l’examen juridique indépendant des licences n’est pas acquis et les autres gates distincts demeurent ouverts. Aucun tag, merge release/main ni publication n’a eu lieu.
