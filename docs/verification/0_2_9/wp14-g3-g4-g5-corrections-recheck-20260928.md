# WP14 — addendum de recontrôle G03/G04/G05

## Conclusion

Les corrections réduisent les blocages et les deux profils de qualité/engineering sont désormais verts sur l’état exécuté :

- **G04 : PASS** — 3 639 tests passés, 36 ignorés, aucun échec ; couverture combinée lignes/branches de **86,19 %**, au-dessus du seuil gelé de 84 %.
- **G05 : PASS** — `verify-all --profile engineering`, 5/5 commandes avec code retour 0.
- **G03 : amélioration partielle seulement** — aperçu strict du périmètre public préparé : 551 fichiers, 0 constat, aucun input manquant. Mais le scan du dépôt d’ingénierie complet et son archive par défaut restent FAIL. L’aperçu n’est ni un gel formel, ni un build/install de paquet, ni une autorisation de publication.

**WP14 reste HOLD, 0/1 officiel, total global inchangé à 95/100.** Cet addendum ne donne aucun point et ne clôt pas la release.

## Provenance d’exécution

- Checkout isolé : `C:\Users\fari\AppData\Local\Temp\qf_solver_029_wp08_r1_13_integration_20260927`
- Branche : `0.2.9-unified-nonlinear`
- HEAD : `72784718f442531fc4901a09d4f3b3e298a0b1d0`
- État : worktree modifié ; G04/G05 ont été exécutés sur les octets du worktree à ce HEAD, pas sur un commit propre/final.
- Avant cet addendum : 21 fichiers suivis modifiés, aucun non-suivi.
- Aucun commit, merge, push, tag, publication ou changement du ledger.
- Aucun processus WP14/test/solve restant après les profils.

Il existe des changements de code source, mais aucun changement de mécanique numérique du solveur, seuil, tolérance ou politique de fallback dans ce lot. Les changements source concernés sont limités à la validation anticipée des entrées de génération Gmsh et à la sérialisation compatible des champs de contact optionnels. Le correctif de provenance Git stabilise les appels Git des runners WP07/WP08 lorsque `PATH` est modifié.

## G03 — périmètre public et constats conservés

| Contrôle | Résultat | Détail |
|---|---|---|
| Audit documentaire dépôt entier | FAIL | 4 490 fichiers suivis, 5 879 constats ; le sous-contrôle en échec est l’hygiène publique des sources. |
| Audit des sources publiques dépôt entier | FAIL | 5 879 constats : 2 811 références d’environnement privé, 2 811 chemins de poste, 253 références à des workflows internes, 4 courriels privés. |
| Audit de l’archive Git par défaut | FAIL | 5 636 chemins, 5 881 constats, incluant 1 occurrence de marque historique en plus des chemins/workflows/courriels. |
| Aperçu du paquet public sélectionné | PASS préparation seulement | 551 fichiers courants sélectionnés, zéro constat strict, aucun input manquant ; mapping SHA-256 `b7d193e096eca85019d307213cebc40f49aa138ca62ecbac3986c6ab29788331`. |

Les constats complets ne sont ni supprimés ni ignorés : ils proviennent du dépôt de qualification/ingénierie, qui contient des rapports, historiques et chemins internes. La stratégie de réduction consiste à publier un sous-ensemble explicite et vérifiable, sans prétendre que le dépôt entier est propre.

L’aperçu utilise un contrat `PREPARATION_ONLY` lié à la base `0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`, SHA-256 du contrat `cd58d1fe159bb5b6ed872975ab2747d79c4668d47994c42e0b924fe266b3b326`. Il observe six fichiers sélectionnés modifiés par rapport à cette base (`pyproject.toml`, baseline standard, API publique, fabrique Gmsh, audit et writer). **Aucun wheel/sdist courant n’a été construit ou installé** ; le mapping préparatoire ne ferme donc pas le gate de paquet.

Les rapports dépôt entier sont conservés dans le dossier temporaire d’audit :

- `public_documents.json` — SHA-256 `2322FEAE242E444DC726819C5A7A062BCC17F54186F161AC922657C16B96219D`
- `public_release.json` — SHA-256 `62F6F21B254A143DAC8A336FD9733CE3B17C4CBCC4293370A1D4211705FB406E`
- `release_archive.json` — SHA-256 `7F0B1E3E932A616325521C83AC20FFB2C9F3FC8C5938CB8FE295A61EF106F56C`

## G04 — tests et couverture sur l’état corrigé

Profil exécuté le 28 septembre 2026 à 02:04:40 (+02:00), durée JUnit 4 772,431 s :

```text
3675 sélectionnés
3639 passés
0 échoué / 0 erreur
36 ignorés
192 désélectionnés par le profil
14 avertissements
Couverture combinée lignes/branches = 86,1898607 % (seuil 84 %)
```

