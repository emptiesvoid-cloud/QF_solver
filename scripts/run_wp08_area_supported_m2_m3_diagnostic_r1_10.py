"""Freeze and run the prospective WP08 area-supported R1.10 M2/M3 campaign.

This runner reuses the immutable M1 evidence, runs M2 then M3 sequentially,
and never claims formal WP08 credit or a mesh-convergence PASS/FAIL.
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
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
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
    MESH_LEVELS,
    NORMAL_RESULTANT_N,
    POISSON_RATIO,
    SLIP_TANGENTIAL_RESULTANT_N,
    STICK_TANGENTIAL_RESULTANT_N,
    TANGENTIAL_STIFFNESS_DENSITY_N_PER_M3,
    WIDTH_M,
    MeshLevel,
    _surface_geometry,
)

CAMPAIGN_REVISION = os.environ.get("QF_WP08_CAMPAIGN_REVISION", "R1.10")
ARTIFACT_ID = os.environ.get(
    "QF_WP08_ARTIFACT_ID", "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.10"
)
POLICY_DIGEST_CONTEXT = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
M1_OUTPUT_ROOT_REL = Path(
    os.environ.get(
        "QF_WP08_M1_OUTPUT_ROOT_REL",
        "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926",
    )
)
CONTRACT_REL = Path(
    os.environ.get(
        "QF_WP08_M2M3_CONTRACT_REL",
        "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926/contract_r1_10_contact_requalification.json",
    )
)
FREEZE_BINDING_REL = Path(
    os.environ.get(
        "QF_WP08_M2M3_BINDING_REL",
        "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_20260926/freeze_binding_r1_10_contact_requalification.json",
    )
)
M1_CONTRACT_DOCUMENT_REL = Path(
    os.environ.get(
        "QF_WP08_CONTRACT_DOCUMENT_REL",
        "docs/verification/0_2_9/wp08-area-supported-contact-requalification-r1-10.md",
    )
)
R1_9_EXPECTED_FILE_HASHES = {
    "contract.json": "54e034808586c71ee58616edbd395ab933450989865d0d35d21a63f2efe85962",
    "contract_r1_9_contact_requalification.json": "c6d24175d521f52ee14f985f373eef57b196771fa6e7f9366e92d56e6980a210",
    "execution_binding.json": "46a02d25a5dcdfa8e0388bad0ca26c9c037608f343f8471a5b8fb1fa99900df8",
    "freeze_binding.json": "21cb741a35736f3a364bbb6245ea3daada7bd58c516952e4fb430659cbc78316",
    "freeze_binding_r1_9_contact_requalification.json": "7f57bb09bfb6b9570e109512d5a00e60fa8a6887e2b896572a441748a9fe81f4",
    "final.json": "d077a53d7782335d2aafe84bba26500d4779992c436b5bcc3b7e04c37d8182f9",
    "source_file_manifest.json": "e677f8145c44a9704210b95281aea3d286aa553dac981be95be1a0caa0e1d94c",
    "M1/stick_target/result.json": "ca55dc35f33067b71a8930d27e50cf604f5d0d069d59d2fce2603989d7d16e98",
    "M1/slip_target/result.json": "e64d257a0f80d05cec45c9c3d7800b163ee7db6350089f438e6c6da3342a99d9",
    "M2_M3/final.json": "34e5258db7dce78fe11de4d9e11fc585a68e7db2f80b3f2385e40ef4bf656974",
    "M2_M3/M3/slip_target/failure.json": "ce824e409e4dc27722e122173c1aff17666d745bc3425f51173e7bd0561f5ffe",
    "M2_M3/M3/slip_target/telemetry.jsonl": "b97a03cf5c26629a846f6b034f3fbd1f71a617d00ea71f8216539fd3b53d6fcf",
}
M1_LOAD_STEPS = [
    {"normal_factor": 0.25, "tangential_factor": 0.0},
    {"normal_factor": 0.50, "tangential_factor": 0.0},
    {"normal_factor": 0.75, "tangential_factor": 0.0},
    {"normal_factor": 1.00, "tangential_factor": 0.0},
    {"normal_factor": 1.00, "tangential_factor": 0.25},
    {"normal_factor": 1.00, "tangential_factor": 0.50},
    {"normal_factor": 1.00, "tangential_factor": 0.75},
    {"normal_factor": 1.00, "tangential_factor": 1.00},
]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _binding_digest(binding: Mapping[str, Any]) -> str:
    normalized = dict(binding)
    normalized["execution_binding_sha256"] = None
    return _canonical_sha(normalized)


def _manifest_preserved_files(root: Path, paths: tuple[Path, ...]) -> list[dict[str, Any]]:
    """Hash immutable historical files without changing their bytes."""
    records: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Historical evidence is missing: {path}")
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def prepare_r1_10_amendment(
    output: Path,
    *,
    historical_r1_9_root: Path | None = None,
    owner_authorized: bool = False,
) -> dict[str, Any]:
    """Freeze the M2/M3 amendment against the completed, immutable R1.10 M1 run."""
    output = output.resolve()
    if not owner_authorized:
        raise PermissionError("Preparing R1.10 M2/M3 requires explicit Owner authorization.")
    if historical_r1_9_root is None:
        raise ValueError("The immutable R1.9 evidence root must be supplied explicitly.")
    parent_contract_path = output / "contract.json"
    parent_binding_path = output / "freeze_binding.json"
    m1_final_path = output / "final.json"
    for path in (parent_contract_path, parent_binding_path, m1_final_path):
        if not path.is_file():
            raise FileNotFoundError(f"R1.10 M1 freeze/evidence prerequisite is missing: {path}")

    parent_contract = json.loads(parent_contract_path.read_text(encoding="utf-8"))
    parent_binding = json.loads(parent_binding_path.read_text(encoding="utf-8"))
    m1_final = json.loads(m1_final_path.read_text(encoding="utf-8"))
    if parent_contract.get("artifact_id") != ARTIFACT_ID:
        raise RuntimeError("M1 parent contract is not the R1.10 contact campaign contract.")
    if (
        parent_contract.get("owner_authorization", {}).get("execution_authorized") is not True
        or parent_contract.get("m2_m3_authorized") is not True
    ):
        raise PermissionError("The frozen M1 contract does not authorize R1.10 structural execution.")
    if _sha(parent_contract_path) != parent_binding.get("contract_sha256"):
        raise RuntimeError("R1.10 M1 contract hash differs from its freeze binding.")
    if m1_final.get("status") != "M1_DIAGNOSTIC_PASS_M2_M3_READY":
        raise RuntimeError("M1 gates failed; M2/M3 amendment must not be prepared.")
    if m1_final.get("contract_sha256") != parent_binding.get("contract_sha256"):
        raise RuntimeError("M1 final evidence is not bound to the frozen R1.10 contract.")

    source_manifest_path = output / str(parent_binding.get("source_manifest_path", "source_file_manifest.json"))
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_digest = _canonical_sha(source_manifest)
    if source_digest != parent_binding.get("source_bundle_sha256"):
        raise RuntimeError("R1.10 M1 source manifest digest mismatch.")
    if source_manifest != _source_inventory() or source_digest != m1_final.get("source_bundle_sha256"):
        raise RuntimeError("Current source tree differs from the source used by R1.10 M1.")

    m1_cases: dict[str, dict[str, str]] = {}
    for case in ("stick_target", "slip_target"):
        case_dir = output / "M1" / case
        progress_path = case_dir / "progress.json"
        process_path = output / "_process_logs" / f"{case}.process.json"
        result_path = case_dir / "result.json"
        raw_path = case_dir / "raw.npz"
        telemetry_path = case_dir / "telemetry.jsonl"
        for path in (progress_path, process_path, result_path, raw_path, telemetry_path):
            if not path.is_file():
                raise FileNotFoundError(f"R1.10 M1 case evidence is incomplete: {path}")
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        process = json.loads(process_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if progress.get("status") != "PASS_DIAGNOSTIC_GATES" or process.get("exit_code") != 0:
            raise RuntimeError(f"R1.10 M1 case did not pass its process and diagnostic gates: {case}")
        if result.get("contract_sha256") != parent_binding["contract_sha256"]:
            raise RuntimeError(f"R1.10 M1 case contract provenance mismatch: {case}")
        with np.load(raw_path, allow_pickle=False) as raw:
            expected = {
                "node_coordinates",
                "body_node_count",
                "displacement",
                "contact_normal_force",
                "contact_tangential_force_global",
            }
            missing = sorted(expected.difference(raw.files))
            if missing:
                raise RuntimeError(f"R1.10 M1 raw evidence lacks required refinement arrays: {case}: {missing}")
        m1_cases[case] = {
            "result_sha256": _sha(result_path),
            "raw_npz_sha256": _sha(raw_path),
            "telemetry_sha256": _sha(telemetry_path),
            "progress_sha256": _sha(progress_path),
            "process_manifest_sha256": _sha(process_path),
        }

    historical_r1_9_root = historical_r1_9_root.resolve()
    if not historical_r1_9_root.is_dir():
        raise FileNotFoundError(f"Immutable R1.9 evidence directory is missing: {historical_r1_9_root}")
    historical_paths = tuple(
        historical_r1_9_root / Path(relative) for relative in R1_9_EXPECTED_FILE_HASHES
    )
    historical_records = _manifest_preserved_files(historical_r1_9_root, historical_paths)
    historical_hashes = {record["path"]: record["sha256"] for record in historical_records}
    for relative, expected_sha in R1_9_EXPECTED_FILE_HASHES.items():
        if historical_hashes.get(relative) != expected_sha:
            raise RuntimeError(f"Immutable R1.9 evidence hash mismatch: {relative}")
    historical_contract = json.loads((historical_r1_9_root / "contract.json").read_text(encoding="utf-8"))
    historical_final = json.loads((historical_r1_9_root / "final.json").read_text(encoding="utf-8"))
    historical_m2_m3 = json.loads((historical_r1_9_root / "M2_M3/final.json").read_text(encoding="utf-8"))
    historical_failure = json.loads(
        (historical_r1_9_root / "M2_M3/M3/slip_target/failure.json").read_text(encoding="utf-8")
    )
    if historical_contract.get("artifact_id") != "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.9":
        raise RuntimeError("Historical directory does not contain the expected R1.9 contract.")
    if historical_final.get("cases") != {
        "slip_target": "PASS_DIAGNOSTIC_GATES",
        "stick_target": "PASS_DIAGNOSTIC_GATES",
    }:
        raise RuntimeError("Historical R1.9 M1 classifications differ from the preserved campaign record.")
    if historical_m2_m3.get("case_status") != {
        "M2/slip_target": "PASS_DIAGNOSTIC_GATES",
        "M2/stick_target": "PASS_DIAGNOSTIC_GATES",
        "M3/slip_target": "FAIL_CLOSED_PROCESS_OR_RESULT",
        "M3/stick_target": "PASS_DIAGNOSTIC_GATES",
    }:
        raise RuntimeError("Historical R1.9 case classifications differ from the preserved campaign record.")
    if (
        historical_failure.get("mesh") != "M3"
        or historical_failure.get("case") != "slip_target"
        or historical_failure.get("error_type") != "NumericalConvergenceError"
        or historical_failure.get("diagnostics", {}).get("step") != 8
    ):
        raise RuntimeError("Historical R1.9 M3/slip failure identity does not match the expected failed gate.")
    source_manifest = json.loads(
        (historical_r1_9_root / "source_file_manifest.json").read_text(encoding="utf-8")
    )
    if _canonical_sha(source_manifest) != historical_contract.get("source_bundle_sha256"):
        raise RuntimeError("Historical R1.9 source manifest does not match its contract digest.")
    historical_evidence = {
        "root_absolute_path": str(historical_r1_9_root),
        "classification": "PRESERVED_HISTORICAL_R1_9_FAIL_CLOSED_NO_REWRITE",
        "m1_contract_sha256": R1_9_EXPECTED_FILE_HASHES["contract.json"],
        "m2_m3_contract_sha256": R1_9_EXPECTED_FILE_HASHES["contract_r1_9_contact_requalification.json"],
        "m2_m3_execution_binding_canonical_sha256": "d5dd9310ed7b28ea4f4821d0136e9a040c935bb7b36f60f4cc2d38063cbb89d8",
        "m1_final_sha256": R1_9_EXPECTED_FILE_HASHES["final.json"],
        "m2_m3_final_sha256": R1_9_EXPECTED_FILE_HASHES["M2_M3/final.json"],
        "m3_slip_failure_sha256": R1_9_EXPECTED_FILE_HASHES["M2_M3/M3/slip_target/failure.json"],
        "m3_slip_telemetry_sha256": R1_9_EXPECTED_FILE_HASHES["M2_M3/M3/slip_target/telemetry.jsonl"],
        "files": historical_records,
        "m1_cases": historical_final.get("cases"),
        "m2_m3_cases": historical_m2_m3["case_status"],
    }

    if parent_contract_path.resolve() != (ROOT / M1_OUTPUT_ROOT_REL / "contract.json").resolve():
        raise RuntimeError(f"{CAMPAIGN_REVISION} M1 artifacts are not in the predeclared campaign output root.")
    amendment_path = ROOT / CONTRACT_REL
    binding_path = ROOT / FREEZE_BINDING_REL
    if amendment_path.exists() or binding_path.exists():
        raise FileExistsError("R1.10 amendment already exists; refusing to rewrite frozen provenance.")

    document_path = ROOT / M1_CONTRACT_DOCUMENT_REL
    if not document_path.is_file():
        raise FileNotFoundError(f"R1.10 contract document is missing: {document_path}")
    amendment = {
        "schema": "qf.wp08.area_supported_contact_campaign_amendment.v1",
        "artifact_id": ARTIFACT_ID,
        "status": f"FROZEN_{CAMPAIGN_REVISION}_PROSPECTIVE_CONTACT_DIAGNOSTIC",
        "frozen_utc": _utc(),
        "contract_document": M1_CONTRACT_DOCUMENT_REL.as_posix(),
        "contract_document_sha256": _sha(document_path),
        "parent_contract_path": parent_contract_path.relative_to(ROOT).as_posix(),
        "parent_contract_sha256": _sha(parent_contract_path),
        "parent_freeze_binding_path": parent_binding_path.relative_to(ROOT).as_posix(),
        "parent_freeze_binding_sha256": _sha(parent_binding_path),
        "provenance_anchor": {
            "branch": parent_contract["git"]["branch"],
            "head": parent_contract["git"]["head"],
            "working_tree_at_freeze": (
                "CLEAN" if not parent_contract["git"].get("porcelain_status") else "DIRTY_HASH_BOUND"
            ),
            "m1_contract_sha256": parent_binding["contract_sha256"],
            "m1_source_bundle_sha256": source_digest,
            "m1_final_sha256": _sha(m1_final_path),
            "m1_artifact_root": output.relative_to(ROOT).as_posix(),
            "m1_cases": m1_cases,
        },
        "historical_r1_9_evidence": historical_evidence,
        "mechanics_change": {
            "production_mechanics_changed": True,
            "scope": [
                "piecewise analytic coupled-projection Jacobian including pressure-dependent residual normalization",
                "best-finite-candidate continuation for active-slip root/semismooth attempts",
                "bounded safeguarded semismooth refinement from the trust-region best candidate",
                *(
                    ["stricter internal least-squares stopping tolerances; physical residual gate unchanged"]
                    if CAMPAIGN_REVISION == "R1.11"
                    else []
                ),
            ],
            "thresholds_or_search_cap_changed": False,
            "regression_tests": [
                "tests/unit/test_wp08d_mixed_open_active_slip.py",
                "tests/unit/test_wp08_area_supported_m1_runner_r1_10.py",
                "tests/unit/test_wp08_area_supported_m2_m3_runner_r1_10.py",
                "tests/unit/test_wp08_area_supported_r1_11_optimizer_runner.py",
            ],
        },
        "unchanged": {
            "geometry": True,
            "mesh_hierarchy": True,
            "material": True,
            "boundary_conditions": True,
            "loads_and_load_steps": True,
            "friction_coefficient": True,
            "surface_stiffness_density": True,
            "iteration_limits": True,
            "contact_count_guard": True,
            "solver_backend": True,
            "fallback_policy": True,
            "tolerances_and_diagnostic_gates": CAMPAIGN_REVISION != "R1.11",
            "physical_tolerance_and_diagnostic_gates": True,
            "optimizer_termination_tolerances_changed": CAMPAIGN_REVISION == "R1.11",
            "refinement_convergence_thresholds": None,
        },
        "optimizer_stopping_policy": os.environ.get(
            "QF_WP08_OPTIMIZER_POLICY",
            "R1.10 optimizer tolerances remain equal to the solver-provided physical tolerance.",
        ),
        "execution": {
            "authorized_attempts": 1,
            "output_root": output.relative_to(ROOT).as_posix(),
            "sequence": [
                "M1/stick_target",
                "M1/slip_target",
                "M2/stick_target",
                "M2/slip_target",
                "M3/stick_target",
                "M3/slip_target",
            ],
            "serial_single_worker": True,
            "run_m2_only_if_both_m1_cases_pass": True,
            "run_m3_only_if_both_m2_cases_pass": True,
            "stop_after_any_numerical_failure": True,
            "no_retry_after_solver_starts": True,
            "no_parameter_or_threshold_adjustments": True,
            "preserve_all_prior_attempts": True,
        },
        "owner_authorization": {
            "execution_authorized": True,
            "recorded_from": "Owner instruction: freeze the runner and launch execution; explicit green light.",
            "scope": f"One serial prospective {CAMPAIGN_REVISION} M1/M2/M3 diagnostic campaign with conditional progression; no formal qualification or point award.",
        },
        "formal_wp08_qualification": False,
        "wp08_points_awarded": False,
        "independent_global_fem_reference": False,
        "formal_replay": False,
        "full_test_suite": False,
    }
    _write_json(amendment_path, amendment)
    amendment_sha = _sha(amendment_path)
    freeze_binding: dict[str, Any] = {
        "schema": "qf.wp08.area_supported_contact_campaign_freeze_binding.v1",
        "artifact_id": ARTIFACT_ID,
            "status": f"FROZEN_{CAMPAIGN_REVISION}_BEFORE_M2_M3_EXECUTION",
        "frozen_utc": _utc(),
        "contract_path": CONTRACT_REL.as_posix(),
        "contract_sha256": amendment_sha,
        "parent_contract_sha256": _sha(parent_contract_path),
        "parent_freeze_binding_sha256": _sha(parent_binding_path),
        "contract_document_path": M1_CONTRACT_DOCUMENT_REL.as_posix(),
        "contract_document_sha256": _sha(document_path),
        "m1_final_sha256": _sha(m1_final_path),
        "m1_cases": m1_cases,
        "owner_execution_authorization": True,
        "formal_wp08_qualification": False,
        "points_awarded": False,
        "freeze_binding_sha256": None,
    }
    freeze_binding["freeze_binding_sha256"] = _canonical_sha(freeze_binding)
    _write_json(binding_path, freeze_binding)
    return freeze_binding


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported value for strict JSON: {type(value).__name__}")


def _write_json(path: Path, value: object, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(_json_safe(value), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _failure_payload(
    error: BaseException,
    *,
    mesh: str,
    case: str,
    contract_sha256: str,
    execution_binding_sha256: str,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve structured solver diagnostics with the exact execution identity."""
    reason = getattr(error, "reason", None)
    return {
        "mesh": mesh,
        "case": case,
        "error_type": type(error).__name__,
        "error": str(error),
        "reason": getattr(reason, "value", reason),
        "diagnostics": getattr(error, "diagnostics", None),
        "contract_sha256": contract_sha256,
        "execution_binding_sha256": execution_binding_sha256,
        "source_bundle_sha256": binding.get("source_bundle_sha256"),
        "source_head": binding.get("git", {}).get("head"),
        "runner_sha256": binding.get("runner_sha256"),
    }


