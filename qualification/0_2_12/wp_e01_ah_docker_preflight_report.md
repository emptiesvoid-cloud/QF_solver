# WP-E01-AH — correction d’identifiant et préflight Docker

Date : 2026-10-22
Branche : `codex/wp-e01-ag-docker-native-fem-vnv`
Baseline AH : `9290a925f5d73197236f74d19e2bbec6735fdcd4`
Tree baseline : `6d36fbfa0564ff9f752f873b0c12342f80a07f42`

## Résultat

Le scénario canonique est `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`. Cette valeur est identique dans `experiments/wp_e01ag_docker_worker.py` et `experiments/wp_e01ad_execution_contract.py`; le nœud allowlisté reste `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`. Le module de test est un stub de collecte qui refuse l’exécution directe; l’identité physique est définie par le contrat/worker et ses entrées de modèle. La variante avec tiret présente dans le manifeste AG était une faute de transcription.

J’ai modifié uniquement le champ `target.scenario_id` du manifeste et recalculé son sidecar SHA-256. Worker, sources scientifiques, test, paramètres Newton–Armijo, tolérances et références sont inchangés. Le manifeste est monté en lecture seule et ne fait pas partie de l’image; l’image existante n’a donc pas été reconstruite.

Le préflight Docker AH a réussi avec reçu `PREFLIGHT_PASS`. Le worker a validé le manifeste et les 533 hashes de son inventaire, puis contrôlé l’environnement et les limites. Le conteneur a terminé normalement et a été supprimé. Aucun pytest, collecte, modèle FEM, assemblage, Newton ou Armijo scientifique n’a été exécuté.

## Identités gelées

| Élément | Identité |
|---|---|
| Commit de correction manifeste | `d7964730843396dc1cabf5e0781922a0e29cc577` |
| Tree du commit | `4365091cd787846f2edfff15f852aaf9d69be675` |
| Manifeste AH | `ff78e668206ef2deabaf4dcd3a099b7ec33725fc9b9fda0126f26a63303d6cab` |
| Sidecar manifeste | `183d153b0259b8dd669d23c5c8c05ef28f66392222d050ee4631841289d2fe5d` |
| Worker inchangé | `20167b10c8d5703d1aeab0187068b8f8aef44c517aa526c8179952ac3a5129ba` |
| Superviseur hôte inchangé | `35be480b46d1375d2f78ae1d8b21663055669d574f3ac429fd30b1cd364b9ef3` |
| Image | `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5` |
| Dockerfile | `e7647801586c6d83ae6ecc1e3f4a72780e87f68f6eac0e48b6e672386eb4181f` |
| Lock des dépendances | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |

Le source HEAD/tree scientifique demeure ancré sur `5826b784e580936da77017941a4f2d23e76f7a44` / `bf55fbd9779c34f47033577943a7e30b811f220d`; le commit AH n’ajoute que le manifeste et son pin. Les 533 hashes sources ont été vérifiés par le worker avec succès.

## Vérification runtime observée

Commande exécutée une seule fois : `experiments/wp_e01ag_docker_host.ps1 -Phase PREFLIGHT` depuis la racine fixe du worktree.

- Reçu hôte : `COMPLETED`, `worker_accepted=true`, code de sortie `0`, timeout faux, OOM faux; durée observée 1.614 s.
- Nettoyage : `REMOVED_CONFIRMED_NOT_FOUND`; conteneur `04d71b3c9cb8f520e5d5e0f844f40e4571ffe5b1e2bbe626dc19e42973839e0b`.
- Image utilisée : `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5`.
- Configuration Docker inspectée : réseau `none`, rootfs lecture seule, utilisateur `10001:10001`, `cap-drop ALL`, `no-new-privileges`, mémoire 1 Gio, swap plafonné à 1 Gio, quota 2 CPU, PID 64, `/tmp` tmpfs 128 Mio `noexec,nosuid`; seuls le manifeste RO et le dossier `/results` RW sont montés.
- Readback interne cgroups : `memory_max=1073741824`, pic mémoire `47190016` octets, `memory_swap_max=0`, `cpu_max=200000 100000`, `pids_max=64` (1 PID observé).
- Contrôles internes : UID 10001; écriture rootfs refusée; socket Docker absent; interface réseau `lo` seulement; écriture temporaire et résultats disponible.
- Runtime : CPython 3.13.1; versions vérifiées des dépendances NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1, Matplotlib 3.10.3 et transitives conformément au lock. Les imports de bibliothèques ont servi au contrôle de runtime; aucun import du solveur ni calcul scientifique n’a eu lieu.

