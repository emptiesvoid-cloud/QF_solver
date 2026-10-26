# Protocole quasi incompressible

**État : `PREPARED_NOT_AUTHORIZED`.** Aucun nouveau calcul ni eigensolve n’a été lancé.

Pour `E=1e6 Pa`, `μ=E/[2(1+ν)]`, `κ=E/[3(1−2ν)]` et `κ/μ=2(1+ν)/[3(1−2ν)]` :

| `ν` | `μ` (Pa) | `κ` (Pa) | `κ/μ` |
|---:|---:|---:|---:|
| 0,3 | 384 615,38 | 1 111 111,11 | 2,1667 |
| 0,45 | 344 827,59 | 3 333 333,33 | 9,6667 |
| 0,49 | 335 570,47 | 16 666 666,67 | 49,6667 |
| 0,499 | 333 555,70 | 166 666 666,67 | 499,6667 |
| 0,4999 | 333 355,56 | 1 666 666 666,67 | 4 999,6667 |

Utiliser les cinq `ν` à chaque niveau et pour chaque formulation, appariés par géométrie. Les 60 nodeids prévus figurent dans `NEXT_CAMPAIGN_MATRIX.csv`. Fixer avant campagne les versions de NumPy/SciPy, la méthode d’assemblage creux, le solveur et les tolérances. Enregistrer une estimation de condition avec méthode explicitée; ne pas calculer une SVD dense à 28 611 DDL sous le budget 16 GiB. Si une condition fiable ne peut être obtenue dans l’enveloppe, écrire `NOT_COMPUTED_RESOURCE_BOUNDED`.

Comparer les erreurs d’un déplacement signé, énergie, résidu, équilibre, déformation volumique moyenne projetée et énergie volumique, contre une référence mixte indépendante. Le déplacement plus grand n’est pas synonyme de précision : analyser l’erreur au même champ et à la même référence. Suivre le conditionnement et arrêter si le résidu, les bilans, les Jacobiens ou la mémoire franchissent les seuils pré-gelés. Les résultats à un seul maillage ne distinguent pas verrouillage, erreur de discrétisation et conditions aux limites.

Le seul constat actuel est borné : à `ν=.4999`, sur le 4×2×2 historique, HEX8 standard donne −0,474 mm contre environ −3,411 mm pour les deux SRI. Le conditionnement archivé monte à `8,59e8` pour le SRI corrigé. Ces valeurs motivent l’étude, mais ne constituent ni une validation d’incompressibilité, ni une conclusion sur l’exactitude.
