---
doc_id: DOC-DEMO-005
revision: 0.1
status: genere et controle
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Demonstration grand modele

Le build documentaire genere un bloc TET4 structure de taille moderee. Ce cas
exerce le format disque, le mapping direct des ddl, l'audit agrege et le
backend matrix-free sans exiger PETSc.

![Resume du cas large](../assets/generated/large_model_summary.png){ .result-figure }

--8<-- "docs/generated/large_model_results.md"

## Jalon un million de ddl

Le cas 1M est volontairement separe du site courant. Il doit etre lance dans
un environnement PETSc/MPI controle, puis verifie avec `verify-large` et
`verify-evidence`. Si aucun dossier signe n'est present, la page affiche
`non execute`; elle ne reutilise jamais silencieusement un ancien temps ou un
ancien residu.

## Plan de campagne P4

Le plan controle couvre par defaut `100 000`, `1 000 000` et `3 000 000` ddl.
Il est genere sans allouer les connectivites ni lancer KSP :

```powershell
python .\qf_solver.py large-campaign --output .\results_large\P4-CAMPAIGN-PLAN-001 --targets 100000 1000000 3000000 --solver-backend petsc
```

Un niveau `BLOCKED` signifie que la machine ou les dependances ne permettent
pas le run. Il ne s'agit ni d'un echec mecanique ni d'une mesure numerique. Le
statut ne devient `PASS` qu'avec `--execute` et un pipeline qualifiant vert a
chaque taille.

## Resultats PETSc/MPI

Les niveaux `100k` et `1M` ont ete executes sur deux rangs MPI. Le niveau 1M
atteint `1 029 000` ddl et `1 971 054` TET4 avec un residu final de
`5,22e-15`. Apres vectorisation batchee, l'assemblage passe de `465,63 s` a
`161,45 s`, et le pipeline de `524,41 s` a `213,47 s`, avec des deplacements
strictement identiques. Les insertions PETSc restent a optimiser avant le
niveau 3M. Les valeurs et empreintes sont figees dans
`qualification/baselines/large_petsc_mpi_2026-07-16.json`.

L'iteration BAIJ finale atteint `3 000 000` DDL et `5 821 794` TET4 en
`88,68 s`, avec un residu de `9,00e-19`. Sur le cas 1M, les temps 1/2/4 rangs
sont `43,66/30,09/26,50 s`; l'efficacite a quatre rangs de `41,18 %` borne
clairement la scalabilite actuelle.

L'iteration distribuee suivante supprime la replication globale des noeuds et
connectivites. Elle ecrit les deplacements collectivement, sans rassemblement
racine. Sur quatre rangs, le cas 1M passe en `25,30 s` avec `0,758 GB/rang` et
le cas 3M en `64,00 s` avec `1,915 GB/rang`. Les residus respectifs sont
`4,53e-19` et `1,10e-18`; les deux manifestes sont `PASS`. Le cout memoire
restant est principalement celui de GAMG.

## Preconditionneurs et scalabilite faible

La commande `large-preconditioners` compare GAMG et Hypre/BoomerAMG sur le
meme modele et accumule l'ecart des deplacements par blocs. Sur 1M/4 rangs,
l'ecart vaut `3,40e-12`; GAMG est environ deux fois plus rapide et trois fois
moins gourmand en memoire. La commande `large-scaling-report` classe la
campagne faible `WARNING`: `72,6 %` d'efficacite a deux rangs et `41,6 %` a
quatre rangs pour un travail local constant a moins de `3 %`.

## Profilage multi-topologie

La commande suivante genere trois modeles d'environ 250 000 DDL, execute quatre
rangs PETSc/MPI et publie les journaux bruts, un comparatif JSON, un rapport
Markdown et un manifeste:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action profile -Execute
```

Les geometries sont un bloc `43x43x43`, une poutre `159x22x22` et une plaque
`91x91x9`. Elles ont des nombres de DDL proches afin de mieux isoler l'effet de
la topologie sur GAMG, les communications et le cout KSP.

| Topologie | DDL | Iterations CG | Pipeline [s] | KSPSolve [s] | PCSetUp [s] |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bloc | 255 552 | 49 | 4,69 | 1,96 | 0,613 |
| Poutre | 253 920 | 161 | 8,61 | 6,24 | 0,546 |
| Plaque | 253 920 | 136 | 7,47 | 5,11 | 0,557 |

Verdict: `PASS`. Sur cette machine, la sensibilite a la topologie se manifeste
principalement dans les iterations KSP. Le cout de construction GAMG reste
voisin pour les trois geometries.

## Tuning GAMG et Hypre

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_large_scaling.ps1 -Action tuning -Execute
```

Les quinze calculs sont executes dans des processus MPI separes. Le meilleur
preset mesure est GAMG avec `pc_gamg_threshold=0.01`, mais son gain n'est pas
uniformement superieur a `10 %`. Le rapport conclut donc a l'absence de
changement robuste du defaut. Hypre `HMIS+ext+i` reduit fortement le cout du
BoomerAMG par defaut, sans rejoindre GAMG sur ces cas.

## Reprise et contraintes par blocs

Le cas bloc de `477 042` TET4 est interrompu volontairement apres deux blocs de
`65 536` elements, puis repris. Le resultat final est `PASS`; l'energie du
post-traitement et celle du solveur s'accordent a `4,14e-13` relatif. Le meme
champ de deplacement recharge dans PETSc conduit a zero iteration et a un
ecart final nul. Ces deux essais prouvent separement la reprise KSP depuis une
solution terminee et la reprise du post-traitement elementaire.
