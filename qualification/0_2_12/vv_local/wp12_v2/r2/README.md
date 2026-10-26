# WP12-V2-R2 — provenance hook correction

**WP12_V2_R2_READY_FOR_OWNER_EXECUTION_DECISION · PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

The [hook](../../../../../scripts/local_vv_pytest_plugin.py) now calls `importlib.import_module("solveur")` in the pytest child before comparing its resolved `__file__` with the approved source root. Import failure, wrong origin, changed `sys.path` or a different node selection denies the test body. The selection record is still created with exclusive `open("x")`; an existing record is never overwritten. The fixed v2 command/profile accepts the exact R2 campaign ID alongside the preserved R1 ID; no arbitrary campaign or command is added.

## Frozen candidate

- [R2 manifest](V2_R2_MANIFEST.json), SHA-256 **`a0eb16a37ab1c4e23e6624b77d829d091a7a1ac4635617a0038034d50611a503`**; 35 SHA-256/Git-OID inventory entries; `PREPARED_NOT_AUTHORIZED`, `execution_authorized=false`.
- Runner: `731fd9d6b05efe227de60e8cb19ba095cc8b29d9`, tree `19b775be2d49890b890c41b6d56f5b1be082279b`; clean detached checkout `E:\QFSolverWP12B\runner-local-vv-v2r2`.
- Tests unchanged: `67813b4a36a057bbaa9e5fba32bcdea66ddf4df3`, tree `ffee889f0cd70b089ec8e1719b84a667babfa1be`; checkout `E:\QFSolverWP12B\tests-wp12-v2-r1`.
- Science unchanged: `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`; checkout `E:\QFSolverWP12B\science`.
- Campaign `WP12-V2-R2-H1-OPERATOR-AUDIT-002`; only nodeid `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.

The [R1 result protocol](../r1/README.md), numeric payload schema and [numerical criteria](../V2_NUMERICAL_CRITERIA.md) are unchanged. The frozen test still has unverified arithmetic assumptions: gamma and the overall scientific status remain `INCONCLUSIVE` if mandatory checks pass. The new hook does not change an oracle, threshold, fixture, mechanical equation or solve route. The [R1 preflight stop](../r1/execution_20261026/PREFLIGHT_STOP_REPORT.md) and R1 manifest remain preserved; their Owner authorization is not transferred.

## Verification performed

The dedicated Python ran [the R2 synthetic lifecycle harness](../../../../../tests/synthetic/test_local_vv_provenance_hook_r2.py) directly through unittest: **8/8 passed** on the frozen runner. Seven subprocesses ran pytest only on generated temporary fake tests and harmless fake solveur packages. The eighth check verifies the R2 fixed argv. No scientific nodeid or real solveur package was imported by these tests.

| Synthetic case | Observed outcome |
|---|---|
| Package absent at test-module collection | Explicit hook import succeeds; real fake-package path matches; body runs. |
| Wrong checkout | Origin recorded; body refused. |
| Import raises ImportError | Error recorded; body refused. |
| Wrong nodeid | Actual selection recorded; body refused. |
| Selection record already exists | Original bytes preserved; body refused. |
| Already imported, conforming source and selection | Body runs. |
| Fake import changes sys.path | Change recorded; body refused. |

The unchanged R1 direct synthetic classifier harness also passes **11/11**. Ruff formatting/checks, syntax/AST, JSON, full command comparison including `-s`, inventory/Git identities, links and `git diff --check` pass. The tests use the current dedicated interpreter, fake-source/plugin PYTHONPATH only, safe-path mode, disabled autoload/conftest/cache and temporary working directories.

Static inspection of the frozen scientific initializer confirms its only eager project import is `solveur.version`, whose module-level statements are constants. API/FEM imports remain lazy; the only initializer-level call is the built-in `frozenset`. The hook itself does not insert or replace import paths. This inspection establishes absence of an eager FEM call in the frozen initializer; it grants no filesystem sandbox or general safety guarantee for arbitrary packages. The real environment must be revalidated at the future authorized preflight.

## Complete proposed Owner decision

The following text is a proposal, not an authorization already granted. No R2 approved execution record is created by this preparation.

> J'autorise explicitement une seule tentative locale de la campagne `WP12-V2-R2-H1-OPERATOR-AUDIT-002`, cas `TET4-H1-OPERATOR-AUDIT-002`, exclusivement sous le manifeste SHA-256 `a0eb16a37ab1c4e23e6624b77d829d091a7a1ac4635617a0038034d50611a503`.
>
> J'approuve le nodeid unique `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`, les identités science et tests R1 conservées, le runner `731fd9d6b05efe227de60e8cb19ba095cc8b29d9` / tree `19b775be2d49890b890c41b6d56f5b1be082279b`, les 35 entrées d'inventaire, l'environnement et la commande complète figés dans le manifeste, incluant `-s` et le plugin corrigé.
>
> J'approuve les critères numériques et le protocole gamma inchangés. Les assertions pytest et les verdicts scientifiques restent distincts. Toute hypothèse gamma non démontrée impose `INCONCLUSIVE`, sans seuil de secours ni promotion automatique en PASS. Un échec obligatoire reste FAIL ; les preuves absentes, invalides ou contradictoires restent INCOMPLETE ou ERROR.
>
> J'approuve une tentative maximale, 300 secondes, un plafond logiciel de 16 MiB par flux et aucune relance automatique. J'approuve la destination exclusive `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R2-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<new_run_id>\`, avec un identifiant généré par le runner et sans écrasement.
>
> Je confirme pour ce cas les limites locales non attestées déjà exposées : compte courant et ses permissions, absence de sandbox, de jeton restreint, de Job Object, de quotas matériels stricts CPU/RAM/disque, de garantie de terminaison des descendants, d'attestation cryptographique et d'archivage indépendant. Le timeout supervise l'enfant direct et les plafonds de journaux sont sondés, avec dépassement possible entre deux contrôles. Les preuves et archives locales restent accessibles selon les droits du compte.
>
> Cette nouvelle décision est valable 24 heures après ma confirmation explicite. Avant lancement, vérifier le manifeste, les checkouts propres, les empreintes, les versions, le chemin réel d'import scientifique, OpenBLAS, les six variables de threads, la commande, la nouvelle destination et l'absence de tentative réservée. Tout écart impose l'arrêt avant calcul. Consigner séparément ma décision, son heure UTC et son expiration, puis conserver intégralement les sorties, erreurs, JUnit, sélection, métriques et reçus.
>
> Aucun autre test, nouveau solve linéaire, raffinement, W1/W2 ou rejeu n'est autorisé. U3 reste FAIL ; les preuves WP12-S/U, les sources scientifiques, les seuils et les tests gelés sont préservés. Aucune promotion de maturité, clôture WP12/WP13, fusion, publication, tag ou release n'est autorisée. L'autorisation R1 n'est pas réutilisée.

WP12-W reste `PREPARED_NOT_AUTHORIZED`. Aucun calcul scientifique n'a été lancé dans R2.
