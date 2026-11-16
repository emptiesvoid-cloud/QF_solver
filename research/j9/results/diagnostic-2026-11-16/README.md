# J9 — artefacts du diagnostic HEX8-SRI et du transitoire TET10

Statut : **développement exploratoire, non qualification**. Ces résultats ne changent pas les FAIL J7 et ne valident pas le solveur dans son ensemble.

## Contenu

- `hex8_constant_domain/` : résultat HEX8-SRI, état NPZ, figure de calcul originale, figure site et reçu runner assaini.
- `hex8_constant_domain/work_method_postprocess.json` : post-traitement contracté des matrices archivées, comparaison NumPy/SciPy et travail des déplacements imposés. Les erreurs logicielles des tentatives 01 et 02 restent archivées séparément; elles n'ont exécuté aucun nouveau calcul FEM.
- `tet10_newmark_direct/` : historiques Newmark directs, oracle semi-discret, maillages, matrices réduites, courbes et figures.
- `tet10_modal_route_failure/` : diagnostic assaini du refus de validation de la base modale complète. Le statut original reste `PYTEST_FAILED`.
- `site_data.json` : résumé structuré prêt à alimenter une future fiche de galerie, sans publication ni statut de qualification.
- `sha256_manifest.json` : tailles et empreintes de tous les fichiers du dossier, hors manifeste lui-même.

Les reçus et préflights assainis conservent les nodeids, SHA source, contrats, budgets, ressources et empreintes de journaux. Les JSON et logs bruts du runner restent dans le stockage local ignoré car ils contiennent des chemins locaux. Aucun résultat n’a été reconstruit à partir de données absentes.

## Contrats et sources

- HEX8 : [`hex8_constant_domain_distortion_contract.json`](../../../j9_hex8/contracts/hex8_constant_domain_distortion_contract.json), run à `a8f5a91653c50c51cb51e51b297ed9c2cd623362`.
- HEX8 travail/méthodes : [`hex8_work_method_postprocess_attempt_03_contract.json`](../../../j9/hex8_work_method_postprocess_attempt_03_contract.json), post-traitement des données du run `a8f5a91653c50c51cb51e51b297ed9c2cd623362`.
- TET10 Newmark direct + modal (tentative conservée `PYTEST_FAILED`) : [`tet10_newmark_transient_contract.json`](../../../j9_transient/contracts/tet10_newmark_transient_contract.json), run à `a8f5a91653c50c51cb51e51b297ed9c2cd623362`.
- TET10 direct seul : [`tet10_newmark_direct_contract.json`](../../../j9_transient/contracts/tet10_newmark_direct_contract.json), run à `88cd0b1cd51d2eb708afd881c3f8130f59a31f1e`.
- Rapport J9 : [`0.3.0-j9-resultats.md`](../../../../docs/planning/0.3.0-j9-resultats.md).

## Reproduire les figures à partir des données suivies

Depuis la racine du dépôt :

```powershell
python research/j9/prepare_public_artifacts.py --plots-only
```

Cette commande relit seulement les résultats versionnés, régénère les trois figures `site_*.png` et met à jour le manifeste. Elle ne lance pas de calcul FEM.

La reproduction d’un solve FEM exige son nodeid, son contrat et une politique de développement locale enregistrée; les trois nodeids de ce jalon ont déjà consommé leur unique tentative dans le ledger local. Les commandes et préflights exacts sont dans les reçus assainis; le ledger historique n’est pas inclus ni réécrit.

## Limites pour la galerie

- HEX8 : patch affine, géométrie régulière faiblement perturbée, neuf DDL libres; ne permet pas d’attribuer les FAIL J7.
- TET10 : l’oracle valide l’intégration temporelle sur le même système semi-discret. Pas de référence externe pour ce cas, seulement deux maillages axiaux et aucun raffinement transversal.
- Le pulse dure un quart de la période propre propre à chaque maillage; les deux cas n’ont donc pas exactement la même durée de charge physique.
- La tentative modale complète a été refusée par le budget de validation agrégé à 108 DDL; aucun résultat modal tronqué n’est présenté.
- Les états nodaux complets `u(t)` ne sont pas archivés; les courbes du nœud de mesure sont disponibles, mais aucune animation de déformée n’est revendiquée.
