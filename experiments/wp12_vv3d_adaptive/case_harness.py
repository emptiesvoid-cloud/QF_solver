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
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from experiments.wp12_vv3d_adaptive import criteria_evaluator, evidence, performance_trace

CAMPAIGN_DIR = Path(__file__).parent / "prepared_20261030_r2"
MATRIX_PATH = CAMPAIGN_DIR / "MATRIX_NOT_AUTHORIZED.json"
VV3D_LEDGER_FILENAME = "node-attempt-ledger-wp12-vv3d-recovery-r2.jsonl"
NOT_AUTHORIZED_FINGERPRINT = "0" * 64
ADAPTIVE_CATALOG_PATH = Path(__file__).parent / "ADAPTIVE_CATALOG_DRAFT.json"
ADAPTIVE_RECEIPT_SCHEMA = "qf-wp12-vv3d-adaptive-runner-receipt-v1"
ADAPTIVE_RECEIPT_CONTRACT = (
    "The controller must emit a strict-JSON receipt with schema/status, campaign_id, candidate_id, "
    "nodeid, execution_kind, seed_case, catalog_sha256, mesh_sha256, criteria_sha256, rule_sha256, "
    "source_hashes, scientific_fingerprint, controller_fingerprint, manifest_sha256, authorization_id, "
    "manifest_path, preflight_receipt_sha256, and allowed_evidence_roots. The raw manifest must be inside "
    "an allowed root and bind the receipt identities, authorization_id, decision records, attempt/job ID, "
    "evidence_root, and the exact frozen catalog criteria plus their canonical digest. Eligibility and archive "
    "files must resolve under the allowed roots; evidence_root must match QF_DEV_EVIDENCE_ROOT. "
    "campaign_decision={status,decision_id,decision_sha256,catalog_sha256}, "
    "transition_decision binds source_case_id and candidate_id plus eligibility_sha256 (FEM) or "
    "eligibility_source_sha256 (QPOST). QPOST source binds campaign/candidate/job IDs, seed PASS and "
    "source run receipt SHA, seed manifest/attempt/mesh, archive path/raw SHA/source identities, campaign "
    "decision id+SHA and postprocessing_jobs_used=0/max=1. "
    "eligibility_record={path,sha256} binding strict JSON {candidate_id,source,transition_decision,result}; "
    "QPOST transition eligibility_source_sha256 is the SHA-256 of canonical source JSON from "
    "json.dumps(source, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8') with no newline, "
    "while eligibility_record.sha256 binds the full raw file. "
    "allowed_evidence_roots containing all eligibility/archive/evidence destinations. FEM uses status RESERVED, "
    "unique reservation_id and attempt_id, selected_dofs, timeout_seconds, attempt_number=1, max_attempts=1, "
    "attempt_reserved=true; QPOST uses "
    "POSTPROCESS_RESERVED, postprocessing_job_id, source_run_receipt_sha256, "
    "postprocessing_jobs_used_before=0/after=1/max=1, attempt_reserved=false, postprocessing_reserved=true, "
    "and archive={path,sha256,source_case_id,source_mesh_sha256,source_manifest_sha256,source_attempt_id}. "
    "The external controller authenticates Owner decisions and performs any reservation; this child parser "
    "only checks exact binding and never reserves or authenticates Owner identity itself."
)
ADAPTIVE_SOURCE_FILES = (
    "experiments/wp12_vv3d_adaptive/case_harness.py",
    "experiments/wp12_vv3d_adaptive/load_assembly_draft.py",
    "experiments/wp12_vv3d_adaptive/field_error_draft.py",
    "experiments/wp12_vv3d_adaptive/sampling.py",
    "experiments/wp12_vv3d_adaptive/quadrature.py",
    "experiments/wp12_vv3d_adaptive/basis.py",
    "experiments/wp12_vv3d_adaptive/oracle.py",
    "experiments/wp12_vv3d_adaptive/mesh.py",
    "experiments/wp12_vv3d_adaptive/metrics.py",
    "experiments/wp12_vv3d_adaptive/criteria_evaluator.py",
    "experiments/wp12_vv3d_adaptive/evidence.py",
    "scripts/wp12_vv3d_r2_ledger.py",
    "experiments/wp12_vv3d_adaptive/r2_contract.py",
    "tests/unit/test_wp12_vv3d_adaptive_prepared.py",
)

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
    if matrix.get("campaign_id") != "WP12-VV3D-RECOVERY-20261030-R2":
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
        artifact_root = CAMPAIGN_DIR.parent.resolve(strict=True)
        for path_key, digest_key in (
            ("criteria_path", "criteria_file_sha256"),
            ("oracle_path", "oracle_sha256"),
        ):
            raw_relative = str(case.get(path_key, ""))
            relative = Path(raw_relative)
            if (relative.is_absolute() or ".." in relative.parts or "\\" in raw_relative
                    or not relative.parts):
                raise ValueError(f"prepared {path_key} escapes the VV3D experiment root")
            artifact = (artifact_root / relative).resolve(strict=True)
            try:
                artifact.relative_to(artifact_root)
            except ValueError as exc:
                raise ValueError(f"prepared {path_key} escapes the VV3D experiment root") from exc
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != case.get(digest_key):
                raise ValueError(f"prepared {path_key} hash mismatch: {case.get('case_id')}")
    return cases


def _expected_nodeid(case_id: str) -> str:
    return ("tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case"
            f"[{case_id}]")


def _strict_json(raw: bytes, label: str) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {label}")
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique_pairs,
                          parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not strict JSON") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _path_within_roots(raw_path: str, roots: list[Path], label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise PermissionError(f"adaptive {label} path is missing")
    try:
        resolved = Path(raw_path).resolve(strict=True)
    except OSError as exc:
        raise PermissionError(f"adaptive {label} path is unavailable") from exc
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise PermissionError(f"adaptive {label} path is outside the allowed evidence roots")
    return resolved


