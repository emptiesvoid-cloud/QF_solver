# Reproductibilité et audit des six cas archivés

## Identités et périmètre

| Identité | Valeur enregistrée |
|---|---|
| Campagne | `HEX8-SRI-CANTILEVER-6-2026-10-26` |
| Branche scientifique | `research/hex8-sri-equilibrium` |
| HEAD scientifique des calculs | `452f31f742ce4ce8356c68c691cbb3484a627920` |
| Fingerprint scientifique | `e14217217a6044ca9cb7c64a0f187864121589463c00e1eaac53251696b60c29` |
| Contrôleur | `codex/hex8sri-controller-registration` |
| HEAD contrôleur | `0d6286ecf75eea62ecafe63ec81cc816ad95226d` |
| SHA-256 runner / policy / plugin | `d73a2a4f…27f198` / `f44e167e…0693d` / `c1cf6238…e9ee16` |
| Origine du solveur | `src/solveur/__init__.py` du worktree scientifique, confirmée dans les six stdout capturés |
| Environnement enregistré | Python 3.13.1, pytest 8.4.1, NumPy 2.2.6 |

Les trois SHA du contrôleur sont complets dans `EVIDENCE_INDEX.json`. Les sources du calcul correspondent au fingerprint enregistré dans chaque manifeste; les six manifests sont `execution_authorized=true`, `do_not_execute=false`, et chacun a une tentative historique unique.

## Modèle apparié

- Géométrie : 20 × 1 × 1 m; maillage structuré 4 × 2 × 2, 16 HEX8 affines.
- 45 nœuds, 135 DDL, 27 DDL bloqués sur la face `x=0`, 108 libres.
- Élasticité isotrope linéaire, `E=1.0e6 Pa`; `ν=0.3` ou `ν=0.4999`.
- Charge nodale cohérente sur `x=20 m`, résultante `(0,0,-1) N`, appliquée aux neuf nœuds de face avec poids surfaciques tensoriels.
- Les trois formulations utilisent la même numérotation, la même géométrie, les mêmes appuis, charges et solveur direct.
- HEX8 standard : règle `2×2×2` complète. SRI historique : expression centrale source figée sans le poids `8`. SRI corrigé : terme volumique central avec le poids `8`.

## Résolution et observables

Les six tests ont un `run.json` `PASS`, code de retour zéro et tentative 1. Les manifestes donnent 180 s, RSS observée avec plafond souple à 1 024 MiB, au plus huit processus, archives 64 MiB, flux capturés bornés et aucun retry. Le contrôleur indique explicitement que le RSS, les processus, le temporaire et l’archive sont des observations/contrôles souples; le timeout est best-effort. Aucun échec historique n’a été relancé.

Les NPZ conservent notamment `K`, `Kff`, les matrices élémentaires, les nœuds, connectivités, charges, déplacements, résidus, réactions, déformations de Gauss et déterminants de Jacobien. Le post-traitement de ce dossier vérifie le bloc `Kff = K[free,free]`, puis recalcule `r=Ku-F`, réactions bloquées, fermetures de force/moment, `U=½uᵀKu`, `W=uᵀF`, défaut de symétrie et `cond₂(Kff)` à partir des matrices déjà archivées.

Pour les six cas, les observables recalculées concordent à la précision float64 sérialisée avec les sidecars : résidu libre, réactions, forces, moments, énergies et conditionnement. `FORMULATION_PAIRWISE_DIFFERENCES.csv` compare les `K` et `u` globaux archivés directement; il n’assemble pas de nouvelle matrice et ne résout rien.

## Résultats de critères

Les six tests sont PASS selon leurs gates gelés : tableaux finis, Jacobien positif aux huit points de Gauss et au centre enregistrés, résidu relatif libre `≤1e-7`. Les critères énergie et fermeture force/moment sont rapportés sans seuil supplémentaire (`REPORTED_NO_ADDITIONAL_THRESHOLD`). La convergence spatiale est `NOT_ASSESSED_SINGLE_MESH`.

Le sidecar nomme `energy_defect_normalized` une quantité calculée comme `|2U-W|/max(|W|,1 J)`. Comme `|W|<1 J` ici, cette grandeur conserve des unités de joules et n’est pas une erreur relative sans dimension. Le rapport utilise à la place `|2U-W|/|W|`, recalculé depuis les valeurs archivées; cette correction de présentation ne réécrit pas les sidecars historiques.

## Intégrité et portée

Vérification actuelle : exactement 12 fichiers dans l’archive de campagne (six sidecars et six NPZ), aucun fichier absent ou supplémentaire, et aucun SHA divergent entre les références des manifests/sidecars/reçus et les octets présents. Le rapport, le script et le JSON de la comparaison élémentaire antérieure, ainsi que les traces de ses tentatives, sont aussi indexés sans modification.

`run.json` ne contient pas de liaison SHA directe vers le sidecar et le NPZ. Il contient le nodeid, la référence et le SHA du manifeste, le reçu de préflight, le fingerprint source et les identités contrôleur/science. Le sidecar contient les chemins/SHA du manifeste et de son NPZ. L’association est unique pour chaque case mais demeure une liaison reconstituée, non une liaison cryptographique run→résultat.

Le post-traitement est algébrique et réutilise `K`, `F` et `u` issus du même calcul. Il vérifie l’intégrité et la cohérence interne; il n’est pas un oracle indépendant de la formulation ni une deuxième validation du solveur.
