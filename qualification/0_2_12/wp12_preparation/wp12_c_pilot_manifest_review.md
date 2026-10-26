# WP12-C — Revue du manifeste pilote v4

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Révision préparée

Le manifeste historique v3 [reste inchangé](wp12_b_pilot_manifest_v3.json). La révision v4 est un nouveau fichier, [wp12_c_pilot_manifest_v4.json](wp12_c_pilot_manifest_v4.json), pour l'unité `WP12-1-PILOT-001-UNIT-01`. Elle autorise sur le papier un seul nodeid :

`tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`

La révision cible distinctement le code scientifique `00428adf38e9397340ac136f6f503a268eb671da` / `df4ec667bf746b042c900fad1f86bf542e1a437b` et le code runner `f9707fdcab3fad2104345085c22db7f7c007567b` / `d813ecef91a2299d5fd5f99538ce1323ec7512a7`. Le checkout runner séparé se trouve à `E:\QFSolverWP12B\runner-wp12-c`; l'ancien checkout `E:\QFSolverWP12B\runner` a été conservé à son identité historique.

Le manifeste v4 a été validé contre `wp12_execution_manifest_v4.schema.json`. Les empreintes couvrent les octets réellement présents dans les deux checkouts désignés : le worktree Windows du runner restitue des fins de ligne CRLF, contrairement au checkout de développement, malgré le même commit/tree. Les hashes runner ont donc été calculés depuis le chemin d'exécution du manifeste. Les 144 empreintes runner, source, test et fixture ont toutes concordé avec leurs chemins déclarés. L'empreinte du manifeste préparé est :

`09ae6021f1248f4210ede7e42446fc44c7e5c048233239e91c06064e2c7f6c27`

Les données inline restent identifiées selon `qf-wp12-inline-fixture-v1`; le hash du fichier de test est lié séparément. Les assertions et tolérances proviennent du test existant, sans nouveau seuil.

## État d'autorisation

Le statut reste `FROZEN_NOT_AUTHORIZED`, `authorization_reference.status=OWNER_DECISION_REQUIRED`, et l'attestation d'exécution reste `NONE`. Aucun fichier de décision Owner, aucune signature, aucun trust root réel et aucune clé de production n'ont été créés. Le SHA ci-dessus identifie seulement le contenu préparé; il n'est pas une approbation.

Le manifeste n'est pas prêt à autoriser un lancement : l'évaluation d'isolation reste `NOT_VERIFIED`, l'ancrage d'archive `NOT_CONFIGURED`, le compte runner dédié n'est pas provisionné et le worker protégé n'est pas intégré à un superviseur scientifique. L'entrée scientifique de `pilot_execution.py` demeure refusée. Le profil Windows de l'hôte reste sous le seuil de politique inscrit dans les scripts. Ces conditions doivent être résolues et revues avant toute décision finale; la validation JSON et les empreintes statiques ne remplacent pas ces contrôles.

Le manifeste v4 ne doit pas être modifié après toute future signature. Toute correction exige une nouvelle révision et un nouveau SHA. Une décision liée au manifeste v3 ou à un autre commit runner ne couvre pas cette révision.

## Contrôles effectués

- Schéma JSON Draft 2020-12 : valide.
- Identités science/runner : deux commits et arbres distincts.
- Nodeid : unique et exact; aucune invocation de pytest effectuée pendant cette revue.
- Empreintes runner, sources, test et fixture : 144/144 vérifiées statiquement sur les checkouts déclarés.
- Destination : une tentative dédiée; état d'isolation explicitement non vérifié.
- Tentatives : maximum 1, sans relance automatique.
- Autorisation Owner, signature et exécution scientifique : absentes / non autorisées.
