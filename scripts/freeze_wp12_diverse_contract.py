"""Freeze the prospective WP12 R3.6 diverse-topology correlation contract."""

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

from scripts.run_wp12_expanded_code_aster import IMAGE  # noqa: E402
from scripts.wp12_diverse_models import (  # noqa: E402
    FAMILIES,
    GEOMETRIES,
    LOADS,
    MATERIAL,
    MESHES_BY_GEOMETRY,
    case_catalog,
)

BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "b591a4c145d7139467281ab67d0b32fec68276e0"
CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_contract.json")
OUTPUT_ROOT = "qualification/0_2_9/wp12_external_vv_r3_6_diverse_raw"
MANIFEST_PATH = "qualification/0_2_9/wp12_external_vv_r3_6_diverse_manifest.json"
AUDIT_PATH = "qualification/0_2_9/wp12_external_vv_r3_6_diverse_audit.json"
R3_5_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_5_expanded_contract.json")
R3_5_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_5_expanded_audit.json")
R3_5_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_5_expanded_manifest.json")
IMAGE_ID = "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"

GATES = {
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
}


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


def _verify_r3_5_predecessor() -> dict[str, Any]:
    contract_path = ROOT / R3_5_CONTRACT
    audit_path = ROOT / R3_5_AUDIT
    manifest_path = ROOT / R3_5_MANIFEST
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if contract.get("revision") != "R3_5_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION":
        raise RuntimeError("R3.5 predecessor contract identity mismatch.")
    if audit.get("audit_status") != "PASS_WITH_LIMITATIONS" or audit.get("case_count") != 144 or audit.get("case_pass_count") != 144:
        raise RuntimeError("R3.5 predecessor is not the expected audited 144/144 package.")
    if audit.get("contract_sha256") != _sha256(R3_5_CONTRACT) or audit.get("manifest_sha256") != _sha256(R3_5_MANIFEST):
        raise RuntimeError("R3.5 predecessor contract/manifest digest mismatch.")
    if len(manifest.get("files", {})) < 100:
        raise RuntimeError("R3.5 predecessor manifest is unexpectedly incomplete.")
    return {
        "revision": contract["revision"],
        "contract_path": R3_5_CONTRACT.as_posix(),
        "contract_sha256": _sha256(R3_5_CONTRACT),
        "audit_path": R3_5_AUDIT.as_posix(),
        "audit_sha256": _sha256(R3_5_AUDIT),
        "audit_status": audit["audit_status"],
        "case_count": audit["case_count"],
        "case_pass_count": audit["case_pass_count"],
        "manifest_path": R3_5_MANIFEST.as_posix(),
        "manifest_sha256": _sha256(R3_5_MANIFEST),
        "historical_evidence_reused": False,
    }


