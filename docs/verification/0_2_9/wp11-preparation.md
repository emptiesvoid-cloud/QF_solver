---
doc_id: DOC-029-WP11-PREPARATION
revision: 1.0
status: preparation-only
---

# WP11 — plan de qualification PETSc/MPI

## Objectif

Qualifier le chemin grands modèles TET4 avec assemblage PETSc, partitionnement
MPI, sorties rank-owned et replay reproductible. WP11 ne revendique pas encore
la scalabilité forte/faible : ces deux propriétés nécessitent des campagnes
distinctes sur plusieurs tailles et plusieurs nombres de rangs.

## Gates gelés

| Gate | Contenu | Preuve attendue |
|---|---|---|
| M1 | Référence sérielle file-backed | résultat, audit, hash et observables |
| M2 | Exécution PETSc/MPI distribuée, au moins 2 rangs | manifeste par rang, équilibre global, sortie agrégée |
| M3 | Nouveau processus et replay des checkpoints | égalité des statuts, hashes et observables |

## Périmètre borné

- TET4 structuré, statique, sans contact ni dynamique ;
- backend PETSc dans une image Docker épinglée ;
- préconditionneur GAMG et paramètres du contrat existant ;
- aucune modification de mécanique de production ;
- aucune revendication Code_Aster, forte scaling ou weak scaling.

## Préflight constaté

```text
HOST_MPI4PY = AVAILABLE
HOST_PETSC4PY = UNAVAILABLE
DOCKER = AVAILABLE
MPIEXEC = AVAILABLE
PINNED_RUNTIME = AVAILABLE
CONTAINER_PETSC = 3.25.1
CONTAINER_MPI_RANKS_PROBE = 1
```

Le runtime conteneurisé est disponible. La campagne multi-rang doit encore
prouver l’orchestration MPI et les artefacts par rang avant toute décision.

## Fail-closed

Toute absence de provenance, de sortie d’un rang, d’agrégation globale ou de
replay bloque WP11. Un résultat sériel ne peut pas être présenté comme une
qualification MPI.

## Décision Owner demandée après exécution

```text
OWNER_ACCEPTS_WP11_M1 = PENDING
OWNER_ACCEPTS_WP11_M2 = PENDING
OWNER_ACCEPTS_WP11_M3 = PENDING
OWNER_AWARDS_WP11_POINTS = PENDING
```
