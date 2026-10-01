from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.nonlinear_assembly import assemble_internal_tangent
from solveur.elements.solid.corotational_j2 import (
    CorotationalJ2Tet4Element,
    _stress_tensor,
    _strain_tensor,
    _strain_voigt,
    _transport_state,
)
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.verification.robustness_nonlinear_solids import _refinement_model


@pytest.mark.parametrize("family,point_count", [("TET4", 1), ("HEX8", 8)])
def test_corotational_j2_runs_bounded_newton_and_labels_postprocessing(
    family: str, point_count: int
) -> None:
    model = _refinement_model(family, 1)
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "kinematics": "corotational_j2",
            "load_steps": 3,
            "corotational_max_local_strain": 0.05,
        },
    )
    model = replace(model, loads=[replace(load, value=0.25 * load.value) for load in model.loads])

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["kinematics"] == "corotational_j2"
    element_result = result.element_results[0]
    assert element_result["type"] == f"{family}_COROTATIONAL_J2"
    assert element_result["kinematics"] == "corotational_small_strain"
    assert len(element_result["integration_points"]) == point_count
    assert all(
        np.isfinite(float(point["corotational_strain_norm"]))
        for point in element_result["integration_points"]
    )


def test_corotational_j2_rigid_rotation_has_no_spurious_response() -> None:
    material = VonMisesElastoplasticMaterial(
        E=1000.0,
        nu=0.3,
        yield_stress=1.0e6,
        hardening_modulus=10.0,
    )
    element = CorotationalJ2Tet4Element(material)
    coords = _tet4_coords()
    angle = 0.7
    rotation = np.asarray(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    displacement = ((rotation @ coords.T).T - coords).ravel()

    internal, tangent, states = element.internal_force_tangent_state(
        coords,
        displacement,
        [material.initial_state()],
    )
    point = element.integration_point_results(coords, displacement, [material.initial_state()])[0]

    assert np.linalg.norm(internal) < 1.0e-10
    assert np.all(np.isfinite(tangent))
    assert point["corotational_strain_norm"] < 1.0e-12
    assert np.max(np.abs(states[0]["stress"])) < 1.0e-10
    assert states[0]["equivalent_plastic_strain"] == 0.0


def test_corotational_j2_transports_committed_local_tensor_state() -> None:
    angle = 0.4
    rotation = np.asarray(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    state = {
        "plastic_strain": [0.02, -0.01, 0.0, 0.03, 0.0, 0.0],
        "stress": [2.0, -1.0, 0.5, 0.25, 0.0, 0.0],
        "strain": [0.01, -0.005, 0.0, 0.02, 0.0, 0.0],
        "equivalent_plastic_strain": 0.04,
        "corotation": np.eye(3).tolist(),
    }

    transported = _transport_state(state, rotation)
    assert transported is not None
    expected_plastic = _strain_voigt(
        rotation.T @ _strain_tensor(np.asarray(state["plastic_strain"])) @ rotation
    )
    expected_stress_tensor = rotation.T @ _stress_tensor(np.asarray(state["stress"])) @ rotation
    expected_stress = np.asarray(
        [
            expected_stress_tensor[0, 0],
            expected_stress_tensor[1, 1],
            expected_stress_tensor[2, 2],
            expected_stress_tensor[0, 1],
            expected_stress_tensor[1, 2],
            expected_stress_tensor[0, 2],
        ]
    )
    np.testing.assert_allclose(transported["plastic_strain"], expected_plastic)
    np.testing.assert_allclose(transported["stress"], expected_stress)
    assert transported["kinematics"] == "corotational_small_strain"
    np.testing.assert_allclose(transported["corotation"], rotation)


def test_corotational_j2_does_not_mutate_committed_state() -> None:
    material = VonMisesElastoplasticMaterial(
        E=1000.0,
        nu=0.3,
        yield_stress=0.02,
        hardening_modulus=10.0,
    )
    element = CorotationalJ2Tet4Element(material)
    coords = _tet4_coords()
    displacement = np.zeros(12)
    displacement[0::3] = 0.02 * coords[:, 0]
    committed = [material.initial_state()]
    snapshot = deepcopy(committed)

    element.internal_force_tangent_state(coords, displacement, committed)

    assert committed == snapshot


def test_corotational_j2_uncached_assembly_passes_strain_limit_to_element() -> None:
    model = _refinement_model("TET4", 1)
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "kinematics": "corotational_j2",
            "corotational_max_local_strain": 0.05,
        },
    )
    dofs = model.dof_manager()
    timing: dict[str, float | int] = {}

    internal, tangent, _ = assemble_internal_tangent(
        model,
        dofs,
        np.zeros(dofs.ndof),
        timing=timing,
    )

    assert np.all(np.isfinite(internal))
    assert tangent.nnz > 0
    assert timing["element_cache_misses"] == len(model.elements)


def test_corotational_j2_rejects_local_strain_outside_bounded_scope() -> None:
    material = VonMisesElastoplasticMaterial(
        E=1000.0,
        nu=0.3,
        yield_stress=1.0e6,
        hardening_modulus=10.0,
    )
    element = CorotationalJ2Tet4Element(material, max_corotational_strain=0.05)
    coords = _tet4_coords()
    stretch = np.diag([1.08, 1.0, 1.0])
    displacement = ((stretch @ coords.T).T - coords).ravel()

    with pytest.raises(ValueError, match="small-strain bound exceeded"):
        element.internal_force_tangent_state(coords, displacement, [material.initial_state()])


def _tet4_coords() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
