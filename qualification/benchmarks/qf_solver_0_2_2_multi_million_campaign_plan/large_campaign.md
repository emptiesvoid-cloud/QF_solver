# Campagne grands modeles TET4

Statut: **BLOCKED**

- Mode: `plan_only`
- Backend: `petsc`
- Preconditionneur: `gamg`
- Taille de bloc: 4096
- Budget mémoire explicite [octets]: 34359738368
- Interpretation: campagne de taille sur une configuration; ce rapport ne revendique pas une scalabilite forte/faible.

| Cible DDL | DDL estimes/reels | Elements | Statut | Temps pipeline [s] | Iterations | Residu | Pic RSS [octets] |
| ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 2000000 | 2044416 | 3951018 | BLOCKED | non execute | non execute | non execute | non execute |
| 4000000 | 4102893 | 7986000 | BLOCKED | non execute | non execute | non execute | non execute |

## Limites

Aucun calcul n'a ete execute. Les tailles et memoires sont des estimations de readiness.
La scalabilite forte/faible exige plusieurs nombres de rangs MPI et reste a mesurer separement.
