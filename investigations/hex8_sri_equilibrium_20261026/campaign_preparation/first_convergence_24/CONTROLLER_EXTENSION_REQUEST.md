# Demande de configuration — première campagne HEX8-SRI de convergence

**Statut : `PREPARED_NOT_AUTHORIZED`.** Aucun préflight ni calcul FEM n’est demandé ou lancé dans le cadre de ce dossier.

## État contrôleur vérifié

- Branche : `codex/hex8sri-controller-registration`
- HEAD : `0d6286ecf75eea62ecafe63ec81cc816ad95226d`
- runner SHA-256 : `d73a2a4f6173d53f49d90899a8d71c112371bad7a97c350c6076f8f96327f198`
- pytest plugin SHA-256 : `c1cf6238bba05fa24de5c455beac9ddd6844935999e8b4556d3b13e5f6e9ee16`
- policy SHA-256 : `f44e167e66c00ed211d385de721883bc05d9c0db9892fc5e5fcc498d0e80693d`

Le scope `hex8sri` actuel exige six bindings exacts, autorise le fichier `tests/verification/test_hex8_sri_structural_campaign.py`, et porte un budget uniforme `180 s / 1 024 MiB RSS souple`. Le runner et la policy doivent évoluer pour accepter 24 bindings sur `test_hex8_sri_convergence.py`, une enveloppe de budget par nodeid, et six tentatives par niveau séquentiel sans augmenter la limite d’une tentative par nodeid.

## Extension minimale demandée

1. Conserver intacts D01, C01, E01 et les six anciennes inscriptions HEX8-SRI.
2. Ajouter seulement les 24 nodeids du manifeste `registration_request.json` et leur chemin/SHA exact.
3. Maintenir le contrôle d’identité, branche, baseline, origine `solveur.__file__`, manifeste, fingerprint, preflight collect-only et worktree propre.
4. Passer au child test le chemin exact du manifeste inscrit via `QF_DEV_MANIFEST_PATH`, en plus de son SHA. Le runner doit définir ce chemin depuis l’entrée enregistrée, jamais depuis une valeur libre du demandeur; le child doit refuser tout chemin hors worktree, mal nommé ou dont le SHA ne correspond pas.
5. Ne permettre aucun skip override; pas de scope générique, de module entier, ni de cible approximative.
6. Ajouter une table de budgets par nodeid, vérifiée contre le manifeste : 180 s / 512 MiB, 300 s / 1 024 MiB, 900 s / 4 096 MiB, 3 600 s / 16 384 MiB selon le maillage. RSS, temporaire et archive restent des observations souples; les limites de sortie capturée restent contrôlées par le runner.
7. Conserver une tentative par nodeid, pas de retry automatique, et limiter ce lot à 24 tentatives. Séquentialiser sous le même verrou FEM.
8. Valider les refus pour nodeid inconnu, mauvais maillage, mauvaise formulation, manifest/hash altéré, identité contrôleur/science incorrecte, préflight absent/invalide, autorisation absente et budget dépassé.

Tout changement doit rester sur la branche de configuration de recherche HEX8-SRI, sans toucher la policy partagée de production ni WP12, et recevoir une revue propre. Les identités et hashes contrôleur de ce dossier sont ceux du contrôleur actuel et deviendront provisoires dès qu’une extension sera commitée : les manifests finaux et leurs SHA doivent alors être régénérés et liés au nouveau HEAD/runner/policy/plugin.

## Préflight requis après configuration

Après implémentation et revue de l’extension, produire exactement un collect-only officiel par nodeid, sans entrer dans le corps des tests. Chaque reçu devra être accepté par le validateur final du runner. Aucun reçu de préflight n’est simulé ou déclaré valide ici.

## Dépendance d’oracle et autorisation scientifique

Le pilote 24 cas est préparé, mais le contrôleur courant ne l’inscrit pas et l’oracle 3D mixte proposé n’est ni installé, ni construit, ni qualifié. Une décision Owner doit distinguer : (a) l’approbation d’une extension isolée du contrôleur et des préflights collect-only; (b) l’autorisation d’exécution de la matrice HEX8/SRI; (c) la campagne FEM distincte de qualification de l’oracle P2/P1. Les préflights ne constituent pas une autorisation de calcul. Aucun manifeste brouillon ne doit être converti en autorisé avant le gel des critères, des identités et de l’oracle utilisé.
