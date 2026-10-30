"""Synthetic-only checks for the non-attested local V&V orchestration helpers."""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import local_vv as runner
from scripts.local_vv import execution as execution_module
from scripts.local_vv import manifest as manifest_module
from scripts.local_vv import process as process_module


NODEID = "tests/unit/test_synthetic_case.py::test_synthetic_case"
COMMIT = "a" * 40
TREE = "b" * 40


def _manifest(tmp_path: Path) -> dict[str, object]:
    checkouts = {}
    for key in ("science", "runner", "tests"):
        root = tmp_path / key
        root.mkdir()
        checkouts[key] = {"path": str(root), "commit": COMMIT, "tree": TREE}
    tests_root = Path(checkouts["tests"]["path"])
    node_file = tests_root / "tests/unit/test_synthetic_case.py"
    node_file.parent.mkdir(parents=True)
    node_file.write_text("def test_synthetic_case():\n    assert True\n", encoding="utf-8")
    import importlib.metadata

    return {
        "schema": runner.MANIFEST_SCHEMA,
        "policy": "QUALIFICATION_LOCAL_VV",
        "status": "PREPARED_NOT_AUTHORIZED",
        "execution_authorized": False,
        "numerical_execution_performed": False,
        "wp12_status": "OPEN",
        "campaign_id": "SYNTHETIC-CAMPAIGN-001",
        "identities": checkouts,
        "environment": {
            "python": {
                "executable": sys.executable,
                "version": platform.python_version(),
                "venv": sys.prefix,
                "solveur_version": "synthetic-source-version",
                "distribution_version": None,
            },
            "packages": {"pytest": importlib.metadata.version("pytest")},
            "thread_environment": {"OPENBLAS_NUM_THREADS": "1"},
        },
        "evidence_root": str(tmp_path / "evidence"),
        "cases": [
            {
                "case_id": "SYNTHETIC-CASE-001",
                "nodeid": NODEID,
                "test_checkout": "tests",
                "status": "PREPARED_NOT_AUTHORIZED",
                "oracle_id": "SYNTHETIC-ORACLE",
                "acceptance_ref": "synthetic-only",
                "command_profile": runner.COMMAND_PROFILE,
                "timeout_seconds": 5,
                "output_limit_bytes": 4096,
                "max_attempts": 1,
                "file_inventory": [
                    {
                        "checkout": "tests",
                        "path": "tests/unit/test_synthetic_case.py",
                        "sha256": runner.sha256_file(node_file),
                        "git_blob_oid": "c" * 40,
                    }
                ],
            }
        ],
    }


def _decision(manifest: dict[str, object]) -> dict[str, object]:
    case = manifest["cases"][0]
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    return {
        "schema": runner.DECISION_SCHEMA,
        "decision_status": "APPROVED_FOR_EXECUTION",
        "authentication": "OWNER_REVIEW_OUTSIDE_RUNNER; NOT_CRYPTOGRAPHIC",
        "decision_id": "SYNTHETIC-DECISION-001",
        "approved_by": "Synthetic Owner",
        "approved_at_utc": "2026-01-01T00:00:00Z",
        "valid_until_utc": future,
        "campaign_id": manifest["campaign_id"],
        "manifest_sha256": runner.sha256_bytes(b"synthetic manifest"),
        "case_id": case["case_id"],
        "nodeid": case["nodeid"],
        "oracle_id": case["oracle_id"],
        "acceptance_ref": case["acceptance_ref"],
        "command_profile": case["command_profile"],
        "science_identity": {"commit": COMMIT, "tree": TREE},
        "runner_identity": {"commit": COMMIT, "tree": TREE},
        "tests_identity": {"commit": COMMIT, "tree": TREE},
        "python_executable": manifest["environment"]["python"]["executable"],
        "evidence_root": manifest["evidence_root"],
        "attempt_number": 1,
        "max_attempts": 1,
        "timeout_seconds": case["timeout_seconds"],
        "output_limit_bytes": case["output_limit_bytes"],
    }


