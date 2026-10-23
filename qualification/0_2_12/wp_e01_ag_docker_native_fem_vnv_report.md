# WP-E01-AG — migration Docker et V&V Newton–Armijo

Date : 2026-10-22
Worktree : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag`
Branche : `codex/wp-e01-ag-docker-native-fem-vnv`

## Résultat

La migration a produit une image Linux E01 dédiée et un profil de conteneur supervisé. Le préflight final a créé puis supprimé un conteneur avec les paramètres Docker inspectés, mais le worker a refusé le manifeste avant son contrôle d’environnement et avant l’import de pytest, NumPy, SciPy ou du solveur. Le refus est dû à une divergence exacte de `scenario_id` entre le manifeste et le worker. Aucun COLLECT n’a eu lieu; aucun assemblage FEM, Newton ou essai Armijo n’a été exécuté.

Les trois cycles de correction statique autorisés ont été consommés : (1) fermeture d’empreintes, identité du montage des résultats et preuve de nettoyage; (2) chemin du manifeste; (3) syntaxe Docker du bind writable. Le dernier blocage est précisément identifié, mais je ne modifie pas une quatrième fois l’identité dans ce mandat.

| État | Résultat |
|---|---|
| `INFRASTRUCTURE_DOCKER` | `NOT_VERIFIED` — configuration hôte inspectée, reçu de préflight worker refusé |
| `GO-DOCKER-PREFLIGHT` | Tenté; refus final conservé |
| `COLLECT` | `NOT_RUN` |
| `RUN` | `NOT_RUN` — aucune autorisation RUN distincte |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `INCREMENTAL_NEWTON` | `VERIFIED_BOUNDED` — historique AA synthétique uniquement |
| `GENERAL_SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `AUTHORITATIVE_INTEGRATION` | `PENDING` |
| `PUBLIC_RELEASE` | `NOT_AUTHORIZED` |

## Baseline, préservation et commits

Le worktree a été créé sur la baseline demandée : HEAD `ce62002e9a4d9f67c7f595e25bac5ef271dfb9de`, tree `c8709917cdad6cebb4b8946efa64329c059b8f24`, origine `https://github.com/emptiesvoid-cloud/QF_solver.git`. Le rapport AF existant a conservé son SHA-256 attendu `3edfb7e0cca452e8959f517649b70ea280c6242486af0998863484e5503c6814`.

Les commits d’implémentation/fix sont :

- `5826b784e580936da77017941a4f2d23e76f7a44` — worker, superviseur, image, lock et cible de collecte;
- `75658809ab203088de469bce30733938e9e4e32e` — manifeste PREFLIGHT initial et sidecar;
- `520c84920838bea83d8953347c75bf48a6ef6ecd` — correction du nom de chemin du manifeste;
- `132ac8f30489be1f5fc815e25a39f4c7e1f0f72b` — syntaxe du montage Docker results.

HEAD avant le présent rapport : `132ac8f30489be1f5fc815e25a39f4c7e1f0f72b`; tree : `30c0681fafbac8da5ee809a2022dbb307ac728ac`. Les sources mécaniques de production sous `src/` n’ont pas été modifiées. Les preuves AA–AF n’ont pas été réécrites.

## Réutilisation D01 et image E01

Un profil Docker D01-AS a été trouvé dans le worktree dédié `C:\wpc01-frictionless-public-integration-wp-d01-as-docker` (HEAD consulté `92097a32aea6dbb78649f8db75f3f7495b05a6c0`). Son rapport indique PREFLIGHT réussi et COLLECT accepté, avec RUN bloqué par un finding P1. Son image utilise la même base Python 3.13.1 slim Bookworm; cette base et ses motifs de supervision/confinement ont été réutilisés. Aucun worker, manifeste ou contrat scientifique D01 n’a été repris.

Image construite : `qfsolver-e01-vnv:ag`, plateforme `linux/amd64`, image ID/digest local `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5`. Base : `python:3.13.1-slim-bookworm@sha256:031ebf3cde9f3719d2db385233bcb18df5162038e9cda20e64e08f49f4b47a2f`. Le build a installé les 17 versions exactes du lock (NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1, Matplotlib 3.10.3 et transitives). Les versions n’ont pas été relues dans un préflight worker accepté; il s’agit de la preuve de build, pas d’une vérification de runtime réussie.

L’image contient un snapshot du dossier `src/` et les entrées fixes du protocole/test/guard/worker. Le manifeste pinne exactement 533 fichiers (526 fichiers suivis sous `src/`, plus 7 fichiers fixes). L’hôte et le worker rejettent une carte incomplète ou excédentaire; l’image ne monte aucune source hôte.

