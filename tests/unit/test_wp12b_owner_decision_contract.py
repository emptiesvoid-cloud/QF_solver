from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "development_autonomous.py"
SPEC = importlib.util.spec_from_file_location("wp12b_controller_contract_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CTRL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CTRL
SPEC.loader.exec_module(CTRL)


@pytest.fixture
def case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    root = tmp_path / "scientific"
    source = root / "src"
    (source / "solveur").mkdir(parents=True)
    (source / "solveur" / "__init__.py").write_text("# synthetic\n", encoding="utf-8")
    store = tmp_path / "evidence"
    controller = tmp_path / "controller"
    controller.mkdir()
    coordination = tmp_path / "coordination"
    scope = CTRL.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID
    target = CTRL.WP12B_HEX20_DIAGNOSTIC_NODEID
    test_path = root / target.split("::", maxsplit=1)[0]
    test_path.parent.mkdir(parents=True)
    test_path.write_text("def test_synthetic():\n    pass\n", encoding="utf-8")
    policy = json.loads((SCRIPT.parents[1] / "development_autonomous_policy.json").read_text(encoding="utf-8"))
    entry = policy["worktrees"][scope]
    entry.update(root=str(root), git_root=str(root), evidence_root=str(store), allowed_nodeids=[target])
    identity = {"root": str(root), "branch": entry["branch"], "head": "a" * 40, "tree": "b" * 40, "status_short": ""}
    source_fp = "c" * 64
    provenance = {"identity": {"root": str(controller)}, "sha256": {"runner": "d" * 64}}
    registration = {
        "target": target,
        "selected_dofs": 60,
        "selection_basis": "Synthetic 20 nodes by three DOFs",
        "timeout_seconds": 300,
        "timeout_reason": None,
        "source_fingerprint": source_fp,
    }
    monkeypatch.setattr(CTRL, "ROOT", controller)
    monkeypatch.setattr(CTRL, "WP12_COORDINATION_ROOT", coordination)
    monkeypatch.setattr(CTRL, "load_policy", lambda *_a, **_k: policy)
    monkeypatch.setattr(CTRL, "_registered_worktree", lambda *_a: (entry, root, source, identity, source_fp))
    monkeypatch.setattr(CTRL, "_wp12_active_registration", lambda *_a: registration)
    monkeypatch.setattr(CTRL, "_worktree_source_fingerprint", lambda *_a: source_fp)
    monkeypatch.setattr(CTRL, "_controller_provenance", lambda: provenance)
    monkeypatch.setattr(CTRL, "_wp12_resource_lock", lambda *_a: nullcontext())
    authorization = store / "authorizations" / scope / "wp12b-synthetic-0001.json"
    authorization.parent.mkdir(parents=True)
    manifest = {
        "schema": "qfsolver-wp12-development-execution-v1",
        "state": "OWNER_AUTHORIZED",
        "authorization_id": "wp12b-synthetic-0001",
        "worktree_id": scope,
        "mandate_id": entry["development_mandate_id"],
        "campaign_id": entry["campaign_id"],
        "target": target,
        "identity": identity,
        "source_fingerprint": source_fp,
        "controller_fingerprint": CTRL._stable_fingerprint(provenance),
        "limits": CTRL._wp12_manifest_limits(entry, registration),
        "owner_decision": {
            "status": "APPROVED",
            "approved_by": "Owner",
            "approved_at_utc": "2026-10-28T10:00:00Z",
            "reason": "Synthetic Owner decision for controller contract verification.",
            "decision_id": "owner-synthetic-0001",
        },
    }
    authorization.write_text(json.dumps(manifest), encoding="utf-8")
    return {
        "scope": scope,
        "target": target,
        "entry": entry,
        "identity": identity,
        "source_fp": source_fp,
        "provenance": provenance,
        "registration": registration,
        "manifest": manifest,
        "path": authorization,
        "store": store,
    }


def validate(case: dict) -> dict:
    return CTRL._validate_wp12_execution_manifest(
        case["path"],
        worktree_id=case["scope"],
        target=case["target"],
        entry=case["entry"],
        identity=case["identity"],
        source_fingerprint=case["source_fp"],
        controller_fingerprint=CTRL._stable_fingerprint(case["provenance"]),
        selection=case["registration"],
    )


def run(case: dict, **kwargs: object) -> tuple:
    return CTRL.run_pytest(
        "fem_exploratory",
        case["target"],
        "dev-synthetic-hex20",
        worktree_id=case["scope"],
        reason="Synthetic controller path with no numerical execution.",
        execution_manifest=case["path"],
        **kwargs,
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_id", "valid decision_id"),
        ("bad_id", "valid decision_id"),
        ("prepared", "distinct, explicit Owner decision"),
        ("stale_source", "exact worktree"),
        ("wrong_controller", "exact worktree"),
        ("budget", "exact worktree"),
        ("preflight", "preflight receipt IDs"),
    ],
)
def test_refusals_precede_reservation(case: dict, monkeypatch: pytest.MonkeyPatch, mutation: str, message: str) -> None:
    manifest = case["manifest"]
    if mutation == "missing_id":
        manifest["owner_decision"].pop("decision_id")
    elif mutation == "bad_id":
        manifest["owner_decision"]["decision_id"] = "bad id"
    elif mutation == "prepared":
        manifest["state"] = "PREPARED_NOT_AUTHORIZED"
    elif mutation == "stale_source":
        manifest["source_fingerprint"] = "0" * 64
    elif mutation == "wrong_controller":
        manifest["controller_fingerprint"] = "0" * 64
    elif mutation == "budget":
        manifest["limits"]["selected_dofs"] = 61
    case["path"].write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(CTRL, "_reserve_node_attempt", lambda *_a, **_k: pytest.fail("must not reserve"))
    monkeypatch.setattr(CTRL, "run_supervised_command", lambda *_a, **_k: pytest.fail("must not launch"))
    with pytest.raises(CTRL.PolicyError, match=message):
        run(case, **({"preflight_id": "pf-000000000000"} if mutation == "preflight" else {}))
    assert not (case["store"] / "node-attempt-ledger.json").exists()


