# WP12-S — Matrice des contrôles de sécurité

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**
Date : 2026-10-25 · Code audité : runner R2 au commit `dfab53f17d06aa752e9619a3b6b894e1fb9a2dc8`

## Légende

- **DÉMONTRÉ (synthétique)** : comportement observé uniquement sur données/processus factices.
- **PARTIEL** : mécanisme présent, mais une dépendance de confiance, couverture ou garantie manque.
- **ABSENT** : le runner ne fournit pas le contrôle.
- **OWNER_ACTION** : configuration/décision externe nécessaire.
- **BLOQUANT** : interdit une campagne tant que le point n'est pas résolu ou explicitement exclu et accepté.

## Contrôles et limites

| Domaine | Mécanisme présent | Vérification disponible | Garantie réellement fournie | Écart / risque | État avant WP12-X |
|---|---|---|---|---|---|
| Autorisation manifeste | Manifeste et décision Owner sont deux documents distincts; statut préparatoire refusé | Tests de schéma/refus synthétiques | Un manifeste `PREPARED_NOT_AUTHORIZED` ne donne pas un feu vert | N'existe pas de décision de production; `EXECUTE` reste désactivé | **DÉMONTRÉ (synthétique)**; bloquant |
| Signature | Vérification Ed25519 du payload et de l'enveloppe | Tests de signatures valides/altérées avec clés éphémères | Altération du payload/signature et clé inconnue sont détectées selon le trust keyring injecté | Aucun signataire Owner audité, aucune clé réelle provisionnée | **PARTIEL**; `OWNER_TRUST_NOT_CONFIGURED` |
| Canonicalisation | JSON UTF-8 trié, compact, `ensure_ascii=False`, NaN/Inf refusés | Tests internes de canonicalisation | Déterminisme avec l'implémentation Python testée | Pas de conformité RFC 8785 démontrée, pas de vecteur inter-langages ni d'outil de signature Owner | **PARTIEL**; décision Owner + vecteurs requis |
| Principal et clé | `key_id`, principal, hash de clé et révocation liés au trust store | Vérification unitaire avec clés synthétiques | Associe une clé de confiance à une chaîne `principal` | Le texte du principal n'est pas une fédération d'identité; son association est vérifiée hors runner | **PARTIEL** |
| Révocation et dates | Booléen de révocation; `not_before_utc` et `expires_utc` comparés à l'horloge locale | Tests synthétiques | Une clé déclarée révoquée/une décision hors intervalle est refusée | Rotation change trust store et pin; source de temps non attestée | **PARTIEL** |
| Trust root machine | Lecture directe des valeurs HKLM; chemin local hors checkout, pin SHA-256; variables de session ignorées | Test avec `winreg` simulé | Refus si HKLM/pin/bytes incohérents; aucune confiance implicite du dépôt | Les deux valeurs HKLM sont absentes sur l'hôte; ACL NTFS/registry non vérifiées par le code | **ABSENT en production**; OWNER_ACTION bloquante |
| Liaison à l'unité | Décision liée au hash manifeste, campagne, commit/tree scientifique et runner, opérations/nodeids, environnement, budgets, destination, tentative | Tests synthétiques de liaisons | Rejette les champs qui ne correspondent pas aux identités attendues par le validateur | Exécution réelle et comparaison de sélection/rapport non implémentées | **PARTIEL**; bloquant |
| Git local | Commit/tree/état propre vérifiés en VALIDATE; SYNC est explicite et sans force | Dépôt bare/local synthétique; vérification read-only du checkout | VALIDATE ne lance pas fetch; SYNC contrôle la branche via un fetch demandé | Aucun reçu SYNC GitHub dans R2; branche distante peut changer après fetch; pas une approbation | **PARTIEL** |
| Environnement | Collecte statique interpréteur/distributions/fichiers natifs détectables/threads/plateforme | Tests unitaires de collecteur | Distingue valeurs déclarées/observées/non vérifiables | DLL réellement chargées et import effectif de solveur dans l'enfant ne sont pas observés | **PARTIEL**; compléter par protocole d'exécution |
| Sélecteur/commande | SELF_TEST limité à une fixture enfant et des cas fermés | Tests synthétiques de refus de commande/nodeid | Aucune API d'exécution scientifique générique n'est exposée | La vérification de tests réellement sélectionnés et des rapports QF n'existe pas encore | **PARTIEL**; `EXECUTE` à réauditer |
| Processus Windows | Enfant factice suspendu, assigné au Job avant reprise; kill-on-close | Faux enfant et descendant | Terminaison des membres du Job à sa fermeture dans le scénario testé | Aucun enfant solveur n'a été exécuté; la frontière de fichiers est indépendante du Job | **DÉMONTRÉ (synthétique)** |
| Limites dures | Job Object : nombre maximal de processus; mémoire agrégée si la valeur est configurée; kill-on-close | Faux enfants | Limites OS supportées par les flags et valeurs explicitement appliqués | Budgets de WP12-1 nuls; pas de quota CPU dur, threads ou stockage | **PARTIEL**; bloquant selon exigences Owner |
| Supervision | Timeout wall parent; polling de RSS/CPU/espace; plafonds sur octets stdout/stderr capturés | Scénarios factices timeout/flood/memory | Détecte/interrompt certaines violations observées | Polling n'est pas une limite dure; timeout n'est pas une échéance OS; output cap ne confine pas l'enfant | **PARTIEL** |
| Protection des fichiers | Dossiers exclusifs; vérifications préalables symlink/junction; chemins de reçus sous destination prévue | Chemins temporaires synthétiques | Réduit collisions et erreurs accidentelles | TOCTOU; enfant garde les permissions du compte; aucune sandbox FS ni ACL automatique | **PARTIEL**; compte/ACL ou VM requis |
| Ledger de tentatives | JSONL séquencé, verrou, chaîne SHA-256, fsync, unicité de run et séquence | Collision, répétition, interruption/ligne incomplète, corruption testées synthétiquement | Détecte une altération si une copie de référence intacte existe; préserve FAIL | Append non atomique; un acteur en écriture peut réécrire toute la chaîne; aucun ancrage externe; pas relié à EXECUTE | **PARTIEL** |
| Reçus et archives | Empreintes SHA-256 des sorties et destinations exclusives | Vérifications de fichiers factices | Intégrité vérifiable par comparaison avec un reçu conservé indépendamment | Le reçu local peut être remplacé avec les données; aucun stockage immuable/signature externe | **PARTIEL** |
| Gestion erreurs | États de refus, échec, timeout, interruption et infrastructure distincts dans les composants | Faux enfants `exit`, `sleep`, `tree`, `flood`, `memory` | Une interruption/erreur ne se transforme pas automatiquement en PASS | Pas d'oracle scientifique ni de validation des rapports dans EXECUTE absent | **DÉMONTRÉ (synthétique)** |
| Overlays C02 / digest C01 | Manifestes prévus pour déclarer overlays et empreintes | Refus statiques et clés synthétiques | Aucun overlay n'est matérialisé et le fixture C01 n'est pas corrigé automatiquement | C02 nécessite décision + overlay exact; C01 digest demeure divergent | **OWNER_ACTION** uniquement si inclus |
| Conservation FAIL | Ledger et politique de refus d'écrasement prévus | Tests synthétiques de collisions et répétitions | Une nouvelle tentative porte un run ID et le ledger refuse réutilisation | Sans archive externe, acteur ayant accès écriture peut remplacer historique local | **PARTIEL** |