Ces éléments vérifient le profil de confinement E01 pour le préflight borné observé. Ils ne qualifient pas une isolation générale au-delà des contrôles Docker/runtime listés.

## Preuves archivées et empreintes

Les fichiers AH sont sous `qualification/0_2_12/wp_e01_ah_evidence/`. Les anciens reçus AG ont été conservés sous `previous-ag-preflight/`; le dossier hôte AG a été renommé `PREFLIGHT_AG_HISTORICAL` afin que le superviseur, qui refuse la réutilisation d’un répertoire non vide, puisse créer le dossier AH vierge. Aucun reçu historique n’a été supprimé.

| Preuve AH | SHA-256 |
|---|---|
| `preflight/docker_preflight.json` | `21afc53f11ac8efc5548e69e4221a04db8b43ccf9a4aa265e24b1d0b63f5684c` |
| `preflight/host-receipt.json` | `24ffb6f91ae5a0077db6ca326c69980a8aa62d90ef8225484c581f6494ec564a` |
| `preflight/host-receipt.pending.json` | `2115d1f35981fe6e3f0282bca041e528a242bd12c4a99f1f0064dcbc3d73408b` |
| `preflight/container-config.json` | `9093ac031cade26fa24c3c0290874fc8ad991ea95ef2910b4b58dfa7a2924d32` |
| `preflight/docker-combined.log` | `f355754c5275230466a41dcc3d256db97280b35d1706d0c6934339e84a2d7dc7` |
| `preflight/worker.stdout.log` | `62e6ccec5febb9418040d83c84bbfcaf805e15a1990744b3ad2d9fe775e63380` |
| `preflight/worker.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Copie du manifeste | `ff78e668206ef2deabaf4dcd3a099b7ec33725fc9b9fda0126f26a63303d6cab` |

Le préflight AH n’a pas exigé de nouvelle revue indépendante du code : worker et superviseur sont inchangés. La revue AG indépendante portait sur leurs contrôles statiques; le reçu AH ajoute ici l’observation runtime du préflight.

## Statuts

- `SCENARIO_IDENTITY`: `CORRECTED_AND_VERIFIED`
- `DOCKER_PREFLIGHT`: `ACCEPTED`
- `INFRASTRUCTURE_DOCKER`: `VERIFIED_BOUNDED` (préflight uniquement)
- `COLLECT`: `NOT_RUN` — non autorisé par AH
- `RUN`: `NOT_RUN` — non autorisé par AH
- `NATIVE_FEM_VNV`: `NOT_RUN`
- `PRODUCTION_ARMIJO_CERTIFICATE`: `NOT_VERIFIED`
- `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`

## Proposition de collecte

Après une autorisation Owner distincte, le superviseur fixe peut être invoqué avec `-Phase COLLECT`. Il n’acceptera cette phase que si un nouveau manifeste gelé porte l’autorisation COLLECT correspondante. L’allowlist reste le seul nœud mentionné ci-dessus. AH ne fournit pas cette autorisation; aucune collecte n’a été lancée. Un futur RUN nécessitera encore un GO-RUN séparé et un reçu COLLECT accepté. La référence d’équilibre indépendante du contact GF4 reste à résoudre ou à exclure explicitement de la portée scientifique avant RUN.
