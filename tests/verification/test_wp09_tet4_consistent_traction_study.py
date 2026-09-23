from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from scripts.run_wp09_tet4_consistent_traction_study import LEVELS, _load_balance, _mesh, _model
from solveur.mesh.validation import MeshValidator


def test_tet4_structured_hierarchy_has_expected_counts_and_positive_volumes() -> None:
    expected = ((8, 5, 24), (27, 40, 81), (64, 135, 192))
    for (_, cells), (nodes_expected, elements_expected, dofs_expected) in zip(LEVELS, expected):
        nodes, elements = _mesh(*cells)
        volumes = [abs(float(np.linalg.det((nodes[element[1:]] - nodes[element[0]]).T))) / 6.0 for element in elements]
        assert (len(nodes), len(elements), 3 * len(nodes)) == (nodes_expected, elements_expected, dofs_expected)
        assert all(volume > 0.0 for volume in volumes)


def test_tet4_uses_consistent_surface_traction_and_preserves_resultant_moment() -> None:
    for _, cells in LEVELS:
        model, surface = _model(cells)
        balance = _load_balance(model, surface)
        assert all(element.type == "TET4" for element in model.elements)
        assert all(load.type == "surface_traction" for load in model.distributed_loads)
        assert np.allclose(balance["integrated_resultant"], [0.25, 0.0, 0.0], atol=1.0e-12)
        assert np.allclose(balance["integrated_moment_about_origin"], [0.0, 0.125, -0.125], atol=1.0e-12)
        assert balance["resultant_error_norm"] <= 1.0e-12
        assert balance["moment_error_norm"] <= 1.0e-12
        assert balance["production_vs_analytic_resultant_error_norm"] <= 1.0e-12
        assert balance["production_vs_analytic_moment_error_norm"] <= 1.0e-12


def test_tet4_study_keeps_bounded_r2_inputs_and_meshes_are_valid() -> None:
    for _, cells in LEVELS:
        model, _ = _model(cells)
        assert MeshValidator().validate(model).to_dict()["status"] == "PASS"
        parameters = model.analysis.parameters
        assert parameters["kinematics"] == "corotational_j2"
        assert parameters["corotational_max_local_strain"] == 0.05
        assert parameters["load_path"] == [0.25, 0.5, 0.75, 1.0]
        assert parameters["tolerance"] == 1.0e-9
        assert parameters["max_iterations"] == 40
        assert parameters["contact_mode"] == "none"


def test_independent_observable_checker_has_no_production_imports() -> None:
    source = Path("scripts/run_wp09_tet4_consistent_traction_reference.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported <= {"__future__", "argparse", "hashlib", "json", "pathlib", "typing", "numpy"}
