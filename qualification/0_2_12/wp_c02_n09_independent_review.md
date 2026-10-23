# WP-C02-N09 — Revue indépendante

## Avis

**Favorable au commit et à la préparation d’un nouveau gel N09.** Aucun finding P0 ou P1 ouvert dans le correctif examiné. Cet avis n’autorise aucun RUN N10.

## Portée et indépendance

La revue a été effectuée en lecture seule sur le candidat N09, les définitions de production, les tests analytiques, le script de calcul hors ligne et les deux rapports N09. Le reviewer n’a exécuté aucun test, solveur, assemblage, calcul FEM ou Docker, et n’a modifié aucun fichier. Les contrôles de tests indiqués ci-dessous sont ceux de l’exécutant.

## Résultats examinés

- La chaîne de production donne `internal_force=Ku+Cᵀμ=Ku−P`, `p=−μ`. Stationnarité correcte sur les DDL libres : `||(internal_force−f)[free]||∞`.
- L’énergie élastique est `½uᵀ(internal_force+P)`, avec comparaison à l’intégration quadraturée de la même énergie. L’oracle QP reste séparé.
- Les tests couvrent l’oracle SPD indépendant, les erreurs de signe/double comptage, l’absence de contact, les données invalides et une énergie de barre intégrée par quadrature de Gauss indépendante.
- Les vecteurs bruts total `internal_force` et `residual` sont conservés dès `SOLVER_COMPLETED_RAW_FIELDS` dans les futurs records, avant les diagnostics qui peuvent échouer.
- Le rapport distingue le produit force de contact finale–déplacement du travail physique intégré sur un trajet; le travail extérieur est formulé comme intégrale de trajet avec ses hypothèses.
- Aucun solveur, modèle, seuil AR ou équation n’est modifié.
- Archive N08 : hashes et tailles vérifiés indépendamment, 539/539 conformes. Le recalcul hors ligne M4/M5 correspond aux valeurs du rapport N09.

## Recalcul hors ligne confirmé

| Niveau | Énergie élastique corrigée hors ligne (J) | Écart avec quadrature (J) |
|---|---:|---:|
| M4 | 1,4857871127899884 | 4,352074256530614×10⁻¹⁴ |
| M5 | 1,4859449717515985 | 6,94999613415348×10⁻¹⁴ |

La stationnarité N08 est `NOT_EVALUATED` hors ligne : les vecteurs de force/résidu de production manquent de l’archive. Ces corrections restent `OFFLINE_DIAGNOSTIC_ONLY`.

## Findings et limites

- **P0 :** aucun.
- **P1 :** aucun ouvert sur les formules, le correctif ou les tests examinés.
- **P2 :** les traces historiques de front M2/M3 restent insuffisantes (`NOT_ACQUIRED`). Il faut une acquisition autorisée pour vérifier le collecteur corrigé sur les résultats FEM et obtenir les vecteurs bruts M4/M5.
- Les 49 PASS unitaires, le `py_compile`, `git diff --check`, les 3 tests collectés et les deux scénarios SKIP sans GO ont été rapportés et exécutés par l’auteur; le reviewer ne les a pas relancés.

Verdicts maintenus : `N06_M4=FAIL`, `N06_M5=FAIL`, `N08_M4=FAIL`, `N08_M5=FAIL`, `WP_C02_SPATIAL_CONVERGENCE=NOT_ACQUIRED`. Pas de qualification générale, d’équivalence Docker, de clôture C02 ou de promotion.

## Empreintes du contenu relu

| Élément | SHA-256 |
|---|---|
| `scripts/wpc02_ar_native_collection.py` | `a9d982a1a0e18aa473305d98e572394e8a411b7194734b99ef828221fc09ff35` |
| `tests/verification/test_wpc02_ar_native_contact_convergence.py` | `141bec2d8c2e25b9087d1ade41c75bf57e0be2f0a6fc1ee417c22c47d8d39a27` |
| `tests/unit/test_wpc02_ar_native_collection_reporting.py` | `76a90035f2e89127d58d6daceb49adb9dcf170746c13e1ff212884ab9bdbe1c4` |
| `scripts/diagnose_wpc02_n08_force_energy_offline.py` | `f888dbf8a4f9b3bc49d6b8c4dc9baaf69f4c0820a7ab6fc44e806749c4f90fa5` |
| `qualification/0_2_12/wpc02_n09_offline_diagnostic.json` | `4371ca883ba84b7c19ca144b76c1d536208f6928733125ed1545a726e2d2bd9a` |
| `qualification/0_2_12/wp_c02_n09_force_stationarity_energy_audit.md` | `f50c5f389c4d1bab4b3336e560457955a2acd3252065e9f285b9f592cc025696` |
| `qualification/0_2_12/wp_c02_n09_offline_diagnostic.md` | `1c4b4cbfdd6d76fb0f0bd6cd21a525415805454418c0e4bb695b1c488073df5f` |
