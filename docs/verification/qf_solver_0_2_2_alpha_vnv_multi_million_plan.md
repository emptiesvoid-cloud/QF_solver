---
doc_id: DOC-BACKEND-022-003
revision: 0.1
status: draft
applicable_version: 0.2.2a0
reviewer: ""
approver: ""
---

# Plan V&V multi-million DDL : QF Solver 0.2.2 alpha

## Statut

Ce dossier definit la campagne de scalabilite au-dela de deux millions de
degres de liberte. Il conserve le plan de readiness et une tentative initiale
controlee qui a ete bloquee sur l'hote faute de `petsc4py`. Une seconde tranche
a depuis ete executee dans l'image Docker PETSc epinglee et est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/`.
Aucune promotion de maturite generale n'est deduite : seule la preuve statique
TET4, contiguë, sur une machine, est PASS bornée.

## Matrice de campagne

Le meme modele TET4 structure, le meme materiau isotrope, les memes conditions
aux limites et le meme chargement doivent etre rejoues dans les quatre cases :

| Cible | Rangs MPI | Backend | Preconditionneur | Format matrice | Partitionnement |
| ---: | ---: | --- | --- | --- | --- |
| 2 000 000 DDL | 2 | PETSc | GAMG | BAIJ | contigu ou graphe trace |
| 2 000 000 DDL | 4 | PETSc | GAMG | BAIJ | contigu ou graphe trace |
| 4 000 000 DDL | 2 | PETSc | GAMG | BAIJ | contigu ou graphe trace |
| 4 000 000 DDL | 4 | PETSc | GAMG | BAIJ | contigu ou graphe trace |

La campagne doit conserver une variante `matrix_free` pour le controle de
memoire, mais cette variante ne remplace pas la preuve PETSc/MPI multi-rang.
SciPy est explicitement exclu de ce palier par le gate
`MULTI-MILLION-GATE`.

## Readiness avant calcul

Chaque case commence par un rapport `large-readiness`. Le rapport doit montrer :

- un backend `petsc` ou `matrix_free` ;
- un budget memoire explicite, enregistre dans les metadonnees runtime ;
- une estimation `petsc_rule_of_thumb_bytes` inferieure a ce budget ;
- un espace disque suffisant pour le modele, les sorties file-backed et les
  manifests ;
- une taille de chunk positive et compatible avec le budget ;
- les versions Python, PETSc, MPI, petsc4py, mpi4py et le materiel traces.

Exemple de planification sans execution :

```powershell
python qf_solver.py large-campaign `
  --output qualification/benchmarks/qf_solver_0_2_2_multi_million_plan `
  --targets 2000000 4000000 `
  --solver-backend petsc `
  --preconditioner gamg `
  --memory-budget-mb 32768
