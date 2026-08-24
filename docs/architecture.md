---
doc_id: DOC-ARCH-001
revision: 2.1
status: controlled
applicable_version: 0.2.3a0
reviewer: ""
approver: ""
---

# Architecture Du Solveur EF

La formulation mathematique, les reperes locaux et les conventions des
elements sont documentes dans les sections `fondements/` et `elements/` des
sources Markdown et PDF versionnees. L'ancien manuel monolithique est
uniquement une redirection.

## Principes

Le solveur est organise par responsabilite. Les modules de calcul ne doivent
pas connaitre la CLI, les formats disque ou les details d'export. Les entrees
Python publiques passent par `qf_solver` et la commande publique est
`qf-solver`. Le namespace `solveur` contient l'implementation et les facades
de compatibilite 0.2.x ; il n'est pas le contrat des nouvelles integrations.

## Arborescence Publique

```text
QF_solver/
  src/
    qf_solver/            # facade Python publique et stable
    solveur/              # implementation interne
      api/                # fonctions reexportees par qf_solver
      cli/                # adaptation des commandes
      core/               # analyses, assemblage et solveurs
      elements/           # TET4, TET10, HEX8, HEX20, MITC3+, MITC4, BEAM2, discret
      materials/          # lois isotropes, orthotropes, stratifies et J2
      mesh/ loads/ post/  # validation, chargements et post-traitement
      large/              # chemin TET4 PETSc/MPI optionnel
      verification/       # campagnes et oracles reproductibles
  examples/               # entrees JSON executables
  qualification/          # exigences, scopes et decisions controlees
  tests/                  # unitaires, integration, V&V et documentation
  docs/                   # source unique du manuel technique
  scripts/                # construction, V&V et publication
  tools/
    containers/large/     # environnement PETSc/MPI optionnel
    legacy_launchers/     # lanceurs specialises non publics
```

Le layout `src/` empeche qu'un test importe accidentellement le code du
repertoire courant au lieu du paquet installe. Le paquet `qf_solver` est le
produit public generaliste. Toute l'implementation MITC4, y compris le
maillage et le modele de coque, vit dans `solveur.elements.shell.mitc4`.
Les visualisations, campagnes et verifications vivent respectivement dans
`solveur.post` et `solveur.verification`. La facade historique
`solveur.compat.mitc4` et le lanceur `mitc4-solver` ne contiennent plus que des adaptateurs compatibles
durant la serie 0.2.x. Les deux chemins d'import sont proteges par une
baseline matricielle et la campagne MITC4.

## Etat de transition 0.2.3a0

`src/solveur/elements/shell/mitc4` est l'unique implementation canonique de
MITC4. `src/solveur/compat/mitc4` est une facade de compatibilite interne maintenue pour la serie
`0.2.x`; son retrait est planifie pour `0.3.0` apres une periode de migration
documentee et testee. Aucun nouveau calcul ne doit etre implemente dans cette
facade.

Les decisions de maturite de la release precedente ne sont pas portees par cette page : le registre
machine-readable `qualification/element_analysis_matrix.json` est la source de
verite. A la date de preparation de `0.2.3a0`, les formulations HEX8 et HEX20
lineaires reutilisent le meme assembleur sparse, les memes backends et les
memes contrats statique/modal/Newmark/harmonique que les solides existants.
Les preuves externes sont statiques et les sous-perimetres J2, contact,
grandes transformations et multi-million de DDL restent explicitement bornes
ou exclus.

Docker ne fait pas partie du runtime standard. Le Dockerfile conserve dans
`tools/containers/large/` sert seulement a reproduire un environnement
PETSc/MPI epingle pour les campagnes grand modele. `pip install qf-solver`
n'installe ni Docker, ni PETSc, ni les artefacts documentaires.

Le backend numerique commun est porte par `solveur.core.linear_methods`,
`solveur.core.linear_policy` et `solveur.core.solver_backend`. SciPy reste le
chemin standard. PETSc/SLEPc sont optionnels et ne sont importes que si
`backend='petsc'` est demande ou si la politique `auto` est configuree pour les
grands systemes. La reponse harmonique complexe reste explicitement sur SciPy
dans cette alpha.

