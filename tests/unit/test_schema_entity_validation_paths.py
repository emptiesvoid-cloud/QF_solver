from __future__ import annotations

import numpy as np

from solveur.io.contact_schema import ContactSchemaValidator
from solveur.io.constraint_schema import ConstraintSchemaValidator
from solveur.io.discrete_schema import DiscreteEntitySchemaValidator
from solveur.io.laminate_schema import validate_laminate_plies
from solveur.io.load_schema import DistributedLoadSchemaValidator


def test_mpc_and_rbe_schema_accept_valid_ordered_links() -> None:
    errors: list[str] = []
    validator = ConstraintSchemaValidator()
    validator.validate(
        [{"name": "tie", "terms": [{"node": 0, "dof": "UX", "coefficient": 1.0}, {"node": 1, "dof": "UX", "coefficient": -1.0}, {"node": 2, "dof": "UY", "coefficient": 0.5}]}],
        3,
        errors,
    )
    validator.validate_rbes(
        [{"master": 0, "slaves": [1, 2], "tie_rotations": True, "name": "r2"}],
        [{"reference": 0, "independents": [{"node": 1, "weight": 0.5}, {"node": 2, "weight": 0.5}], "mode": "weighted", "dofs": ["UX", "UY"]}],
        3,
        errors,
    )
    assert errors == []


def test_mpc_and_rbe_schema_reject_invalid_links() -> None:
    errors: list[str] = []
    validator = ConstraintSchemaValidator()
    validator.validate(["bad", {"terms": [{"node": 0, "dof": "BAD", "coefficient": 0.0}]}], 2, errors)
    validator.validate_rbes(
        [
            {"master": 9, "slaves": [0, 0, 9], "tie_rotations": "yes", "name": 2, "extra": 1},
            {"master": 0, "slaves": []},
        ],
        [
                {"reference": 9, "independents": [{"node": 0, "weight": 0.0}, {"node": 0, "weight": "bad"}], "mode": "bad", "dofs": ["BAD"]},
                {"reference": 0, "independents": ["bad"]},
                {"reference": 0, "independents": [{"node": 1, "weight": 0.0}], "mode": "rigid_body_projection"},
        ],
        2,
        errors,
    )
    assert any("must not contain duplicates" in error for error in errors)
    assert any("must reference an existing node" in error for error in errors)
    assert any("valid DOF" in error for error in errors)
    assert any("must be strictly positive" in error for error in errors)


def test_discrete_schema_accepts_scalar_vector_matrix_and_local_entities() -> None:
    errors: list[str] = []
    DiscreteEntitySchemaValidator().validate(
        [
            {"node_a": 0, "node_b": 1, "dofs": ["UX"], "stiffness": 10.0},
            {"node_a": 1, "dofs": ["UX", "UY"], "stiffness": [10.0, 20.0], "coordinate_system": "local", "orientation": np.eye(3).tolist()},
            {"node_a": 2, "dofs": ["UX", "UY"], "stiffness_matrix": [[10.0, 1.0], [1.0, 20.0]]},
        ],
        [{"node": 0, "mass": 2.0, "center_of_mass": [0.0, 0.0, 0.0], "inertia": np.eye(3).tolist()}],
        3,
        errors,
    )
    assert errors == []


def test_discrete_schema_rejects_nonphysical_springs_masses_and_inertia() -> None:
    errors: list[str] = []
    DiscreteEntitySchemaValidator().validate(
        [
            {"node_a": 0, "node_b": 0, "dofs": ["UX", "UX"], "stiffness": -1.0, "stiffness_matrix": [[1.0, 0.0], [0.0, 1.0]]},
            {"node_a": 9, "dofs": ["BAD"], "stiffness_matrix": [[1.0, 2.0], [0.0, 1.0]], "orientation": np.diag([1.0, 1.0, -1.0]).tolist(), "coordinate_system": "local"},
            {"node_a": 1, "dofs": ["UX"], "stiffness": -1.0},
        ],
        [{"node": 9, "mass": 0.0, "center_of_mass": [0.0], "inertia": [[1.0, 2.0], [2.0, 1.0]]}],
        2,
        errors,
    )
    assert any("exactly one" in error for error in errors)
    assert any("must not contain duplicates" in error for error in errors)
    assert any("positive semidefinite" in error for error in errors)
    assert any("strictly positive" in error for error in errors)
    assert any("existing node" in error for error in errors)


