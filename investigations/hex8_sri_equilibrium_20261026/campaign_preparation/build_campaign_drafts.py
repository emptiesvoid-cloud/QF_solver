"""Build six non-executable HEX8-SRI structural campaign draft manifests.

This preparation script writes input/registration artifacts only. It never
assembles a matrix, solves a model, or launches pytest.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
SOURCE_PREP_COMMIT = "344bb385b905544e8d94df496c312d5904edb55f"
EXPECTED_SOURCE_FINGERPRINT = "60131a66dcafefd55c5b3300c505da3c3a495f2e79619c7006202e051919ef7f"
CAMPAIGN_ID = "HEX8-SRI-CANTILEVER-6-2026-10-26"
TEST_MODULE = "tests/verification/test_hex8_sri_structural_campaign.py"
FORMULATIONS = {
    "hex8_standard": {
        "element_type": "HEX8",
        "operator": "Hex8Element.stiffness",
        "legacy_or_corrected": "standard_full_integration",
    },
    "sri_historical": {
        "element_type": "HEX8SRI_HISTORICAL (proposed test-local alias)",
        "operator": "HistoricalHex8SRIElement.stiffness",
        "legacy_or_corrected": "frozen parent-source central formula without weight 8",
    },
    "sri_corrected": {
        "element_type": "HEX8SRI_CORRECTED (proposed test-local alias)",
        "operator": "Hex8SRIElement.stiffness",
        "legacy_or_corrected": "corrected central volumetric weight 8",
    },
}
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
SOURCE_FILES = (
    "src/solveur/elements/solid/hex8.py",
    "src/solveur/elements/solid/hex8_sri.py",
    "src/solveur/elements/solid/common.py",
    "src/solveur/materials/solid.py",
    "src/solveur/materials/factory.py",
    "src/solveur/core/model.py",
    "src/solveur/core/assembly/assembler.py",
    "src/solveur/core/audit.py",
    "src/solveur/core/solvers/static.py",
    "src/solveur/core/solvers/linear.py",
    "src/solveur/elements/registry.py",
    "src/solveur/loads/integration.py",
    "src/solveur/mesh/validation.py",
    "src/solveur/post/stress.py",
    TEST_MODULE,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def write_json(path: Path, data: dict[str, Any]) -> str:
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")
    return sha256_bytes(path.read_bytes())


def source_fingerprints() -> tuple[dict[str, dict[str, str]], str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for name in SOURCE_FILES:
        worktree_bytes = (ROOT / name).read_bytes()
        blob_bytes = git_bytes(SOURCE_PREP_COMMIT, name)
        hashes[name] = {
            "sha256_worktree_raw_bytes": sha256_bytes(worktree_bytes),
            "sha256_git_blob_bytes": sha256_bytes(blob_bytes),
        }

    spec = importlib.util.spec_from_file_location(
        "hex8_sri_development_autonomous", ROOT / "scripts/development_autonomous.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the development controller for fingerprinting")
    controller = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = controller
    spec.loader.exec_module(controller)
    source_fp = controller._worktree_source_fingerprint(ROOT, NODEIDS[0])
    if source_fp != EXPECTED_SOURCE_FINGERPRINT:
        raise RuntimeError(
            f"controller source fingerprint changed: expected {EXPECTED_SOURCE_FINGERPRINT}, got {source_fp}"
        )
    controller_hashes = {
        name: sha256_bytes((ROOT / name).read_bytes())
        for name in (
            "scripts/development_autonomous.py",
            "scripts/development_autonomous_pytest_plugin.py",
            "development_autonomous_policy.json",
        )
    }
    return hashes, source_fp, controller_hashes


def common_problem(source_hashes: dict[str, dict[str, str]], source_fp: str, controller_hashes: dict[str, str]) -> dict[str, Any]:
    end_face_nodes = []
    force_sum = [0.0, 0.0, 0.0]
    moment_sum = [0.0, 0.0, 0.0]
    for iy in range(3):
        for iz in range(3):
            y_weight = 0.25 if iy in (0, 2) else 0.5
            z_weight = 0.25 if iz in (0, 2) else 0.5
            area_weight = y_weight * z_weight
            node = ((4 * 3) + iy) * 3 + iz
            fz = -1.0 * area_weight  # t_z=-1 Pa over area 1 m².
            xyz = (20.0, 0.5 * iy, 0.5 * iz)
            moment = (xyz[1] * fz, -xyz[0] * fz, 0.0)
            end_face_nodes.append(
                {
                    "node_id": node,
                    "grid_index_iy_iz": [iy, iz],
                    "coordinate_m": list(xyz),
                    "area_weight": area_weight,
                    "force_N": [0.0, 0.0, fz],
                    "moment_about_origin_Nm": list(moment),
                }
            )
            force_sum[2] += fz
            for axis in range(3):
                moment_sum[axis] += moment[axis]

    if force_sum != [0.0, 0.0, -1.0] or moment_sum != [-0.5, 20.0, 0.0]:
        raise RuntimeError(f"load resultant/moment construction changed: {force_sum}, {moment_sum}")

    return {
        "schema": "qfsolver-hex8-sri-structural-common-input-v1",
        "campaign_id": CAMPAIGN_ID,
        "execution_state": "PREPARATION_ONLY_OWNER_AUTHORIZATION_PENDING",
        "execution_authorized": False,
        "source_freeze": {
            "commit": SOURCE_PREP_COMMIT,
            "branch": "research/hex8-sri-equilibrium",
            "source_fingerprint_sha256_controller_algorithm": source_fp,
            "selected_file_hashes": source_hashes,
            "controller_and_policy_raw_sha256": controller_hashes,
            "hash_scope_note": (
                "Controller fingerprint uses its _worktree_source_fingerprint algorithm over the current tracked source/test inventory; "
                "selected files separately record raw worktree-byte and Git-blob-byte SHA-256."
            ),
        },
        "units": {
            "system": "SI",
            "coordinates": "m",
            "young_modulus": "Pa",
            "traction": "Pa = N/m²",
            "force": "N",
            "moment": "N·m",
            "displacement": "m",
            "strain": "dimensionless",
            "stress": "Pa",
            "energy": "J",
            "time": "s",
            "memory": "bytes; report MiB as bytes / 2^20",
        },
        "geometry": {
            "shape": "regular straight cantilever block",
            "dimensions_L_by_y_by_z_m": [20.0, 1.0, 1.0],
            "mesh_divisions_x_y_z": [4, 2, 2],
            "element_count": 16,
            "node_count": 45,
            "coordinate_axes_m": {
                "x": [0.0, 5.0, 10.0, 15.0, 20.0],
                "y": [0.0, 0.5, 1.0],
                "z": [0.0, 0.5, 1.0],
            },
            "node_id_formula_zero_based": "((ix * 3) + iy) * 3 + iz; ix=0..4, iy=0..2, iz=0..2",
            "element_order": "ix outer, iy middle, iz inner; local nodes follow Hex8Element.node_signs",
            "local_connectivity_grid_offsets": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
            "expected_element_volume_m3": 1.25,
            "expected_detJ_at_center_and_eight_gauss_points_m3": 0.15625,
            "expected_total_volume_m3": 20.0,
        },
        "material_reference": {
            "model": "isotropic linear elastic SolidMaterial",
            "E_Pa": 1.0e6,
            "poisson_ratio_case_specific": True,
            "density": None,
            "density_note": "unused by linear static analysis",
            "same_reference_material_except_nu": True,
        },
        "boundary_conditions": {
            "type": "fully fixed x=0 face",
            "fixed_node_ids_zero_based": list(range(9)),
            "dof_order_per_node": ["UX", "UY", "UZ"],
            "fixed_global_dof_indices_zero_based": list(range(27)),
            "total_nodes_times_3_dofs": 135,
            "fixed_dof_count": 27,
            "free_global_dof_indices_zero_based": list(range(27, 135)),
            "free_dof_count": 108,
        },
        "loading": {
            "type": "uniform consistent surface traction on x=L",
            "traction_vector_Pa": [0.0, 0.0, -1.0],
            "loaded_surface_area_m2": 1.0,
            "loaded_node_count": 9,
            "nodal_loads": end_face_nodes,
            "resultant_force_N": force_sum,
            "resultant_moment_about_global_origin_Nm": moment_sum,
            "same_load_vector_for_all_six_cases": True,
        },
        "solver": {
            "analysis": "small-strain linear static",
            "method": "direct",
            "backend": "scipy",
            "residual_failure_tolerance": 1.0e-7,
            "relative_residual_definition": "||Kff uf - Ff||2 / max(||Ff||2, ||Kff uf||2, 1 N)",
            "no_threshold_changes": True,
        },
        "predeclared_observables": {
            "signed_mean_loaded_face_UZ_m": {
                "definition": "surface-area-weighted integral of UZ divided by 1 m²; weights equal the consistent traction weights",
            },
            "deformation": "save full nodal displacement vector and element strains at all eight Gauss points",
            "internal_energy_J": "0.5 * uᵀ K u",
            "external_load_work_J": "uᵀ F with the declared signed force vector",
            "energy_defect_J": "2 * internal_energy - external_load_work; also report normalized absolute defect using max(|work|, 1 J)",
            "free_residual_N": "Kff uf - Ff; save vector, L2 norm, and solver-relative norm",
            "support_reactions_N": "R = K u - F on the 27 fixed DOFs; save each value and total resultant",
            "force_closure_N": "sum of applied nodal forces plus support reactions, componentwise and L2",
            "force_closure_relative": "||ΣF + ΣR||2 / max(||ΣF||2, ||ΣR||2, 1 N)",
            "moment_closure_Nm": "sum x × (F + R) about the global origin (0,0,0), componentwise and L2",
            "moment_closure_relative": "||Σx×(F+R)||2 / max(||Σx×F||2, ||Σx×R||2, 1 N·m)",
            "condition_number": "2-norm condition number of dense 108x108 Kff; report algorithm and value, no acceptance threshold",
            "timing": "controller wall elapsed plus internal assembly, solve, postprocess, and total perf_counter intervals",
            "memory": "controller peak RSS observation and archived artifact bytes; RSS remains a soft sampled monitor",
        },
        "predeclared_interpretation": {
            "numerical_run_validity": [
                "all matrices, displacement, strain, energy, residual, and reaction values finite",
                "all center and Gauss-point Jacobian determinants positive",
                "direct solver's unchanged 1e-7 relative residual failure contract satisfied",
            ],
            "force_and_moment_closures": "report as observables; no new PASS threshold is invented for this exploratory comparison",
            "structural_response": "report paired signed displacement and energy differences against standard and historical controls",
            "locking": "treat as a local comparative signal at nu=0.4999, not as an independent proof from one mesh",
            "spatial_convergence": "not assessable from this single mesh; make no convergence claim",
            "criteria_freeze": "no thresholds or criteria may be adjusted after outputs are read",
        },
        "artifacts_to_preserve_per_case": [
            "manifest copy and its SHA-256",
            "global sparse K and reduced Kff in NPZ form",
            "16 local 24x24 stiffness matrices in NPY form",
            "node coordinates, connectivity, fixed/free DOF lists, and global F vector",
            "full u, residual, reactions, and 16x8x6 Gauss-point strain array",
            "solver/controller metadata, timings, resource observations, stdout/stderr",
        ],
        "proposed_case_budgets": {
            "wall_seconds_per_case": 180,
            "peak_rss_mib_soft": 1024,
            "process_tree_limit": 8,
            "captured_output_total_mib": 16,
            "captured_output_per_stream_mib": 8,
            "temporary_mib_sampled": 64,
            "archive_mib_sampled": 64,
            "minimum_free_disk_mib": 1024,
            "attempts_per_node_initial_campaign": 1,
            "six_case_total_max_attempts": 6,
            "blas_thread_environment": {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"},
            "budget_status": "proposed only; requires Owner acceptance and controller support",
        },
        "execution_artifact_root": f"{OUTPUT.as_posix()}/runs/{CAMPAIGN_ID}",
        "historical_sources": {
            "parent_source_commit": "2aa994f34900f39bef8df9db5fb025157fb694bb",
            "reproduction_location": TEST_MODULE,
            "reproduction_note": "test-local subclass overrides only volumetric_stiffness with the historical missing-weight expression; production Hex8SRIElement is not reverted or registered",
        },
    }


def main() -> None:
    source_paths = (
        "src/solveur",
        "tests",
        "experiments",
        "pyproject.toml",
        "pytest.ini",
        "scripts/development_autonomous.py",
        "scripts/development_autonomous_pytest_plugin.py",
        "development_autonomous_policy.json",
    )
    source_status = subprocess.check_output(
        ["git", "status", "--porcelain", "--", *source_paths], cwd=ROOT, text=True
    ).strip()
    if source_status:
        raise RuntimeError(f"frozen solver/test/controller source is dirty:\n{source_status}")
    source_hashes, source_fp, controller_hashes = source_fingerprints()
    common = common_problem(source_hashes, source_fp, controller_hashes)
    common_path = OUTPUT / "common_problem.json"
    common_hash = write_json(common_path, common)

    manifest_hashes: dict[str, str] = {}
    for formulation, nu, case_id in CASES:
        nodeid = NODEIDS[CASES.index((formulation, nu, case_id))]
        manifest = {
            "schema": "qfsolver-hex8-sri-structural-case-draft-v1",
            "campaign_id": CAMPAIGN_ID,
            "case_id": case_id,
            "execution_state": "OWNER_AUTHORIZATION_PENDING",
            "execution_authorized": False,
            "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
            "qualification_promotion": "PROHIBITED",
            "common_problem": {
                "path": common_path.name,
                "sha256": common_hash,
            },
            "exact_proposed_nodeid": nodeid,
            "nodeid_status": "collected_exact_node; currently skipped placeholder; not active in controller allowlist",
            "formulation": {"id": formulation, **FORMULATIONS[formulation]},
            "poisson_ratio": nu,
            "source_preparation_commit": SOURCE_PREP_COMMIT,
            "source_fingerprint_sha256_controller_algorithm": source_fp,
            "source_freeze_files": source_hashes,
            "controller_and_policy_sha256_raw_worktree_bytes": controller_hashes,
            "run_control": {
                "scope": "fem_exploratory",
                "proposed_worktree_id": "hex8sri",
                "policy_registration_active": False,
                "controller_compatibility": "BLOCKED: current controller only permits d01/c01/e01",
                "owner_decision_required": True,
                "attempt_number_if_authorized": 1,
                "no_automatic_or_manual_retry_in_this_six-case_batch": True,
            },
            "configuration": {
                "common_problem_sha256": common_hash,
                "formulation_specific_changes": "only element stiffness operator; all geometry, material E, nu case, load vector, supports, DOF order, direct solver, tolerance, and postprocess definitions are shared",
            },
            "proposed_budgets": common["proposed_case_budgets"],
            "do_not_execute": True,
        }
        path = OUTPUT / f"manifest_{case_id}.json"
        manifest_hashes[path.name] = write_json(path, manifest)

    plugin = "scripts/development_autonomous_pytest_plugin.py"
    policy = "development_autonomous_policy.json"
    controller_path = "scripts/development_autonomous.py"
    proposal = {
        "schema": "qfsolver-hex8-sri-controller-registration-proposal-v1",
        "campaign_id": CAMPAIGN_ID,
        "status": "DRAFT_NOT_ACTIVE_OWNER_DECISION_PENDING",
        "execution_authorized": False,
        "active_policy_or_controller_modified": False,
        "prepared_on_branch": "research/hex8-sri-equilibrium",
        "prepared_at_source_commit": SOURCE_PREP_COMMIT,
        "current_controller": {
            "path": controller_path,
            "sha256_raw_worktree_bytes": controller_hashes[controller_path],
            "policy_path": policy,
            "policy_sha256_raw_worktree_bytes": controller_hashes[policy],
            "pytest_plugin_path": plugin,
            "pytest_plugin_sha256_raw_worktree_bytes": controller_hashes[plugin],
            "worktree_ids_accepted_by_code": ["d01", "c01", "e01"],
            "policy_validator_requires_exact_keys": ["d01", "c01", "e01"],
            "worktree_identity_contract": "canonical root equals Git root; exact branch; baseline ancestry; source root contains src/solveur/__init__.py; target exists under fixed test root; exact target allowlist; source/import fingerprint captured before and after run",
            "preflight_contract": "the current preflight path is D01-specific; a new registration needs a matching owner-approved exact-node collect-only/preflight route",
            "decision": "this E:\\QFSolverAgents\\hex8-sri-research worktree is not currently compatible for FEM execution",
        },
        "controller_changes_required_after_approval": [
            "add a distinct hex8sri research worktree registration without changing D01/C01/E01 scopes or nodeids",
            "extend strict registry validation explicitly for this new Owner-approved mandate",
            "provide exact-node preflight/collection receipt for all six registered nodes",
            "allow one attempt per nodeid for this finite campaign and retain controller run artifacts",
            "include/verify manifest hashes and the historical-operator reproduction in the frozen source inventory",
            "keep development-only qualification status and prohibit qualification promotion",
        ],
        "proposed_registration": {
            "id": "hex8sri",
            "mode": "fem_exploratory",
            "root": str(ROOT),
            "git_root": str(ROOT),
            "branch": "research/hex8-sri-equilibrium",
            "baseline_commit": SOURCE_PREP_COMMIT,
            "source_root": "src",
            "pytest_root": "tests/verification",
            "require_clean_worktree": True,
            "allow_native_vv_skip_override": False,
            "attempt_limit_per_nodeid": 1,
            "allowed_nodeids": NODEIDS,
            "budgets": common["proposed_case_budgets"],
        },
        "common_problem": {"path": common_path.name, "sha256": common_hash},
        "six_case_manifests": manifest_hashes,
        "collected_nodeids": NODEIDS,
        "collect_only": {
            "command": "python -m pytest --collect-only -q tests/verification/test_hex8_sri_structural_campaign.py",
            "result": "6 exact nodes collected; no test body entered and no FEM performed",
        },
        "source_fingerprint_sha256_controller_algorithm": source_fp,
        "next_step": "Owner decides whether to approve controller/policy registration and an executable FEM harness; do not execute any node yet.",
    }
    proposal_path = OUTPUT / "registration_proposal.json"
    proposal_hash = write_json(proposal_path, proposal)
    print(json.dumps({
        "common_problem_sha256": common_hash,
        "manifest_sha256": manifest_hashes,
        "registration_proposal_sha256": proposal_hash,
        "source_fingerprint": source_fp,
        "source_commit": SOURCE_PREP_COMMIT,
    }, indent=2))


if __name__ == "__main__":
    main()
