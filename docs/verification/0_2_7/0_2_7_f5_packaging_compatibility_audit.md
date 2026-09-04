# QF Solver 0.2.7a0 F5 packaging and compatibility audit

## Status

`F5_STATUS = PASS_WITH_LIMITATIONS`.

The audit started from `124c61f6492eee351a34e3542d198a13c00c2874` on the
`codex/0.2.7-foundation` branch. The candidate package identity is
`qf-solver` / `qf_solver` and version `0.2.7a0`, with `>=3.10` declared.
The package can be built, installed from a wheel or sdist in clean Windows
environments, and used from outside the repository. No tag, PyPI publication
or GitHub release was performed.

The machine-readable source of this audit is
`qualification/0_2_7/f5_packaging_compatibility_audit.json`.

## Finding fixed

The public `release-vv` entry point initially failed in a clean wheel because
`qualification/element_analysis_matrix.json` and
`qualification/technical_content_coverage.json` were tracked but absent from
both the sdist manifest and the wheel data files. This was a P1 packaging
defect. The two resources are now included by `MANIFEST.in` and
`setuptools.data-files`, and the clean installed command writes a controlled
qualification report rather than failing on a missing resource.

No source module under `src/` was changed. The core package remains importable
without `petsc4py`, `mpi4py` or `h5py`; those routes raise typed,
understandable infrastructure errors when their optional dependencies are
absent.

## Artifact and install matrix

| Artifact | Python | OS | Install/import/API/CLI | Resources |
| --- | --- | --- | --- | --- |
| wheel `qf_solver-0.2.7a0-py3-none-any.whl` | 3.13 | Windows | PASS | PASS |
| sdist `qf_solver-0.2.7a0.tar.gz` | 3.13 | Windows | PASS | PASS |
| wheel `qf_solver-0.2.7a0-py3-none-any.whl` | 3.12 | Windows | PASS | PASS |

All clean-install probes ran from a directory outside the repository with no
repository `PYTHONPATH`. The installed API loaded a TET4 example, checked its
mesh and produced finite solve output. The CLI passed `--help`, `--version`,
`check-mesh` and `solve`; invalid input returned a controlled non-zero result.
The legacy `solveur-ef` version command also passed with its deprecation
warning.

The wheel and sdist both passed `twine check` and the repository distribution
policy checker. The tested wheel was 1,344,679 bytes and the tested sdist was
996,957 bytes. Two isolated builds had identical member contents and
structure; whole archive hashes differed only in normal build/archive
metadata. No credentials, personal paths, `.env`, bytecode or unexpected
private dumps were found.

## Dependencies and compatibility

Core dependencies are NumPy, SciPy and Matplotlib. HDF5, MPI/PETSc/SLEPc,
Gmsh and documentation tools remain optional extras. The base import succeeds
when optional solver dependencies are absent, and unavailable optional routes
fail with typed infrastructure diagnostics rather than breaking package
import.

Python 3.12 and 3.13 were directly installed and smoke-tested locally.
Python 3.10 is declared and covered by the quality workflow but was not
available locally; Python 3.11 is declared but was not directly verified in
this run. Windows was directly tested. Linux is represented by the existing
3.10/3.13 CI matrix; no local Linux artifact environment was available.
macOS was not tested and is not in the current CI matrix, so no macOS claim is
made.

## Release-vv boundary

The installed `release-vv` command is technically present and resource-safe,
but its default bundled record is a legacy `0.2.1` release context. Without
the current checkout evidence corpus it returns a controlled qualification
report/status rather than a false 0.2.7 PASS. This is a bounded limitation,
not a package installation failure and not a 0.2.7 release qualification
claim.

## Controls and conclusion

- Numerical source: unchanged.
- Historical evidence: unchanged.
- Maturity: unchanged.
- Heavy benchmark and full regression: not run in F5.
- Tag, push, GitHub release and PyPI publication: not performed.

`WHEEL_READY = YES`, `SDIST_READY = YES`, `CLEAN_INSTALL_READY = YES` and
`PYPI_ARTIFACT_READY = YES` mean technical candidate artifacts only; they do
not authorize publication. F5 is ready for F6 with the compatibility limits
above explicitly retained.
