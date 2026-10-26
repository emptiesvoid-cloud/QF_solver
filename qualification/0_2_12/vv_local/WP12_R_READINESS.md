# WP12-R readiness — local first-campaign preparation

**Disposition:** `WP12_Q_READY_WITH_OWNER_DECISIONS`<br>
**Document status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`<br>
**Manifest:** [`FIRST_CAMPAIGN_MANIFEST.json`](FIRST_CAMPAIGN_MANIFEST.json), SHA-256 `ea8f32e24d9eaded198230b0bc5f8aab45ed76293c3e73bdf77533e0bf08a0db`; detached digest is in [`FIRST_CAMPAIGN_MANIFEST.sha256`](FIRST_CAMPAIGN_MANIFEST.sha256).

## Prepared identities

| Role | Commit | Tree | Observation |
|---|---|---|---|
| Scientific source | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` | Frozen WP12-0 candidate; clean checkout |
| Local runner | `9b1465d79cb19985c823c1329af2540de665a556` | `8b85486840de30f7e8ccd5cec1b5bc744c7fbcb0` | Separate local runner checkout; clean |
| Tests | `69a8642a15879666f59ad545dc83ac5852290b65` | `99c08ec34d2f5a78bb244d27724ac189519accb8` | Separate tests checkout; clean |

The scientific source checkout reports `solveur.__version__ == "0.2.11"` although the frozen integration candidate is tracked on the v0.2.12 branch. The local environment has no installed `qf-solver` distribution; imports resolve to the frozen checkout's `src/solveur/__init__.py`. Both facts are recorded without relabeling the source metadata.

## Local validation and environment observation

The local runner's `VALIDATE` command returned `VALIDATED_NOT_AUTHORIZED` for four cases. It checked all three clean Git identities, the four executable cases' listed SHA-256/Git blob inventories, the interpreter, installed package versions and science import origin. It reported declared/observed thread variables and native thread-pool metadata for review; it does not enforce a match against a manifest-pinned native-library inventory. It created no evidence directory and launched no pytest process or analysis solver.

- Python: `E:\QFSolverWP12B\venv-3.13.17\Scripts\python.exe`, version `3.13.17`.
- Packages: pytest `8.4.1`, NumPy `2.2.6`, SciPy `1.15.2`, threadpoolctl `3.6.0`; no installed `qf-solver` distribution.
- Platform observed: `Windows-10-10.0.19045-SP0`, `AMD64`.
- Native library observed by threadpoolctl: OpenBLAS `0.3.29`, pthreads, one thread, Haswell architecture. The manifest records the native DLL's relative package path and SHA-256.
- Thread variables to be applied to each later child: OpenBLAS, OMP, MKL, NumExpr, VECLIB and BLIS thread counts set to `1`; the runner also sets `PYTHONHASHSEED=0`.
- The interpreter and packages were inspected, not installed or changed. The output root `E:\QFSolverWP12B\wp12-local-vv-evidence` does not form part of the source trees and was not created by `VALIDATE`.

This local route is non-attested. It has no filesystem sandbox, hard CPU/RAM/disk quota or guaranteed descendant termination. The log-size cap is polled and is not a kernel-enforced limit. A future decision must explicitly accept these limits for its case or require another environment.

## Case readiness

