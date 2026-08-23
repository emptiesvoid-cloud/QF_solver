# Matrix-free 1M DDL : campagne incomplete

La tentative matrix-free autour de `1 000 000` DDL a ete arretee localement
apres une execution prolongee sans production de metriques solveur, de
residu, de rapport de convergence ou de manifeste d'evidence.

Le dossier ne contient donc aucune conclusion sur une divergence numerique,
une erreur de solution ou un pic memoire. Le statut est
`BLOCKED_RESOURCE_LIMIT`, avec `manual_stop_without_metrics` comme motif
trace. Cette tentative ne constitue ni un PASS ni un FAIL numerique.

Le dossier `results_large/qualification_matrix_free_1m` ne doit pas etre
utilise pour decrire cette tentative : il correspond a une ancienne campagne
PETSc/GAMG a `1 029 000` DDL, version `0.2.1a0`, et non au chemin matrix-free
de la tranche `0.2.2a0`.
