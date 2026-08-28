from __future__ import annotations

from dataclasses import replace

import pytest
import numpy as np

from solveur.api import solve_model
from solveur.core.errors import InputValidationError
from solveur.core.geometric_assembly import build_total_lagrangian_assembly
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear import NonlinearStaticSolver
from solveur.elements.solid.total_lagrangian_j2 import (
    TotalLagrangianJ2Hex20Element,
    TotalLagrangianJ2Hex8Element,
    TotalLagrangianJ2Tet10Element,
    TotalLagrangianJ2Tet4Element,
)
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.verification.robustness_nonlinear_solids import (
    _refinement_model,
    run_finite_kinematic_j2_benchmark,
)


@pytest.mark.parametrize("family,point_count", [("TET4", 1), ("HEX8", 8)])
def test_total_lagrangian_j2_uses_common_newton_and_objective_postprocessing(
    family: str, point_count: int
) -> None:
    model = _refinement_model(family, 1)
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "kinematics": "total_lagrangian_j2",
            "load_steps": 3,
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["steps"][-1]["relative_residual"] < 1.0e-7
    assert result.solver["kinematics"] == "total_lagrangian_j2"
    assert result.element_results[0]["type"] == f"{family}_TOTAL_LAGRANGIAN_J2"
    assert len(result.element_results[0]["integration_points"]) == point_count
    assert result.element_results[0]["kinematics"] == "green_lagrange_second_piola"
    assert result.element_results[0]["equivalent_plastic_strain"] > 0.0


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
def test_total_lagrangian_j2_supports_high_order_element_families(family: str) -> None:
    model = _high_order_model(family)
    model.analysis = replace(
        model.analysis,
        parameters={**model.analysis.parameters, "kinematics": "total_lagrangian_j2", "load_steps": 3},
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert result.solver["kinematics"] == "total_lagrangian_j2"
    assert result.element_results[0]["type"] == f"{family}_TOTAL_LAGRANGIAN_J2"
    assert result.element_results[0]["equivalent_plastic_strain"] > 0.0
    assert len(result.element_results[0]["integration_points"]) > 1


def test_total_lagrangian_j2_tet10_code_aster_quadrature_reaches_postprocessing() -> None:
    model = _high_order_model("TET10")
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "kinematics": "total_lagrangian_j2",
            "tet10_nonlinear_quadrature": "code_aster_5",
        },
    )
    model = replace(model, loads=[replace(load, value=1.0e-4) for load in model.loads])

    result = solve_model(model, enforce_policy=False)

    assert result.status == "PASS"
    assert len(result.element_results[0]["integration_points"]) == 5
    assert len(result.material_states[0]) == 5


