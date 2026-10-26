"""Freeze the six non-authorized HEX8-SRI execution manifests.

This builder records source/controller identities and writes only preparation
artifacts. It never assembles a model, solves a system, or launches pytest.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PREPARATION = Path(__file__).resolve().parent
CAMPAIGN_ID = "HEX8-SRI-CANTILEVER-6-2026-10-26"
TEST_MODULE = "tests/verification/test_hex8_sri_structural_campaign.py"
CASES = (
    ("hex8_standard", 0.3, "hex8_standard_nu_0p3"),
    ("sri_historical", 0.3, "sri_historical_nu_0p3"),
    ("sri_corrected", 0.3, "sri_corrected_nu_0p3"),
    ("hex8_standard", 0.4999, "hex8_standard_nu_0p4999"),
    ("sri_historical", 0.4999, "sri_historical_nu_0p4999"),
    ("sri_corrected", 0.4999, "sri_corrected_nu_0p4999"),
)
NODEIDS = [
    f"{TEST_MODULE}::test_hex8_sri_cantilever_campaign[{case_id}]"
    for _, _, case_id in CASES
]
BUDGETS = {
    "timeout_seconds": 180,
    "rss_soft_limit_mib": 1024,
    "process_tree_limit": 8,
    "output_total_limit_mib": 16,
    "output_stream_limit_mib": 8,
    "temporary_limit_mib": 64,
    "archive_size_limit_mib": 64,
    "minimum_free_disk_mib": 1024,
    "blas_thread_environment": {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    },
    "attempts_per_nodeid": 1,
    "initial_campaign_max_attempts": 6,
    "blas_thread_environment": {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    },
    "budget_semantics": {
        "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
        "captured_output": "controller-enforced byte caps",
        "wall_timeout": "watchdog process-tree termination, best effort",
    },
}
FORMULATIONS = {
    "hex8_standard": {
        "element_type": "Hex8Element",
        "operator": "complete 2x2x2 Gauss integration",
        "source_note": "production HEX8 element, selected directly; registry not used",
    },
    "sri_historical": {
        "element_type": "HistoricalHex8SRIElement",
        "operator": "parent-source central volumetric expression without weight 8",
        "historical_source_commit": "2aa994f34900f39bef8df9db5fb025157fb694bb",
        "source_note": "research-only override; no production source or archive is changed",
    },
    "sri_corrected": {
        "element_type": "Hex8SRIElement",
        "operator": "corrected central volumetric integration with weight 8",
        "source_note": "research element called directly; registry not used",
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new_json(path: Path, value: dict[str, Any]) -> str:
    if path.exists():
        raise FileExistsError(f"refusing to replace frozen preparation artifact: {path}")
    payload = (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
    return sha256_bytes(payload)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def source_fingerprint(nodeid: str) -> str:
    path = ROOT / "scripts/development_autonomous.py"
    spec = importlib.util.spec_from_file_location("hex8_sri_final_manifest_controller", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the canonical controller fingerprint algorithm")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._worktree_source_fingerprint(ROOT, nodeid)


def source_inventory() -> dict[str, str]:
    names = [
        "src/solveur/elements/solid/hex8.py",
        "src/solveur/elements/solid/hex8_sri.py",
        "src/solveur/materials/solid.py",
        "experiments/hex8_sri_equilibrium/__init__.py",
        "experiments/hex8_sri_equilibrium/campaign.py",
        TEST_MODULE,
    ]
    return {name: sha256_bytes((ROOT / name).read_bytes()) for name in names}


def common_problem(source_head: str, fingerprint: str, controller: dict[str, str]) -> dict[str, Any]:
    nodal_loads = []
    for iy, wy in enumerate((0.25, 0.5, 0.25)):
        for iz, wz in enumerate((0.25, 0.5, 0.25)):
            node_id = 36 + iy * 3 + iz
            force_z = -wy * wz
            x, y, z = 20.0, 0.5 * iy, 0.5 * iz
            nodal_loads.append({
                "node_id": node_id,
                "coordinate_m": [x, y, z],
                "area_weight_m2": wy * wz,
                "force_N": [0.0, 0.0, force_z],
            })
    return {
        "schema": "qfsolver-hex8-sri-structural-common-input-v2",
        "campaign_id": CAMPAIGN_ID,
        "execution_authorized": False,
        "qualification": "DEVELOPMENT_ONLY_NOT_QUALIFICATION",
        "units": {"coordinates": "m", "E": "Pa", "traction": "Pa", "force": "N", "moment": "N·m", "displacement": "m", "strain": "dimensionless", "energy": "J", "time": "s", "memory": "bytes; MiB=bytes/2^20"},
        "source_identity": {
            "branch": "research/hex8-sri-equilibrium",
            "science_source_commit": source_head,
            "source_fingerprint_sha256": fingerprint,
            "source_files_sha256": source_inventory(),
        },
        "controller_code_sha256": controller,
        "model": {
            "geometry_dimensions_L_y_z_m": [20.0, 1.0, 1.0],
            "mesh_divisions_xyz": [4, 2, 2],
            "elements": 16,
            "nodes": 45,
            "degrees_of_freedom": 135,
            "fixed_dofs": list(range(27)),
            "free_dofs": list(range(27, 135)),
            "fixed_face": "x=0; UX, UY, UZ",
            "E_Pa": 1.0e6,
            "poisson_ratios": [0.3, 0.4999],
            "same_geometry_loads_supports_and_dof_order_for_all_cases": True,
        },
        "loading": {
            "loaded_face": "x=20",
            "traction_Pa": [0.0, 0.0, -1.0],
            "area_m2": 1.0,
            "nodal_loads": nodal_loads,
            "resultant_force_N": [0.0, 0.0, -1.0],
            "resultant_moment_about_origin_Nm": [-0.5, 20.0, 0.0],
        },
        "solver": {
            "scope": "test-local element stiffness assembly plus direct SciPy solve",
            "production_registry_used": False,
            "production_global_solver_used": False,
            "residual_failure_tolerance": 1.0e-7,
            "residual_definition": "||Kff uf-Ff||2/max(||Ff||2,||Kff uf||2,1 N)",
        },
        "observables_and_criteria": {
            "signed_mean_loaded_face_UZ_m": "consistent face-area-weighted average",
            "displacements_m": "full 135-vector and L2 norm",
            "strains": "16x8x6 Gauss-point values, dimensionless",
            "energy_J": "0.5*u^T*K*u; load work=u^T*F; report 2U-W without a new threshold",
            "residual_N": "free residual vector, L2 norm and frozen relative value",
            "reactions_and_closure": "27 support reactions; global force and origin-moment closures, no new threshold",
            "conditioning": "dense 108x108 Kff 2-norm condition number, no acceptance threshold",
            "validity_criteria": ["all outputs finite", "center and eight Gauss Jacobians positive", "existing relative residual <=1e-7"],
            "convergence": "not assessed from one mesh",
        },
        "budgets": BUDGETS,
        "artifact_root": "E:/QFSolverAgents/hex8sri-runs/HEX8-SRI-CANTILEVER-6-2026-10-26",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller-runner-sha256", required=True)
    parser.add_argument("--controller-plugin-sha256", required=True)
    args = parser.parse_args()
    if git("branch", "--show-current") != "research/hex8-sri-equilibrium":
        raise RuntimeError("manifests must be prepared on research/hex8-sri-equilibrium")
    status = git("status", "--porcelain", "--", "src/solveur", "experiments", "tests", "pyproject.toml", "pytest.ini")
    if status:
        raise RuntimeError(f"science source/test inventory must be committed and clean:\n{status}")
    source_head = git("rev-parse", "HEAD")
    fingerprint = source_fingerprint(NODEIDS[0])
    controller_hashes = {
        "runner": args.controller_runner_sha256,
        "pytest_plugin": args.controller_plugin_sha256,
    }
    output = PREPARATION / "final_candidates" / f"{source_head}_{args.controller_runner_sha256[:12]}_protocol2"
    output.mkdir(parents=True, exist_ok=False)
    common = common_problem(source_head, fingerprint, controller_hashes)
    common_sha = write_new_json(output / "common_problem.json", common)
    manifest_hashes: dict[str, str] = {}
    for formulation, nu, case_id in CASES:
        nodeid = f"{TEST_MODULE}::test_hex8_sri_cantilever_campaign[{case_id}]"
        manifest = {
            "schema": "qfsolver-hex8-sri-structural-case-v2",
            "campaign_id": CAMPAIGN_ID,
            "case_id": case_id,
            "execution_authorized": False,
            "execution_state": "PREPARATION_COMPLETE_AWAITING_SEPARATE_OWNER_EXECUTION_DECISION",
            "do_not_execute": True,
            "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
            "qualification_promotion": "PROHIBITED",
            "science_branch": "research/hex8-sri-equilibrium",
            "science_source_commit": source_head,
            "source_fingerprint_sha256": fingerprint,
            "source_files_sha256": source_inventory(),
            "controller_registration_id": "hex8sri",
            "controller_code_sha256": controller_hashes,
            "common_problem": {"path": "common_problem.json", "sha256": common_sha},
            "exact_nodeid": nodeid,
            "formulation": {"id": formulation, **FORMULATIONS[formulation]},
            "poisson_ratio": nu,
            "execution_artifact_root": common["artifact_root"],
            "attempt_number": 1,
            "retry_allowed": False,
            "budgets": BUDGETS,
        }
        manifest_name = f"manifest_{case_id}.json"
        manifest_hashes[manifest_name] = write_new_json(output / manifest_name, manifest)
    node_manifest_map = {
        nodeid: {
            "path": (output / f"manifest_{case_id}.json").relative_to(ROOT).as_posix(),
            "sha256": manifest_hashes[f"manifest_{case_id}.json"],
        }
        for (_, _, case_id), nodeid in zip(CASES, NODEIDS)
    }
    registration = {
        "schema": "qfsolver-hex8sri-controller-registration-v2",
        "status": "PREPARED_NOT_EXECUTION_AUTHORIZED",
        "execution_authorized": False,
        "science_source_commit": source_head,
        "science_source_fingerprint_sha256": fingerprint,
        "controller_registration_id": "hex8sri",
        "controller_manifest_map": node_manifest_map,
        "exact_nodeids": NODEIDS,
        "budgets": BUDGETS,
        "preflight": "required exact-node collect-only receipt; NOT_RUN under this Owner decision",
        "campaign_run_count": 0,
    }
    registration_sha = write_new_json(output / "registration.json", registration)
    print(json.dumps({
        "source_head": source_head,
        "source_fingerprint_sha256": fingerprint,
        "output_directory": str(output),
        "common_problem_sha256": common_sha,
        "manifest_sha256": manifest_hashes,
        "registration_sha256": registration_sha,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
