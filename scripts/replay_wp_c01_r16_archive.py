"""Replay the R16 smoke archive and reconstruct its raw balance without FEM."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

FIXTURE_SHA256 = "b74c57cae86d94b4cbfdae0c298ea98aa660f70159c72eb4b72f0ee4b5eee3e5"
R16_RESULT_SHA256 = "43917c4e2f6e4ac4e72db26a327adbe32a98ef679d043425f787250bf0794752"
R14_RESULT_SHA256 = "ecaaf3480f0c29d209a1c68c063447bd335a7494901b7d1e23d3313e76cc56f9"
R16_CAMPAIGN = "WP-C01-R16-INTEGRATED-BSTAR-SMOKE-ONE-SHOT"
R16_SCENARIO = "R14_BSTAR_SLIP_INTEGRATED"
MOMENT_LIMIT_NM = 0.002
DOFS = ("UX", "UY", "UZ")
_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "tests" / "verification" / "wp_c01_r16_smoke_contract.py"
_CONTRACT_SPEC = importlib.util.spec_from_file_location("wp_c01_r16_smoke_contract", _CONTRACT_PATH)
if _CONTRACT_SPEC is None or _CONTRACT_SPEC.loader is None:
    raise RuntimeError("cannot load the local R16 smoke contract helper")
_CONTRACT_MODULE = importlib.util.module_from_spec(_CONTRACT_SPEC)
_CONTRACT_SPEC.loader.exec_module(_CONTRACT_MODULE)
validate_smoke_payload = _CONTRACT_MODULE.validate_smoke_payload


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _moment(nodes: np.ndarray, nodal_forces: np.ndarray) -> np.ndarray:
    return np.cross(nodes, nodal_forces).sum(axis=0)


def _assert_moment_contract(moment_norm_nm: float) -> None:
    if not math.isfinite(moment_norm_nm):
        raise AssertionError("independent moment reconstruction is non-finite")
    if moment_norm_nm > MOMENT_LIMIT_NM:
        raise AssertionError(
            f"independent raw moment {moment_norm_nm:.17g} N.m exceeds "
            f"the unchanged {MOMENT_LIMIT_NM:.17g} N.m contract limit"
        )


def _contact_generalized_forces(
    payload: dict[str, Any], fixture: dict[str, Any]
) -> np.ndarray:
    nodes = np.asarray(fixture["nodes"], dtype=float)
    master = [int(node) for node in fixture["contacts"][0]["master_nodes"]]
    slave = int(fixture["contacts"][0]["slave_node"])
    a, b, c = nodes[master]
    e1, e2 = b - a, c - a
    area_vector = np.cross(e1, e2)
    area2 = float(np.linalg.norm(area_vector))
    if area2 == 0.0:
        raise ValueError("R16 master triangle is degenerate")
    normal = area_vector / area2
    offset = nodes[slave] - a
    d00, d01, d11 = float(e1 @ e1), float(e1 @ e2), float(e2 @ e2)
    d20, d21 = float(offset @ e1), float(offset @ e2)
    denominator = d00 * d11 - d01 * d01
    beta1 = (d11 * d20 - d01 * d21) / denominator
    beta2 = (d00 * d21 - d01 * d20) / denominator
    beta = np.asarray([1.0 - beta1 - beta2, beta1, beta2])
    grad1 = np.cross(e2, normal) / area2
    grad2 = np.cross(normal, e1) / area2
    gradients = np.asarray([-grad1 - grad2, grad1, grad2])
    gap0 = float(normal @ (nodes[slave] - beta @ nodes[master]))

    contact = payload["contact"]["contacts"][0]
    tangents = (
        np.asarray(contact["tangent_one"], dtype=float),
        np.asarray(contact["tangent_two"], dtype=float),
    )
    tangential_force = np.asarray(contact["tangential_force"], dtype=float)
    pressure = float(contact["pressure"])
    dof_map = {
        int(row["node"]): {str(dof): int(index) for dof, index in row["dofs"].items()}
        for row in payload["audit"]["dof_map"]
    }
    displacement_size = len(payload["displacements_m"])
    operator = np.zeros((2, displacement_size), dtype=float)
    for axis, tangent in enumerate(tangents):
        for component, dof in enumerate(DOFS):
            operator[axis, dof_map[slave][dof]] += tangent[component]
        for j, node in enumerate(master):
            coefficient = -beta[j] * tangent + gap0 * float(gradients[j] @ tangent) * normal
            for component, dof in enumerate(DOFS):
                operator[axis, dof_map[node][dof]] += coefficient[component]

    nodal = np.zeros((len(nodes), 3), dtype=float)
    nodal[slave] -= pressure * normal
    for j, node in enumerate(master):
        nodal[node] += beta[j] * pressure * normal
    nodal += (operator.T @ tangential_force).reshape(len(nodes), 3)
    return nodal


def replay(r16: dict[str, Any], fixture: dict[str, Any], r14: dict[str, Any]) -> dict[str, Any]:
    events = validate_smoke_payload(r16)
    if r16.get("campaign_id") != R16_CAMPAIGN or r16.get("scenario_id") != R16_SCENARIO:
        raise ValueError("R16 campaign/scenario identity mismatch")
    if r16.get("fixture_sha256") != FIXTURE_SHA256:
        raise ValueError("R16 result is not bound to the approved fixture hash")
    if r16.get("units") != "SI" or r16.get("mode") != "small_rotation_work_conjugate":
        raise ValueError("R16 result units or transfer mode do not match the expected contract")

    if r16["nodes_m"] != r14["nodes_m"]:
        raise AssertionError("R16 node coordinates differ from R14")
    if r16["displacements_m"] != r14["displacements_m"]:
        raise AssertionError("R16 displacements differ from R14")
    if r16["contact"] != r14["contact"]:
        raise AssertionError("R16 contact result differs from R14")
    r14_events = validate_smoke_payload(r14)
    accepted16 = [event for event in events if event.get("event_type") == "STEP_ACCEPTED"]
    accepted14 = [event for event in r14_events if event.get("event_type") == "STEP_ACCEPTED"]
    for event16, event14 in zip(accepted16, accepted14, strict=True):
        if event16.get("step") != event14.get("step"):
            raise AssertionError("R16/R14 accepted checkpoint ordering differs")
        if event16.get("metrics", {}).get("committed_contact_state") != event14.get(
            "metrics", {}
        ).get("committed_contact_state"):
            raise AssertionError(f"R16 accepted checkpoint differs from R14 at step {event16.get('step')}")

    nodes = np.asarray(fixture["nodes"], dtype=float)
    displacement = np.asarray(r16["displacements_m"], dtype=float)
    nodal_forces = np.zeros((len(nodes), 3), dtype=float)
    factors = fixture["analysis"]["contact_load_history"][-1]
    for factor, load in zip(factors, fixture["loads"], strict=True):
        nodal_forces[int(load["node"]), DOFS.index(load["dof"])] += float(factor) * float(load["value"])
    reactions = r16["audit"]["equilibrium"].get("reactions")
    if not isinstance(reactions, list) or not reactions:
        raise ValueError("R16 archive has no fixed-support reactions")
    for reaction in reactions:
        nodal_forces[int(reaction["node"]), DOFS.index(reaction["dof"])] += float(reaction["value"])
    for spring in fixture.get("springs", []):
        node = int(spring["node_a"])
        for dof, stiffness in zip(spring["dofs"], spring["stiffness"], strict=True):
            nodal_forces[node, DOFS.index(dof)] -= float(stiffness) * displacement[3 * node + DOFS.index(dof)]

    contact_forces = _contact_generalized_forces(r16, fixture)
    external_moment = _moment(nodes, nodal_forces)
    contact_moment = _moment(nodes, contact_forces)
    total_force = nodal_forces.sum(axis=0) + contact_forces.sum(axis=0)
    total_moment = external_moment + contact_moment
    total_moment_norm = float(np.linalg.norm(total_moment))
    _assert_moment_contract(total_moment_norm)

    accepted = [event for event in events if event.get("event_type") == "STEP_ACCEPTED"]
    gaps = [float(event["metrics"]["committed_contact_state"]["gaps"][0]) for event in accepted]
    coulomb_slip_differences = []
    for event in accepted[7:]:
        committed = event["metrics"]["committed_contact_state"]
        pressure = float(committed["pressures"][0])
        force = np.asarray(committed["tangential_forces"][0], dtype=float)
        coulomb_slip_differences.append(abs(float(np.linalg.norm(force)) - 0.4 * pressure))

    return {
        "schema": "qfsolver-wp-c01-r16-archive-replay-v1",
        "verdict": "B_STAR_R16_ARCHIVE_REPLAY_PASS",
        "fem_rerun": False,
        "event_count": len(events),
        "accepted_step_count": len(accepted),
        "accepted_states": [event["metrics"]["committed_contact_state"]["tangential_states"][0] for event in accepted],
        "max_abs_gap_m": max(abs(gap) for gap in gaps),
        "max_slip_coulomb_difference_N": max(coulomb_slip_differences),
        "r16_r14_exact_fields": ["nodes_m", "displacements_m", "contact", "accepted committed_contact_state"],
        "independent_balance": {
            "moment_reference_m": [0.0, 0.0, 0.0],
            "external_support_spring_resultant_N": nodal_forces.sum(axis=0).tolist(),
            "external_support_spring_moment_Nm": external_moment.tolist(),
            "contact_resultant_N": contact_forces.sum(axis=0).tolist(),
            "contact_moment_Nm": contact_moment.tolist(),
            "combined_resultant_N": total_force.tolist(),
            "combined_moment_Nm": total_moment.tolist(),
            "combined_moment_norm_Nm": total_moment_norm,
            "contract_limit_Nm": MOMENT_LIMIT_NM,
            "passes_contract_limit": total_moment_norm <= MOMENT_LIMIT_NM,
            "source": "R16 archived reactions and result fields plus the SHA-bound fixture; independent B* nodal-force and cross-product reconstruction",
        },
        "r16_solver_audit_raw_moment_Nm_cross_check": r16["audit"]["equilibrium"]["raw_moment_imbalance_about_origin"],
        "r16_solver_audit_moment_correction_Nm_cross_check": r16["audit"]["equilibrium"]["contact_reference_moment_correction"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r16-result", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--r14-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite an existing replay report")

    r16 = _read_json(args.r16_result)
    fixture = _read_json(args.fixture)
    r14 = _read_json(args.r14_result)
    if _sha256(args.fixture) != FIXTURE_SHA256:
        parser.error("fixture SHA-256 does not match the approved R16 fixture")
    if _sha256(args.r16_result) != R16_RESULT_SHA256:
        parser.error("R16 result SHA-256 does not match the preserved original archive")
    if _sha256(args.r14_result) != R14_RESULT_SHA256:
        parser.error("R14 result SHA-256 does not match the preserved comparison archive")
    report = replay(r16, fixture, r14)
    report["input_sha256"] = {
        "r16_result": _sha256(args.r16_result),
        "fixture": _sha256(args.fixture),
        "r14_result": _sha256(args.r14_result),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"output_sha256={_sha256(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
