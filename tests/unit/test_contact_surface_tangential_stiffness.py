"""Analytic patch checks for opt-in surface tangential regularization."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from solveur.contact.evaluation import contact_configuration_digest
from solveur.contact.measures import reference_surface_areas
from solveur.core.errors import InputValidationError
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import model_to_dict


def _patch(n: int, tx: float = 2.0, nz: float = -200.0) -> dict[str, Any]:
    nodes = [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 4.0, 0.0]]
    nodes += [[0.5 + i / n, 0.5 + j / n, 0.1] for j in range(n + 1) for i in range(n + 1)]

    def index(i: int, j: int) -> int:
        return 3 + j * (n + 1) + i

    faces = []
    for j in range(n):
        for i in range(n):
            a, c, d, e = index(i, j), index(i + 1, j), index(i, j + 1), index(i + 1, j + 1)
            faces.extend([[a, c, d], [c, e, d]])
    areas = reference_surface_areas(np.asarray(nodes), faces)
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 25},
        "nodes": nodes,
        "elements": [],
        "materials": {},
        "fixed_dofs": [{"node": i, "dofs": ["UX", "UY", "UZ"]} for i in range(3)]
        + [{"node": i, "dofs": ["UY"]} for i in areas],
        "springs": [{"node_a": i, "dofs": ["UX", "UZ"], "stiffness": [1000.0 * a] * 2} for i, a in areas.items()],
        "loads": [
            {"node": i, "dof": dof, "value": value * a}
            for i, a in areas.items()
            for dof, value in (("UX", tx), ("UZ", nz))
        ],
        "contacts": [
            {
                "name": "surface_patch",
                "slave_nodes": list(areas),
                "slave_patch_faces": faces,
                "master_nodes": [0, 1, 2],
                "friction_coefficient": 0.5,
                "tangential_stiffness_mode": "surface",
                "tangential_stiffness": 10000.0,
            }
        ],
    }


@pytest.mark.parametrize("n", [1, 2, 4])
@pytest.mark.parametrize(
    ("tx", "nz", "state", "ux", "force"),
    [
        (2.0, -200.0, "stick", 2.0 / 11000.0, 20.0 / 11.0),
        (200.0, -200.0, "slip", 0.15, 50.0),
        (2.0, 20.0, "open", 0.002, 0.0),
    ],
)
def test_surface_patch_force_and_displacement_are_mesh_independent(
    n: int,
    tx: float,
    nz: float,
    state: str,
    ux: float,
    force: float,
) -> None:
    """Closed-form parallel foundation, not a WP08 structural qualification."""
    model = JsonModelReader().from_dict(_patch(n, tx, nz))
    result = LinearStaticSolver().solve(model)
    rows = result.solver["contact"]["contacts"]
    assert sum(row["reference_slave_area"] for row in rows) == pytest.approx(1.0)
    assert sum(row["tangential_stiffness"] for row in rows) == pytest.approx(10000.0)
    assert sum(row["tangential_force"][0] for row in rows) == pytest.approx(force, abs=1.0e-10)
    for row in rows:
        assert row["tangential_state"] == state
        assert row["tangential_stiffness"] == pytest.approx(10000.0 * row["reference_slave_area"])
        assert result.displacements[result.dofs.index(row["slave_node"], "UX")] == pytest.approx(ux, abs=1.0e-12)
        assert row["declared_tangential_stiffness_unit"] == "N/m^3"


def test_surface_and_equivalent_explicit_nodal_laws_agree() -> None:
    data = _patch(2, 200.0)
    surface = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    nodal = deepcopy(data)
    patch = nodal["contacts"][0]
    areas = reference_surface_areas(np.asarray(nodal["nodes"]), patch["slave_patch_faces"])
    nodal["contacts"] = [
        {
            "slave_node": node,
            "master_nodes": [0, 1, 2],
            "friction_coefficient": 0.5,
            "tangential_stiffness": 10000.0 * area,
        }
        for node, area in areas.items()
    ]
    baseline = LinearStaticSolver().solve(JsonModelReader().from_dict(nodal))
    np.testing.assert_array_equal(surface.displacements, baseline.displacements)
    assert (
        surface.solver["contact"]["cumulative_local_dissipation"]
        == baseline.solver["contact"]["cumulative_local_dissipation"]
    )


def test_roundtrip_and_restart_digest_bind_the_surface_law() -> None:
    model = JsonModelReader().from_dict(_patch(1))
    restored = JsonModelReader().from_dict(model_to_dict(model))
    assert restored.contacts == model.contacts
    original_digest = contact_configuration_digest(model, penalty=1.0e6)
    assert contact_configuration_digest(restored, penalty=1.0e6) == original_digest
    nodal = _patch(1)
    nodal["contacts"][0]["tangential_stiffness_mode"] = "nodal"
    assert contact_configuration_digest(JsonModelReader().from_dict(nodal), penalty=1.0e6) != original_digest


@pytest.mark.parametrize("mode", ["line", "linear", "unknown", None])
def test_unsupported_stiffness_mode_is_not_silently_accepted(mode: object) -> None:
    data = _patch(1)
    data["contacts"][0]["tangential_stiffness_mode"] = mode
    with pytest.raises(InputValidationError, match="tangential_stiffness_mode"):
        JsonModelReader().from_dict(data)


def test_surface_requires_explicit_faces() -> None:
    data = _patch(1)
    del data["contacts"][0]["slave_patch_faces"]
    with pytest.raises(InputValidationError, match="slave_patch_faces"):
        JsonModelReader().from_dict(data)


@pytest.mark.parametrize("faces", [[[0, 1, 2], [2, 1, 0]], [[0, 0, 2]], [[0, 1, 9]], [[0, 1, True]], []])
def test_reference_areas_reject_invalid_or_duplicate_triangles(faces: list[list[int]]) -> None:
    with pytest.raises(InputValidationError):
        reference_surface_areas(np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), faces)


def test_excluding_slave_nodes_does_not_redistribute_their_area() -> None:
    areas = reference_surface_areas(np.asarray([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), [[0, 1, 2]])
    assert areas == pytest.approx({0: 1.0 / 3, 1: 1.0 / 3, 2: 1.0 / 3})
    assert sum(areas[i] for i in (1, 2)) == pytest.approx(2.0 / 3)


def test_surface_accepted_state_restart_rejects_nodal_reinterpretation(tmp_path: Path) -> None:
    data = _patch(1, 200.0)
    checkpoint = tmp_path / "surface_checkpoint.json"
    data["analysis"]["contact_checkpoint_path"] = str(checkpoint)
    LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    assert checkpoint.is_file()
    changed = deepcopy(data)
    changed["contacts"][0]["tangential_stiffness_mode"] = "nodal"
    changed["analysis"]["contact_restart_from"] = str(checkpoint)
    with pytest.raises(InputValidationError, match="does not match the physical model"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(changed))