def test_consumed_ledger_refuses_without_mutation(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = case["store"] / "node-attempt-ledger.json"
    CTRL._reserve_node_attempt(
        ledger,
        ledger.with_suffix(".lock"),
        mandate_id=case["entry"]["development_mandate_id"],
        worktree_id=case["scope"],
        target=case["target"],
        series_id="dev-existing-synthetic",
        source_fingerprint=case["source_fp"],
        reason="Synthetic prior attempt",
        maximum=1,
        total_maximum=1,
        authorization_id="wp12b-synthetic-0001",
        owner_decision_id="owner-synthetic-0001",
    )
    before = ledger.read_bytes()
    monkeypatch.setattr(CTRL, "run_supervised_command", lambda *_a, **_k: pytest.fail("must not launch"))
    with pytest.raises(CTRL.PolicyError, match="exhausted|already been consumed"):
        run(case)
    assert ledger.read_bytes() == before


def test_inconsistent_receipt_refuses_before_reservation(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    original = CTRL._validate_wp12_execution_manifest

    def corrupted(*args: object, **kwargs: object) -> dict:
        receipt = original(*args, **kwargs)
        receipt["decision_id"] = "owner-different-0001"
        return receipt

    monkeypatch.setattr(CTRL, "_validate_wp12_execution_manifest", corrupted)
    monkeypatch.setattr(CTRL, "_reserve_node_attempt", lambda *_a, **_k: pytest.fail("must not reserve"))
    with pytest.raises(CTRL.PolicyError, match="inconsistent decision_id"):
        run(case)
    assert not (case["store"] / "node-attempt-ledger.json").exists()


def test_valid_decision_propagates_to_simulated_run_and_ledger(case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = validate(case)
    assert receipt["decision_id"] == receipt["owner_decision"]["decision_id"] == "owner-synthetic-0001"
    calls = []

    def fake_child(command: list, *, output_dir: Path, **kwargs: object) -> SimpleNamespace:
        calls.append(command)
        (output_dir / "stdout.log").write_text("synthetic child; no pytest\n", encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=0,
            stderr_bytes=0,
            archive_bytes=0,
            temporary_bytes=0,
            stop_reason=None,
        )

    monkeypatch.setattr(CTRL, "run_supervised_command", fake_child)
    monkeypatch.setattr(CTRL, "_wp12b_hex20_diagnostic_sidecar", lambda **_kw: {"status": "VERIFIED"})
    result, exit_code = run(case)
    assert exit_code == 0 and len(calls) == 1
    record = json.loads(Path(result["record"]).read_text(encoding="utf-8"))
    assert record["execution_manifest"]["decision_id"] == "owner-synthetic-0001"
    ledger = json.loads((case["store"] / "node-attempt-ledger.json").read_text(encoding="utf-8"))
    attempts = next(iter(ledger["entries"].values()))
    assert len(attempts) == 1 and attempts[0]["owner_decision_id"] == "owner-synthetic-0001"
    assert attempts[0]["state"] == "PASS"
