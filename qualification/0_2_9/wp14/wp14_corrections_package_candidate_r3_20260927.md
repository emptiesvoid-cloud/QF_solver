# WP14 — correctifs et paquet candidat R3

## Conclusion

**Paquet sélectionné : PASS_CANDIDATE_PACKAGE_ONLY. WP14 : HOLD.**

Les correctifs exécutables ont été appliqués et vérifiés. La campagne a aussi trouvé puis corrigé un défaut concret de distribution : quatre maillages d'exemple étaient présents dans le sdist mais manquaient dans le wheel. Le paquet ne contient pas les gros bruts internes.

Il ne serait pas exact de déclarer toute la release verte : les audits du dépôt entier et l'absence de quatre bruts historiques HEX8 restent bloquants. Aucun seuil numérique ni point officiel n'a été modifié.

## Provenance

- Branche : `codex/wp14-remediation-clean`.
- Base : `0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`.
- Source corrigée R3 : `074f6d14e1a2f7503892552bc492e8ed10ecd50a`.
- Exécution après gel : `d6a7a52bc46495107aba77f28335097af4ed6e92`.
- Contrat : `wp14_public_package_candidate_20260927_r3_contract.json`.
- SHA-256 du contrat : `a65e9b354c322ca83477b38ad57a1dc71a8087c0d61fba83466e608146e8e283`.
- Le commit contenant ce rapport est un checkpoint de preuves ultérieur, pas le SHA exécuté. Il se retrouve avec `git log -1 --format=%H -- qualification/0_2_9/wp14/wp14_corrections_package_candidate_r3_20260927.md`.
- Le précheck lié aux hashes impose un arbre propre, l'ascendance et l'absence de drift des sources sélectionnées/outils.
- Le workspace d'origine n'a pas été nettoyé ou modifié ; l'historique Git n'a pas été réécrit.

## Correctifs de ce lot

1. Outillage de sélection et de build fail-closed : blobs Git exacts, tous les inputs requis, aucune archive ambiguë ou donnée inconnue.
2. Couverture wheel ajoutée pour `examples/vnv_026_g06/*.json` : les quatre maillages sont désormais distribués à l'identique.
3. Probe corrigé : `-P` garde le cwd hors du chemin d'import tout en permettant les sites de dépendances déclarés. L'origine et les SHA-256 de QF restent contrôlés indépendamment.
4. Commandes réellement exécutées, PID, UTC, codes retour et journaux hashés ; manifestes et preuves lourdes dans l'archive externe.
5. Correctifs antérieurs conservés : Ruff, vocabulaire d'analyseur, objectif 700 lignes indicatif et contrôle de la lignée WP04-C acceptée.

Les tentatives R1 et R2 restent distinctes : R1 échoue sur les quatre données absentes du wheel ; R2 passe les archives/install/CLI mais échoue sur NumPy caché par `-I`. Elles n'ont pas été écrasées ni reclassées comme PASS.

## Résultats du paquet R3

| Contrôle | Observé | Statut |
|---|---|---|
| Sélection source | 551 fichiers Git liés aux hashes | PASS |
| Wheel/sdist | Aucun fichier sélectionné manquant ; aucun payload inattendu | PASS |
| Scans stricts | 0 constat sur la sélection et les deux archives | PASS |
| Wheel | 1 509 827 octets, environ 1,5 Mo hors dépendances | PASS |
| Sdist | 1 137 784 octets, environ 1,1 Mo | PASS |
| Installation QF | 473 fichiers de source installés rehashés | PASS |
| CLI | Versions des trois lanceurs et aide principale | PASS |
| Probe hors checkout | PID 43604 ; refus verify-all code 2 ; aucun rapport | PASS |
| Probe avec checkout comme cwd | PID 17532 ; même refus ; aucun rapport | PASS |
| Sous-processus pendant les checks CLI | 0 événement observé par le hook Python | PASS dans ce périmètre |
| Traçabilité | 9 commandes, toutes terminées avec code 0 ; 26 fichiers manifestés | PASS |
| Réhash du manifeste | 26/26 conformes, zéro divergence | PASS |

SHA-256 wheel : `50693a92f1c852a7a443f22e5cc4b09fb882eb928329a614bd8f92607f9bad1b`.

SHA-256 sdist : `0926e4073f9d9a5ab0bdb8f2ee6e4fb4ea27417ed8baaf58738bcaed059e8d9d`.

Le paquet porte **0.2.8**, conformément au contrat : il n'est ni publié ni présenté comme une release 0.2.9. Les fichiers runtime sont identiques à leur source gelée ; les hashes des binaires sont propres à cette construction, sans revendication de build byte-identique entre tentatives.

## Tests et limites de couverture

- **229 tests ciblés passés**, zéro échec/erreur, un avertissement indicatif de taille ; 31,04 s selon pytest.
- Ruff global `src/solveur tests scripts` : PASS.
- Mypy : PASS sur les deux nouveaux outils de paquet, pas une validation globale de tous les types.
- Compileall `src scripts tests` : PASS ; diff-check : PASS.
- Les arguments, UTC, PID, codes et JUnit/logs de cette vérification sont archivés.
- Suite complète et `verify-all` engineering non relancés. Aucune campagne structurelle de qualification n'a été relancée.
- Les probes ne démontrent pas le fonctionnement de chaque commande CLI ni une précision FEM globale.
- Dépendances système/utilisateur visibles : pas d'isolation totale. QF lui-même vient du venv et ses octets sont vérifiés.
- Hook Python pendant les checks CLI : pas une trace OS globale.
- README/changelog/citation et métadonnées sélectionnées seulement : pas de certification de toute la collection documentaire.

