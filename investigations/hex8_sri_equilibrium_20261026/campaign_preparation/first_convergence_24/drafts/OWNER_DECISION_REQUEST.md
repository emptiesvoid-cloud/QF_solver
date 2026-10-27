# Décision Owner demandée — préparation du premier lot de convergence

**Statut : `PREPARED_NOT_AUTHORIZED`. Cette demande ne couvre aucun calcul FEM.**

- Branche scientifique : `research/hex8-sri-equilibrium`; HEAD `7ff2809a854e1434619c261195e78b901be0ea78`.
- Fingerprint scientifique : `1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555`.
- Contrôleur actuel (provisoire) : `codex/hex8sri-controller-registration` à `0d6286ecf75eea62ecafe63ec81cc816ad95226d`.
- Runner SHA-256 `d73a2a4f6173d53f49d90899a8d71c112371bad7a97c350c6076f8f96327f198`, plugin `c1cf6238bba05fa24de5c455beac9ddd6844935999e8b4556d3b13e5f6e9ee16`, policy `f44e167e66c00ed211d385de721883bc05d9c0db9892fc5e5fcc498d0e80693d`.
- Campagne : `HEX8-SRI-CONVERGENCE-24-2026-10-27`, 24 cas, une tentative par nodeid, aucun retry.

## Décision sollicitée

Autoriser Configuration à proposer et vérifier, sur sa branche dédiée, une extension minimale du scope HEX8-SRI pour ces 24 nodeids, puis à produire un collect-only officiel par nodeid après succès de ses contrôles. L’extension doit préserver D01/C01/E01, les six inscriptions historiques, les préflights légitimes et le verrou FEM. Le runner transmettra le chemin du manifeste exclusivement depuis l’entrée enregistrée via `QF_DEV_MANIFEST_PATH` et vérifiera son SHA-256.

Cette décision ne transforme aucun manifeste en autorisé et ne lance pas les tests. Après extension revue, les manifests et préflights seront liés aux nouvelles identités contrôleur; une demande Owner distincte portera sur les exécutions scientifiques et les critères gelés.

## Cas et SHA-256 des manifests brouillons

