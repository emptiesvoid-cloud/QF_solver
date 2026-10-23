#!/usr/bin/env python3
"""Apply the rational interval evaluator to hash-verified per-action inputs."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Permit the documented isolated (-I -S) direct-script invocation. Only this
# hash-bound proof directory is added; ambient working-directory imports stay off.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rigorous_math import RationalInterval, evaluate_margin
from production_branch_budget import certify_production_branch


EXPECTED_ACTION_POINTS = {
    "tet4-perfect-historical-weak-projected": 12,
    "tet4-perfect-mixed-projected": 12,
    "tet4-hardening-historical-weak-projected": 12,
    "tet4-hardening-mixed-projected": 12,
    "hex8-perfect-historical-weak-projected": 64,
    "hex8-perfect-mixed-projected": 64,
    "hex8-hardening-historical-weak-projected": 64,
    "hex8-hardening-mixed-projected": 64,
}


def fraction(obj: dict[str, str]):
    from fractions import Fraction
    return Fraction(int(obj["numerator"]), int(obj["denominator"]))


def interval(obj: dict[str, Any]) -> RationalInterval:
    return RationalInterval(fraction(obj["lo"]), fraction(obj["hi"]))


def decisive_segment_interval(result: dict[str, Any], expected_branch: str) -> RationalInterval:
    """Return the branch-specific extremum enclosure over the full segment."""
    key = "minimum_margin_range" if expected_branch == "plastic" else "maximum_margin_range" if expected_branch == "elastic" else None
    if key is None or key not in result:
        raise ValueError("branch-specific segment extremum is missing or branch is invalid")
    return interval(result[key])


def summarize_segment_bounds(records: list[tuple[str, RationalInterval, RationalInterval]]) -> tuple[RationalInterval, RationalInterval]:
    """Aggregate full margin range and minimum strict clearance across mixed branches."""
    if not records:
        raise ValueError("cannot summarize an empty action")
    all_lows = [margin.lo for _, margin, _ in records]
    all_highs = [margin.hi for _, margin, _ in records]
    clearances = [decisive.lo if branch == "plastic" else -decisive.hi
                  for branch, _, decisive in records]
    return RationalInterval(min(all_lows), max(all_highs)), RationalInterval(min(clearances))


def outward(payload: RationalInterval) -> dict[str, Any]:
    from rigorous_math import serialize_interval
    return serialize_interval(payload)


def combined_verdict(statuses: list[str]) -> str:
    # Invalid provenance defeats a certificate; a proved contradiction is next.
    if "INVALID_PROTOCOL" in statuses: return "INVALID_PROTOCOL"
    if "FAIL" in statuses: return "FAIL"
    if statuses and all(status=="PASS" for status in statuses): return "PASS"
    return "INCONCLUSIVE"


def final_status(technical_aggregate: str) -> dict[str, str]:
    """Map the technical aggregation to the allowed owner-facing status tokens."""
    mapping = {
        "PASS": ("C03_PROOF_READY_FOR_OWNER_REVIEW", "READY_FOR_OWNER_REVIEW", "PROPOSED_NOT_PROMOTED"),
        "FAIL": ("C03_PROOF_PARTIAL", "NOT_READY", "NOT_ELIGIBLE"),
        "INCONCLUSIVE": ("C03_PROOF_INCONCLUSIVE", "NOT_READY", "NOT_ELIGIBLE"),
        "INVALID_PROTOCOL": ("C03_PROOF_INVALID", "NOT_READY", "NOT_ELIGIBLE"),
    }
    try:
        owner_verdict, owner_status, certificate_status = mapping[technical_aggregate]
    except KeyError as exc:
        raise ValueError(f"unknown technical aggregate verdict: {technical_aggregate}") from exc
    return {
        "global_verdict": owner_verdict,
        "technical_aggregate_verdict": technical_aggregate,
        "owner_status": owner_status,
        "certificate_status": certificate_status,
    }


def _all_root_checks_pass(value: Any) -> bool:
    """Check serialized square inequalities without recomputing any roots."""
    if isinstance(value, dict):
        if "lower_squared_le_input" in value or "upper_squared_ge_input" in value:
            if value.get("lower_squared_le_input") is not True or value.get("upper_squared_ge_input") is not True:
                return False
        return all(_all_root_checks_pass(item) for item in value.values())
    if isinstance(value, list):
        return all(_all_root_checks_pass(item) for item in value)
    return True


def _point_branch_proof_passes(point: dict[str, Any]) -> bool:
    branch = point.get("expected_branch_from_archive")
    if branch not in ("plastic", "elastic") or point.get("production_branch_archived") != branch:
        return False
    if point.get("point_verdict") != "PASS" or point.get("mathematical_verdict_for_exact_real_target") != "PASS":
        return False
    bounds = point.get("bounds")
    root_checks = bounds.get("sqrt_squared_checks") if isinstance(bounds, dict) else None
    if not isinstance(root_checks, dict) or not root_checks or not _all_root_checks_pass(root_checks):
        return False
    decisive_key = "minimum_margin_range" if branch == "plastic" else "maximum_margin_range"
    decisive = bounds.get(decisive_key)
    if not isinstance(decisive, dict):
        return False
    decisive_interval = interval(decisive)
    if branch == "plastic" and decisive_interval.lo <= 0:
        return False
    if branch == "elastic" and decisive_interval.hi >= 0:
        return False
    production = point.get("production_branch_budget")
    if not isinstance(production, dict):
        return False
    required_true = (
        "archive_provenance_validated",
        "frozen_source_identity_validated",
        "production_branch_linkage_valid",
        "base_clearance_dominates_B",
    )
    if any(production.get(key) is not True for key in required_true):
        return False
    if production.get("verdict") != "PASS":
        return False
    if production.get("expected_branch") != branch or production.get("archived_elastic") != (branch == "elastic"):
        return False
    if production.get("mathematical_base_sign_status") != "PASS":
        return False
    if production.get("production_sign_status") != "PASS":
        return False
    if production.get("mathematical_segment_sign_status") != "PASS":
        return False
    if "a_posteriori_discrepancy_bound_B_exact" not in production:
        return False
    if production.get("rounding_budget_scope") != "a_posteriori_base_state_discrepancy_only_not_a_priori_segment_budget":
        return False
    return True


def action_proof_status(result: dict[str, Any]) -> str:
    """Classify one already serialized action proof, without reevaluating J2."""
    action_id = result.get("action_id")
    if action_id not in EXPECTED_ACTION_POINTS:
        return "INVALID_PROTOCOL"
    declared = result.get("action_verdict")
    if declared == "INVALID_PROTOCOL":
        return "INVALID_PROTOCOL"
    if declared == "FAIL":
        return "FAIL"
    if declared != "PASS":
        return "INCONCLUSIVE"
    expected_count = EXPECTED_ACTION_POINTS[action_id]
    points = result.get("points")
    if not isinstance(points, list) or len(points) != expected_count:
        return "INCONCLUSIVE"
    if len({point.get("point_id") for point in points if isinstance(point, dict)}) != expected_count:
        return "INCONCLUSIVE"
    action_gates = (
        "production_branch_linkage_valid",
        "production_rounding_budget_valid",
        "provenance_valid",
        "complete_archive_inputs_valid",
    )
    if any(result.get(key) is not True for key in action_gates):
        return "INCONCLUSIVE"
    if result.get("mathematical_candidate_verdict") != "PASS":
        return "INCONCLUSIVE"
    if result.get("mathematical_point_pass_count") != expected_count:
        return "INCONCLUSIVE"
    if result.get("production_point_pass_count") != expected_count:
        return "INCONCLUSIVE"
    if result.get("point_count") != expected_count:
        return "INCONCLUSIVE"
    if not all(_point_branch_proof_passes(point) for point in points):
        return "INCONCLUSIVE"
    return "PASS"


def _all_point_production_gate(result: dict[str, Any], gate: str) -> bool:
    """Derive an action-level production flag from every serialized point gate."""
    action_id = result.get("action_id")
    expected_count = EXPECTED_ACTION_POINTS.get(action_id)
    points = result.get("points")
    if expected_count is None or not isinstance(points, list) or len(points) != expected_count:
        return False
    for point in points:
        if not isinstance(point, dict):
            return False
        production = point.get("production_branch_budget")
        if not isinstance(production, dict) or production.get("verdict") != "PASS":
            return False
        if gate == "production_branch_linkage_valid":
            if production.get(gate) is not True:
                return False
        elif gate == "production_rounding_budget_valid":
            if (
                production.get("base_clearance_dominates_B") is not True
                or "a_posteriori_discrepancy_bound_B_exact" not in production
                or production.get("rounding_budget_scope")
                != "a_posteriori_base_state_discrepancy_only_not_a_priori_segment_budget"
            ):
                return False
        else:
            return False
    return True


def _decision_reason(verdict: str, action_count: int, point_count: int) -> str:
    if verdict == "PASS":
        return (
            f"PASS: all {action_count}/8 authorized actions and {point_count}/304 points "
            "have strict mathematical branch signs over the full frozen segments and "
            "certified production branch linkage at the archived base states. The "
            "production discrepancy bound is a-posteriori at the base only."
        )
    if verdict == "FAIL":
        return "FAIL: at least one verified action proves a branch-sign contradiction; see its point-level extremum evidence."
    if verdict == "INVALID_PROTOCOL":
        return "INVALID_PROTOCOL: an action identity or evidence schema is outside the frozen C03 proof contract."
    return "INCONCLUSIVE: extraction, full-segment sign, production base-linkage, or required point evidence is incomplete."


def derive_final_decision(extraction_inventory: dict[str, Any], action_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive readiness, aggregate, and reason together from checked proof records."""
    ids = [item.get("action_id") for item in action_results]
    extraction_ids = [item.get("action_id") for item in extraction_inventory.get("actions", [])]
    invalid_identities = (
        len(ids) != len(set(ids))
        or any(action_id not in EXPECTED_ACTION_POINTS for action_id in ids)
        or len(extraction_ids) != len(set(extraction_ids))
        or any(action_id not in EXPECTED_ACTION_POINTS for action_id in extraction_ids)
    )
    if invalid_identities:
        aggregate = "INVALID_PROTOCOL"
    else:
        statuses = [action_proof_status(item) for item in action_results]
        missing_ids = set(EXPECTED_ACTION_POINTS) - set(ids)
        extraction_missing_ids = set(EXPECTED_ACTION_POINTS) - set(extraction_ids)
        if (
            missing_ids
            or extraction_missing_ids
            or len(action_results) != 8
            or extraction_inventory.get("all_eight_raw_input_archives_complete") is not True
        ):
            statuses.append("INCONCLUSIVE")
        aggregate = combined_verdict(statuses)
    actual_point_count = sum(
        len(item.get("points", [])) for item in action_results if isinstance(item.get("points"), list)
    )
    status = final_status(aggregate)
    return {
        **status,
        "action_count": len(action_results),
        "point_count": actual_point_count,
        "strict_action_proofs_ready": aggregate == "PASS",
        "reason": _decision_reason(aggregate, len(action_results), actual_point_count),
    }


