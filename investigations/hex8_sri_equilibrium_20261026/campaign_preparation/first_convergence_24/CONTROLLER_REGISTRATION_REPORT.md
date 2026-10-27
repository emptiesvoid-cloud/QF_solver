# HEX8-SRI — rapport d’inscription contrôleur et préflight collect-only

**Statut : `HEX8_SRI_CONVERGENCE_24_PREFLIGHT_READY_FOR_OWNER_REVIEW`**

Ce rapport couvre la préparation contrôleur et les 24 préflights collect-only. Il ne contient aucun résultat FEM : les corps des tests n’ont pas été exécutés, aucun assemblage ou eigensolve n’a été lancé et aucune tentative n’a été réservée.

## Identités figées

| Objet | Identité |
|---|---|
| Branche science au préflight | `research/hex8-sri-equilibrium` |
| HEAD science enregistré par les reçus | `247ff753a8851cd6341633811313c5667579034a` |
| Fingerprint source science | `1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555` |
| Commit code scientifique gelé | `7ff2809a854e1434619c261195e78b901be0ea78` |
| Branche contrôleur | `codex/hex8sri-controller-registration` |
| HEAD contrôleur | `43af3e8b3d17b3be1dfaa8fed3d390f29a5cc80f` |
| SHA-256 runner | `51124e8e81e9bc044366421546f9592763fdad41295ce9c571d9cd1d0ac7813a` |
| SHA-256 plugin pytest | `16a1db698d8d9379dfcff4c0b56db23ac1adfea056c8a55ba967e8af50d667bc` |
| SHA-256 policy | `f8941a7c32ce99b9d0e580157ee3451f88982b553b6a663ea772c35f9d4076b2` |

Le worktree science était propre au préflight; son identité correspond au contrôleur enregistré et son fingerprint égale celui demandé. Le commit de gel source est un ancêtre du HEAD science préflight.

## Inscription isolée

- Scope : `hex8sri-convergence24`; campagne : `HEX8-SRI-CONVERGENCE-24-2026-10-27`.
- Mandat dédié : `DEVELOPMENT_AUTONOMOUS-HEX8SRI-CONVERGENCE24-2026-10-27-v1`.
- Exécution : `execution_authorized=false`; les 24 manifestes portent `do_not_execute=true`, `execution_state=PREPARED_NOT_AUTHORIZED` et `frozen_criteria=null`.
- Les nodeids sont exactement ceux de la matrice 3 formulations × 2 coefficients de Poisson × 4 maillages. Aucun nodeid supplémentaire n’est inscrit.
- Ledger dédié configuré : `node-attempt-ledger-hex8sri-convergence24.json`. Il n’a pas été créé et chaque reçu indique `attempts_reserved=false`.
- Les entrées historiques `d01`, `c01`, `e01` et `hex8sri`, ainsi que les champs de politique de premier niveau, sont sémantiquement identiques au contrôleur de base `0d6286ecf75eea62ecafe63ec81cc816ad95226d`.
- Le runner vérifie le SHA du `common_problem.json` : chemin relatif au manifeste, confinement au worktree et égalité avec le SHA inscrit.

## Configuration et budgets

| Maillage | Éléments | Nœuds | DDL totaux | Bloqués | Libres | Budget par nodeid |
|---|---:|---:|---:|---:|---:|---|
| 4×2×2 | 16 | 45 | 135 | 27 | 108 | 180 s / 512 MiB RSS soft |
| 8×4×4 | 128 | 225 | 675 | 75 | 600 | 300 s / 1,024 MiB RSS soft |
| 16×8×8 | 1,024 | 1,377 | 4,131 | 243 | 3,888 | 900 s / 4,096 MiB RSS soft |
| 32×16×16 | 8,192 | 9,537 | 28,611 | 867 | 27,744 | 3,600 s / 16,384 MiB RSS soft |

Tous les cas sont appariés sur la poutre 20×1×1 m, E=1 MPa, chargement et appuis de la définition commune. Les paramètres variés sont uniquement formulation, ν∈{0,3; 0,4999} et niveau de maillage.

Budgets partagés : une tentative maximale par nodeid, 24 tentatives au plus, 8 processus, stdout/stderr 8 MiB chacun et 16 MiB cumulés, temporaire 512 MiB, archive 256 MiB, plancher disque 2,048 MiB, threads BLAS à 1. RSS/temp/archive sont des observations surveillées et non des quotas OS; le watchdog temporel est best-effort. Somme des plafonds temporels séquentiels : 8 h 18 min.

