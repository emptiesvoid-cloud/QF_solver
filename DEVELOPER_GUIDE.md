# Developer Guide

## Purpose

QF_solver is a white-box Python finite-element solver intended to remain
testable, traceable and maintainable. Changes should be conservative,
mechanically justified and accompanied by proportionate tests.

## Modification Rules

- Do not change public CLI or API contracts without compatibility tests.
- Keep Python source files below 700 lines.
- Keep `solveur/elements` independent from `solveur/io`, `solveur/cli` and
  `solveur/api`; keep `solveur/core` independent from `solveur/cli` and
  `solveur/api`.
- Centralize evidence hashes and manifests in `solveur/io/manifest.py`.
- Avoid dense conversions on the large-model path.
- Use the public error taxonomy at API and CLI boundaries.
- Update requirements, anomaly records and the changelog when a controlled
  scope is affected.
- Do not claim certification or increase maturity without recorded evidence
  and an appropriate Owner review.

## Proportionate Quality Checks

Do not run the complete suite after every local edit. Run the narrowest tests
that cover the modified module and its immediate contracts, then record the
scope. Add integration tests when an API, CLI, schema, export or documentation
boundary changes. Run the relevant mechanical V&V campaign when a formulation,
element, material or numerical algorithm changes.

Run the complete baseline only before a release or tag, a controlled evidence
or site regeneration, a dependency update, a cross-cutting refactor, or when
the impact cannot be bounded confidently. CI remains the independent full
regression gate for pushed changes.

Examples of a focused local check:

```powershell
python -m ruff check solveur\core\solver.py tests\unit\test_solver.py
python -m pytest tests\unit\test_solver.py tests\unit\test_linear_policy.py -q
python -m compileall -q solveur\core\solver.py
```

The detailed tiered procedure and full baseline commands are in
`docs/controle_qualite.md`.

## Publication Hygiene

Run `python .\scripts\audit_public_release.py` before making a source archive
or enabling public hosting. The report must be free of local paths, private
environment references and internal workflow terminology.
