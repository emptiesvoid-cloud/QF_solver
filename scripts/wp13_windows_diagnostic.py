from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEST_MODULE = "tests/unit/test_development_autonomous_policy.py"
NODEID_MANIFEST = "qualification/0_2_12/wp13_windows_missing_root_diagnostic_nodeids.json"
EXPECTED_BRANCH = "codex/wp13-release-engineering-20261031"
EXPECTED_MODULE_BLOB = "db1f77a20cc7dbc5b0c358baffad1588044c7c8a"
EXPECTED_MANIFEST_BLOB = "34130c8ec7f78564a01f2d62bd7b2ffee68efbf4"
EXPECTED_QUALITY_WORKFLOW_BLOB = "b9a0ed46bdbcdb7961a79b4cd3b861832a098259"
NODE_TIMEOUT_SECONDS = 110
TOTAL_BUDGET_SECONDS = 720
SUPPORTED_PYTHON_VERSIONS = {(3, 10), (3, 13)}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, timeout=20
    )
    return completed.stdout.strip()


def git_bytes(*args: str) -> bytes:
    completed = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=20)
    return completed.stdout


def parse_quality_filters() -> tuple[str, str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/quality.yml").read_text(encoding="utf-8"))
    step = next(
        item for item in workflow["jobs"]["standard-baseline"]["steps"]
        if item.get("name") == "Tests and branch coverage"
    )
    command = step["run"]
    marker = re.search(r'-m\s+"([^"]+)"', command)
    keyword = re.search(r'-k\s+"([^"]+)"', command)
    if marker is None or keyword is None:
        raise RuntimeError("The standard CI marker/keyword filters changed; refusing stale diagnostic scope.")
    return marker.group(1), keyword.group(1)


def load_nodeid_manifest() -> dict[str, Any]:
    manifest_blob = git_text("rev-parse", f"HEAD:{NODEID_MANIFEST}")
    if manifest_blob != EXPECTED_MANIFEST_BLOB:
        raise RuntimeError(f"Nodeid manifest Git blob changed: {manifest_blob}")
    raw = git_bytes("show", f"HEAD:{NODEID_MANIFEST}")
    manifest = json.loads(raw)
    if manifest.get("schema") != "wp13-windows-missing-root-diagnostic-nodeids-v1":
        raise RuntimeError("Unexpected diagnostic nodeid manifest schema.")
    if manifest.get("source_run") != 41289474041:
        raise RuntimeError("Unexpected source diagnostic run identity.")
    predecessors = manifest.get("sequence_predecessors")
    mandate_nodes = manifest.get("mandate_parameter_nodeids")
    regressions = manifest.get("regression_nodeids")
    isolated = manifest.get("isolated_nodeid")
    if not isinstance(predecessors, list) or len(predecessors) != 52:
        raise RuntimeError("The frozen prior-test sequence must contain exactly 52 nodeids.")
    if not isinstance(mandate_nodes, list) or len(mandate_nodes) != 9:
        raise RuntimeError("The frozen mandate test must contain exactly nine parameter nodeids.")
    if not isinstance(regressions, list) or len(regressions) != 3:
        raise RuntimeError("The regression set must contain exactly three nodeids.")
    if not isinstance(isolated, str) or isolated != mandate_nodes[0] or not isolated.endswith("[rotor]"):
        raise RuntimeError("The isolated blocker nodeid does not match the frozen rotor parameter.")
    all_nodes = [*predecessors, *mandate_nodes, *regressions]
    if any(not isinstance(nodeid, str) or not nodeid.startswith(TEST_MODULE + "::") for nodeid in all_nodes):
        raise RuntimeError("The frozen diagnostic contains a nodeid outside the synthetic governance module.")
    if len(all_nodes) != len(set(all_nodes)):
        raise RuntimeError("The frozen collection contains duplicate nodeids.")
    expected_regressions = {
        TEST_MODULE + "::test_required_disk_ancestor_returns_existing_path_directly",
        TEST_MODULE + "::test_required_disk_ancestor_climbs_to_existing_parent",
        TEST_MODULE + "::test_required_disk_ancestor_refuses_absent_windows_drive_root_without_loop",
    }
    if set(regressions) != expected_regressions:
        raise RuntimeError("The frozen missing-root regression nodeids changed.")
    return manifest


def normalize_collected_nodeid(line: str) -> str | None:
    value = line.strip()
    prefixes = (TEST_MODULE + "::", TEST_MODULE.replace("/", "\\") + "::")
    for prefix in prefixes:
        if value.startswith(prefix):
            return TEST_MODULE + "::" + value[len(prefix):]
    return None


def collect_selected_nodeids(nodeids: list[str], output: Path, basetemp: Path, deadline: float) -> list[str]:
    marker, keyword = parse_quality_filters()
    command = [
        sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
        *nodeids, "-m", marker, "-k", keyword,
    ]
    environment = os.environ.copy()
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "TEMP": str(basetemp), "TMP": str(basetemp)})
    output.parent.mkdir(parents=True, exist_ok=True)
    basetemp.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as log:
        completed = subprocess.run(
            command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
            timeout=min(90, max(1, deadline - time.monotonic())), check=False,
        )
    if completed.returncode:
        raise RuntimeError(f"Targeted pytest collection failed with exit {completed.returncode}; see {output}")
    collected = [
        normalized for line in output.read_text(encoding="utf-8", errors="replace").splitlines()
        if (normalized := normalize_collected_nodeid(line)) is not None
    ]
    if len(collected) != len(nodeids) or set(collected) != set(nodeids):
        missing = sorted(set(nodeids) - set(collected))
        unexpected = sorted(set(collected) - set(nodeids))
        raise RuntimeError(
            f"Targeted collection mismatch: expected {len(nodeids)}, got {len(collected)}; "
            f"missing={missing}; unexpected={unexpected}"
        )
    (output.parent / "collected_nodeids.txt").write_text("\n".join(collected) + "\n", encoding="utf-8")
    return collected


