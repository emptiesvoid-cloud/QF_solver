from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "development_autonomous.py"
SPEC = importlib.util.spec_from_file_location("development_autonomous", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PLUGIN_PATH = SCRIPT_PATH.with_name("development_autonomous_pytest_plugin.py")
PLUGIN_SPEC = importlib.util.spec_from_file_location("development_autonomous_pytest_plugin", PLUGIN_PATH)
assert PLUGIN_SPEC is not None and PLUGIN_SPEC.loader is not None
PLUGIN = importlib.util.module_from_spec(PLUGIN_SPEC)
sys.modules[PLUGIN_SPEC.name] = PLUGIN
PLUGIN_SPEC.loader.exec_module(PLUGIN)


def _policy() -> dict:
    return MODULE.load_policy()


def test_policy_registers_only_owner_authorized_worktrees_and_keeps_qualification_separate() -> None:
    policy = _policy()
    assert policy["mode"] == "DEVELOPMENT_AUTONOMOUS"
    assert set(policy["worktrees"]) == {"d01", "c01", "e01"}
    assert policy["worktrees"]["d01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["c01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["e01"]["mode"] == "math_non_fem"
    assert policy["worktrees"]["d01"]["allowed_nodeids"] == [
        "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::test_wp05_native_modal_and_residual_flexibility_characterization[M3]"
    ]
    assert "QUALIFICATION_RELEASE" not in policy["worktrees"]


def test_each_worktree_has_a_separate_output_namespace(tmp_path: Path) -> None:
    assert MODULE._series_root(tmp_path, "fem_exploratory", "d01") == tmp_path / "worktrees" / "d01"
    assert MODULE._series_root(tmp_path, "fem_exploratory", "c01") == tmp_path / "worktrees" / "c01"
    assert MODULE._series_root(tmp_path, "math_non_fem", "e01") == tmp_path / "worktrees" / "e01"
    assert MODULE._series_root(tmp_path, "unit", None) == tmp_path / "standard" / "unit"
    with pytest.raises(MODULE.PolicyError, match="unknown worktree"):
        MODULE._series_root(tmp_path, "fem_exploratory", "e02")


def test_run_provenance_records_controller_and_runtime_identity() -> None:
    provenance = MODULE._controller_provenance()
    assert provenance["identity"]["root"] == str(MODULE.ROOT.resolve())
    assert set(provenance["sha256"]) == {"runner", "pytest_plugin", "policy"}
    assert all(len(digest) == 64 for digest in provenance["sha256"].values())
    assert provenance["runtime"]["python_version"]
    assert provenance["runtime"]["pytest_version"]


def test_standard_test_target_is_confined_to_its_scope() -> None:
    policy = _policy()
    target = "tests/unit/test_execution_contract.py::test_invalid_contract_is_rejected"
    assert MODULE.resolve_targets("unit", target, policy) == [target]
    with pytest.raises(MODULE.PolicyError, match="broad suites are not auto-enabled"):
        MODULE.resolve_targets("unit", None, policy)
    with pytest.raises(MODULE.PolicyError, match="exact pytest test-function nodeid"):
        MODULE.resolve_targets("unit", "tests/unit/test_execution_contract.py", policy)
    with pytest.raises(MODULE.PolicyError, match="below tests/unit"):
        MODULE.resolve_targets(
            "unit",
            "tests/integration/test_demonstration_api.py::test_outside_scope",
            policy,
        )
    with pytest.raises(MODULE.PolicyError, match="cannot traverse"):
        MODULE.resolve_targets("unit", "tests/unit/../../scripts/test_release.py::test_outside", policy)


def test_fem_scope_accepts_only_exact_registered_nodeids_and_worktree_pairs() -> None:
    policy = _policy()
    d01 = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    assert MODULE.resolve_targets("fem_exploratory", d01, policy, worktree_id="d01") == [d01]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("fem_exploratory", d01.replace("[M3]", "[M2]"), policy, worktree_id="d01")
    with pytest.raises(MODULE.PolicyError, match="worktree e01 is not authorized"):
        MODULE.resolve_targets("fem_exploratory", d01, policy, worktree_id="e01")
    with pytest.raises(MODULE.PolicyError, match="registered worktree ID"):
        MODULE.resolve_targets("fem_exploratory", d01, policy)


def test_c01_scope_contains_only_registered_legacy_dimensional_and_mechanics_nodes() -> None:
    policy = _policy()
    c01 = policy["worktrees"]["c01"]["allowed_nodeids"]
    assert len(c01) == 18
    assert any("frozen_legacy_counterexample" in nodeid for nodeid in c01)
    assert any("dimensional_v1" in nodeid for nodeid in c01)
    assert any("contact_equilibrium_diagnostic" in nodeid for nodeid in c01)
    assert all(nodeid.startswith("tests/unit/") for nodeid in c01)
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("fem_exploratory", "tests/unit/test_wpc01_gf5a_fe_qualification.py::test_case", policy, worktree_id="c01")


def test_e01_scope_is_math_only_and_rejects_element_or_fem_targets() -> None:
    policy = _policy()
    e01 = policy["worktrees"]["e01"]["allowed_nodeids"]
    assert len(e01) == 15
    assert all("test_wp_e01" in nodeid for nodeid in e01)
    assert all(not any(word in nodeid.lower() for word in ("tet", "hex", "beam", "assembly", "fem")) for nodeid in e01)
    assert MODULE.resolve_targets("math_non_fem", e01[0], policy, worktree_id="e01") == [e01[0]]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("math_non_fem", "tests/unit/test_wp_e01m_hencky_material_point.py::test_tet4_force_adapter_matches_uniform_pk1_reference", policy, worktree_id="e01")


def test_registered_worktree_identity_and_solver_source_are_verified() -> None:
    policy = _policy()
    target = policy["worktrees"]["e01"]["allowed_nodeids"][0]
    entry, root, source_root, identity, fingerprint = MODULE._registered_worktree("e01", target, policy)
    assert root == Path(entry["git_root"]).resolve()
    assert source_root == (root / "src").resolve()
    assert identity["branch"] == entry["branch"]
    assert identity["head"]
    assert len(fingerprint) == 64
    assert (source_root / "solveur" / "__init__.py").is_file()


def test_child_environment_is_noninteractive_and_cannot_inherit_qualification_switches(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    environment = MODULE.build_child_environment(
        tmp_path / "scratch",
        {
            "WPC02_AR_NATIVE_OWNER_GO_TOKEN": "qualification-token",
            "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256": "digest",
            "QF_SOLVER_RUN_EVIDENCE": "1",
            "QF_FAKE_QUALIFICATION_OWNER": "1",
            "QF_WP_D01_BJ_SOURCE_SHA": "stale",
            "PYTEST_ADDOPTS": "--collect-only",
            "PYTEST_PLUGINS": "unexpected",
            "PYTHONHOME": "unexpected",
            "KEEP_ME": "yes",
        },
        source_root=source_root,
        d01_source_sha="a" * 40,
    )
    assert "WPC02_AR_NATIVE_OWNER_GO_TOKEN" not in environment
    assert "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256" not in environment
    assert "QF_FAKE_QUALIFICATION_OWNER" not in environment
    assert environment["QF_SOLVER_RUN_EVIDENCE"] == "0"
    assert environment["QF_WP_D01_BJ_SOURCE_SHA"] == "a" * 40
    assert environment["PYTHONPATH"] == str(source_root)
    assert environment["QF_DEVELOPMENT_AUTONOMOUS"] == "1"
    assert "PYTEST_ADDOPTS" not in environment and "PYTEST_PLUGINS" not in environment
    assert "PYTHONHOME" not in environment and "PYTHONSTARTUP" not in environment
    assert environment["KEEP_ME"] == "yes"
    assert environment["TMP"] == str(tmp_path / "scratch")


def test_registered_command_is_fixed_to_one_target_and_checks_import_origin(tmp_path: Path) -> None:
    policy = _policy()
    target = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=Path(policy["worktrees"]["d01"]["root"]),
        source_root=Path(policy["worktrees"]["d01"]["root"]) / "src",
        allow_native_skip_override=True,
    )
    assert command[:3] == [sys.executable, "-B", "-c"]
    assert "wrong solveur import origin" in command[3]
    assert "QF_DEV_SOLVER_ORIGIN=" in command[3]
    assert command[-1] == target
    with pytest.raises(MODULE.PolicyError, match="one exact nodeid"):
        MODULE.build_pytest_command("fem_exploratory", [target, target], tmp_path / "tmp", source_root=tmp_path)


def test_exact_node_plugin_lifts_only_the_approved_native_skip() -> None:
    nodeid = _policy()["worktrees"]["d01"]["allowed_nodeids"][0]
    native_skip = SimpleNamespace(name="skip", kwargs={"reason": "tier NATIVE_AUTH_REQUIRED: offline route"})
    unrelated_skip = SimpleNamespace(name="skip", kwargs={"reason": "unrelated skip"})
    item = SimpleNamespace(nodeid=nodeid, own_markers=[native_skip, unrelated_skip])
    PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(None, None, [item])
    assert item.own_markers == [unrelated_skip]
    other = SimpleNamespace(nodeid="tests/verification/test_native.py::test_other", own_markers=[native_skip])
    with pytest.raises(pytest.UsageError, match="requires exactly its registered nodeid"):
        PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(None, None, [other])
    ordinary = SimpleNamespace(nodeid=nodeid, own_markers=[native_skip])
    PLUGIN.ExactNodeGate((nodeid,)).pytest_collection_modifyitems(None, None, [ordinary])
    assert ordinary.own_markers == [native_skip]

    arbitrary = SimpleNamespace(nodeid="tests/verification/test_other.py::test_native", own_markers=[native_skip])
    with pytest.raises(pytest.UsageError, match="restricted to the registered D01 M3 node"):
        PLUGIN.ExactNodeGate((arbitrary.nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(
            None, None, [arbitrary]
        )


def test_d01_native_capability_is_scoped_only_to_the_exact_call(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = _policy()
    nodeid = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    guard_path = Path(policy["worktrees"]["d01"]["root"]) / "src/solveur/core/execution_guard.py"
    guard_spec = importlib.util.spec_from_file_location("solveur.core.execution_guard", guard_path)
    assert guard_spec is not None and guard_spec.loader is not None
    guard = importlib.util.module_from_spec(guard_spec)
    guard_spec.loader.exec_module(guard)
    solveur_package = ModuleType("solveur")
    solveur_package.__path__ = []
    core_package = ModuleType("solveur.core")
    core_package.__path__ = []
    monkeypatch.setitem(sys.modules, "solveur", solveur_package)
    monkeypatch.setitem(sys.modules, "solveur.core", core_package)
    monkeypatch.setitem(sys.modules, "solveur.core.execution_guard", guard)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{nodeid} (call)")
    gate = PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True)
    wrapper = gate.pytest_runtest_call(SimpleNamespace(nodeid=nodeid))
    next(wrapper)
    boundary = "solveur.core.analyses.reduced_harmonic.ReducedHarmonicResponseSolver.solve"
    guard.require_solver_execution_allowed(boundary)
    monkeypatch.setenv(guard.NO_NATIVE_EXECUTION_ENV, "1")
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)
    monkeypatch.delenv(guard.NO_NATIVE_EXECUTION_ENV)
    with pytest.raises(StopIteration):
        next(wrapper)
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)

    unrelated = gate.pytest_runtest_call(SimpleNamespace(nodeid="tests/unit/test_other.py::test_safe"))
    next(unrelated)
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)
    with pytest.raises(StopIteration):
        next(unrelated)


def test_d01_explicit_no_fem_environment_refuses_before_attempt_reservation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from contextlib import nullcontext

    nodeid = (
        "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
        "test_wp05_native_modal_and_residual_flexibility_characterization[M3]"
    )
    source_root = tmp_path / "src"
    entry = {
        "allow_native_vv_skip_override": True,
        "attempt_limit_per_nodeid": 3,
        "budgets": {},
    }
    policy = {
        "minimum_free_disk_mib": 1,
        "run_store": ".codex/development-runs",
        "worktrees": {"d01": entry},
    }
    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *args, **kwargs: [nodeid])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *args, **kwargs: (entry, tmp_path, source_root, {"head": "a" * 40}, "b" * 64),
    )
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    monkeypatch.setattr(
        MODULE,
        "_next_attempt",
        lambda *_args, **_kwargs: pytest.fail("environment refusal must precede attempt reservation"),
    )
    for name in MODULE.NATIVE_GUARD_ENV_KEYS:
        for marker_name in MODULE.NATIVE_GUARD_ENV_KEYS:
            monkeypatch.delenv(marker_name, raising=False)
        monkeypatch.setenv(name, "1")
        with pytest.raises(MODULE.PolicyError, match="before reserving an attempt"):
            MODULE.run_pytest(
                "fem_exploratory",
                nodeid,
                "dev-no-fem-flag",
                worktree_id="d01",
                reason="verify fail-closed environment preflight",
            )
        monkeypatch.delenv(name, raising=False)


