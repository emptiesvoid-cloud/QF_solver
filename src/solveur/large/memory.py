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

        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_process_memory_info.restype = wintypes.BOOL
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        process = get_current_process()
        success = get_process_memory_info(process, ctypes.byref(counters), counters.cb)
        if not success:
            return None
        current = int(counters.WorkingSetSize)
        peak = int(counters.PeakWorkingSetSize)
        # Zero is not a meaningful successful process-memory measurement.
        # Returning unavailable lets callers report that fact explicitly.
        if current <= 0 or peak <= 0:
            return None
        return {
            "source": f"windows_psapi:{platform.release()}",
            "current_rss_bytes": current,
            "peak_rss_bytes": peak,
        }
    except (AttributeError, OSError, TypeError, ValueError):
        return None
