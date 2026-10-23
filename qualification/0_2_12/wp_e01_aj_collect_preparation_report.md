# WP-E01-AJ — préparation et gel du manifeste COLLECT Docker

Date : 2026-10-22
Branche : `codex/wp-e01-ag-docker-native-fem-vnv`
HEAD documentaire de départ : `efd26b394c5462c69bbce0dd5ed75f433348b712`
HEAD du gel AJ (superviseur + manifestes) : `1d1beb4c673d8fd11af4e823b53e66d54c7dc1d4`

## Résultat et limites

Le préflight AH reste accepté et inchangé. Les 533 hashes de sources, les artefacts Docker et l’identité de l’image ont été contrôlés avant préparation. Le scénario canonique reste `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA` et le manifeste COLLECT contient un seul nœud allowlisté.

Un manifeste phase `COLLECT` a été préparé avec `authorization.collect_go_id=null`, `run_go_id=null` et `collection_receipt=null`. Il n’est donc pas autorisé et le superviseur le refusera avant création du conteneur tant que l’Owner n’a pas accordé un GO-COLLECT et fourni son identifiant. Aucun identifiant n’a été inventé. Aucun worker, pytest, collecte ou solveur n’a été exécuté dans AJ.

## Modifications

- Le superviseur fixe maintenant des fichiers de manifeste distincts par phase : `wp_e01aj_preflight_manifest.json`, `wp_e01aj_collect_manifest.json` et `wp_e01ag_run_manifest.json`.
- Il refuse explicitement tout hôte qui n’exécute pas PowerShell Core 7.0 ou supérieur. Cela écarte Windows PowerShell 5.1, incompatible avec `ProcessStartInfo.ArgumentList` et `ConvertFrom-Json -AsHashtable`.
- L’invocation Owner proposée utilise le binaire PowerShell 7.6.6 installé dans `%LOCALAPPDATA%`; la version a été vérifiée comme `7.6.6`.
- Le manifeste AI/AH historique `wp_e01ag_runtime_manifest.json`, son hash `ff78e668206ef2deabaf4dcd3a099b7ec33725fc9b9fda0126f26a63303d6cab` et son reçu de préflight sont préservés. Les manifestes AJ sont nouveaux et distincts.
- L’image n’a pas été reconstruite : le manifeste est monté depuis l’hôte en lecture seule, et aucun fichier de l’image ou worker n’a changé.

## Identités gelées

| Artefact | SHA-256 |
|---|---|
| Superviseur `experiments/wp_e01ag_docker_host.ps1` | `e315f3e93875966b23d4b728c3b9634fbd77f6be05011055f7e77f21601abea4` |
| Manifeste AJ PREFLIGHT | `acf3331d719aba23bb8b787abe78fbf313bf6ffb1877fd34f4de6e07e73e5d00` |
| Manifeste AJ COLLECT | `dac654ac7e0862c037784a3fb931ab9b9718ec638470e8f03fd3d2f92e2befd6` |
| Sidecar AJ COLLECT | `f35330ab31b5e6083cd16b2fd035e868fb96b5e060e5c9336fe380af624ccc4d` |
| Image locale | `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5` |
| Dockerfile | `e7647801586c6d83ae6ecc1e3f4a72780e87f68f6eac0e48b6e672386eb4181f` |
| `.dockerignore` | `b1f160fb6cacd787a3400bcc1a768a06e3e1d422c2a7515dd311167bc29f37af` |
| Lock dépendances | `359c2890899d7a2c79323b8247fea35ca37956742b14e739f3ecef2728a3a3d3` |

Le manifeste COLLECT conserve le source HEAD/tree scientifique AH : `5826b784e580936da77017941a4f2d23e76f7a44` / `bf55fbd9779c34f47033577943a7e30b811f220d`. Ses 533 entrées `source_sha256` ont été vérifiées localement; le pin du superviseur correspond au nouveau SHA ci-dessus. L’image inspectée par son image ID correspond exactement au digest gelé.

La valeur intégrale du sidecar est à lire dans le fichier nommé; elle est la SHA-256 calculée de `wp_e01aj_collect_manifest.json` et doit rester synchronisée si un GO-COLLECT est ensuite ajouté. L’ajout de `collect_go_id` changera nécessairement le hash du manifeste et exigera un nouveau gel avant exécution.

## Préflight AH préservé

Le reçu archivé `qualification/0_2_12/wp_e01_ah_evidence/preflight/docker_preflight.json` contient `PREFLIGHT_PASS` et référence le manifeste AH attendu. Les readbacks déjà établis restent limités à ce préflight : mémoire cgroup 1 Gio (pic observé 47 190 016 octets), swap effectif nul, quota CPU 2, PID max 64, UID 10001, rootfs lecture seule, socket Docker absent, interface `lo` seulement, et versions runtime attendues. AJ n’a pas relancé ce préflight ni les calculs scientifiques.

## Commande Owner après autorisation

À lancer manuellement seulement après un GO-COLLECT distinct, l’insertion de l’identifiant Owner fourni dans un nouveau manifeste gelé et la vérification de son nouveau sidecar :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase COLLECT
```

Cette commande cible le chemin phase `COLLECT`, qui sélectionne exactement le manifeste AJ et son nœud fixe. Avec le manifeste présent (GO nul), elle est volontairement refusée avant `docker create`. Ne pas changer manuellement le champ `phase`, `collect_go_id` ou le pin pour contourner ce garde.

## Contrôles statiques

- AST PowerShell du superviseur : PASS sous PowerShell 7.6.5 du runner de développement.
- Version du binaire installé Owner : `7.6.6`.
- Manifeste JSON : valide; schéma et champs conservés; `phase=COLLECT`; allowlist de taille 1; identifiant canonique vérifié; `collect_go_id=null`.
- Hashes : 533/533 sources et quatre pins d’artefacts valides; sidecars cohérents; digest d’image cohérent.
- `git diff --check` : PASS.
- COLLECT / RUN / exécution worker : NOT_RUN.

## Statuts

- `AH_PREFLIGHT`: `PREFLIGHT_PASS` (résultat historique conservé)
- `COLLECT_MANIFEST`: `PREPARED_UNAUTHORIZED`
- `COLLECT`: `NOT_RUN`
- `RUN`: `NOT_RUN`
- `NATIVE_FEM_VNV`: `NOT_RUN`
- `PRODUCTION_ARMIJO_CERTIFICATE`: `NOT_VERIFIED`
- `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`

Prochaine étape : attendre le GO-COLLECT explicite et l’identifiant Owner associé. Après mise à jour autorisée, réémettre et revérifier le hash du manifeste avant que l’Owner n’exécute la commande ci-dessus.
