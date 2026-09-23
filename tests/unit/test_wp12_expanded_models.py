"""Regression checks for prospective WP12 multi-model correlation inputs."""

from __future__ import annotations

import numpy as np
from collections import Counter
from itertools import combinations

from scripts.wp12_expanded_models import (
    FAMILIES,
    GEOMETRIES,
    LOADS,
    MESHES,
    case_catalog,
    mesh_for_case,
)
from solveur.elements.solid.tet4 import Tet4Element


def test_expanded_catalog_covers_all_families_geometries_meshes_and_loads() -> None:
    cases = case_catalog()

    assert len(cases) == len(FAMILIES) * len(GEOMETRIES) * len(MESHES) * len(LOADS) == 144
    assert len({case.case_id for case in cases}) == len(cases)
    assert {case.family for case in cases} == set(FAMILIES)
    assert {case.geometry for case in cases} == set(GEOMETRIES)
    assert {case.mesh for case in cases} == set(MESHES)
    assert {case.load_case for case in cases} == set(LOADS)
    assert all(case.system.stiffness.shape[0] == 3 * len(case.model.nodes) for case in cases)


def test_surface_tractions_preserve_resultant_and_moment_for_every_case() -> None:
    for case in case_catalog():
        loads = case.system.loads.reshape(-1, 3)
        resultant = np.sum(loads, axis=0)
        moment = np.sum(np.cross(case.model.nodes, loads), axis=0)
        expected_force = np.asarray(case.resultant)
        load_center = np.asarray((case.dimensions[0], case.dimensions[1] / 2.0, case.dimensions[2] / 2.0))
        expected_moment = np.cross(load_center, expected_force)

        assert np.isclose(case.load_area, case.dimensions[1] * case.dimensions[2], rtol=1e-12, atol=1e-12)
        assert np.allclose(resultant, expected_force, rtol=1e-12, atol=1e-10)
        assert np.allclose(moment, expected_moment, rtol=1e-12, atol=1e-10)


def test_structured_tetrahedra_are_positive_and_fill_the_box() -> None:
    for geometry, dimensions in GEOMETRIES.items():
        for mesh in MESHES:
            coordinates, connectivity, _, _ = mesh_for_case("TET4", geometry, mesh)
            volumes = [Tet4Element.signed_volume(coordinates[element]) for element in connectivity]
            assert all(volume > 0.0 for volume in volumes)
            assert np.isclose(sum(volumes), np.prod(dimensions), rtol=1e-12, atol=1e-12)


def test_structured_tetrahedral_faces_are_conforming() -> None:
    for geometry, dimensions in GEOMETRIES.items():
        for mesh in MESHES:
            coordinates, connectivity, _, _ = mesh_for_case("TET4", geometry, mesh)
            face_counts = Counter(
                tuple(sorted(int(node) for node in face))
                for element in connectivity
                for face in combinations(element, 3)
            )
            for face, count in face_counts.items():
                face_coordinates = coordinates[list(face)]
                is_external = any(
                    np.allclose(face_coordinates[:, axis], bound, rtol=0.0, atol=1e-12)
                    for axis, dimension in enumerate(dimensions)
                    for bound in (0.0, dimension)
                )
                assert count in (1, 2)
                assert count != 1 or is_external
