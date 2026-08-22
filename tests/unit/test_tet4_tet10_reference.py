"""Unit tests for the structured TET4/TET10 three-dimensional reference."""

from __future__ import annotations

import numpy as np

from solveur.large.generator import generate_tet4_cantilever_block
from solveur.large.io import load_large_model
from solveur.verification.tet4_tet10_reference import convert_structured_tet4_to_tet10
from solveur.verification.tet4_tet10_reference import run_tet4_tet10_reference


def test_conversion_creates_conforming_mid_edge_nodes_and_preserves_resultant(tmp_path) -> None:
    source = tmp_path / "model.npz"
    large = generate_tet4_cantilever_block(source, nx=2, ny=1, nz=1)
    model = convert_structured_tet4_to_tet10(load_large_model(source))

    assert all(item.type == "TET10" for item in model.elements)
    assert all(len(item.nodes) == 10 for item in model.elements)
    assert model.node_count > large.node_count
    assert sum(load.value for load in model.loads) == np.sum(large.load_values)


def test_conversion_fixes_midpoints_on_the_clamped_boundary(tmp_path) -> None:
    source = tmp_path / "model.npz"
    generate_tet4_cantilever_block(source, nx=2, ny=1, nz=1)
    model = convert_structured_tet4_to_tet10(load_large_model(source))

    fixed = {(condition.node, dof) for condition in model.fixed_dofs for dof in condition.dofs}
    root_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], 0.0))
    assert all((int(node), dof) in fixed for node in root_nodes for dof in ("UX", "UY", "UZ"))


def test_reference_runner_writes_machine_readable_artifacts(tmp_path) -> None:
    summary = run_tet4_tet10_reference(
        tmp_path / "study",
        base_nx=2,
        base_ny=1,
        base_nz=1,
        refinement_factors=(1, 2),
    )

    assert summary["study_id"] == "VNV-TET4-TET10-3D-REFERENCE-001"
    assert (tmp_path / "study" / "summary.json").is_file()
    assert (tmp_path / "study" / "convergence.png").stat().st_size > 0
    assert (tmp_path / "study" / "vnv_manifest.json").is_file()


def test_reference_runner_accepts_the_corrected_centered_load_contract(tmp_path) -> None:
    summary = run_tet4_tet10_reference(
        tmp_path / "centered-study",
        base_nx=1,
        base_ny=1,
        base_nz=1,
        refinement_factors=(1, 2),
        decomposition="centered",
        load_distribution="surface_consistent",
        study_id="VNV-TET4-TET10-3D-REFERENCE-CORRECTED-002",
    )

    assert summary["study_id"] == "VNV-TET4-TET10-3D-REFERENCE-CORRECTED-002"
    assert summary["discretization"] == {
        "decomposition": "centered",
        "load_distribution": "surface_consistent",
        "same_mesh_tet4_tet10": True,
    }
