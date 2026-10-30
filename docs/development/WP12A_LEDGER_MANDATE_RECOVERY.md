# WP12-A — Récupération du ledger et dossier de décision WP07

**Statut : WP12A_WP07_OWNER_EXECUTION_DECISION_READY**  
**Date : 2026-10-28**  
**Aucune exécution scientifique ni réservation n’a eu lieu pendant cette mission.**

## Résumé

Le refus « development attempt ledger identity/schema mismatch » provenait de la réutilisation, dans le scope Dynamics, du chemin générique d’un ledger historique lié à un autre mandat. La correction isole désormais le ledger Dynamics v2 et le rattache par empreinte à l’ancien ledger immuable. Le correctif et la nouvelle désignation du contrôleur sont intégrés.

Le préflight officiel collect-only du nodeid WP07 a réussi. Il a collecté exactement un test, sans skip, sans exécuter le corps et sans réserver ni toucher au ledger. Un nouveau manifeste est préparé et reste explicitement non autorisé. Une nouvelle décision Owner est nécessaire avant toute réservation ou exécution.

## Diagnostic du ledger

Le chemin trouvé était E:\QFSolverAgents\evidence\dynamics\node-attempt-ledger.json.

- SHA-256 historique : 20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37.
- Schéma valide pour l’ancien contrat : qfsolver-development-node-ledger-v1.
- Mandat historique : DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1.
- Mandat courant Dynamics : DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1.
- Historique : cinq tentatives sous ce ledger — trois Newmark, une harmonique réduite et une accélération de base.
- Tentatives antérieures du nodeid WP07 harmonique SDOF : zéro.

La cause était une erreur de rattachement au chemin générique, pas un JSON endommagé. Le refus du runner était correct : le mandat et l’identité du fichier existant ne correspondaient pas au scope courant. Il a eu lieu avant réservation et avant pytest.

Les scopes WP12 distincts ont des evidence roots distincts : E:\QFSolverAgents\evidence\wp07, E:\QFSolverAgents\evidence\tet4, E:\QFSolverAgents\evidence\vv-elements, E:\QFSolverAgents\evidence\wp12-elements-loads, E:\QFSolverAgents\evidence\wp12-elements-loads-corrective-r1, E:\QFSolverAgents\evidence\wp12b-hex20-affine-diagnostic-consolidated et E:\QFSolverAgents\evidence\dynamics. Le scope rotor est lui aussi séparé. D01 possède un ledger v2 distinct et son propre prédécesseur. Aucun autre scope ne partage le chemin physique du ledger Dynamics.

La correction ajoute à la politique Dynamics le fichier dédié node-attempt-ledger-wp12-dynamics-v2.json et un lien explicite vers le prédécesseur historique (chemin, SHA-256 et mandat). Le contrôleur valide les deux identités, conserve et compte les tentatives historiques dans les plafonds applicables, et refuse le mauvais schéma, mandat, nodeid, hash ou budget avant réservation. Le ledger v2 n’a pas encore été créé; le préflight et la préparation du manifeste n’ont pas touché le ledger.

## Intégration et contrôles

- PR #53, fix/wp12a-ledger-mandate-recovery : commit de correctif 35203c31dd8238c59c67fc9e93320d9ac0730ec7, fusionné au commit 148f850412c907e62ae899961afc8ce5b18d0ded.
- PR #54, docs/wp12a-ledger-controller-designation : commit de désignation e698ecb2355019f5e0190febf1613e9c30d730c8, fusionné au commit d34d1439e137958d3a97790f494d0972e1f50403.
- HEAD actuel de emptiesvoids-cloud/0.2.12 : d34d1439e137958d3a97790f494d0972e1f50403.
- L’ancien checkout épinglé n’a pas été modifié. Le nouveau checkout contrôleur est propre, détaché et désigné par AGENTS.md.
- La PR #53 a passé la CI WP12 controller / synthetic contracts, run 40662623361. Le job et tous ses pas ont réussi. Résultats locaux : 220 tests du contrat de politique PASS; suite synthétique du contrôleur 228 PASS, 0 FAIL, 0 SKIP; Ruff, py_compile, JSON et git diff --check PASS.
- PR #54 a uniquement mis à jour la désignation textuelle du contrôleur.

La règle protect-main-release renvoie à ~DEFAULT_BRANCH. Le dépôt a main comme branche par défaut; selon la syntaxe GitHub, ce jeton inclut la branche par défaut. La règle ne vise donc pas emptiesvoids-cloud/0.2.12. L’API GitHub confirme que la branche release n’est pas protégée et que la PR #53 était mergeable après la réussite de son check synthétique. Référence : [documentation GitHub des conditions de règles](https://docs.github.com/en/rest/orgs/rules).

## Identités vérifiées

### Contrôleur officiel

