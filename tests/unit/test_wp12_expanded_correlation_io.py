"""Tests for the expanded WP12 correlation runner/auditor boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from scripts import run_wp12_expanded_code_aster as runner
from scripts.audit_wp12_expanded_code_aster import _audit_comm_text, _audit_mesh_text
from scripts.run_wp12_expanded_code_aster import IMAGE, _aster_node_name, _comm_text, _mesh_text, validate_external_configuration
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


def test_code_aster_mesh_records_stay_within_the_80_column_format_limit() -> None:
    for family in FAMILIES:
        case = build_case(family, "slender_beam", "H3", "combined_xyz")
        lines = _mesh_text(case).splitlines()
        coordinate_start = lines.index("COOR_3D") + 1
        coordinate_end = lines.index("FINSF", coordinate_start)
        node_records = lines[coordinate_start:coordinate_end]
        element_start = lines.index("HEXA20") + 1 if family == "HEX20" else lines.index(
            {"TET4": "TETRA4", "HEX8": "HEXA8", "TET10": "TETRA10"}[family]
        ) + 1
        element_end = lines.index("FINSF", element_start)
        mesh_records = lines[element_start:element_end]
        assert max(map(len, lines)) <= 80
        assert [line.split()[0] for line in node_records] == [_aster_node_name(i) for i in range(len(case.model.nodes))]
        assert len(mesh_records) == len(case.connectivity)
        assert all(len(line.split()) == case.connectivity.shape[1] + 1 for line in mesh_records)
        assert _aster_node_name(25) == "Z"
        assert _aster_node_name(26) == "AA"


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


def test_external_resource_contract_is_validated_before_case_execution() -> None:
    valid = {
        "timeout_seconds": 900,
        "memory_limit_mb": 4096,
        "code_aster_version": "18.1.0",
        "code_aster_image": IMAGE,
        "code_aster_image_id": "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435",
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": IMAGE,
            "image_id": "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435",
            "modelisation": "3D",
            "fresh_container_per_case": True,
            "cpu_limit": 1,
            "mpi": False,
            "action": "make_etude",
            "timeout_seconds": 900,
            "memory_limit_mb": 4096,
        },
    }
    assert validate_external_configuration(valid) == (900, 4096)

    del valid["timeout_seconds"]
    try:
        validate_external_configuration(valid)
    except RuntimeError as exc:
        assert "timeout/memory" in str(exc)
    else:
        raise AssertionError("Missing root resource field must fail closed")


def test_campaign_stops_after_first_execution_exception(tmp_path: Path, monkeypatch) -> None:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "output_root": "raw",
                "manifest_path": "manifest.json",
                "runner_sha": "runner",
                "model_builder_sha": "builder",
                "auditor_sha": "auditor",
                "contract_builder_sha": "freezer",
                "limitations": [],
            }
        ),
        encoding="utf-8",
    )
    cases = [SimpleNamespace(case_id="first", family="TET4"), SimpleNamespace(case_id="second", family="HEX8")]
    readiness = {
        "branch": "test",
        "execution_sha": "execution",
        "contract_sha256": "contract-hash",
        "code_aster_image_id": "image-id",
        "code_aster_runtime_version": "code_aster test",
    }
    executed: list[str] = []

    def fake_run(case, case_path, contract, preflight_result):
        executed.append(case.case_id)
        raise runner.CampaignError("simulated external execution failure")

    monkeypatch.setattr(runner, "preflight", lambda contract, root: (readiness, cases))
    monkeypatch.setattr(runner, "_run_case", fake_run)

    summary = runner.execute(contract_path, tmp_path)

    assert executed == ["first"]
    assert summary["status"] == "FAIL_CLOSED"
    assert summary["attempted_case_count"] == 1
    assert summary["not_started_case_count"] == 1
    assert summary["execution_aborted_on_error"] is True
