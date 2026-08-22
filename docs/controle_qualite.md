---
doc_id: DOC-QA-001
revision: 1.2
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Controle qualite projet

Ce document definit les controles a lancer pendant le developpement et avant
une livraison. Le principe est proportionne : une modification locale ne doit
pas declencher mecanquement toutes les campagnes longues. En revanche, chaque
modification doit laisser une preuve claire du perimetre verifie, des controles
executes et de ceux volontairement reportes.

## Installation developpeur

```powershell
python -m pip install -e .[dev]
```

L'extra `dev` installe les dependances de test, couverture, typage, HDF5 et
`ruff`. Les versions candidates de release sont verrouillees dans
`requirements/baseline-standard.txt`.

## Regle de selection

1. Identifier les modules, contrats publics, formulaires mecaniques et
   artefacts documentaires touches.
2. Executer le plus petit ensemble de tests qui couvre directement ce
   perimetre, ses dependances immediates et ses contrats publics modifies.
3. Ajouter les controles d'integration pertinents lorsque l'API, la CLI, le
   schema JSON, les exports ou la documentation executable changent.
4. Relancer une campagne V&V de la famille concernee lorsqu'une formulation,
   un element, un materiau ou un algorithme numerique change.
5. Executer la baseline complete uniquement aux jalons definis ci-dessous.

Le compte rendu de chaque modification indique les commandes lancees, leur
verdict et les campagnes volontairement non relancees. Une absence de test ne
doit jamais etre deguisee en test passe.

## Niveau 1 - Controle local cible

Utiliser ce niveau apres une modification isolee. Remplacer les chemins par
les tests et modules reellement touches :

```powershell
python -m ruff check solveur\core\solver.py tests\unit\test_solver.py
python -m mypy solveur\core\solver.py
python -m pytest tests\unit\test_solver.py tests\unit\test_linear_policy.py -q
python -m compileall -q solveur\core\solver.py tests\unit\test_solver.py
```

Un changement de formulation ajoute le test unitaire de l'element et sa V&V
directe. Un changement de documentation execute au minimum
`python .\scripts\build_docs.py --profile engineering` et les tests
documentaires concernes. Ce niveau est la norme pendant
le developpement courant.

## Niveau 2 - Integration ciblee

Utiliser ce niveau si une frontiere est modifiee : API publique, CLI, lecture
JSON, export, preuve ou site. Il complete le niveau 1 :

```powershell
python -m pytest tests\integration\test_api_and_cli.py tests\unit\test_json_io.py -q
python -m pytest tests\documentation\test_docs_generation.py -q
python .\scripts\build_docs.py --profile engineering
```

Selectionner les fichiers exacts plutot que le repertoire entier lorsque le
contrat touche est clairement borne. Les tests d'integration et de
documentation ne sont pas requis pour une modification purement interne qui
ne traverse pas ces frontieres.

## Niveau 3 - Campagne mecanique ciblee

Utiliser ce niveau pour une modification des calculs EF. Executer seulement la
famille affectee, par exemple :

```powershell
python -m pytest tests\unit\test_tet4_element.py -q
python .\scripts\run_linear_solver_vnv.py --output .\results\VNV-LINEAR-SOLVERS-001
```

Les campagnes longues de dynamique, de coques, de non-lineaire, de benchmarks
mailles ou de grand modele ne sont relancees que si le changement peut affecter
leur formulation, leur assemblage, leur solveur, leurs donnees ou leur preuve.

## Niveau 4 - Baseline complete

La baseline complete est obligatoire avant une livraison, une branche de
publication, un tag, une mise a jour de dependances, un refactoring transverse,
une modification de convention partagee ou une regeneration controlee des
preuves documentaires. Elle est egalement requise si le perimetre d'impact ne peut
pas etre borne avec confiance.

```powershell
python -m ruff check solveur mitc4 scripts tests
python -m pytest
python -m compileall -q solveur mitc4 scripts tests qf_solver.py main_solveur.py mitc4_solver.py
python .\qf_solver.py verify --quick
python .\mitc4_solver.py verify --quick
python .\qf_solver.py verify-all --profile engineering --json-report .\results\verification\verify_all_engineering.json
python .\scripts\build_docs.py --profile engineering
```

La CI conserve cette baseline sur les changements pousses : elle protege les
regressions entre zones qui ne seraient pas visibles dans un controle local.
Elle ne dicte pas le rythme des iterations locales.

### Corpus V&V optionnel

Le corpus complet `qualification/vnv/` contient les sorties brutes, maillages
et traces externes de la baseline de developpement. Son volume depasse 12 Go ;
il n'est donc pas inclus dans l'archive source publique. Les controles qui
lisent directement ce corpus portent le marqueur pytest `evidence`. Ils sont
executes dans le depot de developpement et ignores avec un motif explicite
lorsque le corpus ou le manifeste documentaire genere est absent. Cette regle
ne doit jamais servir a ignorer un test du noyau numerique.

## Commandes de campagne elargie

```powershell
python .\qf_solver.py benchmarks
python -m pytest -m benchmark
python .\qf_solver.py qualification-readiness --scope tet4-linear-static
python .\qf_solver.py evidence --input .\examples\tet4_static.json --output .\results\tet4_evidence
python .\qf_solver.py verify-evidence --input .\results\tet4_evidence --json-report .\results\tet4_evidence_verify.json
python .\qf_solver.py generate-large-tet4-block --output .\results_large\block_small.h5 --nx 2 --ny 2 --nz 2
python .\qf_solver.py large-readiness --output .\results_large\readiness_small --target-dofs 24 --nx 1 --ny 1 --nz 1 --solver-backend scipy
python .\qf_solver.py convert-model --input .\examples\tet4_static.json --output .\results_large\tet4_static.h5
python .\qf_solver.py solve-large --input .\results_large\tet4_static.h5 --output .\results_large\tet4_static --solver-backend scipy
python .\qf_solver.py benchmark-large --input .\results_large\block_small.h5 --output .\results_large\block_small_benchmark --solver-backend scipy
python .\qf_solver.py qualify-large --output .\results_large\qualification_small --target-dofs 24 --nx 1 --ny 1 --nz 1 --solver-backend scipy
python .\qf_solver.py verify-large --input .\results_large\qualification_small --target-dofs 24 --json-report .\results_large\qualification_small_verify.json
python .\qf_solver.py verify-evidence --input .\results_large\qualification_small
python .\qf_solver.py qualify --manifest .\qualification\campaign.json --output .\results\qualification_campaign
```

`ruff` est configure dans `pyproject.toml`. La configuration actuelle reste
volontairement minimale: erreurs Python critiques, imports ou noms inexistants
detectes par `F`, et erreurs syntaxiques/style `E4`, `E7`, `E9`.

Les profils disponibles sont `quick`, `engineering`, `strict` et
`qualification`. Le profil `qualification` refuse les fonctionnalites marquees
experimentales dans le resume de qualification.
