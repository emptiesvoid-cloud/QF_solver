# Spécification de configuration R2 — non implémentée, non autorisée

Scope proposé : `wp12_hex20_affine_diagnostic_r2`; nodeid exact `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual`. La proposition n'est pas une politique active. Les limites proposées sont un seul cas, une tentative, 60 DDL, 300 s, 4096 MiB RSS échantillonnée et 256 MiB d'archives; elles doivent être inscrites dans une politique revue avant d'être considérées comme définitives.

Un validateur en lecture seule du ledger R1 est préparé et testé synthétiquement; il n'est pas raccordé au runner. La matrice voisine énumère 14 nodeids candidats avec des budgets proposés, sans les enregistrer. L'extension complète, les préflights et l'instrumentation des 13 cas de face restent à implémenter. Cette branche ne crée aucun mandat actif.

## Points de code à modifier dans un worktree Configuration distinct

1. Ajouter une entrée distincte dans `development_autonomous_policy.json` et `WP12_OWNER_ENVELOPES`, avec branche/root scientifique exacts après revue du commit `c2d93e255382b74a0cda64693db67a01fcd86268`, empreinte brute effectivement recalculée, mandat propre et racine d'évidence R2 distincte. Ne pas remplacer `wp12_hex20_affine_diagnostic` R1.
2. Étendre l'allowlist, les limites et la résolution d'un seul nodeid exact. Le runner doit valider au préalable la source, ses dépendances, l'origine du solveur, le budget et le clean worktree. Conserver le maximum d'une tentative par nodeid et par mandat R2.
3. Étendre explicitement la route de préflight HEX20 (`preflight_wp12b_hex20_diagnostic_pytest`, l'attestation de collecte et les choix CLI) pour qu'elle lie le scope R2 exact, sans override de skip, collecte un seul nodeid, vérifie `bodies_executed=false` et ne réserve rien. Vérifier et lier le SHA du ledger prédécesseur avant et après collecte.
4. Dans `_node_ledger_context` et la validation de réservation, exiger un nouveau ledger R2 sous la nouvelle racine. Vérifier en lecture seule le prédécesseur R1, son schéma, son mandat, son unique entrée consommée et le SHA-256 `ab5a8e4967ca204898f2eeec52b50f0c6b8e603d0328c3dff06926ff10669f53`. Refuser absence, changement, réutilisation comme ledger R2 ou toute incohérence; ne jamais initialiser ou écrire le ledger R1.
5. Étendre le passage et la validation du reçu d'exécution, l'identifiant de décision Owner, et `_wp12b_hex20_diagnostic_sidecar` pour R2. La liaison doit couvrir scope, DDL, nodeid, tentative, manifeste/SHA, `run.json`, taille, chemin et schéma v2; v1 reste compatible pour R1 historique. Lier aussi le reçu de préflight exact au manifeste et à la tentative si le nouveau contrat officiel le prévoit, en refusant les identités ou hashes périmés.
6. Conserver l'autorisation en attente jusqu'à un manifeste non autorisé produit par le runner et une décision Owner distincte correspondant aux identités finales. Ne pas créer un manifeste `OWNER_AUTHORIZED` ni un ledger lors de la préparation.

## Vérifications synthétiques avant toute intégration

- Acceptation R1/v1 et R1/v2 avec identités cohérentes; acceptation R2/v2 synthétique.
- Refus des versions inconnues, scopes externes, nodeid différent, DDL/budget altérés, source ou contrôleur obsolètes, sidecar ou manifeste non concordant, préflight absent ou altéré, décision absente.
- Refus de ledger R1 absent/modifié/incohérent, chemin R2 aliasant R1, ledger R2 contenant une tentative et dépassement de limite; démontrer zéro écriture sur le prédécesseur dans chaque scénario synthétique.
- R1 et les autres scopes inchangés, y compris mandats, allowlists, limites et chemins. Tests de concurrence et refus de création/écrasement.
- L'écriture atomique des preuves avant assertions et les échecs restent conservés. Les tests de face et de pression préparés restent exclus de toute suite automatique tant que non autorisés.

Après revue et intégration, une désignation officielle `AGENTS.md` épinglée au checkout de contrôleur définitif est nécessaire. Recalculer ses hashes, puis la source et les dépendances effectives; générer un manifeste non autorisé, le préflight officiel et la décision Owner liée aux identités exactes. Ce document n'autorise aucune de ces pièces ni aucun calcul.
