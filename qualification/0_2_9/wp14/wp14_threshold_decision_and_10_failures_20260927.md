# WP14 — Avis sur les seuils et plan de fermeture des dix tests en échec

Rapport d'aide à la décision du 27 septembre 2026. Statut : **ANALYSE, NON APPROUVÉE**.
Ce rapport ne constitue ni une décision Owner, ni une modification de contrat, ni une clôture de gate.

**Direction Owner postérieure à l'analyse :** l'objectif de 700 lignes devient
indicatif, sans plafond bloquant ; les dépassements restent inventoriés. Le
contrôle lexical strict reste applicable aux textes maintenus avec « analyse
Owner » / « Owner review ». Les recommandations initiales ci-dessous ne
remplacent pas cette direction. Son application et les contrôles réellement
exécutés sont décrits dans `wp14_maintainability_application_20260927.md`.
Les constats numériques historiques et leurs seuils restent inchangés.

## 1. Conclusion et recommandation

**Je recommande de conserver les seuils numériques gelés et de corriger d'abord les contrôles qui évaluent le mauvais périmètre ou la mauvaise génération de preuves.** Les dix tests échoués ne démontrent pas dix défauts mécaniques : ils se répartissent en cinq familles de problèmes.

| Famille | Tests échoués | Nature | Recommandation |
| --- | ---: | --- | --- |
| Budget de taille des sources | 1 | Architecture et maintenance ; 39 fichiers dépassent leur budget | Refactoriser le code actif sans changer son comportement ; traiter individuellement les sources historiques gelées |
| Audits de publication | 4 | Mélange entre dépôt de preuves et produit distribuable | Définir prospectivement une sélection publique exacte, garder les scanners stricts et conserver les anciens échecs |
| Vocabulaire de revue | 1 | Contrôle lexical trop large ; cinq fichiers concernés | Distinguer une approbation Owner d'un texte simplement destiné à être lu |
| Convergence TET4 historique | 3 | Ancienne campagne grossière réellement FAIL, mais différente de C2R6 accepté | Tester séparément la préservation de l'échec historique et les gates de la qualification active |
| Bruts HEX8 absents | 1 | Disponibilité/intégrité des preuves, non échec de résolution | Retrouver les octets exacts ; sinon conserver HOLD et prévoir une nouvelle preuve explicitement distincte |

Les correctifs de contact vérifiés dans la précédente reprise ne sont plus dans ces dix échecs. Je ne recommande pas de rouvrir WP07/WP08 à partir de ce seul inventaire.

**WP14 reste HOLD à 0/1 ; le ledger officiel reste à 95/100.** Même la résolution des dix tests ne suffira pas, à elle seule, à prononcer la clôture de WP14 : les commandes complètes de qualité, engineering, documentation et packaging devront être attestées sur le candidat final.

## 2. Périmètre et force probante de cette analyse

État inspecté avant création de ce rapport :

- Branche : `codex/wp14-remediation-clean`.
- HEAD : `0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`.
- Arbre : propre avant rédaction.
- Base d'exécution du recheck précédent : `28459d726ec00676519821836dbd136a86d5b2ba`.
- Governing local : `0.2.9-unified-nonlinear` à `28459d726ec00676519821836dbd136a86d5b2ba`.
- Remote-tracking ref observée, sans nouveau fetch : `origin/0.2.9-unified-nonlinear` à `da1ed3d08c5a61d033e3b492f76ac34432bc2f08` ; governing local dix commits devant.

La reprise précédente a exécuté 13 nœuds ciblés : **3 PASS, 10 FAIL**, en 603,82 s. Le fichier `wp14_r23_open_nodes_recheck_28459.json` conserve leurs identités et les valeurs observées. Son SHA-256 est `813357ac845f2d672be15869d8f6ec870d55a8e699e635bff9ffdfa5bf7085c6`.