- Chemin : C:\Users\fari\.codex\worktrees\wp12-shared-controller-148f850\qf_solver\scripts\development_autonomous.py
- HEAD : 148f850412c907e62ae899961afc8ce5b18d0ded
- Tree : d24d73ee88b024923c14ad51ebcb3c9d99c5e4cd
- État : checkout détaché, propre.
- Fingerprint officiel : 609390083ec1d0f21ed3afe12c94bcacea14fc5d403e930c06844c401d9de9f9
- SHA-256 runner : de4405a4df9622ff6295092c7383f71ee2a91eb19877ea7a6123fa728d7062a1
- SHA-256 plugin pytest : 3011c1c311703c0a0c4df86518105ea636fc340236be79c11ab7a4d3e07cc707
- SHA-256 politique : 761809d97b7210e3d1590ae9c52d9b430f7f6b47aa0dc33026209943fba24fc2
- Runtime observé : Python 3.13.1, pytest 8.4.1, psutil 7.2.2.

### Worktree scientifique

- Chemin : E:\QFSolverAgents\wp12-dynamics
- Branche : codex/wp12-dynamic-harmonic-verification
- HEAD : 630d22b7667a0d84dd7b136b9f8c7d89ae00fc66
- Tree : a6bcf6a3cea4bdc9ab17adcf53ce2151a2bc4758
- État : propre.
- Fingerprint source courant : 969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6.
- L’inscription active append-only correspond à ce fingerprint, au même HEAD et au même nodeid. Le fingerprint historique 6db5b4597252082012fa38b1ed5cba02190562746556d5eabd1f74a256e0f8da demeure dans l’historique d’inscription; aucune preuve historique n’a été modifiée.

## Préflight collect-only

- Nodeid exact : tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames
- Préflight : pf-5b4d23fc8a97 — PREFLIGHT_PASS.
- Reçu : E:\QFSolverAgents\evidence\dynamics\worktrees\wp12_dynamics\preflight\pf-5b4d23fc8a97\preflight.json
- SHA-256 du reçu : 3244c8b4120eb1859f0996e33197f600c356d57d4ff4923086e1edfeec0daff0.
- Phase : PYTEST_COLLECT_ONLY; code de retour 0; durée 3,77 s.
- Collecte : un seul nodeid, exactement celui ci-dessus; zéro skip.
- Origine solveur attendue et observée : E:\QFSolverAgents\wp12-dynamics\src\solveur\__init__.py.
- Fingerprint source et identité science avant/après : inchangés.
- Identité contrôleur avant/après : HEAD 148f850412c907e62ae899961afc8ce5b18d0ded, tree d24d73ee88b024923c14ad51ebcb3c9d99c5e4cd.
- bodies_executed=false; attempt_reserved=false; ledger_touched=false.
- Ledger courant v2 : absent avant et après, empreinte null avant/après.
- Prédécesseur historique : 20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37 avant et après.

## Manifeste préparé

- ID : wp12a-wp07-148f850-20261028-r1.
- Chemin : E:\QFSolverAgents\evidence\dynamics\authorizations\wp12_dynamics\wp12a-wp07-148f850-20261028-r1.json
- SHA-256 : 86cd2d513d2686cd2a60f2c7d69e2757bb4473fe33322c61a84d44747c36dea2.
- État : PREPARED_NOT_AUTHORIZED.
- Décision embarquée : NOT_AUTHORIZED; aucune autorisation d’exécution n’a été créée.
- Le manifeste lie le nodeid exact, le mandat Dynamics, l’identité et le fingerprint source, le contrôleur définitif et le préflight pf-5b4d23fc8a97 avec son SHA-256.

Les artefacts de préflight et de manifeste de cette phase ont des identifiants distincts des anciens. Aucun manifeste antérieur ni reçu historique n’a été remplacé.

## Budget, ledger et décision Owner à soumettre

Inscription active :

- Sélection : 1 DDL libre UX, fixture harmonique BEAM2.
- Timeout maximal : 300 s.
- Plafond du mandat : 10 tentatives par nodeid et 130 au total, en incluant les cinq tentatives historiques du prédécesseur dans le calcul du plafond.
- Tentatives historiques de ce nodeid : 0.
- Tentatives réservées dans cette mission : 0.

La nouvelle décision Owner devrait autoriser exactement une tentative pour le manifeste ci-dessus, limitée à 300 secondes, sans retry, avec archivage complet. Elle doit référencer explicitement le nodeid, le manifeste wp12a-wp07-148f850-20261028-r1 et son SHA-256 86cd2d513d2686cd2a60f2c7d69e2757bb4473fe33322c61a84d44747c36dea2.

L’autorisation précédente se rapportait au contrôleur e420c6a, au préflight pf-ce71eff158b3 et au manifeste de SHA-256 bb2d4db337b1db5f4abff92bbfa092c57815ba69cdbd908563e8ea407917a230. Elle n’est pas transposée. Aucune tentative WP07 n’a été réservée ici et aucun calcul FEM n’a été exécuté.

Après réception de cette nouvelle décision seulement, le contrôleur pourra valider les identités et réserver l’unique tentative selon le contrat. Tout échec de validation devra refuser l’exécution. Aucun PASS de développement ne clôt WP12-A ni ne promeut une qualification.
