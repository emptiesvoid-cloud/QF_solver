# WP12-R — Modèle de confiance et limites de sécurité

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Frontière d'autorité

Le manifeste décrit une unité d'exécution; il ne s'auto-autorise pas. Une décision Owner séparée lie un identifiant de campagne, le SHA-256 exact du manifeste, le commit/tree, les opérations et nodeids, l'environnement, les budgets, les tentatives, la destination, le principal et l'horodatage. Son enveloppe prévoit Ed25519, l'identifiant de clé et les empreintes du payload/signataire.

Le dépôt ne contient pas de magasin de clés Owner protégé ni de vérificateur avec chaîne de confiance indépendante. Les champs JSON et une signature seulement auto-déclarée sont modifiables par l'exécutant. Par conséquent, WP12-R valide la structure et les liaisons de champs mais n'authentifie aucune décision. `OWNER_TRUST_CONFIGURED=False` et `REAL_EXECUTION_ENABLED=False`; `EXECUTE` refuse sans exception, même si un JSON porte `status=APPROVED`.

Pour une future activation, l'Owner doit choisir une clé publique de confiance provisionnée hors du checkout, une représentation canonique non ambiguë du payload signé, la gestion de révocation/rotation, et un canal de publication de la décision à accès contrôlé. Une signature vérifiée ne remplace pas le contrôle de SHA/tree, des entrées, ni l'isolation du processus.

## Identité et sélecteurs

VALIDATE vérifie le schéma local, la branche, le commit, le tree, l'état propre demandé, les OID Git et SHA-256 déclarés, les fixtures, les chemins sûrs et les déclarations d'overlay. Les nodeids sont syntaxiquement exacts et le futur format d'unité n'autorise qu'une commande Python/pytest unique avec un seul nodeid; aucune sélection par dossier, glob ou suite n'est prévue. L'import réel du package solveur et les dépendances numériques natives sont des contrôles nécessaires à l'exécution future, mais aucun code d'exécution scientifique n'est activé ici.

Les manifestes WP12-0 préservent leur ancien commit cible. Le commit WP12-R et son tree ajoutent l'infrastructure/documentation; ils ne doivent pas être présentés comme un nouveau commit de physique. Les manifestes existants n'ont pas été modifiés ni réautorisés.

## Processus et ressources

Le seul lancement de processus disponible au SELF_TEST est un enfant Python fixe et local, sans shell et avec une liste de cas fermée. Les journaux de sortie ont un plafond d'octets; le temps wall, la mémoire RSS, le nombre de processus et l'espace écrit sont contrôlés par timeout ou échantillonnage. RSS, CPU, threads et stockage observés ne sont pas des limites dures.

Sous Windows, le code tente de terminer les descendants via `psutil`, avec `taskkill /T /F` comme repli. Aucun Job Object n'est créé dans WP12-R; le contrôle du nombre de threads, du CPU, du RSS et du stockage ne constitue donc pas une isolation garantie. L'absence de processus résiduels est vérifiée dans les tests synthétiques, mais cette propriété ne vaut pas preuve d'une isolation système pour un solveur arbitraire.

Le SELF_TEST s'exécute avec l'identité utilisateur et les permissions de fichiers du runner. Le programme factice pourrait théoriquement accéder au même système de fichiers. Les chemins exclusifs et les reçus réduisent les erreurs accidentelles; ils ne sandboxent pas un processus enfant. L'exécution scientifique demeure bloquée tant qu'un environnement approuvé n'offre pas les garanties de ressources, de processus descendants et de protection des archives demandées par le manifeste.

## Preuves et intégrité

Les reçus inventorient les sorties avec SHA-256 et un sidecar, et les journaux JSONL refusent les enregistrements tronqués. Ces hashes détectent des altérations ultérieures si le reçu est conservé dans une chaîne de confiance; ils ne sont ni une signature cryptographique, ni un stockage immuable. L'écriture exclusive refuse les collisions et les chemins symlink/junction détectés avant création, mais les protections de `pathlib` ne suppriment pas les courses concurrentes locales.

Les refus EXECUTE sont enregistrés dans `.codex/wp12_runner_audit/`, ignoré par Git, jamais dans `wp12_evidence`. Les preuves scientifiques futures doivent aller sous `qualification/0_2_12/wp12_evidence/<campaign>/<run>/` et ne peuvent pas toucher v0.2.11 ou d'autres archives. Ce contrôle de destination n'est pas une restriction générale des droits du processus enfant.

## Exceptions de provenance connues

- C02 : le helper historique est seulement identifié par commit, blob OID et SHA-256; il n'est pas matérialisé. Un overlay réel nécessite une décision Owner distincte et une isolation avant tout contrôle M4/M5.
- C01 : si le digest R19 attendu diffère des octets, le contrôle est refusé. Le runner ne réécrit ni fixture ni constante.
- Rotordynamique : le runner peut vérifier des nodeids QEP/Campbell, mais aucun GYRO-01 à GYRO-06 ne s'exécute dans WP12-R. L'historique garde sa portée et sa maturité EXPERIMENTAL.

Les restrictions de cette page sont des limitations explicites, pas des garanties d'isolation plus fortes que celles réellement fournies.
