# WP-E01-AM — Diagnostic de l’AttributeError Newton–Armijo

## Conclusion

La trace AL identifie une défaillance d’instrumentation du worker après l’appel au solveur. Le worker AG lisait directement `solver._last_load_step_state` alors que ce champ n’est créé par le solveur qu’après le retour réussi d’un pas de charge. Le chemin de convergence échouée peut donc ne pas le définir. Cette lecture a levé une seconde exception et a masqué l’état d’échec que le worker venait d’intercepter.

La correction minimale est limitée au worker AG : lire cet état comme une donnée optionnelle (`getattr(..., None)`). Aucun objet numérique ou état constitutif n’est fabriqué. Le code de production du solveur et les paramètres scientifiques ne changent pas.

## Identité et éléments historiques

- Dépôt : `wp-e01-ag`, branche `codex/wp-e01-ag-docker-native-fem-vnv`.
- HEAD avant correction : `5f16d128f84482a47fe39eed3e979b6bc539520a`.
- Le rapport AL et ses artefacts restent inchangés. L’exécution AL demeure `ERROR`, pas un résultat scientifique `PASS` ou `FAIL`.
- Le traceback consigné dans `qualification/0_2_12/wp_e01_al_run_report.md` est :

```text
File "/opt/qf/experiments/wp_e01ag_docker_worker.py", line 616, in _run
  runs = [_run_one_physical_case(doc) for _ in range(doc["controls"]["deterministic_replay_count"])]
File "/opt/qf/experiments/wp_e01ag_docker_worker.py", line 559, in _run_one_physical_case
  state = solver._last_load_step_state
AttributeError: 'NonlinearStaticSolver' object has no attribute '_last_load_step_state'
```

Le worker avait déjà appelé `solver.solve(model)`. Il intercepte `NumericalConvergenceError` pour enregistrer un résultat `FAIL`, restaure ses instrumentations dans `finally`, puis accède au champ privé sans garde. Le rapport AL précise que le traceback ne permet pas de savoir si `solve` a retourné ou levé l’erreur interceptée : le diagnostic numérique initial est donc `NOT_RECORDED`. Le premier élément d’une répétition déterministe a échoué dans cette instrumentation; le second n’a pas démarré.

## Cycle de vie vérifié

`NonlinearStaticSolver.__init__` (`src/solveur/core/nonlinear/solver.py`) initialise ses composants mais ne déclare pas `_last_load_step_state`. Le mixin de contrôle de charge l’écrit après obtention d’un résultat de pas et détachement de l’état (`src/solveur/core/nonlinear/load_control.py`, affectation vers la ligne 1136). D’autres écritures concernent les pas acceptés du chemin adaptatif. Plusieurs lectures de production sont dans des chemins de contrôle qui exigent un état accepté ou vérifient explicitement `None`; ce champ est donc un état de résultat disponible après un pas, et non une donnée garantie à la construction du solveur.

Ce cycle est cohérent avec une propriété privée facultative du solveur. Il ne justifie pas de l’initialiser avec un état synthétique : cela pourrait faire croire qu’un pas a été accepté alors qu’aucun ne l’a été.

## Changement appliqué

Dans `experiments/wp_e01ag_docker_worker.py`, ajout de `_optional_accepted_load_state(solver)` qui renvoie l’état existant ou `None`, puis remplacement de l’accès direct post-`solve` par cet helper. Le schéma de résultat conserve `accepted_state_digest: null` si aucun état accepté n’existe; l’erreur de convergence interceptée reste alors rapportable sans exception secondaire.

Test de régression ajouté : `tests/unit/test_wp_e01ag_worker_state_capture.py`. Il reproduit l’`AttributeError` de l’ancien accès sur un objet synthétique, vérifie le retour `None` sans champ, puis vérifie l’identité de l’objet lorsque le champ existe. Il n’instancie aucun solveur ni modèle FEM et n’évalue aucune équation mécanique.

