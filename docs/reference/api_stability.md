---
doc_id: DOC-REF-API-002
revision: 0.3
status: draft
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# Stabilite de l'API Python

## Contrat public

Les nouvelles integrations doivent importer exclusivement depuis `qf_solver` :

```python
from qf_solver import check_mesh, load_model, save_result, solve_model
```

Le cycle standard est `load_model -> check_mesh -> solve_model -> save_result`.
La version est disponible sans importer le noyau interne :

```python
from qf_solver import __version__

print(__version__)
```

Le package `solveur` est l'espace d'implementation interne et une facade de
compatibilite de la serie 0.2.x. Les alias `solveur-ef` et `main_solveur.py`
sont deprecies pour les nouvelles integrations ; la commande recommandee est
`qf-solver`.

## Compatibilite

Les entrees JSON v1 restent compatibles lorsque `schema_version` est absent ou
vaut `1`. Les codes de sortie CLI et les commandes documentees font partie du
contrat public. Un changement numerique volontaire doit etre explique dans le
changelog et rattache a une nouvelle preuve.

La stabilite d'interface ne vaut pas qualification mecanique universelle. Les
limites et la maturite de chaque analyse restent celles du tableau de bord et
des rapports V&V.
