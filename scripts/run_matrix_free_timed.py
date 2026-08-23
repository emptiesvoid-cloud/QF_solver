"""Run a matrix-free campaign with timeout and Linux process telemetry."""

from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _proc_snapshot(root_pid: int) -> dict[str, Any]:
    pids = _process_tree(root_pid)
    rss = 0
    hwm = 0
    states: dict[str, int] = {}
    for pid in pids:
        status = _read_status(pid)
        rss += status.get("VmRSS", 0)
        hwm = max(hwm, status.get("VmHWM", 0))
        state = status.get("State", "unknown")
        states[state] = states.get(state, 0) + 1
    return {
        "timestamp_epoch_s": time.time(),
        "pid": root_pid,
        "process_count": len(pids),
        "rss_bytes": rss,
        "peak_hwm_bytes": hwm,
        "states": states,
    }


def _process_tree(root_pid: int) -> list[int]:
    parents: dict[int, int] = {}
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            pid = int(entry.name)
            status = _read_status(pid)
            if "PPid" in status:
                parents[pid] = int(status["PPid"])
        except (OSError, ValueError):
            continue
    result = [root_pid]
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in result and pid not in result:
                result.append(pid)
                changed = True
    return result


def _read_status(pid: int) -> dict[str, Any]:
    values: dict[str, Any] = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if not _:
                continue
            value = value.strip()
            if key in {"VmRSS", "VmHWM"}:
                values[key] = int(value.split()[0]) * 1024
            elif key == "PPid":
                values[key] = int(value)
            elif key == "State":
                values[key] = value.split()[0]
    except (OSError, ValueError):
        return {}
    return values


def run(args: argparse.Namespace) -> int:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "scripts/compare_large_backends.py",
        "--input",
        str(args.input),
        "--output",
        str(output),
        "--backends",
        "matrix_free",
        "--chunk-size",
        str(args.chunk_size),
    ]
    metadata = {
        "runner": "scripts/run_matrix_free_timed.py",
        "analysis": "linear_static",
        "backend": "matrix_free",
        "target_dofs": args.target_dofs,
        "timeout_seconds": args.timeout,
        "telemetry_interval_seconds": args.interval,
        "input": str(args.input),
        "command": command,
        "started_epoch_s": time.time(),
    }
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    selector = selectors.DefaultSelector()
    started = time.monotonic()
    telemetry_path = output / "telemetry.jsonl"
    log_path = output / "runner.log"
    with log_path.open("w", encoding="utf-8") as log, telemetry_path.open("w", encoding="utf-8") as telemetry:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert process.stdout is not None
        selector.register(process.stdout, selectors.EVENT_READ)
        next_sample = 0.0
        timed_out = False
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed >= next_sample:
                sample = _proc_snapshot(process.pid)
                sample["elapsed_seconds"] = elapsed
                telemetry.write(json.dumps(sample) + "\n")
                telemetry.flush()
                next_sample += args.interval
            for key, _ in selector.select(timeout=min(args.interval, 1.0)):
                line = key.fileobj.readline()
                if line:
                    log.write(line)
                    log.flush()
                    print(line, end="")
            if elapsed >= args.timeout:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
                break
        remaining = process.stdout.read()
        if remaining:
            log.write(remaining)
            print(remaining, end="")
        return_code = process.returncode
    metadata.update(
        {
            "finished_epoch_s": time.time(),
            "elapsed_seconds": time.monotonic() - started,
            "return_code": return_code,
            "termination": "timeout" if timed_out else "completed",
        }
    )
    (output / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    summary_path = output / "backend_comparison.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["timed_runner"] = metadata
        summary["telemetry_file"] = "telemetry.jsonl"
        summary["runner_log"] = "runner.log"
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"MATRIX-FREE TIMED STATUS: {'TIMEOUT' if timed_out else 'COMPLETED'}")
    print(f"output: {output}")
    return 124 if timed_out else (0 if return_code == 0 else 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-dofs", type=int, default=1_000_000)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--interval", type=float, default=30.0)
    parser.add_argument("--chunk-size", type=int, default=4096)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
