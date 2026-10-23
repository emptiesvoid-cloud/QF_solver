# WP-E01-AP — Préparation du COLLECT scientifique

## Résumé

Le reçu AO confirme `PREFLIGHT / COMPLETED`, `worker_accepted=true`, code de sortie 0 et nettoyage du conteneur. La collecte AK précédente a déjà été acceptée dans le répertoire historique `wp-e01-ag-evidence\COLLECT`; ses preuves et manifestes restent inchangés.

Le superviseur partageait jusque-là ce chemin COLLECT historique et n’acceptait un `EvidenceId` que pour PREFLIGHT. Il ne pouvait donc pas isoler une seconde campagne. Un profil AP distinct a été préparé : identifiant fixe, répertoire dédié, manifeste neuf sans autorisation COLLECT/RUN et refus de réutilisation. Aucun Docker, worker, pytest ni calcul FEM n’a été lancé dans AP.

## Identités et preuves vérifiées

- Branche : `codex/wp-e01-ag-docker-native-fem-vnv`
- HEAD parent AP : `13a778fa0bec7ad18294b278c600e988bb8adae8`
- HEAD/tree scientifique gelé : `41f8e4a264ffe4a4e4948bf3040d3c1fdf55d920` / `530c5d233a83301a4c3e869af438e65007d8d861`; ce commit est ancêtre du HEAD parent.
- Origine : `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Scénario : `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`
- Nœud unique : `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`
- SHA-256 du test : `8a0016415fb39872d418ac06beea03aa9ca8506126b997a3e9c0455c491f02a0`
- Image : `sha256:2a1913a6bbc3ce5a4530193cf668edf013eec39c9b990d886fc23ff9a7c806b4`
- Reçu AO : `wp-e01-ag-evidence\WP-E01-AO-PREFLIGHT-20261022-B193B8F7\PREFLIGHT\host-receipt.json`
- SHA-256 du reçu AO : `b0d3442a0ffd7dab8cf2099907cd7a677c98c4f02a67025f4712813a5fcd9e0e`
- Le reçu lie le manifeste `2e4e272bec607c9b3b19466ef438f1d770b50423a7819e1aa4a779bb94db4982`, l’image ci-dessus, `PREFLIGHT`, et le nettoyage `REMOVED_CONFIRMED_NOT_FOUND`.

Le reçu confirme les limites effectivement configurées/readback par le worker lors d’AO : réseau `none`, rootfs en lecture seule, mémoire 1 Gio, 2 CPU, PID max 64, UID 10001. Il ne constitue pas une preuve d’exécution FEM.

## Campagnes et anti-rejeu

Ancienne collecte conservée : `WP-E01-AK-COLLECT-20261022-00D2FFD8108B44FB95D9CC35BE0DBF60`. Le chemin historique `wp-e01-ag-evidence\COLLECT` existe déjà et contient son reçu accepté; il n’est ni réutilisé ni modifié.

Nouvelle campagne AP préparée :

- Identifiant PREFLIGHT requis pour le nouveau hash du superviseur : `WP-E01-AP-PREFLIGHT-20261022-AE31C83E4D3C48A3B5E25F765C9B1A70`
- Identifiant COLLECT : `WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302`
- Dossier futur COLLECT : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302\COLLECT`
- Ce dossier et le dossier PREFLIGHT AP sont absents. L’identifiant COLLECT n’apparaît pas dans l’historique des preuves.

Il n’existe pas de base de données centrale d’identifiants anti-rejeu : le mécanisme implémenté est le refus hôte si le répertoire de campagne unique existe déjà, avec une ID fixe dans le superviseur. Le GO Owner reste une autorisation distincte. Le manifeste AP COLLECT porte `collect_go_id=null` et le superviseur exigera, après un GO explicite, que `collect_go_id` soit exactement l’identifiant AP ci-dessus. L’identifiant seul n’est pas une preuve d’approbation.

## Changements d’infrastructure

`experiments/wp_e01ag_docker_host.ps1` sélectionne désormais des manifestes AP distincts par phase, exige les IDs fixes AP, utilise une racine de preuve par campagne pour COLLECT/RUN, lie l’ID au label Docker et au reçu, et refuse un dossier déjà utilisé. La validation du manifeste précède la création du dossier de campagne. RUN utilise le même dossier AP et un manifeste AP séparé; son GO et son reçu de collecte sont absents.

