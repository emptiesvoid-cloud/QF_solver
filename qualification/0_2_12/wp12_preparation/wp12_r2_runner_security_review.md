# WP12-R2 — Revue sécurité, prérequis et écarts du runner

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Résumé

WP12-R2 sépare l'identité du code scientifique de celle du runner, ajoute un vérificateur de décision Owner Ed25519, un contrôle Windows Job Object pour les processus factices, un ledger hash-chain des tentatives, une collecte statique de provenance et un mode explicite de synchronisation de la branche distante. Les tests utilisent exclusivement des clés éphémères, des dépôts Git locaux factices et des programmes factices.

La politique reste `DENY_EXECUTION`. Aucun trust store machine n'est actuellement configuré; le vérificateur cryptographique ne reçoit aucune clé Owner de production. Les manifestes de WP12-0 et leurs révisions restent non autorisés. Aucun calcul, solveur, test QF Solver, replay historique ou benchmark n'a été exécuté.

## Identités Git et périmètre

Au début de WP12-R2, le HEAD local et `origin/emptiesvoids-cloud/0.2.12` étaient tous deux `ee58cb9b700380e07505f7884c4ea93faaebd0af`, tree `373a8334216995ecf63988f5b51fdaf0e55a36eb`; le checkout était propre. Le code scientifique de référence des manifestes WP12-0 reste commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.

Les décisions distinguent :

| Identité | Sens |
|---|---|
| `scientific_identity` | Commit/tree exact du candidat dont les routes mécaniques sont visées. |
| `runner_identity` | Commit/tree du code de contrôle, distinct du candidat scientifique lorsqu'un overlay ou une infrastructure plus récente est utilisé. |

Le vérificateur lie les deux identités à la décision signée. L'identité scientifique demeure la référence WP12-0; l'infrastructure de runner ajoutée en R2 ne modifie aucune source de solveur. Le HEAD et le tree du commit R2 final seront inscrits dans le reçu de livraison Git, après le commit.

## Chaîne de confiance Owner

### Option retenue : Ed25519 avec racine machine indépendante

La décision Owner v2 est un document distinct du manifeste. Elle lie l'identifiant de campagne, le SHA-256 exact du manifeste, l'identité scientifique, l'identité runner, les opérations, nodeids, environnement, budgets, tentatives, destination, principal Owner et intervalle de validité. La signature Ed25519 porte sur l'objet JSON privé de son enveloppe `signature`, encodé en UTF-8 avec clés triées, séparateurs compacts `,` et `:`, sans NaN/Inf. L'enveloppe comprend `key_id`, l'empreinte de la clé publique, l'empreinte du payload et la signature base64.

Sur Windows, le runner lit le chemin du trust store public et son SHA-256 attendu directement sous `HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`. Il ignore les variables d'environnement de session. Le trust store doit être hors checkout, non symlink/junction, correspondre au pin machine et contenir la clé connue, son principal et son éventuel statut de révocation. La clé privée reste exclusivement sous contrôle Owner; aucun secret n'est inclus dans le dépôt, le chat ou le runner.

Cette chaîne n'est pas encore provisionnée. Un administrateur local peut modifier le registre machine et le fichier public; le modèle suppose donc que les administrateurs de l'hôte sont de confiance. Le runner ne vérifie pas les ACL NTFS de bout en bout. Il faut faire exécuter les campagnes sous un compte standard dédié qui ne peut ni écrire le trust store ni modifier le pin machine. Une décision signée ne remplace pas les contrôles d'identité, d'entrées, d'environnement ou de ressources.

Le vérificateur valide aussi `not_before_utc` et `expires_utc` avec l'horloge locale. L'heure système n'est pas attestée par une source de temps externe; une dérive importante reste un risque. La rotation/révocation s'effectue par mise à jour administrative du trust store public et de son pin, jamais en récupérant une nouvelle clé depuis le checkout.

### Option GitHub protégée

La branche `emptiesvoids-cloud/0.2.12` ne dispose pas d'une protection de branche détectée lors de la lecture seule (réponse GitHub : branche non protégée). Un ruleset actif nommé `protect-main-release` a été observé, mais aucune règle consultée ne démontre qu'il couvre la branche 0.2.12. Une signature de commit ordinaire ou un JSON présent dans une branche ne suffit pas à authentifier l'approbation. Un GitHub Environment avec réviseurs obligatoires serait une autre voie, mais il n'a pas été configuré ni validé dans cette mission.