## Profil et scénario préparés

Le profil `E01_PHYSICAL_FEM_BOUNDED` est fermé par défaut et ne sélectionne qu’un nœud. Le worker a une interface de phase fixe `PREFLIGHT`, `COLLECT`, `RUN`; il n’accepte ni commande arbitraire ni chemin de test fourni par l’appelant. La cible pytest est enregistrée `NATIVE_AUTH_REQUIRED`; son corps appelle un refus explicite et ne constitue pas un chemin d’exécution FEM. COLLECT est prévu via `pytest --collect-only` sur ce seul nœud, plugins externes désactivés.

Le RUN préparé construirait un seul TET4 physique en petites déformations avec matériau isotrope linéaire et contact pénalisé GF4 sur une face régulière. La non-linéarité d’équilibre provient du contact, pas d’un Hencky ou d’un J2 matériel. Les paramètres enregistrés sont : 30 itérations Newton; 14 réductions, soit au plus 15 évaluations de pas; tolérance relative `1e-9`; Armijo `c=1e-4`; alpha minimum `1e-4`; un incrément de charge; replay déterministe prévu deux fois dans une invocation.

Le worker instrumente les résidus, corrections, évaluations alpha/mérite, assemblages, résumés linéaires et états trial/accepted, puis exige le rejet réel du pas complet, l’acceptation d’un alpha réduit, la convergence, un unique commit et la stabilité du replay. Ces éléments sont seulement `IMPLEMENTED_BY_SOURCE`; rien n’a été mesuré.

La seule référence préparée est le prédicteur analytique TET4 ouvert (sans contact), utilisé comme contrôle de conception pour l’ordre de grandeur de fermeture. Ce n’est pas une solution indépendante d’équilibre du problème de contact. Une future revue/run ne devra pas présenter ce prédicteur comme référence de l’équilibre non linéaire; il faut encore une référence physique indépendante ou limiter explicitement la conclusion à la trajectoire observée du solveur.

## Confinement et supervision

L’image et le superviseur configurent : réseau `none`; racine en lecture seule; UID/GID `10001`; `cap-drop ALL`; `no-new-privileges`; 1 Gio mémoire et swap plafonné à 1 Gio (swap effectif attendu nul); quota CPU 2 (`NanoCpus=2,000,000,000`); 64 PID; `/tmp` tmpfs 128 Mio avec `noexec,nosuid`; uniquement le bind `/results` writable et le manifeste read-only. Le socket Docker, les credentials, les home folders, les sources hôte et les autres worktrees ne sont pas montés. Un watchdog hôte de 120 s attend le conteneur, le tue en cas de timeout et n’effectue aucune reprise. Le superviseur exige que le nettoyage soit confirmé par une réponse Docker explicite `No such object/container`.

Le reviewer indépendant avait initialement trouvé trois P1 de source (fermeture d’empreintes, identité du montage results, nettoyage). Ils ont été corrigés. La seconde relecture distincte a confirmé ces trois corrections, aucun P0/P1 résiduel dans ces contrôles, et a rappelé que l’image/manifeste devaient encore être créés avant préflight. Cette relecture était en lecture seule, sans Docker ni calcul.

## Chronologie des préflights et diagnostics

1. **Tentative 1 — identité de chemin.** Arrêt avant inspection d’image/création de conteneur : le superviseur attendait `wp_e01_ag_runtime_manifest.json`, le fichier gelé s’appelait `wp_e01ag_runtime_manifest.json`. Évidence préservée sous `wp_e01_ag_evidence/attempt-01-manifest-path/`.
2. **Tentative 2 — syntaxe `--mount`.** L’image et le manifeste ont passé la lecture hôte; `docker create` a refusé le jeton `rw` isolé (`invalid field 'rw' must be a key=value pair`). Aucun conteneur créé. La syntaxe a été corrigée en omettant ce jeton; le droit RW est ensuite vérifié par inspection (`RW=true`). Évidence sous `attempt-02-docker-create/`.
3. **Tentative 3 — worker préflight.** Le conteneur a été créé conformément au profil, démarré, puis sorti avec code 78 et a été supprimé. Le reçu hôte indique `timed_out=false`, `oom_killed=false`, `cleanup=REMOVED_CONFIRMED_NOT_FOUND`, durée mesurée 0.638 s. Docker inspect a relu `NetworkMode=none`, `ReadonlyRootfs=true`, UID `10001:10001`, cap-drop ALL, no-new-privileges, mémoire 1,073,741,824 octets, `MemorySwap=1,073,741,824`, `NanoCpus=2,000,000,000`, 64 PID, tmpfs `/tmp` et les deux montages attendus. Le worker a écrit `{"event":"REFUSED","reason":"target differs from the single fixed scenario"}`. Aucun `docker_preflight.json` n’a été produit.