def test_native_guard_environment_snapshot_matches_guard_semantics(tmp_path: Path) -> None:
    inherited = {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "false",
        "WPC01_NO_NATIVE_EXECUTION": "0",
        "WPC01_SPATIAL_NO_FEM_TEST": "1",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "0",
    }
    child = MODULE.build_child_environment(tmp_path, base=inherited)
    active = MODULE._native_guard_environment(child)
    assert active["active_markers"] == ["WPC01_SPATIAL_NO_FEM_TEST"]
    assert active["values"] == {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "INACTIVE",
        "WPC01_NO_NATIVE_EXECUTION": "INACTIVE",
        "WPC01_SPATIAL_NO_FEM_TEST": "ACTIVE",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "INACTIVE",
    }


def test_native_guard_snapshot_is_bound_to_the_child_environment() -> None:
    parent = {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "0",
        "WPC01_NO_NATIVE_EXECUTION": "false",
        "WPC01_SPATIAL_NO_FEM_TEST": "0",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "0",
    }
    unchanged_child = dict(parent)
    assert MODULE._validate_native_guard_environment(parent, unchanged_child) == (
        MODULE._native_guard_environment(parent)
    )

    altered_child = {**parent, "QF_SOLVER_NO_NATIVE_EXECUTION": "1"}
    with pytest.raises(MODULE.PolicyError, match="changed an explicit no-native marker"):
        MODULE._validate_native_guard_environment(parent, altered_child)


