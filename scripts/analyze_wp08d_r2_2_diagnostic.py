"""Read-only diagnostic evaluation of WP08-D R2.1 M2-to-M3 evidence.

This tool does not execute a model, reference solve, or replay and never writes
to the input evidence. It applies the proposed R2.2 definitions only as a
non-formal diagnostic; it cannot award points or change historical status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

PROPOSAL_PATH = ROOT / "qualification/0_2_9/wp08d_contact_requalification_r2_2_preparation.json"
DEFAULT_EVIDENCE_ROOT = ROOT / ("qualification/0_2_9/wp08d_contact_requalification_r2_runs/raw_r2_attempt_02")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_hash(path: Path, expected: Any) -> None:
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"invalid expected SHA-256: {path}")
    if _sha256(path) != expected:
        raise ValueError(f"evidence SHA-256 mismatch: {path}")


def diagnostic_status(gates: dict[str, dict[str, Any]], replay: dict[str, Any]) -> str:
    """Never report passing diagnostics when the required replay fails."""
    if replay.get("status") != "PASS":
        return "DIAGNOSTIC_REPLAY_FAIL_CLOSED"
    return (
        "DIAGNOSTIC_GATES_PASS"
        if gates and all(g.get("status") == "PASS" for g in gates.values())
        else "DIAGNOSTIC_REFINEMENT_GATES_FAIL"
    )


def _result_path(evidence_root: Path, mesh: str, kind: str) -> Path:
    if kind == "production":
        return evidence_root / mesh / "production" / mesh / "result.json"
    return evidence_root / mesh / "replay" / mesh / "result.json"


def _raw_path(evidence_root: Path, mesh: str, kind: str) -> Path:
    return _result_path(evidence_root, mesh, kind).with_name("raw.npz")


def _read_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def analyze(evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> dict[str, Any]:
    """Recompute proposed R2.2 diagnostic gates from immutable R2.1 files."""

    from scripts.prepare_wp08d_structural_reference import MESH_LEVELS, generate_mesh
    from scripts.wp08d_phase1_common import replay_comparison
    from scripts.wp08d_refinement_metrics import (
        contact_region_area_fractions,
        evaluate_refinement_gate,
        lumped_slave_surface_areas,
        surface_region_resolution,
    )

    evidence_root = evidence_root.resolve()
    if not evidence_root.is_relative_to(ROOT.resolve()):
        raise ValueError("evidence root must remain inside this repository checkout")
    proposal = _read_json(PROPOSAL_PATH)
    if (
        proposal.get("status") != "PROPOSED_NOT_FROZEN_OWNER_REVIEW_REQUIRED"
        or proposal.get("execution_authority", {}).get("structural_solves_allowed") is not False
    ):
        raise ValueError("diagnostic requires the non-authorizing R2.2 preparation proposal")
    thresholds = proposal["parent_thresholds"]["values"]
    scales = proposal["refinement_normalization_proposal"]["characteristic_scales"]
    provenance = proposal["preparation_provenance"]
    parent_path = ROOT / "qualification/0_2_9/wp08d_structural_reference_contract.json"
    parent = _read_json(parent_path)
    r21_path = ROOT / "qualification/0_2_9/wp08d_contact_requalification_r2_1_contract.json"
    _verify_hash(r21_path, provenance["parent_r2_1_contract_sha256"])
    r21 = _read_json(r21_path)
    canonical = json.dumps(parent, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != r21["parent_contract"]["canonical_sha256"]:
        raise ValueError("parent contract digest mismatch")
    if thresholds != parent["refinement_contract"]["thresholds"]:
        raise ValueError("proposal thresholds differ from frozen parent")
    _verify_hash(evidence_root / "wp08d_requalification_summary.json", provenance["parent_r2_1_summary_sha256"])
    expected_hashes = proposal["diagnostic_recomputation_from_existing_r2_1"]["raw_evidence_sha256"]
    source = subprocess.check_output(
        ["git", "show", provenance["parent_r2_1_execution_sha"] + ":scripts/prepare_wp08d_structural_reference.py"],
        cwd=ROOT,
    )
    if source != (ROOT / "scripts/prepare_wp08d_structural_reference.py").read_bytes():
        raise ValueError("mesh generator differs from historical execution source")

    results: dict[str, dict[str, Any]] = {}
    raw_hashes: dict[str, dict[str, str]] = {}
    for mesh in ("M1", "M2", "M3"):
        result_path = _result_path(evidence_root, mesh, "production")
        raw_path = _raw_path(evidence_root, mesh, "production")
        if not result_path.is_file() or not raw_path.is_file():
            raise FileNotFoundError(f"required immutable {mesh} production evidence is missing")
        _verify_hash(result_path, expected_hashes[f"{mesh}_production_result"])
        _verify_hash(raw_path, expected_hashes[f"{mesh}_production_npz"])
        result = _read_json(result_path)
        if result.get("status") != "PASS" or result.get("terminal_classification") != "PASS":
            raise ValueError(f"{mesh} primary result is not terminal PASS")
        results[mesh] = result
        raw_hashes[f"{mesh}_production_result"] = {
            "path": result_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(result_path),
        }
        raw_hashes[f"{mesh}_production_npz"] = {
            "path": raw_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(raw_path),
        }

    # Keep the source/contract/policy binding identical across levels.
    binding_fields = (
        "execution_sha",
        "requalification_contract_sha256",
        "parent_contract_digest",
        "policy_digest",
        "governing_base_sha",
        "owner_decision_sha256",
    )
    bindings: dict[str, Any] = {}
    for mesh, result in results.items():
        auth = result.get("phase1", {}).get("authorization", {})
        if not isinstance(auth, dict) or any(field not in auth for field in binding_fields):
            raise ValueError(f"{mesh} phase1 authorization binding is incomplete")
        bindings[mesh] = {field: auth[field] for field in binding_fields}
    if not all(bindings[mesh] == bindings["M1"] for mesh in ("M2", "M3")):
        raise ValueError("source/contract/policy/Owner binding differs across mesh levels")
    expected_binding = {
        "execution_sha": provenance["parent_r2_1_execution_sha"],
        "requalification_contract_sha256": provenance["parent_r2_1_contract_sha256"],
        "parent_contract_digest": r21["parent_contract"]["canonical_sha256"],
        "policy_digest": r21["governing"]["policy_digest"],
        "governing_base_sha": r21["governing"]["source_baseline_sha"],
        "owner_decision_sha256": r21["owner_decision"]["sha256"],
    }
    if any(binding != expected_binding for binding in bindings.values()):
        raise ValueError("execution binding differs from the historical frozen contract")

    observable_pairs = {
        "selected_displacement": ("selected_displacement", "selected_displacement"),
        "reaction_resultant": ("reaction_resultant", "reaction_resultant"),
        "reaction_moment": ("reaction_moment", "reaction_moment"),
        "normal_contact_resultant": ("normal_contact_resultant", "normal_contact_resultant"),
        "tangential_contact_resultant": (
            "tangential_contact_resultant",
            "tangential_contact_resultant",
        ),
        "cumulative_dissipation": (
            "cumulative_local_dissipation",
            "cumulative_dissipation",
        ),
    }
    gate_results: dict[str, dict[str, Any]] = {}
    for threshold_name, (observable, scale_name) in observable_pairs.items():
        scale = float(scales[scale_name]["value"])
        gate_results[threshold_name] = evaluate_refinement_gate(
            threshold_name,
            results["M2"]["observables"][observable],
            results["M3"]["observables"][observable],
            characteristic_scale=scale,
            threshold=float(thresholds[threshold_name]),
        )

    regions: dict[str, dict[str, Any]] = {}
    for level in MESH_LEVELS:
        result = results[level.name]
        mesh = generate_mesh(level)
        weights = lumped_slave_surface_areas(mesh.nodes, mesh.bottom_faces, mesh.slave_nodes)
        region = contact_region_area_fractions(result["contact"]["contacts"], weights)
        region["surface_resolution_status"] = surface_region_resolution(
            mesh.nodes, [row["slave_node"] for row in result["contact"]["contacts"] if row["active"]]
        )
        region["area_semantics"] = "HISTORICAL_PROPOSED_RENORMALIZED_NODAL_AREA_NOT_CONTINUUM_CONTACT_AREA"
        if not np.isclose(region["eligible_slave_area"], 2.0, rtol=1.0e-12, atol=1.0e-14):
            raise ValueError(f"{level.name} eligible tributary areas do not cover the frozen 2 m^2 patch")
        regions[level.name] = region

    gate_results["active_contact_region_measure"] = evaluate_refinement_gate(
        "active_contact_region_measure",
        regions["M2"]["active_contact_region_fraction"],
        regions["M3"]["active_contact_region_fraction"],
        characteristic_scale=float(scales["active_contact_region_measure"]["value"]),
        threshold=float(thresholds["active_contact_region_measure"]),
    )
    gate_results["stick_slip_region_measure"] = evaluate_refinement_gate(
        "stick_slip_region_measure",
        regions["M2"]["stick_slip_region_vector"],
        regions["M3"]["stick_slip_region_vector"],
        characteristic_scale=float(scales["stick_slip_region_measure"]["value"]),
        threshold=float(thresholds["stick_slip_region_measure"]),
    )

    replay_result_path = _result_path(evidence_root, "M1", "replay")
    replay_raw_path = _raw_path(evidence_root, "M1", "replay")
    if not replay_result_path.is_file() or not replay_raw_path.is_file():
        raise FileNotFoundError("contract-required M1 replay evidence is missing")
    _verify_hash(replay_result_path, expected_hashes["M1_replay_result"])
    _verify_hash(replay_raw_path, expected_hashes["M1_replay_npz"])
    replay = _read_json(replay_result_path)
    replay_result = replay_comparison(
        results["M1"],
        replay,
        raw_reference=_read_npz(_raw_path(evidence_root, "M1", "production")),
        raw_replay=_read_npz(replay_raw_path),
    )
    raw_hashes["M1_replay_result"] = {
        "path": replay_result_path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(replay_result_path),
    }
    raw_hashes["M1_replay_npz"] = {
        "path": replay_raw_path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(replay_raw_path),
    }

    return {
        "schema_version": 1,
        "artifact_id": "QF-029-WP08-D-R2.2-READ-ONLY-DIAGNOSTIC",
        "status": diagnostic_status(gate_results, replay_result),
        "integrity_status": "PASS_VERIFIED_AGAINST_DECLARED_HASHES",
        "formal_qualification": False,
        "historical_r2_1_reclassified": False,
        "structural_solves_run": False,
        "reference_solves_run": False,
        "replays_run": False,
        "execution_bindings_by_mesh": bindings,
        "mesh_region_measures": regions,
        "m2_to_m3_gates": gate_results,
        "existing_m1_replay_recomparison": replay_result,
        "raw_evidence_hashes": raw_hashes,
        "official_points_awarded": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    args = parser.parse_args()
    try:
        report = analyze(args.evidence_root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "FAIL_CLOSED", "error": f"{type(error).__name__}: {error}"}, indent=2))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "DIAGNOSTIC_GATES_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
