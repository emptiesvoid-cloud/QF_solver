# Revue du port expérimental du prédicteur sécant C24 — 2026-11-28

## Décision

**A — Lot prêt pour une revue d’intégration locale**, sous le statut expérimental décrit ici. Le commit est local et descendant de la tête distante vérifiée. Aucun FEM n’a été lancé pour cette revue. Aucun push, merge vers `main`, tag ou publication n’a été effectué.

Le prédicteur ne choisit ni n’accepte une correction Newton. Il construit un état d’essai détaché à partir des deux derniers états acceptés. Chaque correction reste soumise au garde historique; le contrôle exact inchangé ne peut intervenir que dans les cas déjà éligibles. Les deux verdicts restent distincts.

## Provenance et périmètre

| Élément | Identité vérifiée |
|---|---|
| `origin/0.3.0` au contrôle direct | `b9affb1456fbc04cc236b1bdd146d84e15fe8e5c` |
| Branche produit isolée | `emptiesvoids-cloud/c24-predictor-port-20261128` |
| Commit code/test local | `c6474cb69500c37ad1440981bfa0527e58d1e96f` |
| Source de la confirmation C | `c6ada5710da07aafb9c0de005b47e0513430ed99` |
| Source A/B historique | `4027760c32a132bb5f1b6c4f90ef1e5195829a09` |
| Rapport de confirmation | commit `42f15ed2852294ac509ee79ee0d1420d4175220c` |
| Contrôleur de confirmation | `edd95df1565c42cb12abaaa6f19845fe8055d74b` |

La vérification Git confirme que les fichiers sous `src/` de la source C sont identiques à ceux de la source A/B. Le port produit reprend ces composants testés, avec deux renforcements locaux : validation stricte des types et empreintes des schémas d’extension, et relecture de l’empreinte du checkpoint prédécesseur après son chargement. Il ajoute également un refus explicite si l’option est activée sur une autre route. Le contrôleur de campagne, ses contrats, ledgers, workers et archives de recherche n’ont pas été portés.

Le worktree utilisateur sur `0.2.12` était déjà modifié; il n’a pas été touché. Le worktree produit est parti directement de `b9affb14`. Le distant était encore à ce SHA au dernier contrôle.

### Identités de la confirmation C

Les empreintes lues correspondent au manifeste et au rapport de confirmation :

- contrat C : `c6d1f8c67eca66b189606e79acb4ecc778664a8ee34b45314f629850087dbba2` ; manifeste local : `762866ebb806ac86a5e2419fef4186b92af85c3f5d7d9c650f647eb79255b54a` ;
- checkpoint accepté 197 : `91afff92bddd38d768c25eb9f77b73be306348e194745724cf2aced4257c7e38` ; checkpoint 198 : `170d70cfb88169b618601d1568e6f968bdbeb4e8c52f8a4a8860566a8a2f1714` ;
- manifeste d’entrée : `dd34b0a7e151512b2e794f814fbdf9cbf394242692f219e0320760bb2f3b13cf` ; maillage : `1fc746d7bb4f673f4e08bc07c497b2ab10ef82002a22f591410bc947d3162116` ;
- préflight `pf-973b64c6fc73` : `PREFLIGHT_PASS` ; SHA-256 de son JSON : `02af1c6693810a1c5ab1e940dfa680d0aa01b52c1452600146056a0af64e9374` ;
- ledger de tentative : `d87000dea45b2216abb2f3424e2803c9b3340d0e87518e8edf8655e92835a762` ; ledger de campagne : `9c10ebaa6f9581d3beb6e666283eacf6e6e72a27cdcf65b1251b266e316087c8` ;
- résumé d’archive C : `d91f5ae1d31042a456bbe94d8094f05b2120e8f7bcda4640138bd9e98ff76bef` ; checkpoint final 210 : `623f17c7e21d139dab3c6e50e914145d7ae580e537d1282d7fa5daa6766f1bad`.

Le journal de validation indique `COMPLETE`. Les checkpoints et ledgers historiques n’ont pas été modifiés.

## Revue du comportement

