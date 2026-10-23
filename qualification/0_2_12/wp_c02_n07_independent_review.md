# WP-C02-N07 — Revue indépendante finale

## Avis

**Favorable au gel du code candidat; aucun finding P0/P1 ouvert.** Le candidat peut être commité et gelé selon l'autorisation N07. Cet avis ne constitue pas une autorisation de RUN FEM.

## Portée et preuves

La revue finale a été effectuée en lecture seule sur le delta N07, après ajout des contrôles de signe/flags, de ledger et du paramétrage du générateur de manifeste. Le réviseur n'a lancé aucun test, solveur, assemblage, calcul FEM ou Docker.

- Le correctif du collecteur reste limité au post-traitement; aucun changement au noyau FEM, aux équations, matériaux, conditions aux limites, maillages ou seuils AR n'a été relevé.
- Le collecteur utilise la convention de production déjà auditée : `row["pressure"]` est la force nodale positive en compression (N), la force surfacique vaut force/aire (Pa), et la force sur l'esclave suit `+p n`.
- Le décodeur rejette les tractions dépassant `force_tolerance_n=1e-7 N` et les divergences fortes entre le drapeau actif et le signe/seuil de force; les rangées biactives à force nulle restent possibles.
- Une archive identifiée par un manifeste d'intégrité ou d'exécution mais sans `run_ledger.json` est classée erreur de collecte; l'état scientifique FAIL du ledger demeure prioritaire sur les métriques dérivées manquantes.
- Le nouveau paramétrage du script de gel préserve les valeurs par défaut N03 et permet d'indiquer explicitement une campagne N07. L'identité du manifeste N07 reste à produire après commit.
- Les 46 tests unitaires/non-FEM et contrôles de compilation/statique ont été exécutés par l'agent auteur, pas par le réviseur. Le détail et les commandes figurent dans le rapport d'audit.

## Findings

| Niveau | Finding | Traitement |
|---|---|---|
| P0 | Aucun | — |
| P1 | Aucun | — |
| P2 | La procédure détaillée ayant produit les diagnostics offline n'est pas fournie comme script versionné; les données d'entrée/sortie et hashes sont conservés. | Limite documentée; les résultats restent `OFFLINE_DIAGNOSTIC_ONLY`. |
| P2 | Les nouveaux arguments de `freeze_wpc02_ar_native_manifest.py` n'ont pas de test dédié. | Le manifeste doit être généré après commit, puis ses champs, hashes et identité seront vérifiés avec les tests de contrat existants et un contrôle statique. |

## Statuts et limites

Cette revue ne change pas les résultats antérieurs : `N06_M4=FAIL`, `N06_M5=FAIL`, `WP_C02_SPATIAL_CONVERGENCE=NOT_ACQUIRED`, `GENERAL_CONTACT_QUALIFICATION=NOT_ACQUIRED`. Les verdicts Docker historiques `FAIL_CLOSED` restent intacts.

La revue approuve le gel du correctif de post-traitement et des diagnostics hors ligne avec les P2 ci-dessus. Elle ne qualifie pas M4/M5, ne transforme aucune valeur offline en résultat de campagne, n'autorise aucun calcul, et ne confère aucune équivalence à une qualification Docker.

## Suite autorisée

Après commit, produire un manifeste externe N07 pour le nouveau HEAD/tree, vérifier les empreintes déclarées, le contrat de critères et l'identité, puis archiver les hashes du manifeste et du commit dans le rapport final. Tout RUN FEM demandera une autorisation Owner distincte.