def validate_final_inventory(inventory: dict[str, Any]) -> None:
    """Reject internally contradictory final status fields or explanations."""
    aggregate = inventory.get("technical_aggregate_verdict")
    expected = final_status(aggregate)
    for key, value in expected.items():
        if inventory.get(key) != value:
            raise ValueError(f"final inventory field disagrees with aggregate: {key}")
    ready = aggregate == "PASS"
    if inventory.get("strict_action_proofs_ready") is not ready:
        raise ValueError("strict_action_proofs_ready disagrees with technical aggregate")
    if ready and (inventory.get("action_count") != 8 or inventory.get("candidate_point_count") != 304):
        raise ValueError("PASS inventory does not contain exactly eight actions and 304 points")
    expected_reason = _decision_reason(aggregate, inventory.get("action_count", 0), inventory.get("candidate_point_count", 0))
    if inventory.get("reason") != expected_reason:
        raise ValueError("final inventory reason contradicts its technical aggregate")


def build_final_inventory(
    extraction_inventory: dict[str, Any],
    action_results: list[dict[str, Any]],
    proof_result_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Combine extraction-stage metadata with serialized proof decisions."""
    inventory = deepcopy(extraction_inventory)
    if "extraction_stage" not in inventory:
        extraction_reason = inventory.pop("reason", None)
        inventory["extraction_stage"] = {
            "status": "INPUTS_EXTRACTED_PENDING_PROOF_EVALUATION",
            "strict_action_proofs_ready": False,
            "reason": extraction_reason or "Extraction did not evaluate branch linkage or full-segment signs.",
            "reason_stage": "historical_intermediate_extraction_message",
        }
    by_id = {item.get("action_id"): item for item in action_results}
    for action in inventory.get("actions", []):
        proof = by_id.get(action.get("action_id"))
        action["branch_linkage_valid"] = bool(proof and _all_point_production_gate(proof, "production_branch_linkage_valid"))
        action["production_rounding_budget_valid"] = bool(proof and _all_point_production_gate(proof, "production_rounding_budget_valid"))
        action["action_verdict"] = action_proof_status(proof) if proof else "INCONCLUSIVE"
    decision = derive_final_decision(extraction_inventory, action_results)
    inventory.update(decision)
    inventory["candidate_point_count"] = decision["point_count"]
    inventory["proof_results"] = deepcopy(proof_result_summaries)
    validate_final_inventory(inventory)
    return inventory


def serialize_json(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: Any) -> None:
    path.write_bytes(serialize_json(data))


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--proof-dir",type=Path,default=Path(__file__).parent)
    args=ap.parse_args()
    root=args.proof_dir
    # Revalidate all raw archive/source hashes and regenerate exact input files
    # in this same invocation before consuming them.
    subprocess.run([sys.executable,"-I","-S","-B",str(root/"archive_inputs.py"),"--output-dir",str(root)],check=True)
    inventory=json.loads((root/"archive_inventory.json").read_text(encoding="utf-8"))
    expected_ids={"tet4-perfect-historical-weak-projected","tet4-perfect-mixed-projected",
                  "tet4-hardening-historical-weak-projected","tet4-hardening-mixed-projected",
                  "hex8-perfect-historical-weak-projected","hex8-perfect-mixed-projected",
                  "hex8-hardening-historical-weak-projected","hex8-hardening-mixed-projected"}
    if len(inventory.get("actions",[]))!=8 or {x["action_id"] for x in inventory["actions"]}!=expected_ids:
        raise ValueError("proof input inventory must contain exactly the eight authorized actions")
    summary=[]
    action_outputs=[]
    all_points=0
    for action in inventory["actions"]:
        source=root/action["proof_input_path"]
        if sha256(source).lower()!=action["sha256"].lower():
            raise ValueError(f"proof input hash mismatch: {source.name}")
        data=json.loads(source.read_text(encoding="utf-8"))
        results=[]
        point_verdicts=[]
        math_verdicts=[]
        production_verdicts=[]
        segment_records=[]
        base_discrepancies=[]
        for point in data["points"]:
            result=evaluate_margin(
                interval(point["A_pa2"]),interval(point["B_pa2_per_m"]),interval(point["C_pa2_per_m2"]),
                interval(point["R_pa"]),interval(point["segment_s_m"]),point["expected_branch"],
                provenance_valid=data["provenance_valid"],
                production_branch_linkage_valid=data["production_branch_linkage_valid"],
                production_rounding_budget_valid=data["production_rounding_budget_valid"],
                complete_archive_inputs_valid=True,
            )
            math_verdicts.append(result["mathematical_verdict"])
            if "margin_range" not in result:
                raise ValueError(f"evaluator omitted margin range for {data['action_id']}:{point['point_id']}")
            segment=interval(result["margin_range"])
            decisive=decisive_segment_interval(result,point["expected_branch"])
            g0_result=evaluate_margin(
                interval(point["A_pa2"]),interval(point["B_pa2_per_m"]),interval(point["C_pa2_per_m2"]),
                interval(point["R_pa"]),RationalInterval(0),point["expected_branch"],
                provenance_valid=data["provenance_valid"],complete_archive_inputs_valid=True,
            )
            if "margin_range" not in g0_result:
                raise ValueError(f"evaluator omitted base margin for {data['action_id']}:{point['point_id']}")
            production=certify_production_branch(
                expected_branch=point["expected_branch"],
                archived_elastic=point["production_base_state_record"]["elastic"],
                archived_yield_function=point["production_base_state_record"].get("yield_function"),
                archived_plastic_multiplier=point["production_base_state_record"].get("plastic_multiplier"),
                E_binary64=float(fraction(data["elasticity_modulus_pa"])),
                nu_binary64=float(fraction(data["poisson_ratio"])),
                H_binary64=float(fraction(data["hardening_modulus_pa"])),
                g0_interval=interval(g0_result["margin_range"]),
                segment_extremum_interval=decisive,
                provenance_valid=data.get("provenance_valid"),
                source_identity_valid=data.get("source_identity_valid"),
            )
            production_verdicts.append(production.get("verdict","INVALID_PROTOCOL"))
            point_status=combined_verdict([result["mathematical_verdict"],production.get("verdict","INVALID_PROTOCOL")])
            point_verdicts.append(point_status)
            segment_records.append((point["expected_branch"],segment,decisive))
            if "a_posteriori_discrepancy_bound_B_exact" in production:
                base_discrepancies.append(fraction(production["a_posteriori_discrepancy_bound_B_exact"]))
            results.append({
                "point_id":point["point_id"],
                "expected_branch_from_archive":point["expected_branch"],
                "production_branch_archived":point["production_base_branch_archived"],
                "mathematical_verdict_for_exact_real_target":result["mathematical_verdict"],
                "production_branch_budget":production,
                "point_verdict":point_status,
                "reason":result["reason"],
                "production_base_state_record":point["production_base_state_record"],
                "bounds":{k:result[k] for k in ("radicand_range","resistance_range","sqrt_range","sqrt_squared_checks","margin_range","minimum_margin_range","maximum_margin_range") if k in result},
            })
        expected_count=12 if data["family"]=="TET4" else 64 if data["family"]=="HEX8" else None
        if expected_count is None or len(results)!=expected_count or len({r["point_id"] for r in results})!=expected_count:
            raise ValueError(f"unexpected point count or duplicate point IDs in {data['action_id']}")
        math_action=combined_verdict(math_verdicts)
        action_verdict=combined_verdict(point_verdicts)
        production_gate=all(v=="PASS" for v in production_verdicts)
        action_segment_range,minimum_clearance=summarize_segment_bounds(segment_records)
        branch_counts={name:sum(p["expected_branch"]==name for p in data["points"]) for name in ("plastic","elastic")}
        output={
            "schema_version":1,
            "action_id":data["action_id"],
            "family":data["family"],
            "expected_scope":"elastic_plastic_branch_stability on exact-real affine J2 path",
            "point_count":len(results),
            "branch_point_counts":branch_counts,
            "mathematical_point_pass_count":sum(v=="PASS" for v in math_verdicts),
            "production_point_pass_count":sum(v=="PASS" for v in production_verdicts),
            "mathematical_candidate_verdict":math_action,
            "action_verdict":action_verdict,
            "production_branch_linkage_valid":production_gate,
            "production_rounding_budget_valid":production_gate,
            "provenance_valid":data["provenance_valid"],
            "complete_archive_inputs_valid":True,
            "segment_margin_range_pa":outward(action_segment_range),
            "minimum_certified_clearance_pa":outward(minimum_clearance),
            "maximum_a_posteriori_base_discrepancy_B_pa":outward(RationalInterval(max(base_discrepancies))) if base_discrepancies else None,
            "production_branch_witness":"archived elastic/yield_function for elastic points; inverse division enclosure from archived plastic_multiplier and source operation graph for plastic points",
            "reason":"Exact-real segment signs and per-point production base branch enclosures were evaluated from hash-verified frozen inputs; see each production_branch_budget record for the a-posteriori discrepancy scope and numerical-value availability.",
            "proof_input_path":source.name,
            "proof_input_sha256":sha256(source),
            "points":results,
        }
        destination=root/f"{data['action_id']}.proof_result.json"
        write(destination,output)
        action_outputs.append(output)
        summary.append({"action_id":data["action_id"],"proof_input_sha256":sha256(source),"proof_result_path":destination.name,"proof_result_sha256":sha256(destination),"point_count":len(results),"branch_point_counts":branch_counts,"mathematical_point_pass_count":output["mathematical_point_pass_count"],"production_point_pass_count":output["production_point_pass_count"],"mathematical_candidate_verdict":math_action,"action_verdict":action_verdict,"production_gates_complete":production_gate,"minimum_certified_clearance_pa":output["minimum_certified_clearance_pa"],"maximum_a_posteriori_base_discrepancy_B_pa":output["maximum_a_posteriori_base_discrepancy_B_pa"]})
        all_points+=len(results)
    if all_points != 304:
        raise ValueError(f"expected exactly 304 authorized integration points, found {all_points}")
    decision=derive_final_decision(inventory,action_outputs)
    if decision["point_count"] != all_points:
        raise ValueError("final decision point count differs from evaluated points")
    table={"schema_version":1,**decision,"summary":summary}
    write(root/"proof_action_summary.json",table)
    final_inventory=build_final_inventory(inventory,action_outputs,summary)
    write(root/"archive_inventory.json",final_inventory)
    return 0


if __name__=="__main__": raise SystemExit(main())
