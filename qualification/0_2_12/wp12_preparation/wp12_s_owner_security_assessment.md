# WP12-S — Revue de sécurité Owner

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**
Révision : 2026-10-25 · Branche de référence : `emptiesvoids-cloud/0.2.12`

## Verdict

**`SECURITY_REVIEW_WITH_BLOCKERS`**

Le runner R2 met en place des contrôles utiles et vérifiables pour les manifestes, les décisions signées, les processus factices et les reçus. Il n'existe toutefois ni racine Owner réellement provisionnée sur cet hôte, ni orchestration scientifique activable, ni confinement suffisant des fichiers et ressources pour autoriser une campagne. Le manifeste WP12-1 R2 conserve en outre des champs non résolus et mélange des vérifications de périmètres différents.

Ce verdict autorise une revue Owner de ce dossier. Il n'autorise aucune campagne, ne vaut pas approbation Owner et ne constitue pas une qualification du solveur.

## Identités vérifiées

| Identité | Valeur observée | Portée |
|---|---|---|
| Checkout dédié local | commit `459228bc136044591201d85f26ac1622d814aa2a`, tree `3cd3b2abe6a4536b41c6309a32f6d299327e8b4d`, propre | Référence de cette revue |
| Branche distante | `origin/emptiesvoids-cloud/0.2.12` au même commit `459228bc136044591201d85f26ac1622d814aa2a` | Vérifié par `git ls-remote`; aucun fetch implicite |
| Identité scientifique préparée | commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b` | Candidat fixé par WP12-0/R2; `src/` ne diffère pas de cette référence |
| Code runner | dernier commit qui modifie `scripts/wp12_runner/` : `dfab53f17d06aa752e9619a3b6b894e1fb9a2dc8`, tree `490ac64c28485654f657ad382464cbe00cec2a38` | Référence des modules runner; aucun changement runner après ce commit |

Les modifications documentaires postérieures au commit runner ne sont pas une modification de la physique. Pour une future décision, l'identité complète du checkout d'exécution et l'identité précise du code runner devront être enregistrées séparément. Le dossier parent au-dessus du checkout dédié avait des modifications non commises dans deux tests E01 et un checkout imbriqué non suivi; ces éléments n'ont pas été touchés. La revue et ses changements sont confinés au dépôt Git dédié.

## Chaîne de confiance Owner

La décision Owner est séparée du manifeste. Le validateur vérifie le schéma, la signature Ed25519, le principal lié à la clé, l'identifiant de clé, sa révocation, les dates de validité et les liaisons à la campagne, au SHA-256 du manifeste, aux identités scientifique et runner, aux opérations, commandes/nodeids, ressources, environnement et destination. Le manifeste ne peut donc pas s'auto-autoriser par un simple champ `APPROVED`.

Le CLI lit le chemin du trust store public et son pin SHA-256 depuis HKLM, hors des variables de session. Il exige un chemin local hors checkout et refuse les symlinks/junctions détectés. Cette chaîne n'est pas configurée sur la machine examinée : les deux valeurs HKLM `QF_WP12_TRUST_STORE` et `QF_WP12_TRUST_STORE_SHA256` sont absentes. Aucune clé de production ni décision Owner réelle n'a été créée ou utilisée. Le statut est **`OWNER_TRUST_NOT_CONFIGURED`**.

La présence d'un nom de principal dans le trust store ne prouve pas à elle seule une identité civile ou organisationnelle : cette association relève de la vérification Owner hors runner. Le validateur ne contrôle pas les ACL NTFS effectives du fichier ou du registre. Il suppose que les administrateurs locaux qui possèdent le pin sont de confiance. Les dates sont comparées à l'horloge locale, qui n'est pas attestée par le runner.

La fonction de sérialisation produit un JSON UTF-8 compact à clés triées, sans NaN/Inf. Le code décrit cette représentation comme « RFC-8785-like », pas comme une implémentation certifiée de RFC 8785. Aucun outil de signature Owner audité ni vecteur interopérable n'est fourni. Avant une signature réelle, l'Owner doit choisir et tester une règle de canonicalisation commune au signataire et au vérificateur. Les signatures de tests utilisent des clés éphémères et ne sont pas des preuves d'approbation réelle.

## Garanties d'exécution réellement obtenues

| Contrôle | Garantie démontrée | Limite à conserver |
|---|---|---|
| Mode scientifique `EXECUTE` | Refus inconditionnel dans R2; `REAL_EXECUTION_ENABLED=False`; aucune commande de solveur n'est lancée | Le chemin d'orchestration scientifique et la vérification d'un rapport de campagne n'existent pas |
| Processus factices Windows | Démarrage suspendu, affectation au Job avant reprise, fermeture du Job avec terminaison de ses membres; quota dur du nombre de processus actifs; quota mémoire Job dur lorsqu'une valeur est fournie | Démontré sur faux enfants seulement. Aucun sandbox fichier ni protection contre un administrateur local |
| Temps et sorties | Timeout wall surveillé par le parent; plafond d'octets pour les journaux capturés | Le timeout n'est pas une échéance OS; le plafond des journaux ne borne pas toutes les écritures du processus |
| CPU, threads, RSS et stockage | Certaines mesures peuvent être observées/pollées | Aucun plafond CPU, threads ou stockage dur. Le polling RSS n'est pas une limite mémoire dure |
| Chemins de preuve | Répertoires exclusifs et reçus hachés; refus de collisions et détection préalable de symlink/junction | Vérifications sujettes à une course TOCTOU; pas de restriction des accès du processus enfant |
| Ledger | JSONL séquencé, verrouillage, chaîne SHA-256, fsync; collisions, répétitions et lignes finales incomplètes refusées | Append non atomique; même compte peut réécrire le fichier et recalculer la chaîne; aucun ancrage externe |
| Environnement | Collecte statique de Python, distributions, fichiers natifs connus, variables de threads, entrées et Git | Bibliothèques effectivement chargées et origine d'import du solveur dans un futur enfant non observables sans instrumentation |
| Synchronisation distante | Mode SYNC séparé, refspec sans force; fetch local testable | Pas une preuve d'approbation Owner; R2 n'a pas produit de reçu de sync GitHub; le distant peut changer après le fetch |

Un compte Windows dédié avec ACL séparées est nécessaire même si les limites Job Object sont retenues. Pour protéger les archives contre le processus enfant, les sources et archives doivent être en lecture seule pour le compte d'exécution; seuls les répertoires de travail et de preuve neufs peuvent être inscriptibles. Si le scénario exige une isolation face à du code non fiable, une VM ou un conteneur avec volumes séparés est requis : Job Object seul ne sandboxe pas le système de fichiers.

## Tests et preuves de cette revue

La suite isolée `tests/unit/test_wp12_qualification_runner.py` a réussi **39 tests synthétiques** (processus factices, signatures à clés éphémères, ledger, schémas, chemins et contrôles du runner). Elle n'a pas lancé de test QF Solver ni de calcul FEM. Ces tests ne valident ni une identité Owner réelle, ni les ACL/HKLM réels, ni une campagne scientifique. Aucun test scientifique, `pytest --collect-only`, benchmark, runner de campagne, replay rotor/contact ou solveur n'a été exécuté dans WP12-S.

## Écarts R-01 à R-11 observés

Les statuts ci-dessous reprennent les limites R2 et ne signifient pas « prêt à exécuter ».

| ID | État | Décision de revue |
|---|---|---|
| R-01 | `PARTIALLY_RESOLVED` | Vérificateur Ed25519 présent, mais trust root machine absent; canonicalisation et signer réel à cadrer. Bloquant. |
| R-02 | `PARTIALLY_RESOLVED` | Job Object impose quelques limites sur faux processus; pas de quota CPU/threads/stockage ni sandbox FS. Bloquant si ces protections sont exigées. |
| R-03 | `PARTIALLY_RESOLVED` | R2 complète plusieurs inventaires, mais WP12-1 garde ses valeurs de fixture inline non résolues; les autres lots ont leurs réserves propres. |
| R-04 | `PARTIALLY_RESOLVED` | Provenance statique; environnement chargé et origine d'import enfant restent non observés. Bloquant pour campagne. |
| R-05 | `DEFERRED_WITH_JUSTIFICATION` | `EXECUTE` ne fait que refuser; une mise en œuvre distincte et une nouvelle revue sont nécessaires. |
| R-06 | `PARTIALLY_RESOLVED` | Contrôles de chemin et création exclusive, mais TOCTOU et permissions du processus subsistent. |
| R-07 | `PARTIALLY_RESOLVED` | Hash-chain utile si l'original est conservé; aucune immutabilité ou ancre hors machine. |
| R-08 | `BLOCKED_OWNER_ACTION` | C01 digest divergent et overlay C02 uniquement après décision propre; aucune correction automatique. |
| R-09 | `DEFERRED_WITH_JUSTIFICATION` | Aucune preuve numérique WP12 attendue ici; WP12 demeure `OPEN`. |
| R-10 | `PARTIALLY_RESOLVED` | SYNC existe et est distinct; pas de reçu GitHub approuvé ni de fraîcheur persistante démontrée pour une future campagne. |
| R-11 | `PARTIALLY_RESOLVED` | Ledger logique implémenté mais non intégré au lancement scientifique et non ancré extérieurement. |

## Préconditions avant toute décision WP12-1

1. L'Owner configure et vérifie la racine publique Ed25519 et ses permissions sans transmettre la clé privée.
2. L'Owner approuve le principal, la canonicalisation, l'horloge de validité, la rotation et la révocation.
3. Une nouvelle révision du manifeste fige les fixtures, l'environnement, les commandes/interpréteur, les ressources appliquées, le stockage et les entrées directes/indirectes.
4. L'Owner tranche la frontière du lot : le test Newmark qui appelle `solve_model` est déplacé vers WP12-2 ou reçoit une approbation distincte; le test de checkpoint non linéaire est déplacé vers WP12-3 ou explicitement conservé comme unité transversale.
5. Un compte d'exécution non administrateur, des ACL de lecture seule pour sources/archives, un stockage de preuves séparé et l'ancrage externe choisi sont vérifiés.
6. Le mode `EXECUTE` est implémenté, audité séparément, reste lié au candidat/runner exacts et reçoit une décision signée spécifique à l'unité et à sa tentative.

Jusqu'à satisfaction de ces points, `PREPARED_NOT_AUTHORIZED`, `NOT_RUN`, `OWNER_TRUST_NOT_CONFIGURED`, `WP12=OPEN`, `WP13=OPEN` et `WP11=CLOSED` restent inchangés.
