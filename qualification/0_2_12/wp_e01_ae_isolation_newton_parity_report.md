# WP-E01-AE — Isolation Windows et parité Newton

## Résumé

Le contrat statique du worker AD a été réaligné sur le test AB historique : **30 mises à jour Newton** au lieu de 25 et le plafond du contrôleur existant, **14 réductions / 15 essais maximum**, au lieu de 8 / 9. Le chemin effectif observé dans le test accepte toujours le premier essai réduit à `alpha=0.25` après les essais `1.0` et `0.5`; aucune équation, tolérance, charge, loi de matériau, condition aux limites ou code de solveur n’a été changé.

Un profil Windows Sandbox fermé a été préparé. Il désactive le réseau et les redirections non nécessaires, monte le dépôt en lecture seule et place la sortie dans un répertoire adjacent distinct du dépôt. Il ne démarre aucun programme automatiquement. Ce profil n’est **pas exécutable** : aucune validation runtime n’a eu lieu, aucun environnement Python de campagne n’est préparé hors des dossiers personnels, l’accès/cleanup de la sortie hôte n’est pas runtime-vérifié et Sandbox a un minimum documenté de 2 048 MiB; le plafond Job Object de 256 MiB ne constitue pas une limite de mémoire de la VM.

**Aucun** pytest, worker, superviseur, VM/Sandbox, solveur, assemblage FEM, collecte ou calcul scientifique n’a été lancé. Les preuves AA, AB, AC et AD restent historiques et inchangées.

## Identité et périmètre

- Worktree : `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
- Branche : `codex/wp-e01-x-newton-test-remediation-20261021`
- Baseline requise : HEAD `8a284e5f657fab93b0dff4834a00c10a2934242a`, tree `807971b615df48185de198487c3baef28bc86fa1`
- Origine : `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Rapport AD conservé; son seul changement est la correction d’un artefact typographique `\`n` accidentel. Les affirmations, résultats et empreintes historiques y restent identiques.
- Aucun fichier du worktree WP-D01 n’a été modifié.

## Frontière et profil d’isolation préparé

```mermaid
flowchart LR
  H[Hôte Windows] -->|montage read-only| S[Windows Sandbox]
  H -->|montage output dédié, hors dépôt| O[Répertoire de preuves]
  N[Réseau] -. désactivé dans le .wsb .-> S
  S -->|futur préflight identité/manifest, avant import scientifique| G{Identité + GO valides ?}
  G -->|non| R[Refus]
  G -->|oui, seulement après GO distinct| W[Worker fixe E01]
```

Le fichier [wp_e01_ae_windows_sandbox.wsb](wp_e01_ae_windows_sandbox.wsb) demande : réseau désactivé, Protected Client activé, vGPU/clipboard/audio/vidéo/imprimantes désactivés, sources montées à `C:\e01\source` en lecture seule et sortie montée à `C:\e01\output` en écriture. Aucun dossier personnel n’est monté; la sortie est `C:\wpc01-frictionless-public-integration-wt\wp-e01-ae-output`, hors de `wp-e01-x`.

Le profil [wp_e01_ae_isolation_profile.json](wp_e01_ae_isolation_profile.json) est `runnable=false`, sans GO ni commande de démarrage. Le garde no-FEM historique n’est pas modifié et ne devient pas implicitement autorisé dans Sandbox. Pour un futur démarrage, l’identité du dépôt, du manifeste, du nœud allowlist et de toutes les sources devra être validée avant l’import du solveur. La mise en œuvre et validation de ce bootstrap reste une condition préalable; le `.wsb` seul ne force pas le worker fixe.

### Limites de sécurité et ressources

| Contrôle | État après AE | Limite |
|---|---|---|
| Réseau Sandbox | `Disable` dans le `.wsb` | Déclaré statiquement; non observé runtime |
| Dépôt hôte | Montage Windows Sandbox `ReadOnly=true` | Pas de vérification runtime du montage/ACL |
| Sortie | Seul partage hôte en écriture, adjacent hors dépôt | Persiste sur l’hôte; Windows Sandbox ne garantit pas sa suppression |
| Dossiers personnels | Aucun montage déclaré | Runtime non vérifié |
| Environnement Python | Non préparé dans un chemin dédié | Ancien plan AD référence un `site-packages` sous `AppData`; il ne sera pas monté en AE |
| Mémoire Sandbox | 2 048 MiB dans `.wsb` | Minimum documenté pour démarrer; plafond VM distinct du Job Object |
| Mémoire worker | 256 MiB processus et Job dans le contrat AD | Source/configuration seulement, pas de readback runtime |
| CPU | 100 s de temps CPU user cumulé dans le Job AD | Budget total, **pas** un plafonnement du taux CPU; WSB `.wsb` n’offre pas de limite CPU-rate |
| Délai mural | 120 s par phase dans le superviseur AD | Non vérifié en exécution |
| Processus | un worker, pas de descendants, kill-on-close dans le Job | Non vérifié en exécution |
| Nettoyage | contenu Sandbox éphémère à fermeture | La sortie hôte mappée persiste; procédure de révocation/nettoyage à valider |