Les critères restent ceux proposés dans les brouillons; ils ne sont pas gelés par cette inscription. Le manifeste conserve `criteria_status=PROPOSED_REQUIRES_OWNER_FREEZE`. La référence indépendante 3D reste `NOT_IMPLEMENTED_OR_QUALIFIED`; la valeur Timoshenko ne vaut qu’oracle de tendance. Aucun critère ni seuil n’a été modifié.

## Résultats des 24 préflights

Chaque préflight a été lancé par `scripts/development_autonomous.py preflight` avec un nodeid exact. Le validateur final a accepté chaque reçu après sa création. Pour tous les cas : `PREFLIGHT_PASS`, `PYTEST_COLLECT_ONLY`, `return_code=0`, un nodeid collecté exactement, solveur importé depuis le worktree science, `NO_SKIP_MARKERS`, `bodies_executed=false`, aucune tentative réservée.

| Nodeid exact | DDL totaux/libres | Budget | SHA-256 manifeste brut | SHA-256 liaison contenu | Preflight ID | SHA-256 reçu validé |
|---|---:|---|---|---|---|---|
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `cab08de7d46d1f0c54947890f5662edf6c28cc5e76e374626c17af0fe14947bf` | `6aaff4a9c93c02d6a9a3d54f7a540848d0717dd2da2c9acb6f85262de7e5bd5d` | `pf-4c12c2b7a800` | `3da864e8e878589508b39fb9203cf782a9ac481949402e74f2b9d9518eacb8d6` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `07a6f7ab906325f636f3a5cdd03f8518fc85b46520f0d6654938fc21850a397b` | `94510e6440d7b151526cc76353d2d69df0abbd8230ab133a3e4fb6c4e23fdc21` | `pf-6e43388e4eeb` | `3107a3a96de80a4a18c062387f1ccd3e965f2801f9ba66c6dee5ac087ec98b67` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `eeb4d8eb134be9e18cdea4a048662abb4eca79faeec1c84988d145e707554827` | `59062a9aa03fc319d70942f99dc0d4998b16144a94d8caf45916a1bcef3840a3` | `pf-d4cdf8a1f579` | `ae4dd3f044ecd47abcb6c98cda1e89574ce9f6e48987035f53a27d8a75d9f045` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `4e63d1e3648bf6f9fb6074c44a98f06f90a77cb29a0b1f8b5525b3e17dbc9ffc` | `6b2d6a3ba7832ba8502386b6fb6d8874fe65a550d08eed9330c864d784c2ed36` | `pf-4c7aee5a6230` | `5b5475c67b506ef7afcef341c5102827f3a6965df76edce648a539399f4c168c` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `efdd037b20e491ac9f3d42c29f686649fdc124a5b2ae23c07a5bbbfe64948bc5` | `f1ea0de77113e143d2ffb52c44d118b4243d31bb2663874d1df93fa490fbee94` | `pf-03b68a835c30` | `f2c831b334d20cc9a423f67df9d3d3a07e3d44efdcae3f48e1683039b486d46b` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-4x2x2]` | 135/108 | 180 s / 512 MiB RSS soft | `3538e4fdb54e5197fbe3ddae442bafd4e2687080dd82abb01ff1cc13cf3ace17` | `3a6bd2c37742b486b622c80f236dba8fee4e082db2259a90ed14a4de1d0b0e49` | `pf-20b00fb7de43` | `45ee66c1c3bb62ce065102fd831abde9672ba28ed6f9b19e9ce46a701ff887b4` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `d967ea5584b590db7e01fb3db52a1a6af2d9413f6c41b2514b4dc9e05b72dc55` | `215ae09ad2991afc9a5f968f3cecf691371118023606be13009af07ba342da2e` | `pf-9e08894879c3` | `953416947f944daf8bb41f1b616a2b47cfae11652a31e9488b43731591e5fa5d` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `5e28cae677266a635ffee8601c8e96d343884b758a0e4555dafbad0d631bd29e` | `13c0558df031a796ef5a3dd10d96698b83daeb66c3fce8a12b43713cb1c08392` | `pf-f7450090b53b` | `f5a9e896855c3032eb75961eaa99566b7f53c85ad42ea4e0baa9b4e08e1782d0` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `ab507b6a9149bb876cb69cfddb03a797eee8eaa1ec063fdd444e38cb40518771` | `6e937595e7687f6e066ff54bbcdc8de5d2976c215e6fe6cd6cba7e5220811ec2` | `pf-d0872c3e227c` | `aebf2c58ebb8ed744b8fc4501338de9e08dc3c6d3a25e05d1ee409a3aa37863a` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `93d520fc3def80775c37416b2539f26a49a0ece24a6a7380135724e59becb9ff` | `0710b0a5188174bb27bb0d373c66fea6ee081bb21fe0d9598220536e0004cede` | `pf-72ca99f6cd50` | `46eaab7be8f9ead447d2c46f27e20e806ca88327a0b01f684392c8893206835d` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `94806494a609b05c1a489c15212b46cf26825c57e6b958373c08e4769675872c` | `9964969e81af80eed8fcb366baa658d7be3a8293ea99ab5a0c65f9eff5fa2cc1` | `pf-5b83cc3d6b07` | `26a00aaae31fecdcbc48f38dfa113c6c9f46170de832d94c681659755bd29dcf` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-8x4x4]` | 675/600 | 300 s / 1,024 MiB RSS soft | `b39a55cdf78a247e3b7c7beda4cf0bc63c8334a596896169460d54d614ef03f5` | `8219cd42f65d1ae897d05f2e8f6ca4b44898025b97f243d767ee44d7f941040a` | `pf-21384b44c8d4` | `00486a0f35f528505363b354a1ef9d57d1c95be9d18ced30267560a9ce0f2706` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `51be8818a93a69fc55ca3f5ae964400d4033a701386a0addc934bb4978bbed9a` | `6c47b816f4d003c60243944dd2cd41963c832f360f2b9f328ae83e9a54bd26fc` | `pf-492db27e82cd` | `9638b2f1eae31e21519d16015931e9539715a35e73122df4e515c9a1ab782c4e` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `6627ded8bf20010c85866a858dfd90913b6a1ffa866b6cbc83f7fc59671c599a` | `54c66127261633a91b7fd12becd90bf0e65c51467d871f2d714f1e8c16736a38` | `pf-1bbdce9e29f9` | `bf6be649ac41007429d2940733d37ede38df251fa42e6c4bd87687427a8007fe` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `a5d01ec76bd24e9fb3b2c4493c2a0dc7871aacecd92aab31ca93285e037fcd68` | `0d911341cb00c854af05b88b849c9ec79e2fc89aeaa531c00d2eb641e05b4f15` | `pf-90a67b51ceb9` | `bf7c1e292a33fb0bc09201fd9151987094efdac13876cb717e2a196190148004` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `72963a8edb4f1b4d4650cb64a2d134bd7d2a2dc845852a2514c343541dde893b` | `9ea42a28bb840e2c2f0eeb5f5052985e17b7f0727c1d7cf86ac6cd665f3639e0` | `pf-5c073ffc3046` | `5a26089cc34c43df2a8ce2d2216cc01f9ce31d2eb47a04f17b8b0bf3c0f7227c` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `2e98ae1abdd1a0d69520edd9c26bd629df3010d505f3a580da1464c4ca5a02dd` | `1a4dbd95e1c781ea97c5bedb3d550f9b16c69fc133936df50aa7b0e209dfc8ec` | `pf-dbfff6ca5d10` | `d929ae2f5295b914d4c90654a0a8eec31916476626e34c123a8acf091e61b9fa` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-16x8x8]` | 4131/3888 | 900 s / 4,096 MiB RSS soft | `09f1e6a9be67c8b44f65f592c8a9870b14f724414bd5bcae446168168af5c7cc` | `f08cb9cab490bf7ec5d3750ba11fa8ab79246409368cefb9e42c6a04c92dbb0a` | `pf-626a961b21c3` | `4681c2f07bdf271fdbc914dc2be1d44bb75560cd0bb6db082ae435d3d204d7d7` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `b9907b820296936efb7eb063074d3ba6b4838f95ce899c606633c9504f6c28da` | `e2ee784cf2e5af50c40468f51cb5705540d1fb2e97c54b45728bf037fc3a19ff` | `pf-06405ccdabe1` | `d74ac3acb548e56cd71309205d9d457b989067eabc0b365337367261534038c6` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `0b8b4368db94c8075433a1e5d237a8377780864e4cf8a4dd8e0ef618e2aaef32` | `b73269ebe49aa303e4024bf7454016df8b84160f5d8722e590e520b20160ba35` | `pf-4785e22d3539` | `6ededf8ea8081d4b9c3265d536ae619435ce382d1deda8c9081664b26c007682` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `5ee87f243f4b9e5a7bf47151024ccc28e7e0917b92855874564ad16374b924ae` | `694b5cce25089f6abcdbac147b60ed448274f44d10cecf15770c8ba98d3f9ce0` | `pf-b6b64064bcd6` | `dc05ef9ac250b4cf64669d44402c6629526625d0688f93ae4f225cd37c078aa3` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `deb271b443391f4b1ca88cea561d2b69f3e12b9a5ff073895ad764dbb74741cd` | `9818cfdefd6f861d22baff9f9a892ffeee593dc37d8c5e4343dc1c1bc383b3d2` | `pf-be81a5197879` | `ed12e5677d876c1dfc1969d2902ec811213c1a976cd3e96b82f631fbd0123906` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `100a550c8d23dccce4f846e92f60f9a149d7057718f9f55130729a77a87ac80c` | `61df91a4af8b13195c369bbfe1637028c5d7fb82e59f8d8f9652cedef19e73ed` | `pf-573c5de6af91` | `d4d3158dd8b6a3e8d417ea6060d1579c8884a74ca3051c305e7d0304dbd5f476` |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-32x16x16]` | 28611/27744 | 3,600 s / 16,384 MiB RSS soft | `e53e5ff77ebecf7dc6a5d6d2123f6e3d9aecd45eb3c77632d6e7f99aeb1fe6f2` | `544b9951973754b52913ad96dd515b11b9acc9632dab236b09e93ec17725632d` | `pf-cce5790c722b` | `66d95127a6e1e626ccc393a1d5cda265245f40a2ed57e0d5e1342d98d7ae2be4` |