def _source_inventory() -> dict[str, str]:
    files = {
        path
        for folder in (ROOT / "src", ROOT / "scripts")
        for path in folder.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    files.update(
        ROOT / relative
        for relative in (
            "tests/unit/test_contact_sparse_stick_assembly.py",
            "tests/unit/test_contact_surface_tangential_stiffness.py",
            "tests/unit/test_frictional_contact.py",
            "tests/unit/test_frictional_contact_structural_limit.py",
            "tests/unit/test_contact_surface_lumped_penalty.py",
            "tests/unit/test_wp08d_mixed_open_active_slip.py",
            "tests/unit/test_wp08d_active_set_remediation.py",
            "tests/unit/test_wp08b_frictional_identities_rollback.py",
            "tests/unit/test_wp08c_friction_tangent_dissipation.py",
            "tests/unit/test_wp08_area_supported_m1_runner.py",
            "tests/unit/test_wp08_area_supported_m2_m3_runner.py",
            "tests/unit/test_wp08_area_supported_m1_runner_r1_10.py",
            "tests/unit/test_wp08_area_supported_m2_m3_runner_r1_10.py",
            "tests/unit/test_wp08_area_supported_benchmark_preflight.py",
            "tests/unit/test_frictional_contact_family_survey.py",
            "tests/unit/test_wp08_area_supported_m4_runner.py",
            "tests/unit/test_wp08d_phase1_runner.py",
            "tests/unit/test_wp08d_independent_reference.py",
            "tests/unit/test_wp08_area_supported_r1_11_optimizer_runner.py",
        )
    )
    if any(not path.is_file() for path in files):
        raise FileNotFoundError("A source or targeted-test file is missing from the R1.10 freeze inventory.")
    return {path.relative_to(ROOT).as_posix(): _sha(path) for path in sorted(files)}


def _git_state() -> dict[str, str]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    return {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "porcelain_status": git("status", "--porcelain"),
    }


def _contract(output: Path) -> tuple[dict[str, Any], str]:
    contract_path = ROOT / CONTRACT_REL
    amendment = json.loads(contract_path.read_text(encoding="utf-8"))
    if amendment.get("schema") != "qf.wp08.area_supported_contact_campaign_amendment.v1":
        raise RuntimeError("Unexpected R1.10 contact-campaign amendment schema.")
    base_path = ROOT / amendment["parent_contract_path"]
    if _sha(base_path) != amendment.get("parent_contract_sha256"):
        raise RuntimeError("Parent diagnostic contract hash differs from its frozen amendment.")
    parent_binding_path = ROOT / amendment["parent_freeze_binding_path"]
    if _sha(parent_binding_path) != amendment.get("parent_freeze_binding_sha256"):
        raise RuntimeError("Parent M1 freeze-binding hash differs from its amendment.")
    document_path = ROOT / amendment["contract_document"]
    if _sha(document_path) != amendment.get("contract_document_sha256"):
        raise RuntimeError("R1.10 contract document hash differs from its amendment.")
    historical = amendment["historical_r1_9_evidence"]
    historical_root = Path(historical["root_absolute_path"])
    for artifact in historical["files"]:
        historical_path = historical_root / artifact["path"]
        if (
            not historical_path.is_file()
            or historical_path.stat().st_size != artifact["size_bytes"]
            or _sha(historical_path) != artifact["sha256"]
        ):
            raise RuntimeError(f"Preserved R1.9 historical evidence hash mismatch: {historical_path}")
    contract = json.loads(base_path.read_text(encoding="utf-8"))
    contract["execution_amendment"] = amendment
    contract["provenance_anchor"] = amendment["provenance_anchor"]
    contract["contract_document_sha256"] = amendment["contract_document_sha256"]
    contract_sha = _sha(contract_path)
    binding_path = ROOT / FREEZE_BINDING_REL
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    normalized_binding = dict(binding)
    expected_binding_sha = normalized_binding.pop("freeze_binding_sha256", None)
    normalized_binding["freeze_binding_sha256"] = None
    if expected_binding_sha != _canonical_sha(normalized_binding):
        raise RuntimeError("R1.10 amendment freeze-binding digest mismatch.")
    if binding.get("contract_sha256") != contract_sha:
        raise RuntimeError("R1.10 amendment hash differs from its freeze binding.")
    if amendment.get("status") != f"FROZEN_{CAMPAIGN_REVISION}_PROSPECTIVE_CONTACT_DIAGNOSTIC":
        raise RuntimeError(f"Unexpected {CAMPAIGN_REVISION} contact-campaign amendment status.")
    if binding.get("parent_contract_sha256") != amendment.get("parent_contract_sha256"):
        raise RuntimeError("Parent contract binding mismatch.")
    if binding.get("parent_freeze_binding_sha256") != amendment.get("parent_freeze_binding_sha256"):
        raise RuntimeError("Parent M1 freeze-binding provenance mismatch.")
    if binding.get("contract_document_sha256") != amendment.get("contract_document_sha256"):
        raise RuntimeError("R1.10 contract document binding mismatch.")
    return contract, contract_sha


def _verify_m1_inputs(contract: dict[str, Any], output: Path) -> None:
    anchor = contract["provenance_anchor"]
    m1_root = ROOT / anchor["m1_artifact_root"]
    final_path = m1_root / "final.json"
    if _sha(final_path) != anchor["m1_final_sha256"]:
        raise RuntimeError("Frozen M1 final record hash mismatch.")
    final = json.loads(final_path.read_text(encoding="utf-8"))
    if final.get("status") != "M1_DIAGNOSTIC_PASS_M2_M3_READY":
        raise RuntimeError("M1 diagnostic prerequisite is not a pass candidate.")
    if final.get("contract_sha256") != anchor.get("m1_contract_sha256"):
        raise RuntimeError("Fresh M1 contract digest differs from the R1.10 provenance anchor.")
    if final.get("source_bundle_sha256") != anchor.get("m1_source_bundle_sha256"):
        raise RuntimeError("Fresh M1 source bundle differs from the R1.10 provenance anchor.")
    for case, declared in anchor["m1_cases"].items():
        case_dir = m1_root / "M1" / case
        for filename, key in (
            ("result.json", "result_sha256"),
            ("raw.npz", "raw_npz_sha256"),
            ("telemetry.jsonl", "telemetry_sha256"),
        ):
            if _sha(case_dir / filename) != declared[key]:
                raise RuntimeError(f"M1 prerequisite hash mismatch: {case}/{filename}")
        case_result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
        if (
            case_result.get("contract_sha256") != anchor["m1_contract_sha256"]
            or case_result.get("source_bundle_sha256") != anchor["m1_source_bundle_sha256"]
        ):
            raise RuntimeError(f"M1 prerequisite provenance mismatch: {case}")
        progress = json.loads((case_dir / "progress.json").read_text(encoding="utf-8"))
        if progress.get("status") != "PASS_DIAGNOSTIC_GATES":
            raise RuntimeError(f"M1 prerequisite diagnostic gate failed: {case}")
        with np.load(case_dir / "raw.npz", allow_pickle=False) as raw:
            required = {
                "node_coordinates",
                "body_node_count",
                "displacement",
                "contact_normal_force",
                "contact_tangential_force_global",
            }
            missing = sorted(required.difference(raw.files))
            if missing:
                raise RuntimeError(f"M1 raw evidence is missing comparison arrays for {case}: {missing}")


def _level(name: str) -> MeshLevel:
    for level in MESH_LEVELS:
        if level.name == name:
            return level
    raise ValueError(f"Unknown mesh level: {name}")


def build_area_supported_model(mesh: str, case: str) -> tuple[Any, np.ndarray, tuple[int, ...], dict[int, float]]:
    """Build the frozen M2/M3 model; this function does not solve it."""
    if mesh not in {"M2", "M3"}:
        raise ValueError("Only M2 and M3 are permitted by this runner.")
    if case not in {"stick_target", "slip_target"}:
        raise ValueError("Unknown tangential target case.")

    from solveur.contact.measures import reference_surface_areas
    from solveur.core.model import FiniteElementModel

    level = _level(mesh)
    body, tets, slave_faces, slave_nodes, fixed_nodes = _surface_geometry(level)
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
    tangential_resultant = (
        STICK_TANGENTIAL_RESULTANT_N if case == "stick_target" else SLIP_TANGENTIAL_RESULTANT_N
    )
    loads: list[dict[str, Any]] = []
    load_kinds: list[str] = []
    for node in slave_nodes:
        share = area_by_node[node] / patch_area
        loads.append({"node": node, "dof": "UX", "value": NORMAL_RESULTANT_N * share})
        load_kinds.append("normal")
        loads.append({"node": node, "dof": "UY", "value": tangential_resultant * share})
        load_kinds.append("tangential")
    history = [
        [
            float(step["normal_factor"] if kind == "normal" else step["tangential_factor"])
            for kind in load_kinds
        ]
        for step in M1_LOAD_STEPS
    ]
    elements = [{"type": "TET4", "nodes": list(tet), "material": "elastic"} for tet in tets]
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=elements,
        materials={"elastic": {"type": "isotropic_3d", "E": 1.0e6, "nu": POISSON_RATIO}},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in (*fixed_nodes, *master_ids)
        ],
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