Important : les assertions WP04-C de cette reprise utilisaient une campagne recalculée en mémoire, pas uniquement un ancien résumé JSON. Le writer de campagne n'a pas été invoqué. Ce rapport n'a relancé ni cette campagne, ni un solve, ni pytest.

Pour la présente analyse, les opérations ont été : lecture des sources/contrats/objets Git, scans statiques source et `git archive`, inventaire de métadonnées, recomputation de deltas à partir de valeurs archivées, et vérification SHA-256 des sept fichiers de l'archive récupérée. Aucun historique n'a été réécrit. Aucune correction de code, aucun seuil, ledger, commit, merge ou push n'a été effectué.

Les nouveaux résultats statiques sont capturés dans le snapshot JSON accompagnant ce rapport. Ils ne sont pas présentés comme une campagne de qualification pré-gelée : il n'y a pas de nouveau manifeste de processus ou de journal JUnit pour ces lectures. Le résumé du recheck précédent ne remplace pas non plus un journal brut/processus complet pour une future clôture WP14.

## 3. Décision sur le seuil de 700 lignes

### Ce que ce seuil signifie réellement

`tests/unit/test_architecture_rules.py` fixe `MAX_SOURCE_LINES = 700`. Le test compte toutes les lignes physiques, y compris les commentaires, docstrings et lignes vides, dans `src/solveur`, `scripts` et `tests`. Neuf exceptions nominatives existent déjà, avec un budget individuel plus élevé.

**Ce n'est pas un seuil mécanique ou numérique.** Un fichier de 701 lignes n'est pas physiquement faux et un fichier de 699 lignes n'est pas automatiquement bien conçu. Le garde vise la lisibilité, les responsabilités des modules et la facilité de régression ; le comptage reste un indicateur approximatif.

L'inventaire actuel constate 39 dépassements hors exceptions existantes :

| Zone | Fichiers hors budget | Exemples |
| --- | ---: | --- |
| Produit `src/solveur` | 9 | `contact/slip_root.py` : 1 955 ; `core/nonlinear/robustness.py` : 1 548 ; `core/audit.py` : 1 332 |
| Outillage `scripts` | 26 | `wp07d_execution_binding.py` : 2 243 ; plusieurs runners contact/référence |
| Tests | 4 | tests mixed open/active-slip : 1 104 ; campagne historique WP04-C : 881 |

### Options et mon avis

| Option | Effet | Avis |
| --- | --- | --- |
| Relever globalement 700 vers 2 000 ou davantage | Fait disparaître certains symptômes et autorise une croissance supplémentaire de tous les modules | **Déconseillé** : aucun argument de maintenance ne justifie de caler la limite sur le plus gros fichier actuel |
| Ajouter une exception à chacun des 39 dépassements | Faible travail immédiat, dette générale sanctuarisée | **Déconseillé comme solution globale** |
| Retirer complètement le garde | Supprime le contrôle, pas la complexité | **Déconseillé** |
| Garder 700 pour le code actif, refactoriser par responsabilités ; exceptions exactes pour les sources réellement gelées | Corrige la cause et respecte la traçabilité | **Recommandé** |

Il faut d'abord classer chaque script : archive figée, runner encore actif ou outil courant. Le fait de porter un nom WP ne suffit pas à justifier une exception.

Pour une archive figée, une exception peut être raisonnable si elle lie explicitement le chemin, le SHA source ou SHA-256, le budget exact sans croissance et la dette associée. Elle ne doit pas couvrir arbitrairement tous les scripts ou toute la qualification.

Pour le produit actif, la bonne correction est un découpage fonctionnel : gestion des états/ensembles contact, construction du problème stick-slip, calcul de résidus, validation d'admissibilité et télémétrie. Il faut vérifier les dépendances réellement présentes avant de choisir les frontières. Un découpage cosmétique en fichiers sans responsabilités cohérentes n'apporte pas la garantie recherchée.

