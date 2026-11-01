# WP13 — Rapport final de validation et de performance

Date de l’audit : 1 novembre 2026
Dépôt : emptiesvoid-cloud/QF_solver
PR : [#114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
Branche : codex/wp13-release-engineering-20261031
Branche de release examinée : emptiesvoids-cloud/0.2.12

## Verdict exécutif

**WP13_PARTIAL_OR_BLOCKED**

Les correctifs d’infrastructure autorisés et les diagnostics Windows bornés sont vérifiés. Les preuves v6 d’artefact restent applicables aux fichiers sélectionnés par le contrat de distribution : les changements WP13 ultérieurs concernent les workflows, scripts de diagnostic, tests et rapports internes, sans modifier les blobs distribués. Le correctif de scan source intégré via #118 réduit le travail répété, et le test de câblage documentaire ne lance plus les campagnes FEM.

La clôture reste bloquée par des critères que ce mandat n’autorise pas à remplacer ou à déclarer acquis : l’obligation historique de quatre suites complètes, la campagne complète de référence, les six smoke tests installés dont l’autorisation reste distincte, G03 toujours en échec et l’examen juridique indépendant des licences. Aucun de ces constats ne vaut PASS par extrapolation.

## 1. État initial vérifié

- Le HEAD initial de la PR, rafraîchi depuis GitHub, était c06a669180d1e5e7545b1a48aa5e904f2f45539d, identique à celui indiqué dans le mandat.
- Le worktree WP13 était propre à 67adffbe3 avant rafraîchissement. Le worktree release et ses modifications locales WP12 n’ont pas été touchés.
- La base de PR #114 est emptiesvoids-cloud/0.2.12, commit ab137051d920d7fa9aae9a3012a48b2b26e2198b.
- Les correctifs des PR #115 et #116 sont présents dans le commit intégré #118, 0a736a47d4e9980020970f30c973c6acca4098c1. Le test de câblage des documents remplace les exécutions FEM par des mocks à la frontière de campagne; la fixture de scan réutilise un audit uniquement quand son identité d’entrée Git et son état de worktree correspondent.
- Les rapports exigés ont été relus : matrice de gates, validation P0, optimisation phase 2, correctif Windows, vérification d’artefacts v6, dossier de décision smoke et optimisation de la suite.
- Le HEAD des correctifs code/CI vérifiés est d4761299fe93a1221eb798e6cd37bc5582538b9d. Les changements poussés sont b481ad96c, 8a8ed9b72 et d4761299f. Le diagnostic du HEAD code/CI a passé sur les deux cellules dans le run #41326063607.

## 2. Correctifs réalisés

1. Le workflow de diagnostic Windows vérifie maintenant le même ensemble borné sur Python 3.10 et 3.13. La garde de version du contrôleur a été alignée sur ces deux interpréteurs.
2. Le nom d’artefact distingue la version Python, de sorte que les deux cellules ne partagent plus le même nom logique.
3. Le workflow de qualité conserve les 20 durées pytest les plus longues et le rapport JUnit avec les artefacts de couverture, même lorsque des contrôles échouent. Aucune sélection de tests, commande de couverture, exclusion, seuil ou oracle n’a changé.
4. L’identité Git du workflow de qualité est épinglée dans le diagnostic Windows et correspond au blob effectivement poussé; le run #41326063607 a validé cette combinaison sur le HEAD d4761299f.
5. .gitattributes marque les CRLF du test WP12 concerné comme espaces CR de fin de ligne pour que le contrôle Git diff --check puisse valider le blob existant sans réécrire ses octets ni son oracle.

Ces modifications ajoutent de l’observabilité et permettent le diagnostic ciblé. Elles ne démontrent pas à elles seules le temps d’une future suite de référence.

## 3. Causes des durées excessives

Les rapports et profils disponibles attribuent l’essentiel du coût aux opérations suivantes :

- Les audits publics reparcouraient les sources à plusieurs reprises dans la même session pytest. Le correctif #116 les partage dans une fixture session avec identité d’entrée vérifiée; tout doute invalide la réutilisation.
- Le test de câblage de documentation exécutait auparavant des calculs de campagne FEM alors qu’il vérifiait seulement la copie des entrées. Le test mocke maintenant les trois frontières de campagne; les tests numériques réels restent séparés.
- L’audit réel d’archive Git reste cher : un diagnostic local borné a été interrompu à environ 456 s murales, après au moins 452,92 s CPU, pendant le parcours des membres de l’archive. Il n’a pas été relancé.
- Les fichiers comportant des calculs FEM, non-linéaires ou de contact restent coûteux par conception. Aucun de ces tests n’a été supprimé ni remplacé par un mock dans le but d’accélérer la suite.
- Un profil de scan d’architecture sur ce poste a dépassé 169,064 s murales pour 3,016 s CPU avec 87,4 Mio RSS; le stall dépendait du parcours récursif du volume E: local. Cette observation n’est pas une durée portable du runner Ubuntu.
- Chaque cellule CI doit installer ses dépendances adaptées à son OS et à sa version Python. Le cache pip est déjà activé dans les workflows concernés; partager un environnement entre ces cellules n’est pas équivalent.
- Le démarrage et la collecte pytest représentent environ 1,9 à 2,7 s sur les nodeids de gouvernance mesurés. Les diagnostics Windows lancent séparément trois processus pytest pour isoler le cas rotor, les autres paramètres et la séquence de prédécesseurs.

Les anciens journaux de suite n’exposaient ni durée par nodeid, ni CPU, ni RSS. Les durées de fichier ci-dessous sont des intervalles de progression historiques sur Ubuntu/Python 3.13, pas des profils exacts par test et pas un classement actuel après optimisation.

## 4. Dix principaux postes de coût restant à examiner

Le classement ci-dessous réutilise les plus longues durées de fichier disponibles. Il sert à prioriser des mesures ciblées; il ne prétend pas que les rangs 1 à 10 sont encore les plus lents après #115/#116.

| Rang | Fichier / poste | Durée historique | État après les changements et décision |
|---:|---|---:|---|
| 1 | tests/unit/test_release_readiness.py | 2 413,651 s | Les tests de composition utilisent des scanners mockés; les commandes utilisent un petit dépôt synthétique. Les nodeids locaux concernés passent en 1,23 à 3,41 s. La durée complète du fichier n’a pas été remesurée. |
| 2 | tests/integration/test_release_readiness_pipeline.py | 1 229,360 s | La composition reste vérifiée avec scanners mockés; nodeid ciblé PASS en 2,07 s localement. Suite complète non relancée. |
| 3 | tests/unit/test_public_release_audit.py | 1 226,984 s | Les scans de sources identiques sont partagés sous contrôle d’identité. L’audit d’archive réelle reste mesuré au moins 456 s sous plafond puis interrompu; pas de cache d’archive. |
| 4 | tests/unit/test_wp_e01_j2_corotational_global.py | 504,639 s | Assemblage/global FEM; aucune exécution dans ce mandat. À profiler uniquement dans le cadre et le budget scientifiques autorisés. |
| 5 | tests/unit/test_nonlinear_multielement.py | 337,249 s | Cas non-linéaires; nodeid exact et classification nécessaires avant toute exécution. Aucune tentative dans ce mandat. |
| 6 | tests/unit/test_public_document_audit.py | 309,638 s | Le scan réel est conservé et mutualisé. Dans le test apparié, lectures mesurées réduites de 1 287 881 919 à 652 587 121 octets. |
| 7 | tests/integration/test_contact_verification_cli.py | 152,604 s | Exécute une campagne de contact réelle. Non exécuté ici; conserver un test réel de ce comportement. |
| 8 | tests/unit/test_corotational_j2_corrected.py | 71,366 s | Un nodeid math ciblé a passé en 4,508 s murales, 3,906 s CPU, RSS max observé 152,5 Mio. |
| 9 | tests/integration/test_examples.py | 61,737 s | Mélange solveur, conversion et CLI; pas de réduction de portée décidée. Suite non exécutée. |
| 10 | tests/unit/test_wp_e01_j2_coro_phase8.py | 58,202 s | Portée FEM exacte non établie dans ce profil; non exécuté et non promu en campagne E01. |

Autres postes observés : architecture_rules 56,963 s, WP12 divers modèles 51,157 s, nonlinearity performance 40,334 s, campagne HEX20 34,971 s, API/CLI 34,153 s, famille friction 33,064 s. Ces chiffres héritent de la même limite de granularité fichier.

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

## 6. Tests réellement exécutés et non exécutés

Résultats PASS réalisés dans ce mandat ou vérifiés sur le candidat :

- Nodeids exacts Windows du correctif de racine absente, deux versions Python, workflow #41325510873; 64 nodeids distincts, 65 occurrences par cellule.
- Workflow de contrats synthétiques WP12 #41325515653 sur 8a8ed9b72 : lint, compilation, validation JSON, diff whitespace et contrats synthétiques PASS.
- Tests locaux ciblés du câblage documentaire, de la composition readiness, des commandes sur dépôt synthétique et du pipeline readiness : PASS.
- Ruff et py_compile sur le contrôleur de diagnostic; parsing YAML, validation des matrices, vérification du pin de blob et git diff --check : PASS.
- Run #41325197449 pour les contrôles rapides de workflow : Ruff, compilation, JSON, diff whitespace et contrats synthétiques PASS. L’échec Python 3.10 du diagnostic dans #41325192627 est expliqué et corrigé; les runs post-correctif #41325510873 et #41326063607 ont passé en 3.10 et 3.13. Le dernier a vérifié le pin de workflow et les artefacts séparés sur le HEAD d4761299f.
- Le run #41326438148 a ensuite échoué uniquement au contrôle git diff --check : des espaces de fin de ligne dans les métadonnées du présent rapport. Ils ont été supprimés; le contrôle local du diff complet passe. Le run a échoué avant les contrats synthétiques et n’a révélé aucun défaut du contrôleur.

Non exécutés ou non acquis :

- Suite complète standard sur ce HEAD; une campagne Ubuntu/Python 3.13 complète; quatre suites complètes; couvertures globales actuelles.
- Tests complets Linux et Windows, tests complets Python 3.10 et 3.13, installation d’artefacts sur chaque combinaison OS/Python.
- Six calculs smoke depuis package installé. Ils restent PREPARED_NOT_AUTHORIZED; aucun résultat n’est attribué.
- FEM, campagne de contact, benchmarks, convergence, qualification scientifique, ou tout résultat de smoke qualifié comme preuve scientifique globale.
- Vérification légale indépendante des licences tierces.
- Audit d’archive complet après l’interruption de mesure locale.

## 7. Architecture CI recommandée et compromis

Cette architecture est une proposition d’ingénierie; elle n’est pas une politique Owner acceptée.

| Niveau | Contenu recommandé | Ce que cela prouve | Limite |
|---|---|---|---|
| A — FAST PR | Ruff, mypy configuré, compilation Python, contrats API/CLI et sérialisation non scientifique, gouvernance synthétique, tests exacts des fichiers modifiés, confidentialité et métadonnées. Conserver les traces pytest/JUnit. | Défauts syntaxiques, de style, de typage configuré, de contrat et de gouvernance les plus fréquents. Cible de conception : moins de 10 min sur un changement ordinaire. | La cible de 10 min n’est pas mesurée comme garantie. Les tests ciblés ne démontrent pas le comportement complet ni la couverture globale. |
| B — RELEASE VALIDATION | Suite standard permise et seuils de couverture inchangés : branches globales ≥80 %, modules P0 ≥90 %; vérifications API/CLI/compatibilité; wheel et sdist; Python 3.10 et 3.13; Ubuntu et Windows; artefacts/provenance. | Référence complète sur l’environnement retenu et compatibilité testée dans les autres cellules. | Remplacer les trois autres suites complètes par des tests ciblés baisse la couverture de chemins OS/Python et peut manquer des défauts dans les nodeids omis. |
| C — SCIENTIFIC V&V | Circuit séparé avec manifeste exact, contrôleur, entrées/oracles figés, budget, ledger et autorisation Owner. | Résultats scientifiques dans la portée exacte du manifeste. | Aucun déclenchement automatique de campagnes FEM depuis une validation PR. |

Comparaison des politiques :

| Politique | Couverture | Coût/temps connu | Défauts possibles non détectés |
|---|---|---|---|
| Historique : quatre suites complètes Ubuntu/Windows × Python 3.10/3.13 | La plus large exécution de suite sur la matrice; les quatre cellules donnent leur signal de tests. Le dernier run de référence a mesuré 84,75 % de couverture par branches, modules P0 à 100,00 % et 92,16 %. | Ubuntu 3.10 : 7 537,95 s; Ubuntu 3.13 : 7 120,37 s. Chaque Windows a atteint environ 10 682–10 725 s avant annulation à 180 min. Environ 10 heures de calcul agrégées, autour de 3 h de durée murale parallèle. | Les longues cellules Windows échouent à acquérir le résultat complet; elles ne donnent donc pas une matrice complète PASS. |
| Proposition : suite complète Ubuntu/Python 3.13, trois cellules de compatibilité ciblées | La couverture globale et P0 est mesurée par la suite de référence Ubuntu 3.13; les autres cellules testent uniquement les contrats/compatibilités choisis. Ce n’est pas équivalent à quatre suites complètes. | Non mesuré pour une release validation complète. Une suite Ubuntu 3.13 historique coûte environ 118,7 min; les coûts de ciblage et d’installation doivent être mesurés sur des nodeids déterminés. | Défauts uniquement déclenchés par des tests omis sur Ubuntu 3.10 ou Windows peuvent échapper à ces checks. La compatibilité générale dépend de la qualité du ciblage. |

**L’obligation historique des quatre suites complètes est NOT_ACQUIRED** jusqu’à acceptation explicite par l’Owner d’une politique différente. La proposition à trois cellules ciblées ne s’y substitue pas tacitement. Le workflow de qualité modifié stocke désormais les 20 durées les plus longues et le rapport JUnit pour rendre la prochaine suite diagnostiquable; cette instrumentation n’est pas un résultat de suite.

## 8. Matrice actualisée des gates

Les statuts sont utilisés strictement : PASS = preuve dans la portée revendiquée; FAIL = critère échoué; BLOCKED = la clôture ne peut avancer sans l’action indiquée; NOT_RUN = aucune exécution revendiquée; NOT_ACQUIRED = preuve ou autorisation requise absente.

| Gate | Statut | Preuve | Blocage | Action nécessaire |
|---|---|---|---|---|
| Identité initiale PR #114 / HEAD c06a669 | PASS | Fetch exact de la tête PR, identique au SHA fourni; base release ab137051. | Aucun pour l’identité initiale. | Garder l’identité de tête/artefacts dans les traces de suite. |
| Correctifs #115/#116 intégrés par #118 | PASS | Commit intégré 0a736a47; changements observés dans l’arbre WP13. | Aucun dans leur portée. | Conserver les tests réels de scan/archive et les cas numériques distincts. |
| Correctif de boucle Windows, Python 3.10 et 3.13 | PASS | Run #41325510873; chaque cellule a collecté les 64 nodeids épinglés et réussi les 65 occurrences bornées. | Ne couvre que les nodeids de gouvernance inscrits. | Utiliser le résultat pour ce correctif uniquement. |
| Contrats synthétiques du contrôleur WP12 | PASS | Run #41325515653, commit 8a8ed9b72. | Ne vaut pas suite WP12 ou qualification. | Aucune action additionnelle pour ce gate ciblé. |
| Instrumentation de diagnostics Windows | PASS | Ruff, py_compile, parsing/matrices, pin de blob; run #41326063607 PASS sur Python 3.10 et 3.13 au HEAD d4761299f; deux artefacts nommés par version. | Aucun dans la portée de ce diagnostic. | Garder les logs avec leur commit et leur version Python. |
| Rapport complet avec preuves de ce mandat | PASS | Ce rapport assemble les preuves relues, mesurées et les gates non acquis; le run final #41326063607 est inclus. | Les gates explicitement NOT_RUN/NOT_ACQUIRED/FAIL restent ouverts. | Conserver le statut WP13_PARTIAL_OR_BLOCKED; ne pas inférer une clôture. |
| Candidat de distribution, sélection v6 | PASS | SHA source v6 2865587a; aucun chemin sélectionné ni blob de contrat modifié par les changements WP13; détails §9. | N’englobe ni G03, ni licence, ni smoke calculatoire. | Garder le contrat v6 associé à ses artefacts. |
| Builds v6 wheel/sdist et contrôles d’archive | PASS | Wheel/sdist v6, scans sélectionnés, Twine et contrôles d’installation Windows/Python 3.13.1 consignés dans le rapport v6. | Pas de nouvel OS/Python d’installation; pas de licence indépendante. | Réutiliser uniquement pour l’identité de sélection inchangée. |
| Candidats smoke wheel/sdist (six tentatives) | NOT_ACQUIRED | Contrôleur et manifestes préparés; le dossier indique PREPARED_NOT_AUTHORIZED. | Autorisation distincte de la campagne absente. | Décision exacte Owner décrite §10; ne pas lancer sans elle. |
| Documentation publique sélectionnée | PASS | Sélection v3 : 773 documents, zéro constat de sélection; contenus inchangés depuis la preuve. | Ne purge pas les archives ni les fichiers hors sélection. | Maintenir la sélection et les contrôles de confidentialité. |
| G03, critère indépendant archive/dépôt | FAIL | Le rapport conserve AGENTS.md dans l’archive Git et les fichiers suivis docs/generated/results/*.json. | Critère indépendant non satisfait. | Corriger/qualifier le constat selon son critère propre; ne pas reclasser à partir des scans sélectionnés. |
| Quatre suites complètes historiques | NOT_ACQUIRED | Ancien run partiel : Linux complet; deux cellules Windows annulées après environ 180 min. Aucun run complet sur la tête courante. | Exigence historique non acquise; aucune politique de remplacement acceptée. | Run autorisé selon la politique retenue, ou acceptation explicite d’une politique modifiée par l’Owner. |
| Suite de référence et seuils de couverture sur la tête courante | NOT_RUN | Pas de suite complète ni de nouveaux rapports de couverture produits. | Aucun résultat courant ≥80 %/≥90 % à démontrer. | Après accord sur portée et gate, planifier une seule suite de référence. |
| Compatibilité complète OS/Python et installations wheel/sdist dans la matrice | NOT_RUN | Exécutions ciblées seulement; preuves d’installation v6 sur Windows 3.13.1. | Pas de preuve complète sur les quatre environnements. | Exécuter les cellules acceptées avec rapports de provenance. |
| Audit juridique indépendant des licences | NOT_RUN | Inventaire technique des versions/fichiers consigné; aucune décision juridique. | Compatibilité de redistribution non évaluée indépendamment. | Effectuer l’examen requis avant publication. |
| V&V scientifique / FEM / benchmarks / convergence | NOT_RUN | Aucune campagne scientifique lancée dans ce mandat. | Manifeste et autorisation campagne absents. | Circuit distinct avec gate Owner exact avant toute campagne. |
| Publication, tag, merge release/main | NOT_RUN | Aucun acte de publication, tag ou merge effectué. | Autorisation volontairement absente du mandat. | Une décision de release distincte reste nécessaire. |

**WP13 P0 demeure PARTIAL_OR_BLOCKED.** Les PASS limités ci-dessus ne constituent ni un P0 validé ni un feu vert de publication.

## 9. Compatibilité et identité des packages

Le contrat de sélection public v6 est lié à la source 2865587a44f9e461a0b4e4286c912c17e4f04be5, contrat QF-0212-WP13-SELECTED-CANDIDATE-20261031-06, SHA-256 f33a72b… Les diffs Git entre ce snapshot et le candidat WP13 audité ne montrent aucun changement dans les chemins sélectionnés par le contrat. Les révisions WP13 ajoutées après cette vérification touchent seulement les workflows, scripts d’infrastructure, tests et rapports internes; docs/ et sources distribuées sélectionnées sont inchangées.

Les sept outils épinglés par le contrat — audit_public_release.py, audit_release_archive.py, git_tools.py, plan_public_package.py, probe_installed_package.py, review_vocabulary.py et verify_public_package.py — ont les mêmes blobs Git attendus qu’au snapshot v6. L’identité des fichiers distribués est donc compatible avec les preuves v6 sans reconstruire les artefacts à partir d’une source différente.

Artefacts v6 consignés :

- Wheel : 1 689 662 octets, SHA-256 ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a.
- Sdist normalisée : 1 294 049 octets, SHA-256 183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde.
- 585 fichiers dans le wheel, 593 dans la sdist; zéro finding dans les surfaces sélectionnées; Twine 7.0 PASS.
- Installation fraîche Windows/Python 3.13.1 pour wheel et sdist; 501 fichiers source installés, version/aide CLI et six vérifications non résolvantes check-mesh PASS.
- Les octets bruts de sdist varient avec les métadonnées gzip; la comparaison documentée porte sur la sdist normalisée.

La version v6 de l’inventaire de dépendances a des versions différentes de la v4. Cela ne fournit pas de clearance juridique indépendante. Il n’y a ni smoke de solveur installé, ni nouvelle preuve Ubuntu ou Python 3.10. Le dossier smoke fixe un contrôleur (SHA-256 16df6eba0f902c332cace9e9a5624d1b8b59c3e051bfcc4063782123cc9a7f2f) et un manifeste (SHA-256 dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b); ils n’ont pas été modifiés. Les six tentatives statique, modale et dynamique × wheel/sdist restent préparées sans autorisation d’exécution.

## 10. Décisions Owner requises

1. **Politique Release Validation** — accepter explicitement soit l’obligation de quatre suites complètes, soit la proposition non validée (suite complète Ubuntu/Python 3.13 et compatibilité ciblée sur les trois autres cellules). Pour trancher, les quatre suites antérieures consommaient environ 10 h CPU agrégées et les deux cellules Windows n’ont pas terminé; la proposition abaisse la couverture de test large sur les trois cellules, et son coût total n’est pas mesuré.
2. **Six smoke tests installés** — autoriser séparément les six tentatives serialisées exactement prévues au dossier, sur les wheels/sdists et entrées/oracles figés, avec leur budget/contrôleur/ledger prescrits. Sans cette autorisation exacte, aucun calcul ne sera lancé. Ces résultats ne seraient que des smoke d’installation/correctness dans leur portée, jamais une qualification scientifique globale.

G03 reste un échec conservé jusqu’à satisfaction de son critère indépendant. La décision sur les suites complètes ne modifie ni G03, ni les résultats WP12, ni un seuil de couverture.

## 11. Risques résiduels

- Les anciennes durées de suite n’étaient pas par nodeid. Le profil complet actuel n’existe pas; les dix postes restent un classement historique des fichiers.
- Une source d’archive Git reste très coûteuse. Le diagnostic interrompu n’a pas établi un temps complet ni une amélioration.
- L’architecture de CI proposée ne détectera pas nécessairement les défauts qui n’apparaissent que dans les tests omis des cellules ciblées.
- Les scores de couverture et compatibilité complets de la tête courante ne sont pas acquis.
- Le smoke package, G03, les licences et toute qualification scientifique restent des gates indépendants.
- Les durées de scans sur le volume local et les temps locaux de tests ne prédisent pas directement les runners GitHub.
- Le résultat de test ne permet pas de publier, taguer ou fusionner dans la branche release.

## 12. Références de validation

- [PR #114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114).
- [Run Windows matrix #41325510873](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41325510873).
- [Run Windows final #41326063607 sur le HEAD d4761299f](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41326063607).
- [Run synthétique WP12 #41325515653](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41325515653).
- [Ancien run de référence complet/partiel #41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330).
- [Rapport candidat v6](./WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md).
- [Dossier smoke package](./WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md).
- [Rapport d’optimisation des tests](./WP13_TEST_SUITE_OPTIMIZATION_REPORT.md).

## Verdict final

**WP13_PARTIAL_OR_BLOCKED**

Les travaux d’ingénierie de performance autorisés et vérifiables ont été menés à bien, mais les critères de clôture ne sont pas démontrés. Les exigences de quatre suites complètes demeurent NOT_ACQUIRED; la politique de validation de release proposée n’a pas été acceptée; six smoke tests installés restent sans autorisation; G03 reste FAIL_PRESERVED; l’évaluation juridique des licences n’est pas faite. Aucun tag, merge de release ou publication n’a eu lieu.
