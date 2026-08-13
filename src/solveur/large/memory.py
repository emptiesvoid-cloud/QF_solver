"""Process-level memory telemetry for large-scale benchmarks."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any


def process_memory_snapshot() -> dict[str, Any]:
    """Return current and peak resident memory without adding a dependency."""
    if os.name == "nt":
        snapshot = _windows_memory()
        if snapshot is not None:
            return snapshot
    snapshot = _proc_memory()
    peak = _resource_peak_rss()
    if snapshot is not None or peak is not None:
        return {
            "source": "procfs+resource" if snapshot is not None and peak is not None else "platform_partial",
            "current_rss_bytes": snapshot,
            "peak_rss_bytes": peak,
        }
    return {"source": "unavailable", "current_rss_bytes": None, "peak_rss_bytes": None}


def _proc_memory() -> int | None:
    try:
        resident_pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
        return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, IndexError, OSError, ValueError):
        return None


def _resource_peak_rss() -> int | None:
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError, ValueError):
        return None
    return value if sys.platform == "darwin" else value * 1024


def _windows_memory() -> dict[str, Any] | None:
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        success = ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
        if not success:
            return None
        return {
            "source": f"windows_psapi:{platform.release()}",
            "current_rss_bytes": int(counters.WorkingSetSize),
            "peak_rss_bytes": int(counters.PeakWorkingSetSize),
        }
    except (AttributeError, OSError, TypeError, ValueError):
        return None
