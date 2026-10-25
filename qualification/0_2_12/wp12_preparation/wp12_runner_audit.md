# WP12-R — Rapport d'audit du runner

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

## Portée et identité

Base inspectée : branche `emptiesvoids-cloud/0.2.12`, HEAD initial `da9bb79eba640da500a1b33e32f03e1abb9a9ba2`, tree `d3749260c54ec35776988e30eb6c184e205bad07`. Le distant `origin/emptiesvoids-cloud/0.2.12` pointait au même commit au début. Le dossier WP12-0 cible historiquement le commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`; il a été laissé inchangé. Le commit runner/documentation ultérieur ne représente pas un nouveau changement de physique.

La revue a porté sur les règles de développement, la policy de runner, les runners de développement/C02, le workflow CI, la roadmap, les six manifestes WP12-0, les exigences et plans WP12, ainsi que les modules WP12-R et ses tests synthétiques. Les tests scientifiques et les runners de qualification historiques n'ont pas été exécutés.

## Architecture et constat

Le script CLI délègue les contrats/identités à `scripts/wp12_runner/contracts.py`, les sorties/journaux/reçus à `evidence.py`, et la supervision bornée des processus fixes de SELF_TEST à `process.py`. Les cas enfants sont dans `tests/fixtures/wp12_runner/fake_child.py`. Les schémas distinguent le manifeste préparatoire, une future unité d'exécution gelée et une décision Owner séparée.

`VALIDATE` est une inspection sans enfant scientifique. `SELF_TEST` ne peut sélectionner que les cas factices internes. `EXECUTE` ne peut pas exécuter : il produit `DENY_EXECUTION`, enregistre un événement dans `.codex/wp12_runner_audit/` si possible et retourne 3. La décision Owner n'est pas authentifiée car aucune clé de confiance indépendante n'est configurée; cette absence est bloquante.

Les six manifestes WP12-0 restent `PREPARED_NOT_AUTHORIZED` et n'ont pas été remplacés. La validation statique trouve :

- WP12-1, WP12-2 et WP12-4 : structure JSON cohérente, mais identity maps incomplètes par rapport aux fichiers sources/tests énumérés.
- WP12-3 : mêmes inventaires incomplets, un doublon de nodeid, et le contrôle de digest fixture C01 diverge; le helper C02 reste identifié sans être matérialisé.
- WP12-5 : pas de scénario/nodeid exact ni d'inventaire source/test gelé.
- WP12-6 : commit/tree final et inventaires de sources/tests absents; ces valeurs doivent être définies après les campagnes.

Ces constats sont des écarts de préparation et des refus; aucune preuve historique n'a été modifiée, et aucun résultat courant n'en est déduit.

## Contrôles synthétiques

Commandes dédiées effectuées sur le code WP12-R préparé :

| Contrôle | Résultat |
|---|---|
| `python -m ruff check` sur les fichiers Python WP12-R | PASS |
| `python -m ruff format --check` sur les fichiers Python WP12-R | PASS; 8 fichiers déjà formatés |
| `tests/unit/test_wp12_qualification_runner.py` avec `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` et `--confcutdir=tests/unit` | **27 passed** en 6,92 s; seul nodeid explicitement ciblé |
| CLI `SELF_TEST --case all` | PASS, 5 cas factices; reçus vérifiés, 0 problème de reçu et 0 descendant résiduel sur chaque cas |
| CLI `VALIDATE` sur WP12-1, avant commit | Refus attendu `BLOCKED`, code retour 2, `execution_started=false`; mismatch commit/tree de préparation, worktree alors modifié par WP12-R, inventaire incomplet et hashes des fixtures inline non gelés |
| CLI `VALIDATE` après commit sur worktree propre | Toujours `BLOCKED`, code retour 2, `execution_started=false`; aucun blocker `GIT_CHECKOUT_DIRTY`. Le commit/tree cible historique et les identités source/fixture restent en écart, en plus des blockers d'autorisation intrinsèques du manifeste préparatoire |
| JSON schemas et manifestes préparatoires | Trois schémas chargés/vérifiés; WP12-1/2/4 structurels, WP12-3 dupliqué/invalide, WP12-5 inventaire/scénarios incomplets, WP12-6 identité/inventaires finaux absents; les six restent non exécutables |
| Liens relatifs et recherche de chemins personnels/références employeur dans les fichiers modifiés | 0 lien rompu; 0 correspondance trouvée lors du contrôle statique |
| `git diff --cached --check` avant commit | PASS; le hook de confidentialité du commit a également indiqué PASS |
| Tests, calculs, benchmarks QF Solver | **NON EXÉCUTÉS** |

Un PASS de cette suite est uniquement une preuve de comportement du runner avec fichiers et processus factices. Ce n'est ni une validation du solveur, ni un PASS FEM, ni une qualification de sécurité de production.

Pendant l'implémentation, un premier passage a compté 24 PASS et 1 FAIL synthétique : la fonction de refus classait un chemin d'audit extérieur comme chemin symlink/junction avant de signaler le défaut de confinement. L'ordre des vérifications a été corrigé; la suite finale ci-dessus a été relancée et passe 27/27.

## Limites de sécurité

- Pas d'authentification Owner et pas d'activation d'EXECUTE.
- Aucun Job Object Windows; les limites RSS, CPU, stockage, threads et processus échantillonnées ne sont pas dures.
- Pas de sandbox FS : un processus enfant conserve ses permissions système. Les chemins sont contrôlés mais cette validation n'est pas un confinement.
- Les reçus sont hachés, pas signés ni stockés en immuable; les contrôles de chemin ont une limite de course locale.
- Le runner WP12-R n'orchestra aucune unité scientifique, ne lit pas le chemin d'import du wheel QF et ne contrôle pas les bibliothèques natives de l'environnement d'exécution.

## Verdict de préparation

**RUNNER_READY_WITH_LIMITATIONS** : WP12-R peut être soumis à revue Owner pour VALIDATE et SELF_TEST. Il ne peut pas être utilisé pour lancer une campagne scientifique. Même si tous les tests factices passent, WP12-R ne devra pas être nommé `QUALIFIED`. L'Owner doit encore approuver le modèle de confiance, l'environnement d'isolation, les manifestes complets et chaque campagne; WP12 reste `OPEN`.