def build_contract() -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Must freeze on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before contract freeze.")
    head = _git("rev-parse", "HEAD")
    if head != BASE_SHA and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False
    ).returncode != 0:
        raise RuntimeError("R3.6 branch does not descend from its reviewed preparation commit.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("R3.6 preparation changed production source.")
    if (ROOT / CONTRACT_PATH).exists() or (ROOT / MANIFEST_PATH).exists() or (ROOT / AUDIT_PATH).exists():
        raise RuntimeError("R3.6 contract or output evidence already exists; refusing overwrite.")

    predecessor = _verify_r3_5_predecessor()
    cases: list[dict[str, Any]] = []
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
    if len(cases) != 144 or len({row["case_id"] for row in cases}) != len(cases):
        raise RuntimeError("R3.6 case matrix must contain exactly 144 unique cases.")

    return {
        "work_package": "WP12",
        "revision": "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION",
        "status": "FROZEN",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "branch": BRANCH,
        "branch_base_sha": BASE_SHA,
        "freeze_commit_sha": head,
        "runner_sha": _source_commit("scripts/run_wp12_diverse_code_aster.py"),
        "model_builder_sha": _source_commit("scripts/wp12_diverse_models.py"),
        "auditor_sha": _source_commit("scripts/audit_wp12_expanded_code_aster.py"),
        "contract_builder_sha": _source_commit("scripts/freeze_wp12_diverse_contract.py"),
        "execution_authorized": True,
        "execution_authorization": {
            "basis": "Owner's active objective to substantially increase WP12 external correlations using more distinct models.",
            "scope": "Supplemental diagnostic R3.6 only: 144 sequential same-mesh small-strain linear-static QF Solver versus Code_Aster correlations; one CPU per fresh Code_Aster container; no ledger change, merge, push, or WP12 score allocation.",
        },
        "abort_on_execution_failure": True,
        "thresholds_frozen_before_execution": True,
        "post_result_threshold_retuning_allowed": False,
        "output_overwrite_allowed": False,
        "case_count": len(cases),
        "families": list(FAMILIES),
        "geometry_catalog_m": {name: list(values) for name, values in GEOMETRIES.items()},
        "mesh_catalog_cells_by_geometry": {
            geometry: {mesh: list(divisions) for mesh, divisions in meshes.items()}
            for geometry, meshes in MESHES_BY_GEOMETRY.items()
        },
        "load_catalog_resultants_N": {name: list(values) for name, values in LOADS.items()},
        "case_matrix_order": ["family", "geometry", "mesh", "load_case"],
        "material": dict(MATERIAL),
        "code_aster_version": "18.1.0",
        "code_aster_image": IMAGE,
        "code_aster_image_id": IMAGE_ID,
        "timeout_seconds": 900,
        "memory_limit_mb": 4096,
        "loading": {
            "definition": "uniform traction over the complete distal x=L face, integrated to consistent equivalent nodal forces for each element interpolation",
            "tetrahedral_face_integration": "T3 area/3 per corner; T6 area/3 per edge-midpoint with zero corner contribution for constant traction",
            "hexahedral_face_integration": "2D tensor Gauss integration of HEX8/HEX20 shape functions on xi=+1 face",
            "moment_reference": "global origin; uniform planar traction over the complete active distal cross-section",
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
        "gates": dict(GATES),
        "output_root": OUTPUT_ROOT,
        "manifest_path": MANIFEST_PATH,
        "audit_path": AUDIT_PATH,
        "raw_artifact_storage": "local ignored raw runs; versioned manifest, contract, compact summary and audit",
        "points_policy": {
            "official_points_changed": False,
            "candidate_points": "supplemental correlation evidence only; no automatic WP12 point allocation",
        },
        "fail_closed": True,
        "full_repository_test_suite": False,
        "cases": cases,
        "extends_campaign": predecessor,
        "limitations": [
            "bounded homogeneous isotropic 3D small-strain linear-static elasticity only",
            "only TET4, HEX8, TET10, and HEX20; no wedge, pyramid, shell, or beam element family",
            "three structured non-prismatic solid topologies: L-section, centered through-hole prism, and stepped cantilever",
            "H1/H2/H3 refine only the longitudinal axis within each topology; no isotropic or asymptotic mesh-convergence claim",
            "same discrete mesh, material, boundary conditions, and consistent nodal force vector are supplied to both solvers",
            "same-mesh FEM correlation is not experimental validation or an independent physical benchmark",
            "no stress-field comparison, material/geometric nonlinearity, contact, friction, dynamics, buckling, continuation, or MPI/PETSc claim",
            "R3.6 is supplemental and does not supersede R3.5, prior failure history, Owner decisions, WP12 points, or the global ledger",
        ],
    }


def main() -> int:
    if (ROOT / CONTRACT_PATH).exists():
        raise SystemExit(f"Refusing to overwrite existing contract: {CONTRACT_PATH}")
    contract = build_contract()
    target = ROOT / CONTRACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": contract["status"], "revision": contract["revision"], "case_count": contract["case_count"], "freeze_commit_sha": contract["freeze_commit_sha"], "contract_path": CONTRACT_PATH.as_posix()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