La comparaison locale, sans pytest ni import scientifique, reproduit le refus : le manifeste contient `scenario_id = WP-E01_AB_GF4_TET4_PRESSURE_18_75_PA`, tandis que le worker fixe `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`. Les node ID, module et classification sont identiques. Le refus arrive dans `_load_manifest`, avant `_container_checks`, import de pytest, NumPy/SciPy/Matplotlib, import solver, construction de modèle, assemblage, Newton ou Armijo. C’est un échec d’identité manifeste/worker, pas un échec scientifique.

Les reçus, la configuration Docker inspectée, le stderr du worker et les trois manifestes/échecs sont archivés dans `qualification/0_2_12/wp_e01_ag_evidence/`. Le stderr final SHA-256 est `f063487a7ec2d12b8b8723a70ed526d3acf8d78530497668cfd09db9efa50dfe`; le reçu hôte final SHA-256 est `407265cde4f01d882b810299d619419f933ee716e9295bce3361f57a8fc196d6`; la config inspectée SHA-256 est `3107866022ebe8e5040179ff03819751425bdaecf6da3ec14edda5490d3c5439`.

## Revue scientifique et limites

La revue indépendante précédente confirme la parité de la fixture AB et la pertinence du nœud réservé à la collecte. Elle qualifie toutefois le modèle comme une expérience élastique avec non-linéarité contact GF4; il ne démontre pas la plasticité J2 ou la loi hyperélastique Hencky. Le prédicteur ouvert ne constitue pas un oracle d’équilibre contact indépendant. Ces limitations empêchent toute qualification globale et devront figurer dans tout GO-RUN.

Aucune courbe de résidu, valeur de mérite, décision Armijo, coefficient accepté, réaction, déplacement, erreur de référence, nombre d’assemblages ou factorisations n’a été calculé. L’inspection Docker hôte établit la configuration de création du conteneur et son nettoyage, mais le worker ayant refusé avant `_container_checks`, les readbacks internes cgroups/interfaces/UID et les versions runtime n’ont pas obtenu de reçu accepté. Je ne classe donc pas l’infrastructure runtime E01 comme vérifiée.

## Identités finales et statut

Identités pertinentes :

| Artefact | SHA-256 |
|---|---|
| `experiments/wp_e01ag_docker_worker.py` | `20167b10c8d5703d1aeab0187068b8f8aef44c517aa526c8179952ac3a5129ba` |
| `experiments/wp_e01ag_docker_host.ps1` | `35be480b46d1375d2f78ae1d8b21663055669d574f3ac429fd30b1cd364b9ef3` |
| `Dockerfile.wp_e01ag` | `e7647801586c6d83ae6ecc1e3f4a72780e87f68f6eac0e48b6e672386eb4181f` |
| `Dockerfile.wp_e01ag.dockerignore` | `b1f160fb6cacd787a3400bcc1a768a06e3e1d422c2a7515dd311167bc29f37af` |
| `requirements/wp_e01_ag.lock` | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |
| `tests/conftest.py` | `895c816a1739301be7f1011966fd36d94efb6e4fc2bee66bdc0bb278c3e9b81c` |
| cible pytest fixe | `8a0016415fb39872d418ac06beea03aa9ca8506126b997a3e9c0455c491f02a0` |
| manifeste PREFLIGHT final | `eca8a917135fc654aff97277f56c5ac576295f163a49af1e6fd8e588a8f87fa0` |
| AF report préservé | `3edfb7e0cca452e8959f517649b70ea280c6242486af0998863484e5503c6814` |

`COLLECT=NOT_RUN`; `RUN=NOT_RUN`; `NATIVE_FEM_VNV=NOT_RUN`; `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`; `AUTHORITATIVE_INTEGRATION=PENDING`; `PUBLIC_RELEASE=NOT_AUTHORIZED`.

## Décision Owner suivante

Autoriser une correction limitée du `scenario_id` dans le manifeste, avec nouveau SHA-256/sidecar et un nouveau préflight sous le même superviseur. Si le worker préflight est accepté, faire confirmer la revue de l’identité gelée puis utiliser le GO-COLLECT conditionnel pour une unique collecte du seul nœud allowlisté. Un GO-RUN explicite et distinct restera nécessaire après reçu COLLECT accepté. Avant tout RUN, approuver ou limiter la référence d’équilibre : le prédicteur TET4 ouvert n’est pas une référence indépendante du problème contact.