Le nouveau module est enregistré comme `PURE_UNIT` dans `tests/conftest.py` et lié à son SHA-256. Le test ne fait que des opérations Python synthétiques.

## Vérifications exécutées

- `ast.parse` sur le worker, le nouveau test et `tests/conftest.py` : réussi (`AST_OK 3`).
- Test ciblé, avec le module de cache désactivé : `python -m pytest -q -p no:cacheprovider tests/unit/test_wp_e01ag_worker_state_capture.py` — **1 passed**.
- `git diff --check` : réussi.
- Aucun test de solveur, aucune collecte générale, aucun lancement Docker, aucun calcul FEM et aucun nouveau RUN.

Le succès du test prouve uniquement que la lecture optionnelle ne masque plus l’absence de champ dans le code de capture. Il ne prouve ni convergence de Newton, ni rejet/acceptation Armijo, ni équilibre avec contact.

## Autres références trouvées

Recherche exhaustive de `_last_load_step_state` dans `src`, `experiments` et `tests` :

- Production : lectures dans `solver.py` et `load_control.py`; écritures dans `load_control.py` après des états de pas disponibles/acceptés.
- Worker AG : la lecture post-solve concernée est corrigée.
- Worker AD distinct : lectures directes aux lignes proches de 379, 400 et 437 de `experiments/wp_e01ad_physical_fem_worker.py`. Les deux premières sont dans l’observateur de ligne de recherche et la dernière suit le traitement d’exception du solveur. Elles présentent un risque analogue si aucun pas n’a été accepté. Ce worker n’a pas été modifié dans ce correctif ciblé; ce constat est transmis pour une revue/correction AD distincte avant toute réutilisation de ce chemin.
- Les références dans d’autres tests et preuves sont des assertions ou historiques, non des consommateurs de production.

## Impact et limites

Aucun fichier de production sous `src/` n’a été modifié. `solver.py` et `load_control.py` gardent leurs octets de base. Aucun changement n’affecte Newton–Armijo, les tolérances, le modèle GF4, les conditions de contact ou la référence. La trace AL ne fournit toujours aucune mesure Newton/Armijo exploitable; son diagnostic primaire demeure inconnu.

Le worker, la classification de test et les manifestes gelés sont désormais d’identités différentes de celles d’AL. Les preuves AL historiques restent valides pour leur identité et ne doivent pas être réécrites. Toute nouvelle collecte/exécution qualifiante requiert un nouveau gel avec hashes mis à jour, une image Docker reconstruite ou vérifiée contre le worker modifié, une collecte acceptée et un GO-RUN Owner distinct. Aucun RUN Docker n’est autorisé par AM.

## Empreintes avant commit

- Worker AG modifié : `7c85c5e1903ee9c40825ce2135d0a8885c4b743442d656d95fb69bfd3e2ce91d`
- Nouveau test : `f17f619e0f2088cf92593a8d39c3bef236d97ca37560a488c7d674f0a887c027`
- Registre `tests/conftest.py` modifié : `452a8f76879ba88600aebabbf535f2d9ac0b0af8dc3b6ad86e57f4bafddfbada`
- Solveur de production inchangé (`src/solveur/core/nonlinear/solver.py`) : `678ff73804d721cbe2363b8ec37397ab2bddc18a0baee4cd051c86f834098dc5`
- Contrôle de charge de production inchangé (`src/solveur/core/nonlinear/load_control.py`) : `bf9d4c8f443704d8db408b6f9c3c1dd27941877fc76e83b37d05b09bad9530b9`

## Statut

- Diagnostic de l’AttributeError : cause identifiée dans l’instrumentation worker AG.
- Correction : worker AG, état accepté capturé de manière optionnelle.
- Tests ciblés : 1 passé.
- Comportement numérique Newton–Armijo : non évalué par AM.
- `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`.
- `DOCKER_RUN=NOT_AUTHORIZED / NOT_RUN`.
- Qualification scientifique générale : non acquise.
