# WP-E01-AX — Campagne Docker FEM Newton–Armijo

Date : 2026-10-23
Branche : `codex/wp-e01-ax-registry-packaging-20261023`
Worktree : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag`

## Verdict consolidé

La nouvelle campagne a reconstruit l’image corrigée, passé PREFLIGHT, collecté le seul nœud autorisé et exécuté une fois le RUN supervisé. Le chemin FEM de production a assemblé le TET4 avec contact et exécuté Newton–Armijo. Les deux replays prévus dans cette invocation ont le même historique et la même signature scientifique.

Le résultat ne permet pas de délivrer un certificat Armijo : le reçu worker agrégé indique `PASS`, et les contrôles locaux de convergence/Armijo passent, mais chacun des deux replays porte aussi `run_verdict=FAIL` et `qualification_summary.status=FAIL`, en raison des audits gelés `equilibrium:global_force_balance` et `equilibrium:global_moment_balance`. Le statut agrégé ne respecte donc pas le statut détaillé de qualification. Les audits de bilan n’intègrent pas le terme de contact; les données de contact du reçu semblent compenser les déséquilibres publiés, mais cette fermeture n’a pas été validée par l’audit qualifiant. Ces contradictions restent visibles et ne sont pas converties en PASS.

| Domaine | Résultat |
|---|---|
| BUILD image Linux/amd64 | `PASS` |
| PREFLIGHT | `PREFLIGHT_PASS` |
| COLLECT | `COLLECTION_ACCEPTED`, 1 nœud sur 1, `--collect-only` |
| RUN supervisé | Phase terminée, exit code 0, pas de timeout/OOM, conteneur supprimé |
| Résultat worker agrégé | `PASS` |
| Résultat des deux replays | `solve_outcome=PASS`; `run_verdict=FAIL`; qualification `FAIL` |
| Newton–Armijo observé | Comportement borné démontré pour ce cas : rejet de `α=1` et `α=0.5`, acceptation de `α=0.25`, puis trois acceptations de `α=1` |
| Équilibre dans l’audit enregistré | Échec des deux contrôles globaux; pas de contrôle global contact-aware accepté |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `EXECUTED_BOUNDED_PARTIAL` — chemin FEM de production exercé dans le conteneur, résultat de qualification incomplet |
| Qualification scientifique générale | `NOT_ACQUIRED` |
| Intégration autoritative / publication | `PENDING` / `NOT_AUTHORIZED` |

L’autorisation AX a été consommée par une seule invocation RUN; celle-ci a produit les deux replays déterministes prévus. Aucun retry scientifique n’a été effectué.

## Préservation et identité du gel

Les preuves WP-E01-AW, y compris son RUN antérieur en erreur de configuration, sont conservées. AW n’a pas fourni de résultat de solveur exploitable : l’image ne contenait pas `qualification/requirements.json`, nécessaire à la création de l’audit. AX a corrigé le packaging de ce registre et ajouté le contrôle worker ciblé; aucune équation, loi de contact, tolérance, référence ou paramètre Newton–Armijo n’a été modifié.

Commits AX pertinents :

* `62affc83576bd9be6653f1ed274147868d6a4808` — correctif de packaging et contrôles ciblés; tree scientifique `edb5210b4fee70a71b31f65ed9698480db8b23fc`.
* `fa194d53925cf58d242bfaa01e1dcff2c92e46e2` — gel PREFLIGHT/COLLECT.
* `2f33e984aa2d5ad7120a3b713d2faf5a85aa2ffb` — gel du manifeste RUN; tree documentaire `f8c97b98e00885b02fc09296de72c85aa576d231`.

Le manifeste RUN épingle 534 fichiers. Le contrôle local final a comparé les octets des 534 chemins au manifeste : 0 fichier manquant, 0 empreinte divergente. Le commit scientifique gelé n’a pas été modifié après le gel; les commits postérieurs ajoutent les manifestes et éléments documentaires de campagne.

| Artefact | SHA-256 / identité |
|---|---|
| Image Docker réellement utilisée (`linux/amd64`) | `sha256:dad19b3af962571e682a3f7bcba44e5f9a06abae403e74d6067831002ce1561e` |
| Dockerfile | `e355d052651ad67bc4b25e9aa6ad1d1888e689aaf954e9a15b8154b7887120fe` |
| Docker ignore | `84552280a821f687727ed55dbf0be674f46a5ff293900149c004f9e70c343818` |
| Verrou de dépendances | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |
| Worker `experiments/wp_e01ag_docker_worker.py` | `0214fa5a58770663894d4255b852e3d24cb625a85397d2c9813fcaf088ba5acd` |
| Superviseur `experiments/wp_e01ax_docker_host.ps1` | `eb413987df91125d5f2e437bc997f2fac79b4b6679849c6bb63d526965becdca` |
| Registre `qualification/requirements.json` | `11346b0466a3849bf67fde066354909795dc28cb826f4b9fb6e9e4a30ed25a0e` |
| Protocole GF4 | `548d7d21009020b6065ce1c3383e65b6f63fd26e7493092c1c82e59e29bf1362` |
| Manifeste PREFLIGHT | `a48c907217e205a555afff6c2d087a197a763b462992e89d08beb6ee73a7d163` |
| Manifeste COLLECT | `6197256e121e81cbce4593adfd1b655fcc151acabc8cd8836d6db22fb5c0560b` |
| Manifeste RUN | `3d2b88fd4f2f20f5d0ddb8617ee5b0ddf1cf2f089e048e0d9c285f751f0bd28e` |
| Scénario | `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA` |
| Nœud unique | `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced` |

Les contrôles du scénario sont restés à 30 itérations Newton max., 15 essais Armijo max., 14 réductions max., tolérance relative `1e-9`, coefficient `c=1e-4`, alpha minimal `1e-4`, un pas de charge et deux replays.

## Correctif AX et vérifications préalables

Le gel AW échouait à créer l’audit car le registre de qualification était absent de l’image. AX inclut et épingle `qualification/requirements.json`. Les tests unitaires ciblés de capture d’état worker ont donné `12 passed`; Ruff sur le worker, le test et `conftest.py` a réussi. Les vérifications AST/compilation, parseur PowerShell, manifeste et `git diff --check` ont réussi. Aucun test FEM n’a été exécuté par ces contrôles ciblés.

Une construction initiale n’a pas démarré : la version locale de Buildx ne reconnaissait pas `--ignorefile`. Buildx utilise automatiquement le fichier `Dockerfile.wp_e01ax.dockerignore` associé au Dockerfile; la construction suivant cette convention a réussi et a produit l’image épinglée ci-dessus. Aucun calcul scientifique n’a été exécuté lors de cette erreur de CLI.

## PREFLIGHT et COLLECT

Identifiants :

* PREFLIGHT : `WP-E01-AX-PREFLIGHT-20261023-9D8CA904FE254BBABA38EDB04D0EA45C`.
* COLLECT/RUN : `WP-E01-AX-COLLECT-20261023-CBF0182360954A3E8C631B2B4E2319C8`.

PREFLIGHT s’est terminé avec `PREFLIGHT_PASS`, code hôte 0, `worker_accepted=true`, sans timeout ni OOM, nettoyage `REMOVED_CONFIRMED_NOT_FOUND`. Le readback indiquait Python 3.13.1, NumPy 2.2.6, SciPy 1.15.2, UID 10001, interfaces réseau `lo` uniquement, socket Docker absent, racine non inscriptible, `/tmp` et le répertoire de résultats inscriptibles. Les limites cgroup lues étaient mémoire 1 Gio, swap 0, CPU `200000 100000` (2 CPU), PID max. 64.

COLLECT a terminé naturellement, code 0, et a observé exactement le nœud autorisé. La commande était fixe en mode collecte (`--collect-only`); aucun corps scientifique n’a tourné. Le reçu contient l’inventaire observé et attendu identiques, et le stdout pytest rapporte `1 test collected in 0.01s`. Le conteneur a été supprimé. Le reçu ne possède pas un champ explicite `bodies_executed`; l’absence d’exécution des corps s’appuie sur la phase COLLECT fixe et le journal pytest. Cette limite de schéma est conservée comme P2.

| Preuve | SHA-256 |
|---|---|
| Reçu worker PREFLIGHT `docker_preflight.json` | `fbd037a15bca009528190772d40bc131bd53f01e4b44acc46babf277d4289f48` |
| Reçu hôte PREFLIGHT | `a7f48373f141bb7ccd93ec593a592e9b57ea80eb8ac864c9121c3f7e17170027` |
| Logs Docker PREFLIGHT | `ed94b99548d9eb626b2ed750633adff55bc7719f86fef77c59964dabad384384` |
| Reçu worker COLLECT brut | `e8a21fdecd6f92c9b7ae418b7a89d08e705e5c17ab35626dc3b1f52929d8b80b` |
| Digest canonique du reçu COLLECT (champ `sha256`) | `0190c2ef6c5307bfe2a198e1d0325524e624182e3b5adc0b6555e51398fcbc17` |
| Reçu hôte COLLECT | `20100483668e3f7529bb3bae2d29d30377b38d37ab956b9b8c544f4587bb3a3b` |
| Stdout de collecte | `e6d8a6d1f0bb00f0e4a93f3d2cbd1891f9bcf006770caec69087cdf83699870a` |
| Logs Docker COLLECT | `ac53801d8e168f6d6dd02395fb1d248f8aeb7c2a750e4973fef439a4f4f7eea7` |
| Configuration conteneur COLLECT | `ecd29478be3d617bd16cc2614634cc8c73f073d9d56a521ccc5507b068582999` |

## RUN supervisé

Le RUN a été lancé une fois, après PREFLIGHT accepté, COLLECT accepté, revue du gel favorable et validation de l’autorisation conditionnelle. Le conteneur a terminé code 0 en 3.1496742 s côté hôte, sans timeout/OOM; état final arrêté et absence confirmée après nettoyage. Le reçu worker indique environ 0.9411564 s pour les deux replays. Le pic cgroup mesuré était 204,722,176 octets, sous la limite de 1 Gio; la limite CPU était de 2 CPU et la limite PID 64. Le readback confirmait UID 10001, réseau `lo` seulement, racine en lecture seule, absence du socket Docker, swap plafonné à zéro.

### Historique Newton–Armijo observé (identique pour les deux replays)

| Itération | Mérite initial (N) | Essais alpha : mérite (N) | Décision |
|---:|---:|---|---|
| 1 | `0.8660254037844386` | `1: 13.043364313475424`; `0.5: 3.7854140850566926`; `0.25: 0.6016607470874248` | `1` et `0.5` rejetés; `0.25` accepté; 2 réductions |
| 2 | `0.6016607470874248` | `1: 0.08581211766875732` | `1` accepté |
| 3 | `0.08581211766875732` | `1: 0.00014075840786308667` | `1` accepté |
| 4 | `0.00014075840786308667` | `1: 2.182020284783493e-12` | `1` accepté |

Le solveur a terminé à facteur de charge `1.0`, avec un résidu libre relatif `2.182020284783493e-12`, un commit accepté et `commit_count=1`. Le déplacement maximal était `0.0012253000251038234 m`; les deux replays ont le même digest d’état accepté `e8b28f1a6094d26144ce6d9e58a90c0ed49e9d443ed3b9f450f275cb803449e5`. Leurs signatures scientifiques concordent : `2a17fbbdc7be23833b4cc67426147d7ac90e4bcc0cdf735f126012985a7a3635`; `deterministic_replay_equal=true`. Les temps opérationnels restent dans les reçus mais ne font pas partie de cette signature.

### Bilan et statut contradictoire

Pour chacun des deux replays, les sept contrôles de scénario rapportés sont vrais : convergence sous tolérance relative gelée, facteur final un, rejet physique du pas complet, concordance facteurs/mérités, acceptation du pas réduit, immutabilité des états rejetés/essais et commit unique. En parallèle, `run_verdict=FAIL`, `qualification_summary.status=FAIL` et `blocking_errors=["2 audit check(s) failed."]`.

L’audit de bilan enregistré rapporte :

* Résultante des charges appliquées : `[0, 0, -1.5] N`.
* Résultante des réactions : `[-0.04630120354435955, -0.054915536897736185, 0.5040003347176439] N`.
* Erreur relative de bilan des forces : `0.6657242842315055` (FAIL; limite PASS `1e-10`).
* Erreur relative de bilan des moments : `0.507475126989006` (FAIL; limite PASS `1e-10`).
* Résidu libre relatif : `2.182020284783493e-12` (PASS).

Le diagnostic de contact final du même reçu fournit une résultante physique sur l’esclave `[0.046301203547404, 0.054915536897467684, 0.9959996652823566] N` et son moment à l’origine `[0.3588249907421624, -0.35883360507551243, 0.00375158631704598] N·m`. L’audit global ne contient pas de terme `contact_aware_equilibrium`. L’addition arithmétique des valeurs de contact publiées aux imbalances d’audit ferme ces vecteurs à environ `3.1e-12 N` et `1.4e-12 N·m`; c’est une observation diagnostique dérivée du reçu, pas un contrôle indépendant accepté ni une raison de remplacer le `FAIL` de qualification. Le bilan total reste à faire vérifier par un audit global qui traite explicitement et correctement forces et moments de contact.

La référence enregistrée est un prédicteur linéaire TET4 ouvert, limité au contrôle de conception; elle ne constitue pas une solution indépendante du problème non linéaire avec contact. Le domaine de qualification `tet4-linear-static-v1` est `NOT_APPLICABLE`, et la traçabilité `material-nonlinear` est `FAIL`. Ces limites interdisent une conclusion de qualification générale.

### Sémantique des statuts

La divergence de statut est un finding P1 : le worker pose le résultat agrégé à `PASS` à partir des contrôles du scénario et des signatures, sans imposer `run_verdict=PASS` ni `qualification_summary.status=PASS`. L’hôte accepte ce résultat agrégé et inscrit `scientific_result=PASS`. Les deux objets de replay portent pourtant `run_verdict=FAIL` et qualification `FAIL`. Le rapport conserve les quatre niveaux au lieu de choisir le plus favorable. L’invocation Docker est terminée avec succès comme opération; l’algorithme Newton–Armijo a convergé selon les contrôles ciblés; la qualification complète du scénario a échoué.

## Revue indépendante et findings

Un reviewer distinct a relu en lecture seule les sources gelées, les reçus et les observations du RUN. Aucun P0 n’a été identifié. Le reviewer confirme l’observation du rejet du pas complet et de l’acceptation du pas réduit, la convergence sous le critère relatif enregistré, ainsi que l’égalité des deux signatures. Il relève comme P1 le décalage entre le `PASS` agrégé et les deux verdicts détaillés `FAIL`; aucun certificat ne doit être émis. Les audits globaux échouent selon le reçu et doivent rester échoués dans le verdict brut. Les limites P2 de schéma COLLECT et d’audit de traçabilité restent documentées. Cette revue ne remplace pas une référence indépendante d’équilibre.

Les deux replays incluent dans les observations d’assemblage un état GF4 d’essai à trois points; les champs d’état accepté restent inchangés lors des probes de recherche linéaire. Ces faits sont limités aux observations émises et ne constituent pas une validation générale de l’algorithme de contact.

## Reçus RUN et preuves persistantes

Répertoire de campagne :
`C:\wpc01-frictionless-public-integration-wt\wp-e01-ax-evidence\WP-E01-AX-COLLECT-20261023-CBF0182360954A3E8C631B2B4E2319C8\RUN\`

| Fichier / valeur | SHA-256 |
|---|---|
| Reçu worker brut `run_receipt.json` | `7814935efa2f62bb1329a9a5090d812c20e04802e106854b417fcfa27513e50f` |
| Digest canonique déclaré dans le reçu worker | `45a3ba87cbd4dff3c71ef1237762619e705c3480d61642e3708646e08a355889` |
| Reçu hôte | `c6898efcf23e4fcec1c0cee65257e2604228da9e4fc69279ac7584592441ad84` |
| Logs Docker combinés | `8da17101b60da95d5a3f53b77a55b31397191227b39ae3068b21733987a92812` |
| Stdout worker | `d2aa80813363eda5c39323a75798768e8f799096ec2497ecb6463f7d6687f84f` |
| Stderr worker (vide) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Configuration Docker observée | `7210a7e5707eb0d13e6e0755a3eb3c7a4761ebefeb781b51a482cb261e1b0c6d` |
| Digest canonique du reçu COLLECT lié au RUN | `0190c2ef6c5307bfe2a198e1d0325524e624182e3b5adc0b6555e51398fcbc17` |

Le digest canonique interne du reçu RUN a été recalculé et correspond au champ `sha256`. Le reçu contient les deux replays, leurs traces et leurs audits complets. Les fichiers bruts et journaux ne sont pas modifiés par ce rapport.

## Limites et suite

La campagne établit, pour un scénario TET4 GF4 et un incrément de charge précis, qu’un pas complet et le demi-pas sont rejetés, qu’un quart de pas est accepté par Armijo, puis que Newton converge et commit le pas. Elle établit également la reproductibilité des grandeurs incluses dans la signature entre deux replays dans une invocation.

Elle ne délivre pas de certificat Armijo de production ni de qualification générale parce que :

1. le verdict agrégé contredit les verdicts de qualification des deux replays;
2. les deux contrôles d’équilibre globaux échouent et l’audit n’intègre pas explicitement le contact;
3. la référence est un prédicteur linéaire ouvert, non une référence indépendante pour le contact non linéaire;
4. la traçabilité et le domaine de qualification de registre ne couvrent pas ce cas.

La prochaine décision Owner devrait autoriser séparément une correction du contrat de verdict et un audit d’équilibre global contact-aware avec référence indépendante. Elle devrait préserver les reçus AX et ne pas autoriser un nouveau RUN avant qu’un nouveau gel, une revue de ces critères et une nouvelle autorisation explicite soient établis. Aucun nouveau calcul n’est lancé par ce rapport.

## État final

* `BUILD=PASS`
* `PREFLIGHT=PREFLIGHT_PASS`
* `COLLECT=COLLECTION_ACCEPTED (1/1)`
* `RUN=COMPLETED; worker aggregate PASS; per-replay qualification FAIL`
* `NEWTON_ARMIJO_BEHAVIOR=VERIFIED_BOUNDED_FOR_THIS_CASE`
* `GLOBAL_EQUILIBRIUM_AUDIT=FAIL`
* `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`
* `NATIVE_FEM_VNV=EXECUTED_BOUNDED_PARTIAL`
* `SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`
* `AUTHORITATIVE_INTEGRATION=PENDING`
* `PUBLIC_RELEASE=NOT_AUTHORIZED`