| Critère | A — Ed25519 hors checkout | B — Décision GitHub protégée |
|---|---|---|
| Sécurité réelle | Forte si l'Owner garde la clé privée et si le pin HKLM/ACL sont protégés. | Forte si l'environnement/repository policy impose réellement les réviseurs et si le runner vérifie cette source authentifiée. |
| Simplicité / maintenance | Vérification locale simple; gestion Owner de clé, expiration, rotation et révocation requise. | Dépend des permissions GitHub, de la politique d'environnement et d'un client/API de vérification. |
| Windows / hors ligne | Vérification hors ligne après provisionnement; compatible Windows. | Récupération réseau et identité du compte/connecteur nécessaires. |
| État constaté | Vérificateur implémenté; trust root absente. | Protection de la branche cible non démontrée; aucune décision accessible/configurée. |
| Décision R2 | **Recommandée**, sous condition de provisionnement et d'une revue Owner indépendante. | Non retenue dans cette étape. |

`EXECUTE` reste désactivé même si une décision synthétique ou future est valide. Il n'existe pas de flag de forçage. La validation cryptographique n'est donc pas une autorisation de campagne.

## Processus Windows et ressources

Sur Windows, `SELF_TEST` lance les processus factices suspendus, crée un Job Object, applique `KILL_ON_JOB_CLOSE` et un plafond du nombre de processus actifs, assigne l'enfant au Job, puis reprend son thread principal. Un scénario factice démontre un plafond mémoire agrégé. Une erreur de création, de configuration ou d'assignation empêche le lancement du processus.

Les contrôles durs réellement fournis par cette implémentation du Job Object sont : processus actifs, mémoire agrégée si une limite est spécifiée et terminaison des membres du Job à sa fermeture. Le superviseur surveille en plus le temps wall et les tailles stdout/stderr. Le polling RSS et le suivi du stockage restent des observations périodiques; il n'y a pas de quota CPU dur, de plafond de stockage ou de nombre de threads.

Un premier essai synthétique a tenté un plafond de temps CPU Job Object; le faux enfant a atteint le timeout wall sans que la limite CPU soit démontrée. Le chemin CPU non démontré et son cas de test ont été retirés. Cet échec de sonde reste un constat, pas un résultat PASS; toute exigence `cpu_seconds` future nécessite un confinement externe prouvé ou une nouvelle implémentation et des essais factices dédiés.

Un Job Object ne sandboxe pas le système de fichiers et ne protège pas des archives auxquelles le même compte peut écrire. Les contrôles de chemins exclusifs et de symlinks/junctions sont des barrières contre erreurs/collisions, pas un confinement contre un acteur concurrent. Avant campagne, choisir un compte standard dédié, un répertoire d'évidence neuf et des ACL qui interdisent à l'enfant d'écrire dans les archives historiques. Si un plafond dur de stockage, de threads ou une isolation de fichiers est exigé, fournir un conteneur/VM/compte cloisonné vérifié ou refuser l'exécution.

## Ledger et reçus

`AttemptLedger` conserve les événements de début et de fin avec campagne, manifest SHA-256, run ID, nodeid, tentative, commit/tree, horodatages, statut/raison, hashes de journaux et d'évidence. Le fichier JSONL est verrouillé, chaque événement comporte un numéro de séquence et le hash du précédent, puis le flux est vidé avec `fsync`. Une ligne partielle, un hash incohérent, un run ID dupliqué, une tentative non séquentielle, une tentative toujours ouverte ou une seconde clôture est refusée. Une tentative interrompue doit d'abord être réconciliée comme `INTERRUPTED` avant de créer un nouveau run ID.

Il s'agit d'un append-only **logique**, pas d'une immutabilité physique. Un acteur disposant du même accès en écriture peut remplacer le ledger et recalculer sa chaîne. Un stockage externe immuable ou un ancrage signé est nécessaire si le modèle de preuve l'exige. Les reçus SHA-256 restent également non signés.

## Provenance d'environnement

Le collecteur statique observe le binaire/interpréteur Python, la version, `sys.prefix`/`base_prefix`, la plateforme, l'architecture, les versions et chemins de métadonnées des distributions, les fichiers natifs `.dll`/`.pyd`/`.so`/`.dylib` recensés dans les distributions NumPy/SciPy, les variables de threads et les SHA-256 des sources, tests et fixtures déclarés. Il ne fait aucun import de `solveur`, `qf_solver`, NumPy ou SciPy.

Les métadonnées de distributions ne démontrent pas quelles bibliothèques natives un futur processus chargera réellement. Le chemin réel d'import du solveur et BLAS/LAPACK actif restent non vérifiables sans instrumentation exécutée dans l'enfant approuvé. Les éventuels overlays restent des entrées distinctes et ne sont jamais assimilés au tree Git.

## Synchronisation distante

