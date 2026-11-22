
"""Offline G08 contract preparation and synthetic process/archive exercises.

Official G08 preflights and FEM attempts are registered by
scripts/development_autonomous.py; this module never reserves a real scope.
"""
import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

from research.g08_compare.case import HERE, scope_for

ROOT = HERE.parents[1]
POLICY = HERE / "policy.json"
MIB = 2**20


def environment():
    env = os.environ.copy()
    for key in ("PYTHONPATH", "PYTEST_ADDOPTS", "PYTEST_PLUGINS"):
        env.pop(key, None)
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        env[key] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def file_sha(path):
    return sha256(path.read_bytes()).hexdigest()


def bound_probe(command, cwd):
    return subprocess.run(command, cwd=cwd, env=environment(), capture_output=True,
                          check=True, text=True, timeout=30).stdout


def preflight(scope_id, source):
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    scope = scope_for(scope_id)
    receipt = json.loads(bound_probe([sys.executable, "-B", str(HERE / "case.py"), str(source), scope_id], ROOT))
    if (receipt["common_sha256"] != policy["paired_inputs_sha256"]
            or receipt["solver_tree"] != policy["paired_source_tree"]
            or receipt["inputs_sha256"] != scope["inputs"]
            or receipt["compatibility"] != "SUPPORTED_ROUTE"):
        raise ValueError("preflight identity or compatibility mismatch")
    collected = bound_probe([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider",
                             "--collect-only", "-q", scope["nodeid"]], ROOT)
    nodeids = [line for line in collected.splitlines() if "::" in line]
    if nodeids != [scope["nodeid"]]:
        raise ValueError("exact collection mismatch")
    target = ROOT / scope["nodeid"].split("::")[0]
    receipt.update(
        policy_sha256=file_sha(POLICY), nodeids=nodeids, budget=policy["budget"],
        receipt_status="PREPARED_NOT_AUTHORIZED", attempt_reserved=False,
        controller_files={p.relative_to(ROOT).as_posix(): file_sha(p)
                          for p in (Path(__file__).resolve(), HERE / "case.py", target)},
        free_disk_bytes=shutil.disk_usage(source).free,
        available_memory_bytes=psutil.virtual_memory().available,
    )
    return receipt


def _write(path, data, *, exclusive=False):
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)


def _stop(process, info):
    try:
        children = info.children(recursive=True) if info is not None else []
    except psutil.NoSuchProcess:
        children = []
    for child in reversed(children):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=5)


def _size(directory):
    return sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())


def _launch(command, output, budget):
    output.mkdir()
    start = time.monotonic()
    peak_rss = 0
    limit = None
    stdout, stderr = output / "stdout.log", output / "stderr.log"
    scratch = output / "tmp"
    scratch.mkdir()
    env = environment()
    env.update(TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch))
    with stdout.open("wb") as out, stderr.open("wb") as err:
        with subprocess.Popen(command, stdout=out, stderr=err, cwd=ROOT, env=env) as process:
            try:
                info = psutil.Process(process.pid)
            except psutil.NoSuchProcess:
                info = None
            try:
                while True:
                    try:
                        samples = [] if info is None else [info, *info.children(recursive=True)]
                        rss = sum(p.memory_info().rss for p in samples)
                        peak_rss = max(peak_rss, rss)
                    except psutil.NoSuchProcess:
                        pass
                    if stdout.stat().st_size + stderr.stat().st_size > budget["output_mib"] * MIB:
                        limit = "OUTPUT_LIMIT"
                    elif _size(output) > budget["storage_mib"] * MIB:
                        limit = "STORAGE_LIMIT"
                    elif peak_rss > budget["rss_mib"] * MIB:
                        limit = "RSS_LIMIT"
                    elif time.monotonic() - start > budget["timeout_seconds"]:
                        limit = "TIMEOUT"
                    if limit or process.poll() is not None:
                        break
                    time.sleep(.04)
            finally:
                _stop(process, info)
    return {"exit": process.returncode, "limit": limit,
            "elapsed_seconds": time.monotonic() - start, "peak_sampled_rss_bytes": peak_rss}


def _verdict(output, process, receipt):
    if process["limit"]:
        return process["limit"]
    if process["exit"]:
        return "RUNNER_ERROR"
    try:
        result = json.loads((output / "result.json").read_text(encoding="utf-8"))
        if any(result[k] != receipt[k] for k in ("scope", "source", "inputs_sha256")):
            return "RESULT_ARCHIVE_INCOMPLETE"
        if result["solver_status"] != "PASS":
            return "SOLVER_NON_PASS"
        if result["mode_sha256"] != file_sha(output / "mode.npy"):
            return "RESULT_ARCHIVE_INCOMPLETE"
        if result["mode_rank"] != "NOT_ESTABLISHED":
            return "RESULT_ARCHIVE_INCOMPLETE"
        residual, error = result["residual"], result["euler_relative_error"]
        if not all(math.isfinite(value) and value >= 0 for value in (residual, error)):
            return "RESULT_ARCHIVE_INCOMPLETE"
        if residual > 1e-7 or error > .10:
            return "SCREEN_OUTSIDE_BAND"
    except (OSError, ValueError, KeyError, TypeError):
        return "RESULT_ARCHIVE_INCOMPLETE"
    return "SCREEN_PASS"


def run_synthetic(command, store, receipt):
    """Exercise real process supervision and archive checks using a synthetic producer."""
    if receipt != {"scope": "synthetic", "source": "mock", "inputs_sha256": "mock"}:
        raise ValueError("only the synthetic scope can reserve an attempt")
    store.mkdir(parents=True, exist_ok=True)
    ledger = store / "attempt.json"
    _write(ledger, {"state": "RESERVED", "receipt": receipt}, exclusive=True)
    output = store / "archive"
    budget = json.loads(POLICY.read_text(encoding="utf-8"))["budget"]
    try:
        process = _launch(command, output, budget)
        verdict = _verdict(output, process, receipt)
    except Exception:
        verdict, process = "CONTROLLER_ERROR", {}
        raise
    finally:
        final = store / "attempt.final.json"
        temporary = final.with_suffix(".tmp")
        _write(temporary, {"state": verdict, "receipt": receipt, "process": process}, exclusive=True)
        temporary.replace(final)
    return verdict


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=("g08-tet10-before", "g08-tet10-after"))
    parser.add_argument("source", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    _write(args.receipt, preflight(args.scope, args.source), exclusive=True)


if __name__ == "__main__":
    main()
