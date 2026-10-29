"""Prospective VV3D case harness behind source-bound controller artifacts.

The scientific path imports the solver only after runner, manifest, preflight,
decision and reservation evidence have been checked. Those checks remain a
workflow gate, not a security sandbox or cryptographic Owner identity service.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from experiments.wp12_vv3d_adaptive import criteria_evaluator, evidence

CAMPAIGN_DIR = Path(__file__).parent / "prepared_20261029"
MATRIX_PATH = CAMPAIGN_DIR / "MATRIX_NOT_AUTHORIZED.json"
VV3D_LEDGER_FILENAME = "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl"
NOT_AUTHORIZED_FINGERPRINT = "0" * 64

OBSERVABLES = (
    "displacement_l2_m_5_2",
    "energy_error_norm_sqrt_j",
    "strain_l2",
    "stress_l2_pa",
    "strain_samples",
    "stress_samples_pa",
    "strain_energy_j",
    "external_work_j",
    "free_residual_n",
    "free_relative_residual",
    "vv3d_free_residual_relative",
    "energy_identity_relative",
    "scalar_energy_relative_error",
    "force_closure_relative",
    "moment_closure_relative",
    "reaction_force_n",
    "reaction_moment_nm",
    "reaction_entries_n",
    "force_closure_n",
    "moment_closure_nm",
    "solver_origin",
    "elapsed_seconds",
    "peak_rss_mib",
    "independent_quadrature_8_12",
    "load_quadrature_8_12",
    "minimum_affine_jacobian_m3",
    "vv3d_free_residual_relative",
    "energy_identity_relative",
    "force_closure_relative",
    "moment_closure_relative",
    "quadrature_relative_difference",
    "nodal_displacements_m",
    "nodal_loads_n",
)
CRITERIA = (
    "field_error",
    "energy_error",
    "equilibrium",
    "force_balance",
    "moment_balance",
    "three_level_convergence",
)
_PERMIT_CONTEXT_KEYS = (
    "campaign_id", "case_id", "nodeid", "manifest_sha256",
    "scientific_fingerprint", "controller_fingerprint",
)


def sanitize_for_evidence(value: Any) -> Any:
    """Preserve nonfinite observations explicitly instead of dropping the evidence."""
    if isinstance(value,float) and not math.isfinite(value):
        return {"status":"NONFINITE", "representation":repr(value)}
    if isinstance(value,dict):
        return {str(key):sanitize_for_evidence(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):
        return [sanitize_for_evidence(item) for item in value]
    if hasattr(value,"tolist"):
        return sanitize_for_evidence(value.tolist())
    return value


def load_prepared_cases() -> list[dict[str, Any]]:
    """Load and hash-check the immutable prepared matrix without solver imports."""
    matrix_raw = MATRIX_PATH.read_bytes()
    matrix = json.loads(matrix_raw)
    if matrix.get("state") != "PREPARATION_AUTHORIZED_EXECUTION_NOT_AUTHORIZED":
        raise ValueError("VV3D matrix is not in its expected preparation-only state")
    if matrix.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1":
        raise ValueError("unexpected VV3D campaign identity")
    cases = matrix.get("cases")
    expected = {f"VV3D-{family}-L{level}" for family in ("TET4", "TET10", "HEX8", "HEX20")
                for level in (1, 2, 3)}
    if (not isinstance(cases, list) or len(cases) != len(expected)
            or any(not isinstance(case,dict) for case in cases)
            or {case.get("case_id") for case in cases} != expected):
        raise ValueError("prepared case inventory does not match the twelve expected cases")
    for case in cases:
        expected_nodeid = _expected_nodeid(case.get("case_id", ""))
        if (case.get("execution_authorized") is not False or case.get("do_not_execute") is not True
                or case.get("nodeid_status") != "PREPARED_NOT_AUTHORIZED"
                or case.get("nodeid") != expected_nodeid):
            raise ValueError(f"case is not fail-closed: {case.get('case_id')}")
        mesh_name=case.get("mesh_file")
        if (not isinstance(mesh_name,str) or not mesh_name or "\\" in mesh_name
                or Path(mesh_name).name != mesh_name or mesh_name in {".",".."}):
            raise ValueError("prepared mesh filename escapes its directory")
        mesh_path = CAMPAIGN_DIR / mesh_name
        if hashlib.sha256(mesh_path.read_bytes()).hexdigest() != case.get("mesh_sha256"):
            raise ValueError(f"prepared mesh hash mismatch: {case.get('case_id')}")
    return cases


def _expected_nodeid(case_id: str) -> str:
    return ("tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case"
            f"[{case_id}]")


def require_authorized_execution(case_id: str) -> dict[str, Any]:
    """Check runner-provided identity and raw authorized-manifest bytes.

    Environment values alone are not authentication. The official parent runner
    must validate Owner approval, preflight, source and controller before it
    starts this exact child nodeid; this check detects stale or mismatched data.
    """
    cases = {case["case_id"]: case for case in load_prepared_cases()}
    if case_id not in cases:
        raise PermissionError("case is outside the closed initial VV3D catalogue")
    case = cases[case_id]
    names = {
        "case_id": "QF_DEV_VV3D_CASE_ID",
        "nodeid": "QF_DEV_TARGET_NODEID",
        "manifest_path": "QF_DEV_MANIFEST_PATH",
        "manifest_sha256": "QF_DEV_MANIFEST_SHA256",
        "authorization_id": "QF_DEV_AUTHORIZATION_ID",
        "scientific_fingerprint": "QF_DEV_VV3D_SCIENCE_FINGERPRINT",
        "controller_fingerprint": "QF_DEV_CONTROLLER_FINGERPRINT",
        "evidence_root": "QF_DEV_EVIDENCE_ROOT",
        "runner_receipt_path": "QF_DEV_VV3D_RUNNER_RECEIPT_PATH",
        "runner_receipt_sha256": "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256",
    }
    context = {key: os.environ.get(name, "") for key, name in names.items()}
    context["campaign_id"] = "WP12-VV3D-ADAPTIVE-20261029-R1"
    if (context["case_id"] != case_id or context["nodeid"] != _expected_nodeid(case_id)
            or not all(context.values())
            or not re.fullmatch(r"[0-9a-f]{64}", context["manifest_sha256"])
            or not re.fullmatch(r"[0-9a-f]{64}", context["scientific_fingerprint"])
            or not re.fullmatch(r"[0-9a-f]{64}", context["controller_fingerprint"])
            or not re.fullmatch(r"[0-9a-f]{64}", context["runner_receipt_sha256"])
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", context["authorization_id"])):
        raise PermissionError("missing or mismatched official VV3D runner context")
    try:
        path = Path(context["manifest_path"]).resolve(strict=True)
        raw = path.read_bytes()
    except OSError as exc:
        raise PermissionError("authorized VV3D manifest is unavailable") from exc
    if hashlib.sha256(raw).hexdigest() != context["manifest_sha256"]:
        raise PermissionError("authorized VV3D manifest raw SHA-256 mismatch")
    try:
        def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        manifest = json.loads(raw, object_pairs_hook=unique_pairs,
                              parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("authorized VV3D manifest is not strict JSON") from exc
    expected = {
        "schema": "qf-wp12-vv3d-case-manifest-v1",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": case_id,
        "nodeid": context["nodeid"],
        "state": "OWNER_AUTHORIZED",
        "execution_authorized": True,
        "do_not_execute": False,
        "mesh_sha256": case["mesh_sha256"],
        "selected_dofs": case["dofs"],
        "timeout_seconds": case["timeout_max_seconds"],
        "rss_soft_limit_mib": case["rss_soft_limit_mib"],
        "max_attempts": case["attempts_max"],
        "authorization_id": context["authorization_id"],
        "scientific_fingerprint": context["scientific_fingerprint"],
        "controller_fingerprint": context["controller_fingerprint"],
    }
    if not isinstance(manifest, dict) or any(manifest.get(key) != value for key, value in expected.items()):
        raise PermissionError("VV3D manifest does not bind this case, identity and budget")
    decision = manifest.get("owner_decision")
    if (not isinstance(decision, dict) or decision.get("status") != "APPROVED"
            or decision.get("approved_by") != "Owner"
            or not isinstance(decision.get("decision_id"), str) or not decision["decision_id"]):
        raise PermissionError("VV3D manifest has no explicit Owner decision")
    decision_sha256 = decision.get("decision_sha256")
    if not isinstance(decision_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", decision_sha256):
        raise PermissionError("VV3D manifest does not bind the raw Owner decision digest")
    preflight = manifest.get("preflight")
    if (not isinstance(preflight, dict) or preflight.get("nodeid") != context["nodeid"]
            or preflight.get("status") != "PREFLIGHT_PASS"
            or not isinstance(preflight.get("receipt_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", preflight["receipt_sha256"])
            or not isinstance(preflight.get("receipt_path"), str)):
        raise PermissionError("VV3D manifest has no exact successful preflight binding")
    try:
        receipt_path = Path(preflight["receipt_path"]).resolve(strict=True)
        receipt_raw = receipt_path.read_bytes()
    except OSError as exc:
        raise PermissionError("VV3D preflight receipt is unavailable") from exc
    if hashlib.sha256(receipt_raw).hexdigest() != preflight["receipt_sha256"]:
        raise PermissionError("VV3D preflight receipt SHA-256 mismatch")
    try:
        receipt = json.loads(receipt_raw, object_pairs_hook=unique_pairs,
                             parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("VV3D preflight receipt is not strict JSON") from exc
    if (not isinstance(receipt, dict) or receipt.get("nodeid") != context["nodeid"]
            or receipt.get("status") != "PREFLIGHT_PASS"
            or receipt.get("bodies_executed") is not False
            or receipt.get("reservation_created") is not False
            or receipt.get("selected_nodeids") != [context["nodeid"]]
            or receipt.get("skipped") not in (0, [])):
        raise PermissionError("VV3D preflight receipt does not attest a clean exact-node collect-only run")
    try:
        runner_receipt_path = Path(context["runner_receipt_path"]).resolve(strict=True)
        runner_receipt_raw = runner_receipt_path.read_bytes()
        runner_receipt = json.loads(
            runner_receipt_raw, object_pairs_hook=unique_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("VV3D runner reservation receipt is unavailable or invalid") from exc
    if hashlib.sha256(runner_receipt_raw).hexdigest() != context["runner_receipt_sha256"]:
        raise PermissionError("VV3D runner reservation receipt SHA-256 mismatch")
    reservation_id = runner_receipt.get("reservation_id") if isinstance(runner_receipt, dict) else None
    attempt_id = runner_receipt.get("attempt_id") if isinstance(runner_receipt, dict) else None
    if (not isinstance(runner_receipt, dict)
            or runner_receipt.get("schema") != "qf-wp12-vv3d-runner-reservation-v1"
            or runner_receipt.get("status") != "RESERVED"
            or runner_receipt.get("campaign_id") != context["campaign_id"]
            or runner_receipt.get("case_id") != case_id
            or runner_receipt.get("nodeid") != context["nodeid"]
            or runner_receipt.get("manifest_sha256") != context["manifest_sha256"]
            or runner_receipt.get("preflight_receipt_sha256") != preflight["receipt_sha256"]
            or runner_receipt.get("decision_id") != decision.get("decision_id")
            or runner_receipt.get("decision_sha256") != decision_sha256
            or runner_receipt.get("authorization_id") != context["authorization_id"]
            or runner_receipt.get("scientific_fingerprint") != context["scientific_fingerprint"]
            or runner_receipt.get("controller_fingerprint") != context["controller_fingerprint"]
            or runner_receipt.get("ledger_scope_id") != "wp12_vv3d_adaptive"
            or not isinstance(runner_receipt.get("ledger_path"), str)
            or Path(runner_receipt.get("ledger_path", "")).name != VV3D_LEDGER_FILENAME
            or runner_receipt.get("selected_dofs") != case["dofs"]
            or runner_receipt.get("timeout_seconds") != case["timeout_max_seconds"]
            or runner_receipt.get("rss_soft_limit_mib") != case["rss_soft_limit_mib"]
            or runner_receipt.get("archive_size_limit_mib") != 256
            or runner_receipt.get("attempt_number") != 1
            or runner_receipt.get("max_attempts") != 1
            or runner_receipt.get("attempt_reserved") is not True
            or not isinstance(runner_receipt.get("ledger_sha256_after_reservation"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", runner_receipt["ledger_sha256_after_reservation"])
            or type(runner_receipt.get("campaign_attempts_used_after")) is not int
            or not 1 <= runner_receipt["campaign_attempts_used_after"] <= 24
            or type(runner_receipt.get("campaign_seconds_reserved_after")) is not int
            or not case["timeout_max_seconds"] <= runner_receipt["campaign_seconds_reserved_after"] <= 28_800
            or runner_receipt.get("evidence_root") != context["evidence_root"]
            or not isinstance(reservation_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", reservation_id)
            or not isinstance(attempt_id, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", attempt_id)):
        raise PermissionError("VV3D runner receipt does not bind an exact authorized one-attempt reservation")
    frozen_criteria = manifest.get("frozen_criteria")
    criteria_sha = manifest.get("criteria_sha256")
    if (not isinstance(frozen_criteria, list) or not frozen_criteria
            or not isinstance(criteria_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", criteria_sha)):
        raise PermissionError("VV3D manifest has no frozen criteria list and digest")
    criteria_raw = json.dumps(frozen_criteria, sort_keys=True, separators=(",", ":"),
                              allow_nan=False).encode("utf-8")
    if hashlib.sha256(criteria_raw).hexdigest() != criteria_sha:
        raise PermissionError("VV3D frozen criteria digest mismatch")
    supported_criteria = {
        "finite", "det_j_positive", "free_residual", "energy_identity",
        "force_closure", "moment_closure", "load_quadrature", "post_quadrature",
        "displacement_error_L3", "energy_error_L3", "stress_error_L3",
        "scalar_energy_error_L3", "displacement_order", "energy_order",
    }
    seen: set[str] = set()
    for rule in frozen_criteria:
        if (not isinstance(rule, dict) or set(rule) != {"id", "classification", "operator", "threshold", "unit"}
                or rule["id"] not in supported_criteria or rule["id"] in seen
                or rule["classification"] not in {"CASE_GATE", "CASE_DIAGNOSTIC", "CAMPAIGN_GATE",
                                                    "CAMPAIGN_GATE_DEFERRED"}):
            raise PermissionError("VV3D frozen criteria contain an unsupported or duplicate rule")
        seen.add(rule["id"])
        try:
            criteria_evaluator.evaluate(rule, [True] if rule["operator"] == "ALL_TRUE" else 0.0)
        except (TypeError, ValueError) as exc:
            raise PermissionError(f"VV3D frozen criterion is malformed: {rule['id']}") from exc
    mandatory = {"finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                 "moment_closure", "load_quadrature", "post_quadrature"}
    if not mandatory.issubset(seen) or any(
        next(rule for rule in frozen_criteria if rule["id"] == name)["classification"] != "CASE_GATE"
        for name in mandatory
    ):
        raise PermissionError("VV3D case gates are incomplete or reclassified")
    campaign_rules = {
        "displacement_error_L3", "energy_error_L3", "stress_error_L3", "scalar_energy_error_L3",
        "displacement_order", "energy_order",
    }
    if any(rule["classification"] not in {"CAMPAIGN_GATE", "CAMPAIGN_GATE_DEFERRED"}
           for rule in frozen_criteria if rule["id"] in campaign_rules):
        raise PermissionError("VV3D multi-mesh criteria cannot be classified as per-case gates")
    context["frozen_criteria"] = frozen_criteria
    context["criteria_sha256"] = criteria_sha
    context["manifest_path"] = str(path)
    context["attempt_id"] = attempt_id
    context["reservation_id"] = reservation_id
    context["runner_receipt_sha256"] = hashlib.sha256(runner_receipt_raw).hexdigest()
    context["preflight_receipt_sha256"] = preflight["receipt_sha256"]
    context["owner_decision_sha256"] = decision_sha256
    return context


def run_prospective_case(
    case_id: str,
    attempt_id: str,
    evidence_root: Path,
    *,
    scientific_fingerprint: str,
    controller_fingerprint: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Prospective model/solve/postprocess body behind the runner receipt gate.

    The official runner must validate and reserve before writing the bound
    receipt. Sidecar persistence is in ``finally`` and precedes caller assertions.
    """
    execution_context = require_authorized_execution(case_id)

    # Imports with FEM effects are deliberately below the first fail-closed step.
    import time

    if (scientific_fingerprint != execution_context["scientific_fingerprint"]
            or controller_fingerprint != execution_context["controller_fingerprint"]
            or manifest_sha256 != execution_context["manifest_sha256"]
            or attempt_id != execution_context["attempt_id"]
            or evidence_root.resolve() != Path(execution_context["evidence_root"]).resolve()):
        raise PermissionError("caller fingerprints differ from the validated runner context")

    cases = {case["case_id"]: case for case in load_prepared_cases()}
    if case_id not in cases:
        raise ValueError(f"unknown prepared VV3D case: {case_id}")
    case = cases[case_id]
    payload = synthetic_not_exposed_payload(case_id, attempt_id)
    payload.update({
        "scientific_fingerprint": scientific_fingerprint,
        "controller_fingerprint": controller_fingerprint,
        "manifest_sha256": manifest_sha256,
        "owner_decision_sha256": execution_context["owner_decision_sha256"],
        "preflight_receipt_sha256": execution_context["preflight_receipt_sha256"],
        "runner_receipt_sha256": execution_context["runner_receipt_sha256"],
        "reservation_id": execution_context["reservation_id"],
        "case_level": case["level"],
        "formulation": case["formulation"],
        "case_state": "OWNER_AUTHORIZED_EXECUTION",
    })
    payload["execution"] = {
        "status": "STARTED", "attempt_reserved": True, "attempt_id": attempt_id,
        "reservation_id": execution_context["reservation_id"], "fem_started": False,
    }
    started = time.perf_counter()
    failure: BaseException | None = None
    try:
        from solveur.api.public import FiniteElementModel, recover_solid_stress_field, solve_model
        from experiments.wp12_vv3d_adaptive import field_error_draft, load_assembly_draft, metrics, oracle

        prepared = json.loads((CAMPAIGN_DIR / case["mesh_file"]).read_bytes())
        family = case["formulation"]
        denominator = prepared["integer_coordinate_denominator"]
        coordinates = [tuple(value / denominator for value in point) for point in prepared["nodes_integer"]]

        # This public adapter is itself fail-closed until its review/integration.
        # It must return the coherent nodal vector int(N^T f dV), in N.
        def permit_validator(candidate: dict[str, str]) -> bool:
            permit_context = {
                key: execution_context[key]
                for key in _PERMIT_CONTEXT_KEYS
            }
            return (candidate == permit_context
                    and hashlib.sha256(Path(execution_context["manifest_path"]).read_bytes()).hexdigest()
                    == execution_context["manifest_sha256"])

        load8 = load_assembly_draft.assemble_body_load(
            prepared, order=8,
            execution_context={key: execution_context[key] for key in _PERMIT_CONTEXT_KEYS},
            permit_validator=permit_validator,
        )
        nodal_load = load_assembly_draft.assemble_body_load(
            prepared, order=12,
            execution_context={key: execution_context[key] for key in _PERMIT_CONTEXT_KEYS},
            permit_validator=permit_validator,
        )
        if len(nodal_load) != 3 * len(coordinates) or not all(math.isfinite(value) for value in nodal_load):
            raise ValueError("body-load adapter returned an invalid global nodal vector")
        if len(load8) != len(nodal_load) or not all(math.isfinite(value) for value in load8):
            raise ValueError("comparison load quadrature returned an invalid global nodal vector")
        def nodal_triples(vector):
            return [tuple(vector[3*node+axis] for axis in range(3)) for node in range(len(coordinates))]
        zeros=[(0.0,0.0,0.0)]*len(coordinates)
        balance8=metrics.force_moment_balance(coordinates,nodal_triples(load8),zeros)
        balance12=metrics.force_moment_balance(coordinates,nodal_triples(nodal_load),zeros)
        exact_balance=oracle.exact_global_balance()
        load_quadrature = _load_quadrature_relative_diagnostics(
            tuple(load8), tuple(nodal_load), balance8, balance12, exact_balance,
        )
        payload["observables"]["load_quadrature_8_12"]={
            "status":"DIAGNOSTIC_UNQUALIFIED", "order_8":balance8, "order_12":balance12,
            "exact_body_force_n":exact_balance["body_force_n"],
            "exact_body_moment_origin_nm":exact_balance["body_moment_origin_nm"],
            **load_quadrature,
            "comparison_basis": "global consistent nodal load vector, order 8 versus order 12",
            "note":"includes quadrature agreement and independent analytic resultant/moment checks; thresholds remain proposed",
        }
        raw_loads = [
            {"node": node, "dof": dof, "value": float(nodal_load[3 * node + axis])}
            for node in range(len(coordinates))
            for axis, dof in enumerate(("UX", "UY", "UZ"))
            if nodal_load[3 * node + axis] != 0.0
        ]
        raw_elements = [
            {"type": family, "nodes": cell, "material": "mms"}
            for cell in prepared["connectivity_zero_based"]
        ]
        raw_fixed = [
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in prepared["fixed_node_ids_all_components"]
        ]
        model = FiniteElementModel.from_raw(
            nodes=coordinates,
            elements=raw_elements,
            materials={"mms": {"type": "isotropic_3d", "E": oracle.E_PA, "nu": oracle.NU}},
            fixed_dofs=raw_fixed,
            loads=raw_loads,
            analysis="linear_static",
            units={"system": "SI", "length": "m", "force": "N", "stress": "Pa"},
        )
        payload["execution"]["fem_started"] = True
        # Keep the public verification-policy check enabled; a campaign runner
        # must not disable it to make a scientific case appear to pass.
        result = solve_model(model)
        payload["observables"]["solver_status"] = {"status": "AVAILABLE", "value": result.status}
        payload["observables"]["minimum_affine_jacobian_m3"] = {
            "status": "AVAILABLE", "value": case["affine_jacobian_min_m3"],
            "unit": "m^3", "basis": "affine straight-sided mesh matrix, determinant constant over each cell",
        }
        payload["observables"]["nodal_displacements_m"] = {
            "status": "AVAILABLE", "value": result.displacements.tolist(), "unit": "m",
            "ordering": "solver full degree-of-freedom map",
        }
        payload["observables"]["nodal_loads_n"] = {
            "status": "AVAILABLE", "value": nodal_load, "unit": "N",
            "ordering": "node-major UX UY UZ",
        }
        payload["observables"]["solver_origin"] = {
            "status": "AVAILABLE", "value": str(Path(__import__("solveur").__file__).resolve()),
        }
        recovered = recover_solid_stress_field(model, result.displacements)
        payload["observables"]["strain_samples"] = {
            "status": "AVAILABLE",
            "value": [{"element_index": element["element_index"], "integration_points": [
                {"integration_point_index": point["integration_point_index"], "coordinates": point["coordinates"],
                 "weight": point["weight"], "strain_components": point["strain_components"]}
                for point in element["integration_points"]]} for element in recovered["elements"]],
            "component_order": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"],
            "strain_shear": "engineering", "integration_rule": "solver recovery points",
        }
        payload["observables"]["stress_samples_pa"] = {
            "status": "AVAILABLE",
            "value": [{"element_index": element["element_index"], "integration_points": [
                {"integration_point_index": point["integration_point_index"], "coordinates": point["coordinates"],
                 "weight": point["weight"], "stress_tensor": point["stress_tensor"]}
                for point in element["integration_points"]]} for element in recovered["elements"]],
            "component_order": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"],
            "shear": "tensor", "integration_rule": "solver recovery points",
        }

        # Evaluate with independent reference basis derivatives and 4/8-point
        # rules. Agreement is an observation until the Owner freezes the gate.
        nodal_u = [tuple(float(result.displacements[result.dofs.index(node, dof)])
                         for dof in ("UX", "UY", "UZ")) for node in range(len(coordinates))]
        error8 = field_error_draft.integrated_errors(prepared, nodal_u, order=8)
        error12 = field_error_draft.integrated_errors(prepared, nodal_u, order=12)
        payload["observables"]["independent_quadrature_8_12"] = {
            "status": "DIAGNOSTIC_UNQUALIFIED", "order_8": error8, "order_12": error12,
            "note": "quadrature agreement and field norms require frozen Owner criteria",
        }
        for name, key, relative_key, unit in (
            ("displacement_l2_m_5_2", "displacement_l2_m_5_2", "displacement_relative_l2", "m^(5/2)"),
            ("energy_error_norm_sqrt_j", "energy_error_norm_sqrt_j", "energy_error_relative", "sqrt(J)"),
            ("strain_l2", "strain_error_l2_m_3_2", "strain_error_relative", "m^(3/2)"),
            ("stress_l2_pa", "stress_error_l2_pa_m_3_2", "stress_error_relative", "Pa m^(3/2)"),
        ):
            payload["observables"][name] = {
                "status": "DIAGNOSTIC_UNQUALIFIED", "value": error12[key],
                "relative_error": error12[relative_key], "unit": unit,
            }
        payload["observables"]["quadrature_relative_difference"] = {
            "status": "AVAILABLE", "value": _relative_observable_difference(error8, error12), "unit": "1",
            "orders": [8, 12],
        }

        equilibrium = result.audit.equilibrium if result.audit is not None else {}
        payload["closed_equilibrium"] = {
            key: equilibrium[key] for key in (
                "external_resultant", "reaction_resultant", "force_imbalance",
                "external_moment_about_origin", "reaction_moment_about_origin",
                "moment_imbalance_about_origin",
            ) if key in equilibrium
        }
        for name, source, unit in (
            ("free_residual_n", "free_residual_norm", "N"),
            ("free_relative_residual", "free_relative_residual", "1"),
            ("reaction_force_n", "reaction_resultant", "N"),
            ("reaction_moment_nm", "reaction_moment_about_origin", "N m"),
            ("force_closure_n", "force_imbalance", "N"),
            ("moment_closure_nm", "moment_imbalance_about_origin", "N m"),
            ("strain_energy_j", "secant_internal_energy", "J"),
            ("external_work_j", "external_work_at_final_load", "J"),
        ):
            if source in equilibrium:
                payload["observables"][name] = {"status": "AVAILABLE", "value": equilibrium[source], "unit": unit}
        if "free_relative_residual" in equilibrium:
            payload["observables"]["free_relative_residual"]["normalization"] = (
                "solver-reported: free_residual_norm / max(norm(reduced_external), 1 N); diagnostic only"
            )
        if {"free_residual_norm", "external_load_norm", "internal_force_norm"}.issubset(equilibrium):
            payload["observables"]["vv3d_free_residual_relative"] = {
                "status": "AVAILABLE",
                "value": float(equilibrium["free_residual_norm"])
                / max(float(equilibrium["external_load_norm"]), float(equilibrium["internal_force_norm"]), 1e-30),
                "unit": "1",
                "formula": "||r_free||2 / max(||F_external||2, ||F_internal||2, 1e-30 N)",
            }
        if {"secant_internal_energy", "external_work_at_final_load"}.issubset(equilibrium):
            internal_energy = float(equilibrium["secant_internal_energy"])
            external_work = float(equilibrium["external_work_at_final_load"])
            payload["observables"]["energy_identity_relative"] = {
                "status": "AVAILABLE",
                "value": abs(2 * internal_energy - external_work)
                / max(abs(2 * internal_energy), abs(external_work), 1e-30),
                "unit": "1",
                "formula": "|2 U_internal - W_external| / max(|2 U_internal|, |W_external|, 1e-30 J)",
            }
            exact_energy = oracle.exact_energy_j()
            payload["observables"]["scalar_energy_relative_error"] = {
                "status": "AVAILABLE", "value": abs(internal_energy - exact_energy) / exact_energy,
                "unit": "1", "reference_value_j": exact_energy,
                "formula": "|U_internal - U_exact| / U_exact",
            }
        if {"force_imbalance", "external_resultant", "reaction_resultant"}.issubset(equilibrium):
            force_scale = (math.sqrt(sum(value * value for value in equilibrium["external_resultant"]))
                           + math.sqrt(sum(value * value for value in equilibrium["reaction_resultant"])))
            payload["observables"]["force_closure_relative"] = {
                "status": "AVAILABLE",
                "value": math.sqrt(sum(value * value for value in equilibrium["force_imbalance"]))
                / max(force_scale, 1e-30), "unit": "1",
            }
        if {"moment_imbalance_about_origin", "external_resultant", "reaction_resultant"}.issubset(equilibrium):
            force_scale = (math.sqrt(sum(value * value for value in equilibrium["external_resultant"]))
                           + math.sqrt(sum(value * value for value in equilibrium["reaction_resultant"])))
            moment_scale = force_scale * max(oracle.LENGTHS_M)
            payload["observables"]["moment_closure_relative"] = {
                "status": "AVAILABLE",
                "value": math.sqrt(sum(value * value for value in equilibrium["moment_imbalance_about_origin"]))
                / max(moment_scale, 1e-30), "unit": "1", "length_scale_m": max(oracle.LENGTHS_M),
            }
        if "reactions" in equilibrium:
            payload["observables"]["reaction_entries_n"] = {
                "status": "AVAILABLE", "value": equilibrium["reactions"], "unit": "N or N m by component",
            }

        # Acceptance-quality samples still need approved independent quadrature;
        # keep criteria explicitly unassessed.
        payload["execution"] = {"status": "COMPLETED_UNASSESSED", "attempt_reserved": True, "fem_started": True}
        payload["observables"]["elapsed_seconds"] = {"status": "AVAILABLE", "value": time.perf_counter() - started, "unit": "s"}
        payload["execution"]["status"] = "COMPLETED_UNASSESSED"
        payload["criteria"] = evaluate_case_criteria(payload, execution_context["frozen_criteria"])
        return {"result": result, "payload": payload}
    except BaseException as exc:
        failure = exc
        payload["execution"] = {
            "status": "FAILED_OR_INCOMPLETE", "attempt_reserved": True,
            "fem_started": payload["execution"].get("fem_started", False),
            "error_type": type(exc).__name__, "error": str(exc),
        }
        raise
    finally:
        if failure is not None:
            for name in OBSERVABLES:
                payload["observables"].setdefault(name, {"status": "NOT_EXPOSED"})
        evidence.write_observables(evidence_root, case_id, attempt_id, sanitize_for_evidence(payload))


