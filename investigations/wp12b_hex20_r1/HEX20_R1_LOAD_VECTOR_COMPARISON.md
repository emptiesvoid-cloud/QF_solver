# HEX20 R1 — charges nodales de production et oracle QUAD8

Les données de chaque nœud et composante sont dans [R1_DERIVED_MATRIX_COMPARISON.json](R1_DERIVED_MATRIX_COMPARISON.json), recalculées depuis le sidecar SHA-256 `dee3c6976929954b7f4c5a678d474b3a151f7821db9c334f0f01d22320d2133e`. L'oracle sélectionne les nœuds par coordonnées, utilise l'aire géométrique et `t=σn`, sans table de faces ni quadrature de production. Il est exact pour les faces planes rectangulaires et tractions constantes du cas R1.

Pour une face de surface `A=1 m²`, `Fp−Fq=−2A t/27` par coin et `+2A t/27` par milieu. Les colonnes des nœuds suivent la boucle de production : quatre coins, puis les quatre milieux associés aux arêtes successives. Face 5 est encastrée et ne reçoit pas de charge appliquée de production; son vecteur indépendant est inclus dans l'oracle de frontière à six faces.

| Face | Normale | Composante | Coins | Milieux | `Fp−Fq` par coin / milieu (N) | Résultante production = oracle (N) | Moment production = oracle (N·m) |
|---|---|---|---|---|---|---|---|
| 0 | −Z | Z | 0,3,2,1 | 9,13,11,8 | `+897435,897 / −897435,897` | `(0,0,−12115384,615)` | `(0,6057692,308,0)` |
| 1 | +Z | Z | 4,5,6,7 | 16,18,19,17 | `−897435,897 / +897435,897` | `(0,0,12115384,615)` | `(0,−6057692,308,0)` |
| 2 | −Y | Y | 0,1,5,4 | 8,12,16,10 | `+897435,897 / −897435,897` | `(0,−12115384,615,0)` | `(0,0,−6057692,308)` |
| 3 | +X | X | 1,2,6,5 | 11,14,18,12 | `−2094017,094 / +2094017,094` | `(28269230,769,0,0)` | `(0,0,0)` |
| 4 | +Y | Y | 2,3,7,6 | 13,15,19,14 | `−897435,897 / +897435,897` | `(0,12115384,615,0)` | `(0,0,6057692,308)` |
| 5 | −X | X | 3,0,4,7 | 9,10,17,15 | non appliquée | oracle `(-28269230,769,0,0)` | oracle `(0,0,0)` |

Les autres composantes sont nulles par face dans ce chargement. La face 3 illustre la distribution : chaque coin reçoit `−4 449 786,325 N` en production contre `−2 355 769,231 N` par l'oracle; chaque milieu reçoit `11 517 094,017 N` contre `9 423 076,923 N`. Malgré cela, les quatre écarts de coin et les quatre écarts de milieu s'annulent en résultante et moment.

La somme des cinq vecteurs de production reproduit exactement `F` archivé (`||F−ΣF_face||∞=0`). Le défaut est donc dans la distribution intégrée de face sur ce cas, non dans la sommation de ces cinq vecteurs. Les normales, milieux et jacobiens surfaciques sont vérifiés géométriquement dans le JSON; leur conformité sur ce cube ne prouve pas celle d'autres géométries.
