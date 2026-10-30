# WP12-A — Revue du chemin d'exécution du runner

PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN

## Chemin courant

Le code runner de WP12-A refuse toute exécution scientifique de façon inconditionnelle. Le CLI de scripts/wp12_runner/cli.py retourne DENY_EXECUTION avec le blocker REAL_EXECUTION_DISABLED_IN_WP12_A avant d'ouvrir un manifeste ou une décision. scripts/wp12_runner/scientific_execution.py est un stub de refus. Le chemin de lancement de processus restant dans scripts/wp12_runner/process.py accepte uniquement les six cas fixes de SELF_TEST et appelle tests/fixtures/wp12_runner/fake_child.py avec shell=False. Aucun nodeid pytest scientifique n'est construit ou lancé.

Les helpers qui classifient du XML JUnit ou vérifient des critères ne sont pas appelés dans un chemin de campagne scientifique; un rapport fourni isolément ne vaut pas preuve. Le code retour zéro ne suffit donc pas à créer un PASS. Il n'existe aujourd'hui ni orchestrateur scientifique ni chemin capable d'exécuter l'ordre complet d'autorisation, vérification, réservation, supervision, rapport, reçu et ancrage demandé pour un futur pilote.

## Orchestration synthétique WP12-X

WP12-X orchestre les six seuls cas synthétiques : success, exit, sleep, tree, flood et memory. Le rapport d'exécution SELF_TEST observé pour cette révision indique :

- six cas factices PASS selon leur résultat attendu;
- journal temporaire de 14 événements, chaîne vérifiée;
- SHA-256 du plan 2bbc9f808347e093daa7535efb42f99eed22c424fdba3afa4291a26d2eca2f10;
- SHA-256 du journal 55706b16fa6551de9a3599edd1c394439337d283a20737d322b7089b1891dffb;
- scientific_execution=false et real_execute_enabled=false.

La suite dédiée tests/unit/test_wp12_qualification_runner.py a produit 50 tests synthétiques PASS; Ruff a réussi sur les modules du runner et cette suite. Ces résultats valident seulement des chemins runner et enfants factices. Aucun test QF Solver, calcul FEM, solveur, QEP, Campbell, contact ou benchmark n'a été exécuté. Une revue de sécurité indépendante a inspecté le code en lecture seule; elle n'a pas exécuté de tests ni vérifié les ACL du système.

## Écarts qui empêchent une activation scientifique

1. Authentification Owner absente. Aucun trust store ni pin HKLM réel, aucune clé Owner et aucune décision signée; aucun champ APPROVED n'est accepté comme substitut.
2. Confinement des fichiers absent. Le compte d'exécution peut modifier les checkouts et les archives. Le Job Object ne limite pas les accès NTFS.
3. Ressources incomplètes. CPU, threads et stockage ne sont pas des limites dures; aucune capacité externe n'a été vérifiée.
4. Provenance d'import inconnue. Le package installé qf-solver 0.2.10 coexiste avec le checkout scientifique. Aucun import du solveur n'a été fait; le manifeste marque l'origine NOT_VERIFIED.
5. Commande inter-checkouts incomplète. L'argv pilote ne fige ni cwd ni chemin d'import runner. Le plugin de provenance doit être chargé depuis le commit runner tout en sélectionnant uniquement le test du checkout scientifique. Une solution reproductible doit aussi diriger JUnit vers la destination unique sans ouvrir l'écriture sur les archives.
6. Ledger/reçu sans ancrage externe. Les contrôles hash-chain fournissent une cohérence logique locale, pas une immutabilité physique contre un acteur pouvant écrire sur le support.
7. Rapport JUnit et sélection réelle non validés scientifiquement. Les helpers existants ne sont pas intégrés à un orchestrateur; un futur PASS doit exiger la présence et l'intégrité du rapport, l'unique nodeid réellement collecté/exécuté, les assertions et la vérification des entrées/sorties.

## Conditions pour une future revue d'activation

1. Corriger le modèle de commande pour désigner les deux checkouts, le cwd, PYTHONPATH ou une autre méthode équivalente, les variables d'environnement enfant, l'interpréteur absolu et les sorties. Ajouter des refus si le module résolu ne provient pas du commit runner ou si le test ne vient pas de l'identité scientifique.
2. Faire lier ces propriétés, toutes les entrées et la version du runner à un nouveau SHA de manifeste et à une décision Owner distincte signée.
3. Implémenter le véritable orchestrateur uniquement après une conception révisée : authentification, identité, hashes, environnement, protections OS, ledger, réservation exclusive, commande fixe, supervision, rapport, reçu et ancrage dans cet ordre.
4. Tester le nouveau chemin avec des programmes factices et des décisions/clés synthétiques; inclure rapport absent/contradictoire, sortie zéro sans rapport, temps, mémoire, descendants, interruption, collision et reprise. Les tests doivent continuer à exclure le package QF et toute route solveur.
5. Faire réexaminer le chemin par un auditeur sécurité indépendant; faire auditer l'environnement par un administrateur distinct.
6. Atteindre la barrière WP12_1_PILOT_OWNER_GATE, puis obtenir l'autorisation authentifiée et la confirmation Owner pour l'unique unité figée. Sans les deux, conserver DENY_EXECUTION.

Le commit a26901217826b9c5740066f1acbbc245e1a15519 porte le runner testé et reste distinct de l'identité scientifique 00428adf38e9397340ac136f6f503a268eb671da. La documentation et les propositions de scope ajoutées après le commit runner n'étendent pas les fonctions exécutables et ne changent pas cette identité. WP11 demeure CLOSED; WP12 et WP13 demeurent OPEN.