@pytest.mark.parametrize("family,expected_entries", [("TET10", 900), ("HEX20", 3600)])
def test_high_order_geometric_assembly_uses_bounded_sparse_chunks(
    family: str, expected_entries: int
) -> None:
    model = _high_order_model(family)
    model.analysis = replace(
        model.analysis,
        parameters={**model.analysis.parameters, "nonlinear_assembly_chunk_size": 1},
    )
    assembly = build_total_lagrangian_assembly(model)

    internal, tangent = assembly.assemble(np.zeros(assembly.ndof))

    assert tangent is not None
    assert np.allclose(internal, 0.0)
    assert assembly.assembly_diagnostics() == {
        "sparse_chunk_count": 1,
        "sparse_peak_chunk_entries": expected_entries,
        "sparse_peak_chunk_bytes_estimate": expected_entries * 48,
        "sparse_accumulator_levels": 1,
    }


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
def test_total_lagrangian_j2_high_order_tangent_matches_finite_difference(family: str) -> None:
    material = VonMisesElastoplasticMaterial(
        E=1000.0,
        nu=0.3,
        yield_stress=1.0e6,
        hardening_modulus=10.0,
    )
    if family == "TET10":
        element = TotalLagrangianJ2Tet10Element(material)
        coords = np.vstack(
            [
                _tet4_coords(),
                [(_tet4_coords()[first] + _tet4_coords()[second]) / 2.0 for first, second in ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))],
            ]
        )
    else:
        element = TotalLagrangianJ2Hex20Element(material)
        coords = _hex20_coords()
    displacement = np.zeros(3 * element.node_count)
    displacement[0::3] = 0.02 * coords[:, 0]
    displacement[1::3] = -0.01 * coords[:, 1]
    displacement[2::3] = 0.015 * coords[:, 2]
    committed = [material.initial_state()] * element.integration_point_count
    _, tangent, _ = element.internal_force_tangent_state(coords, displacement, committed)
    step = 1.0e-7
    columns = []
    for column in range(displacement.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[column] += step
        minus[column] -= step
        force_plus, _, _ = element.internal_force_tangent_state(coords, plus, committed)
        force_minus, _, _ = element.internal_force_tangent_state(coords, minus, committed)
        columns.append((force_plus - force_minus) / (2.0 * step))

    np.testing.assert_allclose(tangent, np.column_stack(columns), rtol=8.0e-6, atol=2.0e-6)


def test_total_lagrangian_j2_reuses_reference_geometry_data() -> None:
    material = VonMisesElastoplasticMaterial(
        E=1000.0,
        nu=0.3,
        yield_stress=1.0e6,
        hardening_modulus=10.0,
    )
    element = TotalLagrangianJ2Hex20Element(material)
    coords = _hex20_coords()
    displacement = np.zeros(3 * element.node_count)
    committed = [material.initial_state()] * element.integration_point_count

    element.internal_force_tangent_state(coords, displacement, committed)
    element.internal_force_tangent_state(coords, displacement, committed)

    assert element.reference_geometry_cache_info() == {"hits": 1, "misses": 1}
    changed_coords = coords.copy()
    changed_coords[6, 0] += 1.0e-3
    element.internal_force_tangent_state(changed_coords, displacement, committed)
    assert element.reference_geometry_cache_info() == {"hits": 1, "misses": 2}


def test_total_lagrangian_j2_rejects_modified_newton() -> None:
    model = _refinement_model("TET4", 1)
    model.analysis = replace(
        model.analysis,
        method="modified_newton",
        parameters={**model.analysis.parameters, "kinematics": "total_lagrangian_j2"},
    )

    with pytest.raises(InputValidationError, match="qualified only with Full Newton"):
        solve_model(model, enforce_policy=False)


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
def test_total_lagrangian_j2_arc_length_scope_accepts_supported_families(family: str) -> None:
    model = _high_order_model(family) if family in {"TET10", "HEX20"} else _refinement_model(family, 1)
    parameters = {**model.analysis.parameters, "kinematics": "total_lagrangian_j2"}
    model.analysis = replace(model.analysis, method="arc_length", parameters=parameters)

    NonlinearStaticSolver._validate_kinematics_scope(model, parameters)


def test_total_lagrangian_j2_tangent_matches_finite_difference() -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0)
    element = TotalLagrangianJ2Tet4Element(material)
    coords = _tet4_coords()
    displacement = [0.0, 0.0, 0.0, 0.03, 0.001, 0.0, 0.001, 0.02, 0.0, 0.0, 0.0, 0.02]
    committed = [material.initial_state()]
    internal, tangent, _ = element.internal_force_tangent_state(coords, displacement, committed)
    finite_difference = []
    step = 1.0e-7
    for column in range(12):
        plus = list(displacement)
        minus = list(displacement)
        plus[column] += step
        minus[column] -= step
        force_plus, _, _ = element.internal_force_tangent_state(coords, plus, committed)
        force_minus, _, _ = element.internal_force_tangent_state(coords, minus, committed)
        finite_difference.append((force_plus - force_minus) / (2.0 * step))

    finite_difference_matrix = np.column_stack(finite_difference)
    np.testing.assert_allclose(tangent, finite_difference_matrix, rtol=2.0e-6, atol=5.0e-7)
    assert np.all(np.isfinite(internal))


