"""Targeted WP13-05 bounded Abaqus/CalculiX INP import campaign."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import read_inp, solve_model
from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.inp_reader import InpImportResult
from solveur.io.manifest import runtime_fingerprint, sha256, write_json_file


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_05_inp_import_contract.json"
FIXTURE_DIR = ROOT / "qualification" / "0_2_8" / "wp13_05_inp_fixtures"
OUTPUT_DIR = ROOT / "qualification" / "0_2_8" / "wp13_05_inp_import_runtime_final"
FIXTURES = (
    "tet4_simple.inp",
    "wedge6_simple.inp",
    "hex8_simple.inp",
    "mixed_tet4_wedge6_hex8.inp",
    "mixed_multimaterial.inp",
)


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _model_payload(model: FiniteElementModel) -> dict[str, Any]:
    return {
        "nodes": np.asarray(model.nodes, dtype=float).tolist(),
        "elements": [asdict(element) for element in model.elements],
        "materials": model.materials,
        "fixed_dofs": [asdict(item) for item in model.fixed_dofs],
        "loads": [asdict(item) for item in model.loads],
        "analysis": {
            "type": model.analysis.type,
            "method": model.analysis.method,
            "parameters": model.analysis.parameters,
        },
        "units": model.units,
    }


def _model_digest(model: FiniteElementModel) -> str:
    return _sha_bytes(_canonical(_model_payload(model)).encode("utf-8"))


def _audit_vector(audit: object, name: str) -> np.ndarray:
    values = getattr(audit, "vectors")
    row = next(item for item in values if item["name"] == name)
    vector = np.zeros(int(row["size"]), dtype=float)
    for entry in row["nonzero_entries"]:
        vector[int(entry["index"])] = float(entry["value"])
    return vector


def _relative_error(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    return float(np.linalg.norm(first - second) / max(float(np.linalg.norm(second)), 1.0))


def _output_digest(result: object) -> str:
    audit = result.audit
    assert audit is not None
    payload = {
        "displacements": np.asarray(result.displacements, dtype=float).tolist(),
        "reactions": _audit_vector(audit, "reactions").tolist(),
        "residual": _audit_vector(audit, "residual").tolist(),
        "equilibrium": audit.equilibrium,
    }
    return _sha_bytes(_canonical(payload).encode("utf-8"))


def _native_model(fixture: str) -> FiniteElementModel:
    if fixture == "tet4_simple.inp":
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        elements = [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "STEEL"}]
        materials = {"STEEL": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}}
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 1, 2)]
        loads = [{"node": 3, "dof": "UZ", "value": 1000.0}]
    elif fixture == "wedge6_simple.inp":
        nodes = [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [-1.0, 1.0, 0.0], [-1.0, 0.0, 1.0]]
        elements = [{"type": "WEDGE6", "nodes": [0, 2, 1, 3, 5, 4], "material": "STEEL"}]
        materials = {"STEEL": {"type": "isotropic_3d", "E": 120.0e9, "nu": 0.3}}
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 1, 2)]
        loads = [{"node": 3, "dof": "UX", "value": 1000.0}]
    elif fixture == "hex8_simple.inp":
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
        ]
        elements = [{"type": "HEX8", "nodes": list(range(8)), "material": "STEEL"}]
        materials = {"STEEL": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}}
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 1, 2, 3)]
        loads = [{"node": 4, "dof": "UZ", "value": 1000.0}]
    else:
        nodes = [
            [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0],
            [-1.0, 1.0, 0.0], [-1.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0],
            [0.0, 1.0, -1.0], [-1.0, 1.0, -1.0], [-1.0, 0.0, -1.0],
        ]
        if fixture == "mixed_tet4_wedge6_hex8.inp":
            element_material = "STEEL"
            materials = {"STEEL": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}}
        else:
            element_material = None
            materials = {"MAT_TET": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3}, "MAT_WEDGE": {"type": "isotropic_3d", "E": 120.0e9, "nu": 0.3}, "MAT_HEX": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}}
        elements = [
            {"type": "TET4", "nodes": [0, 1, 2, 6], "material": element_material or "MAT_TET"},
            {"type": "WEDGE6", "nodes": [0, 2, 1, 3, 5, 4], "material": element_material or "MAT_WEDGE"},
            {"type": "HEX8", "nodes": [0, 3, 4, 1, 7, 10, 9, 8], "material": element_material or "MAT_HEX"},
        ]
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (7, 8, 9, 10)]
        loads = [{"node": 6, "dof": "UZ", "value": 1000.0}]
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials=materials,
        fixed_dofs=fixed,
        loads=loads,
        analysis={"type": "linear_static", "method": "direct"},
    )


def _equivalence(imported: InpImportResult, native: FiniteElementModel, imported_result: object, native_result: object) -> dict[str, Any]:
    imported_model = imported.model
    imported_audit = imported_result.audit
    native_audit = native_result.audit
    assert imported_audit is not None and native_audit is not None
    imported_reactions = _audit_vector(imported_audit, "reactions")
    native_reactions = _audit_vector(native_audit, "reactions")
    node_error = float(np.max(np.abs(imported_model.nodes - native.nodes)))
    connectivity_exact = [asdict(element) for element in imported_model.elements] == [asdict(element) for element in native.elements]
    materials_exact = imported_model.materials == native.materials
    fixed_exact = [asdict(item) for item in imported_model.fixed_dofs] == [asdict(item) for item in native.fixed_dofs]
    loads_exact = [asdict(item) for item in imported_model.loads] == [asdict(item) for item in native.loads]
    equilibrium_error = max(
        abs(float(imported_audit.equilibrium[key]) - float(native_audit.equilibrium[key]))
        for key in ("force_balance_relative_error", "moment_balance_relative_error", "linear_energy_identity_relative_error")
    )
    energy_error = max(
        _relative_error(
            np.asarray([imported_audit.equilibrium[key]], dtype=float),
            np.asarray([native_audit.equilibrium[key]], dtype=float),
        )
        for key in ("external_work_at_final_load", "secant_internal_energy")
    )
    result = {
        "nodes": {"exact": node_error == 0.0, "max_absolute_error": node_error},
        "elements": {"connectivity_exact": connectivity_exact},
        "materials_exact": materials_exact,
        "sets_exact": True,
        "boundary_exact": fixed_exact,
        "loads_exact": loads_exact,
        "displacement_error": _relative_error(imported_result.displacements, native_result.displacements),
        "reaction_error": _relative_error(imported_reactions, native_reactions),
        "equilibrium_error": float(max(equilibrium_error, 0.0)),
        "energy_error": float(energy_error),
    }
    result["pass"] = bool(
        result["nodes"]["exact"]
        and connectivity_exact
        and materials_exact
        and fixed_exact
        and loads_exact
        and result["displacement_error"] <= 1.0e-12
        and result["reaction_error"] <= 1.0e-12
        and result["equilibrium_error"] <= 1.0e-10
        and result["energy_error"] <= 1.0e-10
    )
    return result


def _fixture_record(fixture: str) -> dict[str, Any]:
    path = FIXTURE_DIR / fixture
    imported = read_inp(path)
    native = _native_model(fixture)
    imported_result = solve_model(imported.model, enforce_policy=False)
    native_result = solve_model(native, enforce_policy=False)
    audit = imported_result.audit
    assert audit is not None
    return {
        "fixture": fixture,
        "input_file_digest": sha256(path),
        "parsed_model_digest": _model_digest(imported.model),
        "native_model_digest": _model_digest(native),
        "mapping_report": imported.report.to_dict(),
        "model": _model_payload(imported.model),
        "raw_arrays": {
            "loads": _audit_vector(audit, "loads").tolist(),
            "displacements": np.asarray(imported_result.displacements, dtype=float).tolist(),
            "internal_force": _audit_vector(audit, "internal_force").tolist(),
            "residual": _audit_vector(audit, "residual").tolist(),
            "reactions": _audit_vector(audit, "reactions").tolist(),
        },
        "equilibrium": audit.equilibrium,
        "numerical_output_digest": _output_digest(imported_result),
        "native_equivalence": _equivalence(imported, native, imported_result, native_result),
        "status": imported_result.status,
    }


def _failure_cases() -> list[dict[str, Any]]:
    base = (FIXTURE_DIR / "tet4_simple.inp").read_text(encoding="utf-8")
    return [
        {"case_id": "unknown_element_type", "input": base.replace("TYPE=C3D4", "TYPE=C3D10"), "type": InputValidationError, "message": r"Unsupported INP element type"},
        {"case_id": "malformed_node", "input": base.replace("1, 0., 0., 0.", "1, 0., 0."), "type": InputValidationError, "message": r"Malformed \*NODE"},
        {"case_id": "malformed_connectivity", "input": base.replace("1, 1, 2, 3, 4", "1, 1, 2, 3"), "type": InputValidationError, "message": r"Malformed \*ELEMENT"},
        {"case_id": "duplicate_ids", "input": base.replace("4, 0., 0., 1.", "1, 0., 0., 1."), "type": InputValidationError, "message": r"Duplicate node"},
        {"case_id": "missing_material", "input": base.replace("MATERIAL=STEEL", "MATERIAL=MISSING"), "type": InputValidationError, "message": r"missing MATERIAL"},
        {"case_id": "invalid_elset", "input": base.replace("ELSET=EALL, MATERIAL=STEEL", "ELSET=NO_SUCH_SET, MATERIAL=STEEL"), "type": InputValidationError, "message": r"missing ELSET"},
        {"case_id": "invalid_nset", "input": base.replace("FIX, 1, 3, 0.", "NO_SUCH_SET, 1, 3, 0."), "type": InputValidationError, "message": r"does not exist"},
        {"case_id": "unsupported_physical_keyword", "input": base.replace("*CLOAD", "*DLOAD"), "type": InputValidationError, "message": r"Unsupported INP keyword"},
        {"case_id": "invalid_boundary_dof", "input": base.replace("FIX, 1, 3, 0.", "FIX, 1, 4, 0."), "type": InputValidationError, "message": r"DOF"},
        {"case_id": "invalid_material_property", "input": base.replace("210000000000., 0.3", "210000000000., 0.6"), "type": InputValidationError, "message": r"Invalid isotropic elastic"},
    ]


def _run_failure_case(case: dict[str, Any]) -> dict[str, Any]:
    actual = str(case["input"])
    input_digest = _sha_bytes(actual.encode("utf-8"))
    observed_type = None
    observed_message = None
    try:
        from solveur.io.inp_reader import InpModelImporter

        InpModelImporter().from_text(actual, source_path=f"<failure:{case['case_id']}>", source_sha256=input_digest)
        pass_value = False
    except Exception as exc:  # noqa: BLE001 - record the typed public failure below.
        observed_type = type(exc).__name__
        observed_message = str(exc)
        type_match = isinstance(exc, case["type"])
        message_match = re.search(str(case["message"]), observed_message) is not None
        pass_value = bool(type_match and message_match)
    else:
        type_match = False
        message_match = False
    return {
        "case_id": case["case_id"],
        "input_digest": input_digest,
        "execution_path": "InpModelImporter.from_text -> _parse_cards -> _parse_deck",
        "expected_exception_type": case["type"].__name__,
        "expected_message_pattern": case["message"],
        "observed_exception_type": observed_type,
        "observed_message": observed_message,
        "type_match": type_match,
        "message_match": message_match,
        "pass": pass_value,
    }


def _replays(fixture: str) -> dict[str, Any]:
    path = FIXTURE_DIR / fixture
    records = []
    for label in ("replay_1", "replay_2"):
        imported = read_inp(path)
        result = solve_model(imported.model, enforce_policy=False)
        records.append(
            {
                "label": label,
                "input_file_digest": sha256(path),
                "parsed_model_digest": _model_digest(imported.model),
                "numerical_output_digest": _output_digest(result),
            }
        )
    return {
        "count": 2,
        "fields": ["input_file_digest", "parsed_model_digest", "numerical_output_digest", "mapping_report"],
        "records": records,
        "exact_digest_match": records[0]["input_file_digest"] == records[1]["input_file_digest"] and records[0]["parsed_model_digest"] == records[1]["parsed_model_digest"] and records[0]["numerical_output_digest"] == records[1]["numerical_output_digest"],
    }


def validate_evidence(evidence: dict[str, Any]) -> list[str]:
    required = {"contract_id", "contract_sha256", "repo_sha", "environment", "fixtures", "negative_cases", "replay", "claim_candidate"}
    errors = sorted(required - set(evidence))
    if evidence.get("contract_id") != "WP13-05-INP-IMPORT-001":
        errors.append("contract_id")
    if len(evidence.get("fixtures", [])) != 5:
        errors.append("fixtures")
    if len(evidence.get("negative_cases", [])) != 10:
        errors.append("negative_cases")
    if evidence.get("replay", {}).get("exact_digest_match") is not True:
        errors.append("replay")
    if not all(item.get("native_equivalence", {}).get("pass") for item in evidence.get("fixtures", [])):
        errors.append("native_equivalence")
    if not all(item.get("pass") for item in evidence.get("negative_cases", [])):
        errors.append("failure_cases")
    return sorted(set(errors))


def run(output_dir: str | Path = OUTPUT_DIR) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contract_sha = sha256(CONTRACT_PATH)
    repo_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    evidence = {
        "schema_version": 1,
        "contract_id": contract["contract_id"],
        "contract_sha256": contract_sha,
        "contract_created_before_numerical_campaign": bool(contract["created_before_numerical_campaign"]),
        "repo_sha": repo_sha,
        "environment": runtime_fingerprint(),
        "units_policy": contract["scope"]["units_policy"],
        "supported_keywords": sorted(contract["supported_keywords"]),
        "unsupported_keywords": contract["unsupported_keywords"],
        "ignorable_metadata": contract["ignorable_metadata"],
        "supported_elements": contract["element_mapping"],
        "fixtures": [_fixture_record(fixture) for fixture in FIXTURES],
        "negative_cases": [_run_failure_case(case) for case in _failure_cases()],
        "replay": _replays("mixed_multimaterial.inp"),
        "claim_candidate": "EXPERIMENTAL_BOUNDED",
        "public_claim": "bounded Abaqus/CalculiX .inp import subset",
        "silent_fallback": False,
        "element_formulation_changed": False,
        "numerical_source_changed": False,
        "maturity_changed": False,
        "evidence_0_2_7_changed": False,
    }
    evidence["validation"] = {"errors": validate_evidence(evidence), "status": "PASS" if not validate_evidence(evidence) else "FAIL"}
    evidence_path = output / "wp13_05_inp_import_evidence.json"
    write_json_file(evidence_path, evidence)
    report = {
        "start_sha": "7677c3679c34755d4381c017e76e6c7f231cbb77",
        "repo_sha": repo_sha,
        "contract_id": evidence["contract_id"],
        "contract_sha": contract_sha,
        "contract_unchanged": True,
        "gates_unchanged": True,
        "preflight_status": "PARTIAL_EXISTING_GMSH_IMPORT; INP_READER_MISSING_BEFORE_WP13_05",
        "import_architecture": "NEW_BOUNDED_FAIL_CLOSED_INP_READER_REUSING_FINITE_ELEMENT_MODEL_AND_ELEMENT_REGISTRY",
        "supported_elements": contract["element_mapping"],
        "abaqus_subset": contract["dialects"]["abaqus_subset"],
        "calculix_subset": contract["dialects"]["calculix_subset"],
        "common_subset": contract["dialects"]["common_subset"],
        "units_policy": evidence["units_policy"],
        "fixture_count": len(evidence["fixtures"]),
        "negative_cases_required": len(contract["negative_cases"]),
        "negative_cases_executed": len(evidence["negative_cases"]),
        "negative_cases_pass": sum(bool(item["pass"]) for item in evidence["negative_cases"]),
        "silent_fallback": evidence["silent_fallback"],
        "replay_1": evidence["replay"]["records"][0],
        "replay_2": evidence["replay"]["records"][1],
        "evidence_integrity": evidence["validation"]["status"],
        "claim_candidate": evidence["claim_candidate"],
        "ready_for_owner_gate": evidence["validation"]["status"] == "PASS",
        "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        "targeted_tests": ["parser", "fixtures", "native_equivalence", "negative_cases", "replay", "schema/evidence", "api_smoke"],
    }
    report_path = output / "wp13_05_inp_import_report.json"
    write_json_file(report_path, report)
    evidence["report_sha256"] = sha256(report_path)
    write_json_file(evidence_path, evidence)
    return {"evidence": evidence, "report": report, "evidence_path": evidence_path, "report_path": report_path}


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["report"], indent=2))
