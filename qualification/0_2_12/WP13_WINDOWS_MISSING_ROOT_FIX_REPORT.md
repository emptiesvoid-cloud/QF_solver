# WP13 — Correctif de boucle sur racine Windows absente

**État :** correctif vérifié par tests ciblés locaux et par une unique exécution Windows hébergée. WP13 P0 reste `PARTIAL_OR_BLOCKED` : ce diagnostic ne qualifie ni la suite complète, ni la matrice de compatibilité, ni la candidate de release.

**Branche / PR :** `codex/wp13-release-engineering-20261031`, [PR #114](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)

**Commit testé :** `2aa14bfc4f875d7bf3786e2e2f0402b8721f2107`
**Exécution Windows :** [GitHub Actions #41291708923](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41291708923) — `push`, `success`, durée 1 min 25 s.

## Cause reproduite avant correction

Le diagnostic [#41289474041](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41289474041), sur le commit `1ef0ec97351971d65e79d45ad9ff234103676b36`, a bloqué le nodeid :

`tests/unit/test_development_autonomous_policy.py::test_wp12_runner_selects_scope_mandate_without_launching[rotor]`

Le test a dépassé le watchdog de 110 s et s’est terminé après 112,234 s avec le code 124. La trace place l’exécution dans `Path.exists()` depuis la boucle de remontée des parents de `run_pytest`. Le chemin historique `E:\QFSolverAgents\evidence\.wp12-coordination` n’avait aucun ancêtre existant sur le runner Windows.

## Diff appliqué

Dans [`scripts/development_autonomous.py`](../../scripts/development_autonomous.py), la recherche est bornée à la racine du chemin. Elle refuse explicitement le chemin si la racine ne peut pas être trouvée, sans substitution de lecteur ni création d’un emplacement alternatif :

```python
def _existing_filesystem_ancestor(disk_path: Path) -> Path:
    anchor = disk_path.resolve()
    while not anchor.exists():
        parent = anchor.parent
        if parent == anchor:
            raise PolicyError(f"No existing filesystem ancestor for required path: {disk_path}")
        anchor = parent
    return anchor
```

`run_pytest` appelle désormais cette fonction pour chaque chemin contrôlé avant le contrôle d’espace disque.

Dans [`tests/unit/test_development_autonomous_policy.py`](../../tests/unit/test_development_autonomous_policy.py), le test paramétré du mandat remplace le chemin `E:\...` par un répertoire de coordination sous `tmp_path`, configuré par `monkeypatch`. Le test conserve le contrôle de mandat. Il intercepte `_next_attempt` avant toute réservation, fait échouer tout appel à `run_supervised_command`, et compare le contenu du store avant et après.

Trois tests synthétiques couvrent l’ancêtre direct, plusieurs remontées vers un ancêtre existant et une racine Windows absente. Le dernier simule `Z:\QF_solver\missing\coordination`, vérifie le `PolicyError` fail-closed et confirme exactement quatre vérifications `exists()` jusqu’à `Z:\`, ce qui exclut la boucle infinie.

Le manifeste exact des nodeids et son identité sont conservés dans [`wp13_windows_missing_root_diagnostic_nodeids.json`](./wp13_windows_missing_root_diagnostic_nodeids.json), blob Git `34130c8ec7f78564a01f2d62bd7b2ffee68efbf4`, SHA-256 canonique `874ea54d476cce761ceff5698c9a4b9513ab042cfa93f1504af2b3326e218c17`.

## Validation locale ciblée

Les 12 nodeids ci-dessous ont été lancés séparément, sans FEM : les neuf paramètres du test de mandat et les trois nouveaux tests de chemin. Résultat : **12 PASS, 0 FAIL**.

Ont également réussi : `py_compile` des deux scripts et du module de tests, parsing YAML du workflow, parsing JSON du manifeste et `git diff --check`. Ruff n’était pas installé dans l’environnement local et n’a pas été exécuté.

## Exécution Windows hébergée

Le workflow [`wp13-windows-diagnostic.yml`](../../.github/workflows/wp13-windows-diagnostic.yml) a conservé Windows, Python 3.13, le timeout de job de 15 minutes, les permissions `contents: read`, la collecte des logs et l’absence de FEM. Le runner sélectionne seulement les nodeids épinglés, applique les filtres de la suite standard, vérifie que la collecte correspond exactement au manifeste, limite chaque nodeid à 110 s et le diagnostic à 720 s. Il a collecté **64 nodeids distincts** et exécuté **65 occurrences** parce que `[rotor]` est joué à l’isolement puis dans la séquence.

| Groupe | Nodeids exécutés | Résultat pytest | Temps pytest / temps mural du groupe | Maximum RSS observé |
|---|---:|---|---:|---:|
| `[rotor]` isolé | 1 | 1 PASS | 1,36 s / 2,019 s | 89 837 568 octets |
| Huit autres paramètres du test de mandat | 8 | 8 PASS | 1,48 s / 2,018 s | 87 678 976 octets |
| 52 prédécesseurs, `[rotor]`, 3 régressions | 56 | 56 PASS | 3,51 s / 4,032 s | 93 130 752 octets |

Les journaux d’événements enregistrent les 65 débuts/fins, les temps muraux et CPU par nodeid, RSS et compteurs d’E/S. Aucun timeout n’a eu lieu. Les trois groupes ont terminé avec le code 0. Le checkout est resté propre et les trois chemins `forbidden-fem-evidence` configurés sous le répertoire temporaire sont restés absents.

En comparaison, le run initial a consommé 112,234 s avant le timeout sur le même nodeid `[rotor]`; après correction, ce nodeid passe isolément en 1,36 s de temps pytest (0,019 s de temps mur enregistré par le plugin). La comparaison inclut le démarrage du processus dans le premier temps mural; le rapport distingue donc les temps pytest et les temps du runner.

Environnement du run correctif : Windows Server 2025, Python 3.13.16, pytest 8.4.1, psutil 7.0.0. L’artefact `wp13-windows-diagnostic-41291708923` contient `baseline.json`, `summary.json`, la collecte exacte, les journaux pytest et les journaux d’événements.

## Sécurité et portée

- Aucun FEM, benchmark, campagne scientifique, réservation ni lancement de processus de solveur n’a été effectué. Le test du mandat intercepte la frontière de réservation et interdit tout appel au lanceur.
- Aucun ledger scientifique n’a été modifié. Les sorties du diagnostic et les fichiers temporaires sont dans le répertoire temporaire du runner, hors checkout; le store temporaire synthétique du test est inchangé.
- La racine de lecteur absente est couverte par un chemin Windows simulé. Le run prouve également que le test `[rotor]` n’accède plus au chemin historique de coordination.
- Ces résultats ne remplacent pas la suite complète, la matrice OS × Python ou les autres gates P0. Ils ne justifient pas `WP13_P0_VALIDATED`.
- Aucun merge dans `main`, tag, package ou publication n’a été réalisé.

## Fichiers et références

- Code et tests : commit `2aa14bfc4f875d7bf3786e2e2f0402b8721f2107`, PR #114.
- [Diff exact du commit](https://github.com/emptiesvoid-cloud/QF_solver/commit/2aa14bfc4f875d7bf3786e2e2f0402b8721f2107).
- Manifeste d’exécution : `wp13_windows_missing_root_diagnostic_nodeids.json`.
- Logs pré-correctif : run #41289474041; logs post-correctif : run #41291708923, artefact `wp13-windows-diagnostic-41291708923`.
- Statut restant : WP13 P0 `PARTIAL_OR_BLOCKED`; aucun autre run hébergé n’est autorisé par cette décision.