Un refactor sans changement de comportement n'est pas automatiquement un changement de formulation physique. Il change néanmoins l'identité source. La validation devra donc comprendre : mêmes signatures et imports publics, mêmes tests présents, déterminisme, transitions/rollback, indépendance des références, et comparaison d'observables sur des petits cas ciblés. Les décisions et SHAs historiques restent intacts ; un nouveau binding ne doit pas prétendre que l'ancienne exécution utilisait les nouveaux fichiers. Un rerun intégral de toutes les qualifications n'est pas automatiquement nécessaire : l'analyse d'impact doit en déterminer le besoin.

**Décision suggérée : conserver 700 pour les sources actives, autoriser un refactor purement structurel et examiner séparément les seules exceptions historiques justifiées.** Aucune modification du garde n'a été faite ici.

## 4. Décision sur les seuils numériques TET4

### Le point central : deux campagnes différentes

Les trois tests en échec recalculent l'ancien WP04-C, avec maillages parents `8×4×4`, `16×8×8`, `24×12×12`. Ils exigent toujours un PASS de cette campagne dont le résultat FAIL est expressément conservé dans la clôture WP04-F.

Le dossier actif WP04-F, `qualification/0_2_9/wp04f/wp04_final_closure_audit.json`, cite pour G04-10 **C2R6 M2/M3**, maillages `48×24×24` et `64×32×32`, et non cette ancienne paire grossière. Le SHA-256 du dossier WP04-F lu ici est `3bb1bbf9e0e0d9252bec3bc28d64174546484a913c19b7d926aafa61620c7533`.

| Observable | Ancien WP04-C recalculé | Seuil gelé | C2R6, paire retenue dans WP04-F |
| --- | ---: | ---: | ---: |
| Déplacement | 16,406181 % — FAIL | 2 % | 1,692701 % — PASS |
| Énergie | 16,379509 % — FAIL | 2 % | 1,689047 % — PASS |
| Contrainte représentative | 24,310580 % — FAIL | 10 % | 2,164607 % — PASS |

Les trois anciennes valeurs dépassent respectivement leur seuil d'environ 8,20×, 8,19× et 2,43×. Ce n'est pas une fluctuation d'arrondi autour de la limite.

### Dénominateurs : ne pas confondre les conventions

L'ancien helper `_relative_scalar(fine, medium)` divise par `max(abs(medium), 1e-12)`. L'audit C2R6 déclare `abs(fine-medium)/max(abs(fine),abs(medium),1e-12)`.

Ces définitions doivent rester attachées à leur révision : ce ne sont pas exactement les mêmes métriques. Une vérification de sensibilité, sans modifier les contrats, donne pour C2R6 **1,721846 % / 1,718066 % / 2,212499 %** avec le dénominateur medium de l'ancien helper. Les trois resteraient PASS. Le franchissement des seuils n'est donc pas créé ici par le seul choix du dénominateur.

### Pourquoi l'ancienne paire échoue

Le diagnostic existant WP04-C1 fournit une explication plus forte qu'une hypothèse improvisée : déplacement et énergie évoluent presque pareil dans les calculs linéaires et non linéaires. Les rapports de variation linéaire/non linéaire sont environ 1,0030 et 1,0047. Cela situe la difficulté principalement dans la discrétisation TET4 du cas de flexion, plutôt que dans un défaut apparu avec la petite déformation finie.

Le même diagnostic constate aussi que le volume de la fenêtre de contrainte sélectionnée par centroïdes varie entre maillages. Cela peut perturber la contrainte moyenne, mais ne peut expliquer les deux échecs indépendants de déplacement et énergie. Ni verrouillage, ni défaut de formulation Total-Lagrangienne ne sont démontrés par ce constat seul.

Cette interprétation est compatible avec la documentation officielle Abaqus : les tétraèdres linéaires peuvent demander des maillages très fins pour atteindre une précision utile. Cette source décrit Abaqus, pas une preuve indépendante de QF ; elle renforce une explication générale sans remplacer les données locales. [Documentation Abaqus — choix des éléments continus](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEGSARefMap/simagsa-c-ctmselecting.htm).