VALIDATE ne fait aucun fetch. Le mode distinct `SYNC` vérifie l'URL attendue d'`origin`, récupère seulement la branche cible par refspec non forcé, vérifie l'ascendance du HEAD local et écrit un reçu informatif. Une divergence/non-fast-forward arrête la synchronisation. SYNC a été testé uniquement contre un dépôt bare local factice; il n'a pas été exécuté sur GitHub pendant R2. Ce reçu établit l'état observé au moment du fetch, mais ne constitue pas une approbation Owner et ne garantit pas que le distant restera immobile après la synchronisation.

## Révisions des manifestes

Les six fichiers WP12-0 originaux restent inchangés. Chaque fichier `revisions/wp12_*_execution_manifest.r2-prepared.json` conserve `PREPARED_NOT_AUTHORIZED`, le commit/tree scientifique de référence et un lien vers le SHA-256 de l'original. Les révisions 1–4 complètent les OID/SHA des fichiers statiquement résolus; les chemins inexistants sont résolus vers des candidats observés dans le tree mais marqués comme changements de périmètre à approuver. Les nodeids WP12-3 dupliqués sont dédupliqués dans la nouvelle révision et consignés. L'écart de digest C01 et l'exigence d'overlay C02 sont maintenus.

WP12-5 ne contient que des scénarios proposés sans valeur, seuil ou budget inventé. WP12-6 conserve commit/tree prospectifs jusqu'à la réception et la consolidation des campagnes antérieures. Les hashes de contenu inline non matérialisés, l'approbation des remplacements de chemins et les paramètres de performance restent à résoudre avant un freeze.

## Registre R-01 à R-11 après R2

| ID | État WP12-R2 | État vérifiable / limite |
|---|---|---|
| R-01 | `PARTIALLY_RESOLVED` | Vérificateur Ed25519 canonique, liaison manifeste/campagne/source/runner, expiration/révocation; aucune clé Owner réelle ni trust store HKLM provisionné. Bloquant. |
| R-02 | `PARTIALLY_RESOLVED` | Job Object Windows implémenté/testé avec faux enfants pour processus actifs, mémoire agrégée et kill-on-close; quota CPU dur non démontré et retiré, sans confinement FS/stockage/threads. Bloquant si l'un de ces plafonds est exigé. |
| R-03 | `PARTIALLY_RESOLVED` | Révisions 1–4 ont inventaires Git OID/SHA-256 pour fichiers résolus; plusieurs remplacements demandent revue de périmètre. WP12-5 sans harness/valeurs; WP12-6 prospectif; contenus inline non résolus. Bloquant par unité. |
| R-04 | `PARTIALLY_RESOLVED` | Collecteur statique Python/distributions/fichiers natifs connus/threads/entrées; bibliothèques réellement chargées et import du solveur enfant non observables sans instrumenter l'exécution. |
| R-05 | `DEFERRED_WITH_JUSTIFICATION` | Aucun orchestrateur scientifique n'est activé; `EXECUTE` refuse dans WP12-R2. Activation nécessite architecture et autorisation distinctes après R-01/R-02 et revue Owner. |
| R-06 | `PARTIALLY_RESOLVED` | Revalidation des chemins, refus de collision et ledger protégé contre symlinks détectés; courses locales et accès FS de l'enfant demeurent. |
| R-07 | `PARTIALLY_RESOLVED` | Ledger hash-chain verrouillé et reçu SHA-256 détectent des altérations si référence conservée; accès en écriture permet de réécrire/recalculer. Ancrage externe absent. |
| R-08 | `BLOCKED_OWNER_ACTION` | Aucun overlay C02 matérialisé; aucun changement automatique du digest C01. Owner doit choisir l'inclusion et résoudre l'identité avant ces cas. |
| R-09 | `DEFERRED_WITH_JUSTIFICATION` | Aucun résultat numérique attendu dans R2; WP12 reste OPEN et les preuves historiques ne sont pas promues. |
| R-10 | `PARTIALLY_RESOLVED` | Mode SYNC explicite sans force et test local bare; pas de sync GitHub R2, le reçu n'est pas une approbation et une course distante post-fetch reste possible. |
| R-11 | `PARTIALLY_RESOLVED` | Ledger append-only logique avec verrou, chaîne, fsync, limites de reprises et tests de collision/interruption/corruption; pas de backing externe immuable ni intégration à EXECUTE. |

## Activation future de WP12-1 : préconditions ordonnées

