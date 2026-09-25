# WP07-D — correction de l’intégration pénalité `surface_lumped`

## Résumé

La campagne WP07-D R2.3 a échoué en route `PENALTY` sur M1, M2 et M3 avec
`LINE_SEARCH_FAILURE` au premier incrément. L’analyse du contrat, du runner,
du modèle parsé et de l’assembleur révèle une divergence d’implémentation : le
runner et la référence indépendante déclaraient et utilisaient
`surface_lumped`, tandis que l’assembleur de production appliquait la pénalité
complète à chaque nœud esclave.

Le paramètre `contact_penalty_integration` était placé dans les paramètres du
modèle, mais jamais lu par l’assembleur. En outre, `slave_patch_faces` était
fourni par le runner puis ignoré par le parseur du modèle. L’assembleur ne
renvoyait pas non plus les `effective_penalties` attendues par l’extraction
d’observables du runner.

## Effet quantifié avant correction

Le contrat R2.3 fixe une pénalité totale de `1e8` répartie selon les aires
tributaires du patch. L’ancienne assemblée nodale utilisait `1e8` à chacun des
nœuds du patch, sans tenir compte des poids de surface :

| Niveau | Nœuds esclaves | Pénalité totale ancienne | Pénalité totale contractuelle |
|---|---:|---:|---:|
| M1 | 81 | `8.1e9` | `1.0e8` |
| M2 | 289 | `2.89e10` | `1.0e8` |
| M3 | 561 | `5.61e10` | `1.0e8` |

Cette erreur rendait la raideur de contact dépendante du nombre de nœuds et
pouvait dégrader fortement le conditionnement et la recherche linéaire lors du
raffinement. Elle constitue une explication mécanique plausible et directement
étayée des échecs observés ; seul un rerun autorisé peut confirmer si elle en
était la cause suffisante.

Les résultats R2.3 d’origine restent inchangés et classés `FAIL_CLOSED` :
M1/M2/M3 ont échoué au premier incrément, respectivement après 5, 7 et 5
itérations Newton. Aucun fallback n’a été utilisé.

## Correction implémentée

- Le modèle conserve maintenant les faces triangulaires de la surface esclave.
- En mode explicitement sélectionné `surface_lumped`, l’assembleur calcule,
  pour chaque nœud, son aire tributaire divisée par l’aire totale du patch.
- Les poids sont appliqués de façon cohérente à la force interne et à la
  tangente; ils restent positifs et leur somme vaut 1 par patch.
- Les pénalités effectives sont incluses dans les détails d’assemblage pour
  que l’extraction du résultant et de l’énergie utilise exactement les
  coefficients appliqués par le solveur.
- Le mode historique `nodal` reste le défaut et conserve sa contribution
  mécanique antérieure.
- Seuils, géométrie, maillages, charges, matériau, pénalité de base,
  tolérances, politique de recherche linéaire, backend et fallback n’ont pas
  été modifiés.

## Vérification locale

Pour les géométries exactes de WP07-D, les poids calculés par l’assembleur
concordent exactement avec la recomputation indépendante existante :

| Niveau | Nœuds | Faces | Somme des poids | Écart max à la référence |
|---|---:|---:|---:|---:|
| M1 | 81 | 128 | `0.9999999999999998` | `0` |
| M2 | 289 | 512 | `0.9999999999999980` | `0` |
| M3 | 561 | 1024 | `1.0000000000000010` | `0` |

La correction est committée au SHA source `4e63f0929b0d8a4ff83482769a34a2ce3e232544`.
La vérification ciblée a donné `89 passed`, Ruff PASS, mypy PASS sur les quatre
fichiers source/test visés, compileall PASS et `git diff --check` PASS.

## Statut de requalification

Cette vérification ne constitue pas une qualification structurelle. Aucun
solve M1/M2/M3 n’a été lancé sur le nouveau SHA. Les autorisations existantes
sont exactes pour l’ancien SHA `a2483c6b157de5fc06c53d81ea92b638feaacb54`;
le garde d’exécution les refuse désormais, comme prévu, car le code de
production a changé. Une nouvelle autorisation liée au SHA source ci-dessus
est nécessaire avant toute exécution formelle, référence ou replay.

```text
WP07D_OLD_PENALTY_M1_M2_M3 = FAIL_CLOSED_HISTORICAL_PRESERVED
WP07D_SURFACE_LUMPED_IMPLEMENTATION = CORRECTED_NOT_REQUALIFIED
WP07D_NEW_M1_M2_M3 = NOT_RUN_OWNER_SHA_BOUND_AUTHORIZATION_REQUIRED
WP07D_FORMAL_POINTS = UNCHANGED
WP07E = NOT_RUN
WP08 = NOT_MODIFIED_BY_THIS_REMEDIATION
PRODUCTION_MECHANICS_CHANGED = YES
THRESHOLDS_CHANGED = NO
MERGE_OR_PUSH = NOT_PERFORMED
```
