"""Checks for the prospective WP12 non-prismatic 3D model catalog."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
import re

import numpy as np
import pytest

from scripts.wp12_diverse_models import (
    END_FACE_AREA_FRACTION,
    EXPECTED_VOLUME_FRACTION,
    FAMILIES,
    GEOMETRIES,
    LOADS,
    MESHES_BY_GEOMETRY,
    case_catalog,
    code_aster_command_text,
    code_aster_mesh_text,
    mesh_for_case,
)
from scripts.audit_wp12_expanded_code_aster import (
    _audit_comm_text,
    _audit_mesh_text,
    _decode_aster_node_name,
)
from scripts import run_wp12_expanded_code_aster as r3_runner
from scripts import run_wp12_diverse_code_aster as diverse_runner
from scripts.wp12_expanded_models import MATERIAL
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.large.multifamily import solve_linear_system


@pytest.fixture(scope="module")
def diverse_cases():
    return case_catalog()


def test_diverse_catalog_has_144_unique_cases_and_broad_topology_coverage(diverse_cases) -> None:
    cases = diverse_cases
    assert len(cases) == len(FAMILIES) * len(GEOMETRIES) * 3 * len(LOADS) == 144
    assert len({case.case_id for case in cases}) == len(cases)
    assert {case.family for case in cases} == set(FAMILIES)
    assert {case.geometry for case in cases} == set(GEOMETRIES)
    assert {case.load_case for case in cases} == set(LOADS)
    assert all(case.system.stiffness.shape == (3 * len(case.model.nodes),) * 2 for case in cases)


def test_diverse_geometry_masks_preserve_expected_solid_volumes_for_all_meshes() -> None:
    for geometry, dimensions in GEOMETRIES.items():
        expected = np.prod(dimensions) * EXPECTED_VOLUME_FRACTION[geometry]
        for mesh in MESHES_BY_GEOMETRY[geometry]:
            coordinates, connectivity, _, _ = mesh_for_case("TET4", geometry, mesh)
            volumes = [Tet4Element.signed_volume(coordinates[element]) for element in connectivity]
            assert all(volume > 0.0 for volume in volumes)
            assert np.isclose(sum(volumes), expected, rtol=1e-12, atol=1e-12)


def test_hex_meshes_are_valid_compact_and_have_expected_solid_volumes() -> None:
    for geometry, dimensions in GEOMETRIES.items():
        expected = np.prod(dimensions) * EXPECTED_VOLUME_FRACTION[geometry]
        for mesh in MESHES_BY_GEOMETRY[geometry]:
            coordinates, connectivity, _, _ = mesh_for_case("HEX8", geometry, mesh)
            assert np.array_equal(np.unique(connectivity), np.arange(len(coordinates)))
            volumes = []
            for element in connectivity:
                element_coordinates = coordinates[element]
                Hex8Element.validate_geometry(element_coordinates)
                jacobian = Hex8Element.jacobian(element_coordinates, (0.0, 0.0, 0.0))
                volumes.append(8.0 * float(np.linalg.det(jacobian)))
            assert np.isclose(sum(volumes), expected, rtol=1e-12, atol=1e-12)


def test_traction_resultants_moments_and_loaded_faces_are_valid_for_all_cases(diverse_cases) -> None:
    for case in diverse_cases:
        coordinates = np.asarray(case.model.nodes, dtype=np.float64)
        loads = case.system.loads.reshape(-1, 3)
        loaded = np.flatnonzero(np.any(loads != 0.0, axis=1))
        assert loaded.size > 0
        assert np.allclose(coordinates[loaded, 0], case.dimensions[0], rtol=0.0, atol=1e-12)
        assert np.isclose(case.load_area, np.prod(case.dimensions[1:]) * END_FACE_AREA_FRACTION[case.geometry], rtol=1e-12, atol=1e-12)
        assert np.allclose(np.sum(loads, axis=0), case.resultant, rtol=1e-12, atol=1e-10)
        moment = np.sum(np.cross(coordinates, loads), axis=0)
        assert np.allclose(moment, case.load_moment, rtol=1e-12, atol=1e-10)


def test_all_diverse_primary_linear_systems_solve_with_small_free_residual(diverse_cases) -> None:
    for case in diverse_cases:
        displacement, _ = solve_linear_system(case.system)
        assert np.all(np.isfinite(displacement))
        residual = np.asarray(case.system.stiffness @ displacement - case.system.loads)
        free = np.ones(residual.size, dtype=bool)
        free[case.system.fixed] = False
        load_scale = max(float(np.linalg.norm(case.system.loads)), 1.0)
        assert float(np.linalg.norm(residual[free]) / load_scale) < 1e-8


def test_tetrahedral_faces_are_manifold_without_duplicate_or_nonmanifold_faces() -> None:
    for geometry in GEOMETRIES:
        for mesh in MESHES_BY_GEOMETRY[geometry]:
            coordinates, connectivity, _, _ = mesh_for_case("TET4", geometry, mesh)
            face_counts = Counter(
                tuple(sorted(int(node) for node in face))
                for element in connectivity
                for face in combinations(element, 3)
            )
            assert face_counts
            assert all(count in (1, 2) for count in face_counts.values())


def test_highest_diverse_meshes_respect_code_aster_mail_record_width(diverse_cases) -> None:
    for case in diverse_cases:
        if case.mesh == "H3" and case.load_case == "combined_xyz":
            text = code_aster_mesh_text(case)
            assert max(map(len, text.splitlines())) <= 80
            node_records = text.split("COOR_3D\n", maxsplit=1)[1].split("\nFINSF\n", maxsplit=1)[0]
            node_names = [line.split(maxsplit=1)[0] for line in node_records.splitlines()]
            assert len(node_names) == len(case.model.nodes)
            assert len(set(node_names)) == len(node_names)
            assert all(len(name) == 2 and name[0].isalpha() for name in node_names)

            command_text = code_aster_command_text(case)
            force_group_indices = {int(value) for value in re.findall(r'GROUP_NO="QF([0-9]{5})"', command_text)}
            assert force_group_indices <= set(range(len(case.model.nodes)))
            assert 'NOEUD=' not in command_text


def test_compact_aster_serialization_round_trips_in_independent_auditor(diverse_cases, tmp_path) -> None:
    assert _decode_aster_node_name("N1") == 0
    assert _decode_aster_node_name("A0") == 0
    assert _decode_aster_node_name("A1") == 1
    assert _decode_aster_node_name("B0") == 36

    for case in diverse_cases:
        if case.mesh != "H3" or case.load_case != "combined_xyz":
            continue
        mesh_path = tmp_path / f"{case.case_id}.mail"
        comm_path = tmp_path / f"{case.case_id}.comm"
        mesh_path.write_text(code_aster_mesh_text(case), encoding="ascii")
        comm_path.write_text(code_aster_command_text(case), encoding="utf-8")
        assert _audit_mesh_text(
            mesh_path,
            case.family,
            np.asarray(case.model.nodes, dtype=np.float64),
            np.asarray(case.connectivity, dtype=np.int64),
        ) == []
        assert _audit_comm_text(
            comm_path,
            case.system.loads.reshape(-1, 3),
            MATERIAL,
            case.case_id,
        ) == []


def test_independent_auditor_remains_compatible_with_legacy_noeud_commands(diverse_cases, tmp_path) -> None:
    case = next(
        row for row in diverse_cases
        if row.family == "TET4" and row.geometry == "l_section_beam" and row.mesh == "H1" and row.load_case == "axial_x"
    )
    mesh_path = tmp_path / "legacy.mail"
    comm_path = tmp_path / "legacy.comm"
    mesh_path.write_text(r3_runner._mesh_text(case), encoding="ascii")
    comm_path.write_text(r3_runner._comm_text(case), encoding="utf-8")
    assert _audit_mesh_text(
        mesh_path,
        case.family,
        np.asarray(case.model.nodes, dtype=np.float64),
        np.asarray(case.connectivity, dtype=np.int64),
    ) == []
    assert _audit_comm_text(comm_path, case.system.loads.reshape(-1, 3), MATERIAL, case.case_id) == []


def test_independent_auditor_rejects_invalid_or_duplicate_qf_load_groups(diverse_cases, tmp_path) -> None:
    case = next(
        row for row in diverse_cases
        if row.family == "TET4" and row.geometry == "l_section_beam" and row.mesh == "H1" and row.load_case == "axial_x"
    )
    command_path = tmp_path / "loads.comm"
    command = code_aster_command_text(case)
    command_path.write_text(command, encoding="utf-8")
    assert _audit_comm_text(command_path, case.system.loads.reshape(-1, 3), MATERIAL, case.case_id) == []

    first_group = re.search(r'GROUP_NO="QF([0-9]{5})"', command)
    assert first_group is not None
    invalid = command[: first_group.start(1)] + "99999" + command[first_group.end(1) :]
    command_path.write_text(invalid, encoding="utf-8")
    assert any("differ from the frozen QF nodal load vector" in error for error in _audit_comm_text(
        command_path, case.system.loads.reshape(-1, 3), MATERIAL, case.case_id
    ))

    first_factor = re.search(r'_F\(GROUP_NO="QF[0-9]{5}"[^)]*\)', command)
    assert first_factor is not None
    duplicated = command.replace(first_factor.group(0), first_factor.group(0) + ",\n    " + first_factor.group(0), 1)
    command_path.write_text(duplicated, encoding="utf-8")
    assert any("duplicated" in error or "differ from the frozen" in error for error in _audit_comm_text(
        command_path, case.system.loads.reshape(-1, 3), MATERIAL, case.case_id
    ))


def test_independent_auditor_checks_qf_mesh_groups_are_singletons_for_correct_nodes(diverse_cases, tmp_path) -> None:
    case = next(
        row for row in diverse_cases
        if row.family == "TET4" and row.geometry == "l_section_beam" and row.mesh == "H1"
    )
    mesh_path = tmp_path / f"{case.case_id}.mail"
    mesh = code_aster_mesh_text(case)
    mesh_path.write_text(mesh, encoding="ascii")
    assert _audit_mesh_text(
        mesh_path,
        case.family,
        np.asarray(case.model.nodes, dtype=np.float64),
        np.asarray(case.connectivity, dtype=np.int64),
    ) == []

    mesh_path.write_text(mesh.replace("GROUP_NO\nQF00000\nA0\nFINSF", "GROUP_NO\nQF00000\nA1\nFINSF", 1), encoding="ascii")
    assert any("QF group does not contain" in error for error in _audit_mesh_text(
        mesh_path,
        case.family,
        np.asarray(case.model.nodes, dtype=np.float64),
        np.asarray(case.connectivity, dtype=np.int64),
    ))


def test_r36_serializer_does_not_recurse_when_installed_as_runner_callback(diverse_cases) -> None:
    case = next(
        row for row in diverse_cases
        if row.family == "TET4" and row.geometry == "l_section_beam" and row.mesh == "H1"
    )
    original_mesh_text = r3_runner._mesh_text
    original_comm_text = r3_runner._comm_text
    r3_runner._mesh_text = code_aster_mesh_text
    r3_runner._comm_text = code_aster_command_text
    try:
        assert "TETRA4" in code_aster_mesh_text(case)
        assert "MECA_STATIQUE" in code_aster_command_text(case)
    finally:
        r3_runner._mesh_text = original_mesh_text
        r3_runner._comm_text = original_comm_text


def test_r36_r2_runner_fails_closed_without_both_prior_attempts(tmp_path) -> None:
    with pytest.raises(diverse_runner.CampaignError, match="bind both preserved failed attempts"):
        diverse_runner._verify_prior_attempts({}, tmp_path)
