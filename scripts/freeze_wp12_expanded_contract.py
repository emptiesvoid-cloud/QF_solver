"""Generate the immutable WP12 R3 expanded correlation contract.

The script refuses an existing contract and only freezes the checked-in case
matrix, never execution results. Run and commit its output before any solve.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scripts.wp12_expanded_models import (  # noqa: E402
    FAMILIES,
    GEOMETRIES,
    LOADS,
    MATERIAL,
    MESHES,
    case_catalog,
)

CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_expanded_contract.json")
OUTPUT_ROOT = "qualification/0_2_9/wp12_external_vv_r3_expanded_raw"
MANIFEST_PATH = "qualification/0_2_9/wp12_external_vv_r3_expanded_manifest.json"
BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "c5e842d5e589358633221ecd9f29c2ff1ef003aa"
IMAGE = "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"
IMAGE_ID = "sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _source_commit(path: str) -> str:
    return _git("log", "-1", "--format=%H", "--", path)


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
        "revision": "R3_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION",
        "status": "FROZEN",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "branch": BRANCH,
        "branch_base_sha": BASE_SHA,
        "freeze_commit_sha": head,
        "runner_sha": _source_commit("scripts/run_wp12_expanded_code_aster.py"),
        "model_builder_sha": _source_commit("scripts/wp12_expanded_models.py"),
        "auditor_sha": _source_commit("scripts/audit_wp12_expanded_code_aster.py"),
        "contract_builder_sha": _source_commit("scripts/freeze_wp12_expanded_contract.py"),
        "execution_authorized": True,
        "execution_authorization": {
            "basis": "Owner request to substantially increase external correlation coverage after acceptance of the WP12 R2 perimeter.",
            "scope": "144 sequential same-mesh QF Solver SciPy direct versus Code_Aster 18.1 serial linear-static correlations; one CPU per Code_Aster container; no nonlinear runs, no ledger change, no merge, no push.",
        },
        "case_count": len(cases),
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
        "limitations": [
            "bounded homogeneous isotropic 3D small-strain linear-static elasticity only",
            "only TET4, HEX8, TET10, and HEX20 are covered; no wedge, pyramid, shell, or beam family",
            "three simple rectangular block geometries, three low-to-moderate structured mesh sizes, and four prescribed distal-face traction directions",
            "mesh labels H1/H2/H3 define model diversity only; no mesh-convergence or asymptotic accuracy claim",
            "same discrete mesh, material, boundary conditions, and consistent nodal force vector are supplied to both solvers",
            "no stress-field comparison, material nonlinearity, geometric nonlinearity, contact, friction, dynamics, buckling, continuation, or MPI/PETSc claim",
            "correlation between two FEM implementations is not experimental validation",
            "this supplemental R3 campaign does not alter existing WP12 R2 results, Owner decisions, points, or global ledger",
        ],
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
