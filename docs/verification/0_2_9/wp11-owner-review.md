---
doc_id: DOC-029-WP11-OWNER-REVIEW
revision: 1.0
status: ready-for-owner-review
---

# WP11 — revue Owner PETSc/MPI

## Verdict

```text
WP11_OWNER_REVIEW_STATUS = READY_FOR_OWNER_REVIEW
WP11_CANDIDATE_POINTS = PENDING_OWNER
WP11_OFFICIAL_POINTS = 0/6
```

La campagne est réussie sur un cas TET4 statique borné de 24 DDL. Elle ne
constitue pas encore une preuve de scalabilité forte ou faible.

## Provenance

```text
BRANCH = codex/wp11-qualification
BASE_SHA = 04d1f1a60dcb4435c925cf5f788302da698aaf0e
RUNNER_SHA = b3bec329b4ae6a4c3f3f3e8ef9d221fd12fea13c
EXECUTION_SHA = f9bb50f8f1fe8d6920a81ebe61f1730214a469e0
EVIDENCE_COMMIT_SHA = 6ec88ca384120ae1ec495344809e03ba66c24b7b
CONTRACT_SHA256 = 37876e3da02b1ca9a97ee535d8e2026131cc61900f3d478a578d9398ff0eb0d6
DOCKER_IMAGE = ghcr.io/fenics/dolfinx/dolfinx@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8
MPI_RANKS = 2
PETSC = 3.25.1
```

Le contrat est aligné sur le runner MPI. Le modèle est généré une seule fois
par le rang 0, puis lu par les autres rangs après une barrière MPI. Les sorties
agrégées sont écrites par le rang 0.

## Résultats

| Gate | Résultat | Preuve |
|---|---|---|
| M1 référence sérielle | PASS_CANDIDATE | SciPy, 24 DDL, audit et manifest PASS |
| M2 PETSc/MPI | PASS_CANDIDATE | 2 rangs, 24 DDL, résidu `1.97e-26`, audit PASS |
| M3 replay frais | PASS_REPLAY | différence déplacement M2/M3 `0.0` |

Comparaison M1/M2 : différence absolue maximale `3.31e-24`, soit
`6.42e-16` relative.

## Validation

```text
TARGETED_TESTS = 49 passed, 1 skipped
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
JSON_VALIDATION = PASS
GIT_DIFF_CHECK = PASS
FULL_TEST_SUITE = NOT_RUN
```

## Limites

- cas de démonstration limité à 24 DDL ;
- TET4 statique uniquement ;
- tableaux d’entrée répliqués sur les rangs ;
- pas d’entrée HDF5 partitionnée ;
- aucune revendication de strong scaling ou weak scaling ;
- aucune qualification dynamique, contact ou frictionnelle ;
- aucune corrélation avec Code_Aster ou un solveur FEM externe.

## Historique de correction

Le premier essai multi-rang échouait avant calcul parce que chaque rang créait
le même HDF5. Le runner R1 corrige cette orchestration : génération sur le rang
0, barrière, lecture commune, puis résolution distribuée. Cet incident est
conservé dans les artefacts non retenus ; il n’est pas reclassé en échec
numérique.

## Décision Owner demandée

```text
OWNER_ACCEPTS_WP11_M1 = PENDING
OWNER_ACCEPTS_WP11_M2 = PENDING
OWNER_ACCEPTS_WP11_M3 = PENDING
OWNER_AWARDS_WP11_POINTS = PENDING
```

Les points restent à `0/6` jusqu’à décision explicite Owner. Aucun merge ni
push n’a été effectué.
