"""Independent scalar characteristic-polynomial oracle for the WP04 2-DOF case.

This test is prepared for a future Owner-approved V&V run. It is not executed as
part of WP12-Q preparation.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.modal_basis import ModalBasis


@pytest.mark.scientific_vv
def test_two_dof_eigenvalues_match_independent_characteristic_polynomial() -> None:
    mass_exact = (
        (Fraction(2), Fraction(1, 4)),
        (Fraction(1, 4), Fraction(3, 2)),
    )
    stiffness_exact = (
        (Fraction(20), Fraction(-2)),
        (Fraction(-2), Fraction(8)),
    )

    # det(K - lambda M) = a*lambda**2 + b*lambda + c.
    a = mass_exact[0][0] * mass_exact[1][1] - mass_exact[0][1] * mass_exact[1][0]
    b = -(
        stiffness_exact[0][0] * mass_exact[1][1]
        + stiffness_exact[1][1] * mass_exact[0][0]
        - stiffness_exact[0][1] * mass_exact[1][0]
        - stiffness_exact[1][0] * mass_exact[0][1]
    )
    c = stiffness_exact[0][0] * stiffness_exact[1][1] - stiffness_exact[0][1] * stiffness_exact[1][0]
    assert (a, b, c) == (Fraction(47, 16), Fraction(-47), Fraction(156))

    discriminant = b * b - 4 * a * c
    root = math.sqrt(float(discriminant))
    expected = np.sort(
        np.asarray([float((-float(b) - root) / (2 * float(a))), float((-float(b) + root) / (2 * float(a)))])
    )

    mass = np.asarray([[2.0, 0.25], [0.25, 1.5]])
    stiffness = np.asarray([[20.0, -2.0], [-2.0, 8.0]])
    basis = ModalBasis._from_operators(
        csr_matrix(stiffness),
        csr_matrix(mass),
        operator_identity="wp04-independent-characteristic-polynomial-v1",
        dof_signature=(),
        requested_modes=2,
        method="dense",
        dense_limit=2,
    )

    eigenvalues = np.asarray(basis.eigenvalues)
    np.testing.assert_allclose(eigenvalues, expected, rtol=1.0e-10, atol=0.0)
    projected_mass = basis.modes.T @ mass @ basis.modes
    np.testing.assert_allclose(projected_mass, np.eye(2), rtol=0.0, atol=1.0e-8)
    np.testing.assert_allclose(basis.projected_stiffness, np.diag(expected), rtol=1.0e-10, atol=0.0)

    residuals = []
    for index, eigenvalue in enumerate(eigenvalues):
        mode = basis.modes[:, index]
        k_mode = stiffness @ mode
        m_mode = mass @ mode
        numerator = np.linalg.norm(k_mode - eigenvalue * m_mode)
        denominator = np.linalg.norm(k_mode) + abs(eigenvalue) * np.linalg.norm(m_mode)
        residuals.append(numerator / denominator)
    assert max(residuals) <= 1.0e-8

    mass_orthogonality_error = np.linalg.norm(projected_mass - np.eye(2), ord="fro")
    assert mass_orthogonality_error <= 1.0e-8
    assert basis.maturity == "EXPERIMENTAL"