def test_manifest_accepts_exact_prepared_case_and_rejects_wildcard(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    assert runner.validate_manifest_shape(manifest) == []
    manifest["cases"][0]["nodeid"] = "tests/unit/test_*.py::test_synthetic_case"
    assert any("nodeid" in error for error in runner.validate_manifest_shape(manifest))


def test_manifest_inventory_detects_changed_test_file_hash(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    manifest["cases"][0]["file_inventory"][0]["sha256"] = "0" * 64
    assert runner.validate_manifest_shape(manifest) == []
    with pytest.raises(runner.LocalVVError, match="file hash mismatch"):
        runner.verify_file_inventory(manifest, manifest["cases"][0])


def test_owner_decision_requires_exact_manifest_and_case_bindings(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    case = manifest["cases"][0]
    digest = runner.sha256_bytes(b"synthetic manifest")
    decision = _decision(manifest)
    assert runner.validate_owner_decision(manifest, case, decision, digest) == []
    decision["manifest_sha256"] = "0" * 64
    assert any(
        "manifest SHA-256" in error for error in runner.validate_owner_decision(manifest, case, decision, digest)
    )


def test_owner_decision_rejects_expired_decision(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    case = manifest["cases"][0]
    decision = _decision(manifest)
    decision["valid_until_utc"] = "2000-01-01T00:00:00Z"
    errors = runner.validate_owner_decision(manifest, case, decision, runner.sha256_bytes(b"synthetic manifest"))
    assert any("expired" in error for error in errors)


def test_exact_command_disables_conftest_autoload_and_has_one_nodeid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path)
    case = manifest["cases"][0]
    monkeypatch.setattr(
        process_module,
        "_checkout_path",
        lambda _manifest, key: Path(manifest["identities"][key]["path"]),
    )
    run_dir = tmp_path / "run"
    argv, cwd, _ = runner._case_command(manifest, case, run_dir)
    assert argv[-1] == NODEID
    assert argv.count(NODEID) == 1
    assert "--noconftest" in argv
    assert "addopts=" in argv
    assert "-c" in argv
    assert cwd == Path(manifest["identities"]["tests"]["path"])
    assert "-c" in argv and str(cwd / "pyproject.toml") in argv


def test_cli_refuses_to_accept_a_caller_supplied_command() -> None:
    parser = runner.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--manifest",
                "manifest.json",
                "--decision",
                "decision.json",
                "--case-id",
                "CASE",
                "--command",
                "python",
            ]
        )


def test_validate_path_does_not_create_evidence_directories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    evidence_root = Path(manifest["evidence_root"])
    monkeypatch.setattr(execution_module, "verify_runner_entrypoint", lambda _manifest: "synthetic-runner-entrypoint")
    monkeypatch.setattr(
        execution_module, "inspect_checkout", lambda identity: {"path": identity["path"], "status": "CLEAN"}
    )
    monkeypatch.setattr(execution_module, "verify_file_inventory", lambda *_args: [{"sha256": "c" * 64}])
    monkeypatch.setattr(execution_module, "verify_environment", lambda _manifest: {"synthetic": True})
    monkeypatch.setattr(execution_module, "probe_import_origin", lambda *_args: {"synthetic": True})
    execution_module.validate_all_cases(manifest)
    assert not evidence_root.exists()


def test_runner_entrypoint_must_match_manifested_checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    runner_scripts = Path(manifest["identities"]["runner"]["path"]) / "scripts"
    runner_scripts.mkdir()
    (runner_scripts / "run_local_vv.py").write_text("# synthetic placeholder\n", encoding="utf-8")
    monkeypatch.setattr(
        manifest_module,
        "_checkout_path",
        lambda _manifest, key: Path(manifest["identities"][key]["path"]),
    )
    with pytest.raises(runner.LocalVVError, match="runner entrypoint path mismatch"):
        runner.verify_runner_entrypoint(manifest)


def test_junit_classifier_distinguishes_pass_fail_and_infrastructure(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text('<testsuite><testcase name="test_synthetic_case"/></testsuite>', encoding="utf-8")
    assert runner.classify_junit(junit, NODEID, [NODEID], 0) == "PYTEST_PASS_ONLY"
    junit.write_text(
        '<testsuite><testcase name="test_synthetic_case"><failure/></testcase></testsuite>', encoding="utf-8"
    )
    assert runner.classify_junit(junit, NODEID, [NODEID], 1) == "FAIL"
    assert runner.classify_junit(junit, NODEID, ["other"], 1) == "INFRA_ERROR"
    assert runner.classify_junit(junit, NODEID, [NODEID], None, timed_out=True) == "TIMEOUT"


def test_junit_classifier_does_not_call_skipped_test_a_pass(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuite><testcase name="test_synthetic_case"><skipped/></testcase></testsuite>', encoding="utf-8"
    )
    assert runner.classify_junit(junit, NODEID, [NODEID], 0) == "INCONCLUSIVE"


def test_numeric_payload_is_not_inferred_when_unexposed(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.log"
    stdout.write_text("synthetic output only\n", encoding="utf-8")
    assert runner.extract_numeric_payload(stdout) == ("NOT_EXPOSED", None)


def test_numeric_payload_requires_schema_and_case_identity(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.log"
    stdout.write_text(
        'QF_VV_NUMERIC_RESULT={"schema":"synthetic-v1","case_id":"CASE-001","value":1.0}\n',
        encoding="utf-8",
    )
    assert runner.extract_numeric_payload(stdout) == (
        "EXPOSED_JSON",
        {"schema": "synthetic-v1", "case_id": "CASE-001", "value": 1.0},
    )


def test_numeric_payload_rejects_duplicate_markers(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.log"
    marker = 'QF_VV_NUMERIC_RESULT={"schema":"synthetic-v1","case_id":"CASE-001"}\n'
    stdout.write_text(marker + marker, encoding="utf-8")
    with pytest.raises(runner.LocalVVError, match="at most one"):
        runner.extract_numeric_payload(stdout)


def test_numeric_payload_rejects_non_finite_json(tmp_path: Path) -> None:
    stdout = tmp_path / "stdout.log"
    stdout.write_text('QF_VV_NUMERIC_RESULT={"schema":"x","case_id":"x","value":NaN}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        runner.extract_numeric_payload(stdout)


def test_new_json_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    runner._write_new_json(path, {"status": "first"})
    with pytest.raises(FileExistsError):
        runner._write_new_json(path, {"status": "replacement"})
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "first"


def test_synthetic_child_captures_streams_and_nonzero_exit(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "local_vv" / "fake_child.py"
    stdout = tmp_path / "stdout.log"
    stderr = tmp_path / "stderr.log"
    result = runner.supervise_process(
        [sys.executable, str(fixture), "--stdout", "child-output", "--stderr", "child-error", "--exit-code", "7"],
        cwd=tmp_path,
        environment=dict(os.environ),
        stdout_path=stdout,
        stderr_path=stderr,
        timeout_seconds=5,
        output_limit_bytes=4096,
    )
    assert result["exit_code"] == 7
    assert stdout.read_text(encoding="utf-8").strip() == "child-output"
    assert stderr.read_text(encoding="utf-8").strip() == "child-error"


def test_synthetic_child_timeout_is_classified_without_scientific_failure(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "local_vv" / "fake_child.py"
    result = runner.supervise_process(
        [sys.executable, str(fixture), "--sleep", "2"],
        cwd=tmp_path,
        environment=dict(os.environ),
        stdout_path=tmp_path / "stdout.log",
        stderr_path=tmp_path / "stderr.log",
        timeout_seconds=0,
        output_limit_bytes=4096,
    )
    assert result["timed_out"] is True
    assert result["exit_code"] is not None


def test_synthetic_child_output_cap_is_observed(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "local_vv" / "fake_child.py"
    result = runner.supervise_process(
        [sys.executable, str(fixture), "--stdout", "x" * 2000, "--sleep", "0.5"],
        cwd=tmp_path,
        environment=dict(os.environ),
        stdout_path=tmp_path / "stdout.log",
        stderr_path=tmp_path / "stderr.log",
        timeout_seconds=5,
        output_limit_bytes=64,
    )
    assert result["output_limited"] is True


def test_prepared_manifest_alone_never_calls_supervisor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    called = False

    def forbidden(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        raise AssertionError("scientific supervision must not start in this synthetic test")

    monkeypatch.setattr(execution_module, "supervise_process", forbidden)
    with pytest.raises(runner.LocalVVError, match="DENY_EXECUTION"):
        runner.run_case(manifest, b"synthetic manifest", {}, manifest["cases"][0])
    assert called is False


def test_orchestrator_records_only_synthetic_pass_and_refuses_second_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _manifest(tmp_path)
    case = manifest["cases"][0]
    raw_manifest = b"synthetic manifest"
    decision = _decision(manifest)
    call_count = 0

    def fake_preflight(_manifest: object, _case: object) -> dict[str, object]:
        identity = {"path": str(tmp_path), "commit": COMMIT, "tree": TREE, "status": "CLEAN"}
        return {
            "identities": {key: identity for key in ("science", "runner", "tests")},
            "files": [{"checkout": "tests", "path": "synthetic", "sha256": "c" * 64}],
            "environment": {"synthetic": True},
            "import_origin": {"synthetic": "fake source only"},
        }

    def fake_supervise(
        _argv: list[str], *, stdout_path: Path, stderr_path: Path, **_kwargs: object
    ) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        run_dir = stdout_path.parent
        stdout_path.write_text("synthetic child completed\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        selection = {
            "collected_nodeids": [NODEID],
            "exact_match": True,
            "source_import_ok": True,
            "source_import": str(Path(manifest["identities"]["science"]["path"]) / "src" / "solveur" / "__init__.py"),
        }
        (run_dir / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
        (run_dir / "junit.xml").write_text(
            '<testsuite><testcase name="test_synthetic_case"/></testsuite>', encoding="utf-8"
        )
        return {
            "exit_code": 0,
            "timed_out": False,
            "output_limited": False,
            "interrupted": False,
            "duration_seconds": 0.001,
            "stdout_bytes": stdout_path.stat().st_size,
            "stderr_bytes": 0,
        }

    identity = {"path": str(tmp_path), "commit": COMMIT, "tree": TREE, "status": "CLEAN"}
    monkeypatch.setattr(execution_module, "_preflight", fake_preflight)
    monkeypatch.setattr(execution_module, "inspect_checkout", lambda _identity: identity)
    monkeypatch.setattr(execution_module, "verify_file_inventory", lambda *_args: [{"sha256": "c" * 64}])
    monkeypatch.setattr(execution_module, "_case_command", lambda *_args: (["synthetic-child"], tmp_path, {}))
    monkeypatch.setattr(execution_module, "supervise_process", fake_supervise)
    monkeypatch.setattr(execution_module, "extract_numeric_payload", lambda _path: ("NOT_EXPOSED", None))

    first = runner.run_case(manifest, raw_manifest, decision, case)
    assert first["status"] == "PYTEST_PASS_ONLY"
    assert Path(first["receipt"]).is_file()
    receipt = json.loads(Path(first["receipt"]).read_text(encoding="utf-8"))
    assert receipt["numeric_observables"]["status"] == "NOT_EXPOSED"
    assert receipt["output_hashes"]
    with pytest.raises(runner.LocalVVError, match="already reserved"):
        runner.run_case(manifest, raw_manifest, decision, case)
    assert call_count == 1


def test_orchestrator_rejects_missing_required_numeric_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(tmp_path)
    case = manifest["cases"][0]
    case["numeric_payload_schema"] = "synthetic-observables-v1"
    raw_manifest = b"synthetic manifest requiring output"
    decision = _decision(manifest)

    def fake_preflight(_manifest: object, _case: object) -> dict[str, object]:
        identity = {"path": str(tmp_path), "commit": COMMIT, "tree": TREE, "status": "CLEAN"}
        return {
            "identities": {key: identity for key in ("science", "runner", "tests")},
            "files": [{"checkout": "tests", "path": "synthetic", "sha256": "c" * 64}],
            "environment": {"synthetic": True},
            "import_origin": {"synthetic": "fake source only"},
        }

    def fake_supervise(
        _argv: list[str], *, stdout_path: Path, stderr_path: Path, **_kwargs: object
    ) -> dict[str, object]:
        run_dir = stdout_path.parent
        stdout_path.write_text("synthetic child completed without required payload\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        selection = {
            "collected_nodeids": [NODEID],
            "exact_match": True,
            "source_import_ok": True,
            "source_import": str(Path(manifest["identities"]["science"]["path"]) / "src" / "solveur" / "__init__.py"),
        }
        (run_dir / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
        (run_dir / "junit.xml").write_text(
            '<testsuite><testcase name="test_synthetic_case"/></testsuite>', encoding="utf-8"
        )
        return {
            "exit_code": 0,
            "timed_out": False,
            "output_limited": False,
            "interrupted": False,
            "duration_seconds": 0.001,
            "stdout_bytes": stdout_path.stat().st_size,
            "stderr_bytes": 0,
        }

    identity = {"path": str(tmp_path), "commit": COMMIT, "tree": TREE, "status": "CLEAN"}
    monkeypatch.setattr(execution_module, "_preflight", fake_preflight)
    monkeypatch.setattr(execution_module, "inspect_checkout", lambda _identity: identity)
    monkeypatch.setattr(execution_module, "verify_file_inventory", lambda *_args: [{"sha256": "c" * 64}])
    monkeypatch.setattr(execution_module, "_case_command", lambda *_args: (["synthetic-child"], tmp_path, {}))
    monkeypatch.setattr(execution_module, "supervise_process", fake_supervise)
    monkeypatch.setattr(execution_module, "extract_numeric_payload", lambda _path: ("NOT_EXPOSED", None))

    result = runner.run_case(manifest, raw_manifest, decision, case)
    assert result["status"] == "INFRA_ERROR"
    receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
    assert receipt["numeric_observables"]["status"] == "NOT_EXPOSED"
    assert receipt["numeric_observables"]["error"] == "required numeric result marker is missing"


def test_selection_plugin_writes_only_exact_synthetic_nodeid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import local_vv_pytest_plugin as plugin

    source_root = tmp_path / "source" / "src"
    package_dir = source_root / "solveur"
    package_dir.mkdir(parents=True)
    init_file = package_dir / "__init__.py"
    init_file.write_text("# synthetic source only\n", encoding="utf-8")
    selection = tmp_path / "selection.json"
    monkeypatch.setenv("QF_LOCAL_VV_EXPECTED_NODEID", NODEID)
    monkeypatch.setenv("QF_LOCAL_VV_SELECTION_PATH", str(selection))
    monkeypatch.setenv("QF_LOCAL_VV_EXPECTED_SOURCE_ROOT", str(source_root))
    monkeypatch.setitem(sys.modules, "solveur", SimpleNamespace(__file__=str(init_file)))
    session = SimpleNamespace(items=[SimpleNamespace(nodeid=NODEID)])
    plugin.pytest_collection_finish(session)
    payload = json.loads(selection.read_text(encoding="utf-8"))
    assert payload["collected_nodeids"] == [NODEID]
    assert payload["exact_match"] is True
