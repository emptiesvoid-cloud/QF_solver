"""Preparation-only VV3D case metadata and synthetic sidecar helpers.

This module does not import QF Solver or perform any FEM operation. Its guard is
deliberately unconditional until an official controller and approved manifests
are integrated.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from experiments.wp12_vv3d_adaptive import evidence

CAMPAIGN_DIR = Path(__file__).parent / "prepared_20261029"
MATRIX_PATH = CAMPAIGN_DIR / "MATRIX_NOT_AUTHORIZED.json"
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
    "reaction_force_n",
    "reaction_moment_nm",
    "reaction_entries_n",
    "force_closure_n",
    "moment_closure_nm",
    "solver_origin",
    "elapsed_seconds",
    "peak_rss_mib",
    "independent_quadrature_4_8",
    "load_quadrature_4_8",
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
        if (case.get("execution_authorized") is not False or case.get("do_not_execute") is not True
                or case.get("nodeid_status") != "NOT_IMPLEMENTED_NOT_REGISTERED"):
            raise ValueError(f"case is not fail-closed: {case.get('case_id')}")
        mesh_name=case.get("mesh_file")
        if (not isinstance(mesh_name,str) or not mesh_name or "\\" in mesh_name
                or Path(mesh_name).name != mesh_name or mesh_name in {".",".."}):
            raise ValueError("prepared mesh filename escapes its directory")
        mesh_path = CAMPAIGN_DIR / mesh_name
        if hashlib.sha256(mesh_path.read_bytes()).hexdigest() != case.get("mesh_sha256"):
            raise ValueError(f"prepared mesh hash mismatch: {case.get('case_id')}")
    return cases


def require_authorized_execution(_case_id: str) -> None:
    """Refuse all FEM entry until the official control and manifest path exists."""
    raise PermissionError("PREPARED_NOT_AUTHORIZED: official controller/manifests are not integrated")


def run_prospective_case(
    case_id: str,
    attempt_id: str,
    evidence_root: Path,
    *,
    scientific_fingerprint: str,
    controller_fingerprint: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Prospective model/solve/postprocess body, behind the unconditional gate.

    No caller can reach imports or FEM work until the official execution path is
    integrated and this guard is deliberately replaced in a reviewed change.
    Sidecar persistence is in ``finally`` and precedes any caller assertions.
    """
    require_authorized_execution(case_id)

    # Imports with FEM effects are deliberately below the first fail-closed step.
    import time

    cases = {case["case_id"]: case for case in load_prepared_cases()}
    if case_id not in cases:
        raise ValueError(f"unknown prepared VV3D case: {case_id}")
    case = cases[case_id]
    payload = synthetic_not_exposed_payload(case_id, attempt_id)
    payload.update({
        "scientific_fingerprint": scientific_fingerprint,
        "controller_fingerprint": controller_fingerprint,
        "manifest_sha256": manifest_sha256,
        "case_state": "AUTHORIZED_EXECUTION_UNASSESSED",
    })
    payload["execution"] = {"status": "STARTED", "attempt_reserved": True, "fem_started": False}
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
        load4 = load_assembly_draft.assemble_body_load(prepared, order=4)
        nodal_load = load_assembly_draft.assemble_body_load(prepared, order=8)
        if len(nodal_load) != 3 * len(coordinates) or not all(math.isfinite(value) for value in nodal_load):
            raise ValueError("body-load adapter returned an invalid global nodal vector")
        if len(load4) != len(nodal_load) or not all(math.isfinite(value) for value in load4):
            raise ValueError("comparison load quadrature returned an invalid global nodal vector")
        def nodal_triples(vector):
            return [tuple(vector[3*node+axis] for axis in range(3)) for node in range(len(coordinates))]
        zeros=[(0.0,0.0,0.0)]*len(coordinates)
        balance4=metrics.force_moment_balance(coordinates,nodal_triples(load4),zeros)
        balance8=metrics.force_moment_balance(coordinates,nodal_triples(nodal_load),zeros)
        exact_balance=oracle.exact_global_balance()
        payload["observables"]["load_quadrature_4_8"]={
            "status":"DIAGNOSTIC_UNQUALIFIED", "order_4":balance4, "order_8":balance8,
            "exact_body_force_n":exact_balance["body_force_n"],
            "exact_body_moment_origin_nm":exact_balance["body_moment_origin_nm"],
            "note":"quadrature convergence and independent load oracle require Owner-frozen criteria",
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
        payload["observables"]["nodal_displacements_m"] = {
            "status": "AVAILABLE", "value": result.displacements.tolist(), "unit": "m",
            "ordering": "solver full degree-of-freedom map",
        }
        payload["observables"]["nodal_loads_n"] = {
            "status": "AVAILABLE", "value": nodal_load, "unit": "N",
            "ordering": "node-major UX UY UZ",
        }
        payload["observables"]["solver_origin"] = {"status": "NOT_EXPOSED"}
        recovered = recover_solid_stress_field(model, result.displacements)
        payload["observables"]["strain_samples"] = {
            "status": "AVAILABLE", "value": recovered["elements"],
            "component_order": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"],
            "strain_shear": "engineering", "integration_rule": "solver recovery points",
        }
        payload["observables"]["stress_samples_pa"] = {
            "status": "AVAILABLE", "value": recovered["elements"],
            "component_order": ["XX", "YY", "ZZ", "XY", "YZ", "ZX"],
            "shear": "tensor", "integration_rule": "solver recovery points",
        }

        # Evaluate with independent reference basis derivatives and 4/8-point
        # rules. Agreement is an observation until the Owner freezes the gate.
        nodal_u = [tuple(float(result.displacements[result.dofs.index(node, dof)])
                         for dof in ("UX", "UY", "UZ")) for node in range(len(coordinates))]
        error4 = field_error_draft.integrated_errors(prepared, nodal_u, order=4)
        error8 = field_error_draft.integrated_errors(prepared, nodal_u, order=8)
        payload["observables"]["independent_quadrature_4_8"] = {
            "status": "DIAGNOSTIC_UNQUALIFIED", "order_4": error4, "order_8": error8,
            "note": "quadrature agreement and field norms require frozen Owner criteria",
        }
        for name, key, unit in (
            ("displacement_l2_m_5_2", "displacement_l2_m_5_2", "m^(5/2)"),
            ("energy_error_norm_sqrt_j", "energy_error_norm_sqrt_j", "sqrt(J)"),
            ("strain_l2", "strain_error_l2_m_3_2", "m^(3/2)"),
            ("stress_l2_pa", "stress_error_l2_pa_m_3_2", "Pa m^(3/2)"),
        ):
            payload["observables"][name] = {"status": "DIAGNOSTIC_UNQUALIFIED", "value": error8[key], "unit": unit}

        equilibrium = result.audit.equilibrium if result.audit is not None else {}
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
        if "reactions" in equilibrium:
            payload["observables"]["reaction_entries_n"] = {
                "status": "AVAILABLE", "value": equilibrium["reactions"], "unit": "N or N m by component",
            }

        # Acceptance-quality samples still need approved independent quadrature;
        # keep criteria explicitly unassessed.
        payload["execution"] = {"status": "COMPLETED_UNASSESSED", "attempt_reserved": True, "fem_started": True}
        payload["observables"]["elapsed_seconds"] = {"status": "AVAILABLE", "value": time.perf_counter() - started, "unit": "s"}
        payload["criteria"]["field_error"] = {"status": "NOT_IMPLEMENTED", "reason": "independent evaluation quadrature not approved"}
        payload["criteria"]["energy_error"] = {"status": "NOT_IMPLEMENTED", "reason": "independent evaluation quadrature not approved"}
        payload["criteria"]["three_level_convergence"] = {"status": "NOT_IMPLEMENTED", "reason": "cross-case authorized batch not available"}
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


def assert_prospective_acceptance(payload: dict[str, Any]) -> None:
    """Keep result assertions closed until an approved criteria revision exists."""
    if payload.get("case_state") == "PREPARED_NOT_AUTHORIZED":
        raise PermissionError("PREPARED_NOT_AUTHORIZED: no result assertions may run")
    raise NotImplementedError("VV3D acceptance thresholds and evaluation quadrature are not frozen")


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
