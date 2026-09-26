"""Freeze and execute the prospective M4-only WP08 surface-contact diagnostic.

R1.10 M1/M2/M3 inputs are hash-verified and reused read-only. M4 extends the
same dyadic hierarchy to 16x8x8 parent cells. Stick then slip run in separate,
sequential child processes. This is diagnostic only, never formal WP08 credit.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.prepare_wp08_area_supported_benchmark import (  # noqa: E402
    FRICTION_COEFFICIENT,
    HEIGHT_M,
    INITIAL_GAP_M,
    LENGTH_M,
    MeshLevel,
    NORMAL_RESULTANT_N,
    POISSON_RATIO,
    SLIP_TANGENTIAL_RESULTANT_N,
    STICK_TANGENTIAL_RESULTANT_N,
    TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
    WIDTH_M,
    _surface_geometry,
    generate_preflight,
)


ARTIFACT_ID = "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.10-M4"
PARENT_ARTIFACT_ID = "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.10"
OUTPUT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_m4_20260926"
)
DOC_REL = Path("docs/verification/0_2_9/wp08-area-supported-contact-r1-10-m4.md")
M1_ROOT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926"
)
PARENT_CONTRACT_REL = M1_ROOT_REL / "contract_r1_10_contact_requalification.json"
PARENT_BINDING_REL = M1_ROOT_REL / "freeze_binding_r1_10_contact_requalification.json"
PARENT_EXECUTION_BINDING_REL = M1_ROOT_REL / "execution_binding.json"
PARENT_M2M3_FINAL_REL = M1_ROOT_REL / "M2_M3" / "final.json"
M4_LEVEL = MeshLevel("M4", 16, 8, 8)
POLICY_DIGEST_CONTEXT = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
SOURCE_TESTS = (
    "tests/unit/test_contact_sparse_stick_assembly.py",
    "tests/unit/test_contact_surface_lumped_penalty.py",
    "tests/unit/test_contact_surface_tangential_stiffness.py",
    "tests/unit/test_frictional_contact_family_survey.py",
    "tests/unit/test_frictional_contact_structural_limit.py",
    "tests/unit/test_frictional_contact.py",
    "tests/unit/test_wp08_area_supported_benchmark_preflight.py",
    "tests/unit/test_wp08_area_supported_m1_runner_r1_10.py",
    "tests/unit/test_wp08_area_supported_m1_runner.py",
    "tests/unit/test_wp08_area_supported_m2_m3_runner_r1_10.py",
    "tests/unit/test_wp08_area_supported_m2_m3_runner.py",
    "tests/unit/test_wp08_area_supported_m4_runner.py",
    "tests/unit/test_wp08b_frictional_identities_rollback.py",
    "tests/unit/test_wp08c_friction_tangent_dissipation.py",
    "tests/unit/test_wp08d_active_set_remediation.py",
    "tests/unit/test_wp08d_independent_reference.py",
    "tests/unit/test_wp08d_mixed_open_active_slip.py",
    "tests/unit/test_wp08d_phase1_runner.py",
    "tests/unit/test_wp08_area_supported_m4_r1_10_runner.py",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _binding_sha(binding: Mapping[str, Any]) -> str:
    normalized = dict(binding)
    normalized["execution_binding_sha256"] = None
    return _canonical_sha(normalized)


def _write_json(path: Path, value: object, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _git_state() -> dict[str, str]:
    return {
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "porcelain_at_freeze": _git("status", "--porcelain"),
    }


def _source_inventory() -> dict[str, str]:
    files = {
        path
        for folder in (ROOT / "src", ROOT / "scripts")
        for path in folder.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    files.update(ROOT / relative for relative in SOURCE_TESTS)
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing bound source/test file: {missing[0]}")
    return {
        path.relative_to(ROOT).as_posix(): _sha(path)
        for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())
    }


def _parent_evidence() -> dict[str, Any]:
    """Verify the frozen R1.10 M1/M2/M3 campaign read-only before M4."""
    root = ROOT / M1_ROOT_REL
    m1_contract_path = root / "contract.json"
    m1_binding_path = root / "freeze_binding.json"
    m1_amendment_path = ROOT / PARENT_CONTRACT_REL
    m1_r1_10_binding_path = ROOT / PARENT_BINDING_REL
    m2_binding_path = ROOT / PARENT_EXECUTION_BINDING_REL
    m1_final_path = root / "final.json"
    m2_final_path = ROOT / PARENT_M2M3_FINAL_REL
    m1_contract = _json(m1_contract_path)
    m1_binding = _json(m1_binding_path)
    amendment = _json(m1_amendment_path)
    m1_r1_10_binding = _json(m1_r1_10_binding_path)
    m2_binding = _json(m2_binding_path)
    m1_final = _json(m1_final_path)
    m2_final = _json(m2_final_path)

    if _sha(m1_contract_path) != m1_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M1 contract SHA-256 mismatch.")
    if _sha(m1_binding_path) != amendment.get("parent_freeze_binding_sha256"):
        raise RuntimeError("R1.10 M1 parent freeze-binding hash mismatch.")
    normalized_r1_10_binding = dict(m1_r1_10_binding)
    normalized_r1_10_binding["freeze_binding_sha256"] = None
    if _canonical_sha(normalized_r1_10_binding) != m1_r1_10_binding.get("freeze_binding_sha256"):
        raise RuntimeError("R1.10 M1 amendment freeze-binding digest mismatch.")
    if _sha(m1_amendment_path) != m1_r1_10_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M1 amendment contract hash mismatch.")
    if _sha(m1_amendment_path) != m2_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M2/M3 contract SHA-256 mismatch.")
    if _binding_sha(m2_binding) != m2_binding.get("execution_binding_sha256"):
        raise RuntimeError("R1.10 M2/M3 execution-binding digest mismatch.")
    if amendment.get("status") != "FROZEN_R1_10_PROSPECTIVE_CONTACT_DIAGNOSTIC":
        raise RuntimeError("R1.10 M2/M3 contract is not frozen.")
    if m1_contract.get("artifact_id") != PARENT_ARTIFACT_ID or m1_final.get("status") != "M1_DIAGNOSTIC_PASS_M2_M3_READY":
        raise RuntimeError("R1.10 M1 evidence is not the expected passing parent.")
    if m2_final.get("artifact_id") != PARENT_ARTIFACT_ID:
        raise RuntimeError("R1.10 M2/M3 artifact identity mismatch.")
    if m2_final.get("status") != "M2_M3_DIAGNOSTIC_CASES_PASS_REFINEMENT_UNCLASSIFIED":
        raise RuntimeError("R1.10 M2/M3 evidence is not complete and passing.")
    if m1_final.get("contract_sha256") != m1_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M1 final record contract mismatch.")
    if m2_final.get("contract_sha256") != m2_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M2/M3 final record contract mismatch.")

    m1_manifest = _json(root / "source_file_manifest.json")
    m2_manifest = _json(root / "execution_source_manifest.json")
    source_digest = _canonical_sha(m1_manifest)
    if m1_manifest != m2_manifest:
        raise RuntimeError("R1.10 M1 and M2/M3 source manifests differ.")
    if source_digest != m1_binding.get("source_bundle_sha256") or source_digest != m2_binding.get("source_bundle_sha256"):
        raise RuntimeError("R1.10 parent source bundle digest mismatch.")
    if source_digest != m1_final.get("source_bundle_sha256") or source_digest != m2_final.get("source_bundle_sha256"):
        raise RuntimeError("R1.10 final record source bundle mismatch.")

    cases: dict[str, dict[str, Any]] = {}
    for mesh in ("M1", "M2", "M3"):
        for case in ("stick_target", "slip_target"):
            case_dir = root / "M1" / case if mesh == "M1" else root / "M2_M3" / mesh / case
            process_name = f"{case}.process.json" if mesh == "M1" else f"{mesh}_{case}.process.json"
            process_path = root / "_process_logs" / process_name
            progress_path, result_path = case_dir / "progress.json", case_dir / "result.json"
            raw_path, telemetry_path = case_dir / "raw.npz", case_dir / "telemetry.jsonl"
            paths = (progress_path, result_path, raw_path, telemetry_path, process_path)
            if not all(path.is_file() for path in paths):
                raise FileNotFoundError(f"Incomplete R1.10 parent evidence for {mesh}/{case}.")
            progress, result, process = _json(progress_path), _json(result_path), _json(process_path)
            expected_contract = m1_binding["contract_sha256"] if mesh == "M1" else m2_binding["contract_sha256"]
            if progress.get("status") != "PASS_DIAGNOSTIC_GATES" or result.get("diagnostic", {}).get("status") != "PASS_DIAGNOSTIC_GATES":
                raise RuntimeError(f"R1.10 {mesh}/{case} diagnostic gate did not pass.")
            if (
                result.get("artifact_id") != PARENT_ARTIFACT_ID
                or result.get("mesh", mesh) != mesh
                or result.get("case") != case
            ):
                raise RuntimeError(f"R1.10 {mesh}/{case} result identity mismatch.")
            if result.get("contract_sha256") != expected_contract or result.get("source_bundle_sha256") != source_digest:
                raise RuntimeError(f"R1.10 {mesh}/{case} result provenance mismatch.")
            if process.get("exit_code") != 0 or process.get("case") != case or process.get("mesh", mesh) != mesh:
                raise RuntimeError(f"R1.10 {mesh}/{case} process manifest mismatch.")
            for field, path in (("result_sha256", result_path), ("raw_sha256", raw_path), ("telemetry_sha256", telemetry_path)):
                if process.get(field) and process[field] != _sha(path):
                    raise RuntimeError(f"R1.10 {mesh}/{case} process {field} mismatch.")
            with np.load(raw_path, allow_pickle=False) as raw:
                required = {"node_coordinates", "body_node_count", "displacement", "contact_active",
                            "contact_normal_force", "contact_tangential_force_global"}
                missing = sorted(required.difference(raw.files))
                if missing:
                    raise RuntimeError(f"R1.10 {mesh}/{case} raw fields incomplete: {missing}")
                for name in required.difference({"body_node_count", "contact_active"}):
                    if not np.all(np.isfinite(np.asarray(raw[name], dtype=float))):
                        raise RuntimeError(f"R1.10 {mesh}/{case} raw field {name} is non-finite.")
            lines = telemetry_path.read_text(encoding="utf-8").splitlines()
            if not lines or any(not isinstance(json.loads(line), dict) for line in lines):
                raise RuntimeError(f"R1.10 {mesh}/{case} telemetry is empty or invalid JSONL.")
            cases[f"{mesh}/{case}"] = {
                "progress": {"path": progress_path.relative_to(ROOT).as_posix(), "sha256": _sha(progress_path)},
                "result": {"path": result_path.relative_to(ROOT).as_posix(), "sha256": _sha(result_path)},
                "raw_npz": {"path": raw_path.relative_to(ROOT).as_posix(), "sha256": _sha(raw_path)},
                "telemetry": {"path": telemetry_path.relative_to(ROOT).as_posix(), "sha256": _sha(telemetry_path)},
                "process_manifest": {"path": process_path.relative_to(ROOT).as_posix(), "sha256": _sha(process_path)},
            }

    current = _source_inventory()
    for relative, digest in m2_manifest.items():
        if current.get(relative) != digest:
            raise RuntimeError(f"R1.10 bound source changed before M4: {relative}")
    additions = set(current).difference(m2_manifest)
    expected_additions = {
        "scripts/run_wp08_area_supported_m4_diagnostic_r1_10.py",
        "tests/unit/test_wp08_area_supported_m4_r1_10_runner.py",
    }
    if additions != expected_additions or set(m2_manifest).difference(current):
        raise RuntimeError(f"Unexpected source inventory delta since R1.10 M2/M3: {sorted(additions)}")
    return {
        "m1_contract_path": m1_contract_path.relative_to(ROOT).as_posix(),
        "m1_contract_sha256": _sha(m1_contract_path),
        "m1_freeze_binding_path": m1_binding_path.relative_to(ROOT).as_posix(),
        "m1_freeze_binding_sha256": _sha(m1_binding_path),
        "m1_r1_10_freeze_binding_path": PARENT_BINDING_REL.as_posix(),
        "m1_r1_10_freeze_binding_sha256": _sha(m1_r1_10_binding_path),
        "m1_amendment_path": PARENT_CONTRACT_REL.as_posix(),
        "m1_amendment_sha256": _sha(m1_amendment_path),
        "m2_m3_execution_binding_path": PARENT_EXECUTION_BINDING_REL.as_posix(),
        "m2_m3_execution_binding_sha256": _sha(m2_binding_path),
        "m1_final_path": m1_final_path.relative_to(ROOT).as_posix(),
        "m1_final_sha256": _sha(m1_final_path),
        "m2_m3_final_path": PARENT_M2M3_FINAL_REL.as_posix(),
        "m2_m3_final_sha256": _sha(m2_final_path),
        "source_bundle_sha256": source_digest,
        "cases_read_only": cases,
    }

def _contract_payload(source_bundle_sha: str, parent: dict[str, Any]) -> dict[str, Any]:
    preflight = generate_preflight(M4_LEVEL)
    return {
        "schema": "qf.wp08.area_supported_contact_m4_diagnostic_contract.r2",
        "artifact_id": ARTIFACT_ID,
        "status": "FROZEN_PROSPECTIVE_EXPERIMENTAL_M4_ONLY",
        "frozen_utc": _utc(),
        "contract_document": DOC_REL.as_posix(),
        "contract_document_sha256": _sha(ROOT / DOC_REL),
        "execution": {
            "output_root": OUTPUT_REL.as_posix(),
            "attempts": 1,
            "overwrite_or_retry": False,
            "sequence": ["M4/stick_target", "M4/slip_target_if_stick_passes"],
            "one_solver_process_at_a_time": True,
            "stop_after_any_failed_gate": True,
        },
        "mesh": {
            "name": "M4",
            "parent_cells": {"nx": 16, "ny": 8, "nz": 8},
            "element_type": "TET4",
            "tet4_elements": preflight["element_count"],
            "body_nodes": preflight["body_node_count"],
            "body_dofs": preflight["body_dofs"],
            "total_nodes_including_master": preflight["node_count"],
            "total_dofs_including_master_metadata": preflight["total_dofs_including_rigid_master_metadata"],
            "contact_slave_nodes": preflight["contact_slave_node_count"],
            "contact_faces_t3": preflight["contact_face_count"],
            "preflight": {
                key: preflight[key]
                for key in ("contact_support_affine_rank", "all_slave_nodes_project_inside_master_patch",
                            "contact_patch_area_m2", "integrated_tangential_stiffness_N_per_m",
                            "minimum_tet_volume_m3", "total_volume_m3")
            },
        },
        "benchmark": {
            "parent_campaign_artifact_id": "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.10",
            "geometry_m": {"length_x": LENGTH_M, "width_y": WIDTH_M, "height_z": HEIGHT_M},
            "material": {"type": "linear_isotropic_elastic", "young_modulus_Pa": 1.0e6, "poisson_ratio": POISSON_RATIO},
            "fixed_face": "x=0, all body UX/UY/UZ",
            "slave_patch": "complete body boundary face x=2",
            "master": {"plane_x_m": LENGTH_M + INITIAL_GAP_M, "normal": [-1.0, 0.0, 0.0]},
            "normal_contact": "existing fixed initial-search node-to-triangle",
            "friction_coefficient": FRICTION_COEFFICIENT,
            "tangential_stiffness_mode": "surface",
            "tangential_stiffness_density_N_per_m3": TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
            "area_redistribution": False,
            "load_resultants_N": {
                "normal": [NORMAL_RESULTANT_N, 0.0, 0.0],
                "stick_target": [0.0, STICK_TANGENTIAL_RESULTANT_N, 0.0],
                "slip_target": [0.0, SLIP_TANGENTIAL_RESULTANT_N, 0.0],
            },
            "load_steps": 8,
            "parent_m1_m2_m3_reused_read_only": True,
        },
        "diagnostic_gates": {
            "all_serialized_observables_finite": True,
            "solver_converged": True,
            "accepted_load_steps": 8,
            "active_support_affine_rank": 2,
            "terminal_state": {"stick_target": "stick", "slip_target": "slip"},
            "mesh_refinement_threshold": None,
        },
        "comparison": {
            "M3_to_M4": "descriptive_only; no frozen mesh threshold; not PASS/FAIL",
            "metrics": ["common-node displacement", "normal contact resultant",
                        "tangential contact resultant", "active area fraction"],
        },
        "limitations": {
            "formal_wp08_qualification": False,
            "points_awarded": False,
            "independent_global_fem_reference": False,
            "external_solver_correlation": False,
            "formal_replay": False,
            "fallback_count_claim": False,
            "interpretation": "experimental M4 refinement diagnostic only",
        },
        "policy_context_only": {"digest": POLICY_DIGEST_CONTEXT, "governing_policy_enforced": False},
        "parent_provenance": parent,
        "source_bundle_sha256": source_bundle_sha,
        "owner_authorization": {
            "execution_authorized": True,
            "recorded_from": "Owner instruction: freeze the runner and launch execution; explicit green light.",
            "scope": "One serial R1.10-bound M4 stick/slip diagnostic at 16x8x8 only; no parameter tuning, no retries, no formal qualification, no score award.",
        },
    }

def freeze() -> dict[str, Any]:
    output = ROOT / OUTPUT_REL
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing M4 output root: {output}")
    parent = _parent_evidence()
    inventory = _source_inventory()
    source_digest = _canonical_sha(inventory)
    doc_path = ROOT / DOC_REL
    if not doc_path.is_file():
        raise FileNotFoundError(f"Frozen R1.10 M4 contract document is missing: {doc_path}")
    output.mkdir(parents=True, exist_ok=False)
    contract = _contract_payload(source_digest, parent)
    _write_json(output / "contract.json", contract)
    _write_json(output / "source_manifest.json", inventory)
    contract_sha = _sha(output / "contract.json")
    binding: dict[str, Any] = {
        "schema": "qf.wp08.area_supported_contact_m4_execution_binding.v1",
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": _utc(),
        "contract_path": OUTPUT_REL.joinpath("contract.json").as_posix(),
        "contract_sha256": contract_sha,
        "runner_path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "runner_sha256": _sha(Path(__file__).resolve()),
        "source_manifest_path": OUTPUT_REL.joinpath("source_manifest.json").as_posix(),
        "source_file_count": len(inventory),
        "source_bundle_sha256": source_digest,
        "git": _git_state(),
        "runtime": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
        },
        "owner_authorization": {"authorized": True, **contract["owner_authorization"], "recorded_utc": _utc()},
        "execution_order": ["M4/stick_target", "M4/slip_target_if_stick_passes"],
        "execution_binding_sha256": None,
    }
    binding["execution_binding_sha256"] = _binding_sha(binding)
    _write_json(output / "execution_binding.json", binding)
    freeze_record = {
        "status": "FROZEN_READY_TO_EXECUTE",
        "frozen_utc": binding["frozen_utc"],
        "contract_sha256": contract_sha,
        "runner_sha256": binding["runner_sha256"],
        "source_bundle_sha256": source_digest,
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "parent_m1_m2_m3_reverified_read_only": True,
        "owner_authorization": binding["owner_authorization"],
    }
    _write_json(output / "freeze_record.json", freeze_record)
    return freeze_record


def _verify_frozen(output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if output.resolve() != (ROOT / OUTPUT_REL).resolve():
        raise PermissionError("M4 output root differs from its frozen dedicated path.")
    contract = _json(output / "contract.json")
    binding = _json(output / "execution_binding.json")
    manifest = _json(output / "source_manifest.json")
    if contract.get("status") != "FROZEN_PROSPECTIVE_EXPERIMENTAL_M4_ONLY":
        raise RuntimeError("M4 contract is not frozen for prospective execution.")
    if _sha(output / "contract.json") != binding.get("contract_sha256"):
        raise RuntimeError("M4 contract digest differs from the frozen execution binding.")
    if binding.get("execution_binding_sha256") != _binding_sha(binding):
        raise RuntimeError("M4 execution-binding digest mismatch.")
    if manifest != _source_inventory() or _canonical_sha(manifest) != binding.get("source_bundle_sha256"):
        raise RuntimeError("Source/runner/test inventory changed after freeze.")
    if contract.get("source_bundle_sha256") != binding.get("source_bundle_sha256"):
        raise RuntimeError("Contract and execution binding disagree on source bundle.")
    if _sha(ROOT / DOC_REL) != contract.get("contract_document_sha256"):
        raise RuntimeError("M4 contract document changed after freeze.")
    if binding.get("owner_authorization", {}).get("authorized") is not True:
        raise PermissionError("M4 execution is not Owner-authorized in the frozen binding.")
    if _sha(Path(__file__).resolve()) != binding.get("runner_sha256"):
        raise RuntimeError("M4 runner source changed after freeze.")
    _parent_evidence()
    return contract, binding


def _build_model(case: str) -> tuple[Any, np.ndarray, tuple[int, ...], dict[int, float]]:
    if case not in {"stick_target", "slip_target"}:
        raise ValueError(f"Unsupported M4 case: {case}")
    from solveur.contact.measures import reference_surface_areas
    from solveur.core.model import FiniteElementModel

    body, tets, slave_faces, slave_nodes, fixed_nodes = _surface_geometry(M4_LEVEL)
    body_count = len(body)
    master = np.asarray(
        [
            [LENGTH_M + INITIAL_GAP_M, 0.0, 0.0],
            [LENGTH_M + INITIAL_GAP_M, 0.0, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, HEIGHT_M],
            [LENGTH_M + INITIAL_GAP_M, WIDTH_M, 0.0],
        ],
        dtype=float,
    )
    nodes = np.vstack((body, master))
    master_ids = tuple(range(body_count, body_count + 4))
    master_faces = (
        (master_ids[0], master_ids[1], master_ids[2]),
        (master_ids[0], master_ids[2], master_ids[3]),
    )
    area_by_node = reference_surface_areas(nodes, slave_faces)
    patch_area = float(sum(area_by_node.values()))
    tangent = STICK_TANGENTIAL_RESULTANT_N if case == "stick_target" else SLIP_TANGENTIAL_RESULTANT_N
    loads: list[dict[str, Any]] = []
    load_kinds: list[str] = []
    for node in slave_nodes:
        share = area_by_node[node] / patch_area
        loads.extend(
            (
                {"node": node, "dof": "UX", "value": NORMAL_RESULTANT_N * share},
                {"node": node, "dof": "UY", "value": tangent * share},
            )
        )
        load_kinds.extend(("normal", "tangential"))
    load_steps = (
        {"normal_factor": 0.25, "tangential_factor": 0.0},
        {"normal_factor": 0.50, "tangential_factor": 0.0},
        {"normal_factor": 0.75, "tangential_factor": 0.0},
        {"normal_factor": 1.00, "tangential_factor": 0.0},
        {"normal_factor": 1.00, "tangential_factor": 0.25},
        {"normal_factor": 1.00, "tangential_factor": 0.50},
        {"normal_factor": 1.00, "tangential_factor": 0.75},
        {"normal_factor": 1.00, "tangential_factor": 1.00},
    )
    history = [
        [float(step["normal_factor"] if kind == "normal" else step["tangential_factor"]) for kind in load_kinds]
        for step in load_steps
    ]
    elements = [{"type": "TET4", "nodes": list(tet), "material": "elastic"} for tet in tets]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=elements,
        materials={"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": POISSON_RATIO}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (*fixed_nodes, *master_ids)],
        loads=loads,
        contacts=[
            {
                "name": "wp08_area_supported_fixed_search",
                "slave_nodes": list(slave_nodes),
                "slave_patch_faces": [list(face) for face in slave_faces],
                "master_nodes": list(master_faces[0]),
                "master_faces": [list(face) for face in master_faces],
                "friction_coefficient": FRICTION_COEFFICIENT,
                "tangential_stiffness_mode": "surface",
                "tangential_stiffness": TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
                "gap_tolerance": 1.0e-10,
            }
        ],
        analysis={
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 25,
            "contact_friction_tolerance": 1.0e-9,
            "contact_load_history": history,
            "contact_search_mode": "initial",
            "contact_emit_step_checkpoints": True,
        },
    )
    return model, body, slave_nodes, area_by_node


def _finite(value: Any) -> bool:
    if isinstance(value, (float, np.floating, int, np.integer)):
        return bool(np.isfinite(value))
    if isinstance(value, np.ndarray):
        return bool(np.all(np.isfinite(value)))
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(item) for item in value)
    return True


def _case_gates(payload: dict[str, Any], case: str, body: np.ndarray, slave_nodes: tuple[int, ...], area_by_node: dict[int, float]) -> dict[str, Any]:
    solver = payload.get("solver", {})
    contact = solver.get("contact", {})
    rows = contact.get("contacts", [])
    active = [row for row in rows if bool(row.get("active", False))]
    active_nodes = sorted({int(row["slave_node"]) for row in active if "slave_node" in row})
    points = body[active_nodes] if active_nodes else np.empty((0, 3))
    rank = int(np.linalg.matrix_rank(points - np.mean(points, axis=0))) if len(active_nodes) >= 2 else 0
    terminal = sorted({str(row.get("tangential_state", "unknown")) for row in active})
    expected = "stick" if case == "stick_target" else "slip"
    steps = contact.get("load_steps", [])
    gates = {
        "serialized_observables_finite": _finite(payload),
        "solver_converged": bool(solver.get("converged", False)),
        "eight_load_steps_recorded": len(steps) == 8,
        "active_support_affine_rank_2": rank == 2,
        "expected_terminal_tangential_state": terminal == [expected],
    }
    active_area = float(sum(area_by_node.get(node, 0.0) for node in active_nodes))
    total_area = float(sum(area_by_node.values()))
    return {
        "status": "PASS_DIAGNOSTIC_GATES" if all(gates.values()) else "FAIL_CLOSED_DIAGNOSTIC_GATE",
        "mesh": "M4",
        "case": case,
        "gates": gates,
        "solver_converged": bool(solver.get("converged", False)),
        "load_step_count": len(steps),
        "active_slave_nodes": active_nodes,
        "active_slave_node_count": len(active_nodes),
        "slave_node_count": len(slave_nodes),
        "active_support_affine_rank": rank,
        "active_area_m2": active_area,
        "nominal_patch_area_m2": total_area,
        "active_area_fraction": active_area / total_area if total_area else 0.0,
        "terminal_active_states": terminal,
        "expected_terminal_state": expected,
        "fallback_count": None,
        "fallback_count_note": "Not exposed by the result schema; no zero-fallback claim.",
    }


def _worker(output: Path, case: str, binding_sha: str) -> int:
    output = output.resolve()
    contract, binding = _verify_frozen(output)
    if binding.get("execution_binding_sha256") != binding_sha:
        raise RuntimeError("Worker was invoked with a different execution binding.")
    case_dir = output / "M4" / case
    case_dir.mkdir(parents=True, exist_ok=False)
    from solveur.api.public import solve_model
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter

    model, body, slave_nodes, area_by_node = _build_model(case)
    sink = JsonlSink(case_dir / "telemetry.jsonl", fsync=True, sink_identifier="wp08_area_r1_10_m4")
    telemetry = TelemetryEmitter(
        analysis_id=f"{ARTIFACT_ID}-M4-{case}",
        analysis_type="linear_static",
        route="linear_static",
        sinks=(sink,),
        metadata={
            "contract_sha256": binding["contract_sha256"],
            "execution_binding_sha256": binding_sha,
            "source_bundle_sha256": binding["source_bundle_sha256"],
            "mesh": "M4",
            "case": case,
        },
    )
    started = perf_counter()
    try:
        result = solve_model(model, enforce_policy=False, telemetry=telemetry)
        elapsed = perf_counter() - started
        payload = result.to_dict()
        diagnostic = _case_gates(payload, case, body, slave_nodes, area_by_node)
        payload.update(
            {
                "artifact_id": ARTIFACT_ID,
                "execution_kind": "EXPERIMENTAL_R1_10_M4_REFINEMENT_DIAGNOSTIC",
                "mesh": "M4",
                "case": case,
                "formal_wp08_qualification": False,
                "points_awarded": False,
                "contract_sha256": binding["contract_sha256"],
                "execution_binding_sha256": binding_sha,
                "source_bundle_sha256": binding["source_bundle_sha256"],
                "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
                "diagnostic": {**diagnostic, "elapsed_seconds": elapsed},
            }
        )
        _write_json(case_dir / "result.json", payload)
        body_count = len(body)
        all_coordinates = np.vstack(
            (
                body,
                np.asarray(
                    [
                        [LENGTH_M + INITIAL_GAP_M, 0.0, 0.0],
                        [LENGTH_M + INITIAL_GAP_M, 0.0, HEIGHT_M],
                        [LENGTH_M + INITIAL_GAP_M, WIDTH_M, HEIGHT_M],
                        [LENGTH_M + INITIAL_GAP_M, WIDTH_M, 0.0],
                    ],
                    dtype=float,
                ),
            )
        )
        eq = payload.get("audit", {}).get("equilibrium", {})
        contact_rows = payload.get("solver", {}).get("contact", {}).get("contacts", [])
        normals = np.asarray([row.get("normal", [0.0, 0.0, 0.0]) for row in contact_rows], dtype=float).reshape((-1, 3))
        pressure = np.asarray([row.get("pressure", 0.0) for row in contact_rows], dtype=float)
        normal_force = -pressure[:, None] * normals
        tangent_global = []
        for row in contact_rows:
            components = np.asarray(row.get("tangential_force", [0.0, 0.0]), dtype=float)
            tangent_global.append(
                components[0] * np.asarray(row.get("tangent_one", [0.0, 0.0, 0.0]), dtype=float)
                + components[1] * np.asarray(row.get("tangent_two", [0.0, 0.0, 0.0]), dtype=float)
            )
        tangent_global_array = np.asarray(tangent_global, dtype=float).reshape((-1, 3))
        areas = np.asarray([area_by_node[node] for node in slave_nodes], dtype=float)
        np.savez_compressed(
            case_dir / "raw.npz",
            displacement=np.asarray(result.displacements, dtype=float),
            node_coordinates=all_coordinates,
            body_node_count=np.asarray([body_count], dtype=np.int64),
            slave_nodes=np.asarray(slave_nodes, dtype=np.int64),
            reference_slave_area=areas,
            contact_slave_nodes=np.asarray([row.get("slave_node", -1) for row in contact_rows], dtype=np.int64),
            contact_active=np.asarray([row.get("active", False) for row in contact_rows], dtype=bool),
            contact_pressure=pressure,
            contact_normal=normals,
            contact_normal_force=normal_force,
            contact_gap=np.asarray([row.get("gap", np.nan) for row in contact_rows], dtype=float),
            contact_states=np.asarray([row.get("tangential_state", "unknown") for row in contact_rows], dtype=str),
            contact_tangential_force_global=tangent_global_array,
            contact_reference_area=np.asarray([row.get("reference_slave_area", 0.0) for row in contact_rows], dtype=float),
            reaction_resultant=np.asarray(eq.get("reaction_resultant", [0.0, 0.0, 0.0]), dtype=float),
            reaction_moment=np.asarray(eq.get("reaction_moment_about_origin", [0.0, 0.0, 0.0]), dtype=float),
            force_balance_relative_error=np.asarray([eq.get("force_balance_relative_error", np.nan)], dtype=float),
            moment_balance_relative_error=np.asarray([eq.get("moment_balance_relative_error", np.nan)], dtype=float),
            active_slave_nodes=np.asarray(diagnostic["active_slave_nodes"], dtype=np.int64),
        )
        _write_json(case_dir / "progress.json", {"status": diagnostic["status"], **diagnostic})
        return 0 if all(diagnostic["gates"].values()) else 3
    except BaseException as error:
        _write_json(
            case_dir / "failure.json",
            {
                "artifact_id": ARTIFACT_ID,
                "mesh": "M4",
                "case": case,
                "contract_sha256": binding["contract_sha256"],
                "execution_binding_sha256": binding_sha,
                "error_type": type(error).__name__,
                "error": str(error),
                "failed_utc": _utc(),
            },
        )
        raise
    finally:
        telemetry.close()


def _relative_delta(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    absolute = float(np.linalg.norm(b - a))
    denom = max(float(np.linalg.norm(a)), float(np.linalg.norm(b)))
    return {"absolute_l2": absolute, "relative_l2": absolute / denom if denom else 0.0}


def _m3_m4_comparison(m3_raw_path: Path, m4_raw_path: Path) -> dict[str, Any]:
    with np.load(m3_raw_path, allow_pickle=False) as m3, np.load(m4_raw_path, allow_pickle=False) as m4:
        x3 = np.asarray(m3["node_coordinates"][: int(m3["body_node_count"][0])], dtype=float)
        x4 = np.asarray(m4["node_coordinates"][: int(m4["body_node_count"][0])], dtype=float)
        u3 = np.asarray(m3["displacement"], dtype=float).reshape((-1, 3))[: len(x3)]
        u4 = np.asarray(m4["displacement"], dtype=float).reshape((-1, 3))[: len(x4)]
        map4 = {tuple(np.round(point, 14)): idx for idx, point in enumerate(x4)}
        pairs = [(idx, map4[tuple(np.round(point, 14))]) for idx, point in enumerate(x3) if tuple(np.round(point, 14)) in map4]
        if not pairs:
            raise RuntimeError("M3/M4 comparison found no common body nodes.")
        i3 = np.asarray([pair[0] for pair in pairs], dtype=int)
        i4 = np.asarray([pair[1] for pair in pairs], dtype=int)
        u_delta = _relative_delta(u3[i3], u4[i4])
        n3 = np.sum(np.asarray(m3["contact_normal_force"], dtype=float), axis=0)
        n4 = np.sum(np.asarray(m4["contact_normal_force"], dtype=float), axis=0)
        t3 = np.sum(np.asarray(m3["contact_tangential_force_global"], dtype=float), axis=0)
        t4 = np.sum(np.asarray(m4["contact_tangential_force_global"], dtype=float), axis=0)
        active3 = np.asarray(m3["contact_active"], dtype=bool)
        active4 = np.asarray(m4["contact_active"], dtype=bool)
        areas3 = np.asarray(m3["contact_reference_area"], dtype=float)
        areas4 = np.asarray(m4["contact_reference_area"], dtype=float)
        active_area3 = float(np.sum(areas3[active3]))
        active_area4 = float(np.sum(areas4[active4]))
        patch_area3 = float(np.sum(areas3))
        patch_area4 = float(np.sum(areas4))
    return {
        "classification": "DESCRIPTIVE_ONLY_NO_FROZEN_MESH_THRESHOLD",
        "common_body_node_count": len(pairs),
        "common_node_displacement": u_delta,
        "normal_contact_resultant": _relative_delta(n3, n4),
        "tangential_contact_resultant": _relative_delta(t3, t4),
        "active_area_fraction": {
            "M3": active_area3 / patch_area3 if patch_area3 else 0.0,
            "M4": active_area4 / patch_area4 if patch_area4 else 0.0,
        },
    }


def _invoke(output: Path, case: str, binding: dict[str, Any]) -> dict[str, Any]:
    logs = output / "_process_logs"
    logs.mkdir(exist_ok=True)
    tag = f"M4_{case}"
    stdout_path = logs / f"{tag}.stdout.log"
    stderr_path = logs / f"{tag}.stderr.log"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--worker",
        "--output-root",
        str(output),
        "--case",
        case,
        "--execution-binding-sha256",
        str(binding["execution_binding_sha256"]),
    ]
    start = _utc()
    t0 = perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        exit_code = process.wait()
    record: dict[str, Any] = {
        "mesh": "M4",
        "case": case,
        "execution_kind": "EXPERIMENTAL_M4_REFINEMENT_DIAGNOSTIC",
        "pid": process.pid,
        "command": command,
        "started_utc": start,
        "ended_utc": _utc(),
        "elapsed_seconds": perf_counter() - t0,
        "exit_code": exit_code,
        "contract_sha256": binding["contract_sha256"],
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "stdout_path": stdout_path.relative_to(output).as_posix(),
        "stdout_sha256": _sha(stdout_path),
        "stderr_path": stderr_path.relative_to(output).as_posix(),
        "stderr_sha256": _sha(stderr_path),
    }
    case_dir = output / "M4" / case
    for filename, key in (("result.json", "result"), ("raw.npz", "raw"), ("telemetry.jsonl", "telemetry"), ("failure.json", "failure")):
        path = case_dir / filename
        if path.is_file():
            record[f"{key}_path"] = path.relative_to(output).as_posix()
            record[f"{key}_sha256"] = _sha(path)
    _write_json(logs / f"{tag}.process.json", record)
    return record


def execute() -> int:
    output = ROOT / OUTPUT_REL
    contract, binding = _verify_frozen(output)
    run_root = output / "M4"
    if run_root.exists():
        raise FileExistsError("M4 execution directory exists; refusing retry or overwrite.")
    run_root.mkdir(parents=True, exist_ok=False)
    _write_json(run_root / "progress.json", {"status": "RUNNING", "started_utc": _utc(), "cases": {}}, exclusive=False)
    process_records: list[dict[str, Any]] = []
    statuses: dict[str, str] = {}
    for case in ("stick_target", "slip_target"):
        if case == "slip_target" and statuses.get("stick_target") != "PASS_DIAGNOSTIC_GATES":
            statuses[case] = "NOT_RUN_PREVIOUS_CASE_FAILED"
            break
        record = _invoke(output, case, binding)
        process_records.append(record)
        result_path = output / "M4" / case / "result.json"
        if record["exit_code"] == 0 and result_path.is_file():
            statuses[case] = str(_json(result_path).get("diagnostic", {}).get("status", "UNKNOWN"))
        else:
            statuses[case] = "FAIL_CLOSED_PROCESS_OR_RESULT"
        _write_json(
            run_root / "progress.json",
            {"status": "RUNNING", "started_utc": _json(run_root / "progress.json")["started_utc"], "updated_utc": _utc(), "cases": statuses, "processes": process_records},
            exclusive=False,
        )
        if statuses[case] != "PASS_DIAGNOSTIC_GATES":
            break

    comparisons: dict[str, Any] = {}
    if all(statuses.get(case) == "PASS_DIAGNOSTIC_GATES" for case in ("stick_target", "slip_target")):
        parent_root = ROOT / M1_ROOT_REL
        for case in ("stick_target", "slip_target"):
            comparisons[case] = _m3_m4_comparison(
                parent_root / "M2_M3" / "M3" / case / "raw.npz",
                run_root / case / "raw.npz",
            )
    all_pass = all(statuses.get(case) == "PASS_DIAGNOSTIC_GATES" for case in ("stick_target", "slip_target"))
    final = {
        "artifact_id": ARTIFACT_ID,
        "status": "M4_DIAGNOSTIC_CASES_PASS_REFINEMENT_OBSERVED" if all_pass else "M4_DIAGNOSTIC_INCOMPLETE_OR_FAIL_CLOSED",
        "contract_sha256": binding["contract_sha256"],
        "execution_binding_sha256": binding["execution_binding_sha256"],
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "source_head": binding["git"]["head"],
        "parent_m1_m2_m3_reused_read_only": True,
        "case_status": statuses,
        "processes": process_records,
        "m3_to_m4_refinement_diagnostics": comparisons,
        "mesh_convergence_status": "NOT_CLASSIFIED_NO_FROZEN_THRESHOLD",
        "formal_wp08_qualification": False,
        "points_awarded": False,
        "independent_global_fem_reference_run": False,
        "formal_replay_run": False,
        "production_mechanics_changed_in_m4_runner": False,
        "thresholds_changed": False,
        "full_test_suite_run": False,
    }
    _write_json(run_root / "final.json", final)
    _write_json(run_root / "progress.json", {"status": "COMPLETED", "completed_utc": _utc(), **final}, exclusive=False)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if all_pass else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT / OUTPUT_REL)
    parser.add_argument("--case", choices=("stick_target", "slip_target"))
    parser.add_argument("--execution-binding-sha256")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        return execute()
    if args.worker and args.case and args.execution_binding_sha256:
        output = args.output_root.resolve()
        _, binding = _verify_frozen(output)
        if binding["execution_binding_sha256"] != args.execution_binding_sha256:
            raise RuntimeError("Worker execution binding argument mismatch.")
        return _worker(output, args.case, args.execution_binding_sha256)
    parser.error("Choose --freeze, --execute, or a complete --worker invocation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
