# First local V&V campaign — execution plan

**Status:** `PREPARATION_ONLY`<br>
**Execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`

This is a plan for a future WP12-R mission. It does not authorize a test. Each case requires a separate explicit Owner decision binding the final manifest hash and case.

## 1. Verified candidate and environment

The science checkout was observed clean at commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.

The named interpreter exists at `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`; its observed version is Python 3.13.17. The environment has NumPy 2.2.6, SciPy 1.15.2, pytest 8.4.1 and threadpoolctl 3.6.0. The `qf-solver` distribution is not installed in that venv. A separate no-solve diagnostic import with `PYTHONPATH=E:\QFSolverWP12B\science\src` resolved `solveur.__file__` to the frozen science checkout. Its module version metadata says `0.2.11`; the Git integration candidate is tracked on the v0.2.12 branch. Record both facts; do not relabel the package metadata.

The local runner's future `VALIDATE` command rechecks the interpreter, packages, Git identities, listed file hashes/blob OIDs, `solveur.__file__`, NumPy/SciPy versions and observed native thread pools. The source import probe is a distinct diagnostic subprocess and does not assemble matrices or call an analysis solver. No environment installation or package update is performed in WP12-Q.

## 2. Exact selection and command construction

For each case, the runner constructs this fixed argument structure; only the exact manifest nodeid and the unique run-directory JUnit path vary:

```text
<venv-python> -m pytest -q --noconftest
  -p no:cacheprovider
  -p local_vv_pytest_plugin
  -c <tests-checkout>/pyproject.toml
  -o pythonpath= -o addopts=
  --junitxml=<new-run-directory>/junit.xml
  <one-exact-nodeid>
```

The invocation uses the manifest-bound **tests checkout** as `cwd` and for `pyproject.toml`; it sets `PYTHONPATH` to the frozen science checkout's `src` and the manifest-bound runner's `scripts` directory. It disables user-site packages, bytecode writes, plugin autoload and conftest loading, and applies the thread variables below. There is no shell parsing and no caller-provided command or nodeid. The in-process plugin records the actual collected nodeid list and loaded `solveur.__file__`; the runner checks these records together with the JUnit testcase.

For reproducible manual preflight in a future authorized mission, resolve the repository root once and inspect only:

```powershell
$RepoRoot = (git rev-parse --show-toplevel).Trim()
$Manifest = Join-Path $RepoRoot 'qualification/0_2_12/vv_local/FIRST_CAMPAIGN_MANIFEST.json'
& 'E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe' `
  'E:\QFSolverWP12B\runner-local-vv\scripts\run_local_vv.py' `
  validate --manifest $Manifest
```

`VALIDATE` creates no evidence directory and does not run pytest. A future `run` call must include an Owner-approved decision file outside the checkouts and an exact case ID. No such decision file is prepared in WP12-Q.

## 3. Case order and operational budgets

One case per process; one attempt maximum; no automatic retry. The values below are proposed operational ceilings only. They are not scientific tolerances and remain subject to Owner confirmation in the per-case decision.

| Order / ID | Exact nodeid | Proposed wall timeout | Per-stream log cap | Extra notes |
|---|---|---:|---:|---|
| Q1 `ALG-PROJ-001` | `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form` | 120 s | 16 MiB | Algebraic-only, no FEM solve |
| Q2 `MODAL-DISCRETE-001` | `tests/unit/test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form` | 120 s | 16 MiB | Small discrete modal solve |
| Q3 `MODAL-2DOF-001` | `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | 120 s | 16 MiB | Existing same-backend oracle; separate scalar oracle is recorded as supplemental and excluded |
| Q4 `DYN-SDOF-001` | `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection` | 180 s | 16 MiB | One-element BEAM2 transient |

