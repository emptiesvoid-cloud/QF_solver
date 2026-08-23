# Matrix-free 1M - relance R3

Statut : **BLOCKED_TIMEOUT**.

Le modele de `1 029 000` DDL a ete relance avec le backend `matrix_free`,
un timeout de `900 s`, une telemetry toutes les `30 s` et une sortie de
runner persistante. La campagne a produit `31` points de telemetry. La RSS
observee est restee proche de `308 224 000` octets, soit `293,95 MiB`.

Le processus est reste actif jusqu'au timeout controle, sans produire de
resume solveur ni de residu final. Aucun echec numerique n'a ete observe et
aucun PASS n'est revendique. R3 est donc executee et documentee, mais le
perimetre matrix-free 1M reste bloque par le temps de calcul.

Artefacts : `attempt.json`, `run_metadata.json`, `telemetry.jsonl` et
`runner.log`. Le modele source est l'artefact historique
`results_large/qualification_matrix_free_1m/qualification_model.h5`; son
ancien resultat PETSc n'est pas reutilise comme preuve matrix-free.
