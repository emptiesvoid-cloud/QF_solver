---
doc_id: DOC-LRG-002
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Mode grand modele

Le mode grand modele est un chemin separe du solveur standard. Il vise les
maillages TET4 statiques lineaires avec beaucoup de ddl, sans produire de JSON
monolithique contenant tous les deplacements.

## Objectif de continuation

Le prochain jalon mesurable est de rendre le solveur capable de generer,
resoudre, auditer et benchmarker un cas TET4 statique lineaire d'au moins
1 million de ddl, avec sorties HDF5 et dossier de preuve verifiable. Le mode
SciPy sert au developpement et a la comparaison sur petits cas; le mode PETSc
est la cible scalable pour les vrais gros modeles.

La campagne `VNV-LARGE-PETSC-SCIPY-001` compare la solution SciPy au chemin
PETSc/GAMG sur deux rangs MPI Docker, sur le meme bloc HDF5. L'ecart de
deplacement `1,02e-12` et les deux residus sous `1e-7` etablissent l'accord
numerique. Cette comparaison ne constitue pas une mesure de performance.

## Perimetre v1

Supporte:

- analyse `linear_static`;
- elements `TET4`;
- materiaux `isotropic_3d`;
- ddl homogenes `UX`, `UY`, `UZ`;
- entree HDF5 `.h5/.hdf5` ou NPZ `.npz`;
- sortie standard `displacements.h5/.npz`; sortie PETSc multi-rangs
  `displacements.bin` par MPI-IO collectif avec metadonnees JSON;
- generation de blocs TET4 synthetiques;
- benchmark avec `benchmark_large.json`, `benchmark_large.md` et
  `runtime_environment.json`, `evidence_manifest.json`;
- backend `scipy` pour tests et modeles intermediaires;
- backend `petsc` optionnel pour usage scalable.
- backend `matrix_free` pour les blocs structures produits par
  `generate-large-tet4-block`, sans assemblage de matrice globale.

Non supporte en v1 large-scale:

- `MITC4`, `TET10`;
- modal, dynamique, harmonique;
- non-lineaire;
- chargements repartis (`distributed_loads`); la conversion les refuse au lieu
  de les supprimer silencieusement;
- audit elementaire complet;
- export VTU ASCII monolithique.

## Installation

Le chemin standard ne change pas. Pour activer les dependances grand modele:

```powershell
python -m pip install -e .[large]
```

Si `petsc4py`, `mpi4py` ou `h5py` manquent, les commandes concernées echouent
avec un message explicite. Le backend `scipy` reste disponible pour valider le
flux localement.

Sous Windows, le paquet PETSc officiel ne se compile pas avec Python natif.
Le runtime controle utilise donc Docker Linux :

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_large_container.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_container.ps1 -Action test-mpi -Ranks 2
```

L'image `qf-solver-large:0.2.0` est basee sur un digest immuable et contient
Python `3.12.3`, MPI/`mpi4py 4.1.2`, PETSc/`petsc4py 3.25.1` et `h5py 3.13.0`.

## Commandes

Generer un bloc synthetique proche d'une taille cible:

```powershell
python .\qf_solver.py generate-large-tet4-block --output .\results_large\block_1m.h5 --target-dofs 1000000
```

Verifier que la machine et le backend sont prets:

```powershell
python .\qf_solver.py large-readiness --output .\results_large\readiness_1m --target-dofs 1000000 --solver-backend petsc
```

Generer un bloc avec dimensions imposees:

```powershell
python .\qf_solver.py generate-large-tet4-block --output .\results_large\block_small.h5 --nx 4 --ny 4 --nz 4
```

Convertir un JSON existant vers HDF5:

```powershell
python .\qf_solver.py convert-model --input .\examples\tet4_static.json --output .\results_large\tet4_static.h5
```

Inspecter sans resoudre:

```powershell
python .\qf_solver.py inspect-large --input .\results_large\tet4_static.h5 --output .\results_large\audit_large.json
```

Resoudre avec backend de test SciPy:

```powershell
python .\qf_solver.py solve-large --input .\results_large\tet4_static.h5 --output .\results_large\tet4_static --solver-backend scipy
```

Resoudre avec PETSc:

```powershell
python .\qf_solver.py solve-large --input .\results_large\tet4_static.h5 --output .\results_large\tet4_static_petsc --solver-backend petsc --preconditioner gamg
```

Resoudre un bloc genere sans matrice globale:

```powershell
python .\qf_solver.py qualify-large --output .\results_large\qualification_matrix_free --target-dofs 1000000 --solver-backend matrix_free
python .\qf_solver.py verify-large --input .\results_large\qualification_matrix_free --target-dofs 1000000
```

Lancer un benchmark avec dossier de preuve:

```powershell
python .\qf_solver.py benchmark-large --input .\results_large\block_1m.h5 --output .\results_large\block_1m_benchmark --solver-backend petsc --preconditioner gamg
python .\qf_solver.py verify-evidence --input .\results_large\block_1m_benchmark
```

Comparer GAMG et Hypre/BoomerAMG sur le meme modele et verifier l'accord des
deplacements sans les charger integralement:

```powershell
mpiexec -n 4 python .\qf_solver.py large-preconditioners --input .\results_large\block_1m.h5 --output .\results_large\pc_1m --preconditioners gamg hypre
```

Construire un rapport de scalabilite a partir de benchmarks termines:

```powershell
python .\qf_solver.py large-scaling-report --mode weak --inputs .\results_large\weak_r1\benchmark_large.json .\results_large\weak_r2\benchmark_large.json .\results_large\weak_r4\benchmark_large.json --output .\results_large\weak_report
```

Le lanceur Docker reproductible demande volontairement `-Execute`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action weak
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action weak -Execute
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action preconditioners -Execute
```