@pytest.mark.parametrize("family", ["TET4", "HEX8"])
def test_total_lagrangian_j2_tangent_vectorization_matches_finite_difference(family: str) -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0)
    if family == "TET4":
        element = TotalLagrangianJ2Tet4Element(material)
        coords = _tet4_coords()
        displacement = np.asarray([0.0, 0.0, 0.0, 0.03, 0.001, 0.0, 0.001, 0.02, 0.0, 0.0, 0.0, 0.02])
    else:
        element = TotalLagrangianJ2Hex8Element(material)
        coords = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]
        )
        displacement = np.zeros(24)
        displacement[0::3] = 0.02 * coords[:, 0]
        displacement[1::3] = 0.01 * coords[:, 1]
        displacement[2::3] = -0.005 * coords[:, 2]
    _, tangent, _ = element.internal_force_tangent_state(
        coords, displacement, [material.initial_state()] * element.integration_point_count
    )
    step = 1.0e-7
    finite_difference = []
    for column in range(displacement.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[column] += step
        minus[column] -= step
        force_plus, _, _ = element.internal_force_tangent_state(
            coords, plus, [material.initial_state()] * element.integration_point_count
        )
        force_minus, _, _ = element.internal_force_tangent_state(
            coords, minus, [material.initial_state()] * element.integration_point_count
        )
        finite_difference.append((force_plus - force_minus) / (2.0 * step))

    np.testing.assert_allclose(tangent, np.column_stack(finite_difference), rtol=3.0e-6, atol=8.0e-7)


def test_total_lagrangian_j2_rigid_rotation_has_no_spurious_stress() -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0)
    element = TotalLagrangianJ2Tet4Element(material)
    coords = _tet4_coords()
    angle = 0.7
    rotation = np.asarray(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    displacement = ((rotation @ coords.T).T - coords).ravel()
    internal, _, states = element.internal_force_tangent_state(coords, displacement, [material.initial_state()])

    assert np.linalg.norm(internal) < 1.0e-10
    assert np.max(np.abs(states[0]["stress"])) < 1.0e-10
    assert states[0]["equivalent_plastic_strain"] == 0.0


@pytest.mark.parametrize("families", [("TET4", "HEX8"), ("TET10", "HEX20")])
def test_finite_kinematic_j2_campaign_records_bounded_research_evidence(
    families: tuple[str, ...],
) -> None:
    evidence = run_finite_kinematic_j2_benchmark(families)

    assert evidence["status"] == "PASS_INTERNAL_RESEARCH"
    assert {row["element"] for row in evidence["rows"]} == set(families)
    assert all(row["maximum_relative_residual"] < 1.0e-7 for row in evidence["rows"])
    assert all(row["rigid_rotation_internal_force_norm"] < 1.0e-9 for row in evidence["rows"])
    assert all(row["final_peeq"] > 0.0 for row in evidence["rows"])


def _tet4_coords():
    return np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def _high_order_model(family: str):
    if family == "TET10":
        corners = _tet4_coords()
        nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))]])
        connectivity = list(range(10))
    else:
        nodes = _hex20_coords()
        connectivity = list(range(20))
    fixed = [index for index, node in enumerate(nodes) if np.isclose(node[0], 0.0)]
    loaded = [index for index, node in enumerate(nodes) if np.isclose(node[0], 1.0)]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": connectivity, "material": "j2"}],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=[{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in fixed],
        loads=[{"node": index, "dof": "UX", "value": 1.0 / len(loaded)} for index in loaded],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 3, "max_iterations": 40, "tolerance": 1.0e-7},
    )


def _hex20_coords() -> np.ndarray:
    corners = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
         [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]],
        dtype=float,
    )
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