The manifest fixes `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `BLIS_NUM_THREADS=1`, and `VECLIB_MAXIMUM_THREADS=1`; the runner also sets `PYTHONHASHSEED=0`. The runner records observed native pools. A log cap is polled from the output files and is not a hard storage quota. No hard CPU or RAM budget is available in this local design; those fields are explicitly `NOT_ENFORCED`.

The proposed output root is `E:\QFSolverWP12B\wp12-local-vv-evidence`; no directory at that path is created now. Each future attempt is stored under `<root>/<campaign-id>/<case-id>/<unique-run-id>/`. Existing attempt reservation or run directory means stop; do not delete or reuse it. Results are saved outside source and historical evidence trees.

## 4. Stop and retention sequence

Before a case: check the final manifest and detached hash; confirm the Owner decision's exact manifest hash, case, attempt, nodeid, identities, interpreter, budgets, oracle, output root and validity period; run `VALIDATE`; inspect that no file changed after validation; confirm that output and attempt paths do not exist.

During a case: supervise the direct Python child; retain stdout/stderr; stop on timeout or observed output cap. The current local runner does not guarantee termination of all descendants.

After a case: require a single exact collection entry, matching in-process import origin, one matching JUnit testcase and unchanged source/test hashes. Preserve all evidence, including partial output. Classify assertion failure as `FAIL`; missing/contradictory selection or JUnit, import mismatch or checkout mutation as `INFRA_ERROR`; skip as `INCONCLUSIVE`; timeout and output cap separately. A passing process result remains `PYTEST_PASS_ONLY` until an oracle-specific review is recorded.

Copy the complete result directory and receipt to an Owner-controlled archive and check the copied hashes. Local hashes do not prevent later modification by the same Windows account.

## 5. Future cases beyond the first four

### STAT-BEAM-001

The BEAM2 Timoshenko cantilever test is parameterized in the source as `("dof", "inertia", "rotation_dof", "rotation_sign")`. With pytest 8.4.1's default primitive-value ID generation, the exact parameter IDs are:

- `tests/unit/test_beam2_element.py::test_beam2_cantilever_matches_timoshenko_tip_solution[UY-3e-06-RZ-1.0]`
- `tests/unit/test_beam2_element.py::test_beam2_cantilever_matches_timoshenko_tip_solution[UZ-2e-06-RY--1.0]`

These IDs are derived from the source values and the installed pytest ID rule; no collection or test was run. Each uses a one-element, 2 m cantilever, E=210 GPa, nu=0.3, A=0.01 m², Iy=2e-6 m⁴, Iz=3e-6 m⁴, and a 1000 N tip force. The Timoshenko formula and existing `rel=1e-12` assertions are in the test. The Owner must choose the bending plane and approve the exact parameterized nodeid.

### FEM-TET4-H-001

Candidate entry point: `solveur.verification.tet4_structured_convergence.run_structured_tet4_study`, with `StructuredTet4ConvergencePlan`; implementation is in `src/solveur/verification/tet4_structured_convergence.py`. The utility defaults to a much larger `(20,4,4)` base and factors `(1,2,4,8)`, so that default must not be used for a small local campaign without review.

One bounded planning candidate is a nested base grid `(2,1,1)` with factors `(1,2,4)`, six-tetrahedron cell split, dimensions `(length,width,height)=(4.0,0.4,0.4)`, `E=70e9`, `nu=0.3`, total global-Z load `-1.0`, `load_distribution="tributary"`, and the matrix-free backend. From the generator source, the left face `x=0` is fixed in all three translational components; the resultant load is distributed over the right face `x=length` in global Z. The implemented observable is mean tip-face `UZ`; the reference is the utility's Euler-Bernoulli plus Timoshenko diagnostic. Factors 1/2/4 imply 24/192/1536 tetrahedra and 36/135/675 DOFs. These are proposed model settings, not Owner-approved criteria or results. The existing summary reports tip displacement, reference/error, relative residual, iteration count, solve time, operator-memory estimate and solver configuration. It does not report support reactions or strain energy; add a separately reviewed extraction method if those are required.

The utility defaults include `relative_limit=0.01` and `residual_limit=1e-8`; they are implementation defaults and are not accepted criteria until the Owner reviews them. The utility writes a model file and summary/report under each level directory and the campaign output root; the output root must be new and exclusive. A metric-logic unit test is not evidence that this multi-mesh study ran. Preserve raw per-level data and report error relative to an independently justified reference separately from mesh-to-mesh change. The runner's current command profile accepts exact pytest nodeids only, so this function is not yet an executable campaign entry point under that runner; a reviewed fixed benchmark wrapper and separate approval are required.
