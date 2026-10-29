from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import re
import threading
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("wp12a_p0_batch", ROOT / "scripts" / "wp12a_p0_batch.py")
assert SPEC is not None and SPEC.loader is not None
BATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BATCH)

MANDATE = "DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1"
NODES = (
    "tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators",
    "tests/unit/test_modal_basis_damping.py::test_degenerate_subspace_rotation_and_sign_are_equivalent_and_residual_safe",
    "tests/unit/test_modal_basis_damping.py::test_rayleigh_projection_and_modal_damping_provenance_and_cluster_guard",
    "tests/unit/test_analysis_features.py::test_transient_dynamic_sdof_matches_closed_form_initial_energy",
    "tests/unit/test_analysis_features.py::test_harmonic_sdof_matches_closed_form_amplitude_and_phase",
    "tests/unit/test_prepared_dynamic_system.py::test_prepared_system_assembles_once_and_excitation_does_not_invalidate_operators",
)


class SyntheticPolicyError(RuntimeError):
    """Expected refusal from the synthetic controller fixture."""


class FakeController:
    """Temporary-file controller double; it never imports or executes scientific tests."""

    PolicyError = SyntheticPolicyError
    WP12_DYNAMICS_P0_BATCH_NODEIDS = NODES
    WP12_DYNAMICS_PREFLIGHT_NODEIDS = NODES
    WP12_OWNER_ENVELOPES = {"wp12_dynamics": {"development_mandate_id": MANDATE}}
    SERIES_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
    _WP12A_BATCH_LOCK_LOCAL = threading.local()
    ET = ET

    def __init__(self, tmp_path: Path) -> None:
        self.ROOT = tmp_path / "controller"
        self.ROOT.mkdir()
        self.science = tmp_path / "science"
        self.store = tmp_path / "evidence"
        self.store.mkdir()
        self.preflight_root = self.store / "worktrees" / "wp12_dynamics" / "preflight"
        self.ledger_path = self.store / "node-attempt-ledger-wp12-dynamics-v2.json"
        self.predecessor = {"path": "history/legacy.json", "sha256": ""}
        predecessor_path = self.store / self.predecessor["path"]
        predecessor_path.parent.mkdir(parents=True)
        predecessor_path.write_text('{"immutable":true}\n', encoding="utf-8")
        self.predecessor["sha256"] = self.sha256(predecessor_path)
        self.identity = {
            "root": str(self.science),
            "branch": "codex/wp12-dynamic-harmonic-verification",
            "head": "7406e34efc28ed8f18c15440115595dfa3dd9ca5",
            "tree": "a618d0d1790ab8642f408a78b2d2856debcc60c0",
            "status_short": "",
        }
        self.registrations: dict[str, dict[str, Any]] = {}
        self.policy = {
            "minimum_free_disk_mib": 1,
            "worktrees": {
                "wp12_dynamics": {
                    "allowed_nodeids": list(NODES),
                    "development_mandate_id": MANDATE,
                    "campaign_id": "wp12-dynamics-2026-10-26",
                    "nodeid_registration": {"enabled": True, "max_nodeids": 18},
                    "attempt_limit_per_nodeid": 10,
                    "max_total_attempts": 130,
                    "budgets": {
                        "timeout_seconds": 300,
                        "rss_limit_mib": 4096,
                        "archive_size_limit_mib": 256,
                    },
                    "evidence_root": str(self.store),
                    "node_attempt_ledger": {"predecessor": dict(self.predecessor)},
                }
            },
        }
        self.provenance = {"head": "d" * 40, "tree": "e" * 40, "path": str(self.ROOT)}
        self.fingerprints: dict[str, str] = {}
        self.preflight_count = 0
        self.preflight_failure_on: int | None = None
        self.outcomes: list[str] = ["PASS"] * len(NODES)
        self.pytest_failure_kind = "failure"
        self.run_targets: list[str] = []
        self.foreign_mutation_after_first = False
        self.ledger_mutation_during_manifest_prepare = False
        self.interrupt_after_reservation = False
        self.reservation_count = 0
        self._create_source_and_case_manifests()
        self.ledger_path.write_text(
            json.dumps(
                {
                    "schema": "qfsolver-development-node-ledger-v2",
                    "mandate_id": MANDATE,
                    "predecessor": dict(self.predecessor),
                    "entries": {},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _create_source_and_case_manifests(self) -> None:
        for target in NODES:
            module_path = target.split("::", maxsplit=1)[0]
            source_path = self.science / module_path
            source_path.parent.mkdir(parents=True, exist_ok=True)
            if not source_path.exists():
                source_path.write_text(f"# synthetic source identity for {module_path}; no FEM body\n", encoding="utf-8")
            digest = self.sha256(source_path)
            self.fingerprints[module_path] = hashlib.sha256(("source:" + digest).encode()).hexdigest()
            dofs = 2 if target == NODES[0] else 3 if target in NODES[1:3] or target == NODES[5] else 1
            basis = f"synthetic fixed fixture selecting {dofs} free DDL"
            self.registrations[target] = {
                "selected_dofs": dofs,
                "selection_basis": basis,
                "timeout_seconds": 300,
                "timeout_reason": None,
            }
            criteria = {
                "oracle": "fixed synthetic oracle description",
                "oracle_independence": "synthetic test double only; no physical validation",
                "acceptance": "existing case criteria copied unchanged",
                "acceptance_source_sha256": digest,
            }
            manifest = {
                "schema": BATCH.CASE_MANIFEST_SCHEMA,
                "state": "PROPOSED_NOT_AUTHORIZED",
                "case_id": f"wp12a-p0-case-{len(self.registrations):02d}",
                "worktree_id": "wp12_dynamics",
                "mandate_id": MANDATE,
                "nodeid": target,
                "science": {
                    "head": self.identity["head"],
                    "tree": self.identity["tree"],
                    "branch": self.identity["branch"],
                },
                "identity": dict(self.identity),
                "source_fingerprint": self.fingerprints[module_path],
                "test_module_sha256": digest,
                "selection": {
                    "selected_dofs": dofs,
                    "selection_basis": basis,
                    "timeout_seconds": 300,
                    "timeout_reason": None,
                },
                "criteria": criteria,
                "criteria_sha256": BATCH._canonical_sha256(criteria),
                "max_attempts": 1,
                "continue_after": ["PASS", "SCIENTIFIC_ASSERTION_FAILED"],
                "conditions_of_stop": list(BATCH._STOP_CONDITIONS),
            }
            path = self.ROOT / "qualification" / "wp12a_p0" / "case_manifests" / f"case-{len(self.registrations):02d}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.case_paths = sorted((self.ROOT / "qualification" / "wp12a_p0" / "case_manifests").glob("*.json"))

    @staticmethod
    def sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def load_policy(self) -> dict[str, Any]:
        return self.policy

    def _run_root(self, policy: Mapping[str, Any], worktree_id: str) -> Path:
        assert worktree_id == "wp12_dynamics"
        return self.store

    def _controller_provenance(self) -> dict[str, str]:
        return dict(self.provenance)

    @staticmethod
    def _stable_fingerprint(value: Mapping[str, Any]) -> str:
        return BATCH._canonical_sha256(value)

    def resolve_targets(self, _scope: str, target: str, _policy: Mapping[str, Any], *, worktree_id: str) -> list[str]:
        if worktree_id != "wp12_dynamics" or target not in self.policy["worktrees"][worktree_id]["allowed_nodeids"]:
            raise SyntheticPolicyError("unregistered exact nodeid")
        return [target]

    def _registered_worktree(
        self, worktree_id: str, target: str, _policy: Mapping[str, Any]
    ) -> tuple[dict[str, Any], Path, Path, dict[str, Any], str]:
        assert worktree_id == "wp12_dynamics"
        module_path = target.split("::", maxsplit=1)[0]
        return (
            self.policy["worktrees"][worktree_id],
            self.science,
            self.science,
            dict(self.identity),
            self.fingerprints[module_path],
        )

    def _wp12_active_registration(
        self, _worktree_id: str, target: str, _entry: Mapping[str, Any], _fingerprint: str
    ) -> dict[str, Any]:
        return self.registrations[target]

    def _sha256(self, path: Path) -> str:
        return self.sha256(path)

    def _node_ledger_context(
        self, _policy: Mapping[str, Any], _store: Path, worktree_id: str
    ) -> tuple[Path, Path, str, dict[str, str]]:
        assert worktree_id == "wp12_dynamics"
        return self.ledger_path, self.store / "locks" / "ledger.lock", MANDATE, dict(self.predecessor)

    def _wp12_dynamics_predecessor_history(
        self, store: Path, predecessor: Mapping[str, str], *, allowed_nodeids: set[str]
    ) -> tuple[Path, dict[str, Any], dict[str, int], int]:
        assert allowed_nodeids == set(NODES)
        path = store / predecessor["path"]
        return path, json.loads(path.read_text(encoding="utf-8")), {}, 0

    def _validate_wp12_dynamics_ledger(
        self, ledger: Mapping[str, Any], *, mandate_id: str, predecessor: Mapping[str, str],
        allowed_nodeids: set[str], predecessor_counts: Mapping[str, int], predecessor_total: int,
        attempt_limit: int, total_limit: int,
    ) -> None:
        assert mandate_id == MANDATE and predecessor == self.predecessor
        assert allowed_nodeids == set(NODES) and attempt_limit == 10 and total_limit == 130
        assert ledger.get("schema") == "qfsolver-development-node-ledger-v2"
        assert ledger.get("mandate_id") == MANDATE and ledger.get("predecessor") == self.predecessor
        assert isinstance(ledger.get("entries"), Mapping)
        assert sum(len(records) for records in ledger["entries"].values()) < 130
        assert predecessor_counts == {} and predecessor_total == 0

    @staticmethod
    @contextlib.contextmanager
    def _node_attempt_locks(*_args: Any, **_kwargs: Any) -> Iterator[None]:
        yield

    @staticmethod
    @contextlib.contextmanager
    def _exclusive_file_lock(*_args: Any, **_kwargs: Any) -> Iterator[None]:
        yield

    @staticmethod
    def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _atomic_json_new(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def _series_root(self, _store: Path, _scope: str, _worktree_id: str) -> Path:
        return self.store / "runs"

    def preflight_wp12_dynamics_pytest(self, target: str, *, policy: Mapping[str, Any]) -> dict[str, Any]:
        assert target in NODES and policy is self.policy
        self.preflight_count += 1
        if self.preflight_count == self.preflight_failure_on:
            raise RuntimeError("synthetic interruption before next JIT preflight")
        preflight_id = f"pf-{self.preflight_count:012x}"
        path = self.preflight_root / preflight_id / "preflight.json"
        path.parent.mkdir(parents=True, exist_ok=False)
        ledger_sha = self.sha256(self.ledger_path)
        source_module = target.split("::", maxsplit=1)[0]
        source_fingerprint = self.fingerprints[source_module]
        record = {
            "schema": "qfsolver-development-wp12-dynamics-preflight-v2",
            "mode": "DEVELOPMENT_AUTONOMOUS",
            "mandate_id": MANDATE,
            "worktree_id": "wp12_dynamics",
            "target": target,
            "preflight_id": preflight_id,
            "phase": "PYTEST_COLLECT_ONLY",
            "state": "PREFLIGHT_PASS",
            "bodies_executed": False,
            "attempt_reserved": False,
            "ledger_touched": False,
            "identity": dict(self.identity),
            "identity_after": dict(self.identity),
            "source_fingerprint": source_fingerprint,
            "source_fingerprint_after": source_fingerprint,
            "controller_provenance": dict(self.provenance),
            "controller_provenance_after": dict(self.provenance),
            "solver_origin_expected": str(self.science / "src" / "solveur" / "__init__.py"),
            "solver_origin_observed": str(self.science / "src" / "solveur" / "__init__.py"),
            "collected_nodeids": [target],
            "skip_markers": [],
            "return_code": 0,
            "registration": {
                "target": target,
                "source_fingerprint": source_fingerprint,
                "selected_dofs": self.registrations[target]["selected_dofs"],
                "timeout_seconds": 300,
            },
            "budgets": {"timeout_seconds": 300},
            "attempt_ledger": {
                "path": str(self.ledger_path),
                "sha256_before": ledger_sha,
                "sha256_after": ledger_sha,
                "touched": False,
                "predecessor": dict(self.predecessor),
                "predecessor_sha256_before": self.predecessor["sha256"],
                "predecessor_sha256_after": self.predecessor["sha256"],
            },
        }
        path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        digest = self.sha256(path)
        (path.parent / "preflight.sha256.json").write_text(
            json.dumps({"sha256": digest}, sort_keys=True) + "\n", encoding="utf-8"
        )
        return {
            "state": "PREFLIGHT_PASS",
            "preflight_id": preflight_id,
            "bodies_executed": False,
            "receipt_sha256": digest,
        }

    def prepare_wp12_execution_manifest(
        self, worktree_id: str, target: str, authorization_id: str, *, preflight_id: str
    ) -> dict[str, str]:
        assert worktree_id == "wp12_dynamics" and target in NODES and preflight_id
        path = self.store / "authorizations" / worktree_id / f"{authorization_id}.json"
        preflight_path = self.preflight_root / preflight_id / "preflight.json"
        self._atomic_json_new(
            path,
            {
                "schema": "qfsolver-wp12-development-execution-v1",
                "state": "PREPARED_NOT_AUTHORIZED",
                "execution_authorized": False,
                "do_not_execute": True,
                "authorization_id": authorization_id,
                "worktree_id": "wp12_dynamics",
                "mandate_id": MANDATE,
                "campaign_id": self.policy["worktrees"]["wp12_dynamics"]["campaign_id"],
                "target": target,
                "identity": dict(self.identity),
                "source_fingerprint": self.fingerprints[target.split("::", maxsplit=1)[0]],
                "controller_fingerprint": self._stable_fingerprint(self.provenance),
                "preflight": {
                    "preflight_id": preflight_id,
                    "receipt_path": str(preflight_path),
                    "receipt_sha256": self.sha256(preflight_path),
                },
            },
        )
        if self.ledger_mutation_during_manifest_prepare:
            ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            ledger["entries"]["foreign:changed-after-preflight"] = [{"attempt": 1, "state": "PASS"}]
            self._atomic_json(self.ledger_path, ledger)
        return {"state": "PREPARED_NOT_AUTHORIZED", "path": str(path), "target": target}

    def _validate_wp12_dynamics_preflight_receipt(
        self, store: Path, preflight_id: str, *, target: str, **_kwargs: Any
    ) -> tuple[Path, str]:
        path = store / "worktrees" / "wp12_dynamics" / "preflight" / preflight_id / "preflight.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        assert receipt["target"] == target and receipt["bodies_executed"] is False
        return path, self.sha256(path)

    def run_pytest(
        self, _scope: str, target: str, series_id: str, *, execution_manifest: Path,
        batch_context: Mapping[str, Any], **_kwargs: Any,
    ) -> tuple[dict[str, Any], int]:
        manifest = json.loads(execution_manifest.read_text(encoding="utf-8"))
        assert manifest["state"] == "OWNER_AUTHORIZED"
        assert manifest["execution_authorized"] is True and manifest["do_not_execute"] is False
        assert manifest["batch_authorization"] == dict(batch_context)
        assert manifest["owner_decision"]["decision_id"] == batch_context["decision_id"]
        preflight = json.loads(Path(manifest["preflight"]["receipt_path"]).read_text(encoding="utf-8"))
        if preflight["attempt_ledger"]["sha256_after"] != self.sha256(self.ledger_path):
            raise SyntheticPolicyError("ledger changed after the JIT preflight; refused before reservation")
        self.run_targets.append(target)
        self.reservation_count += 1
        ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        key = f"{MANDATE}:wp12_dynamics:{target}"
        attempts = ledger["entries"].setdefault(key, [])
        ordinal = next(index for index, item in enumerate(NODES, start=1) if item == target)
        state = self.outcomes[ordinal - 1]
        record = {
            "attempt": len(attempts) + 1,
            "authorization_id": batch_context["authorization_id"],
            "batch": dict(batch_context),
            "controller_fingerprint": self._stable_fingerprint(self.provenance),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "owner_decision_id": batch_context["decision_id"],
            "post_source_fingerprint": self.fingerprints[target.split("::", maxsplit=1)[0]],
            "series_id": series_id,
            "source_fingerprint": self.fingerprints[target.split("::", maxsplit=1)[0]],
            "state": "RESERVED" if self.interrupt_after_reservation else state,
        }
        attempts.append(record)
        if self.foreign_mutation_after_first and self.reservation_count == 1:
            ledger["entries"]["foreign:unregistered"] = [{"attempt": 1, "state": "PASS"}]
        self._atomic_json(self.ledger_path, ledger)
        run_path = self._series_root(self.store, "fem_exploratory", "wp12_dynamics") / series_id / "attempt-0001" / "run.json"
        self._atomic_json(
            run_path,
            {
                "batch_context": dict(batch_context),
                "state": record["state"],
                "target": [target],
                "identity": dict(self.identity),
                "source_fingerprint": self.fingerprints[target.split("::", maxsplit=1)[0]],
                "controller_provenance": dict(self.provenance),
                "execution_manifest": {
                    "path": str(execution_manifest.resolve()),
                    "sha256": self.sha256(execution_manifest),
                },
            },
        )
        if not self.interrupt_after_reservation and state in {"PASS", "PYTEST_FAILED"}:
            output_dir = run_path.parent / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            failure = (
                '<failure type="AssertionError">synthetic assertion failure</failure>'
                if state == "PYTEST_FAILED" and self.pytest_failure_kind == "failure"
                else '<error type="RuntimeError">synthetic setup error</error>'
                if state == "PYTEST_FAILED"
                else ""
            )
            (output_dir / "pytest-results.xml").write_text(
                f'<testsuite tests="1" failures="{int(state == "PYTEST_FAILED" and self.pytest_failure_kind == "failure")}" errors="{int(state == "PYTEST_FAILED" and self.pytest_failure_kind == "error")}" skipped="0">'
                f'<testcase name="{target.split("::", maxsplit=1)[1]}">{failure}</testcase></testsuite>\n',
                encoding="utf-8",
            )
        if self.interrupt_after_reservation:
            raise KeyboardInterrupt("synthetic interruption after reservation")
        return {"record": str(run_path), "series_id": series_id, "state": state}, 0 if state == "PASS" else 1


def _authorize_fixture(controller: FakeController, campaign_id: str = "wp12a-p0-test-campaign") -> tuple[Path, str, Path, str]:
    prepared = BATCH.prepare_contract(controller, campaign_id, controller.case_paths)
    contract_path = Path(prepared["contract_path"])
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    decision_path = Path(contract["decision_path"])
    decision = {
        "schema": BATCH.BATCH_DECISION_SCHEMA,
        "state": "OWNER_AUTHORIZED",
        "execution_authorized": True,
        "do_not_execute": False,
        "campaign_id": campaign_id,
        "contract_path": str(contract_path),
        "contract_sha256": prepared["contract_sha256"],
        "decision_id": "owner-synthetic-p0-batch-01",
        "approved_by": "Owner",
        "approved_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "Synthetic test fixture only; no scientific execution is authorized.",
        "approved_cases": BATCH._expected_owner_cases(contract),
        "no_retry": True,
    }
    decision_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return (
        contract_path,
        prepared["contract_sha256"],
        decision_path,
        FakeController.sha256(decision_path),
    )


@pytest.fixture
def batch_harness(tmp_path: Path) -> tuple[FakeController, tuple[Path, str, Path, str]]:
    controller = FakeController(tmp_path)
    return controller, _authorize_fixture(controller)


def _run(controller: FakeController, auth: tuple[Path, str, Path, str], *, resume: bool = False) -> dict[str, Any]:
    return BATCH.run_batch(controller, *auth, resume=resume)


def test_batch_runs_six_exact_cases_sequentially_with_independent_receipts(batch_harness: Any) -> None:
    controller, auth = batch_harness
    result = _run(controller, auth)

    assert result["state"] == "BATCH_COMPLETED"
    assert controller.run_targets == list(NODES)
    assert controller.preflight_count == len(NODES)
    assert controller.reservation_count == len(NODES)
    batch_dir = auth[0].parent
    receipts = sorted((batch_dir / "case-receipts").glob("case-*.json"))
    assert len(receipts) == len(NODES)
    assert [json.loads(path.read_text(encoding="utf-8"))["nodeid"] for path in receipts] == list(NODES)
    assert len({json.loads(path.read_text(encoding="utf-8"))["run_record_sha256"] for path in receipts}) == len(NODES)


def test_contract_preserves_per_case_source_fingerprints_for_one_git_identity(tmp_path: Path) -> None:
    controller = FakeController(tmp_path)
    fingerprints = {
        controller.fingerprints[target.split("::", maxsplit=1)[0]] for target in NODES
    }
    assert len(fingerprints) > 1

    prepared = BATCH.prepare_contract(controller, "wp12a-p0-case-fingerprints", controller.case_paths)
    contract = json.loads(Path(prepared["contract_path"]).read_text(encoding="utf-8"))

    assert {json.dumps(case["identity"], sort_keys=True) for case in contract["ordered_cases"]} == {
        json.dumps(controller.identity, sort_keys=True)
    }
    assert {case["source_fingerprint"] for case in contract["ordered_cases"]} == fingerprints
    assert [case["nodeid"] for case in contract["ordered_cases"]] == list(NODES)


def test_contract_rejects_different_git_identities_even_with_valid_case_fingerprints(tmp_path: Path) -> None:
    controller = FakeController(tmp_path)
    registered_worktree = controller._registered_worktree

    def divergent_identity(
        worktree_id: str, target: str, policy: Mapping[str, Any]
    ) -> tuple[dict[str, Any], Path, Path, dict[str, Any], str]:
        result = registered_worktree(worktree_id, target, policy)
        if target == NODES[1]:
            result[3]["head"] = "f" * 40
        return result

    controller._registered_worktree = divergent_identity  # type: ignore[method-assign]

    with pytest.raises(SyntheticPolicyError, match="frozen scientific checkout identity"):
        BATCH.prepare_contract(controller, "wp12a-p0-divergent-git-identity", controller.case_paths)


def test_scientific_failure_continues_only_when_closed_contract_allows_it(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.outcomes[0] = "PYTEST_FAILED"

    result = _run(controller, auth)

    assert result["state"] == "BATCH_COMPLETED"
    assert controller.run_targets == list(NODES)
    first = json.loads((auth[0].parent / "case-receipts" / "case-01.json").read_text(encoding="utf-8"))
    assert first["attempt_state"] == "PYTEST_FAILED"


def test_infrastructure_failure_stops_before_the_next_case(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.outcomes[0] = "LAUNCH_FAILED"

    result = _run(controller, auth)

    assert result["state"] == "BATCH_STOPPED_BY_CASE_RESULT"
    assert controller.run_targets == [NODES[0]]
    assert controller.reservation_count == 1


@pytest.mark.parametrize(
    ("state", "xml", "expected"),
    [
        (
            "PYTEST_FAILED",
            '<testsuite><testcase name="test_case"><failure type="AssertionError"/></testcase></testsuite>',
            ("SCIENTIFIC_ASSERTION_FAILED", "CONTINUE"),
        ),
        (
            "PYTEST_FAILED",
            '<testsuite><testcase name="test_case"><failure type="RuntimeError"/></testcase></testsuite>',
            ("UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP"),
        ),
        (
            "PYTEST_FAILED",
            '<testsuite><testcase name="test_case"><skipped/></testcase></testsuite>',
            ("UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP"),
        ),
        (
            "PYTEST_FAILED",
            '<testsuite><testcase name="test_case"><failure type="AssertionError"/></testcase>'
            '<testcase name="other"/></testsuite>',
            ("UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP"),
        ),
        (
            "LAUNCH_FAILED",
            '<testsuite><testcase name="test_case"/></testsuite>',
            ("UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE", "STOP"),
        ),
    ],
)
def test_junit_classification_allows_only_one_exact_assertion_failure(
    tmp_path: Path, state: str, xml: str, expected: tuple[str, str]
) -> None:
    run_path = tmp_path / "attempt" / "run.json"
    output = run_path.parent / "output"
    output.mkdir(parents=True)
    (output / "pytest-results.xml").write_text(xml, encoding="utf-8")
    classification, disposition, _junit = BATCH._classify_batch_result(
        FakeController, {"state": state}, run_path, "tests/unit/test_synthetic.py::test_case"
    )
    assert (classification, disposition) == expected


def test_pytest_setup_error_is_archived_but_does_not_continue(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.outcomes[0] = "PYTEST_FAILED"
    controller.pytest_failure_kind = "error"

    result = _run(controller, auth)

    assert result["state"] == "BATCH_STOPPED_BY_CASE_RESULT"
    assert controller.run_targets == [NODES[0]]
    receipt = json.loads((auth[0].parent / "case-receipts" / "case-01.json").read_text(encoding="utf-8"))
    assert receipt["failure_classification"] == "UNCLASSIFIED_OR_INFRASTRUCTURE_FAILURE"
    assert receipt["batch_disposition"] == "STOP"

    receipt["batch_disposition"] = "CONTINUE"
    receipt_path = auth[0].parent / "case-receipts" / "case-01.json"
    controller._atomic_json(receipt_path, receipt)
    with pytest.raises(SyntheticPolicyError, match="result classification changed"):
        _run(controller, auth, resume=True)
    assert controller.run_targets == [NODES[0]]


def test_foreign_ledger_mutation_stops_after_the_first_attempt(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.foreign_mutation_after_first = True

    with pytest.raises(SyntheticPolicyError, match="outside its exact case list"):
        _run(controller, auth)

    assert controller.run_targets == [NODES[0]]
    assert controller.preflight_count == 1
    assert not (auth[0].parent / "case-receipts" / "case-01.json").exists()


def test_interruption_between_cases_resumes_without_repeating_completed_case(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.preflight_failure_on = 2

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        _run(controller, auth)
    assert controller.run_targets == [NODES[0]]
    assert (auth[0].parent / "case-receipts" / "case-01.json").is_file()

    controller.preflight_failure_on = None
    result = _run(controller, auth, resume=True)

    assert result["state"] == "BATCH_COMPLETED"
    assert controller.run_targets == list(NODES)
    assert controller.reservation_count == len(NODES)


def test_interruption_after_reservation_consumes_attempt_and_cannot_retry(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.interrupt_after_reservation = True

    with pytest.raises(KeyboardInterrupt, match="after reservation"):
        _run(controller, auth)
    controller.interrupt_after_reservation = False

    with pytest.raises(SyntheticPolicyError, match="unfinished"):
        _run(controller, auth, resume=True)

    assert controller.reservation_count == 1
    assert controller.preflight_count == 1


def test_completed_batch_requires_explicit_resume_and_never_duplicates_attempts(batch_harness: Any) -> None:
    controller, auth = batch_harness
    assert _run(controller, auth)["state"] == "BATCH_COMPLETED"
    with pytest.raises(SyntheticPolicyError, match="progress exists"):
        _run(controller, auth)

    result = _run(controller, auth, resume=True)

    assert result["state"] == "BATCH_COMPLETED"
    assert controller.reservation_count == len(NODES)


@pytest.mark.parametrize("artifact", ["preflight", "prepared_manifest", "authorized_manifest", "progress"])
def test_resume_refuses_changed_archived_artifact_without_reserving_again(
    batch_harness: Any, artifact: str
) -> None:
    controller, auth = batch_harness
    assert _run(controller, auth)["state"] == "BATCH_COMPLETED"
    batch_dir = auth[0].parent
    case_receipt_path = batch_dir / "case-receipts" / "case-01.json"
    case_receipt = json.loads(case_receipt_path.read_text(encoding="utf-8"))
    if artifact == "preflight":
        path = Path(case_receipt["preflight_receipt_path"])
    elif artifact == "prepared_manifest":
        path = Path(case_receipt["prepared_manifest_path"])
    elif artifact == "authorized_manifest":
        path = Path(case_receipt["authorized_manifest_path"])
    else:
        path = batch_dir / "progress.json"
        progress = json.loads(path.read_text(encoding="utf-8"))
        progress["ledger_sha256"] = "0" * 64
        controller._atomic_json(path, progress)
        with pytest.raises(SyntheticPolicyError, match="progress ledger checkpoint"):
            _run(controller, auth, resume=True)
        assert controller.reservation_count == len(NODES)
        return

    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(SyntheticPolicyError):
        _run(controller, auth, resume=True)
    assert controller.reservation_count == len(NODES)


@pytest.mark.parametrize("mutation", ["source", "controller", "budget", "case_manifest"])
def test_authorization_refuses_changed_source_budget_or_case_manifest(batch_harness: Any, mutation: str) -> None:
    controller, auth = batch_harness
    contract = json.loads(auth[0].read_text(encoding="utf-8"))
    case = contract["ordered_cases"][0]
    if mutation == "source":
        source_path = controller.science / case["nodeid"].split("::", maxsplit=1)[0]
        source_path.write_text("# changed source identity\n", encoding="utf-8")
    elif mutation == "controller":
        controller.provenance["tree"] = "f" * 40
    elif mutation == "case_manifest":
        manifest_path = Path(case["case_manifest"]["path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["criteria"]["acceptance"] = "silently changed"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    else:
        controller.registrations[NODES[0]]["timeout_seconds"] = 301

    with pytest.raises(SyntheticPolicyError):
        _run(controller, auth)

    assert controller.reservation_count == 0


def test_contract_refuses_a_nodeid_outside_the_closed_candidate_set(tmp_path: Path) -> None:
    controller = FakeController(tmp_path)
    extra = json.loads(controller.case_paths[-1].read_text(encoding="utf-8"))
    extra["nodeid"] = "tests/unit/test_unreviewed.py::test_not_registered"
    extra_path = controller.ROOT / "qualification" / "wp12a_p0" / "case_manifests" / "unreviewed.json"
    extra_path.write_text(json.dumps(extra, sort_keys=True) + "\n", encoding="utf-8")
    paths = [*controller.case_paths[:-1], extra_path]

    with pytest.raises(SyntheticPolicyError, match="unregistered exact nodeid"):
        BATCH.prepare_contract(controller, "wp12a-p0-extra-case", paths)


def test_batch_refuses_stale_ledger_before_preflight_or_reservation(batch_harness: Any) -> None:
    controller, auth = batch_harness
    ledger = json.loads(controller.ledger_path.read_text(encoding="utf-8"))
    ledger["entries"]["outside-campaign"] = [{"attempt": 1, "state": "PASS"}]
    controller._atomic_json(controller.ledger_path, ledger)

    with pytest.raises(SyntheticPolicyError, match="outside its exact case list"):
        _run(controller, auth)

    assert controller.preflight_count == 0
    assert controller.reservation_count == 0


def test_batch_refuses_when_the_entire_case_list_does_not_fit_remaining_budget(tmp_path: Path) -> None:
    controller = FakeController(tmp_path)
    ledger = json.loads(controller.ledger_path.read_text(encoding="utf-8"))
    ledger["entries"] = {f"{MANDATE}:wp12_dynamics:prior-{index}": [{}] for index in range(125)}
    controller._atomic_json(controller.ledger_path, ledger)

    with pytest.raises(SyntheticPolicyError, match="does not fit"):
        BATCH.prepare_contract(controller, "wp12a-p0-budget-test", controller.case_paths)


def test_batch_refuses_when_any_nodeid_has_no_attempt_budget(tmp_path: Path) -> None:
    controller = FakeController(tmp_path)
    ledger = json.loads(controller.ledger_path.read_text(encoding="utf-8"))
    ledger["entries"][f"{MANDATE}:wp12_dynamics:{NODES[0]}"] = [
        {"attempt": index, "state": "PYTEST_FAILED"} for index in range(1, 11)
    ]
    controller._atomic_json(controller.ledger_path, ledger)

    with pytest.raises(SyntheticPolicyError, match="attempt budget is exhausted"):
        BATCH.prepare_contract(controller, "wp12a-p0-node-budget", controller.case_paths)


def test_ledger_change_between_jit_preflight_and_reservation_refuses_without_reserving(batch_harness: Any) -> None:
    controller, auth = batch_harness
    controller.ledger_mutation_during_manifest_prepare = True

    with pytest.raises(SyntheticPolicyError, match="after the JIT preflight"):
        _run(controller, auth)

    assert controller.preflight_count == 1
    assert controller.reservation_count == 0
