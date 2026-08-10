from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.api import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.vtu_writer import VtuResultWriter


def _square_model(
    *,
    analysis: str | dict[str, object] = "linear_static",
    loads: list[dict[str, object]] | None = None,
    distributed_loads: list[dict[str, object]] | None = None,
    material: dict[str, object] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        elements=[
            {"type": "MITC3", "nodes": [0, 1, 2], "material": "skin"},
            {"type": "MITC3", "nodes": [0, 2, 3], "material": "skin"},
        ],
        materials={
            "skin": material
            or {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 3, "dofs": ["UX", "UZ", "RX", "RY"]},
            {"node": 1, "dofs": ["UZ", "RX", "RY"]},
            {"node": 2, "dofs": ["UZ", "RX", "RY"]},
        ],
        loads=loads,
        distributed_loads=distributed_loads,
        analysis=analysis,
    )


def test_static_membrane_traction_matches_plane_stress_solution_and_postprocessing() -> None:
    model = _square_model(
        distributed_loads=[
            {"type": "edge_traction", "element": 0, "edge": 1, "value": [1.0e6, 0.0, 0.0]}
        ]
    )
    report = check_mesh(model)
    assert report.status == "PASS"
    result = solve_model(model)
    expected_strain = 1.0e6 / (0.01 * 70.0e9)
    assert result.status == "PASS"
    assert result.max_displacement == pytest.approx(expected_strain, rel=2.0e-12)
    assert len(result.element_results) == 2
    assert all(element["type"] == "MITC3" for element in result.element_results)
    # Element 0 is aligned with the global frame. Element 1 deliberately uses
    # its diagonal edge as e1 and therefore reports the same tensor rotated.
    aligned = result.element_results[0]
    assert aligned["membrane_strain"] == pytest.approx(
        [expected_strain, -0.3 * expected_strain, 0.0], abs=1.0e-14
    )
    assert aligned["membrane_force"][0] == pytest.approx(1.0e6, rel=2.0e-12)
    nodal = result.displacements.reshape((-1, 6))
    assert nodal[:, 0] == pytest.approx([0.0, expected_strain, expected_strain, 0.0])
    assert nodal[:, 1] == pytest.approx([0.0, 0.0, -0.3 * expected_strain, -0.3 * expected_strain])


def test_pressure_and_body_load_preserve_global_resultants() -> None:
    model = _square_model(
        distributed_loads=[
            {"type": "pressure", "element": 0, "value": 12.0},
            {"type": "pressure", "element": 1, "value": 12.0},
        ]
    )
    dofs = model.dof_manager()
    from solveur.core.assembler import GlobalAssembler

    assembler = GlobalAssembler()
    vector = assembler.assemble_loads(model, dofs)
    assert sum(vector[dofs.index(node, "UZ")] for node in range(4)) == pytest.approx(-12.0)


