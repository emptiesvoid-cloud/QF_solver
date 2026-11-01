# WP13 technical third-party license audit

**Technical status:** `REVIEWED_WITH_LIMITS`

**Independent legal clearance:** `NOT_ACQUIRED`

**Audit evidence:** v6 wheel and sdist installed in separate Windows/Python 3.13.1 environments; the v6 contract and installation reports are identified below.

## Scope and method

The v6 package contract selected source `2865587a44f9e461a0b4e4286c912c17e4f04be5`, wheel SHA-256 `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a`, and run-2 sdist SHA-256 `15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5`. The wheel and sdist were each installed with dependency resolution into separate Windows/Python 3.13.1 environments. Their pip report SHA-256 values are `0adc8a1908c9d91fc65c47b05a2646d4da5d604de9e7e9a4d1d20353cee44fc5` and `7fcd951fa10727a137fa2619d0df7854a8d6cbd6d5749715eba2be6255e6790e`; both reports resolve the same 14 distributions.

The audit read each installed distribution's `METADATA` and license files under its `.dist-info`, recorded the Windows native libraries beside NumPy and SciPy, compared resolved versions with `requirements/baseline-standard.txt`, and checked upstream project license sources. The package wheel and sdist do **not** vendor the dependency wheels: they declare three runtime requirements and extras. The separately installed dependencies retain their own licenses and notices.

## v6 runtime dependency graph

