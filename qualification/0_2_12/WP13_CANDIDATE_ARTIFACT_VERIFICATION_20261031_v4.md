# WP13 candidate artifact verification — v4

- **Date:** 2026-10-31
- **Project:** QF Solver 0.2.12 alpha
- **Release base:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`
- **Frozen package source:** `60c202a75d20c6dea1df35aab591bd3832d12c58`
- **Execution HEAD:** `bf6004a9be324798558b537c744ceb73343bc1a7`
- **Contract:** `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04`; contract commit `e0d552173f932eaf7a7ef584f1f9026fd84bf336`; contract file SHA-256 `f8c43bd1bad5987acb589c7735ac7a1e39e0f7119e50a49dd2061cd135954833`.

## Result boundary

The selected Windows candidate build, installation, CLI and mesh-check gates
passed. This establishes bounded candidate artifact evidence only. It is not a
general solver qualification, a whole-repository clearance, or authorization to
publish. No FEM, benchmark, structural solve, publication, tag, release, or
public-site deployment was performed. WP12 evidence, scientific ledgers,
thresholds, and maturity dispositions were not modified. G03 remains
`FAIL_PRESERVED`.

## Frozen scope and build results

The contract selected 585 package files and 773 served documentation files.
The v4 source and documentation scans each had zero findings. The wheel held
585 files, including 501 Python modules; the sdist held 593 files. Both archive
content scans had zero findings, and `twine check` passed on each run's wheel
and raw sdist, plus each normalized sdist.

| Run | Wheel | Raw sdist |
| --- | --- | --- |
| v4 run 1 | `qf_solver-0.2.12-py3-none-any.whl`, 1,689,654 bytes; SHA-256 `8d3e571ce7d4ced533d7b97ed0bc0f7a91e29a3d530e3a1b406716fecf721b0e` | 1,320,055 bytes; SHA-256 `4d9e571583b3bd345abdbf4bca5f6b86e17d776c6d2a386019da32c8c0b8a44b` |
| v4 run 2 | `qf_solver-0.2.12-py3-none-any.whl`, 1,689,654 bytes; SHA-256 `8d3e571ce7d4ced533d7b97ed0bc0f7a91e29a3d530e3a1b406716fecf721b0e` | 1,319,963 bytes; SHA-256 `0f2c990c07d14686d2b22d1db4d705d7bc244c09022df1a7e90ef00de7fc0291` |

Raw sdist gzip files have different metadata. Normalized sdist outputs from both
runs are byte-identical: 1,294,041 bytes, SHA-256
`4fba0a1f1e700aaa6bf58c4cdd1a0edd5adea1145db886d5bf1903d30f460da1`.

The failed v3 attempt remains part of the record at
[`wp13_candidate_build_run1_failure_20261031_v3.json`](wp13_candidate_build_run1_failure_20261031_v3.json).
It found selected examples missing from the archives. The v4 packaging change
added explicit manifest/data-file entries; no scientific source or evidence
changed to address that packaging failure.

## Installed-artifact checks

The exact wheel and raw sdist were installed, separately, into fresh Windows
Python 3.13.1 virtual environments with normal dependency resolution. Both
installs completed without errors. Each probe confirmed QF Solver 0.2.12,
verified all 501 installed source files against the frozen package, and loaded
the package from the installed environment outside the source checkout. CLI
`--version` and `--help` exited 0. `verify-all` exited 2 with the expected
developer-command refusal because the installed package is not a complete Git
source checkout; it created no report and ran no solve. The Python audit hook
observed no subprocess events during these CLI probes; it is not a system-wide
OS trace.

Dependency resolution installed the same set in both environments:

`qf-solver 0.2.12`, `numpy 2.5.4`, `scipy 1.18.1`, `matplotlib 3.11.2`,
`contourpy 1.4.0`, `cycler 0.12.1`, `fonttools 4.68.0`, `kiwisolver 1.5.1`,
`packaging 26.3`, `Pillow 13.0.0`, `pyparsing 3.3.3`, `python-dateutil 3.0.0`,
`six 1.17.0`, and `tzdata 2026.6`.

`check-mesh` passed against the installed wheel and sdist for
`examples/tet4_static.json`, `examples/beam2_cantilever.json`, and
`examples/mitc4_shell_static.json`. These checks validate file parsing and
model/mesh input only. They do not assemble element stiffness or run a
structural solve.

## License inventory boundary

Both installed environments exposed all 14 listed distributions with some
license metadata and at least one license-like file. The QF Solver wheel
contains `LICENSE`, `LICENSE-DOCS`, `NOTICE`, and
`THIRD_PARTY_LICENSES.md`; its metadata declares `Apache-2.0`. The inventory
does not determine legal compatibility or grant redistribution rights.
`THIRD_PARTY_LICENSES.md` remains a starting inventory; optional integrations
and engineering/documentation tools are not bundled in the candidate wheel or
sdist. A final distribution review must follow the release rule in that file.

## Preserved gates and limitations

- v2's 16 served-document findings, the v3 archive-content failure, and the
  v3/v4 scope/build contracts remain retained as historical records.
- The v4 selected-surface scans do not clear G03 or the whole Git archive.
- The standard full suite and its coverage thresholds were not run. Targeted
  API/serialization/CLI tests, Ruff, mypy, compileall, and a strict local
  MkDocs build passed as separately recorded in the gate matrix.
- Windows Python 3.12/3.13 targeted checks are recorded; the official
  cross-platform/Python release matrix, including Linux and Python 3.10/3.11,
  remains `NOT_RUN`.
- No solver/FEM smoke test ran. No candidate artifact was uploaded or
  published. No final release authorization is implied.

## External evidence manifest

External outputs are retained outside the repository under the following
directory basenames. The hashes below bind the referenced JSON records without
embedding host-specific paths.

| External record | SHA-256 |
| --- | --- |
| `wp13_candidate_build_20261031_v4_run1/result.json` | `02a0bcaf4942b5e518928bb5af6e1550151190533df85b94a4e0999ca3b3afcc` |
| `wp13_candidate_build_20261031_v4_run1/manifest.json` | `a3b1737a168ad8028da1f10b86090c34ea776ab4ff2d84c770d2178d4eb592aa` |
| `wp13_candidate_build_20261031_v4_run1/package_check.json` | `9dd713f707cd11c6205e548c19e0293e56b5312f927500e6255a2f98aa640c7a` |
| `wp13_candidate_build_20261031_v4_run2/result.json` | `948e1dfc73e5a923fc8cc27f922036433c146072923f6b76f65b4e91d6d03a73` |
| `wp13_candidate_build_20261031_v4_run2/manifest.json` | `4ab1532b5313d927c64847ce733c7b38c7fd1fedf72d1b3500b3b17280143872` |
| `wp13_candidate_build_20261031_v4_run2/package_check.json` | `f83e3630f160d6eed383d56241966bdcfdb38a9d29f97f1f37db77b47e27c75c` |
| `wp13_deps_wheel_install_report_20261031_v4.json` | `c3821c3fc2cb54016201cb4bb5d5aa36980c4c3243e2ad3b7fa6ed972fda29ad` |
| `wp13_deps_sdist_install_report_20261031_v4.json` | `4174c1da535d983d5c8cc4821640743a1e2d02359b378cdbbae23016ffe4259f` |
| `wp13_deps_wheel_probe_20261031_v4.json` | `0ad4089c7d068ac6eb91e3855fda738ed5368d0e828d4a3227c38f8a46909f50` |
| `wp13_deps_sdist_probe_20261031_v4.json` | `8383a7891012ad93348672f376493272ec89388fc7f267c2d87787aea6217de7` |
| `wp13_deps_wheel_license_audit_20261031_v4.json` | `959f2497ae7bc1cf98d72a9845da6af01d8ef221a0585c7675743472ddfe119b` |
| `wp13_deps_sdist_license_audit_20261031_v4.json` | `d7a41ff5980c0ce5b337c8aa7b488b7a6543170ada54a6aeaaa9eb6d20420433` |
| `wp13_v4_*_check_mesh_tet4.json` (wheel/sdist, identical contents) | `ab274e429181e15037d377b6b0c37f692219a1e4fbb13aaa8d512b6c799b48d5` |
| `wp13_v4_*_check_mesh_beam2.json` (wheel/sdist, identical contents) | `94bde54bb7d5d51bcddd888a744a754689b969c113b3147322095f8190fcdf73` |
| `wp13_v4_*_check_mesh_mitc4.json` (wheel/sdist, identical contents) | `710abf6db06802565c5e4096b04502ae7fe9ff1e4806ec5d5f329aba0d803e25` |

The detailed contracts and bounded scans remain in this directory:
[`wp13_candidate_build_contract_20261031_v4.json`](wp13_candidate_build_contract_20261031_v4.json),
[`wp13_candidate_public_scope_scan_20261031_v4.json`](wp13_candidate_public_scope_scan_20261031_v4.json),
and the historical v3 failure record linked above.
