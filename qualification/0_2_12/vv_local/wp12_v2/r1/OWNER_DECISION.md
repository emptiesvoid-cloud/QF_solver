# WP12-V2-R1 — proposed Owner execution decision

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**

This document is an unsigned proposal for review. No approval record is created, and the current R1 mission authorizes no scientific execution. The original conditional decision bound to manifest `dd72bc80ff5dbae1d105bef5ad6f778eb9046335706697db0479b0764145d665` does not authorize these revised identities.

## Bound unit

- Manifest: [V2_R1_MANIFEST.json](V2_R1_MANIFEST.json), SHA-256 `fe19d40bd46c0d8c1fc0fc6f49cb37e978b8132d5c5077d15b4ab8d9f46db77d`.
- Campaign: `WP12-V2-R1-H1-OPERATOR-AUDIT-002`.
- Case: `TET4-H1-OPERATOR-AUDIT-002`.
- Nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.
- Science: commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`, checkout `E:\QFSolverWP12B\science`.
- Tests: commit `67813b4a36a057bbaa9e5fba32bcdea66ddf4df3`, tree `ffee889f0cd70b089ec8e1719b84a667babfa1be`, checkout `E:\QFSolverWP12B\tests-wp12-v2-r1`.
- Runner: commit `a9dcd5ac2b13e02db7e1fe2bc6fb940fbb490a09`, tree `fd4ea17d7a25452f72faa58a62704daa51b62fab`, checkout `E:\QFSolverWP12B\runner-local-vv-v2r1`.
- Python: `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`, version 3.13.17. Pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, h5py 3.14.0, threadpoolctl 3.6.0. The solveur import must resolve to the science checkout; its recorded source version is 0.2.11 and no installed qf-solver distribution is expected.
- All six BLAS/OpenMP-related thread variables listed in the manifest are set to `1` by the runner's child environment. Recorded native library: OpenBLAS 0.3.29, one thread; expected DLL SHA-256 `6547e9fb966e9773caee2755e91a8bf4d6f3a2f0eebf9646b0158f8675ea4ab5`.
- One attempt, plan ID `WP12-V2-R1-H1-OPERATOR-AUDIT-002-A1`, timeout 300 seconds, 16 MiB software-polled cap per stdout/stderr stream, no automatic retry.
- Evidence: `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R1-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<new_run_id>\`. The campaign directory is absent at preparation. The runner generates the run ID and uses an exclusive new directory; the existing common evidence root is retained.
- Working directory: `E:\QFSolverWP12B\tests-wp12-v2-r1`. Temporary files are confined by convention to `<new_run_directory>\tmp`; this is not a filesystem sandbox.

## Reviewed argument vector

The following is a review representation. A future authorized run uses the runner's exact-case interface and its separate decision record. Only `<new_run_id>` is generated; no caller-selected argument may be added.

```text
E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe -m pytest -q -s --noconftest -p no:cacheprovider -p local_vv_pytest_plugin -c E:\QFSolverWP12B\tests-wp12-v2-r1\pyproject.toml -o pythonpath= -o addopts= --junitxml=E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R1-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<new_run_id>\junit.xml tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002
```

The exact numerical criteria are [unchanged from V2](../V2_NUMERICAL_CRITERIA.md). The [R1 protocol](README.md) controls explicit gamma/result statuses. In this frozen test, arithmetic assumptions remain unverified. Gamma and the overall scientific assessment therefore remain `INCONCLUSIVE` when mandatory checks pass. Mandatory failures remain `FAIL`; missing or invalid evidence is `INCOMPLETE`/`ERROR`. The future approval cannot turn an unverified assumption into a verified one.

## Texte complet d'approbation proposé — à confirmer explicitement par l'Owner

> J'autorise une seule tentative locale de `TET4-H1-OPERATOR-AUDIT-002`, campagne `WP12-V2-R1-H1-OPERATOR-AUDIT-002`, exclusivement sous le manifeste SHA-256 `fe19d40bd46c0d8c1fc0fc6f49cb37e978b8132d5c5077d15b4ab8d9f46db77d`.
>
> J'approuve le nodeid unique `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`, les trois identités commit/tree, les 34 entrées de l'inventaire, le Python et les dépendances, le cwd, la commande effective incluant `-s`, l'oracle et les critères numériques inchangés décrits dans ce manifeste et ce dossier.
>
> J'accepte le protocole R1 : les assertions pytest, les diagnostics et les verdicts scientifiques sont enregistrés séparément. Une hypothèse gamma non démontrée impose `INCONCLUSIVE`, sans tolérance de secours. Un succès pytest ne promeut pas ce contrôle en `PASS`. Si les assertions obligatoires passent et que gamma reste indéterminé, le verdict scientifique global reste `INCONCLUSIVE`. Un échec obligatoire reste `FAIL`; les preuves absentes, invalides ou contradictoires restent `INCOMPLETE` ou `ERROR`.
>
> J'approuve une tentative maximale, un timeout de 300 secondes et le plafond logiciel de 16 MiB par flux. J'approuve la destination `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R1-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\<new_run_id>\`, avec un nouvel identifiant généré par le runner, sans écrasement ni relance automatique.
>
> J'accepte pour ce cas de code connu les limites de l'exécution Windows locale non attestée : même compte interactif et droits courants, absence de sandbox et de protection des archives contre ce compte, de token restreint, de Job Object, de quotas matériels stricts CPU/RAM/disque et de garantie de terminaison des descendants. Le timeout vise l'enfant direct et le plafond des journaux est sondé, avec dépassement possible entre deux contrôles. Les fichiers locaux, décisions et empreintes ne fournissent pas d'attestation cryptographique ni d'archivage indépendant.
>
> Cette décision est valable 24 heures après ma confirmation explicite. L'opérateur consignera l'identité Owner, l'heure UTC de cette confirmation et l'expiration correspondante dans l'enregistrement local séparé exigé par le runner. Aucun enregistrement ne doit être marqué approuvé avant cette confirmation.
>
> Avant lancement, je demande la vérification du manifeste et des trois checkouts propres, des hashes, de l'environnement réel, du chemin d'import scientifique, des bibliothèques et threads, de la commande, de la destination et de l'absence de tentative déjà réservée. Tout écart impose l'arrêt avant calcul. Je demande la conservation des sorties brutes, JUnit, sélection réelle, métriques, statuts, erreurs et reçus, y compris négatifs, puis leur revue et une copie d'archive contrôlée par l'Owner avant toute conclusion de qualification.
>
> Aucun nouveau solve linéaire, raffinement, autre nodeid, W1/W2 ou rejeu n'est autorisé. U3 reste `FAIL`; aucun résultat WP12-U n'est modifié. Cette décision ne promeut aucune maturité et ne clôture pas WP12 ou WP13 ; elle n'autorise ni merge, tag, release ni publication.

## Texte de refus proposé

> Je refuse l'exécution du manifeste SHA-256 `fe19d40bd46c0d8c1fc0fc6f49cb37e978b8132d5c5077d15b4ab8d9f46db77d`. Aucun lancement scientifique n'est autorisé. Le dossier reste `PREPARED_NOT_AUTHORIZED` jusqu'à une nouvelle décision explicite.

The proposed 24-hour decision validity is an Owner choice in the approval text, not an approval already granted. The existing local runner requires explicit approval/expiry timestamps. The local decision record is operational and non-cryptographic under [QUALIFICATION_LOCAL_VV](../../LOCAL_VV_POLICY.md); no Ed25519 identity, key or signature is created here.
