"""Verify the distinct historical WP04-C failure and accepted C2R6 mesh gate.

This is an evidence reader, not a solver or a new qualification execution.
No result, threshold, source digest or Owner decision is rewritten.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from scripts.git_tools import git_blob
from tests.helpers.recovered_evidence import load_verified_evidence_bytes


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_SHA = "0c7ecfaee74c1f0bb362afb1f0ac8bc45686c0ba"
CLOSURE_PATH = "qualification/0_2_9/wp04f/wp04_final_closure_audit.json"
CONTRACT_PATH = "qualification/0_2_9/wp04_c_tet4_campaign.json"
HISTORY_PATH = "qualification/0_2_9/wp04_c_tet4_structural_summary.json"
SOURCE_BINDINGS = {
    CLOSURE_PATH: "3bb1bbf9e0e0d9252bec3bc28d64174546484a913c19b7d926aafa61620c7533",
    CONTRACT_PATH: "011d8db0b5244e567524db1b89a4b7a2f8c791527291224c0501fbc3f2f72a0e",
    HISTORY_PATH: "66e640474fd052de1012e9a175605b98db09826b4a106db9d95d09dbd5aa0708",
}
LIMITS = {"displacement": 0.02, "reaction": 0.02, "energy": 0.02, "stress": 0.1}
ROUTE = {
    "linear_solver": "MINRES", "preconditioner": "Jacobi", "rtol": 1e-11,
    "atol": 1e-14, "maxiter": 10000, "direct_fallback": False,
    "line_search": "existing/enabled", "newton_tolerance": 1e-10,
    "increments": 12, "floor_aware_termination": True,
}
HISTORY_KEYS = {
    "displacement": "fine_medium_tip_displacement_relative",
    "reaction": "fine_medium_reaction_relative",
    "energy": "fine_medium_energy_relative",
    "stress": "fine_medium_stress_relative",
}
OBSERVABLE_KEYS = {
    "displacement": "tip_displacement", "energy": "strain_energy",
    "stress": "representative_stress_sigma_xx",
}
AUDIT_KEYS = {
    "displacement": "displacement_tip_proxy", "reaction": "reaction_resultant_norm",
    "energy": "strain_energy", "stress": "representative_stress_sigma_xx",
}


class WP04LineageError(ValueError):
    """Missing, inconsistent or reclassified evidence cannot satisfy this guard."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WP04LineageError(message)


def _number(value: Any) -> float:
    _require(not isinstance(value, bool) and isinstance(value, (int, float)), "A numeric observable is required.")
    result = float(value)
    _require(math.isfinite(result), "Nonfinite observable.")
    return result


def _equal(value: Any, expected: Any) -> None:
    _require(math.isclose(_number(value), _number(expected), rel_tol=1e-14, abs_tol=1e-15), "Recomputed metric mismatch.")


