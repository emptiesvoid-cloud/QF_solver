"""Low-overhead telemetry for large-model assembly runs."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timezone
from collections.abc import Callable
from pathlib import Path
from typing import Any

from solveur.large.memory import process_memory_snapshot


LOGGER = logging.getLogger(__name__)
PHASES = frozenset(
    {
        "GENERATING",
        "ASSEMBLING",
        "MAT_ASSEMBLY",
        "RHS",
        "PCSETUP",
        "PC_READY",
        "PC_READY_GLOBAL",
        "FAILED",
        "COMPLETED",
    }
)


class AssemblyTelemetry:
    """Append-only JSONL progress telemetry; non-rank-zero instances are no-ops."""

    def __init__(
        self,
        path: str | Path | None,
        elements_total: int,
        *,
        rank: int = 0,
        rank_count: int = 1,
        local_elements_total: int | None = None,
        global_progress: Callable[[int], int] | None = None,
        checkpoint_elements: int = 100_000,
        recent_window: int = 3,
        run_id: str | None = None,
        source_sha: str | None = None,
    ) -> None:
        self.path = Path(path) if path is not None else None
        self.elements_total = max(0, int(elements_total))
        self.local_elements_total = max(0, int(local_elements_total or elements_total))
        self.rank = int(rank)
        self.rank_count = int(rank_count)
        self.global_progress = global_progress
        self.checkpoint_elements = max(1, int(checkpoint_elements))
        self.checkpoint_interval = max(
            self.checkpoint_elements,
            max(1, math.ceil(self.local_elements_total / 100)) if self.local_elements_total else 1,
        )
        self.recent_window = max(2, int(recent_window))
        self.run_id = run_id
        self.source_sha = source_sha
        self.status = "DISABLED" if self.path is None else "ENABLED"
        self._handle: Any = None
        self._started = time.monotonic()
        self._last_processed = 0
        self._next_checkpoint = self.checkpoint_interval
        self._points: list[tuple[int, float]] = []
        self._emitted_million: set[int] = set()
        if self.path is not None and self.rank == 0:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._handle = self.path.open("a", encoding="utf-8", newline="\n")
            except OSError as exc:
                self._degrade(f"cannot open telemetry log {self.path}: {exc}")

    def set_local_total(self, local_elements_total: int) -> None:
        """Update the local scheduling total after a distributed model is loaded."""
        self.local_elements_total = max(0, int(local_elements_total))
        self.checkpoint_interval = max(
            self.checkpoint_elements,
            max(1, math.ceil(self.local_elements_total / 100)) if self.local_elements_total else 1,
        )
        self._next_checkpoint = self.checkpoint_interval

    def phase(self, name: str) -> None:
        """Write a dedicated phase transition without affecting the calculation."""
        if self.rank != 0:
            return
        if name not in PHASES:
            self._degrade(f"unknown telemetry phase: {name}")
            return
        self._emit(self._base("phase", name, self._last_processed, include_rates=False, record_point=False))

    def checkpoint(self, local_processed: int, *, elements_total: int | None = None) -> None:
        """Record a global progress checkpoint after a chunk was inserted."""
        local_processed = max(0, int(local_processed))
        if local_processed < self._next_checkpoint and local_processed < self.local_elements_total:
            return
        while self._next_checkpoint <= local_processed:
            self._next_checkpoint += self.checkpoint_interval
        processed = local_processed
        if self.global_progress is not None:
            try:
                processed = int(self.global_progress(local_processed))
            except Exception as exc:  # telemetry must never stop the solver
                self._degrade(f"global progress reduction unavailable: {exc}")
                processed = local_processed
        total = self.elements_total if elements_total is None else max(0, int(elements_total))
        processed = min(max(0, processed), total) if total else processed
        if processed < self._last_processed:
            return
        self._last_processed = processed
        if self.rank != 0:
            return
        self._emit(self._base("checkpoint", "MAT_ASSEMBLY", processed, include_rates=True, total=total))

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.flush()
                self._handle.close()
            except OSError as exc:
                self._degrade(f"cannot close telemetry log {self.path}: {exc}")
            finally:
                self._handle = None

    def _base(
        self,
        event: str,
        phase: str,
        processed: int,
        *,
        include_rates: bool,
        total: int | None = None,
        record_point: bool = True,
    ) -> dict[str, Any]:
        now = time.monotonic()
        elapsed = max(0.0, now - self._started)
        total = self.elements_total if total is None else total
        if record_point:
            self._points.append((processed, elapsed))
            if len(self._points) > self.recent_window + 1:
                self._points = self._points[-(self.recent_window + 1) :]
        # Windows clocks can have a zero-resolution tick for rapid synthetic checks.
        avg_rate = processed / max(elapsed, 1e-12) if processed > 0 else None
        recent_rate = None
        if len(self._points) >= 2:
            old_processed, old_time = self._points[-2]
            dt = elapsed - old_time
            dp = processed - old_processed
            recent_rate = dp / dt if dt > 0.0 and dp >= 0 else None
        eta_avg = self._eta(total, processed, avg_rate)
        eta_recent = self._eta(total, processed, recent_rate)
        slices = []
        if record_point:
            for milestone in range(1_000_000, total + 1, 1_000_000):
                if milestone <= processed and milestone not in self._emitted_million:
                    self._emitted_million.add(milestone)
                    slices.append(
                        {
                            "milestone_elements": milestone,
                            "elapsed_s": elapsed,
                            "seconds_per_million_elements": elapsed / (milestone / 1_000_000),
                        }
                    )
        memory = process_memory_snapshot()
        return {
            "schema_version": 1,
            "event": event,
            "phase": phase,
            "telemetry_status": self.status,
            "run_id": self.run_id,
            "source_sha": self.source_sha,
            "rank": 0,
            "rank_count": self.rank_count,
            "elements_processed": processed,
            "elements_total": total,
            "progress_fraction": (processed / total) if total else None,
            "progress_percent": (100.0 * processed / total) if total else None,
            "elapsed_s": elapsed,
            "avg_elements_per_s": avg_rate if include_rates else None,
            "recent_elements_per_s": recent_rate if include_rates else None,
            "eta_avg_s": eta_avg if include_rates else None,
            "eta_recent_s": eta_recent if include_rates else None,
            "million_element_slices": slices,
            "rss_bytes": memory.get("current_rss_bytes"),
            "rss_percent_of_limit": None,
            "cpu_percent": None,
            "swap": "NOT_MEASURED",
        }

    @staticmethod
    def _eta(total: int, processed: int, rate: float | None) -> float | None:
        if processed >= total:
            return 0.0
        if rate is None or rate <= 0.0:
            return None
        return max(0.0, (total - processed) / rate)

    def _emit(self, payload: dict[str, Any]) -> None:
        if self._handle is None:
            return
        try:
            self._handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            self._handle.flush()
        except (OSError, TypeError, ValueError) as exc:
            self._degrade(f"telemetry write failed: {exc}")

    def _degrade(self, message: str) -> None:
        self.status = "DEGRADED"
        LOGGER.warning("Assembly telemetry degraded: %s", message)
        if self._handle is not None:
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None


class RankPhaseTelemetry:
    """Independent, append-only phase markers for each MPI rank.

    The stream intentionally performs no MPI operation.  A failed telemetry write
    degrades only the marker stream and never changes the numerical route.
    """

    def __init__(
        self,
        path: str | Path | None,
        *,
        rank: int,
        rank_count: int,
        run_id: str | None = None,
        source_sha: str | None = None,
    ) -> None:
        self.rank = int(rank)
        self.rank_count = int(rank_count)
        self.run_id = run_id
        self.source_sha = source_sha
        self.path = self._rank_path(path, self.rank)
        self.status = "DISABLED" if self.path is None else "ENABLED"
        self._started = time.monotonic()
        self._handle: Any = None
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._handle = self.path.open("a", encoding="utf-8", newline="\n")
            except OSError as exc:
                self._degrade(f"cannot open rank telemetry log {self.path}: {exc}")

    @staticmethod
    def _rank_path(path: str | Path | None, rank: int) -> Path | None:
        if path is None:
            return None
        base = Path(path)
        return base.with_name(f"{base.stem}.rank{int(rank):03d}{base.suffix}")

    def marker(
        self,
        name: str,
        *,
        phase: str,
        error: BaseException | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        if self._handle is None:
            return
        memory = process_memory_snapshot()
        payload: dict[str, Any] = {
            "schema_version": 1,
            "record_type": "lu2_wp04_rank_phase_marker",
            "event": f"RANK_{self.rank}_{name}",
            "utc_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "elapsed_s": max(0.0, time.monotonic() - self._started),
            "rank": self.rank,
            "rank_count": self.rank_count,
            "phase": phase,
            "pid": os.getpid(),
            "rss_bytes": memory.get("current_rss_bytes"),
            "run_id": self.run_id,
            "source_sha": self.source_sha,
            "telemetry_status": self.status,
        }
        if error is not None:
            payload["exception_type"] = type(error).__name__
            payload["exception_message"] = str(error)
        if context:
            payload["context"] = dict(context)
        self._emit(payload)

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.flush()
                self._handle.close()
            except OSError as exc:
                self._degrade(f"cannot close rank telemetry log {self.path}: {exc}")
            finally:
                self._handle = None

    def _emit(self, payload: dict[str, Any]) -> None:
        try:
            self._handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            self._handle.flush()
        except (OSError, TypeError, ValueError) as exc:
            self._degrade(f"rank telemetry write failed: {exc}")

    def _degrade(self, message: str) -> None:
        self.status = "DEGRADED"
        LOGGER.warning("Rank phase telemetry degraded: %s", message)
        if self._handle is not None:
            try:
                self._handle.close()
            except OSError:
                pass
            self._handle = None
