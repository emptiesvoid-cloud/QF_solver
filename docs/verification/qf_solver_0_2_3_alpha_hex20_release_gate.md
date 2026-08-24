---
doc_id: DOC-HEX20-023-002
revision: 0.1
status: draft
applicable_version: 0.2.3a0
reviewer: ""
approver: ""
---

# Gate de release 0.2.3 alpha - chaine HEX20

## Regle non negociable

`OPEN`, `WARNING`, `BLOCKED`, `FAIL`, `N/A` ou une preuve non rejouable
maintiennent le gate ouvert. Les resultats `PASS_INTERNAL` ne remplacent pas
une correlation externe ni une revue Owner.

## Tableau de gate

| Gate | Preuve | Etat courant | Condition de fermeture |
| --- | --- | --- | --- |
| H20-G01 | Formulation, interpolation, Jacobien et Gauss | PASS_INTERNAL | Tests unitaires et geometries invalides rejoues. |
| H20-G02 | K/M coherentes, masse lumped et modes rigides | PASS_INTERNAL | Symetrie, masse, energie et rigid body `PASS`. |
| H20-G03 | Body force, gravite, traction et pression QUAD8 | PASS_INTERNAL | Resultantes, normales et moments verifies. |
| H20-G04 | Post-traitement Gauss et nodal | PASS_INTERNAL | 27 points, 20 noeuds et champs finis. |
| H20-G05 | Statique, modal, Newmark, harmonique | PASS_INTERNAL | Quatre chemins communs `PASS`. |
| H20-G06 | J2 Newton-Raphson | PASS_INTERNAL | Etats commites et convergence aux quatre increments. |
| H20-G07 | Import Gmsh type 17 / face type 16 | PASS_INTERNAL | Connectivite, BC, pression et resolution `PASS`. |
| H20-G08 | Sparse/HPC commun | PASS_INTERNAL | Aucun backend ou assembleur special HEX20. |
| H20-G09 | Comparaison 3 modeles x 4 familles | PASS_INTERNAL | 12 lignes avec metriques et residus archives. |
| H20-G10 | CalculiX C3D20 | PASS_EXTERNAL_CORRELATION | Meme maillage; ecart global `8.50e-7`, noeud charge `7.04e-7`, seuil `1 %`. |
| H20-G11 | Code_Aster HEXA20 | PASS_EXTERNAL_CORRELATION | Meme maillage; ecart noeud charge `5.42e-15`, seuil `1 %`. |
| H20-G12 | Non-regression, documentation, Owner | OPEN | Tests et audits `PASS`; signature et decision Owner encore a enregistrer. |

## Limites obligatoires

- La campagne interne est de petite taille et ne revendique pas le scaling
  multi-million de DDL.
- La comparaison TET4/TET10/HEX8/HEX20 mesure un compromis sur trois cas et
  ne designe pas un element universellement meilleur.
- La plasticite J2 est validee sur le cas local documente; rupture, dommage,
  grandes deformations et contact restent exclus.
- La masse lumped est une option distincte et ne remplace pas silencieusement
  la masse coherente.
- Les correlations externes sont statiques sur un cas de reference; modal,
  dynamique et J2 externes restent des extensions de campagne.

## Paquet minimal avant revue Owner

```text
results/hex20_internal/summary.json
results/hex20_internal/report.md
results/hex20_tet_multi_model/summary.json
results/hex20_tet_multi_model/report.md
results/hex20_tet_multi_model/tet_hex8_hex20_multi_model_comparison.png
results/hex20_external_calculix/summary.json
results/hex20_external_calculix/calculix.log
results/hex20_external_code_aster/summary.json
results/hex20_external_code_aster/code_aster.log
```

La fiche Owner contient les reponses techniques et a ete signee le 2026-08-24
avec la decision `accepted_with_recommendations`. Les gates CI restent a
observer apres push ; l'upload PyPI reste volontairement desactive.
