---
doc_id: DOC-REF-API-002
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Stabilite de l'API Python

## Contrat public

Les imports pris en charge sont ceux de `solveur.api`. Ils couvrent le cycle
standard `load_model -> check_mesh -> solve_model -> save_result`, les exports
de preuve et les fonctions de benchmark publiees. Les modules `solveur.core`,
`solveur.elements`, `solveur.io` et `solveur.large` restent internes, meme si
leur code est lisible.

La version installee est disponible sans importer le noyau interne :

```python
import solveur

print(solveur.__version__)
```

Les entrees JSON v1 restent compatibles tant que `schema_version` est absent
ou vaut `1`. Les codes de sortie CLI documentes sont egalement publics. Un
changement de resultat numerique doit etre explique dans le changelog et
protege par une mise a jour de preuve ou de snapshot.

## Politique de version

- Correctif: correction sans changement volontaire de contrat public.
- Mineure: ajout retrocompatible d'une fonctionnalite, d'un champ optionnel ou
  d'une commande.
- Majeure: retrait d'API, rupture JSON/CLI ou changement numerique intentionnel
  d'une baseline publiee.

Les alias `solveur-ef` et `main_solveur.py` sont deprecies et prevus pour
retrait a partir de `0.3.0`. Les nouvelles integrations doivent utiliser
`qf-solver` ou `python -m solveur.cli.main`.

## Maturite

La stabilite d'interface ne vaut pas validation mecanique universelle. Chaque
analyse conserve son statut de maturite et ses limites dans le tableau de bord
et les rapports V&V.
