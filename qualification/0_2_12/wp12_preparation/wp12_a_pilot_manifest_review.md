# WP12-A — Revue du manifeste pilote

PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN

## Identité et validation documentaire

Manifeste : [wp12_a_pilot_manifest_v1.json](wp12_a_pilot_manifest_v1.json), campagne WP12-1-PILOT-001, unité WP12-1-PILOT-001-UNIT-01, statut FROZEN_NOT_AUTHORIZED.

Le schéma wp12_execution_manifest_v3.schema.json l'accepte. Le champ de limite CPU a été ramené de hard à soft, car le runner ne garantit pas de plafond CPU dur. solver_import_origin est NOT_VERIFIED; aucun import QF n'a été fait. Le statut reste non autorisé et aucune enveloppe ou décision de signature n'est jointe.

Le manifeste identifie le code scientifique (00428adf... / df4ec667...) indépendamment du runner (a2690121... / ef0e3556...). Les SHA-256 de sources/tests déclarés ont été confrontés statiquement au checkout scientifique propre. Le nodeid exact est unique dans ce pilote; aucun autre test n'est dans son argv.

## Entrée inline canonique

Le fichier scripts/wp12_runner/inline_fixtures.py définit qf-wp12-inline-fixture-v1. Une extraction AST limitée au corps du nodeid lit les affectations littérales stiffness et modes; les matrices sont converties en listes JSON, dimensions explicites et chaînes décimales repr(float(value)), puis sérialisées en UTF-8 JSON à clés triées et séparateurs compacts, sans saut de ligne. Le SHA-256 obtenu est 5873637fc10c495c3cee53f41b9a3956565e07c295cb1a4b071f6dfae9dd6aff, identique à la valeur du manifeste. Le fichier complet du test, SHA-256 9be78449948ebcdc9d577a8968b2dbacbc9b25015b4c9484ece8f91218e20d28, reste aussi une entrée identifiée. Aucune valeur de fixture n'a été changée.

## Oracle et dépendances

Le manifeste reprend l'oracle existant : forme bilinéaire dense modes.T @ (stiffness @ modes), symétrie exacte de la matrice projetée et de l'entrée; la comparaison dense utilise rtol=2e-16, atol=2e-16. Il s'agit du contrat/assertion de ce test, pas d'un nouveau critère d'acceptation. Le test importe NumPy, pytest, SciPy sparse, le module de base modale, le module numérique de projection, le système préparé et les erreurs; leurs sources principales sont hashées. L'inventaire de fichiers ne prouve pas à lui seul la fermeture de toutes les dépendances transitives ni quelle distribution Python sera importée.

## Écarts qui interdisent le gel pour signature

1. Import plugin / checkout. L'argv choisit le nodeid dans le checkout scientifique, mais appelle le plugin par nom de module scripts.wp12_runner.pytest_provenance_plugin. Aucun cwd ou PYTHONPATH ne relie explicitement le checkout runner. Le module peut être introuvable ou être résolu depuis le mauvais arbre. Une nouvelle révision doit pinner le répertoire courant, l'origine absolue du plugin, les règles de sys.path et la destination effective; l'exécuteur doit ensuite vérifier ces valeurs dans l'enfant.
2. Origine solveur. L'environnement contient un package installé qf-solver 0.2.10, tandis que le code scientifique ciblé est le worktree v0.2.12. L'origine d'import réelle n'a pas été observée; NOT_VERIFIED est volontaire. La future décision ne doit pas signer ce champ en l'état.
3. Séparation déclaré/observé. Les variables de threads "1" sont une configuration de processus proposée, pas une observation de l'environnement actuel. Le runner n'applique ni ne vérifie un profil enfant scientifique, car EXECUTE reste bloqué.
4. Ressources. Les budgets chiffrés restent des propositions. CPU, threads et stockage sont soft; les mécanismes Job Object ont été testés uniquement avec des enfants factices. Il n'y a ni quota disque ni confinement fichier.
5. Destination et tentative. attempt-001 est un emplacement prévu, non une réservation effective. Aucun run ID ni événement ledger n'est créé. Le répertoire n'a pas été créé et ses ACL ne sont pas sécurisées.
6. Authenticité. Aucun trust store, pin HKLM, clé Owner réelle, signature ou décision n'existe. Le manifeste ne peut s'autoriser lui-même.

## Conclusion

Le document est structurellement préparé, mais ne constitue pas un manifeste prêt à signer ni à exécuter. Il faut le réviser après résolution des écarts d'import, d'environnement et d'isolation. Toute modification ultérieure invalidera le hash déclaré au dossier Owner; une nouvelle empreinte et une décision Owner entièrement nouvelle seront requises. Le runner courant refuse de toute façon EXECUTE avant la lecture du manifeste. Aucun test scientifique n'a été lancé.