| Dependency | v6 resolved version | CI baseline lock | License evidence | Redistribution obligations and technical risk |
|---|---:|---:|---|---|
| NumPy (direct) | 2.5.4 | 2.2.6 | `License-Expression: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`; 17 license files in `.dist-info/licenses`. The inspected Windows install contains `numpy.libs/libscipy_openblas64_...dll`. | Preserve each applicable notice and license. Its wheel license payload also records OpenBLAS and libgfortran terms. Those bundled binary terms require review if the dependency wheel or its binaries are rehosted or redistributed. [Upstream license and bundled-component notes](https://numpy.org/doc/stable/license.html). |
| SciPy (direct) | 1.18.1 | 1.15.2 | Free-text legacy `License` metadata; `.dist-info/LICENSE.txt` contains the modified BSD terms and bundled-component notices. The inspected install contains `scipy.libs/libscipy_openblas...dll`. | Retain BSD notices and the bundled OpenBLAS/libgfortran notices in any redistributed SciPy binary. The exact v6 Windows package includes the license text; do not infer the same binary inventory for other platforms. [SciPy license source](https://github.com/scipy/scipy/blob/main/LICENSE.txt). |
| Matplotlib (direct) | 3.11.2 | 3.10.3 | Free-text metadata identifies the Matplotlib license agreement; `.dist-info/LICENSE` is present and includes the project's bundled software and font notices. | Retain the Matplotlib notice and license. Its bundled components include additional terms, including font terms with reserved-name conditions. The exact license file must accompany a redistributed Matplotlib wheel. [Matplotlib license and bundled software](https://matplotlib.org/stable/project/license.html). |
| contourpy | 1.4.0 | 1.3.2 | `BSD-3-Clause`; `.dist-info/licenses/LICENSE`. | Retain notice, conditions and disclaimer. [Upstream metadata](https://github.com/contourpy/contourpy/blob/main/pyproject.toml). |
| cycler | 0.12.1 | 0.12.1 | BSD-3-Clause license text in `.dist-info/LICENSE`. | Retain notice, conditions and disclaimer. [Upstream license](https://github.com/matplotlib/cycler/blob/main/LICENSE). |
| fonttools | 4.68.0 | 4.58.0 | `MIT`; `.dist-info/licenses/LICENSE` and `LICENSE.external`. | Retain the MIT notice and review the additional external/font notices when redistributing files that use them. [Upstream licenses](https://github.com/fonttools/fonttools/tree/main). |
| kiwisolver | 1.5.1 | 1.4.8 | Modified BSD license text in `.dist-info/licenses/LICENSE`. | Retain notice, conditions and disclaimer. [Upstream license](https://github.com/nucleic/kiwi/blob/master/LICENSE). |
| packaging | 26.3 | 24.2 | `Apache-2.0 OR BSD-2-Clause`; three license files are present. | Preserve the selected license's notice and terms; the upstream package distributes both license texts. [Upstream license](https://github.com/pypa/packaging/blob/main/LICENSE). |
| Pillow | 13.0.0 | 11.2.1 | `MIT-CMU`; `.dist-info/licenses/LICENSE`. | Retain copyright and license notice; do not use authors' names for endorsement. [Upstream license](https://github.com/python-pillow/Pillow/blob/main/LICENSE). |
| pyparsing | 3.3.3 | 3.2.3 | `MIT`; `.dist-info/licenses/LICENSE`. | Retain MIT notice. [Upstream project](https://github.com/pyparsing/pyparsing). |
| python-dateutil | 3.0.0 | 2.9.0.post0 | Free-text `Dual License`; `.dist-info/licenses/LICENSE`. Upstream states pre-December 2017 contributions are BSD-3-Clause only, while later contributions are available under Apache-2.0 or BSD-3-Clause. | Preserve the applicable notices and license. A single SPDX label would hide the contribution-date distinction. [Upstream licensing statement](https://github.com/dateutil/dateutil). |
| six | 1.17.0 | 1.17.0 | `MIT`; `.dist-info/LICENSE`. | Retain MIT notice. [Upstream license](https://github.com/benjaminp/six/blob/master/LICENSE). |
| tzdata | 2026.6 | Not listed in this lock | `Apache-2.0`; `LICENSE` and `licenses/LICENSE_APACHE` are present. | Preserve Apache-2.0 notice, license text and any applicable attribution. This resolver-selected package is not pinned by the CI baseline file. [Upstream license](https://github.com/python/tzdata/blob/master/LICENSE). |

The project's own installed metadata declares `License-Expression: Apache-2.0` and four `License-File` entries: `LICENSE`, `LICENSE-DOCS`, `NOTICE` and `THIRD_PARTY_LICENSES.md`. `LICENSE-DOCS` applies CC BY 4.0 to QF Solver documentation and original examples; it does not relicense third-party publications, meshes or solver outputs.

### Version comparison

The release package declares ranges (`numpy>=1.24`, `scipy>=1.10`, `matplotlib>=3.7`), not an end-user lock. The v6 Windows install resolved the versions shown above. The controlled standard CI lock is a separate test environment: its NumPy, SciPy and Matplotlib pins are older than the v6 resolver result, as are contourpy, fonttools, kiwisolver, packaging, Pillow, pyparsing and python-dateutil. Cycler and six match. `tzdata 2026.6` was resolved by the v6 installer but is absent from the CI lock. These version differences are not a license approval for every version allowed by the open-ended runtime ranges.

## Optional and engineering-only dependencies

These extras are declared in the v6 package metadata but were not installed by the two default wheel/sdist installation checks. Their constraints, upstream license references and scope are:

| Extra | Declared packages | Technical license notes and risk |
|---|---|---|
| `hdf5` | `h5py>=3.10` | h5py upstream declares BSD-3-Clause; the HDF5 library and any wheel-bundled native components have their own notices. Neither h5py nor HDF5 was in the v6 default install. [h5py metadata](https://github.com/h5py/h5py/blob/master/pyproject.toml). |
| `large`, `hpc` | `mpi4py>=3.1`, `petsc4py>=3.20`, `slepc4py>=3.20` | mpi4py identifies BSD-3-Clause. PETSc and SLEPc identify 2-clause BSD, but PETSc explicitly states that separately downloaded packages retain their own licenses. MPI implementations and native numerical libraries must be reviewed independently. [mpi4py](https://github.com/mpi4py/mpi4py), [PETSc](https://petsc.org/main/install/license/), [SLEPc](https://slepc.upv.es/release/documentation/manual/slepc-manual.pdf). |
| `mesh` | `gmsh==4.15.2` | Gmsh is GPL-2.0-or-later with a linking exception. It is an optional, separately installed dependency, not part of the v6 wheel or sdist. Review before bundling, rehosting, or distributing it with another product. [Official Gmsh terms](https://gmsh.info/). |
| `docs` | `gmsh==4.15.2`, `reportlab==4.4.9`, `svglib==2.0.2`, `pypdf==6.10.0`, `platformdirs==4.9.4`, `mkdocs>=1.6,<2`, `mkdocs-material>=9.5,<10` | Not installed by the v6 package checks. Gmsh is GPL-2.0-or-later with linking exception; svglib's upstream repository identifies LGPL-3.0; pypdf identifies BSD-3-Clause; ReportLab and MkDocs identify BSD-style licenses; platformdirs and Material for MkDocs identify MIT. Their exact extra-resolution graph and release-specific license payloads were not captured by v6, so inspect them before bundling. [svglib](https://github.com/deeplook/svglib), [pypdf](https://github.com/py-pdf/pypdf/blob/main/pyproject.toml), [ReportLab](https://docs.reportlab.com/developerfaqs/), [MkDocs](https://github.com/mkdocs/mkdocs/blob/master/docs/about/license.md), [platformdirs](https://github.com/tox-dev/platformdirs/blob/main/LICENSE), [Material for MkDocs](https://github.com/squidfunk/mkdocs-material/blob/opensource/LICENSE). |
| `test`, `dev`, `wp12-runner` | pytest and pytest-cov (MIT); tomli (MIT); coverage (Apache-2.0); psutil and threadpoolctl (BSD-3-Clause); h5py (BSD-3-Clause); jsonschema, PyYAML, Ruff and mypy (MIT); Hypothesis (MPL-2.0); cryptography (Apache-2.0 OR BSD) | These are development/test or runner extras, not the default solver runtime graph. The standard CI lock fixes versions, but the v6 install evidence does not include this optional graph. Keep each package's own notices if separately redistributed; review Hypothesis's MPL-covered files and cryptography's package notices if bundling these tools. [pytest](https://github.com/pytest-dev/pytest/blob/main/pyproject.toml), [pytest-cov](https://github.com/pytest-dev/pytest-cov), [coverage.py](https://github.com/coveragepy/coveragepy), [psutil](https://github.com/giampaolo/psutil), [jsonschema](https://github.com/python-jsonschema/jsonschema/blob/main/pyproject.toml), [PyYAML](https://github.com/yaml/pyyaml), [Ruff](https://github.com/astral-sh/ruff), [mypy](https://github.com/python/mypy/blob/master/LICENSE), [Hypothesis](https://github.com/HypothesisWorks/hypothesis/blob/master/LICENSE.txt), [cryptography](https://github.com/pyca/cryptography/blob/main/LICENSE). |

## Assessment of `THIRD_PARTY_LICENSES.md`

The file is included in the wheel and sdist and accurately presents itself as a starting inventory. It names the three direct runtime dependencies, identifies major optional integrations and documentation tools, distinguishes external outputs/material, and links to upstream sources. The installed dependency distributions carry their own license files; the QF Solver wheel does not bundle those dependency packages.

The file is not a versioned, exhaustive notice schedule: it does not enumerate the full resolved transitive graph, exact v6 versions, bundled native components, or the GPL/LGPL considerations for the optional Gmsh and svglib integrations. That is a documentation and legal-review limitation, not evidence that the v6 package embeds those optional packages. No edit to the distributed license inventory was made because that file is selected by the v6 contract; changing it would invalidate the existing artifact hashes and require a new contract and package build.

## Findings and release decision

- The default v6 dependency graph is technically documented and each of its 13 third-party distributions has a license file or recorded license text in the installed environment. NumPy, SciPy and Matplotlib carry additional bundled-component notices.
- No dependency package is embedded into the QF Solver wheel or sdist. No direct license conflict was established from the inspected default runtime graph.
- The optional `mesh` and `docs` extras include Gmsh under GPL-2.0-or-later with a linking exception; `docs` also includes svglib under LGPL-3.0. These remain separate optional installs and require counsel review before combined redistribution.
- The CI pinned versions and the v6 resolver versions differ as listed above. The open-ended runtime ranges can resolve versions outside this single v6 installation evidence.
- `LEGAL_REVIEW_NOT_ACQUIRED`: this is an engineering metadata and notice audit, not a legal opinion or redistribution authorization. The release license gate remains open until an independent reviewer accepts the exact candidate scope and its optional dependency policy.