La documentation Microsoft indique que les dossiers mappés peuvent être montés en lecture seule, que le réseau Sandbox est activé par défaut sauf désactivation explicite, que `ProtectedClient` ajoute AppContainer Isolation, et qu’une valeur mémoire insuffisante est augmentée au minimum requis de **2 048 MB**. Le `.wsb` utilise ces contrôles, mais cela ne constitue pas une preuve de leur application sur cette machine. Références : [configuration Windows Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file) et [isolation AppContainer](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file#protected-client).

### Refus avant import scientifique

Le worker AD conserve son préflight avant import solveur : identité repository, branche, HEAD/tree, hashes, allowlist, manifeste et phase doivent être satisfaits. Le validateur exige également les attestations d’isolation et refuse tant que le fournisseur d’isolation OS est absent. La configuration AE ne transforme aucune valeur déclarative en preuve : `runtime_verified=false`, `runnable=false`, et les autorisations restent nulles. Il n’existe pas encore de commande de démarrage pouvant franchir le préflight; aucun risque de calcul implicite n’est introduit par le fichier `.wsb`.

## Réutilisation WP-D01

La seule note D01 disponible dans ce worktree est `qualification/0_2_12/wpc01_r3_wp_d01_handoff.md`, qui dit explicitement que WP-D01 n’a pas commencé et traite de l’équilibre de contact, pas d’isolation Windows. Les autres documents `wp_d01_*` visibles sont des contrats/protocoles scientifiques et ne fournissent pas de worker, superviseur, VM, ACL ou composant générique réutilisable. Le worktree D01 n’est pas présent dans la liste locale des worktrees. Aucun accès ni changement D01 n’a été fait. Les composants AD restent E01-spécifiques; aucun couplage scientifique D01/E01 n’est ajouté.

## Parité Newton AB / AE

Valeurs du test d’origine lues dans `tests/unit/test_wpc01_gf4_p3_newton.py`, `tests/unit/test_wpc01_gf4_normal_fe.py`, `tests/unit/test_wpc01_gf4_friction_fe.py` et `tests/unit/test_wpc01_gf4_p3r_alpha_rejection.py`; aucune de ces sources n’a été modifiée.

| Paramètre | AB historique | Contrat/worker AE | Résultat |
|---|---|---|---|
| Élément/maillage | 1 TET4, 4 nœuds, 12 DDL | identique | Parité |
| Géométrie | trois sommets à `z=0.001 m`, quatrième à `z=0.501 m`; xy `(0.2,0.2)`, `(0.6,0.2)`, `(0.2,0.6)` | même géométrie et face de référence | Parité |
| Matériau | `isotropic_3d`, `E=10 000 Pa`, `nu=0.25`, `rho=1 kg/m³` | mêmes paramètres après override du modèle friction | Parité |
| Conditions aux limites | nœud 3 XYZ; nœud 0 XY; nœud 1 Y | mêmes DDL fixés | Parité |
| Charge | pression `18.75 Pa`, aire `0.08 m²`, `-0.5 N` sur chacun des nœuds 0–2, un incrément | identique | Parité |
| Contact | GF4, `kappa_a=100 000 Pa/m`, `mu=0.4`, `kt=100 000 Pa/m`, déplacement maître nul | identique | Parité |
| Méthode / cinématique | `newton_line_search`, petites déformations | identique | Parité |
| Convergence | tolérance relative résiduelle `1e-9` | `1e-9` | Parité |
| Newton | 30 itérations maximum dans `_supported_model` | 30 | Corrigé par AE |
| Recherche linéaire | paramètres expérimentaux non redéfinis dans le helper; contrôleur robuste par défaut `max_reductions=14`, donc jusqu’à 15 essais | 14 réductions / 15 essais | Aligné statiquement par AE |
| Armijo | `c=1e-4`, vérifié par assertion AB | `c=1e-4`, comportement inchangé | Parité |
| Observed backtracking | essais `1.0`, `0.5`, `0.25`, acceptation à `0.25` | worker conserve l’observation de la trace; pas de résultat AE nouveau | Le contrôle statique ne prouve pas l’issue physique |

Le changement 25→30 lève l’ancien plafond plus strict; il ne change pas la formulation ni la tolérance. Le plafond de recherche linéaire est fixé à 14 réductions, comme dans le contrôleur utilisé par le helper AB; cela autorise 15 évaluations au maximum. L’absence d’un résultat physique AD/AE signifie qu’on ne prétend pas que 30 corrections seront nécessaires ou suffisantes; seuls les contrôles de configuration sont désormais paritaires selon le code inspecté.

## Modifications et contrôles statiques

Sources modifiées :

- `experiments/wp_e01ad_execution_contract.py` : profil et cas simulé alignés sur 30 corrections / 15 essais max.
- `experiments/wp_e01ad_physical_fem_worker.py` : paramètres de solveur alignés sur 30 corrections et 14 réductions.
- `qualification/0_2_12/wp_e01_ad_profile.json` : scénario aligné et hashes recalculés.
- `qualification/0_2_12/wp_e01_ad_runtime_manifest.template.json` : profil et map source mis à jour; reste `runnable=false`.
- `qualification/0_2_12/wp_e01_ad_physical_fem_supervisor_implementation.md` : correction de séparation Markdown dans une ligne, sans changement d’affirmations historiques.
- Nouveaux fichiers : `wp_e01_ae_windows_sandbox.wsb`, `wp_e01_ae_isolation_profile.json`.

Contrôles accomplis sans import scientifique :

1. JSON des profils/manifeste analysés; 204 pins de sources AD correspondent octet par octet, et les 205 entrées du template correspondent aux 204 pins plus le hash du profil.
2. AST + `compile()` en mémoire pour 203 fichiers Python épinglés; aucun module scientifique n’a été importé et aucun `.pyc` n’a été écrit.
3. XML Sandbox analysé sans lancement; contrôles exacts vérifiés pour réseau, Protected Client, vGPU, mémoire, redirections, montages et absence de commande de démarrage.
4. `python -m experiments.wp_e01ad_execution_contract` : 50 décisions simulées, dont 5 formes valides de schéma, 45 refus. Aucun worker, superviseur, solveur ou processus enfant n’est créé par cet auto-contrôle.
5. `git diff --check` : PASS.

Ces contrôles sont statiques/simulés. Ils ne prouvent pas les ACL, les montages, le réseau, les limites Windows, le timeout, le cleanup ni la convergence Newton.

## Revue indépendante

Revue read-only distincte par `/root/wp_e01x_review`, sans fichier modifié ni calcul lancé. **P0: aucun. P1: blocages d’isolation et de câblage.** Les chemins guest du `.wsb` ne correspondent pas aux racines codées en dur du worker/superviseur AD; aucun runtime ni bootstrap ne permet de lancer le worker exact. L’isolation effective, les ACL, le Job readback et le nettoyage ne sont pas runtime-vérifiés; la sortie hôte est persistante. **P2 fermé par correction statique :** le worker utilise 14 réductions maximum, correspondant au défaut du contrôleur robuste AB; Newton est à 30. La revue confirme que ces contrôles restent statiques et ne prouvent pas un calcul physique.

## Empreintes

| Fichier | SHA-256 |
|---|---|
| `experiments/wp_e01ad_execution_contract.py` | `d1486843a2ede814d9ec213dbbc01361c787d97300f1f3f5c44bdd1a00ec0b1d` |
| `experiments/wp_e01ad_physical_fem_worker.py` | `fe23211f22c7d976133bede8761b66aee7ff478a5761c246578144b7e0827a05` |
| `experiments/wp_e01ad_physical_fem_supervisor.py` | `824223c056a8b854d7d4f1ac87a1f8dc937774e6cabf5646064b484c0e9c9887` |
| `experiments/wp_e01ad_collection_guard.py` | `ca3ad3154f73279cf887bf6ccc1c84876fb61288602c3431c469a3acbd1e9698` |
| `qualification/0_2_12/wp_e01_ad_profile.json` | `e827ddedabf2a4b5e2c8ddf9abcadb65750d79d33842cada88bb90da04f33fc8` |
| `qualification/0_2_12/wp_e01_ad_runtime_manifest.template.json` | `585d755754a7ac45817b0b3fa7f5ff01b4f7741614f71110fc86caac0081cbd2` |
| `qualification/0_2_12/wp_e01_ae_isolation_profile.json` | `100ab00806784e49e7f57b102895298e68562af4e73eb40d3b03147788a948b0` |
| `qualification/0_2_12/wp_e01_ae_windows_sandbox.wsb` | `a4c71440cb184e266ee845e54093deb6d4a74330b14cb62d4d11a2c2bc10facb` |

Invariants confirmés sur le gel local : test AB `tests/unit/test_wp_e01uvw_newton.py` SHA-256 `973df15eb8fffb8a9fb3af7fcb0365485ce3c582147159556ea1ec2eac3f6e7e`; garde scientifique `src/solveur/core/execution_guard.py` SHA-256 `fe8624948dab00db74d45da9b86f0cbaf128ea590a16689b5aa4bee99b7c6364`. Les autres sources de calcul demeurent les entrées inchangées du source-map validé.

Commit infrastructure/statique : `4ee2fa85c5ffc92144aacda99ef8fdcdebfdb75d`; tree : `591d8cc256b3c197226f51d46a4f4da66b359e85`. Le commit final du rapport est indiqué dans l’historique Git et dans le rapport de livraison; l’empreinte du présent rapport est calculée après son gel et ne fait pas partie des pins scientifiques.

## Findings et conditions futures

- **P1 — runtime d’isolation non démontré.** Aucune Sandbox démarrée; le profil demeure `PREPARED_NOT_EXECUTABLE`.
- **P1 — runtime Python isolé absent.** L’ancien template AD mentionne un chemin `site-packages` sous `AppData`, exclu du montage AE. Un runtime dépendances dédié et hashé doit être préparé hors des profils personnels.
- **P1 — limites composées non validées.** Le minimum Sandbox documenté est 2 048 MiB; les limites 256 MiB/100 s du Job restent distinctes. Il faut vérifier qu’un Job créé dans l’invité contrôle le seul worker et que le superviseur / cleanup restent surveillés. Le Job ne fournit pas une limite de taux CPU.
- **P1 — sortie hôte persistante.** Le dossier output en écriture est hors dépôt, mais Windows Sandbox ne le supprime pas à la fermeture; une procédure d’export et nettoyage contrôlée doit être établie avant toute campagne.
- **P1 — chemins Sandbox/worker incompatibles.** Le `.wsb` mappe les sources en `C:\e01\source` et la sortie en `C:\e01\output`; le worker, le superviseur et le contrat AD exigent le chemin racine hôte `C:\wpc01-frictionless-public-integration-wt\wp-e01-x` et écrivent sous `qualification/0_2_12/wp_e01_ad_execution`. Le worker refuserait l’identité ou ne trouverait pas son manifeste; le montage output n’est pas consommé. Il faut un bootstrap guest fixe/hashé, avec racine et sortie compatibles, sans exposer le dépôt en écriture.
- **P1 — bootstrap exact non préparé.** Pas de logon command ni de mécanisme qui lance seulement le superviseur fixe après validation; c’est volontaire pour éviter un démarrage implicite, mais cela empêche encore COLLECT/RUN.
- Aucun changement du garde no-FEM, aucune modification de tolérance ou formule Armijo, aucun résultat physique nouveau.

### Conditions d’un futur GO-COLLECT

1. Préparer hors des dossiers personnels un environnement Python 3.13 et ses dépendances exactes; en vérifier les hashes et le mapping read-only.
2. Ajouter un bootstrap fixe à cible déterminée, sans arguments arbitraires, qui vérifie manifeste, HEAD/tree, branches, hashes et allowlist avant import solver; laisser le GO propriétaire distinct comme condition d’opération.
3. Valider les ACL/montages effectifs, le réseau désactivé, Protected Client, processus, mémoire Job, délai, sortie et fermeture/cleanup dans un essai système non scientifique spécifiquement autorisé.
4. Geler HEAD/tree finals et les hashes du worker, du superviseur, du runtime et du `.wsb`; vérifier qu’aucune source ne change entre COLLECT et RUN.
5. Ne demander un GO-COLLECT que séparément; obtenir ensuite un GO-RUN distinct avec reçu COLLECT accepté.

## Statut

`WP_E01_PHYSICAL_EXECUTION_INFRASTRUCTURE=STATICALLY_REVIEWED` (revue statique indépendante complétée; findings P1 conservés)

`WP_E01_ISOLATION_RUNTIME=NOT_VERIFIED`

`WP_E01_PHYSICAL_EXECUTION_PROFILE=NOT_READY`

`COLLECT=NOT_RUN`; `RUN=NOT_RUN`; `NATIVE_FEM_VNV=NOT_RUN`

`PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`; `SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`; `AUTHORITATIVE_INTEGRATION=PENDING`; `PUBLIC_RELEASE=NOT_AUTHORIZED`.
