"""Freeze a new WP07-D contact-event line-search requalification binding.

This preparation command writes only the R2.3 contract, Owner decision, and
fail-closed execution binding. It never runs a solve or modifies prior R2
evidence.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.wp07d_execution_binding import (
    CONTACT_REQUAL_R2_2_BINDING_PATH,
    CONTACT_REQUAL_R2_3_BINDING_PATH,
    CONTACT_REQUAL_R2_3_CONTRACT_PATH,
    CONTACT_REQUAL_R2_3_OWNER_DECISION_PATH,
    CONTACT_REQUAL_R2_3_AUTH_ROOT,
    CONTACT_REQUAL_R2_3_REPLAY_GATE_PATH,
    CONTACT_REQUAL_R2_3_RUN_ROOT,
    _file_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "b2485f98260c7ca9892997eefa3a327637d83cd3"
POLICY_DIGEST = "93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac"
PREVIOUS_EXECUTION_SHA = "7541ff9701511d6dc692b98d3dd578288cce4550"
EXPECTED_INCREMENTAL_SOURCE_PATHS = [
    "src/solveur/core/analyses/geometric_nonlinear.py",
    "src/solveur/core/assembly/nonlinear.py",
    "src/solveur/core/nonlinear/iteration.py",
    "src/solveur/core/nonlinear/robustness.py",
]
ADDENDUM_PATH = Path("docs/verification/0_2_9/wp07-d-contact-event-line-search-remediation-r2-3.md")


def _git(*args: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=text
    )
    return completed.stdout.strip() if text else completed.stdout


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
        stream.flush()


def build() -> dict[str, Any]:
    if _git("branch", "--show-current") != "codex/wp07d-penalty-r2-5":
        raise PermissionError("R2.3 freeze must be prepared on codex/wp07d-penalty-r2-5.")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise PermissionError("R2.3 freeze preparation requires a clean source checkout.")
    head = str(_git("rev-parse", "HEAD"))
    _git("merge-base", "--is-ancestor", PREVIOUS_EXECUTION_SHA, head)
    incremental_paths = str(
        _git("diff", "--name-only", PREVIOUS_EXECUTION_SHA, head, "--", "src")
    ).splitlines()
    if incremental_paths != EXPECTED_INCREMENTAL_SOURCE_PATHS:
        raise ValueError(f"Unexpected R2.3 production-source delta: {incremental_paths!r}")
    for path in (
        CONTACT_REQUAL_R2_3_BINDING_PATH,
        CONTACT_REQUAL_R2_3_CONTRACT_PATH,
        CONTACT_REQUAL_R2_3_OWNER_DECISION_PATH,
        ROOT / CONTACT_REQUAL_R2_3_RUN_ROOT,
        ROOT / CONTACT_REQUAL_R2_3_AUTH_ROOT,
        ROOT / CONTACT_REQUAL_R2_3_REPLAY_GATE_PATH,
        ROOT / "qualification/0_2_9/wp07d_contact_requalification_r2/analysis_final_r2_5.json",
        ROOT / "qualification/0_2_9/wp07d_contact_requalification_r2/progress_r2_5.json",
    ):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite or mix R2.3 evidence: {path}")

    r2_2_binding = _load(CONTACT_REQUAL_R2_2_BINDING_PATH)
    contract = _load(
        ROOT
        / "qualification/0_2_9/wp07d_contact_requalification_r2/contact_requalification_contract.json"
    )
    contract["artifact_id"] = "QF-029-WP07-D-CONTACT-MECHANICS-REQUALIFICATION-R2-3-001"
    contract["revision"] = "0.2.9-WP07D-CONTACT-R2.3"
    contract["supersedes"] = {
        "path": "qualification/0_2_9/wp07d_contact_requalification_r2/contact_requalification_contract.json",
        "sha256": _file_sha256(
            ROOT
            / "qualification/0_2_9/wp07d_contact_requalification_r2/contact_requalification_contract.json"
        ),
        "classification": "HISTORICAL_R2_2_FAIL_CLOSED_PRESERVED",
    }
    contract["source_identity"] = {
        "authorized_base_sha": BASE_SHA,
        "previous_execution_sha": PREVIOUS_EXECUTION_SHA,
        "source_correction_commit": head,
        "execution_sha_semantics": "Exact final R2.3 freeze commit is supplied in each generated per-case authorization and runner process manifest.",
        "execution_branch": "codex/wp07d-penalty-r2-5",
    }
    contract["contact_event_line_search"] = {
        "status": "FROZEN_BOUNDED_SUPPLEMENTAL_TRIALS",
        "canonical_backtracking_runs_first": True,
        "supplemental_trials_only_after_canonical_failure": True,
        "same_merit_acceptance_rule": True,
        "contact_law_unchanged": True,
        "search_scope": "fixed initial search only",
        "event": "predicted zero crossing of a fixed-search normal gap along the current Newton correction",
        "candidate_sampling": "bounded factors between each representative event factor and the nearest larger canonical backtracking factor, plus the event factor itself when admissible",
        "representative_event_factors": "minimum, median, and maximum unique predicted factors",
        "fractions": [0.75, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625],
        "max_supplemental_alphas_per_iteration": 24,
        "failure_behavior": "If no canonical or supplemental candidate satisfies the unchanged merit rule, preserve the original fail-closed line-search failure.",
    }
    contract["mechanics_requalification"]["additional_change"] = {
        "change_commit": head,
        "classification": "CONTACT_EVENT_AWARE_GLOBALIZATION_CORRECTION",
        "changed_production_paths": EXPECTED_INCREMENTAL_SOURCE_PATHS,
        "mechanics_changed": True,
        "route": "PENALTY",
        "description": "Adds read-only penalty-contact snapshots and bounded trial-factor probes around predicted fixed-search gap activation after canonical backtracking fails. The contact residual/tangent law, physical inputs, thresholds, convergence/failure criteria, linear backend, and fallback policy are unchanged.",
        "addendum_path": ADDENDUM_PATH.as_posix(),
        "addendum_sha256": _file_sha256(ROOT / ADDENDUM_PATH),
    }
    contract["governance"]["line_search_acceptance_criteria_changed"] = False
    contract["governance"]["line_search_trial_generation_changed"] = True
    contract["governance"]["solver_policy_digest_role"] = "Existing digest binds frozen configured policy values; R2.3 source and contract hashes bind the supplemental trial-generation implementation."

    owner_decision = {
        "schema_version": 1,
        "artifact_id": "QF-029-WP07-D-OWNER-EXECUTION-DECISION-CONTACT-R2-3-001",
        "decision_date": datetime.now(timezone.utc).date().isoformat(),
        "status": "AUTHORIZED_FOR_SOURCE_BOUND_REQUALIFICATION",
        "authorization_basis": "Owner explicitly froze the corrected R2.3 candidate and authorized sequential WP07-D M1/M2/M3 validation, references, and contract-required replays in the current task.",
        "decisions": {
            "OWNER_AUTHORIZES_WP07D_M1_M2_M3_REQUALIFICATION": True,
            "OWNER_AUTHORIZES_WP07D_INDEPENDENT_REFERENCES": True,
            "OWNER_AUTHORIZES_WP07D_CONTRACT_REQUIRED_REPLAYS": True,
            "OWNER_AUTHORIZES_WP07E_OR_WP08E": False,
            "OWNER_AWARDS_POINTS": False,
            "OWNER_AUTHORIZES_MERGE_OR_PUSH": False,
        },
        "conditions": [
            "Run sequentially, one solve at a time, using only the frozen M1/M2/M3 meshes and unchanged physical thresholds.",
            "Preserve all historical R2.2 failures and outputs; write only under the R2.5 output roots.",
            "Run an independent reference only after its primary case passes; run only contract-required replay after its raw-evidence gate passes.",
            "Do not run WP07-E/WP08-E, change score/ledger, merge, push, tag, or release.",
        ],
        "execution_sha_semantics": "Each per-case authorization generated by the frozen runner pins the exact final R2.3 freeze commit SHA.",
        "qualification_claim": "Execution authorization only; no points are awarded by this decision.",
    }

    contract_bytes = (json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    contract_sha = hashlib.sha256(contract_bytes).hexdigest()
    owner_bytes = (json.dumps(owner_decision, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    owner_sha = hashlib.sha256(owner_bytes).hexdigest()
    base_diff = _git("diff", "--binary", BASE_SHA, head, "--", "src", text=False)
    if not isinstance(base_diff, bytes):
        raise TypeError("Git returned a non-byte production-source diff.")
    binding = dict(r2_2_binding)
    binding.update(
        {
            "artifact_id": "QF-029-WP07-D-EXECUTION-BINDING-CONTACT-R2-003",
            "binding_revision": "R2.3_CONTACT_EVENT_LINE_SEARCH_REQUALIFICATION",
            "supersedes": {
                "path": "qualification/0_2_9/wp07d_contact_requalification_r2/execution_binding_r2_2.json",
                "sha256": _file_sha256(CONTACT_REQUAL_R2_2_BINDING_PATH),
            },
            "status": "FROZEN_FAIL_CLOSED_PER_CASE_AUTHORIZATION_REQUIRED",
            "execution_branch": "codex/wp07d-penalty-r2-5",
            "requalification_contract": {
                "path": "qualification/0_2_9/wp07d_contact_requalification_r2/contact_requalification_contract_r2_3.json",
                "sha256": contract_sha,
            },
            "owner_decision": {
                "path": "qualification/0_2_9/wp07d_contact_requalification_r2/owner_execution_decision_r2_3.json",
                "sha256": owner_sha,
            },
            "execution_artifacts": {
                "run_root": CONTACT_REQUAL_R2_3_RUN_ROOT.as_posix(),
                "authorization_root": CONTACT_REQUAL_R2_3_AUTH_ROOT.as_posix(),
                "replay_gate_path": CONTACT_REQUAL_R2_3_REPLAY_GATE_PATH.as_posix(),
            },
            "previous_source_correction": {
                "execution_sha": PREVIOUS_EXECUTION_SHA,
                "corrected_source_commit": head,
                "failure_status": "FAIL_CLOSED_PENALTY_LINE_SEARCH_FAILURE",
            },
            "source_correction": {
                "classification": "CONTACT_EVENT_AWARE_GLOBALIZATION_CORRECTION",
                "route": "PENALTY",
                "candidate_sampling": "After canonical backtracking fails, evaluate bounded trial factors around predicted fixed-search gap-zero events using the same merit acceptance rule.",
                "acceptance_criterion_changed": False,
                "contact_residual_or_tangent_law_changed": False,
                "thresholds_or_physical_inputs_changed": False,
                "commit": head,
            },
            "source_correction_addendum": {
                "path": ADDENDUM_PATH.as_posix(),
                "sha256": _file_sha256(ROOT / ADDENDUM_PATH),
            },
            "execution_sha": "BOUND_IN_PER_CASE_AUTHORIZATIONS_TO_FINAL_R2_3_FREEZE_COMMIT",
            "execution_sha_semantics": "Exact final freeze commit SHA is generated into each case authorization and process manifest.",
            "source_lineage_disclosure": {
                "authorized_governing_base_sha": BASE_SHA,
                "changed_production_source_paths_since_governing_base": str(
                    _git("diff", "--name-only", BASE_SHA, head, "--", "src")
                ).splitlines(),
                "production_source_diff_sha256_since_governing_base": hashlib.sha256(base_diff).hexdigest(),
                "requalification_adds_mechanics_change": True,
                "source_contains_wp07_candidate_changes_since_governing_base": True,
                "source_correction_commit": head,
                "source_correction_classification": "CONTACT_EVENT_AWARE_GLOBALIZATION_CORRECTION",
            },
            "invariants": {
                "production_mechanics_changed": True,
                "thresholds_changed": False,
                "mesh_changed": False,
                "loads_changed": False,
                "contact_parameters_changed": False,
                "fallback_policy_changed": False,
                "frozen_physics_contract_changed": False,
            },
        }
    )

    _write_new(CONTACT_REQUAL_R2_3_CONTRACT_PATH, contract)
    _write_new(CONTACT_REQUAL_R2_3_OWNER_DECISION_PATH, owner_decision)
    _write_new(CONTACT_REQUAL_R2_3_BINDING_PATH, binding)
    return {
        "status": "PASS_R2_3_CONTRACT_AND_BINDING_PREPARED_NO_SOLVES_RUN",
        "source_correction_commit": head,
        "contract_sha256": contract_sha,
        "owner_decision_sha256": owner_sha,
        "binding_sha256": _file_sha256(CONTACT_REQUAL_R2_3_BINDING_PATH),
        "source_diff_sha256_since_governing_base": hashlib.sha256(base_diff).hexdigest(),
        "source_paths_since_governing_base": binding["source_lineage_disclosure"][
            "changed_production_source_paths_since_governing_base"
        ],
    }


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
