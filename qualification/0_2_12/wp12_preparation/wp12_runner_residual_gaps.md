# WP12-R — Registre des écarts résiduels

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

> Snapshot de WP12-R conservé pour traçabilité. Les statuts courants après WP12-R2 sont dans l'addendum ci-dessous.

| ID | Écart | Effet | Requis avant WP12-1 | Statut |
|---|---|---|---|---|
| R-01 | Aucune racine de confiance Owner n'est configurée; la structure Ed25519 n'est pas une authentification. | Une décision JSON ne peut pas autoriser un processus. | Provisionner une clé publique vérifiable hors du checkout, définir payload canonique, vérification, révocation et rotation; revue indépendante. | Bloquant; EXECUTE désactivé. |
| R-02 | Pas de Job Object Windows ni d'environnement équivalent avec plafond dur CPU/mémoire/processus/stockage. | Les mesures psutil sont périodiques et souples; aucune protection forte des archives par le processus enfant. | Choisir et valider un hôte/container/Job Object approprié; démontrer limites et arrêt des descendants avec processus factices dédiés. | Bloquant pour exécuter des campagnes. |
| R-03 | Manifestes WP12-1 à WP12-4 ont des entrées de fichiers sans Git blob OID; WP12-3 contient aussi un nodeid dupliqué. WP12-5 est un plan sans nodeid/scénarios et WP12-6 n'a pas de commit/tree gelé. | Les unités ne sont pas identifiées de manière reproductible; VALIDATE signale l'incomplétude. | Préparer des manifestes unitaires complets après décision Owner, sans réécrire silencieusement les manifestes historiques. | Bloquant par unité. |
| R-04 | Pas d'inventaire complet de provenance de l'environnement (wheel/package solver, NumPy/SciPy, BLAS natives, threads, modèles/maillages). | Une future preuve ne pourrait pas être liée au binaire/exécutable physique réel. | Ajouter des collecteurs read-only et les lier au manifeste figé; contrôler le vrai chemin d'import avant de lancer un test. | Bloquant pour campagne. |
| R-05 | L'implémentation présente n'exécute que des cas factices; aucune orchestration d'unité scientifique, vérification JUnit de tests lancés, ressource dure ou reçu signé n'est disponible. | Les résultats SELF_TEST valident seulement des comportements locaux du runner. | Après R-01/R-02, faire une revue d'architecture et une mise en œuvre/test distincts d'EXECUTE, puis nouvelle décision Owner. | Bloquant. |
| R-06 | Contrôles de symlink/junction basés sur des vérifications de chemin préalables; une course locale reste possible. | Pas de confinement de fichiers contre un acteur concurrent. | Exécuter uniquement sous un compte/session isolé avec stockage dédié; utiliser API de fichiers sans-follow/permissions si le risque le requiert. | Bloquant si l'intégrité d'archives dépend du confinement local. |
| R-07 | Les hashes/sidecars sont auto-calculés et non signés/stockés immuablement. | Ils détectent une modification après réception, mais un acteur ayant le même accès peut remplacer sortie et reçu. | Ancrer les reçus dans un stockage immuable ou signature externe vérifiable et archiver les sorties brutes. | À décider selon le modèle d'assurance avant campagne. |
| R-08 | C02 nécessite un overlay temporaire du helper historique absent du tree; C01 R19 a un digest divergent dans le dossier WP12-0. | Ces unités doivent être refusées jusqu'à résolution explicite; aucun fichier historique ne sera modifié. | Décision Owner séparée, vérification OID/SHA, isolation overlay; pour C01 trancher l'identité normative du fixture. | Bloquant seulement si ces contrôles sont inclus dans la campagne. |
| R-09 | Aucun résultat numérique courant, preuve de non-régression QF, résultat rotor ni benchmark n'est produit par WP12-R. | La préparation du runner ne ferme aucune revendication scientifique de WP12. | Exécuter les campagnes futures seulement après approbation; conserver FAIL, NOT_RUN et INCONCLUSIVE. | WP12 reste OPEN. |
| R-10 | VALIDATE contrôle la branche/commit/tree présents localement, mais ne rafraîchit pas le remote et ne vérifie pas une relation d'ascendance au tip distant. | Une référence de suivi locale périmée ou une branche distante concurrente pourrait ne pas être détectée par une future activation locale. | Avant activation, définir une référence distante approuvée, l'actualiser par un canal contrôlé et inclure le statut d'ascendance dans le contrat; aucun fetch automatique en mode VALIDATE. | Bloquant pour une campagne nécessitant un candidat courant au distant. |
| R-11 | Aucun ledger durable de tentatives campagne/unité n'est encore intégré; le gate reçoit un compte de tentatives mais le mode EXECUTE actuel est désactivé. | Une future activation ne doit pas réutiliser le compte statique du prototype ni masquer une tentative passée. | Concevoir/faire approuver un ledger append-only lié au SHA manifeste et à chaque run id; chaque relance doit avoir une nouvelle unité/tentative approuvée. | Bloquant avant activation d'EXECUTE. |

