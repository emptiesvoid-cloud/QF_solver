# Contributing to QF Solver

Thanks for considering a contribution to QF Solver.

QF Solver is an open-source finite-element solver focused on structural mechanics,
transparent numerical formulations, reproducible verification, and explicit
capability boundaries.

QF Solver has its roots in a personal FEM solver project I started back in 2024. It has changed a lot since then and eventually evolved into the current QF Solver project. I still haven't had the time to put everything on GitHub, because I'm kind of mixing new upgrades with older parts of the original project as I go.

Contributions are welcome, including bug fixes, documentation improvements,
new examples, tests, numerical methods, solver improvements, and verification
cases.

Because QF Solver is numerical engineering software, changes that affect results
need a little more care than ordinary application code.

## Ways to contribute

Useful contributions include:

- fixing reproducible bugs
- improving documentation
- adding examples or tutorials
- improving test coverage
- improving error messages and input validation
- adding or improving finite-element formulations
- improving solver backends
- improving performance
- adding verification and validation cases
- improving reproducibility and qualification evidence

Small contributions are welcome too. A documentation correction or a clearer
example can be just as useful as a new solver feature.

## Before writing code

For anything that changes numerical behavior or introduces a substantial new
feature, please open a GitHub issue first.

Describe:

- the problem or requested capability
- the mechanical or numerical scope
- the expected behavior
- any assumptions
- how the change could be tested or verified

For small documentation fixes, typos, or clearly bounded corrections, opening
an issue first is not required.

Use GitHub issues for reproducible defects and feature proposals.

For mechanical comparisons, benchmarks, or verification questions, use the
appropriate V&V issue template when possible.

## Development setup

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
cd QF_solver
python -m pip install -e ".[test,dev]"
```

Check that the public CLI is available:

```bash
qf-solver --version
```

A basic Python API check is:

```python
from qf_solver import check_mesh, load_model, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
```

## Keep changes focused

Please keep pull requests reasonably focused.

A PR should preferably address one problem or one coherent feature.

Avoid mixing unrelated:

- numerical changes
- formatting changes
- large refactors
- documentation rewrites
- dependency updates

Focused changes are easier to review and easier to verify.

## Coding rules

QF Solver currently targets Python 3.10 and newer.

General rules:

- keep public behavior explicit
- preserve the `elements -> core -> api/cli` dependency direction
- use the project error taxonomy at public boundaries
- avoid hidden numerical fallbacks
- prefer deterministic behavior where practical
- document important assumptions
- keep source files reasonably sized
- do not silently change a numerical baseline

The supported public Python namespace is:

```python
qf_solver
```

Internal implementation details under `solveur` are not automatically part of
the stable public API.

## Numerical changes

Changes affecting finite-element formulations, materials, solvers, convergence
behavior, contact, dynamics, or post-processing should include appropriate
numerical evidence.

Depending on the change, this may include:

- analytical comparisons
- convergence studies
- regression tests
- equilibrium checks
- residual checks
- energy checks
- comparison with an existing reference
- deterministic replay
- resource or performance measurements

A passing example does not automatically qualify a complete element, material,
analysis, or solver family.

Do not label a capability as `QUALIFIED`, `QUALIFIED_BOUNDED`, or equivalent
without the corresponding recorded evidence and review.

Experimental behavior should remain clearly identified as experimental.

## Tests

Run targeted tests while developing.

For example:

```bash
python -m pytest tests/unit/test_solver.py -q
```

For a broader change:

```bash
python -m pytest tests/unit tests/integration -q
```

Static checks can be run with:

```bash
python -m ruff check src tests scripts
```

The progressively typed core can be checked with:

```bash
python -m mypy \
  src/solveur/core/errors.py \
  src/solveur/core/qualification.py \
  src/solveur/io/manifest.py \
  src/solveur/verification/traceability.py
```

Compile checks:

```bash
python -m compileall -q src scripts tests
```

The complete CI also runs automated tests, coverage checks, verification routes,
and documentation evidence on GitHub Actions.

The main regression suite targets a minimum branch coverage of 80% for the
configured package scope.

Do not run expensive unrelated campaigns after every small edit.

The full engineering baseline is expected before:

- releases
- tags
- dependency changes
- cross-cutting refactors
- major formulation changes
- controlled verification evidence updates

## Examples

Maintained examples are available in:

```text
examples/
```

The example catalogue includes static, modal, transient, harmonic, buckling,
nonlinear, and selected contact cases.

When adding an example:

- keep it reasonably small
- explain what it demonstrates
- make it reproducible
- add a test when appropriate
- do not present an example as general validation

## Documentation

Documentation changes are welcome.

Please:

- keep technical claims consistent with the current capability matrix
- preserve explicit limitations
- link important claims to reproducible evidence when possible
- follow the style and language of the document being edited
- avoid claiming certification or universal validation

Public documentation is built from the `docs/` directory.

Documentation site:

https://emptiesvoid-cloud.github.io/QF_solver/

## Pull requests

Before opening a pull request:

1. make sure the change is focused
2. run the relevant local tests
3. update documentation when public behavior changes
4. add or update tests for bug fixes and new behavior
5. explain any numerical baseline change
6. check that no private, confidential, or workstation-specific information is included

A useful PR description should explain:

- what changed
- why it changed
- how it was tested
- whether numerical results changed
- any remaining limitations

For numerical work, include the relevant residuals, errors, comparisons, or
verification evidence when available.

## Continuous integration

Pull requests are checked automatically with GitHub Actions.

The current CI includes:

- Python 3.10 and 3.13
- Ubuntu and Windows
- Ruff
- progressive mypy checks
- unit and integration tests
- branch coverage
- source compilation
- quick solver verification
- engineering verification campaigns
- documentation evidence checks

A green CI result is expected for normal contributions unless a maintainer
explicitly documents why a failing or unavailable check is acceptable.

## Review

Pull requests may require changes before they are merged.

Review may focus on:

- correctness
- numerical assumptions
- test coverage
- API compatibility
- documentation
- reproducibility
- performance impact
- capability claims

Feedback is intended to improve the contribution, not discourage it.

## Credit

Contributors remain visible through the Git history and pull-request history.

Substantial technical, documentation, verification, testing, or example
contributions may also be acknowledged in release notes or project
documentation when appropriate.

Please do not include third-party code or data unless its license is compatible
and its origin is clearly documented.

## Security

Do not report suspected security vulnerabilities publicly.

Follow:

```text
SECURITY.md
```

for the current reporting process.

Do not upload confidential industrial models, credentials, private datasets,
or restricted engineering data.

## Support

For usage questions, reproducible defects, or feature proposals, see:

```text
SUPPORT.md
```

QF Solver is provided on a best-effort basis and is not certified engineering
software.

Engineering results still require appropriate model review and
application-specific validation.
