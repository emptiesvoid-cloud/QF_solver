---
doc_id: DOC-AUDIT-CODE-API-0-2-2-001
revision: 0.1
status: draft
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# Audit code, documentation et API publique 0.2.2a0

## Perimetre et methode

L'audit couvre `src/`, `README.md`, les sources Markdown de `docs/`, les
lanceurs racine, le packaging et les tests d'integration. Il combine la
recherche de references, Ruff sur les erreurs statiques de famille `F`, la
lecture des chemins d'execution statique, modal et dynamique, et les contrats
de packaging. Une fonction non appelee directement n'est pas declaree morte
si elle constitue une entree CLI, un hook de verification ou une facade de
compatibilite testee.

## Constat

Le nom de distribution PyPI etait `qf-solver`, mais le wheel ne decouvrait que
`solveur*`. Les exemples publics utilisaient en outre `solveur.api` et parfois
des modules internes. Le contrat demande `from qf_solver import ...`; il etait
donc impossible a respecter depuis un wheel. Le lanceur racine `qf_solver.py`
creait aussi une collision de nom dans un checkout source.

La recherche statique Ruff ne trouve aucune importation inutilisee, aucun nom
indefini et aucune variable locale morte dans `src/`. Les petits appels a
`numpy.linalg.inv` des formulations TET4, TET10, MITC3 et MITC4 portent sur des
Jacobiennes ou matrices locales de taille bornee ; ils ne sont pas des
inversions de la matrice globale. Les conversions denses du modal sont bornees
par `dense_modal_max_dofs` ou par les limites explicites des diagnostics. Elles
restent a surveiller, mais ne sont pas du code mort.

La facade `solveur.compat.mitc4` est encore referencee par le CLI specialise,
les tests de migration et plusieurs campagnes de verification. La supprimer
maintenant casserait une baseline numerique et une compatibilite annoncee.

## A supprimer

### Suppression immediate

Aucun fichier de code n'est supprimable avec une preuve suffisante dans cette
revision. Les candidats apparents sont encore executes ou proteges par des
tests. Supprimer sur la seule base d'un faible taux de couverture serait une
erreur d'audit.

### Retrait programme pour 0.3.0

| Element exact | Condition prealable | Justification |
|---|---|---|
| `main_solveur.py` | fin de la periode deprecation 0.2.x | lanceur remplace par `qf-solver` |
| entree `solveur-ef` de `pyproject.toml` et fonction `solveur.cli.main.legacy_main` | meme gate de deprecation | doublon du CLI public |
| `mitc4_solver.py` et entree `mitc4-solver` | migration des scripts et preuves vers le CLI generaliste | lanceur specialise de compatibilite |
| `src/solveur/compat/mitc4/` | zero import dans `tests/`, `scripts/` et documentation active, baseline de migration remplacee | facade sans formulation canonique, mais encore utilisee |
| lien README vers `docs/reference/legacy/analyse_solveur_ef.md` | index d'archive disponible | le document reste une preuve historique, pas un guide actif |

Les trois documents de `docs/reference/legacy/` doivent rester archives tant
qu'ils sont cites par le registre documentaire. Leur suppression physique
n'est acceptable qu'avec une politique d'archivage des preuves historiques.

## A mettre a jour

| Element | Correction appliquee ou attendue |
|---|---|
| `pyproject.toml` | inclure `qf_solver*` dans la decouverte setuptools |
| `src/qf_solver/__init__.py` | facade publique reexportant uniquement le contrat documente |
| `qf_solver.py` | conserver le CLI source tout en exposant le meme contrat lors d'un import depuis le checkout |
| `src/solveur/api/__init__.py` | centraliser les symboles documentes, y compris qualite de maillage, lamelle orthotrope et campagne TET4 structuree |
| `README.md` et guides API | remplacer tous les imports Python `solveur.*` par `from qf_solver import ...` |
| `docs/reference/api_stability.md` | declarer `qf_solver` comme seul namespace public des nouvelles integrations |
| `docs/architecture.md` | distinguer facade publique, implementation interne et compatibilite 0.2.x |
| `src/solveur/__init__.py` | conserver seulement comme compatibilite ; aligner ou deprecier sa liste d'exports avant 0.3.0 |
| `src/solveur/core/modal.py::_exact_lazy_shift_inverse` | remplacer a terme `coupling_dp.toarray()` par une strategie par blocs si la limite de 6000 DDL est relevee |
| `src/solveur/core/audit.py` | conserver les diagnostics denses strictement bornes a 200 DDL et tester le refus au-dela |

## Nouveau contrat d'import

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
result = solve_model(model)
save_result(result, "results.json")
```

Les scripts de maintenance et le moteur peuvent importer `solveur.*` afin de
respecter les couches internes. Cette exception ne s'applique ni au README, ni
aux guides utilisateur, ni aux exemples d'integration.

## Gates de fermeture

1. Le wheel contient `qf_solver` et `solveur`.
2. Les imports documentes fonctionnent depuis un checkout et depuis une
   installation construite.
3. Aucun Markdown public n'utilise directement le namespace interne dans un
   exemple Python.
4. Ruff, tests d'integration du packaging et suite CI avec couverture passent.
   Le gate global est fixé à `80 %`; la campagne du 23 août 2026 produit
   `1336 passed`, `107 deselected` et `88,67 %` de couverture branchée.
5. R3 est archive avec verdict, duree, memoire et raison de fin explicites.

La relance R3 du 23 aout 2026 est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/matrix_free_1m_r3/`.
Elle atteint le timeout controle a `901,113 s`, avec `31` echantillons et un
pic RSS de `293,77 MiB`. Aucun resume solveur ni residu final n'est produit :
le verdict reste `BLOCKED_TIMEOUT`, et non un PASS 1M.

La decision de suppression des compatibilites et la decision de release
restent reservees a l'Owner.
