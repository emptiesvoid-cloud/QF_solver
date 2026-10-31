# Candidate artifact verification — v6

**Result:** `PASS_CANDIDATE_PACKAGE_ONLY`
**Candidate source:** `2865587a44f9e461a0b4e4286c912c17e4f04be5`
**Execution/report HEAD:** `d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23`
**Build contract:** `QF-0212-WP13-SELECTED-CANDIDATE-20261031-06`
**Contract SHA-256:** `f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`

This verification checks selected candidate archives, their contents and installed non-solving behavior. It performed no structural solve, changed no ledger or qualification evidence, and did not publish or release anything. It does not clear the whole-repository G03 failure.

## Reproducible builds

Two independent runs used the same v6 contract, Git-blob materialization, Windows Python 3.13.1 x64, `build` 1.5.0, `setuptools` 82.0.1, `wheel` 0.47.0 and `SOURCE_DATE_EPOCH=1793444684`. Both returned `PASS_CANDIDATE_PACKAGE_ONLY`; each selected 585 package inputs and scanned 585 wheel files and 593 sdist files with zero findings.

| Output | Run 1 | Run 2 | Reproducibility |
|---|---|---|---|
| Wheel, 1,689,662 bytes | SHA-256 `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a` | Same SHA-256 and size | Byte-identical |
| Raw sdist | 1,320,001 bytes; SHA-256 `f4aaafffc184c662808f061e2b234fe4d6623ae07f2a3c18f2d74721185f71e3` | 1,320,067 bytes; SHA-256 `15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5` | Raw gzip archives differ |
| Normalized sdist, 1,294,049 bytes | SHA-256 `183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde` | Same SHA-256 and size | Byte-identical after the source-bound normalizer |

Both run result files and output manifests are retained externally:

- Run 1: `E:\QFSolverAgents\wp13_candidate_build_20261031_v6_run1`; `result.json` SHA-256 `0f417ca4072a954667040954babc98dfa24b2e151546e0042e28ba0fb4b70610`; `manifest.json` SHA-256 `442ec774519d3ed73da87efbb3049180f1855573d1b570d0f703238f2bd798bb`.
- Run 2: `E:\QFSolverAgents\wp13_candidate_build_20261031_v6_run2`; `result.json` SHA-256 `9ed03f96d620f09309d4f0b09a9a2447a5195afc5753965bb89f99e2511cd0ae`; `manifest.json` SHA-256 `355427e49ad044c2684fd268a1f4fa3bb1a7445369708bbf00d9756d11ac917a`.
- Supplemental normalized-build, install, CLI, check-mesh and twine records: `E:\QFSolverAgents\wp13_candidate_package_checks_20261031_v6\record.json`; SHA-256 `31b602fb73fd2f2c365c50789caa70d76bc0372bc000348ec9da696e9b090653`.

Twine 7.0.0 checks passed for both runs' wheel and raw sdist, plus both normalized sdist outputs. The run-1 log is `E:\QFSolverAgents\wp13_candidate_package_checks_20261031_v6\twine_run1_check.log`, SHA-256 `7d90422da43d7ba7907e74a2b94a27aaa15304d65c2e8c316f1c70e6d9f3d58b`; the run-2 log is `E:\QFSolverAgents\wp13_candidate_build_20261031_v6_run2\twine_check.log`, SHA-256 `e9990184e9cf0eeca80dbd770f2021f165e588edbf0dde23ca6886b7b898a3a3`.

The v6 build runner itself performed a no-dependency wheel install in its build environment. The separately required dependency-resolving wheel and sdist installs are recorded below. This distinction prevents the contract's broader install language from being mistaken for work performed by the build runner alone.

## Fresh installed-artifact checks

The run-2 wheel and raw sdist were each installed from their exact local artifact path into a new independent Windows Python 3.13.1 virtual environment, with normal dependency resolution and no checkout on `sys.path`. Pip reports bind the install to the exact wheel and sdist hashes. Both environments resolved 501 installed solver source files to `site-packages`, reported version `0.2.12`, and passed `qf-solver --version` and `--help`.

Resolved runtime packages in both environments: `qf-solver 0.2.12`, `numpy 2.5.4`, `scipy 1.18.1`, `matplotlib 3.11.2`, `contourpy 1.4.0`, `cycler 0.12.1`, `fonttools 4.68.0`, `kiwisolver 1.5.1`, `packaging 26.3`, `pillow 13.0.0`, `pyparsing 3.3.3`, `python-dateutil 3.0.0`, `six 1.17.0`, and `tzdata 2026.6`; pip was 24.3.1.

| Installed artifact | Environment and evidence | Result |
|---|---|---|
| Wheel `ae521113…b39c287a` | `E:\QFSolverAgents\wp13_deps_wheel_20261031_v6`; install report SHA-256 `0adc8a1908c9d91fc65c47b05a2646d4da5d604de9e7e9a4d1d20353cee44fc5`; probe SHA-256 `ed8ab4cac5e15af08f70a4c873ecc3ffee3f570565ef04d6dec434094d108edb` | **PASS** |
| sdist `15c838af…cbf082e5` | `E:\QFSolverAgents\wp13_deps_sdist_20261031_v6`; install report SHA-256 `7fcd951fa10727a137fa2619d0df7854a8d6cbd6d5749715eba2be6255e6790e`; probe SHA-256 `2abed85448db8e877ce0eb198d85dfa7220e87862e0ec2ad52e6c25ad3804017` | **PASS** |

For both installs, `verify-all` returned exit 2 with the expected `UNSUPPORTED` message because an installed distribution is not a complete Git source checkout; no report was created. The probe treats this fail-closed boundary as expected and passed.

The six installed `check-mesh` commands also passed: `tet4_static.json`, `beam2_cantilever.json`, and `mitc4_shell_static.json` from each installed distribution. Each output was exactly `MESH STATUS: PASS` (log SHA-256 `87e8211ca1c74f89357ffe3fc4a371366fcbd563725eedd58ac1b83a60bc5bde`). These commands validate model and mesh input only; they do not assemble or solve a structural model.

The six pre-existing v4 checks are additionally applicable to the v6 solver behavior: a Git diff between v4 source `60c202a75d20c6dea1df35aab591bd3832d12c58` and v6 source `2865587a44f9e461a0b4e4286c912c17e4f04be5` found `src/solveur/`, `src/qf_solver/`, `examples/`, `pyproject.toml`, and `MANIFEST.in` unchanged. The only changed file among those selected distribution inputs was `requirements/baseline-standard.txt`.

## Structural-solve boundary

No static, modal, or dynamic structural solve was performed. The build contract explicitly sets `structural_solves_allowed=false`; its installed-artifact probes cover import origin, version, CLI, and the expected `verify-all` refusal only. A fresh WP13 package-smoke controller and its exact Owner-bound reservation are not present. The three proposed solve cases and their oracle limits remain in [`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md), status `PREPARED_NOT_AUTHORIZED`. No smoke-test `EXECUTION_PASS` or numerical-oracle claim is made.