### Ce qu'un gate de 2 % prouve et ne prouve pas

Le gate exprime une variation entre deux maillages de la hiérarchie figée, **pas une garantie universelle d'erreur physique inférieure à 2 %**. Le taux de raffinement, l'ordre observé et le régime asymptotique comptent. La méthode NASA de Richardson/GCI distingue précisément la différence entre maillages d'une estimation d'erreur de discrétisation. Son contexte est CFD ; le principe est pertinent pour réfléchir à une vérification de convergence, pas pour importer automatiquement un seuil dans QF. [NASA — convergence spatiale](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html).

Illustration seulement : pour la paire C2R6, `r = 64/48 = 4/3`. En supposant, sans le démontrer, un ordre `p=2`, l'estimateur simplifié `delta/(r^p-1)` serait environ 2,18 % pour un delta de 1,69 %. **Ce n'est ni un nouveau gate, ni une estimation certifiée de l'erreur QF** ; cela montre pourquoi « delta ≤2 % » ne signifie pas automatiquement « erreur exacte ≤2 % ».

Il faut aussi séparer quatre contrôles :

- convergence Newton/linéaire : résolution du problème discrétisé ;
- équilibre force/moment : cohérence du bilan mécanique sur ce problème ;
- convergence de maillage : sensibilité de la réponse à la discrétisation ;
- corrélation externe/validation physique : contrôle distinct, non déduit des trois premiers.

Rendre Newton ou MINRES plus strict ne corrige pas automatiquement un TET4 trop grossier. Inversement, un excellent équilibre ne suffit pas à démontrer un déplacement précis.

### Correction recommandée, sans changement de seuil

1. Conserver le contrat, les trois valeurs FAIL et les résultats WP04-C historiques.
2. Transformer la vérification de cette histoire en contrôle explicite de préservation/non-reclassification : elle doit réussir parce qu'elle reconnaît correctement le FAIL, pas parce qu'elle prétend que les maillages grossiers satisfont 2 %.
3. Ajouter ou renforcer séparément les contrôles du dossier actif C2R6 : contrat, lineage, source/policy, hashes, deltas, enveloppe et équilibre. Les tests WP04-F existants contrôlent déjà les deltas du dossier ; un contrôle d'intégrité des entrées est plus fort qu'un simple résumé PASS.
4. Si une recomputation live de WP04-C grossier reste utile, la garder dans une campagne historique explicitement nommée ; ne pas la supprimer ou lui attribuer artificiellement PASS dans une suite release.
5. Figer prospectivement cette organisation des tests. Elle ne remplace pas un ancien échec R1 par un succès rétroactif.

Les sept fichiers de l'archive récupérée ont été rehashés : 7/7 conformes. Ils comprennent le `frozen_threshold_audit.json`, le `campaign_result.json` et le `m3_result.json` C2R6. Cela ne constitue pas ici une réinspection exhaustive de toutes les anciennes télémétries ou une nouvelle exécution C2R6.

**Mon avis : ne relever ni 2 % vers 20 %, ni 10 % vers 25 %. Corriger la sélection de campagne et la sémantique des tests historiques.**

## 5. Les dix erreurs, une par une

