# Exécution du nettoyage local QF Solver — Phase 2

Résumé public rattaché à la PR #118. Les chemins de poste, noms d’utilisateurs et détails de dossiers scientifiques sont omis ici. Le journal exact par chemin est conservé localement par l’Owner; il n’est pas publié dans ce dépôt public.

## Résultats observés

| Volume | Espace libre avant (octets) | Mesure finale (octets) | Variation nette observée |
|---|---:|---:|---:|
| C: | 19 769 651 200 | 23 293 005 824 | +3 523 354 624 B |
| D: | 89 865 822 208 | 89 865 822 208 | 0 B |
| E: | 840 807 104 512 | 841 536 024 576 | +728 920 064 B |

La variation nette C:+E est d’environ **3,96 Gio**. Elle mesure l’évolution de l’espace libre des volumes, pas la somme exacte des tailles logiques supprimées. Les caches supprimés représentaient environ 2,29 Gio logiques et deux copies de worktree environ 1,30 Gio logiques; allocation NTFS et activité concurrente peuvent modifier l’écart.

### Caches

- 14 420 répertoires de caches standards ont été supprimés sans forçage.
- Le cache pip identifié a été purgé; un résidu de vérification a ensuite été supprimé après inspection.
- 186 répertoires Python ont été conservés après refus d’accès Windows; aucune nouvelle tentative avec privilèges/forçage n’a été faite.
- Les chemins associés à des processus ou fils actifs ont été exclus.

Les exports agrégés, sans chemins locaux, sont dans [l’inventaire résumé](QF_SOLVER_LOCAL_DISK_CLEANUP_PHASE2_INVENTORY_SUMMARY.csv) et [le résumé des opérations](QF_SOLVER_LOCAL_DISK_CLEANUP_PHASE2_OUTCOME_SUMMARY.csv).

### Worktrees

Deux copies propres et redondantes d’un même checkout ont été retirées avec `git worktree remove`, sans `--force`. Leur SHA était `f5f46c51344b7cd9352a9b67c63acd418b0e6e42`, arbre `62401358022471a9bdca07b06c7d8db6bf52f566`. Le commit était ancêtre de la branche distante `emptiesvoids-cloud/0.2.12` au SHA observé `ab137051d920d7fa9aae9a3012a48b2b26e2198b`. La branche locale et les objets Git partagés ont été conservés. Il restait 162 worktrees enregistrés après l’opération.

### Conservation

Aucune suppression de donnée scientifique, build, manifeste, ledger ou archive de preuve n’a été effectuée. Les grands ensembles historiques examinés en Phase 2 ont été laissés en place pour revue distincte. Aucun calcul FEM, test, `git gc`, `git clean` ou reset Git n’a été lancé.
