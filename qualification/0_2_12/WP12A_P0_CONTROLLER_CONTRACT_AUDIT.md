# WP12-A P0 — Audit du contrat de campagne

## Verdict

**Le prototype local rend la séquence groupée testable synthétiquement, mais n’est pas activé.** Le contrôleur canonique actuel refuse encore le préflight de la majorité des six cas et n’a pas le nouveau chemin batch. Les contrôles faits sur fichiers temporaires ne constituent ni des préflights, ni une réservation, ni une validation scientifique.

## Identités vérifiées en lecture seule

| Objet | Identité |
|---|---|
| Contrôleur officiel actuel | `C:\Users\fari\.codex\worktrees\wp12-controller-hex20-0d91fc5\qf_solver\scripts\development_autonomous.py` ; HEAD `0d91fc5a9bc09875526af6f17cf42c3ac666c5b7`, tree `3d57c36c948c9cc3fbc8a5d399fc465245c54a11`, fingerprint `4fdbd810091de83ff5f729edfb4b9a20b660156e60dfa136c50eab97350e6afb`. Checkout propre/détaché. |
| Sources du contrôleur courant | runner `31fd3a08b78d73e5cc6720a6b96033568a64ec21e640781a2fa069ae86df55b0`; plugin `3011c1c311703c0a0c4df86518105ea636fc340236be79c11ab7a4d3e07cc707`; politique `ffe483af5ec8dbb590c7de0a3ec875291af2d4ad3876a914e861a6a76a694bf3`. |
| Worktree scientifique | `E:\QFSolverAgents\wp12-dynamics`, branche `codex/wp12-dynamic-harmonic-verification`, HEAD `7406e34efc28ed8f18c15440115595dfa3dd9ca5`, tree `a618d0d1790ab8642f408a78b2d2856debcc60c0`, propre. |
| Mandat et capacité actifs | `DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1`, 13 nodeids enregistrés, 10 tentatives par nodeid, 130 total. Le contrôleur officiel garde son plafond de 13. |
| Ledger lu, non modifié | v2 SHA `01aec735ca1f7bfc06f4873df533089bda3f9253555911885ef5dc5b9ba9dd88`, 5 tentatives du mandat Dynamics v2 (4 PASS, 1 PYTEST_FAILED). Prédécesseur v1 SHA `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`, 5 tentatives (4 PASS, 1 PYTEST_FAILED). Total observé 10/130. |

Le préflight officiel accepte actuellement quatre anciens nodeids : Newmark, harmonique réduit, accélération complexe et WP07 harmonique. Il n’accepte aucun des six nodeids du lot proposé. Les cinq nouvelles inscriptions n’existent pas dans le registre actif ; le cas modal couplé est déjà enregistré, mais sa collecte P0 est absente de l’allowlist du préflight courant.

## Contrat implémenté dans le prototype non intégré

- Une campagne identifiée par ID sûr, six cas ordonnés exacts, chaque manifest scientifique hashé, même identité source/controller, critères existants hashés, sélection DDL et budget indépendant.
- Décision Owner séparée liée au hash exact du contrat et à la liste complète ordonnée ; les flags du template restent `execution_authorized=false`, `do_not_execute=true`.
- Snapshot ledger v2 et lien au prédécesseur historique ; sous verrou, toute entrée hors des six clés autorisées doit rester identique. Pour chaque clé, une seule tentative peut être ajoutée, dans l’ordre, avec l’identité de campagne/décision/nodeid/manifeste et fingerprints attendus.
- Verrou batch et verrou ledger détenus pendant la séquence de campagne. Chaque cas refait le préflight officiel collect-only au ledger courant, puis vérifie son reçu et son SHA immédiatement avant la réservation. La comparaison de hash au point de réservation reste activée.
- Après réservation, le runner finalise l’enregistrement. La validation attend seulement cette transition par le contrôleur et ses champs de terminaison ; elle ne traite pas la finalisation comme preuve scientifique.
- Archives indépendantes par cas : préflight, manifeste préparé, copie autorisée, run JSON, JUnit, reçu et checkpoint. En reprise, l’implémentation revalide les octets, chemins, identités, hashes, classement JUnit et chaîne de ledger avant de continuer.
- Une tentative `RESERVED` interrompue est consommée ; le batch ne la rejoue jamais. `--resume` est explicite, les tentatives déjà terminées sont reconstruites depuis leur preuve, sans re-réservation.
- Continuation après un échec scientifique limitée à un unique `<failure type="AssertionError">` dans le JUnit du seul nodeid attendu, sans erreur ou skip. Un échec de setup/infra, un JUnit absent/ambigu, un refus de préflight ou une divergence de source, critère, budget, contrôleur ou ledger arrête le lot.

Le ledger et les fichiers demeurent des preuves procédurales locales : un verrou et des SHA ne sont pas une signature cryptographique et ne protègent pas contre un processus local arbitraire qui modifie tous les fichiers. L’OS n’apporte pas ici une isolation dure de CPU, RAM ou disque. Les limites RSS et taille restent souples/échantillonnées selon le contrat courant.

## Proposition de capacité

L’augmentation 13 → 18 est présentée dans le dossier Owner, mais la branche locale contient la modification proposée seulement pour revue : aucune modification n’a été intégrée au contrôleur partagé ou à la release. Elle ajoute cinq nodeids exacts, conserve toutes les inscriptions et leurs historiques, et ne touche pas 130/10 ni les ressources. Elle ne devra devenir active qu’après approbation explicite, intégration selon les protections, tests, puis pin propre du contrôleur.

## Tests de contrat

Dans des répertoires temporaires et avec un faux contrôleur qui n’importe aucun test scientifique : enchaînement des six cas, continuation après une assertion unique, arrêt infra, mutation étrangère du ledger, ledger modifié entre préflight et réservation, modification des fingerprints/source/critères/DDL, limite totale/par nodeid, reprise entre cas, reprise refusée après `RESERVED`, refus de tentative dupliquée, et altération de manifestes/préflight/JUnit/reçu/checkpoint. Les tests directs du validateur du runner couvrent aussi le refus hors voie batch et les quatre fichiers liés par hash.

Les vrais préflights officiels, manifestes runtime, approbation d’exécution et réservations restent `NOT_RUN`. Le contrôleur actuel n’offre pas le contrat intégré; le statut est donc revue Owner/politique, pas autorisation d’exécution.
