# WP13 — diagnostic de traçabilité des smoke tests installés v7

- Date : 2026-11-01
- Branche examinée : `codex/wp13-release-engineering-20261031`
- HEAD source examiné : `e180969645f19fead1564834ad028a55d7e590e0`
- Artefacts : wheel `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518`; sdist normalisée `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174`

## Verdict

**`EXPECTED_CONTRACT_BEHAVIOR`**

Les trois modèles possèdent des scopes et des références de formule dans les registres du dépôt. La validation échoue sur les environnements installés parce que le candidat v7 contient la sélection de package prévue, mais pas l’arborescence de preuves complète vers laquelle ces registres pointent. Le statut `FAIL` est le résultat fidèle de cette absence de traçabilité dans le package installé; il est conservé.

## Origine des statuts

[`traceability.py`](../../src/solveur/verification/traceability.py) choisit un scope à partir de l’analyse et des familles d’éléments :

| Modèle du smoke | Scope inféré | Exigences couvertes au runtime | Formules demandées |
|---|---|---:|---:|
| `STATIC-01` — TET4 `linear_static` | `tet4-linear-static` | 13/13 | 6 |
| `MODAL-01` — TET4 `modal` | `tet4-modal` | 8/8 | 6 |
| `DYNAMIC-01` — TET4 `transient_dynamic` | `tet4-transient-dynamic` | 10/10 | 7 |

Les modèles JSON ne déclarent pas eux-mêmes des formules. `scope_for_model()` les associe aux scopes de `qualification/requirements.json`; les scopes listent les références de formule qui sont ensuite chargées depuis `qualification/formulas.json`.

`QualificationRegistry.readiness()` renvoie `FAIL` dès qu’un contrôle de scope échoue. Les contrôles comprennent le statut du scope, la présence des liens obligatoires, l’existence de leurs chemins, les références mécaniques indépendantes et la validation de chaque formule. `FormulaRegistry._record_issues()` exige pour chaque formule un document et sa section, des chemins de code et de tests, des symboles de fonction existants, une exigence connue et une référence externe résoluble. Une formule n’est comptée comme couverte que si tous ces liens passent.

[`qualification.py`](../../src/solveur/core/qualification.py) incorpore ce résultat à `qualification_metadata()`. Avec le profil `engineering` des six smoke runs, `qualification_summary()` convertit le scope non prêt en `WARNING` et n’ajoute aucun `blocking_error`. En profils `strict` ou `qualification`, un avertissement de traçabilité peut bloquer l’acceptation du run; les smoke v7 n’utilisaient pas ces profils.

## Résultat comparé : dépôt source et packages installés

Les contrôles ont été exécutés sans solveur ni assemblage, avec le même code installé et les trois scopes exacts :

| Contexte | Scope | Résultat | Formules couvertes | Liens de registre sans cible |
|---|---|---|---:|---:|
| Dépôt source | `tet4-linear-static` | PASS | 6/6 | 0 |
| Dépôt source | `tet4-modal` | PASS | 6/6 | 0 |
| Dépôt source | `tet4-transient-dynamic` | PASS | 7/7 | 0 |
| Wheel installé | `tet4-linear-static` | FAIL | 0/6 | 75 |
| Wheel installé | `tet4-modal` | FAIL | 0/6 | 49 |
| Wheel installé | `tet4-transient-dynamic` | FAIL | 0/7 | 73 |
| Sdist installée | `tet4-linear-static` | FAIL | 0/6 | 75 |
| Sdist installée | `tet4-modal` | FAIL | 0/6 | 49 |
| Sdist installée | `tet4-transient-dynamic` | FAIL | 0/7 | 73 |

Les six `result.json` concordent avec ce diagnostic. Les catégories manquantes sont des liens `design`, `code`, `tests` et `artifacts` vers l’arborescence du dépôt. Par exemple, les formules TET4 pointent vers `docs/elements/tet4/...`, `docs/reference/references.md`, les sources `src/solveur/...` et les tests `tests/...`. Le wheel et la sdist ne contiennent volontairement pas les préfixes `docs/` et `tests/` prévus par le contrat de sélection v7; les fichiers de code sont installés sous `site-packages/solveur/`, pas sous les chemins source `src/solveur/` du registre.

Le registre lui-même déclare les trois scopes `qualified`, et tous les liens de requirements sont couverts selon le compteur de requirements. Cela ne signifie pas que les liens de formules ont été validés depuis le package : le compteur `covered_formula_count` reste explicitement à zéro et chaque formule échoue à la résolution de ses preuves. Dans le dépôt source, les mêmes enregistrements passent intégralement; aucune formule ou référence n’est absente de la source.

## Effet sur le calcul et interprétation

La traçabilité est calculée pour l’audit et les métadonnées de résultat; elle ne modifie pas les matrices, les conditions aux limites, les oracles ou l’algorithme de résolution. Les six calculs v7 ont produit leurs résultats avant l’évaluation de readiness, et le profil `engineering` a émis un `qualification_summary.status=WARNING`, sans blocage. Les contrôles numériques distincts du contrôleur WP13 ont tous passé. Ce constat ne transforme pas ces résultats en qualification globale et ne valide pas les références de formule depuis le package installé.

Le comportement attendu pour ce candidat est donc de signaler `FAIL` pour la traçabilité non disponible dans l’installation et `WARNING` pour le résumé d’ingénierie. Il ne faut ni masquer ces champs ni les convertir en PASS.

## Correction et impact sur v7

Aucun correctif du solveur ou du package n’est appliqué dans cette revue. Ajouter les documents/tests au package, changer les références du registre ou modifier la résolution des chemins affecterait la surface distribuée et donc les hashes du candidat v7. Une solution future visant une traçabilité PASS en environnement installé nécessiterait un contrat de package révisé, une reconstruction et une nouvelle décision Owner avant toute nouvelle exécution scientifique. Les six tentatives déjà consommées ne sont pas relancées.