def test_modal_newmark_and_harmonic_routes_accept_mitc3() -> None:
    fixed = [
        {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
        {"node": 3, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
    ]
    base = {
        "nodes": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        "elements": [
            {"type": "MITC3", "nodes": [0, 1, 2], "material": "skin"},
            {"type": "MITC3", "nodes": [0, 2, 3], "material": "skin"},
        ],
        "materials": {
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.02,
                "density": 2700.0,
            }
        },
        "fixed_dofs": fixed,
    }
    modal = solve_model(
        FiniteElementModel.from_raw(
            **base,
            analysis={"type": "modal", "method": "eigh", "parameters": {"mode_count": 3}},
        )
    )
    assert np.all(np.asarray(modal.frequencies_hz[:3]) > 0.0)
    dynamic = solve_model(
        FiniteElementModel.from_raw(
            **base,
            analysis={
                "type": "transient_dynamic",
                "method": "newmark",
                "parameters": {
                    "time_step": 1.0e-4,
                    "steps": 4,
                    "beta": 0.25,
                    "gamma": 0.5,
                    "initial_displacements": [{"node": 1, "dof": "UZ", "value": 1.0e-4}],
                },
            },
        )
    )
    assert dynamic.status == "PASS"
    harmonic = solve_model(
        FiniteElementModel.from_raw(
            **base,
            loads=[{"node": 1, "dof": "UZ", "value": 1.0}],
            analysis={
                "type": "harmonic_response",
                "method": "direct_frequency",
                "parameters": {"frequencies_hz": [1.0, 10.0]},
            },
        )
    )
    assert harmonic.status == "PASS"
    assert len(harmonic.shell_stress_response) == 2
    assert all(row["element_results"] for row in harmonic.shell_stress_response)


def test_laminate_static_and_dynamic_use_projected_ply_material() -> None:
    laminate = {
        "type": "shell_laminate",
        "reference_direction": [1.0, 0.0, 0.0],
        "plies": [
            {
                "name": "zero",
                "thickness": 0.001,
                "angle_deg": 0.0,
                "E1": 130.0e9,
                "E2": 9.0e9,
                "nu12": 0.28,
                "G12": 5.0e9,
                "G13": 4.0e9,
                "G23": 3.5e9,
                "density": 1550.0,
            },
            {
                "name": "ninety",
                "thickness": 0.001,
                "angle_deg": 90.0,
                "E1": 130.0e9,
                "E2": 9.0e9,
                "nu12": 0.28,
                "G12": 5.0e9,
                "G13": 4.0e9,
                "G23": 3.5e9,
                "density": 1550.0,
            },
        ],
    }
    static = solve_model(
        _square_model(
            material=laminate,
            distributed_loads=[
                {"type": "edge_traction", "element": 0, "edge": 1, "value": [1000.0, 0.0, 0.0]}
            ],
        )
    )
    assert static.element_results[0]["ply_results"]
    assert static.element_results[0]["material_angle_offset_deg"] == pytest.approx(0.0)
    harmonic = solve_model(
        _square_model(
            material=laminate,
            loads=[{"node": 1, "dof": "UZ", "value": 1.0}],
            analysis={
                "type": "harmonic_response",
                "method": "direct_frequency",
                "parameters": {"frequencies_hz": [5.0]},
            },
        )
    )
    element = harmonic.shell_stress_response[0]["element_results"][0]
    assert len(element["ply_results"]) == 6
    assert element["ply_results"][0]["stress_material"]["amplitude"]
    assert all(np.isfinite(element["shell_faces"][0]["stress"]["amplitude"]))


def test_vtu_writer_uses_triangle_cell_type(tmp_path: Path) -> None:
    result = solve_model(
        _square_model(
            distributed_loads=[
                {"type": "edge_traction", "element": 0, "edge": 1, "value": [1000.0, 0.0, 0.0]}
            ]
        )
    )
    path = tmp_path / "mitc3.vtu"
    VtuResultWriter().write(result, _square_model(), path)
    content = path.read_text(encoding="utf-8")
    assert 'Name="types"' in content
    assert "5 5" in content


def test_mixed_mitc3_mitc4_interface_passes_affine_membrane_patch() -> None:
    young = 70.0e9
    thickness = 0.01
    traction = 1.0e6
    expected = traction / (young * thickness)
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0], [2, 1, 0]],
        elements=[
            {"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"},
            {"type": "MITC3", "nodes": [1, 4, 2], "material": "skin"},
            {"type": "MITC3", "nodes": [4, 5, 2], "material": "skin"},
        ],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": young,
                "nu": 0.3,
                "t": thickness,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 3, "dofs": ["UX", "UZ", "RX", "RY"]},
            *[
                {"node": node, "dofs": ["UZ", "RX", "RY"]}
                for node in (1, 2, 4, 5)
            ],
        ],
        distributed_loads=[
            {"type": "edge_traction", "element": 2, "edge": 0, "value": [traction, 0.0, 0.0]}
        ],
        verification_profile="quick",
    )
    assert check_mesh(model).status == "PASS"
    result = solve_model(model)
    nodal = result.displacements.reshape((-1, 6))
    assert nodal[:, 0] == pytest.approx([0.0, expected, expected, 0.0, 2.0 * expected, 2.0 * expected])
    assert nodal[:, 1] == pytest.approx([0.0, 0.0, -0.3 * expected, -0.3 * expected, 0.0, -0.3 * expected])


def test_inconsistent_mitc3_orientation_is_rejected() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        elements=[
            {"type": "MITC3", "nodes": [0, 1, 2], "material": "skin"},
            {"type": "MITC3", "nodes": [0, 3, 2], "material": "skin"},
        ],
        materials={
            "skin": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.3, "t": 0.01}
        },
    )
    report = check_mesh(model)
    assert report.status == "FAIL"
    assert any("Inconsistent shell orientation" in error for error in report.errors)