## État du registre R-01 à R-11

| R | État R2 maintenu en WP12-S | Élément restant |
|---|---|---|
| R-01 | `PARTIALLY_RESOLVED` | Provisionner trust root et revue de canonicalisation |
| R-02 | `PARTIALLY_RESOLVED` | Décider/garantir isolation et ressources réellement requises |
| R-03 | `PARTIALLY_RESOLVED` | Fermer les inventaires et scopes par unité |
| R-04 | `PARTIALLY_RESOLVED` | Compléter la provenance observée de l'environnement enfant |
| R-05 | `DEFERRED_WITH_JUSTIFICATION` | Implémenter et auditer EXECUTE sous nouvelle autorisation |
| R-06 | `PARTIALLY_RESOLVED` | Mitiger TOCTOU par permissions et stockage isolé |
| R-07 | `PARTIALLY_RESOLVED` | Ancrer les preuves hors du compte d'exécution |
| R-08 | `BLOCKED_OWNER_ACTION` | Décision de scope C01/C02 uniquement si ces tests sont retenus |
| R-09 | `DEFERRED_WITH_JUSTIFICATION` | Aucune preuve numérique n'est attendue en WP12-S |
| R-10 | `PARTIALLY_RESOLVED` | SYNC approuvé et frais avant campagne; historique R2 local seulement |
| R-11 | `PARTIALLY_RESOLVED` | Intégrer le ledger à l'orchestrateur futur et préserver l'ancre indépendante |

## Critère de sortie sécurité

Ne pas autoriser une unité scientifique sur la seule base d'un test de runner vert. Une revue d'activation doit vérifier une racine Owner réellement protégée, un manifeste figé avec toutes ses entrées, l'environnement et la sélection réellement observés, les limites dures applicables, un stockage de preuves protégé contre le compte enfant, le ledger et l'ancre externe, puis un `EXECUTE` nouvellement implémenté et revu. Aucun de ces éléments ne change les statuts WP ou la maturité scientifique.
