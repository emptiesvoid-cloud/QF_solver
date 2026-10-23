# WP-E01-AN — Worker Newton–Armijo, gel et préflight

## Résumé exécutif

Le worker AG conserve maintenant le résultat de `solver.solve()` séparément du verdict d’acceptation du scénario. Les retours normaux conservent leur statut solveur; `NumericalConvergenceError` est sérialisée comme `FAIL` avec type, message et diagnostics; une exception ordinaire est sérialisée comme `ERROR`. Le calcul global du cas ne peut passer que si le statut solveur est `PASS`, que le résidu satisfait le seuil gelé et que les autres contrôles existants sont vrais.

Les quatre tests synthétiques ciblés passent. Aucun solveur FEM ni test scientifique n’a été exécuté.

Le nouveau gel source/image est prêt, mais la tentative unique de préflight s’est arrêtée avant création du conteneur : le superviseur a trouvé le répertoire `PREFLIGHT` déjà non vide et a refusé toute nouvelle tentative. Le préflight historique présent dans ce dossier concerne le manifeste AH antérieur (SHA-256 `ff78e668…03d6cab`), pas le gel AN. Il ne valide donc pas l’image et le worker actuels. Aucun nouveau reçu de préflight ni nouvelle preuve de nettoyage n’a été produit.

## Baseline et préservation

- Baseline AM : commit `25a02b4d386fb2bd533fbb5ac7bbd15866f83994`.
- Branche : `codex/wp-e01-ag-docker-native-fem-vnv`.
- HEAD final de préparation : `1ea147d9f3b220264182b5756d73978d51195789`.
- Tree final : `102b75027906381342510e5b1cc6eb98b5d01a0a`.
- Worktree propre après commit du présent rapport.
- Le rapport AL et les fichiers de preuve AL n’ont pas été modifiés. Les RUN/AL demeurent `ERROR`, et aucun résultat Newton–Armijo exploitable n’est enregistré.

## Correctif du worker et sémantique des résultats

`experiments/wp_e01ag_docker_worker.py` utilise `_invoke_solver_for_evidence` :

- Retour de `solve()` : conserve le statut original dans `solve_outcome.kind=RESULT` et `solve_outcome.status`.
- `NumericalConvergenceError` : statut interne `FAIL`, détails et diagnostics conservés sous `solve_outcome`; aucune valeur de convergence n’est inventée.
- Autre `Exception` : statut de solve `ERROR`, classe, message et diagnostics éventuels conservés. L’exception est incluse dans le reçu de run plutôt que de faire tomber la construction du reçu.
- Champ accepté absent : digest `null`; aucun état constitutif synthétique n’est créé.
- Vérification finale : un résultat global `PASS` reste impossible après `FAIL` ou `ERROR`, puisque le contrôle de convergence exige explicitement un statut solveur `PASS`, un résidu numérique présent et sous la tolérance, ainsi que la réussite des vérifications Armijo, d’état, de commit et de facteur de charge.

Le champ `solve_outcome.status` préserve l’état solveur réel. Le statut agrégé de campagne peut être `FAIL` si ce résultat n’établit pas les critères scientifiques; ce `FAIL` agrégé ne transforme pas un `ERROR` solveur en succès.

Les paramètres du scénario TET4, les tolérances, les limites Newton–Armijo, les références et le code de production sous `src/` n’ont pas changé.

## Tests ciblés

Module : `tests/unit/test_wp_e01ag_worker_state_capture.py` — classification `PURE_UNIT` hash-liée dans `tests/conftest.py`.

Commande exécutée :

```text
python -m pytest -q -p no:cacheprovider tests/unit/test_wp_e01ag_worker_state_capture.py
```

Résultat observé : **4 passed in 0.60s**. Les quatre cas utilisent un faux solveur Python et ne construisent ni maillage ni modèle FEM :

1. champ d’état accepté absent : lecture renvoie `None`;
2. solveur factice retourne `PASS` sans champ d’état : statut de retour conservé et digest absent;
3. erreur de convergence typée : `FAIL`, type/message et diagnostics préservés;
4. exception initiale inattendue (`ValueError`) : `ERROR`, type/message préservés, aucune conversion en `PASS`.

La sérialisation complète du reçu à travers `_run` n’est pas testée bout en bout; son chemin a été vérifié statiquement. L’indépendant classe cette limite P2. Ces tests ne vérifient pas la convergence Newton, Armijo ou l’équilibre.

Contrôles statiques : Ruff (`All checks passed`), `ast.parse` sur worker/test/registre (`AST_OK 3`), `git diff --check` réussi, aucun diff sous `src/`.

## Revue indépendante

Revue distincte, lecture seule, sans test, Docker ni calcul FEM :

- Aucun P0 identifié.
- Le P1 relatif aux exceptions solveur non-convergence ordinaires est corrigé : elles sont maintenant sérialisées et peuvent atteindre le reçu RUN, sous réserve du fonctionnement ultérieur des écritures du worker.
- Le statut `ERROR` ne peut pas satisfaire les critères finaux `PASS`.
- P2 : le test n’exerce pas l’agrégateur complet du worker ni la sérialisation finale du reçu; cette propriété est établie par inspection du code.
- P1 distinct : le worker AD conserve des lectures directes de `_last_load_step_state` aux lignes 379, 400 et 437 de `experiments/wp_e01ad_physical_fem_worker.py`. Ce worker n’a pas été modifié, conformément au périmètre demandé; ne pas le réutiliser avant correction et gel distincts.

