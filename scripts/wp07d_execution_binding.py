"""Validate the separately versioned WP07-D execution binding.

The historical WP07-D contract remains preparation-only.  This module binds
that immutable physics contract to the governing nonlinear policy and creates
only a no-solve readiness record.  A later Owner authorization is required
before a structural or independent-reference execution path may be imported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, cast


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BINDING_PATH = ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding.json"
REMEDIATION_BINDING_PATH = ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding_remediation_r1.json"
AREA_REFINEMENT_BINDING_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding_surface_lumped_experiment.json"
)
GRADED_TET4_BINDING_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding_graded_tet4_experiment.json"
)
GRADED_RAISED_HIERARCHY_BINDING_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding_graded_raised_hierarchy_experiment.json"
)
LOCAL_CONTACT_REFINEMENT_BINDING_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_execution_binding_local_contact_refinement_experiment.json"
)
FOCUSED_LOCAL_CONTACT_REFINEMENT_BINDING_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_execution_binding_focused_local_refinement_experiment.json"
)
FORMAL_REBIND_R1_BINDING_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_formal_rebind_r1"
    / "wp07d_execution_binding_formal_rebind_r1.json"
)
PREPARATION_CONTRACT_PATH = ROOT / "qualification" / "0_2_9" / "wp07d_structural_vnv_contract.json"
FORMAL_REBIND_R1_CONTRACT_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_formal_rebind_r1"
    / "wp07d_formal_requalification_contract_r1.json"
)
FORMAL_REBIND_R1_OWNER_DECISION_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_formal_rebind_r1" / "owner_decision.json"
)
FORMAL_REBIND_R1_EXPERIMENT_SUMMARY_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_focused_local_refinement_experiment"
    / "focused_local_refinement_summary.json"
)
FORMAL_REBIND_R1_REPLAY_GATE_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_formal_rebind_r1" / "replay_authorization_gate.json"
)
HISTORICAL_PREPARATION_CONTRACT_SHA256 = (
    "a31f32d45bfa65f5aaaac62034cdc94cfafae3d59a7fbc1ce8ce8489d7cae3e9"
)
FORMAL_REBIND_R1_ARTIFACT_ID = "QF-029-WP07-D-EXECUTION-BINDING-FORMAL-REBIND-R1-001"
FORMAL_REBIND_R1_TOKEN = "OWNER_AUTHORIZED_WP07D_FORMAL_REBIND_R1"
CONTACT_REQUAL_R2_ARTIFACT_ID = "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-001"
CONTACT_REQUAL_R2_BINDING_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_contact_requalification_r2"
    / "execution_binding_r2_1.json"
)
CONTACT_REQUAL_R2_CONTRACT_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_contact_requalification_r2" / "contact_requalification_contract.json"
)
CONTACT_REQUAL_R2_OWNER_DECISION_PATH = (
    ROOT / "qualification" / "0_2_9" / "wp07d_contact_requalification_r2" / "owner_execution_decision.json"
)
CONTACT_REQUAL_R2_TOKEN = "OWNER_AUTHORIZED_WP07D_CONTACT_REQUALIFICATION_R2"
CONTACT_REQUAL_R2_REPLAY_GATE_PATH = (
    ROOT
    / "qualification"
    / "0_2_9"
    / "wp07d_contact_requalification_r2"
    / "replay_authorization_gate_r2_2.json"
)
CONTACT_REQUAL_R2_RUN_ROOT = Path("qualification/0_2_9/wp07d_contact_requalification_r2/runs_r2_2")
CONTACT_REQUAL_R2_AUTH_ROOT = Path(
    "qualification/0_2_9/wp07d_contact_requalification_r2/authorizations_r2_2"
)
UNAUTHORIZED_EXECUTION = "WP07D_UNAUTHORIZED_EXECUTION_FAIL_CLOSED"
EXPECTED_ROUTES = ("ACTIVE_SET", "PENALTY")
EXPECTED_LEVELS = ("M1", "M2", "M3")


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def validate_authorized_execution_source(authorization: Mapping[str, Any]) -> str:
    """Require the runtime source tree to match its Owner-authorized commit.

    Evidence-only commits may follow the authorized source commit, but neither
    committed nor uncommitted changes under ``src`` or ``scripts`` are allowed
    between that source and the current execution.  The actual HEAD remains
    separately recorded in each run artifact.
    """

    authorized_sha = authorization.get("execution_sha")
    if (
        not isinstance(authorized_sha, str)
        or len(authorized_sha) != 40
        or any(character not in "0123456789abcdef" for character in authorized_sha)
    ):
        raise PermissionError("WP07-D authorization has no valid execution source SHA.")

    try:
        resolved_sha = _git("rev-parse", "--verify", f"{authorized_sha}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise PermissionError("WP07-D authorized execution source SHA is unavailable.") from exc
    if resolved_sha != authorized_sha:
        raise PermissionError("WP07-D authorized execution source SHA is not canonical.")

    current_sha = _git("rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", authorized_sha, current_sha],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise PermissionError("WP07-D authorized execution source is not an ancestor of HEAD.")

    committed_source_changes = _git(
        "diff", "--name-only", authorized_sha, current_sha, "--", "src", "scripts"
    )
    if committed_source_changes:
        raise PermissionError("WP07-D source files differ from the authorized execution SHA.")

    working_source_changes = _git(
        "status", "--porcelain=v1", "--untracked-files=all", "--", "src", "scripts"
    )
    if working_source_changes:
        raise PermissionError("WP07-D execution source tree has uncommitted changes.")
    return authorized_sha


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object.")
    return value


def _validate_focused_local_comparison_baseline(
    binding: Mapping[str, Any], *, root: Path, required_base: str
) -> None:
    """Validate the byte-pinned M2 baseline used by the focused M3 experiment."""

    baseline = binding.get("comparison_baseline")
    if (
        not isinstance(baseline, Mapping)
        or baseline.get("level") != "M2"
        or baseline.get("source_mesh") != "M3"
        or baseline.get("source_cell_counts") != [16, 16, 8]
        or baseline.get("coordinate_grading_exponent") != 1.5
        or baseline.get("classification") != "DIAGNOSTIC_ONLY"
    ):
        raise ValueError("Focused local-refinement binding lacks its exact diagnostic M2 baseline.")
    route_records = baseline.get("routes")
    if not isinstance(route_records, Mapping) or tuple(route_records) != EXPECTED_ROUTES:
        raise ValueError("Focused local-refinement M2 baseline must cover both routes in order.")
    baseline_root = "qualification/0_2_9/wp07d_focused_local_refinement_experiment/baseline/M2"
    for route in EXPECTED_ROUTES:
        records = route_records[route]
        if not isinstance(records, Mapping) or tuple(records) != ("production", "independent_reference"):
            raise ValueError(f"Focused M2 baseline is malformed for {route}.")
        for role in ("production", "independent_reference"):
            record = records[role]
            if not isinstance(record, Mapping):
                raise ValueError(f"Focused M2 {route}/{role} provenance is malformed.")
            relative_root = f"{baseline_root}/{route}/{role}"
            result_path = record.get("result_path")
            result_digest = record.get("result_sha256")
            if (
                result_path != f"{relative_root}/result.json"
                or not isinstance(result_digest, str)
                or _file_sha256((root / result_path).resolve()) != result_digest
            ):
                raise ValueError(f"Focused M2 {route}/{role} result hash or path mismatch.")
            result = _load_json((root / result_path).resolve())
            if result.get("status") not in ({"PASS", "success", "COMPLETED"} if role == "production" else {"PASS"}):
                raise ValueError(f"Focused M2 {route}/{role} result is not passing.")
            observables = result.get("wp07d_observables")
            if not isinstance(observables, Mapping):
                raise ValueError(f"Focused M2 {route}/{role} lacks WP07-D observables.")
            if role == "production":
                run_path = record.get("run_path")
                run_digest = record.get("run_sha256")
                source_binding_path = record.get("source_binding_path")
                source_binding_digest = record.get("source_binding_sha256")
                source_authorization_path = record.get("source_authorization_path")
                source_authorization_digest = record.get("source_authorization_sha256")
                if (
                    run_path != f"{relative_root}/run.json"
                    or not isinstance(run_digest, str)
                    or _file_sha256((root / run_path).resolve()) != run_digest
                    or source_binding_path != f"{relative_root}/source_binding.json"
                    or not isinstance(source_binding_digest, str)
                    or _file_sha256((root / source_binding_path).resolve()) != source_binding_digest
                    or source_authorization_path != f"{relative_root}/source_authorization.json"
                    or not isinstance(source_authorization_digest, str)
                    or _file_sha256((root / source_authorization_path).resolve()) != source_authorization_digest
                ):
                    raise ValueError(f"Focused M2 {route} production source artifacts are incomplete or altered.")
                run = _load_json((root / run_path).resolve())
                if (
                    run.get("status") != "COMPLETED"
                    or run.get("route") != route
                    or run.get("mesh") != "M3"
                    or run.get("mesh_cell_counts") != [16, 16, 8]
                    or run.get("mesh_axis_fractions") is not None
                    or run.get("coordinate_grading_exponent") != 1.5
                    or run.get("result_file_sha256") != result_digest
                    or run.get("binding_file_sha256") != source_binding_digest
                    or run.get("authorization_file_sha256") != source_authorization_digest
                    or (route == "PENALTY" and run.get("penalty_integration") != "surface_lumped")
                ):
                    raise ValueError(f"Focused M2 {route} production manifest does not bind the raw result.")
                execution_sha = run.get("execution_sha")
                if (
                    not isinstance(execution_sha, str)
                    or len(execution_sha) != 40
                    or _git("rev-parse", "--verify", f"{execution_sha}^{{commit}}") != execution_sha
                ):
                    raise ValueError(f"Focused M2 {route} production execution SHA is invalid.")
                ancestry = subprocess.run(
                    ["git", "merge-base", "--is-ancestor", required_base, execution_sha],
                    cwd=root,
                    check=False,
                    capture_output=True,
                )
                if ancestry.returncode != 0:
                    raise ValueError(f"Focused M2 {route} production is outside the governing lineage.")
                if run.get("telemetry_status") not in {None, "PASS", "HEALTHY"}:
                    raise ValueError(f"Focused M2 {route} production has unexpected telemetry status.")
            else:
                if (
                    result.get("route") != route
                    or result.get("mesh_cell_counts") != [16, 16, 8]
                    or result.get("mesh_axis_fractions") is not None
                    or result.get("coordinate_grading_exponent") != 1.5
                ):
                    raise ValueError(f"Focused M2 {route} reference result mesh provenance drifted.")
                run_path = record.get("run_path")
                if route == "ACTIVE_SET":
                    if (
                        run_path is not None
                        or record.get("run_sha256") is not None
                        or record.get("telemetry_status") != "NOT_RECORDED_BY_SOURCE_RUNNER"
                    ):
                        raise ValueError("Focused M2 ACTIVE_SET reference provenance must disclose the missing run manifest.")
                else:
                    run_digest = record.get("run_sha256")
                    source_binding_path = record.get("source_binding_path")
                    source_binding_digest = record.get("source_binding_sha256")
                    source_authorization_path = record.get("source_authorization_path")
                    source_authorization_digest = record.get("source_authorization_sha256")
                    if (
                        run_path != f"{relative_root}/run.json"
                        or not isinstance(run_digest, str)
                        or _file_sha256((root / run_path).resolve()) != run_digest
                        or source_binding_path != f"{relative_root}/source_binding.json"
                        or not isinstance(source_binding_digest, str)
                        or _file_sha256((root / source_binding_path).resolve()) != source_binding_digest
                        or source_authorization_path != f"{relative_root}/source_authorization.json"
                        or not isinstance(source_authorization_digest, str)
                        or _file_sha256((root / source_authorization_path).resolve()) != source_authorization_digest
                    ):
                        raise ValueError("Focused M2 PENALTY reference source artifacts are incomplete or altered.")
                    run = _load_json((root / run_path).resolve())
                    if (
                        run.get("status") != "COMPLETED"
                        or run.get("route") != route
                        or run.get("mesh") != "M3"
                        or run.get("mesh_cell_counts") != [16, 16, 8]
                        or run.get("mesh_axis_fractions") is not None
                        or run.get("coordinate_grading_exponent") != 1.5
                        or run.get("result_file_sha256") != result_digest
                        or run.get("binding_file_sha256") != source_binding_digest
                        or run.get("authorization_file_sha256") != source_authorization_digest
                        or run.get("telemetry_status") != record.get("telemetry_status")
                        or run.get("telemetry_status") not in {"PASS", "HEALTHY", "DEGRADED"}
                        or run.get("penalty_integration") != "surface_lumped"
                    ):
                        raise ValueError("Focused M2 PENALTY reference manifest does not bind the raw result.")
                    execution_sha = run.get("execution_sha")
                    if (
                        not isinstance(execution_sha, str)
                        or len(execution_sha) != 40
                        or _git("rev-parse", "--verify", f"{execution_sha}^{{commit}}") != execution_sha
                    ):
                        raise ValueError("Focused M2 PENALTY reference execution SHA is invalid.")
                    ancestry = subprocess.run(
                        ["git", "merge-base", "--is-ancestor", required_base, execution_sha],
                        cwd=root,
                        check=False,
                        capture_output=True,
                    )
                    if ancestry.returncode != 0:
                        raise ValueError("Focused M2 PENALTY reference is outside the governing lineage.")


def load_binding(path: Path = BINDING_PATH) -> dict[str, Any]:
    """Load the execution binding without applying defaults."""

    raw = _load_json(path)
    if raw.get("artifact_id") != CONTACT_REQUAL_R2_ARTIFACT_ID:
        return raw
    parent_ref = raw.get("extends_binding")
    if not isinstance(parent_ref, Mapping) or not isinstance(parent_ref.get("path"), str):
        raise ValueError("WP07-D contact R2 binding has no exact parent binding reference.")
    parent_path = (ROOT / str(parent_ref["path"])).resolve()
    if not parent_path.is_relative_to(ROOT.resolve()) or not parent_path.is_file():
        raise ValueError("WP07-D contact R2 parent binding is missing or outside the repository.")
    if _file_sha256(parent_path) != parent_ref.get("sha256"):
        raise ValueError("WP07-D contact R2 parent binding hash mismatch.")
    parent = _load_json(parent_path)
    owner_ref = raw.get("owner_decision")
    contract_ref = raw.get("requalification_contract")
    governing = raw.get("governing")
    authorization = raw.get("authorization")
    lineage = raw.get("source_lineage_disclosure")
    invariants = raw.get("invariants")
    if not isinstance(owner_ref, Mapping):
        raise ValueError("WP07-D contact R2 owner-decision reference is malformed.")
    if not isinstance(contract_ref, Mapping):
        raise ValueError("WP07-D contact R2 contract reference is malformed.")
    if not isinstance(governing, Mapping):
        raise ValueError("WP07-D contact R2 governing reference is malformed.")
    if not isinstance(authorization, Mapping):
        raise ValueError("WP07-D contact R2 authorization is malformed.")
    if not isinstance(lineage, Mapping):
        raise ValueError("WP07-D contact R2 source-lineage disclosure is malformed.")
    if not isinstance(invariants, Mapping):
        raise ValueError("WP07-D contact R2 invariants are malformed.")
    hydrated = dict(parent)
    hydrated.update(
        {
            "artifact_id": CONTACT_REQUAL_R2_ARTIFACT_ID,
            "status": raw.get("status"),
            "owner_decision": {
                "contract_rebind_authorized": True,
                "file_sha256": owner_ref.get("sha256"),
                "formal_wp07d_requalification_authorized": True,
                "path": owner_ref.get("path"),
                "push_merge_ledger_update_authorized": False,
                "wp07e_authorized": False,
            },
            "governing": {
                "authorized_base_sha": governing.get("authorized_base_sha"),
                "policy_digest": governing.get("policy_digest"),
                "policy_id": "qf-solver-floor-aware-termination",
                "policy_version": 1,
            },
            "authorization": {
                "required": True,
                "token": authorization.get("token"),
                "structural_solves_allowed": False,
                "independent_references_allowed": False,
                "replay_allowed": False,
                "wp07e_allowed": False,
            },
            "invariants": dict(invariants),
            "source_lineage_disclosure": dict(lineage),
            "source_requalification": {
                "path": contract_ref.get("path"),
                "sha256": contract_ref.get("sha256"),
                "parent_binding_path": parent_ref.get("path"),
                "parent_binding_sha256": parent_ref.get("sha256"),
            },
            "_binding_path": path.resolve().relative_to(ROOT.resolve()).as_posix(),
        }
    )
    return hydrated


def formal_contract_identity(
    binding: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any] | None:
    """Return the SHA-pinned formal contract identity for the formal R1 binding."""

    if binding.get("artifact_id") not in {FORMAL_REBIND_R1_ARTIFACT_ID, CONTACT_REQUAL_R2_ARTIFACT_ID}:
        return None
    reference = binding.get("formal_contract")
    if not isinstance(reference, Mapping) or not isinstance(reference.get("path"), str):
        raise ValueError("Formal WP07-D rebind binding lacks a valid contract reference.")
    path = (root / str(reference["path"])).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Formal WP07-D contract path is missing or escapes the validation root.")
    digest = _file_sha256(path)
    if digest != reference.get("file_sha256"):
        raise ValueError("Formal WP07-D contract file hash drifted.")
    contract = _load_json(path)
    return {
        "path": str(reference["path"]).replace("\\", "/"),
        "file_sha256": digest,
        "record_id": contract.get("record_id"),
        "revision": contract.get("revision"),
        "base_contract_path": reference.get("base_contract_path"),
        "base_contract_sha256": reference.get("base_contract_sha256"),
        "owner_decision_path": reference.get("owner_decision_path"),
        "owner_decision_sha256": reference.get("owner_decision_sha256"),
    }


def load_contract_for_binding(
    binding: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    """Load the exact contract used by a binding, retaining legacy defaults."""

    identity = formal_contract_identity(binding, root=root)
    if identity is not None:
        return _load_json(root / str(identity["path"]))
    from scripts.prepare_wp07d_structural_vnv import load_contract

    return load_contract()


def _validate_formal_rebind_r1_binding(binding: Mapping[str, Any], *, root: Path) -> None:
    """Validate the Owner-approved R1 contract rebind without opening execution."""

    if binding.get("artifact_id") != FORMAL_REBIND_R1_ARTIFACT_ID:
        raise ValueError("Unexpected formal WP07-D R1 binding identity.")
    if binding.get("status") != "FROZEN_READY_FOR_SHA_BOUND_PER_CASE_AUTHORIZATION":
        raise ValueError("Formal WP07-D R1 binding must remain fail-closed before per-case authorization.")
    if binding.get("work_package") != "WP07-D":
        raise ValueError("Formal WP07-D R1 binding has the wrong work package.")

    relative_base_path = PREPARATION_CONTRACT_PATH.relative_to(ROOT)
    base_path = root / relative_base_path
    if _file_sha256(base_path) != HISTORICAL_PREPARATION_CONTRACT_SHA256:
        raise ValueError("The historical WP07-D preparation-only contract was modified.")
    base_contract = _load_json(base_path)
    base_execution = base_contract.get("execution_policy")
    if (
        base_contract.get("status") != "PREPARATION_ONLY"
        or not isinstance(base_execution, Mapping)
        or base_execution.get("structural_solves_allowed") is not False
    ):
        raise ValueError("The historical WP07-D contract no longer preserves its preparation-only state.")

    identity = formal_contract_identity(binding, root=root)
    if identity is None:
        raise ValueError("Formal WP07-D R1 contract identity is unavailable.")
    reference = binding["formal_contract"]
    if (
        reference.get("path") != FORMAL_REBIND_R1_CONTRACT_PATH.relative_to(ROOT).as_posix()
        or reference.get("record_id") != "QF-029-WP07-D-STRUCTURAL-VNV-FORMAL-REBIND-R1-001"
        or reference.get("revision") != "0.2.9-WP07D-FORMAL-REBIND-R1"
        or reference.get("base_contract_path") != relative_base_path.as_posix()
        or reference.get("base_contract_sha256") != HISTORICAL_PREPARATION_CONTRACT_SHA256
        or reference.get("owner_decision_path")
        != FORMAL_REBIND_R1_OWNER_DECISION_PATH.relative_to(ROOT).as_posix()
    ):
        raise ValueError("Formal WP07-D R1 contract provenance differs from the frozen binding.")
    preparation_reference = binding.get("preparation_contract")
    if (
        not isinstance(preparation_reference, Mapping)
        or preparation_reference.get("path") != relative_base_path.as_posix()
        or preparation_reference.get("file_sha256") != HISTORICAL_PREPARATION_CONTRACT_SHA256
        or preparation_reference.get("preserved_preparation_only") is not True
    ):
        raise ValueError("Formal WP07-D R1 must preserve the exact historical preparation-contract reference.")

    contract_path = root / str(reference["path"])
    contract = _load_json(contract_path)
    if (
        contract.get("record_id") != reference.get("record_id")
        or contract.get("revision") != reference.get("revision")
        or contract.get("status") != "FROZEN_FOR_OWNER_AUTHORIZED_FORMAL_REQUALIFICATION"
        or contract.get("qualification_campaign_executed") is not False
        or contract.get("structural_solves_run") is not False
        or contract.get("external_solver_run") is not False
        or contract.get("validated_total") != "58/100"
    ):
        raise ValueError("Formal WP07-D R1 contract state is inconsistent or already claims results.")

    unchanged_sections = (
        "physical_benchmark",
        "loading",
        "observables",
        "scales",
        "thresholds",
        "negative_cases",
        "external_reference_plan",
    )
    if any(contract.get(section) != base_contract.get(section) for section in unchanged_sections):
        raise ValueError("Formal WP07-D rebind changed a pinned physics, observable, threshold, or reference section.")
    if contract.get("rebind_r1", {}).get("formal_thresholds_copied_byte_for_byte") is not True:
        raise ValueError("Formal WP07-D R1 does not declare byte-identical thresholds.")
    penalty_rebind = contract.get("rebind_r1", {}).get("penalty_integration_rebind", {})
    if (
        contract.get("rebind_r1", {}).get("penalty_integration_changed_from_historical_contract") is not True
        or penalty_rebind.get("historical_contract")
        != "nodal (historical runner default; field absent from preparation contract)"
        or penalty_rebind.get("formal_rebind_r1") != "surface_lumped"
        or base_contract.get("benchmarks", {}).get("PENALTY", {}).get("penalty_integration", "nodal") != "nodal"
        or contract.get("benchmarks", {}).get("PENALTY", {}).get("penalty_integration") != "surface_lumped"
    ):
        raise ValueError("Formal WP07-D R1 must explicitly disclose the nodal-to-surface-lumped contract rebind.")
    rebind_prechecks = contract.get("rebind_r1_prechecks", {})
    if (
        rebind_prechecks.get("status") != "PASS"
        or tuple(item.get("level") for item in rebind_prechecks.get("levels", [])) != EXPECTED_LEVELS
        or any(
            item.get("mesh", {}).get("status") != "PASS"
            or item.get("load", {}).get("status") != "PASS"
            or item.get("graded_geometry_and_load", {}).get("status") != "PASS"
            for item in rebind_prechecks.get("levels", [])
        )
    ):
        raise ValueError("Formal WP07-D R1 mesh/load prechecks are missing or failing.")
    if (
        contract.get("governance", {}).get("production_mechanics_changed_since_governing_base") is not True
        or contract.get("governance", {}).get("production_mechanics_changed_by_rebind") is not False
    ):
        raise ValueError("Formal WP07-D R1 must disclose inherited source mechanics changes separately from the rebind.")
    if (
        contract.get("execution_policy", {}).get("structural_solves_allowed") is not True
        or contract.get("execution_policy", {}).get("per_case_owner_authorization_required") is not True
        or contract.get("execution_policy", {}).get("external_solver_allowed") is not False
        or contract.get("execution_policy", {}).get("wp07e_allowed") is not False
    ):
        raise ValueError("Formal WP07-D R1 contract authorization scope is inconsistent.")

    owner_reference = binding.get("owner_decision")
    if not isinstance(owner_reference, Mapping):
        raise ValueError("Formal WP07-D R1 binding lacks the Owner decision reference.")
    owner_path = (root / str(owner_reference.get("path"))).resolve()
    if not owner_path.is_relative_to(root.resolve()) or not owner_path.is_file():
        raise ValueError("Formal WP07-D R1 Owner decision is missing or escapes the validation root.")
    owner_sha = _file_sha256(owner_path)
    if (
        owner_sha != owner_reference.get("file_sha256")
        or owner_sha != reference.get("owner_decision_sha256")
        or owner_reference.get("contract_rebind_authorized") is not True
        or owner_reference.get("formal_wp07d_requalification_authorized") is not True
        or owner_reference.get("wp07e_authorized") is not False
        or owner_reference.get("push_merge_ledger_update_authorized") is not False
    ):
        raise ValueError("Formal WP07-D R1 Owner decision is altered or out of scope.")
    owner = _load_json(owner_path)
    if (
        owner.get("OWNER_ACCEPTS_EXPERIMENTAL_RESULT") is not True
        or owner.get("OWNER_ACCEPTS_REFINED_M3_AS_FORMAL_LEVEL_UNDER_CURRENT_CONTRACT") is not False
        or owner.get("OWNER_AUTHORIZES_CONTRACT_REBIND") is not True
        or owner.get("OWNER_AUTHORIZES_FORMAL_WP07D_REQUALIFICATION_AFTER_REBIND") is not True
        or owner.get("OWNER_AUTHORIZES_WP07E") is not False
    ):
        raise ValueError("Formal WP07-D R1 Owner decision fields do not authorize this bounded requalification.")
    experiment_summary = root / FORMAL_REBIND_R1_EXPERIMENT_SUMMARY_PATH.relative_to(ROOT)
    expected_experiment_sha = owner.get("provenance", {}).get("accepted_experimental_summary_sha256")
    if (
        not experiment_summary.is_file()
        or _file_sha256(experiment_summary) != expected_experiment_sha
        or expected_experiment_sha != "9f4d861e15968511cb050343387f620e892754c2a76c228835c7218d761d9948"
    ):
        raise ValueError("Accepted diagnostic experiment summary provenance is missing or altered.")

    governing = binding.get("governing")
    if (
        not isinstance(governing, Mapping)
        or governing.get("authorized_base_sha") != "a670f106f4eef88a3cfe5ca65a09ed55cdcc19fe"
        or governing.get("policy_digest") != "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
    ):
        raise ValueError("Formal WP07-D R1 governing base or policy digest differs from the reviewed lineage.")
    descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(governing["authorized_base_sha"]), _git("rev-parse", "HEAD")],
        cwd=root,
        check=False,
        capture_output=True,
    ).returncode == 0
    if not descendant:
        raise ValueError("Formal WP07-D R1 candidate is not based on its authorized governing SHA.")
    lineage = binding.get("source_lineage_disclosure")
    if (
        not isinstance(lineage, Mapping)
        or lineage.get("authorized_governing_base_sha") != governing["authorized_base_sha"]
        or lineage.get("source_contains_wp07_candidate_changes_since_governing_base") is not True
        or lineage.get("rebind_commit_adds_production_mechanics_changes") is not False
    ):
        raise ValueError("Formal WP07-D R1 source lineage disclosure is incomplete.")
    source_patch = subprocess.run(
        ["git", "diff", "--binary", str(governing["authorized_base_sha"]), "HEAD", "--", "src"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    if hashlib.sha256(source_patch).hexdigest() != lineage.get("production_source_diff_sha256_since_governing_base"):
        raise ValueError("Formal WP07-D R1 candidate production source diff changed after the Owner decision.")

    from scripts.prepare_wp07d_structural_vnv import focused_local_contact_refinement_axis_fractions

    axes = {axis: list(values) for axis, values in focused_local_contact_refinement_axis_fractions().items()}
    expected_counts = {"M1": [8, 8, 4], "M2": [16, 16, 8], "M3": [32, 16, 16]}
    mesh_definition = binding.get("mesh_definition")
    if (
        not isinstance(mesh_definition, Mapping)
        or mesh_definition.get("family") != "TET4"
        or mesh_definition.get("topology") != "frozen six-TET structured-cell pattern"
        or mesh_definition.get("coordinate_grading_exponent") != 1.5
        or mesh_definition.get("graded_axes") != ["x", "z"]
        or mesh_definition.get("ungraded_axis") != "y"
        or mesh_definition.get("physical_bounds_preserved") is not True
        or mesh_definition.get("cell_counts_by_level") != expected_counts
        or mesh_definition.get("axis_fractions_by_level") != {"M3": axes}
        or mesh_definition.get("nested_in_m2") is not True
    ):
        raise ValueError("Formal WP07-D R1 TET4 hierarchy or local M3 coordinates drifted.")
    if contract.get("mesh_recipe", {}).get("cell_counts_by_level") != expected_counts:
        raise ValueError("Formal WP07-D R1 contract mesh hierarchy differs from its execution binding.")
    if contract.get("mesh_recipe", {}).get("axis_fractions_by_level") != {"M3": axes}:
        raise ValueError("Formal WP07-D R1 contract local M3 coordinates differ from its execution binding.")
    for level, counts in expected_counts.items():
        mesh_level = next((item for item in contract.get("mesh_levels", []) if item.get("id") == level), None)
        if not isinstance(mesh_level, Mapping) or mesh_level.get("base_cells") != counts:
            raise ValueError(f"Formal WP07-D R1 contract level {level} differs from its frozen hierarchy.")

    routes = binding.get("routes")
    if not isinstance(routes, Mapping) or tuple(routes) != EXPECTED_ROUTES:
        raise ValueError("Formal WP07-D R1 must bind ACTIVE_SET then PENALTY routes.")
    for route_name in EXPECTED_ROUTES:
        route = routes[route_name]
        if (
            not isinstance(route, Mapping)
            or tuple(route.get("mesh_levels", ())) != EXPECTED_LEVELS
            or route.get("updated_search") is not False
            or route.get("finite_sliding") is not False
            or route.get("fallback_allowed") is not False
        ):
            raise ValueError(f"Formal WP07-D R1 {route_name} route scope or fallback policy drifted.")
    if routes["ACTIVE_SET"].get("analysis_type") != "linear_static" or routes["ACTIVE_SET"].get("replay_level") != "M2":
        raise ValueError("Formal WP07-D R1 active-set route or replay level drifted.")
    required_penalty = {
        "analysis_type": "geometric_nonlinear_static",
        "load_increments": 8,
        "adaptive_load_steps": False,
        "linear_solver": "minres",
        "linear_preconditioner": "jacobi",
        "linear_rtol": 1e-11,
        "linear_atol": 1e-14,
        "linear_maxiter": 10000,
        "linear_direct_fallback": False,
        "line_search": "existing",
        "floor_aware_termination": True,
        "penalty_integration": "surface_lumped",
        "replay_level": "M1",
    }
    if any(routes["PENALTY"].get(key) != value for key, value in required_penalty.items()):
        raise ValueError("Formal WP07-D R1 penalty route or governing nonlinear policy drifted.")

    authorization = binding.get("authorization")
    if (
        not isinstance(authorization, Mapping)
        or authorization.get("required") is not True
        or authorization.get("token") != FORMAL_REBIND_R1_TOKEN
        or any(
            authorization.get(field) is not False
            for field in (
                "structural_solves_allowed",
                "independent_references_allowed",
                "replay_allowed",
                "wp07e_allowed",
            )
        )
    ):
        raise ValueError("Formal WP07-D R1 execution binding must fail closed until per-case authorization.")
    invariants = binding.get("invariants")
    if (
        not isinstance(invariants, Mapping)
        or invariants.get("production_mechanics_changed") is not False
        or invariants.get("thresholds_changed") is not False
        or invariants.get("mesh_changed") is not True
        or invariants.get("loads_changed") is not False
        or invariants.get("contact_parameters_changed") is not False
        or invariants.get("penalty_integration_changed") is not True
        or invariants.get("fallback_policy_changed") is not False
    ):
        raise ValueError("Formal WP07-D R1 rebind invariants are inconsistent.")
    if "comparison_baseline" in binding or "reused_diagnostic_levels" in binding:
        raise ValueError("Diagnostic experiment evidence must not be silently reused as formal levels.")


def _validate_formal_replay_gate(
    authorization: Mapping[str, Any],
    binding: Mapping[str, Any],
    binding_path: Path,
    *,
    route: str,
    mesh: str,
    execution_sha: str,
    root: Path,
) -> None:
    """Require a raw-evidence-backed, SHA-pinned route gate before a replay solve."""

    if binding.get("artifact_id") == CONTACT_REQUAL_R2_ARTIFACT_ID:
        _validate_contact_r2_replay_gate(
            authorization,
            binding,
            binding_path,
            route=route,
            mesh=mesh,
            execution_sha=execution_sha,
            root=root,
        )
        return

    relative_gate = FORMAL_REBIND_R1_REPLAY_GATE_PATH.relative_to(ROOT).as_posix()
    gate_value = authorization.get("replay_gate_path")
    gate_sha = authorization.get("replay_gate_file_sha256")
    if gate_value != relative_gate or not isinstance(gate_sha, str):
        raise PermissionError("WP07-D R1 replay authorization lacks its exact pre-replay gate reference.")
    gate_path = (root / relative_gate).resolve()
    if not gate_path.is_relative_to(root.resolve()) or not gate_path.is_file() or _file_sha256(gate_path) != gate_sha:
        raise PermissionError("WP07-D R1 replay gate is missing, outside the validation root, or altered.")
    gate = _load_json(gate_path)
    contract = formal_contract_identity(binding, root=root)
    expected_binding_sha = _file_sha256(binding_path)
    if (
        gate.get("artifact_id") != "QF-029-WP07-D-FORMAL-REBIND-R1-PRE-REPLAY-ANALYSIS-001"
        or gate.get("status") != "PASS_REPLAY_GATES_EVALUATED"
        or gate.get("execution_sha") != execution_sha
        or gate.get("binding_file_sha256") != expected_binding_sha
        or not isinstance(contract, Mapping)
        or gate.get("formal_contract_provenance", {}).get("file_sha256") != contract.get("file_sha256")
        or gate.get("owner_decision", {}).get("file_sha256") != binding.get("owner_decision", {}).get("file_sha256")
        or gate.get("analysis_script_path") != "scripts/analyze_wp07d_formal_rebind_r1.py"
    ):
        raise PermissionError("WP07-D R1 replay gate provenance does not match the current frozen source and contract.")
    analysis_script = (root / str(gate["analysis_script_path"])).resolve()
    if (
        not analysis_script.is_relative_to(root.resolve())
        or not analysis_script.is_file()
        or _file_sha256(analysis_script) != gate.get("analysis_script_sha256")
    ):
        raise PermissionError("WP07-D R1 replay analysis script differs from the SHA-pinned gate producer.")
    expected_level = binding["routes"][route].get("replay_level")
    if mesh != expected_level:
        raise PermissionError("WP07-D R1 replay is not at the route's exact frozen replay level.")
    route_gate = gate.get("routes", {}).get(route)
    if (
        not isinstance(route_gate, Mapping)
        or route_gate.get("status") != "PASS_READY_FOR_REPLAY"
        or route_gate.get("replay_level") != mesh
        or route_gate.get("production_and_reference_cases_pass") is not True
        or route_gate.get("convergence_gates_pass") is not True
    ):
        raise PermissionError("WP07-D R1 route has not passed every production/reference and mesh gate for replay.")
    cases = route_gate.get("cases")
    if not isinstance(cases, Mapping) or set(cases) != set(EXPECTED_LEVELS):
        raise PermissionError("WP07-D R1 replay gate lacks complete M1/M2/M3 route coverage.")
    auth_root = Path("qualification/0_2_9/wp07d_formal_rebind_r1/authorizations")
    run_root = Path("qualification/0_2_9/wp07d_formal_rebind_r1/runs")
    for level in EXPECTED_LEVELS:
        case = cases[level]
        if not isinstance(case, Mapping) or case.get("status") != "PASS":
            raise PermissionError(f"WP07-D R1 replay gate case {route}/{level} is not PASS.")
        for role, kind, result_field, run_field, result_sha_field, run_sha_field in (
            ("primary", "PRIMARY_PRODUCTION", "production_result_path", "production_run_path", "production_result_sha256", "production_run_sha256"),
            ("reference", "INDEPENDENT_REFERENCE", "reference_result_path", "reference_run_path", "reference_result_sha256", "reference_run_sha256"),
        ):
            expected_output = (
                run_root / route / level / ("primary" if role == "primary" else "reference")
            )
            result_path = (root / str(case.get(result_field, ""))).resolve()
            run_path = (root / str(case.get(run_field, ""))).resolve()
            if (
                str(case.get(result_field, "")).replace("\\", "/")
                != (expected_output / "result.json").as_posix()
                or str(case.get(run_field, "")).replace("\\", "/")
                != (expected_output / "run.json").as_posix()
                or case.get("status") != "PASS"
                or not result_path.is_relative_to(root.resolve())
                or not run_path.is_relative_to(root.resolve())
                or not result_path.is_relative_to((root / run_root).resolve())
                or not run_path.is_relative_to((root / run_root).resolve())
                or not result_path.is_file()
                or not run_path.is_file()
                or _file_sha256(result_path) != case.get(result_sha_field)
                or _file_sha256(run_path) != case.get(run_sha_field)
            ):
                raise PermissionError(f"WP07-D R1 replay gate raw evidence hash failed for {route}/{level}/{role}.")
            run = _load_json(run_path)
            auth_path = (root / auth_root / kind / f"{route}_{level}.json").resolve()
            run_contract = run.get("formal_contract_provenance", {})
            if (
                not auth_path.is_relative_to(root.resolve())
                or not auth_path.is_file()
                or run.get("status") != "COMPLETED"
                or run.get("route") != route
                or run.get("mesh") != level
                or run.get("execution_kind") != kind
                or run.get("execution_sha") != execution_sha
                or run.get("binding_file_sha256") != expected_binding_sha
                or run.get("authorization_file_sha256") != _file_sha256(auth_path)
                or run.get("result_file_sha256") != _file_sha256(result_path)
                or not isinstance(run_contract, Mapping)
                or run_contract.get("file_sha256") != contract.get("file_sha256")
                or run_contract.get("revision") != contract.get("revision")
            ):
                raise PermissionError(f"WP07-D R1 replay gate run manifest failed for {route}/{level}/{role}.")
            result = _load_json(result_path)
            result_identity = result.get("formal_contract_provenance", result.get("wp07d_contract_provenance", {}))
            expected_result_status = (
                result.get("status") == "PASS"
                if role == "reference" or route == "ACTIVE_SET"
                else str(result.get("status", "")).lower() in {"pass", "success"}
            )
            if (
                not expected_result_status
                or result.get("execution_kind", result.get("wp07d_execution_kind")) != kind
                or not isinstance(result_identity, Mapping)
                or result_identity.get("file_sha256") != contract.get("file_sha256")
                or result_identity.get("revision") != contract.get("revision")
                or (
                    role == "reference"
                    and result.get("wp07d_observables", {}).get("source")
                    != "independent_numpy_scipy_reference_postprocessed"
                )
            ):
                raise PermissionError(f"WP07-D R1 replay gate raw result failed for {route}/{level}/{role}.")


def _validate_contact_r2_replay_gate(
    authorization: Mapping[str, Any],
    binding: Mapping[str, Any],
    binding_path: Path,
    *,
    route: str,
    mesh: str,
    execution_sha: str,
    root: Path,
) -> None:
    """Validate the R2 replay gate against raw M1/M2/M3 production/reference evidence."""

    relative_gate = CONTACT_REQUAL_R2_REPLAY_GATE_PATH.relative_to(ROOT).as_posix()
    if authorization.get("replay_gate_path") != relative_gate:
        raise PermissionError("WP07-D contact R2 replay authorization names the wrong gate.")
    gate_path = (root / relative_gate).resolve()
    if (
        not gate_path.is_relative_to(root.resolve())
        or not gate_path.is_file()
        or _file_sha256(gate_path) != authorization.get("replay_gate_file_sha256")
    ):
        raise PermissionError("WP07-D contact R2 replay gate is missing or has a hash mismatch.")
    gate = _load_json(gate_path)
    identity = formal_contract_identity(binding, root=root)
    decision = binding.get("owner_decision", {})
    requalification = binding.get("source_requalification", {})
    if (
        gate.get("artifact_id") != "QF-029-WP07-D-CONTACT-R2-PRE-REPLAY-GATE-001"
        or gate.get("status") != "PASS_REPLAY_GATES_EVALUATED"
        or gate.get("execution_sha") != execution_sha
        or gate.get("binding_path") != CONTACT_REQUAL_R2_BINDING_PATH.relative_to(ROOT).as_posix()
        or gate.get("binding_file_sha256") != _file_sha256(binding_path)
        or not isinstance(identity, Mapping)
        or gate.get("formal_contract_provenance", {}).get("file_sha256") != identity.get("file_sha256")
        or gate.get("owner_decision", {}).get("file_sha256") != decision.get("file_sha256")
        or gate.get("requalification_contract_sha256") != requalification.get("sha256")
        or gate.get("analysis_script_path") != "scripts/analyze_wp07d_formal_rebind_r1.py"
    ):
        raise PermissionError("WP07-D contact R2 replay gate provenance differs from the frozen campaign.")
    analysis_path = (root / str(gate.get("analysis_script_path"))).resolve()
    if (
        not analysis_path.is_relative_to(root.resolve())
        or not analysis_path.is_file()
        or _file_sha256(analysis_path) != gate.get("analysis_script_sha256")
    ):
        raise PermissionError("WP07-D contact R2 replay analyzer hash mismatch.")
    if mesh != binding["routes"][route].get("replay_level"):
        raise PermissionError("WP07-D contact R2 replay level differs from the frozen route.")
    route_gate = gate.get("routes", {}).get(route)
    if (
        not isinstance(route_gate, Mapping)
        or route_gate.get("status") != "PASS_READY_FOR_REPLAY"
        or route_gate.get("replay_level") != mesh
        or route_gate.get("production_and_reference_cases_pass") is not True
        or route_gate.get("convergence_gates_pass") is not True
    ):
        raise PermissionError("WP07-D contact R2 route is not ready for replay.")
    cases = route_gate.get("cases")
    if not isinstance(cases, Mapping) or set(cases) != set(EXPECTED_LEVELS):
        raise PermissionError("WP07-D contact R2 replay gate lacks complete M1/M2/M3 coverage.")
    run_root = Path(str(gate.get("run_root", "")))
    auth_root = Path(str(gate.get("authorization_root", "")))
    expected_run_root = CONTACT_REQUAL_R2_RUN_ROOT
    expected_auth_root = CONTACT_REQUAL_R2_AUTH_ROOT
    if run_root != expected_run_root or auth_root != expected_auth_root:
        raise PermissionError("WP07-D contact R2 replay gate uses an unexpected artifact root.")
    _validate_contact_r2_process_evidence(gate, root=root, run_root=run_root)
    for level in EXPECTED_LEVELS:
        case = cases[level]
        if not isinstance(case, Mapping) or case.get("status") != "PASS":
            raise PermissionError(f"WP07-D contact R2 replay dependency {route}/{level} is not PASS.")
        for role, kind in (("production", "PRIMARY_PRODUCTION"), ("reference", "INDEPENDENT_REFERENCE")):
            expected_dir = run_root / route / level / ("primary" if role == "production" else "reference")
            result_relative = str(case.get(f"{role}_result_path", "")).replace("\\", "/")
            run_relative = str(case.get(f"{role}_run_path", "")).replace("\\", "/")
            result_path = (root / result_relative).resolve()
            run_path = (root / run_relative).resolve()
            auth_path = (root / auth_root / kind / f"{route}_{level}.json").resolve()
            if (
                result_relative != (expected_dir / "result.json").as_posix()
                or run_relative != (expected_dir / "run.json").as_posix()
                or not result_path.is_relative_to(root.resolve())
                or not run_path.is_relative_to(root.resolve())
                or not result_path.is_file()
                or not run_path.is_file()
                or not auth_path.is_file()
                or _file_sha256(result_path) != case.get(f"{role}_result_sha256")
                or _file_sha256(run_path) != case.get(f"{role}_run_sha256")
            ):
                raise PermissionError(f"WP07-D contact R2 raw evidence hash/path mismatch for {route}/{level}/{role}.")
            run_record = _load_json(run_path)
            result_record = _load_json(result_path)
            if (
                run_record.get("status") != "COMPLETED"
                or run_record.get("route") != route
                or run_record.get("mesh") != level
                or run_record.get("execution_kind") != kind
                or run_record.get("execution_sha") != execution_sha
                or run_record.get("binding_file_sha256") != _file_sha256(binding_path)
                or run_record.get("authorization_file_sha256") != _file_sha256(auth_path)
                or run_record.get("result_file_sha256") != _file_sha256(result_path)
                or result_record.get("execution_kind", result_record.get("wp07d_execution_kind")) != kind
            ):
                raise PermissionError(f"WP07-D contact R2 run manifest mismatch for {route}/{level}/{role}.")
            if role == "reference" and (
                result_record.get("status") != "PASS"
                or result_record.get("wp07d_observables", {}).get("source")
                != "independent_numpy_scipy_reference_postprocessed"
            ):
                raise PermissionError(f"WP07-D contact R2 reference is not an accepted independent result for {route}/{level}.")


def _validate_contact_r2_process_evidence(
    gate: Mapping[str, Any], *, root: Path, run_root: Path
) -> None:
    """Require hash-bound, non-overlapping child-process records before replay."""

    process_maps = {
        "production": gate.get("production_process_manifests"),
        "reference": gate.get("reference_process_manifests"),
    }
    expected_keys = [f"{route}/{level}" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS]
    expected_order = [
        f"{route}/{level}/PRIMARY_PRODUCTION" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS
    ] + [
        f"{route}/{level}/INDEPENDENT_REFERENCE" for route in EXPECTED_ROUTES for level in EXPECTED_LEVELS
    ]
    if gate.get("sequential_process_order") != expected_order:
        raise PermissionError("WP07-D contact R2 process order is incomplete or not strictly phase-sequential.")

    intervals: list[tuple[datetime, datetime, str]] = []
    for role, kind in (("production", "PRIMARY_PRODUCTION"), ("reference", "INDEPENDENT_REFERENCE")):
        manifests = process_maps[role]
        if not isinstance(manifests, Mapping) or set(manifests) != set(expected_keys):
            raise PermissionError(f"WP07-D contact R2 {role} process manifests lack exact M1/M2/M3 route coverage.")
        folder = "primary" if role == "production" else "reference"
        for key in expected_keys:
            route, level = key.split("/")
            expected_path = run_root / route / level / folder / "runner_process.json"
            manifest = manifests[key]
            if not isinstance(manifest, Mapping) or manifest.get("path") != expected_path.as_posix():
                raise PermissionError(f"WP07-D contact R2 process manifest path mismatch for {key}/{role}.")
            manifest_path = (root / expected_path).resolve()
            if (
                not manifest_path.is_relative_to(root.resolve())
                or not manifest_path.is_file()
                or _file_sha256(manifest_path) != manifest.get("sha256")
            ):
                raise PermissionError(f"WP07-D contact R2 process manifest hash mismatch for {key}/{role}.")
            record = _load_json(manifest_path)
            label = f"{route}/{level}/{kind}"
            if (
                record.get("case") != label
                or record.get("route") != route
                or record.get("mesh") != level
                or record.get("execution_kind") != kind
                or record.get("execution_sha") != gate.get("execution_sha")
                or record.get("exit_code") != 0
                or record.get("invocation_error") is not None
                or manifest.get("exit_code") != 0
                or manifest.get("pid") != record.get("pid")
                or not isinstance(record.get("pid"), int)
                or record["pid"] <= 0
            ):
                raise PermissionError(f"WP07-D contact R2 process record failed identity/exit checks for {label}.")
            command = record.get("command")
            if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
                raise PermissionError(f"WP07-D contact R2 process command is missing for {label}.")
            for filename, digest_field in (
                ("runner.stdout.log", "stdout_sha256"),
                ("runner.stderr.log", "stderr_sha256"),
            ):
                log_path = manifest_path.parent / filename
                if not log_path.is_file() or _file_sha256(log_path) != record.get(digest_field):
                    raise PermissionError(f"WP07-D contact R2 process log hash mismatch for {label}: {filename}.")
            try:
                started = datetime.fromisoformat(str(record["started_utc"]).replace("Z", "+00:00"))
                ended = datetime.fromisoformat(str(record["ended_utc"]).replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError) as error:
                raise PermissionError(f"WP07-D contact R2 process timestamps are invalid for {label}.") from error
            if started.tzinfo is None or ended.tzinfo is None or ended < started:
                raise PermissionError(f"WP07-D contact R2 process interval is invalid for {label}.")
            intervals.append((started, ended, label))

    for previous, current in zip(intervals, intervals[1:]):
        if current[0] < previous[1] or current[0] < previous[0]:
            raise PermissionError(
                f"WP07-D contact R2 child process order overlaps or regresses: {previous[2]} then {current[2]}."
            )


def validate_formal_requalification_authorization(
    authorization: Mapping[str, Any],
    binding: Mapping[str, Any],
    binding_path: Path,
    *,
    route: str,
    mesh: str,
    execution_kind: str,
    root: Path = ROOT,
) -> None:
    """Validate one SHA-bound Owner authorization for a formal R1 case."""

    if binding.get("artifact_id") == CONTACT_REQUAL_R2_ARTIFACT_ID:
        identity = formal_contract_identity(binding, root=root)
        owner_reference = binding.get("owner_decision")
        source_reference = binding.get("source_requalification")
        if (
            identity is None
            or not isinstance(owner_reference, Mapping)
            or not isinstance(source_reference, Mapping)
        ):
            raise PermissionError(UNAUTHORIZED_EXECUTION)
        required_r2 = {
            "token": CONTACT_REQUAL_R2_TOKEN,
            "route": route,
            "mesh": mesh,
            "execution_kind": execution_kind,
            "binding_file_sha256": _file_sha256(binding_path),
            "formal_contract_file_sha256": identity["file_sha256"],
            "owner_decision_file_sha256": owner_reference["file_sha256"],
            "source_requalification_contract_file_sha256": source_reference["sha256"],
            "policy_digest": binding["governing"]["policy_digest"],
            "authorized_base_sha": binding["governing"]["authorized_base_sha"],
        }
        if any(authorization.get(key) != value for key, value in required_r2.items()):
            raise PermissionError("WP07-D contact R2 authorization does not bind the exact source and case.")
        expected_flags_r2 = {
            "PRIMARY_PRODUCTION": (True, False, False),
            "INDEPENDENT_REFERENCE": (False, True, False),
            "REPLAY": (True, False, True),
        }
        flags_r2 = expected_flags_r2.get(execution_kind)
        if flags_r2 is None or (
            authorization.get("structural_solves_allowed"),
            authorization.get("independent_references_allowed"),
            authorization.get("replay_allowed"),
        ) != flags_r2:
            raise PermissionError("WP07-D contact R2 case authorization enables an invalid execution class.")
        if authorization.get("wp07e_allowed") is not False:
            raise PermissionError("WP07-D contact R2 authorization must not enable WP07-E.")
        if execution_kind == "REPLAY":
            _validate_formal_replay_gate(
                authorization,
                binding,
                binding_path,
                route=route,
                mesh=mesh,
                execution_sha=str(authorization.get("execution_sha", "")),
                root=root,
            )
        elif authorization.get("replay_gate_path") is not None or authorization.get("replay_gate_file_sha256") is not None:
            raise PermissionError("WP07-D contact R2 non-replay authorization cannot carry replay-gate fields.")
        validate_authorized_execution_source(authorization)
        return
    if binding.get("artifact_id") != FORMAL_REBIND_R1_ARTIFACT_ID:
        return
    identity = formal_contract_identity(binding, root=root)
    owner_reference = binding.get("owner_decision")
    if identity is None or not isinstance(owner_reference, Mapping):
        raise PermissionError(UNAUTHORIZED_EXECUTION)
    required = {
        "token": FORMAL_REBIND_R1_TOKEN,
        "route": route,
        "mesh": mesh,
        "execution_kind": execution_kind,
        "binding_file_sha256": _file_sha256(binding_path),
        "formal_contract_file_sha256": identity["file_sha256"],
        "owner_decision_file_sha256": owner_reference["file_sha256"],
        "authorized_base_sha": binding["governing"]["authorized_base_sha"],
    }
    if any(authorization.get(key) != value for key, value in required.items()):
        raise PermissionError("WP07-D R1 authorization does not bind the exact contract, decision, route, and source.")
    expected_flags = {
        "PRIMARY_PRODUCTION": (True, False, False),
        "INDEPENDENT_REFERENCE": (False, True, False),
        "REPLAY": (True, False, True),
    }
    flags = expected_flags.get(execution_kind)
    actual_flags = (
        authorization.get("structural_solves_allowed"),
        authorization.get("independent_references_allowed"),
        authorization.get("replay_allowed"),
    )
    if flags is None or actual_flags != flags:
        raise PermissionError("WP07-D R1 per-case authorization enables the wrong execution class.")
    if authorization.get("wp07e_allowed") is not False:
        raise PermissionError("WP07-D R1 authorization cannot enable WP07-E.")
    if execution_kind == "REPLAY":
        if mesh != binding["routes"][route].get("replay_level"):
            raise PermissionError("WP07-D R1 replay authorization is not bound to the route's frozen replay level.")
        execution_sha = authorization.get("execution_sha")
        if not isinstance(execution_sha, str):
            raise PermissionError("WP07-D R1 replay authorization has no exact execution source SHA.")
        _validate_formal_replay_gate(
            authorization,
            binding,
            binding_path,
            route=route,
            mesh=mesh,
            execution_sha=execution_sha,
            root=root,
        )
    elif authorization.get("replay_gate_path") is not None or authorization.get("replay_gate_file_sha256") is not None:
        raise PermissionError("WP07-D R1 non-replay authorization must not carry a replay gate exemption.")
    validate_authorized_execution_source(authorization)


def _canonical_sha256(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(rendered).hexdigest()


def _validate_contact_requalification_r2_binding(binding: Mapping[str, Any], *, root: Path) -> None:
    if (
        binding.get("artifact_id") != CONTACT_REQUAL_R2_ARTIFACT_ID
        or binding.get("status") != "FROZEN_FAIL_CLOSED_PER_CASE_AUTHORIZATION_REQUIRED"
        or binding.get("_binding_path") != CONTACT_REQUAL_R2_BINDING_PATH.relative_to(ROOT).as_posix()
    ):
        raise ValueError("WP07-D contact R2 binding identity or fail-closed status is invalid.")
    descriptor_path = (root / CONTACT_REQUAL_R2_BINDING_PATH.relative_to(ROOT)).resolve()
    if not descriptor_path.is_relative_to(root.resolve()) or not descriptor_path.is_file():
        raise ValueError("WP07-D contact R2 execution binding file is missing.")
    descriptor = _load_json(descriptor_path)
    parent = descriptor.get("extends_binding", {})
    parent_path = (root / str(parent.get("path", ""))).resolve()
    if (
        not parent_path.is_relative_to(root.resolve())
        or not parent_path.is_file()
        or _file_sha256(parent_path) != parent.get("sha256")
        or parent.get("sha256") != "ef223ee40ed1d4d9b1c60a20c2ee2958ea4e37acd8c0265058a4a12218fcf52d"
    ):
        raise ValueError("WP07-D contact R2 parent binding hash/provenance mismatch.")
    contract_ref = descriptor.get("requalification_contract", {})
    contract_path = (root / str(contract_ref.get("path", ""))).resolve()
    decision_ref = descriptor.get("owner_decision", {})
    decision_path = (root / str(decision_ref.get("path", ""))).resolve()
    if (
        not contract_path.is_relative_to(root.resolve())
        or not contract_path.is_file()
        or _file_sha256(contract_path) != contract_ref.get("sha256")
        or contract_ref.get("sha256") != "7045a9e2afb7d84c033ae1b4e473a0e6fd5c5efa02880f0d70c0262eb9c247e0"
        or not decision_path.is_relative_to(root.resolve())
        or not decision_path.is_file()
        or _file_sha256(decision_path) != decision_ref.get("sha256")
        or decision_ref.get("sha256") != "e6de753a7a433da9f56ee724c74e389126dda79e278cf02ebce20509aabb0a24"
    ):
        raise ValueError("WP07-D contact R2 addendum or Owner decision hash mismatch.")
    contract = _load_json(contract_path)
    decision = _load_json(decision_path)
    if (
        contract.get("artifact_id") != "QF-029-WP07-D-CONTACT-MECHANICS-REQUALIFICATION-R2-001"
        or contract.get("status") != "FROZEN_FOR_SHA_BOUND_OWNER_AUTHORIZED_REQUALIFICATION"
        or contract.get("governing", {}).get("base_sha") != "b2485f98260c7ca9892997eefa3a327637d83cd3"
        or contract.get("governing", {}).get("policy_digest")
        != "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
        or contract.get("parent", {}).get("formal_contract_sha256")
        != "b923f560a0d6719ee149ea31f912f46b6b7d32600df1cd7b80bf70a40562d7d7"
        or contract.get("authorization", {}).get("exact_execution_sha_required") is not True
        or contract.get("formal_points_awarded") != 0
    ):
        raise ValueError("WP07-D contact R2 requalification contract is malformed or out of scope.")
    if (
        decision.get("status") != "AUTHORIZED_FOR_SOURCE_BOUND_REQUALIFICATION"
        or decision.get("decisions", {}).get("OWNER_AUTHORIZES_WP07D_M1_M2_M3_REQUALIFICATION") is not True
        or decision.get("decisions", {}).get("OWNER_AUTHORIZES_WP07D_INDEPENDENT_REFERENCES") is not True
        or decision.get("decisions", {}).get("OWNER_AUTHORIZES_WP07D_CONTRACT_REQUIRED_REPLAYS") is not True
        or decision.get("decisions", {}).get("OWNER_AUTHORIZES_WP07E_OR_WP08E") is not False
        or decision.get("decisions", {}).get("OWNER_AWARDS_POINTS") is not False
        or decision.get("decisions", {}).get("OWNER_AUTHORIZES_MERGE_OR_PUSH") is not False
    ):
        raise PermissionError("Recorded Owner decision does not authorize exactly the WP07-D requalification scope.")

    identity = formal_contract_identity(binding, root=root)
    formal_contract = _load_json(root / str(identity["path"])) if identity else {}
    if (
        identity is None
        or identity.get("file_sha256") != contract.get("parent", {}).get("formal_contract_sha256")
        or formal_contract.get("status") != "FROZEN_FOR_OWNER_AUTHORIZED_FORMAL_REQUALIFICATION"
    ):
        raise ValueError("WP07-D contact R2 does not bind the immutable formal R1 physics contract.")
    digest_fields = {
        "thresholds": "thresholds_canonical_sha256",
        "physical_benchmark": "physical_benchmark_canonical_sha256",
        "loading": "loading_canonical_sha256",
        "mesh_levels": "mesh_levels_canonical_sha256",
    }
    for section, digest_field in digest_fields.items():
        if _canonical_sha256(formal_contract.get(section)) != contract.get("frozen_contract_digests", {}).get(digest_field):
            raise ValueError(f"WP07-D contact R2 changed frozen parent-contract section {section}.")

    governing = binding.get("governing", {})
    if (
        governing.get("authorized_base_sha") != "b2485f98260c7ca9892997eefa3a327637d83cd3"
        or governing.get("policy_digest") != contract["governing"]["policy_digest"]
    ):
        raise ValueError("WP07-D contact R2 governing base or policy digest mismatch.")
    execution_sha = _git("rev-parse", "HEAD")
    for sha in (governing["authorized_base_sha"], contract["governing"]["contact_mechanics_remediation_commit"]):
        if subprocess.run(
            ["git", "merge-base", "--is-ancestor", sha, execution_sha],
            cwd=root,
            check=False,
            capture_output=True,
        ).returncode:
            raise ValueError(f"WP07-D contact R2 execution is not descended from required source {sha}.")
    source_diff = subprocess.run(
        ["git", "diff", "--binary", governing["authorized_base_sha"], execution_sha, "--", "src"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    lineage = binding.get("source_lineage_disclosure", {})
    if (
        hashlib.sha256(source_diff).hexdigest()
        != lineage.get("production_source_diff_sha256_since_governing_base")
        or lineage.get("authorized_governing_base_sha") != governing["authorized_base_sha"]
        or lineage.get("changed_production_source_paths_since_governing_base")
        != ["src/solveur/contact/slip_root.py", "src/solveur/contact/solver.py"]
        or lineage.get("requalification_adds_mechanics_change") is not True
    ):
        raise ValueError("WP07-D contact R2 production-source lineage differs from the reviewed correction.")
    if binding.get("routes") != _load_json(parent_path).get("routes"):
        raise ValueError("WP07-D contact R2 changed a frozen route or replay-level definition.")
    if binding.get("mesh_definition") != _load_json(parent_path).get("mesh_definition"):
        raise ValueError("WP07-D contact R2 changed the frozen M1/M2/M3 mesh hierarchy.")
    if binding.get("authorization", {}).get("token") != CONTACT_REQUAL_R2_TOKEN or any(
        binding.get("authorization", {}).get(field) is not False
        for field in ("structural_solves_allowed", "independent_references_allowed", "replay_allowed", "wp07e_allowed")
    ):
        raise ValueError("WP07-D contact R2 static binding must remain fail-closed before per-case authorization.")
    invariants = binding.get("invariants", {})
    if (
        invariants.get("production_mechanics_changed") is not True
        or invariants.get("thresholds_changed") is not False
        or invariants.get("loads_changed") is not False
        or invariants.get("mesh_changed") is not False
        or invariants.get("fallback_policy_changed") is not False
    ):
        raise ValueError("WP07-D contact R2 change classification is inconsistent.")


def validate_binding(binding: Mapping[str, Any], *, root: Path = ROOT) -> None:
    """Reject any binding that changes frozen physics or bypasses authorization."""

    binding_id = binding.get("artifact_id")
    if binding_id == CONTACT_REQUAL_R2_ARTIFACT_ID:
        _validate_contact_requalification_r2_binding(binding, root=root)
        return
    if binding_id == FORMAL_REBIND_R1_ARTIFACT_ID:
        _validate_formal_rebind_r1_binding(binding, root=root)
        return
    if binding_id not in {
        "QF-029-WP07-D-EXECUTION-BINDING-001",
        "QF-029-WP07-D-EXECUTION-BINDING-REMEDIATION-R1-001",
        "QF-029-WP07-D-EXECUTION-BINDING-SURFACE-LUMPED-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-GRADED-TET4-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-GRADED-RAISED-HIERARCHY-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-LOCAL-CONTACT-REFINEMENT-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-FOCUSED-LOCAL-REFINEMENT-EXPERIMENT-001",
    }:
        raise ValueError("Unexpected WP07-D execution binding identity.")
    if binding.get("status") != "READY_FOR_OWNER_AUTHORIZATION":
        raise ValueError("WP07-D binding must remain ready for Owner authorization.")
    if binding.get("work_package") != "WP07-D":
        raise ValueError("WP07-D execution binding has the wrong work package.")

    contract = binding.get("preparation_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("WP07-D binding lacks preparation-contract provenance.")
    expected_path = "qualification/0_2_9/wp07d_structural_vnv_contract.json"
    if contract.get("path") != expected_path or contract.get("preserved_preparation_only") is not True:
        raise ValueError("WP07-D binding must preserve the preparation-only contract.")
    contract_path = root / expected_path
    if _file_sha256(contract_path) != contract.get("file_sha256"):
        raise ValueError("WP07-D preparation-contract file hash drifted.")
    original = _load_json(contract_path)
    execution = original.get("execution_policy")
    if (
        original.get("status") != "PREPARATION_ONLY"
        or not isinstance(execution, Mapping)
        or execution.get("structural_solves_allowed") is not False
        or execution.get("status") != "PENDING_GOVERNING_BRANCH_INTEGRATION"
    ):
        raise ValueError("WP07-D historical preparation contract was modified.")

    governing = binding.get("governing")
    if not isinstance(governing, Mapping):
        raise ValueError("WP07-D binding lacks governing provenance.")
    required_base = governing.get("authorized_base_sha")
    if not isinstance(required_base, str) or len(required_base) != 40:
        raise ValueError("WP07-D binding has no valid governing base SHA.")
    current = _git("rev-parse", "HEAD")
    descendant = subprocess.run(
        ["git", "merge-base", "--is-ancestor", required_base, current],
        cwd=root,
        check=False,
        capture_output=True,
    ).returncode == 0
    if not descendant:
        raise ValueError("WP07-D execution source is not based on the authorized governing SHA.")
    if governing.get("policy_digest") != "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac":
        raise ValueError("WP07-D governing policy digest mismatch.")

    routes = binding.get("routes")
    if not isinstance(routes, Mapping) or tuple(routes) != EXPECTED_ROUTES:
        raise ValueError("WP07-D binding must declare ACTIVE_SET then PENALTY routes.")
    for name in EXPECTED_ROUTES:
        route = routes[name]
        if not isinstance(route, Mapping) or tuple(route.get("mesh_levels", ())) != EXPECTED_LEVELS:
            raise ValueError(f"WP07-D {name} mesh scope is incomplete.")
        if route.get("updated_search") is not False or route.get("finite_sliding") is not False:
            raise ValueError(f"WP07-D {name} exceeds initial-search scope.")
        if route.get("fallback_allowed") is not False:
            raise ValueError(f"WP07-D {name} fallback policy drifted.")
    penalty = routes["PENALTY"]
    required_penalty = {
        "analysis_type": "geometric_nonlinear_static",
        "load_increments": 8,
        "adaptive_load_steps": False,
        "linear_solver": "minres",
        "linear_preconditioner": "jacobi",
        "linear_rtol": 1e-11,
        "linear_atol": 1e-14,
        "linear_maxiter": 10000,
        "linear_direct_fallback": False,
        "line_search": "existing",
        "floor_aware_termination": True,
    }
    if any(penalty.get(key) != value for key, value in required_penalty.items()):
        raise ValueError("WP07-D penalty execution policy is not the frozen governing policy.")
    integration = penalty.get("penalty_integration", "nodal")
    if binding_id in {
        "QF-029-WP07-D-EXECUTION-BINDING-SURFACE-LUMPED-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-GRADED-TET4-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-GRADED-RAISED-HIERARCHY-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-LOCAL-CONTACT-REFINEMENT-EXPERIMENT-001",
        "QF-029-WP07-D-EXECUTION-BINDING-FOCUSED-LOCAL-REFINEMENT-EXPERIMENT-001",
    }:
        if integration != "surface_lumped":
            raise ValueError("WP07-D surface-lumped experiment must explicitly bind surface_lumped integration.")
    elif integration != "nodal":
        raise ValueError("Formal WP07-D bindings must retain historical nodal penalty integration.")

    authorization = binding.get("authorization")
    if not isinstance(authorization, Mapping):
        raise ValueError("WP07-D binding lacks authorization controls.")
    if authorization.get("required") is not True or authorization.get("structural_solves_allowed") is not False:
        raise ValueError("WP07-D binding must fail closed before explicit Owner authorization.")
    if any(value is not False for key, value in authorization.items() if key.endswith("_allowed")):
        raise ValueError("WP07-D binding enables execution without Owner authorization.")
    expected_token = (
        {
            "QF-029-WP07-D-EXECUTION-BINDING-GRADED-RAISED-HIERARCHY-EXPERIMENT-001":
                "OWNER_AUTHORIZED_WP07D_GRADED_RAISED_HIERARCHY_EXPERIMENT",
            "QF-029-WP07-D-EXECUTION-BINDING-GRADED-TET4-EXPERIMENT-001":
                "OWNER_AUTHORIZED_WP07D_GRADED_TET4_EXPERIMENT",
            "QF-029-WP07-D-EXECUTION-BINDING-SURFACE-LUMPED-EXPERIMENT-001":
                "OWNER_AUTHORIZED_WP07D_SURFACE_LUMPED_EXPERIMENT",
            "QF-029-WP07-D-EXECUTION-BINDING-LOCAL-CONTACT-REFINEMENT-EXPERIMENT-001":
                "OWNER_AUTHORIZED_WP07D_LOCAL_CONTACT_REFINEMENT_EXPERIMENT",
            "QF-029-WP07-D-EXECUTION-BINDING-FOCUSED-LOCAL-REFINEMENT-EXPERIMENT-001":
                "OWNER_AUTHORIZED_WP07D_FOCUSED_LOCAL_REFINEMENT_EXPERIMENT",
        }.get(binding_id, "OWNER_AUTHORIZED_WP07D_STRUCTURAL_EXECUTION")
    )
    if authorization.get("token") != expected_token:
        raise ValueError("WP07-D binding has an unexpected authorization token.")

    invariants = binding.get("invariants")
    if not isinstance(invariants, Mapping):
        raise ValueError("WP07-D binding lacks invariant declarations.")
    if binding_id == "QF-029-WP07-D-EXECUTION-BINDING-001":
        if any(value is not False for value in invariants.values()):
            raise ValueError("WP07-D binding records an unauthorized mechanics or threshold change.")
    elif binding_id == "QF-029-WP07-D-EXECUTION-BINDING-REMEDIATION-R1-001":
        remediation = binding.get("remediation")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "FIXED_SEARCH_PENALTY_CONTACT_ACTIVATION"
            or invariants.get("production_mechanics_changed") is not True
        ):
            raise ValueError("WP07-D remediation binding lacks authorized mechanics provenance.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key != "production_mechanics_changed"
        ):
            raise ValueError("WP07-D remediation binding changes more than the authorized contact activation scope.")
    elif binding_id == "QF-029-WP07-D-EXECUTION-BINDING-SURFACE-LUMPED-EXPERIMENT-001":
        remediation = binding.get("remediation")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "SURFACE_LUMPED_PENALTY_BY_REFERENCE_TRIBUTARY_AREA"
            or invariants.get("production_mechanics_changed") is not True
        ):
            raise ValueError("WP07-D surface-lumped experiment lacks explicit mechanics provenance.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key != "production_mechanics_changed"
        ):
            raise ValueError("WP07-D surface-lumped experiment changes more than its declared mechanics scope.")
    elif binding_id == "QF-029-WP07-D-EXECUTION-BINDING-GRADED-TET4-EXPERIMENT-001":
        remediation = binding.get("remediation")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "GRADED_TET4_CLAMP_CONTACT_EDGE_REFINEMENT"
            or invariants.get("production_mechanics_changed") is not True
        ):
            raise ValueError("WP07-D graded-TET4 experiment lacks explicit mechanics provenance.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key != "production_mechanics_changed"
        ):
            raise ValueError("WP07-D graded-TET4 experiment changes more than its declared mechanics scope.")
        mesh_definition = binding.get("mesh_definition")
        if (
            not isinstance(mesh_definition, Mapping)
            or mesh_definition.get("family") != "TET4"
            or mesh_definition.get("topology") != "frozen six-TET structured-cell pattern"
            or mesh_definition.get("coordinate_grading_exponent") != 1.5
            or tuple(mesh_definition.get("graded_axes", ())) != ("x", "z")
            or mesh_definition.get("ungraded_axis") != "y"
            or mesh_definition.get("physical_bounds_preserved") is not True
        ):
            raise ValueError("WP07-D graded-TET4 mesh definition drifted from the reviewed experiment.")
    elif binding_id == "QF-029-WP07-D-EXECUTION-BINDING-FOCUSED-LOCAL-REFINEMENT-EXPERIMENT-001":
        remediation = binding.get("remediation")
        mesh_definition = binding.get("mesh_definition")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "FOCUSED_LOCAL_TET4_CONTACT_REFINEMENT"
            or invariants.get("production_mechanics_changed") is not False
            or invariants.get("mesh_changed") is not True
            or not isinstance(mesh_definition, Mapping)
            or mesh_definition.get("family") != "TET4"
            or mesh_definition.get("topology") != "frozen six-TET structured-cell pattern"
            or mesh_definition.get("coordinate_grading_exponent") != 1.5
            or tuple(mesh_definition.get("graded_axes", ())) != ("x", "z")
            or mesh_definition.get("ungraded_axis") != "y"
            or mesh_definition.get("physical_bounds_preserved") is not True
        ):
            raise ValueError("WP07-D focused local-refinement experiment lacks its exact mesh binding.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key != "mesh_changed"
        ):
            raise ValueError("WP07-D focused local refinement changes a frozen non-mesh input.")
        expected_cells = {
            "M1": [8, 8, 4],
            "M2": [16, 16, 8],
            "M3": [32, 16, 16],
        }
        if mesh_definition.get("cell_counts_by_level") != expected_cells:
            raise ValueError("WP07-D focused local-refinement hierarchy drifted.")
        from scripts.prepare_wp07d_structural_vnv import focused_local_contact_refinement_axis_fractions

        expected_axes = {
            axis: list(values)
            for axis, values in focused_local_contact_refinement_axis_fractions().items()
        }
        axes_by_level = mesh_definition.get("axis_fractions_by_level")
        if not isinstance(axes_by_level, Mapping) or dict(axes_by_level) != {"M3": expected_axes}:
            raise ValueError("WP07-D focused local-refinement coordinate fractions drifted.")
        if mesh_definition.get("nested_in_m2") is not True:
            raise ValueError("WP07-D focused local M3 must be nested in the M2 coordinate grid.")
        _validate_focused_local_comparison_baseline(binding, root=root, required_base=required_base)
    elif binding_id == "QF-029-WP07-D-EXECUTION-BINDING-LOCAL-CONTACT-REFINEMENT-EXPERIMENT-001":
        remediation = binding.get("remediation")
        mesh_definition = binding.get("mesh_definition")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "LOCAL_TET4_CONTACT_FRONT_REFINEMENT"
            or invariants.get("production_mechanics_changed") is not False
            or invariants.get("mesh_changed") is not True
            or not isinstance(mesh_definition, Mapping)
            or mesh_definition.get("family") != "TET4"
            or mesh_definition.get("topology") != "frozen six-TET structured-cell pattern"
            or mesh_definition.get("coordinate_grading_exponent") != 1.5
            or tuple(mesh_definition.get("graded_axes", ())) != ("x", "z")
            or mesh_definition.get("ungraded_axis") != "y"
            or mesh_definition.get("physical_bounds_preserved") is not True
        ):
            raise ValueError("WP07-D local-refinement experiment lacks its exact mesh binding.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key not in {"mesh_changed"}
        ):
            raise ValueError("WP07-D local refinement changes a frozen non-mesh input.")
        expected_cells = {
            "M1": [8, 8, 4],
            "M2": [16, 16, 8],
            "M3": [24, 16, 12],
        }
        if mesh_definition.get("cell_counts_by_level") != expected_cells:
            raise ValueError("WP07-D local-refinement cell hierarchy drifted.")
        from scripts.prepare_wp07d_structural_vnv import local_contact_refinement_axis_fractions

        expected_axes = {
            axis: list(values)
            for axis, values in local_contact_refinement_axis_fractions().items()
        }
        axes_by_level = mesh_definition.get("axis_fractions_by_level")
        if not isinstance(axes_by_level, Mapping) or dict(axes_by_level) != {"M3": expected_axes}:
            raise ValueError("WP07-D local-refinement coordinate fractions drifted.")
        reused_levels = binding.get("reused_diagnostic_levels")
        expected_sources = {
            "M1": (
                "wp07d_graded_tet4_experiment",
                "M3",
                "qualification/0_2_9/wp07d_execution_binding_graded_tet4_experiment.json",
            ),
            "M2": (
                "wp07d_raised_hierarchy_experiment",
                "M3",
                "qualification/0_2_9/wp07d_execution_binding_graded_raised_hierarchy_experiment.json",
            ),
        }
        if not isinstance(reused_levels, Mapping) or tuple(reused_levels) != ("M1", "M2"):
            raise ValueError("WP07-D local refinement must bind reused M1/M2 evidence.")
        for level, (source_experiment, source_mesh, source_binding_path) in expected_sources.items():
            level_record = reused_levels[level]
            route_records = level_record.get("routes") if isinstance(level_record, Mapping) else None
            if (
                not isinstance(level_record, Mapping)
                or level_record.get("source_experiment") != source_experiment
                or level_record.get("source_mesh") != source_mesh
                or not isinstance(route_records, Mapping)
                or tuple(route_records) != EXPECTED_ROUTES
            ):
                raise ValueError(f"WP07-D local-refinement reused provenance drifted for {level}.")
            expected_counts = level_record.get("source_mesh_cell_counts")
            source_binding_digest = level_record.get("source_binding_sha256")
            if (
                expected_counts != expected_cells[level]
                or level_record.get("source_binding_path") != source_binding_path
                or not isinstance(source_binding_digest, str)
                or _file_sha256(root / source_binding_path) != source_binding_digest
            ):
                raise ValueError(f"WP07-D local-refinement source mesh counts drifted for {level}.")
            for route in EXPECTED_ROUTES:
                role_record = route_records[route]
                if not isinstance(role_record, Mapping):
                    raise ValueError(f"WP07-D local-refinement provenance is malformed for {route}/{level}.")
                for role, path_key, digest_key in (
                    ("production", "production_result_path", "production_result_sha256"),
                    (
                        "independent_reference",
                        "independent_reference_result_path",
                        "independent_reference_result_sha256",
                    ),
                ):
                    expected_path = (
                        f"qualification/0_2_9/wp07d_local_contact_refinement/reused/{level}/"
                        f"{route}/{role}/result.json"
                    )
                    relative_path = role_record.get(path_key)
                    digest = role_record.get(digest_key)
                    if relative_path != expected_path or not isinstance(digest, str):
                        raise ValueError(f"WP07-D local-refinement evidence path drifted for {route}/{level}/{role}.")
                    evidence_path = (root / relative_path).resolve()
                    if not evidence_path.is_relative_to(root.resolve()) or _file_sha256(evidence_path) != digest:
                        raise ValueError(f"WP07-D local-refinement evidence hash mismatch for {route}/{level}/{role}.")
                run_path = role_record.get("production_run_path")
                run_digest = role_record.get("production_source_run_sha256")
                run_execution_sha = role_record.get("source_execution_sha")
                reference_execution_sha = role_record.get("source_reference_execution_sha")
                expected_run_path = (
                    f"qualification/0_2_9/wp07d_local_contact_refinement/reused/{level}/"
                    f"{route}/production/run.json"
                )
                if (
                    run_path != expected_run_path
                    or not isinstance(run_digest, str)
                    or not isinstance(run_execution_sha, str)
                    or len(run_execution_sha) != 40
                    or reference_execution_sha != "NOT_RECORDED_BY_SOURCE_RUNNER"
                ):
                    raise ValueError(f"WP07-D local-refinement source-run provenance is malformed for {route}/{level}.")
                source_run_path = (root / run_path).resolve()
                if not source_run_path.is_relative_to(root.resolve()) or _file_sha256(source_run_path) != run_digest:
                    raise ValueError(f"WP07-D local-refinement source-run hash mismatch for {route}/{level}.")
                source_run = _load_json(source_run_path)
                result_path = root / role_record["production_result_path"]
                reference_path = root / role_record["independent_reference_result_path"]
                production_result = _load_json(result_path)
                reference_result = _load_json(reference_path)
                if (
                    source_run.get("execution_sha") != run_execution_sha
                    or source_run.get("route") != route
                    or source_run.get("mesh") != source_mesh
                    or source_run.get("mesh_cell_counts") != expected_counts
                    or source_run.get("coordinate_grading_exponent") != 1.5
                    or source_run.get("binding_file_sha256") != source_binding_digest
                    or source_run.get("result_file_sha256") != _file_sha256(result_path)
                    or (route == "PENALTY" and source_run.get("penalty_integration") != "surface_lumped")
                    or production_result.get("status") not in {"PASS", "success", "COMPLETED"}
                    or reference_result.get("status") != "PASS"
                    or reference_result.get("mesh_cell_counts") != expected_counts
                    or reference_result.get("coordinate_grading_exponent") != 1.5
                    or not isinstance(production_result.get("wp07d_observables"), Mapping)
                    or not isinstance(reference_result.get("wp07d_observables"), Mapping)
                ):
                    raise ValueError(f"WP07-D local-refinement source-run metadata mismatch for {route}/{level}.")
                if _git("rev-parse", "--verify", f"{run_execution_sha}^{{commit}}") != run_execution_sha:
                    raise ValueError(f"WP07-D local-refinement source SHA is not canonical for {route}/{level}.")
                source_ancestry = subprocess.run(
                    ["git", "merge-base", "--is-ancestor", required_base, run_execution_sha],
                    cwd=root,
                    check=False,
                    capture_output=True,
                )
                if source_ancestry.returncode != 0:
                    raise ValueError(f"WP07-D local-refinement source SHA is outside the governing lineage for {route}/{level}.")
    else:
        remediation = binding.get("remediation")
        mesh_definition = binding.get("mesh_definition")
        if (
            not isinstance(remediation, Mapping)
            or remediation.get("authorized") is not True
            or remediation.get("scope") != "RAISED_GRADED_TET4_HIERARCHY"
            or invariants.get("production_mechanics_changed") is not True
            or invariants.get("mesh_changed") is not True
            or not isinstance(mesh_definition, Mapping)
            or mesh_definition.get("family") != "TET4"
            or mesh_definition.get("topology") != "frozen six-TET structured-cell pattern"
            or mesh_definition.get("coordinate_grading_exponent") != 1.5
            or tuple(mesh_definition.get("graded_axes", ())) != ("x", "z")
            or mesh_definition.get("ungraded_axis") != "y"
            or mesh_definition.get("physical_bounds_preserved") is not True
        ):
            raise ValueError("WP07-D raised graded-TET4 hierarchy lacks its exact mesh/remediation binding.")
        if any(
            value is not False
            for key, value in invariants.items()
            if key not in {"production_mechanics_changed", "mesh_changed"}
        ):
            raise ValueError("WP07-D raised hierarchy changes additional frozen inputs.")
        expected_cells = {
            "M1": [4, 4, 2],
            "M2": [8, 8, 4],
            "M3": [16, 16, 8],
        }
        if mesh_definition.get("cell_counts_by_level") != expected_cells:
            raise ValueError("WP07-D raised mesh hierarchy differs from the reviewed sequence.")
        reused_levels = binding.get("reused_diagnostic_levels")
        expected_source_mesh = {"M1": "M2", "M2": "M3"}
        if not isinstance(reused_levels, Mapping):
            raise ValueError("WP07-D raised hierarchy does not bind its reused lower-level evidence.")
        for new_level, source_mesh in expected_source_mesh.items():
            level_record = reused_levels.get(new_level)
            route_records = level_record.get("routes") if isinstance(level_record, Mapping) else None
            if (
                not isinstance(level_record, Mapping)
                or level_record.get("source_experiment") != "wp07d_graded_tet4_experiment"
                or level_record.get("source_mesh") != source_mesh
                or not isinstance(route_records, Mapping)
                or tuple(route_records) != EXPECTED_ROUTES
            ):
                raise ValueError(f"WP07-D raised hierarchy has invalid reused evidence for {new_level}.")
            for route in EXPECTED_ROUTES:
                role_record = route_records[route]
                if not isinstance(role_record, Mapping):
                    raise ValueError(f"WP07-D reused evidence is malformed for {route}/{new_level}.")
                for role, path_key, digest_key in (
                    ("production", "production_result_path", "production_result_sha256"),
                    (
                        "independent_reference",
                        "independent_reference_result_path",
                        "independent_reference_result_sha256",
                    ),
                ):
                    expected_path = (
                        f"qualification/0_2_9/wp07d_graded_tet4_experiment/runs/"
                        f"{route}_{source_mesh}/{role}/result.json"
                    )
                    relative_path = role_record.get(path_key)
                    digest = role_record.get(digest_key)
                    if relative_path != expected_path or not isinstance(digest, str):
                        raise ValueError(f"WP07-D reused evidence provenance drifted for {route}/{new_level}.")
                    evidence_path = (root / relative_path).resolve()
                    if not evidence_path.is_relative_to(root.resolve()) or _file_sha256(evidence_path) != digest:
                        raise ValueError(f"WP07-D reused evidence hash mismatch for {route}/{new_level}/{role}.")


def penalty_integration_from_authorization(
    binding: Mapping[str, Any], authorization: Mapping[str, Any], *, route: str
) -> str:
    """Bind a penalty-integration mode to the reviewed route and authorization."""

    if route != "PENALTY":
        if "penalty_integration" in authorization:
            raise PermissionError("WP07-D active-set authorization must not declare penalty integration.")
        return "nodal"
    routes = binding.get("routes")
    if not isinstance(routes, Mapping) or not isinstance(routes.get("PENALTY"), Mapping):
        raise PermissionError("WP07-D binding has no penalty-route definition.")
    expected = str(routes["PENALTY"].get("penalty_integration", "nodal"))
    declared = str(authorization.get("penalty_integration", "nodal"))
    if expected not in {"nodal", "surface_lumped"} or declared != expected:
        raise PermissionError("WP07-D authorization penalty integration differs from the bound route.")
    return expected


def coordinate_grading_from_authorization(
    binding: Mapping[str, Any], authorization: Mapping[str, Any]
) -> float:
    """Bind the declared coordinate grading to the reviewed experiment."""

    mesh = binding.get("mesh_definition")
    expected = 1.0 if not isinstance(mesh, Mapping) else mesh.get("coordinate_grading_exponent", 1.0)
    try:
        expected_value = float(expected)
        declared_value = float(authorization.get("coordinate_grading_exponent", 1.0))
    except (TypeError, ValueError) as error:
        raise PermissionError("WP07-D coordinate grading is invalid.") from error
    if expected_value < 1.0 or declared_value != expected_value:
        raise PermissionError("WP07-D authorization coordinate grading differs from the bound mesh.")
    return expected_value


def mesh_cell_counts_from_authorization(
    binding: Mapping[str, Any], authorization: Mapping[str, Any], *, level: str
) -> tuple[int, int, int] | None:
    """Bind optional experimental cell counts to one exact hierarchy level."""

    mesh = binding.get("mesh_definition")
    counts_by_level = mesh.get("cell_counts_by_level") if isinstance(mesh, Mapping) else None
    declared = authorization.get("mesh_cell_counts")
    if not isinstance(counts_by_level, Mapping):
        if declared is not None:
            raise PermissionError("WP07-D authorization declares cell counts absent from the binding.")
        return None
    expected = counts_by_level.get(level)
    if (
        not isinstance(expected, list)
        or len(expected) != 3
        or any(type(item) is not int or item <= 0 for item in expected)
        or not isinstance(declared, list)
        or declared != expected
    ):
        raise PermissionError("WP07-D authorization cell counts differ from the bound mesh hierarchy.")
    return (expected[0], expected[1], expected[2])


def mesh_axis_fractions_from_authorization(
    binding: Mapping[str, Any], authorization: Mapping[str, Any], *, level: str
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] | None:
    """Bind optional nonuniform axis coordinates to one exact mesh level."""

    mesh = binding.get("mesh_definition")
    axes_by_level = mesh.get("axis_fractions_by_level") if isinstance(mesh, Mapping) else None
    expected = axes_by_level.get(level) if isinstance(axes_by_level, Mapping) else None
    declared = authorization.get("mesh_axis_fractions")
    if expected is None:
        if declared is not None:
            raise PermissionError("WP07-D authorization declares axis fractions absent from the binding.")
        return None
    if not isinstance(expected, Mapping) or declared != expected:
        raise PermissionError("WP07-D authorization axis fractions differ from the bound mesh hierarchy.")
    try:
        fractions = tuple(
            tuple(float(value) for value in expected[axis])
            for axis in ("x", "y", "z")
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PermissionError("WP07-D bound axis fractions are malformed.") from error
    from scripts.prepare_wp07d_structural_vnv import _validated_axis_fractions

    try:
        return _validated_axis_fractions(
            cast(
                tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]],
                fractions,
            )
        )
    except ValueError as error:
        raise PermissionError("WP07-D bound axis fractions are invalid.") from error


def dry_run(binding_path: Path = BINDING_PATH) -> dict[str, Any]:
    """Validate every frozen case without solving or importing a solver route."""

    binding = load_binding(binding_path)
    validate_binding(binding)
    from scripts.prepare_wp07d_structural_vnv import (
        actual_mesh_load_check,
        mesh_contract_check,
    )

    contract = load_contract_for_binding(binding)
    cases: list[dict[str, Any]] = []
    mesh_definition = binding.get("mesh_definition")
    cells_by_level = mesh_definition.get("cell_counts_by_level") if isinstance(mesh_definition, Mapping) else None
    axes_by_level = mesh_definition.get("axis_fractions_by_level") if isinstance(mesh_definition, Mapping) else None
    for route in EXPECTED_ROUTES:
        for level in EXPECTED_LEVELS:
            raw_counts = cells_by_level.get(level) if isinstance(cells_by_level, Mapping) else None
            cell_counts = tuple(raw_counts) if isinstance(raw_counts, list) else None
            raw_axes = axes_by_level.get(level) if isinstance(axes_by_level, Mapping) else None
            axis_fractions = (
                cast(
                    tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]],
                    tuple(tuple(float(value) for value in raw_axes[axis]) for axis in ("x", "y", "z")),
                )
                if isinstance(raw_axes, Mapping)
                else None
            )
            mesh = mesh_contract_check(
                contract, level, cell_counts=cell_counts, axis_fractions=axis_fractions
            )
            load = actual_mesh_load_check(
                contract, level, cell_counts=cell_counts, axis_fractions=axis_fractions
            )
            cases.append(
                {
                    "case_id": f"WP07D-{route}-{level}",
                    "route": route,
                    "mesh": level,
                    "mesh_cell_counts": list(cell_counts) if cell_counts is not None else None,
                    "axis_fraction_counts": (
                        [len(axis) for axis in axis_fractions]
                        if axis_fractions is not None
                        else None
                    ),
                    "mesh_status": mesh["status"],
                    "load_status": load["status"],
                    "structural_solve": "NOT_RUN",
                    "independent_reference": "NOT_RUN",
                    "replay": "NOT_RUN",
                }
            )
    return {
        "schema_version": 1,
        "artifact_id": "QF-029-WP07-D-EXECUTION-READINESS-001",
        "status": "PASS_READY_FOR_OWNER_AUTHORIZATION",
        "source_sha": _git("rev-parse", "HEAD"),
        "binding_path": str(binding_path.relative_to(ROOT)).replace("\\", "/"),
        "binding_file_sha256": _file_sha256(binding_path),
        "policy_digest": binding["governing"]["policy_digest"],
        "planned_cases": cases,
        "structural_solves_run": False,
        "independent_references_run": False,
        "replay_run": False,
        "execution_guard": UNAUTHORIZED_EXECUTION,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, default=BINDING_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = dry_run(args.binding.resolve())
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"WP07-D execution binding failed closed: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output is None:
        print(rendered)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
