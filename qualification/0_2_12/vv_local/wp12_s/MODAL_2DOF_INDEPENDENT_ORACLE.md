# Independent scalar oracle — coupled two-DOF modal case

**Status:** `EXECUTION_RECORDED`<br>
**Numerical execution:** `PERFORMED_WITH_TEST_FAILURE`<br>
**WP12:** `OPEN`

The case `MODAL-2DOF-POLY-001` instruments the separate source test [`test_modal_two_dof_independent_oracle.py`](../../../../tests/unit/test_modal_two_dof_independent_oracle.py). It was run once under the WP12-S manifest and its exact result is in the [execution report](WP12_S_EXECUTION_REPORT.md). The scalar-root values meet the stated eigenvalue criterion, but the overall pytest status is `FAIL` because the projected-stiffness assertion compares near-zero off-diagonal roundoff values using `atol=0`. No assertion or tolerance was edited, and no retry occurred.

For

```text
M = [[2, 1/4], [1/4, 3/2]]
K = [[20, -2], [-2, 8]]
```

exact rational expansion gives

```text
det(K - lambda M) = (47/16) lambda^2 - 47 lambda + 156
47 lambda^2 - 752 lambda + 2496 = 0
lambda = (376 +/- 16 sqrt(94))/47
```

The scalar coefficients and discriminant are formed with `fractions.Fraction`; floating square roots are used only to compare the reference roots with the computed eigenvalues. The acceptance limits are those already present in the WP04 contract and referenced source test: eigenvalue relative error `1e-10`, relative modal residual `1e-8`, and mass-orthogonality Frobenius error `1e-8`. Projected stiffness is compared with the diagonal expected eigenvalue matrix at the existing `rtol=1e-10`, `atol=0` assertion.

This is independent for the scalar eigenvalue reference only. The production `ModalBasis._from_operators` remains the system under test and uses its configured dense backend; the oracle does not independently establish eigenvectors, element assembly, prepared-system construction, or a full modal route. The basis remains `EXPERIMENTAL`. The separate instrumented unit emits coefficients, roots, computed eigenvalues, frequencies, residuals, projected mass/stiffness and orthogonality before assertions so a failure can preserve the observed payload.

The recorded scalar roots, computed eigenvalues, residuals and orthogonality values are reported in the execution report. This scalar oracle does not independently establish eigenvectors, assembly, prepared-system construction or full modal-route validity; it does not confer qualification. See the immutable manifest and [Owner decision package](WP12_S_OWNER_DECISION_PACKAGE.md) for the exact case binding and decision record limitations.
