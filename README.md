# QF_solver

Solveur FEM Python boîte blanche, utilisable par CLI et API. Le projet couvre
les solides TET4/TET10, les coques MITC3+/MITC4, la statique, le modal, Newmark,
l'harmonique, un non-linéaire expérimental et un chemin grand modèle.

## Origine et objectif

QF_solver est un projet personnel commencé en août 2024 par Quentin Farinazzo.
Il est publié progressivement, par périmètres techniques et preuves V&V
associées, plutôt que comme un bloc opaque. Son objectif à long terme est de
proposer un solveur FEM ouvert, fiable, explicable et utile à l'ingénieur : les
hypothèses, limites, validations et résultats doivent pouvoir être relus.

Cette alpha ne revendique ni certification externe, ni équivalence générale à
un logiciel commercial. Elle fournit un noyau ouvert et des domaines d'emploi
documentés, à utiliser avec le jugement mécanique adapté au cas calculé.

La version publique cible est **0.2.1a0**, une alpha de consolidation
V&V construite sur la baseline immuable `0.2.0a0` (`v0.2.0-alpha`). Le projet vise
un outil **qualifiable et vérifiable**. Il n'est
pas présenté comme certifié et ne doit pas remplacer une Owner review
mécanique adaptée au cas d'emploi.

## Licence et attribution

Le code source de QF_solver est publié sous
[Apache License 2.0](LICENSE). La documentation et les exemples originaux
sont publies sous [CC BY 4.0](LICENSE-DOCS). Les composants tiers restent
régis par leurs propres licences, recensées dans
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

QF_solver est un projet personnel de Quentin Farinazzo. La licence autorise
la réutilisation et l'usage commercial, mais ne constitue ni une garantie de
résultat mécanique ni une certification. Les contrats publics, les règles de
contribution, de sécurité et de signalement V&V sont disponibles dans
[`OPEN_SOURCE_READINESS.md`](OPEN_SOURCE_READINESS.md).

## Documentation technique

