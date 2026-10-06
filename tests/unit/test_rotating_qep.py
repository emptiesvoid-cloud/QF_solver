"""GYRO-03/04 analytical QEP checks and complex result serialization."""

from __future__ import annotations

import json

import numpy as np
import pytest

from solveur.core.analyses.qep import QuadraticEigenSolver
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.results import RotatingModalResult
from solveur.mesh.validation import MeshReport


J_DIAMETRAL = 0.01
J_POLAR = 0.02
K_THETA = 100.0


def _analytic_pair(omega: float) -> tuple[float, float]:
    omega0 = np.sqrt(K_THETA / J_DIAMETRAL)
    split = abs(omega * J_POLAR / J_DIAMETRAL) / 2.0
    center = np.sqrt(omega0**2 + split**2)
    return float(center - split), float(center + split)


def _solve(omega: float, *, length: float = 1.0):
    mass = J_DIAMETRAL * np.eye(2)
    stiffness = K_THETA * np.eye(2)
    gyro = np.asarray([[0.0, J_POLAR], [-J_POLAR, 0.0]])
    result = QuadraticEigenSolver().solve(
        mass,
        stiffness,
        gyro,
        omega,
        length_reference=length,
        dof_names=("RY", "RZ"),
    )
    return result, mass, stiffness


@pytest.mark.parametrize("omega", [0.0, 5.0, -5.0, 25.0, -25.0, 50.0, -50.0, 100.0, -100.0])
def test_gyro03_independent_disk_oracle_and_qep_residual(omega: float) -> None:
    result, mass, _ = _solve(omega)
    positive_frequencies = np.sort(result.eigenvalues.imag[result.eigenvalues.imag > 0.0])
    positive_frequencies /= 2.0 * np.pi
    expected = np.asarray(_analytic_pair(omega)) / (2.0 * np.pi)

    assert positive_frequencies == pytest.approx(expected, rel=1.0e-10, abs=1.0e-12)
    assert float(np.max(result.residuals)) <= 1.0e-10
    assert float(np.max(result.diagnostics["maximum_mass_normalization_error"])) <= 1.0e-10
    assert float(result.diagnostics["maximum_conservative_growth_ratio"]) <= 1.0e-8
    assert float(result.diagnostics["normalized_conjugate_spectrum_mismatch"]) <= 1.0e-8
    for mode in result.modes.T:
        assert np.vdot(mode, mass @ mode) == pytest.approx(1.0 + 0.0j, abs=1.0e-10)


def test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies() -> None:
    positive, _, _ = _solve(25.0)
    negative, _, _ = _solve(-25.0)

    assert positive.diagnostics["signed_speed_rad_s"] == 25.0
    assert negative.diagnostics["signed_speed_rad_s"] == -25.0
    assert positive.diagnostics["scaled_signed_speed"] == pytest.approx(
        -float(negative.diagnostics["scaled_signed_speed"]), rel=0.0, abs=1.0e-15
    )
    positive_spectrum = np.sort(positive.eigenvalues.imag[positive.eigenvalues.imag > 0.0])
    negative_spectrum = np.sort(negative.eigenvalues.imag[negative.eigenvalues.imag > 0.0])
    assert negative_spectrum == pytest.approx(positive_spectrum, rel=1.0e-10, abs=1.0e-10)


def test_gyro04_splitting_increases_with_absolute_signed_spin() -> None:
    speeds = (0.0, 5.0, 25.0, 50.0, 100.0)
    splittings: list[float] = []
    for speed in speeds:
        result, _, _ = _solve(speed)
        positive = np.sort(result.eigenvalues.imag[result.eigenvalues.imag > 0.0])
        splittings.append(float(positive[-1] - positive[0]))
    assert splittings == sorted(splittings)


def test_qep_physical_spectrum_is_invariant_to_frozen_coordinate_length_scale() -> None:
    unit_scale, _, _ = _solve(-50.0, length=1.0)
    long_scale, _, _ = _solve(-50.0, length=10.0)
    assert np.sort_complex(unit_scale.eigenvalues) == pytest.approx(
        np.sort_complex(long_scale.eigenvalues), rel=1.0e-10, abs=1.0e-10
    )


def test_qep_rejects_non_skew_gyro_and_non_positive_mass() -> None:
    solver = QuadraticEigenSolver()
    with pytest.raises(InputValidationError, match="skew-symmetric"):
        solver.solve(
            np.eye(2),
            np.eye(2),
            np.asarray([[0.0, 1.0], [0.0, 0.0]]),
            10.0,
            length_reference=1.0,
            dof_names=("RY", "RZ"),
        )
    with pytest.raises(InputValidationError, match="positive definite"):
        solver.solve(
            np.diag([1.0, 0.0]),
            np.eye(2),
            np.zeros((2, 2)),
            0.0,
            length_reference=1.0,
            dof_names=("RY", "RZ"),
        )


def test_rotating_modal_complex_serialization_round_trip_preserves_all_roots() -> None:
    qep, _, _ = _solve(25.0)
    dofs = DofManager.from_node_requirements({0: {"RY", "RZ"}})
    result = RotatingModalResult(
        numerical_status="PASS",
        maturity="EXPERIMENTAL",
        eigenvalues=qep.eigenvalues,
        modes=qep.modes,
        frequencies_hz=np.abs(qep.eigenvalues.imag) / (2.0 * np.pi),
        growth_rate_per_s=qep.eigenvalues.real,
        qep_residuals=qep.residuals,
        selected_mode_indices=(0, 2),
        dofs=dofs,
        mesh_report=MeshReport("PASS"),
        node_count=1,
        element_count=0,
        spin_speed_rad_s=25.0,
        axis_global=(1.0, 0.0, 0.0),
        frame_convention="global_fixed_right_hand_rule",
        solver_metadata={"backend": "scipy.linalg.eig(A,B)"},
        diagnostics={"case": "unit test"},
        provenance={"source_package_version": "0.2.10"},
    )
    serialized = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    eigenvalues, modes = RotatingModalResult.complex_arrays_from_dict(serialized)

    assert eigenvalues == pytest.approx(qep.eigenvalues)
    assert modes == pytest.approx(qep.modes)
    assert serialized["maturity"] == "EXPERIMENTAL"
    assert serialized["numerical_status"] == "PASS"
    assert set(serialized["raw_eigenvalues"]) == {"real", "imag"}