def _relative_observable_difference(low: dict[str, Any], high: dict[str, Any]) -> dict[str, float]:
    keys = ("displacement_relative_l2", "energy_error_relative", "strain_error_relative", "stress_error_relative")
    differences: dict[str, float] = {}
    for key in keys:
        left, right = float(low[key]), float(high[key])
        scale = max(abs(left), abs(right), 1e-30)
        differences[key] = abs(left - right) / scale
    return differences


def _relative_vector_difference(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right) or not all(math.isfinite(value) for value in (*left, *right)):
        raise ValueError("quadrature balance vectors are not finite and paired")
    numerator = math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
    denominator = math.sqrt(sum(value * value for value in right))
    if denominator <= 1e-30:
        return 0.0 if numerator <= 1e-30 else math.inf
    return numerator / denominator


def _load_quadrature_relative_diagnostics(
    load_low: tuple[float, ...],
    load_high: tuple[float, ...],
    balance_low: dict[str, tuple[float, ...]],
    balance_high: dict[str, tuple[float, ...]],
    exact: dict[str, tuple[float, ...]],
) -> dict[str, float]:
    """Compare load-rule nodal vectors and both rules to the analytic global oracle."""
    comparisons = {
        "nodal_load_vector_relative_l2": _relative_vector_difference(load_low, load_high),
        "order_8_body_resultant_relative_error": _relative_vector_difference(
            balance_low["force_closure_n"], exact["body_force_n"]),
        "order_12_body_resultant_relative_error": _relative_vector_difference(
            balance_high["force_closure_n"], exact["body_force_n"]),
        "order_8_body_moment_relative_error": _relative_vector_difference(
            balance_low["moment_closure_nm"], exact["body_moment_origin_nm"]),
        "order_12_body_moment_relative_error": _relative_vector_difference(
            balance_high["moment_closure_nm"], exact["body_moment_origin_nm"]),
    }
    comparisons["maximum_relative_difference"] = max(comparisons.values())
    return comparisons


