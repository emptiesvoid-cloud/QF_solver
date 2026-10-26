# Q1–Q4 quantitative extraction review

**Status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`

## Historical record

The four WP12-R cases ran under the old campaign manifest SHA-256 `ea8f32e24d9eaded198230b0bc5f8aab45ed76293c3e73bdf77533e0bf08a0db`. Their outcome is `PYTEST_PASS_ONLY`; each receipt says numeric observables `NOT_EXPOSED`. The receipts contain exact selection, process, identity and environment facts, but no raw result values from which a scientific table or plot can be reconstructed. The receipt/run IDs and hashes are in [`FIRST_CAMPAIGN_ORACLE_REVIEW.md`](../FIRST_CAMPAIGN_ORACLE_REVIEW.md) and the immutable evidence tree outside the repository.

## Instrumented cases

The fixed wrapper is a separate test file and uses the exact source test helpers where available. It does not edit the prior tests. Its nodeids are all unparameterized exact selections accepted by the local runner.

| Prior WP12-R case | Historical node | Quantities to expose in new run | Reference and frozen checks | Limits |
|---|---|---|---|---|
| Q1 `ALG-PROJ-001` | `test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form` | Structured and dense projected matrices, max absolute difference, Frobenius-relative error with explicit normalization, symmetry defect | Dense `Phi.T @ K @ Phi`; exact symmetry and existing `rtol=atol=2e-16` | Algebraic identity only; no mesh or FEM validation |
| Q2 `MODAL-DISCRETE-001` | `test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form` | Effective K/M entries, theoretical and calculated frequency, relative error, modal residual | `omega=sqrt(k/m)`, `f=omega/(2*pi)`; existing frequency `rel=1e-12`, residual `<1e-12` | Test inputs do not declare an explicit unit system |
| Q3 `MODAL-2DOF-001` | `test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators` | K/M, eigenvalues/frequencies, projected K/M, modal residuals, mass-orthogonality and reconstruction errors | Existing test uses SciPy `eigh` as reference and production basis extraction uses the same generalized eigenvalue backend; existing assertions unchanged | Backend consistency and invariants, not independent eigenvalue or physical validation |
| Q4 `DYN-SDOF-001` | `test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection` | Prepared K/M, omega, full 81-point time/displacement history, analytic response, max and RMS errors, energy drift and reduced equilibrium diagnostic | Existing final value `rel=2e-4`, `abs=1e-9`; initial projection `<1e-12`; reduced equilibrium `<1e-7` | Instrumented variant adds output-only `record_time_history` and a `tip_ux` probe. Omega comes from prepared FE K/M; single dt, so no temporal convergence claim |

Q4's additional history flags are recorded in its canonical manifest fixture. The physical model, initial conditions, time step, integration parameters, modal count, and existing final-value oracle are retained. Because this is an instrumented variant rather than a byte-identical execution of the old test function, it has a separate case ID and Owner decision.

## Re-execution and reporting policy

The new marker records actual observed numbers only after an authorized run. The result table currently uses `NOT_EXPOSED` for all quantities, including theoretical reference quantities not serialized in old receipts. The analytical formulas and source inputs are documented but are not mislabeled as solver outputs. The original four receipts remain untouched. See [the campaign plan](WP12_S_CAMPAIGN_PLAN.md) and [the manifest](WP12_S_QUANTITATIVE_MANIFEST.json).
