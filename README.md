# QF Solver

**White-box finite-element tools for verifiable structural mechanics.**

[![Quality and verification](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml/badge.svg?branch=main)](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml)
[![PyPI](https://img.shields.io/pypi/v/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![Python](https://img.shields.io/pypi/pyversions/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![License](https://img.shields.io/github/license/emptiesvoid-cloud/QF_solver.svg)](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE)

QF Solver est un solveur d'elements finis Python open source pour la mecanique
des structures, la dynamique et la simulation d'ingenierie verifiable. Le
projet est concu comme un logiciel white-box : formulations, hypotheses,
resultats et preuves restent consultables dans le depot.

La version candidate `0.2.5a0` consolide le backend solide non lineaire et ses
preuves de verification. Elle n'ajoute pas de nouvelle famille d'elements et
ne revendique pas une validation physique generale ni un remplacement d'un
solveur industriel.

## Installation

Depuis PyPI, apres publication de la release :

```powershell
python -m pip install qf-solver==0.2.5a0
qf-solver --version
```

Pour travailler depuis un clone du depot :

```powershell
python -m pip install -e ".[test]"
qf-solver --version
```

Extras optionnels :

```powershell
python -m pip install -e ".[mesh]"  # import Gmsh et benchmarks mailles
python -m pip install -e ".[docs]"  # construction de la documentation
python -m pip install -e ".[hpc]"   # PETSc/SLEPc/MPI si disponibles
```

PETSc et SLEPc ne sont pas requis pour l'installation standard. Python 3.10 a
3.13 est couvert par la CI annoncee.

## Premier calcul

Le cas JSON suivant est maintenu par les tests d'integration :
`examples/tet4_static.json`.

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4.json
```

La meme operation est disponible par l'API publique :

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
mesh_report = check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

L'unique namespace Python public pour les nouvelles integrations est
`qf_solver`. Le namespace `solveur` reste interne et sert uniquement aux
compatibilites historiques de la serie 0.2.x.

## Capacites et maturite de 0.2.5a0

Les statuts ci-dessous sont limites aux enveloppes de preuves documentees.
`QUALIFIED` signifie qualifie dans ce domaine borne, et non valide pour toute
structure ou toute echelle.

| Statut | Capacites dans le scope de la release |
| --- | --- |
| **QUALIFIED / BOUNDED** | J2 small-strain sur TET4/TET10/HEX8/HEX20 ; elasticite Total-Lagrangian TET4/HEX8 dans le domaine pre-limite teste ; flambement lineaire sparse borne ; contact sans frottement borne ; caracterisation de performance ; contrats de modes d'echec |
| **EXPERIMENTAL / NOT QUALIFIED** | arc-length FEM complet ; J2 finite-kinematic ; workflows non lineaires couples ; couplage triple ; grandes transformations au-dela du domaine G02 |
| **NOT IN RELEASE SCOPE** | contact avec frottement ; G07 |

Les chemins lineaires TET4/TET10, MITC3+/MITC4, BEAM2 et les entites discretes
restent disponibles avec leurs propres domaines de maturite. Le detail par
element et par analyse se trouve dans
[`docs/etat/capacites.md`](docs/etat/capacites.md). Une implementation ou un
test experimental ne devient pas une capacite qualifiee par sa seule presence.

## Analyses disponibles

Le routeur commun prend en charge, selon le modele et le scope de preuve :

- statique lineaire sparse ;
- modal generalise sparse ;
- dynamique transitoire Newmark ;
- reponse harmonique ;
- statique non lineaire a chargement controle, avec Full Newton dans le scope
  qualifie ;
- flambement lineaire sparse dans son domaine borne ;
- contact sans frottement borne.

Les chemins arc-length, finite-kinematic J2 et couples sont exposes pour la
recherche et les essais traces, mais ne sont pas des claims qualifies de
`0.2.5a0`.

## Architecture

Le produit suit le flux :

```text
modele FEM -> assemblage sparse -> analyse du systeme -> backend
           -> solveur -> convergence -> resultats et metriques
```

Pour les chemins non lineaires, les responsabilites sont separees entre
cinematique, loi constitutive, etat materiau, assemblage du residu/tangente,
strategie Full Newton, controle d'increments et diagnostics. Les elements
conservent leurs fonctions de forme et leur quadrature ; ils ne choisissent
pas le solveur global.

Le backend standard utilise SciPy sparse. PETSc/SLEPc sont optionnels pour les
environnements HPC. Les limites memoire, les conventions de quadrature et les
choix de formulation sont decrits dans
[`docs/architecture.md`](docs/architecture.md) et le pack 0.2.5.

## Verification et validation

QF Solver distingue :

- **verification** : formules, invariants, tangentes, residus et convergence ;
- **correlation externe** : comparaison numerique avec Code_Aster ou CalculiX
  sous hypotheses documentees ;
- **validation physique** : preuve separee du domaine d'application, non
  revendiquee par une simple comparaison de codes.

Pour le candidat 0.2.5a0, les preuves de release documentent notamment :

- G11 : `1719 passed / 0 failed` ;
- couverture de la campagne de reference : `88.37 %` ;
- campagne externe disponible : `64/64 PASS` ;
- provenance par SHA source, empreintes d'artefacts et etat de l'arbre source.

Ces chiffres concernent le perimetre qualifie et borne, pas les capacites
experimentalement exclues. Les preuves detaillees, les courbes et les limites
sont dans [`docs/verification/0_2_5/README.md`](docs/verification/0_2_5/README.md),
la [matrice V&V](docs/verification/0_2_5/0_2_5_vnv_matrix.md) et le
[rapport de readiness](docs/verification/0_2_5/0_2_5_release_readiness.md).

## Exemples, Gmsh et benchmarks

Les exemples JSON sont dans [`examples/`](examples/) et leur catalogue est
decrit dans [`examples/README.md`](examples/README.md). Quelques commandes :

```powershell
qf-solver methods
qf-solver benchmarks
qf-solver benchmark --case BM-SOL-TET4-PATCH-001 --output .\results\benchmark
qf-solver import-mesh --mesh modele.msh --setup modele.setup.json --output modele.json
```

Pour un cas V&V existant :

```powershell
qf-solver vnv-import-benchmark --case BM-SOL-CANTILEVER-001 --output .\VNV-CANTILEVER
```

Les sorties de campagne et les documents generes sont des artefacts traces ;
ils ne doivent pas etre modifies manuellement.

## Limites importantes

- Les claims mecaniques sont bornes par element, formulation, maillage,
  chargement et domaine de deformation documentes.
- G02 ne qualifie que l'elasticite Total-Lagrangian TET4/HEX8 avant la zone de
  perte de stabilite ; TET10/HEX20 et le J2 finite-kinematic restent exclus.
- G03 est une analyse de premier seuil d'instabilite tangentielle, pas une
  prediction generale de ruine avec imperfections.
- G05 concerne un contact sans frottement borne entre noeuds/patchs esclaves et
  surface triangulee fournie ; il ne constitue pas un contact mortar ou
  surface-a-surface general.
- L'arc-length, le couplage des non-linearites, le frottement et la
  plasticite finite-strain sont experimentaux, differes ou hors scope.
- Aucune revendication nouvelle de calcul non lineaire a plusieurs millions de
  DDL n'est faite. PETSc/SLEPc restent optionnels.
- Une correlation Code_Aster/CalculiX est une preuve numerique dans un cas
  comparable, pas une certification ni une validation physique universelle.

Voir [`docs/etat/limites.md`](docs/etat/limites.md) pour les details et les
restrictions d'usage.

## Documentation et developpement

```powershell
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
python -m ruff check src scripts tests
python -m compileall -q src scripts tests qf_solver.py
```

La documentation de developpement est indexee dans
[`docs/index.md`](docs/index.md). Les conventions d'API sont dans
[`docs/reference/api_stability.md`](docs/reference/api_stability.md), et la
feuille de route dans [`prochaines_etapes.md`](prochaines_etapes.md).

## Evolution du projet

| Version | Contribution principale |
| --- | --- |
| `0.2.0a0` | Base open source, premier cadre V&V et packaging public initial. |
| `0.2.1a0` | Registre de qualification, automatisation release V&V, correlations externes et tracabilite renforcee. |
| `0.2.2a0` | Backend sparse renforce, selection/diagnostics des solveurs, optimisation memoire et preparation PETSc/SLEPc/HPC. |
| `0.2.3a0` | Integration HEX8/HEX20, import Gmsh, chargements, post-traitement et benchmarks TET/HEX. |
| `0.2.4a0` | J2 small-strain commun, Full Newton, tangent coherent et etats `trial/commit/rollback`. |
| `0.2.5a0` | Qualification bornee J2, elasticite Total-Lagrangian, flambement sparse, contact sans frottement, performance et modes d'echec. |

Voir [`CHANGELOG.md`](CHANGELOG.md) pour l'historique detaille des releases.

Les capacites arc-length, J2 finite-kinematic et les couplages non lineaires
restent experimentaux et exclus des claims qualifies de `0.2.5a0`.

## Licence

Le code est sous [Apache License 2.0](LICENSE). La documentation et les
exemples originaux sont sous [CC BY 4.0](LICENSE-DOCS). Les composants tiers
restent soumis a leurs licences, inventoriees dans
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