| ID | Test actuel | Cause établie | Preuve nécessaire pour sa fermeture |
| --- | --- | --- | --- |
| R01 | `test_architecture_rules.py::test_python_source_files_stay_within_product_or_frozen_evidence_budgets` | 39 fichiers hors budgets | Aucun dépassement hors exceptions nominatives justifiées ; tests de comportement après refactor |
| R02 | `test_public_document_audit.py::test_public_document_audit_passes_without_web_delivery_or_internal_paths` | Le scan courant de publication FAIL ; vocabulaire large FAIL | Audit strict du périmètre public approuvé ; liens/claims accessibles ; vocabulaire de décision correctement contrôlé |
| R03 | `test_public_document_audit.py::test_controlled_public_document_audit_record_matches_current_classification` | Le nouveau scan FAIL alors que le snapshot historique doit rester PASS | Ancien record 0.2.7 intact, nouveau record source-bound distinct et PASS sur son périmètre approuvé |
| R04 | `test_public_release_audit.py::test_current_public_release_candidates_are_clean` | 5 866 constats dans la sélection large | Zéro constat sur l'ensemble exact réellement publié, sans assouplir les regex |
| R05 | `test_public_release_audit.py::test_current_git_archive_excludes_runtime_and_private_evidence_trees` | L'archive HEAD contient les mêmes constats | Archive réellement distribuée, sélection/mapping/hashes attestés ; ancien `git archive HEAD` reste classé FAIL |
| R06 | `test_review_vocabulary.py::test_published_sources_use_controlled_review_vocabulary` | Recherche de sous-chaînes qui assimile texte lisible et revue Owner | Tests négatifs sur les approbations ambiguës et tests positifs sur le vocabulaire normal d'interface ; archives gelées non réécrites |
| R07 | `test_wp04_c_tet4_structural.py::test_c05_mesh_displacement_convergence` | Ancienne paire grossière : 16,406181 % >2 % | Échec ancien conservé ; gate actif C2R6 vérifié séparément |
| R08 | `test_wp04_c_tet4_structural.py::test_c07_mesh_energy_convergence` | Ancienne paire grossière : 16,379509 % >2 % | Même traitement ; aucun relèvement du seuil |
| R09 | `test_wp04_c_tet4_structural.py::test_c08_mesh_representative_stress_convergence` | Ancienne paire grossière : 24,310580 % >10 % | Même traitement ; définition de fenêtre attachée à chaque contrat |
| R10 | `test_wp04_d_hex8_structural.py::test_raw_hex8_arrays_are_reproducible_and_do_not_use_object_arrays` | Quatre NPZ requis absents du checkout | Octets exacts retrouvés et vérifiés, ou nouveau dossier prospectif explicitement distinct ; jamais un faux remplacement du hash historique |

### R02 à R05 : publication, pas résolution FEM

Les scans exécutés pendant cette analyse, avant rédaction du rapport, donnent :

| Objet inspecté | Fichiers | Constats | Statut |
| --- | ---: | ---: | --- |
| Sources candidates actuelles | 4 456 | 5 866 | FAIL |
| `git archive HEAD`, attributs courants | 5 602 | 5 866 | FAIL |

Répartition des 5 866 constats : 2 811 marqueurs de chemin de poste, 2 811 de contexte privé, 243 de workflow interne, 1 marqueur email. **Un même emplacement peut produire deux constats : ce ne sont pas 5 866 bugs distincts.** Le scan ne trouve pas de marqueur `credential` dans le périmètre inspecté ; cela n'atteste pas la totalité de l'historique Git.

Par zone : `qualification` 5 762, `docs` 73, `scripts` 26, `src` 1, `tests` 4. Environ 98,23 % des constats sont dans les dossiers de preuve. Le seul constat produit est dans `src/solveur/verification/j2_multifamily_performance.py` : une référence de branche de campagne ; ce fichier était déjà exclu du périmètre public R2.3.1. L'email détecté se trouve dans une fixture de test de prémerge ; il ne faut pas assimiler automatiquement cette catégorie à une fuite d'identité réelle sans inspection du contexte.

Le scan documentaire actuel comporte deux sous-contrôles déjà PASS : absence de runtime web et absence des préfixes internes explicitement classés dans l'index. L'hygiène de publication et le vocabulaire restent FAIL.

La solution cohérente avec la préservation des preuves est :

1. conserver le dépôt d'ingénierie et les archives brutes inchangés ;
2. sélectionner le paquet/site public par une liste exacte figée au SHA courant ;
3. lier chaque fichier sélectionné au blob Git et à son SHA-256 ;
4. exclure des binaires distribués les sorties runtime et les campagnes internes, sans casser les commandes promises ;
5. scanner le staging, le wheel, le sdist et toute archive source réellement publiée avec les règles strictes ;
6. vérifier les imports et chaque commande distribuée dans un environnement d'installation ;
7. conserver la garde `verify-all` réservée au checkout source complet, déjà corrigée, et la documenter dans le paquet.