Lancer le pipeline qualifiant complet en une commande:

```powershell
python .\qf_solver.py large-readiness --output .\results_large\readiness_1m --target-dofs 1000000 --solver-backend petsc
python .\qf_solver.py qualify-large --output .\results_large\qualification_1m --target-dofs 1000000 --solver-backend petsc --preconditioner gamg
python .\qf_solver.py verify-large --input .\results_large\qualification_1m --target-dofs 1000000 --json-report .\results_large\qualification_1m_verify.json --markdown .\results_large\qualification_1m_verify.md
python .\qf_solver.py verify-evidence --input .\results_large\qualification_1m
python .\qf_solver.py verify-evidence --input .\results_large\qualification_1m\benchmark
```

Planifier puis executer la campagne P4 multi-echelle :

```powershell
python .\qf_solver.py large-campaign --output .\results_large\P4-CAMPAIGN-PLAN-001 --targets 100000 1000000 3000000 --solver-backend petsc
python .\qf_solver.py large-campaign --output .\results_large\P4-CAMPAIGN-PETSC-001 --targets 100000 1000000 3000000 --solver-backend petsc --preconditioner gamg --execute
```

Le premier appel est un dimensionnement sans generation de modele. Le second
execute les trois qualifications et ecrit `large_campaign.json`,
`large_campaign.md`, les sous-dossiers de preuve et un manifeste racine.

API equivalente:

```python
from qf_solver import (
    benchmark_large_model,
    check_large_readiness,
    generate_large_tet4_block,
    qualify_large_tet4_pipeline,
    recommended_large_block,
    run_large_scale_campaign,
    verify_large_qualification,
)

nx, ny, nz = recommended_large_block(1_000_000)
readiness = check_large_readiness("readiness_1m", target_dofs=1_000_000, solver_backend="petsc")
generate_large_tet4_block("block_1m.h5", nx=nx, ny=ny, nz=nz)
benchmark = benchmark_large_model("block_1m.h5", "block_1m_evidence", solver_backend="petsc", preconditioner="gamg")
qualification = qualify_large_tet4_pipeline("qualification_1m", target_dofs=1_000_000, solver_backend="petsc")
verification = verify_large_qualification("qualification_1m", target_dofs=1_000_000)
campaign = run_large_scale_campaign(
    "P4-CAMPAIGN-PLAN-001",
    targets=(100_000, 1_000_000, 3_000_000),
    solver_backend="petsc",
    execute=False,
)
```

## Format entree

HDF5 contient:

- `nodes`: `float64 [n_nodes, 3]`;
- `tet4`: `int64 [n_elements, 4]`;
- `material_ids`: `int64 [n_elements]`;
- `fixed_nodes`, `fixed_dofs`;
- `load_nodes`, `load_dofs`, `load_values`;
- attribut `metadata_json` pour analyse, unites et materiaux.

NPZ contient les memes tableaux et `metadata_json`.

## Audit large

`audit_large.json` donne un audit agrege:

- nombre noeuds, elements et ddl;
- nombre ddl fixes/libres;
- statistiques qualite TET4 min/max/moyenne;
- volumes invalides et elements de faible qualite;
- echantillon deterministe d'elements;
- norme charge, norme deplacement, residu libre;
- energie de deformation et travail externe quand une solution est disponible.

