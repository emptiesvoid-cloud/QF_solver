# WP-E01-AW — Rapport de campagne FEM Newton–Armijo

Date : 2026-10-23
Worktree : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag`
Branche : `codex/wp-e01-ag-docker-native-fem-vnv`

## Verdict consolidé

La campagne a passé BUILD, FREEZE, PREFLIGHT et COLLECT, puis a effectué une seule phase RUN supervisée. Le solveur a réellement assemblé le problème TET4 avec contact GF4 et pris des décisions Newton–Armijo. Les deux replays déterministes ont observé le rejet du pas complet, puis l’acceptation d’un pas réduit.

Le worker a ensuite terminé chaque replay en `ERROR` sur une `InputValidationError` : l’image ne contient pas `qualification/requirements.json`, requis par la construction de l’audit. Le reçu brut agrégé est `FAIL` et le processus a terminé avec le code 1. Ce résultat est une erreur de configuration d’image, pas une preuve de non-convergence numérique. Il ne satisfait pas les critères finaux du scénario et ne constitue pas un certificat Armijo.

| Gate / statut | Résultat |
|---|---|
| BUILD | `PASS` — image Linux/amd64 construite et épinglée |
| FREEZE | `PASS` — manifeste RUN vérifié, 533 empreintes scientifiques concordantes |
| PREFLIGHT | `PREFLIGHT_PASS` |
| COLLECT | `COLLECTION_ACCEPTED`, 1 nœud autorisé sur 1, corps scientifique non exécuté |
| RUN brut | Worker `FAIL`, code de sortie 1; deux replays terminés par `InputValidationError` |
| Interprétation d’exécution | `ERROR_CONFIGURATION` — registre de qualification absent de l’image |
| Confinement Docker | `VERIFIED_BOUNDED` pour cette invocation et ce profil |
| Newton–Armijo observé | Rejet de `α=1` et `α=0.5`, acceptation de `α=0.25`, puis trois acceptations de `α=1` |
| Convergence/équilibre final | `NOT_ESTABLISHED` — aucun résultat final complet retourné |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `EXECUTED_PARTIAL` — assemblage physique et chemin Newton–Armijo exercés, scénario incomplet |
| `INCREMENTAL_NEWTON` historique AA | `VERIFIED_BOUNDED` — campagne synthétique antérieure, preuve distincte |
| Qualification scientifique générale | `NOT_ACQUIRED` |

L’autorisation RUN de WP-E01-AW a été consommée par cette invocation unique. Aucun retry n’a été exécuté ni n’est autorisé par ce rapport.

## Identité et gel

Le gel scientifique reprend le correctif AV : commit `bdec1cb5874d0b03ddd977263679336cd0a8e7c4`, tree `da09256da0e7b9fb4fa10ae653f6c06e04898e9f`. Le HEAD documentaire avant l’exécution était `32fc8e33349a101484f786c66aa93cf947bff6d4`, tree `284a9aa33e80a547259e87c8967bc454443626fa`. Le rapport ci-présent est uniquement documentaire; les identités d’exécution demeurent celles-ci.

Identifiants de campagne :

* PREFLIGHT : `WP-E01-AW-PREFLIGHT-20261023-15620DAD174A4CC09A89C4E35E58B9E0`
* COLLECT/RUN : `WP-E01-AW-COLLECT-20261023-7492035166364F328883E2EF2759B237`
* Scénario : `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`
* Nœud unique : `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`

| Artefact | SHA-256 / identité |
|---|---|
| Image effectivement utilisée, tag `qfsolver-e01-vnv:aw-20261023`, Linux/amd64 | `sha256:4fea3c029ee7bfb2ee509590d74ef2ed5f7779bdeb3a96d32622668b3ea61638` |
| Manifeste PREFLIGHT | `a414ff71f2b66eaaaa212cc43de44b5142b43375d476911ada4ce782a13863e6` |
| Manifeste COLLECT | `38ce13a5db27b6c2323c1460126b1be401b600b1cc6dbe6c209a6dce53ce7512` |
| Manifeste RUN | `e14102c361efcb63dbbb3a3cdc4c996964af8b725d6aab92dec71f6e84f59871` |
| Worker Docker gelé | `7b8e0271e9b34c2613f40f44fca9fe76a001c5236be6cfb826861f5f031d8717` |
| Superviseur hôte utilisé pour RUN | `5293ae0f346798804212dbe161e857665d66489e734ee5de78e4c80ae9fdbdc1` |
| Dockerfile | `e7647801586c6d83ae6ecc1e3f4a72780e87f68f6eac0e48b6e672386eb4181f` |
| Docker ignore | `b1f160fb6cacd787a3400bcc1a768a06e3e1d422c2a7515dd311167bc29f37af` |
| Verrou de dépendances | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |
| Module du test ciblé | `8a0016415fb39872d418ac06beea03aa9ca8506126b997a3e9c0455c491f02a0` |
| Protocole GF4 | `548d7d21009020b6065ce1c3383e65b6f63fd26e7493092c1c82e59e29bf1362` |

Le manifeste RUN lie le reçu `COLLECTION_ACCEPTED` et utilise l’identifiant Owner `WP-E01-AW GO-RUN`. La carte des sources contient 533 entrées; la vérification locale finale a trouvé 0 fichier manquant et 0 divergence pour ces entrées. Les sources mécaniques et les critères scientifiques n’ont pas changé après le gel. La correction du superviseur après COLLECT ne concerne que le choix/contrôle du reçu RUN; elle n’a changé ni le worker, ni les sources scientifiques, ni le reçu COLLECT. Le manifeste RUN pinne le nouveau hash du superviseur.

Commits associés à la préparation d’exécution :

* `a6dd6887064b771f33dd1913db9bf11964993036` — validation du reçu RUN par le superviseur hôte;
* `32fc8e33349a101484f786c66aa93cf947bff6d4` — gel du manifeste RUN.

## PREFLIGHT et COLLECT

Le PREFLIGHT a confirmé Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1 et les dépendances gelées. Le readback conteneur indiquait réseau limité à `lo`, UID 10001, racine en lecture seule, absence du socket Docker, écriture refusée dans la racine, limites cgroup mémoire de 1 Gio, CPU `200000 100000` (2 CPU) et processus `1/64`. Le conteneur de préflight a été nettoyé.

COLLECT a observé exactement le nœud autorisé. Le worker a confirmé `COLLECTION_ACCEPTED`; pytest a terminé avec code 0 en mode collecte uniquement. Le conteneur a été supprimé, sans corps de test exécuté.

Hashes des preuves de phases :

| Preuve | SHA-256 |
|---|---|
| Reçu worker PREFLIGHT (fichier `docker_preflight.json`) | `f31c2d31f161349790c7af2b4e145d6a7e7686a78e16944260c1c472b5762842` |
| Reçu hôte PREFLIGHT | `e3ed3c930a38f32a89202842f57054a00edf40b21a1604d30160e071aab5e1c4` |
| Logs PREFLIGHT | `89a709105ce276108894242348e37614585565a77cb37751f6a37f6f0da26d30` |
| Reçu worker COLLECT, fichier brut | `ac5fe8dc10eca8defd8d09dc5ea374c9ba8a0b1ed9b91af56ab436dace5c8bbc` |
| Digest canonique interne du reçu COLLECT | `be9b54590b2ade627613b415c3e79f1b74d4da2ee2ae24487363171f95a86a0f` |
| Reçu hôte COLLECT | `432f8be281128f518c8af072a3743f8b6cee72c1f5c64b4f9d674892a697d901` |
| Logs COLLECT | `2a744ded8ba82279aae205f553d4b349a6ab72dc21a491e2554cec48b02ec633` |

Les preuves sont conservées hors du worktree sous `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\`.

## RUN : observations numériques

Le RUN supervisé a été invoqué une seule fois. Il a terminé en environ 2.872493 s côté hôte; le conteneur a terminé avec code 1, sans timeout ni OOM. Le protocole gelé a exécuté deux replays dans cette invocation, et non deux tentatives après échec.

Les historiques numériques observés sont identiques pour les deux replays :

| Itération | Mérite initial (N) | Essais `α → mérite (N)` | Décision |
|---:|---:|---|---|
| 1 | `0.8660254037844386` | `1 → 13.043364313475424`; `0.5 → 3.7854140850566926`; `0.25 → 0.6016607470874248` | rejets de 1 et 0.5; acceptation de 0.25 après 2 réductions |
| 2 | `0.6016607470874248` | `1 → 0.08581211766875732` | acceptation de 1 |
| 3 | `0.08581211766875732` | `1 → 0.00014075840786308667` | acceptation de 1 |
| 4 | `0.00014075840786308667` | `1 → 2.182020284783493e-12` | acceptation de 1 |

Les seuils Armijo calculés pour les quatre étapes étaient respectivement `0.8659388012440602`, `0.6016005810127161`, `0.08580353645699045` et `0.00014074433202230035 N`; chaque essai accepté satisfaisait le seuil enregistré. Chaque replay a enregistré quatre résolutions directes SciPy, marquées convergées. Les normes de résidu des systèmes linéaires étaient environ `1.36e-15`, `2.72e-18`, `1.30e-18` et `2.80e-20`.

Le worker a enregistré 12 observations d’assemblage par replay. Les états d’essai GF4 observés utilisaient le schéma `gf4_contact_state/v1` à trois points. Les vérifications de non-mutation pendant les probes et l’immutabilité de l’état accepté étaient vraies. Ces observations décrivent les états provisoires des évaluations Armijo; elles ne remplacent pas un état final accepté ni un bilan global.

Les deux signatures scientifiques sont identiques : `ace2b31e900f4b95af71c8d6426d0f0500a62daa6af5ed8f1e46883003606210`. Le worker a indiqué `deterministic_replay_equal=true`. Les durées opérationnelles sont conservées séparément et ne participent pas à cette signature.

Les contrôles suivants sont restés faux : `converged_under_frozen_relative_tolerance`, `final_load_factor_is_one` et `single_accepted_commit`. L’observateur de transaction a rapporté un commit (digest avant `020607b81f8f816fce627ee69d4b1838010f392141eb4501f9a0c063af768a60`, digest après `2b2a095612551684571ffeb73072e66d639616b838b6a1f797b26e84ff4ff259`), tandis que le champ séparé `accepted_state_digest` vaut `e8b28f1a6094d26144ce6d9e58a90c0ed49e9d443ed3b9f450f275cb803449e5`. Cette divergence n’est pas résolue par les preuves présentes. Aucun `SolveResult` final n’a été reçu; déplacements finaux, réactions, résidu relatif final et état final de convergence sont absents.

Les champs `support_force_balance_residual_n` à zéro dans certaines observations appartiennent aux diagnostics de contact, et ne sont pas une mesure des réactions globales d’appui. Le prédicteur de référence disponible est le prédicteur linéaire TET4 ouvert, explicitement réservé au contrôle de conception; il ne constitue pas une solution indépendante du problème non linéaire avec contact.

## Cause de l’erreur et interprétation scientifique

Le worker rapporte pour les deux replays :

`InputValidationError: Cannot load qualification registry /opt/qf/qualification/requirements.json: [Errno 2] No such file or directory`

Le fichier existe sur l’hôte (`qualification/requirements.json`, SHA-256 `11346b0466a3849bf67fde066354909795dc28cb826f4b9fb6e9e4a30ed25a0e`), mais il est absent de l’image : le Dockerfile ne le copie pas, et la whitelist du `.dockerignore` ne comprend que les entrées `qualification/0_2_12` prévues. Le code fixe `DEFAULT_REGISTRY` à ce chemin dans `src/solveur/verification/traceability.py:15`; `QualificationRegistry` lève l’exception en cas d’absence (`:184–193`). La création de l’audit appelle `qualification_metadata` (`src/solveur/core/audit.py:438`), qui demande les métadonnées de traçabilité (`src/solveur/core/qualification.py:154–167`).

Le reçu ne contient pas de traceback Python. Le lien exact entre l’exception observée et la création de l’audit est donc corroboré par le message, les sources et la revue indépendante, mais le frame runtime précis reste non enregistré. Le résultat brut worker est conservé sans réécriture : `result=FAIL`, `status=FAIL` pour chaque replay, avec `solve_outcome.kind=SOLVER_EXCEPTION` et `solve_outcome.status=ERROR`. La classification de campagne est `ERROR_CONFIGURATION`, car cette exception empêche l’obtention d’un résultat final vérifiable; les observations montrent que les opérations Newton–Armijo et les assemblages ont néanmoins eu lieu avant l’erreur.

## Confinement RUN et preuves

Le conteneur RUN était non-root (UID 10001), réseau `none`, racine en lecture seule, `cap-drop ALL`, `no-new-privileges`, sans socket Docker, `/tmp` isolé, répertoire de résultats dédié writable et montages du manifeste et du reçu COLLECT en lecture seule. Les limites effectivement configurées/readback étaient mémoire et swap à 1 Gio, quota CPU 2 et 64 PID maximum. Le pic mémoire cgroup mesuré était `203,984,896` octets; un processus était observé. Le watchdog n’a pas expiré. Le conteneur a été confirmé supprimé (`REMOVED_CONFIRMED_NOT_FOUND`) et une vérification Docker ultérieure ne trouve plus son ID.

Références des preuves RUN : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AW-COLLECT-20261023-7492035166364F328883E2EF2759B237\RUN\`.

| Fichier | SHA-256 |
|---|---|
| Reçu worker brut `run_receipt.json` | `5f8996e054364b83d52da6c1f0cf2ddac9b577cd2af677274442482025493e9e` |
| Digest canonique interne du reçu worker | `b82f8f4745187f9ac2e47a8391e9dad7e154a0db5a3d2f7a433e4c2ed8a9d6cc` |
| Reçu hôte | `5dae8b04555ee529a1c96324304851e0c2ceda0238975e813efe06c593cdb365` |
| Logs Docker combinés | `9e10bb62497c30a711889cf086f468256a6556815bc48a1171359f6c0233f4ba` |
| Stdout worker | `a41266b6265991c702f1ee4a0e90e3fed0d00ba63732da966ea1f4ed5b7de5b3` |
| Stderr worker (vide) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Configuration Docker inspectée | `df567545ca0e8e6637997b53d9b57e289d42400cb99fa65bdfa3bb5a3aa2d239` |

Le digest canonique dans le reçu worker a été recalculé depuis son contenu JSON; il correspond. L’hôte a reconnu le reçu conforme comme artefact d’exécution, a enregistré `status=COMPLETED`, `worker_accepted=true`, `scientific_result=FAIL`, `exit_code=1`, `timed_out=false`, `oom_killed=false`, puis a confirmé le nettoyage. « COMPLETED » décrit la phase supervisée, pas une réussite scientifique.

## Revue indépendante

Un reviewer distinct a effectué une revue en lecture seule des données post-RUN, des signatures, du chemin d’erreur et de la configuration. Il confirme :

* le rejet de `α=1` et `α=0.5`, puis l’acceptation de `α=0.25` sont effectivement observés;
* les replays ont des signatures identiques, avec les timings gardés hors de la signature;
* la classification scientifique doit rester `ERROR` de configuration; le `FAIL` agrégé brut ne prouve pas une non-convergence;
* les informations finales de solution, réactions et convergence sont absentes; la divergence de digest du commit ne doit pas être interprétée;
* le registre de qualification manquant est un finding P1 de packaging pour toute exécution complète ultérieure; aucun P0 n’est relevé.

La revue ne remplace pas les mesures manquantes et n’accorde aucune qualification.

## Suite nécessaire — nouvelle campagne uniquement

L’identifiant RUN AW est consommé. Ne pas corriger l’image et réutiliser son autorisation. Une campagne suivante nécessitera un nouveau GO Owner, un nouveau gel et des identifiants inédits. La correction infrastructurelle candidate est d’inclure et pinner `qualification/requirements.json` dans la fermeture de sources/image (Docker ignore, Dockerfile, carte de sources, manifeste, vérifications worker/hôte) puis de vérifier la fermeture de toute ressource de registre requise. Il faut reconstruire une image Linux/amd64 et refaire revue, PREFLIGHT, COLLECT et RUN sous de nouvelles identités. Aucun seuil, modèle ou critère scientifique ne doit être modifié pour masquer cette erreur.

Le résultat existant reste :

* `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`
* `NATIVE_FEM_VNV=EXECUTED_PARTIAL`
* `SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`
* `AUTHORITATIVE_INTEGRATION=PENDING`
* `PUBLIC_RELEASE=NOT_AUTHORIZED`