Les documents Markdown et PDF versionnés sont la source détaillée unique pour
les formulations, repères locaux, solveurs, démonstrations, limites et preuves.

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```

Le premier script régénère les tableaux, figures et manifestes Markdown. Le
second produit le dossier PDF lorsque Pandoc et MiKTeX/LaTeX sont disponibles.
La documentation ne dépend d'aucun serveur, navigateur, CDN ou télémétrie.

Une construction `qualification` refuse volontairement une source sans
révision Git approuvée ou avec des exigences orphelines :

```powershell
python .\scripts\build_docs.py --profile qualification
```

## Maturité et périmètres

| Capacite | Maturite actuelle | Usage recommande |
| --- | --- | --- |
| TET4 et TET10 isotropes linéaires | `stable` | Statique, modal, Newmark et harmonique dans les cas documentés |
| MITC3+ isotrope classique | `stable` | Statique, modal, Newmark et harmonique dans les domaines documentés |
| MITC3+ multicouche mince plan et courbe mixte/transverse | `stable` | Sous-périmètres explicitement limités ; domaine axial complet non promu |
| MITC4 isotrope | `stable` | Statique, modal, Newmark et harmonique avec masse cohérente et drilling condensé |
| MITC4 multicouche plan et orthotrope mono-pli | `stable` | Layups, géométries et exclusions explicitement documentés |
| BEAM2 et entités discrètes linéaires | `stable` | Statique, modal, Newmark et harmonique documentés |
| Solides orthotropes TET4/TET10 | `stable` | Matériau homogène, statique, modal et Newmark dans le domaine testé |
| J2 TET4/TET10, contact et grand modèle TET4 | `accepted_for_bounded_engineering_use` | Usage borné ; limites propres à chaque scope obligatoires |
| TET4 total-lagrangien structurel | `research` | Preuves incomplètes ; aucune promotion engineering |
| MITC4 orthotrope courbe | `out_of_acceptance` | Diagnostic interne uniquement, sans revendication d'usage |

Le détail des 36 scopes de release, de leurs preuves et de leurs exclusions est
dans le [registre de maturité](qualification/element_analysis_matrix.json) et
dans le [paquet de clôture](docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md).

## État de la release 0.2.1a0

La consolidation locale est avancée, mais la release n'est pas encore gelée :
le dernier contrôle `release-vv` recense `28` scopes PASS et `8` scopes
volontairement non stables. Le lot public a passé l'audit de confidentialité et
de vocabulaire (`1550` fichiers analysés, `0` constat). Restent obligatoires
avant toute publication : la campagne de release complète, la revalidation
Owner finale et un checkout Git propre. La branche `main` contient les
préparatifs ; aucun nouveau tag de release ni publication PyPI n'est effectué.

Les manifestes de documentation calculent le nombre de tests, la campagne
courante, la révision source et les verdicts au moment de la génération.
La page de revue publie aussi la couverture des 61 formules critiques et
distingue explicitement contrôle automatique, Owner review et baseline Git.

La validation engineering interne du TET4 linéaire isotrope est documentée
dans la [décision de revue](docs/verification/revue_tet4_lineaire.md). Une
[page HTML autonome](docs/reference/reports/REVUE_TET4_LINEAIRE.html) rassemble aussi les tableaux,
conclusions et PNG pour une lecture locale sans serveur.

Le MITC4 statique linéaire est valide pour l'usage engineering interne avec
réserves, dans sa [décision de revue](docs/verification/revue_mitc4_lineaire.md).

Le dossier Newmark MITC4 couvre vibration libre, amortissement, impulsion,
chirp, table arbitraire, contraintes de face et corrélation Code_Aster. Quentin
Farinazzo l'accepte avec recommandations le `2026-07-16` pour l'usage
engineering interne. La [revue mécanique](docs/verification/revue_mitc4_transitoire.md)
reste une auto-revue non indépendante.

La configuration source, les contrôles passés et les réserves de la version
figée sont consignés dans la
[baseline engineering QF_solver 0.2.0](qualification/baselines/qf_solver_0.2.0_engineering.md).

## Installation

Préparation locale de l'alpha `0.2.1a0` :

```powershell
python -m pip install -e ".[test]"
qf-solver --version
```

Après publication, la même version pourra être installée depuis PyPI avec
`python -m pip install "qf-solver==0.2.1a0"`. Cette commande devient disponible
après publication effective sur PyPI ; le présent checkout ne la déclenche pas.

Pendant la préparation locale, les extras s'installent depuis le checkout :

```powershell
python -m pip install -e ".[mesh]"  # import Gmsh MSH 4.1
python -m pip install -e ".[docs]"  # outils de construction documentaire
python -m pip install -e ".[large]" # HDF5, PETSc et MPI
```

Après publication, les mêmes extras seront disponibles avec la forme
`qf-solver[mesh]==0.2.1a0`, `qf-solver[docs]==0.2.1a0` ou
`qf-solver[large]==0.2.1a0`.

Pour contribuer ou exécuter la suite de tests depuis un clone du dépôt :

```powershell
python -m pip install -e ".[test]"
```

Extras en mode développement :

```powershell
python -m pip install -e ".[docs]"   # documentation locale
python -m pip install -e ".[mesh]"   # import Gmsh MSH 4.1 et benchmarks mailles
python -m pip install -e ".[large]"  # HDF5, PETSc et MPI si disponibles
```

Python 3.10 à 3.13 est ciblé par la CI. Les versions de baseline sont dans
[`requirements/`](requirements/).

Le code installable suit un layout `src/` : `src/solveur` porte le produit
généraliste et la formulation MITC4 canonique vit sous
`src/solveur/elements/shell/mitc4`. `src/solveur/compat/mitc4` ne conserve que des façades
de compatibilité dépréciées pour la série `0.2.x`. Les choix d'architecture et la place du conteneur
PETSc/MPI optionnel sont détaillés dans
[`docs/architecture.md`](docs/architecture.md).

La wheel PyPI contient le runtime, les exemples JSON et les registres
machine-readable nécessaires au fonctionnement courant. Le manuel complet,
les tests et les preuves V&V restent dans le dépôt GitHub ; générer les
artefacts Markdown/PDF ou exécuter `qualification-readiness` avec vérification de tous les liens
nécessite donc un clone source. L'extra `docs` installe les outils de
construction, pas une livraison web préconstruite.

## Premier calcul

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results.json
qf-solver evidence --input .\examples\tet4_static.json --output .\evidence
```

Sans entrée `Scripts` dans le `PATH`, la forme portable équivalente est
`python -m solveur.cli.main`. `solveur-ef` et `main_solveur.py` sont des alias
dépréciés conservés jusqu'à la version 0.3.0.

API publique :

```python
from solveur.api import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
result = solve_model(model)
save_result(result, "results.json")
```

Les codes de sortie CLI stables sont `0` (accepté), `2` (entrée/maillage),
`3` (numérique), `4` (refus de qualification) et `5` (infrastructure).

## Grands modèles

Le chemin large-scale v1 est limité à `linear_static + TET4` avec matériau
`isotropic_3d`, `orthotropic_3d` ou `composite_orthotropic_3d` homogénéisé.
Il utilise des tableaux compacts, HDF5/NPZ et, si installé, PETSc/MPI. La
preuve orthotrope à `1 029 000` DDL est technique ; le modal et Newmark
distribués restent hors scope.

```powershell
qf-solver generate-large-tet4-block --output model.npz --nx 20 --ny 8 --nz 8
qf-solver solve-large --input model.npz --output results_large --solver-backend matrix_free
```

## Gmsh et benchmarks maillés

