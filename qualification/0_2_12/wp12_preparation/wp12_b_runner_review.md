# WP12-B — Revue du runner et limites d'exécution

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Chemins réellement présents

Le runner sépare maintenant VALIDATE des entrées de deux checkouts : code scientifique et infrastructure. La correction commit `782820fe31fa8b69223bd368e39949fca325ba3e` contrôle les identités Git et empreintes dans chacun des deux arbres sans importer les modules QF. Le test synthétique ajouté construit deux dépôts Git factices, prouve que les fichiers se vérifient dans le bon arbre et confirme qu'une altération source rend le manifeste bloqué.

Le chemin `EXECUTE` n'est **pas opérationnel** :

1. `scripts/run_wp12_qualification.py --mode EXECUTE` entre dans `scientific_execution.execute_pilot` après refus des arguments non approuvés.
2. `execute_pilot` vérifie l'identité, l'environnement, le trust store, les ressources, l'isolation et l'archive.
3. Avec le manifeste v3 courant, les contrôles s'arrêtent sur l'absence de décision authentifiée, d'archive externe, d'isolation vérifiée et de revue indépendante enregistrée.
4. Même si ces précontrôles étaient artificiellement satisfaits, `pilot_execution.execute_authenticated_pilot_unit` retourne toujours `DENY_EXECUTION / SYSTEM_CHILD_PROCESS_ATTESTATION_NOT_IMPLEMENTED`; `process.run_approved_pilot_process` lève également ce blocage avant tout démarrage.
5. Le seul lancement disponible dans `process.py` est `run_fake_process`, qui accepte un ensemble fermé de scénarios factices et fabrique lui-même la commande du faux enfant.

Il n'existe donc pas de moyen runner/API/CLI, ni de commande de contournement, pour lancer le nodeid scientifique. Un utilisateur local peut toutefois lancer pytest hors runner; le runner n'est pas une sandbox OS et n'empêche pas une exécution manuelle non gouvernée.

## Contrôles Windows démontrés

`SELF_TEST` a utilisé les sept cas synthétiques fixes `cpu`, `exit`, `flood`, `memory`, `sleep`, `success` et `tree`. Résultat : `PASS`, 7 invocations, chaîne de journal vérifiée, aucune erreur de journal, aucun PID enfant restant, `real_execute_enabled=false` et `scientific_execution=false`. Les enfants CPU, mémoire, processus et timeout sont artificiels. Le Job Object a démontré pour ces faux enfants les plafonds CPU/mémoire/processus et la terminaison de l'arbre.

Ces résultats ne démontrent pas l'application des mêmes contrôles à un compte runner réellement isolé. Un Job Object n'isole pas le système de fichiers. Les ACL effectives de l'hôte n'ont pas été configurées ni testées. Les limites disque et threads sont souples. Le test de lien symbolique Windows est ignoré faute de privilège de création de symlink dans le compte actuel.

## Revue de sécurité indépendante et statut

Une revue read-only antérieure du call graph avait confirmé le refus au niveau API/CLI et l'absence de commande arbitraire dans les points de lancement. La modification du commit `782820fe…` porte uniquement sur le mode statique `VALIDATE` et son test synthétique; elle n'ouvre aucune route de lancement. Cette observation antérieure n'est pas enregistrée comme revue indépendante actuelle dans le manifeste v3. Celui-ci garde `security_review.status=NOT_REVIEWED`, et le verdict de sécurité d'exécution demeure bloqué.

Une revue indépendante formelle doit examiner le commit runner exact qui sera autorisé, le worker SYSTEM, les ACL effectives, l'attestation du processus, les sorties JUnit/collection, le ledger et la conservation externe des preuves. La réussite des tests factices ne ferme pas cette revue.

## Résultats logiciels factices

Exécutés depuis `E:\QFSolverWP12B\runner` avec `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe` :

| Contrôle | Résultat |
|---|---|
| `tests/unit/test_wp12_qualification_runner.py` | 63 passed, 1 skipped; skip : création d'un répertoire symlink non permise au compte courant |
| `SELF_TEST --case all` | PASS, 7 cas factices; zéro processus enfant résiduel |
| Ruff check | PASS |
| Ruff format --check | PASS |
| `VALIDATE` manifeste v3 | `STRUCTURALLY_VALID_NOT_AUTHORIZED`; 141 identités vérifiées, aucune erreur d'entrée |
| Calcul FEM/solveur/test QF | Non exécuté |

Le `SELF_TEST` met en œuvre uniquement les faux enfants autorisés. Le test de validation split-checkout utilise des dépôts Git temporaires synthétiques. Aucun test du solveur, de la mécanique ou du pilote n'a été lancé.

## Blocages avant le pilote

* Windows `19045.6456` est sous le minimum `19045.7807` du script.
* Aucun compte runner standard dédié ni ACL NTFS testée.
* Aucun trust store public épinglé en HKLM, aucune clé Owner réelle, aucune signature ni décision de lancement.
* Aucun ancrage de preuve externe configuré; le worker existant copie des artefacts mais n'atteste pas le processus qui les a produits.
* Attestation du processus enfant et orchestration finale scientifique non implémentées; l'exécuteur est un stub de refus.
* Revue indépendante actuelle non enregistrée dans la décision/manifeste.
* Le budget de stockage et la limite de threads ne sont pas garantis durs.

Tant que ces points ne sont pas résolus, le runner doit rester `DENY_EXECUTION`. La voie la plus courte n'est pas de signer le manifeste actuel : il faut d'abord terminer l'attestation et la chaîne d'archive, réviser le manifeste avec les nouvelles identités, refaire la revue indépendante, puis faire signer une décision Owner distincte liée au SHA-256 final et à l'unique unité.