Ce registre ne classe pas l'absence de preuve comme un défaut mécanique. Il précise les prérequis d'exécution, d'intégrité et de provenance.

## Addendum WP12-R2 — 2026-10-25

Ce tableau remplace les statuts de travail pour le suivi du runner à partir de R2; il ne supprime pas l'état R1 ci-dessus. `PARTIALLY_RESOLVED` ne signifie pas autorisé. `BLOCKED_OWNER_ACTION` est conditionnel aux cas C01/C02 de WP12-3.

| ID | Statut WP12-R2 | Observation et réserve |
|---|---|---|
| R-01 | `PARTIALLY_RESOLVED` | Vérificateur Ed25519 et trust loader HKLM présents; aucune clé réelle ni trust store machine configuré. `EXECUTE` refuse. |
| R-02 | `PARTIALLY_RESOLVED` | Job Object Windows impose et teste processus actifs, mémoire agrégée et kill-on-close sur faux enfants. La sonde de quota CPU dur a échoué au timeout wall et a été retirée; aucun sandbox FS, plafond de threads/stockage ou compte dédié n'est fourni. |
| R-03 | `PARTIALLY_RESOLVED` | Révisions R2 WP12-1..4 complètent les OID/SHA pour le scope résolu; les changements de chemins proposés restent à approuver. Inline fixtures non matérialisées; WP12-5 harness/scénarios chiffrés et WP12-6 identité finale encore à résoudre. |
| R-04 | `PARTIALLY_RESOLVED` | Collecte statique d'environnement et d'identités implémentée sans import scientifique; libraries réellement chargées et chemin d'import du processus futur non observables. |
| R-05 | `DEFERRED_WITH_JUSTIFICATION` | Aucune orchestration scientifique n'est activée; activation incompatible avec la restriction R2. Nouvelle revue/autorisation requise. |
| R-06 | `PARTIALLY_RESOLVED` | Contrôle de reparse/symlink et `mkdir` exclusif, garde du ledger et refusions testés; TOCTOU et permissions de fichiers du compte subsistent. |
| R-07 | `PARTIALLY_RESOLVED` | Chaîne hash du ledger et reçus sont vérifiables, mais pas physiquement immuables ni ancrés à l'extérieur. |
| R-08 | `BLOCKED_OWNER_ACTION` | Inclusion C02 exige décision et overlay exact isolé; l'écart C01 reste inchangé et exige décision d'identité. Aucune correction ou matérialisation automatique. |
| R-09 | `DEFERRED_WITH_JUSTIFICATION` | Pas de preuve numérique actuelle attendue en WP12-R2; tous résultats WP12 restent NOT_RUN et WP12=OPEN. |
| R-10 | `PARTIALLY_RESOLVED` | SYNC explicite à refspec non forcé, testé sur bare Git local; aucune sync GitHub R2 et aucune garantie de fraîcheur après le fetch. |
| R-11 | `PARTIALLY_RESOLVED` | Ledger verrouillé/hash-chain/fsync, états incomplets, répétitions et tentatives distinctes testés; l'intégration au futur EXECUTE et l'archivage externe restent absents. |

Voir [revue sécurité WP12-R2](wp12_r2_runner_security_review.md) et l'[index des révisions de manifestes](revisions/manifest_revision_index.json). Aucun statut scientifique ni statut WP n'est modifié.
