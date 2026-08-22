# QF_solver

Solveur FEM Python boite blanche, utilisable par CLI et API. Le projet couvre
les solides TET4/TET10, les coques MITC3+/MITC4, la statique, le modal, Newmark,
l'harmonique, un non-lineaire experimental et un chemin grand modele.

## Origine et objectif

QF_solver est un projet personnel commence en aout 2024 par Quentin Farinazzo.
Il est publie progressivement, par perimetres techniques et preuves V&V
associees, plutot que comme un bloc opaque. Son objectif a long terme est de
proposer un solveur FEM ouvert, fiable, explicable et utile a l'ingenieur : les
hypotheses, limites, validations et resultats doivent pouvoir etre relus.

Cette alpha ne revendique ni certification externe, ni equivalence generale a
un logiciel commercial. Elle fournit un noyau ouvert et des domaines d'emploi
documentes, a utiliser avec le jugement mecanique adapte au cas calcule.

La version publique cible est **0.2.1a0**, une alpha de consolidation
V&V construite sur la baseline immuable `0.2.0a0` (`v0.2.0-alpha`). Le projet vise
un outil **qualifiable et verifiable**. Il n'est
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

Les documents Markdown et PDF versionnes sont la source detaillee unique pour
les formulations, reperes locaux, solveurs, demonstrations, limites et preuves.

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```

Le premier script regenere les tableaux, figures et manifestes Markdown. Le
second produit le dossier PDF lorsque Pandoc et MiKTeX/LaTeX sont disponibles.
La documentation ne depend d'aucun serveur, navigateur, CDN ou telemetrie.

Une construction `qualification` refuse volontairement une source sans
revision Git approuvee ou avec des exigences orphelines :

```powershell
python .\scripts\build_docs.py --profile qualification
```

## Maturite et perimetres

| Capacite | Maturite actuelle | Usage recommande |
| --- | --- | --- |
| TET4 et TET10 isotropes lineaires | `stable` | Statique, modal, Newmark et harmonique dans les cas documentes |
| MITC3+ isotrope classique | `stable` | Statique, modal, Newmark et harmonique dans les domaines documentes |
| MITC3+ multicouche mince plan et courbe mixte/transverse | `stable` | Sous-perimetres explicitement limites; domaine axial complet non promu |
| MITC4 isotrope | `stable` | Statique, modal, Newmark et harmonique avec masse coherente et drilling condense |
| MITC4 multicouche plan et orthotrope mono-pli | `stable` | Layups, geometries et exclusions explicitement documentes |
| BEAM2 et entites discretes lineaires | `stable` | Statique, modal, Newmark et harmonique documentes |
| Solides orthotropes TET4/TET10 | `stable` | Materiau homogene, statique, modal et Newmark dans le domaine teste |
| J2 TET4/TET10, contact et grand modele TET4 | `accepted_for_bounded_engineering_use` | Usage borne; limites propres a chaque scope obligatoires |
| TET4 total-lagrangien structurel | `research` | Preuves incompletes; aucune promotion engineering |
| MITC4 orthotrope courbe | `out_of_acceptance` | Diagnostic interne uniquement, sans revendication d'usage |

Le detail des 36 scopes de release, de leurs preuves et de leurs exclusions est
dans le [registre de maturite](qualification/element_analysis_matrix.json) et
dans le [paquet de cloture](docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md).

## Etat de la release 0.2.1a0

La consolidation locale est avancee, mais la release n'est pas encore gelee :
le dernier controle `release-vv` recense `28` scopes PASS et `8` scopes
volontairement non stables. Le lot public a passe l'audit de confidentialite et
de vocabulaire (`1550` fichiers analyses, `0` finding). Restent obligatoires
avant toute publication : la campagne de release complete, la revalidation
Owner finale et un checkout Git propre. Aucun tag ni push n'est cree par ces
preparatifs.

Les manifestes de documentation calculent le nombre de tests, la campagne
courante, la revision source et les verdicts au moment de la generation.
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

Preparation locale de l'alpha `0.2.1a0` :

```powershell
python -m pip install -e ".[test]"
qf-solver --version
```

Apres publication, la meme version pourra etre installee depuis PyPI avec
`python -m pip install "qf-solver==0.2.1a0"`. Cette commande devient disponible
apres publication effective sur PyPI ; le present checkout ne la declenche pas.

Pendant la preparation locale, les extras s'installent depuis le checkout :

```powershell
python -m pip install -e ".[mesh]"  # import Gmsh MSH 4.1
python -m pip install -e ".[docs]"  # outils de construction documentaire
python -m pip install -e ".[large]" # HDF5, PETSc et MPI
```

Apres publication, les memes extras seront disponibles avec la forme
`qf-solver[mesh]==0.2.1a0`, `qf-solver[docs]==0.2.1a0` ou
`qf-solver[large]==0.2.1a0`.

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
generaliste et la formulation MITC4 canonique vit sous
`src/solveur/elements/shell/mitc4`. `src/solveur/compat/mitc4` ne conserve que des facades
de compatibilite depreciees pour la serie `0.2.x`. Les choix d'architecture et la place du conteneur
PETSc/MPI optionnel sont detailles dans
[`docs/architecture.md`](docs/architecture.md).

La wheel PyPI contient le runtime, les exemples JSON et les registres
machine-readable necessaires au fonctionnement courant. Le manuel complet,
les tests et les preuves V&V restent dans le depot GitHub; generer les
artefacts Markdown/PDF ou executer `qualification-readiness` avec verification de tous les liens
necessite donc un clone source. L'extra `docs` installe les outils de
construction, pas une livraison web preconstruite.

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
python -m ruff check src scripts tests
python -m pytest
python -m compileall -q src scripts tests qf_solver.py main_solveur.py mitc4_solver.py
python .\qf_solver.py verify --quick
python .\mitc4_solver.py verify
python .\scripts\build_docs.py --profile engineering
```