Le contrôle P0 sur ce rapport donne `solveur/core/errors.py = 100 %` et `solveur/verification/traceability.py = 92,16 %`. Ruff, mypy ciblé WP07/WP08, compileall et `git diff --check` passent également.

Les 14 avertissements n’ont pas été effacés : ils incluent notamment l’objectif indicatif des 700 lignes dépassé dans 48 fichiers, des avertissements numériques émis par des tests négatifs, et les avertissements de dépréciation `numpy.trapz`. Le seuil de couverture n’a pas été abaissé.

Artefacts G04 dans le dossier temporaire `qf_wp14_g4_final_after_wp08fix_20260928` :

- `coverage.json` — SHA-256 `D239FACF119C12B448C67055E396A2D252CDD20F8277E8FEB1C9047B8740F02C`
- `junit.xml` — SHA-256 `CCD2A20B11521312577C09AD230D6293302D2550417603FE3BA1C57280DA00ED`
- `pytest.log` — SHA-256 `8A53870B73267DF468FF1430CED232C551BA637452F0D976317A076E89D82822`

Le premier profil de couverture antérieur avait échoué sur un appel Git non résolu après modification de `PATH`. Le runner utilise maintenant l’exécutable Git résolu ; le test de régression correspondant et le profil G04 final passent. L’ancien échec reste historique et n’est pas réécrit.

## G05 — profil engineering `verify-all`

Run frais sur le même checkout de travail : `verify_all.json` indique `PASS`, profil `engineering`, 5 commandes/5 codes retour 0. Le pytest intégré rapporte les mêmes 3 639 succès, 36 skips, 192 désélections et 14 avertissements. Les autres commandes validées sont `compileall`, `qf_solver.py verify --quick`, `mitc4_solver.py verify --quick` et `qf_solver.py verify-tet10`.

- `verify_all.json` — SHA-256 `9539196E81559259B22F2377C5A847313D8EA9752D0AD9E6D7481491C0F5345B`
- `verify_all.log` — SHA-256 `B66E9027F4D85B558C5E102C89525CDFB3A2C11E528D1E0F35C9C7BD3B09EE53`

Le manifeste d’évidence R2.3 conserve sept JSON historiques récupérés après coup ; **7/7 tailles et hashes sont vérifiés** dans l’archive locale temporaire. Cette archive n’est pas un stockage externe durable. Les quatre NPZ originaux WP04-D (`h1_raw`, `h1_replay_raw`, `h2_raw`, `h3_raw`) restent absents ; aucun n’a été régénéré ni présenté comme original retrouvé.

## Gates qui restent ouverts

| Gate | État après correction | Pourquoi il reste ouvert |
|---|---|---|
| G03 | FAIL dépôt entier / PASS préparation paquet sélectionné | Le périmètre sélectionné n’est pas encore prospectivement gelé et son vrai paquet n’a pas été construit, installé et audité. |
| G04 | PASS pour le profil exécuté | Les profils optionnels/documentation/benchmark/large/évidence non sélectionnés ne sont pas couverts par ce résultat. |
| G05 | PASS profil engineering | Ne vaut pas fermeture des autres gates de release. |
| G06 | HOLD | Inventaire précédent : 63 champs documentaires requis absents et 87 dossiers de revue incomplets. Aucun champ Owner/reviewer/approver n’a été inventé. |
| G07 | HOLD | Aucun build/install/CLI attesté depuis le périmètre corrigé ; aucune release 0.2.9 n’est revendiquée. |
| G08 | NOT_RUN | Matrice de plateformes non exécutée. |
| G09 | OWNER_GATED | Pas de tag, publication ni décision finale de release. |
| R10 WP04-D | HOLD | Quatre NPZ historiques d’origine manquent toujours. |

## Prochaine étape

1. Après intégration contrôlée et arbre propre, geler prospectivement le contrat de sélection publique et faire confirmer ce périmètre par décision Owner.
2. Construire wheel/sdist de ce périmètre, vérifier leur mapping/hashes, l’installation isolée, le comportement CLI et les scanners d’archive.
3. Traiter G06 sans inventer d’approbations ; traiter G08 sur les plateformes requises ; conserver G09 comme décision séparée.
4. Garder les anciens FAIL et le manque R10 visibles. Ne pas attribuer WP14 tant que ses gates obligatoires ne sont pas satisfaits ou explicitement reclassés par décision de gouvernance.

```text
WP14_STATUS = HOLD
WP14_OFFICIAL_POINTS = 0/1
GLOBAL_OFFICIAL_TOTAL = 95/100
G03_WHOLE_REPOSITORY = FAIL
G03_SELECTED_PACKAGE_PREVIEW = PASS_PREPARATION_ONLY
G04 = PASS_FOR_EXECUTED_PROFILE
G05 = PASS_ENGINEERING_PROFILE
MERGE_OR_PUSH = NOT_PERFORMED
LEDGER_CHANGED = NO
```
