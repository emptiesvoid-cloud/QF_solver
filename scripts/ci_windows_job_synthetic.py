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


class ASSOCIATE_COMPLETION_PORT(C.Structure):
    _fields_ = [("CompletionKey", C.c_void_p), ("CompletionPort", W.HANDLE)]


class BASIC_ACCOUNTING(C.Structure):
    _fields_ = [("TotalUserTime", C.c_int64), ("TotalKernelTime", C.c_int64),
                ("ThisPeriodTotalUserTime", C.c_int64), ("ThisPeriodTotalKernelTime", C.c_int64),
                ("TotalPageFaultCount", W.DWORD), ("TotalProcesses", W.DWORD),
                ("ActiveProcesses", W.DWORD), ("TotalTerminatedProcesses", W.DWORD)]


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
create_iocp = api("CreateIoCompletionPort", [W.HANDLE, W.HANDLE, C.c_size_t, W.DWORD], W.HANDLE)
get_iocp = api("GetQueuedCompletionStatus", [W.HANDLE, C.POINTER(W.DWORD), C.POINTER(C.c_size_t),
                                                C.POINTER(C.c_void_p), W.DWORD], W.BOOL)


def run(argv: list[str], memory: int, processes: int, seconds: float) -> dict:
    """Apply hard job limits before resuming a synthetic child; never use for real CI."""
    if not argv or memory <= 0 or processes <= 0 or seconds <= 0:
        raise ValueError("positive limits and a command are required")
    job = create_job(None, None)
    if not job:
        raise C.WinError(C.get_last_error())
    port = create_iocp(W.HANDLE(-1), None, 0, 1)
    if not port:
        close(job)
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
        association = ASSOCIATE_COMPLETION_PORT(C.c_void_p(1), port)
        if not set_job(job, 7, C.byref(association), C.sizeof(association)):
            raise C.WinError(C.get_last_error())
        startup = STARTUP()
        startup.cb = C.sizeof(startup)
        cmd = C.create_unicode_buffer(subprocess.list2cmdline(argv))
        if not create_process(None, cmd, None, None, False, 0x00000004 | 0x08000000, None, None,
                              C.byref(startup), C.byref(pi)):
            raise C.WinError(C.get_last_error())
        if not assign(job, pi.process):
            error = C.get_last_error()
            K.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
            K.TerminateProcess.restype = W.BOOL
            if not K.TerminateProcess(pi.process, 1):
                raise C.WinError(C.get_last_error())
            raise C.WinError(error)
        if resume(pi.thread) == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        deadline = started + seconds
        timed_out = False
        violation = None
        while True:
            if time.monotonic() >= deadline:
                timed_out = True
                if not terminate(job, 124):
                    raise C.WinError(C.get_last_error())
                break
            remaining_ms = max(0, min(100, int((deadline - time.monotonic()) * 1000)))
            message = W.DWORD()
            key = C.c_size_t()
            overlapped = C.c_void_p()
            ok = get_iocp(port, C.byref(message), C.byref(key), C.byref(overlapped), remaining_ms)
            if ok:
                # Completion-port delivery is best effort for these messages.
                # The kernel hard limits still prevent memory/process growth past
                # their configured caps; a received violation kills the full job.
                if message.value in (3, 9, 10):  # active-process, process-memory, job-memory limit
                    violation = {3: "active_process_limit", 9: "process_memory_limit",
                                 10: "job_memory_limit"}[message.value]
                    if not terminate(job, 125):
                        raise C.WinError(C.get_last_error())
                    break
                if message.value == 4:  # JOB_OBJECT_MSG_ACTIVE_PROCESS_ZERO
                    break
                continue
            error = C.get_last_error()
            if error != 258:  # WAIT_TIMEOUT
                raise C.WinError(error)
            state = wait(pi.process, 0)
            if state == 0:
                break
            if state != 0x102:
                raise C.WinError(C.get_last_error())
            if time.monotonic() >= deadline:
                timed_out = True
                if not terminate(job, 124):
                    raise C.WinError(C.get_last_error())
                break
        # A signaled root does not prove descendants are gone. Wait for the job's
        # active-process-zero notification, with a bounded fail-closed cleanup.
        cleanup_deadline = time.monotonic() + 5
        while True:
            accounting = BASIC_ACCOUNTING()
            if not query_job(job, 1, C.byref(accounting), C.sizeof(accounting), None):
                raise C.WinError(C.get_last_error())
            active_count = accounting.ActiveProcesses
            if active_count == 0:
                break
            if time.monotonic() >= deadline and violation is None and not timed_out:
                timed_out = True
                if not terminate(job, 124):
                    raise C.WinError(C.get_last_error())
            if time.monotonic() >= cleanup_deadline:
                if not terminate(job, 126):
                    raise C.WinError(C.get_last_error())
                raise TimeoutError("job descendants did not exit within 5 seconds")
            message = W.DWORD()
            key = C.c_size_t()
            overlapped = C.c_void_p()
            if not get_iocp(port, C.byref(message), C.byref(key), C.byref(overlapped), 50):
                error = C.get_last_error()
                if error != 258:
                    raise C.WinError(error)
        code = W.DWORD()
        if not exit_code(pi.process, C.byref(code)):
            raise C.WinError(C.get_last_error())
        measured = EXTENDED()
        if not query_job(job, 9, C.byref(measured), C.sizeof(measured), None):
            raise C.WinError(C.get_last_error())
        return {"timed_out": timed_out, "violation": violation, "exit_code": code.value, "elapsed_seconds": time.monotonic() - started,
                "peak_job_commit_bytes": measured.PeakJobMemoryUsed, "memory_limit_bytes": memory,
                "configured_job_memory_limit_bytes": measured.JobMemoryLimit,
                "configured_process_memory_limit_bytes": measured.ProcessMemoryLimit,
                "process_limit": processes, "active_descendants": 0}
    except BaseException:
        # On any supervisor/API error, make a best effort to kill and verify the
        # whole job before releasing the last job handle.
        if not terminate(job, 127):
            raise C.WinError(C.get_last_error())
        deadline = time.monotonic() + 5
        while True:
            accounting = BASIC_ACCOUNTING()
            if not query_job(job, 1, C.byref(accounting), C.sizeof(accounting), None):
                raise C.WinError(C.get_last_error())
            if accounting.ActiveProcesses == 0:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("failed to verify whole-job termination after supervisor error")
            wait(pi.process, 50) if pi.process else time.sleep(0.05)
        raise
    finally:
        for handle in (pi.thread, pi.process, job, port):
            if handle and not close(handle):
                raise C.WinError(C.get_last_error())


if __name__ == "__main__":
    print(json.dumps(run([sys.executable, "-c", "print('synthetic')"], 128 * 1024 * 1024, 2, 5)))
