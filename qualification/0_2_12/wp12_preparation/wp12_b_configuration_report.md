# WP12-B — Configuration Windows et état opérationnel

**PREPARATION_ONLY** · **NUMERICAL_EXECUTION_NOT_PERFORMED** · **WP12_STATUS=OPEN**

Date d'inspection : 2026-10-26. Verdict : **WP12_B_BLOCKED_WITH_EXACT_OWNER_ACTIONS**.

## Décision d'environnement

Le choix préparé est **A — hôte Windows local avec compte runner standard dédié et ACL NTFS**, après mise à jour Windows et approbation Owner. Les capacités brutes relevées — 12 processeurs logiques, environ 96 GiB de RAM et environ 911 GB libres sur E: NTFS — sont compatibles avec un pilote ciblé de faible complexité; elles ne prouvent ni les budgets réels ni l'isolation. La virtualisation firmware est active, mais les propriétés WMI `VMMonitorModeExtensions` et `SecondLevelAddressTranslationExtensions` sont fausses et l'état Hyper-V n'a pas pu être interrogé sans élévation. Une VM persistante ne peut donc pas être déclarée disponible. Docker est déjà présent; il n'a pas été installé ni utilisé.

Ce choix est une cible opérationnelle, pas une attestation de sécurité. À l'inspection, le compte courant est standard et non administrateur, mais aucun compte `QF_WP12_RUNNER`, ACL de séparation ou probe NTFS n'a été configuré. L'hôte reste sous le minimum de build requis par le script de provisionnement.

## Faits observés sur l'hôte

| Propriété | Observation |
|---|---|
| Windows | Windows 10 Enterprise, 22H2, x64, build 19045, UBR 6456 |
| Minimum du script d'isolation | UBR 7807 ou supérieur; l'hôte est en dessous. Ce seuil correspond au build publié pour octobre 2026, mais doit être obtenu via le canal Windows/ESU applicable à l'appareil. |
| CPU | AMD Ryzen 5 5500, 12 processeurs logiques |
| Mémoire visible | 102 963 109 888 octets |
| Virtualisation | Firmware activé; extensions VM monitor/SLAT non déclarées; Hyper-V non vérifiable sans élévation |
| Volume de qualification | E: fixe, NTFS, 999 477 784 576 octets au total, 910 896 295 936 octets libres au relevé |
| Compte courant | Non administrateur; aucune action d'élévation exécutée |
| Outils | Python 3.13 et Python 3.12 présents sur l'hôte; Docker présent mais non utilisé |

Source : exécution en lecture seule de `scripts/wp12_runner/windows/Get-WP12HostAudit.ps1` le 2026-10-26. Le relevé des checkouts a été complété séparément; le rapport initial sans arguments ne les énumérait pas.

## Checkouts et Python réellement préparés

Les arbres sont séparés et propres :

| Rôle | Chemin | Commit | Git tree |
|---|---|---|---|
| Source scientifique | `E:\QFSolverWP12B\science` | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` |
| Infrastructure runner | `E:\QFSolverWP12B\runner` | `782820fe31fa8b69223bd368e39949fca325ba3e` | `100d7b3ca869cad267666337947f204c9c8bf31e` |
| Environnement Python | `E:\QFSolverWP12B\venv-3.13.17` | Python 3.13.17 | — |

Interpréteur absolu : `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`, SHA-256 `4e67d9e9a3673aa7b6219f1280d5ec3f1b6c0d5bd98ea8688c72d0cb7582d664`. Le venv exclut les packages système. Les versions épinglées comprennent NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1, cryptography 48.0.0, jsonschema 4.26.0, psutil 7.0.0 et Ruff 0.15.20. Les six variables BLAS/OpenMP/NumExpr sont déclarées à `1`; ce profil est observé par la sonde, mais le nombre de threads n'est pas une limite dure.

La distribution installée `qf-solver` est absente du venv. Une sonde distincte a importé uniquement `solveur` depuis `E:\QFSolverWP12B\science\src\solveur\__init__.py`, version de package `0.2.11`, sans distribution `qf-solver` installée et sans appel d'API FEM/analyse. L'identité du code à qualifier reste le commit/tree ci-dessus, non le champ de version Python du package.

## Identités et contrôle du manifeste v3

Le manifeste pilote v3 épingle le checkout scientifique et le checkout runner séparément. Une correction de `VALIDATE` permet désormais de vérifier chaque inventaire dans son checkout réel, sans résoudre les imports scientifiques. Au contrôle du 2026-10-26 :

* `VALIDATE` a retourné `STRUCTURALLY_VALID_NOT_AUTHORIZED`.
* Schéma et erreurs structurelles : aucune.
* Entrées contrôlées : 141 enregistrements d'empreintes; aucune erreur d'identité.
* Les deux checkouts étaient propres et correspondaient aux commit/tree déclarés.
* Les quatre blocages restent explicites : décision Owner séparée requise, archive externe non configurée, isolation Windows non vérifiée et revue de sécurité indépendante non enregistrée dans le manifeste.
* `execution_started=false`; le manifeste n'a ni signature ni décision Owner.

Le dossier des empreintes et le nodeid sont dans la [revue du manifeste pilote](wp12_b_pilot_manifest_review.md). Le [manifeste v3](wp12_b_pilot_manifest_v3.json) a le SHA-256 `501d978557e6b45ee8fcebfd99de8d928af451b8bfa47dd9f970738ea83bdd01` et reste `FROZEN_NOT_AUTHORIZED`.

## Contrôles Windows non réalisés

Aucune ACL, entrée HKLM, clé, trust pin, tâche SYSTEM, répertoire d'evidence ou compte runner n'a été créé. Le probe ACL avec fichiers factices n'a pas été exécuté, car le compte runner n'existe pas encore et le build Windows est trop ancien. Les sources scientifiques et les archives v0.2.11 n'ont pas été écrites.

Le Job Object a été testé avec sept enfants factices. Le test synthétique a démontré les limites dures de CPU, mémoire et nombre de processus ainsi que la terminaison des descendants pour ces faux processus. Ce n'est pas un sandbox de fichiers. Les limites de stockage et de threads restent souples; la protection NTFS réelle n'a pas été prouvée.

## Conclusion opérationnelle

Le PC peut héberger la configuration candidate après mise à jour et provisionnement administrateur, mais **il n'est pas actuellement attesté comme environnement WP12 sûr**. En outre, le chemin scientifique `EXECUTE` reste bloqué par code tant que l'attestation du processus enfant n'est pas implémentée et revue. Le pilote n'est donc pas prêt à recevoir sa décision finale de lancement. Aucun résultat scientifique actuel n'a été produit.
