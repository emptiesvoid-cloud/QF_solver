---
doc_id: DOC-ARCH-001
revision: 2.0
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Architecture Du Solveur EF

La formulation mathematique, les reperes locaux et les conventions des
elements sont documentes dans les sections `fondements/` et `elements/` du
site MkDocs. L'ancien manuel monolithique est uniquement une redirection.

## Principes

Le solveur est organise par responsabilite. Les modules de calcul ne doivent
pas connaitre la CLI, les formats disque ou les details d'export. Les entrees
publiques passent par `solveur.api` ou `solveur.cli.main`.

## Couches

```text
CLI -> API -> core / large -> elements / materials / loads / mesh / post
                    |
                    v
                   io
```

- `solveur.api`: facade stable pour scripts Python.
- `solveur.cli`: construction du parser et commandes minces.
- `solveur.core`: modeles memoire, analyses, assemblage, solveurs et DTO de
  resultats. `ReusableSparseFactorization` porte les LU constantes utilisees
  par les analyses multi-resolutions comme Newmark.
- `solveur.elements`: formulations MITC4, TET4 et TET10, sans lecture JSON ni
  export.
- `solveur.materials`: lois materiaux et tangentes.
- `solveur.loads`: entites typees, integration coherente et bilans globaux
  des chargements repartis, sans parsing JSON.
- `solveur.mesh`: validations, qualite et rapports maillage.
- `solveur.benchmarks`: registre et runners des cas mecaniques mailles.
- `solveur.post`: contraintes, resultats derives et audits post-traitement.
- `solveur.io`: JSON, CSV, VTU, Markdown, evidence et manifestes.
- `solveur.large`: chemin separe pour TET4 statique lineaire grand modele.

## Flux Standard

```text
JSON -> JsonModelReader -> MeshValidator -> AnalysisRouter
     -> assembler/solver/post -> Result DTO -> JSON/CSV/VTU/audit/evidence
```

La CLI ne contient pas de logique EF. Elle applique les options utilisateur,
appelle l'API, puis ecrit les artefacts demandes.

Le flux Gmsh est separe du lecteur JSON:

```text
MSH 4.1 + setup JSON -> GmshNativeReader -> GmshModelImporter
                     -> FiniteElementModel + GmshImportReport
                     -> validation obligatoire -> API/CLI standard
```

L'assemblage statique des charges reparties accumule un seul vecteur global et
libere chaque contribution apres son bilan. Les vecteurs individuels ne sont
conserves que pour Newmark lorsque le chargement temporel doit etre module par
index de charge; le chemin courant evite ainsi une memoire
`O(nombre_de_charges * nombre_de_DDL)`.

## Flux Grand Modele

```text
HDF5/NPZ -> LargeModel -> inspect_large_model -> backend SciPy/PETSc/matrix_free
         -> summary.json + audit_large.json + displacements.h5/npz
         -> evidence_manifest.json
```

Le mode grand modele evite les deplacements monolithiques en JSON et utilise
un audit agrege. Les artefacts de preuve incluent une empreinte d'entree et un
rapport `runtime_environment.json`.

## Flux Documentaire

```text
examples + API publique + campagne qualification + benchmarks Gmsh
    -> scripts/docs_models.py
    -> scripts/docs_assets.py + scripts/docs_benchmarks.py
    -> PNG/SVG + tableaux Markdown + resultats JSON
    -> scripts/docs_publication.py
    -> registre valide + manifeste SHA-256 + statut courant
    -> MkDocs Material hors ligne -> site/
```

`scripts/build_docs.py` est l'orchestrateur public. Le profil `engineering`
accepte une revision non commitee en l'affichant comme telle. Le profil
`qualification` refuse une source non commitee, un arbre sale ou une page sans
statut `controlled`/`approved`. Les valeurs numeriques ne sont pas recopiees
dans les pages; elles sont incluses depuis `docs/generated/`.

## Artefacts Generes

Les dossiers `results/`, `results_large/`, caches Python, caches de test,
metadonnees d'installation editable et fichiers HDF5/NPZ lourds sont ignores
par `.gitignore`. Les artefacts existants ne doivent pas etre supprimes par un
refactoring automatique.

## Garde-Fous

- Aucun fichier Python sous `solveur`, `mitc4` ou `tests` ne depasse 700 lignes.
- `solveur/elements` ne depend pas de `solveur/io`, `solveur/cli` ou
  `solveur/api`.
- `solveur/core` ne depend pas de `solveur/cli` ou `solveur/api`.
- Les empreintes SHA-256 et entrees de manifeste sont centralisees dans
  `solveur/io/manifest.py`.
- Les formats publics JSON/CLI/API sont proteges par tests de regression.
- Toute page Markdown publiee possede une entete de configuration et une
  entree dans `docs/document_registry.json`.
- Toutes les ressources web sont locales; MathJax est fige avec sa licence
  dans `docs/assets/vendor/`.
