# QF Solver 0.2.10 bounded candidate audit (not a release)

- Frozen source: `aa45694f02bcc7607f5aef4b770ddb07269e42fe`.
- Prospective contract commit: `e052dd8a9310d95b57a875fa9d12f79d74d12ffe`.
- Contract: `qualification/0_2_10/public_package_candidate_contract.json` (SHA-256 `6eb627ed2e0030add5e355b4f15be83dba9352892521bd6d28e3de9651b8216c`).
- Execution: Windows, Python 3.13.1, 2026-10-02 16:48–16:49 UTC. The full audit and build reports remain local, outside the checkout; this summary is not a replacement for their manifests and logs.

| Check | Result |
| --- | --- |
| Frozen selected package source scan | PASS, 551 files, zero findings |
| Frozen served-documentation scan | PASS, 745 files, zero findings |
| Rebuilt wheel and sdist, content checks | `PASS_CANDIDATE_PACKAGE_ONLY`; wheel 551 and sdist 559 scanned files, zero findings |
| Installed-package probes outside checkout | PASS; CLI reports `0.2.10` |
| `twine check` and distribution inspection | PASS for both rebuilt artifacts |
| Strict MkDocs build | PASS locally |
| Targeted metadata/documentation tests | 41 passed, 2 skipped |
| Publication metadata preflight for `v0.2.10` | FAIL as intended: `CITATION.cff` and public release copy still identify the last published release, 0.2.8 |

Rebuilt local artifacts (not uploaded or designated final release bytes):

| File | SHA-256 |
| --- | --- |
| `qf_solver-0.2.10-py3-none-any.whl` | `c84ed84413742b1d0abf5dee6d91db520272873ffb59cf3a64319c84b097ca1a` |
| `qf_solver-0.2.10.tar.gz` | `5ded75ae5a46f9d3c78ac7d8ef1eb007c1e438026caedda757e363e1140e1a37` |

The Zenodo v0.2.10 draft reserves `10.5281/zenodo.23106744` but has no files and is unpublished. The DOI is not registered or citable yet. The full-repository G03 archive scan remains failed; this bounded result does not clear that archive. The current candidate is **not publication-ready**: final citation/release metadata, tag-bound engineering CI, an exact final-source contract and a separate publication decision remain required. No tag, Zenodo deposit, GitHub Release, PyPI upload, ledger change or WP14 promotion occurred in this audit.