def _all_finite(value: Any) -> bool:
    if isinstance(value, (float, np.floating)):
        return bool(np.isfinite(value))
    if isinstance(value, np.ndarray):
        return bool(np.all(np.isfinite(value)))
    if isinstance(value, Mapping):
        return all(_all_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_finite(item) for item in value)
    return True


def _diagnostic_gates(
    payload: dict[str, Any],
    mesh: str,
    case: str,
    body: np.ndarray,
    slave_nodes: tuple[int, ...],
    area_by_node: dict[int, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    solver = payload.get("solver", {})
    contact = solver.get("contact", {})
    rows = contact.get("contacts", [])
    active_rows = [row for row in rows if bool(row.get("active", False))]
    active_nodes = sorted({int(row["slave_node"]) for row in active_rows if "slave_node" in row})
    active_coordinates = body[active_nodes] if active_nodes else np.empty((0, 3), dtype=float)
    rank = (
        int(np.linalg.matrix_rank(active_coordinates - np.mean(active_coordinates, axis=0)))
        if len(active_nodes) >= 2
        else 0
    )
    active_area = float(sum(area_by_node.get(node, 0.0) for node in active_nodes))
    patch_area = float(sum(area_by_node.values()))
    steps = contact.get("load_steps", [])
    target_state = "stick" if case == "stick_target" else "slip"
    terminal_states = sorted({str(row.get("tangential_state", "unknown")) for row in active_rows})
    gates = {
        "serialized_observables_finite": _all_finite(payload),
        "solver_converged": bool(solver.get("converged", False)),
        "eight_load_steps_recorded": len(steps) == 8,
        "active_support_affine_rank_2": rank == 2,
        "expected_terminal_tangential_state": terminal_states == [target_state],
    }
    diagnostic = {
        "mesh": mesh,
        "case": case,
        "status": "PASS_DIAGNOSTIC_GATES" if all(gates.values()) else "FAIL_CLOSED_DIAGNOSTIC_GATE",
        "solver_converged": bool(solver.get("converged", False)),
        "solver_residual_norm": solver.get("residual_norm"),
        "load_step_count": len(steps),
        "active_slave_nodes": active_nodes,
        "active_slave_node_count": len(active_nodes),
        "slave_node_count": len(slave_nodes),
        "active_support_affine_rank": rank,
        "active_area_m2": active_area,
        "active_area_fraction": active_area / patch_area if patch_area else 0.0,
        "nominal_patch_area_m2": patch_area,
        "terminal_active_states": terminal_states,
        "expected_terminal_state": target_state,
        "fallback_count": None,
        "fallback_count_note": "Not exposed by this result schema; no zero-fallback claim.",
        "gates": gates,
    }
    return diagnostic, {"rows": rows, "active_rows": active_rows, "steps": steps}


def _worker(mesh: str, case: str, output: Path, expected_binding_sha: str) -> int:
    output = output.resolve()
    contract, contract_sha = _contract(output)
    binding_path = output / "execution_binding.json"
    source_manifest_path = output / "execution_source_manifest.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if (
        binding.get("execution_binding_sha256") != expected_binding_sha
        or _binding_digest(binding) != expected_binding_sha
    ):
        raise RuntimeError("Execution binding hash mismatch.")
    if binding.get("contract_sha256") != contract_sha or binding.get("owner_authorization", {}).get("authorized") is not True:
        raise RuntimeError("No valid Owner execution authorization is bound to this run.")
    frozen_inventory = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if _canonical_sha(frozen_inventory) != binding.get("source_bundle_sha256"):
        raise RuntimeError("Frozen execution source-manifest digest mismatch.")
    if frozen_inventory != _source_inventory():
        raise RuntimeError("Execution source tree differs from its frozen manifest.")
    if _sha(Path(__file__).resolve()) != binding.get("runner_sha256"):
        raise RuntimeError("Frozen M2/M3 runner SHA mismatch.")
    _verify_m1_inputs(contract, output)

    case_dir = output / "M2_M3" / mesh / case
    case_dir.mkdir(parents=True, exist_ok=False)
    from solveur.api.public import solve_model
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter

    model, body, slave_nodes, area_by_node = build_area_supported_model(mesh, case)
    sink = JsonlSink(case_dir / "telemetry.jsonl", fsync=True, sink_identifier=f"wp08_area_{mesh.lower()}")
    telemetry = TelemetryEmitter(
        analysis_id=f"{ARTIFACT_ID}-{mesh}-{case}",
        analysis_type="linear_static",
        route="linear_static",
        sinks=(sink,),
        metadata={
            "campaign_contract_sha256": contract_sha,
            "execution_binding_sha256": expected_binding_sha,
            "source_bundle_sha256": binding["source_bundle_sha256"],
            "mesh": mesh,
            "case": case,
        },
    )
    started = perf_counter()
    result_path = case_dir / "result.json"
    try:
        result = cast(Any, solve_model(model, enforce_policy=False, telemetry=telemetry))
        elapsed = perf_counter() - started
        payload = result.to_dict()
        diagnostic, decoded = _diagnostic_gates(payload, mesh, case, body, slave_nodes, area_by_node)
        payload.update(
            {
                "artifact_id": ARTIFACT_ID,
                "execution_kind": "EXPERIMENTAL_MESH_REFINEMENT_DIAGNOSTIC",
                "mesh": mesh,
                "case": case,
                "formal_wp08_qualification": False,
                "points_awarded": False,
                "contract_sha256": contract_sha,
                "parent_contract_sha256": contract["execution_amendment"]["parent_contract_sha256"],
                "execution_binding_sha256": expected_binding_sha,
                "source_bundle_sha256": binding["source_bundle_sha256"],
                "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
                "diagnostic": {**diagnostic, "elapsed_seconds": elapsed},
            }
        )
        _write_json(result_path, payload)
        rows = decoded["rows"]
        displacements = np.asarray(result.displacements, dtype=float)
        if displacements.size != (len(body) + 4) * 3:
            raise RuntimeError(f"Unexpected displacement vector size {displacements.size} for {mesh}.")
        areas_ordered = np.asarray([area_by_node[node] for node in slave_nodes], dtype=float)
        equilibrium = payload.get("audit", {}).get("equilibrium", {})
        contact_normal = np.asarray(
            [row.get("normal", [0.0, 0.0, 0.0]) for row in rows], dtype=float
        ).reshape((-1, 3))
        contact_pressure = np.asarray([row.get("pressure", 0.0) for row in rows], dtype=float)
        normal_forces = -contact_pressure[:, None] * contact_normal
        contact_tangent: NDArray[np.float64] = np.zeros((len(rows), 3), dtype=float)
        for index, row in enumerate(rows):
            components = np.asarray(row.get("tangential_force", [0.0, 0.0]), dtype=float)
            t1 = np.asarray(row.get("tangent_one", [0.0, 0.0, 0.0]), dtype=float)
            t2 = np.asarray(row.get("tangent_two", [0.0, 0.0, 0.0]), dtype=float)
            contact_tangent[index] = components[0] * t1 + components[1] * t2
        np.savez_compressed(
            case_dir / "raw.npz",
            displacement=displacements,
            node_coordinates=np.vstack(
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
            ),
            body_node_count=np.asarray([len(body)], dtype=np.int64),
            slave_nodes=np.asarray(slave_nodes, dtype=np.int64),
            reference_slave_area=areas_ordered,
            contact_slave_nodes=np.asarray([row.get("slave_node", -1) for row in rows], dtype=np.int64),
            contact_active=np.asarray([row.get("active", False) for row in rows], dtype=bool),
            contact_pressure=contact_pressure,
            contact_normal=contact_normal,
            contact_normal_force=normal_forces,
            contact_gap=np.asarray([row.get("gap", np.nan) for row in rows], dtype=float),
            contact_states=np.asarray([row.get("tangential_state", "unknown") for row in rows], dtype=str),
            contact_tangential_force_local=np.asarray(
                [row.get("tangential_force", [0.0, 0.0]) for row in rows], dtype=float
            ).reshape((-1, 2)),
            contact_tangential_force_global=contact_tangent,
            contact_reference_area=np.asarray([row.get("reference_slave_area", 0.0) for row in rows], dtype=float),
            reaction_resultant=np.asarray(equilibrium.get("reaction_resultant", [0.0, 0.0, 0.0]), dtype=float),
            reaction_moment=np.asarray(
                equilibrium.get("reaction_moment_about_origin", [0.0, 0.0, 0.0]), dtype=float
            ),
            force_balance_relative_error=np.asarray(
                [equilibrium.get("force_balance_relative_error", np.nan)], dtype=float
            ),
            moment_balance_relative_error=np.asarray(
                [equilibrium.get("moment_balance_relative_error", np.nan)], dtype=float
            ),
            active_slave_nodes=np.asarray(diagnostic["active_slave_nodes"], dtype=np.int64),
        )
        _write_json(
            case_dir / "progress.json",
            {"status": diagnostic["status"], **diagnostic, "execution_binding_sha256": expected_binding_sha},
        )
        return 0 if all(diagnostic["gates"].values()) else 3
    except BaseException as error:
        _write_json(
            case_dir / "failure.json",
            _failure_payload(
                error,
                mesh=mesh,
                case=case,
                contract_sha256=contract_sha,
                execution_binding_sha256=expected_binding_sha,
                binding=binding,
            ),
        )
        raise
    finally:
        telemetry.close()


def _make_execution_binding(output: Path, *, owner_authorized: bool) -> dict[str, Any]:
    contract, contract_sha = _contract(output)
    if not owner_authorized:
        raise RuntimeError("An explicit Owner authorization is required to freeze execution.")
    _verify_m1_inputs(contract, output)
    run_root = output / "M2_M3"
    if run_root.exists():
        raise FileExistsError("M2_M3 output directory already exists; refusing to overwrite or rerun.")
    if (output / "execution_binding.json").exists() or (output / "execution_source_manifest.json").exists():
        raise FileExistsError("An execution binding already exists; refusing to replace it.")

    inventory = _source_inventory()
    source_digest = _canonical_sha(inventory)
    if source_digest != contract["provenance_anchor"]["m1_source_bundle_sha256"]:
        raise RuntimeError("Source tree no longer matches the R1.10 M1 execution source bundle.")
    _write_json(output / "execution_source_manifest.json", inventory)
    test_path = ROOT / os.environ.get(
        "QF_WP08_RUNNER_TEST_REL", "tests/unit/test_wp08_area_supported_m2_m3_runner_r1_10.py"
    )
    binding: dict[str, Any] = {
        "schema": "qf.wp08.area_supported_contact_campaign_execution_binding.v1",
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": _utc(),
        "contract_path": CONTRACT_REL.as_posix(),
        "contract_sha256": contract_sha,
        "contract_document_sha256": contract["contract_document_sha256"],
        "parent_contract_sha256": contract["execution_amendment"]["parent_contract_sha256"],
        "runner_path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "runner_sha256": _sha(Path(__file__).resolve()),
        "targeted_test_path": test_path.relative_to(ROOT).as_posix(),
        "targeted_test_sha256": _sha(test_path) if test_path.is_file() else None,
        "source_manifest_path": "execution_source_manifest.json",
        "source_file_count": len(inventory),
        "source_bundle_sha256": source_digest,
        "git": _git_state(),
        "runtime": {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "policy_digest_context_only": POLICY_DIGEST_CONTEXT,
            "governing_policy_enforced": False,
        },
        "owner_authorization": {
            "authorized": True,
            "scope": f"Run M2 and M3 stick_target/slip_target sequentially under the frozen {CAMPAIGN_REVISION} campaign; M3 only after both M2 cases pass; no formal qualification or point award.",
            "recorded_from": "Explicit Owner instruction: freeze the runner and launch execution; green light.",
            "recorded_utc": _utc(),
        },
        "m1_inputs_reverified": True,
        "execution_order": ["M2/stick_target", "M2/slip_target", "M3/stick_target", "M3/slip_target"],
        "execution_policy": "one child process at a time; stop after any numerical failure; M3 only if both M2 gates pass; preserve all artifacts; no rerun",
        "execution_binding_sha256": None,
    }
    binding_sha = _canonical_sha(binding)
    binding["execution_binding_sha256"] = binding_sha
    _write_json(output / "execution_binding.json", binding)
    return binding


def _verify_execution_binding(output: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    contract, contract_sha = _contract(output)
    binding_path = output / "execution_binding.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    expected = binding.get("execution_binding_sha256")
    if expected != _binding_digest(binding):
        raise RuntimeError("Execution binding canonical digest mismatch.")
    if binding.get("contract_sha256") != contract_sha or binding.get("owner_authorization", {}).get("authorized") is not True:
        raise RuntimeError("Execution authorization/contract binding mismatch.")
    source_manifest = json.loads((output / binding["source_manifest_path"]).read_text(encoding="utf-8"))
    if len(source_manifest) != binding.get("source_file_count"):
        raise RuntimeError("Execution source manifest count mismatch.")
    if _canonical_sha(source_manifest) != binding.get("source_bundle_sha256"):
        raise RuntimeError("Execution source manifest digest mismatch.")
    if source_manifest != _source_inventory():
        raise RuntimeError("Source files changed after execution freeze.")
    if _sha(Path(__file__).resolve()) != binding.get("runner_sha256"):
        raise RuntimeError("Runner source SHA differs from frozen execution binding.")
    _verify_m1_inputs(contract, output)
    return contract, binding, str(expected)


def _invoke(output: Path, mesh: str, case: str, binding_sha: str) -> dict[str, Any]:
    logs = output / "_process_logs"
    logs.mkdir(exist_ok=True)
    tag = f"{mesh}_{case}"
    stdout_path = logs / f"{tag}.stdout.log"
    stderr_path = logs / f"{tag}.stderr.log"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--worker",
        "--output-root",
        str(output),
        "--mesh",
        mesh,
        "--case",
        case,
        "--execution-binding-sha256",
        binding_sha,
    ]
    started = _utc()
    child_started = perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        child = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, text=False)
        exit_code = child.wait()
    execution_binding = json.loads((output / "execution_binding.json").read_text(encoding="utf-8"))
    record = {
        "mesh": mesh,
        "case": case,
        "execution_kind": "EXPERIMENTAL_MESH_REFINEMENT_DIAGNOSTIC",
        "pid": child.pid,
        "command": command,
        "started_utc": started,
        "ended_utc": _utc(),
        "elapsed_seconds": perf_counter() - child_started,
        "exit_code": exit_code,
        "contract_sha256": _sha(ROOT / CONTRACT_REL),
        "parent_contract_sha256": execution_binding["parent_contract_sha256"],
        "execution_binding_sha256": binding_sha,
        "stdout_path": stdout_path.relative_to(output).as_posix(),
        "stdout_sha256": _sha(stdout_path),
        "stderr_path": stderr_path.relative_to(output).as_posix(),
        "stderr_sha256": _sha(stderr_path),
    }
    case_dir = output / "M2_M3" / mesh / case
    result_path = case_dir / "result.json"
    if result_path.is_file():
        record["result_path"] = result_path.relative_to(output).as_posix()
        record["result_sha256"] = _sha(result_path)
        record["raw_path"] = (case_dir / "raw.npz").relative_to(output).as_posix()
        record["raw_sha256"] = _sha(case_dir / "raw.npz")
        record["telemetry_path"] = (case_dir / "telemetry.jsonl").relative_to(output).as_posix()
        record["telemetry_sha256"] = _sha(case_dir / "telemetry.jsonl")
    else:
        failure_path = case_dir / "failure.json"
        if failure_path.is_file():
            record["failure_path"] = failure_path.relative_to(output).as_posix()
            record["failure_sha256"] = _sha(failure_path)
    _write_json(logs / f"{tag}.process.json", record)
    return record


