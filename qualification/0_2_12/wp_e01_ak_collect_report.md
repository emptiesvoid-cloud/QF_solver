# WP-E01-AK — Collecte Docker supervisée

Date d’exécution : 2026-10-22 (UTC dans le reçu Docker). Aucun calcul scientifique n’a été lancé.

## Identité et autorisation

- Campagne : `WP-E01-AK-COLLECT-20261022-00D2FFD8108B44FB95D9CC35BE0DBF60`
- Autorisation : le GO-COLLECT explicite fourni par l’Owner dans WP-E01-AK constitue l’autorisation. L’identifiant ci-dessus est un identifiant de corrélation généré pour cette campagne; il n’est pas une preuve indépendante d’approbation.
- HEAD avant gel : `83c5280196cd7a5c50d2b4f72b2c0eab2b8186c0`.
- Commit du manifeste autorisé : `2af401d42ffb1b5d3f731bc0c7216585b71a0c3e`.
- Tree après gel : `6acdd871d8010d1ede7eac9f2de2491cad757ccc`.
- Worktree propre avant invocation. Aucun code scientifique, test, paramètre Newton–Armijo ni seuil n’a été modifié.
- Scénario : `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA`.
- Manifeste COLLECT final : `qualification/0_2_12/wp_e01aj_collect_manifest.json`.
- SHA-256 manifeste final : `40e9d24c63d0f01695dafc39f632ab1a0942c3f31bea2a9fd9b89aa47e9230fd`.
- SHA-256 superviseur : `e315f3e93875966b23d4b728c3b9634fbd77f6be05011055f7e77f21601abea4`.
- Les 533 entrées `source_sha256` ont été comparées aux fichiers présents : 533 concordantes, 0 écart.
- Image épinglée et présente : `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5`.
- Préflight AH conservé : worker `PREFLIGHT_PASS`, hôte `COMPLETED`, `worker_accepted=true`. Son manifeste reste `ff78e668206ef2deabaf4dcd3a099b7ec33725fc9b9fda0126f26a63303d6cab`.
- L’interpréteur utilisé pour l’unique invocation était PowerShell Core 7.6.6 (`pwsh.exe`). Le contrat ne prévoit pas de confirmation interactive; aucune confirmation Owner n’a été saisie ni simulée.

Le manifeste n’a changé que sur `authorization.collect_go_id`, de `null` à l’identifiant de campagne. `run_go_id` et `collection_receipt` restent `null`. La valeur `owner_go_id` existante est conservée; l’autorité de cette collecte provient du GO Owner présent dans la conversation, pas du texte de l’identifiant généré.

## Commande et résultat

Invocation unique depuis la racine du worktree, avec PowerShell 7.6.6 :

```powershell
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase COLLECT
```

- Résultat hôte : `COMPLETED`, code `0`, `worker_accepted=true`.
- Résultat worker : `COLLECTION_ACCEPTED`.
- Nœuds : **1 collecté sur 1 autorisé**, ID exactement égal à l’allowlist :
  `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`
- Pytest : code de sortie `0`, code de session `0`; journal : `1 test collected in 0.01s`.
- `bodies_executed` : **0 par mode `--collect-only`**. Le reçu ne possède pas de compteur explicite de corps; aucune exécution de corps de test n’a eu lieu.
- Durée supervisée : `1.7933499 s`; timeout : `false`; OOM : `false`.
- Processus/conteneur : état final `exited`, code `0`.
- Nettoyage Docker : `REMOVED_CONFIRMED_NOT_FOUND`.
- Containment observée dans la configuration du conteneur : réseau `none`, rootfs en lecture seule, mémoire `1 GiB`, swap plafonné à `1 GiB`, CPU `2`, PID `64`, toutes capacités supprimées et `no-new-privileges` activé.
- Aucun RUN n’a été demandé ou lancé.

Le superviseur accepte `collect_go_id` s’il est non vide et lie le reçu au hash du manifeste; il ne valide pas de signature cryptographique Owner. Pour cette campagne, l’autorisation est fournie directement par le présent GO Owner. L’identifiant n’est pas présenté comme une authentification indépendante.

## Reçus et archivage

Les fichiers externes du superviseur et les éléments de préflight ont été copiés sans modification dans [le dossier de preuves](wp_e01_ak_collect_evidence). L’index des preuves couvre 15 fichiers et fait `401877` octets au total.

- SHA-256 du fichier `collection_receipt.json` : `21ae5a6bbfccc89c20d00d0281c2fb41d6e79d104955fd6bfba012d4acea302c`.
- SHA interne canonique du reçu (champ `sha256`) : `18d41b2eed3ba7193621b36062ff54c1e01b7ace3cbcdda8ad3504de63d8ace2`.
- SHA-256 du reçu hôte : `0b6ab3851d3e3cd5204e804bcc4af06a21ab9aa3089e389a60ea8cc6a761bb5a`.
- SHA-256 des journaux Docker combinés : `386de7f2a0275bb4c79efbd887255fb196b00ba471a96c355d754047a8b014ad`.
- SHA-256 de la sortie pytest de collecte : `e6d8a6d1f0bb00f0e4a93f3d2cbd1891f9bcf006770caec69087cdf83699870a`.
- SHA-256 de l’index d’archive : `ae546049c4b5138c22cd291a39da8aecb48e1cf38007a9a2541365a0147fed2e`.

Les SHA-256 complets de tous les éléments figurent dans `wp_e01_ak_collect_evidence/evidence-index.json`.

## État final

- `COLLECT` : **ACCEPTED — 1/1**.
- `bodies_executed` : **0** (collect-only; pas de compteur explicite dans le reçu).
- `RUN` : **NON AUTORISÉ / NON LANCÉ**.
- Calcul FEM scientifique : **NON LANCÉ**.
- Aucune relance ne sera effectuée sous cette autorisation.