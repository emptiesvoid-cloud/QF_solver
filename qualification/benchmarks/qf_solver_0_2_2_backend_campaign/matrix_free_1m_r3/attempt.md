# R3 matrix-free 1M - relance controlee

La relance a vise `1 000 000` DDL avec le backend `matrix_free`, un timeout de
`900 s`, un intervalle de telemetry de `30 s` et des blocs de `4096`.

| Observable | Valeur |
|---|---:|
| Duree mesuree | `901,113 s` |
| Echantillons de telemetry | `31` |
| Pic RSS | `293,77 MiB` |
| Pic HWM | `293,77 MiB` |
| Code de retour | `-15` |
| Resume solveur | absent |
| Residu final | indisponible |
| Verdict | `BLOCKED_TIMEOUT` |

Le processus etait encore actif au dernier echantillon et sa memoire residente
est restee bornee. Cette observation ecarte un OOM sur cette tentative, mais ne
prouve ni la convergence ni la performance acceptable du cas 1M. La prochaine
etude doit profiler l'assemblage et les produits matrice-vecteur avant de
repeter un calcul long.
