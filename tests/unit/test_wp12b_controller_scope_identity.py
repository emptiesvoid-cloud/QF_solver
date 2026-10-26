"""Synthetic checks that WP12-B tests use their exact registered controller scope."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from wp12b_test_support import WP12B_WORKTREE_ID, require_controller_scope


CONTROLLER_POLICY = Path(r"E:\QFSolverAgents\wp12b-canonical\development_autonomous_policy.json")
WP12B_NODEIDS = {
    "tests/unit/test_wp12b_beam2_continuity.py::test_wp12b_beam2_rotated_uniform_line_load",
    "tests/unit/test_wp12b_tet10_curved_load.py::test_wp12b_tet10_curved_face_pressure_solve",
    "tests/unit/test_wp12b_hex20_affine_patch.py::test_wp12b_hex20_uniaxial_traction_patch",
}
NODEID_MODULES = {
    "tests/unit/test_wp12b_beam2_continuity.py": "test_wp12b_beam2_rotated_uniform_line_load",
    "tests/unit/test_wp12b_tet10_curved_load.py": "test_wp12b_tet10_curved_face_pressure_solve",
    "tests/unit/test_wp12b_hex20_affine_patch.py": "test_wp12b_hex20_uniaxial_traction_patch",
}


def _declared_scope_id(module_path: Path, function_name: str) -> str | None:
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    function = next(item for item in module.body if isinstance(item, ast.FunctionDef) and item.name == function_name)
    call = next(
        item
        for item in ast.walk(function)
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == "require_controller_scope"
    )
    scope = next(keyword.value for keyword in call.keywords if keyword.arg == "expected_worktree_id")
    return scope.value if isinstance(scope, ast.Constant) and isinstance(scope.value, str) else None


def test_wp12b_scope_guard_matches_exact_controller_registration(monkeypatch, tmp_path) -> None:
    policy = json.loads(CONTROLLER_POLICY.read_text(encoding="utf-8"))
    registration = policy["worktrees"][WP12B_WORKTREE_ID]
    repo_root = Path(__file__).resolve().parents[2]

    assert WP12B_WORKTREE_ID == "wp12_elements_loads"
    assert Path(registration["git_root"]).resolve() == repo_root
    assert set(registration["allowed_nodeids"]) == WP12B_NODEIDS
    for module_path, function_name in NODEID_MODULES.items():
        assert _declared_scope_id(repo_root / module_path, function_name) == WP12B_WORKTREE_ID

    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    monkeypatch.setenv("QF_DEVELOPMENT_AUTONOMOUS", "1")
    monkeypatch.setenv("QF_DEV_SELECTED_DOFS", "12")
    monkeypatch.setenv("QF_DEV_EVIDENCE_ROOT", str(evidence_root))

    monkeypatch.setenv("QF_DEV_WORKTREE_ID", WP12B_WORKTREE_ID)
    assert require_controller_scope(12, expected_worktree_id="wp12_elements_loads") == evidence_root

    monkeypatch.setenv("QF_DEV_WORKTREE_ID", "wp12_elements")
    with pytest.raises(RuntimeError, match="wrong controller worktree ID"):
        require_controller_scope(12, expected_worktree_id="wp12_elements_loads")
    with pytest.raises(RuntimeError, match="test declares the wrong controller worktree ID"):
        require_controller_scope(12, expected_worktree_id="wp12_elements")
