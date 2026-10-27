"""Synthetic execution-guard contracts; never invoke a FEM case."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments.hex8_sri_equilibrium import criteria_contract as criteria


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


@pytest.fixture
def contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target_file = Path(__file__).resolve().parents[1] / "verification/test_hex8_sri_convergence.py"
    spec = importlib.util.spec_from_file_location("synthetic_hex8_guard", target_file)
    assert spec and spec.loader
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)
    science = tmp_path / "science"
    campaign = science / "campaign"
    controller = tmp_path / "controller"
    for relative in ("scripts/development_autonomous.py", "scripts/development_autonomous_pytest_plugin.py"):
        path = controller / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    write(controller / "development_autonomous_policy.json", {"run_store": ".codex/development-runs"})
    solveur = science / "src/solveur/__init__.py"
    solveur.parent.mkdir(parents=True)
    solveur.write_text("# synthetic\n", encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", science)
    monkeypatch.setattr(gate, "CAMPAIGN_DIR", campaign)
    monkeypatch.setattr(gate, "_source_fingerprint", lambda _node: "c" * 64)
    monkeypatch.setattr(
        gate,
        "_git",
        lambda *a: {"--show-current": "research/hex8-sri-equilibrium", "HEAD": "d" * 40, "HEAD^{tree}": "e" * 40}[
            a[-1]
        ],
    )
    git_values = {
        "--show-toplevel": str(controller),
        "--show-current": "",
        "HEAD": "a" * 40,
        "HEAD^{tree}": "b" * 40,
        "--untracked-files=all": "",
    }
    monkeypatch.setattr(
        gate,
        "subprocess",
        SimpleNamespace(
            run=lambda *_a, **_k: SimpleNamespace(returncode=0),
            check_output=lambda args, **_k: git_values[args[-1]],
        ),
    )
    monkeypatch.setitem(sys.modules, "solveur", SimpleNamespace(__file__=str(solveur)))
    hashes = {
        "runner": digest(controller / "scripts/development_autonomous.py"),
        "policy": digest(controller / "development_autonomous_policy.json"),
        "pytest_plugin": digest(controller / "scripts/development_autonomous_pytest_plugin.py"),
    }
    prov = {
        "identity": {"root": str(controller), "branch": "", "head": "a" * 40, "tree": "b" * 40, "status_short": ""},
        "sha256": hashes,
        "runtime": {},
    }
    prov_sha = hashlib.sha256(
        json.dumps(prov, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    authroot = controller / ".codex/development-runs/authorizations/hex8sri-convergence24"
    scope = "hex8sri-convergence24"
    mandate, campaign_id = gate.DEVELOPMENT_MANDATE_ID, gate.CAMPAIGN_ID
    identity = {
        "root": str(science),
        "branch": "research/hex8-sri-equilibrium",
        "head": "d" * 40,
        "tree": "e" * 40,
        "status_short": "",
    }

    def make(nodeid: str):
        token = nodeid.split("[")[1][:-1]
        form, nu, mesh = token.split("-")
        case_id = f"{form}_{nu}_{mesh}"
        case_path = campaign / f"manifest_{case_id}.json"
        case = {
            "case_id": case_id,
            "exact_nodeid": nodeid,
            "controller_campaign_scope_id": scope,
            "campaign_id": campaign_id,
            "execution_state": "PREPARED_NOT_AUTHORIZED",
            "execution_authorized": False,
            "do_not_execute": True,
            "source_fingerprint_sha256": "c" * 64,
            "science_source_commit": "d" * 40,
            "controller_identity_status": "FINAL_CONTROLLER_IDENTITY_BOUND",
            "controller_identity": {"branch": "", "head": "a" * 40},
            "controller_code_sha256": hashes,
            "criteria_status": "OWNER_FREEZE_REQUIRED",
            "criteria_contract": {
                "schema": criteria.CRITERIA_CONTRACT_SCHEMA,
                "revision": criteria.CRITERIA_CONTRACT_REVISION,
                "dispositions": criteria.PROPOSED_DISPOSITIONS,
            },
            "proposed_criteria": criteria.PROPOSED_CRITERIA,
            "frozen_criteria": None,
        }
        write(case_path, case)
        reg = gate._manifest_registration_sha256(case)
        binding = {
            "path": str(case_path),
            "sha256": digest(case_path),
            "registration_sha256": reg,
            "case_id": case_id,
            "scope_id": scope,
        }
        regs = {n: "f" * 64 for n in criteria.FIRST6_NODEIDS}
        regs[nodeid] = reg
        freeze_content = {
            "schema": criteria.CRITERIA_FREEZE_SCHEMA,
            "revision": criteria.CRITERIA_CONTRACT_REVISION,
            "dispositions": criteria.FROZEN_DISPOSITIONS,
            "frozen_case_gate_criteria": criteria.FROZEN_CASE_GATE_CRITERIA,
            "case_manifest_registration_sha256_by_nodeid": regs,
        }
        freeze_id = "freeze-synthetic-001"
        freeze_path = authroot / "owner-decisions/criteria-freeze" / f"{freeze_id}.json"
        freeze = {
            "schema": "qfsolver-hex8sri-criteria-freeze-decision-v1",
            "decision_type": "CRITERIA_FREEZE_ONLY",
            "status": "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED",
            "execution_authorized": False,
            "do_not_execute": True,
            "approved_by": "Owner",
            "approved_at_utc": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            "reason": "Synthetic criteria freeze for controller contract verification.",
            "decision_id": freeze_id,
            "scope_id": scope,
            "mandate_id": mandate,
            "campaign_id": campaign_id,
            "source_fingerprint": "c" * 64,
            "controller_fingerprint": prov_sha,
            "controller_head": "a" * 40,
            "frozen_nodeids": list(criteria.FIRST6_NODEIDS),
            "criteria_freeze": freeze_content,
        }
        write(freeze_path, freeze)
        now = datetime.now(timezone.utc)
        decision_id = "execution-synthetic-001"
        decision_path = authroot / "owner-decisions/execution" / f"{decision_id}.json"
        limits = {"timeout_seconds": 180}
        case_bindings = {n: {} for n in criteria.FIRST6_NODEIDS}
        case_bindings[nodeid] = binding
        decision = {
            "schema": "qfsolver-hex8sri-execution-approval-v1",
            "decision_type": "EXECUTION_APPROVED",
            "execution_authorized": True,
            "do_not_execute": False,
            "decision_id": decision_id,
            "status": "APPROVED",
            "approved_by": "Owner",
            "reason": "Synthetic execution approval for controller contract verification.",
            "approved_at_utc": (now - timedelta(minutes=1)).isoformat(),
            "expires_at_utc": (now + timedelta(hours=1)).isoformat(),
            "scope_id": scope,
            "mandate_id": mandate,
            "campaign_id": campaign_id,
            "source_fingerprint": "c" * 64,
            "controller_fingerprint": prov_sha,
            "controller_head": "a" * 40,
            "authorized_nodeids": list(criteria.FIRST6_NODEIDS),
            "case_manifests_by_nodeid": case_bindings,
            "limits_by_nodeid": {n: limits for n in criteria.FIRST6_NODEIDS},
            "criteria_freeze_record": {
                "decision_id": freeze_id,
                "path": str(freeze_path),
                "sha256": digest(freeze_path),
            },
            "criteria_freeze": freeze_content,
        }
        write(decision_path, decision)
        pf_id = "pf-0123456789ab"
        pf = controller / ".codex/development-runs/worktrees" / scope / "preflight" / pf_id / "preflight.json"
        collection = {
            "schema": "qfsolver-hex8sri-convergence24-collection-v1",
            "scope_id": scope,
            "target": nodeid,
            "collected_nodeids": [nodeid],
            "skip_markers": [],
            "bodies_executed": False,
            "exitstatus": 0,
        }
        receipt = {
            "state": "PREFLIGHT_PASS",
            "execution_authorized": False,
            "bodies_executed": False,
            "attempt_reserved": False,
            "worktree_id": scope,
            "target": nodeid,
            "preflight_id": pf_id,
            "source_fingerprint": "c" * 64,
            "identity": identity,
            "controller_provenance": prov,
            "case_manifest": binding,
            "solver_origin_observed": str(solveur),
            "collected_nodeids": [nodeid],
            "skip_status": "NO_SKIP_MARKERS",
            "collection_report": collection,
            "attempt_ledger": {"attempts_reserved": False},
        }
        write(pf, receipt)
        write(pf.parent / "preflight.sha256.json", {"sha256": digest(pf)})
        execution_path = authroot / "synthetic-execution.json"
        execution = {
            "schema": "qfsolver-hex8sri-convergence24-execution-v1",
            "state": "OWNER_AUTHORIZED",
            "authorization_id": "synthetic-execution",
            "execution_authorized": True,
            "do_not_execute": False,
            "worktree_id": scope,
            "mandate_id": mandate,
            "campaign_id": campaign_id,
            "target": nodeid,
            "identity": identity,
            "source_fingerprint": "c" * 64,
            "controller_provenance": prov,
            "controller_fingerprint": prov_sha,
            "case_manifest": binding,
            "preflight": {"preflight_id": pf_id, "receipt_path": str(pf), "receipt_sha256": digest(pf)},
            "limits": limits,
            "owner_decision": decision,
            "owner_decision_record": {"path": str(decision_path), "sha256": digest(decision_path)},
        }

        def sync():
            write(decision_path, decision)
            execution["owner_decision_record"]["sha256"] = digest(decision_path)
            write(execution_path, execution)
            monkeypatch.setenv("QF_DEV_MANIFEST_SHA256", digest(execution_path))

        sync()
        env = {
            "QF_DEVELOPMENT_AUTONOMOUS": "1",
            "QF_DEV_WORKTREE_ID": scope,
            "QF_DEV_CAMPAIGN_SCOPE_ID": scope,
            "QF_DEV_TARGET_NODEID": nodeid,
            "QF_DEV_AUTHORIZATION_ID": "synthetic-execution",
            "QF_DEV_MANIFEST_PATH": str(execution_path),
            "QF_DEV_CASE_MANIFEST_PATH": str(case_path),
            "QF_DEV_CASE_MANIFEST_SHA256": digest(case_path),
            "QF_DEV_OWNER_DECISION_ID": decision_id,
            "QF_DEV_PREFLIGHT_ID": pf_id,
            "QF_DEV_PREFLIGHT_SHA256": digest(pf),
            "QF_DEV_CONTROLLER_ROOT": str(controller),
            "QF_DEV_CONTROLLER_BRANCH": "",
            "QF_DEV_CONTROLLER_HEAD": "a" * 40,
            "QF_DEV_CONTROLLER_TREE": "b" * 40,
            "QF_DEV_CONTROLLER_RUNNER_SHA256": hashes["runner"],
            "QF_DEV_CONTROLLER_POLICY_SHA256": hashes["policy"],
            "QF_DEV_CONTROLLER_PLUGIN_SHA256": hashes["pytest_plugin"],
        }
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return SimpleNamespace(
            gate=gate,
            request=SimpleNamespace(node=SimpleNamespace(nodeid=nodeid)),
            case_id=case_id,
            decision=decision,
            decision_path=decision_path,
            execution=execution,
            execution_path=execution_path,
            sync=sync,
            git_values=git_values,
            controller=controller,
            receipt=receipt,
            preflight=pf,
            freeze=freeze,
            freeze_path=freeze_path,
            case=case,
            binding=binding,
            identity=identity,
            provenance=prov,
            authroot=authroot,
        )

    return make


def _load_candidate_controller(path: str):
    spec = importlib.util.spec_from_file_location("reviewed_hex8sri_controller", path)
    assert spec and spec.loader
    controller = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = controller
    spec.loader.exec_module(controller)
    return controller


def _verify_live_science_registration(controller) -> tuple[dict, Path, dict, str, dict]:
    """Cross-check policy constants and the complete raw-byte inventory against the live source tree."""
    policy = controller.load_policy()
    scope_id = controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    entry = policy["worktrees"][scope_id]
    nodeid = controller.HEX8SRI_FIRST6_NODEIDS[0]
    registered, root, _source_root, identity, fingerprint = controller._registered_worktree(scope_id, nodeid, policy)

    expected = entry["source_identity"]
    assert registered == entry
    assert expected == controller.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY
    assert identity["branch"] == expected["branch"]
    assert identity["head"] == expected["head"] == controller.HEX8SRI_CONVERGENCE24_SOURCE_HEAD
    assert identity["tree"] == expected["tree"] == controller.HEX8SRI_CONVERGENCE24_SOURCE_TREE
    assert fingerprint == expected["fingerprint_sha256"]
    assert fingerprint == controller.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    assert entry["source_fingerprint_sha256"] == fingerprint

    inventory = controller._worktree_source_inventory(root, nodeid)
    inventory_path = (controller.ROOT / expected["inventory_path"]).resolve(strict=True)
    assert controller._sha256(inventory_path) == expected["inventory_sha256"]
    recorded = controller._read_strict_json(inventory_path)
    assert recorded["head"] == identity["head"]
    assert recorded["tree"] == identity["tree"]
    assert recorded["fingerprint_sha256"] == fingerprint
    assert recorded["inventory_file_count"] == len(inventory)
    assert recorded["files_sha256"] == inventory

    # Independently run the science guard's inventory algorithm against the same checkout.
    guard_path = root / nodeid.split("::", maxsplit=1)[0]
    guard_spec = importlib.util.spec_from_file_location("live_hex8sri_science_guard", guard_path)
    assert guard_spec and guard_spec.loader
    guard = importlib.util.module_from_spec(guard_spec)
    sys.modules[guard_spec.name] = guard
    guard_spec.loader.exec_module(guard)
    assert guard._source_fingerprint(nodeid) == fingerprint
    return entry, root, identity, fingerprint, inventory


@pytest.mark.parametrize("nodeid", criteria.FIRST6_NODEIDS)
def test_official_contract_accepts_detached_controller_without_fem(contract, nodeid: str) -> None:
    c = contract(nodeid)
    assert c.gate._authorized_case(c.request, c.case_id)["owner_decision_id"] == "execution-synthetic-001"


def test_merged_controller_and_science_guard_accept_same_complete_synthetic_contract(contract) -> None:
    controller_path = os.environ.get("QF_HEX8SRI_CONTROLLER_PATH")
    if not controller_path:
        pytest.skip("set QF_HEX8SRI_CONTROLLER_PATH to the reviewed merged controller for cross-contract validation")
    controller = _load_candidate_controller(controller_path)
    _verify_live_science_registration(controller)
    c = contract(criteria.FIRST6_NODEIDS[0])
    nodeid = c.request.node.nodeid
    entry = deepcopy(controller.load_policy()["worktrees"][controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID])
    entry["case_manifests"][nodeid]["sha256"] = c.binding["registration_sha256"]
    freeze_content = controller._hex8sri_expected_criteria_freeze(
        entry=entry, source_fingerprint="c" * 64, controller_provenance=c.provenance
    )
    c.freeze["criteria_freeze"] = freeze_content
    write(c.freeze_path, c.freeze)
    c.decision["criteria_freeze"] = freeze_content
    c.decision["criteria_freeze_record"]["sha256"] = digest(c.freeze_path)
    c.decision["limits_by_nodeid"] = {
        n: controller._hex8sri_execution_limits(entry, n) for n in criteria.FIRST6_NODEIDS
    }
    c.execution["limits"] = c.decision["limits_by_nodeid"][nodeid]
    bindings = {}
    for n in criteria.FIRST6_NODEIDS:
        form, nu, mesh = controller._hex8sri_convergence24_case(n)
        bindings[n] = {
            "path": str(c.authroot / "synthetic-cases" / f"{form}_{nu}_{mesh}.json"),
            "sha256": "a" * 64,
            "registration_sha256": entry["case_manifests"][n]["sha256"],
            "case_id": f"{form}_nu_{nu}_{mesh}",
            "scope_id": controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        }
    bindings[nodeid] = c.binding
    c.decision["case_manifests_by_nodeid"] = bindings
    c.sync()
    validated = controller._validate_hex8sri_execution_manifest(
        c.execution_path,
        store=c.authroot.parent.parent,
        target=nodeid,
        entry=entry,
        identity=c.identity,
        source_fingerprint="c" * 64,
        controller_provenance=c.provenance,
        case_manifest_binding=c.binding,
        case_manifest=c.case,
        preflight_id="pf-0123456789ab",
        preflight_receipt=(c.preflight, digest(c.preflight)),
    )
    assert validated["authorization_id"] == "synthetic-execution"
    assert c.gate._authorized_case(c.request, c.case_id)["owner_decision_id"] == "execution-synthetic-001"


@pytest.mark.parametrize(
    "fault", ["head", "tree", "fingerprint", "incomplete_inventory", "wrong_worktree", "policy_identity"]
)
def test_cross_contract_rejects_scientific_identity_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    controller_path = os.environ.get("QF_HEX8SRI_CONTROLLER_PATH")
    if not controller_path:
        pytest.skip("set QF_HEX8SRI_CONTROLLER_PATH to the reviewed merged controller for cross-contract validation")
    controller = _load_candidate_controller(controller_path)
    policy = controller.load_policy()
    scope_id = controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    entry = deepcopy(policy["worktrees"][scope_id])
    nodeid = controller.HEX8SRI_FIRST6_NODEIDS[0]
    registered, root, _source_root, identity, fingerprint = controller._registered_worktree(scope_id, nodeid, policy)
    inventory = controller._worktree_source_inventory(root, nodeid)

    if fault == "head":
        identity["head"] = "0" * 40
    elif fault == "tree":
        identity["tree"] = "0" * 40
    elif fault == "fingerprint":
        fingerprint = "0" * 64
    elif fault == "incomplete_inventory":
        inventory.pop(next(iter(inventory)))
    elif fault == "wrong_worktree":
        altered_policy = deepcopy(policy)
        altered = altered_policy["worktrees"][scope_id]
        altered["root"] = str(tmp_path)
        altered["git_root"] = str(tmp_path)
        with pytest.raises((controller.PolicyError, OSError)):
            controller._registered_worktree(scope_id, nodeid, altered_policy)
        return
    elif fault == "policy_identity":
        entry["source_identity"]["head"] = "0" * 40

    with pytest.raises(controller.PolicyError):
        controller._validate_hex8sri_registered_source_identity(
            root, entry if fault == "policy_identity" else registered, identity, nodeid, inventory, fingerprint
        )


@pytest.mark.parametrize(
    "fault",
    [
        "branch_missing",
        "attached_branch",
        "head",
        "runner",
        "policy",
        "decision_path",
        "freeze_as_execution",
        "decision_hash",
        "freeze_hash",
        "preflight_sidecar",
        "limits",
        "source",
        "manifest",
        "nodeid",
        "attempt",
        "expired",
    ],
)
def test_official_contract_rejects_incoherent_inputs(contract, monkeypatch, fault: str) -> None:
    c = contract(criteria.FIRST6_NODEIDS[0])
    if fault == "branch_missing":
        monkeypatch.delenv("QF_DEV_CONTROLLER_BRANCH")
    elif fault == "attached_branch":
        c.git_values["--show-current"] = "main"
    elif fault == "head":
        c.git_values["HEAD"] = "0" * 40
    elif fault in {"runner", "policy"}:
        path = c.controller / (
            "scripts/development_autonomous.py" if fault == "runner" else "development_autonomous_policy.json"
        )
        path.write_text("tampered", encoding="utf-8")
    elif fault == "decision_path":
        c.execution["owner_decision_record"]["path"] = c.execution["owner_decision"]["criteria_freeze_record"]["path"]
        c.sync()
    elif fault == "freeze_as_execution":
        c.decision["decision_type"] = "CRITERIA_FREEZE_ONLY"
        c.sync()
    elif fault == "decision_hash":
        c.execution["owner_decision_record"]["sha256"] = "0" * 64
        write(c.execution_path, c.execution)
        monkeypatch.setenv("QF_DEV_MANIFEST_SHA256", digest(c.execution_path))
    elif fault == "freeze_hash":
        c.decision["criteria_freeze_record"]["sha256"] = "0" * 64
        c.sync()
    elif fault == "preflight_sidecar":
        write(c.preflight.parent / "preflight.sha256.json", {"sha256": "0" * 64})
    elif fault == "limits":
        c.decision["limits_by_nodeid"][c.request.node.nodeid] = {"timeout_seconds": 181}
        c.sync()
    elif fault == "source":
        monkeypatch.setattr(c.gate, "_source_fingerprint", lambda _node: "0" * 64)
    elif fault == "manifest":
        c.execution["target"] = "obsolete"
        c.sync()
    elif fault == "nodeid":
        monkeypatch.setenv("QF_DEV_TARGET_NODEID", "wrong")
    elif fault == "attempt":
        c.receipt["attempt_reserved"] = True
        write(c.preflight, c.receipt)
        c.execution["preflight"]["receipt_sha256"] = digest(c.preflight)
        write(c.preflight.parent / "preflight.sha256.json", {"sha256": digest(c.preflight)})
        monkeypatch.setenv("QF_DEV_PREFLIGHT_SHA256", digest(c.preflight))
        c.sync()
    elif fault == "expired":
        c.decision["expires_at_utc"] = "2000-01-01T00:00:00Z"
        c.sync()
    with pytest.raises((RuntimeError, ValueError, OSError)):
        c.gate._authorized_case(c.request, c.case_id)