| Cas | Nodeid exact | Mesh / ν / formulation | Budget proposé | SHA-256 manifest |
|---|---|---|---|---|
| `hex8_standard_nu_0p3_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]` | `4x2x2` / `0.3` / `hex8_standard` | `180s, 512 MiB RSS souple` | `224586429e993ca139ed7ff78b313efa91ab6181f33e06d4051051a8d3dd5618` |
| `sri_historical_nu_0p3_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-4x2x2]` | `4x2x2` / `0.3` / `sri_historical` | `180s, 512 MiB RSS souple` | `7036052404a94dcb3f0aa0b8914921e31fcf967b85d281a281e07dd8951b8608` |
| `sri_corrected_nu_0p3_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-4x2x2]` | `4x2x2` / `0.3` / `sri_corrected` | `180s, 512 MiB RSS souple` | `3fe35be175359dc54984f18d84b4f41af1bfee35514e1f5077b056b26b8a996b` |
| `hex8_standard_nu_0p4999_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-4x2x2]` | `4x2x2` / `0.4999` / `hex8_standard` | `180s, 512 MiB RSS souple` | `0243b6c0f35776f65c61072e8c0b5005d4675b6ca342e0ee7251a8de16ddec19` |
| `sri_historical_nu_0p4999_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-4x2x2]` | `4x2x2` / `0.4999` / `sri_historical` | `180s, 512 MiB RSS souple` | `5924028c7d6f8a94b46a72ef31ed31f1020ea6d815ae7c9636bd5d287d4c84a7` |
| `sri_corrected_nu_0p4999_4x2x2` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-4x2x2]` | `4x2x2` / `0.4999` / `sri_corrected` | `180s, 512 MiB RSS souple` | `a3fae93b02fcc11b05ad9c4bd988695070a094892404abf422ec8e63480159ca` |
| `hex8_standard_nu_0p3_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-8x4x4]` | `8x4x4` / `0.3` / `hex8_standard` | `300s, 1024 MiB RSS souple` | `22cb84b90013f726fb6828d8b4a8a4e9e2ff9c2ead0a9a467b992eb74a3fb254` |
| `sri_historical_nu_0p3_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-8x4x4]` | `8x4x4` / `0.3` / `sri_historical` | `300s, 1024 MiB RSS souple` | `fa1dc87da560cfa67ddba8b1b09a80f1ff26e336372fd1188240883a7254e4f4` |
| `sri_corrected_nu_0p3_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-8x4x4]` | `8x4x4` / `0.3` / `sri_corrected` | `300s, 1024 MiB RSS souple` | `7f61405c4bb12afed7fd2f178470db407e1b2cdf54f401aad3bcb0a1dc7c2e45` |
| `hex8_standard_nu_0p4999_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-8x4x4]` | `8x4x4` / `0.4999` / `hex8_standard` | `300s, 1024 MiB RSS souple` | `33f1baa5fb189e11a2857309c008a1a345a39914bcb27fc65119b9e9666ebd58` |
| `sri_historical_nu_0p4999_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-8x4x4]` | `8x4x4` / `0.4999` / `sri_historical` | `300s, 1024 MiB RSS souple` | `fd8ea2a8d1ec13c05dfc0c0f4015d658e20527a592e63ac5c88076123714a5b9` |
| `sri_corrected_nu_0p4999_8x4x4` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-8x4x4]` | `8x4x4` / `0.4999` / `sri_corrected` | `300s, 1024 MiB RSS souple` | `1d4262a1d839c77088634d6879226051cc7817262cb6cfeb8c4cd99d37320566` |
| `hex8_standard_nu_0p3_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-16x8x8]` | `16x8x8` / `0.3` / `hex8_standard` | `900s, 4096 MiB RSS souple` | `93f54c5744ba5b133e4a2c8027489405777f3f3b6c932986772a8dd70602c037` |
| `sri_historical_nu_0p3_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-16x8x8]` | `16x8x8` / `0.3` / `sri_historical` | `900s, 4096 MiB RSS souple` | `2bcf57369becbde3e6ee52a23c12d1d0f89fcfac718d768073426d0470dc6ebd` |
| `sri_corrected_nu_0p3_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-16x8x8]` | `16x8x8` / `0.3` / `sri_corrected` | `900s, 4096 MiB RSS souple` | `f47afc440267e8db6c089177db228ed87f31f2c0456d797303094128a25d33b5` |
| `hex8_standard_nu_0p4999_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-16x8x8]` | `16x8x8` / `0.4999` / `hex8_standard` | `900s, 4096 MiB RSS souple` | `35337ff55a3ba56fbae134babe0eb94daedc4bab5c22dc94bd293f3499933999` |
| `sri_historical_nu_0p4999_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-16x8x8]` | `16x8x8` / `0.4999` / `sri_historical` | `900s, 4096 MiB RSS souple` | `4b1cb65ae717bbae422e3e64a211aa9ad7a1b42183912bf666ee35ac5cee9214` |
| `sri_corrected_nu_0p4999_16x8x8` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-16x8x8]` | `16x8x8` / `0.4999` / `sri_corrected` | `900s, 4096 MiB RSS souple` | `c8ea321b06606e2f8b6a095c69a26a2dfb5a41783bc8745c7e3370ac13d235d4` |
| `hex8_standard_nu_0p3_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-32x16x16]` | `32x16x16` / `0.3` / `hex8_standard` | `3600s, 16384 MiB RSS souple` | `d160133540298e1be1241df478f1e5811e9e8b80b0d5a09e975090282f601703` |
| `sri_historical_nu_0p3_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-32x16x16]` | `32x16x16` / `0.3` / `sri_historical` | `3600s, 16384 MiB RSS souple` | `3cda176558f57a8b6d30ca22c495399d44a81869241466d303ff7ec0347e6d11` |
| `sri_corrected_nu_0p3_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-32x16x16]` | `32x16x16` / `0.3` / `sri_corrected` | `3600s, 16384 MiB RSS souple` | `c4094524fb8a6e6afc69505b1a2a5963f050b43c0350fac6ee6b4e35c8f642bd` |
| `hex8_standard_nu_0p4999_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-32x16x16]` | `32x16x16` / `0.4999` / `hex8_standard` | `3600s, 16384 MiB RSS souple` | `3036ed019ce9139584a84fc4d3f67fa25a0edaa9399d2111f89145fbd75dba85` |
| `sri_historical_nu_0p4999_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-32x16x16]` | `32x16x16` / `0.4999` / `sri_historical` | `3600s, 16384 MiB RSS souple` | `0638beff323aaf2162edfe98c11f6e474b2e013d31b3b47c67e30e7e768e3137` |
| `sri_corrected_nu_0p4999_32x16x16` | `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-32x16x16]` | `32x16x16` / `0.4999` / `sri_corrected` | `3600s, 16384 MiB RSS souple` | `d2555d2fdd76025da593e0ba1eb1fcfdf605eabfbabd5e4fd8350c76a109342c` |

## État des preuves

`common_problem.json` SHA-256 `48f1c5b59b74b4148c8167c967c634b381cb48b3c24a1702dc1252e5d6def809`; `registration_request.json` SHA-256 `a0b0c20888db08550af5fb8531d523f9cfc225c62a2569908539564d5db412e5`; `FIRST_CAMPAIGN_MATRIX.csv` SHA-256 `12643e98189dec53c18e3c9df23f019dc181b3408f982dcdb0dd0f6040ca8ba9`.
Tous les manifests portent `execution_authorized=false`, `do_not_execute=true` et `criteria_status=PROPOSED_REQUIRES_OWNER_FREEZE`. Aucun préflight n’existe.
