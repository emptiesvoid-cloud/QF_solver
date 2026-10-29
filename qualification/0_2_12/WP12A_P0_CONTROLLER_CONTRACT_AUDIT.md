# WP12-A — Audit du contrat du contrôleur P0

**État : `BLOCKED_FOR_BATCH_READINESS`.** Aucun préflight officiel de ces candidats, manifeste de campagne, décision Owner d’exécution ou réservation réelle n’a été créé.

## Identités et contrôles observés

La release désigne le launcher `C:\Users\fari\.codex\worktrees\wp12-controller-hex20-0d91fc5\qf_solver\scripts\development_autonomous.py` : HEAD `0d91fc5a9bc09875526af6f17cf42c3ac666c5b7`, tree `3d57c36c948c9cc3fbc8a5d399fc465245c54a11`, fingerprint officiel recalculé `4fdbd810091de83ff5f729edfb4b9a20b660156e60dfa136c50eab97350e6afb`. Checkout propre et détaché. SHA-256 des octets locaux : runner `31fd3a08b78d73e5cc6720a6b96033568a64ec21e640781a2fa069ae86df55b0`, politique `ffe483af5ec8dbb590c7de0a3ec875291af2d4ad3876a914e861a6a76a694bf3`.

La source candidate propre est `E:\QFSolverAgents\wp12-dynamics` HEAD `7406e34efc28ed8f18c15440115595dfa3dd9ca5`, tree `a618d0d1790ab8642f408a78b2d2856debcc60c0`. L’inventaire officiel de source donne `f590849467f9fadf10e871c053d0f369e8e2a095a6ef99ddc452a9d6128b0262` pour les tests WP04 proposés, `f314c4d8011f9b9b815ee92ddc04d4386798a5a104bed528122649b2067efec1` pour les tests directs proposés et `2604e9d0d837a9860f70210be2fc96da1d124cb063d896884dc9033b96a30f23` pour le test de préparation. Ce sont des calculs d’empreinte, pas des inscriptions nouvelles ni des exécutions.

Le mandat est `DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1`, maximum 10 tentatives par nodeid et 130 au total, 300 s par processus. Le ledger v1 historique est `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37` ; le v2 est `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88`, 10/130 en incluant le prédécesseur. Les deux hashes ont été recalculés après les contrôles synthétiques. Le v2 conserve sa liaison au prédécesseur. Aucune écriture réelle au ledger n’a été demandée.

## Défauts du parcours groupé

1. `WP12_DYNAMICS_PREFLIGHT_NODEIDS` du contrôleur officiel n’autorise que les quatre anciens cas, même si la politique allowliste 13 nodeids. Le WP04 analytique proposé a une inscription active et un fingerprint concordant, mais est refusé avant collecte.
2. La politique Dynamics actuelle contient déjà 13/13 nodeids. Les cinq autres candidats du plan ne sont pas dans l’allowlist. Une inscription append-only exige une modification examinée de l’enveloppe, des allowlists exactes, des sélections DDL et des empreintes ; elle ne peut pas être faite en changeant directement le checkout épinglé.
3. `_validate_wp12_dynamics_preflight_receipt` exige que le SHA du ledger courant corresponde à celui du préflight. La première réservation fait évoluer ce SHA. Le test synthétique `test_wp12a_other_case_reservation_invalidates_prepared_case_preflight` reproduit sur fichiers temporaires le refus d’un cas B après la réservation simulée d’un autre cas A. L’intégrité du préflight, du prédécesseur et du ledger après refus est conservée.
4. Le schéma courant valide une décision explicite par manifeste et lie chaque manifeste à un préflight exact. Il n’existe pas de contrat officiel validé qui rende exécutables, après A, les décisions préalablement signées pour B et C. Les préparer toutes sur le même SHA ne satisfait donc pas la demande d’une seule revue exécutable.
5. Les candidats supplémentaires n’ont pas tous un sidecar numérique. Le succès d’un test de contrat de writer ne démontre pas qu’un test scientifique donné expose ses valeurs. Leur instrumentation, si nécessaire, doit être prospective et entraîner une nouvelle identité source.

## Travaux isolés et vérifications synthétiques

Dans le worktree `fix/wp12a-p0-batch-preparation-20261029`, une extension **non intégrée** du préflight accepte quatre nodeids supplémentaires déjà présents parmi les 13 allowlistés, dont le WP04 analytique ; la sélection finale du lot et l’inscription des nouveaux nodeids restent à compléter. Le contrôle synthétique vérifie que cette liste est un sous-ensemble de la politique et que le chemin collect-only ne réserve rien. Il ne modifie ni la politique, ni le contrôleur officiel, ni les plafonds.

Contrôles sur la base de développement : 50 tests de politique filtrés Dynamics PASS ; 4 variantes synthétiques du nouveau routage PASS ; 12 refus MPC/RBE PASS ; 5 DTO/inventaire API PASS ; 15 contrôles synthétiques sidecar PASS ; 1 test synthétique supplémentaire de péremption inter-cas PASS. Les tests de lancement utilisent des fichiers temporaires et un enfant simulé ; aucun résultat scientifique n’en découle. Ruff et `git diff --check` sont passés. Ces contrôles ne valident pas encore un parcours groupé réel.

## Contrat de campagne à concevoir, sans assouplissement silencieux

Une solution prospective devrait lier une décision Owner vérifiable à la liste ordonnée des nodeids exacts, à chaque identité source/test, au contrôleur, aux budgets, aux préflights et à un état initial de ledger. Avant chaque réservation, le contrôleur devrait vérifier sous verrou que toute transition depuis cet état est exactement celle de tentatives autorisées de cette campagne, avec identifiants uniques, ordre, plafonds, statut consommé et aucune écriture étrangère. Une divergence ou une modification de preuve doit refuser avant réservation ; les manifestes et décisions historiques restent inchangés. Cette solution n’est pas implémentée ou testée ici et doit être revue avec la politique, le runner, les tests synthétiques, la CI et la désignation officielle.

Le contournement consistant à ignorer le SHA du ledger, à régénérer un manifeste après approbation ou à faire passer une décision générique pour une décision liée à son SHA est exclu. Tant que le contrat groupé n’existe pas, seule la préparation just-in-time officielle permet de poursuivre chaque cas, avec une décision nouvelle sur son manifeste effectivement produit.