Le depot de developpement contient un corpus V&V de travail d'environ 12,2 Go
qui n'est pas inclus dans l'archive source. Les tests marques `evidence`
s'executent lorsque ce corpus et le manifeste documentaire genere sont
presents ; dans une archive publique legere, ils sont explicitement ignores.
Les tests du noyau, de l'API, de la CLI et des formulations restent obligatoires.
La copie publique fournit les sources Markdown, PDF et artefacts documentaires
versionnes. La commande `build_docs.py` regenere toutes les preuves et requiert
donc le corpus V&V de developpement.

## Documents de pilotage

- [Prochaines etapes](prochaines_etapes.md)
- [Analyse historique du solveur](docs/reference/legacy/analyse_solveur_ef.md)
- [Audit de qualification industrielle](docs/audit_qualification_industrielle.md)
- [Architecture](docs/architecture.md)
- [Registre d'exigences](qualification/requirements.json)
- [Registre des formules](qualification/formulas.json)
- [Perimetre V&V MITC4](docs/verification/mitc4_validation.md)
- [Baseline engineering 0.2.0](qualification/baselines/qf_solver_0.2.0_engineering.md)
- [Pack V&V release 0.2.1a0](docs/verification/release_vv_0_2_1.md)
- [Paquet de cloture Owner 0.2.1a0](docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md)
- [Decision finale Owner 0.2.1a0](docs/verification/owner_final_release_decision_0_2_1a0.md)
- [Audit hygiene et architecture 0.2.1a0](docs/verification/project_hygiene_architecture_audit_0_2_1.md)
- [Cloture technique P0 documentaire](docs/verification/baseline_documentaire_p0.md)
- [Changelog](CHANGELOG.md)

Les artefacts generes ne sont pas edites a la main. Toute valeur numerique
publiee doit provenir de `scripts/build_docs.py` et etre reliee a son entree,
sa tolerance, son verdict et son empreinte SHA-256.