Le mode large interdit les conversions dense type `toarray()` dans le chemin de
resolution teste.

## Sorties benchmark

`benchmark-large` ecrit:

- `input_fingerprint.json`: taille et SHA-256 du modele d'entree;
- `runtime_environment.json`: version solveur, Python, plateforme, dependances
  critiques, variables de parallelisme et metadonnees du run;
- `summary.json`: statut, backend, iterations, residu, temps et estimation memoire;
- `audit_large.json`: audit agrege du modele et de la solution;
- `displacements.h5/.npz`, ou `displacements.bin` avec
  `displacements_metadata.json` en PETSc multi-rangs: deplacements nodaux hors
  JSON monolithique;
- `benchmark_large.json`: recapitulatif machine-readable;
- `benchmark_large.md`: resume lisible;
- `evidence_manifest.json`: empreintes SHA-256 de tous les artefacts.

La telemetrie memoire distingue le pic des allocations Python mesure par
`tracemalloc` du pic RSS processus, qui inclut autant que la plateforme le
permet les tableaux NumPy et les allocations natives PETSc/MPI.

`qualify-large` ecrit en plus:

- `runtime_environment.json` a la racine pour tracer l'orchestration de la
  qualification;
- `large_readiness.json` et `large_readiness.md`: dependances, dimensions,
  estimation disque/memoire et garde-fous backend;
- `qualification_model.h5`: modele genere pour la cible;
- `large_qualification_summary.json`;
- `large_qualification_summary.md`;
- un `evidence_manifest.json` racine couvrant le modele, le resume et les
  artefacts du benchmark.

`verify-large` relit un dossier `qualify-large` sans relancer le calcul et
controle:

- manifests racine et benchmark;
- rapports `runtime_environment.json` racine et benchmark;
- statut du benchmark, de l'audit et du resume qualification;
- DDL reels superieurs ou egaux a la cible;
- forme et taille du fichier `displacements.h5`, `.npz` ou `.bin`;
- absence de deplacements complets dans les JSON;
- empreinte SHA-256 du modele d'entree;
- presence des dependances minimales du backend dans le rapport runtime;
- residu solveur sous le seuil demande.

Pour valider le jalon 1M ddl, conserver le dossier complet et verifier que:

- `LARGE READINESS STATUS: PASS`;
- `BENCHMARK LARGE STATUS: PASS`;
- `QUALIFY LARGE STATUS: PASS`;
- `VERIFY LARGE STATUS: PASS`;
- `EVIDENCE VERIFY STATUS: PASS`;
- le residu final est compatible avec le profil choisi;
- la memoire reste stable sans fichier JSON contenant tous les deplacements.

Le backend SciPy est volontairement bloque au-dessus de 200 000 ddl par defaut
dans le mode large. Pour le jalon 1M ddl, utiliser PETSc/MPI.
Le backend `matrix_free` est accepte au-dessus de ce seuil uniquement pour les
blocs TET4 structures generes; il applique `K.u` element par element sans
construire la matrice globale.

## Preuve locale 1M historique (P4)

La section suivante conserve les mesures P4 pour leur provenance. Elle ne
remplace pas les preuves actives 0.2.7 : les claims courants de grande route
sont bornes par les manifestes et la configuration de chaque campagne.

### PETSc/MPI controle

La campagne du `2026-07-16` a ete executee sur deux rangs MPI avec `CG+GAMG`.

| Cas | DDL | TET4 | Assemblage | Resolution | Iterations | Residu | Pic RSS/rang |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `P4-PETSC-100K-BATCHED-002` | 107 811 | 196 608 | 2,73 s | 3,23 s | 132 | 1,82e-15 | 0,50 GB |
| `P4-PETSC-1M-BAIJ-003` | 1 029 000 | 1 971 054 | 13,15 s | 14,61 s | 52 | 5,34e-19 | 1,13 GB |
| `P4-PETSC-3M-001` | 3 000 000 | 5 821 794 | 34,54 s | 47,75 s | 56 | 9,00e-19 | 3,02 GB |
| `P4-PETSC-1M-PARTITIONED-MPIIO-R4-006` | 1 029 000 | 1 971 054 | 11,30 s | 13,44 s | 53 | 4,53e-19 | 0,758 GB |
| `P4-PETSC-3M-PARTITIONED-MPIIO-R4-006` | 3 000 000 | 5 821 794 | 23,93 s | 38,55 s | 54 | 1,10e-18 | 1,915 GB |

