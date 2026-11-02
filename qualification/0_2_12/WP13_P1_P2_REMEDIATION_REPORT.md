# QF Solver 0.2.12 P1/P2 Remediation Report

## Scope and baseline

- Audited base commit: `d31614f59341d175d8e2daade92daf7d8149d199`
- Corrective branch: `codex/qfsolver-0.2.12-p1-p2-remediation-20261102`
- Intended pull request base: `emptiesvoids-cloud/0.2.12`
- Scope: the demonstrated P1 unsupported-spring routing defect. P2 findings remain unaudited because their required source register was unavailable.

## P1 correction

The `geometric_nonlinear_static` and `linear_buckling` route validators now reject models containing discrete springs with `InputValidationError`. The guard runs before mesh validation or assembly. This prevents unsupported springs from being silently omitted. Models without springs retain their existing scope behavior. No spring support, numerical algorithm, oracle, or tolerance was added or changed.

Regression coverage in `tests/unit/test_p1_route_spring_rejections.py` verifies that each public route raises before mesh validation or assembly and that spring-free models still pass both existing scope validators.

## P2 findings and missing audit inputs

The directive identifies `QF_0212_FINDINGS_REGISTER.json` and an audit roadmap as the authoritative sources for four demonstrated P2 code defects. Neither file was present in the audited checkout, local Git history, or the repository's GitHub code-search results. The available `qualification/0_2_12/ROADMAP.md` is a general integration roadmap and does not identify the four audit findings.

No P2 defect was inferred or changed without its evidence. The four P2 items therefore remain unclassified and unaddressed pending the exact register and audit roadmap.

## Validation performed

Environment: Python 3.13.1, pytest 8.4.1.

| Check | Result |
| --- | --- |
| `test_geometric_nonlinear_rejects_springs_before_validation_or_assembly` | PASS, 1 test |
| `test_linear_buckling_rejects_springs_before_validation_or_assembly` | PASS, 1 test |
| `test_spring_free_models_remain_inside_both_existing_scopes` | PASS, 1 test |
| Ruff on both modified modules and the new regression test | PASS |
| `py_compile` on both modified modules and the new regression test | PASS |
| `git diff --check` | PASS |

No complete suite, scientific FEM campaign, WP13 installed-package smoke, or CI matrix was run. No scientific result or historical ledger was changed.

## WP13 v7 artifact impact

The v7 wheel and normalized sdist remain historical artifacts with their previously verified identities; this branch does not rebuild or alter them. The two modified solver modules are part of the distributed source, so a package built from this remediation branch would have different contents and cannot inherit the v7 artifact hashes or claim that the v7 installed-package smokes exercised these new guards. The six existing v7 smoke results remain valid only for the exact v7 packages and their original scope. No new scientific execution is authorized or claimed here.

## Open items and verdict

- P1 unsupported-spring routing defect: corrected and covered by targeted non-FEM route tests.
- Four P2 audit findings: open; exact register and audit roadmap required to identify and address them.
- New package identity and any package-level verification for the corrected source: not acquired.

**Verdict: `REMEDIATION_BLOCKED`** — the P1 correction is ready for review, but the requested P2 remediation cannot be completed from the available audit evidence.
