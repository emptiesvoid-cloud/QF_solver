# WP13 R2.1 — caractérisation J2 TET4/TET10/HEX8/HEX20

## Résultat

```text
WP13_R2_STATUS = PASS_CANDIDATE_WITH_LIMITATIONS
CAMPAIGN_STATUS = PASS_INTERNAL
OFFICIAL_WP13_POINTS = 0 — unchanged; Owner decision and ledger allocation remain pending
```

Les quatre cas ont convergé sur les 24 facteurs de charge, avec résultats complets finis et sans échec d’import bloquant. L’exécution est séquentielle. Ce résultat caractérise un cas J2 borné ; ce n’est ni une qualification globale des familles, ni un classement d’efficacité ou une validation de précision.

| Élément | Nœuds | Éléments | DDL | États d’intégration | Temps solveur (s) | Newton | Résidu relatif max | Pic `tracemalloc` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 68 | 140 | 204 | 140 | 34.572482 | 33 | 4.0612e-9 | 11,423,702 B |
| TET10 | 341 | 140 | 1,023 | 560 | 136.371798 | 33 | 7.4937e-9 | 51,728,284 B |
| HEX8 | 63 | 24 | 189 | 192 | 56.589020 | 33 | 9.1961e-11 | 7,717,796 B |
| HEX20 | 201 | 24 | 603 | 648 | 517.012010 | 42 | 2.1790e-10 | 35,245,653 B |

Tous : `solver_status=PASS`, 24/24 incréments, `full_result_json_finite=true`. Les imports HEX8/HEX20 sont `PASS` sans avertissement. TET4/TET10 ont un rapport global `WARNING` uniquement parce que les groupes physiques `y_min` et `z_min` ne sont pas utilisés ; leur validation géométrique reste `mesh_status=PASS`, et ces deux avertissements sont explicitement autorisés/archivés par le contrat.

## Lecture des performances

HEX20 a été le cas le plus coûteux de cette campagne : 517 s de temps solveur pour 603 DDL, 648 états d’intégration et 42 itérations de Newton. HEX8 a pris 56.6 s pour 189 DDL. Ces valeurs ne permettent pas d’isoler le coût propre d’un élément : les topologies, ordres, nombres d’éléments et maillages diffèrent.

Par rapport aux observations WP13 R1, TET4 est ici environ 3.91× plus lent (`34.57 s` contre `8.84 s`) et TET10 environ 3.83× (`136.37 s` contre `35.61 s`). Les métadonnées plateforme/Python sont comparables, mais cette campagne ne contrôle ni répète les conditions de charge machine et ne diagnostique pas cette différence. Elle ne doit donc pas être présentée comme une régression attribuée à HEX8/HEX20, ni comme une mesure A/B reproductible. Une comparaison performance formelle nécessiterait des répétitions et un protocole de charge/environnement dédié ; aucun rerun n’est inclus ici.

Le pic mémoire est `tracemalloc` (allocations Python), pas le RSS. Les temps ne couvrent que `solve_model`, après création et import du maillage.

## Contrat, provenance et incident de lancement

- Contrat actif : `QF-029-WP13-EXEC-003`, contrat R2.1 prospectif.
- SHA-256 contrat : `8ff91f880f2979198d23b23b7f98b3df0d8a698e33124b454849e86d43896499`.
- SHA d’exécution : `1fc52758d53e1caa4434b22f453fb03fa40f6266`.
- SHA d’implémentation (parent immédiat du contrat) : `77a640b438b495603670a756b1ff2548b7a75ec3`.
- Branche isolée : `codex/wp13-r2-multifamily`.
- Policy digest : `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`.
- Contrat R2 initial conservé : son premier lancement a échoué au chargement Python (`ModuleNotFoundError`) avant création du répertoire brut ou tout solve. R2.1 a ajouté uniquement le bootstrap `src/`, rebindi les hashes, puis lancé la même campagne sans changer les cas ou paramètres.
- Le runner a vérifié branche, arbre propre, SHA parent, policy digest, hashes sources et chemin brut. Environnement : Windows 10, Python 3.13.1, NumPy 2.2.6, Gmsh 4.15.2, 6 cœurs physiques / 12 logiques.

Contrat : [`wp13_r2_1_execution_contract.json`](../../../qualification/0_2_9/wp13_r2_multifamily/wp13_r2_1_execution_contract.json)
Registre d’exécution : [`wp13_r2_execution_record.json`](../../../qualification/0_2_9/wp13_r2_multifamily/wp13_r2_execution_record.json)
Manifeste SHA-256 brut : [`wp13_r2_raw_evidence_manifest.json`](../../../qualification/0_2_9/wp13_r2_multifamily/wp13_r2_raw_evidence_manifest.json)

Les 18 fichiers bruts (résultats, setups, maillages et rapports d’import) totalisent 99,611,184 octets (~95.0 MiB) et restent dans le répertoire local ignoré `qualification/0_2_9/wp13_r2_multifamily/raw/`. Le manifeste versionné contient taille et SHA-256 de chaque fichier. Aucun service d’archive externe ou sauvegarde n’est configuré pour ce dossier.

## Vérifications et périmètre

- Tests ciblés (API publique, audit/diagnostics, harness de performance, nouveau maillage et setup multifamille) : **21 passed**.
- Ruff : PASS ; mypy ciblé sur runner/campagne/tests : PASS ; compileall : PASS ; JSON brut : 13/13 parsés ; `git diff --check` : PASS.
- Suite complète : non exécutée.
- Aucun changement de mécanique solver, seuil numérique, politique ou fallback ; changements limités à l’outillage de benchmark/maillage, tests, contrat et preuves.
- WP14 non exécuté ; ledger non modifié ; aucun point officiel attribué ; aucun merge ou push.

Limites : barre J2 cyclique homogène uniquement, un maillage par famille, aucune étude de convergence, aucune comparaison à un solveur externe, aucune revendication de scalabilité/HPC ou de classement d’éléments. Le dossier peut passer à une revue Owner comme caractérisation expérimentale bornée, avec la différence de temps TET entre R1/R2 explicitement non résolue.