Les copies exactes des 24 dossiers de préflight (reçu, checksum, stdout, stderr et rapport de collection) sont dans [`preflight_receipts/`](preflight_receipts/). L’index machine est [`PREFLIGHTS_INDEX.json`](preflight_receipts/PREFLIGHTS_INDEX.json), SHA-256 `b81befa67a54c7b86d2f89853fb6243c97c5d085ccc577fab84e5f69ebd53af4`. Le fichier [`SHA256SUMS.txt`](preflight_receipts/SHA256SUMS.txt) couvre les dossiers et l’index (121 fichiers), SHA-256 `b6c8d9ad6ff5e2bbe2773ec44f309b8812676bde4a2fa78e5c7d006b8090dfab`.

## Contrôles du contrôleur

- 22/22 tests exacts de l’extension convergence24 PASS, incluant refus de scopes, nodeids, budgets, empreintes, contenu manifeste, autorisation, marqueur skip et ledger falsifié.
- 12 autres nodeids unitaires ciblés PASS : D01/C01/E01, collect-only, reçus historiques HEX8-SRI et namespace de sortie.
- `ruff check`, `py_compile` et `git diff --check` PASS.
- `ruff format --check` reste en échec sur ces fichiers, mais échoue aussi sur leurs versions de base inchangées. Aucun reformatage global non lié n’a été appliqué.

