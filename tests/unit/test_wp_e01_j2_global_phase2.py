"""Independent, no-solve checks for the J2 tangent under fixed histories.

These tests call only the constitutive kernel or in-memory element assembly.
They never invoke a nonlinear solver, Newton iteration, native FEM backend, or
external mesh generator.
"""

from __future__ import annotations

import json
from dataclasses import replace
from itertools import product

import numpy as np
import pytest

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.assembly.nonlinear import assemble_internal_tangent
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.corotational_j2 import CorotationalJ2Tet4Element
from solveur.materials.solid import VonMisesElastoplasticMaterial


def _strain_tensor(voigt: np.ndarray) -> np.ndarray:
    xx, yy, zz, xy, yz, xz = np.asarray(voigt, dtype=float)
    return np.array([[xx, xy / 2.0, xz / 2.0], [xy / 2.0, yy, yz / 2.0], [xz / 2.0, yz / 2.0, zz]])


def _strain_voigt(tensor: np.ndarray) -> np.ndarray:
    return np.array([tensor[0, 0], tensor[1, 1], tensor[2, 2], 2.0 * tensor[0, 1], 2.0 * tensor[1, 2], 2.0 * tensor[0, 2]])


def _stress_voigt(tensor: np.ndarray) -> np.ndarray:
    return np.array([tensor[0, 0], tensor[1, 1], tensor[2, 2], tensor[0, 1], tensor[1, 2], tensor[0, 2]])


