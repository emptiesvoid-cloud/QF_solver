"""WP05-B controlled HEX20 high-order TL identity fixtures."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.assembly.geometric import build_total_lagrangian_assembly

from wp05_high_order_identity_support import (
    affine_deformation_gradient,
    affine_displacement,
    energy_gradient_metrics,
    finite_difference_step,
    hex20_coordinates,
    linear_reaction,
    model_for_family,
    rigid_body_displacement,
    stvk_oracle,
    structural_model,
    tangent_metrics,
    tl_reaction,
    tl_assembly,
)


def test_hex20_objectivity_uses_multiple_finite_rotations() -> None:
    assembly = tl_assembly("HEX20")
    coordinates = hex20_coordinates()
    for axis, angle in ((np.asarray([0.0, 0.0, 1.0]), 0.2), (np.asarray([1.0, 2.0, 3.0]), -0.47)):
        displacement = rigid_body_displacement(coordinates, axis, angle)
        internal, tangent = assembly.assemble(displacement)
        assert tangent is not None
        assert np.all(np.isfinite(internal))
        assert np.all(np.isfinite(tangent.data))
        assert assembly.strain_energy(displacement) <= 1.0e-12
        assert np.linalg.norm(internal) <= 1.0e-11


def test_hex20_affine_patch_matches_independent_stvk_oracle() -> None:
    deformation = affine_deformation_gradient()
    displacement = affine_displacement(hex20_coordinates(), deformation)
    assembly = tl_assembly("HEX20")
    state = assembly.element_states(displacement)
    oracle = stvk_oracle(deformation)
    np.testing.assert_allclose(state["green_lagrange_strain"][0], oracle["green"], rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(state["second_piola_stress"][0], _stress_tensor(oracle["stress"]), rtol=1.0e-12, atol=1.0e-14)
    assert assembly.strain_energy(displacement) == pytest.approx(float(oracle["energy_density"]), rel=1.0e-12, abs=1.0e-14)


def test_hex20_internal_force_is_energy_gradient_with_declared_step() -> None:
    relative, step = energy_gradient_metrics("HEX20")
    assert step == pytest.approx(finite_difference_step(affine_displacement(hex20_coordinates(), affine_deformation_gradient())))
    assert relative <= 1.0e-7


def test_hex20_tangent_matches_finite_difference_at_corner_and_midside_dofs() -> None:
    frobenius, maximum_column, symmetry, sampled = tangent_metrics("HEX20")
    assert sampled == [0, 1, 2, 24, 25, 26]
    assert frobenius <= 1.0e-6
    assert maximum_column <= 5.0e-6
    assert symmetry <= 1.0e-12


def test_hex20_small_displacement_limit_matches_linear_route() -> None:
    linear_model = structural_model("HEX20", "linear_static", 1.0e-7)
    tl_model = structural_model("HEX20", "geometric_nonlinear_static", 1.0e-7)
    linear = solve_model(linear_model, enforce_policy=False)
    total_lagrangian = solve_model(tl_model, enforce_policy=False)
    assert linear.status == "PASS"
    assert total_lagrangian.status == "success"
    displacement_error = np.linalg.norm(linear.displacements - total_lagrangian.displacements) / max(
        np.linalg.norm(linear.displacements), np.finfo(float).eps
    )
    linear_support = linear_reaction(linear_model, linear.displacements)
    tl_support = tl_reaction(tl_model, total_lagrangian.displacements)
    reaction_error = np.linalg.norm(linear_support - tl_support) / max(
        np.linalg.norm(linear_support), np.finfo(float).eps
    )
    assert displacement_error <= 1.0e-4
    assert reaction_error <= 1.0e-4


def test_hex20_has_positive_finite_jacobians_at_all_27_gauss_points() -> None:
    assembly = tl_assembly("HEX20")
    determinants = assembly._kernels[0]._cached_reference_data(hex20_coordinates())
    assert len(determinants) == 27
    assert all(np.isfinite(measure) and measure > 0.0 for measure, _ in determinants)


def test_hex20_tl_rejects_inverted_and_nonfinite_reference_geometry() -> None:
    coordinates = hex20_coordinates()
    inverted = coordinates[[0, 3, 2, 1, 4, 7, 6, 5, 9, 13, 11, 8, 10, 15, 19, 17, 16, 18, 14, 12]]
    with pytest.raises(ValueError, match="Invalid HEX20 Jacobian"):
        _assembly_from_coordinates("HEX20", inverted).assemble(np.zeros(60))
    nonfinite = coordinates.copy()
    nonfinite[8, 0] = np.inf
    with pytest.raises(ValueError, match="nodes must be a finite|nodes must have"):
        _assembly_from_coordinates("HEX20", nonfinite)


def _stress_tensor(values: object) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.asarray([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]])


def _assembly_from_coordinates(family: str, coordinates: np.ndarray) -> Any:
    model = model_for_family(family)
    model.nodes = np.asarray(coordinates, dtype=float)
    return build_total_lagrangian_assembly(model)