```

Cette commande ne doit pas recevoir `--execute` pendant la preparation. Les
executions MPI seront lancees separement, dans des environnements epingles,
par exemple avec `mpiexec -n 2` puis `mpiexec -n 4`, et dans des repertoires de
sortie distincts.

## Observables obligatoires

Chaque execution doit produire, par rang et au niveau global :

1. nombre de noeuds, elements, DDL et NNZ ;
2. temps de chargement, assemblage, resolution et pipeline total ;
3. iterations KSP, residu initial, residu final, residu relatif et raison de
   convergence ;
4. pic RSS par rang, somme RSS, memoire Python et estimation sparse ;
5. repartition des elements, lignes et charges, avec les communications
   estimees ;
6. deplacements file-backed, reactions, energie et audit d'equilibre ;
7. empreinte du modele, environnement runtime et manifest de preuve.

Les tableaux de scaling doivent comparer les deux rangs sur la meme taille
(strong scaling) et les deux tailles a travail par rang documente (weak
scaling). Une seule station ne permet pas d'extrapoler a un cluster different.

## Criteres de sortie proposes

Une case est `PASS` uniquement si tous les points suivants sont satisfaits :

- DDL reels au moins egaux a la cible ;
- audit de maillage et de chargement `PASS` ;
- residu relatif final au plus `1e-8`, ou seuil justifie dans le rapport ;
- ecart de deplacement et de reactions entre les configurations equivalentes
  au plus `1e-8` relatif, hors tolerance numerique documentee ;
- aucun deplacement non fini et aucune sortie monolithique JSON ;
- budget memoire respecte par le pic observe ;
- manifest et empreinte d'entree verifies ;
- temps, iterations et repartition disponibles pour les quatre cases.

Une efficacite faible ne transforme pas un calcul correct en echec numerique,
mais elle reste un `WARNING` de scalabilite et interdit une revendication
generale de performance. Le seuil provisoire de weak scaling est conserve a
`60 %` jusqu'a une decision technique fondee sur au moins deux configurations
materielles.

## Comparaison numerique

Avant toute comparaison de temps, les cases doivent comparer les memes
grandeurs mecaniques :

- norme relative des deplacements nodaux ;
- reactions sur les DDL bloques et resultant global ;
- energie de deformation ;
- residu d'equilibre ;
- maximum de contrainte ou champ equivalent lorsque le post-traitement est
  disponible.

Une difference de performance ne sera retenue que si ces observables sont
identiques dans les tolerances. Les sorties MPI-IO et les sorties rassemblees
ne doivent pas etre comparees comme des fichiers bruts.

## Limites et decision

Cette campagne reste manuelle, couteuse et dependante de PETSc/MPI. Le gate
de readiness protege contre une allocation prematuree, mais ne prouve ni la
scalabilite forte, ni la scalabilite faible, ni la portabilite sur une autre
machine. Le statut du dossier reste `draft` jusqu'a obtention des quatre
rapports d'execution et d'une revue technique.

## Tentative locale controlee

L'execution est archivee dans
`qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_execute_blocked/`.
Le resultat est `BLOCKED` au controle `DEP-PETSC4PY`, avec `mpi4py` et `h5py`
disponibles, un budget de `32 GiB` accepte et une estimation PETSc de
`4,13 GiB` pour la cible 2M. Le second cas 4M est `NOT_RUN` conformement a la
politique `stop_on_failure`. Cette sortie demontre le comportement du gate,
pas la capacite de resolution PETSc.

La decision de release et toute promotion de maturite restent reservees a
l'Owner.

## Execution Docker realisee le 2026-08-23

L'image executee est `qf-solver-large:0.2.0@sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8`, construite
depuis l'image de base epinglee `sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`.
Le backend est PETSc, avec `CG`, `GAMG`, `BAIJ`, sorties deplacements
file-backed et partitionnement contigu.

| Cas | DDL reels | Rangs | Assemblage (s) | Resolution (s) | Pipeline (s) | Iterations | Residu | RSS cumule |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2m_r2` | 2 044 416 | 2 | 19,921 | 27,161 | 48,238 | 54 | `8,801e-19` | 4,70 GiB |
| `2m_r4` | 2 044 416 | 4 | 12,585 | 23,530 | 37,029 | 55 | `5,477e-19` | 5,10 GiB |
| `4m_r2` | 4 102 893 | 2 | 61,328 | 57,781 | 121,394 | 57 | `7,552e-19` | 9,14 GiB |
| `4m_r4` | 4 102 893 | 4 | 47,227 | 49,624 | 98,690 | 57 | `1,041e-18` | 9,59 GiB |

Le scaling fort 2 vers 4 rangs donne une efficacité de `0,651` à 2M et
`0,615` à 4M, pour un seuil provisoire de `0,60`. Les quatre manifestes et
les audits grand modèle sont vérifiés `PASS`. Le rapport consolidé est
`campaign.md`/`campaign.json` dans le dossier d'archive.

La campagne backend complémentaire est maintenant agrégée dans
`qualification/benchmarks/qf_solver_0_2_2_backend_campaign/`. Elle ajoute :

| Variante | Résultat borné |
| --- | --- |
| PETSc/PT-Scotch graphe, 2M DDL, 2/4 rangs | `PASS`, efficacité forte `0,621` |
| matrix-free, 107 811 DDL | `PASS`, résidu relatif `1,104e-12` |
| modal SLEPc, 107 811 DDL | `PASS`, trois modes, résidu maximal `2,789e-12` |
| Newmark PETSc/GAMG, 2 044 416 DDL | `PASS`, 10 pas, résidu relatif maximal `1,968e-6` |

La comparaison SciPy/matrix-free/PETSc sur `1 029` DDL termine avec trois
backends et des écarts relatifs inférieurs à `1,5e-13`. La tentative modale
SLEPc à `2 044 416` DDL a été arrêtée par le conteneur pendant la
factorisation shift-invert (signal `9`, environ `33,5 GiB`) et reste classée
`BLOCKED_RESOURCE_LIMIT`. La tranche ferme donc un périmètre backend borné,
mais ne revendique pas le modal multi-million, une seconde machine ou une
promotion de maturité.
