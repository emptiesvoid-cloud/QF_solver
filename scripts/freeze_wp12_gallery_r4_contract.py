"""Freeze the prospective WP12 R4 multi-topology/material correlation matrix."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_wp12_expanded_code_aster as auditor  # noqa: E402
from scripts import run_wp12_expanded_code_aster as engine  # noqa: E402
from scripts.wp12_gallery_models import FAMILIES, GEOMETRIES, MATERIALS, MESHES_BY_GEOMETRY, case_catalog, topology_summary  # noqa: E402
from scripts.run_wp12_gallery_r4 import BRANCH, EXPECTED_CASES, REVISION, _case_record  # noqa: E402


BASE_SHA = "3d01b1ad6be59b09377ac66cab7f327f62b3bdf5"
R3_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_contract.json")
R3_SUMMARY = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_summary.json")
R3_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_audit.json")
R3_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_manifest.json")
CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r4_gallery_contract.json")
OUTPUT_ROOT = Path("qualification/0_2_9/wp12_external_vv_r4_gallery_raw")
MANIFEST_PATH = Path("qualification/0_2_9/wp12_external_vv_r4_gallery_manifest.json")
AUDIT_PATH = Path("qualification/0_2_9/wp12_external_vv_r4_gallery_audit.json")
SUMMARY_PATH = Path("qualification/0_2_9/wp12_external_vv_r4_gallery_summary.json")
REPORT_PATH = Path("docs/verification/0_2_9/wp12-expanded-correlation-r4-gallery-results.md")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _verify_prior_campaign() -> dict[str, Any]:
    old_contract = engine.load_json(ROOT / R3_CONTRACT)
    old_summary = engine.load_json(ROOT / R3_SUMMARY)
    old_audit = engine.load_json(ROOT / R3_AUDIT)
    old_manifest = engine.load_json(ROOT / R3_MANIFEST)
    if (
        old_contract.get("case_count") != 144
        or old_summary.get("candidate_cases_passed") != 144
        or old_audit.get("audit_status") != "PASS_WITH_LIMITATIONS"
        or old_audit.get("case_pass_count") != 144
    ):
        raise RuntimeError("R3.6 prior campaign is not the complete 144/144 PASS_WITH_LIMITATIONS package.")
    raw_root = (ROOT / old_contract["output_root"]).resolve()
    if ROOT not in raw_root.parents or not raw_root.is_dir():
        raise RuntimeError("R3.6 raw evidence directory is absent or escapes the repository.")
    entries = old_manifest.get("files")
    actual = {
        path.relative_to(raw_root).as_posix()
        for path in raw_root.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    if not isinstance(entries, dict) or actual != set(entries):
        raise RuntimeError("R3.6 raw files do not exactly match the prior manifest.")
    for relative, record in entries.items():
        path = raw_root / relative
        if path.stat().st_size != record.get("size_bytes") or engine.sha256_file(path) != record.get("sha256"):
            raise RuntimeError(f"R3.6 raw hash mismatch before R4 freeze: {relative}")
    prior_audit = auditor.audit(ROOT / R3_CONTRACT, raw_root, ROOT)
    if prior_audit.get("audit_status") != "PASS_WITH_LIMITATIONS" or prior_audit.get("case_pass_count") != 144:
        raise RuntimeError("R3.6 independent raw evidence audit did not reproduce PASS.")
    return {
        "revision": old_contract["revision"],
        "case_count": 144,
        "contract_path": R3_CONTRACT.as_posix(),
        "contract_sha256": engine.sha256_file(ROOT / R3_CONTRACT),
        "summary_path": R3_SUMMARY.as_posix(),
        "summary_sha256": engine.sha256_file(ROOT / R3_SUMMARY),
        "audit_path": R3_AUDIT.as_posix(),
        "audit_sha256": engine.sha256_file(ROOT / R3_AUDIT),
        "manifest_path": R3_MANIFEST.as_posix(),
        "manifest_sha256": engine.sha256_file(ROOT / R3_MANIFEST),
        "manifested_raw_file_count": len(entries),
        "raw_bytes": sum(int(row["size_bytes"]) for row in entries.values()),
        "recomputed_audit_status": prior_audit["audit_status"],
        "historical_evidence_reused_as_r4_results": False,
    }


def build_contract() -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Must freeze on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before R4 contract freeze.")
    head = _git("rev-parse", "HEAD")
    if head != BASE_SHA and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False
    ).returncode:
        raise RuntimeError("R4 branch does not descend from the completed R3.6 campaign.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("R4 tooling branch unexpectedly changes production source.")
    for path in (CONTRACT_PATH, OUTPUT_ROOT, MANIFEST_PATH, AUDIT_PATH, SUMMARY_PATH, REPORT_PATH):
        if (ROOT / path).exists():
            raise RuntimeError(f"Refusing to overwrite R4 output: {path}")

    prior = _verify_prior_campaign()
    cases = [_case_record(case) for case in case_catalog()]
    if len(cases) != EXPECTED_CASES or len({record["case_id"] for record in cases}) != EXPECTED_CASES:
        raise RuntimeError("R4 generated catalog must contain exactly 864 unique models/cases.")

    old = engine.load_json(ROOT / R3_CONTRACT)
    source_paths = {
        "runner_sha": "scripts/run_wp12_gallery_r4.py",
        "model_builder_sha": "scripts/wp12_gallery_models.py",
        "auditor_sha": "scripts/audit_wp12_expanded_code_aster.py",
        "contract_builder_sha": "scripts/freeze_wp12_gallery_r4_contract.py",
    }
    contract = json.loads(json.dumps(old))
    contract.update(
        {
            "schema": "wp12-r4-gallery-correlation-contract-v1",
            "revision": REVISION,
            "status": "FROZEN",
            "branch": BRANCH,
            "branch_base_sha": BASE_SHA,
            "freeze_commit_sha": head,
            "frozen_utc": datetime.now(timezone.utc).isoformat(),
            "contract_builder_path": "scripts/freeze_wp12_gallery_r4_contract.py",
            **{field: _git("log", "-1", "--format=%H", "--", path) for field, path in source_paths.items()},
            "case_count": len(cases),
            "case_matrix_order": ["family", "geometry", "material_variant", "mesh", "load_case"],
            "cases": cases,
            "families": list(FAMILIES),
            "geometry_catalog_m": {name: list(dimensions) for name, dimensions in GEOMETRIES.items()},
            "geometry_cell_counts_cross_section": topology_summary(),
            "mesh_catalog_cells_by_geometry": {
                name: {mesh: list(divisions) for mesh, divisions in levels.items()}
                for name, levels in MESHES_BY_GEOMETRY.items()
            },
            "material_catalog": MATERIALS,
            "material_variants": list(MATERIALS),
            "material": MATERIALS["steel"],
            "load_catalog_resultants_N": old["load_catalog_resultants_N"],
            "extends_campaign": {
                **prior,
                "historical_raw_used_as_r4_results": False,
                "r4_cases_are_fresh_executions": True,
            },
            "case_count_breakdown": {
                "geometries": 6,
                "materials": 3,
                "element_families": 4,
                "meshes_per_geometry": 3,
                "loads_per_mesh": 4,
                "cases_per_geometry_material_pair": 48,
                "case_total": len(cases),
                "cumulative_with_r3_6": len(cases) + prior["case_count"],
            },
            "execution_authorization": {
                "basis": "User-approved continuation objective to substantially increase WP12 correlations across many different models.",
                "scope": "Supplemental R4 only: 864 fresh sequential same-mesh QF Solver versus Code_Aster linear-static correlations; one CPU per fresh container; no score allocation, ledger change, merge, or push.",
            },
            "execution_authorized": True,
            "abort_on_execution_failure": True,
            "output_overwrite_allowed": False,
            "post_result_threshold_retuning_allowed": False,
            "contract_path": CONTRACT_PATH.as_posix(),
            "output_root": OUTPUT_ROOT.as_posix(),
            "manifest_path": MANIFEST_PATH.as_posix(),
            "audit_path": AUDIT_PATH.as_posix(),
            "summary_path": SUMMARY_PATH.as_posix(),
            "report_path": REPORT_PATH.as_posix(),
            "raw_artifact_storage": "R4 raw case files are local Git-ignored artifacts; contract, manifest, independent audit, compact summary and Markdown report are versioned.",
            "points_policy": {
                "candidate_points": "supplemental evidence only; no automatic WP12 point allocation",
                "official_points_changed": False,
                "ledger_changed": False,
            },
            "limitations": [
                "homogeneous isotropic 3D small-strain linear-static elasticity only",
                "six extruded solid cross-section topologies: triangular prism, T-section, I-section, channel, box tube, and cruciform",
                "three elastic material parameter sets: steel, aluminum, and polymer; all isotropic and linear elastic",
                "element families limited to TET4, HEX8, TET10, and HEX20",
                "H1/H2/H3 refine only the longitudinal axis; no isotropic/asymptotic mesh-convergence claim",
                "same discrete mesh, material, boundary conditions, and equivalent nodal force vector are supplied to both solvers",
                "same-mesh solver correlation is not experimental validation or an independent physical benchmark",
                "no stress-field comparison, geometric/material nonlinearity, contact, friction, dynamics, buckling, continuation, or MPI/PETSc claim",
                "R4 supplements but does not supersede R3.5/R3.6, historical failures, Owner decisions, WP12 points, or the global ledger",
            ],
        }
    )
    # Preserve the exact solver/threshold/export contracts from R3.6.
    contract["gates"] = old["gates"]
    contract["external_solver"] = old["external_solver"]
    contract["code_aster_image"] = old["code_aster_image"]
    contract["code_aster_image_id"] = old["code_aster_image_id"]
    contract["code_aster_version"] = old["code_aster_version"]
    contract["memory_limit_mb"] = old["memory_limit_mb"]
    contract["timeout_seconds"] = old["timeout_seconds"]
    contract["boundary_condition"] = old["boundary_condition"]
    contract["loading"] = old["loading"]
    contract["qf_solver"] = old["qf_solver"]
    return contract


def main() -> int:
    if (ROOT / CONTRACT_PATH).exists():
        raise SystemExit(f"Refusing to overwrite frozen R4 contract: {CONTRACT_PATH}")
    contract = build_contract()
    target = ROOT / CONTRACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(
        {
            "status": contract["status"],
            "revision": contract["revision"],
            "case_count": contract["case_count"],
            "cumulative_case_count": contract["case_count_breakdown"]["cumulative_with_r3_6"],
            "freeze_commit_sha": contract["freeze_commit_sha"],
            "contract_path": CONTRACT_PATH.as_posix(),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