## Gel source et image

Le gel scientifique est fondé sur le commit de code/test `41f8e4a264ffe4a4e4948bf3040d3c1fdf55d920`, tree `530c5d233a83301a4c3e869af438e65007d8d861`; ce commit est ancêtre du HEAD documentaire final. Le manifeste inventorie et vérifie 533 entrées de sources. Les modifications du worker et de `tests/conftest.py` sont comprises dans ces pins. L’image a été reconstruite à partir du Dockerfile existant et de la dépendance lock inchangée; l’image de runtime demeure configurée avec réseau `none`.

| Artefact | SHA-256 / identité |
|---|---|
| `experiments/wp_e01ag_docker_worker.py` | `fb81fedbfa42d7b4d536867a84bf271e26900d949b45da7ed2f84cdcc6a51566` |
| `tests/unit/test_wp_e01ag_worker_state_capture.py` | `fd21c1a87294decb4079516aa08aece2045d675d51e14ca88b03838ddc81f6dc` |
| `tests/conftest.py` | `90402efc0e5c3dc9303192b5f2799fffd39e1a66e3ac93b842ca7223a1d36f71` |
| `experiments/wp_e01ag_docker_host.ps1` | `e315f3e93875966b23d4b728c3b9634fbd77f6be05011055f7e77f21601abea4` |
| Manifeste PREFLIGHT | `a66d4cca9c6818a9f4ba13c735618936e9e6f88f5df1557f202e3f18313a6ac2` |
| Image Docker `qfsolver-e01-vnv:an` | `sha256:2a1913a6bbc3ce5a4530193cf668edf013eec39c9b990d886fc23ff9a7c806b4` (`linux/amd64`) |
| `src/solveur/core/nonlinear/solver.py` inchangé | `678ff73804d721cbe2363b8ec37397ab2bddc18a0baee4cd051c86f834098dc5` |
| `src/solveur/core/nonlinear/load_control.py` inchangé | `bf9d4c8f443704d8db408b6f9c3c1dd27941877fc76e83b37d05b09bad9530b9` |

Le manifeste pointe vers le HEAD/tree source ci-dessus et l’image `:an`. Sa carte de 533 empreintes et son sidecar ont passé une vérification locale intégrale avant commit.

## Tentatives Docker et résultat du préflight

1. Build image avec `--network=none` : échec au `pip install` des dépendances épinglées car aucune roue/cache n’était disponible dans ce build. Aucun conteneur runtime n’a été créé.
2. Build image avec accès réseau de build : réussi, à partir des mêmes Dockerfile, base Python épinglée et lock de dépendances. L’image résultante a été inspectée `linux/amd64` avec l’identifiant indiqué ci-dessus. Le réseau reste désactivé dans la configuration d’exécution du conteneur.
3. Une seule invocation de préflight a été tentée :

```text
pwsh -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase PREFLIGHT
```

Le superviseur a vérifié Docker Linux, puis a refusé avant lecture du nouveau manifeste et avant `docker create`, parce que `..\wp-e01-ag-evidence\PREFLIGHT` contenait déjà des preuves. Message observé : `phase evidence already exists; automatic retries are prohibited`. Cette règle est le garde-fou anti-réexécution du profil; aucun fichier ancien n’a été supprimé ou remplacé.

Le dossier historique contient un `PREFLIGHT_PASS` lié au manifeste AH `ff78e668…03d6cab`, avec nettoyage historique `REMOVED_CONFIRMED_NOT_FOUND`. Il est distinct du nouveau manifeste/image. Pour cette tentative AN, aucun worker/container n’a été créé, donc le nettoyage est **N/A (non créé)**; il ne s’agit pas d’un nouveau test de confinement.

**Statut du préflight AN : BLOQUÉ avant lancement conteneur**, et non `VERIFIED`. La raison est l’unicité de l’emplacement de preuve déjà consommé. Une suite nécessiterait une nouvelle autorisation Owner pour un répertoire d’évidence unique lié à la nouvelle identité et une nouvelle invocation; aucun changement de superviseur n’a été fait pour contourner ce refus.

## Commandes futures et autorisations distinctes

Le superviseur fixe les commandes par phase. Après obtention d’un manifeste COLLECT refait pour le gel AN, d’un emplacement d’évidence inédit et d’un GO-COLLECT distinct :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
pwsh -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase COLLECT
```

Après reçu COLLECT accepté, manifeste RUN lié au même gel et autorisation Owner GO-RUN distincte :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
pwsh -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase RUN
```

Les manifestes COLLECT/RUN existants n’ont pas été actualisés dans ce travail et leurs pins ne doivent pas être utilisés avec le nouveau worker. Les commandes ci-dessus sont les syntaxes fixes, pas une autorisation ni une preuve que les manifestes actuels sont prêts.

## Statuts

- Correctifs/tests ciblés du worker : implémentés; 4 tests synthétiques passés.
- Préparation du gel : effectuée; 533 pins validés; image reconstruite et inspectée.
- Préflight Docker AN : **BLOQUÉ avant création du conteneur** par le garde d’unicité des preuves; confinement AN non vérifié.
- `COLLECT=NOT_RUN`.
- `RUN=NOT_RUN`.
- `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`.
- Newton incrémental physique : résultat non établi; AL reste `ERROR` sans mesures utilisables.
- Qualification scientifique : non acquise.