## Les dix points historiques

Le recheck à `652d7af6…` est archivé : **5 PASS, 5 FAIL**, avec JUnit hashé. Il n'a pas été présenté comme un résultat neuf après le correctif `-P`, qui ne touche que l'outillage du paquet.

| Point | Sujet | État |
|---|---|---|
| R01 | Objectif 700 lignes indicatif, dépassements visibles | PASS avec avertissement |
| R02 | Audit documentaire du dépôt entier | FAIL |
| R03 | Snapshot documentaire versus audit courant | FAIL |
| R04 | Hygiène des sources du dépôt entier | FAIL |
| R05 | Archive Git du dépôt entier | FAIL |
| R06 | Vocabulaire contrôlé | PASS |
| R07 | Déplacement WP04-C, lignée acceptée C2R6 | PASS, ancien échec préservé |
| R08 | Énergie WP04-C, lignée acceptée C2R6 | PASS, ancien échec préservé |
| R09 | Contrainte WP04-C, lignée acceptée C2R6 | PASS, ancien échec préservé |
| R10 | Quatre NPZ historiques HEX8 | FAIL : données introuvables dans la recherche bornée |

Un autre test de publication a été contrôlé : 12 PASS/1 FAIL dans `test_packaging.py`. Son échec vient du chemin réel de l'archive consigné dans un ancien rapport interne, contenant l'ancien nom du projet. Ce rapport est exclu du paquet mais reste conservé comme preuve. Ce constat n'a pas été masqué en modifiant le test ou le rapport.

**Les quatre audits du dépôt entier ne sont pas les mêmes gates que les scans du wheel/sdist.** Passer les seconds ne transforme pas rétroactivement les premiers en PASS et ne rend pas l'historique Git privé.

## Bruts HEX8

Recherche en lecture seule : **56 racines**, aucune erreur de lecture ; inventaires de **20 963 et 10 962 objets Git** dans deux magasins ; zéro candidat aux tailles attendues. Ces recherches ne prouvent pas l'absence d'une sauvegarde externe.

| Fichier manquant | Octets | SHA-256 attendu |
|---|---:|---|
| h1_raw.npz | 510 642 | 021fb16a46f369452f5aa0a8e913c1bd345eb3128df3cb5c5a1edce63805ab2d |
| h1_replay_raw.npz | 510 642 | 021fb16a46f369452f5aa0a8e913c1bd345eb3128df3cb5c5a1edce63805ab2d |
| h2_raw.npz | 1 635 806 | cdaf20e269e379e52d9888a618bad6b5bd8d7ca98dc20adbef1a7d54a1aaf3ee |
| h3_raw.npz | 3 761 002 | a595374adbabde01a1f297a6e221c73adeaf10f915dfd7f59af4b4bf455dd14b |

L'échec initial de lancement d'un inventaire, dû à un chemin d'exécutable incorrect, est classé séparément : aucun enfant lancé, pas un résultat de recherche. Les logs vides sont préservés ; l'inventaire réussi utilise ensuite l'exécutable découvert. Aucun résultat physique n'en dépend.

Je n'ai ni recréé les anciens tableaux, ni changé leurs hashes, ni utilisé un résumé comme substitut. Une nouvelle campagne donnerait une nouvelle provenance et ne prouverait pas la récupération des fichiers d'origine.

## Où sont les preuves ?

Racine contrôlée par `QF_SOLVER_EVIDENCE_ARCHIVE_ROOT`, sous `0_2_9/wp14/` :

- `package_candidate_20260927_r1/` : échec de contenu préservé.
- `package_candidate_20260927_r2/` : échec d'outillage préservé.
- `package_candidate_20260927_r3/` : sources liées, binaires, installation, probes, commandes, logs, manifeste.
- `tooling_validation_20260927_r2/` : recheck historique et échec de publication supplémentaire.
- `tooling_validation_20260927_r3/` : 229 tests et contrôles actuels avec manifeste d'intégrité.
- `historical_hex8_recovery_inventory_20260927/` : inventaires Git/filesystem et classement de l'échec de lancement.

Le JSON compagnon contient les SHA-256 exacts des manifestes et des preuves compactes. Les gros outputs et le venv ne sont pas ajoutés à Git. Le manifeste ne prétend pas figer tout le venv : il lie les binaires, sources, probes et journaux contrôlés.

## Gouvernance et prochaine action

```text
PACKAGE_R3 = PASS_CANDIDATE_PACKAGE_ONLY
OWNER_PACKAGE_ACCEPTANCE = PENDING
WP14 = HOLD / 0/1
OFFICIAL_TOTAL = 95/100
NUMERIC_THRESHOLDS_CHANGED = NO
NUMERICAL_SOLVER_KERNELS_CHANGED = NO
HISTORICAL_RAW_RESULTS_CHANGED = NO
FULL_REPOSITORY_SUITE_RUN = NO
GOVERNING_MERGE_PUSH_TAG_PUBLICATION = NO
```

1. Décision Owner sur le seul périmètre public R3 et ses limitations, puis réconciliation prospective des gates de publication ; aucun ancien FAIL n'est réécrit.
2. Fournir les quatre bruts depuis une sauvegarde, ou autoriser séparément une nouvelle lignée HEX8 gelée avant calcul, sans faire passer ses nouveaux artefacts pour les anciens.
3. Les autres gates R1 de qualité/engineering/documentation/plateforme/release gardent leurs propres preuves et ne sont ni requalifiés ni dispensés par ce lot.
