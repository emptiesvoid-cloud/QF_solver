# QF_solver

Solveur FEM Python boite blanche, utilisable par CLI et API. Le projet couvre
les solides TET4/TET10, les coques MITC3+/MITC4, la statique, le modal, Newmark,
l'harmonique, un non-lineaire experimental et un chemin grand modele.

La version publique preparee est **0.2.0a0**, correspondant au tag de release
`v0.2.0-alpha`. Le projet vise un outil **qualifiable et verifiable**. Il n'est
pas presente comme certifie et ne doit pas remplacer une Owner review
mecanique adaptee au cas d'emploi.

## Licence et attribution

Le code source de QF_solver est publie sous
[Apache License 2.0](LICENSE). La documentation et les exemples originaux
sont publies sous [CC BY 4.0](LICENSE-DOCS). Les composants tiers restent
regis par leurs propres licences, recensees dans
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

QF_solver est un projet personnel de Quentin Farinazzo. La licence autorise
la reutilisation et l'usage commercial, mais ne constitue ni une garantie de
resultat mecanique ni une certification. Les contrats publics, les regles de
contribution, de securite et de signalement V&V sont disponibles dans
[`OPEN_SOURCE_READINESS.md`](OPEN_SOURCE_READINESS.md).

## Documentation technique

Le site MkDocs local est la source detaillee unique pour les formulations,
reperes locaux, solveurs, demonstrations, limites et preuves.

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\serve_docs.py
```

Le dernier script ouvre directement le navigateur systeme, puis reste actif
jusqu'a `Ctrl+C`. La construction
est entierement hors ligne : MathJax, polices et ressources visuelles sont
locales.

Pour verifier la publication sans lancer de serveur ni de navigateur :

```powershell
python .\scripts\serve_docs.py --check
```

Une construction `qualification` refuse volontairement une source sans
revision Git approuvee ou avec des exigences orphelines :

```powershell
python .\scripts\build_docs.py --profile qualification
```

## Maturite

| Capacite | Maturite actuelle | Usage recommande |
| --- | --- | --- |
| TET4 statique lineaire, maillage, audit, API/CLI | `stable` | Calcul engineering borne et revu |
| MITC4 statique, modal, Newmark et harmonique isotropes | `owner_accepted_bounded` | Domaines lineaires documentes; masse coherente et drilling condense en dynamique |
| MITC4 multicouche statique | `owner_accepted_bounded` | Stratifies documentes dans le domaine lineaire couvert |
| MITC4 multicouche dynamique plane | `owner_accepted_experimental_bounded_use` | Trois empilements symetriques; reserve modale 10 000 QUAD4; dynamique courbe exclue |
| MITC3+ statique et dynamique lineaire isotrope | `owner_accepted_bounded` | Statique, modal, Newmark et harmonique dans les domaines documentes |
| MITC3+ multicouche courbe projete | `owner_accepted_experimental_bounded_use` | Statique courbe seulement; extension dynamique encore experimentale |
| Modal, Newmark, harmonique solides | `stable_after_reinforced_tests` | Engineering avec revue des residus |
| TET10 lineaire isotrope | `stable_after_reinforced_tests` | Validation interne avec recommandations du 2026-07-18 |
| TET10 avance, materiaux non lineaires | `experimental` | Hors du scope lineaire accepte |
| Lamelle, CLT et criteres premier pli | `experimental` | V&V analytique/structurelle disponible; dommage, rupture progressive et delaminage exclus |
| Solides orthotropes TET4/TET10 | `engineering_internal_validated_with_recommendations` | Statique lineaire borne accepte; TET4 a raffiner en flexion, campagne complexe finale differee |
| Contact sans frottement borne | `engineering_ready_bounded` | Owner review acceptee le 29 juillet 2026; statique lineaire, petites transformations et active-set noeud-triangle uniquement |
| Grand modele PETSc/MPI | `experimental` | Campagne dediee, pas de qualification implicite |

Le tableau de bord du site calcule le nombre de tests, la campagne courante,
la revision source et les verdicts au moment de la construction.
La page de revue publie aussi la couverture des 61 formules critiques et
distingue explicitement controle automatique, Owner review et baseline Git.

La validation engineering interne du TET4 lineaire isotrope est documentee
dans la [decision de revue](docs/verification/revue_tet4_lineaire.md). Une
[page HTML autonome](docs/reference/reports/REVUE_TET4_LINEAIRE.html) rassemble aussi les tableaux,
conclusions et PNG pour une lecture locale sans serveur.

Le MITC4 statique lineaire est valide pour l'usage engineering interne avec
reservations, dans sa [decision de revue](docs/verification/revue_mitc4_lineaire.md).

Le dossier Newmark MITC4 couvre vibration libre, amortissement, impulsion,
chirp, table arbitraire, contraintes de face et correlation Code_Aster. Quentin
Farinazzo l'accepte avec recommandations le `2026-07-16` pour l'usage
engineering interne. La [revue mecanique](docs/verification/revue_mitc4_transitoire.md)
reste une auto-revue non independante.

La configuration source, les controles passes et les reserves de la version
figee sont consignes dans la
[baseline engineering QF_solver 0.2.0](qualification/baselines/qf_solver_0.2.0_engineering.md).

## Installation

Installation de la version alpha distribuee sur PyPI :

```powershell
python -m pip install "qf-solver==0.2.0a0"
qf-solver --version
```

Les fonctionnalites optionnelles s'installent avec les extras correspondants :

```powershell
python -m pip install "qf-solver[mesh]==0.2.0a0"  # import Gmsh MSH 4.1
python -m pip install "qf-solver[docs]==0.2.0a0"  # outils de construction documentaire
python -m pip install "qf-solver[large]==0.2.0a0" # HDF5, PETSc et MPI
```

Pour contribuer ou executer la suite de tests depuis un clone du depot :

```powershell
python -m pip install -e ".[test]"
```

Extras en mode developpement :

```powershell
python -m pip install -e ".[docs]"   # documentation locale
python -m pip install -e ".[mesh]"   # import Gmsh MSH 4.1 et benchmarks mailles
python -m pip install -e ".[large]"  # HDF5, PETSc et MPI si disponibles
```

Python 3.10 a 3.13 est cible par la CI. Les versions de baseline sont dans
[`requirements/`](requirements/).

Le code installable suit un layout `src/`: `src/solveur` porte le produit
generaliste et `src/mitc4` conserve le noyau historique valide utilise par
l'adaptateur coque. Les choix d'architecture et la place du conteneur
PETSc/MPI optionnel sont detailles dans
[`docs/architecture.md`](docs/architecture.md).

La wheel PyPI contient le runtime, les exemples JSON et les registres
machine-readable necessaires au fonctionnement courant. Le manuel complet,
les tests et les preuves V&V restent dans le depot GitHub; construire le site
ou executer `qualification-readiness` avec verification de tous les liens
necessite donc un clone source. L'extra `docs` installe les outils de
construction, pas une copie preconstruite du site.

## Premier calcul

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results.json
qf-solver evidence --input .\examples\tet4_static.json --output .\evidence
```

