"""WP05-A controlled TET10 high-order TL identity fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.assembly.geometric import build_total_lagrangian_assembly
from solveur.elements.solid.tet10 import Tet10Element
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshCell, GmshMeshData, GmshPhysicalGroup

from wp05_high_order_identity_support import (
    affine_deformation_gradient,
    affine_displacement,
    energy_gradient_metrics,
    finite_difference_step,
    linear_reaction,
    model_for_family,
    rigid_body_displacement,
    stvk_oracle,
    structural_model,
    tangent_metrics,
    tet10_coordinates,
    tl_assembly,
    tl_reaction,
)


def test_tet10_objectivity_uses_multiple_finite_rotations() -> None:
    assembly = tl_assembly("TET10")
    coordinates = tet10_coordinates()
    for axis, angle in ((np.asarray([0.0, 0.0, 1.0]), 0.2), (np.asarray([1.0, 2.0, 3.0]), -0.47)):
        displacement = rigid_body_displacement(coordinates, axis, angle)
        internal, tangent = assembly.assemble(displacement)
        assert tangent is not None
        assert np.all(np.isfinite(internal))
        assert np.all(np.isfinite(tangent.data))
        assert assembly.strain_energy(displacement) <= 1.0e-12
        assert np.linalg.norm(internal) <= 1.0e-11


def test_tet10_affine_patch_matches_independent_stvk_oracle() -> None:
    deformation = affine_deformation_gradient()
    displacement = affine_displacement(tet10_coordinates(), deformation)
    assembly = tl_assembly("TET10")
    state = assembly.element_states(displacement)
    oracle = stvk_oracle(deformation)
    np.testing.assert_allclose(state["green_lagrange_strain"][0], oracle["green"], rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(state["second_piola_stress"][0], _stress_tensor(oracle["stress"]), rtol=1.0e-12, atol=1.0e-14)
    assert assembly.strain_energy(displacement) == pytest.approx(float(oracle["energy_density"]) / 6.0, rel=1.0e-12, abs=1.0e-14)


def test_tet10_internal_force_is_energy_gradient_with_declared_step() -> None:
    relative, step = energy_gradient_metrics("TET10")
    assert step == pytest.approx(finite_difference_step(affine_displacement(tet10_coordinates(), affine_deformation_gradient())))
    assert relative <= 1.0e-7


def test_tet10_tangent_matches_finite_difference_at_corner_and_midside_dofs() -> None:
    frobenius, maximum_column, symmetry, sampled = tangent_metrics("TET10")
    assert sampled == [0, 1, 2, 12, 13, 14]
    assert frobenius <= 1.0e-6
    assert maximum_column <= 5.0e-6
    assert symmetry <= 1.0e-12


def test_tet10_small_displacement_limit_matches_linear_route() -> None:
    linear_model = structural_model("TET10", "linear_static", 1.0e-7)
    tl_model = structural_model("TET10", "geometric_nonlinear_static", 1.0e-7)
    linear = solve_model(linear_model, enforce_policy=False)
    total_lagrangian = solve_model(tl_model, enforce_policy=False)
    assert linear.status == "PASS"
    assert total_lagrangian.status == "success"
    displacement_error = np.linalg.norm(linear.displacements - total_lagrangian.displacements) / max(
        np.linalg.norm(linear.displacements), np.finfo(float).eps
    )
    reaction_error = np.linalg.norm(linear_reaction(linear_model, linear.displacements) - tl_reaction(tl_model, total_lagrangian.displacements)) / max(
        np.linalg.norm(linear_reaction(linear_model, linear.displacements)), np.finfo(float).eps
    )
    assert displacement_error <= 1.0e-4
    assert reaction_error <= 1.0e-4


def test_tet10_gmsh_ordering_maps_to_internal_order() -> None:
    nodes = {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
        3: (0.0, 1.0, 0.0),
        4: (0.0, 0.0, 1.0),
        5: (0.5, 0.0, 0.0),
        6: (0.5, 0.5, 0.0),
        7: (0.0, 0.5, 0.0),
        8: (0.0, 0.0, 0.5),
        9: (0.5, 0.0, 0.5),
        10: (0.0, 0.5, 0.5),
    }
    cells = {1: GmshCell(1, 11, 3, 2, "Tetrahedron 10", (1, 3, 2, 4, 7, 6, 5, 8, 9, 10))}
    groups = {(3, "domain"): GmshPhysicalGroup("domain", 3, 1, (1,), tuple(nodes))}
    mesh = GmshMeshData(Path("tet10_wp05.msh"), "4.1", False, "wp05", nodes, cells, groups)
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "materials": {"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
        "groups": [
            {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": "TET10", "material": "solid"}]}
        ],
    }
    imported = GmshModelImporter().from_data(mesh, setup, repair_tetra_orientation=True)
    assert imported.model.elements[0].nodes == tuple(range(10))
    assert imported.report.orientation_repairs == 1
    assert Tet10Element.corner_signed_volume(imported.model.nodes[list(range(10))]) > 0.0


def test_tet10_default_and_code_aster5_rules_are_explicitly_distinct() -> None:
    default = tl_assembly("TET10", nonlinear_quadrature="hammer4")
    diagnostic = tl_assembly("TET10", nonlinear_quadrature="code_aster_5")
    assert len(default._kernels[0]._rule()) == 4
    assert len(diagnostic._kernels[0]._rule()) == 5
    displacement = affine_displacement(tet10_coordinates(), affine_deformation_gradient())
    assert diagnostic.strain_energy(displacement) == pytest.approx(default.strain_energy(displacement), rel=1.0e-12, abs=1.0e-14)


def test_tet10_tl_rejects_inverted_and_nonfinite_reference_geometry() -> None:
    coordinates = tet10_coordinates()
    inverted = coordinates[[0, 2, 1, 3, 4, 6, 5, 7, 9, 8]]
    with pytest.raises(ValueError, match="Invalid TET10 reference"):
        _assembly_from_coordinates("TET10", inverted).assemble(np.zeros(30))
    nonfinite = coordinates.copy()
    nonfinite[4, 0] = np.nan
    with pytest.raises(ValueError, match="nodes must be a finite|nodes must have"):
        _assembly_from_coordinates("TET10", nonfinite)


def _stress_tensor(values: object) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.asarray([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]])


def _assembly_from_coordinates(family: str, coordinates: np.ndarray) -> Any:
    model = model_for_family(family)
    model.nodes = np.asarray(coordinates, dtype=float)
    return build_total_lagrangian_assembly(model)
