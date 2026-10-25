# WP12-R2 — Guide d'utilisation du runner

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Ce guide ne vaut pas autorisation Owner. Le runner n'importe pas le solveur QF. Son mode EXECUTE reste désactivé dans WP12-R2, quelle que soit la décision fournie.

## Modes

### VALIDATE

```powershell
python scripts/run_wp12_qualification.py --mode VALIDATE --manifest qualification/0_2_12/wp12_preparation/wp12_1_execution_manifest.json
```

VALIDATE lit le JSON et son schéma, contrôle la branche/commit/tree/état Git, puis compare les OID Git et SHA-256 déclarés avec le dépôt et le worktree. Il collecte aussi des métadonnées Python/distributions, les fichiers natifs identifiables dans les métadonnées NumPy/SciPy, les variables de threads et les hashes d'entrées, sans importer QF Solver, NumPy ou SciPy. Il ne lance aucun processus de test et ne rafraîchit jamais les références distantes. Les bibliothèques effectivement chargées par un futur enfant et son origine d'import restent non vérifiables sans instrumentation autorisée.

Le résultat `STRUCTURALLY_VALID_NOT_AUTHORIZED` signifie uniquement que la structure et les identités contrôlées n'ont pas produit d'erreur; il ne confère aucune autorisation. Un manifeste préparatoire conserve toujours les blockers `PREPARED_NOT_AUTHORIZED` et `REAL_EXECUTION_DISABLED_IN_WP12_R`.

### SYNC

```powershell
python scripts/run_wp12_qualification.py --mode SYNC
```

SYNC est une opération distincte et explicite. Elle valide l'URL `origin`, récupère uniquement `refs/heads/emptiesvoids-cloud/0.2.12` vers sa référence de suivi sans refspec forcé, vérifie l'ascendance locale et écrit un reçu informatif sous `.codex/wp12_runner_audit/`. Le reçu ne constitue pas une approbation Owner. En cas de divergence ou de mise à jour non fast-forward, l'opération s'arrête. SYNC n'a pas été exécuté sur le distant réel pendant WP12-R2; son seul test utilise un dépôt bare Git temporaire local.

### SELF_TEST

```powershell
python scripts/run_wp12_qualification.py --mode SELF_TEST --case all
```

SELF_TEST n'accepte aucun manifeste, décision Owner, commande ni nodeid. Il sélectionne uniquement les cas fixes `success`, `exit`, `sleep`, `tree`, `flood` et `memory` du programme `tests/fixtures/wp12_runner/fake_child.py`. Sur Windows, le superviseur crée le processus suspendu, l'assigne à un Windows Job Object puis reprend le thread. Le Job Object impose la limite de processus active, la terminaison à la fermeture et, pour le seul scénario mémoire factice, un plafond agrégé de 64 MiB. Cette valeur est exclusivement un paramètre du SELF_TEST; ce n'est pas un budget WP12 approuvé. Les sorties sont dans un dossier temporaire unique; ce sont des tests du superviseur, pas du solveur.

Le plafond CPU dur n'est pas fourni : une sonde synthétique du Job Object n'a pas démontré son application et le code correspondant a été retiré. Le timeout wall reste une terminaison supervisée, pas une limite CPU.

Les Job Objects ne limitent pas le stockage ou le nombre de threads, ne sandboxent pas le système de fichiers et n'empêchent pas le processus enfant d'écrire avec les permissions de son compte. Sur les plateformes autres que Windows, le scénario de plafond mémoire Job Object est `NOT_APPLICABLE`; le nombre de processus et l'arrêt des descendants ne sont pas garantis par ce runner hors Windows. Un manifeste exigeant ces garanties doit être refusé dans un environnement qui ne les fournit pas.

La suite pytest autorisée est exactement :

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -q --confcutdir=tests/unit tests/unit/test_wp12_qualification_runner.py
```

Cette commande ne couvre que les tests du runner et ses fixtures. Elle ne doit pas être élargie à `tests/`, à un nodeid QF Solver, à `--collect-only` ou à la CI complète dans WP12-R2.

### EXECUTE

```powershell
python scripts/run_wp12_qualification.py --mode EXECUTE --manifest <manifest.json> --manifest-sha256 <sha256-exact> --nodeid <nodeid-exact>
```

EXECUTE inspecte les éléments fournis, tente l'authentification Ed25519 par la racine machine décrite dans le [modèle de sécurité](wp12_runner_security_model.md), écrit un refus sous `.codex/wp12_runner_audit/` si possible et retourne le code 3. Il ne démarre jamais pytest ni un autre processus scientifique. Sans clé de confiance provisionnée hors du checkout, aucune décision ne s'authentifie. Aucun argument de forçage ou de contournement n'existe.

## Interprétation des états

`PASS`, `FAIL`, `INCONCLUSIVE`, `TIMEOUT`, `RESOURCE_LIMIT`, `INTERRUPTED` et `INFRA_ERROR` sont distincts. Un échec scientifique avec rapport JUnit reste FAIL; une absence ou corruption du rapport reste INFRA_ERROR. Un timeout, skip ou interruption ne devient jamais PASS. Aucun état `CURRENT_PASS_EVIDENCED` n'est créé par une inspection statique ou un SELF_TEST.

Le ledger des tentatives sous `.codex/wp12_runner_audit/` utilise un verrou, un append JSONL avec `fsync` et une chaîne SHA-256. Il refuse les journaux tronqués ou incohérents et les identifiants de run réutilisés. Il est logiquement append-only, mais un acteur ayant accès en écriture peut le remplacer et recalculer la chaîne; une archive externe est nécessaire pour une meilleure garantie d'intégrité.

Les preuves d'une campagne future ne peuvent être émises qu'après provisionnement et revue de la racine de confiance, choix d'un compte/environnement d'exécution protégé, décision Owner spécifique, manifeste d'unité figé et vérification des identités. WP12-R2 ne réalise pas cette exécution.

Un futur manifeste d'unité utilise le schéma execution v2 : `target` et `runner_identity` désignent ensemble le commit/tree exact de la branche qui exécuterait le runner; `scientific_identity` désigne séparément le commit/tree du code scientifique de référence. Les SHA-256 des sources/tests/fixtures lient les fichiers effectivement présents au checkout. La décision Owner v2 signe les deux identités et le SHA-256 brut exact du manifeste. Un commit d'infrastructure runner plus récent ne modifie donc pas l'identité scientifique par simple transitivité.