Les audits et manifestes sont `PASS`. La comparaison du petit cas entre un et
deux rangs donne une erreur relative de deplacement de `2,92e-16`. La preuve
compacte et ses empreintes sont figees dans
`qualification/baselines/large_petsc_mpi_2026-07-16.json`.

Cette campagne ne prouve pas encore la scalabilite faible. La lecture
multi-rangs partitionne les elements et compacte les noeuds locaux; les grands
tableaux ne sont plus repliques. Les charges sont filtrees par plage de DDL
possedees, et les blocages sont limites au halo elementaire ou aux lignes PETSc
possedees; l'audit publie les comptes locaux/globaux de conditions aux limites
et les tailles de halo nodal par rang. Le bloc `mpi_communication` estime les
volumes de coordonnees de halo, de blocages, de charges et les faces coupees du
partitionnement graphe. La sortie MPI-IO
collective evite aussi le rassemblement des deplacements sur le rang racine.
L'assemblage batche des
gradients, matrices `B` et rigidites reduit l'assemblage d'un
facteur `10,36` a 100k et `2,88` a 1M, sans aucun ecart de deplacement. Les
insertion BAIJ par blocs nodaux puis conversion AIJ avant GAMG reduit encore
le pipeline 1M a `30,09 s`. Le cas 3M est execute en `88,68 s`.

Chaque resume PETSc ajoute `preconditioner_diagnostics`: type KSP/PC, nombre
de niveaux multigrilles si PETSc l'expose, tailles globale/locale de matrice et
`matrix_info`. Ces champs sont des diagnostics de confiance et de performance;
ils sont completes par un profilage PETSc `-log_view` reproductible.

### Profilage PETSc detaille

La campagne `profile` produit le journal PETSc `ascii_info_detail` sur trois
topologies TET4 de taille voisine: bloc compact, poutre elancee et plaque
mince. Le parseur QF_solver n'execute jamais le contenu du journal. Il extrait:

- temps minimum, moyen et maximum entre rangs, et desequilibre associe;
- nombres de messages, longueurs de messages dans les unites natives PETSc et
  reductions collectives;
- temps `PCSetUp`, `PCApply`, `KSPSolve`, `MatMult`, `VecScatter` et assemblage;
- etapes de construction des niveaux GAMG;
- vingt evenements dominants, avec empreinte SHA-256 du journal source.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action profile -Execute
python .\qf_solver.py petsc-profile-report --inputs .\run1.txt .\run2.txt --labels bloc poutre --output .\results_large\profile_report
```

Le rapport JSON est destine aux comparaisons automatiques. Le Markdown rappelle
que les temps d'evenements peuvent se recouvrir et ne doivent donc pas etre
additionnes comme une decomposition exclusive du temps total.

La campagne `P4-PETSC-PROFILE-TOPOLOGIES-001` a ete executee sur quatre rangs
avec PETSc `3.25.1`, `CG+GAMG`, BAIJ puis AIJ et partition contigue:

| Topologie | DDL | TET4 | Iterations | Pipeline [s] | KSPSolve [s] | PCSetUp [s] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Bloc | 255 552 | 477 042 | 49 | 4,69 | 1,96 | 0,613 |
| Poutre | 253 920 | 461 736 | 161 | 8,61 | 6,24 | 0,546 |
| Plaque | 253 920 | 447 174 | 136 | 7,47 | 5,11 | 0,557 |

Le setup GAMG varie peu entre ces trois cas. L'augmentation du temps total sur
la poutre et la plaque vient principalement du nombre d'iterations et du cout
`KSPSolve`. Cette observation motive la prochaine campagne de reglages GAMG et
Hypre par topologie.

La campagne `P4-PETSC-TUNING-TOPOLOGIES-001` compare quinze calculs independants:
GAMG par defaut, seuils `0.01` et `0.05`, Hypre par defaut et Hypre
`HMIS+ext+i`. Tous les calculs et manifestes passent; l'ecart maximal de
deplacement est `1,96e-11`, sous le seuil `1e-8`.

| Topologie | GAMG defaut [s] | GAMG seuil 0.01 [s] | Gain | Hypre defaut [s] | Hypre HMIS+ext+i [s] |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bloc | 4,875 | 3,999 | 18,0 % | 13,258 | 7,994 |
| Poutre | 8,061 | 7,631 | 5,3 % | 18,625 | 13,586 |
| Plaque | 7,406 | 6,863 | 7,3 % | 15,306 | 12,733 |

Le seuil GAMG `0.01` est le meilleur des presets mesures sur les trois cas,
mais son gain reste inferieur a `10 %` sur la poutre et la plaque. Il est donc
publie comme option de tuning, sans remplacer GAMG par defaut. Hypre
`HMIS+ext+i` ameliore nettement Hypre par defaut, mais reste plus lent et plus
gourmand en memoire que GAMG sur cette machine.

### Reprise PETSc et post-traitement par blocs

Une sortie PETSc MPI-IO terminee peut servir d'estimation initiale a un nouveau
benchmark. QF_solver compare d'abord l'empreinte SHA-256 et la taille du modele
avec `input_fingerprint.json`, puis chaque rang lit uniquement sa plage de DDL:

```powershell
python .\qf_solver.py benchmark-large --input .\model.h5 --output .\restart `
  --solver-backend petsc --restart-from .\previous_benchmark
```

