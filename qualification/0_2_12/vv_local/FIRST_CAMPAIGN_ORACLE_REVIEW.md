# First local V&V cases — oracle and evidence review

**Status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`<br>
**Frozen candidate:** science commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.

The manifest binds the four existing nodeids below. Test source presence and prior campaign records are not results from this candidate run. All four are `NOT_RUN` here. The criteria below are taken from the existing tests/contracts; no assertion or tolerance is changed.

## Q1 — ALG-PROJ-001: structured symmetric projection

- **Exact node:** `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`
- **Code:** `src/solveur/core/analyses/modal_basis_numerics.py`, with the `ModalBasis` consumer in `src/solveur/core/analyses/modal_basis.py`.
- **Input:** test-owned symmetric CSR stiffness matrix `K` (4×4) and basis `Phi` (4×2), all defined inline in the test. No external fixture and no mesh.
- **Oracle:** dense bilinear form `Phi.T @ K @ Phi` compared with the structured projection.
- **Frozen checks:** exact input symmetry; symmetry metrics `(0.0, True)`; projected matrix exactly symmetric; dense/structured agreement with the existing `rtol=2e-16`, `atol=2e-16`; source matrix remains symmetric. Existing test assertions are authoritative.
- **Evidence class:** algebraic implementation identity. It is not an FEM solve, modal eigensolution, physical reference or convergence study.
- **Result availability:** assertion-only; no values are emitted for publication. Runner should record `NOT_EXPOSED` absent an explicit structured result.
- **Preparation:** lowest-cost first case; still requires its own Owner decision.

## Q2 — MODAL-DISCRETE-001: ground spring and concentrated mass

- **Exact node:** `tests/unit/test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form`
- **Code:** `src/solveur/elements/discrete.py`, `src/solveur/core/router.py`, `src/solveur/core/modal.py` and the modal assembly path.
- **Inline model:** one node; ground springs in UX/UY/UZ with stiffnesses 1000/4000/9000; concentrated mass 10; a 25 N UX load is present in the model but the modal eigenfrequency does not use that static load; one requested mode.
- **Oracle and units:** `omega = sqrt(k/m)` in rad/s; expected reported frequency is `sqrt(1000/10)/(2*pi)` Hz. The test does not declare a unit system, so the numeric inputs are treated as internally consistent only; no explicit N/m or kg metadata is asserted.
- **Frozen checks:** frequency relative error `1e-12`; maximum relative residual `<1e-12`.
- **Evidence class:** closed-form eigenfrequency comparison for a discrete spring/mass system through the modal route. It is not continuum-element or general structural modal qualification.
- **Result availability:** the test only asserts; raw frequency and residual are not printed by the test.
- **Preparation:** small solve, but unlike Q1 it executes the modal analysis route.

## Q3 — MODAL-2DOF-001: coupled two-DOF modal basis

- **Existing exact node:** `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators`
- **Code:** `src/solveur/core/analyses/modal_basis.py` and `src/solveur/core/analyses/modal_basis_numerics.py`.
- **Inline operators:** `M=[[2,0.25],[0.25,1.5]]`; `K=[[20,-2],[-2,8]]`.
- **Existing oracle limitation:** the test computes its expected eigenvalues with `scipy.linalg.eigh`; production `_matrix_basis` reaches `ModalBasis._from_operators`, which also uses SciPy `eigh`. This is useful same-backend consistency, not an independent eigenvalue reference.
- **Existing checks:** eigenvalues versus SciPy with `rtol=1e-12`, `atol=1e-12`; projected mass identity with absolute tolerance `1e-12`; projected stiffness and reconstruction with `rtol=1e-11`, `atol=1e-11`; mass orthogonality; full basis; maturity remains `EXPERIMENTAL`.
- **Contract:** [WP04 modal-basis/damping contract](../wp04_modal_basis_damping_contract.json) records eigensolver relative tolerance `1e-10`, maximum relative modal residual `1e-8`, and mass-orthogonality Frobenius error `1e-8`. These are contract criteria, not a new promotion.

### Separate independent scalar oracle

A distinct, unexecuted test has been added at `tests/unit/test_modal_two_dof_independent_oracle.py::test_two_dof_eigenvalues_match_independent_characteristic_polynomial`. It derives the coefficients using scalar rational arithmetic, not SciPy eigenvalues:

```text
det(K - lambda*M) = (47/16)*lambda^2 - 47*lambda + 156
47*lambda^2 - 752*lambda + 2496 = 0
lambda = (376 +/- 16*sqrt(94))/47
```

The new test compares the production eigenvalues to these roots at the WP04 `1e-10` relative eigensolver tolerance and checks the contract residual and mass-orthogonality maxima (`1e-8`). It also checks the projected operators. This makes the eigenvalue reference independent; it does **not** make the eigensolver, eigenvectors, matrix assembly or complete modal route independent. The separate test is deliberately not included in the four-case execution list and needs its own future manifest revision and Owner decision.

## Q4 — DYN-SDOF-001: undamped modal Newmark response

- **Exact node:** `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`
- **Code:** `src/solveur/core/analyses/modal_newmark.py`, `prepared_dynamic_system.py`, `modal_basis.py` and the BEAM2 element/assembly path.
- **Model:** one BEAM2 element of length 1; node 0 fixed in all six DOFs; node 1 fixed in UY/UZ/RX/RY/RZ, leaving UX; `E=1000`, `nu=0.25`, `A=1`, `Iy=Iz=0.1`, `J=0.2`, density 1; one mode; zero Rayleigh damping; initial UX displacement `0.002`, zero initial velocity; `dt=0.00005`, 80 steps; modal history enabled.
- **Reference:** `u(t)=u0*cos(omega*t)+v0*sin(omega*t)/omega`; this test uses `v0=0`, and derives `omega` from the prepared FE K/M operators. It checks time integration conditional on those operators, not an independent spatial FE solution.
- **Frozen checks:** final displacement uses relative tolerance `2e-4` and absolute tolerance `1e-9`; initial projection relative mass error `<1e-12`; reduced-equilibrium maximum relative error `<1e-7`; first modal acceleration relation; maturity remains `EXPERIMENTAL`. See [WP06 modal Newmark contract](../wp06_modal_newmark_contract.json).
- **Limit:** one time step size is tested. It does not establish time-step convergence, beam mesh convergence, arbitrary damping/excitation behavior or general transient qualification.
- **Result availability:** the test asserts the result but does not emit a table/time history suitable for publication; the runner will record `NOT_EXPOSED` unless a reviewed data extraction path is approved.

## Q5 supplemental oracle — separate from the four cases

The added scalar-oracle test has a distinct test-file hash and belongs to the separately identified tests checkout at commit `69a8642a15879666f59ad545dc83ac5852290b65`, tree `99c08ec34d2f5a78bb244d27724ac189519accb8`. It is not in the runner tree or frozen science tree. It is `PREPARED_NOT_AUTHORIZED`, `NOT_RUN`, and excluded from the first manifest's executable `cases` array. No claim about its runtime behavior or numerical outcome is made before its separate Owner review and execution.

## Evidence interpretation

For these cases the expected process-level success label is `PYTEST_PASS_ONLY`. An oracle pass requires a human or separate reviewed analysis to connect the recorded test assertions/results to the stated reference and frozen criteria. No benchmark or test in this folder creates an independent code_Aster correlation, physical experiment, spatial convergence result or release qualification.