**Ne pas remplacer simplement `assert status == PASS` par une assertion qui accepte FAIL.** Le périmètre nouveau nécessite un contrat prospectif explicite et des tests qui démontrent la sélection, la couverture et les rejets. Les anciens gates R1 sur le dépôt entier restent FAIL dans leur dossier historique ; ils ne deviennent pas PASS rétroactivement.

Attention : `.gitignore`, `export-ignore` ou un petit wheel empêchent certaines données d'entrer dans un paquet, **pas de rester accessibles dans un dépôt Git déjà publié ou dans son historique**. Si le dépôt d'ingénierie doit lui-même être rendu public, cette question requiert une décision spécifique ; la présente proposition ne réécrit pas l'historique.

### R06 : vocabulaire et décision Owner

Le test interdit les anciens termes génériques de revue. Cinq fichiers déclenchent ce contrôle : des textes maintenus et un token contractuel historique. La terminologie de cette copie de travail a été alignée sur « analyse Owner », sans modifier les données ni le constat initial.

Ce sont des usages de lisibilité, pas la preuve d'une approbation générique qui se substituerait à une décision Owner. La politique documentaire distingue déjà `automated_verification`, `owner_review` et `external_audit` : cette distinction doit rester.

La décision Owner postérieure à cette analyse exige de corriger aussi les formulations des textes actifs, y compris les docstrings, sans aucun effet numérique. Le contrôle lexical strict est conservé ; aucune formulation générique nouvelle n'est autorisée.

Le token d'un contrat historique gelé ne doit pas être remplacé silencieusement : une exemption exact-hash pour ce document historique ou un addendum prospectif est préférable. Ajouter une exclusion générique à toute la qualification serait trop large.

### R10 : disponibilité des preuves HEX8

Les quatre fichiers absents sont `h1_raw.npz`, `h1_replay_raw.npz`, `h2_raw.npz` et `h3_raw.npz`. Le premier attendu pèse 510 642 octets et doit avoir le SHA-256 `021fb16a46f369452f5aa0a8e913c1bd345eb3128df3cb5c5a1edce63805ab2d`.

Le test contrôle les coordonnées, connectivités, déplacements, l'absence de tableaux `object`, la finitude et l'identité des octets. Les JSON de résultats ne suffisent pas à remplacer ce contrôle des états bruts.

Les chemins H1 et H3 n'existent pas non plus comme blobs à `70e1bf953c8e6f37b8070e78ca97e58b21499291`, SHA de référence de l'audit WP04-F. Le dossier de clôture contient des digests déclarés, mais une déclaration de digest ne restitue pas les données. L'absence au SHA d'audit signifie que compter uniquement sur un checkout Git de ce commit ne garantit pas la récupération.

Ordre recommandé : inventaire ciblé des archives/restes de worktrees, recherche par taille/hash, contrôle des quatre charges utiles avec `allow_pickle=False`, manifeste externe immuable et resolver explicite pour les tests. Le resolver déjà ajouté aux preuves récupérées est un exemple utilisable, mais son manifeste actuel ne contient pas ces quatre NPZ.

Si les octets originaux restent introuvables, deux choix honnêtes : conserver la gate d'intégrité en HOLD, ou geler une nouvelle campagne de récupération/requalification qui produit de nouveaux hashes et conserve l'ancienne lacune. **Un rerun peut produire une nouvelle preuve ; il ne prouve pas l'intégrité d'un fichier historique disparu.** Aucun fichier brut n'a été régénéré dans cette analyse.

## 6. Autres gates WP14 : ce que les dix erreurs ne couvrent pas

La liste de dix vient de 13 nœuds anciennement ouverts ; ce n'est pas la totalité du contrat de release.

