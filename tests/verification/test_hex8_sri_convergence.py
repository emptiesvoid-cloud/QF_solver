"""Twenty-four exact research nodes for the prepared HEX8-SRI convergence lot.

These nodes assemble and solve FEM systems. They are deliberately not covered
by the current six-node controller registration and must not be run until a
separate controller configuration and Owner decision bind their manifests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import time

import numpy as np
import pytest

from experiments.hex8_sri_equilibrium.campaign import atomic_write_json_new, atomic_write_new_bytes
from experiments.hex8_sri_equilibrium.convergence import (
    run_convergence_case,
)
from experiments.hex8_sri_equilibrium.campaign_spec import (
    FORMULATIONS,
    MESH_LEVELS,
    POISSON_RATIOS,
    convergence_case_id,
    convergence_nodeid,
)
from experiments.hex8_sri_equilibrium.criteria_contract import (
    FIRST6_NODEIDS,
    FROZEN_DISPOSITIONS,
    validate_frozen_case_criteria,
)


ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = ROOT / "investigations/hex8_sri_equilibrium_20261026/campaign_preparation/first_convergence_24"
CASE_PARAMETERS = tuple(
    pytest.param(
        formulation,
        nu,
        mesh,
        convergence_case_id(formulation, nu, mesh),
        id=convergence_nodeid(formulation, nu, mesh).split("[", maxsplit=1)[1][:-1],
    )
    for formulation in FORMULATIONS
    for nu in POISSON_RATIOS
    for mesh in MESH_LEVELS
)

EXECUTION_CONTRACT_MARKER = "QF-HEX8SRI-EXECUTION-CONTRACT: hex8sri-convergence24-v2"
CRITERIA_CONTRACT_STRINGS = (
    "criteria_contract",
    "criteria_freeze",
    "CASE_GATE",
    "CASE_DIAGNOSTIC",
    "CAMPAIGN_GATE_DEFERRED",
    "NOT_ASSESSED",
    "negative_mean_loaded_face_uz",
)
EXECUTION_SCOPE_ID = "hex8sri-convergence24"
CAMPAIGN_ID = "HEX8-SRI-CONVERGENCE-24-2026-10-27"
DEVELOPMENT_MANDATE_ID = "DEVELOPMENT_AUTONOMOUS-HEX8SRI-CONVERGENCE24-2026-10-27-v1"
GATE_ENVIRONMENT_CONTRACT = (
    "QF_DEV_EXECUTION_MANIFEST_PATH",
    "QF_DEV_EXECUTION_MANIFEST_SHA256",
    "QF_DEV_OWNER_DECISION_ID",
    "QF_DEV_CASE_MANIFEST_PATH",
    "QF_DEV_PREFLIGHT_ID",
    "QF_DEV_PREFLIGHT_SHA256",
    "QF_DEV_TARGET_NODEID",
    "QF_DEV_CONTROLLER_ROOT",
    "QF_DEV_CONTROLLER_BRANCH",
    "QF_DEV_CONTROLLER_HEAD",
    "QF_DEV_CONTROLLER_RUNNER_SHA256",
    "QF_DEV_CONTROLLER_POLICY_SHA256",
    "QF_DEV_CONTROLLER_PLUGIN_SHA256",
    EXECUTION_SCOPE_ID,
    "OWNER_AUTHORIZED",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_registration_sha256(manifest: dict) -> str:
    controller_fields = {"controller_code_sha256", "controller_identity", "controller_identity_status"}
    content = {key: value for key, value in manifest.items() if key not in controller_fields}
    payload = json.dumps(content, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _strict_json_object(path: Path, label: str) -> dict:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"HEX8-SRI refused: {label} is unreadable or ambiguous: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"HEX8-SRI refused: {label} must be a JSON object")
    return payload


def _source_fingerprint(nodeid: str) -> str:
    """Mirror the controller's stable inventory hash for an independent source check."""
    target_module = nodeid.split("::", maxsplit=1)[0]
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if listed.returncode != 0:
        raise RuntimeError("HEX8-SRI refused: cannot inventory the source files")
    files: set[str] = set()
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(os.fsdecode(raw).replace("\\", "/"))
        relative_text = relative.as_posix()
        if (
            relative_text.startswith("src/solveur/")
            and relative.suffix == ".py"
            or relative_text.startswith("experiments/")
            and relative.suffix == ".py"
            or relative_text == target_module
            or relative_text in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            files.add(relative_text)
    if target_module not in files:
        raise RuntimeError("HEX8-SRI refused: exact test module is absent from the source inventory")
    digest = hashlib.sha256()
    for relative_text in sorted(files):
        path = (ROOT / Path(relative_text)).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise RuntimeError(f"HEX8-SRI refused: source path escapes the science worktree: {relative_text}") from exc
        if not path.is_file():
            raise RuntimeError(f"HEX8-SRI refused: source file is missing: {relative_text}")
        digest.update(relative_text.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"HEX8-SRI refused: required controller field {name} is missing")
    return value


def _same_path(left: str, right: str) -> bool:
    return Path(left).resolve() == Path(right).resolve()


def _authorized_case(request: pytest.FixtureRequest, case_id: str) -> dict:
    """Validate the exact Owner manifest, case manifest, preflight and controller before assembly."""
    contract_marker = "QF-HEX8SRI-EXECUTION-CONTRACT: hex8sri-convergence24-v2"
    if contract_marker != EXECUTION_CONTRACT_MARKER:
        raise RuntimeError("HEX8-SRI refused: execution contract marker mismatch")

    nodeid = request.node.nodeid
    scope_id = "hex8sri-convergence24"
    expected_environment = {
        "QF_DEVELOPMENT_AUTONOMOUS": "1",
        "QF_DEV_WORKTREE_ID": scope_id,
        "QF_DEV_CAMPAIGN_SCOPE_ID": scope_id,
        "QF_DEV_TARGET_NODEID": nodeid,
    }
    mismatches = {
        name: (os.environ.get(name), expected)
        for name, expected in expected_environment.items()
        if os.environ.get(name) != expected
    }
    if mismatches:
        raise RuntimeError(f"HEX8-SRI refused before assembly: scope or node identity mismatch {mismatches}")

    # The merged controller currently emits QF_DEV_MANIFEST_PATH/SHA256; accept the
    # explicit execution-manifest aliases as well, and reject disagreement if both exist.
    execution_path_value = os.environ.get("QF_DEV_EXECUTION_MANIFEST_PATH")
    controller_path_value = os.environ.get("QF_DEV_MANIFEST_PATH")
    execution_sha_value = os.environ.get("QF_DEV_EXECUTION_MANIFEST_SHA256")
    controller_sha_value = os.environ.get("QF_DEV_MANIFEST_SHA256")
    if execution_path_value and controller_path_value and not _same_path(execution_path_value, controller_path_value):
        raise RuntimeError("HEX8-SRI refused: execution-manifest path aliases disagree")
    if execution_sha_value and controller_sha_value and execution_sha_value != controller_sha_value:
        raise RuntimeError("HEX8-SRI refused: execution-manifest hash aliases disagree")
    execution_path_value = execution_path_value or controller_path_value
    execution_sha_value = execution_sha_value or controller_sha_value
    if not execution_path_value or not execution_sha_value:
        raise RuntimeError("HEX8-SRI refused: execution-manifest path or hash is missing")

    execution_manifest_path = Path(execution_path_value).resolve(strict=True)
    if (
        execution_manifest_path.parent.name != scope_id
        or execution_manifest_path.parent.parent.name != "authorizations"
    ):
        raise RuntimeError("HEX8-SRI refused: execution manifest is outside the dedicated scope directory")
    execution_manifest_sha256 = _sha256(execution_manifest_path)
    if execution_manifest_sha256 != execution_sha_value:
        raise RuntimeError("HEX8-SRI refused: execution-manifest SHA-256 mismatch")
    execution_manifest = _strict_json_object(execution_manifest_path, "execution manifest")
    authorization_id = _required_environment("QF_DEV_AUTHORIZATION_ID")
    if (
        execution_manifest.get("schema") != "qfsolver-hex8sri-convergence24-execution-v1"
        or execution_manifest.get("state") != "OWNER_AUTHORIZED"
        or execution_manifest.get("execution_authorized") is not True
        or execution_manifest.get("do_not_execute") is not False
        or execution_manifest.get("worktree_id") != scope_id
        or execution_manifest.get("mandate_id") != DEVELOPMENT_MANDATE_ID
        or execution_manifest.get("campaign_id") != CAMPAIGN_ID
        or execution_manifest.get("target") != nodeid
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", authorization_id)
        or execution_manifest.get("authorization_id") != authorization_id
        or execution_manifest_path.name != f"{authorization_id}.json"
    ):
        raise RuntimeError("HEX8-SRI refused: execution manifest does not authorize this exact case")
    source_identity = execution_manifest.get("identity")
    if not isinstance(source_identity, dict):
        raise RuntimeError("HEX8-SRI refused: execution manifest has no scientific worktree identity")

    case_manifest_path = Path(_required_environment("QF_DEV_CASE_MANIFEST_PATH")).resolve(strict=True)
    try:
        CAMPAIGN_DIR.resolve().relative_to(ROOT.resolve())
        case_manifest_path.relative_to(CAMPAIGN_DIR.resolve())
    except ValueError as exc:
        raise RuntimeError("HEX8-SRI refused: case manifest escapes the campaign directory") from exc
    if case_manifest_path.name != f"manifest_{case_id}.json":
        raise RuntimeError("HEX8-SRI refused: case manifest filename does not match the exact case")
    case_manifest_sha256 = _sha256(case_manifest_path)
    if case_manifest_sha256 != _required_environment("QF_DEV_CASE_MANIFEST_SHA256"):
        raise RuntimeError("HEX8-SRI refused: case-manifest SHA-256 mismatch")
    case_manifest = _strict_json_object(case_manifest_path, "case manifest")
    case_binding = execution_manifest.get("case_manifest")
    if (
        not isinstance(case_binding, dict)
        or not _same_path(str(case_binding.get("path", "")), str(case_manifest_path))
        or case_binding.get("sha256") != case_manifest_sha256
        or case_binding.get("case_id") != case_id
        or case_binding.get("scope_id") != scope_id
        or case_manifest.get("case_id") != case_id
        or case_manifest.get("exact_nodeid") != nodeid
        or case_manifest.get("controller_campaign_scope_id") != scope_id
        or case_manifest.get("campaign_id") != CAMPAIGN_ID
        or case_manifest.get("execution_state") != "PREPARED_NOT_AUTHORIZED"
        or case_manifest.get("execution_authorized") is not False
        or case_manifest.get("do_not_execute") is not True
    ):
        raise RuntimeError("HEX8-SRI refused: case-manifest identity or preparation state mismatch")

    fingerprint = _source_fingerprint(nodeid)
    if (
        execution_manifest.get("source_fingerprint") != fingerprint
        or case_manifest.get("source_fingerprint_sha256") != fingerprint
    ):
        raise RuntimeError("HEX8-SRI refused: source fingerprint differs from both manifests")
    if (
        source_identity.get("root") != str(ROOT.resolve())
        or source_identity.get("branch") != _git("branch", "--show-current")
        or source_identity.get("head") != _git("rev-parse", "HEAD")
        or source_identity.get("tree") != _git("rev-parse", "HEAD^{tree}")
    ):
        raise RuntimeError("HEX8-SRI refused: frozen science worktree identity mismatch")
    if source_identity.get("branch") != "research/hex8-sri-equilibrium":
        raise RuntimeError("HEX8-SRI refused: science branch is outside the registered research branch")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", str(case_manifest.get("science_source_commit", "")), "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError("HEX8-SRI refused: registered case source commit is not an ancestor of the frozen worktree")

    controller_provenance = execution_manifest.get("controller_provenance")
    if not isinstance(controller_provenance, dict):
        raise RuntimeError("HEX8-SRI refused: controller provenance is missing")
    controller_identity = controller_provenance.get("identity", {})
    controller_hashes = controller_provenance.get("sha256", {})
    if not isinstance(controller_identity, dict) or not isinstance(controller_hashes, dict):
        raise RuntimeError("HEX8-SRI refused: controller provenance has an invalid shape")
    controller_fingerprint = hashlib.sha256(
        json.dumps(controller_provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if execution_manifest.get("controller_fingerprint") != controller_fingerprint:
        raise RuntimeError("HEX8-SRI refused: controller provenance fingerprint mismatch")
    expected_controller_environment = {
        "QF_DEV_CONTROLLER_ROOT": controller_identity.get("root"),
        "QF_DEV_CONTROLLER_BRANCH": controller_identity.get("branch"),
        "QF_DEV_CONTROLLER_HEAD": controller_identity.get("head"),
        "QF_DEV_CONTROLLER_TREE": controller_identity.get("tree"),
        "QF_DEV_CONTROLLER_RUNNER_SHA256": controller_hashes.get("runner"),
        "QF_DEV_CONTROLLER_POLICY_SHA256": controller_hashes.get("policy"),
        "QF_DEV_CONTROLLER_PLUGIN_SHA256": controller_hashes.get("pytest_plugin"),
    }
    if any(
        name not in os.environ
        or not isinstance(expected, str)
        or (not expected and name != "QF_DEV_CONTROLLER_BRANCH")
        or os.environ[name] != expected
        for name, expected in expected_controller_environment.items()
    ):
        raise RuntimeError("HEX8-SRI refused: runtime controller identity differs from the Owner manifest")
    controller_root = Path(controller_identity["root"]).resolve(strict=True)

    def controller_git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=controller_root, text=True).strip()

    if (
        Path(controller_git("rev-parse", "--show-toplevel")).resolve() != controller_root
        or controller_git("branch", "--show-current") != controller_identity["branch"]
        or controller_git("rev-parse", "HEAD") != controller_identity["head"]
        or controller_git("rev-parse", "HEAD^{tree}") != controller_identity["tree"]
        or controller_git("status", "--porcelain", "--untracked-files=all")
        or controller_identity.get("status_short") != ""
    ):
        raise RuntimeError("HEX8-SRI refused: controller worktree Git identity differs from its provenance")
    for key, relative in {
        "runner": "scripts/development_autonomous.py",
        "policy": "development_autonomous_policy.json",
        "pytest_plugin": "scripts/development_autonomous_pytest_plugin.py",
    }.items():
        controller_file = (controller_root / relative).resolve(strict=True)
        if not controller_file.is_relative_to(controller_root) or _sha256(controller_file) != controller_hashes.get(
            key
        ):
            raise RuntimeError(f"HEX8-SRI refused: controller {key} hash mismatch")
    controller_policy = _strict_json_object(controller_root / "development_autonomous_policy.json", "controller policy")
    run_store = controller_policy.get("run_store")
    if (
        not isinstance(run_store, str)
        or not run_store
        or Path(run_store).is_absolute()
        or ".." in Path(run_store).parts
    ):
        raise RuntimeError("HEX8-SRI refused: controller run store is invalid")
    store = (controller_root / run_store).resolve()
    if (
        not store.is_relative_to(controller_root)
        or not execution_manifest_path.parent.is_relative_to(store)
        or execution_manifest_path.parent != (store / "authorizations" / scope_id).resolve()
    ):
        raise RuntimeError("HEX8-SRI refused: execution manifest is outside the controller authorization root")
    case_controller = case_manifest.get("controller_identity", {})
    case_controller_hashes = case_manifest.get("controller_code_sha256", {})
    if (
        case_manifest.get("controller_identity_status") != "FINAL_CONTROLLER_IDENTITY_BOUND"
        or case_controller.get("branch") != controller_identity.get("branch")
        or case_controller.get("head") != controller_identity.get("head")
        or case_controller_hashes.get("runner") != controller_hashes.get("runner")
        or case_controller_hashes.get("policy") != controller_hashes.get("policy")
        or case_controller_hashes.get("pytest_plugin") != controller_hashes.get("pytest_plugin")
    ):
        raise RuntimeError("HEX8-SRI refused: case manifest is not bound to the final controller identity")

    owner_decision_id = _required_environment("QF_DEV_OWNER_DECISION_ID")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", owner_decision_id):
        raise RuntimeError("HEX8-SRI refused: Owner decision ID is invalid")
    decision_reference = execution_manifest.get("owner_decision_record")
    if not isinstance(decision_reference, dict):
        raise RuntimeError("HEX8-SRI refused: separately archived Owner decision reference is missing")
    decision_path = Path(str(decision_reference.get("path", ""))).resolve(strict=True)
    if (
        not decision_path.is_relative_to(execution_manifest_path.parent)
        or decision_path.name != f"{owner_decision_id}.json"
        or decision_path
        != (execution_manifest_path.parent / "owner-decisions" / "execution" / f"{owner_decision_id}.json").resolve()
    ):
        raise RuntimeError("HEX8-SRI refused: Owner decision record is outside its dedicated scope")
    if _sha256(decision_path) != decision_reference.get("sha256"):
        raise RuntimeError("HEX8-SRI refused: Owner decision record SHA-256 mismatch")
    owner_decision = _strict_json_object(decision_path, "Owner decision record")
    if (
        owner_decision != execution_manifest.get("owner_decision")
        or owner_decision.get("schema") != "qfsolver-hex8sri-execution-approval-v1"
        or owner_decision.get("decision_type") != "EXECUTION_APPROVED"
        or owner_decision.get("execution_authorized") is not True
        or owner_decision.get("do_not_execute") is not False
        or owner_decision.get("decision_id") != owner_decision_id
        or owner_decision.get("status") != "APPROVED"
        or owner_decision.get("approved_by") != "Owner"
        or owner_decision.get("scope_id") != scope_id
        or owner_decision.get("mandate_id") != DEVELOPMENT_MANDATE_ID
        or owner_decision.get("campaign_id") != CAMPAIGN_ID
        or owner_decision.get("source_fingerprint") != fingerprint
        or owner_decision.get("controller_fingerprint") != execution_manifest.get("controller_fingerprint")
        or owner_decision.get("controller_head") != controller_identity.get("head")
        or owner_decision.get("authorized_nodeids") != list(FIRST6_NODEIDS)
        or set(owner_decision.get("case_manifests_by_nodeid", {})) != set(FIRST6_NODEIDS)
        or owner_decision.get("case_manifests_by_nodeid", {}).get(nodeid) != case_binding
        or set(owner_decision.get("limits_by_nodeid", {})) != set(FIRST6_NODEIDS)
        or owner_decision.get("limits_by_nodeid", {}).get(nodeid) != execution_manifest.get("limits")
    ):
        raise RuntimeError("HEX8-SRI refused: Owner decision does not authorize this exact identity and case")
    try:
        approved_at = datetime.fromisoformat(owner_decision["approved_at_utc"].replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(owner_decision["expires_at_utc"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if (
            approved_at.utcoffset() != timezone.utc.utcoffset(approved_at)
            or expires_at.utcoffset() != timezone.utc.utcoffset(expires_at)
            or approved_at > now
            or expires_at <= now
            or expires_at <= approved_at
        ):
            raise ValueError("invalid approval interval")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError("HEX8-SRI refused: Owner execution approval is expired or has invalid dates") from exc
    freeze_ref = owner_decision.get("criteria_freeze_record")
    if not isinstance(freeze_ref, dict) or set(freeze_ref) != {"decision_id", "path", "sha256"}:
        raise RuntimeError("HEX8-SRI refused: distinct criteria freeze reference is missing")
    freeze_id = freeze_ref["decision_id"]
    if not isinstance(freeze_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", freeze_id):
        raise RuntimeError("HEX8-SRI refused: criteria freeze ID is invalid")
    freeze_path = Path(str(freeze_ref["path"])).resolve(strict=True)
    if (
        not freeze_path.is_relative_to(execution_manifest_path.parent)
        or freeze_path.name != f"{freeze_id}.json"
        or freeze_path
        != (execution_manifest_path.parent / "owner-decisions" / "criteria-freeze" / f"{freeze_id}.json").resolve()
        or _sha256(freeze_path) != freeze_ref["sha256"]
    ):
        raise RuntimeError("HEX8-SRI refused: criteria freeze path or hash mismatch")
    freeze_decision = _strict_json_object(freeze_path, "criteria freeze decision")
    if (
        freeze_decision.get("schema") != "qfsolver-hex8sri-criteria-freeze-decision-v1"
        or freeze_decision.get("decision_type") != "CRITERIA_FREEZE_ONLY"
        or freeze_decision.get("status") != "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED"
        or freeze_decision.get("execution_authorized") is not False
        or freeze_decision.get("do_not_execute") is not True
        or freeze_decision.get("approved_by") != "Owner"
        or freeze_decision.get("decision_id") != freeze_id
        or freeze_decision.get("scope_id") != scope_id
        or freeze_decision.get("mandate_id") != DEVELOPMENT_MANDATE_ID
        or freeze_decision.get("campaign_id") != CAMPAIGN_ID
        or freeze_decision.get("source_fingerprint") != fingerprint
        or freeze_decision.get("controller_fingerprint") != execution_manifest.get("controller_fingerprint")
        or freeze_decision.get("controller_head") != controller_identity.get("head")
        or freeze_decision.get("frozen_nodeids") != list(FIRST6_NODEIDS)
        or freeze_decision.get("criteria_freeze") != owner_decision.get("criteria_freeze")
    ):
        raise RuntimeError("HEX8-SRI refused: archived criteria freeze differs from the execution decision")
    try:
        freeze_at = datetime.fromisoformat(freeze_decision["approved_at_utc"].replace("Z", "+00:00"))
        if freeze_at.utcoffset() != timezone.utc.utcoffset(freeze_at) or freeze_at > approved_at:
            raise ValueError("invalid freeze time")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError("HEX8-SRI refused: criteria freeze time is invalid") from exc
    try:
        case_registration_sha256 = _manifest_registration_sha256(case_manifest)
        if case_binding.get("registration_sha256") != case_registration_sha256:
            raise ValueError("case manifest registration digest differs from its Owner binding")
        frozen_criteria = validate_frozen_case_criteria(
            case_manifest,
            owner_decision,
            target=nodeid,
            case_registration_sha256=case_registration_sha256,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"HEX8-SRI refused: Owner criteria freeze is invalid: {exc}") from exc
    criteria_freeze = owner_decision.get("criteria_freeze")
    if not isinstance(criteria_freeze, dict) or set(criteria_freeze["dispositions"]) != set(FROZEN_DISPOSITIONS):
        raise RuntimeError("HEX8-SRI refused: Owner criteria classifications are incomplete")

    preflight_id = _required_environment("QF_DEV_PREFLIGHT_ID")
    if not re.fullmatch(r"pf-[0-9a-f]{12}", preflight_id):
        raise RuntimeError("HEX8-SRI refused: preflight ID is invalid")
    preflight_sha256 = _required_environment("QF_DEV_PREFLIGHT_SHA256")
    preflight = execution_manifest.get("preflight")
    if (
        not isinstance(preflight, dict)
        or preflight.get("preflight_id") != preflight_id
        or preflight.get("receipt_sha256") != preflight_sha256
    ):
        raise RuntimeError("HEX8-SRI refused: preflight identity differs from the execution manifest")
    preflight_path = Path(str(preflight.get("receipt_path", ""))).resolve(strict=True)
    expected_preflight_path = (store / "worktrees" / scope_id / "preflight" / preflight_id / "preflight.json").resolve()
    if not preflight_path.is_relative_to(store) or preflight_path != expected_preflight_path:
        raise RuntimeError("HEX8-SRI refused: preflight receipt escapes its registered location")
    if _sha256(preflight_path) != preflight_sha256:
        raise RuntimeError("HEX8-SRI refused: preflight receipt SHA-256 mismatch")
    sidecar_path = (preflight_path.parent / "preflight.sha256.json").resolve(strict=True)
    if not sidecar_path.is_relative_to(preflight_path.parent):
        raise RuntimeError("HEX8-SRI refused: preflight checksum escapes its receipt directory")
    preflight_sidecar = _strict_json_object(sidecar_path, "preflight checksum")
    if preflight_sidecar.get("sha256") != preflight_sha256:
        raise RuntimeError("HEX8-SRI refused: preflight checksum sidecar mismatch")
    preflight_receipt = _strict_json_object(preflight_path, "preflight receipt")
    if (
        preflight_receipt.get("state") != "PREFLIGHT_PASS"
        or preflight_receipt.get("execution_authorized") is not False
        or preflight_receipt.get("bodies_executed") is not False
        or preflight_receipt.get("attempt_reserved") is not False
        or preflight_receipt.get("worktree_id") != scope_id
        or preflight_receipt.get("target") != nodeid
        or preflight_receipt.get("preflight_id") != preflight_id
        or preflight_receipt.get("source_fingerprint") != fingerprint
        or preflight_receipt.get("identity") != source_identity
        or preflight_receipt.get("controller_provenance") != controller_provenance
        or preflight_receipt.get("case_manifest") != case_binding
        or preflight_receipt.get("solver_origin_observed") != str((ROOT / "src/solveur/__init__.py").resolve())
        or preflight_receipt.get("collected_nodeids") != [nodeid]
        or preflight_receipt.get("skip_status") != "NO_SKIP_MARKERS"
    ):
        raise RuntimeError("HEX8-SRI refused: collect-only receipt is invalid or belongs to another identity")
    collection = preflight_receipt.get("collection_report", {})
    ledger = preflight_receipt.get("attempt_ledger", {})
    if (
        collection.get("schema") != "qfsolver-hex8sri-convergence24-collection-v1"
        or collection.get("scope_id") != scope_id
        or collection.get("target") != nodeid
        or collection.get("collected_nodeids") != [nodeid]
        or collection.get("skip_markers") != []
        or collection.get("bodies_executed") is not False
        or collection.get("exitstatus") != 0
        or ledger.get("attempts_reserved") is not False
    ):
        raise RuntimeError("HEX8-SRI refused: collect-only attestation or no-attempt proof is invalid")

    import solveur

    expected_solver_origin = str((ROOT / "src/solveur/__init__.py").resolve())
    if str(Path(solveur.__file__).resolve()) != expected_solver_origin:
        raise RuntimeError("HEX8-SRI refused: imported solver package is not from the frozen science worktree")

    return {
        "case_manifest_path": case_manifest_path,
        "case_manifest": case_manifest,
        "case_manifest_sha256": case_manifest_sha256,
        "execution_manifest_path": execution_manifest_path,
        "execution_manifest_sha256": execution_manifest_sha256,
        "execution_manifest": execution_manifest,
        "preflight_id": preflight_id,
        "preflight_sha256": preflight_sha256,
        "owner_decision_id": owner_decision_id,
        "owner_decision": owner_decision,
        "criteria_freeze": criteria_freeze,
        "frozen_criteria": frozen_criteria,
        "criteria_dispositions": FROZEN_DISPOSITIONS,
        "source_fingerprint": fingerprint,
    }


@pytest.mark.parametrize(("formulation", "poisson_ratio", "divisions_xyz", "case_id"), CASE_PARAMETERS)
def test_convergence_case(
    formulation: str,
    poisson_ratio: float,
    divisions_xyz: tuple[int, int, int],
    case_id: str,
    request: pytest.FixtureRequest,
) -> None:
    """Run one approved FEM case, archive it, then apply its frozen local gates."""
    authorization = _authorized_case(request, case_id)
    manifest_path = authorization["case_manifest_path"]
    manifest = authorization["case_manifest"]
    manifest_sha256 = authorization["case_manifest_sha256"]
    execution_manifest_path = authorization["execution_manifest_path"]
    execution_manifest_sha256 = authorization["execution_manifest_sha256"]
    fingerprint = authorization["source_fingerprint"]
    nx, ny, nz = divisions_xyz
    expected_node_count = math.prod((nx + 1, ny + 1, nz + 1))
    expected_dof_count = 3 * expected_node_count
    expected_fixed_dof_count = 3 * (ny + 1) * (nz + 1)
    expected_free_dof_count = expected_dof_count - expected_fixed_dof_count
    mesh = manifest.get("mesh", {})
    loading = manifest.get("loading", {})
    boundary_conditions = manifest.get("boundary_conditions", {})
    material = manifest.get("material", {})
    formulation_manifest = manifest.get("formulation", {})
    if (
        formulation_manifest.get("id") != formulation
        or float(manifest.get("poisson_ratio", float("nan"))) != poisson_ratio
        or mesh.get("divisions_xyz") != list(divisions_xyz)
        or mesh.get("dimensions_L_y_z_m") != [20.0, 1.0, 1.0]
        or mesh.get("element_count") != math.prod(divisions_xyz)
        or mesh.get("node_count") != expected_node_count
        or mesh.get("dof_count") != expected_dof_count
        or mesh.get("fixed_dof_count") != expected_fixed_dof_count
        or mesh.get("free_dof_count") != expected_free_dof_count
        or material.get("young_modulus_pa") != 1.0e6
        or material.get("poisson_ratio") != poisson_ratio
        or boundary_conditions.get("fixed_face") != "x=0"
        or boundary_conditions.get("fixed_components") != ["UX", "UY", "UZ"]
        or loading.get("loaded_face") != "x=20 m"
        or loading.get("uniform_traction_pa") != [0.0, 0.0, -1.0]
        or loading.get("resultant_force_n") != [0.0, 0.0, -1.0]
        or loading.get("resultant_moment_about_origin_nm") != [-0.5, 20.0, 0.0]
    ):
        raise RuntimeError("HEX8-SRI convergence refused: manifest physics or selected DDL do not match the case")
    criteria = authorization["frozen_criteria"]
    artifact_root = Path(manifest["execution_artifact_root"])
    started = time.perf_counter()
    controller_identity = {
        "worktree_id": os.environ["QF_DEV_WORKTREE_ID"],
        "root": os.environ["QF_DEV_CONTROLLER_ROOT"],
        "branch": os.environ["QF_DEV_CONTROLLER_BRANCH"],
        "head": os.environ["QF_DEV_CONTROLLER_HEAD"],
        "tree": os.environ["QF_DEV_CONTROLLER_TREE"],
        "runner_sha256": os.environ["QF_DEV_CONTROLLER_RUNNER_SHA256"],
        "policy_sha256": os.environ["QF_DEV_CONTROLLER_POLICY_SHA256"],
        "pytest_plugin_sha256": os.environ["QF_DEV_CONTROLLER_PLUGIN_SHA256"],
    }
    science_identity = {
        "branch": _git("branch", "--show-current"),
        "head": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "source_fingerprint_sha256": fingerprint,
    }
    start_path = artifact_root / f"started_{case_id}_attempt-001.json"
    start_record = {
        "schema": "qfsolver-hex8-sri-convergence-attempt-v1",
        "attempt_status": "STARTED",
        "campaign_id": manifest["campaign_id"],
        "case_id": case_id,
        "case_manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
        "execution_manifest": {
            "path": str(execution_manifest_path),
            "sha256": execution_manifest_sha256,
            "authorization_id": os.environ["QF_DEV_AUTHORIZATION_ID"],
        },
        "owner_decision_id": authorization["owner_decision_id"],
        "preflight": {
            "preflight_id": authorization["preflight_id"],
            "receipt_sha256": authorization["preflight_sha256"],
        },
        "exact_nodeid": request.node.nodeid,
        "attempt_number": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget": manifest["budgets"],
        "science_identity": science_identity,
        "controller_identity": controller_identity,
        "criteria_contract": manifest["criteria_contract"],
        "criteria_freeze": authorization["criteria_freeze"],
        "criteria_dispositions": authorization["criteria_dispositions"],
        "frozen_case_gate_criteria": criteria,
    }
    start_sha256 = atomic_write_json_new(start_path, start_record)
    record: dict | None = None
    state_path: Path | None = None
    sidecar_path: Path | None = None
    sidecar_sha256: str | None = None
    try:
        record, state = run_convergence_case(formulation, poisson_ratio, divisions_xyz, criteria=criteria)

        state_buffer = BytesIO()
        np.savez_compressed(state_buffer, **state)
        state_path = artifact_root / f"state_{case_id}_attempt-001.npz"
        state_sha256 = atomic_write_new_bytes(state_path, state_buffer.getvalue())
        try:
            import psutil

            rss_bytes = int(psutil.Process().memory_info().rss)
        except ImportError:
            rss_bytes = None
        record["resource_observations"] = {
            "process_rss_bytes_at_postprocess": rss_bytes,
            "rss_semantics": "single process snapshot; controller sampled peak RSS is authoritative",
            "state_artifact_bytes": state_path.stat().st_size,
            "elapsed_seconds_before_assertions": time.perf_counter() - started,
        }
        sidecar = {
            "schema": "qfsolver-hex8-sri-convergence-sidecar-v1",
            "campaign_id": manifest["campaign_id"],
            "case_id": case_id,
            "attempt_receipt": {"path": str(start_path), "sha256": start_sha256},
            "case_manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
            "execution_manifest": {
                "path": str(execution_manifest_path),
                "sha256": execution_manifest_sha256,
                "authorization_id": os.environ["QF_DEV_AUTHORIZATION_ID"],
            },
            "owner_decision_id": authorization["owner_decision_id"],
            "preflight": {
                "preflight_id": authorization["preflight_id"],
                "receipt_sha256": authorization["preflight_sha256"],
            },
            "state_artifact": {"path": str(state_path), "sha256": state_sha256},
            "science_identity": science_identity,
            "controller_identity": controller_identity,
            "criteria_contract": manifest["criteria_contract"],
            "criteria_freeze": authorization["criteria_freeze"],
            "criteria_dispositions": authorization["criteria_dispositions"],
            "frozen_case_gate_criteria": criteria,
            **record,
        }
        sidecar_path = artifact_root / f"sidecar_{case_id}_attempt-001.json"
        sidecar_sha256 = atomic_write_json_new(sidecar_path, sidecar)
    except Exception as exc:
        failure = {
            "schema": "qfsolver-hex8-sri-convergence-attempt-v1",
            "attempt_status": "FAILED_DURING_EXECUTION_OR_ARCHIVING",
            "campaign_id": manifest["campaign_id"],
            "case_id": case_id,
            "exact_nodeid": request.node.nodeid,
            "attempt_number": 1,
            "case_manifest": {"path": str(manifest_path), "sha256": manifest_sha256},
            "execution_manifest": {
                "path": str(execution_manifest_path),
                "sha256": execution_manifest_sha256,
                "authorization_id": os.environ["QF_DEV_AUTHORIZATION_ID"],
            },
            "owner_decision_id": authorization["owner_decision_id"],
            "preflight": {
                "preflight_id": authorization["preflight_id"],
                "receipt_sha256": authorization["preflight_sha256"],
            },
            "attempt_receipt": {"path": str(start_path), "sha256": start_sha256},
            "science_identity": science_identity,
            "controller_identity": controller_identity,
            "elapsed_seconds_before_failure": time.perf_counter() - started,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "state_artifact": (
                {"path": str(state_path), "sha256": _sha256(state_path)}
                if state_path is not None and state_path.is_file()
                else None
            ),
            "sidecar_written": sidecar_path is not None and sidecar_path.is_file(),
            "criteria_verdicts": record.get("criteria_verdicts") if record is not None else None,
        }
        failure_path = artifact_root / f"failure_{case_id}_attempt-001.json"
        atomic_write_json_new(failure_path, failure)
        raise

    # Persist full state and observables before the first assertion.
    assert state_path is not None and state_path.is_file()
    assert sidecar_path is not None and sidecar_path.is_file() and sidecar_sha256 is not None
    assert _sha256(state_path) == sidecar["state_artifact"]["sha256"]
    assert sidecar_path.is_file() and _sha256(sidecar_path) == sidecar_sha256
    assert record is not None
    deferred_verdicts = {"independent_3d_reference_error", "single_case_convergence"}
    for criterion_name, verdict in record["criteria_verdicts"].items():
        if criterion_name in deferred_verdicts:
            assert verdict.startswith("NOT_ASSESSED"), f"{criterion_name} must remain deferred for one mesh"
            continue
        assert verdict == "PASS", f"{criterion_name} failed; evidence was preserved"