| ID | Exact node | Oracle character | Preparation state |
|---|---|---|---|
| `ALG-PROJ-001` | `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form` | Dense bilinear identity; no FEM | Exact inline payload, test/source/contract hashes and historical assertions frozen; not authorized |
| `MODAL-DISCRETE-001` | `tests/unit/test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form` | Closed-form discrete spring/mass frequency and residual | Exact inline payload and hashes frozen; test has no explicit unit-system declaration; not authorized |
| `MODAL-2DOF-001` | `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | Same-SciPy-backend consistency | Exact matrices and hashes frozen; not an independent oracle; not authorized |
| `DYN-SDOF-001` | `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection` | Analytic free response conditional on prepared FE K/M | Exact model and hashes frozen; not a temporal or spatial convergence study; not authorized |

The canonical inline-payload profile is `qf-inline-fixture-json-v1`; each case stores its canonical SHA-256 and byte length alongside the source test file identity. Q3's independent characteristic-polynomial node is recorded separately in the manifest's supplemental review section and is not selectable as one of these four cases. It has not been executed.

Static comparison confirmed that the Git blob OIDs for the four executable test files are identical between the frozen science commit and tests commit above. The working copies use CRLF while repository blobs use LF; the manifest records both the Git blob OID and the exact SHA-256 of the Windows working-copy bytes. The supplemental Q3 test file is unique to the tests checkout, is recorded there, and is not checked by the current runner's case-only `VALIDATE` loop.

The tests assert values but do not emit a publication dataset. Unless a separately reviewed extraction path is approved, the runner must record numerical observables as `NOT_EXPOSED`; no values or plots may be inferred from a Boolean assertion result.

## Follow-on FEM preparation

### `STAT-BEAM-001`

The source parameterization yields two candidate exact IDs under the recorded pytest `8.4.1` primitive-value ID convention:

- `tests/unit/test_beam2_element.py::test_beam2_cantilever_matches_timoshenko_tip_solution[UY-3e-06-RZ-1.0]`
- `tests/unit/test_beam2_element.py::test_beam2_cantilever_matches_timoshenko_tip_solution[UZ-2e-06-RY--1.0]`

These were derived by source inspection, not pytest collection. The Owner must select the bending plane and later bind its exact parameterized node ID. The one-element BEAM2 model uses a 2 m cantilever, `E=210 GPa`, `nu=0.3`, `A=0.01 m^2`, `Iy=2e-6 m^4`, `Iz=3e-6 m^4`, and 1000 N. The existing test uses Timoshenko tip displacement/rotation expressions and `rel=1e-12`; those assertions remain unchanged.

### `FEM-TET4-H-001`

The static source supports a small nested candidate with base cells `(2,1,1)`, factors `(1,2,4)`, `decomposition="six"`, and `load_distribution="tributary"`. It creates a TET4 cantilever block with length 4.0, height 0.4, depth 0.4, `E=70e9`, `nu=0.3`, and total global-Z load `-1.0`. The generator fixes all three translational DOFs on the `x=0` face and distributes the resultant over the `x=length` face. The selected output is mean tip-face `UZ`; the reference is the utility's Euler-Bernoulli plus Timoshenko diagnostic. The levels imply 24/192/1536 tetrahedra and 36/135/675 DOFs.

The existing function reports tip displacement, reference/error, relative residual, iterations, solve time, operator-memory estimate and solver configuration. It does not report support reactions or strain energy. Its default `relative_limit=0.01` and `residual_limit=1e-8` are implementation defaults, not approved scientific criteria. A later plan must decide whether those criteria are retained, and whether additional observables require a reviewed extraction change. The current local runner only accepts exact pytest nodeids; it cannot yet run this function as a fixed benchmark entry point. The campaign is therefore prepared for review, not launch.

## Required Owner decisions before any scientific execution

1. Review and explicitly approve the exact manifest SHA-256 above, the selected case, its oracle and existing assertions, one attempt, proposed timeout/log limits, evidence destination, interpreter and three Git identities.
2. Confirm the non-attested same-user execution model is acceptable for the selected small case, including the absence of hard resource and filesystem isolation.
3. Confirm the source metadata version `0.2.11` is acceptable as recorded for this `0.2.12` candidate, and that the discrete spring/mass test's internally consistent but untagged units are acceptable.
4. If Q3's independent eigenvalue oracle is desired, approve it as a separate case and create a new manifest revision; the current four-case manifest excludes it from execution.
5. Approve a fixed benchmark wrapper and final criteria before any TET4 convergence run. No such wrapper or TET4 execution authorization exists here.
6. Choose the STAT-BEAM bending plane before preparing its separate exact-case manifest.

The structured decision schema is not an authenticated signature. This policy requires explicit Owner review outside the runner; the runner can check record fields and bindings but cannot prove who authored the record. No decision file exists. There has been no case-specific approval, numerical result, qualification decision, maturity promotion or WP12 closure.

## Synthetic infrastructure evidence

The dedicated runner suite previously completed **19 synthetic tests passed**; Ruff checks for the runner, pytest plugin, fake child and synthetic tests passed. These tests use fake processes and temporary data only. They are evidence about the local runner's control flow, not about QF Solver mechanics. No scientific node, FEM solve, benchmark or runner `run` command has been executed for this preparation.
