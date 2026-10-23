# WP-E01-BA — Certificat borné Newton–Armijo du sous-système esclave

Date : 2026-10-23  
Branche : `emptiesvoids-cloud/wp-e01-ba-slave-bounded`

## Verdict

Le RUN supervisé satisfait le contrat prospectif strictement borné à `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED` : les deux replays passent les six contrôles requis, présentent la même signature scientifique, convergent au facteur de charge 1, committent un état accepté et ferment le bilan mécanique du corps déformable esclave avec les forces de contact GF4.

**`PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED`** pour le seul scénario, le maillage et le gel ci-dessous.

Le verdict brut global reste **`FAIL`** dans les deux replays et dans l’agrégat global. Le contrôle de provenance de la réaction du montage rigide demeure `WARNING / NOT_INDEPENDENTLY_MEASURED`, conformément au périmètre approuvé. L’équilibre du maître et de son montage reste **`NOT_VERIFIED`**; la qualification scientifique générale reste **`NOT_ACQUIRED`**. Le statut global n’est ni masqué ni transformé en PASS.

## Gel et provenance

Baseline Owner : HEAD `4b6e94af6999200455b849def1edff07fdf81b2a`, tree `26948e039ef266bb4d9ab9e4f7ee79dd30c039ce`. Le commit scientifique exécuté est `524c15a0355a3033d92f7a723b27e1ca5752d3bd`, tree scientifique `9d0820780d1499a8488d295c740f8debd767eeee`. Les commits documentaires de campagne sont `0b7bf290c50d93675d5bfca0a5d8924a320d92cb` et `67e0f02c4427dd6916309c1a6d06f921dd3fe34a`; HEAD avant le présent rapport : `67e0f02c4427dd6916309c1a6d06f921dd3fe34a`, tree `1cfc48185464df28fe2ae7288d44cadb61dfe6ae`.

Le dépôt est `https://github.com/emptiesvoid-cloud/QF_solver.git`. Les trois manifestes épinglent les mêmes **534 fichiers**. Vérification locale des octets contre le manifeste RUN : 534 entrées, 0 fichier absent, 0 divergence. Les contrôles ont également recalculé les SHA-256 des reçus et journaux; les valeurs concordent avec les reçus hôte. Le worker a validé à nouveau les pins à chaque phase.

| Artefact | SHA-256 / identité |
|---|---|
| Image `qfsolver-e01-ba-vnv` (`linux/amd64`) | `sha256:026266d6794175608d476510353573b1784fbdae073f8cedf7873f84121ac01c` |
| Manifeste PREFLIGHT | `16107fa6fe28a5ceef95ced290ee281dde84ab1f441e649c40b26673fa150b72` |
| Manifeste COLLECT | `0e5c38a957fb90a743b9254d02b0b85cb9d6ce7dfaee64dc18499703ba43040d` |
| Manifeste RUN exécuté | `1ba645f82f991918078bd13b7d46bc2ae4c6b42810973b49d72f9f0aefafc27e` |
| Worker `experiments/wp_e01ag_docker_worker.py` | `a653c1c0578ee00710c1163e0fb7a4b24dac4c15fc018c126a0da795f9b201ff` |
| Superviseur `experiments/wp_e01ba_docker_host.ps1` | `ea4aedfc32959ea137ba59026c63482b2aad9acd5d067bd6e41a997667b63f65` |
| Dockerfile | `3d7ae1eeb113376f192edd4868ac9d27a2c96a7e7c36b449b893deec03ca0fbf` |
| `.dockerignore` associé | `86b87b59f54d466a54edc8e53e709c88fcc5a8dce72e9aae4b34c8d39d2a721a` |
| Verrou dépendances | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |
| Registre `qualification/requirements.json` | `11346b0466a3849bf67fde066354909795dc28cb826f4b9fb6e9e4a30ed25a0e` |
| Test `tests/verification/test_wp_e01ag_physical_newton.py` | `8a0016415fb39872d418ac06beea03aa9ca8506126b997a3e9c0455c491f02a0` |

L’image utilise CPython 3.13.1, NumPy 2.2.6, SciPy 1.15.2 et pytest 8.4.1, entre autres dépendances verrouillées. Le scénario reste `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA` et le seul nœud autorisé est `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`.

## Construction, PREFLIGHT et COLLECT

BUILD a produit l’image épinglée ci-dessus. Le journal de build est conservé à `C:\wpc01-frictionless-public-integration-wt\wp-e01-ba-evidence\build-524c15a0.log` (SHA-256 `ac32caf07cffad28d7175fa80e9640d89c3a67e6847cf5e3db2ceb1bc8ff6790`).

