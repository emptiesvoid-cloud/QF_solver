"""Windows Job Object controls for synthetic children.

This module uses stdlib ctypes and is intentionally not a filesystem sandbox.
It imposes active-process and optional aggregate memory limits, plus
kill-on-close. Wall time is supervised by the parent process. No hard CPU-time,
CPU-rate, storage, thread-count, or archive-write restriction is implemented.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import subprocess
from typing import Any

from .contracts import ContractError


_JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_LIMIT_JOB_MEMORY = 0x00000200
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_THREAD_SUSPEND_RESUME = 0x0002
_TH32CS_SNAPTHREAD = 0x00000004


class _IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_size_t)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", ctypes.c_long),
        ("tpDeltaPri", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
    ]


class WindowsJob:
    """One Job Object with kill-on-close and explicitly requested hard limits."""

    def __init__(
        self,
        *,
        process_count_limit: int,
        memory_limit_bytes: int | None = None,
    ) -> None:
        if os.name != "nt":
            raise ContractError("Windows Job Objects are unavailable on this platform")
        if process_count_limit < 1 or (memory_limit_bytes is not None and memory_limit_bytes < 1):
            raise ContractError("Windows Job Object limits must be positive")
        self.process_count_limit = process_count_limit
        self.memory_limit_bytes = memory_limit_bytes
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._handle: Any = None
        self._configure_api()

    def _configure_api(self) -> None:
        kernel = self._kernel32
        kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.TerminateJobObject.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        kernel.ResumeThread.argtypes = [wintypes.HANDLE]
        kernel.ResumeThread.restype = wintypes.DWORD
        kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenThread.restype = wintypes.HANDLE
        kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
        kernel.Thread32First.restype = wintypes.BOOL
        kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry32)]
        kernel.Thread32Next.restype = wintypes.BOOL

    @staticmethod
    def _raise_last_error(label: str) -> None:
        raise OSError(ctypes.get_last_error(), label)

    def __enter__(self) -> "WindowsJob":
        self._handle = self._kernel32.CreateJobObjectW(None, None)
        if not self._handle:
            self._raise_last_error("CreateJobObjectW failed")
        info = _ExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | _JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        info.BasicLimitInformation.ActiveProcessLimit = self.process_count_limit
        if self.memory_limit_bytes is not None:
            info.BasicLimitInformation.LimitFlags |= _JOB_OBJECT_LIMIT_JOB_MEMORY
            info.JobMemoryLimit = self.memory_limit_bytes
        if not self._kernel32.SetInformationJobObject(
            self._handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            self._raise_last_error("SetInformationJobObject failed")
        return self

    def assign_suspended_process(self, process: subprocess.Popen[bytes]) -> None:
        if self._handle is None:
            raise ContractError("Windows Job Object has not been configured")
        if not self._kernel32.AssignProcessToJobObject(self._handle, process._handle):  # type: ignore[attr-defined]
            self._raise_last_error("AssignProcessToJobObject failed")
        self._resume_primary_thread(process.pid)

    def _resume_primary_thread(self, process_id: int) -> None:
        snapshot = self._kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
        if snapshot == wintypes.HANDLE(-1).value:
            self._raise_last_error("CreateToolhelp32Snapshot failed")
        thread_id: int | None = None
        try:
            entry = _ThreadEntry32()
            entry.dwSize = ctypes.sizeof(entry)
            found = self._kernel32.Thread32First(snapshot, ctypes.byref(entry))
            while found:
                if entry.th32OwnerProcessID == process_id:
                    thread_id = int(entry.th32ThreadID)
                    break
                found = self._kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        finally:
            self._kernel32.CloseHandle(snapshot)
        if thread_id is None:
            raise ContractError("could not locate suspended child main thread")
        thread = self._kernel32.OpenThread(_THREAD_SUSPEND_RESUME, False, thread_id)
        if not thread:
            self._raise_last_error("OpenThread failed for suspended child")
        try:
            if self._kernel32.ResumeThread(thread) == 0xFFFFFFFF:
                self._raise_last_error("ResumeThread failed")
        finally:
            self._kernel32.CloseHandle(thread)

    def terminate(self, exit_code: int = 1) -> None:
        if self._handle is not None and not self._kernel32.TerminateJobObject(self._handle, exit_code):
            self._raise_last_error("TerminateJobObject failed")

    def close(self) -> None:
        if self._handle is not None:
            handle, self._handle = self._handle, None
            if not self._kernel32.CloseHandle(handle):
                self._raise_last_error("CloseHandle(Job Object) failed")

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


def windows_job_available() -> bool:
    return os.name == "nt" and hasattr(ctypes, "WinDLL")