def process_snapshot(pid: int) -> dict[str, Any]:
    try:
        processes = [psutil.Process(pid)]
        processes.extend(processes[0].children(recursive=True))
    except psutil.Error:
        return {"cpu_seconds": None, "rss_bytes": None, "process_count": 0}
    cpu = 0.0
    rss = 0
    count = 0
    for process in processes:
        try:
            cpu_times = process.cpu_times()
            cpu += cpu_times.user + cpu_times.system
            rss += process.memory_info().rss
            count += 1
        except psutil.Error:
            continue
    return {"cpu_seconds": cpu, "rss_bytes": rss, "process_count": count}


def stop_tree(pid: int) -> None:
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
    except psutil.Error:
        return
    for process in reversed(children):
        try:
            process.terminate()
        except psutil.Error:
            pass
    try:
        parent.terminate()
    except psutil.Error:
        pass
    _, alive = psutil.wait_procs([*children, parent], timeout=3)
    for process in alive:
        try:
            process.kill()
        except psutil.Error:
            pass


def run_pytest(
    label: str, nodeids: list[str], output_dir: Path, scratch: Path, deadline: float, group_timeout: int
) -> dict[str, Any]:
    event_log = output_dir / f"{label}.events.jsonl"
    trace_log = output_dir / f"{label}.timeout-trace.txt"
    log_path = output_dir / f"{label}.pytest.log"
    event_log.unlink(missing_ok=True)
    trace_log.unlink(missing_ok=True)
    command = [
        sys.executable, "-m", "pytest", "-vv", "-s", "--full-trace", "-p",
        "scripts.wp13_windows_diagnostic_plugin", "-p", "no:cacheprovider",
        "-o", "faulthandler_timeout=90", "--basetemp", str(scratch), *nodeids,
    ]
    environment = os.environ.copy()
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "TEMP": str(scratch),
        "TMP": str(scratch),
        "WP13_DIAGNOSTIC_EVENT_LOG": str(event_log),
        "WP13_DIAGNOSTIC_TRACE_LOG": str(trace_log),
        "WP13_DIAGNOSTIC_NODE_TIMEOUT_SECONDS": str(NODE_TIMEOUT_SECONDS),
        "QF_DEV_EVIDENCE_ROOT": str(scratch / "forbidden-fem-evidence"),
    })
    started_at = utc_now()
    started = time.monotonic()
    timeout_seconds = min(group_timeout, max(1, deadline - time.monotonic()))
    scratch.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
        peak_rss = 0
        peak_cpu = 0.0
        latest = process_snapshot(process.pid)
        timed_out = False
        while process.poll() is None:
            latest = process_snapshot(process.pid)
            peak_rss = max(peak_rss, latest["rss_bytes"] or 0)
            peak_cpu = max(peak_cpu, latest["cpu_seconds"] or 0.0)
            if time.monotonic() - started >= timeout_seconds:
                timed_out = True
                stop_tree(process.pid)
                break
            time.sleep(0.5)
        try:
            return_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            stop_tree(process.pid)
            return_code = process.wait(timeout=5)
    ended = time.monotonic()
    result = {
        "label": label,
        "nodeids": nodeids,
        "started_at_utc": started_at,
        "ended_at_utc": utc_now(),
        "wall_seconds": ended - started,
        "exit_code": return_code,
        "timed_out": timed_out or return_code == 124,
        "timeout_seconds": timeout_seconds,
        "peak_sampled_process_tree_cpu_seconds": peak_cpu,
        "peak_sampled_process_tree_rss_bytes": peak_rss,
        "process_count_final_sample": latest["process_count"],
        "pytest_log": str(log_path),
        "event_log": str(event_log),
        "trace_log": str(trace_log) if trace_log.exists() else None,
    }
    if (scratch / "forbidden-fem-evidence").exists():
        raise RuntimeError("A selected synthetic test created the FEM evidence root; refusing the run as unsafe.")
    if return_code != 0 or result["timed_out"]:
        raise DiagnosticFailure(result)
    return result


