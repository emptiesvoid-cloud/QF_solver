# 026-WP04-ARCH Architecture Refactor Evidence

## Decision

`026-WP04-ARCH = PASS`

This evidence covers the authorized internal reorganization of the numerical
core. It does not introduce an FEM feature, change a formulation, or promote a
verification maturity claim. The foundation gate `026-G04` is left unchanged:
it officially names the later linear/element robustness batch, not this
architecture work package.

## Provenance

| Item | SHA / state |
| --- | --- |
| Baseline | `41154d7f0aca9004759d1c8a4ba21d6f60f24a42` |
| Implementation and regression-fix source | `6b77fd7b318dab0fea4a371c3567dea3cdc19b47` |
| Evidence context | `af2aa75895e6edf0db698384a3fabdde7fcd0640` |
| Worktree at evidence capture | `clean` |

## Architecture result

The implementation ownership is now explicit:

| Domain | Package |
| --- | --- |
| Global, geometric and nonlinear assembly | `solveur.core.assembly` |
| Linear solvers, policies and optional backends | `solveur.core.solvers` |
| Modal, dynamic, harmonic and buckling analyses | `solveur.core.analyses` |
| Nonlinear state, contracts and solution strategies | `solveur.core.nonlinear` |

Thirty legacy flat modules remain compatibility facades. They resolve to the
new module objects, preserving 0.2.x imports and monkeypatch paths while new
production imports use the hierarchical packages. The verification package was
not migrated in this task; that remains a separate, higher-risk activity.

## Verification results

- Foundation smoke: `9 PASS`, `1 EXPECTED_FAILURE`, `0 FAIL`, `0 BLOCKED`.
- Full regression: `1663 passed`, `0 failed`, `14 skipped`, `187 deselected`.
- Framework coverage: `80 %` branch-aware targeted coverage.
- Focused post-fix checks: `39 passed`, `2 skipped`.
- Representative numerical route comparison: `8` routes, `0` mismatches.
- Normalized comparison of all moved implementation bodies: `0` mismatches.
- Ruff, `compileall`, `git diff --check`, public API/CLI smoke and architecture
  audit: PASS.

The full regression was run without coverage instrumentation. Coverage was
checked separately on the V&V framework, as required by the foundation gate;
the refactor does not claim a new whole-project coverage level.

## Boundary and next step

`G04` is ready for Owner review. `G05` was not started, and no push, merge,
tag, release or publication was performed.
