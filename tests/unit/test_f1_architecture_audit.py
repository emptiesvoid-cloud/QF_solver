from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "qualification" / "0_2_7" / "f1_architecture_audit.json"
DOCUMENT_PATH = ROOT / "docs" / "verification" / "0_2_7" / "0_2_7_f1_architecture_audit.md"
START_SHA = "995531841c5203144889aaebd7fcfd906cc0622b"


def _audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_f1_audit_has_no_release_blocker() -> None:
    record = _audit()
    assert record["status"] == "PASS_WITH_LIMITATIONS"
    assert record["start_sha"] == START_SHA
    assert record["audit_source_sha"] == START_SHA
    assert record["finding_summary"] == {
        "P0": 0,
        "P1": 0,
        "P2": 7,
        "P3": 1,
        "p0_fixed": 0,
        "p1_fixed": 0,
    }
    assert record["decisions"]["numerical_source_changed"] is False
    assert record["decisions"]["maturity_promoted"] is False


def test_f1_finding_evidence_and_outputs_exist() -> None:
    record = _audit()
    assert DOCUMENT_PATH.is_file()
    assert record["files"]["source_files_changed"] == []
    for reference in record["evidence_refs"]:
        assert (ROOT / reference).is_file(), reference


def test_deferred_cycles_are_documented_and_runtime_importable() -> None:
    record = _audit()
    cycles = record["dependency_audit"]["deferred_cycles"]
    assert len(cycles) == 2
    expected = {
        frozenset({"solveur.api.public", "solveur.verification.mitc4_campaign"}),
        frozenset(
            {
                "solveur.verification.nonlinear_failure_runner",
                "solveur.verification.nonlinear_failure_campaign",
            }
        ),
    }
    assert {frozenset(item["modules"]) for item in cycles} == expected
    for module in sorted(expected.pop()):
        importlib.import_module(module)
    for module in sorted(expected.pop()):
        importlib.import_module(module)


def test_public_facades_and_maturity_boundaries_remain_explicit() -> None:
    qf_solver = importlib.import_module("qf_solver")
    solveur = importlib.import_module("solveur")
    assert qf_solver.__version__ == "0.2.7"
    assert solveur.__version__ == "0.2.7"
    assert "solve_model" in qf_solver.__all__
    assert "solve_model" in solveur.__all__

    from solveur.compatibility.preflight import check_compatibility

    assert check_compatibility("WEDGE6", "linear_static", "elastic").status == "EXPERIMENTAL_ROUTE"
    assert check_compatibility("WEDGE6", "modal", "elastic").status == "SUPPORTED_ROUTE"
    assert check_compatibility("WEDGE6", "transient_dynamic", "elastic").status == "UNSUPPORTED_ROUTE"
    assert (
        check_compatibility("HEX8", "linear_static", "finite_kinematic_j2").status
        == "NOT_QUALIFIED_ROUTE"
    )


def test_source_has_no_module_global_statement() -> None:
    violations: list[str] = []
    for path in (ROOT / "src" / "solveur").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(isinstance(node, ast.Global) for node in ast.walk(tree)):
            violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []
