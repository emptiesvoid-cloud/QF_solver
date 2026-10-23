# WP-E01-AQ — Résultat du préflight Docker AP

Date : 2026-10-22

## Autorisation et périmètre

Le GO de WP-E01-AQ autorisait une unique phase `PREFLIGHT` non scientifique pour le profil AP. La commande supervisée a été appelée une fois après vérification des identités. Aucune phase `COLLECT` ou `RUN`, aucun nœud pytest et aucun calcul FEM scientifique n’a été lancé.

## Identité gelée vérifiée avant l’appel

| Élément | Valeur observée |
|---|---|
| Worktree | `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag` |
| Branche | `codex/wp-e01-ag-docker-native-fem-vnv` |
| HEAD d’exécution | `2a8b984126bc646bf3d3e7568b155aa8772fba7c` |
| Origin | `https://github.com/emptiesvoid-cloud/QF_solver.git` |
| État avant appel | Propre |
| Superviseur | `experiments/wp_e01ag_docker_host.ps1` |
| SHA-256 superviseur | `1ce6b5077f1ea550a77964a2b8496776fce1232f06adbb42a9a8b409a08cf531` |
| Manifeste PREFLIGHT | `qualification/0_2_12/wp_e01ap_preflight_manifest.json` |
| SHA-256 manifeste et sidecar | `cd73b05cae5eca7ee048d85673a54b26ad3a9e570098b272da83de15450f5215` |
| Profil / phase | `E01_PHYSICAL_FEM_BOUNDED` / `PREFLIGHT` |
| ID de preuve | `WP-E01-AP-PREFLIGHT-20261022-AE31C83E4D3C48A3B5E25F765C9B1A70` |
| Scénario canonique | `WP_E01_AB_GF4_TET4_PRESSURE_18_75_PA` |
| Image Docker | `sha256:2a1913a6bbc3ce5a4530193cf668edf013eec39c9b990d886fc23ff9a7c806b4` |

Les 533 entrées `source_sha256` ont été vérifiées contre les fichiers du worktree : 533 présentes, 0 différence. Le HEAD scientifique `41f8e4a264ffe4a4e4948bf3040d3c1fdf55d920` est un ancêtre du HEAD d’exécution et son arbre correspond au tree `530c5d233a83301a4c3e869af438e65007d8d861` déclaré dans le manifeste. Le manifeste ne contient aucune autorisation COLLECT/RUN et aucun reçu de collecte. Le superviseur lie l’ID PREFLIGHT ci-dessus et a refusé tout ID différent dans son contrat.

PowerShell Core `7.6.6` a été utilisé. Commande exécutée depuis la racine du worktree :

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase PREFLIGHT -EvidenceId 'WP-E01-AP-PREFLIGHT-20261022-AE31C83E4D3C48A3B5E25F765C9B1A70'
```

## Résultat observé

La phase s’est terminée avec `PREFLIGHT_PASS` côté worker et `COMPLETED` côté hôte. Le code de sortie est 0; le worker a été accepté; aucun timeout ni OOM n’a été signalé. La durée hôte observée est de 1,1000394 s. Le conteneur `a8ef248831e23a8a4267bdb77b3973a477fd0e91bf4eff5573b2fa1c706b4888` a été supprimé, avec le statut `REMOVED_CONFIRMED_NOT_FOUND` après nettoyage.

Contrôles runtime lus dans le reçu worker :

* UID `10001`; système de fichiers racine en lecture seule, écriture refusée.
* Réseau Docker `none`; seule l’interface `lo` est visible dans le conteneur.
* Socket Docker absent; élévation de privilèges interdite par `no-new-privileges`; capacités supprimées.
* Mémoire cgroup maximale : 1 073 741 824 octets; swap : 0; pic observé : 19 951 616 octets.
* CPU cgroup : `200000 100000` (2 CPU); processus maximum : 64, courant : 1.
* Écriture autorisée uniquement dans le montage de résultats et le temporaire isolé, selon le contrôle du worker.
* Python `3.13.1`; dépendances observées, notamment NumPy `2.2.6`, SciPy `1.15.2` et pytest `8.4.1`, conformes au reçu.

Ces éléments valident le profil de préflight rapporté par le superviseur pour cette invocation. Ils ne constituent ni une collecte, ni une preuve de calcul FEM, ni une qualification Newton–Armijo.

## Reçus et empreintes des preuves

Répertoire persistant :

`C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AP-PREFLIGHT-20261022-AE31C83E4D3C48A3B5E25F765C9B1A70\PREFLIGHT`

| Fichier | Octets | SHA-256 |
|---|---:|---|
| `host-receipt.json` | 4 361 | `a28935a370a0a606689005b4e0e89aa847469b2cfcf5a206ab663ef3a8880050` |
| `host-receipt.pending.json` | 4 341 | `da87104101f90d47fd6590b4753d8959eae56931743793dea19faa6ce3992cb7` |
| `docker_preflight.json` | 63 678 | `5a7b473ca903664af2c9a8aad203ccc0cb85d1fff716dfd862258152d9c14077` |
| `container-config.json` | 6 838 | `fcc554fdaf8401f167eba0cab50240c0d16d5b3886493031d9588cf6457f3426` |
| `docker-combined.log` | 61 291 | `d4af5b0580a16773982c21501f7a62ce5b02730be9942297a7e7940573aba4f8` |
| `worker.stdout.log` | 61 292 | `020a7b33e2dd7718df83e0548f6b84724adbf880b11402d25df3abefae84ecff` |
| `worker.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Le reçu hôte confirme le hash du manifeste, de l’image, des journaux et du reçu worker. Aucun `collection_receipt.json` ni artefact RUN n’existe dans ce répertoire.

## Statuts

* `AP_PREFLIGHT_DOCKER`: `PREFLIGHT_PASS`
* `COLLECT`: `NOT_RUN` — le GO-COLLECT n’est pas accordé
* `RUN`: `NOT_RUN` — le GO-RUN n’est pas accordé
* `NATIVE_FEM_VNV`: `NOT_RUN`
* `PRODUCTION_ARMIJO_CERTIFICATE`: `NOT_VERIFIED`
* `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`

## Prochaine décision Owner

Le préflight AP ayant réussi, la prochaine demande peut autoriser une seule collecte sous l’identifiant déjà gelé `WP-E01-AP-COLLECT-20261022-5D50B1E9A1A14B4EAB66EB4A2B849302`. La collecte reste soumise à un GO-COLLECT distinct. Aucun changement du gel n’est requis pour préparer cette demande. Un éventuel RUN nécessitera ensuite son autorisation séparée.