L’option `experimental_secant_predictor` est absente par défaut et exige une valeur booléenne stricte. `true` est limité à une extension identifiée du chemin C24, sur la route Newton géométrique TET10, à pas fixes, avec `experimental_newton_exact_residual=true`, sans contact ni état matériau. L’extension vérifie la signature du modèle, les facteurs de charge absolus, les DDL imposés, les empreintes SHA-256 des checkpoints 197/198 et l’identité du chemin précédent. Les schémas invalides, historiques incomplets, checkpoints altérés ou états matériau/contact sont refusés.

Le vecteur extrapolé est un état d’essai détaché. La transaction Newton conserve l’état accepté comme base; un échec ou un refus ne remplace pas cet état. Le nouveau code ne change ni le seuil de Newton (`1e-8`), ni le seuil linéaire historique (`1e-7`), ni le budget de contrôle exact. Il n’introduit aucun nouveau schéma persistant de checkpoint.

Le périmètre est volontairement étroit : ce n’est pas une API générale de prédiction pour tout checkpoint. L’option `false` ou absente laisse le chemin de référence inchangé. L’activation sur une autre route est refusée.

## Résultat historique C et comparaison hors ligne

La confirmation C officiellement rapportée a atteint `p = 0,0546875` en six incréments : runner `PASS`, archive `COMPLETE`, Newton `CONVERGED`, 11 corrections. Le garde historique a accepté les onze corrections; le contrôle exact est resté `NOT_RUN` (0/48). Ce calcul confirme le prédicteur sur ce témoin, mais ne démontre pas le déclenchement du contrôle exact en situation de rejet.

J’ai vérifié hors ligne les trois tableaux de déplacement et de réaction archivés, sans modifier leurs fichiers. C et B ont les mêmes empreintes de champs et sont égaux bit à bit. Avec la norme relative L2 du contrat, dénominateur `max(||A||₂, ||B||₂, smallest_positive_float)`, C contre A donne `4,582644e-13` pour le déplacement et `3,563749e-13` pour les réactions. Les trois cas finissent à la même charge. Les archives A/B gardent leurs verdicts officiels `ARCHIVE_INVALID`; leur réussite au rejeu hors ligne ne réécrit pas ces verdicts.

La comparaison ne montre pas de gain supplémentaire de C par rapport à B : chacun a 11 corrections, avec 41,397 s pour C et 41,336 s pour B. L’écart A/B (36 contre 11 corrections) reste une observation sur une seule plage, pas une mesure générale de performance. Les bilans historiques sont réévalués avec le même opérateur produit, pas par une référence mécanique indépendante.

## Tests ciblés sans FEM

Chaque nodeid a été exécuté séparément, conformément à la politique locale. Les tests de route remplacent l’assemblage par une matrice identité jouet; ils vérifient le routage, Newton et les checkpoints, pas la formulation FEM.

| Nodeid / vérification | Résultat | Portée |
|---|---:|---|
| `test_c24_secant_extension_resumes_step_198_on_same_absolute_path` | PASS | Checkpoints 197/198, facteurs absolus, ratios 2 puis 1, refus de mauvaise identité/empreinte, état accepté préservé après refus; assemblage double. |
| `test_c24_terminal_extension_keeps_absolute_force_and_accepted_state` | PASS | Extension du chemin absolu, archive corrompue et échec sans mutation; assemblage double. |
| `test_public_geometric_route_resumes_from_last_accepted_checkpoint` | PASS | Régression de reprise sans prédicteur; assemblage double. |
| `test_public_route_pauses_and_resumes_the_same_fixed_path` | PASS | Pause et reprise par défaut; assemblage double. |
| `test_secant_predictor_is_rejected_on_other_routes_and_false_is_a_noop` | PASS | Refus hors route et option désactivée sans changement sur `linear_static` simulé. |
| `test_secant_predictor_requires_an_identified_continuation_before_assembly` | PASS | Refus avant assemblage si l’identité/checkpoint requis manque. |
| `test_secant_predictor_option_requires_boolean` | PASS (3 cas) | Types invalides refusés. |
| `test_secant_trial_uses_load_ratio_preserves_fixed_dofs_and_source_states` | PASS | Calcul détaché, DDL imposés et ratios 2 puis 1. |
| `test_secant_trial_refuses_stateful_or_inconsistent_history` | PASS (3 cas) | Refus des états matériau/contact et DDL incohérents. |
| `test_accepted_and_disabled_do_not_start_check` | PASS | Le garde accepté et l’option désactivée n’appellent pas le contrôle exact. |
| `test_bound_pass_returns_original_without_refinement` | PASS | Verdict historique rejeté séparé du contrôle exact `PASS`. |
| `test_cancellation_above_exact_threshold_preserves_rejection` | PASS | Contrôle exact `FAIL`, sans promotion. |
| `ruff check` sur les fichiers du lot | PASS | Aucune erreur Ruff. |

