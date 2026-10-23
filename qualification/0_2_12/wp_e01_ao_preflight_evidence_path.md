# WP-E01-AO — Préparation statique du préflight Docker

## Résultat

La tentative AN a été arrêtée avant création du conteneur, car le répertoire de preuves partagé `PREFLIGHT` était déjà occupé. AO prépare un emplacement distinct pour une tentative ultérieure. Aucun appel Docker, worker, pytest ni solveur n’a été lancé dans AO.

## Identité et chemin proposés

- Identifiant : `WP-E01-AO-PREFLIGHT-20261022-B193B8F7`
- Racine de preuves dédiée : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AO-PREFLIGHT-20261022-B193B8F7`
- Répertoire de preuves PREFLIGHT : `C:\wpc01-frictionless-public-integration-wt\wp-e01-ag-evidence\WP-E01-AO-PREFLIGHT-20261022-B193B8F7\PREFLIGHT`
- L’ancien `wp-e01-ag-evidence\PREFLIGHT` est conservé intact. Le superviseur refuse de réutiliser un répertoire de campagne existant et crée le nouveau répertoire seulement lors d’une future invocation autorisée.

L’identifiant est un argument obligatoire du superviseur pour `PREFLIGHT`, validé contre la valeur AO fixée dans le code. Il est propagé au label Docker `com.qf.evidence-id` et au reçu. Les phases `COLLECT` et `RUN` rejettent cet argument. Cette correction n’autorise aucune phase.

## Changements limités

- `experiments/wp_e01ag_docker_host.ps1` : ajout de `-EvidenceId` au profil PREFLIGHT; sélection d’une racine propre à cet identifiant; refus si le chemin cible existe déjà; contrôle de confinement sous la racine de preuves et refus d’une racine de base qui serait un reparse point; vérification du label de conteneur; identifiant consigné dans le reçu.
- `qualification/0_2_12/wp_e01aj_preflight_manifest.json` et son sidecar SHA-256 : mise à jour du pin du superviseur, sans changer le gel scientifique AN.

Aucun solveur, worker scientifique, test, paramètre Newton–Armijo, seuil, référence, image ou résultat historique n’a été modifié. Le HEAD scientifique et l’arbre restent ceux du gel AN : `41f8e4a264ffe4a4e4948bf3040d3c1fdf55d920`, tree `530c5d233a83301a4c3e869af438e65007d8d861`.

## Contrôles statiques

- Analyse syntaxique PowerShell via le parseur AST : réussie (`3762` tokens); le script n’a pas été exécuté.
- Assertions statiques sur l’identifiant, le chemin unique, le refus de réutilisation, le contrôle de chemin, le label, le reçu et les pins : réussies.
- 533 entrées `source_sha256` du manifeste : 533 valides, aucune manquante ou erronée.
- SHA-256 du manifeste égal au sidecar; pin `host_artifacts.supervisor_sha256` égal au hash courant du superviseur.
- `git diff --check` : réussi.
- Diff de périmètre : uniquement le superviseur, le manifeste et son sidecar avant ajout de ce rapport.
- Ancien répertoire de preuves présent; nouveau répertoire absent au moment du contrôle statique.

Ces contrôles ne démontrent pas le confinement Docker en exécution. Un GO-PREFLIGHT-DOCKER séparé reste requis.

## Revue indépendante

Un reviewer distinct a effectué une revue en lecture seule. Il a confirmé que le P1 initial de pin superviseur/manifeste était levé : hash du superviseur conforme au manifeste, hash du manifeste conforme au sidecar, 533/533 pins sources valides. Aucun P0/P1 restant n’a été signalé dans le périmètre de cette revue. Le reviewer a également confirmé qu’aucun Docker ni worker n’avait été lancé. Il a relevé que les identités modifiées devaient encore être figées dans un HEAD propre; ce rapport et le commit AO accomplissent cette étape.

## Identités avant commit

- Branche : `codex/wp-e01-ag-docker-native-fem-vnv`
- HEAD parent : `b193b8f746728cec28aabc2e6b0be8aee6e601ef`
- SHA-256 superviseur : `61016a67322577273c865ab5e20589592b1440a73c589d419f6208f16b1499fc`
- SHA-256 manifeste PREFLIGHT : `2e4e272bec607c9b3b19466ef438f1d770b50423a7819e1aa4a779bb94db4982`
- Sidecar `wp_e01aj_preflight_manifest.sha256` contient exactement ce hash.
- Image gelée : `sha256:2a1913a6bbc3ce5a4530193cf668edf013eec39c9b990d886fc23ff9a7c806b4`

## Commande à utiliser après un GO-PREFLIGHT-DOCKER distinct

```powershell
Set-Location 'C:\wpc01-frictionless-public-integration-wt\wp-e01-ag'
pwsh -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase PREFLIGHT -EvidenceId 'WP-E01-AO-PREFLIGHT-20261022-B193B8F7'
```

Avant lancement, vérifier le HEAD propre issu du commit AO, les SHA-256 ci-dessus, le digest de l’image, l’absence du répertoire cible, et obtenir un GO-PREFLIGHT-DOCKER distinct. Cette commande n’effectue ni COLLECT ni RUN; aucun GO correspondant n’est accordé ici.

## Statuts AO

- `EVIDENCE_PATH_CORRECTION`: `PREPARED_BY_SOURCE`
- `STATIC_CHECKS`: `PASS`
- `INDEPENDENT_REVIEW`: `COMPLETE`
- `PREFLIGHT_DOCKER`: `NOT_RUN`
- `COLLECT`: `NOT_RUN`
- `RUN`: `NOT_RUN`
- `PRODUCTION_ARMIJO_CERTIFICATE`: `NOT_VERIFIED`
- `NATIVE_FEM_VNV`: `NOT_RUN`
- `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`