def _finite_numeric_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, dict):
        if value.get("status") in {"NOT_EXPOSED", "NONFINITE"}:
            return False
        return all(_finite_numeric_tree(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_numeric_tree(item) for item in value)
    return False


def evaluate_case_criteria(payload: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate frozen case gates and retain diagnostics/deferred items separately."""
    obs = payload.get("observables", {})
    required = (
        "nodal_displacements_m", "nodal_loads_n", "strain_samples", "stress_samples_pa",
        "displacement_l2_m_5_2", "energy_error_norm_sqrt_j", "strain_l2", "stress_l2_pa",
        "strain_energy_j", "external_work_j", "free_residual_n", "vv3d_free_residual_relative",
        "energy_identity_relative", "scalar_energy_relative_error", "force_closure_n",
        "moment_closure_nm", "force_closure_relative", "moment_closure_relative",
        "reaction_force_n", "reaction_moment_nm", "reaction_entries_n", "solver_origin",
        "elapsed_seconds", "independent_quadrature_8_12", "load_quadrature_8_12",
        "minimum_affine_jacobian_m3", "quadrature_relative_difference",
    )
    closure = payload.get("closed_equilibrium", {})
    load = obs.get("load_quadrature_8_12", {})
    post = obs.get("quadrature_relative_difference", {})
    values: dict[str, Any] = {
        "finite": [all(obs.get(name, {}).get("status") in {"AVAILABLE", "DIAGNOSTIC_UNQUALIFIED"}
                       for name in required)
                   and all(_finite_numeric_tree(obs[name]) for name in required)
                   and _finite_numeric_tree(closure)],
        "det_j_positive": obs.get("minimum_affine_jacobian_m3", {}).get("value"),
        "free_residual": obs.get("vv3d_free_residual_relative", {}).get("value"),
        "energy_identity": obs.get("energy_identity_relative", {}).get("value"),
        "force_closure": obs.get("force_closure_relative", {}).get("value"),
        "moment_closure": obs.get("moment_closure_relative", {}).get("value"),
        "load_quadrature": load.get("maximum_relative_difference"),
        "post_quadrature": max(post.get("value", {}).values(), default=None),
        "displacement_error_L3": obs.get("displacement_l2_m_5_2", {}).get("relative_error"),
        "energy_error_L3": obs.get("energy_error_norm_sqrt_j", {}).get("relative_error"),
        "stress_error_L3": obs.get("stress_l2_pa", {}).get("relative_error"),
        "scalar_energy_error_L3": obs.get("scalar_energy_relative_error", {}).get("value"),
    }
    verdicts: dict[str, Any] = {}
    for rule in rules:
        name = rule["id"]
        classification = rule["classification"]
        if classification != "CASE_GATE":
            verdicts[name] = {"status": "NOT_ASSESSED", "classification": classification}
            continue
        outcome = criteria_evaluator.evaluate(rule, values.get(name))
        verdicts[name] = {**outcome, "classification": classification,
                          "status": "PASS" if outcome["status"] == "PROVISIONAL_PASS"
                          else "FAIL" if outcome["status"] == "PROVISIONAL_FAIL" else outcome["status"]}
    for required_gate in (
        "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
        "moment_closure", "load_quadrature", "post_quadrature",
    ):
        if required_gate not in verdicts or verdicts[required_gate].get("classification") != "CASE_GATE":
            raise ValueError(f"frozen criteria omitted mandatory case gate: {required_gate}")
    return verdicts


def assert_prospective_acceptance(payload: dict[str, Any]) -> None:
    """Assert only frozen CASE_GATE verdicts; campaign gates remain deferred."""
    if payload.get("case_state") != "OWNER_AUTHORIZED_EXECUTION":
        raise PermissionError("VV3D result does not carry an Owner-authorized execution state")
    failures = [name for name, record in payload.get("criteria", {}).items()
                if record.get("classification") == "CASE_GATE" and record.get("status") != "PASS"]
    if failures:
        raise AssertionError(f"VV3D frozen case criteria failed or remain unassessed: {failures}")


def synthetic_not_exposed_payload(case_id: str, attempt_id: str) -> dict[str, Any]:
    """Build synthetic, explicitly unassessed evidence; zero hashes are sentinels."""
    cases = {case["case_id"]: case for case in load_prepared_cases()}
    if case_id not in cases:
        raise ValueError(f"unknown prepared VV3D case: {case_id}")
    case = cases[case_id]
    return {
        "schema": "qf-wp12-vv3d-observables-v1",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": case_id,
        "attempt_id": attempt_id,
        "case_state": "PREPARED_NOT_AUTHORIZED",
        "mesh_sha256": case["mesh_sha256"],
        "scientific_fingerprint": NOT_AUTHORIZED_FINGERPRINT,
        "controller_fingerprint": NOT_AUTHORIZED_FINGERPRINT,
        "manifest_sha256": NOT_AUTHORIZED_FINGERPRINT,
        "observables": {name: {"status": "NOT_EXPOSED"} for name in OBSERVABLES},
        "criteria": {name: {"status": "NOT_ASSESSED"} for name in CRITERIA},
        "execution": {"status": "NOT_AUTHORIZED", "attempt_reserved": False, "fem_started": False},
    }


def write_synthetic_sidecar(root: Path, case_id: str, attempt_id: str) -> dict[str, str]:
    """Persist only an explicitly synthetic sidecar via the existing create-only writer."""
    payload = synthetic_not_exposed_payload(case_id, attempt_id)
    return evidence.write_observables(root, case_id, attempt_id, payload)


def run_registered_case(case_id: str) -> dict[str, Any]:
    """Entry point used by one exact runner-selected initial nodeid."""
    context = require_authorized_execution(case_id)
    outcome = run_prospective_case(
        case_id,
        context["attempt_id"],
        Path(context["evidence_root"]),
        scientific_fingerprint=context["scientific_fingerprint"],
        controller_fingerprint=context["controller_fingerprint"],
        manifest_sha256=context["manifest_sha256"],
    )
    assert_prospective_acceptance(outcome["payload"])
    return outcome
