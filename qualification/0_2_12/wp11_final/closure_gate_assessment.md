# WP11 v0.2.12 — Évaluation du gate de clôture

## Verdict

**Verdict : `CLOSE` — WP11 opérationnel d’intégration API, résultats et sérialisation.**
Les critères acceptés par l’Owner sont satisfaits selon la
[`matrice d’acceptation`](wp11_acceptance_matrix.tsv) et les résultats de tests
du [`manifeste de suivi`](owner_decision_followup_manifest.json). Le statut
officiel a été maintenu `WP11=OPEN` pendant les contrôles, puis clôturé pour ce
seul gate opérationnel v0.2.12 après leur réussite.

## Motifs et références exactes

- L’inventaire public (77 exports : 30 `STABLE`, 47 `PROVISIONAL`), la
  classification, les signatures et les références 0.2.12 sont couverts par
  les tests `tests/unit/test_public_api_contract.py::test_public_facade_matches_documented_export_inventory`,
  `tests/unit/test_public_api_contract.py::test_documented_stability_classification_covers_every_export`,
  `tests/unit/test_public_api_contract.py::test_critical_workflow_signatures_are_stable` et
  `tests/unit/test_public_api_contract.py::test_reference_pages_match_the_0_2_12_api_candidate`.
- Les contrats versionnés et refus ciblés sont étayés par les tests référencés
  dans `regression_manifest.json` et la matrice : round-trips Modal-Newmark,
  réduit et D01; intégrité HDF5; métadonnées harmoniques alignées; refus JSON.
- Le changement de comportement historique de `save_result` est vérifié et
  déclaré. Les cibles nouvelles conservent le chemin à deux arguments; le
  remplacement existant requiert `overwrite=True` ou `--overwrite`. Les tests
  `tests/unit/test_public_api_contract.py::test_public_save_result_refuses_to_overwrite_an_existing_path`,
  `tests/unit/test_public_api_contract.py::test_public_save_result_can_explicitly_overwrite_an_existing_path`,
  `tests/unit/test_save_result_cli_overwrite.py::test_solve_cli_overwrite_is_opt_in`,
  `tests/unit/test_save_result_cli_overwrite.py::test_solve_cli_forwards_explicit_overwrite_without_solving` et
  `tests/unit/test_save_result_cli_overwrite.py::test_all_json_result_cli_commands_expose_overwrite`
  vérifient le refus par défaut, l’écrasement explicite et le passage du flag
  CLI sans solveur.
- Les pages API gardent `status: controlled_candidate` et contiennent le nom du
  reviewer, la décision Owner datée et la limite « pas une approbation de
  release ». La roadmap conserve les états scientifiques séparés.

Les nodeids, commandes, environnement, résultat Ruff et contrôles locaux sont
consignés dans `owner_decision_followup_manifest.json`, avec le SHA exact du
commit source testé. Le manifeste historique
[`regression_manifest.json`](regression_manifest.json) est conservé intact.

## Réserves documentaires et limites de preuve

- Les intégrations qui appelaient `save_result(result, path)` pour remplacer
  implicitement un fichier doivent ajouter `overwrite=True`. Le test
  d’intégration FEM existant a été migré vers `--overwrite`, mais son exécution
  n’a pas été autorisée dans cette mission.
- Aucun solveur ni assemblage FEM n’a été exécuté. Les tests de suivi sont
  synthétiques ou vérifient les contrats CLI/API sans lancer de calcul. Cela
  laisse hors preuve les campagnes V&V numériques, les performances et les
  résultats de calcul de bout en bout; ces sujets relèvent de WP12 ou d’un
  manifeste et d’une autorisation dédiés.
- Les DTO ordinaires n’ont toujours pas de schéma universel ni de
  `load_result()` générique, conformément à la décision Owner. Les règles de
  refus, versions, capacités et limites propres aux contrats sont maintenues.

## Frontières administratives et scientifiques

La clôture concerne uniquement le gate API/intégration WP11 v0.2.12. D01 reste
`INCONCLUSIVE`; C02 reste `CLOSED_BOUNDED` uniquement sur AR/N03; E01 reste
`OPEN_WITH_BOUNDED_CERTIFICATES`. Aucune qualification ou promotion
scientifique n’en découle. WP12 et WP13 ne sont pas lancés. Aucun merge vers
`main`, tag, package ou site n’est réalisé dans cette mission.
