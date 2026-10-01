# WP14 — Application de la direction Owner du 27 septembre 2026

Statut : **CORRECTIFS CIBLÉS VÉRIFIÉS ; WP14 HOLD**.

**Checkpoint antérieur, supersédé pour le vocabulaire et Ruff :** les résultats
ci-dessous décrivent la copie de travail avant la dernière direction Owner.
Les copies courantes WP06-F ont depuis reçu la migration analyseur explicite,
et les 23 diagnostics Ruff ont été corrigés. Le bilan courant est
`wp14_analyzer_and_lint_corrections_20260927.md` ; les anciens chiffres de
test et hashes restent ici comme état antérieur, pas comme état courant.

Branche : `codex/wp14-remediation-clean`. HEAD de départ :
`0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba`. Les contrôles de ce dossier
portent sur la copie de travail modifiée, non committée. Ils ne sont pas une
qualification prospective ni une acceptation de release.

## Taille des sources et architecture

700 lignes demeure l'objectif de maintenance. Ce n'est plus une limite
éliminatoire : 1 000, 2 000 ou davantage sont autorisés, sans plafond arbitraire.
Cette évolution est une décision de politique **non numérique**, non une
modification des seuils physiques ou de convergence.

`scripts/audit_source_maintainability.py` a inventorié 1 593 fichiers Python
sous `src/solveur`, `scripts` et `tests`. Les **48** fichiers dépassant
700 lignes sont tous conservés dans les avertissements et l'inventaire.
Les neuf anciens budgets nominatifs sont des références historiques ; ils
n'exemptent aucun fichier et ne fixent pas un nouveau plafond.

Le test de taille a été remplacé explicitement par un contrôle de visibilité
de la dette. Les tests de dépendances entre couches, de namespace, de façades
et de centralisation du helper produit restent présents et passent. Les
fichiers manquants ou non décodables restent des erreurs. Les contrôles de
comportement et la syntaxe ne deviennent pas facultatifs.

Exécuter `python -m scripts.audit_source_maintainability` permet d'obtenir
l'inventaire complet, sans écrire de fichier et sans lancer un solve.

## Terminologie

Les textes maintenus emploient « analyse Owner », « Owner review »,
`owner_analysis` ou `owner_review`. Une analyse ne vaut pas acceptation ;
un champ reviewer/approver vide ne vaut pas approbation.

Les deux contrats WP06-F historiques ne sont pas réécrits. Leur classement
est limité à deux chemins exacts et aux SHA-256 suivants :

| Artefact préservé | SHA-256 |
| --- | --- |
| `docs/verification/0_2_9/wp06f-closure-contract.md` | `45f919ba237957cad473959fd86b0dd9d1e4c8a2009856407b088802378df866` |
| `qualification/0_2_9/wp06f_closure_contract.json` | `b9379d24e255343020428ee840fdc5afe724a6bf4cee4190975ea2aad178843d` |

Un hash divergent invalide le contrôle. Une copie dans un nouveau chemin
ne bénéficie d'aucune exception. Ce classement n'est pas une autorisation
de publication : le scan du paquet n'accorde aucune dispense historique.

L'analyse préparatoire non committée a reçu un addendum de direction et une
mise à jour de terminologie. Ses valeurs numériques n'ont pas été changées.
Le snapshot JSON initial est intact :
`09650c1a2861250542413d88c6df52bd92ce752d310c081ebf9734e24039ed09`.

## Préparation de la publication

Le plan `wp14_public_package_selection_preparation_20260927.json` réutilise
la sélection explicite du périmètre paquet, avec **551 fichiers**, sans
confondre ce périmètre avec le dépôt de preuves. Son SHA-256 est
`cd58d1fe159bb5b6ed872975ab2747d79c4668d47994c42e0b924fe266b3b326`.

`scripts/plan_public_package.py` lie chaque fichier à un blob Git, une taille
et un SHA-256. Il réutilise les scans stricts existants, contrôle les entrées
de build/data (y compris les globs), et refuse chemins traversants, fichiers
requis absents, liens, collisions de casse et exclusions incohérentes.
Il n'extrait, ne construit et ne publie aucun paquet.

Deux résultats distincts doivent rester visibles :

- **Baseline committée `0c7ecfa…` : FAIL_CLOSED_PREPARATION**, pour deux
  anciens libellés dans `src/solveur/api/public.py` et `src/solveur/core/audit.py`.
  Toutes les entrées de paquet requises sont présentes.
- **Prévisualisation de la copie corrigée : scan PASS, zéro constat sur
  551 fichiers, aucune entrée de paquet manquante.** Elle est non gelée,
  donc n'est pas une preuve d'exécution formelle.

La prochaine campagne doit lier un nouveau contrat prospectif au commit
contenant ces corrections avant le build, les contrôles wheel/sdist et les
essais des commandes installées. La version demeure `0.2.8` ; aucune release
`0.2.9` n'est annoncée. Les audits globaux R1 et l'historique Git ne sont
ni nettoyés par ce plan, ni reclassifiés PASS.

## Contrôles réellement exécutés

| Contrôle | Résultat | Portée |
| --- | --- | --- |
| Pytest ciblé | **64 passed**, un avertissement de dette de taille, 9,22 s | Sept modules : maintenance, vocabulaire courant/historique, architecture, audit compact, API publique, sélection du paquet |
| Ruff ciblé | PASS | Fichiers Python modifiés/créés pour ce correctif |
| Ruff global `src scripts tests` | **FAIL : 23 diagnostics** | 20 E402, 2 F401, 1 F841 ; échecs conservés hors de ce correctif ciblé |
| Mypy ciblé | PASS | Trois nouveaux scripts, `--follow-imports=silent` ; pas un résultat mypy global |
| Compileall ciblé | PASS | Scripts/tests nouveaux et analyseur documentaire modifié |
| Comparaison AST des deux fichiers produit | PASS | Identiques après retrait des docstrings et normalisation du seul message de présentation modifié |
| Hashes WP06-F et snapshot initial | PASS | Octets préservés |
| JSON et diff-check | PASS | Enregistrements de cette direction et diff local |

Commande pytest :

```text
python -m pytest -q tests/unit/test_source_maintainability.py tests/unit/test_review_vocabulary.py tests/unit/test_review_vocabulary_history.py tests/unit/test_architecture_rules.py tests/unit/test_audit_detail_levels.py tests/unit/test_public_api_contract.py tests/unit/test_public_package_plan.py
```

Aucune campagne structurelle WP04/WP05/WP07/WP08 n'a été relancée et aucune
suite complète n'a été exécutée. Les tests ciblés utilisent leurs petites
fixtures habituelles ; ce n'est pas un rerun des qualifications longues.

## Échecs et gates encore ouverts

La réussite ciblée ne convertit pas les anciens échecs en PASS. Restent
notamment ouverts : les audits du dépôt complet, les 23 diagnostics Ruff
globaux, les résultats engineering/documentaires historiques, les trois
gates de l'ancien maillage WP04-C et les bruts NPZ WP04-D absents. Les preuves
C2R6 acceptées et l'ancien FAIL sont des générations distinctes : aucun seuil
ni brut n'a été adapté pour les fusionner artificiellement.

**WP14 = HOLD, 0/1 ; total officiel = 95/100, inchangé.** Aucun merge, push,
tag, publication ni attribution de points n'a été effectué. Les correctifs
restent sur la branche de remédiation pour une intégration ultérieure.
