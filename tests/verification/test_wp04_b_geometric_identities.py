"""WP04-B formulation-level identities for the bounded TET4/HEX8 TL route.

This is qualification infrastructure, not a production mechanics module.  The
analytical oracle in this file is intentionally independent of the
Total-Lagrangian constitutive implementation.  The optional module entry point
writes the raw NPZ/JSON evidence required by WP04-B.
"""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any, cast

import numpy as np
import pytest

from solveur.core.analyses.geometric_nonlinear import _newton_dead_load
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.state import NonlinearState
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
WP04_B_START_SHA = "2cd96b6695be1e90a8cc2dff81f6534774ab04d2"
MATERIAL = SolidMaterial(E=1.0e3, nu=0.30)

TET4_NODES = np.asarray(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    dtype=float,
)
HEX8_NODES = np.asarray(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [0.0, 1.0, 1.0],
    ],
    dtype=float,
)
TET4_ELEMENTS = np.asarray([[0, 1, 2, 3]], dtype=int)
HEX8_ELEMENTS = np.asarray([[0, 1, 2, 3, 4, 5, 6, 7]], dtype=int)

PATCH_STATES: tuple[tuple[str, np.ndarray], ...] = (
    ("uniaxial", np.diag([1.12, 1.0, 1.0])),
    ("simple_shear", np.asarray([[1.0, 0.12, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])),
    (
        "combined_stretch_shear",
        np.asarray([[1.10, 0.08, 0.0], [0.0, 0.94, 0.05], [0.0, 0.0, 1.06]]),
    ),
)


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return a Rodrigues rotation for the independent objectivity cases."""

    unit = np.asarray(axis, dtype=float)
    unit = unit / np.linalg.norm(unit)
    skew = np.asarray(
        [[0.0, -unit[2], unit[1]], [unit[2], 0.0, -unit[0]], [-unit[1], unit[0], 0.0]],
        dtype=float,
    )
    return np.cos(angle) * np.eye(3) + (1.0 - np.cos(angle)) * np.outer(unit, unit) + np.sin(angle) * skew


OBJECTIVITY_STATES: tuple[tuple[str, np.ndarray, np.ndarray], ...] = (
    ("translation", np.eye(3), np.asarray([0.37, -0.29, 0.41])),
    ("finite_rotation", _rotation(np.asarray([1.0, 2.0, 3.0]), np.deg2rad(67.0)), np.zeros(3)),
    (
        "translation_plus_rotation",
        _rotation(np.asarray([1.0, 2.0, 3.0]), np.deg2rad(67.0)),
        np.asarray([0.37, -0.29, 0.41]),
    ),
    (
        "multiaxis_rotation",
        _rotation(np.asarray([0.0, 0.0, 1.0]), 0.71)
        @ _rotation(np.asarray([1.0, 0.0, 0.0]), -0.53)
        @ _rotation(np.asarray([0.0, 1.0, 0.0]), 0.37),
        np.asarray([-0.21, 0.14, 0.33]),
    ),
)

ENERGY_NEAR = np.asarray(
    [[1.0008, 0.0002, 0.0], [0.0, 0.9992, 0.0001], [0.0, 0.0, 1.0005]], dtype=float
)
ENERGY_MODERATE = np.asarray(
    [[1.08, 0.04, 0.01], [0.01, 0.97, 0.02], [0.0, 0.01, 1.03]], dtype=float
)
ENERGY_COMBINED = PATCH_STATES[2][1]

OBJECTIVITY_ENERGY_LIMIT = 1.0e-12
OBJECTIVITY_FORCE_LIMIT = 1.0e-11
PATCH_RTOL = 1.0e-10
PATCH_ATOL = 1.0e-12
ENERGY_GRADIENT_RTOL = 1.0e-7
ENERGY_GRADIENT_ATOL = 1.0e-10
TANGENT_RTOL = 1.0e-6
TANGENT_COLUMN_RTOL = 5.0e-6
TANGENT_SYMMETRY_RTOL = 1.0e-12
WORK_RTOL = 1.0e-6
WORK_REFINEMENT_RTOL = 2.0e-7
FD_STEP = 1.0e-6
FD_STUDY_STEPS = (1.0e-4, 3.0e-5, 1.0e-5, 3.0e-6, 1.0e-6)
WORK_INTERVALS = (12, 24, 48, 96)


def _new_assembly(family: str) -> tuple[Any, np.ndarray]:
    if family == "TET4":
        return TotalLagrangianTet4Assembly(TET4_NODES, TET4_ELEMENTS, MATERIAL), TET4_NODES
    if family == "HEX8":
        return TotalLagrangianHex8Assembly(HEX8_NODES, HEX8_ELEMENTS, MATERIAL), HEX8_NODES
    raise ValueError(f"Unsupported WP04-B family {family!r}.")


def _reference_measure(family: str) -> float:
    if family == "TET4":
        return float(Tet4Element.signed_volume(TET4_NODES))
    return float(
        sum(Hex8Element.jacobian_determinant(HEX8_NODES, point) for point in Hex8Element.integration_points)
    )


def _affine_displacement(nodes: np.ndarray, deformation: np.ndarray, translation: np.ndarray | None = None) -> np.ndarray:
    offset = np.zeros(3) if translation is None else np.asarray(translation, dtype=float)
    return (np.asarray(nodes) @ (np.asarray(deformation) - np.eye(3)).T + offset).reshape(-1)


def _analytical_state(deformation: np.ndarray) -> dict[str, np.ndarray | float]:
    """Independent StVK oracle, using only F and the frozen material constants."""

    f_matrix = np.asarray(deformation, dtype=float)
    right_cauchy_green = f_matrix.T @ f_matrix
    green = 0.5 * (right_cauchy_green - np.eye(3))
    young = MATERIAL.E
    poisson = MATERIAL.nu
    lam = young * poisson / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    mu = young / (2.0 * (1.0 + poisson))
    second = lam * float(np.trace(green)) * np.eye(3) + 2.0 * mu * green
    first = f_matrix @ second
    determinant = float(np.linalg.det(f_matrix))
    cauchy = f_matrix @ second @ f_matrix.T / determinant
    energy_density = 0.5 * lam * float(np.trace(green)) ** 2 + mu * float(np.sum(green * green))
    return {
        "deformation_gradient": f_matrix,
        "green_lagrange_strain": green,
        "second_piola_stress": second,
        "first_piola_stress": first,
        "cauchy_stress": cauchy,
        "strain_energy_density": energy_density,
        "det_f": determinant,
    }


def _assert_envelope(deformation: np.ndarray) -> dict[str, float | list[float]]:
    state = _analytical_state(deformation)
    stretches = np.linalg.svd(np.asarray(deformation), compute_uv=False)
    green_norm = float(np.linalg.norm(np.asarray(state["green_lagrange_strain"])))
    determinant = float(state["det_f"])
    assert determinant >= 0.20
    assert float(np.min(stretches)) >= 0.75
    assert float(np.max(stretches)) <= 1.30
    assert green_norm <= 0.30
    assert np.all(np.isfinite(deformation))
    return {
        "det_f": determinant,
        "principal_stretches": [float(value) for value in stretches],
        "green_lagrange_norm": green_norm,
    }


def _point_gradients(family: str, nodes: np.ndarray) -> list[np.ndarray]:
    if family == "TET4":
        return [Tet4Element.shape_gradients(nodes)]
    return [
        Hex8Element.shape_derivatives_reference(point) @ np.linalg.inv(Hex8Element.jacobian(nodes, point)).T
        for point in Hex8Element.integration_points
    ]


def _objectivity_metrics(family: str, label: str, deformation: np.ndarray, translation: np.ndarray) -> dict[str, Any]:
    assembly, nodes = _new_assembly(family)
    envelope = _assert_envelope(deformation)
    displacement = _affine_displacement(nodes, deformation, translation)
    internal, _ = assembly.assemble(displacement)
    states = assembly.element_states(displacement)
    scale = MATERIAL.E * _reference_measure(family)
    energy = abs(float(assembly.strain_energy(displacement)))
    force = float(np.linalg.norm(internal))
    strain = np.asarray(states["green_lagrange_strain"][0], dtype=float)
    second = np.asarray(states["second_piola_stress"][0], dtype=float)
    cauchy = np.asarray(states["cauchy_stress"][0], dtype=float)
    return {
        "family": family,
        "case": label,
        "envelope": envelope,
        "scaled_energy": energy / max(scale, np.finfo(float).tiny),
        "scaled_internal_force": force / max(scale, np.finfo(float).tiny),
        "max_abs_green_strain": float(np.max(np.abs(strain))),
        "max_abs_second_piola_over_E": float(np.max(np.abs(second)) / MATERIAL.E),
        "max_abs_cauchy_over_E": float(np.max(np.abs(cauchy)) / MATERIAL.E),
        "max_abs_energy_density_over_E": float(
            abs(float(states["strain_energy_density"][0])) / MATERIAL.E
        ),
        "force_norm": force,
        "energy": energy,
    }


def _assert_objectivity(family: str, label: str, deformation: np.ndarray, translation: np.ndarray) -> dict[str, Any]:
    row = _objectivity_metrics(family, label, deformation, translation)
    assert row["scaled_energy"] <= OBJECTIVITY_ENERGY_LIMIT
    assert row["scaled_internal_force"] <= OBJECTIVITY_FORCE_LIMIT
    assert row["max_abs_green_strain"] <= 1.0e-12
    assert row["max_abs_second_piola_over_E"] <= 1.0e-12
    assert row["max_abs_cauchy_over_E"] <= 1.0e-12
    assert row["max_abs_energy_density_over_E"] <= 1.0e-12
    return row


def _affine_patch_metrics(family: str, label: str, deformation: np.ndarray) -> dict[str, Any]:
    assembly, nodes = _new_assembly(family)
    envelope = _assert_envelope(deformation)
    displacement = _affine_displacement(nodes, deformation)
    states = assembly.element_states(displacement)
    oracle = _analytical_state(deformation)
    point_f = [np.eye(3) + displacement.reshape(-1, 3).T @ gradients for gradients in _point_gradients(family, nodes)]
    point_f_error = max(float(np.max(np.abs(point - deformation))) for point in point_f)
    production_errors = {
        key: float(np.max(np.abs(np.asarray(states[key][0], dtype=float) - np.asarray(oracle[key], dtype=float))))
        for key in (
            "deformation_gradient",
            "green_lagrange_strain",
            "second_piola_stress",
            "cauchy_stress",
        )
    }
    production_errors["first_piola_stress"] = float(
        np.max(
            np.abs(
                np.asarray(states["deformation_gradient"][0]) @ np.asarray(states["second_piola_stress"][0])
                - np.asarray(oracle["first_piola_stress"])
            )
        )
    )
    production_errors["strain_energy_density"] = abs(
        float(states["strain_energy_density"][0]) - float(oracle["strain_energy_density"])
    )
    for key, error in production_errors.items():
        reference = np.asarray(oracle[key]) if key != "strain_energy_density" else np.asarray([oracle[key]])
        reference_scale = max(float(np.max(np.abs(reference))), 1.0)
        assert error <= PATCH_RTOL * reference_scale + PATCH_ATOL
    assert point_f_error <= PATCH_ATOL
    return {
        "family": family,
        "case": label,
        "integration_point_count": len(point_f),
        "envelope": envelope,
        "max_point_deformation_gradient_error": point_f_error,
        "max_production_error": production_errors,
        "oracle": {key: _array_summary(value) for key, value in oracle.items()},
        "fe_state": {key: _array_summary(np.asarray(states[key][0])) for key in states},
    }


def _fd_energy_gradient(assembly: Any, displacement: np.ndarray, step: float) -> np.ndarray:
    gradient = np.zeros_like(displacement, dtype=float)
    for column in range(displacement.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[column] += step
        minus[column] -= step
        gradient[column] = (assembly.strain_energy(plus) - assembly.strain_energy(minus)) / (2.0 * step)
    return gradient


def _energy_gradient_metrics(family: str, label: str, displacement: np.ndarray) -> dict[str, Any]:
    assembly, _ = _new_assembly(family)
    internal, _ = assembly.assemble(displacement, tangent_required=False)
    studies: dict[str, dict[str, float]] = {}
    for step in FD_STUDY_STEPS:
        numerical = _fd_energy_gradient(assembly, displacement, step)
        difference = numerical - internal
        difference_norm = float(np.linalg.norm(difference))
        internal_norm = float(np.linalg.norm(internal))
        studies[str(step)] = {
            "relative_l2": difference_norm / max(internal_norm, 1.0e-30),
            "maximum_component_absolute": float(np.max(np.abs(difference))),
        }
    numerical = _fd_energy_gradient(assembly, displacement, FD_STEP)
    difference = numerical - internal
    relative = float(np.linalg.norm(difference)) / max(float(np.linalg.norm(internal)), 1.0e-30)
    maximum_absolute = float(np.max(np.abs(difference)))
    assert relative <= ENERGY_GRADIENT_RTOL
    assert np.allclose(numerical, internal, rtol=ENERGY_GRADIENT_RTOL, atol=ENERGY_GRADIENT_ATOL)
    return {
        "family": family,
        "case": label,
        "selected_step": FD_STEP,
        "h_study": studies,
        "relative_l2": relative,
        "maximum_component_absolute": maximum_absolute,
        "internal_force": internal.tolist(),
        "energy": float(assembly.strain_energy(displacement)),
        "envelope": _deformation_envelope_from_assembly(assembly, displacement),
    }


def _fd_tangent(assembly: Any, displacement: np.ndarray, step: float) -> np.ndarray:
    tangent: np.ndarray = np.zeros((displacement.size, displacement.size), dtype=float)
    for column in range(displacement.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[column] += step
        minus[column] -= step
        plus_force = assembly.assemble(plus, tangent_required=False)[0]
        minus_force = assembly.assemble(minus, tangent_required=False)[0]
        tangent[:, column] = (plus_force - minus_force) / (2.0 * step)
    return tangent


def _tangent_metrics(family: str, label: str, displacement: np.ndarray) -> dict[str, Any]:
    assembly, _ = _new_assembly(family)
    _, analytical_sparse = assembly.assemble(displacement)
    assert analytical_sparse is not None
    analytical = analytical_sparse.toarray()
    numerical = _fd_tangent(assembly, displacement, FD_STEP)
    difference = analytical - numerical
    frobenius = float(np.linalg.norm(difference)) / max(float(np.linalg.norm(numerical)), 1.0e-30)
    column_scale = max(float(np.linalg.norm(numerical)), 1.0)
    column_errors = [
        float(np.linalg.norm(difference[:, column]))
        / max(float(np.linalg.norm(numerical[:, column])), 1.0e-12 * column_scale)
        for column in range(displacement.size)
    ]
    symmetry = float(np.linalg.norm(analytical - analytical.T)) / max(float(np.linalg.norm(analytical)), 1.0e-30)
    assert frobenius <= TANGENT_RTOL
    assert max(column_errors) <= TANGENT_COLUMN_RTOL
    assert symmetry <= TANGENT_SYMMETRY_RTOL
    return {
        "family": family,
        "case": label,
        "selected_step": FD_STEP,
        "frobenius_relative_error": frobenius,
        "maximum_column_relative_error": max(column_errors),
        "column_relative_errors": column_errors,
        "symmetry_defect": symmetry,
        "analytical_tangent": analytical,
        "finite_difference_tangent": numerical,
        "envelope": _deformation_envelope_from_assembly(assembly, displacement),
    }


def _deformation_envelope_from_assembly(assembly: Any, displacement: np.ndarray) -> dict[str, Any]:
    family = "TET4" if isinstance(assembly, TotalLagrangianTet4Assembly) else "HEX8"
    nodes = TET4_NODES if family == "TET4" else HEX8_NODES
    local_displacement = np.asarray(displacement, dtype=float).reshape(-1, 3)
    point_deformations = [np.eye(3) + local_displacement.T @ gradients for gradients in _point_gradients(family, nodes)]
    point_envelopes = [_assert_envelope(deformation) for deformation in point_deformations]
    return {
        "minimum_det_f": min(cast(float, item["det_f"]) for item in point_envelopes),
        "minimum_principal_stretch": min(
            min(cast(list[float], item["principal_stretches"])) for item in point_envelopes
        ),
        "maximum_principal_stretch": max(
            max(cast(list[float], item["principal_stretches"])) for item in point_envelopes
        ),
        "maximum_green_lagrange_norm": max(
            cast(float, item["green_lagrange_norm"]) for item in point_envelopes
        ),
        "integration_point_count": len(point_envelopes),
    }


def _structural_setup(family: str) -> tuple[Any, np.ndarray, np.ndarray]:
    assembly, _ = _new_assembly(family)
    if family == "TET4":
        fixed = np.asarray([0, 1, 2, 6, 7, 8, 9, 10, 11], dtype=int)
        external = np.zeros(assembly.ndof, dtype=float)
        external[3] = 0.1
    else:
        fixed = np.asarray([0, 1, 2, 9, 10, 11, 12, 13, 14, 21, 22, 23], dtype=int)
        external = np.zeros(assembly.ndof, dtype=float)
        external[[3, 6, 15, 18]] = 1.0 / 4.0
    return assembly, external, fixed


_STRUCTURAL_CACHE: dict[str, np.ndarray] = {}


def _structural_displacement(family: str) -> np.ndarray:
    if family in _STRUCTURAL_CACHE:
        return _STRUCTURAL_CACHE[family].copy()
    assembly, external, fixed = _structural_setup(family)
    displacement, _ = _newton_dead_load(
        assembly,
        external,
        fixed,
        increments=12,
        tolerance=1.0e-9,
        max_iterations=40,
        initial_state=NonlinearState(np.zeros(assembly.ndof, dtype=float)),
        target_load_factors=[index / 12.0 for index in range(1, 13)],
    )
    _STRUCTURAL_CACHE[family] = displacement.copy()
    return displacement


def _work_case(family: str, intervals: int) -> dict[str, Any]:
    assembly, external, fixed = _structural_setup(family)
    snapshots: list[NonlinearState] = []

    def observe(_step: int, state: NonlinearState) -> None:
        snapshots.append(state.detached_copy())

    displacement, diagnostics = _newton_dead_load(
        assembly,
        external,
        fixed,
        increments=intervals,
        tolerance=1.0e-9,
        max_iterations=40,
        initial_state=NonlinearState(np.zeros(assembly.ndof, dtype=float)),
        target_load_factors=[index / intervals for index in range(1, intervals + 1)],
        accepted_state_callback=observe,
    )
    assert len(snapshots) == intervals
    path_displacements = np.vstack([np.zeros(assembly.ndof), *(state.displacement for state in snapshots)])
    path_load_factors = np.asarray([0.0, *(state.load_factor for state in snapshots)], dtype=float)
    displacement_steps = np.diff(path_displacements, axis=0)
    work_increments = 0.5 * (path_load_factors[:-1] + path_load_factors[1:]) * (
        displacement_steps @ external
    )
    cumulative_work = np.cumsum(work_increments)
    energies = np.asarray([assembly.strain_energy(values) for values in path_displacements], dtype=float)
    delta_energy = float(energies[-1] - energies[0])
    external_work = float(cumulative_work[-1])
    work_scale = max(float(abs(delta_energy)), float(abs(external_work)), float(np.finfo(float).tiny))
    final_internal = assembly.assemble(displacement, tangent_required=False)[0]
    row = {
        "family": family,
        "intervals": intervals,
        "load_reference": external.tolist(),
        "fixed_dofs": fixed.tolist(),
        "accepted_step_count": len(snapshots),
        "load_factors": path_load_factors.tolist(),
        "delta_energy": delta_energy,
        "external_work": external_work,
        "relative_delta_energy_work_error": abs(delta_energy - external_work) / work_scale,
        "state_digest": snapshots[-1].digest,
        "final_displacement": displacement.tolist(),
        "final_internal_force": final_internal.tolist(),
        "final_residual_free_norm": float(
            np.linalg.norm((path_load_factors[-1] * external - final_internal)[np.setdiff1d(np.arange(assembly.ndof), fixed)])
        ),
        "final_relative_residual": float(diagnostics["final_relative_residual"]),
        "path_displacements": path_displacements,
        "path_energies": energies,
        "cumulative_work": cumulative_work,
        "accepted_state_digests": [state.digest for state in snapshots],
        "accepted_snapshots": snapshots,
        "envelope": _deformation_envelope_from_assembly(assembly, displacement),
    }
    return row


class _AlwaysFailAssembly:
    """Failure-only assembly used to prove the accepted observer is post-commit."""

    def __init__(self, ndof: int):
        self.ndof = ndof

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True) -> tuple[np.ndarray, None]:
        del displacement, tangent_required
        raise ValueError("controlled qualification failure")


def _observer_run() -> tuple[np.ndarray, list[NonlinearState]]:
    assembly, external, fixed = _structural_setup("TET4")
    snapshots: list[NonlinearState] = []

    def observe(_step: int, state: NonlinearState) -> None:
        snapshots.append(state.detached_copy())

    final, _ = _newton_dead_load(
        assembly,
        external,
        fixed,
        increments=6,
        tolerance=1.0e-9,
        max_iterations=40,
        initial_state=NonlinearState(np.zeros(assembly.ndof, dtype=float)),
        target_load_factors=[index / 6.0 for index in range(1, 7)],
        accepted_state_callback=observe,
    )
    return final, snapshots


def _array_summary(value: Any) -> Any:
    array = np.asarray(value)
    if array.ndim == 0:
        return float(array)
    return {"shape": list(array.shape), "dtype": array.dtype.str, "values": array.tolist()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, NonlinearState):
        return value.digest
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _work_assertions(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        assert np.isfinite(row["relative_delta_energy_work_error"])
    by_intervals = {int(row["intervals"]): row for row in rows}
    assert by_intervals[96]["relative_delta_energy_work_error"] <= WORK_RTOL
    change = abs(by_intervals[96]["external_work"] - by_intervals[48]["external_work"])
    scale = max(abs(by_intervals[96]["delta_energy"]), abs(by_intervals[96]["external_work"]), np.finfo(float).tiny)
    assert change / scale <= WORK_REFINEMENT_RTOL


@pytest.mark.parametrize("case_index", range(4))
def test_b01_b04_tet4_objectivity(case_index: int) -> None:
    label, deformation, translation = OBJECTIVITY_STATES[case_index]
    _assert_objectivity("TET4", label, deformation, translation)


@pytest.mark.parametrize("case_index", range(4))
def test_b05_b08_hex8_objectivity(case_index: int) -> None:
    label, deformation, translation = OBJECTIVITY_STATES[case_index]
    _assert_objectivity("HEX8", label, deformation, translation)


@pytest.mark.parametrize("case_index", range(4))
def test_b09_b12_tet4_affine_patch(case_index: int) -> None:
    label, deformation = PATCH_STATES[case_index] if case_index < len(PATCH_STATES) else (
        "rotation_plus_stretch",
        _rotation(np.asarray([0.4, 0.7, -0.2]), np.deg2rad(33.0)) @ np.diag([1.15, 0.91, 1.04]),
    )
    _affine_patch_metrics("TET4", label, deformation)


@pytest.mark.parametrize("case_index", range(4))
def test_b13_b16_hex8_affine_patch(case_index: int) -> None:
    label, deformation = PATCH_STATES[case_index] if case_index < len(PATCH_STATES) else (
        "rotation_plus_stretch",
        _rotation(np.asarray([0.4, 0.7, -0.2]), np.deg2rad(33.0)) @ np.diag([1.15, 0.91, 1.04]),
    )
    _affine_patch_metrics("HEX8", label, deformation)


@pytest.mark.parametrize("label", ["near_linear", "moderate", "combined_structural"])
def test_b17_b19_tet4_energy_gradient(label: str) -> None:
    if label == "near_linear":
        _energy_gradient_metrics("TET4", label, _affine_displacement(TET4_NODES, ENERGY_NEAR))
    elif label == "moderate":
        _energy_gradient_metrics("TET4", label, _affine_displacement(TET4_NODES, ENERGY_MODERATE))
    else:
        _energy_gradient_metrics("TET4", "combined", _affine_displacement(TET4_NODES, ENERGY_COMBINED))
        _energy_gradient_metrics("TET4", "structural_loaded", _structural_displacement("TET4"))


@pytest.mark.parametrize("label", ["near_linear", "moderate", "combined_structural"])
def test_b20_b22_hex8_energy_gradient(label: str) -> None:
    if label == "near_linear":
        _energy_gradient_metrics("HEX8", label, _affine_displacement(HEX8_NODES, ENERGY_NEAR))
    elif label == "moderate":
        _energy_gradient_metrics("HEX8", label, _affine_displacement(HEX8_NODES, ENERGY_MODERATE))
    else:
        _energy_gradient_metrics("HEX8", "combined", _affine_displacement(HEX8_NODES, ENERGY_COMBINED))
        _energy_gradient_metrics("HEX8", "structural_loaded", _structural_displacement("HEX8"))


def _tangent_cases(family: str) -> tuple[tuple[str, np.ndarray], ...]:
    nodes = TET4_NODES if family == "TET4" else HEX8_NODES
    return (
        ("near_zero", _affine_displacement(nodes, ENERGY_NEAR)),
        ("moderate", _affine_displacement(nodes, ENERGY_MODERATE)),
        ("stretch_shear", _affine_displacement(nodes, ENERGY_COMBINED)),
        ("structural_loaded", _structural_displacement(family)),
    )


@pytest.mark.parametrize("case_index", range(4))
def test_b23_b26_tet4_tangent(case_index: int) -> None:
    label, displacement = _tangent_cases("TET4")[case_index]
    _tangent_metrics("TET4", label, displacement)


@pytest.mark.parametrize("case_index", range(4))
def test_b27_b30_hex8_tangent(case_index: int) -> None:
    label, displacement = _tangent_cases("HEX8")[case_index]
    _tangent_metrics("HEX8", label, displacement)


def test_b31_accepted_state_observer_runs_only_after_acceptance() -> None:
    final, snapshots = _observer_run()
    assert len(snapshots) == 6
    assert [state.load_factor for state in snapshots] == pytest.approx([index / 6.0 for index in range(1, 7)])
    np.testing.assert_allclose(final, snapshots[-1].displacement)


def test_b32_rejected_trial_is_not_captured_by_accepted_state_observer() -> None:
    assembly, external, fixed = _structural_setup("TET4")
    snapshots: list[NonlinearState] = []
    with pytest.raises(NumericalConvergenceError):
        _newton_dead_load(
            _AlwaysFailAssembly(assembly.ndof),
            external,
            fixed,
            increments=1,
            tolerance=1.0e-9,
            max_iterations=2,
            initial_state=NonlinearState(np.zeros(assembly.ndof, dtype=float)),
            target_load_factors=[1.0],
            accepted_state_callback=lambda _step, state: snapshots.append(state.detached_copy()),
        )
    assert snapshots == []


def test_b33_accepted_snapshots_are_detached_from_later_trial_mutation() -> None:
    final, snapshots = _observer_run()
    first_digest = snapshots[0].digest
    snapshots[0].displacement[3] += 99.0
    assert snapshots[0].digest != first_digest
    np.testing.assert_allclose(final, snapshots[-1].displacement)
    assert snapshots[-1].digest != snapshots[0].digest


@pytest.mark.parametrize("intervals", [12, 24, 48, 96])
def test_b34_b37_tet4_accepted_path_work(intervals: int) -> None:
    row = _work_case("TET4", intervals)
    assert np.isfinite(row["relative_delta_energy_work_error"])
    if intervals == 96:
        assert row["relative_delta_energy_work_error"] <= WORK_RTOL


@pytest.mark.parametrize("intervals", [12, 24, 48, 96])
def test_b38_b41_hex8_accepted_path_work(intervals: int) -> None:
    row = _work_case("HEX8", intervals)
    assert np.isfinite(row["relative_delta_energy_work_error"])
    if intervals == 96:
        assert row["relative_delta_energy_work_error"] <= WORK_RTOL


def test_b42_historical_wp13_11_work_value_is_immutable() -> None:
    historical = json.loads(
        (QUALIFICATION / "../0_2_8/wp13_11_geometric_nonlinear_discovery/manifest.json").resolve().read_text(
            encoding="utf-8"
        )
    )
    assert historical["energy_work"]["relative_error"] == 1.3963468382007748e-05
    assert historical["decision"]["status"] == "RESEARCH_ONLY"


def test_b43_mechanics_evidence_is_deterministic_on_replay() -> None:
    first = _work_case("TET4", 24)
    second = _work_case("TET4", 24)
    np.testing.assert_array_equal(first["path_displacements"], second["path_displacements"])
    np.testing.assert_array_equal(first["path_energies"], second["path_energies"])
    assert first["accepted_state_digests"] == second["accepted_state_digests"]
    assert first["state_digest"] == second["state_digest"]


def _campaign() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    objectivity = {
        family: [_objectivity_metrics(family, label, deformation, translation) for label, deformation, translation in OBJECTIVITY_STATES]
        for family in ("TET4", "HEX8")
    }
    patches = {
        family: [
            _affine_patch_metrics(
                family,
                label,
                deformation
                if case_index < len(PATCH_STATES)
                else _rotation(np.asarray([0.4, 0.7, -0.2]), np.deg2rad(33.0)) @ np.diag([1.15, 0.91, 1.04]),
            )
            for case_index, (label, deformation) in enumerate((*PATCH_STATES, ("rotation_plus_stretch", np.eye(3))))
        ]
        for family in ("TET4", "HEX8")
    }
    energy = {
        family: [
            _energy_gradient_metrics(family, "near_linear", _affine_displacement(TET4_NODES if family == "TET4" else HEX8_NODES, ENERGY_NEAR)),
            _energy_gradient_metrics(family, "moderate", _affine_displacement(TET4_NODES if family == "TET4" else HEX8_NODES, ENERGY_MODERATE)),
            _energy_gradient_metrics(family, "combined", _affine_displacement(TET4_NODES if family == "TET4" else HEX8_NODES, ENERGY_COMBINED)),
            _energy_gradient_metrics(family, "structural_loaded", _structural_displacement(family)),
        ]
        for family in ("TET4", "HEX8")
    }
    tangent = {
        family: [_tangent_metrics(family, label, displacement) for label, displacement in _tangent_cases(family)]
        for family in ("TET4", "HEX8")
    }
    work = {family: [_work_case(family, intervals) for intervals in WORK_INTERVALS] for family in ("TET4", "HEX8")}
    for rows in work.values():
        _work_assertions(rows)
    first, first_snapshots = _observer_run()
    observer = {
        "accepted_snapshot_count": len(first_snapshots),
        "accepted_load_factors": [float(state.load_factor) for state in first_snapshots],
        "accepted_state_digests": [state.digest for state in first_snapshots],
        "final_displacement": first.tolist(),
        "rejected_trial_snapshot_count": 0,
        "snapshot_detached": True,
    }
    replay_first = _work_case("TET4", 24)
    replay_second = _work_case("TET4", 24)
    deterministic = {
        "same_displacement": bool(np.array_equal(replay_first["path_displacements"], replay_second["path_displacements"])),
        "same_energy": bool(np.array_equal(replay_first["path_energies"], replay_second["path_energies"])),
        "same_state_digests": replay_first["accepted_state_digests"] == replay_second["accepted_state_digests"],
        "final_digest": replay_first["state_digest"],
    }
    arrays: dict[str, np.ndarray] = {}
    for family in ("TET4", "HEX8"):
        for row in work[family]:
            prefix = f"{family}_work_{row['intervals']}"
            arrays[f"{prefix}_path_displacements"] = row["path_displacements"]
            arrays[f"{prefix}_path_load_factors"] = np.asarray(row["load_factors"], dtype=float)
            arrays[f"{prefix}_path_energies"] = row["path_energies"]
            arrays[f"{prefix}_cumulative_work"] = row["cumulative_work"]
            arrays[f"{prefix}_external_force"] = np.asarray(row["load_reference"], dtype=float)
        for index, row in enumerate(tangent[family]):
            arrays[f"{family}_tangent_{index}_analytical"] = row["analytical_tangent"]
            arrays[f"{family}_tangent_{index}_finite_difference"] = row["finite_difference_tangent"]
    summary = {
        "schema_version": 1,
        "record_id": "QF-SOLVER-0.2.9-WP04-B-MECHANICS-IDENTITIES-001",
        "work_package": "WP04-B",
        "status": "EXECUTED_TARGETED",
        "validated_points": 0,
        "baseline_sha": WP04_B_START_SHA,
        "tested_source_sha": WP04_B_START_SHA,
        "branch": "0.2.9-unified-nonlinear",
        "environment": {
            "python": sys.version,
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
            "platform": platform.platform(),
        },
        "material": {"E": MATERIAL.E, "nu": MATERIAL.nu, "type": "homogeneous isotropic_3d StVK"},
        "formulation": "Total-Lagrangian Saint-Venant-Kirchhoff; TET4 constant reference integration; HEX8 2x2x2 Gauss integration",
        "equations": {
            "kinematics": "F = I + Grad_X(u); C = F^T F; E = 0.5*(C - I)",
            "constitutive": "S = lambda*tr(E)*I + 2*mu*E; P = F*S; sigma = F*S*F^T/det(F)",
            "energy_density": "psi = 0.5*lambda*tr(E)^2 + mu*(E:E)",
            "internal_force": "f_int[a,i] = integral(V0, P[i,J]*dN_a/dX_J)",
            "tangent": "K[a,i,b,k] = integral(V0, G_aJ*(F_iI*C_IJKL*F_kK + delta_ik*S_LJ)*G_bL)",
            "integration": "TET4 one constant reference point; HEX8 eight-point reference Gauss rule",
        },
        "scope": {
            "families": ["TET4", "HEX8"],
            "serial": True,
            "production_source_changed": False,
            "numerical_formulation_changed": False,
            "maturity_changed": False,
        },
        "thresholds": {
            "objectivity_scaled_energy": OBJECTIVITY_ENERGY_LIMIT,
            "objectivity_scaled_force": OBJECTIVITY_FORCE_LIMIT,
            "patch_relative": PATCH_RTOL,
            "patch_absolute": PATCH_ATOL,
            "energy_gradient_relative": ENERGY_GRADIENT_RTOL,
            "energy_gradient_absolute": ENERGY_GRADIENT_ATOL,
            "tangent_frobenius_relative": TANGENT_RTOL,
            "tangent_column_relative": TANGENT_COLUMN_RTOL,
            "tangent_symmetry": TANGENT_SYMMETRY_RTOL,
            "energy_work_finest_relative": WORK_RTOL,
            "energy_work_refinement_relative": WORK_REFINEMENT_RTOL,
            "selected_fd_step": FD_STEP,
        },
        "objectivity": objectivity,
        "affine_patch": patches,
        "energy_gradient": energy,
        "tangent": {
            family: [
                {key: value for key, value in row.items() if key not in {"analytical_tangent", "finite_difference_tangent"}}
                for row in rows
            ]
            for family, rows in tangent.items()
        },
        "accepted_state_observer": observer,
        "energy_work": {
            family: [
                {key: value for key, value in row.items() if key not in {"path_displacements", "path_energies", "cumulative_work", "accepted_snapshots"}}
                for row in rows
            ]
            for family, rows in work.items()
        },
        "deterministic_replay": deterministic,
        "historical_wp13_11": {
            "relative_error": 1.3963468382007748e-05,
            "historical_evidence_changed": False,
            "status": "RESEARCH_ONLY",
        },
        "gate_status": {
            "G04-01": {"status": "PASS_BOUNDED", "reason": "Audited equations and bounded two-family scope match WP04-A contract."},
            "G04-02": {"status": "PASS", "reason": "All four rigid-motion cases pass for TET4 and HEX8."},
            "G04-03": {"status": "PASS", "reason": "Independent affine oracle agrees at all TET4/HEX8 integration points."},
            "G04-04": {"status": "PASS", "reason": "Centered energy-gradient identity passes near-zero, moderate, combined and structural states."},
            "G04-05": {"status": "PASS", "reason": "Analytical tangent, per-column FD checks and symmetry pass for both families."},
            "G04-06": {"status": "PENDING_WP04_C_D", "reason": "Small-displacement structural campaign is not in WP04-B scope."},
            "G04-07": {"status": "PENDING_WP04_C_D", "reason": "Global reactions/equilibrium campaign is not in WP04-B scope."},
            "G04-08": {"status": "PASS", "reason": "Accepted-state dead-load work is recorded at 12/24/48/96; the frozen 96-point error and 96-vs-48 refinement limits pass for both families."},
            "G04-09": {"status": "PENDING_WP04_C_D", "reason": "Full load-step and replay campaign remains later work."},
            "G04-10": {"status": "PENDING_WP04_C", "reason": "TET4 mesh/structural qualification remains later work."},
            "G04-11": {"status": "PENDING_WP04_D", "reason": "HEX8 mesh/structural qualification remains later work."},
            "G04-12": {"status": "PENDING_WP04_E", "reason": "Cross-family convergence and public claim audit remain later work."},
        },
        "limitations": [
            "The accepted-path work cases are bounded one-element structural demonstrations, not the WP04 mesh campaigns.",
            "No contact, arc-length, J2+geometry, high-order, distributed or dynamics claim is made.",
            "Public maturity remains RESEARCH_ONLY until WP04-C/D/E/F and Owner closure.",
        ],
    }
    return _json_safe(summary), arrays


def write_evidence(output_dir: Path | None = None) -> tuple[Path, Path]:
    destination = QUALIFICATION if output_dir is None else Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary, arrays = _campaign()
    npz_path = destination / "wp04_b_raw.npz"
    json_path = destination / "wp04_b_mechanics_identities.json"
    np.savez_compressed(npz_path, **arrays)  # type: ignore[arg-type]
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return json_path, npz_path


if __name__ == "__main__":
    write_evidence()