| Phase | Identifiant | Résultat vérifié |
|---|---|---|
| PREFLIGHT | `WP-E01-BA-PREFLIGHT-20261023-94BB64469D6448E49227967C42CA01E4` | `PREFLIGHT_PASS`; code 0; reçu canonique vérifié; 534 pins; pic mémoire 22 003 712 octets; 1,4677 s; nettoyage confirmé |
| COLLECT | `WP-E01-BA-COLLECT-20261023-109AFC066630412E9626D4A5489115AB` | `COLLECTION_ACCEPTED`; exactement 1/1 nœud; `bodies_executed=0`; code 0; 3,5690 s; nettoyage confirmé |

Le SHA-256 du fichier reçu COLLECT est `c696eea8b6bcf99256f35c7303bb7d13bcae0f152e6e8e8ae9bfcb4d891b02d0`; son digest canonique, utilisé comme liaison par le manifeste RUN, est `9fb5801bba30a151b17f88559478391339420e34d1b62b00d26cae959b7099bd`. Le reçu hôte COLLECT est `8e8a24686f5bbae00b8a4111ac8eab29ca9bc8b1b75bf93bc0a5ab7cf65d4d95`.

## RUN supervisé

Une seule invocation RUN a été faite après `COLLECTION_ACCEPTED`; elle contenait les **deux replays déterministes prévus**, qui ne sont pas un retry. Aucun changement du code scientifique, du scénario, des seuils ou du manifeste n’est intervenu entre COLLECT et RUN.

Résultat superviseur : `COMPLETED`, `worker_accepted=true`, sortie 0, `scientific_result=PASS` pour le certificat nommé, `global_scope_result=FAIL`, aucun timeout ni OOM, nettoyage `REMOVED_CONFIRMED_NOT_FOUND`. Le conteneur `a233e4781fe7cd0018dd2b6681219a37e9d7047c04202f323aa74e520ff0fa76` est absent après la phase. Durée murale hôte : 3,0529 s.

Confinement observé : réseau `none`, système racine en lecture seule, UID/GID 10001, capacités supprimées, `no-new-privileges`, socket Docker absent, montages résultats seuls en écriture et manifeste/collecte en lecture seule. Limites effectives : mémoire 1 Gio, swap 0, quota CPU 2 cœurs (`200000/100000`), PIDs 64; lecture cgroup après calcul : pic mémoire 208 261 120 octets, un processus courant. L’interface réseau observée était seulement `lo`; l’écriture sur la racine a été refusée et les écritures temporaires/résultats autorisées ont fonctionné.

Reçus et journaux RUN :

| Preuve | SHA-256 |
|---|---|
| Reçu worker `run_receipt.json` (fichier) | `cc560b85f8d16df2c6b2b434206786196683f7e75b005c2fa38ff86a54b3eb19` |
| Digest canonique contenu dans le reçu worker | `030bf297d95251c8ebed88afbc2cef0fc0bdbc2eadf2b04f7a83029f2bfb4389` |
| Reçu hôte | `a1ea5d46c10daaf1df85b5fd73c9a43ec10046dd10419b25a599738eef88ade8` |
| Log combiné Docker | `6788e7e807a182f356777eaf449249faec561405fafec75be816e8158e3dfe6b` |
| stdout worker | `18397b31e4699a132815b649758fc5fd09c597524985626614526ed1ac859a1a` |
| stderr worker (vide) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Configuration Docker observée | `1e91ce29e629e37e47ec8e879c3dad19162453fba9736ac8b0bd6f23cf5337ac` |

Le digest canonique du reçu worker a été recalculé après retrait du champ `sha256`; le résultat correspond. Le hash brut du reçu worker égale celui épinglé dans le reçu hôte. Les hashes stdout, stderr et log combiné correspondent également au reçu hôte. Manifest RUN, reçu COLLECT et carte des 534 sources concordent avec le reçu RUN.

## Résultats numériques

Les deux replays donnent `solve_outcome=RESULT/PASS`, `status=PASS`, un facteur de charge final de 1, une seule étape de charge et un commit accepté. Chaque replay satisfait les sept assertions de scénario, notamment convergence sous la tolérance relative gelée, rejet du pas complet, acceptation du pas réduit, stabilité des états provisoires et commit unique.

### Newton–Armijo (premier replay; le second a la même signature)

Paramètres gelés : 30 itérations Newton maximum; 15 essais Armijo maximum; 14 réductions maximum; tolérance relative `1e-9`; coefficient Armijo `c=1e-4`; alpha minimal `1e-4`; une étape; solveur linéaire direct.

