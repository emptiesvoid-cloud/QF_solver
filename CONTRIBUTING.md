# Contributing to QF_solver

## Before Writing Code

Open an issue describing the mechanical scope, numerical assumptions and
expected evidence. A new element, material, solver or exporter needs unit
tests, an integration test where relevant, and documentation in French. Keep
the public API in `solveur.api`; internal modules are not compatibility
contracts.

## Development Rules

- Keep Python source files below 700 lines.
- Preserve the `elements -> core -> api/cli` dependency direction.
- Add explicit validation and use the project error taxonomy at public edges.
- Do not change a numerical baseline without recording the reason, tolerance
  and verification evidence.
- Do not mark a capability as certified or qualified without a recorded human
  decision.

## Proportionate Local Checks

Use targeted tests by default: test the modified code, its immediate
dependencies and the changed public boundary. Do not run long unrelated
campaigns after every local edit. A formulation change requires the associated
V&V family; an API, CLI, export or documentation change requires the relevant
integration checks.

The complete baseline is required before a release, tag, dependency update,
cross-cutting refactor, controlled evidence/site regeneration, or when impact
cannot be confidently bounded. CI runs the full regression suite for pushed
changes.

Example for a bounded solver change:

```powershell
python -m ruff check solveur\core\solver.py tests\unit\test_solver.py
python -m pytest tests\unit\test_solver.py tests\unit\test_linear_policy.py -q
python -m compileall -q solveur\core\solver.py
```

See `docs/controle_qualite.md` for the required tiered procedure and the full
baseline. Include generated evidence only when it is controlled, traceable and
suitable for version control.