def _reference_j2(
    strain: np.ndarray,
    old_plastic_strain: np.ndarray,
    old_equivalent_plastic_strain: float,
    *,
    young: float,
    poisson: float,
    yield_stress: float,
    hardening: float,
    force_branch: str | None = None,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Tensor-form radial return and consistent tangent, independent of source helpers."""
    shear = young / (2.0 * (1.0 + poisson))
    bulk = young / (3.0 * (1.0 - 2.0 * poisson))
    elastic_strain = _strain_tensor(strain) - _strain_tensor(old_plastic_strain)
    trial = 2.0 * shear * (elastic_strain - np.trace(elastic_strain) * np.eye(3) / 3.0)
    trial += bulk * np.trace(elastic_strain) * np.eye(3)
    mean = np.trace(trial) / 3.0
    deviator = trial - mean * np.eye(3)
    q_trial = float(np.sqrt(1.5 * np.sum(deviator * deviator)))
    current_yield = yield_stress + hardening * old_equivalent_plastic_strain
    yield_value = q_trial - current_yield
    branch = force_branch or ("elastic" if yield_value <= 0.0 else "plastic")
    identity = np.eye(3)

    if branch == "elastic":
        stress = trial

        def tangent_action(direction: np.ndarray) -> np.ndarray:
            delta = _strain_tensor(direction)
            return 2.0 * shear * (delta - np.trace(delta) * identity / 3.0) + bulk * np.trace(delta) * identity

    else:
        assert q_trial > 0.0
        denominator = 3.0 * shear + hardening
        delta_gamma = yield_value / denominator
        updated_yield = yield_stress + hardening * (old_equivalent_plastic_strain + delta_gamma)
        radial_factor = updated_yield / q_trial
        stress = mean * identity + radial_factor * deviator
        incoming_yield = current_yield
        tangent_coefficient = 9.0 * shear**2 * incoming_yield / (denominator * q_trial**3)

        def tangent_action(direction: np.ndarray) -> np.ndarray:
            delta = _strain_tensor(direction)
            delta_deviator = delta - np.trace(delta) * identity / 3.0
            return (
                bulk * np.trace(delta) * identity
                + 2.0 * shear * radial_factor * delta_deviator
                - tangent_coefficient * np.sum(deviator * delta_deviator) * deviator
            )

    tangent = np.column_stack(
        [
            _stress_voigt(tangent_action(np.eye(6)[column]))
            for column in range(6)
        ]
    )
    return _stress_voigt(stress), tangent, branch


def test_j2_return_map_and_tangent_match_independent_tensor_oracle(tmp_path) -> None:
    young, poisson, yield_stress = 2100.0, 0.27, 3.0
    histories = (
        (np.zeros(6), 0.0),
        (np.array([0.001, -0.0004, -0.0006, 0.0003, -0.0002, 0.0001]), 0.002),
    )
    increments = (
        np.array([2e-4, 2e-4, 2e-4, 0.0, 0.0, 0.0]),
        np.array([0.012, -0.006, -0.006, 0.001, -0.0005, 0.0008]),
    )
    observations: list[tuple[float, str, float, float]] = []
    for hardening, (old_plastic, old_equivalent), increment in product((0.0, 75.0), histories, increments):
        previous = {
            "plastic_strain": old_plastic.tolist(),
            "equivalent_plastic_strain": old_equivalent,
            "plastic_dissipation": 0.0,
            "stress": [0.0] * 6,
        }
        material = VonMisesElastoplasticMaterial(
            E=young,
            nu=poisson,
            yield_stress=yield_stress,
            hardening_modulus=hardening,
        )
        strain = old_plastic + increment
        expected_stress, expected_tangent, branch = _reference_j2(
            strain,
            old_plastic,
            old_equivalent,
            young=young,
            poisson=poisson,
            yield_stress=yield_stress,
            hardening=hardening,
        )
        response = material.evaluate(strain, previous)
        assert response.diagnostics["elastic"] is (branch == "elastic")
        np.testing.assert_allclose(response.stress, expected_stress, rtol=2e-13, atol=2e-13)
        np.testing.assert_allclose(response.tangent, expected_tangent, rtol=3e-13, atol=3e-13)
        observations.append(
            (
                hardening,
                branch,
                float(np.linalg.norm(response.stress - expected_stress)),
                float(np.linalg.norm(response.tangent - expected_tangent)),
            )
        )
        assert previous["plastic_strain"] == old_plastic.tolist()
        assert previous["equivalent_plastic_strain"] == old_equivalent
    assert {row[1] for row in observations} == {"elastic", "plastic"}
    assert {row[0] for row in observations} == {0.0, 75.0}
    (tmp_path / "j2_constitutive_metrics.json").write_text(
        json.dumps(
            {
                "case_count": len(observations),
                "branch_counts": {
                    branch: sum(row[1] == branch for row in observations)
                    for branch in ("elastic", "plastic")
                },
                "max_stress_absolute_error": max(row[2] for row in observations),
                "max_tangent_absolute_frobenius_error": max(row[3] for row in observations),
                "hardening_values": sorted({row[0] for row in observations}),
                "history_count": len(histories),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_j2_yield_surface_uses_elastic_value_and_has_distinct_one_sided_tangents() -> None:
    material = VonMisesElastoplasticMaterial(E=2.0, nu=0.0, yield_stress=1.0, hardening_modulus=20.0)
    committed = material.initial_state()
    strain = np.array([0.5, 0.0, 0.0, 0.0, 0.0, 0.0])
    response = material.evaluate(strain, committed)
    assert response.trial_state["yield_function"] == 0.0
    assert response.diagnostics["elastic"] is True

    _, elastic_limit, _ = _reference_j2(
        strain,
        np.zeros(6),
        0.0,
        young=2.0,
        poisson=0.0,
        yield_stress=1.0,
        hardening=20.0,
        force_branch="elastic",
    )
    _, plastic_limit, _ = _reference_j2(
        strain,
        np.zeros(6),
        0.0,
        young=2.0,
        poisson=0.0,
        yield_stress=1.0,
        hardening=20.0,
        force_branch="plastic",
    )
    np.testing.assert_array_equal(response.tangent, elastic_limit)
    assert np.linalg.norm(elastic_limit - plastic_limit) > 0.1

    direction = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    step = 2.0**-20
    plus = material.evaluate(strain + step * direction, committed)
    minus = material.evaluate(strain - step * direction, committed)
    assert plus.diagnostics["elastic"] is False
    assert minus.diagnostics["elastic"] is True
    right_slope = (plus.stress - response.stress) / step
    left_slope = (response.stress - minus.stress) / step
    np.testing.assert_allclose(left_slope, elastic_limit @ direction, rtol=2e-6, atol=2e-6)
    np.testing.assert_allclose(right_slope, plastic_limit @ direction, rtol=2e-5, atol=2e-5)


def test_legacy_corotational_symmetrization_changes_raw_force_derivative(tmp_path) -> None:
    """Search for a raw derivative counterexample without invoking a solve."""
    nodes, _ = _mesh("TET4")
    coordinates = nodes[:4]
    material = VonMisesElastoplasticMaterial(
        E=210.0e9,
        nu=0.3,
        yield_stress=250.0e6,
        hardening_modulus=1.0e9,
    )
    element = CorotationalJ2Tet4Element(material)

    def affine_displacement(deformation: np.ndarray) -> np.ndarray:
        return (coordinates @ (deformation - np.eye(3)).T).reshape(-1)

    first = np.diag([1.016, 1.0 - 0.008, 1.0 - 0.008])
    rotation = np.array([[np.cos(0.42), -np.sin(0.42), 0.0], [np.sin(0.42), np.cos(0.42), 0.0], [0.0, 0.0, 1.0]])
    second = rotation @ np.diag([1.0136, 1.0096, 0.9768]) @ rotation.T
    _, accepted, _ = element._force_and_states(coordinates, affine_displacement(first), [material.initial_state()])
    displacement = affine_displacement(second)
    _, production_tangent, _ = element.internal_force_tangent_state(coordinates, displacement, accepted)

    step = element.tangent_step * max(1.0, float(np.max(np.abs(displacement))), float(np.max(np.abs(coordinates))))
    raw = np.empty_like(production_tangent)
    for column in range(displacement.size):
        direction = np.eye(displacement.size)[column]
        plus = element._force_and_states(coordinates, displacement + step * direction, accepted)[0]
        minus = element._force_and_states(coordinates, displacement - step * direction, accepted)[0]
        raw[:, column] = (plus - minus) / (2.0 * step)

    expected_symmetrized = 0.5 * (raw + raw.T)
    np.testing.assert_allclose(production_tangent, expected_symmetrized, rtol=2e-13, atol=2e-5)
    raw_skew = float(np.linalg.norm(raw - raw.T) / np.linalg.norm(raw))
    direction = np.random.default_rng(20261024).normal(size=displacement.size)
    direction /= np.linalg.norm(direction)
    raw_action = raw @ direction
    production_action = production_tangent @ direction
    action_gap = float(np.linalg.norm(production_action - raw_action) / np.linalg.norm(raw_action))
    (tmp_path / "legacy_corotational_metrics.json").write_text(
        json.dumps({"raw_skew_relative": raw_skew, "symmetrization_action_gap_relative": action_gap}, indent=2),
        encoding="utf-8",
    )
    print(f"E01_J2_LEGACY raw_skew_rel={raw_skew:.9e} symmetrization_action_gap_rel={action_gap:.9e}")
    assert raw_skew > 1.0e-12
    assert action_gap > 1.0e-12


def _mesh(family: str) -> tuple[np.ndarray, list[list[int]]]:
    if family == "TET4":
        nodes = np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]
        )
        return nodes, [[0, 1, 2, 3], [0, 2, 1, 4]]
    nodes = np.array([[i, j, k] for i in range(3) for j in range(2) for k in range(2)], dtype=float)

    def index(i: int, j: int, k: int) -> int:
        return 4 * i + 2 * j + k

    connectivity = []
    for i in range(2):
        connectivity.append(
            [
                index(i, 0, 0), index(i + 1, 0, 0), index(i + 1, 1, 0), index(i, 1, 0),
                index(i, 0, 1), index(i + 1, 0, 1), index(i + 1, 1, 1), index(i, 1, 1),
            ]
        )
    return nodes, connectivity


def _tet4_reference_data(coordinates: np.ndarray) -> tuple[float, np.ndarray]:
    parent_gradients = np.array([[-1.0, -1.0, -1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    jacobian = np.column_stack([coordinates[index] - coordinates[0] for index in (1, 2, 3)])
    determinant = float(np.linalg.det(jacobian))
    return determinant / 6.0, parent_gradients @ np.linalg.inv(jacobian)


_HEX_SIGNS = np.array(
    [[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]],
    dtype=float,
)


def _hex8_reference_data(coordinates: np.ndarray) -> list[tuple[float, np.ndarray]]:
    coordinate = 1.0 / np.sqrt(3.0)
    result = []
    for xi, eta, zeta in product((-coordinate, coordinate), repeat=3):
        point = np.array([xi, eta, zeta])
        derivatives = np.column_stack(
            [
                _HEX_SIGNS[:, axis]
                * np.prod(1.0 + _HEX_SIGNS[:, np.arange(3) != axis] * point[np.arange(3) != axis], axis=1)
                / 8.0
                for axis in range(3)
            ]
        )
        jacobian = coordinates.T @ derivatives
        determinant = float(np.linalg.det(jacobian))
        result.append((determinant, derivatives @ np.linalg.inv(jacobian)))
    return result


def _reference_tl_global(
    family: str,
    nodes: np.ndarray,
    connectivity: list[list[int]],
    displacement: np.ndarray,
    *,
    young: float,
    poisson: float,
    yield_stress: float,
    hardening: float,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    force = np.zeros(displacement.size)
    tangent = np.zeros((displacement.size, displacement.size))
    branches: list[str] = []
    for element_nodes in connectivity:
        coordinates = nodes[element_nodes]
        local_u = displacement.reshape(-1, 3)[element_nodes]
        if family == "TET4":
            data = [_tet4_reference_data(coordinates)]
        else:
            data = _hex8_reference_data(coordinates)
        local_force = np.zeros(3 * len(element_nodes))
        local_tangent = np.zeros((local_force.size, local_force.size))
        for measure, gradients in data:
            deformation = np.eye(3) + local_u.T @ gradients
            green = 0.5 * (deformation.T @ deformation - np.eye(3))
            stress, material_tangent, branch = _reference_j2(
                _strain_voigt(green),
                np.zeros(6),
                0.0,
                young=young,
                poisson=poisson,
                yield_stress=yield_stress,
                hardening=hardening,
            )
            second = np.array(
                [[stress[0], stress[3], stress[5]], [stress[3], stress[1], stress[4]], [stress[5], stress[4], stress[2]]]
            )
            first = deformation @ second
            local_force += measure * (first @ gradients.T).T.reshape(-1)
            branches.append(branch)
            for node_b, gradient_b in enumerate(gradients):
                for component in range(3):
                    delta_deformation = np.zeros((3, 3))
                    delta_deformation[component, :] = gradient_b
                    delta_green = 0.5 * (deformation.T @ delta_deformation + delta_deformation.T @ deformation)
                    delta_stress_voigt = material_tangent @ _strain_voigt(delta_green)
                    delta_second = np.array(
                        [
                            [delta_stress_voigt[0], delta_stress_voigt[3], delta_stress_voigt[5]],
                            [delta_stress_voigt[3], delta_stress_voigt[1], delta_stress_voigt[4]],
                            [delta_stress_voigt[5], delta_stress_voigt[4], delta_stress_voigt[2]],
                        ]
                    )
                    delta_first = delta_deformation @ second + deformation @ delta_second
                    column = 3 * node_b + component
                    local_tangent[:, column] += measure * (delta_first @ gradients.T).T.reshape(-1)
        global_dofs = np.array([3 * node + component for node in element_nodes for component in range(3)])
        force[global_dofs] += local_force
        tangent[np.ix_(global_dofs, global_dofs)] += local_tangent
    return force, tangent, branches


@pytest.mark.parametrize(
    ("family", "hardening", "branch"),
    [
        ("TET4", 0.0, "plastic"),
        ("TET4", 10.0, "plastic"),
        ("HEX8", 0.0, "plastic"),
        ("HEX8", 10.0, "plastic"),
        ("TET4", 0.0, "elastic"),
        ("TET4", 10.0, "elastic"),
        ("HEX8", 0.0, "elastic"),
        ("HEX8", 10.0, "elastic"),
    ],
)
def test_j2_total_lagrangian_global_full_dof_assembly_matches_tensor_reference(
    family: str,
    hardening: float,
    branch: str,
    tmp_path,
) -> None:
    nodes, connectivity = _mesh(family)
    young, poisson = 1000.0, 0.25
    yield_stress = 0.02 if branch == "plastic" else 0.2
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": element_nodes, "material": "j2"} for element_nodes in connectivity],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": young,
                "nu": poisson,
                "yield_stress": yield_stress,
                "hardening_modulus": hardening,
            }
        },
        fixed_dofs=[],
        loads=[],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 1, "max_iterations": 2, "tolerance": 1e-9},
    )
    model.analysis = replace(
        model.analysis,
        parameters={**model.analysis.parameters, "kinematics": "total_lagrangian_j2"},
    )
    dofs = model.dof_manager()
    displacement_scale = 1.0 if branch == "plastic" else 4.0e-4
    displacement_gradient = displacement_scale * np.array(
        [[0.025, 0.006, 0.0], [-0.003, -0.010, 0.004], [0.002, 0.0, 0.015]]
    )
    displacement = (nodes @ displacement_gradient.T).reshape(-1)
    point_count = 1 if family == "TET4" else 8
    initial_state = VonMisesElastoplasticMaterial(
        E=young,
        nu=poisson,
        yield_stress=yield_stress,
        hardening_modulus=hardening,
    ).initial_state()
    fixed_history = {
        index: [dict(initial_state) for _ in range(point_count)]
        for index in range(len(connectivity))
    }

    production_force, production_tangent, _ = assemble_internal_tangent(model, dofs, displacement, fixed_history)
    reference_force, reference_tangent, branches = _reference_tl_global(
        family,
        nodes,
        connectivity,
        displacement,
        young=young,
        poisson=poisson,
        yield_stress=yield_stress,
        hardening=hardening,
    )
    assert dofs.ndof == 3 * len(nodes)
    assert set(branches) == {branch}
    production_tangent_dense = production_tangent.toarray()
    force_error = float(np.linalg.norm(production_force - reference_force) / np.linalg.norm(reference_force))
    tangent_error = float(np.linalg.norm(production_tangent_dense - reference_tangent) / np.linalg.norm(reference_tangent))
    print(
        "E01_J2_GLOBAL_METRICS "
        f"family={family} H={hardening:g} branch={branch} free_dofs={dofs.ndof} "
        f"force_rel={force_error:.9e} tangent_rel={tangent_error:.9e}"
    )
    np.testing.assert_allclose(production_force, reference_force, rtol=3e-12, atol=3e-12)
    np.testing.assert_allclose(production_tangent_dense, reference_tangent, rtol=4e-12, atol=4e-12)

    # Check the independent full-DOF matrix by centered differences over a
    # step sweep. This is a numerical cross-check, not the proof oracle.
    steps = (1e-4, 3e-5, 1e-5, 3e-6)
    sweep_errors = []
    branch_switches_by_step = []
    for step in steps:
        fd = np.empty_like(reference_tangent)
        branch_switches = 0
        for column in range(dofs.ndof):
            direction = np.zeros(dofs.ndof)
            direction[column] = 1.0
            plus, _, plus_branches = _reference_tl_global(
                family, nodes, connectivity, displacement + step * direction,
                young=young, poisson=poisson, yield_stress=yield_stress, hardening=hardening,
            )
            minus, _, minus_branches = _reference_tl_global(
                family, nodes, connectivity, displacement - step * direction,
                young=young, poisson=poisson, yield_stress=yield_stress, hardening=hardening,
            )
            branch_switches += sum(item != branch for item in plus_branches)
            branch_switches += sum(item != branch for item in minus_branches)
            fd[:, column] = (plus - minus) / (2.0 * step)
        error = float(np.linalg.norm(fd - reference_tangent) / np.linalg.norm(reference_tangent))
        sweep_errors.append(error)
        branch_switches_by_step.append(branch_switches)
        print(
            f"E01_J2_GLOBAL_FD family={family} H={hardening:g} h={step:.1e} "
            f"rel={error:.9e} branch_switches={branch_switches}"
        )
    (tmp_path / f"tl_j2_metrics_{family.lower()}_h{hardening:g}_{branch}.json").write_text(
        json.dumps(
            {
                "family": family,
                "hardening": hardening,
                "branch": branch,
                "free_dofs": dofs.ndof,
                "branches": branches,
                "force_relative_error": force_error,
                "tangent_relative_error": tangent_error,
                "finite_difference_steps": list(steps),
                "finite_difference_relative_errors": sweep_errors,
                "finite_difference_branch_switch_counts": branch_switches_by_step,
                "minimum_fd_relative_error": min(sweep_errors),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # The sweep is diagnostic only. It may cross branch boundaries and is not
    # used as a pass criterion or as a proof of the derivative identity.


def test_j2_dirichlet_reduction_preserves_the_free_dof_tangent_action(tmp_path) -> None:
    nodes, connectivity = _mesh("TET4")
    young, poisson, yield_stress, hardening = 1000.0, 0.25, 0.02, 10.0
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": element_nodes, "material": "j2"} for element_nodes in connectivity],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": young,
                "nu": poisson,
                "yield_stress": yield_stress,
                "hardening_modulus": hardening,
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY"]}],
        loads=[],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 1},
    )
    model.analysis = replace(model.analysis, parameters={**model.analysis.parameters, "kinematics": "total_lagrangian_j2"})
    dofs = model.dof_manager()
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    displacement_gradient = np.array([[0.025, 0.006, 0.0], [-0.003, -0.010, 0.004], [0.002, 0.0, 0.015]])
    displacement = (nodes @ displacement_gradient.T).reshape(-1)
    initial = VonMisesElastoplasticMaterial(
        E=young, nu=poisson, yield_stress=yield_stress, hardening_modulus=hardening
    ).initial_state()
    history = {index: [dict(initial)] for index in range(len(connectivity))}
    production_force, production_tangent, _ = assemble_internal_tangent(model, dofs, displacement, history)
    reference_force, reference_tangent, branches = _reference_tl_global(
        "TET4", nodes, connectivity, displacement,
        young=young, poisson=poisson, yield_stress=yield_stress, hardening=hardening,
    )
    assert fixed.tolist() == [0, 1]
    assert free.size == dofs.ndof - fixed.size
    assert set(branches) == {"plastic"}
    tangent_free = production_tangent.toarray()[np.ix_(free, free)]
    reference_free = reference_tangent[np.ix_(free, free)]
    force_error = float(np.linalg.norm(production_force[free] - reference_force[free]) / np.linalg.norm(reference_force[free]))
    tangent_error = float(np.linalg.norm(tangent_free - reference_free) / np.linalg.norm(reference_free))
    (tmp_path / "dirichlet_reduction_metrics.json").write_text(
        json.dumps({"full_dofs": dofs.ndof, "fixed_dofs": fixed.tolist(), "free_dofs": int(free.size), "force_relative_error": force_error, "tangent_relative_error": tangent_error}, indent=2),
        encoding="utf-8",
    )
    np.testing.assert_allclose(production_force[free], reference_force[free], rtol=3e-12, atol=3e-12)
    np.testing.assert_allclose(tangent_free, reference_free, rtol=4e-12, atol=4e-12)
