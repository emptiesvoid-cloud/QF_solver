"""Algebraic contract tests for WP-C01-R13's bounded experimental transfer."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact.entities import FrictionlessContact
from solveur.contact.evaluation import contact_configuration_payload
from solveur.contact.support import (
    LEGACY_TANGENTIAL_TRANSFER,
    SMALL_ROTATION_TANGENTIAL_TRANSFER,
    _contact_tangential_transfer_mode,
    _details,
    _friction_system,
    _friction_update,
    _operator as _build_operator,
    _tangential_contact_force,
)
from solveur.contact.solver import _contact_operators
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.solvers.static import _apply_contact_moment_transport
from solveur.io.json_reader import JsonModelReader
from solveur.mesh.contact_validation import frictionless_contact_errors


NODES = np.array(
    [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.25, 0.30, 0.20],
    ],
    dtype=float,
)
MASTER = (0, 1, 2)
SLAVE = 3
MU = 0.5
KT = 1000.0


def _dofs() -> DofManager:
    return DofManager.from_node_requirements(
        {node: {"UX", "UY", "UZ"} for node in range(len(NODES))}
    )


def _contact() -> FrictionlessContact:
    return FrictionlessContact(
        slave_node=SLAVE,
        master_nodes=MASTER,
        name="r13_pair",
        friction_coefficient=MU,
        tangential_stiffness=KT,
    )


def _operator(mode: str | None = None):
    options = {} if mode is None else {"tangential_transfer_mode": mode}
    return _build_operator(_contact(), NODES, _dofs(), **options)


def _independent_triangle_gradients(points: np.ndarray) -> np.ndarray:
    edge_one = points[1] - points[0]
    edge_two = points[2] - points[0]
    cross = np.cross(edge_one, edge_two)
    area_twice = float(np.linalg.norm(cross))
    normal = cross / area_twice
    gradient_one = np.cross(edge_two, normal) / area_twice
    gradient_two = np.cross(normal, edge_one) / area_twice
    return np.array((-gradient_one - gradient_two, gradient_one, gradient_two))


def _nodal_forces(
    operator,
    local_force: np.ndarray,
) -> np.ndarray:
    generalized = _tangential_contact_force([operator], np.asarray([local_force]), operator.vector.size)
    dofs = _dofs()
    result = np.zeros((4, 3), dtype=float)
    for node in range(4):
        for axis, name in enumerate(("UX", "UY", "UZ")):
            result[node, axis] = generalized[dofs.index(node, name)]
    return result


def _resultant(forces: np.ndarray) -> np.ndarray:
    return np.sum(forces, axis=0)


def _moment(points: np.ndarray, forces: np.ndarray, origin: np.ndarray | None = None) -> np.ndarray:
    center = np.zeros(3) if origin is None else np.asarray(origin, dtype=float)
    return np.sum(np.cross(points - center, forces), axis=0)


def _rigid_increment(dofs: DofManager, omega: np.ndarray, translation: np.ndarray) -> np.ndarray:
    values = np.zeros(dofs.ndof, dtype=float)
    for node, point in enumerate(NODES):
        increment = translation + np.cross(omega, point)
        for component, name in enumerate(("UX", "UY", "UZ")):
            values[dofs.index(node, name)] = increment[component]
    return values


def _model_data(parameters: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "parameters": parameters or {}},
        "nodes": NODES.tolist(),
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)
        ],
        "springs": [{"node_a": SLAVE, "dofs": ["UZ"], "stiffness": 1.0}],
        "contacts": [
            {
                "name": "r13_pair",
                "slave_node": SLAVE,
                "master_nodes": list(MASTER),
                "friction_coefficient": MU,
                "tangential_stiffness": KT,
            }
        ],
    }


def _read_model(parameters: dict[str, object] | None = None) -> FiniteElementModel:
    return JsonModelReader().from_dict(_model_data(parameters))


def test_default_and_explicit_legacy_are_identical() -> None:
    implicit = _operator()
    explicit = _operator(LEGACY_TANGENTIAL_TRANSFER)

    assert implicit.tangential_transfer_mode == LEGACY_TANGENTIAL_TRANSFER
    assert explicit.tangential_transfer_mode == LEGACY_TANGENTIAL_TRANSFER
    np.testing.assert_array_equal(implicit.tangential_vectors, explicit.tangential_vectors)

    legacy_details = _details([implicit], np.array([implicit.initial_gap]), np.zeros(1), (), [])
    assert "tangential_transfer_mode" not in legacy_details
    assert "tangential_transfer_mode" not in legacy_details["contacts"][0]

    experimental = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    experimental_details = _details(
        [experimental], np.array([experimental.initial_gap]), np.zeros(1), (), []
    )
    assert experimental_details["tangential_transfer_mode"] == SMALL_ROTATION_TANGENTIAL_TRANSFER
    assert experimental_details["contacts"][0]["tangential_transfer_mode"] == (
        SMALL_ROTATION_TANGENTIAL_TRANSFER
    )


def test_bstar_matches_independent_virtual_work_and_force_formula() -> None:
    operator = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    dofs = _dofs()
    rows = np.vstack(operator.tangential_vectors)
    legacy = np.vstack(_operator(LEGACY_TANGENTIAL_TRANSFER).tangential_vectors)
    gradients = _independent_triangle_gradients(NODES[list(MASTER)])
    expected = legacy.copy()
    for local_node, node in enumerate(MASTER):
        coefficient = operator.initial_gap * (operator.tangents[0] @ gradients[local_node])
        coefficient_two = operator.initial_gap * (operator.tangents[1] @ gradients[local_node])
        for axis, name in enumerate(("UX", "UY", "UZ")):
            expected[0, dofs.index(node, name)] += coefficient * operator.normal[axis]
            expected[1, dofs.index(node, name)] += coefficient_two * operator.normal[axis]
    np.testing.assert_allclose(rows, expected, rtol=0.0, atol=2.0e-15)

    local_force = np.array([3.0, -4.0])
    world_force = local_force[0] * operator.tangents[0] + local_force[1] * operator.tangents[1]
    actual = _nodal_forces(operator, local_force)
    expected_forces = np.zeros((4, 3), dtype=float)
    expected_forces[SLAVE] = world_force
    for local_node, node in enumerate(MASTER):
        expected_forces[node] = (
            -operator.master_barycentric[local_node] * world_force
            + operator.initial_gap
            * float(gradients[local_node] @ world_force)
            * operator.normal
        )
    np.testing.assert_allclose(actual, expected_forces, rtol=0.0, atol=2.0e-14)
    virtual = np.linspace(-0.3, 0.8, dofs.ndof)
    lhs = float(local_force @ (rows @ virtual))
    rhs = float(np.sum(_tangential_contact_force([operator], np.asarray([local_force]), dofs.ndof) * virtual))
    assert lhs == pytest.approx(rhs, abs=2.0e-14)


def test_bstar_transfer_conserves_force_moment_and_is_rigid_motion_objective() -> None:
    operator = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    local_force = np.array([3.0, 4.0])
    generalized = _nodal_forces(operator, local_force)
    np.testing.assert_allclose(_resultant(generalized), np.zeros(3), atol=2.0e-14)
    np.testing.assert_allclose(_moment(NODES, generalized), np.zeros(3), atol=2.0e-14)

    for omega in (
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
        np.array([1.0, -2.0, 3.0]),
    ):
        rigid = _rigid_increment(_dofs(), omega, np.array([0.4, -0.2, 0.7]))
        assert abs(float(np.vstack(operator.tangential_vectors) @ rigid @ local_force)) < 2.0e-14

    legacy = _operator(LEGACY_TANGENTIAL_TRANSFER)
    legacy_forces = _nodal_forces(legacy, local_force)
    expected_gap_couple = operator.initial_gap * np.cross(
        operator.normal,
        local_force[0] * operator.tangents[0] + local_force[1] * operator.tangents[1],
    )
    np.testing.assert_allclose(_moment(NODES, legacy_forces), expected_gap_couple, atol=2.0e-14)

    shifted_origin = np.array([0.3, -0.7, 1.2])
    np.testing.assert_allclose(
        _moment(NODES, generalized, shifted_origin),
        _moment(NODES, generalized) - np.cross(shifted_origin, _resultant(generalized)),
        atol=2.0e-14,
    )


def test_zero_reference_gap_reduces_exactly_to_legacy_transfer() -> None:
    nodes = NODES.copy()
    nodes[SLAVE] -= np.array([0.0, 0.0, 0.20])
    legacy = _build_operator(_contact(), nodes, _dofs(), tangential_transfer_mode="legacy")
    experimental = _build_operator(
        _contact(), nodes, _dofs(), tangential_transfer_mode=SMALL_ROTATION_TANGENTIAL_TRANSFER
    )
    np.testing.assert_array_equal(legacy.tangential_vectors, experimental.tangential_vectors)


def test_stick_tangent_and_assembled_force_are_the_same_bstar_operator() -> None:
    operator = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    size = operator.vector.size
    matrix, loads = _friction_system(
        csr_matrix((size, size)),
        np.zeros(size),
        [operator],
        (0,),
        ("stick",),
        np.zeros((1, 2)),
        np.zeros((1, 2)),
    )
    basis = np.vstack(operator.tangential_vectors)
    expected = KT * basis.T @ basis
    np.testing.assert_allclose(matrix.toarray(), expected, rtol=1.0e-13, atol=1.0e-13)
    np.testing.assert_array_equal(loads, np.zeros(size))

    pressure = np.array([100.0])
    zero_reference = np.zeros((1, 2))

    def assembled_force(displacement: np.ndarray) -> np.ndarray:
        states, local, _, _ = _friction_update(
            [operator], (0,), displacement, pressure, zero_reference, ("stick",)
        )
        assert states == ("stick",)
        return _tangential_contact_force([operator], local, size)

    step = 1.0e-7
    for column in range(size):
        plus, minus = np.zeros(size), np.zeros(size)
        plus[column] += step
        minus[column] -= step
        numerical = (assembled_force(plus) - assembled_force(minus)) / (2.0 * step)
        np.testing.assert_allclose(numerical, expected[:, column], rtol=2.0e-8, atol=2.0e-8)


def test_slip_force_uses_same_mapping_and_existing_branch_transition() -> None:
    operator = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    size = operator.vector.size
    dofs = _dofs()
    displacement = np.zeros(size)
    displacement[dofs.index(SLAVE, "UX")] = 0.01
    pressure = np.array([10.0])
    references = np.zeros((1, 2))
    states, local_force, _, slip_reference = _friction_update(
        [operator], (0,), displacement, pressure, references, ("stick",)
    )
    assert states == ("slip",)
    assert np.linalg.norm(local_force[0]) == pytest.approx(MU * pressure[0])
    generalized = _tangential_contact_force([operator], local_force, size)
    np.testing.assert_allclose(generalized, np.vstack(operator.tangential_vectors).T @ local_force[0])

    retained, retained_force, _, retained_reference = _friction_update(
        [operator], (0,), displacement, pressure, slip_reference, ("slip",)
    )
    assert retained == ("slip",)
    np.testing.assert_allclose(retained_force, local_force, atol=2.0e-14)
    np.testing.assert_allclose(retained_reference, slip_reference, atol=2.0e-14)

    unloading = np.zeros(size)
    unloading[dofs.index(SLAVE, "UX")] = 0.0008
    returned, _, _, _ = _friction_update(
        [operator], (0,), unloading, pressure, slip_reference, ("slip",)
    )
    assert returned == ("stick",)


def test_open_and_zero_capacity_pairs_have_no_tangential_transfer() -> None:
    operator = _operator(SMALL_ROTATION_TANGENTIAL_TRANSFER)
    size = operator.vector.size
    displacement = np.linspace(-1.0e-3, 1.0e-3, size)

    open_state, open_force, _, _ = _friction_update(
        [operator], (), displacement, np.array([0.0]), np.zeros((1, 2)), ("open",)
    )
    assert open_state == ("open",)
    np.testing.assert_array_equal(open_force, np.zeros((1, 2)))
    np.testing.assert_array_equal(
        _tangential_contact_force([operator], open_force, size), np.zeros(size)
    )

    no_friction = FrictionlessContact(
        slave_node=SLAVE,
        master_nodes=MASTER,
        name="r13_zero_capacity",
        friction_coefficient=0.0,
        tangential_stiffness=KT,
    )
    frictionless_operator = _build_operator(
        no_friction,
        NODES,
        _dofs(),
        tangential_transfer_mode=SMALL_ROTATION_TANGENTIAL_TRANSFER,
    )
    zero_state, zero_force, _, _ = _friction_update(
        [frictionless_operator],
        (0,),
        displacement,
        np.array([100.0]),
        np.zeros((1, 2)),
        ("stick",),
    )
    assert zero_state == ("frictionless",)
    np.testing.assert_array_equal(zero_force, np.zeros((1, 2)))
    np.testing.assert_array_equal(
        _tangential_contact_force([frictionless_operator], zero_force, size), np.zeros(size)
    )


def test_experimental_mode_skips_postprocessed_moment_correction() -> None:
    raw = np.array([0.0, -0.003, -0.13])
    equilibrium: dict[str, object] = {"moment_imbalance_about_origin": raw.tolist()}
    _apply_contact_moment_transport(
        equilibrium,
        {"tangential_transfer_mode": SMALL_ROTATION_TANGENTIAL_TRANSFER, "contacts": []},
        moment_scale=1.0,
    )
    np.testing.assert_array_equal(equilibrium["moment_imbalance_about_origin"], raw)
    np.testing.assert_array_equal(equilibrium["raw_moment_imbalance_about_origin"], raw)
    np.testing.assert_array_equal(equilibrium["contact_reference_moment_correction"], np.zeros(3))
    assert equilibrium["moment_transport_status"] == "ASSEMBLED_WORK_CONJUGATE_TRANSFER"


def test_mode_validation_is_opt_in_and_excludes_updated_or_finite_sliding_routes() -> None:
    model = _read_model({"contact_tangential_transfer": SMALL_ROTATION_TANGENTIAL_TRANSFER})
    assert _contact_tangential_transfer_mode(model) == SMALL_ROTATION_TANGENTIAL_TRANSFER
    assert frictionless_contact_errors(model) == []
    operators = _contact_operators(model, model.contacts, model.dof_manager())
    assert operators[0].tangential_transfer_mode == SMALL_ROTATION_TANGENTIAL_TRANSFER
    with pytest.raises(InputValidationError, match="displaced reference"):
        _contact_operators(
            model,
            model.contacts,
            model.dof_manager(),
            np.zeros(model.dof_manager().ndof),
        )

    model.analysis.parameters["contact_search_mode"] = "updated"
    assert any("frozen initial contact projection" in error for error in frictionless_contact_errors(model))
    with pytest.raises(InputValidationError, match="frozen initial contact projection"):
        _contact_operators(model, model.contacts, model.dof_manager())

    model.analysis.parameters["contact_search_mode"] = "initial"
    model.analysis.parameters["contact_finite_sliding"] = True
    assert any("does not support finite sliding" in error for error in frictionless_contact_errors(model))

    model.analysis.parameters["contact_tangential_transfer"] = "unknown"
    with pytest.raises(InputValidationError, match="contact_tangential_transfer"):
        _contact_tangential_transfer_mode(model)
    assert any("contact_tangential_transfer" in error for error in frictionless_contact_errors(model))

    model = _read_model({"contact_tangential_transfer": SMALL_ROTATION_TANGENTIAL_TRANSFER})
    model.contacts.append(_contact())
    assert any("one frozen slave-master pair" in error for error in frictionless_contact_errors(model))


def test_restart_configuration_binds_experimental_transfer_without_changing_legacy_payload() -> None:
    legacy = _read_model()
    experimental = _read_model({"contact_tangential_transfer": SMALL_ROTATION_TANGENTIAL_TRANSFER})
    legacy_payload = contact_configuration_payload(legacy, penalty=1.0)
    experimental_payload = contact_configuration_payload(experimental, penalty=1.0)

    assert "contact_tangential_transfer" not in legacy_payload["parameters"]
    assert experimental_payload["parameters"]["contact_tangential_transfer"] == (
        SMALL_ROTATION_TANGENTIAL_TRANSFER
    )


def test_slave_patch_is_rejected_by_the_single_pair_experiment_contract() -> None:
    model = _read_model({"contact_tangential_transfer": SMALL_ROTATION_TANGENTIAL_TRANSFER})
    model.contacts[0] = FrictionlessContact(
        slave_node=SLAVE,
        master_nodes=MASTER,
        name="r13_patch",
        friction_coefficient=MU,
        tangential_stiffness=KT,
        slave_patch_nodes=(SLAVE,),
    )
    model.analysis.parameters["contact_tangential_transfer"] = SMALL_ROTATION_TANGENTIAL_TRANSFER
    errors = frictionless_contact_errors(model)

    assert any("small_rotation_work_conjugate" in error for error in errors)
    with pytest.raises(InputValidationError, match="one slave node and one reference master triangle"):
        _contact_operators(
            model,
            list(model.contacts[0].expanded_slave_contacts()),
            model.dof_manager(),
        )
