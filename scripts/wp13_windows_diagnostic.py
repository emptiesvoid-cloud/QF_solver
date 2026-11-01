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
EXPECTED_MODULE_BLOB = "6603a639662bf79462d14bb87d8b9929d1c7adb2"
EXPECTED_QUALITY_WORKFLOW_BLOB = "e1ebb19f35ea640812f3dd1e742b1be9a74dcaac"
EXPECTED_MODULE_NODES = 247
EXPECTED_NODEIDS_SHA256 = "0227ce061aff18ced4c0ef36463565bdc49dfcdd28340799b3e1426e0b9df946"
EXPECTED_PREFIX_53_SHA256 = "c161dce17668b68e96fd618c79492d02a19cdd1ec0647b12aa8b0a93e3c7e2ef"
NODE_TIMEOUT_SECONDS = 110
TOTAL_BUDGET_SECONDS = 720


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, timeout=20
    )
    return completed.stdout.strip()


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


def collect_module(output: Path, basetemp: Path, deadline: float) -> list[str]:
    marker, keyword = parse_quality_filters()
    command = [
        sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
        TEST_MODULE, "-m", marker, "-k", keyword,
    ]
    environment = os.environ.copy()
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "TEMP": str(basetemp), "TMP": str(basetemp)})
    with output.open("w", encoding="utf-8", newline="\n") as log:
        completed = subprocess.run(
            command, cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT,
            timeout=min(90, max(1, deadline - time.monotonic())), check=False,
        )
    if completed.returncode:
        raise RuntimeError(f"pytest collection failed with exit {completed.returncode}; see {output}")
    lines = output.read_text(encoding="utf-8", errors="replace").splitlines()
    prefix = TEST_MODULE.replace("/", "\\") + "::"
    nodeids = [line.strip() for line in lines if line.strip().startswith((TEST_MODULE + "::", prefix))]
    if len(nodeids) != EXPECTED_MODULE_NODES:
        raise RuntimeError(f"Expected {EXPECTED_MODULE_NODES} selected nodeids; collected {len(nodeids)}")
    nodeids_hash = hashlib.sha256(("\n".join(nodeids) + "\n").encode()).hexdigest()
    prefix_hash = hashlib.sha256(("\n".join(nodeids[:53]) + "\n").encode()).hexdigest()
    if nodeids_hash != EXPECTED_NODEIDS_SHA256 or prefix_hash != EXPECTED_PREFIX_53_SHA256:
        raise RuntimeError("Collected nodeid identity changed; diagnostic stops before executing tests.")
    (output.parent / "collected_nodeids.txt").write_text("\n".join(nodeids) + "\n", encoding="utf-8")
    return nodeids


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


def run_pytest(label: str, nodeids: list[str], output_dir: Path, scratch: Path, deadline: float) -> dict[str, Any]:
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
    })
    started_at = utc_now()
    started = time.monotonic()
    timeout_seconds = min(120 if label == "isolated" else 480, max(1, deadline - time.monotonic()))
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
    if return_code != 0 or result["timed_out"]:
        raise DiagnosticFailure(result)
    return result


class DiagnosticFailure(RuntimeError):
    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__(f"{result['label']} diagnostic failed; see {result['pytest_log']}")
        self.result = result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic Windows policy-test diagnosis.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    try:
        output_dir.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise RuntimeError("Diagnostic output must stay outside the checkout and scientific evidence roots.")
    if sys.platform != "win32" or sys.version_info[:2] != (3, 13):
        raise RuntimeError("This workflow is restricted to Windows and Python 3.13.")
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = output_dir / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    for required_tool in ("pytest", "psutil"):
        if importlib_find(required_tool) is None:
            raise RuntimeError(f"Required diagnostic dependency missing: {required_tool}")
    head = git_text("rev-parse", "HEAD")
    module_blob = git_text("rev-parse", f"HEAD:{TEST_MODULE}")
    workflow_blob = git_text("rev-parse", "HEAD:.github/workflows/quality.yml")
    if module_blob != EXPECTED_MODULE_BLOB or workflow_blob != EXPECTED_QUALITY_WORKFLOW_BLOB:
        raise RuntimeError("Candidate test module or standard CI filters changed; refusing mismatched evidence.")
    initial_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    baseline = {
        "status": "WP13_WINDOWS_DIAGNOSTIC_BASELINE",
        "head": head,
        "module_blob": module_blob,
        "quality_workflow_blob": workflow_blob,
        "python": sys.version,
        "platform": platform.platform(),
        "pytest": __import__("pytest").__version__,
        "psutil": psutil.__version__,
        "source_scope": TEST_MODULE,
        "execution_scope": "synthetic/governance module only; no FEM or benchmark",
        "ledger_write_policy": "pytest basetemp and all logs are under runner temp outside checkout",
        "started_at_utc": utc_now(),
    }
    (output_dir / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    results: list[dict[str, Any]] = []
    try:
        nodeids = collect_module(output_dir / "collection.log", scratch / "collect", deadline)
        candidate = nodeids[52]
        baseline["selected_nodeid"] = candidate
        baseline["selected_nodeid_index_1_based"] = 53
        results.append(run_pytest("isolated", [candidate], output_dir, scratch / "isolated", deadline))
        # One process keeps state across the 52 preceding governance tests and the candidate.
        results.append(run_pytest("prefix_1_through_53", nodeids[:53], output_dir, scratch / "prefix", deadline))
        final_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
        if final_status != initial_status:
            raise RuntimeError("The diagnostic changed checkout state; inspect logs before any cleanup.")
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