def test_retry_series_is_scoped_and_bounded(tmp_path: Path) -> None:
    series = tmp_path / "dev-12345678abcd"
    first, _ = MODULE._next_attempt(series, series.name, "unit", 2)
    second, _ = MODULE._next_attempt(series, series.name, "unit", 2)
    assert (first, second) == (1, 2)
    with pytest.raises(MODULE.PolicyError, match="exhausted"):
        MODULE._next_attempt(series, series.name, "unit", 2)
    with pytest.raises(MODULE.PolicyError, match="different scope"):
        MODULE._next_attempt(series, series.name, "integration", 2)


def test_per_nodeid_mandate_attempt_ledger_bounds_attempts_and_refuses_identical_retry(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    lock = tmp_path / "ledger.lock"
    kwargs = {
        "ledger_path": ledger,
        "lock_path": lock,
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-test-v1",
        "worktree_id": "d01",
        "target": "tests/verification/test_case.py::test_m3[M3]",
        "source_fingerprint": "a" * 64,
        "maximum": 3,
    }
    key, first = MODULE._reserve_node_attempt(**kwargs, series_id="dev-11111111", reason="baseline diagnostic")
    assert first == 1
    with pytest.raises(MODULE.PolicyError, match="identical repeat"):
        MODULE._reserve_node_attempt(**kwargs, series_id="dev-22222222", reason="baseline diagnostic")
    _, second = MODULE._reserve_node_attempt(
        **{**kwargs, "source_fingerprint": "b" * 64},
        series_id="dev-22222222",
        reason="instrumented projection hypothesis",
    )
    assert second == 2
    _, third = MODULE._reserve_node_attempt(
        **kwargs,
        series_id="dev-33333333",
        reason="independent rounding hypothesis",
    )
    assert third == 3
    with pytest.raises(MODULE.PolicyError, match="exhausted 3 attempts"):
        MODULE._reserve_node_attempt(
            **{**kwargs, "source_fingerprint": "c" * 64},
            series_id="dev-44444444",
            reason="new attempt",
        )
    record = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(record["entries"][key]) == 3


def test_development_attempt_record_cannot_claim_qualification() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert '"qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY"' in source
    assert '"qualification_promotion": "PROHIBITED"' in source
    assert "qualification_release" not in source.lower()


def test_standard_pytest_command_excludes_release_evidence_markers(tmp_path: Path) -> None:
    command = MODULE.build_pytest_command("unit", ["tests/unit/test_contract.py"], tmp_path)
    assert command[:4] == [sys.executable, "-B", "-m", "pytest"]
    assert "not evidence and not benchmark and not large" in command
    assert not any("owner-go" in part.lower() for part in command)


def _monitor_limits(**overrides) -> dict:
    return {
        "timeout_seconds": 5,
        "rss_soft_limit_mib": 2048,
        "process_tree_limit": 8,
        "output_total_limit_mib": 1,
        "output_stream_limit_mib": 1,
        "temporary_limit_mib": 2,
        "archive_size_limit_mib": 2,
        **overrides,
    }


def test_supervisor_times_out_a_synthetic_child_without_interactive_input(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    limits = _monitor_limits(timeout_seconds=0.2)
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=limits,
        poll_interval=0.05,
    )
    assert result.status == "WALL_TIMEOUT_EXCEEDED"
    assert result.return_code is not None
    assert result.elapsed_seconds < 5


def test_timeout_terminates_a_synthetic_descendant(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    child_pid_path = tmp_path / "child.pid"
    child_source = "import time; time.sleep(20)"
    parent_source = (
        "import pathlib,subprocess,sys,time;"
        f"child=subprocess.Popen([sys.executable, '-c', {child_source!r}]);"
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid));"
        "time.sleep(20)"
    )
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", parent_source],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(timeout_seconds=0.3),
        poll_interval=0.03,
    )
    assert result.status == "WALL_TIMEOUT_EXCEEDED"
    child_pid = int(child_pid_path.read_text(encoding="ascii"))
    assert not MODULE.psutil.pid_exists(child_pid)


