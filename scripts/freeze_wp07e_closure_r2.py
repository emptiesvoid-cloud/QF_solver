"""Freeze a provenance-bound WP07-E closure contract without changing its gates."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
R1_PATH = ROOT / "qualification/0_2_9/wp07e_closure_contract.json"
R2_DIR = ROOT / "qualification/0_2_9/wp07e_closure_r2"
EXPECTED_R1_SHA256 = "36421eddc5b19dcac9245279bfb037953f370883f961e9a34e3f541df3b61b61"
EXPECTED_GOVERNING_SHA = "168e345b74f221fb1b975161faea841ca48d9c7c"
EXPECTED_D_SHA = "ed89446bb74d454ec40170a75c9252514ecc95e2"
EXPECTED_D_ANALYSIS_SHA256 = "1a81e261eec99e201b6266a41dd87a8f452880dab4105b9a940087ab9e8854ab"
EXPECTED_D_CONTRACT_SHA256 = "b923f560a0d6719ee149ea31f912f46b6b7d32600df1cd7b80bf70a40562d7d7"
EXPECTED_D_BINDING_SHA256 = "ef223ee40ed1d4d9b1c60a20c2ee2958ea4e37acd8c0265058a4a12218fcf52d"
EXPECTED_OWNER_D_SHA256 = "17837563364304d41ecb9ec4308f455d673f06bd533dc588f7f9daaf85b434dc"
POLICY_SHA256 = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"

FROZEN_CRITERIA = (
    "raw_evidence_schema",
    "track_separation",
    "refinement_policy",
    "equilibrium_policy",
    "active_set_closure",
    "penalty_closure",
    "identity_thresholds",
    "replay_policy",
    "reference_policy",
    "negative_case_policy",
    "decision_matrix",
    "point_policy",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_is_clean(root: Path, pathspec: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", pathspec],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git diff check failed: {result.stderr.strip()}")
    if result.returncode != 0:
        return False
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--", pathspec],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return not status


def _static_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return sorted(imports)


def _digest_contract(contract: dict[str, Any]) -> str:
    canonical = copy.deepcopy(contract)
    canonical["provenance_contract"]["expected_contract_digest"] = ""
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _artifact(path: Path, *, artifact_id: str, role: str, root: Path | None = None) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    record: dict[str, Any] = {
        "id": artifact_id,
        "role": role,
        "path": str(resolved).replace("\\", "/"),
        "sha256": _sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }
    if root is not None:
        record["relative_path"] = resolved.relative_to(root.resolve()).as_posix()
    return record


def freeze(d_source_root: Path, owner_acceptance_source: Path) -> tuple[Path, Path]:
    d_root = d_source_root.resolve(strict=True)
    owner_source = owner_acceptance_source.resolve(strict=True)
    if R2_DIR.exists():
        raise FileExistsError(f"Refusing to overwrite existing WP07-E R2 package: {R2_DIR}")
    if _git(ROOT, "rev-parse", "HEAD") != EXPECTED_GOVERNING_SHA:
        raise RuntimeError("WP07-E R2 must be frozen from the reviewed governing base SHA.")
    if _git(d_root, "rev-parse", "HEAD") != EXPECTED_D_SHA:
        raise RuntimeError("WP07-D evidence checkout is not at the accepted execution SHA.")
    if not _git_is_clean(d_root, "src"):
        raise RuntimeError("Tracked production source in the accepted WP07-D checkout is modified.")

    r1_bytes = R1_PATH.read_bytes()
    if hashlib.sha256(r1_bytes).hexdigest() != EXPECTED_R1_SHA256:
        raise RuntimeError("Historical WP07-E R1 contract hash differs; stop without rebinding.")
    r1 = json.loads(r1_bytes)
    analysis_path = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/analysis_final.json"
    d_contract_path = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/wp07d_formal_requalification_contract_r1.json"
    d_binding_path = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/wp07d_execution_binding_formal_rebind_r1.json"
    d_owner_path = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/owner_decision.json"
    analysis_sha = _sha256(analysis_path)
    if analysis_sha != EXPECTED_D_ANALYSIS_SHA256:
        raise RuntimeError("Accepted D R1 analysis hash mismatch.")
    if _sha256(d_contract_path) != EXPECTED_D_CONTRACT_SHA256:
        raise RuntimeError("Accepted D R1 contract hash mismatch.")
    if _sha256(d_binding_path) != EXPECTED_D_BINDING_SHA256:
        raise RuntimeError("Accepted D R1 binding hash mismatch.")

    owner_d = json.loads(owner_source.read_text(encoding="utf-8"))
    if _sha256(owner_source) != EXPECTED_OWNER_D_SHA256:
        raise RuntimeError("WP07-D Owner acceptance record hash mismatch.")
    if (
        owner_d.get("OWNER_ACCEPTS_WP07D_FORMAL_REQUALIFICATION") is not True
        or owner_d.get("OWNER_AWARDS_WP07D_POINTS") != "3/3"
        or owner_d.get("owner_review_status") != "PASS_REPLAY_VERIFIED"
    ):
        raise RuntimeError("The D Owner acceptance record does not award 3/3.")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if analysis.get("execution_sha") != EXPECTED_D_SHA or analysis.get("policy_digest") != POLICY_SHA256:
        raise RuntimeError("D R1 execution or policy provenance mismatch.")

    contract = copy.deepcopy(r1)
    contract.update(
        {
            "record_id": "QF-029-WP07-E-CLOSURE-R2-D-R1-BOUND",
            "revision": "R2_D_R1_EVIDENCE_BINDING",
            "status": "FROZEN_FOR_E_CLOSURE",
            "owner_status": "OWNER_AUTHORIZED_EXECUTION_PENDING_EVIDENCE",
            "owner_correction": "OWNER_EXECUTION_AUTHORIZATION_2026-09-17",
            "preparation_only": False,
            "qualification_campaign_executed": False,
            "source_sha": EXPECTED_GOVERNING_SHA,
            "formal_points": "0/2",
            "wp07_points": "8/10",
            "execution_policy_status": "BOUND_TO_ACCEPTED_WP07D_R1",
        }
    )
    contract.pop("validated_total", None)
    contract["global_ledger_status"] = "NOT_UPDATED; totals require separate reconciliation"
    contract["governing_source"] = {
        "branch": "0.2.9-unified-nonlinear",
        "sha": EXPECTED_GOVERNING_SHA,
        "policy_digest": POLICY_SHA256,
        "working_tree_at_base": "clean committed base; E package is built on an isolated branch",
    }
    contract["owner_execution_authorization"] = {
        "authorized": True,
        "authorization_scope": "WP07-E evidence closure; reuse accepted D R1; no D M1/M2/M3 rerun, no push/merge/ledger update",
        "authorization_date": "2026-09-17",
        "source_kind": "explicit user instruction in this conversation",
        "formal_owner_decision_sha": None,
        "note": "This records the later conversational authorization; the earlier D decision remains unchanged and still records E unauthorized at that time.",
    }
    contract["wp07d_dependency"] = {
        "owner_acceptance": "YES",
        "points": "3/3",
        "rerun": False,
        "authorized_base_sha": analysis["authorized_base_sha"],
        "execution_sha": EXPECTED_D_SHA,
        "analysis_path": str(analysis_path.resolve()).replace("\\", "/"),
        "analysis_sha256": analysis_sha,
        "formal_contract_path": str(d_contract_path.resolve()).replace("\\", "/"),
        "formal_contract_sha256": EXPECTED_D_CONTRACT_SHA256,
        "execution_binding_path": str(d_binding_path.resolve()).replace("\\", "/"),
        "execution_binding_sha256": EXPECTED_D_BINDING_SHA256,
        "owner_acceptance_source_path": str(owner_source).replace("\\", "/"),
        "owner_acceptance_sha256": EXPECTED_OWNER_D_SHA256,
        "policy_digest": POLICY_SHA256,
    }

    run_root = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/runs"
    run_dirs = [
        run_root / route / level / kind
        for route in ("ACTIVE_SET", "PENALTY")
        for level in ("M1", "M2", "M3")
        for kind in ("primary", "reference")
    ]
    run_dirs.extend((run_root / "ACTIVE_SET/M2/replay", run_root / "PENALTY/M1/replay"))
    d_artifacts: list[dict[str, Any]] = []
    root_files = (
        d_contract_path,
        d_binding_path,
        d_owner_path,
        analysis_path,
        d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/readiness.json",
        d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/replay_authorization_gate.json",
    )
    for path in root_files:
        d_artifacts.append(_artifact(path, artifact_id=f"D-R1:{path.name}", role="D_R1_CONTROL", root=d_root))
    authorization_root = d_root / "qualification/0_2_9/wp07d_formal_rebind_r1/authorizations"
    for path in sorted(authorization_root.rglob("*.json")):
        d_artifacts.append(_artifact(path, artifact_id=f"D-R1-AUTH:{path.relative_to(authorization_root).as_posix()}", role="D_R1_AUTHORIZATION", root=d_root))
    for run_dir in run_dirs:
        if not run_dir.is_dir():
            raise FileNotFoundError(f"Required D R1 run directory is missing: {run_dir}")
        for path in sorted(item for item in run_dir.iterdir() if item.is_file()):
            d_artifacts.append(_artifact(path, artifact_id=f"D-R1-RUN:{path.relative_to(run_root).as_posix()}", role="D_R1_RAW_RUN", root=d_root))

    independent_reference = d_root / "scripts/wp07d_independent_reference.py"
    reference_helpers = [
        d_root / "scripts/prepare_wp07d_structural_vnv.py",
        d_root / "scripts/wp07d_execution_binding.py",
    ]
    reference_import_audit = {
        path.name: _static_imports(path)
        for path in [independent_reference, *reference_helpers]
    }
    forbidden_imports = sorted(
        f"{filename}:{module}"
        for filename, modules in reference_import_audit.items()
        for module in modules
        if module == "solveur.contact"
        or module.startswith("solveur.contact.")
        or module == "solveur.core.analyses"
        or module.startswith("solveur.core.analyses.")
    )
    if forbidden_imports:
        raise RuntimeError(
            "The WP07-D reference source/import helpers import production contact or analysis code: "
            + ", ".join(forbidden_imports)
        )
    d_artifacts.append(_artifact(independent_reference, artifact_id="D-R1-INDEPENDENT-REFERENCE-SOURCE", role="INDEPENDENT_REFERENCE_SOURCE", root=d_root))
    for helper in reference_helpers:
        d_artifacts.append(_artifact(helper, artifact_id=f"D-R1-REFERENCE-HELPER:{helper.name}", role="INDEPENDENT_REFERENCE_HELPER_SOURCE", root=d_root))

    required_files: list[dict[str, Any]] = []
    for rel, identifier, role in (
        ("qualification/0_2_9/wp07a_contact_formulation_contract.json", "WP07-A-CONTRACT", "WP07_A_CONTRACT"),
        ("qualification/0_2_9/wp07b_contact_evaluation_restart.json", "WP07-B-CONTRACT", "WP07_B_CONTRACT"),
        ("qualification/0_2_9/wp07c_contact_identities.json", "WP07-C-CONTRACT", "WP07_C_CONTRACT"),
    ):
        required_files.append(_artifact(ROOT / rel, artifact_id=identifier, role=role, root=ROOT))
    required_files.append(_artifact(owner_source, artifact_id="WP07-D-OWNER-ACCEPTANCE", role="D_OWNER_ACCEPTANCE"))
    required_files.extend(d_artifacts)

    contract["required_evidence"] = {
        "description": "Every listed D R1 file is referenced at its real source path and hash-checked. No D data is relocated or rewritten.",
        "artifacts": required_files,
        "negative_case_artifacts": [
            {
                "case": item["case"],
                "expected_classifications": item["accepted_classifications"],
                "path": f"qualification/0_2_9/wp07e_closure_r2/negative_cases/{item['case']}.json",
                "role": "WP07E_NEGATIVE_CASE_RAW",
            }
            for item in contract["negative_case_policy"]
        ],
        "negative_case_manifest_path": "qualification/0_2_9/wp07e_closure_r2/negative_case_manifest.json",
        "d_r1_manifest_path": "qualification/0_2_9/wp07e_closure_r2/d_r1_evidence_manifest.json",
    }
    contract["governing_execution_policy"] = {
        "status": "BOUND_TO_ACCEPTED_WP07D_R1_BINDING_AND_POLICY_DIGEST",
        "expected": {
            "governing_policy_sha": POLICY_SHA256,
            "wp07d_execution_sha": EXPECTED_D_SHA,
            "formal_contract_sha256": EXPECTED_D_CONTRACT_SHA256,
            "execution_binding_sha256": EXPECTED_D_BINDING_SHA256,
        },
        "frozen_route_binding": json.loads(d_binding_path.read_text(encoding="utf-8"))["routes"],
        "source_artifact": str(d_binding_path.resolve()).replace("\\", "/"),
    }
    contract["independent_reference_source_audit"] = {
        "status": "PASS_STATIC_IMPORT_SCAN",
        "production_contact_or_analysis_imports": [],
        "scanned_sources": reference_import_audit,
        "scope_note": "Static source/import audit only; the frozen D R1 numerical reference artifacts remain the numerical reference evidence.",
    }
    contract["execution_policy_binding"] = {
        "status": "BOUND_TO_ACCEPTED_WP07D_R1",
        "governing_policy_sha": POLICY_SHA256,
        "wp07d_execution_sha": EXPECTED_D_SHA,
        "formal_contract_sha256": EXPECTED_D_CONTRACT_SHA256,
        "execution_binding_sha256": EXPECTED_D_BINDING_SHA256,
        "required_runtime_fields": ["governing_policy_sha", "wp07d_execution_sha", "contract_sha256", "binding_sha256"],
        "mismatch_policy": "FAIL_CLOSED",
        "physics_contract_unchanged": True,
    }
    contract["provenance_contract"].update(
        {
            "expected_contract_revision": "R2_D_R1_EVIDENCE_BINDING",
            "expected_contract_digest": "",
            "expected_integrated_source_sha": EXPECTED_D_SHA,
            "governing_source_sha": EXPECTED_GOVERNING_SHA,
            "d_execution_sha": EXPECTED_D_SHA,
            "contract_digest_convention": "SHA256 of canonical JSON with provenance_contract.expected_contract_digest set to the empty string; detached byte-level SHA256 is recorded in wp07e_closure_binding_r2.json.",
            "rebind_sha256": EXPECTED_R1_SHA256,
        }
    )
    contract["governance"] = {
        "structural_solves_run": False,
        "external_solver_run": False,
        "production_mechanics_changed": False,
        "contact_mechanics_changed": False,
        "maturity_changed": False,
        "official_points_awarded": False,
        "next_step": "Owner review after all hashes, D dependency gates and six raw negative-case records pass.",
    }
    contract["scope_and_limitations"] = [
        "Only the accepted frozen WP07-D R1 routes, meshes, observables and gates are reused.",
        "No broader contact qualification is implied.",
        "No updated-search or finite-sliding qualification.",
        "No D structural rerun is part of WP07-E closure unless a verified artifact discrepancy makes reuse invalid.",
        "D source SHA and current governing branch SHA are distinct and remain separately disclosed.",
        "WP07-E candidate points remain 0/2 until an explicit Owner decision.",
    ]

    # Assert that the formal rebind changed provenance/paths only, not qualification criteria.
    for field in FROZEN_CRITERIA:
        if contract[field] != r1[field]:
            raise RuntimeError(f"Frozen criterion section changed during R2 generation: {field}")
    contract_digest = _digest_contract(contract)
    contract["provenance_contract"]["expected_contract_digest"] = contract_digest

    R2_DIR.mkdir(parents=True, exist_ok=False)
    contract_path = R2_DIR / "wp07e_closure_contract_r2.json"
    contract_path.write_text(json.dumps(contract, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    binding = {
        "schema_version": 1,
        "record_id": "QF-029-WP07-E-CONTRACT-BINDING-R2-001",
        "contract_path": str(contract_path.resolve()).replace("\\", "/"),
        "contract_file_sha256": _sha256(contract_path),
        "contract_semantic_digest": contract_digest,
        "historical_r1_path": str(R1_PATH.resolve()).replace("\\", "/"),
        "historical_r1_sha256": EXPECTED_R1_SHA256,
        "governing_branch": "0.2.9-unified-nonlinear",
        "governing_source_sha": EXPECTED_GOVERNING_SHA,
        "wp07d_execution_sha": EXPECTED_D_SHA,
        "wp07d_analysis_sha256": analysis_sha,
        "policy_digest": POLICY_SHA256,
        "d_r1_artifact_count": len(d_artifacts),
        "d_r1_artifacts": d_artifacts,
        "criteria_unchanged": True,
        "criteria_sections": list(FROZEN_CRITERIA),
        "criteria_source_r1_sha256": EXPECTED_R1_SHA256,
        "official_wp07e_points_awarded": "0/2",
        "owner_e_authorization": contract["owner_execution_authorization"],
    }
    binding_path = R2_DIR / "wp07e_closure_binding_r2.json"
    binding_path.write_text(json.dumps(binding, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return contract_path, binding_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d-source-root", type=Path, required=True)
    parser.add_argument("--owner-acceptance-source", type=Path, required=True)
    args = parser.parse_args()
    contract, binding = freeze(args.d_source_root, args.owner_acceptance_source)
    print(f"CONTRACT={contract}")
    print(f"BINDING={binding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