Le scope historique `hex8sri` et ses six manifestes autorisés ont été conservés sans altération. Leurs SHA correspondent aux valeurs enregistrées. Ils portent le fingerprint historique `e14217217a6044ca9cb7c64a0f187864121589463c00e1eaac53251696b60c29`, différent du fingerprint courant calculé pour leurs nodeids (`5d1733d8f1272b5fb39d4ea745338c84ac873c58eb8b084b921132e0c27f27be`). Le contrôleur refuse donc ces anciens manifestes sur le worktree science courant par contrôle d’identité source; aucune tentative n’a été lancée avec eux.

## Livraison et limites

- Commit manifests préparation : `8dd9dbd0700d82652c1c9ab3dcc7342379761ef9`.
- Commit final d’identité des manifestes : `247ff753a8851cd6341633811313c5667579034a`.
- Commit contrôleur : `43af3e8b3d17b3be1dfaa8fed3d390f29a5cc80f`, poussé sur `codex/hex8sri-controller-registration`.
- Aucun manifeste n’est devenu OWNER_AUTHORIZED. La campagne reste `PREPARED_NOT_AUTHORIZED` pour toute exécution FEM.
- Aucun calcul FEM, assemblage scientifique, calcul modal ou eigensolve n’a été effectué. Aucune intégration vers v0.2.12 n’a été faite.

Prochaine décision Owner requise : autoriser explicitement ou refuser une campagne de résolution sur les 24 identités et empreintes rapportées. Cette décision doit rester distincte de la présente autorisation d’inscription et de préflight.
