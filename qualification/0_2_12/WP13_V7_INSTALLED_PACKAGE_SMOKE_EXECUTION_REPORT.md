# WP13 v7 — rapport d’exécution des smoke tests sur packages installés

Date d’exécution : 2026-11-01
Dépôt : `emptiesvoid-cloud/QF_solver` · PR #114
Branche : `codex/wp13-release-engineering-20261031`
HEAD contrôlé : `d0a3df9bd7265429d433b44560c0cd0606aedbf0`

## Verdict

**`WP13_V7_INSTALLED_PACKAGE_SMOKES_PASS`**

Les six exécutions et les six oracles numériques ont passé dans la portée exacte des trois cas et des deux artefacts installés. `qualification_status` reste `NOT_CLAIMED`. Ce résultat ne vaut pas qualification scientifique globale ni clôture WP12/WP13.

## Identités vérifiées

| Élément | Identité |
|---|---|
| Source package v7 | `7a78cc673da2abb7c3d0afd6cabd378aa327f424` |
| Contrat v7 | SHA-256 `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43` |
| Manifeste rebind | SHA-256 `4a9398df42b52d1e088d640a6896b6e00873f479f77cf8fdec01310809ffa9cb` |
| Préflight principal | SHA-256 `01795a37ef09d67a4bd653fd34aca98d0aadee1eb23cec3ba826c63f0b20cd46` · `PASS_NO_FEM_PREFLIGHT` |
| Préflight synthétique | SHA-256 `7790f26725a4b9f56bcb6862de88952c279384b05e521d4b77b9908f8256187e` · `PASS_NO_FEM` |
| Ledger synthétique | SHA-256 `09b173088615a6039af701481b48b32fdf8c8e4c16b86ed9caac53da1296dd9c` |
| Décision Owner | `OWNER-WP13-V7-SIX-SMOKES-HEAD-D0A3-01`; SHA-256 `a692c5d65e18f806b655eb4cd1070c62627b976227f9e40a0fc574fb5ee1ee1c` |
| Contrôleur | SHA-256 `cba01759b5b3b1cc41cfcc23c405adef55a6cccdaffcec85ac4a057b8b7e2ed7` |
| Wheel | SHA-256 `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518` |
| Sdist normalisée | SHA-256 `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174` |
| Hôte / environnement | Windows 10 · Python 3.13.1 · QF Solver 0.2.12, installé séparément depuis chaque artefact |

Les trois entrées installées sont identiques entre wheel et sdist :