class DiagnosticFailure(RuntimeError):
    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(f"{result['label']} diagnostic failed; see {result['pytest_log']}")
        self.result = result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic Windows missing-root regression diagnosis.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        output_dir.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise RuntimeError("Diagnostic output must stay outside the checkout and scientific evidence roots.")
    if sys.platform != "win32" or sys.version_info[:2] not in SUPPORTED_PYTHON_VERSIONS:
        raise RuntimeError("This workflow is restricted to Windows and Python 3.10 or 3.13.")
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = output_dir / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    for required_tool in ("pytest", "psutil", "yaml"):
        if importlib_find(required_tool) is None:
            raise RuntimeError(f"Required diagnostic dependency missing: {required_tool}")
    head = git_text("rev-parse", "HEAD")
    branch = git_text("branch", "--show-current")
    module_blob = git_text("rev-parse", f"HEAD:{TEST_MODULE}")
    workflow_blob = git_text("rev-parse", "HEAD:.github/workflows/quality.yml")
    manifest = load_nodeid_manifest()
    manifest_raw = git_bytes("show", f"HEAD:{NODEID_MANIFEST}")
    manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"Unexpected candidate branch: {branch}")
    if module_blob != EXPECTED_MODULE_BLOB or workflow_blob != EXPECTED_QUALITY_WORKFLOW_BLOB:
        raise RuntimeError("Candidate test module or standard CI filters changed; refusing mismatched evidence.")
    initial_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    if initial_status:
        raise RuntimeError("Diagnostic requires an immutable, clean candidate checkout.")
    predecessors = manifest["sequence_predecessors"]
    mandate_nodes = manifest["mandate_parameter_nodeids"]
    regressions = manifest["regression_nodeids"]
    isolated = manifest["isolated_nodeid"]
    collection_targets = [*predecessors, *mandate_nodes, *regressions]
    baseline = {
        "status": "WP13_WINDOWS_MISSING_ROOT_DIAGNOSTIC_BASELINE",
        "head": head,
        "branch": branch,
        "test_module_blob": module_blob,
        "quality_workflow_blob": workflow_blob,
        "nodeid_manifest": NODEID_MANIFEST,
        "nodeid_manifest_blob": EXPECTED_MANIFEST_BLOB,
        "nodeid_manifest_sha256": manifest_sha256,
        "source_run": manifest["source_run"],
        "python": sys.version,
        "platform": platform.platform(),
        "pytest": __import__("pytest").__version__,
        "psutil": psutil.__version__,
        "source_scope": TEST_MODULE,
        "execution_scope": "64 exact synthetic/governance nodeids; no FEM, benchmarks, or full module run",
        "ledger_write_policy": (
            "read-only checkout; test temp and logs under runner temp; FEM evidence root must remain absent"
        ),
        "node_timeout_seconds": NODE_TIMEOUT_SECONDS,
        "runner_budget_seconds": TOTAL_BUDGET_SECONDS,
        "started_at_utc": utc_now(),
    }
    (output_dir / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    results: list[dict[str, Any]] = []
    try:
        collected = collect_selected_nodeids(
            collection_targets, output_dir / "collection.log", scratch / "collect", deadline
        )
        baseline["collected_nodeids_count"] = len(collected)
        baseline["selected_isolated_nodeid"] = isolated
        baseline["mandate_parameters"] = mandate_nodes
        baseline["sequence_predecessor_count"] = len(predecessors)
        baseline["regression_nodeids"] = regressions
        (output_dir / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        results.append(run_pytest("isolated_rotor", [isolated], output_dir, scratch / "isolated", deadline, 115))
        other_parameters = mandate_nodes[1:]
        results.append(
            run_pytest("other_mandate_parameters", other_parameters, output_dir, scratch / "parameters", deadline, 300)
        )
        sequence = [*predecessors, isolated, *regressions]
        results.append(
            run_pytest("targeted_preceding_sequence", sequence, output_dir, scratch / "sequence", deadline, 420)
        )
        final_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
        if final_status != initial_status:
            raise RuntimeError("The diagnostic changed checkout state; inspect logs and artifact before cleanup.")
        summary = {"status": "DIAGNOSTIC_COMPLETED_NO_REPRODUCTION", "results": results}
    except DiagnosticFailure as error:
        summary = {"status": "DIAGNOSTIC_REPRODUCED_FAILURE_OR_TIMEOUT", "results": [*results, error.result]}
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 1
    except Exception as error:
        summary = {"status": "DIAGNOSTIC_BLOCKED", "results": results, "error": f"{type(error).__name__}: {error}"}
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 2
    summary["candidate"] = baseline
    summary["checkout_status_unchanged"] = True
    summary["completed_at_utc"] = utc_now()
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def importlib_find(name: str) -> Any:
    import importlib.util
    return importlib.util.find_spec(name)


if __name__ == "__main__":
    raise SystemExit(main())
