---
doc_id: DOC-CFG-001
revision: 1.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Gestion de configuration

## Baseline

- Le depot Git local est la source de verite du code et de la documentation.
- Une release associe un tag, un index de configuration et un changelog.
- Les dependances sont verrouillees par baseline d'execution.
- Aucun artefact de resultat lourd n'est versionne dans le depot source.

## Modification

Toute modification qualifiable doit avoir:

- une exigence ou une anomalie source;
- une analyse d'impact mecanique, numerique, API et format;
- des tests associes;
- une revue independante;
- une mise a jour de la tracabilite et des limites connues.

## Environnements

Le manifeste de preuve enregistre Python, OS, architecture, NumPy, SciPy,
BLAS/LAPACK, PETSc/MPI si presents, variables de parallelisme et revision Git.

## Regles Git

- Aucun commit automatique par un outil sans demande explicite.
- Les fichiers generes restent ignores.
- Une baseline candidate doit avoir un arbre propre et un tag signe selon la
  politique de l'organisation.