def _relative_delta(coarse: np.ndarray, fine: np.ndarray) -> dict[str, float | None]:
    coarse = np.asarray(coarse, dtype=float)
    fine = np.asarray(fine, dtype=float)
    if coarse.shape != fine.shape:
        return {"absolute_l2": None, "relative_l2": None}
    absolute = float(np.linalg.norm(fine - coarse))
    denominator = max(float(np.linalg.norm(coarse)), float(np.linalg.norm(fine)))
    relative = absolute / denominator if denominator > 0.0 else (0.0 if absolute == 0.0 else None)
    return {"absolute_l2": absolute, "relative_l2": relative}


def _load_case_metrics(case_root: Path, mesh: str, case: str) -> dict[str, Any]:
    case_dir = case_root / mesh / case
    result = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    with np.load(case_dir / "raw.npz", allow_pickle=False) as raw:
        required = {
            "node_coordinates",
            "body_node_count",
            "displacement",
            "contact_normal_force",
            "contact_tangential_force_global",
        }
        missing = sorted(required.difference(raw.files))
        if missing:
            raise ValueError(f"{mesh}/{case} raw.npz is missing required comparison arrays: {missing}")
        coordinates = np.asarray(raw["node_coordinates"], dtype=float)
        body_node_count = int(np.asarray(raw["body_node_count"], dtype=np.int64)[0])
        displacement = np.asarray(raw["displacement"], dtype=float).reshape((-1, 3))
        normal_force = np.asarray(raw["contact_normal_force"], dtype=float).reshape((-1, 3))
        tangential_force = np.asarray(raw["contact_tangential_force_global"], dtype=float).reshape((-1, 3))
    if coordinates.ndim != 2 or coordinates.shape[1] != 3:
        raise ValueError(f"{mesh}/{case} node_coordinates must be N×3.")
    if coordinates.shape != displacement.shape or not 0 < body_node_count <= len(coordinates):
        raise ValueError(f"{mesh}/{case} coordinate/displacement dimensions are inconsistent.")
    if normal_force.shape != tangential_force.shape:
        raise ValueError(f"{mesh}/{case} contact force arrays have inconsistent dimensions.")
    if not all(np.all(np.isfinite(array)) for array in (coordinates, displacement, normal_force, tangential_force)):
        raise ValueError(f"{mesh}/{case} required comparison arrays contain non-finite values.")
    equilibrium = result.get("audit", {}).get("equilibrium", {})
    required_equilibrium = ("reaction_resultant", "reaction_moment_about_origin")
    missing_equilibrium = [name for name in required_equilibrium if name not in equilibrium]
    if missing_equilibrium:
        raise ValueError(f"{mesh}/{case} result is missing equilibrium fields: {missing_equilibrium}")
    contact = result.get("solver", {}).get("contact", {})
    rows = contact.get("contacts", [])
    if not isinstance(rows, list):
        raise ValueError(f"{mesh}/{case} contact rows are not a list.")
    return {
        "mesh": mesh,
        "case": case,
        "result": result,
        "coordinates": coordinates,
        "body_node_count": body_node_count,
        "displacement": displacement,
        "reaction_resultant": np.asarray(equilibrium["reaction_resultant"], dtype=float),
        "reaction_moment": np.asarray(equilibrium["reaction_moment_about_origin"], dtype=float),
        "normal_resultant": np.sum(normal_force, axis=0),
        "tangential_resultant": np.sum(tangential_force, axis=0),
        "active_area": float(result["diagnostic"]["active_area_m2"]),
        "active_area_fraction": float(result["diagnostic"]["active_area_fraction"]),
        "active_node_count": int(result["diagnostic"]["active_slave_node_count"]),
        "active_rank": int(result["diagnostic"]["active_support_affine_rank"]),
        "state_counts": {
            state: sum(1 for row in rows if row.get("active") and row.get("tangential_state") == state)
            for state in ("stick", "slip", "open", "unknown")
        },
        "friction_utilization_max": max(
            (
                float(row.get("tangential_force_norm", 0.0)) / float(row["friction_limit"])
                for row in rows
                if row.get("active") and float(row.get("friction_limit", 0.0)) > 0.0
            ),
            default=0.0,
        ),
        "tangential_energy": float(contact.get("cumulative_local_dissipation", 0.0)),
        "force_balance_relative_error": equilibrium.get("force_balance_relative_error"),
        "moment_balance_relative_error": equilibrium.get("moment_balance_relative_error"),
        "solver_residual_norm": result.get("solver", {}).get("residual_norm"),
    }