Sans entree `Scripts` dans le `PATH`, la forme portable equivalente est
`python -m solveur.cli.main`. `solveur-ef` et `main_solveur.py` sont des alias
deprecies conserves jusqu'a la version 0.3.0.

API publique :

```python
from solveur.api import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
result = solve_model(model)
save_result(result, "results.json")
```

Les codes de sortie CLI stables sont `0` (accepte), `2` (entree/maillage),
`3` (numerique), `4` (refus de qualification) et `5` (infrastructure).

## Grands modeles

Le chemin large-scale v1 est limite a `linear_static + TET4` avec materiau
`isotropic_3d`, `orthotropic_3d` ou `composite_orthotropic_3d` homogeneise.
Il utilise des tableaux compacts, HDF5/NPZ et, si installe, PETSc/MPI. La
preuve orthotrope a `1 029 000` DDL est technique; le modal et Newmark
distribues restent hors scope.

```powershell
qf-solver generate-large-tet4-block --output model.npz --nx 20 --ny 8 --nz 8
qf-solver solve-large --input model.npz --output results_large --solver-backend matrix_free
```

## Gmsh et benchmarks mailles

```powershell
qf-solver import-mesh --mesh modele.msh --setup modele.setup.json --output modele.json
qf-solver benchmarks
qf-solver benchmark --case BM-SOL-TET4-PATCH-001 --output .\results\benchmarks
```

