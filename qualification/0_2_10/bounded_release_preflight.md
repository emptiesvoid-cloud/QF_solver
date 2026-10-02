# QF Solver 0.2.10 bounded release preflight

This is a source-and-package preflight, not an assertion that PyPI or Zenodo has been published.

- Frozen source commit: `d6ab4d58797b0a12632fa7bc2b394ade16eed32f`.
- Prospective contract commit: `ff26b312139a2ed4ef0bfc42548757f9714c55f8`.
- Contract: `qualification/0_2_10/public_package_release_contract.json` (SHA-256 `d721cf1da3c653d4c92115981bb5651104501b7994c901da0741244b8cc00020`).
- Local execution: Windows, Python 3.13.1, 2026-10-02 19:25–19:26 UTC. Full machine-readable reports remain outside the checkout; this summary does not replace CI artifacts.

| Check | Local result |
| --- | --- |
| Frozen selected package source scan | `PASS_BOUNDED_PUBLIC_SURFACES`: 551 files, zero findings |
| Frozen selected documentation scan | `PASS_BOUNDED_PUBLIC_SURFACES`: 746 files, zero findings |
| Rebuilt wheel and sdist content | `PASS_CANDIDATE_PACKAGE_ONLY`: 551 and 559 scanned files, respectively, zero findings |
| Installed-package probes outside the checkout | PASS; package and CLI report `0.2.10` |
| `twine check` and distribution boundary check | PASS for both rebuilt artifacts |
| Publication metadata preflight for `v0.2.10` | PASS locally |
| Strict MkDocs build | PASS locally |
| Targeted metadata/documentation tests | 56 passed, 2 skipped |

Rebuilt local artifacts, not yet uploaded or designated as published bytes:

| File | SHA-256 |
| --- | --- |
| `qf_solver-0.2.10-py3-none-any.whl` | `7badec45bea8553e879e300d5d2cd1e5f9e5c0ac51f2c1967ac94da689e543ba` |
| `qf_solver-0.2.10.tar.gz` | `1fef22f049fce12a5e9c285a95c50048d25c9703831558b0021660363cbfa394` |

The full-repository G03 archive scan remains failed. This bounded preflight does not clear it, change the ledger, or promote WP14. The Zenodo DOI `10.5281/zenodo.23106744` is reserved but not registered or citable until the version record is published. Publication still requires successful CI on this branch and tag, an exact tag-bound package build, and a deliberately scoped Zenodo deposit. No tag or upload was performed by this preflight.
