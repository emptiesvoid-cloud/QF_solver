"""Generate the immutable WP12 R3 expanded correlation contract.

The script refuses an existing contract and only freezes the checked-in case
matrix, never execution results. Run and commit its output before any solve.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.wp12_expanded_models import (  # noqa: E402
    FAMILIES,
    GEOMETRIES,
    LOADS,
    MATERIAL,
    MESHES,
    case_catalog,
)

CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_5_expanded_contract.json")
OUTPUT_ROOT = "qualification/0_2_9/wp12_external_vv_r3_5_expanded_raw"
MANIFEST_PATH = "qualification/0_2_9/wp12_external_vv_r3_5_expanded_manifest.json"
BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "c5e842d5e589358633221ecd9f29c2ff1ef003aa"
IMAGE = "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
IMAGE_ID = "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
R3_2_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_2_expanded_contract.json")
R3_2_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_2_expanded_manifest.json")
R3_2_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_2_expanded_audit.json")
R3_3_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_3_expanded_contract.json")
R3_3_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_3_expanded_manifest.json")
R3_3_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_3_execution_audit.json")
R3_4_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_4_expanded_contract.json")
R3_4_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_4_expanded_manifest.json")
R3_4_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_4_execution_audit.json")
R3_4_FULL_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_4_expanded_audit.json")
R3_5_SMOKE_REPORT = Path("qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke.json")
R3_5_SMOKE_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke_manifest.json")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _source_commit(path: str) -> str:
    return _git("log", "-1", "--format=%H", "--", path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_contract() -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Must freeze on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before contract freeze.")
    head = _git("rev-parse", "HEAD")
    if head != _git("rev-parse", "--verify", f"{BASE_SHA}^{{commit}}") and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False
    ).returncode != 0:
        raise RuntimeError("WP12 R3 branch does not descend from the preserved R2 audit package.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("WP12 expanded correlation preparation changed production source.")
    parent_audit = json.loads((ROOT / R3_2_AUDIT).read_text(encoding="utf-8"))
    if parent_audit.get("audit_status") != "FAIL_CLOSED" or parent_audit.get("case_count") != 144 or parent_audit.get("case_pass_count") != 132:
        raise RuntimeError("Preserved R3.2 audit is missing or differs from its recorded 132/144 fail-closed result.")
    parent_contract = json.loads((ROOT / R3_2_CONTRACT).read_text(encoding="utf-8"))
    if parent_contract.get("revision") != "R3_2_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION":
        raise RuntimeError("Preserved R3.2 contract identity is inconsistent.")
    r3_3_contract = json.loads((ROOT / R3_3_CONTRACT).read_text(encoding="utf-8"))
    r3_3_audit = json.loads((ROOT / R3_3_AUDIT).read_text(encoding="utf-8"))
    if (
        r3_3_contract.get("revision") != "R3_3_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION"
        or r3_3_contract.get("status") != "FROZEN"
        or r3_3_audit.get("audit_status") != "FAIL_CLOSED"
        or r3_3_audit.get("case_count") != 144
        or r3_3_audit.get("completed_case_count") != 20
        or r3_3_audit.get("completed_failure_count") != 20
        or r3_3_audit.get("completed_pass_count") != 0
        or r3_3_audit.get("interrupted_case_count") != 1
        or r3_3_audit.get("not_started_case_count") != 123
        or r3_3_audit.get("contract_sha256") != _sha256(R3_3_CONTRACT)
        or r3_3_audit.get("manifest_sha256") != _sha256(R3_3_MANIFEST)
        or r3_3_audit.get("manifest_entry_count") != 337
        or r3_3_audit.get("manifest_hash_audit") != "PASS; all 337 listed files exist with matching size and SHA-256; no missing or extra files"
    ):
        raise RuntimeError("Preserved R3.3 interrupted fail-closed evidence is missing or inconsistent.")
    r3_3_execution_sha = str(r3_3_audit.get("execution_sha", ""))
    if _git("rev-parse", f"{r3_3_execution_sha}^") != r3_3_contract.get("freeze_commit_sha"):
        raise RuntimeError("R3.3 execution SHA does not immediately follow its recorded freeze commit.")
    r3_4_contract = json.loads((ROOT / R3_4_CONTRACT).read_text(encoding="utf-8"))
    r3_4_audit = json.loads((ROOT / R3_4_AUDIT).read_text(encoding="utf-8"))
    r3_4_full_audit = json.loads((ROOT / R3_4_FULL_AUDIT).read_text(encoding="utf-8"))
    if (
        r3_4_contract.get("revision") != "R3_4_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION"
        or r3_4_audit.get("audit_status") != "FAIL_CLOSED"
        or r3_4_audit.get("case_count") != 144
        or r3_4_audit.get("attempted_case_count") != 1
        or r3_4_audit.get("case_pass_count") != 0
        or r3_4_audit.get("not_started_case_count") != 143
        or r3_4_audit.get("contract_sha256") != _sha256(R3_4_CONTRACT)
        or r3_4_audit.get("manifest_sha256") != _sha256(R3_4_MANIFEST)
        or r3_4_audit.get("manifest_entry_count") != 20
        or r3_4_audit.get("independent_audit_sha256") != _sha256(R3_4_FULL_AUDIT)
        or r3_4_full_audit.get("audit_status") != "FAIL_CLOSED"
        or r3_4_full_audit.get("case_pass_count") != 0
    ):
        raise RuntimeError("Preserved R3.4 first-case fail-closed evidence is missing or inconsistent.")
    r3_4_execution_sha = str(r3_4_audit.get("execution_sha", ""))
    if _git("rev-parse", f"{r3_4_execution_sha}^") != r3_4_contract.get("freeze_commit_sha"):
        raise RuntimeError("R3.4 execution SHA does not immediately follow its recorded freeze commit.")
    smoke = json.loads((ROOT / R3_5_SMOKE_REPORT).read_text(encoding="utf-8"))
    if (
        smoke.get("status") != "PASS_DIAGNOSTIC_ONLY"
        or smoke.get("case_count") != 4
        or smoke.get("case_pass_count") != 4
        or smoke.get("not_started_case_count") != 0
        or set(smoke.get("families", [])) != set(FAMILIES)
        or subprocess.run(
            ["git", "cat-file", "-e", f"{smoke.get('source_sha', '')}^{{commit}}"], cwd=ROOT, check=False
        ).returncode != 0
        or smoke.get("runner_sha") != _source_commit("scripts/run_wp12_expanded_code_aster.py")
        or smoke.get("smoke_runner_sha") != _source_commit("scripts/smoke_wp12_expanded_code_aster.py")
        or {case.get("family") for case in smoke.get("cases", []) if case.get("status") == "PASS_SMOKE_ONLY"} != set(FAMILIES)
        or smoke.get("threshold_source_contract_sha256") != _sha256(R3_4_CONTRACT)
        or smoke.get("manifest_sha256") != _sha256(R3_5_SMOKE_MANIFEST)
    ):
        raise RuntimeError("R3.5 diagnostic mesh smoke is incomplete, stale, or not independently hash-bound.")

    cases = []
    for case in case_catalog():
        cases.append(
            {
                "case_id": case.case_id,
                "family": case.family,
                "geometry": case.geometry,
                "dimensions_m": list(case.dimensions),
                "mesh": case.mesh,
                "divisions": list(case.divisions),
                "load_case": case.load_case,
                "resultant_N": list(case.resultant),
                "load_area_m2": case.load_area,
                "load_moment_origin_Nm": list(case.load_moment),
                "model_fingerprint": case.fingerprint,
                "nodes": len(case.model.nodes),
                "elements": len(case.connectivity),
                "dofs": int(case.system.stiffness.shape[0]),
            }
        )
    return {
        "work_package": "WP12",
        "revision": "R3_5_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION",
        "status": "FROZEN",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "branch": BRANCH,
        "branch_base_sha": BASE_SHA,
        "freeze_commit_sha": head,
        "runner_sha": _source_commit("scripts/run_wp12_expanded_code_aster.py"),
        "smoke_runner_sha": _source_commit("scripts/smoke_wp12_expanded_code_aster.py"),
        "model_builder_sha": _source_commit("scripts/wp12_expanded_models.py"),
        "auditor_sha": _source_commit("scripts/audit_wp12_expanded_code_aster.py"),
        "contract_builder_sha": _source_commit("scripts/freeze_wp12_expanded_contract.py"),
        "execution_authorized": True,
        "abort_on_execution_failure": True,
        "execution_authorization": {
            "basis": "Owner request to substantially increase external correlation coverage after acceptance of the WP12 R2 perimeter; fresh reruns preserved R3.2 truncation, R3.3 numeric-name rejection, and R3.4 nodal-load identifier failure before preparing this revision.",
            "scope": "144 sequential same-mesh QF Solver SciPy direct versus Code_Aster 18.1 serial linear-static correlations. Use Code_Aster native node IDs N1, N2, ... for mesh and nodal-load cards; use short bijective alphabetic element IDs A..Z, AA... to keep every .mail record at or below 80 columns. Abort on the first execution exception; one CPU per Code_Aster container; no nonlinear runs, no ledger change, no merge, no push.",
        },
        "pre_execution_mesh_smoke": {
            "status": smoke.get("status"),
            "report_path": R3_5_SMOKE_REPORT.as_posix(),
            "report_sha256": _sha256(R3_5_SMOKE_REPORT),
            "manifest_path": R3_5_SMOKE_MANIFEST.as_posix(),
            "manifest_sha256": _sha256(R3_5_SMOKE_MANIFEST),
            "source_sha": smoke.get("source_sha"),
            "runner_sha": smoke.get("runner_sha"),
            "smoke_runner_sha": smoke.get("smoke_runner_sha"),
            "case_count": smoke.get("case_count"),
            "case_pass_count": smoke.get("case_pass_count"),
            "formal_correlation_evidence": False,
        },
        "case_count": len(cases),
        "code_aster_version": "18.1.0",
        "code_aster_image": IMAGE,
        "code_aster_image_id": IMAGE_ID,
        "timeout_seconds": 900,
        "memory_limit_mb": 4096,
        "families": list(FAMILIES),
        "geometry_catalog_m": {name: list(values) for name, values in GEOMETRIES.items()},
        "mesh_catalog_cells": {name: list(values) for name, values in MESHES.items()},
        "load_catalog_resultants_N": {name: list(values) for name, values in LOADS.items()},
        "material": dict(MATERIAL),
        "case_matrix_order": ["family", "geometry", "mesh", "load_case"],
        "loading": {
            "definition": "uniform traction over the complete distal x=L face, integrated to consistent equivalent nodal forces for each element interpolation",
            "total_resultant_magnitude_N": 1000.0,
            "tetrahedral_face_integration": "T3: area/3 per corner; T6: area/3 per edge-midpoint, zero corner contribution for constant traction",
            "hexahedral_face_integration": "2D tensor Gauss integration of HEX8/HEX20 shape functions on xi=+1 face",
            "moment_reference": "global origin; expected for uniform planar traction at (L,H/2,W/2)",
        },
        "boundary_condition": "all translational DOFs fixed on the complete x=0 plane; no other constraints",
        "qf_solver": {
            "backend": "SciPy sparse direct spsolve via the existing WP11 linear-system helper",
            "analysis": "small-strain linear static",
            "fallback": "none",
        },
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "image": IMAGE,
            "image_id": IMAGE_ID,
            "modelisation": "3D",
            "fresh_container_per_case": True,
            "cpu_limit": 1,
            "mpi": False,
            "action": "make_etude",
            "timeout_seconds": 900,
            "memory_limit_mb": 4096,
        },
        "gates": {
            "displacement_relative_l2": 1e-8,
            "displacement_relative_linf": 1e-8,
            "reaction_relative_l2": 1e-8,
            "reaction_relative_linf": 1e-8,
            "strain_energy_from_external_work_relative": 1e-8,
            "qf_free_residual_relative_l2": 1e-8,
            "qf_force_equilibrium_relative": 1e-8,
            "aster_force_equilibrium_relative": 1e-8,
            "qf_moment_equilibrium_relative": 1e-8,
            "aster_moment_equilibrium_relative": 1e-8,
            "fixed_displacement_abs_max": 1e-12,
        },
        "output_root": OUTPUT_ROOT,
        "manifest_path": MANIFEST_PATH,
        "raw_artifact_storage": "local ignored output root; versioned sibling SHA-256 manifest and compact reports",
        "points_policy": {
            "official_points_changed": False,
            "candidate_points": "supplemental evidence only; no automatic WP12 point allocation",
        },
        "fail_closed": True,
        "thresholds_frozen_before_execution": True,
        "post_result_threshold_retuning_allowed": False,
        "output_overwrite_allowed": False,
        "full_repository_test_suite": False,
        "cases": cases,
        "supersedes_diagnostic_campaign": {
            "revision": "R3.2",
            "contract_path": R3_2_CONTRACT.as_posix(),
            "contract_sha256": _sha256(R3_2_CONTRACT),
            "execution_sha": parent_contract.get("freeze_commit_sha"),
            "manifest_path": R3_2_MANIFEST.as_posix(),
            "manifest_sha256": _sha256(R3_2_MANIFEST),
            "audit_path": R3_2_AUDIT.as_posix(),
            "audit_sha256": _sha256(R3_2_AUDIT),
            "audit_status": parent_audit.get("audit_status"),
            "candidate_cases_passed": parent_audit.get("case_pass_count"),
            "case_count": parent_audit.get("case_count"),
            "raw_evidence_reused": False,
            "historical_results_preserved": True,
        },
        "limitations": [
            "bounded homogeneous isotropic 3D small-strain linear-static elasticity only",
            "only TET4, HEX8, TET10, and HEX20 are covered; no wedge, pyramid, shell, or beam family",
            "three simple rectangular block geometries, three low-to-moderate structured mesh sizes, and four prescribed distal-face traction directions",
            "mesh labels H1/H2/H3 define model diversity only; no mesh-convergence or asymptotic accuracy claim",
            "same discrete mesh, material, boundary conditions, and consistent nodal force vector are supplied to both solvers",
            "no stress-field comparison, material nonlinearity, geometric nonlinearity, contact, friction, dynamics, buckling, continuation, or MPI/PETSc claim",
            "correlation between two FEM implementations is not experimental validation",
            "this supplemental R3.5 campaign does not alter existing WP12 R2 results, R3.2, R3.3, or R3.4 failures, Owner decisions, points, or global ledger",
        ],
        "supersedes_failed_attempt": {
            "revision": "R3.4",
            "contract_path": R3_4_CONTRACT.as_posix(),
            "contract_sha256": _sha256(R3_4_CONTRACT),
            "execution_sha": r3_4_execution_sha,
            "manifest_path": R3_4_MANIFEST.as_posix(),
            "manifest_sha256": _sha256(R3_4_MANIFEST),
            "audit_path": R3_4_AUDIT.as_posix(),
            "audit_sha256": _sha256(R3_4_AUDIT),
            "independent_audit_path": R3_4_FULL_AUDIT.as_posix(),
            "independent_audit_sha256": _sha256(R3_4_FULL_AUDIT),
            "audit_status": r3_4_audit.get("audit_status"),
            "attempted_cases": r3_4_audit.get("attempted_case_count"),
            "not_started_cases": r3_4_audit.get("not_started_case_count"),
            "raw_evidence_reused": False,
            "historical_results_preserved": True,
        },
    }


def main() -> int:
    target = ROOT / CONTRACT_PATH
    if target.exists():
        raise SystemExit(f"Refusing to overwrite frozen contract: {target}")
    contract = build_contract()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(CONTRACT_PATH), "cases": contract["case_count"], "freeze_commit_sha": contract["freeze_commit_sha"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
