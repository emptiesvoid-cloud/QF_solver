# WP12-R — Guide d'utilisation du runner

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Ce guide ne vaut pas autorisation Owner. Le runner n'importe pas le solveur QF. Son mode EXECUTE est un refus permanent dans cette version.

## Modes

### VALIDATE

```powershell
python scripts/run_wp12_qualification.py --mode VALIDATE --manifest qualification/0_2_12/wp12_preparation/wp12_1_execution_manifest.json
```

VALIDATE lit le JSON et son schéma, contrôle la branche/commit/tree/état Git, puis compare les OID Git et SHA-256 déclarés avec le dépôt et le worktree. Il ne lance aucun processus de test. Il signale les valeurs proposées, inventaires incomplets, écarts de fixture (dont le contrôle C01) et overlay historique C02 non matérialisé.

Le résultat `STRUCTURALLY_VALID_NOT_AUTHORIZED` signifie uniquement que la structure et les identités contrôlées n'ont pas produit d'erreur; il ne confère aucune autorisation. Un manifeste préparatoire conserve toujours les blockers `PREPARED_NOT_AUTHORIZED` et `REAL_EXECUTION_DISABLED_IN_WP12_R`.

### SELF_TEST

```powershell
python scripts/run_wp12_qualification.py --mode SELF_TEST --case all
```

SELF_TEST n'accepte aucun manifeste, décision Owner, commande ni nodeid. Il sélectionne uniquement les cas fixes `success`, `exit`, `sleep`, `tree` et `flood` du programme `tests/fixtures/wp12_runner/fake_child.py`. Les sorties sont dans un dossier temporaire unique, supprimé après le mode; ce sont des tests du superviseur, pas du solveur.

La suite pytest autorisée est exactement :

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -q --confcutdir=tests/unit tests/unit/test_wp12_qualification_runner.py
```

Cette commande doit être relue avant exécution et ne doit pas être élargie à `tests/`, à un nodeid QF Solver, à `--collect-only` ou à la CI complète dans WP12-R.

### EXECUTE

```powershell
python scripts/run_wp12_qualification.py --mode EXECUTE --manifest <manifest.json> --manifest-sha256 <sha256-exact> --nodeid <nodeid-exact>
```

EXECUTE inspecte les éléments fournis, écrit un refus durable sous `.codex/wp12_runner_audit/` si possible et retourne le code 3. Il ne démarre jamais pytest ni un autre processus scientifique. Un fichier de décision JSON marqué APPROVED reste non authentifié. Aucun argument de forçage ou de contournement n'existe.

## Interprétation des états

`PASS`, `FAIL`, `INCONCLUSIVE`, `TIMEOUT`, `RESOURCE_LIMIT`, `INTERRUPTED` et `INFRA_ERROR` sont distincts. Un échec scientifique avec rapport JUnit reste FAIL; une absence ou corruption du rapport reste INFRA_ERROR. Un timeout, skip ou interruption ne devient jamais PASS. Aucun état `CURRENT_PASS_EVIDENCED` n'est créé par une inspection statique ou un SELF_TEST.

Les preuves d'une campagne future ne peuvent être émises qu'après une évolution contrôlée du modèle de confiance et du confinement, une décision Owner spécifique, un manifeste d'unité figé, la vérification des identités et une revue de sécurité. WP12-R ne réalise pas encore cette exécution.
