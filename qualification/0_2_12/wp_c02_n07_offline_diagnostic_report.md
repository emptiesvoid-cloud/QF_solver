# WP-C02-N07 — Diagnostics N06 recalculés hors ligne

## Statut

**`OFFLINE_DIAGNOSTIC_ONLY`.** Ce document décrit une correction de post-traitement des champs déjà archivés par N06. Il n’exécute aucun solveur ni assemblage, ne modifie pas les diagnostics/archive N06 et ne requalifie aucun résultat. `N06_M4=FAIL`, `N06_M5=FAIL`, `WP_C02_SPATIAL_CONVERGENCE=NOT_ACQUIRED` restent inchangés.

Archive source N06 : `wpc02_ar_native_campaign_n05_20261023_01`, manifeste externe SHA-256 `d929ddeaeac4ad716b8b843de51f35c3faafa5e228467603ace94bbe8098810e`.

Le solveur de production convertit le multiplicateur selle brut en pression de compression `p=−μ_raw` et exporte déjà cette valeur dans `row["pressure"]`. Le collecteur N06 l’avait encore niée (`multipliers=-row["pressure"]`). Le recalcul ci-dessous annule uniquement cette négation supplémentaire : `p_corrigé=-multipliers_N06`. Pour le plan AR de normale `+Z`, la force sur l’esclave est `p_corrigé ez`; la pression surfacique est `p_corrigé/A_tributaire`.

## Résultats recalculés

| Mesure | M4 | M5 |
|---|---:|---:|
| Contacts actifs / ouverts | 30 / 15 | 42 / 24 |
| Multiplicateur physique min…max N | 0…17,8572 | 0…12,9099 |
| Pression surfacique min…max Pa | 0…874,881 | 0…900,018 |
| Erreur L2 pression AJ | 0,106096527 | 0,077907374 |
| Ratio d’erreur pression M5/M1 (M1 AQ) | — | 0,167943275 (`<0,9`, endpoint PASS hors ligne) |
| Ratio d’erreur déplacement M5/M1 (M1 AQ) | — | 0,137547461 (`<0,9`, endpoint PASS; déplacements N06 inchangés) |
| Erreur énergétique M5 < M1 AQ | — | 0,017972658 < 0,0646443 (PASS sur endpoint) |
| Résultante contact z N; exact AJ | 166,742898; 166,666667 | 166,668452; 166,666667 |
| Erreur de résultante relative | 4,5739e−4 | 1,0718e−5 |
| Équilibre force relatif du corps | 5,5435e−14 | 2,5491e−14 |
| Équilibre moment relatif du corps | 1,2249e−14 | 2,9361e−14 |
| Complémentarité max N·m | 1,9832e−13 | 2,2757e−12 |
| Écart multiplicateur à l’oracle QP archivé N | 2,5441e−8 | 4,1542e−7 |
| Front actif bracketé, rangées | 5/5 | 6/6 |
| Erreur max front / hx | 1,0 | 1,0 |
| Faux positifs / faux négatifs | 5 / 0 | 6 / 0 |
| Stationnarité de production | `NOT_EVALUATED` | `NOT_EVALUATED` |

Les erreurs de force/moment en découlent directement : l’ancien calcul avait inversé la résultante de contact avant de la sommer aux charges et réactions. Après correction, les deux bilans sont très inférieurs à `1e−9`. Le front se trouve à la limite d’une cellule; tous les faux positifs observés restent dans cette bande. Les seuils AR ne sont pas modifiés.

## Limites et indépendance

- Les nombres M4/M5 corrigés sont des transformations de données N06, pas de nouvelles observations. Les champs N06, logs, ledger, hashes et verdicts gardent leurs valeurs originales.
- L’oracle QP stocke son propre vecteur de déplacement et multiplicateurs; l’accord recalculé des multiplicateurs est informatif mais repose toujours sur la même sortie N06 côté production.
- Le vecteur de force interne production n’a pas été archivé. La stationnarité corrigée n’est donc pas recalculable sans hypothèse ou nouveau calcul : elle reste `NOT_EVALUATED`.
- La réaction opposée du plan maître est déduite de l’action/réaction; aucun vecteur maître distinct n’est archivé.
- Les traces historiques AQ M2/M3 restent indisponibles : les résumés agrégés/maxima ne contiennent ni lignes, ni gaps, ni multiplicateurs par nœud, ni brackets. Le front complet M2–M5 reste `NOT_ACQUIRED`.
- Les résultats ne démontrent ni convergence asymptotique ni qualification générale. Aucune équivalence Docker, aucun `VERIFIED_BOUNDED`, aucune promotion de N06.

Fichiers détaillés conservés à part : `m4_offline_diagnostics.json`, `m5_offline_diagnostics.json` et `offline_diagnostic_summary.json` sous `qualification/0_2_12/wpc02_n07_offline_diagnostics/`.