Le test complet, les tests FEM et toute campagne de qualification sont `NOT_RUN`. `ruff format --check` signale des différences de formatage sur des fichiers historiques touchés; aucun reformatage global n’a été appliqué. Les deux nouveaux modules ajoutés passent le contrôle de format.

## Wheel installée hors checkout

La wheel reconstruite depuis le code testé `c6474cb69500c37ad1440981bfa0527e58d1e96f` a ensuite été installée avec `--force-reinstall --no-deps` dans deux environnements Python 3.13.1 hors checkout. Le dernier artefact de revue est :

- `qf_solver-0.3.0-py3-none-any.whl`, 1 742 708 octets ; SHA-256 `be112e522d6e8df29c91a3a4f886ab39f7d020030eb88c96c4eb34714328481f` ;
- un environnement avec `eas-diagnostic` (`psutil 7.2.2`) et un environnement sans cet extra (`psutil` absent) ;
- les scripts ont été lancés avec `python -I` depuis un répertoire temporaire, sans accès implicite au checkout. Dans les deux environnements, `solveur` provient de `site-packages` et `research` est introuvable.

Les vérifications supplémentaires ont exercé les interfaces de la wheel :

| Scénario installé | Résultat | Exercé |
|---|---|---|
| Garde `REJECTED_BOUND`, exact `PASS` sur les mêmes A/b/x et seuil | PASS | Adaptateur et vérificateur exact réels ; processus enfant réellement lancé sous Windows avec `spawn`, code de sortie 0. Le rejet historique reste `REJECTED_BOUND`. |
| Garde `REJECTED_BOUND`, `psutil` absent | `INCONCLUSIVE / PSUTIL_UNAVAILABLE` | Adaptateur installé et `solve_full_newton`; aucune correction n’est autorisée et le digest de l’état accepté reste inchangé. |
| Prédicteur absent/désactivé | PASS | Route publique TET10 synthétique ; reprise de `p=1.5` à `p=2.5`, sans diagnostic de prédicteur. |
| Checkpoint modifié | Refus | La route produit refuse le SHA incorrect avant la résolution. |
| Checkpoint issu d’un modèle/chargement incohérent | Refus | La validation produit rejette l’identité incompatible. |
| Erreur Newton après initialisation sécante | PASS du contrôle de sûreté | La route utilise un double d’assemblage identité; l’état/checkpoint source reste inchangé et aucune archive d’incrément accepté n’est créée. |

La route, Newton, le validateur de checkpoint et le superviseur sont importés depuis la wheel. Les essais de reprise remplacent uniquement l’assemblage TET10 par une matrice identité synthétique : ils vérifient l’interface et les transactions, et ne sont pas des calculs FEM. Le test exact `PASS` utilise le vérificateur réel en enfant; le cas sans `psutil` vérifie le refus avant promotion. La wheel inclut `solveur/core/nonlinear/secant.py` et ne contient pas de chemin `research/`.

Le budget temps de l’enfant et la limite de RSS sont respectivement un watchdog démarrant après le lancement synchrone et une surveillance RSS échantillonnée ; aucun quota mémoire OS strict n’est revendiqué. Les scénarios présents/absents de `psutil` ont été exercés, ainsi que le lancement `spawn` réel.

## Limites et conclusion

Le calcul C réel et les archives de comparaison restent des preuves de recherche, pas une nouvelle exécution de la route produit intégrée. Les tests de ce port et de la wheel sont synthétiques, sauf pour le solveur linéaire 2×2 et le processus enfant du vérificateur exact; aucun nouveau FEM n’a été lancé. Le prédicteur ne couvre pas les états matériau/contact et la transition de checkpoint reste limitée au chemin C24 explicite. La confirmation C n’a pas déclenché le contrôle exact en situation de rejet. Un gain observé sur une seule comparaison n’est pas une performance générale.

La branche locale est prête pour une revue d’intégration expérimentale, sans push. La tête distante vérifiée demeure `b9affb1456fbc04cc236b1bdd146d84e15fe8e5c`.