Le post-traitement scalable lit les deplacements binaires par `memmap`, recupere
les noeuds utiles a chaque bloc et ecrit directement dans `element_results.h5`:

```powershell
python .\qf_solver.py postprocess-large --input .\model.h5 `
  --displacements .\benchmark\displacements.bin --output .\post --chunk-size 65536
python .\qf_solver.py postprocess-large --input .\model.h5 `
  --displacements .\benchmark\displacements.bin --output .\post --chunk-size 65536 --resume
```

Les datasets contiennent volume, deformation et contrainte dans l'ordre Voigt
`XX,YY,ZZ,XY,YZ,XZ`, von Mises et energie de deformation par element. Apres
chaque bloc, HDF5 est synchronise sur disque puis un checkpoint JSON est remplace
atomiquement. Une empreinte differente, une taille de bloc differente ou un
fichier incomplet interdit la reprise.

La preuve `P4-POSTPROCESS-CHECKPOINT-001` traite `477 042` TET4. Un arret apres
`131 072` elements reprend les `345 970` restants a environ `536 000 elements/s`.
Le fichier resultat pese `62,9 MB`; l'energie vaut `2,31699889991776e-6`, avec
un ecart relatif de `4,14e-13` face a l'energie du solveur. La reprise PETSc
`P4-PETSC-RESTART-001` converge en zero iteration, avec un ecart de deplacement
strictement nul et un manifeste `PASS`.

La scalabilite forte 1M donne des temps pipeline de `43,66`, `30,09` et
`26,50 s` sur 1, 2 et 4 rangs, soit des accelerations `1,00`, `1,45` et
`1,65`. L'efficacite a quatre rangs est limitee a `41,18 %`; la priorite est
donc le cout des communications, la qualite de partition et le preconditionneur
GAMG. Un partitionnement de graphe PETSc/PT-Scotch avec redistribution reelle
des elements est disponible en mode experimental. Il passe sur `264 600` et
`1 029 000` DDL en quatre rangs, avec un ecart relatif de deplacement
graphe/contigu de `2,24e-13` sur 1M. Sur ce jalon, il reduit legerement le
pipeline solve (`23,93 s` contre `24,56 s`) et le nombre de noeuds compacts par
rang, mais augmente le chargement/preprocessing (`4,40 s` contre `0,53 s`) et
la memoire pic. Le partitionnement contigu reste donc le defaut tant que le
gain total n'est pas demontre sur plusieurs topologies. L'image PETSc figee ne
fournit pas HDF5 parallele; la sortie collective utilise donc MPI-IO natif avec
controle strict de taille.

### Preuve matrix-free historique

Un run complet a ete produit dans:

```text
results_large/qualification_matrix_free_1m_current
```

Synthese du run:

- backend: `matrix_free`;
- DDL cible: `1000000`;
- DDL obtenus: `1029000`;
- elements TET4: `1971054`;
- solve time: environ `473 s`;
- iterations CG: `1000`;
- residu relatif: `9.826054272177696e-09`;
- pic memoire Python trace: environ `202 MB`;
- `verify-large`: `PASS`;
- `verify-evidence` racine: `PASS`;
- `verify-evidence` benchmark: `PASS`;
- sorties principales: `qualification_model.h5`, `benchmark/displacements.h5`,
  `benchmark/audit_large.json`, `benchmark/benchmark_large.json`,
  `benchmark/runtime_environment.json`, `runtime_environment.json`,
  `evidence_manifest.json`.

Test manuel associe:

```powershell
$env:QF_SOLVER_RUN_LARGE_1M = "1"
$env:QF_SOLVER_LARGE_BACKEND = "petsc"
python -m pytest -m large tests\integration\test_large_model.py
```