| Itération | α essayé | Mérite observé (N) | Seuil Armijo (N) | Décision |
|---:|---:|---:|---:|---|
| 1 | 1 | 13,043364313475424 | 0,8659388012440602 | rejet |
| 1 | 0,5 | 3,7854140850566926 | 0,8659821025142493 | rejet |
| 1 | 0,25 | 0,6016607470874248 | 0,866003753149344 | accepté, 2 réductions |
| 2 | 1 | 0,08581211766875732 | 0,6016005810127161 | accepté |
| 3 | 1 | 0,00014075840786308667 | 0,08580353645699045 | accepté |
| 4 | 1 | 2,182020284783493e-12 | 0,00014074433202230035 | accepté |

La norme résiduelle libre finale est `2,182020284783493e-12 N`, sous la tolérance relative `1e-9`; la séquence des normes est `[0,8660254037844386; 0,6016607470874248; 0,08581211766875732; 0,00014075840786308667; 2,182020284783493e-12] N`. Quatre itérations Newton et quatre résolutions linéaires ont été enregistrées. L’état a été commité exactement une fois (`commit_count=1`), au facteur de charge 1.

### Équilibre du corps déformable esclave

Convention enregistrée : forces physiques agissant sur le corps déformable; résidu `F_int - F_ext`; réactions égales aux résidus des DDL fixés; moments autour de l’origine globale en coordonnées de référence. Les charges extérieures sont trois charges nodales `UZ=-0,5 N`, soit `E=(0,0,-1,5) N`, `M_E=(-0,5;0,5;0) N·m`.

| Contribution au sous-système esclave | Force (N) | Moment de référence (N·m) |
|---|---|---|
| Charges extérieures `E` | `(0; 0; -1,5)` | `(-0,5; 0,5; 0)` |
| Réactions directes aux six DDL fixés `R` | `(-0,04630120354435955; -0,054915536897736185; 0,5040003347176439)` | `(0,14117500925783807; -0,14116639492448468; -0,003751586318383675)` |
| Contact GF4 appliqué à l’esclave `C_s` | `(0,046301203547404; 0,054915536897467684; 0,9959996652823566)` | `(0,3588249907421624; -0,35883360507551243; 0,003751586317045979)` |
| Résidu `E + R + C_s` | `(3,0444535781271043e-12; -2,685004996116902e-13; 5,551115123125783e-16)` | `(4,996003610813204e-16; 2,886579864025407e-15; -1,3376955793065193e-12)` |

La recomposition arithmétique hors ligne de ces vecteurs aboutit à une norme de résidu force d’environ `3,05627e-12 N` et de moment `1,33770e-12 N·m`. Erreurs relatives calculées par l’audit : force `2,0375137808189935e-12` sur l’échelle `1,5 N`; moment `1,337698787036916e-12` sur l’échelle `1,0 N·m`. Les critères gelés sont `<=1e-10 PASS`, `<=1e-8 WARNING` pour chacun. Les résidus libres (`2,18202e-12 N`) et ce bilan complet de l’esclave sont des contrôles distincts.

Le contact est affecté par ownership explicite aux trois points de quadrature GF4 externes sur l’esclave (zéro paire interne esclave–esclave). Trois points sont actifs, branche `STICK`; les pressions normales observées sont `2,3699891216765754`, `17,4899991632059`, `17,4899991632059 Pa`; la pénétration maximale observée est `0,000174899991632059 m`. La résultante de contact sur l’esclave et son moment sont ceux de la table. Le reçu enregistre action-réaction opposée sur la surface rigide, mais ne mesure pas indépendamment les réactions de son montage.

Les anciens champs « contact-blind » `E+R` restent présents : erreurs relatives force `0,6657242842315055` et moment `0,507475126989006`. Ils omettent le contact sur l’esclave et sont conservés comme diagnostic historique; le bilan prospectif BA ajoute `C_s` une fois et obtient les contrôles PASS. Ils ne sont pas effacés ni présentés comme le bilan contact-aware.

### État et reproductibilité

Pour les deux replays, le contrôle contact assure l’intégrité des états d’essai. Les trois lignes d’état acceptées et d’essai sont complètes; les digests acceptés/essai finaux valent `ccd0b11442b2a494df9ebfbeacd8539abad27e19823add6f1b308cb127f069d9`. Les assemblages de recherche linéaire ont conservé l’état accepté lors des probes; les probes rejetées n’ont pas modifié leur état d’essai avant/après. Un commit accepté a ensuite finalisé le pas.

Les deux signatures scientifiques sont identiques : `c086f9c59bcd6dea6d1855163c23f77e9bcc2a092a40cc17773e233571cdf3ce`; `deterministic_replay_equal=true`. Les timings restent archivés, mais ne font pas partie de cette égalité scientifique.

