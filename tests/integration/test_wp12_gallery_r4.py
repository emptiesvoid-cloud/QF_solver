from __future__ import annotations

from collections import deque

import numpy as np
import pytest

from scripts import run_wp12_expanded_code_aster as command_engine
from scripts.audit_wp12_expanded_code_aster import _case_expected_material
from scripts.wp12_diverse_models import code_aster_command_text
from scripts.wp12_expanded_models import FAMILIES, LOADS
from scripts.wp12_gallery_models import (
    GEOMETRIES,
    MATERIALS,
    MESHES_BY_GEOMETRY,
    active_cell_mask,
    build_case,
    case_matrix,
    mesh_for_case,
    topology_summary,
)
from solveur.elements.solid.hex8 import Hex8Element


EXPECTED_CROSS_SECTION_CELL_COUNTS = {
    "triangular_prism": 15,
    "tee_section_beam": 9,
    "i_section_beam": 13,
    "channel_section_beam": 13,
    "box_tube_beam": 16,
    "cruciform_beam": 9,
}


def _assert_connected(mask: np.ndarray) -> None:
    active = {(j, k) for j in range(5) for k in range(5) if bool(mask[j, k])}
    first = next(iter(active))
    seen = {first}
    pending = deque([first])
    while pending:
        j, k = pending.popleft()
        for neighbor in ((j - 1, k), (j + 1, k), (j, k - 1), (j, k + 1)):
            if neighbor in active and neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    assert seen == active


def test_r4_matrix_is_large_unique_and_balanced() -> None:
    matrix = case_matrix()
    assert len(matrix) == 864
    assert len(set(matrix)) == 864
    assert len({(row[1], row[2]) for row in matrix}) == 18
    assert set(row[0] for row in matrix) == set(FAMILIES)
    assert set(row[1] for row in matrix) == set(GEOMETRIES)
    assert set(row[2] for row in matrix) == set(MATERIALS)
    assert set(row[3] for row in matrix) == {"H1", "H2", "H3"}
    assert set(row[4] for row in matrix) == set(LOADS)
    assert topology_summary() == EXPECTED_CROSS_SECTION_CELL_COUNTS


@pytest.mark.parametrize("geometry", tuple(GEOMETRIES))
def test_gallery_cross_sections_are_connected_and_have_frozen_cell_count(geometry: str) -> None:
    mask = active_cell_mask(geometry, (1, 5, 5)).reshape(5, 5)
    assert int(np.count_nonzero(mask)) == EXPECTED_CROSS_SECTION_CELL_COUNTS[geometry]
    _assert_connected(mask)
    for mesh, divisions in MESHES_BY_GEOMETRY[geometry].items():
        nx, ny, nz = divisions
        full_mask = active_cell_mask(geometry, divisions).reshape(nx, ny, nz)
        assert np.all(full_mask == mask[np.newaxis, :, :])
        assert int(np.count_nonzero(full_mask)) == nx * EXPECTED_CROSS_SECTION_CELL_COUNTS[geometry]
        assert mesh in {"H1", "H2", "H3"}


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("geometry", tuple(GEOMETRIES))
@pytest.mark.parametrize("mesh", ("H1", "H2", "H3"))
def test_all_r4_family_topology_meshes_are_compact_and_positive(
    family: str, geometry: str, mesh: str
) -> None:
    coordinates, connectivity, _, _ = mesh_for_case(family, geometry, mesh)
    expected_nodes_per_element = {"TET4": 4, "TET10": 10, "HEX8": 8, "HEX20": 20}[family]
    assert connectivity.ndim == 2
    assert connectivity.shape[1] == expected_nodes_per_element
    assert np.array_equal(np.unique(connectivity), np.arange(len(coordinates)))
    assert np.all(np.isfinite(coordinates))
    assert int(connectivity.min()) >= 0
    assert int(connectivity.max()) < len(coordinates)

    if family.startswith("TET"):
        corners = coordinates[connectivity[:, :4]]
        determinants = np.linalg.det(np.stack((corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0], corners[:, 3] - corners[:, 0]), axis=2))
        assert np.all(determinants > 0.0)
    else:
        gauss = 1.0 / np.sqrt(3.0)
        for element in connectivity:
            local = coordinates[element[:8]]
            for xi in (-gauss, gauss):
                for eta in (-gauss, gauss):
                    for zeta in (-gauss, gauss):
                        derivative = Hex8Element.shape_derivatives_reference((xi, eta, zeta))
                        jacobian = derivative.T @ local
                        assert np.linalg.det(jacobian) > 0.0


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("geometry", tuple(GEOMETRIES))
@pytest.mark.parametrize("material_variant", tuple(MATERIALS))
def test_gallery_cases_assemble_and_preserve_resultant_and_moment(
    family: str, geometry: str, material_variant: str
) -> None:
    case = build_case(family, geometry, material_variant, "H1", "combined_xyz")
    nodal_loads = np.asarray(case.system.loads, dtype=np.float64).reshape(-1, 3)
    coordinates = np.asarray(case.model.nodes, dtype=np.float64)
    assert case.material == MATERIALS[material_variant]
    assert case.system.stiffness.shape == (3 * len(coordinates), 3 * len(coordinates))
    assert np.all(np.isfinite(case.system.stiffness.data))
    assert np.allclose(np.sum(nodal_loads, axis=0), case.resultant, rtol=1e-12, atol=1e-10)
    observed_moment = np.sum(np.cross(coordinates, nodal_loads), axis=0)
    assert np.allclose(observed_moment, case.load_moment, rtol=1e-12, atol=1e-10)
    assert np.allclose(
        case.model.materials["solid"]["E"], MATERIALS[material_variant]["E"], rtol=0.0, atol=0.0
    )


def test_auditor_supports_per_case_materials_and_legacy_global_fallback() -> None:
    global_material = {"E": 210.0e9, "nu": 0.30}
    case_override = {"E": 69.0e9, "nu": 0.33}
    contract = {"material": global_material}
    assert _case_expected_material({}, contract) == global_material
    assert _case_expected_material({"material": case_override}, contract) == case_override
    with pytest.raises(ValueError, match="JSON object"):
        _case_expected_material({"material": [1, 2]}, contract)


@pytest.mark.parametrize("material_variant", tuple(MATERIALS))
def test_code_aster_command_serializes_each_frozen_material(material_variant: str, monkeypatch: pytest.MonkeyPatch) -> None:
    case = build_case("HEX8", "tee_section_beam", material_variant, "H1", "transverse_z")
    monkeypatch.setattr(command_engine, "MATERIAL", dict(case.material))
    text = code_aster_command_text(case)
    assert f"E={float(case.material['E']):.17g}" in text
    assert f"NU={float(case.material['nu']):.17g}" in text
    assert "MECA_STATIQUE" in text