Les archives PyPI sont volontairement centrees sur le produit : elles ne
dupliquent ni le manuel, ni les Owner reviews, ni les tests. Le depot GitHub
est la distribution publique complete et lisible. Les operations de qualification qui
verifient l'existence physique de ces preuves s'executent depuis un clone du
depot; le paquet installe reste utilisable pour charger, verifier et resoudre
les modeles couverts.

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

## Assemblage et scaling 0.2.2 alpha

Le chantier backend distingue explicitement le kernel elementaire, le motif
de DDL, la fusion sparse, la reduction des contraintes et la resolution. Le
chemin SciPy ne doit pas additionner chaque chunk directement a une matrice
globale : `solveur.core.sparse_accumulator.SparseCsrAccumulator` fusionne les
chunks pairwise et conserve des metriques de chunk/NNZ. Le chemin PETSc utilise
une matrice AIJ ou BAIJ native lorsque le backend optionnel est disponible.

`solveur.core.assembly_plan.AssemblyPlan` pre-calcule maintenant les
specifications d'elements, les coordonnees, les indices DDL globaux et le
nombre d'entrees locales pour un couple `(model, dofs)`. Les chemins statique,
modal, Newmark et harmonique peuvent reutiliser ce plan pour K et M. Le plan
ne cache pas les matrices locales lorsque la geometrie, l'orientation ou
l'etat materiel varie. Les diagnostics indiquent si le plan a ete reutilise et
mesurent sa preparation.

Les chemins modal, Newmark et harmonique utilisent aussi
`GlobalAssembler.assemble_stiffness_and_mass`. Pour chaque chunk, les vecteurs
`rows` et `cols` du motif DDL sont construits une seule fois puis reutilises
pour K et M ; les valeurs locales restent calculees separement et les chunks
temporaires sont liberes apres fusion. Cette implementation evite de conserver
un motif global et potentiellement volumineux : `paired_assembly` et
`shared_chunk_pattern` sont exposes dans les diagnostics. Elle mutualise la
structure de travail sans supposer que K et M ont les memes valeurs.

Une estimation conservatrice de la memoire temporaire est calculee avant la
creation des tableaux COO. Les parametres `assembly_memory_budget_mb` et
`enforce_assembly_memory_budget=true` permettent respectivement d'avertir ou
de refuser une allocation estimee trop grande ; sans ces parametres, le
comportement reste retrocompatible et l'estimation est seulement tracee.

Cette optimisation est acceptee comme changement de performance seulement
apres comparaison numerique de K, M, des reactions, des frequences et des
reponses temporelles. La prochaine tranche porte sur la reutilisation explicite
des operateurs constants et la mesure du gain reel de la paire K/M, sous la
meme contrainte de non-regression. Les campagnes manuelles sont
`scripts/benchmark_sparse_scaling.py` pour la resolution et
`scripts/benchmark_assembly_scaling.py` pour l'assemblage ; elles ne sont pas
des tests CI obligatoires.

## Flux Documentaire

```text
examples + API publique + campagne qualification + benchmarks Gmsh
    -> scripts/docs_models.py
    -> scripts/docs_assets.py + scripts/docs_benchmarks.py
    -> PNG/SVG + tableaux Markdown + resultats JSON
    -> scripts/docs_publication.py
    -> registre valide + manifeste SHA-256 + statut courant
    -> sources Markdown + dossier PDF optionnel
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

- Aucun fichier Python sous `src/solveur`, `src/solveur/compat/mitc4` ou `tests` ne depasse 700 lignes.
- `src/solveur/elements` ne depend pas de `solveur/io`, `solveur/cli` ou
  `solveur/api`.
- `src/solveur/core` ne depend pas de `solveur/cli` ou `solveur/api`.
- Les empreintes SHA-256 et entrees de manifeste sont centralisees dans
  `src/solveur/io/manifest.py`.
- Les formats publics JSON/CLI/API sont proteges par tests de regression.
- Toute page Markdown publiee possede une entete de configuration et une
  entree dans `docs/document_registry.json`.
- Aucune ressource web n'est requise pour la documentation publiee : les
  sources Markdown, PDF et figures locales sont versionnees et controlees.