| Gate | Situation à considérer | Condition avant fermeture |
| --- | --- | --- |
| G01 Provenance | Branche d'analyse propre avant rédaction ; futur code non encore gelé | SHA source exact, contrat prospectif, chronologie, arbre final propre et manifestes vérifiés |
| G02 Ledger | WP14 0/1 et total 95/100 cohérents ; libellé WP14 `NOT_STARTED` encore présent | Mettre à jour le statut descriptif au moment approprié, sans attribuer le point avant Owner |
| G03 Claims/registry | Séparer périmètre interne/public et vérifier chaque portée | Aucun surclassement ; références résolubles ; limites et échecs visibles |
| G04 Qualité | Tests ciblés ne prouvent pas toute la qualité standard | Ruff global, mypy progressif, tests standard, couverture ≥80 %, contrôle P0, compileall et quick verifications selon le contrat |
| G05 Engineering | Les dix nœuds ne remplacent pas un `verify-all` complet réussi | Profil engineering complet ; chaque échec attribué ; aucun désélectionnement ad hoc |
| G06 Documentation | Lacunes actuelles différentes de l'ancien inventaire | Métadonnées, registre, références et builds/tests documentaires stricts ; approbations non inventées |
| G07 Paquet/source publique | Frontière CLI corrigée, publication large toujours FAIL ; version actuelle 0.2.8 | Contrat de portée explicite, build/install/CLI/scans/hashes ; version release changée seulement avec décision distincte |
| G08 Plateformes | Aucune matrice complète exécutée ici | Chaque leg réellement exécuté ou conservé NOT_RUN ; aucune CI supposée |
| G09 Autorité release | Aucune décision de clôture WP14 par cette analyse | Owner séparé pour point, merge/push autorisé, tag et publication ; pas de release implicite |

### G06 : inventaire frais, pas les anciens 63/87 recopiés

Le registre courant contient **436 documents**, contre 495 dans l'ancien inventaire de la branche divergente. Son SHA-256 est `5878f85bffeabf31374ddfc85eaea9d1146da3f8e5413ef3813812bcbb68dabc`.

La lecture actuelle trouve :

- 13 documents dont les métadonnées ne peuvent être lues par le parseur courant ;
- 13 documents lisibles avec au moins une clé requise absente ; `reviewer` et `approver` manquent dans les 13, `applicable_version` dans un ;
- 76 documents aux statuts contrôlés sélectionnés par la règle d'inventaire avec reviewer/approver incomplets parmi les documents lisibles.

Les 76 ne sont pas nécessairement disjoints des 13 à champs absents. Les documents non lisibles ne sont pas inclus dans ce compteur ; il ne représente pas une attestation exhaustive des revues manquantes.

La présence d'une clé et une approbation sont deux choses différentes : un document préparatoire peut honnêtement porter `reviewer: ""` et `approver: ""` si sa revue reste PENDING. En revanche, un document présenté comme Owner-accepté doit référencer la vraie décision, son identité, sa date et son périmètre. Ne pas remplir tous les champs avec `Owner` par défaut.

Les rapports historiques gelés peuvent être accompagnés d'une enveloppe documentaire/addendum traçable. Si une nouvelle version corrige seulement leur front matter, il faut conserver les anciens octets et déclarer cette nouvelle révision, non remplacer une preuve gelée sans trace.

## 7. Plan conseillé, dans l'ordre

