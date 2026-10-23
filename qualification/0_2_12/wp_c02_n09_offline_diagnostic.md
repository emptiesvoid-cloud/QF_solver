# WP-C02-N09 — Rejeu hors ligne des diagnostics N08

## Statut et entrée

**`OFFLINE_DIAGNOSTIC_ONLY`**. Aucun modèle, solveur, assemblage de matrice ni calcul FEM n’a été exécuté. Le script [`diagnose_wpc02_n08_force_energy_offline.py`](../../scripts/diagnose_wpc02_n08_force_energy_offline.py) lit uniquement les JSON archivés et valide avant calcul les tailles et SHA-256 des 539 fichiers de l’archive.

Source : archive de la revue N08 de l’unique campagne native identifiée `wpc02-ar-native-n07-m4m5-20261023-01`, dans `wpc02_ar_native_campaign_n07_20261023_01`. Cette identité reste historique et n’est pas réutilisée. HEAD/tree de l’exécution : `d517ddc53a871e3032ac82d2712076693e45220b` / `daece63b182e733ea19183febbfb4a61827140bc`. Manifeste d’exécution N07 SHA-256 `1618fe6f3cd29cd9f1a3005a45f92df7937c26cdd6ce94bf785261d65149309a`; manifeste d’intégrité de l’archive SHA-256 `5df8d84ed560c3535b9c5cbc2ae04d94916059415b9363a56e35cab41a435bc2`. Les diagnostics sources sont M4 SHA-256 `894ae0bcb82d3b97e1cf539465f2fe3b67764eaa97f5f7a041600aec83000def` et M5 SHA-256 `d435b99c8e1f8df9cdfa26b0a6019e270f06bbc99e6f4cd9553dc363ad4bc1e5`.

Le JSON de sortie est [`wpc02_n09_offline_diagnostic.json`](wpc02_n09_offline_diagnostic.json). Il ne modifie aucun fichier N08 et marque explicitement `production_stationarity_status=NOT_EVALUATED`.

## Méthode

Le contact physique archivé est `p_i≥0` (N), et le déplacement vertical archivé est `u_{z,i}` (m). Le produit final-force–déplacement recalculé est `C_contact=Σ p_i u_{z,i}`. Il est comparé au scalaire `production_contact_work_j` de l’archive, au sens de l’identité d’extrémité AR. Il ne s’agit pas de l’intégrale physique du travail de contact sur le trajet; aucun terme `∫P(α)ᵀdu` n’est reconstruit. Dans le modèle frictionless linéaire, le vecteur production archivé lors de N08 était interprété comme `internal_force=K u−P`, donc l’ancien scalaire `U_old=½uᵀinternal_force` vaut `U_el−½C_contact`. La valeur élastique corrigée hors ligne est `U_el=U_old+½C_contact`. Elle est comparée à l’énergie de déformation indépendante déjà calculée par intégration quadraturée dans N08.

L’archive n’a pas les vecteurs bruts production `internal_force` ou `residual`, ni `K u`. Aucune stationnarité corrigée n’est donc estimée ou reconstruite depuis l’oracle QP. La valeur historique de stationnarité provenait de la formule N08 qui soustrayait le contact une seconde fois; elle demeure un FAIL historique et ne devient pas une nouvelle mesure.

## Valeurs recalculées

| Niveau | Produit final-force–déplacement contact recalculé (J) | `U_old` archivée (J) | `U_el` corrigée hors ligne (J) | Quadrature archivée (J) | Ancien écart (J) | Écart corrigé hors ligne (J) |
|---|---:|---:|---:|---:|---:|---:|
| M4 | −0,16674289824050134 | 1,569158561910239 | 1,4857871127899884 | 1,485787112790032 | 0,08337144912020711 | 4,352074256530614×10⁻¹⁴ |
| M5 | −0,16666845229584257 | 1,5692791978995198 | 1,4859449717515985 | 1,485944971751668 | 0,0833342261478518 | 6,94999613415348×10⁻¹⁴ |

L’écart corrigé est inférieur au seuil inchangé de `1e-10 J` sur ces champs archivés, mais cette constatation est une correction arithmétique hors ligne du post-traitement N08. Elle ne remplace pas l’assertion d’un test exécuté avec le collecteur N09 et ne modifie pas `N08_M4=FAIL` ou `N08_M5=FAIL`.

## Éléments manquants et autres gates

- `internal_force` production brut : absent de l’archive N08.
- `residual` production brut : absent de l’archive N08.
- `K u` production : absent de l’archive N08.
- Stationnarité de production recalculable : **NOT_EVALUATED**.
- Traces ligne par ligne du front AQ M2/M3 : `NOT_RECORDED_IN_AQ_SUMMARY`; classement complet du front M2–M5 : **NOT_ACQUIRED**.
- Résultats N08 : M4 FAIL et M5 FAIL conservés. Résultat spatial WP-C02 global : **NOT_ACQUIRED**.

Le nouveau collecteur enregistre les forces totales et résidus bruts dès `SOLVER_COMPLETED_RAW_FIELDS` lors d’une éventuelle acquisition future autorisée. N09 ne lance pas cette acquisition.