def test_distributed_load_schema_covers_supported_topologies() -> None:
    elements = [
        {"type": "TET4"},
        {"type": "MITC4"},
        {"type": "BEAM2"},
    ]
    errors: list[str] = []
    DistributedLoadSchemaValidator().validate(
        [
            {"type": "gravity", "acceleration": [0.0, 0.0, -9.81]},
            {"type": "body_force", "value": [1.0, 0.0, 0.0], "elements": [0], "coordinate_system": "local"},
            {"type": "pressure", "element": 0, "face": 3, "value": 2.0},
            {"type": "surface_traction", "element": 1, "value": [1.0, 0.0, 0.0]},
            {"type": "edge_traction", "element": 1, "edge": 2, "value": [1.0, 0.0, 0.0]},
            {"type": "line_load", "element": 2, "value": [1.0, 0.0, 0.0]},
        ],
        elements,
        errors,
    )
    assert errors == []


def test_distributed_load_schema_rejects_invalid_targets_faces_and_followers() -> None:
    elements = [{"type": "TET4"}, {"type": "MITC3"}, {"type": "BEAM2"}]
    errors: list[str] = []
    DistributedLoadSchemaValidator().validate(
        [
            {"type": "unknown"},
            {"type": "gravity", "acceleration": [0.0], "elements": [9]},
            {"type": "pressure", "element": 0, "face": 9, "value": "bad"},
            {"type": "surface_traction", "element": 1, "face": 1, "value": [1.0, 0.0], "follower": True},
            {"type": "edge_traction", "element": 0, "edge": 9, "value": [1.0, 0.0, 0.0]},
            {"type": "line_load", "element": 1, "value": [1.0, 0.0, 0.0]},
        ],
        elements,
        errors,
    )
    assert any("unsupported" in error for error in errors)
    assert any("face" in error for error in errors)
    assert any("follower=true" in error for error in errors)
    assert any("shell elements only" in error for error in errors)
    assert any("BEAM2 only" in error for error in errors)


def test_contact_schema_covers_node_face_friction_and_type_errors() -> None:
    validator = ContactSchemaValidator()
    errors: list[str] = []
    validator.validate(
        [
            {
                "slave_node": 0,
                "master_nodes": [1, 2, 3],
                "gap_tolerance": 1.0e-8,
                "friction_coefficient": 0.2,
                "tangential_stiffness": 100.0,
            },
            {
                "slave_node": 0,
                "master_faces": [[1, 2, 3], [1, 2, 3]],
                "friction_coefficient": 0.0,
                "tangential_stiffness": 10.0,
            },
        ],
        4,
        errors,
    )
    assert any("duplicates" in error for error in errors)

    invalid: list[str] = []
    validator.validate(
        [
            "bad",
            {"slave_node": 9, "master_nodes": [0, 1], "master_faces": [], "friction_coefficient": -1.0},
            {"slave_node": 0, "master_faces": [[0, 1, "bad"]], "gap_tolerance": 0.0, "friction_coefficient": 1.0},
        ],
        3,
        invalid,
    )
    assert any("must be an object" in error for error in invalid)
    assert any("exactly one" in error for error in invalid)
    assert any("positive finite" in error for error in invalid)
    assert any("existing node" in error for error in invalid)


def test_laminate_schema_covers_strength_and_strain_allowable_contracts() -> None:
    valid = {
        "E1": 10.0,
        "E2": 8.0,
        "nu12": 0.2,
        "G12": 3.0,
        "G13": 3.0,
        "G23": 3.0,
        "thickness": 0.01,
        "angle_deg": 45.0,
        "strengths": {"Xt": 1.0, "Xc": 1.0, "Yt": 1.0, "Yc": 1.0, "S12": 1.0, "f12_star": 0.2},
        "strain_allowables": {"e1t": 0.01, "e1c": 0.01, "e2t": 0.01, "e2c": 0.01, "g12": 0.01},
    }
    errors: list[str] = []
    validate_laminate_plies("materials.laminate", [valid], errors)
    assert errors == []

    invalid: list[str] = []
    validate_laminate_plies(
        "materials.laminate",
        [{**valid, "E1": 0.0, "thickness": -1.0, "strengths": {"Xt": -1.0, "f12_star": 1.0}, "strain_allowables": {"e1t": 0.0}}],
        invalid,
    )
    assert any("must be positive" in error for error in invalid)
    assert any("is required" in error for error in invalid)
