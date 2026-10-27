"""Static-only checks for the HEX8-SRI execution boundary; never invoke FEM."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCIENCE_TEST = ROOT / "tests/verification/test_hex8_sri_convergence.py"


def _module_and_source() -> tuple[ast.Module, str]:
    source = SCIENCE_TEST.read_text(encoding="utf-8")
    return ast.parse(source, filename=str(SCIENCE_TEST)), source


def _function(module: ast.Module, name: str) -> ast.FunctionDef:
    match = next(
        node for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    )
    assert isinstance(match, ast.FunctionDef)
    return match


def _call_line(function: ast.FunctionDef, called_name: str) -> int:
    return min(
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == called_name
    )


def test_execution_contract_is_bound_to_the_exact_scope_and_owner_evidence() -> None:
    module, _source = _module_and_source()
    authorized_case = _function(module, "_authorized_case")
    module_strings = {
        node.value for node in ast.walk(module) if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    guard_strings = {
        node.value
        for node in ast.walk(authorized_case)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    required = {
        "QF-HEX8SRI-EXECUTION-CONTRACT: hex8sri-convergence24-v1",
        "QF_DEV_EXECUTION_MANIFEST_PATH",
        "QF_DEV_EXECUTION_MANIFEST_SHA256",
        "QF_DEV_OWNER_DECISION_ID",
        "QF_DEV_CASE_MANIFEST_PATH",
        "QF_DEV_PREFLIGHT_ID",
        "QF_DEV_PREFLIGHT_SHA256",
        "QF_DEV_TARGET_NODEID",
        "QF_DEV_CONTROLLER_ROOT",
        "QF_DEV_CONTROLLER_BRANCH",
        "QF_DEV_CONTROLLER_HEAD",
        "QF_DEV_CONTROLLER_RUNNER_SHA256",
        "QF_DEV_CONTROLLER_POLICY_SHA256",
        "QF_DEV_CONTROLLER_PLUGIN_SHA256",
        "hex8sri-convergence24",
        "OWNER_AUTHORIZED",
    }
    assert required.issubset(module_strings)
    assert "QF-HEX8SRI-EXECUTION-CONTRACT: hex8sri-convergence24-v1" in guard_strings
    assert "hex8sri" not in module_strings
    assert "codex/hex8sri-controller-registration" not in module_strings


def test_authorization_and_evidence_writes_precede_fem_and_assertions() -> None:
    module, _source = _module_and_source()
    test_case = _function(module, "test_convergence_case")
    authorization_line = _call_line(test_case, "_authorized_case")
    fem_line = _call_line(test_case, "run_convergence_case")
    start_write_line = _call_line(test_case, "atomic_write_json_new")
    state_write_line = _call_line(test_case, "atomic_write_new_bytes")
    first_assert_line = min(node.lineno for node in ast.walk(test_case) if isinstance(node, ast.Assert))
    sidecar_write_line = min(
        node.lineno
        for node in ast.walk(test_case)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "atomic_write_json_new"
        and any(isinstance(argument, ast.Name) and argument.id == "sidecar_path" for argument in node.args)
    )

    assert authorization_line < fem_line
    assert start_write_line < fem_line
    assert fem_line < state_write_line < sidecar_write_line < first_assert_line


def test_mesh_and_ddl_contract_is_checked_before_assembly() -> None:
    module, _source = _module_and_source()
    test_case = _function(module, "test_convergence_case")
    fem_line = _call_line(test_case, "run_convergence_case")
    assigned_names = {
        node.id for node in ast.walk(test_case) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    required_checks = {
        "expected_node_count",
        "expected_dof_count",
        "expected_fixed_dof_count",
        "expected_free_dof_count",
        "mesh",
        "loading",
        "boundary_conditions",
        "material",
    }
    assert required_checks.issubset(assigned_names)
    assert all(
        node.lineno < fem_line
        for node in ast.walk(test_case)
        if isinstance(node, ast.Name) and node.id in required_checks
    )