| Cas | Entrée | SHA-256 |
|---|---|---|
| STATIC-01 | `tet4_static.json` | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` |
| MODAL-01 | `tet4_modal_unit.json` | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` |
| DYNAMIC-01 | `tet4_dynamic_sdof_free_vibration.json` | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` |

Les sources d’oracle de la source v7 ont été vérifiées contre leurs blobs SHA-256 : `analytical_references.py` `38ae37e1ff40844eedf7c2ca5b95d9d03f3fe660670036b05895c5043c96fb6c`; `campaign.py` `ea06968dc65927791549d698d19eeae33b6a3ad3e466ed2da0b87ae45e8952f1`; `qualification/campaign.json` `8750d29a9d52498ec5051f4850c600232b0e7a4515905a8354f4a34771fd92cf`.

## Résultats des six tentatives

| # | Artefact | Cas | Entrée SHA-256 | Tentative | Exécution | Oracle numérique | Durée murale (s) | RSS maximale (octets / MiB) | Résultat SHA-256 |
|---:|---|---|---|---:|---|---|---:|---:|---|
| 1 | wheel | STATIC-01 | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.917 | 119304192 (113.78 MiB) | `3d383f560a999898b55abb7d2d02e3293de4eefc01d4fb7eb31aacfe231209ad` |
| 2 | wheel | MODAL-01 | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.854 | 119517184 (113.98 MiB) | `4e40dff8b385cddd4fef0744cf178d7b6ad4193bf47e1014322134b0836958ce` |
| 3 | wheel | DYNAMIC-01 | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.926 | 119152640 (113.63 MiB) | `aae2901fcfa2cfffdfedcf99b0c23406fd044b25579913448436449001a9614b` |
| 4 | sdist | STATIC-01 | `5296102b955ae4ac83b341178a8a555feb87faa0e9a30abe9f77c29df21988b8` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.924 | 119107584 (113.59 MiB) | `eef305c2d1b73b9df95c258ca6e53a1153a846d8cd60c13119aa74d91f2d1559` |
| 5 | sdist | MODAL-01 | `0d40df125888b467017d053795336cb8960f643c95a209c3c96379a50c689750` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.848 | 119607296 (114.07 MiB) | `6ced18dc369c0fb55271f1364798448b7e746d1c096af04aa47aa7937fb6b03f` |
| 6 | sdist | DYNAMIC-01 | `b40d7188143e4bcc73ee63407f426633490921075990bcad47bd25c9a188480b` | 1 | EXECUTION_PASS | NUMERICAL_ORACLE_PASS | 1.988 | 119226368 (113.70 MiB) | `232f239c188acbfcb25092794922a970a53d93bf6831b15e530687331e4a4afa` |

Les six processus ont été lancés par les exécutables `qf-solver` des environnements installés identifiés au préflight. Ils n’ont pas importé depuis le checkout. Chaque paire a eu une tentative unique, en série; aucun timeout, retry ou échec n’a eu lieu. Temps cumulé des six tentatives : 11.457 s. RSS maximale observée : 119607296 octets (114.07 MiB), sous la limite souple de 512 MiB.

L’enveloppe appliquée était : timeout 30 s; stdout et stderr plafonnés chacun à 1 Mio; RSS échantillonné ≤512 MiB; au plus quatre nœuds et trois DDL libres. Les tailles réellement observées de stdout sont 250, 241, 255, 250, 241 et 255 octets; stderr est vide pour les six tentatives.

### SHA-256 des preuves par tentative

| # | `result.json` | `stdout.log` | `stderr.log` |
|---:|---|---|---|
| 1 | `3d383f560a999898b55abb7d2d02e3293de4eefc01d4fb7eb31aacfe231209ad` | `fce05987eb28a4b05eb00a33999191f41fc79c23cb1b61e1c0a60dcacc79b17f` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 2 | `4e40dff8b385cddd4fef0744cf178d7b6ad4193bf47e1014322134b0836958ce` | `8947af1ef4667eed17a11ec288d34f17221c371f609119a523608c49b31eb46a` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 3 | `aae2901fcfa2cfffdfedcf99b0c23406fd044b25579913448436449001a9614b` | `b5b5d1d29bde7551d5e0d7c2b4b758ac0cffd273012f08cc56fa4b9c447cf7e6` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 4 | `eef305c2d1b73b9df95c258ca6e53a1153a846d8cd60c13119aa74d91f2d1559` | `23698f9ecaad065f7b04b2a794829a58bb98880921e3aa96e231dd616d86a0ae` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 5 | `6ced18dc369c0fb55271f1364798448b7e746d1c096af04aa47aa7937fb6b03f` | `c054898bd7f2c57a9e78901a2d960cd9fb8f7fbc5532b2703784e56fd3791fbc` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 6 | `232f239c188acbfcb25092794922a970a53d93bf6831b15e530687331e4a4afa` | `73ac5ee8795984c2c990a04c4b73db767ecd226ab150aab3096d5ecb2a58afad` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Comparaison aux oracles numériques

Les checks numériques wheel et sdist sont identiques pour chaque cas. Les tolérances proviennent du manifeste v7 et du contrôleur figés; aucune entrée, oracle ou tolérance n’a été modifié.

### STATIC-01

| Mesure | Attendu | Mesuré (wheel et sdist) | Écart absolu | Écart relatif / critère | Résultat |
|---|---:|---:|---:|---:|---|
| Déplacement UX (m) | 2.1224489795918369e-8 | 2.122448979591837e-8 | 0 | 0; tol. 1e-12 | PASS |
| Von Mises (Pa) | 3428.5714285714284 | 3428.5714285714284 | 0 | 0; tol. 1e-12 | PASS |
| Résidu libre relatif | ≤1e-9 | 0 | — | 0 | PASS |
| Réaction X (N) | -1000 | -999.9999999999994 | 5.684341886080801e-13 N | tol. absolue 1e-10 N | PASS |
| Équilibre global des forces | ≤1e-12 | 5.684341886080802e-16 | — | erreur relative 5.684341886080802e-16 | PASS |
| Identité d’énergie linéaire | ≤1e-9 | 0 | — | erreur relative 0 | PASS |

### MODAL-01

| Mesure | Attendu | Mesuré (wheel et sdist) | Écart absolu | Écart relatif / tolérance | Résultat |
|---|---:|---:|---:|---:|---|
| Première fréquence (Hz) | 1619.5553821068941 | 1619.5553821068938 | 2.2737367544323206e-13 Hz | 1.403926521780562e-16; tol. 1e-12 | PASS |
| Résidu propre relatif maximal | ≤1e-10 | 2.0193754640700194e-16 | — | — | PASS |
| Erreur d’orthogonalité de masse | ≤1e-10 | 0 | — | — | PASS |
| Erreur de diagonalisation de raideur | ≤1e-10 | 5.39108692432493e-17 | — | — | PASS |

### DYNAMIC-01

| Mesure | Attendu | Mesuré (wheel et sdist) | Écart absolu | Écart relatif / tolérance | Résultat |
|---|---:|---:|---:|---:|---|
| Énergie initiale (J) | 1.0000000000000000e-4 | 9.999999999999999e-5 | 1.3552527156068805e-20 J | 1.3552527156068805e-16; tol. 1e-10 | PASS |
| Première énergie enregistrée (J) | 1e-4 | 9.999999999999998e-5 | 2.710505431213761e-20 J | 2.710505431213761e-16; tol. 1e-10 | PASS |
| Énergie de l’état final (J) | 1e-4 | 9.999999999998331e-5 | 1.6696713456276768e-17 J | 1.6696713456276768e-13; tol. 1e-10 | PASS |
| Cohérence énergie historique / état indépendant | écart ≤1e-14 J | 9.99999999999833e-5 vs 9.999999999998331e-5 J | 1.3552527156068805e-20 J | — | PASS |
| Dérive énergétique relative | ≤1e-10 | -1.6696713456276768e-13 | 1.6696713456276768e-13 | — | PASS |
| Résidu dynamique | ≤1e-10 | 1.6410484082740595e-14 | — | — | PASS |
| Résidu libre relatif | ≤1e-10 | 1.6410484082740595e-14 | — | — | PASS |

La séquence dynamique couvre les 40 pas définis; le premier enregistrement est à 0,001 s et l’état final à 0,04 s. Les checks d’énergie initiale, historique, état final et résidus ont tous passé.

## Intégrité des preuves et limites

Ledger d’exécution append-only : SHA-256 `62c2c843e3cd5c80a2098efef97ca146a332c9a4375df549542d2593522bb67f`; 12 lignes exactement, soit six `RESERVED` suivis de six `TERMINAL`, dans l’ordre prescrit. Chaque réservation porte `attempt=1`; les six hashes de `result.json` concordent avec le ledger et le résumé. Le résumé officiel a le statut `SIX_EXECUTION_AND_NUMERICAL_ORACLES_PASS`, SHA-256 `a470fd99ffa146104375f7786cf9bc3c15b8fe8720750036105cb516b55c7fa6`. Il n’existe aucune septième tentative. Le ledger réel reste hors du dépôt.

Les six fichiers de résultats portent également `qualification_summary.status=WARNING`; leur `audit.qualification.traceability.status=FAIL` et `covered_formula_count=0` (sur 6 formules en statique/modal et 7 en dynamique). Ces champs de readiness/traçabilité ne font pas partie des oracles numériques des smoke tests et ne sont pas reclassés ici. Ils interdisent de présenter ces sorties comme qualification globale; les états WP12 et les résultats scientifiques historiques restent inchangés.

Aucune matrice CI complète, reconstruction package, autre campagne FEM, fusion, tag ou publication n’a été effectuée dans ce mandat. Verdict limité : **`WP13_V7_INSTALLED_PACKAGE_SMOKES_PASS`**. `QUALIFICATION_PASS` n’est pas revendiqué.