## Portée des verdicts

Les deux classifications de replay du certificat borné sont `PASS`; les six exigences du certificat (`newton_armijo_line_search`, `free_dof_convergence`, `accepted_state_finalization_and_commit`, `contact_trial_state_integrity`, `direct_slave_subsystem_force_moment_balance`, `two_replay_scientific_reproducibility`) sont toutes `PASS`. Le reçu worker et le reçu hôte donnent donc `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=PASS`, accepté par le superviseur.

Séparément, les classifications globales des deux replays et `global_scope_result` restent `FAIL`. Le `run_verdict` demeure `WARNING`, avec l’avertissement explicite `equilibrium:rigid_mount_reaction_provenance=NOT_INDEPENDENTLY_MEASURED`; la traceabilité de qualification générale `material-nonlinear` n’est pas un PASS. Ce résultat global fail-closed n’est pas contradictoire avec le certificat prospectif plus étroit : ce dernier autorise exactement le warning maître prévu et n’inclut pas l’équilibre maître/montage.

### Limites scientifiques restantes

- Le résultat porte sur le GF4 TET4, son chargement, ses supports et le contact du scénario gelé uniquement.
- Le bilan force/moment utilise les forces de contact aux points de quadrature émises par le chemin de production et les additionne dans un audit distinct. Il ne constitue pas un recalcul indépendant de la loi de contact à partir de la pression, de l’aire et des poids de quadrature.
- Aucune réaction de support du maître rigide n’est indépendamment mesurée; l’équilibre maître + montage est `NOT_VERIFIED`.
- La qualification scientifique générale `material-nonlinear` est `NOT_ACQUIRED`; la maturité demeure expérimentale. Aucun certificat global ou public n’est délivré.
- Aucun essai tangent indépendant de contact n’est inclus dans ce certificat.

## Revue indépendante

Un reviewer distinct a examiné en lecture seule le gel, les reçus et les journaux du RUN final; il n’a exécuté ni test, ni Docker, ni calcul. Il confirme la cohérence des hashes, les deux signatures égales, les six contrôles bornés PASS, les valeurs de Newton–Armijo et les bilans du sous-système esclave. **Aucun P0/P1 ne bloque le seul certificat borné** si son périmètre reste inchangé. Le reviewer confirme également le verdict global `FAIL`, l’équilibre maître/montage `NOT_VERIFIED` et la qualification générale `NOT_ACQUIRED`. Sa limite signalée — absence de recalcul indépendant de la force contact à partir de la loi et des poids — est conservée ci-dessus.

## Contrôles avant et après campagne

Avant les phases Docker, la suite ciblée a donné **59 passed in 2.19 s** :

```text
python -m pytest -q tests/unit/test_wp_e01ag_worker_state_capture.py tests/unit/test_wp_e01az_nonlinear_contact_audit.py tests/unit/test_contact_aware_equilibrium_audit.py
```

Ruff sur le worker et son test, `py_compile`, le parse AST PowerShell, la validation manifeste/source-map et `git diff --check` ont réussi. Un lancement de développement antérieur a donné `32 passed, 3 failed` pour des attentes de fixtures obsolètes après changement de contrat; celles-ci ont été corrigées, puis la suite finale a passé. Ces contrôles unitaires sont distincts du RUN physique. Aucun test n’a été relancé après le RUN.

Le RUN et ses replays ont été exécutés une fois dans Docker sous le gel décrit. Aucun retry scientifique, changement de seuil, modification de solveur, merge ou publication n’a eu lieu.

## Statuts finaux

| Statut | Résultat |
|---|---|
| `BUILD` | `PASS` |
| `PREFLIGHT` | `PREFLIGHT_PASS` |
| `COLLECT` | `COLLECTION_ACCEPTED`, 1/1, aucun corps exécuté |
| `RUN` | Exécuté une fois; deux replays prévus; worker accepté; sortie 0 |
| `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED` | `VERIFIED_BOUNDED` |
| Verdict brut global | `FAIL` (conservé; périmètre général) |
| `MASTER_ASSEMBLY_EQUILIBRIUM` | `NOT_VERIFIED` |
| `GENERAL_SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `PRODUCTION_ARMIJO_CERTIFICATE` global | `NOT_VERIFIED` |
| Intégration autoritative | `PENDING` |
| Publication publique | `NOT_AUTHORIZED` |

Les preuves brutes restent archivées sous `C:\wpc01-frictionless-public-integration-wt\wp-e01-ba-evidence\`, séparément du dépôt. Ce commit ajoute uniquement le présent rapport; le gel scientifique et les preuves existantes ne sont pas modifiés.
