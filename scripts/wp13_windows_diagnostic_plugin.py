from __future__ import annotations

import json
import os
import threading
import time
import faulthandler
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - workflow baseline installs psutil
    psutil = None


EVENT_PATH = Path(os.environ["WP13_DIAGNOSTIC_EVENT_LOG"])
TRACE_PATH = Path(os.environ["WP13_DIAGNOSTIC_TRACE_LOG"])
NODE_TIMEOUT_SECONDS = int(os.environ.get("WP13_DIAGNOSTIC_NODE_TIMEOUT_SECONDS", "110"))
_LOCK = threading.Lock()
_ACTIVE: dict[str, tuple[float, dict[str, Any], threading.Timer]] = {}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _resource_snapshot() -> dict[str, Any]:
    if psutil is None:
        return {"available": False}
    try:
        root = psutil.Process()
        processes = [root, *root.children(recursive=True)]
        cpu = 0.0
        rss = 0
        read_ops = write_ops = read_bytes = write_bytes = 0
        for process in processes:
            try:
                cpu_times = process.cpu_times()
                memory = process.memory_info()
                counters = process.io_counters()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            cpu += cpu_times.user + cpu_times.system
            rss += memory.rss
            read_ops += getattr(counters, "read_count", 0)
            write_ops += getattr(counters, "write_count", 0)
            read_bytes += getattr(counters, "read_bytes", 0)
            write_bytes += getattr(counters, "write_bytes", 0)
        return {
            "available": True,
            "process_tree_cpu_seconds": cpu,
            "process_tree_rss_bytes": rss,
            "read_operations": read_ops,
            "write_operations": write_ops,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes,
        }
    except (psutil.Error, OSError):
        return {"available": False}


def _append(record: dict[str, Any]) -> None:
    EVENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, EVENT_PATH.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()


def _watchdog(nodeid: str) -> None:
    with _LOCK:
        active = _ACTIVE.get(nodeid)
        if active is None:
            return
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_PATH.open("a", encoding="utf-8") as trace:
        trace.write(f"WP13_NODE_TIMEOUT utc={_utc()} seconds={NODE_TIMEOUT_SECONDS} nodeid={nodeid}\n")
        trace.flush()
        faulthandler.dump_traceback(file=trace, all_threads=True)
        trace.flush()
    _append({"event": "NODE_TIMEOUT", "utc": _utc(), "nodeid": nodeid})
    os._exit(124)


def pytest_runtest_logstart(nodeid: str, location: tuple[str, int | None, str]) -> None:
    started = time.perf_counter()
    before = _resource_snapshot()
    timer = threading.Timer(NODE_TIMEOUT_SECONDS, _watchdog, args=(nodeid,))
    timer.daemon = True
    with _LOCK:
        _ACTIVE[nodeid] = (started, before, timer)
    timer.start()
    print(f"WP13_NODE_START utc={_utc()} nodeid={nodeid} resources={json.dumps(before, sort_keys=True)}", flush=True)


def pytest_runtest_logfinish(nodeid: str, location: tuple[str, int | None, str]) -> None:
    finished = time.perf_counter()
    after = _resource_snapshot()
    with _LOCK:
        active = _ACTIVE.pop(nodeid, None)
    if active is None:
        return
    started, before, timer = active
    timer.cancel()
    cpu_delta = None
    if before.get("available") and after.get("available"):
        cpu_delta = max(0.0, after["process_tree_cpu_seconds"] - before["process_tree_cpu_seconds"])
    print(
        f"WP13_NODE_FINISH utc={_utc()} nodeid={nodeid} wall_seconds={finished - started:.6f} "
        f"cpu_seconds={cpu_delta} resources={json.dumps(after, sort_keys=True)}",
        flush=True,
    )
    _append(
        {
            "event": "NODE_FINISH",
            "utc": _utc(),
            "nodeid": nodeid,
            "wall_seconds": finished - started,
            "cpu_seconds": cpu_delta,
            "rss_start_bytes": before.get("process_tree_rss_bytes"),
            "rss_end_bytes": after.get("process_tree_rss_bytes"),
            "read_ops_delta": _delta(before, after, "read_operations"),
            "write_ops_delta": _delta(before, after, "write_operations"),
            "read_bytes_delta": _delta(before, after, "read_bytes"),
            "write_bytes_delta": _delta(before, after, "write_bytes"),
        }
    )


def _delta(before: dict[str, Any], after: dict[str, Any], key: str) -> int | None:
    if not before.get("available") or not after.get("available"):
        return None
    return max(0, int(after[key] - before[key]))
