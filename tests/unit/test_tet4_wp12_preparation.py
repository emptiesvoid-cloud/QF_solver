"""Focused checks for WP12 TET4 mesh preparation and post-processing oracles."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "wp12_dev"))

from prepare_tet4_quality_sequence import controlled_levels, prepare
from tet4_mechanical_oracles import linear_static_observables, surface_average, surface_measure_weights


def test_tet4_wp12_preparation_geometry_load_and_static_observables() -> None:
    levels = controlled_levels()
    assert [(item["nx"], item["ny"], item["nz"], item["dofs"]) for item in levels] == [
        (5, 1, 1, 72),
        (10, 2, 2, 297),
        (20, 4, 4, 1575),
        (40, 8, 8, 9963),
    ]
    assert all(item["cell_aspect_ratio"] == 2.0 for item in levels)

    tet4_nodes = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )
    tet4_connectivity = [(0, 1, 2, 3)]
    tet4_measure = surface_measure_weights(tet4_nodes, tet4_connectivity, "TET4", axis=0, coordinate=0.0)
    assert tet4_measure.face_count == 1
    assert np.isclose(tet4_measure.total_area, 0.5)
    assert np.isclose(np.sum(tet4_measure.nodal_area_weights), 0.5)
    tet4_displacement = np.zeros((4, 3))
    tet4_displacement[:, 1] = tet4_nodes[:, 1]
    assert np.isclose(surface_average(tet4_displacement, tet4_measure, component=1), 1.0 / 3.0)

    edge_order = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    tet10_nodes = tet4_nodes.tolist()
    tet10_nodes.extend((0.5 * (tet4_nodes[first] + tet4_nodes[second])).tolist() for first, second in edge_order)
    tet10_measure = surface_measure_weights(tet10_nodes, [tuple(range(10))], "TET10", axis=0, coordinate=0.0)
    assert tet10_measure.face_count == 1
    assert np.isclose(tet10_measure.total_area, 0.5)
    assert np.allclose(tet10_measure.nodal_area_weights[[0, 2, 3]], 0.0)
    assert np.allclose(tet10_measure.nodal_area_weights[[6, 7, 9]], np.full(3, 1.0 / 6.0))
    tet10_displacement = np.zeros((10, 3))
    tet10_displacement[:, 1] = np.asarray(tet10_nodes)[:, 1]
    assert np.isclose(surface_average(tet10_displacement, tet10_measure, component=1), 1.0 / 3.0)

    hex8_nodes = np.asarray(
        [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )
    hex8_measure = surface_measure_weights(hex8_nodes, [tuple(range(8))], "HEX8", axis=0, coordinate=1.0)
    assert hex8_measure.face_count == 1
    assert np.isclose(hex8_measure.total_area, 1.0)
    assert np.allclose(hex8_measure.nodal_area_weights[[1, 2, 5, 6]], 0.25)
    hex8_displacement = np.zeros((8, 3))
    hex8_displacement[:, 1] = hex8_nodes[:, 1]
    assert np.isclose(surface_average(hex8_displacement, hex8_measure, component=1), 0.5)

    support_load_nodes = np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    stiffness = np.diag([10.0] * 6 + [1.0] * 3)
    for fixed_dof, coupling in ((0, -1.0), (3, 1.0), (5, -1.0)):
        stiffness[fixed_dof, 8] = coupling
        stiffness[8, fixed_dof] = coupling
    displacement = np.zeros(9)
    displacement[8] = -1.0
    force = np.zeros(9)
    force[8] = -1.0
    result = linear_static_observables(
        nodes=support_load_nodes,
        stiffness=stiffness,
        force_vector=force,
        displacement=displacement,
        fixed_dofs=np.arange(6),
    )
    assert np.allclose(result["reaction_resultant_n"], [0.0, 0.0, 1.0])
    assert np.allclose(result["force_equilibrium_residual_n"], [0.0, 0.0, 0.0])
    assert np.allclose(result["applied_moment_about_origin_nm"], [0.0, 1.0, 0.0])
    assert np.allclose(result["moment_equilibrium_residual_nm"], [0.0, 0.0, 0.0])
    assert np.isclose(result["strain_energy_j"], 0.5)
    assert np.isclose(result["external_work_j"], 1.0)
    assert np.isclose(result["twice_energy_minus_work_j"], 0.0)
    assert np.isclose(result["free_residual_norm_n"], 0.0)
    assert result["residual_method"].startswith("K_supplied_times_u_minus_f")


def test_tet4_wp12_mesh_preparation_builds_nested_and_family_inputs(tmp_path: Path) -> None:
    output = tmp_path / "prepared"
    summary = prepare(output)

    assert summary["status"] == "PREPARED_NO_FEM_EXECUTED"
    assert summary["execution"] == {
        "fem_execution_performed": False,
        "solver_calls": 0,
        "displacement_or_reaction_results": None,
    }
    levels = summary["mesh_sequence"]["levels"]
    assert [item["elements"] for item in levels] == [30, 240, 1920, 15360]
    assert [item["signed_volume_m3"] for item in levels] == pytest.approx([0.64] * 4)
    assert all(item["mesh_quality"]["fatal_element_count"] == 0 for item in levels)
    for item in levels:
        quality = item["mesh_quality"]["metrics"]["tet4_quality_6sqrt2V_over_rms_edge_cubed"]
        assert quality["min"] <= quality["p05"] <= quality["median"] <= quality["p95"] <= quality["max"]
    assert all(item["mechanical_input_audit"]["load_resultant_n"] == pytest.approx([0.0, 0.0, -1.0]) for item in levels)

    family_models = summary["family_comparison"]["models"]
    assert [item["family"] for item in family_models] == ["TET4", "TET10", "HEX8"]
    assert all(item["dofs"] <= 50_000 for item in family_models)
    assert all(item["mesh_quality"]["fatal_element_count"] == 0 for item in family_models)
    for item in family_models:
        for values in item["mesh_quality"]["metrics"].values():
            assert values["min"] <= values["p05"] <= values["median"] <= values["p95"] <= values["max"]
        assert item["mechanical_input_audit"]["load_resultant_n"] == pytest.approx([0.0, 0.0, -1.0])
        assert item["mechanical_input_audit"]["applied_moment_about_origin_nm"] == pytest.approx([-0.2, 4.0, 0.0])
        assert (output / item["model_file"]).is_file()

    with pytest.raises(FileExistsError):
        prepare(output)
