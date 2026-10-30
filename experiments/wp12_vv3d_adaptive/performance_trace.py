"""Opt-in, durable timing for one separately authorized VV3D diagnostic.

This module does not authorize, reserve, or execute a scientific operation.
Events are appended and synced outside the runner's temporary directory so a
hard timeout leaves the last started stage and sampled memory available.
"""
from __future__ import annotations

import contextvars
import functools
import json
import os
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Iterator

_CURRENT: contextvars.ContextVar[PerformanceTrace | None] = contextvars.ContextVar("vv3d_trace", default=None)


def matrix_metadata(matrix: Any) -> dict[str, Any]:
    """Describe a matrix without converting, traversing, or copying it."""
    shape = getattr(matrix, "shape", None)
    result: dict[str, Any] = {"type": f"{type(matrix).__module__}.{type(matrix).__qualname__}"}
    if shape is not None:
        result["shape"] = [int(value) for value in shape]
    if hasattr(matrix, "nnz"):
        result["nnz"] = int(matrix.nnz)
    if hasattr(matrix, "dtype"):
        result["dtype"] = str(matrix.dtype)
    return result


class PerformanceTrace:
    """Create-only JSONL trace with monotonic events and sampled RSS peaks."""

    def __init__(self, path: Path, *, case_id: str, attempt_id: str, sample_seconds: float = 5.0) -> None:
        if sample_seconds <= 0:
            raise ValueError("sample interval must be positive")
        self.path = path
        self.case_id = case_id
        self.attempt_id = attempt_id
        self.sample_seconds = sample_seconds
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._stack: list[str] = []
        self._peak_rss: int | None = None
        self._started = time.monotonic()
        self._token: contextvars.Token | None = None
        self._stream = None
        self._thread: threading.Thread | None = None
        self._sampler_error: Exception | None = None

    def __enter__(self) -> PerformanceTrace:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("x", encoding="utf-8", newline="\n")
        self._token = _CURRENT.set(self)
        self.event("trace", "START")
        self._thread = threading.Thread(target=self._sample_loop, name="vv3d-rss-sampler", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, kind: Any, error: Any, tb: Any) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        try:
            self.event("trace", "ERROR" if error is not None else "END", error_type=type(error).__name__ if error else None)
        finally:
            if self._token is not None:
                _CURRENT.reset(self._token)
            if self._stream is not None:
                self._stream.close()
        if error is None and self._sampler_error is not None:
            raise RuntimeError("VV3D performance sampling failed") from self._sampler_error

    def _memory(self) -> int | None:
        try:
            import psutil
        except ImportError:
            return None
        try:
            process = psutil.Process()
            total = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except psutil.Error:
                    continue
            return int(total)
        except (psutil.Error, OSError):
            return None

    def event(self, stage: str, state: str, **fields: Any) -> None:
        with self._lock:
            rss = self._memory()
            if rss is not None:
                self._peak_rss = max(self._peak_rss or 0, rss)
            record = {"schema": "qf-vv3d-performance-trace-v1", "case_id": self.case_id,
                      "attempt_id": self.attempt_id, "process_id": os.getpid(), "stage": stage, "state": state,
                      "monotonic_seconds": time.monotonic() - self._started,
                      "active_stages": list(self._stack), "rss_bytes_sampled": rss,
                      "peak_rss_bytes_sampled": self._peak_rss, **fields}
            assert self._stream is not None
            self._stream.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
            self._stream.flush()
            os.fsync(self._stream.fileno())

    def _sample_loop(self) -> None:
        while not self._stop.wait(self.sample_seconds):
            try:
                self.event("heartbeat", "SAMPLE")
            except Exception as exc:
                self._sampler_error = exc
                self._stop.set()
                return

    @contextmanager
    def stage(self, name: str, **fields: Any) -> Iterator[None]:
        with self._lock:
            self._stack.append(name)
            self.event(name, "START", **fields)
        started = time.monotonic()
        try:
            yield
        except BaseException as exc:
            self.event(name, "ERROR", duration_seconds=time.monotonic() - started, error_type=type(exc).__name__)
            raise
        else:
            self.event(name, "END", duration_seconds=time.monotonic() - started)
        finally:
            with self._lock:
                self._stack.pop()


def stage(name: str, **fields: Any):
    trace = _CURRENT.get()
    return trace.stage(name, **fields) if trace is not None else nullcontext()


def current() -> PerformanceTrace | None:
    return _CURRENT.get()


@contextmanager
def instrument_static_solver(trace: PerformanceTrace | None) -> Iterator[None]:
    """Wrap existing solver calls temporarily, retaining their inputs and outputs."""
    if trace is None:
        yield
        return
    from solveur.core.assembly.assembler import GlobalAssembler
    from solveur.core.constraints import ConstraintReduction
    from solveur.core.solvers.linear import LinearSystemSolver

    patches: list[tuple[type, str, Any]] = []

    def patch(cls: type, name: str, label: str, *, class_method: bool = False) -> None:
        descriptor = cls.__dict__[name]
        original = descriptor.__func__ if class_method else descriptor

        @functools.wraps(original)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            fields: dict[str, Any] = {}
            if label == "linear_solve":
                fields = {"matrix": matrix_metadata(args[1]), "method": str(kwargs.get("method", "unknown"))}
            with trace.stage(label, **fields):
                result = original(*args, **kwargs)
                if label == "stiffness_assembly":
                    trace.event(label, "MATRIX", matrix=matrix_metadata(result))
                elif label == "constraint_reduction":
                    trace.event(label, "MATRIX", matrix=matrix_metadata(result.matrix),
                                transform=matrix_metadata(result.transform))
                elif label == "linear_solve":
                    info = result[1]
                    trace.event(label, "SOLVER", method=str(info.method), backend=str(info.backend))
                return result

        patches.append((cls, name, descriptor))
        setattr(cls, name, classmethod(wrapper) if class_method else wrapper)

    try:
        patch(GlobalAssembler, "prepare_plan", "assembly_plan")
        patch(GlobalAssembler, "assemble_stiffness", "stiffness_assembly")
        patch(GlobalAssembler, "assemble_loads", "load_vector_assembly")
        patch(GlobalAssembler, "fixed_indices", "fixed_dofs")
        patch(ConstraintReduction, "from_system", "constraint_reduction", class_method=True)
        patch(LinearSystemSolver, "solve", "linear_solve")
        yield
    finally:
        for cls, name, descriptor in reversed(patches):
            setattr(cls, name, descriptor)