def _common_coordinate_displacement_delta(coarse: dict[str, Any], fine: dict[str, Any]) -> dict[str, Any]:
    coarse_map = {
        tuple(np.round(point, 12)): coarse["displacement"][index]
        for index, point in enumerate(coarse["coordinates"][: coarse["body_node_count"]])
    }
    fine_map = {
        tuple(np.round(point, 12)): fine["displacement"][index]
        for index, point in enumerate(fine["coordinates"][: fine["body_node_count"]])
    }
    shared = sorted(set(coarse_map).intersection(fine_map))
    if not shared:
        return {"common_node_count": 0, "absolute_l2_m": None, "relative_l2": None}
    a = np.asarray([coarse_map[key] for key in shared], dtype=float)
    b = np.asarray([fine_map[key] for key in shared], dtype=float)
    delta = _relative_delta(a, b)
    return {
        "common_node_count": len(shared),
        "absolute_l2_m": delta["absolute_l2"],
        "relative_l2": delta["relative_l2"],
    }


def _refinement_comparison(coarse: dict[str, Any], fine: dict[str, Any]) -> dict[str, Any]:
    return {
        "from": coarse["mesh"],
        "to": fine["mesh"],
        "case": coarse["case"],
        "common_node_displacement": _common_coordinate_displacement_delta(coarse, fine),
        "reaction_resultant_relative_delta": _relative_delta(
            coarse["reaction_resultant"], fine["reaction_resultant"]
        ),
        "reaction_moment_relative_delta": _relative_delta(coarse["reaction_moment"], fine["reaction_moment"]),
        "normal_contact_resultant_relative_delta": _relative_delta(
            coarse["normal_resultant"], fine["normal_resultant"]
        ),
        "tangential_contact_resultant_relative_delta": _relative_delta(
            coarse["tangential_resultant"], fine["tangential_resultant"]
        ),
        "active_area_m2": {"from": coarse["active_area"], "to": fine["active_area"]},
        "active_area_fraction": {"from": coarse["active_area_fraction"], "to": fine["active_area_fraction"]},
        "active_node_count": {"from": coarse["active_node_count"], "to": fine["active_node_count"]},
        "active_support_affine_rank": {"from": coarse["active_rank"], "to": fine["active_rank"]},
        "stick_slip_state_counts": {"from": coarse["state_counts"], "to": fine["state_counts"]},
        "max_friction_utilization": {"from": coarse["friction_utilization_max"], "to": fine["friction_utilization_max"]},
        "reported_dissipation": {"from": coarse["tangential_energy"], "to": fine["tangential_energy"]},
        "force_balance_relative_error": {
            "from": coarse["force_balance_relative_error"],
            "to": fine["force_balance_relative_error"],
        },
        "moment_balance_relative_error": {
            "from": coarse["moment_balance_relative_error"],
            "to": fine["moment_balance_relative_error"],
        },
        "solver_residual_norm": {"from": coarse["solver_residual_norm"], "to": fine["solver_residual_norm"]},
        "classification": "DESCRIPTIVE_ONLY_NO_FROZEN_MESH_CONVERGENCE_THRESHOLD",
    }


