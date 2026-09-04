"""Contracts for the bounded finite-sliding penalty contact option."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.contact.entities import FrictionlessContact
from solveur.contact.solver import assemble_penalty_contact
from solveur.api import solve_model
from solveur.compatibility.preflight import CompatibilityError
from solveur.core.errors import InputValidationError
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import model_to_dict
from solveur.verification.robustness_nonlinear_solids import (
    run_contact_facet_transition_rollback_benchmark,
    run_contact_finite_sliding_benchmark,
    run_contact_surface_patch_benchmark,
    run_contact_three_facet_sliding_benchmark,
)


def _outside_triangle_model():
    return JsonModelReader().from_dict(
        {
            "analysis": {
                "type": "nonlinear_static",
                "method": "newton_raphson",
                "contact_mode": "penalty",
                "contact_search_mode": "updated",
                "contact_finite_sliding": True,
            },
            "nodes": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.2, 0.2, -0.1],
            ],
            "elements": [],
            "materials": {},
            "fixed_dofs": [],
            "loads": [],
            "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
            "contacts": [{"slave_node": 3, "master_nodes": [0, 1, 2]}],
        }
    )


def test_clamped_projection_is_opt_in() -> None:
    nodes = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.2, 0.2, -0.1]],
        dtype=float,
    )
    contact = FrictionlessContact(slave_node=3, master_nodes=(0, 1, 2))

    with pytest.raises(InputValidationError, match="outside the compatible"):
        contact.face_geometry(nodes)

    geometry = contact.face_geometry(nodes, allow_clamped_projection=True)
    assert geometry.projection_clamped is True
    assert geometry.gap == pytest.approx(-0.1)
    assert np.sum(geometry.barycentric) == pytest.approx(1.0)
    assert np.all(geometry.barycentric >= -1.0e-12)


def test_common_penalty_records_bounded_finite_sliding_projection() -> None:
    model = _outside_triangle_model()
    dofs = model.dof_manager()
    internal, tangent, details = assemble_penalty_contact(
        model, dofs, np.zeros(dofs.ndof), penalty=1000.0
    )

    assert np.all(np.isfinite(internal))
    assert tangent.nnz > 0
    assert details["finite_sliding"] is True
    assert details["projection_clamped"] == [True]
    assert details["active_contacts"] == [0]


def test_finite_sliding_requires_updated_search() -> None:
    model = _outside_triangle_model()
    model.analysis.parameters["contact_search_mode"] = "initial"
    with pytest.raises(InputValidationError, match="contact_search_mode='updated'"):
        assemble_penalty_contact(model, model.dof_manager(), np.zeros(model.dof_manager().ndof), penalty=1000.0)


def test_updated_finite_sliding_recomputes_deformed_master_normal() -> None:
    model = _outside_triangle_model()
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof, dtype=float)
    displacement[dofs.index(2, "UZ")] = 0.5

    _, _, details = assemble_penalty_contact(model, dofs, displacement, penalty=1000.0)

    normal = np.asarray(details["normals"][0], dtype=float)
    assert np.all(np.isfinite(normal))
    assert np.linalg.norm(normal) == pytest.approx(1.0)
    assert normal[1] < -0.4
    assert details["search_mode"] == "updated"


def test_finite_sliding_benchmark_records_bounded_face_crossing() -> None:
    result = run_contact_finite_sliding_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["selected_face_indices"] == [0, 1]
    assert result["face_switch_count"] == 1
    assert all(row["projection_clamped"] for row in result["rows"])
    assert all(row["active_contacts"] == [0] for row in result["rows"])


def test_public_finite_sliding_route_fails_closed_until_qualified() -> None:
    model = JsonModelReader().from_dict(
        {
            "analysis": {
                "type": "nonlinear_static",
                "method": "newton_raphson",
                "parameters": {
                    "contact_mode": "penalty",
                    "contact_penalty": 1000.0,
                    "contact_search_mode": "updated",
                    "contact_finite_sliding": True,
                    "load_path": [1.0],
                    "max_iterations": 20,
                    "tolerance": 1.0e-8,
                },
            },
            "nodes": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.2, 0.25, -0.1],
            ],
            "elements": [],
            "materials": {},
            "fixed_dofs": [
                {"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)
            ] + [{"node": 4, "dofs": ["UX", "UY"]}],
            "loads": [{"node": 4, "dof": "UZ", "value": -1.0}],
            "springs": [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
            "contacts": [
                {
                    "name": "surface",
                    "slave_node": 4,
                    "master_faces": [[0, 1, 2], [0, 2, 3]],
                }
            ],
        }
    )

    with pytest.raises(CompatibilityError, match="ANALYSIS_NOT_SUPPORTED"):
        solve_model(model, enforce_policy=False)


def test_surface_patch_is_backward_compatible_and_sparse() -> None:
    data = {
        "analysis": {
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_search_mode": "updated", "contact_finite_sliding": True},
        },
        "nodes": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.25, 0.25, -0.1],
            [0.75, 0.75, -0.1],
        ],
        "elements": [],
        "materials": {},
        "springs": [
            {"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": 1.0},
            {"node_a": 5, "dofs": ["UX", "UY", "UZ"], "stiffness": 1.0},
        ],
        "contacts": [
            {
                "name": "patch",
                "slave_nodes": [4, 5],
                "master_faces": [[0, 1, 2], [0, 2, 3]],
            }
        ],
    }
    model = JsonModelReader().from_dict(data)
    restored = JsonModelReader().from_dict(model_to_dict(model))
    assert restored.contacts == model.contacts
    _, tangent, details = assemble_penalty_contact(
        model, model.dof_manager(), np.zeros(model.dof_manager().ndof), penalty=1000.0
    )
    assert details["slave_surface_mode"] == "node_patch_to_faceted_surface"
    assert details["slave_node_count"] == 2
    assert details["active_contacts"] == [0, 1]
    assert tangent.nnz > 0
    assert run_contact_surface_patch_benchmark()["status"] == "PASS_INTERNAL_RESEARCH"


def test_surface_patch_rejects_duplicate_slave_nodes() -> None:
    data = {
        "analysis": {"type": "nonlinear_static", "method": "newton_raphson"},
        "nodes": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.25, 0.25, -0.1],
        ],
        "elements": [],
        "materials": {},
        "springs": [{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": 1.0}],
        "contacts": [{"slave_nodes": [3, 3], "master_nodes": [0, 1, 2]}],
    }
    with pytest.raises(ValueError, match="slave_nodes must not contain duplicates"):
        JsonModelReader().from_dict(data)


def test_finite_sliding_crosses_three_facets() -> None:
    result = run_contact_three_facet_sliding_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["selected_face_indices"] == [0, 1, 2]
    assert result["face_switch_count"] == 2
    assert result["facet_count"] == 3


def test_facet_transition_rollback_replays_cleanly() -> None:
    result = run_contact_facet_transition_rollback_benchmark()

    assert result["status"] == "PASS_INTERNAL_RESEARCH"
    assert result["facet_transition_observed"] is True
    assert result["committed_face"] == result["rollback_face"] == 1
    assert result["failed_trial_face"] == result["retry_face"] == 2
    assert result["clean_retry"] is True
