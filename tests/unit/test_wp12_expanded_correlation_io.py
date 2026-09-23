"""Tests for the expanded WP12 correlation runner/auditor boundary."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from scripts.audit_wp12_expanded_code_aster import _audit_comm_text, _audit_mesh_text
from scripts.run_wp12_expanded_code_aster import _comm_text, _mesh_text
from scripts.wp12_expanded_models import FAMILIES, LOADS, MATERIAL, build_case


def test_code_aster_inputs_represent_exact_generated_qf_mesh_and_loads(tmp_path: Path) -> None:
    for family in FAMILIES:
        case = build_case(family, "rectangular_beam", "H2", "combined_xyz")
        mail_path = tmp_path / f"{case.case_id}.mail"
        comm_path = tmp_path / f"{case.case_id}.comm"
        mail_path.write_text(_mesh_text(case), encoding="ascii")
        comm_path.write_text(_comm_text(case), encoding="utf-8")

        mesh_errors = _audit_mesh_text(mail_path, case.family, case.model.nodes, case.connectivity)
        comm_errors = _audit_comm_text(comm_path, case.system.loads.reshape(-1, 3), MATERIAL, case.case_id)

        assert mesh_errors == []
        assert comm_errors == []


def test_all_frozen_load_vectors_have_the_same_declared_resultant_magnitude() -> None:
    for resultant in LOADS.values():
        assert np.isclose(np.linalg.norm(resultant), 1000.0, rtol=1e-14, atol=1e-12)


def test_independent_auditor_does_not_import_qf_solver_or_runner() -> None:
    tree = ast.parse(Path("scripts/audit_wp12_expanded_code_aster.py").read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "solveur" not in imported_roots
    assert "run_wp12_expanded_code_aster" not in imported_roots
    assert "wp12_expanded_models" not in imported_roots