1. **Séparer les lignées WP04** : échec C ancien préservé, gate actif C2R6 contrôlé. Cela traite R07–R09 sans modifier la mécanique ou les seuils.
2. **Chercher les NPZ historiques** et qualifier leur disponibilité. C'est le seul des dix points qui peut rester bloqué faute d'octets récupérables ; ne pas promettre sa fermeture avant récupération.
3. **Classer les périmètres de publication et de vocabulaire** ; définir un nouveau contrat et sa sélection exacte. Réutiliser le travail R2.3.1 comme base technique, pas comme PASS rétroactif de R1.
4. **Réduire les neuf gros modules produit**, puis les quatre modules de test, avec préservation de toutes les assertions. Classer les 26 scripts avant refactor/exception ; ne pas augmenter globalement 700.
5. **Corriger G06** avec un inventaire versionné des champs et des vraies décisions ; refaire le registre et les builds documentaires.
6. **Geler le candidat consolidé** avant exécution des gates de qualité/engineering/build concernées. Une évolution autorisée de l'organisation des tests doit figurer dans le contrat de cette nouvelle exécution.
7. **Rejouer d'abord les contrôles ciblés, puis les jobs complets exigés**. Enregistrer pour chaque commande argv exact, UTC début/fin, exit code, log et hash, exclusions prévues avant résultats, et raison des skips.
8. **Soumettre WP14 à Owner** uniquement si les gates obligatoires du nouveau contrat passent et les limites restantes sont recevables. Aucun point n'est attribué par un checker.

## 8. Décisions proposées — non enregistrées comme acceptées

| Décision | Mon avis | Conséquence |
| --- | --- | --- |
| Garder les seuils WP04 2 % / 10 % | YES | Aucun relâchement de précision pour effacer un ancien échec |
| Tester séparément la préservation de WP04-C et la qualification C2R6 | YES, avec contrôle des hashes/contrats | Répare le contrôle de lineage, pas les anciens nombres |
| Garder 700 sur le code actif et autoriser le refactor sans changement comportemental | YES | Fermeture architecture par réduction de dette |
| Exceptions exactes pour les seuls runners historiques immuables | YES, examen individuel | Préservation des sources de campagne, sans nouveau budget global |
| Distinguer dépôt de preuves et distribution publique par mapping exact | YES, contrat prospectif | Produit léger et traçable ; dépôt interne non réécrit |
| Relâcher les scanners de publication | NO | Les marqueurs interdits restent interdits sur la distribution |
| Accepter un résultat absent comme `NOT_APPLICABLE` ou PASS | NO | R10 reste HOLD si les octets nécessaires sont indisponibles |
| Fermer WP14 maintenant | NO | Qualité/engineering/docs/packaging complets encore à démontrer |

Ces propositions sont distinctes d'une autorisation de rerun coûteux, de changement de seuil, de publication ou de suppression de preuves. Le présent travail s'arrête à l'analyse et à la rédaction demandées.

## 9. Références principales inspectées

- `tests/unit/test_architecture_rules.py` : budgets et périmètre réel du comptage.
- `tests/unit/test_public_document_audit.py`, `test_public_release_audit.py`, `test_review_vocabulary.py` : assertions en échec.
- `scripts/audit_public_documents.py`, `audit_public_release.py`, `audit_release_archive.py` : fonctions de scan, sans utilisation de leurs writers.
- `qualification/0_2_9/wp04_c_tet4_campaign.json`, `wp04_c_tet4_structural_summary.json` : original FAIL.
- `docs/verification/0_2_9/wp04-c1-tet4-mesh-diagnosis.md` : diagnostic de discrétisation et fenêtre de contrainte.
- `qualification/0_2_9/wp04f/wp04_final_closure_audit.json` : gates et lineage C2R6/HEX8 acceptés dans la clôture existante.
- `qualification/0_2_9/wp14/wp14_r23_recovered_evidence_manifest.json` et ses sept entrées récupérées : vérification fraîche des hashes.
- Contrats WP14 R1 et R2.3.1 lus depuis les objets Git de `ed300b981e309dad09b9d9b1e30aa75e00b3cb67` ; ils ne sont pas implicitement promus comme le contrat d'une future campagne.
- Sources primaires scientifiques liées dans la section 4 ; consultées le 27 septembre 2026. Aucun article ne fournit un seuil universel de 2 % pour ce benchmark particulier.

**Statut final : ANALYSIS_COMPLETE / WP14_HOLD / NO_THRESHOLD_CHANGE / NO_OWNER_AWARD.**