Le catalogue controle contient dix structures maillees: patch TET4, panneau
mince TET4 en traction/compression, arbre circulaire TET4 en torsion, poutre
TET4/TET10, cylindre de Lame TET10, Cook, Scordelis-Lo, cylindre pince,
porte-a-faux dynamique et barre J2. Le registre autoritatif est
[`qualification/benchmarks.json`](qualification/benchmarks.json).

## Etudes V&V avec theorie, Code_Aster et CalculiX

Le contrat V&V normalise les resultats externes, automatise les ecarts et la
convergence en maillage, puis produit un rapport Markdown avec les deformees
QF_solver/reference et les liens VTU :

```powershell
qf-solver vnv-compare --study .\study.json --output .\results\vnv_study
```

Un cas TET4 de porte-a-faux avec quatre niveaux de maillage, PNG et reference
analytique peut etre initialise depuis le benchmark existant :

```powershell
qf-solver vnv-import-benchmark --case BM-SOL-CANTILEVER-001 --output .\VNV-TET4-CANTILEVER-ANALYTIC-001
qf-solver vnv-import-benchmark --case BM-SOL-TET4-TORSION-001 --output .\VNV-TET4-TORSION-ANALYTIC-001
```

L'etude de torsion contient huit comparaisons QF_solver/Saint-Venant puis une
sonde h9 a `105 529` TET4, soit `4,007` fois h8. L'erreur globale L2 de
contrainte descend de `29,06 %` a `18,89 %`; le cas est accepte pour l'usage
engineering interne sous un seuil global borne a `20 %`. Les pics ponctuels
et singularites restent exclus.

```powershell
python .\scripts\run_torsion_stress_probe.py `
  --output .\VNV-TET4-TORSION-ANALYTIC-001\stress_probe_h9 `
  --overwrite
```

Les formats, modeles et regles de revue sont decrits dans
[Etudes V&V comparees](docs/verification/etudes_vnv.md). La politique active
est [Code_Aster / CalculiX / theorie](qualification/external_oracle_policy.json);
les references Abaqus publiees restent historiques et ne sont pas requises. La baseline declare
Quentin Farinazzo comme auteur et validateur mecanique en mode `self_review`;
ce mode ne revendique aucune independence externe.

## Verification developpeur

```powershell
python -m ruff check solveur mitc4 scripts tests
python -m pytest
python -m compileall -q solveur mitc4 scripts tests qf_solver.py main_solveur.py mitc4_solver.py
python .\qf_solver.py verify --quick
python .\mitc4_solver.py verify
python .\scripts\build_docs.py --profile engineering
```

Le depot de developpement contient un corpus V&V de travail d'environ 12,2 Go
qui n'est pas inclus dans l'archive source. Les tests marques `evidence`
s'executent lorsque ce corpus et le manifeste documentaire genere sont
presents ; dans une archive publique legere, ils sont explicitement ignores.
Les tests du noyau, de l'API, de la CLI et des formulations restent obligatoires.
La copie publique fournit un snapshot documentaire leger, constructible avec
`python -m mkdocs build --strict --clean`. La commande `build_docs.py`
regenere toutes les preuves et requiert donc le corpus V&V de developpement.

## Documents de pilotage

- [Prochaines etapes](prochaines_etapes.md)
- [Analyse historique du solveur](docs/reference/legacy/analyse_solveur_ef.md)
- [Audit de qualification industrielle](docs/audit_qualification_industrielle.md)
- [Architecture](docs/architecture.md)
- [Registre d'exigences](qualification/requirements.json)
- [Registre des formules](qualification/formulas.json)
- [Perimetre V&V MITC4](docs/verification/mitc4_validation.md)
- [Baseline engineering 0.2.0](qualification/baselines/qf_solver_0.2.0_engineering.md)
- [Cloture technique P0 documentaire](docs/verification/baseline_documentaire_p0.md)
- [Changelog](CHANGELOG.md)

Les fichiers generes du site ne sont pas edites a la main. Toute valeur
numerique publiee doit provenir de `scripts/build_docs.py` et etre reliee a son
entree, sa tolerance, son verdict et son empreinte SHA-256.