def _read_bound_manifest(receipt: dict[str, Any], base: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    manifest_path = receipt.get("manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path:
        raise PermissionError("adaptive receipt has no raw manifest path")
    roots_raw = receipt.get("allowed_evidence_roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise PermissionError("adaptive manifest receipt has no allowed evidence roots")
    try:
        roots = [Path(root).resolve(strict=True) for root in roots_raw]
        path = _path_within_roots(manifest_path, roots, "manifest")
        raw = path.read_bytes()
    except PermissionError:
        raise
    except OSError as exc:
        raise PermissionError("adaptive raw manifest is unavailable") from exc
    if _sha256(raw) != receipt["manifest_sha256"]:
        raise PermissionError("adaptive raw manifest SHA-256 mismatch")
    manifest = _strict_json(raw, "adaptive manifest")
    if (not isinstance(manifest, dict)
            or manifest.get("schema") != "qf-wp12-vv3d-adaptive-execution-manifest-v1"
            or manifest.get("execution_authorized") is not True
            or manifest.get("do_not_execute") is not False
            or any(manifest.get(key) != value for key, value in base.items())
            or manifest.get("authorization_id") != receipt.get("authorization_id")
            or manifest.get("scientific_fingerprint") != receipt.get("scientific_fingerprint")
            or manifest.get("controller_fingerprint") != receipt.get("controller_fingerprint")
            or manifest.get("campaign_decision") != receipt.get("campaign_decision")
            or manifest.get("transition_decision") != receipt.get("transition_decision")):
        raise PermissionError("adaptive manifest does not bind the authorized receipt identities")
    return manifest, path


def _adaptive_inventory() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    """Load the registered closed set while retaining its not-authorized state."""
    raw = ADAPTIVE_CATALOG_PATH.read_bytes()
    catalog = _strict_json(raw, "adaptive catalog")
    if (not isinstance(catalog, dict)
            or catalog.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1"):
        raise ValueError("unexpected adaptive-catalog campaign identity")
    candidates = catalog.get("candidates")
    expected_ids = {
        f"VV3D-ADAPT-{family}-{kind}"
        for family in ("TET4", "TET10", "HEX8", "HEX20")
        for kind in ("H1", "QLOAD", "QPOST")
    }
    if (not isinstance(candidates, list) or len(candidates) != 12
            or {candidate.get("candidate_id") for candidate in candidates if isinstance(candidate, dict)}
            != expected_ids):
        raise ValueError("adaptive catalog is not the closed set of twelve candidates")
    if any(candidate.get("status") != "PREPARED_NOT_AUTHORIZED"
           or candidate.get("nodeid_status") != "REGISTERED_PREPARED_NOT_AUTHORIZED"
           for candidate in candidates):
        raise ValueError("adaptive catalog contains a candidate outside its preparation-only state")
    by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    return candidates, by_id, _sha256(raw)


def _safe_catalog_file(relative: str) -> Path:
    if (not isinstance(relative, str) or not relative or Path(relative).is_absolute()
            or "\\" in relative or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise ValueError("adaptive catalog path is not a safe relative path")
    root = Path(__file__).resolve().parent
    path = (root / relative).resolve(strict=True)
    if path != root and root not in path.parents:
        raise ValueError("adaptive catalog path escapes the experiment directory")
    return path


def _adaptive_bindings(candidate: dict[str, Any]) -> dict[str, Any]:
    """Compute current catalog, candidate, mesh, rule and source identities."""
    _, candidates, catalog_sha256 = _adaptive_inventory()
    candidate_id = candidate.get("candidate_id")
    if candidate_id not in candidates or candidates[candidate_id] != candidate:
        raise ValueError("candidate is not the exact record in the closed adaptive catalog")
    prepared = candidate.get("prepared_mesh")
    if not isinstance(prepared, dict):
        raise ValueError("adaptive candidate has no prepared mesh identity")
    mesh_path = _safe_catalog_file(prepared.get("path"))
    mesh_sha256 = _sha256(mesh_path.read_bytes())
    if mesh_sha256 != prepared.get("sha256"):
        raise ValueError("adaptive candidate mesh hash differs from the catalog")
    criteria_path = _safe_catalog_file(candidate.get("criteria_path"))
    criteria_sha256 = _sha256(criteria_path.read_bytes())
    if criteria_sha256 != candidate.get("criteria_sha256_provisional"):
        raise ValueError("adaptive criteria source hash differs from the catalog")
    repo_root = Path(__file__).resolve().parents[2]
    source_hashes: dict[str, str] = {}
    for relative in ADAPTIVE_SOURCE_FILES:
        path = (repo_root / relative).resolve(strict=True)
        if repo_root not in path.parents:
            raise ValueError("adaptive source path escapes the repository")
        source_hashes[relative] = _sha256(path.read_bytes())
    rule_identity = {
        "execution_kind": candidate["execution_kind"],
        "kind": candidate["kind"],
        "mesh_rule": candidate["mesh_rule"],
        "numerical_conditions": candidate["numerical_conditions"],
        "criteria_sha256": criteria_sha256,
        "quadrature_source_sha256": source_hashes["experiments/wp12_vv3d_adaptive/quadrature.py"],
        "field_error_source_sha256": source_hashes["experiments/wp12_vv3d_adaptive/field_error_draft.py"],
    }
    canonical = json.dumps(rule_identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {
        "catalog_sha256": catalog_sha256,
        "candidate_sha256": _sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode()),
        "mesh_sha256": mesh_sha256,
        "criteria_sha256": criteria_sha256,
        "rule_sha256": _sha256(canonical),
        "source_hashes": source_hashes,
    }


def _adaptive_candidate_nodeid(candidate: dict[str, Any]) -> str:
    nodeid = candidate.get("nodeid")
    if not isinstance(nodeid, str) or not nodeid.startswith("tests/unit/test_wp12_vv3d_adaptive_prepared.py::"):
        raise ValueError("adaptive candidate nodeid is missing or outside the prepared test module")
    candidate_id = candidate["candidate_id"]
    if candidate["execution_kind"] == "POSTPROCESS_ONLY":
        expected = ("tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_archived_postprocess_case"
                    f"[{candidate['family']}]" )
    else:
        expected = ("tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_adaptive_fem_case"
                    f"[{candidate_id}]")
    if nodeid != expected:
        raise ValueError("adaptive candidate nodeid does not match its exact parameter identity")
    return nodeid


CAMPAIGN_GATE_IDS = frozenset({
    "displacement_error_L3", "energy_error_L3", "stress_error_L3", "scalar_energy_error_L3",
    "displacement_order", "energy_order",
})
CAMPAIGN_INPUT_CASE_GATE_IDS = frozenset({
    "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
    "moment_closure", "load_quadrature", "post_quadrature",
})


def _inconclusive_campaign_assessment(reason: str) -> dict[str, Any]:
    criteria = {
        name: {"classification": "CAMPAIGN_GATE", "status": "INCONCLUSIVE", "reason": reason}
        for name in sorted(CAMPAIGN_GATE_IDS)
    }
    return _campaign_assessment("INCONCLUSIVE", criteria, {}, reason)


def evaluate_campaign_criteria(
    family: str, seed_cases: dict[str, Any], rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate frozen family-level criteria using only paired archived observations.

    L3 limits are evaluated as soon as the exact L3 evidence exists. Order gates
    require all three exact mesh levels. Missing not-yet-run levels remain
    NOT_ASSESSED; malformed, interrupted, nonfinite, or contradictory evidence
    is INCONCLUSIVE. This function performs no assembly or solver work.
    """
    expected_families = {"TET4", "TET10", "HEX8", "HEX20"}
    if family not in expected_families:
        raise ValueError("campaign criteria require an exact registered element family")
    expected_cases = {f"VV3D-{family}-L{level}" for level in (1, 2, 3)}
    if not isinstance(seed_cases, dict) or any(case_id not in expected_cases for case_id in seed_cases):
        return _inconclusive_campaign_assessment("SEED_CASE_IDENTITY_INVALID")

    frozen_rules: dict[str, dict[str, Any]] = {}
    try:
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("id") not in CAMPAIGN_GATE_IDS:
                continue
            name = rule["id"]
            if name in frozen_rules or rule.get("classification") != "CAMPAIGN_GATE":
                raise ValueError("campaign gate is duplicated or not frozen as CAMPAIGN_GATE")
            if rule.get("unit") != "1":
                raise ValueError("campaign gate must retain its dimensionless unit")
            frozen_rules[name] = rule
        if set(frozen_rules) != CAMPAIGN_GATE_IDS:
            raise ValueError("the exact six frozen campaign gates are required")
        for name, expected_operator in (
            ("displacement_error_L3", "LE"), ("energy_error_L3", "LE"),
            ("stress_error_L3", "LE"), ("scalar_energy_error_L3", "LE"),
            ("displacement_order", "GE"), ("energy_order", "GE"),
        ):
            rule = frozen_rules[name]
            if rule.get("operator") != expected_operator:
                raise ValueError(f"frozen campaign gate {name} has an unexpected operator")
            criteria_evaluator.evaluate(rule, 0.0)
    except (KeyError, TypeError, ValueError) as exc:
        return _inconclusive_campaign_assessment(f"FROZEN_CRITERIA_INVALID:{exc}")

    verdicts: dict[str, dict[str, Any]] = {
        name: {"classification": "CAMPAIGN_GATE", "status": "NOT_ASSESSED",
              "reason": "REQUIRED_EVIDENCE_NOT_YET_AVAILABLE"}
        for name in sorted(CAMPAIGN_GATE_IDS)
    }
    level_metrics: dict[str, dict[str, Any]] = {}
    interrupted = {
        case_id: record.get("state")
        for case_id, record in seed_cases.items()
        if isinstance(record, dict) and record.get("state") in {
            "PYTEST_FAILED", "SCIENTIFIC_DEVIATION", "INCONCLUSIVE", "TIMEOUT", "INTERRUPTED",
            "RESOURCE_LIMIT", "INFRA_ERROR", "PROVENANCE_MISMATCH",
        }
    }

    def mark_inconclusive(name: str, reason: str) -> None:
        verdicts[name] = {"classification": "CAMPAIGN_GATE", "status": "INCONCLUSIVE", "reason": reason}

    def record_is_valid(case_id: str, record: Any) -> bool:
        if not isinstance(record, dict) or record.get("case_id") != case_id:
            return False
        if not isinstance(record.get("observables"), dict) or not isinstance(record.get("criteria"), dict):
            return False
        if any(
            not isinstance(record["criteria"].get(name), dict)
            or record["criteria"][name].get("classification") != "CASE_GATE"
            or record["criteria"][name].get("status") != "PASS"
            for name in CAMPAIGN_INPUT_CASE_GATE_IDS
        ):
            return False
        if record.get("state") != "PASS":
            return False
        if record.get("provenance_state") != "VERIFIED":
            return False
        if record.get("sidecar_valid") is not True:
            return False
        for digest_name in ("sidecar_sha256", "mesh_sha256", "manifest_sha256",
                            "scientific_fingerprint", "controller_fingerprint"):
            digest = record.get(digest_name)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                return False
        level = int(case_id.rsplit("-L", maxsplit=1)[1])
        if record.get("h_m") != 1.0 / (2 ** level):
            return False
        return True

    invalid_present = sorted(
        case_id for case_id, record in seed_cases.items()
        if not record_is_valid(case_id, record)
    )
    if invalid_present:
        missing_present = sorted(expected_cases.difference(seed_cases))
        reason = "PRESENT_SEED_EVIDENCE_NOT_A_COMPLETE_CASE_GATE_PASS:" + ",".join(invalid_present)
        if missing_present:
            reason += ";MISSING_LEVELS:" + ",".join(missing_present)
        return _inconclusive_campaign_assessment(
            reason,
        )

    for case_id in expected_cases.intersection(seed_cases):
        record = seed_cases[case_id]
        if not record_is_valid(case_id, record):
            continue
        observations = record.get("observables")
        if not isinstance(observations, dict):
            continue
        extracted: dict[str, Any] = {"case_id": case_id, "h_m": record.get("h_m")}
        for output_name, observable_name, value_key in (
            ("displacement_error", "displacement_l2_m_5_2", "relative_error"),
            ("energy_error", "energy_error_norm_sqrt_j", "relative_error"),
            ("stress_error", "stress_l2_pa", "relative_error"),
            ("scalar_energy_error", "scalar_energy_relative_error", "value"),
        ):
            source = observations.get(observable_name)
            value = source.get(value_key) if isinstance(source, dict) else None
            extracted[output_name] = value
            extracted[f"{output_name}_status"] = source.get("status") if isinstance(source, dict) else None
        level_metrics[case_id] = extracted

    l3_id = f"VV3D-{family}-L3"
    l3 = seed_cases.get(l3_id)
    l3_values = {
        "displacement_error_L3": ("displacement_error", "displacement_l2_m_5_2"),
        "energy_error_L3": ("energy_error", "energy_error_norm_sqrt_j"),
        "stress_error_L3": ("stress_error", "stress_l2_pa"),
        "scalar_energy_error_L3": ("scalar_energy_error", "scalar_energy_relative_error"),
    }
    if l3 is not None:
        if l3_id in interrupted:
            for name in l3_values:
                mark_inconclusive(name, f"L3_ATTEMPT_{interrupted[l3_id]}")
        elif not record_is_valid(l3_id, l3):
            for name in l3_values:
                mark_inconclusive(name, "L3_EVIDENCE_OR_PROVENANCE_INVALID")
        else:
            extracted_l3 = level_metrics.get(l3_id, {})
            for gate_id, (value_name, observable_name) in l3_values.items():
                value = extracted_l3.get(value_name)
                source = l3.get("observables", {}).get(observable_name, {})
                if (not isinstance(source, dict)
                        or source.get("status") not in {"AVAILABLE", "DIAGNOSTIC_UNQUALIFIED"}
                        or isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value < 0):
                    mark_inconclusive(gate_id, "L3_METRIC_MISSING_NONFINITE_OR_INVALID")
                    continue
                evaluated = criteria_evaluator.evaluate(frozen_rules[gate_id], float(value))
                evaluated_status = evaluated.get("status")
                verdicts[gate_id] = {
                    "classification": "CAMPAIGN_GATE",
                    "status": ("PASS" if evaluated_status == "PROVISIONAL_PASS" else
                               "FAIL" if evaluated_status == "PROVISIONAL_FAIL" else "INCONCLUSIVE"),
                    "operator": frozen_rules[gate_id]["operator"],
                    "threshold": frozen_rules[gate_id]["threshold"],
                    "unit": frozen_rules[gate_id]["unit"], "observation": float(value),
                    "observable": observable_name,
                }

    missing_cases = expected_cases.difference(seed_cases)
    if interrupted:
        reason = "INTERRUPTED_LEVELS:" + ",".join(
            f"{key}={value}" for key, value in sorted(interrupted.items())
        )
        if missing_cases:
            reason += ";MISSING_LEVELS:" + ",".join(sorted(missing_cases))
        for gate_id in ("displacement_order", "energy_order"):
            mark_inconclusive(gate_id, reason)
    elif missing_cases:
        for gate_id in ("displacement_order", "energy_order"):
            verdicts[gate_id] = {
                "classification": "CAMPAIGN_GATE", "status": "NOT_ASSESSED",
                "reason": "THREE_EXACT_LEVELS_REQUIRED", "missing_case_ids": sorted(missing_cases),
            }
    else:
        invalid_levels = [case_id for case_id in sorted(expected_cases)
                          if case_id not in interrupted and not record_is_valid(case_id, seed_cases[case_id])]
        if invalid_levels:
            reason = "LEVEL_EVIDENCE_OR_PROVENANCE_INVALID:" + ",".join(invalid_levels)
            for gate_id in ("displacement_order", "energy_order"):
                mark_inconclusive(gate_id, reason)
        else:
            from experiments.wp12_vv3d_adaptive.metrics import observed_orders

            h_values = [level_metrics.get(f"VV3D-{family}-L{level}", {}).get("h_m") for level in (1, 2, 3)]
            for gate_id, metric_name in (
                ("displacement_order", "displacement_error"), ("energy_order", "energy_error"),
            ):
                errors = [level_metrics.get(f"VV3D-{family}-L{level}", {}).get(metric_name)
                          for level in (1, 2, 3)]
                statuses = [level_metrics.get(f"VV3D-{family}-L{level}", {}).get(f"{metric_name}_status")
                            for level in (1, 2, 3)]
                if (any(status not in {"AVAILABLE", "DIAGNOSTIC_UNQUALIFIED"} for status in statuses)
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value) or value <= 0 for value in errors)
                        or any(isinstance(value, bool) or not isinstance(value, (int, float))
                               or not math.isfinite(value) or value <= 0 for value in h_values)):
                    mark_inconclusive(gate_id, "ORDER_INPUT_MISSING_NONFINITE_OR_ZERO")
                    continue
                try:
                    orders = observed_orders([float(value) for value in h_values],
                                             [float(value) for value in errors])
                except ValueError as exc:
                    mark_inconclusive(gate_id, f"ORDER_INPUT_INVALID:{exc}")
                    continue
                if len(orders) != 2 or any(value is None or not math.isfinite(value) for value in orders):
                    mark_inconclusive(gate_id, "BOTH_ADJACENT_ORDERS_REQUIRED")
                    continue
                threshold = float(frozen_rules[gate_id]["threshold"])
                interval_pass = [value >= threshold for value in orders]
                verdicts[gate_id] = {
                    "classification": "CAMPAIGN_GATE",
                    "status": "PASS" if all(interval_pass) else "FAIL",
                    "operator": "GE", "threshold": threshold, "unit": "1",
                    "observations": [float(value) for value in orders],
                    "intervals": ["L1-L2", "L2-L3"],
                    "mesh_sizes_m": [float(value) for value in h_values],
                    "errors": [float(value) for value in errors],
                    "interval_pass": interval_pass,
                }

    statuses = [item["status"] for item in verdicts.values()]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "INCONCLUSIVE" in statuses:
        overall = "INCONCLUSIVE"
    elif "NOT_ASSESSED" in statuses:
        overall = "NOT_ASSESSED"
    else:
        overall = "PASS"
    return _campaign_assessment(overall, verdicts, level_metrics)


def _campaign_assessment(
    status: str, criteria: dict[str, Any], level_metrics: dict[str, Any], reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "qf-wp12-vv3d-campaign-assessment-v1", "status": status,
        "decision": ("SCIENTIFIC_DEVIATION_STOP" if status == "FAIL" else
                     "STOP_INCONCLUSIVE" if status == "INCONCLUSIVE" else
                     "WAIT_FOR_REQUIRED_RESULTS" if status == "NOT_ASSESSED" else "CONTINUE"),
        "criteria": criteria, "level_metrics": level_metrics,
        "blocking_failures": sorted(name for name, item in criteria.items() if item.get("status") == "FAIL"),
        **({"reason": reason} if reason else {}),
    }


def evaluate_adaptive_eligibility(candidate_id: str, source: dict[str, Any]) -> dict[str, Any]:
    """Pure evaluation of catalog trigger conditions from archived seed observations."""
    _, candidates, _catalog_sha = _adaptive_inventory()
    if candidate_id not in candidates:
        raise ValueError("candidate is outside the closed adaptive catalog")
    candidate = candidates[candidate_id]
    kind = candidate["kind"]
    conditions = candidate["numerical_conditions"]
    family = candidate["family"]
    if not isinstance(source, dict):
        raise ValueError("adaptive eligibility source must be a mapping")
    if kind == "uniform_h_refinement":
        seed_levels = source.get("seed_cases")
        if not isinstance(seed_levels, dict) or set(seed_levels) != {f"VV3D-{family}-L{i}" for i in (1, 2, 3)}:
            return {"status": "NOT_ASSESSABLE", "reason": "THREE_EXACT_SEED_CASES_REQUIRED"}
        criteria = _strict_json(_safe_catalog_file(candidate["criteria_path"]).read_bytes(), "family criteria")
        campaign_assessment = evaluate_campaign_criteria(family, seed_levels, criteria["criteria"])
        if campaign_assessment["status"] != "PASS":
            status = "INELIGIBLE" if campaign_assessment["status"] == "FAIL" else "NOT_ASSESSABLE"
            return {"status": status, "reason": "CAMPAIGN_GATES_NOT_PASS",
                    "campaign_assessment": campaign_assessment}
        gate_ids = {"finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                    "moment_closure", "load_quadrature", "post_quadrature"}
        errors_u: list[float] = []
        errors_e: list[float] = []
        hs: list[float] = []
        for level in (1, 2, 3):
            record = seed_levels[f"VV3D-{family}-L{level}"]
            if (not isinstance(record, dict) or not isinstance(record.get("observables"), dict)
                    or not isinstance(record.get("criteria"), dict)):
                return {"status": "NOT_ASSESSABLE", "reason": f"MISSING_LEVEL_{level}_EVIDENCE"}
            if any(record["criteria"].get(gate, {}).get("status") != "PASS" for gate in gate_ids):
                return {"status": "INELIGIBLE", "reason": f"SEED_LEVEL_{level}_CASE_GATE_FAILED"}
            obs = record["observables"]
            u = obs.get("displacement_l2_m_5_2", {})
            e = obs.get("energy_error_norm_sqrt_j", {})
            if (u.get("status") not in {"AVAILABLE", "DIAGNOSTIC_UNQUALIFIED"}
                    or e.get("status") not in {"AVAILABLE", "DIAGNOSTIC_UNQUALIFIED"}):
                return {"status": "NOT_ASSESSABLE", "reason": f"MISSING_LEVEL_{level}_FIELD_ERROR"}
            uv, ev = u.get("relative_error"), e.get("relative_error")
            if (isinstance(uv, bool) or isinstance(ev, bool) or not isinstance(uv, (int, float))
                    or not isinstance(ev, (int, float)) or not math.isfinite(uv) or not math.isfinite(ev)
                    or uv <= 0 or ev <= 0):
                return {"status": "NOT_ASSESSABLE", "reason": f"INVALID_LEVEL_{level}_FIELD_ERROR"}
            errors_u.append(float(uv))
            errors_e.append(float(ev))
            h = 1.0 / (2 ** level)
            # The prepared matrix uses n=(2,4,8), hence h=(1/2,1/4,1/8).
            hs.append(h)
        from experiments.wp12_vv3d_adaptive.metrics import observed_orders
        pu = observed_orders(hs, errors_u)
        pe = observed_orders(hs, errors_e)
        floors = {rule["id"]: rule["threshold"] for rule in criteria["criteria"]
                  if rule["id"] in {"displacement_order", "energy_order"}}
        if set(floors) != {"displacement_order", "energy_order"}:
            return {"status": "NOT_ASSESSABLE", "reason": "SLOPE_FLOORS_MISSING"}
        trigger = (any(value is not None and value < floors["displacement_order"] for value in pu)
                   or any(value is not None and value < floors["energy_order"] for value in pe))
        return {"status": "ELIGIBLE" if trigger else "INELIGIBLE",
                "trigger": "SLOPE_BELOW_PROPOSED_FLOOR" if trigger else "NO_SLOPE_TRIGGER",
                "displacement_orders": pu, "energy_orders": pe, "h_m": hs}
    if kind == "body_load_quadrature_escalation":
        load = source.get("load_quadrature_8_12")
        if not isinstance(load, dict):
            return {"status": "NOT_ASSESSABLE", "reason": "LOAD_QUADRATURE_OBSERVATION_MISSING"}
        low, high = load.get("order_8"), load.get("order_12")
        try:
            resultant = _relative_vector_difference(tuple(low["force_closure_n"]), tuple(high["force_closure_n"]))
            moment = _relative_vector_difference(tuple(low["moment_closure_nm"]), tuple(high["moment_closure_nm"]))
        except (KeyError, TypeError, ValueError) as exc:
            return {"status": "NOT_ASSESSABLE", "reason": f"LOAD_BALANCE_INVALID:{type(exc).__name__}"}
        trigger = max(resultant, moment)
        floor = float(conditions["relative_resultant_or_moment_change_trigger_gt"])
        return {"status": "ELIGIBLE" if trigger > floor else "INELIGIBLE",
                "trigger": "LOAD_RESULTANT_OR_MOMENT_SENSITIVITY" if trigger > floor else "LOAD_RULES_AGREE",
                "resultant_relative_change": resultant, "moment_relative_change": moment,
                "threshold": floor}
    if kind == "archived_field_postprocessing_quadrature_escalation":
        if (source.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1"
                or source.get("candidate_id") != candidate_id
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(source.get("postprocessing_job_id", "")))):
            return {"status": "NOT_ASSESSABLE", "reason": "EXACT_QPOST_JOB_IDENTITY_REQUIRED"}
        seed = source.get("seed_case")
        archive = source.get("archive")
        slot = source.get("postprocessing_slot")
        if (not isinstance(seed, dict) or seed.get("case_id") != candidate["seed_case"]
                or seed.get("status") != "PASS"
                or seed.get("mesh_sha256") != candidate["prepared_mesh"]["sha256"]
                or not re.fullmatch(r"[0-9a-f]{64}", str(seed.get("source_run_receipt_sha256", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(seed.get("manifest_sha256", "")))
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(seed.get("attempt_id", "")))):
            return {"status": "NOT_ASSESSABLE", "reason": "EXACT_SEED_CASE_EVIDENCE_REQUIRED"}
        campaign_decision = source.get("campaign_decision")
        if (not isinstance(campaign_decision, dict)
                or not isinstance(campaign_decision.get("decision_id"), str)
                or not campaign_decision["decision_id"]
                or not re.fullmatch(r"[0-9a-f]{64}", str(campaign_decision.get("decision_sha256", "")))):
            return {"status": "NOT_ASSESSABLE", "reason": "APPROVED_CAMPAIGN_DECISION_REQUIRED"}
        if (not isinstance(archive, dict) or archive.get("status") != "AVAILABLE"
                or archive.get("source_case_id") != candidate["seed_case"]
                or archive.get("source_mesh_sha256") != candidate["prepared_mesh"]["sha256"]
                or archive.get("source_manifest_sha256") != seed.get("manifest_sha256")
                or archive.get("source_attempt_id") != seed.get("attempt_id")
                or not isinstance(archive.get("path"), str) or not archive["path"]
                or not re.fullmatch(r"[0-9a-f]{64}", str(archive.get("source_manifest_sha256", "")))
                or not re.fullmatch(r"[0-9a-f]{64}", str(archive.get("sha256", "")))
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(archive.get("source_attempt_id", "")))):
            return {"status": "NOT_ASSESSABLE", "reason": "EXACT_ARCHIVED_SEED_STATE_REQUIRED"}
        if (not isinstance(slot, dict)
                or type(slot.get("postprocessing_jobs_used")) is not int
                or type(slot.get("postprocessing_jobs_max")) is not int
                or slot.get("postprocessing_jobs_max") != conditions.get("postprocessing_jobs_max")
                or slot.get("postprocessing_jobs_used") != 0
                or conditions.get("postprocessing_jobs_max") != 1):
            return {"status": "INELIGIBLE", "reason": "NO_UNUSED_QPOST_SLOT"}
        source_hash = _sha256(json.dumps(
            source, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8"))
        return {"status": "ELIGIBLE", "trigger": "SEED_PASS_ARCHIVE_BOUND_SLOT_UNUSED",
                "postprocessing_jobs_used": 0,
                "postprocessing_jobs_max": conditions["postprocessing_jobs_max"],
                "eligibility_source_sha256": source_hash}
    return {"status": "NOT_ASSESSABLE", "reason": "UNSUPPORTED_ADAPTIVE_KIND"}


def validate_adaptive_runner_receipt(candidate_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact child-side adaptive receipt contract, without reservation."""
    _, candidates, catalog_sha256 = _adaptive_inventory()
    if candidate_id not in candidates:
        raise PermissionError("adaptive candidate is outside the closed catalog")
    candidate = candidates[candidate_id]
    bindings = _adaptive_bindings(candidate)
    expected_nodeid = _adaptive_candidate_nodeid(candidate)
    execution_kind = candidate["execution_kind"]
    if not isinstance(receipt, dict) or receipt.get("schema") != ADAPTIVE_RECEIPT_SCHEMA:
        raise PermissionError("adaptive runner receipt schema mismatch")
    base = {
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "candidate_id": candidate_id,
        "nodeid": expected_nodeid,
        "execution_kind": execution_kind,
        "seed_case": candidate["seed_case"],
        "catalog_sha256": catalog_sha256,
        "candidate_sha256": bindings["candidate_sha256"],
        "mesh_sha256": bindings["mesh_sha256"],
        "criteria_sha256": bindings["criteria_sha256"],
        "rule_sha256": bindings["rule_sha256"],
        "source_hashes": bindings["source_hashes"],
    }
    if any(receipt.get(key) != value for key, value in base.items()):
        raise PermissionError("adaptive runner receipt does not bind the exact candidate/nodeid/mesh/rule/sources")
    for name in ("manifest_sha256", "scientific_fingerprint", "controller_fingerprint"):
        if not isinstance(receipt.get(name), str) or not re.fullmatch(r"[0-9a-f]{64}", receipt[name]):
            raise PermissionError(f"adaptive runner receipt has invalid {name}")
    if (not isinstance(receipt.get("authorization_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", receipt["authorization_id"])):
        raise PermissionError("adaptive runner receipt has invalid authorization_id")
    roots_raw = receipt.get("allowed_evidence_roots")
    if not isinstance(roots_raw, list) or not roots_raw or any(not isinstance(root, str) or not root for root in roots_raw):
        raise PermissionError("adaptive runner receipt has no allowed evidence roots")
    try:
        roots = [Path(root).resolve(strict=True) for root in roots_raw]
    except OSError as exc:
        raise PermissionError("adaptive allowed evidence root is unavailable") from exc
    if any(not root.is_dir() for root in roots):
        raise PermissionError("adaptive allowed evidence root is not a directory")
    try:
        evidence_root = Path(receipt.get("evidence_root", "")).resolve(strict=True)
    except (OSError, TypeError) as exc:
        raise PermissionError("adaptive runner evidence root is unavailable") from exc
    if not evidence_root.is_dir() or evidence_root not in roots:
        raise PermissionError("adaptive evidence root is not an allowed evidence root")
    if (not isinstance(receipt.get("preflight_receipt_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["preflight_receipt_sha256"])):
        raise PermissionError("adaptive runner receipt has invalid preflight receipt identity")
    for decision_name in ("campaign_decision", "transition_decision"):
        decision = receipt.get(decision_name)
        if (not isinstance(decision, dict) or decision.get("status") != "APPROVED"
                or not isinstance(decision.get("decision_id"), str) or not decision["decision_id"]
                or not isinstance(decision.get("decision_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", decision["decision_sha256"])):
            raise PermissionError(f"adaptive runner receipt lacks approved {decision_name}")
    campaign_decision = receipt["campaign_decision"]
    if campaign_decision.get("catalog_sha256") != catalog_sha256:
        raise PermissionError("adaptive campaign decision is not bound to the closed catalog")
    transition = receipt["transition_decision"]
    transition_hash_key = ("eligibility_source_sha256" if execution_kind == "POSTPROCESS_ONLY"
                           else "eligibility_sha256")
    if (transition.get("source_case_id") != candidate["seed_case"]
            or transition.get("candidate_id") != candidate_id
            or not isinstance(transition.get(transition_hash_key), str)
            or not re.fullmatch(r"[0-9a-f]{64}", transition[transition_hash_key])):
        raise PermissionError("adaptive transition decision does not bind the seed/candidate eligibility")
    eligibility_ref = receipt.get("eligibility_record")
    if (not isinstance(eligibility_ref, dict) or not isinstance(eligibility_ref.get("path"), str)
            or not isinstance(eligibility_ref.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", eligibility_ref["sha256"])
            or (execution_kind != "POSTPROCESS_ONLY"
                and eligibility_ref["sha256"] != transition["eligibility_sha256"])):
        raise PermissionError("adaptive receipt does not bind a raw eligibility record")
    try:
        eligibility_path = _path_within_roots(eligibility_ref["path"], roots, "eligibility record")
        eligibility_raw = eligibility_path.read_bytes()
    except PermissionError:
        raise
    except OSError as exc:
        raise PermissionError("adaptive eligibility record is unavailable") from exc
    if _sha256(eligibility_raw) != eligibility_ref["sha256"]:
        raise PermissionError("adaptive eligibility record SHA-256 mismatch")
    eligibility_record = _strict_json(eligibility_raw, "adaptive eligibility record")
    if (not isinstance(eligibility_record, dict)
            or eligibility_record.get("schema") != "qf-wp12-vv3d-adaptive-eligibility-v1"
            or eligibility_record.get("candidate_id") != candidate_id
            or (execution_kind == "POSTPROCESS_ONLY"
                and eligibility_record.get("transition_decision") != transition)):
        raise PermissionError("adaptive eligibility record identity mismatch")
    computed_eligibility = evaluate_adaptive_eligibility(candidate_id, eligibility_record.get("source"))
    eligibility = receipt.get("eligibility")
    if (computed_eligibility.get("status") != "ELIGIBLE"
            or eligibility_record.get("result") != computed_eligibility
            or not isinstance(eligibility, dict) or eligibility.get("status") != "ELIGIBLE"
            or eligibility.get("sha256") != eligibility_ref["sha256"]
            or (execution_kind == "POSTPROCESS_ONLY"
                and computed_eligibility.get("eligibility_source_sha256")
                != transition["eligibility_source_sha256"])):
        raise PermissionError("adaptive receipt lacks the exact eligible transition record")
    manifest, manifest_path = _read_bound_manifest(receipt, base)
    criteria_document = _strict_json(
        _safe_catalog_file(candidate["criteria_path"]).read_bytes(), "adaptive criteria source",
    )
    expected_criteria = criteria_document.get("criteria") if isinstance(criteria_document, dict) else None
    frozen_criteria = manifest.get("frozen_criteria")
    frozen_raw = json.dumps(frozen_criteria, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if execution_kind == "FEM":
        reservation_binding_matches = (
            manifest.get("attempt_id") == receipt.get("attempt_id")
            and manifest.get("reservation_id") == receipt.get("reservation_id")
        )
    else:
        reservation_binding_matches = (
            manifest.get("postprocessing_job_id") == receipt.get("postprocessing_job_id")
        )
    if (not isinstance(frozen_criteria, list) or not frozen_criteria
            or frozen_criteria != expected_criteria
            or _sha256(frozen_raw) != manifest.get("frozen_criteria_sha256")
            or not reservation_binding_matches
            or manifest.get("preflight_receipt_sha256") != receipt.get("preflight_receipt_sha256")
            or manifest.get("evidence_root") != receipt.get("evidence_root")):
        raise PermissionError("adaptive manifest frozen criteria or reservation binding mismatch")
    if execution_kind == "FEM":
        numerical = candidate["numerical_conditions"]
        selected_dofs = candidate["prepared_mesh"]["selected_dofs"]
        if (receipt.get("status") != "RESERVED" or receipt.get("attempt_reserved") is not True
                or receipt.get("postprocessing_reserved") is not False
                or not isinstance(receipt.get("attempt_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", receipt["attempt_id"])
                or not isinstance(receipt.get("reservation_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", receipt["reservation_id"])
                or type(receipt.get("selected_dofs")) is not int
                or receipt.get("selected_dofs") != selected_dofs
                or receipt.get("selected_dofs") > numerical.get("dofs_max", 0)
                or type(receipt.get("timeout_seconds")) is not int
                or receipt.get("timeout_seconds") != numerical.get("timeout_seconds_max")
                or type(receipt.get("attempt_number")) is not int
                or receipt.get("attempt_number") != 1 or receipt.get("max_attempts") != 1
                or type(receipt.get("max_attempts")) is not int
                or type(manifest.get("selected_dofs")) is not int
                or manifest.get("selected_dofs") != selected_dofs
                or type(manifest.get("timeout_seconds")) is not int
                or manifest.get("timeout_seconds") != numerical.get("timeout_seconds_max")
                or type(manifest.get("attempt_number")) is not int
                or manifest.get("attempt_number") != 1
                or type(manifest.get("max_attempts")) is not int or manifest.get("max_attempts") != 1):
            raise PermissionError("adaptive FEM receipt does not bind one reserved exact attempt")
    elif execution_kind == "POSTPROCESS_ONLY":
        archive = receipt.get("archive")
        source_record = eligibility_record.get("source", {})
        seed_record = source_record.get("seed_case", {}) if isinstance(source_record, dict) else {}
        slot_record = source_record.get("postprocessing_slot", {}) if isinstance(source_record, dict) else {}
        if (not isinstance(source_record, dict) or not isinstance(seed_record, dict)
                or receipt.get("status") != "POSTPROCESS_RESERVED"
                or receipt.get("attempt_reserved") is not False
                or receipt.get("postprocessing_reserved") is not True
                or not isinstance(receipt.get("postprocessing_job_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", receipt["postprocessing_job_id"])
                or type(receipt.get("postprocessing_jobs_used_before")) is not int
                or receipt.get("postprocessing_jobs_used_before") != 0
                or type(receipt.get("postprocessing_jobs_used_after")) is not int
                or receipt.get("postprocessing_jobs_used_after") != 1
                or type(receipt.get("postprocessing_jobs_max")) is not int
                or receipt.get("postprocessing_jobs_max") != candidate["numerical_conditions"].get("postprocessing_jobs_max")
                or type(manifest.get("postprocessing_jobs_used_before")) is not int
                or manifest.get("postprocessing_jobs_used_before") != 0
                or type(manifest.get("postprocessing_jobs_used_after")) is not int
                or manifest.get("postprocessing_jobs_used_after") != 1
                or type(manifest.get("postprocessing_jobs_max")) is not int
                or manifest.get("postprocessing_jobs_max") != candidate["numerical_conditions"].get("postprocessing_jobs_max")
                or manifest.get("source_run_receipt_sha256") != receipt.get("source_run_receipt_sha256")
                or source_record.get("campaign_id") != receipt["campaign_id"]
                or source_record.get("candidate_id") != candidate_id
                or source_record.get("postprocessing_job_id") != receipt["postprocessing_job_id"]
                or slot_record != {
                    "postprocessing_jobs_used": receipt.get("postprocessing_jobs_used_before"),
                    "postprocessing_jobs_max": receipt.get("postprocessing_jobs_max"),
                }
                or source_record.get("campaign_decision") != {
                    "decision_id": campaign_decision["decision_id"],
                    "decision_sha256": campaign_decision["decision_sha256"],
                }
                or not isinstance(receipt.get("source_run_receipt_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", receipt["source_run_receipt_sha256"])
                or seed_record.get("source_run_receipt_sha256") != receipt["source_run_receipt_sha256"]
                or not isinstance(archive, dict)
                or archive.get("source_case_id") != candidate["seed_case"]
                or archive.get("source_mesh_sha256") != bindings["mesh_sha256"]
                or archive.get("source_manifest_sha256") != receipt.get("source_manifest_sha256")
                or seed_record.get("manifest_sha256") != archive.get("source_manifest_sha256")
                or seed_record.get("attempt_id") != archive.get("source_attempt_id")
                or seed_record.get("mesh_sha256") != archive.get("source_mesh_sha256")
                or not re.fullmatch(r"[0-9a-f]{64}", str(archive.get("sha256", "")))
                or not isinstance(archive.get("path"), str)
                or not isinstance(archive.get("source_attempt_id"), str)):
            raise PermissionError("adaptive QPOST receipt does not bind an archived state without FEM attempt")
        if not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("source_manifest_sha256", ""))):
            raise PermissionError("adaptive QPOST receipt has invalid source manifest identity")
        archive_path = _path_within_roots(archive["path"], roots, "QPOST archive")
        eligible_archive = eligibility_record.get("source", {}).get("archive")
        expected_archive_source = {
            "status": "AVAILABLE", "path": str(archive_path), "sha256": archive["sha256"],
            "source_case_id": archive["source_case_id"],
            "source_mesh_sha256": archive["source_mesh_sha256"],
            "source_manifest_sha256": archive["source_manifest_sha256"],
            "source_attempt_id": archive["source_attempt_id"],
        }
        try:
            eligible_archive_path = _path_within_roots(eligible_archive.get("path", ""), roots,
                                                       "QPOST eligibility archive")
        except AttributeError as exc:
            raise PermissionError("adaptive QPOST eligibility is not bound to the archived state") from exc
        if eligible_archive != expected_archive_source or eligible_archive_path != archive_path:
            raise PermissionError("adaptive QPOST eligibility is not bound to the reserved archived state")
        transition_source_hash = _sha256(json.dumps(
            eligibility_record["source"], sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8"))
        if transition.get("eligibility_source_sha256") != transition_source_hash:
            raise PermissionError("adaptive QPOST transition does not bind its canonical source digest")
    else:
        raise PermissionError("unsupported adaptive execution kind")
    return {**base, **receipt, "manifest_path": str(manifest_path), "manifest": manifest,
            "archive_path": str(archive_path) if execution_kind == "POSTPROCESS_ONLY" else None,
            "nodeid": expected_nodeid, "bindings": bindings}


def require_adaptive_runner_receipt(candidate_id: str) -> dict[str, Any]:
    """Load and check a controller-produced adaptive receipt; never reserve work."""
    expected_nodeid = None
    _, candidates, _ = _adaptive_inventory()
    candidate = candidates.get(candidate_id)
    if candidate is None:
        raise PermissionError("adaptive candidate is outside the closed catalog")
    expected_nodeid = _adaptive_candidate_nodeid(candidate)
    if (os.environ.get("QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID") != candidate_id
            or os.environ.get("QF_DEV_TARGET_NODEID") != expected_nodeid):
        raise PermissionError("adaptive candidate/nodeid runner context mismatch")
    receipt_path = os.environ.get("QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH", "")
    receipt_sha = os.environ.get("QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256", "")
    if not receipt_path or not re.fullmatch(r"[0-9a-f]{64}", receipt_sha):
        raise PermissionError("adaptive runner receipt context is missing")
    try:
        resolved = Path(receipt_path).resolve(strict=True)
        raw = resolved.read_bytes()
    except OSError as exc:
        raise PermissionError("adaptive runner receipt is unavailable") from exc
    if _sha256(raw) != receipt_sha:
        raise PermissionError("adaptive runner receipt raw SHA-256 mismatch")
    receipt = _strict_json(raw, "adaptive runner receipt")
    verified = validate_adaptive_runner_receipt(candidate_id, receipt)
    try:
        expected_evidence_root = Path(os.environ.get("QF_DEV_EVIDENCE_ROOT", "")).resolve(strict=True)
        receipt_evidence_root = Path(verified["evidence_root"]).resolve(strict=True)
    except OSError as exc:
        raise PermissionError("adaptive controller evidence root context is unavailable") from exc
    if expected_evidence_root != receipt_evidence_root:
        raise PermissionError("adaptive receipt evidence root differs from the controller assignment")
    verified["receipt_sha256"] = receipt_sha
    return verified


def run_registered_adaptive_fem_candidate(candidate_id: str) -> dict[str, Any]:
    """Run one exact H1/QLOAD candidate after receipt and manifest validation."""
    receipt = require_adaptive_runner_receipt(candidate_id)
    _, candidates, _ = _adaptive_inventory()
    candidate = candidates.get(candidate_id)
    if (candidate is None or candidate["execution_kind"] != "FEM"
            or candidate["kind"] not in {"uniform_h_refinement", "body_load_quadrature_escalation"}):
        raise PermissionError("adaptive FEM entrypoint accepts only catalogued H1/QLOAD candidates")
    prepared_path = _safe_catalog_file(candidate["prepared_mesh"]["path"])
    prepared_raw = prepared_path.read_bytes()
    if _sha256(prepared_raw) != receipt["mesh_sha256"]:
        raise PermissionError("adaptive FEM mesh changed after receipt validation")
    prepared = _strict_json(prepared_raw, "adaptive FEM mesh")
    conditions = candidate["numerical_conditions"]
    if (prepared.get("family") != candidate["family"]
            or prepared.get("summary", {}).get("dofs") != candidate["prepared_mesh"].get("selected_dofs")
            or conditions.get("dofs", prepared.get("summary", {}).get("dofs"))
            != prepared.get("summary", {}).get("dofs")
            or conditions.get("dofs_max", 0) < prepared.get("summary", {}).get("dofs", 0)):
        raise PermissionError("adaptive catalog mesh family or selected DDL does not match its exact candidate")
    manifest = receipt["manifest"]
    execution_context = {
        "campaign_id": receipt["campaign_id"], "case_id": candidate_id,
        "nodeid": receipt["nodeid"], "manifest_sha256": receipt["manifest_sha256"],
        "manifest_path": receipt["manifest_path"],
        "scientific_fingerprint": receipt["scientific_fingerprint"],
        "controller_fingerprint": receipt["controller_fingerprint"],
        "authorization_id": receipt["authorization_id"],
        "evidence_root": receipt["evidence_root"], "attempt_id": receipt["attempt_id"],
        "reservation_id": receipt["reservation_id"],
        "owner_decision_sha256": receipt["campaign_decision"]["decision_sha256"],
        "preflight_receipt_sha256": receipt["preflight_receipt_sha256"],
        "runner_receipt_sha256": receipt["receipt_sha256"],
        "frozen_criteria": manifest["frozen_criteria"],
    }
    case_record = {
        "case_id": candidate_id, "level": "ADAPTIVE", "formulation": candidate["family"],
        "mesh_sha256": receipt["mesh_sha256"],
        "affine_jacobian_min_m3": prepared["summary"]["affine_jacobian_min_m3"],
    }
    outcome = _run_prospective_case_with_context(
        candidate_id, case_record, receipt["attempt_id"], Path(receipt["evidence_root"]),
        scientific_fingerprint=receipt["scientific_fingerprint"],
        controller_fingerprint=receipt["controller_fingerprint"],
        manifest_sha256=receipt["manifest_sha256"], execution_context=execution_context,
        prepared_mesh=prepared,
    )
    assert_prospective_acceptance(outcome["payload"])
    return outcome


def _valid_campaign_reserved_seconds(value: Any, *, minimum: int) -> bool:
    """Validate the controller's JSON number without rounding elapsed time.

    JSON booleans are Python integers by inheritance, so exact type checks are
    intentional. Integer values are inherently finite; floats must be finite.
    The range check also rejects arbitrarily large JSON integers.
    """
    if type(value) is int:
        seconds: int | float = value
    elif type(value) is float and math.isfinite(value):
        seconds = value
    else:
        return False
    return minimum <= seconds <= 28_800


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
    context["campaign_id"] = "WP12-VV3D-RECOVERY-20261030-R2"
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
        "campaign_id": "WP12-VV3D-RECOVERY-20261030-R2",
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
            or runner_receipt.get("ledger_scope_id") != "wp12_vv3d_recovery_r2"
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
            or not _valid_campaign_reserved_seconds(
                runner_receipt.get("campaign_seconds_reserved_after"),
                minimum=case["timeout_max_seconds"],
            )
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
    with performance_trace.stage("authorized_context_and_catalog"):
        execution_context = require_authorized_execution(case_id)
        cases = {case["case_id"]: case for case in load_prepared_cases()}
        if case_id not in cases:
            raise ValueError(f"unknown prepared VV3D case: {case_id}")
    return _run_prospective_case_with_context(
        case_id, cases[case_id], attempt_id, evidence_root,
        scientific_fingerprint=scientific_fingerprint,
        controller_fingerprint=controller_fingerprint,
        manifest_sha256=manifest_sha256,
        execution_context=execution_context,
    )


def _run_prospective_case_with_context(
    case_id: str,
    case: dict[str, Any],
    attempt_id: str,
    evidence_root: Path,
    *,
    scientific_fingerprint: str,
    controller_fingerprint: str,
    manifest_sha256: str,
    execution_context: dict[str, Any],
    prepared_mesh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the common prospective body with a caller-verified exact context."""

    # Imports with FEM effects are deliberately below the first fail-closed step.
    import time

    if (scientific_fingerprint != execution_context["scientific_fingerprint"]
            or controller_fingerprint != execution_context["controller_fingerprint"]
            or manifest_sha256 != execution_context["manifest_sha256"]
            or attempt_id != execution_context["attempt_id"]
            or evidence_root.resolve() != Path(execution_context["evidence_root"]).resolve()):
        raise PermissionError("caller fingerprints differ from the validated runner context")

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
        with performance_trace.stage("imports"):
            from solveur.api.public import FiniteElementModel, recover_solid_stress_field, solve_model
            from experiments.wp12_vv3d_adaptive import field_error_draft, load_assembly_draft, metrics, oracle

        with performance_trace.stage("model_preparation"):
            if prepared_mesh is None:
                prepared = json.loads((CAMPAIGN_DIR / case["mesh_file"]).read_bytes())
            else:
                prepared = prepared_mesh
            family = case["formulation"]
            denominator = prepared["integer_coordinate_denominator"]
            coordinates = [tuple(value / denominator for value in point) for point in prepared["nodes_integer"]]
            trace = performance_trace.current()
            if trace is not None:
                trace.event("model_preparation", "MESH", nodes=len(coordinates),
                            elements=len(prepared["connectivity_zero_based"]), dofs=3 * len(coordinates))

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

        with performance_trace.stage("body_load_order_8"):
            load8 = load_assembly_draft.assemble_body_load(
                prepared, order=8,
                execution_context={key: execution_context[key] for key in _PERMIT_CONTEXT_KEYS},
                permit_validator=permit_validator,
            )
        with performance_trace.stage("body_load_order_12"):
            nodal_load = load_assembly_draft.assemble_body_load(
                prepared, order=12,
                execution_context={key: execution_context[key] for key in _PERMIT_CONTEXT_KEYS},
                permit_validator=permit_validator,
            )
        with performance_trace.stage("load_checks_and_model_inputs"):
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
        with performance_trace.stage("finite_element_model"):
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
        with performance_trace.stage("solve_model"), performance_trace.instrument_static_solver(performance_trace.current()):
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
        with performance_trace.stage("stress_recovery"):
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

        # Evaluate with an independent postprocessor and 8/12-point rules.
        # Agreement is an observation until the Owner freezes the gate.
        with performance_trace.stage("extract_displacements"):
            nodal_u = [tuple(float(result.displacements[result.dofs.index(node, dof)])
                             for dof in ("UX", "UY", "UZ")) for node in range(len(coordinates))]
        with performance_trace.stage("independent_errors_order_8"):
            error8 = field_error_draft.integrated_errors(prepared, nodal_u, order=8)
        with performance_trace.stage("independent_errors_order_12"):
            error12 = field_error_draft.integrated_errors(prepared, nodal_u, order=12)
        postprocess_trace = performance_trace.current()
        postprocess_started = time.monotonic()
        if postprocess_trace is not None:
            postprocess_trace.event("postprocess_metrics", "START")
        exact_scalar_energy = oracle.exact_energy_j()
        for order, error_record in ((8, error8), (12, error12)):
            scalar_energy = error_record["scalar_energy_j"]
            error_record["scalar_energy_relative_error"] = abs(scalar_energy - exact_scalar_energy) / exact_scalar_energy
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
                "solver static-equilibrium convention: ||r_reduced||2 / max(||F_reduced||2, 1 N)"
            )
            payload["observables"]["vv3d_free_residual_relative"] = (
                _free_residual_observable(equilibrium)
            )
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

        if postprocess_trace is not None:
            postprocess_trace.event("postprocess_metrics", "END", duration_seconds=time.monotonic() - postprocess_started)

        # Acceptance-quality samples still need approved independent quadrature;
        # keep criteria explicitly unassessed.
        payload["execution"] = {"status": "COMPLETED_UNASSESSED", "attempt_reserved": True, "fem_started": True}
        payload["observables"]["elapsed_seconds"] = {"status": "AVAILABLE", "value": time.perf_counter() - started, "unit": "s"}
        payload["execution"]["status"] = "COMPLETED_UNASSESSED"
        with performance_trace.stage("criteria_evaluation"):
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
        with performance_trace.stage("serialize_and_archive"):
            evidence.write_observables(evidence_root, case_id, attempt_id, sanitize_for_evidence(payload))


def _relative_observable_difference(low: dict[str, Any], high: dict[str, Any]) -> dict[str, float]:
    keys = ("displacement_relative_l2", "energy_error_relative", "strain_error_relative",
            "stress_error_relative", "scalar_energy_relative_error")
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


def _free_residual_observable(equilibrium: dict[str, Any]) -> dict[str, Any]:
    """Bind the VV3D gate to the solver's documented reduced-equation residual."""
    value = equilibrium.get("free_relative_residual")
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0.0):
        raise ValueError("solver audit has no finite nonnegative free relative residual")
    return {
        "status": "AVAILABLE",
        "value": float(value),
        "unit": "1",
        "formula": "||r_reduced||2 / max(||F_reduced||2, 1 N)",
        "source": "solveur.core.audit.static_equilibrium_summary.free_relative_residual",
    }


def process_archived_qpost(candidate_id: str, archive: dict[str, Any]) -> dict[str, Any]:
    """Pure archived-displacement postprocessing; no solve or assembly occurs.

    Expected archive schema is ``qf-wp12-vv3d-state-archive-v1`` with the exact
    catalog seed case, mesh SHA, source manifest/attempt identity and a finite
    node-major full-order displacement vector. The caller must separately
    validate archive bytes against the controller receipt before using this
    function; this pure helper is used directly only with synthetic fixtures.
    """
    _, candidates, _ = _adaptive_inventory()
    candidate = candidates.get(candidate_id)
    if candidate is None or candidate.get("execution_kind") != "POSTPROCESS_ONLY":
        raise ValueError("QPOST candidate is outside the closed archived-state set")
    bindings = _adaptive_bindings(candidate)
    if (not isinstance(archive, dict)
            or archive.get("schema") != "qf-wp12-vv3d-state-archive-v1"
            or archive.get("campaign_id") != "WP12-VV3D-ADAPTIVE-20261029-R1"
            or archive.get("case_id") != candidate["seed_case"]
            or archive.get("mesh_sha256") != bindings["mesh_sha256"]
            or archive.get("case_state") != "OWNER_AUTHORIZED_EXECUTION"
            or archive.get("execution_status") != "COMPLETED_UNASSESSED"
            or not re.fullmatch(r"[0-9a-f]{64}", str(archive.get("manifest_sha256", "")))
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,79}", str(archive.get("attempt_id", "")))):
        raise ValueError("archived QPOST state is not bound to the exact authorized seed case")
    prepared_path = _safe_catalog_file(candidate["prepared_mesh"]["path"])
    prepared = _strict_json(prepared_path.read_bytes(), "QPOST mesh")
    displacements = archive.get("nodal_displacements_m")
    if (not isinstance(displacements, list) or len(displacements) != 3 * len(prepared["nodes_integer"])
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                   for value in displacements)):
        raise ValueError("archived displacement vector is missing, nonfinite or has the wrong length")
    nodal_u = [tuple(float(displacements[3 * node + axis]) for axis in range(3))
               for node in range(len(prepared["nodes_integer"]))]
    from experiments.wp12_vv3d_adaptive import oracle, field_error_draft

    results = {order: field_error_draft.integrated_errors(prepared, nodal_u, order=order)
               for order in (8, 12)}
    for order in (8, 12):
        energy = results[order]["scalar_energy_j"]
        results[order]["scalar_energy_relative_error"] = abs(energy - oracle.exact_energy_j()) / oracle.exact_energy_j()
    metric_keys = (
        "displacement_relative_l2", "energy_error_relative", "stress_error_relative",
        "scalar_energy_relative_error",
    )
    differences: dict[str, float] = {}
    for name in metric_keys:
        low, high = results[8][name], results[12][name]
        scale = max(abs(low), abs(high))
        if not math.isfinite(low) or not math.isfinite(high) or scale <= 1e-30:
            return {"status": "NOT_ASSESSABLE", "reason": f"ZERO_OR_NONFINITE_DENOMINATOR:{name}",
                    "order_8": results[8], "order_12": results[12]}
        differences[name] = abs(low - high) / scale
    threshold = float(candidate["numerical_conditions"]["relative_observable_change_trigger_gt"])
    maximum = max(differences.values())
    return {
        "status": "COMPLETED_UNASSESSED",
        "candidate_id": candidate_id,
        "mesh_sha256": bindings["mesh_sha256"],
        "archive_attempt_id": archive["attempt_id"],
        "orders": [8, 12],
        "order_8": results[8],
        "order_12": results[12],
        "relative_changes": differences,
        "maximum_relative_change": maximum,
        "triggered": maximum > threshold,
        "threshold": threshold,
        "criteria_status": "DIAGNOSTIC_UNQUALIFIED",
    }


def run_registered_qpost_candidate(family: str) -> dict[str, Any]:
    """Controller-bound QPOST entry; persists a sidecar for success or processing failure."""
    candidate_id = f"VV3D-ADAPT-{family}-QPOST"
    receipt = require_adaptive_runner_receipt(candidate_id)
    archive_ref = receipt["archive"]
    attempt_id = receipt["postprocessing_job_id"]
    _, candidates, _ = _adaptive_inventory()
    candidate = candidates[candidate_id]
    outcome: dict[str, Any] = {"status": "NOT_EXPOSED"}
    failure: BaseException | None = None
    sidecar = {
        "schema": "qf-wp12-vv3d-observables-v1",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": candidate_id,
        "attempt_id": attempt_id,
        "case_state": "OWNER_AUTHORIZED_POSTPROCESS_ONLY",
        "mesh_sha256": candidate["prepared_mesh"]["sha256"],
        "scientific_fingerprint": receipt["scientific_fingerprint"],
        "controller_fingerprint": receipt["controller_fingerprint"],
        "manifest_sha256": receipt["manifest_sha256"],
        "runner_receipt_sha256": receipt["receipt_sha256"],
        "archive_sha256": archive_ref["sha256"],
        "observables": {"qpost": {"status": "NOT_EXPOSED"}},
        "criteria": {"qpost_trigger": {"status": "NOT_ASSESSED"}},
        "execution": {"status": "STARTED", "attempt_reserved": False,
                      "postprocessing_reserved": True, "fem_started": False},
    }
    try:
        archive_path = Path(receipt["archive_path"])
        archive_raw = archive_path.read_bytes()
        if _sha256(archive_raw) != archive_ref["sha256"]:
            raise PermissionError("QPOST archived-state SHA-256 mismatch")
        archive = _strict_json(archive_raw, "QPOST archived state")
        if (archive.get("case_id") != archive_ref["source_case_id"]
                or archive.get("mesh_sha256") != archive_ref["source_mesh_sha256"]
                or archive.get("manifest_sha256") != archive_ref["source_manifest_sha256"]
                or archive.get("attempt_id") != archive_ref["source_attempt_id"]):
            raise PermissionError("QPOST archive contents differ from the runner receipt binding")
        outcome = process_archived_qpost(candidate_id, archive)
        sidecar["observables"]["qpost"] = outcome
        sidecar["execution"]["status"] = "COMPLETED_UNASSESSED"
    except BaseException as exc:
        failure = exc
        outcome = {"status": "FAILED_OR_INCOMPLETE", "error_type": type(exc).__name__, "error": str(exc)}
    finally:
        if failure is not None:
            sidecar["observables"]["qpost"] = outcome
            sidecar["execution"]["status"] = "FAILED_OR_INCOMPLETE"
            sidecar["execution"]["error_type"] = type(failure).__name__
        evidence.write_observables(Path(receipt["evidence_root"]), candidate_id, attempt_id,
                                   sanitize_for_evidence(sidecar))
    if failure is not None:
        raise failure
    return {"payload": sidecar, "outcome": outcome}


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
    if case_id.startswith("VV3D-ADAPT-"):
        _, candidates, _ = _adaptive_inventory()
        candidate = candidates.get(case_id)
        if candidate is None:
            raise ValueError(f"unknown prepared adaptive VV3D candidate: {case_id}")
        mesh_sha256 = candidate["prepared_mesh"]["sha256"]
    else:
        cases = {case["case_id"]: case for case in load_prepared_cases()}
        if case_id not in cases:
            raise ValueError(f"unknown prepared VV3D case: {case_id}")
        mesh_sha256 = cases[case_id]["mesh_sha256"]
    campaign_id = "WP12-VV3D-ADAPTIVE-20261029-R1" if case_id.startswith("VV3D-ADAPT-") else "WP12-VV3D-RECOVERY-20261030-R2"
    return {
        "schema": "qf-wp12-vv3d-observables-v1",
        "campaign_id": campaign_id,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "case_state": "PREPARED_NOT_AUTHORIZED",
        "mesh_sha256": mesh_sha256,
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
    trace = None
    if os.environ.get("QF_VV3D_PERFORMANCE_TRACE") == "1":
        if case_id != "VV3D-TET4-L3":
            raise PermissionError("performance tracing is restricted to the exact TET4-L3 diagnostic")
        evidence_root = Path(context["evidence_root"]).resolve(strict=True)
        path = (evidence_root / "diagnostic-timings" / case_id / context["attempt_id"] / "stages.jsonl").resolve()
        if not path.is_relative_to(evidence_root):
            raise PermissionError("performance trace escapes the authorized evidence root")
        trace = performance_trace.PerformanceTrace(path, case_id=case_id, attempt_id=context["attempt_id"])
    with trace if trace is not None else nullcontext():
        with performance_trace.stage("registered_case"):
            outcome = run_prospective_case(
                case_id,
                context["attempt_id"],
                Path(context["evidence_root"]),
                scientific_fingerprint=context["scientific_fingerprint"],
                controller_fingerprint=context["controller_fingerprint"],
                manifest_sha256=context["manifest_sha256"],
            )
        with performance_trace.stage("acceptance"):
            assert_prospective_acceptance(outcome["payload"])
        return outcome