1. **OWNER_ACTION_REQUIRED — provisionner la racine Ed25519** décrite ci-dessous; vérifier que l'empreinte HKLM correspond au fichier public et que le compte runner ne peut pas modifier le registre ni le fichier.
2. Owner revoit les remplacements de chemins dans les révisions WP12-1 et approuve le scope exact; les bytes des deux fixtures inline sont gelés par une méthode déterministe avant de signer.
3. Réviser et figer une nouvelle unité WP12-1 avec le SHA-256 du manifeste, les OID/SHA complets, les nodeids développés exacts, les versions d'environnement et les ressources. Aucun seuil scientifique ne peut être ajouté sans contrat ou décision.
4. Le runner dédié reçoit une identité distincte; vérifier le commit/tree scientifique et le commit/tree runner, un checkout propre, les entrées et un reçu SYNC frais du distant approuvé.
5. Owner signe une décision v2 distincte pour exactement cette unité, cette commande/nodeid, cet environnement, ces budgets, cette destination et cette tentative.
6. Revue de sécurité séparée: compte standard dédié, ACL de preuves, confirmation du Job Object et décision explicite sur stockage/threads non limités. Si le scope exige ces limites, rester bloqué ou utiliser un hôte isolé qui les impose.
7. **Nouvelle implémentation/révision obligatoire** pour le mode scientifique `EXECUTE`; R2 garde un refus inconditionnel. Après revue et nouvelle décision Owner, lancer une seule unité approuvée. Aucun PASS n'est déduit du code retour seul; sélection réelle, rapport et oracles doivent concorder.

## OWNER_ACTION_REQUIRED — préparation du trust store

**Action exacte :** provisionner la clé publique Ed25519 Owner et son pin sous HKLM; garder la clé privée hors du dépôt et du chat.

**Pourquoi :** le vérificateur est présent mais n'a pas de racine indépendante. Tant que ces valeurs machine n'existent pas, toute décision reste non authentifiée et `EXECUTE` refuse.

**Étapes :**

1. Owner génère une paire Ed25519 sur son poste de confiance. Conserver la clé privée dans son gestionnaire matériel/secret ou support hors ligne; ne la copier ni dans le dépôt, ni dans les logs, ni dans le chat.
2. Créer un fichier public `C:\ProgramData\QFSolver\wp12-owner-trust.json`, hors du checkout, de forme :

   ```json
   {
     "schema": "qf-wp12-owner-trust-store-v1",
     "keys": [
       {
         "key_id": "<identifiant stable>",
         "principal": "<identité Owner vérifiable>",
         "public_key_base64": "<32 octets Ed25519 encodés en base64>",
         "revoked": false
       }
     ]
   }
   ```

3. Protéger le fichier par ACL NTFS : SYSTEM et administrateurs de confiance peuvent l'administrer; le compte standard utilisé pour le runner peut le lire mais pas le modifier. Ne pas exécuter les campagnes depuis un compte administrateur.
4. Dans `regedit`, sous `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment`, créer deux valeurs de type `REG_SZ` : `QF_WP12_TRUST_STORE` = chemin absolu du fichier; `QF_WP12_TRUST_STORE_SHA256` = SHA-256 en minuscules des octets exacts du fichier. Seul un administrateur de confiance doit pouvoir modifier cette clé machine.
5. Vérifier depuis une session d'administration :

   ```powershell
   Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment' -Name QF_WP12_TRUST_STORE,QF_WP12_TRUST_STORE_SHA256
   Get-FileHash 'C:\ProgramData\QFSolver\wp12-owner-trust.json' -Algorithm SHA256
   Get-Acl 'C:\ProgramData\QFSolver\wp12-owner-trust.json' | Format-List
   icacls 'C:\ProgramData\QFSolver\wp12-owner-trust.json'
   ```

6. Soumettre seulement la clé publique, son empreinte, l'identité exacte du principal, le résultat ACL et la preuve du pin HKLM pour revue. Ne transmettre aucune clé privée ou token.

**Prérequis :** Owner contrôlant une identité de signature et administrateur de l'hôte; compte runner non administrateur; chemin et ACL approuvés. Le runner n'installe pas ces paramètres.

**Résultat attendu :** le même utilisateur runner peut lire le trust store mais ne peut ni le réécrire ni modifier son pin; `load_machine_trust_store()` retrouve les octets dont le hash correspond exactement à HKLM. Une future décision signée est vérifiée contre cette clé.

**Risque si omis :** aucune décision ne s'authentifie; toutes les campagnes restent refusées. Même configuré, ce mécanisme ne protège pas d'un administrateur local malveillant; pour ce risque, utiliser un hôte d'exécution isolé et une racine maintenue hors de sa portée.

Ce document est une préparation et une revue de sécurité du runner; il ne clôt ni WP12-R2 ni WP12.