Les manifestes AP PREFLIGHT, COLLECT et RUN ont été dérivés du manifeste AO validé afin de garder exactement la même source map. Les manifestes AJ/AO/AK historiques, leurs reçus, résultats, code scientifique, tests, seuils, paramètres Newton–Armijo et image restent inchangés. L’image n’a pas été reconstruite : le superviseur reste un outil hôte, le worker dans l’image n’a pas changé.

## SHA-256 préparés

- Superviseur : `1ce6b5077f1ea550a77964a2b8496776fce1232f06adbb42a9a8b409a08cf531`
- Manifeste AP PREFLIGHT : `cd73b05cae5eca7ee048d85673a54b26ad3a9e570098b272da83de15450f5215`
- Manifeste AP COLLECT : `c3b14fee1240dfaa0fce71e93fcdba73cbc42a67a0454db6b46f21684fae8e47`
- Manifeste AP RUN non autorisé : `7086830693b76e89e19476b6adce25efed090e00e5272c2c49fbffc648493a08`
- Chaque sidecar `.sha256` correspond au manifeste portant le même nom.
- Chaque manifeste porte le hash du superviseur ci-dessus et les **533/533** pins sources correspondent aux octets du worktree.
- Les trois manifestes ont `collect_go_id=null`, `run_go_id=null` et `collection_receipt=null` (l’ancienne collection AK est préservée séparément).

## Vérifications statiques

- Parseur AST PowerShell : PASS, 3787 tokens; aucun script d’exécution n’a été appelé.
- JSON des trois manifestes : lisible; phases exactes PREFLIGHT/COLLECT/RUN; schémas dérivés du manifeste AO.
- Scénario et allowlist : scénario canonique exact; un seul nœud; hash du test égal au pin.
- Hash de superviseur, sidecars et 533 pins : PASS, zéro écart.
- HEAD/tree source : ancêtre valide et tree identique au gel.
- Anti-rejeu : ancien répertoire COLLECT présent; nouveaux dossiers AP absents; IDs nouveaux; refus de réutilisation présent dans le code.
- `git diff --check` : PASS.
- Aucune commande Docker, pytest, worker ou solveur exécutée.

### Limite de portée du préflight

Le `PREFLIGHT_PASS` AO est réel et préservé, mais il est lié à l’ancien superviseur et manifeste AO. Le superviseur AP a un nouveau SHA-256 et de nouveaux manifestes. Pour vérifier runtime cette identité modifiée et ses nouveaux chemins, une nouvelle invocation PREFLIGHT AP doit recevoir un GO-PREFLIGHT-DOCKER distinct avant le COLLECT. La configuration de l’image/ressources n’a pas changé; cela ne rend pas le reçu AO équivalent à un reçu AP.

## Commandes proposées après autorisations distinctes

Après un GO-PREFLIGHT-DOCKER pour l’identité AP, lancer une seule fois :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase PREFLIGHT -EvidenceId 'WP-E01-AP-PREFLIGHT-20261022-AE31C83E4D3C48A3B5E25F765C9B1A70'
```

Après PREFLIGHT accepté, obtenir un GO-COLLECT séparé qui autorise explicitement l’identifiant `WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302`. Mettre alors `authorization.collect_go_id` à cette valeur dans le manifeste AP COLLECT, recalculer le sidecar, committer et vérifier les empreintes. La commande COLLECT sera :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase COLLECT -EvidenceId 'WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302'
```

Ces commandes ne sont pas exécutées et ne confèrent pas d’autorisation. Aujourd’hui le manifeste COLLECT non autorisé sera refusé avant création du dossier de campagne. Aucun GO-COLLECT ni GO-RUN n’est présent. Après une collecte réussie, il faudra solliciter séparément le GO-RUN Owner et préparer son manifeste avec le reçu accepté.

## Statuts

- `AO_PREFLIGHT_RECEIPT`: `VERIFIED_PREVIOUS_PASS`
- `AP_PROFILE`: `PREPARED_STATICALLY`
- `AP_CURRENT_SUPERVISOR_PREFLIGHT`: `NOT_RUN`
- `AP_COLLECT_MANIFEST`: `PREPARED_UNAUTHORIZED`
- `AP_COLLECT`: `NOT_RUN`
- `AP_RUN`: `NOT_AUTHORIZED / NOT_RUN`
- `NATIVE_FEM_VNV`: `NOT_RUN`
- `PRODUCTION_ARMIJO_CERTIFICATE`: `NOT_VERIFIED`
- `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`