def _bound_current(path: str, root: Path) -> dict[str, Any]:
    blob, original = git_blob(SNAPSHOT_SHA, path, cwd=root)
    _require(hashlib.sha256(original).hexdigest() == SOURCE_BINDINGS[path], "Immutable source binding mismatch.")
    current = (root / path).read_bytes()
    # A Git checkout can transform line endings, but never numeric content.
    _require(current.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n"), "Current evidence differs from its original Git blob.")
    if path == HISTORY_PATH:
        _require(blob == "0138e7583c2e0ce0488c69ab8630f87118a299e6", "Original failure blob mismatch.")
    return json.loads(original)


def historical_failure_metrics(summary: dict[str, Any], contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Recompute the old coarse-mesh deltas and require their real FAIL status."""
    frozen = contract["campaigns"]["mesh_convergence"]["fine_vs_medium_limits"]
    _require(frozen == {
        "tip_displacement_relative": 0.02, "reaction_relative": 0.02,
        "strain_energy_relative": 0.02, "representative_stress_relative": 0.1,
    }, "Historical thresholds were changed.")
    _require(summary["gate_status"]["G04-10"]["status"] == "FAIL", "The original numerical failure was reclassified.")
    _require(summary["mesh_convergence"]["passes_fine_medium_limits"] is False, "Historical FAIL flag missing.")
    rows = summary["mesh_campaign"]
    for label, cells in {"M1": [8, 4, 4], "M2": [16, 8, 8], "M3": [24, 12, 12]}.items():
        _require(rows[label]["cells"] == cells, "Wrong historical mesh hierarchy.")
    output: dict[str, dict[str, Any]] = {}
    for name, key in HISTORY_KEYS.items():
        if name == "reaction":
            # The historical definition uses the resultant vector, not its norm.
            medium = [_number(v) for v in rows["M2"]["equilibrium"]["reaction_resultant"]]
            fine = [_number(v) for v in rows["M3"]["equilibrium"]["reaction_resultant"]]
            _require(len(medium) == len(fine) == 3, "Wrong reaction dimension.")
            delta = math.sqrt(sum((a - b) ** 2 for a, b in zip(fine, medium))) / max(math.sqrt(sum(v ** 2 for v in medium)), 1e-12)
        else:
            observable = {"displacement": "tip_displacement", "energy": "strain_energy", "stress": "representative_stress_sigma_xx"}[name]
            medium_value, fine_value = _number(rows["M2"][observable]), _number(rows["M3"][observable])
            delta = abs(fine_value - medium_value) / max(abs(medium_value), 1e-12)
        _equal(summary["mesh_convergence"][key], delta)
        passes = delta <= LIMITS[name]
        _require(passes is (name == "reaction"), "The historical pattern of three failed mesh gates changed.")
        output[name] = {"value": delta, "limit": LIMITS[name], "status": "PASS" if passes else "FAIL"}
    return output


def active_mesh_metrics(campaign: dict[str, Any], audit: dict[str, Any], closure: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Recompute the accepted C2R6 pair using only its original definitions."""
    section = closure["structural_evidence"]["tet4_c2r6"]
    _require(section["thresholds"] == LIMITS, "Accepted mesh thresholds changed.")
    _require(audit["route"] == ROUTE, "Frozen solver route mismatch.")
    _require(campaign["G04-10"] == audit["raw_campaign_top_level_g04_10"] == "UNRESOLVED", "Original runner placeholder was rewritten.")
    _require(audit["mesh_pair_thresholds"]["definition"] == "abs(fine-medium)/max(abs(fine),abs(medium),1e-12)", "Wrong C2R6 relative-delta definition.")
    for label, cells in {"C2-M2": [48, 24, 24], "C2-M3": [64, 32, 32]}.items():
        case = campaign["cases"][label]
        _require(case["status"] == "COMPLETED" and case["failure"] is None, "Incomplete active campaign.")
        _require(case["mesh_cells"] == cells and case["route"] == ROUTE, "Wrong active hierarchy or solver route.")
        _require(case["start_sha"] == audit["source_sha"], "Active execution SHA mismatch.")
        observables = case["observables"]
        factors = observables["accepted_load_factors"]
        _require(len(factors) == len(case["accepted_records"]) == len(observables["accepted_state_digests"]) == 12, "Accepted-path evidence incomplete.")
        for index, (factor, record) in enumerate(zip(factors, case["accepted_records"]), start=1):
            _equal(factor, index / 12)
            _equal(record["load_factor"], factor)
            _require(record["step"] == index and record["digest"] == observables["accepted_state_digests"][index - 1], "Accepted-state path mismatch.")
        for key in ("force_relative_error", "moment_relative_error"):
            _require(0 <= _number(observables["equilibrium"][key]) <= 1e-8, "Equilibrium gate failed.")
        _require(_number(observables["minimum_det_f"]) >= 0.2, "det(F) envelope failed.")
        _require(0.75 <= _number(observables["minimum_principal_stretch"]) <= _number(observables["maximum_principal_stretch"]) <= 1.3, "Stretch envelope failed.")
        _require(0 <= _number(observables["maximum_green_lagrange_norm"]) <= 0.3, "Strain envelope failed.")
        _require(section[label.replace("C2-", "")]["fallbacks"] == 0, "Closure fallback count mismatch.")
    medium = campaign["cases"]["C2-M2"]["observables"]
    fine = campaign["cases"]["C2-M3"]["observables"]
    output: dict[str, dict[str, Any]] = {}
    for name in LIMITS:
        observable_key = OBSERVABLE_KEYS.get(name)
        a = _number(medium[observable_key]) if observable_key else _number(medium["equilibrium"]["reaction_resultant_norm"])
        b = _number(fine[observable_key]) if observable_key else _number(fine["equilibrium"]["reaction_resultant_norm"])
        delta = abs(b - a) / max(abs(a), abs(b), 1e-12)
        recorded = audit["mesh_pair_thresholds"][AUDIT_KEYS[name]]
        _require(recorded["limit"] == LIMITS[name] and recorded["pass"] is True, "Audit threshold/status mismatch.")
        _equal(recorded["value"], delta)
        _equal(section["M2_to_M3_deltas"][name], delta)
        _require(delta <= LIMITS[name], "Active mesh convergence gate failed.")
        output[name] = {"value": delta, "limit": LIMITS[name], "status": "PASS"}
    _require(audit["mesh_pair_thresholds"]["all_pass"] is True, "Combined C2R6 gate not PASS.")
    return output


def verify_wp04_mesh_lineage(root: Path = ROOT) -> dict[str, Any]:
    """Check pinned bytes, raw JSON observables, historical failure and lineage."""
    closure = _bound_current(CLOSURE_PATH, root)
    contract = _bound_current(CONTRACT_PATH, root)
    history = _bound_current(HISTORY_PATH, root)
    preservation = closure["provenance"]["original_failure_preservation"]
    _require(preservation["preserved"] is True and preservation["original_gate"] == "FAIL", "Closure lost the original failure.")
    records = closure["source_audit"]["evidence_record_digests"]
    prefix = "qualification/0_2_9/c2r6/"
    payloads = {
        name: load_verified_evidence_bytes(prefix + name, records[prefix + name])
        for name in ("frozen_threshold_audit.json", "campaign_result.json", "m3_result.json")
    }
    audit = json.loads(payloads["frozen_threshold_audit.json"])
    campaign = json.loads(payloads["campaign_result.json"])
    m3 = json.loads(payloads["m3_result.json"])
    _require(audit["campaign_result_sha256"].lower() == hashlib.sha256(payloads["campaign_result.json"]).hexdigest(), "Audit/campaign hash mismatch.")
    _require(m3 == campaign["cases"]["C2-M3"], "Standalone M3 differs from campaign M3.")
    return {
        "status": "PASS_MESH_LINEAGE_ONLY",
        "historical_mesh_gates": historical_failure_metrics(history, contract),
        "accepted_c2r6_mesh_gates": active_mesh_metrics(campaign, audit, closure),
        "original_numerical_gate": "FAIL_PRESERVED",
        "c2r6_runner_placeholder": "UNRESOLVED_PRESERVED",
        "new_solve_performed": False, "thresholds_changed": False,
        "owner_points_changed": False,
        "limitations": ["JSON observable recomputation only; no new FEM solve or exhaustive replay of historical telemetry."],
    }
