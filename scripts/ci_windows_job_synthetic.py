"""Experimental Windows Job Object synthetic supervisor. Not enabled for CI."""
from __future__ import annotations

import ctypes as C
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes as W

if os.name != "nt":
    raise SystemExit("Windows only; CI execution remains blocked")

K = C.WinDLL("kernel32", use_last_error=True)
SIZE = C.c_size_t


class BASIC(C.Structure):
    _fields_ = [("PerProcessUserTimeLimit", C.c_int64), ("PerJobUserTimeLimit", C.c_int64),
                ("LimitFlags", W.DWORD), ("MinimumWorkingSetSize", SIZE), ("MaximumWorkingSetSize", SIZE),
                ("ActiveProcessLimit", W.DWORD), ("Affinity", SIZE), ("PriorityClass", W.DWORD),
                ("SchedulingClass", W.DWORD)]


class IO(C.Structure):
    _fields_ = [(x, C.c_uint64) for x in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                                             "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class EXTENDED(C.Structure):
    _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO), ("ProcessMemoryLimit", SIZE),
                ("JobMemoryLimit", SIZE), ("PeakProcessMemoryUsed", SIZE), ("PeakJobMemoryUsed", SIZE)]


class STARTUP(C.Structure):
    _fields_ = [("cb", W.DWORD), ("reserved", W.LPWSTR), ("desktop", W.LPWSTR), ("title", W.LPWSTR),
                ("x", W.DWORD), ("y", W.DWORD), ("xs", W.DWORD), ("ys", W.DWORD), ("xc", W.DWORD),
                ("yc", W.DWORD), ("fill", W.DWORD), ("flags", W.DWORD), ("show", W.WORD),
                ("reserved2", W.WORD), ("reserved_ptr", C.c_void_p), ("stdin", W.HANDLE),
                ("stdout", W.HANDLE), ("stderr", W.HANDLE)]


class PROCESS(C.Structure):
    _fields_ = [("process", W.HANDLE), ("thread", W.HANDLE), ("pid", W.DWORD), ("tid", W.DWORD)]


def api(name: str, args: list, result: object) -> object:
    fn = getattr(K, name)
    fn.argtypes = args
    fn.restype = result
    return fn


create_job = api("CreateJobObjectW", [C.c_void_p, W.LPCWSTR], W.HANDLE)
set_job = api("SetInformationJobObject", [W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL)
query_job = api("QueryInformationJobObject", [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p], W.BOOL)
create_process = api("CreateProcessW", [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD,
                                        C.c_void_p, W.LPCWSTR, C.POINTER(STARTUP), C.POINTER(PROCESS)], W.BOOL)
assign = api("AssignProcessToJobObject", [W.HANDLE, W.HANDLE], W.BOOL)
resume = api("ResumeThread", [W.HANDLE], W.DWORD)
wait = api("WaitForSingleObject", [W.HANDLE, W.DWORD], W.DWORD)
terminate = api("TerminateJobObject", [W.HANDLE, W.UINT], W.BOOL)
close = api("CloseHandle", [W.HANDLE], W.BOOL)
exit_code = api("GetExitCodeProcess", [W.HANDLE, C.POINTER(W.DWORD)], W.BOOL)


def run(argv: list[str], memory: int, processes: int, seconds: float) -> dict:
    """Apply hard job limits before resuming a synthetic child; never use for real CI."""
    if not argv or memory <= 0 or processes <= 0 or seconds <= 0:
        raise ValueError("positive limits and a command are required")
    job = create_job(None, None)
    if not job:
        raise C.WinError(C.get_last_error())
    pi = PROCESS()
    started = time.monotonic()
    try:
        limits = EXTENDED()
        limits.BasicLimitInformation.LimitFlags = 0x00002000 | 0x00000200 | 0x00000008
        limits.BasicLimitInformation.ActiveProcessLimit = processes
        limits.JobMemoryLimit = memory
        if not set_job(job, 9, C.byref(limits), C.sizeof(limits)):
            raise C.WinError(C.get_last_error())
        startup = STARTUP()
        startup.cb = C.sizeof(startup)
        cmd = C.create_unicode_buffer(subprocess.list2cmdline(argv))
        if not create_process(None, cmd, None, None, False, 0x00000004 | 0x08000000, None, None,
                              C.byref(startup), C.byref(pi)):
            raise C.WinError(C.get_last_error())
        if not assign(job, pi.process):
            K.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
            K.TerminateProcess(pi.process, 1)
            raise C.WinError(C.get_last_error())
        if resume(pi.thread) == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        state = wait(pi.process, int(seconds * 1000))
        timed_out = state == 0x102
        if state not in (0, 0x102):
            raise C.WinError(C.get_last_error())
        if timed_out:
            terminate(job, 124)
            wait(pi.process, 5000)
        code = W.DWORD()
        if not exit_code(pi.process, C.byref(code)):
            raise C.WinError(C.get_last_error())
        measured = EXTENDED()
        if not query_job(job, 9, C.byref(measured), C.sizeof(measured), None):
            raise C.WinError(C.get_last_error())
        return {"timed_out": timed_out, "exit_code": code.value, "elapsed_seconds": time.monotonic() - started,
                "peak_job_commit_bytes": measured.PeakJobMemoryUsed, "memory_limit_bytes": memory,
                "process_limit": processes, "remaining_descendants": "terminated_on_job_close"}
    finally:
        if pi.thread:
            close(pi.thread)
        if pi.process:
            close(pi.process)
        close(job)


if __name__ == "__main__":
    print(json.dumps(run([sys.executable, "-c", "print('synthetic')"], 128 * 1024 * 1024, 2, 5)))
