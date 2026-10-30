# WP12-A — Dossier de décision Owner pour le pilote

PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN

## Objet de la décision

Ce dossier prépare une décision future portant exclusivement sur l'unité WP12-1-PILOT-001-UNIT-01, campagne WP12-1-PILOT-001, et le nodeid exact :

tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form

La revue WP12-S (f2c1be4fdeef3cc041f01a4af8b5664395908491) conclut SECURITY_REVIEW_WITH_BLOCKERS. L'accord de principe courant n'est pas une décision cryptographique et n'autorise pas le lancement. Aucun document signé, aucune décision approuvée et aucun trust store Owner réel n'ont été créés.

## Identités et artefacts préparés

| Élément | Identité / état |
|---|---|
| Code scientifique | commit 00428adf38e9397340ac136f6f503a268eb671da, tree df4ec667bf746b042c900fad1f86bf542e1a437b |
| Code runner | commit a26901217826b9c5740066f1acbbc245e1a15519, tree ef0e3556c08b768642b6c3fee4d8669cbc9ecf16 |
| Manifeste pilote | [wp12_a_pilot_manifest_v1.json](wp12_a_pilot_manifest_v1.json), SHA-256 45f63db5dbe2b2cb561de484444e8771840b69d1285b9fd3d2e6ff706886fbce |
| Attestation d'isolation | [wp12_a_isolation_attestation.json](wp12_a_isolation_attestation.json), SHA-256 b1b3842bebcce5235dc0b73d13e1a3616da4ca3b9736bb18b7ab0e6c35c426b3 |
| Statut du manifeste | FROZEN_NOT_AUTHORIZED; hash calculé, non signé, non approuvé |
| Tentative | Emplacement proposé attempt-001; aucun run ID, aucune réservation de ledger et aucune tentative approuvée |
| Destination | qualification/0_2_12/wp12_evidence/WP12-1-PILOT-001/attempt-001; inexistante lors de l'inspection, ACL non sécurisées |

Le manifeste a été validé par inspection de schéma. La méthode qf-wp12-inline-fixture-v1 extrait statiquement les deux matrices littérales du nodeid, les encode en JSON UTF-8 canonique versionné, et produit SHA-256 5873637fc10c495c3cee53f41b9a3956565e07c295cb1a4b071f6dfae9dd6aff. Le fichier source du test est lié par SHA-256 9be78449948ebcdc9d577a8968b2dbacbc9b25015b4c9484ece8f91218e20d28. Ces contrôles ne lancent pas le test et ne constituent pas un résultat numérique.

## Oracle existant et portée scientifique

Le pilote reprend les assertions déjà présentes dans le test : égalité exacte de la projection à sa transposée, égalité exacte de la symétrie de la matrice d'entrée et comparaison à la forme dense par assert_allclose(rtol=2e-16, atol=2e-16). Aucune tolérance n'a été ajoutée ou modifiée. La classification est ALGEBRAIC_INVARIANT_TEST; aucune validation FEM indépendante n'est revendiquée.

## Environnement candidat et limites

L'inspection statique a observé Windows 10 build 19045, CPython 3.13.1 64-bit à C:/Python313/python.exe, sans environnement virtuel dédié. Les métadonnées installées comprennent qf-solver 0.2.10, numpy 2.2.6, scipy 1.15.2, pytest 8.4.1, cryptography 48.0.0, jsonschema 4.26.0 et psutil 7.2.2; les empreintes de bibliothèques natives présentes sont inscrites au manifeste. Le package qf-solver 0.2.10 n'établit pas quelle source le test importerait. Aucun import du solveur n'a été effectué; solver_import_origin est explicitement NOT_VERIFIED.

Le manifeste contient une commande pytest ciblée, mais sa résolution du plugin scripts.wp12_runner.pytest_provenance_plugin ne fixe pas un chemin d'import inter-checkouts ni un répertoire courant déterministe. Il faut une révision préparatoire corrigée avant qu'une décision puisse lier une commande réellement exécutable. Les variables BLAS/OpenMP inscrites sont des valeurs de profil proposées; leur application et vérification dans l'enfant ne sont pas implémentées dans le chemin scientifique actuel.

Les budgets proposés sont 120 s wall, 120 s CPU, 1 GiB mémoire, 8 processus, 1 thread, 256 MiB temporaire et 1 MiB par journal. Seul le wall, la mémoire, le nombre de processus, la terminaison Job Object et les plafonds de journaux ont un mécanisme technique observé ou testé synthétiquement dans le périmètre du runner; les tests n'établissent pas que ces plafonds ont été appliqués à un processus QF. CPU, threads et stockage sont soft. Aucun de ces budgets n'est approuvé.

## Actions Owner requises avant signature

1. Statuer sur le scope. Approuver ou refuser la répartition proposée dans l'[index R3](revisions/manifest_scope_proposal_index.r3.json), en particulier les six nodeids WP12-1 et les transferts proposés vers WP12-2/3. L'historique des neuf nodeids reste conservé; les manifestes R1/R2 ne sont pas modifiés.
2. Établir l'authenticité Owner. Provisionner par le canal administratif approuvé une clé publique et son pin/ACL hors checkout, après approbation du profil de canonicalisation et des vecteurs synthétiques. L'Owner garde sa clé privée; aucune clé ou aucun secret ne doit être transmis dans le chat.
3. Approuver l'environnement. Choisir un compte Windows standard dédié ou une VM isolée; démontrer par ACL effectives que sources/tests/archives sont en lecture seule, que seule la destination neuve est inscriptible, et que le runner ne peut modifier le trust store ou son pin.
4. Résoudre les ressources. Accepter explicitement les limites observées, fournir un environnement qui applique CPU/threads/stockage comme limites dures si requis, ou refuser ce profil. Le runner ne doit pas annoncer de garanties absentes.
5. Résoudre la commande. Figer le cwd, le chemin absolu du plugin runner, l'environnement enfant et la destination entre les deux checkouts dans une nouvelle version du manifeste; calculer son hash final après contrôle de schéma.
6. Ancrer les preuves. Définir et vérifier un stockage indépendant si l'Owner exige une protection contre la modification ultérieure des reçus/ledger.
7. Revoir le runner. Demander une revue de sécurité indépendante du chemin d'exécution effectif après son implémentation; son état courant refuse toutes les exécutions scientifiques.

Après ces actions, l'Owner devra produire une décision Ed25519 distincte liant le SHA-256 exact du manifeste révisé, les identités scientifiques et runner, la commande/nodeid, l'environnement, les budgets, la destination, la tentative unique, l'identité Owner et la fenêtre de validité. Le runner devra l'authentifier avec une racine provisionnée indépendamment du checkout. Une confirmation explicite de lancement devra être recueillie pour cette unité figée; le silence ne vaut pas approbation.

## Décision courante

Aucune approbation demandée n'est présentée comme acquise. Aucune décision signée n'existe. Le pilote ne peut pas être exécuté. Verdict WP12-A : WP12_A_BLOCKED_SECURITY. Aucun fichier wp12_a_pilot_outcome.md n'est créé.
