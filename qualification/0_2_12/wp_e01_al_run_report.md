# WP-E01-AL — Exécution RUN Newton–Armijo

## Résultat

**RUN : ERROR.** Le worker a appelé le solveur physique, puis a échoué pendant l’instrumentation de l’état. Aucun résultat numérique ni reçu numérique RUN n’a été écrit. L’exécution ne peut donc être classée ni PASS ni FAIL scientifique. Aucun second lancement ni retry n’a été effectué.

## Gel et autorisation

- GO-RUN : autorisation Owner explicite reçue dans WP-E01-AL pour une exécution unique.
- L’identifiant de suivi `WP-E01-AL-RUN-20261022-03781E9D30DD46F6A36BB90E408AA4FB` est généré pour relier cette autorisation à la phase et au gel; il n’est pas une preuve autonome d’approbation.
- Manifeste COLLECT : SHA-256 `40e9d24c63d0f01695dafc39f632ab1a0942c3f31bea2a9fd9b89aa47e9230fd`.
- Reçu COLLECT : SHA-256 du fichier `21ae5a6bbfccc89c20d00d0281c2fb41d6e79d104955fd6bfba012d4acea302c`; son hash canonique interne est `18d41b2eed3ba7193621b36062ff54c1e01b7ace3cbcdda8ad3504de63d8ace2`.
- Le contrat impose un manifeste distinct `wp_e01ag_run_manifest.json`, un `run_go_id` non vide, un `collect_go_id` nul et le reçu `COLLECTION_ACCEPTED`. Le manifeste RUN contient le hash canonique du reçu COLLECT, le même nœud unique, le même gel scientifique et les 533 pins sources.
- Manifeste RUN : SHA-256 `a38e608cd6a4cb28f1af06f58b2a1eee608b97c86b339a7949630e07ef400ea2`; pin latéral concordant.
- Commit de gel RUN : `feeb6ba604ac9587a53fbc9c578fcd070de8c62a`.
- Les 533 empreintes du manifeste RUN ont été vérifiées contre les fichiers avant exécution : 0 écart. Aucun code scientifique, test, paramètre, référence ou seuil n’a été modifié.
- Nœud unique : `tests/verification/test_wp_e01ag_physical_newton.py::test_production_gf4_tet4_newton_armijo_rejects_full_then_accepts_reduced`.
- Image épinglée : `sha256:4dd620505509972e6b8520185a43cae46306e1c170b3dc0719d409cca332c2d5`.

## Exécution observée

Commande unique lancée avec PowerShell Core 7.6.6 :

```powershell
& "$env:LOCALAPPDATA\Programs\PowerShell\7.6.6\pwsh.exe" -NoLogo -NoProfile -File .\experiments\wp_e01ag_docker_host.ps1 -Phase RUN
```

Le conteneur a démarré avec l’image et les montages prévus. Le reçu hôte indique `REJECTED`, exit code `1`, `worker_accepted=false`, `timed_out=false`, `oom_killed=false`, durée murale `2.8036975 s`. La configuration enregistrée indique réseau `none`, rootfs en lecture seule, mémoire 1 GiB, 2 CPU, 64 PID, toutes les capacités supprimées et `no-new-privileges`.

Le code appelle `solver.solve(model)` à la ligne 539. Le traceback effectivement enregistré se termine ainsi :

```text
  File "/opt/qf/experiments/wp_e01ag_docker_worker.py", line 616, in _run
    runs = [_run_one_physical_case(doc) for _ in range(doc["controls"]["deterministic_replay_count"])]
  File "/opt/qf/experiments/wp_e01ag_docker_worker.py", line 559, in _run_one_physical_case
    state = solver._last_load_step_state
AttributeError: 'NonlinearStaticSolver' object has no attribute '_last_load_step_state'
```

Le flux de contrôle confirme que `solver.solve(model)` a été appelé; le worker a ensuite tenté de lire `_last_load_step_state`, absent de l’objet. Le worker n’a pas écrit `run_receipt.json` ni de résultat numérique. Le journal d’erreur ne permet pas de savoir si `solve` a retourné un résultat ou levé l’exception de convergence interceptée par le worker. En conséquence, les résidus, déplacements, réactions, itérations Newton, coefficients Armijo, réductions, équilibre de contact et écarts à la référence sont **NOT_RECORDED**. Le rejet du pas complet et l’acceptation du pas réduit ne sont pas démontrés.

Le profil avait `deterministic_replay_count=2`; le premier appel `_run_one_physical_case` a échoué à l’instrumentation, donc le second replay n’a pas commencé. Cela ne constitue pas un retry effectué par l’agent.

## Reçu et nettoyage

- Reçu d’exécution hôte : [host-receipt.json](wp_e01_al_run_evidence/RUN/host-receipt.json), SHA-256 `b7567ed250d3b02ed1a04b04b23d6bbe4d096bcc927e19735e2ecafb6608dbd1`.
- Reçu numérique worker : **absent**; `worker_receipt_sha256=null` dans le reçu hôte.
- `worker.stderr.log` SHA-256 `e2ae117d2a0e503963745eae6af6f4726771daef2b44c3e23f597fae92e2f0f4`.
- `worker.stdout.log` et `docker-combined.log` sont vides (SHA-256 chacun `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- `container-config.json` SHA-256 `36ba41720cf9cc2500d6dffb59fcacbd4f25d272b953be8f92ef574759cea158`.
- Le nettoyage est confirmé par le superviseur : `REMOVED_CONFIRMED_NOT_FOUND`. Une vérification Docker après exécution a également renvoyé `No such container` pour l’identifiant enregistré.
- L’index d’archive couvre 10 fichiers; SHA-256 `009a9c1071e57c396205cca1aae16b6ae57b4d90cf0b19d0bc87cabb404497fa`.

Les reçus, journaux et manifestes utilisés sont archivés dans [le dossier de preuves RUN](wp_e01_al_run_evidence).

## Conclusion scientifique

- **Statut d’exécution : ERROR**, après invocation de `solver.solve(model)` et avant production du résultat instrumenté.
- **Newton–Armijo : non vérifié** : aucune trace numérique persistée n’établit convergence, rejet du pas complet ni acceptation réduite.
- **Références :** le prédicteur du TET4 ouvert est une vérification de conception seulement et ne certifie pas l’équilibre non linéaire avec contact.
- `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`.
- Aucun RUN supplémentaire n’est autorisé par cette campagne. Une correction de l’instrumentation et un nouveau GO distinct seront nécessaires avant toute nouvelle exécution.