def _case_skip_reason(mesh: str, case: str, case_status: Mapping[str, str]) -> str | None:
    """Apply the frozen fail-closed serial campaign dependencies."""
    if mesh == "M2" and case == "slip_target":
        if case_status.get("M2/stick_target") != "PASS_DIAGNOSTIC_GATES":
            return "NOT_RUN_PREVIOUS_M2_CASE_FAILED"
    if mesh == "M3":
        if any(
            case_status.get(f"M2/{name}") != "PASS_DIAGNOSTIC_GATES"
            for name in ("stick_target", "slip_target")
        ):
            return "NOT_RUN_M2_GATE_FAILED"
        if case == "slip_target" and case_status.get("M3/stick_target") != "PASS_DIAGNOSTIC_GATES":
            return "NOT_RUN_PREVIOUS_M3_CASE_FAILED"
    return None


def execute(output: Path) -> int:
    output = output.resolve()
    contract, binding, binding_sha = _verify_execution_binding(output)
    run_root = output / "M2_M3"
    if run_root.exists():
        raise FileExistsError("M2_M3 results already exist; refusing rerun or overwrite.")
    run_root.mkdir(parents=True, exist_ok=False)
    process_records: list[dict[str, Any]] = []
    case_status: dict[str, str] = {}
    order = [("M2", "stick_target"), ("M2", "slip_target"), ("M3", "stick_target"), ("M3", "slip_target")]
    for mesh, case in order:
        skip_reason = _case_skip_reason(mesh, case, case_status)
        if skip_reason is not None:
            case_status[f"{mesh}/{case}"] = skip_reason
            _write_json(
                run_root / "progress.json",
                {
                    "status": "RUNNING",
                    "completed_cases": list(case_status),
                    "case_status": case_status,
                    "processes": process_records,
                    "m2_m3_started": True,
                },
                exclusive=False,
            )
            continue
        record = _invoke(output, mesh, case, binding_sha)
        process_records.append(record)
        result_path = output / "M2_M3" / mesh / case / "result.json"
        if record["exit_code"] == 0 and result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            case_status[f"{mesh}/{case}"] = str(result.get("diagnostic", {}).get("status", "UNKNOWN"))
        else:
            case_status[f"{mesh}/{case}"] = "FAIL_CLOSED_PROCESS_OR_RESULT"
        _write_json(
            run_root / "progress.json",
            {
                "status": "RUNNING",
                "completed_cases": list(case_status),
                "case_status": case_status,
                "processes": process_records,
                "m2_m3_started": True,
            },
            exclusive=False,
        )

    metrics: dict[str, Any] = {}
    postprocess_error: dict[str, str] | None = None
    m1_root = ROOT / contract["provenance_anchor"]["m1_artifact_root"]
    try:
        for case in ("stick_target", "slip_target"):
            if case_status.get(f"M2/{case}") == "PASS_DIAGNOSTIC_GATES":
                m1 = _load_case_metrics(m1_root, "M1", case)
                m2 = _load_case_metrics(run_root, "M2", case)
                metrics[f"{case}/M1_to_M2"] = _refinement_comparison(m1, m2)
            if (
                case_status.get(f"M3/{case}") == "PASS_DIAGNOSTIC_GATES"
                and case_status.get(f"M2/{case}") == "PASS_DIAGNOSTIC_GATES"
            ):
                m2 = _load_case_metrics(run_root, "M2", case)
                m3 = _load_case_metrics(run_root, "M3", case)
                metrics[f"{case}/M2_to_M3"] = _refinement_comparison(m2, m3)
    except Exception as error:
        postprocess_error = {"error_type": type(error).__name__, "error": str(error)}

    m2_ok = all(case_status.get(f"M2/{case}") == "PASS_DIAGNOSTIC_GATES" for case in ("stick_target", "slip_target"))
    m3_ran = any(key.startswith("M3/") and value != "NOT_RUN_M2_GATE_FAILED" for key, value in case_status.items())
    m3_ok = all(
        case_status.get(f"M3/{case}") == "PASS_DIAGNOSTIC_GATES"
        for case in ("stick_target", "slip_target")
    ) if m3_ran else False
    if postprocess_error is not None:
        final_status = "FAIL_CLOSED_POSTPROCESSING"
    elif m2_ok and m3_ok:
        final_status = "M2_M3_DIAGNOSTIC_CASES_PASS_REFINEMENT_UNCLASSIFIED"
    else:
        final_status = "M2_M3_DIAGNOSTIC_INCOMPLETE_OR_FAIL_CLOSED"
    final = {
        "artifact_id": ARTIFACT_ID,
        "status": final_status,
        "contract_sha256": _sha(ROOT / CONTRACT_REL),
        "parent_contract_sha256": contract["execution_amendment"]["parent_contract_sha256"],
        "execution_binding_sha256": binding_sha,
        "source_bundle_sha256": binding["source_bundle_sha256"],
        "source_head": binding["git"]["head"],
        "case_status": case_status,
        "processes": process_records,
        "refinement_diagnostics": metrics,
        "postprocessing_error": postprocess_error,
        "m2_all_case_gates_pass": m2_ok,
        "m3_started": bool(m3_ran),
        "m3_all_case_gates_pass": m3_ok,
        "mesh_convergence_status": "NOT_CLASSIFIED_NO_FROZEN_THRESHOLD",
        "formal_wp08_qualification": False,
        "points_awarded": False,
        "independent_global_fem_reference_run": False,
        "external_solver_correlation_run": False,
        "formal_replay_run": False,
        "full_test_suite_run": False,
        "production_mechanics_changed": True,
        "thresholds_changed": False,
    }
    _write_json(run_root / "final.json", final)
    _write_json(
        run_root / "progress.json",
        {"status": "COMPLETED" if postprocess_error is None else "FAIL_CLOSED_POSTPROCESSING", **final},
        exclusive=False,
    )
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if m2_ok and m3_ok else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--prepare-r1-10-amendment", action="store_true")
    parser.add_argument("--freeze-runner", action="store_true")
    parser.add_argument("--owner-authorized", choices=("yes", "no"))
    parser.add_argument("--historical-r1-9-root", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--mesh", choices=("M2", "M3"))
    parser.add_argument("--case", choices=("stick_target", "slip_target"))
    parser.add_argument("--execution-binding-sha256")
    args = parser.parse_args()
    if args.prepare_r1_10_amendment:
        binding = prepare_r1_10_amendment(
            args.output_root.resolve(),
            historical_r1_9_root=args.historical_r1_9_root,
            owner_authorized=args.owner_authorized == "yes",
        )
        print(json.dumps(binding, indent=2, sort_keys=True))
        return 0
    if args.freeze_runner:
        binding = _make_execution_binding(args.output_root.resolve(), owner_authorized=args.owner_authorized == "yes")
        print(json.dumps(binding, indent=2, sort_keys=True))
        return 0
    if args.execute:
        return execute(args.output_root)
    if args.worker and args.mesh and args.case and args.execution_binding_sha256:
        return _worker(args.mesh, args.case, args.output_root, args.execution_binding_sha256)
    parser.error("Choose --freeze-runner, --execute, or a complete --worker invocation.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