```powershell
qf-solver import-mesh --mesh modele.msh --setup modele.setup.json --output modele.json
qf-solver benchmarks
qf-solver benchmark --case BM-SOL-TET4-PATCH-001 --output .\results\benchmarks
```

Le catalogue contrôlé contient dix structures maillées : patch TET4, panneau
mince TET4 en traction/compression, arbre circulaire TET4 en torsion, poutre
TET4/TET10, cylindre de Lame TET10, Cook, Scordelis-Lo, cylindre pince,
porte-a-faux dynamique et barre J2. Le registre autoritatif est
[`qualification/benchmarks.json`](qualification/benchmarks.json).

## Études V&V avec théorie, Code_Aster et CalculiX

Le contrat V&V normalise les résultats externes, automatise les écarts et la
convergence en maillage, puis produit un rapport Markdown avec les déformées
QF_solver/reference et les liens VTU :

```powershell
qf-solver vnv-compare --study .\study.json --output .\results\vnv_study
```

Un cas TET4 de porte-à-faux avec quatre niveaux de maillage, PNG et référence
analytique peut être initialisé depuis le benchmark existant :

```powershell
qf-solver vnv-import-benchmark --case BM-SOL-CANTILEVER-001 --output .\VNV-TET4-CANTILEVER-ANALYTIC-001
qf-solver vnv-import-benchmark --case BM-SOL-TET4-TORSION-001 --output .\VNV-TET4-TORSION-ANALYTIC-001
```

L'étude de torsion contient huit comparaisons QF_solver/Saint-Venant puis une
sonde h9 à `105 529` TET4, soit `4,007` fois h8. L'erreur globale L2 de
contrainte descend de `29,06 %` à `18,89 %` ; le cas est accepté pour l'usage
engineering interne sous un seuil global borné à `20 %`. Les pics ponctuels
et singularités restent exclus.

```powershell
python .\scripts\run_torsion_stress_probe.py `
  --output .\VNV-TET4-TORSION-ANALYTIC-001\stress_probe_h9 `
  --overwrite
```

Les formats, modèles et règles de revue sont décrits dans
[Études V&V comparées](docs/verification/etudes_vnv.md). La politique active
est [Code_Aster / CalculiX / théorie](qualification/external_oracle_policy.json) ;
les références Abaqus publiées restent historiques et ne sont pas requises. La baseline déclare
Quentin Farinazzo comme auteur et validateur mécanique en mode `self_review` ;
ce mode ne revendique aucune indépendance externe.

## Vérification développeur

```powershell
python -m ruff check src scripts tests
python -m pytest
python -m compileall -q src scripts tests qf_solver.py main_solveur.py mitc4_solver.py
python .\qf_solver.py verify --quick
python .\mitc4_solver.py verify
python .\scripts\build_docs.py --profile engineering
```

Le dépôt de développement contient un corpus V&V de travail d'environ 12,2 Go
qui n'est pas inclus dans l'archive source. Les tests marqués `evidence`
s'exécutent lorsque ce corpus et le manifeste documentaire généré sont
présents ; dans une archive publique légère, ils sont explicitement ignorés.
Les tests du noyau, de l'API, de la CLI et des formulations restent obligatoires.
La copie publique fournit les sources Markdown, PDF et artefacts documentaires
versionnés. La commande `build_docs.py` régénère toutes les preuves et requiert
donc le corpus V&V de développement.

## Documents de pilotage

- [Prochaines étapes](prochaines_etapes.md)
- [Analyse historique du solveur](docs/reference/legacy/analyse_solveur_ef.md)
- [Audit de qualification industrielle](docs/audit_qualification_industrielle.md)
- [Architecture](docs/architecture.md)
- [Registre d'exigences](qualification/requirements.json)
- [Registre des formules](qualification/formulas.json)
- [Périmètre V&V MITC4](docs/verification/mitc4_validation.md)
- [Baseline engineering 0.2.0](qualification/baselines/qf_solver_0.2.0_engineering.md)
- [Pack V&V release 0.2.1a0](docs/verification/release_vv_0_2_1.md)
- [Paquet de clôture Owner 0.2.1a0](docs/verification/release_vv_0_2_1_closure_package_2026-08-22.md)
- [Décision finale Owner 0.2.1a0](docs/verification/owner_final_release_decision_0_2_1a0.md)
- [Audit hygiène et architecture 0.2.1a0](docs/verification/project_hygiene_architecture_audit_0_2_1.md)
- [Clôture technique P0 documentaire](docs/verification/baseline_documentaire_p0.md)
- [Changelog](CHANGELOG.md)

Les artefacts générés ne sont pas édités à la main. Toute valeur numérique
publiée doit provenir de `scripts/build_docs.py` et être reliée à son entrée,
sa tolérance, son verdict et son empreinte SHA-256.