def test_supervisor_caps_captured_output(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    result_dir = tmp_path / "output"
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "print('x' * 10000)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=result_dir,
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(output_total_limit_mib=0.001, output_stream_limit_mib=0.001),
        poll_interval=0.02,
    )
    assert result.status == "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
    assert result.stdout_bytes <= int(0.001 * 1024 * 1024)
    assert (result_dir / "stdout.log").stat().st_size == result.stdout_bytes


def test_supervisor_monitors_archive_and_temporary_size_separately(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    output_dir = tmp_path / "output"
    temporary_dir = tmp_path / "tmp"
    temporary_dir.mkdir()
    payload = temporary_dir / "payload.bin"
    source = f"from pathlib import Path; import time; Path({str(payload)!r}).write_bytes(b'x'*10000); time.sleep(20)"
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", source],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(temporary_dir),
        output_dir=output_dir,
        temporary_dir=temporary_dir,
        limits=_monitor_limits(temporary_limit_mib=0.002),
        poll_interval=0.03,
    )
    assert result.status == "TEMPORARY_SIZE_LIMIT_OBSERVED"
    assert result.temporary_bytes > int(0.002 * 1024 * 1024)


def test_supervisor_monitors_rss_as_a_soft_limit(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "data=bytearray(128*1024*1024); import time; time.sleep(20)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(rss_soft_limit_mib=48),
        poll_interval=0.03,
    )
    assert result.status == "RSS_SOFT_LIMIT_EXCEEDED"
    assert result.peak_rss_bytes > 48 * 1024 * 1024


def test_archive_writer_is_atomic_json(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    MODULE._atomic_json(path, {"state": "PASS", "attempt": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"attempt": 1, "state": "PASS"}
    assert list(tmp_path.glob("*.tmp")) == []
