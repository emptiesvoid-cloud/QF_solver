"""Append-only R2 ledger linked to the immutable VV3D R1 ledger.

This module accounts only for the twelve initial R2 FEM cases. It deliberately
has no H1, QLOAD, or QPOST reservation API. Owner authorization, exact
preflight, and provenance validation remain the controller's responsibility.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any
import uuid

if __package__:
    from .wp12_vv3d_ledger import (
        BudgetLedger as R1BudgetLedger,
        LedgerError,
        RunBinding,
        RunnerCaseBinding,
        _canonical,
        _exclusive_lock,
        _sha256,
        _valid_elapsed,
    )
else:
    from wp12_vv3d_ledger import (
        BudgetLedger as R1BudgetLedger,
        LedgerError,
        RunBinding,
        RunnerCaseBinding,
        _canonical,
        _exclusive_lock,
        _sha256,
        _valid_elapsed,
    )


CAMPAIGN_ID = "WP12-VV3D-RECOVERY-20261030-R2"
LEDGER_SCOPE_ID = "wp12_vv3d_recovery_r2"
MAX_R2_ATTEMPTS = 12
MAX_GLOBAL_ATTEMPTS = 24
MAX_TOTAL_SECONDS = 28_800
MAX_ATTEMPT_SECONDS = 1_200
R1_LEDGER_SHA256 = "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8"
R1_CASE_STATES = (
    ("VV3D-TET4-L1", "PASS"),
    ("VV3D-TET4-L2", "INFRA_ERROR"),
)
CASE_IDS = tuple(
    f"VV3D-{family}-L{level}"
    for family in ("TET4", "TET10", "HEX8", "HEX20")
    for level in (1, 2, 3)
)
NODEID_PREFIX = "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case["
_HEX64 = re.compile(r"[0-9a-f]{64}")
_GENESIS = "0" * 64
_TERMINAL = frozenset({"PASS", "FAIL", "TIMEOUT", "INTERRUPTED", "RESOURCE_LIMIT", "INFRA_ERROR", "INCONCLUSIVE"})


class RecoveryR2Ledger:
    """Budget-enforcing, hash-chained R2 ledger with a checked R1 baseline."""

    def __init__(
        self,
        path: Path,
        *,
        allowed_root: Path,
        predecessor_path: Path,
        predecessor_sha256: str = R1_LEDGER_SHA256,
    ) -> None:
        self.allowed_root = allowed_root.resolve(strict=True)
        self.path = path.resolve(strict=False)
        self.predecessor_path = predecessor_path.resolve(strict=True)
        if not isinstance(predecessor_sha256, str) or _HEX64.fullmatch(predecessor_sha256) is None:
            raise LedgerError("R2 requires an exact R1 predecessor SHA-256")
        self.predecessor_sha256 = predecessor_sha256
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._assert_safe_paths()
        if self.path == self.predecessor_path:
            raise LedgerError("R2 ledger must be physically distinct from the R1 predecessor")
        if self.path.exists() and self.predecessor_path.exists():
            try:
                if os.path.samefile(self.path, self.predecessor_path):
                    raise LedgerError("R2 ledger must not alias the R1 predecessor")
            except OSError as exc:
                raise LedgerError("cannot prove R2/R1 ledger path separation") from exc

    def _assert_safe_paths(self) -> None:
        for candidate, root in ((self.path, self.allowed_root), (self.lock_path, self.allowed_root)):
            try:
                relative = candidate.relative_to(root)
            except ValueError as exc:
                raise LedgerError("R2 ledger and lock must stay under its dedicated evidence root") from exc
            if not relative.parts:
                raise LedgerError("R2 ledger must be a file below its evidence root")
            current = root
            for part in relative.parts:
                current = current / part
                if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                    raise LedgerError("R2 ledger path contains a symlink or junction")

    def _predecessor(self) -> tuple[int, float]:
        if _sha256(self.predecessor_path.read_bytes()) != self.predecessor_sha256:
            raise LedgerError("immutable R1 predecessor SHA-256 changed")
        r1 = R1BudgetLedger(self.predecessor_path, allowed_root=self.predecessor_path.parent)
        if _sha256(self.predecessor_path.read_bytes()) != self.predecessor_sha256:
            raise LedgerError("R1 predecessor changed while R2 acquired its ledger lock")
        records = r1._read_unlocked()
        attempts, elapsed, reserved, active, crashed = r1._projection(records)
        finished = {record.get("run_id"): record for record in records
                    if record.get("event") == "ATTEMPT_FINISHED"}
        starts = [record for record in records if record.get("event") == "ATTEMPT_STARTED"]
        observed = tuple((record.get("case_id"), finished.get(record.get("run_id"), {}).get("status"))
                         for record in starts)
        if (observed != R1_CASE_STATES or attempts != len(R1_CASE_STATES)
                or active is not None or crashed or reserved != 0):
            raise LedgerError("R1 predecessor is not the exact closed two-attempt history approved for R2")
        if not _valid_elapsed(elapsed) or elapsed > MAX_TOTAL_SECONDS:
            raise LedgerError("R1 predecessor elapsed time is invalid for the combined campaign budget")
        return attempts, float(elapsed)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        self._assert_safe_paths()
        baseline_attempts, baseline_elapsed = self._predecessor()
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise LedgerError("R2 ledger ends with an incomplete record")
        records: list[dict[str, Any]] = []
        previous = _GENESIS
        for sequence, line in enumerate(raw.splitlines(), 1):
            import json

            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise LedgerError(f"R2 ledger record {sequence} is invalid JSON") from exc
            if (not isinstance(record, dict) or type(record.get("sequence")) is not int
                    or record.get("sequence") != sequence or record.get("previous_record_sha256") != previous):
                raise LedgerError(f"R2 ledger sequence/hash chain is invalid at record {sequence}")
            claimed = record.pop("record_sha256", None)
            calculated = _sha256(_canonical(record))
            record["record_sha256"] = claimed
            if claimed != calculated:
                raise LedgerError(f"R2 ledger record hash mismatch at sequence {sequence}")
            if (record.get("campaign_id") != CAMPAIGN_ID
                    or record.get("ledger_scope_id") != LEDGER_SCOPE_ID
                    or record.get("r1_ledger_sha256") != self.predecessor_sha256):
                raise LedgerError("R2 ledger record has a foreign campaign/scope/predecessor identity")
            previous = calculated
            records.append(record)
        self._validate(records, baseline_attempts=baseline_attempts, baseline_elapsed=baseline_elapsed)
        return records

    @staticmethod
    def _validate(
        records: list[dict[str, Any]], *, baseline_attempts: int, baseline_elapsed: float,
    ) -> None:
        seen_cases: set[str] = set()
        active: dict[str, dict[str, Any]] = {}
        stopped = False
        campaign_binding: tuple[Any, ...] | None = None
        elapsed = 0.0
        seen_preflights: set[str] = set()
        for record in records:
            event = record.get("event")
            run_id = record.get("run_id")
            if event == "ATTEMPT_STARTED":
                case_id = record.get("case_id")
                if (stopped or active or not isinstance(case_id, str) or case_id not in CASE_IDS
                        or case_id in seen_cases or not isinstance(run_id, str) or run_id in active
                        or case_id != CASE_IDS[len(seen_cases)]
                        or record.get("attempt") != len(seen_cases) + 1
                        or record.get("reserved_seconds") != MAX_ATTEMPT_SECONDS
                        or record.get("monitored_limit_seconds") != MAX_ATTEMPT_SECONDS
                        or record.get("r1_attempts_before") != baseline_attempts
                        or record.get("r1_elapsed_seconds_before") != baseline_elapsed
                        or record.get("campaign_attempt_number") != baseline_attempts + len(seen_cases) + 1
                        or record.get("campaign_seconds_reserved_after")
                        != baseline_elapsed + elapsed + MAX_ATTEMPT_SECONDS):
                    raise LedgerError("R2 attempt start is duplicate, out of order, over budget, or after STOP")
                bind = tuple(record.get(key) for key in (
                    "contract_sha256", "decision_id", "decision_sha256", "manifest_sha256", "preflight_sha256",
                ))
                if (_HEX64.fullmatch(str(bind[0])) is None or not isinstance(bind[1], str)
                        or not bind[1] or any(_HEX64.fullmatch(str(value)) is None for value in bind[2:])):
                    raise LedgerError("R2 reservation lacks complete contract/decision/manifest/preflight binding")
                if campaign_binding is not None and bind[:3] != campaign_binding:
                    raise LedgerError("R2 attempts do not share the exact frozen contract and Owner decision")
                if bind[4] in seen_preflights:
                    raise LedgerError("R2 preflight receipt cannot be reused")
                campaign_binding = bind[:3]
                seen_preflights.add(bind[4])
                seen_cases.add(case_id)
                active[run_id] = record
            elif event == "ATTEMPT_FINISHED":
                start = active.pop(run_id, None)
                measured = record.get("elapsed_seconds")
                status = record.get("status")
                if (start is None or not _valid_elapsed(measured) or status not in _TERMINAL
                        or record.get("monitored_limit_seconds") != MAX_ATTEMPT_SECONDS):
                    raise LedgerError("R2 finish event does not match one valid reservation")
                expected_stops = []
                if measured > MAX_ATTEMPT_SECONDS:
                    expected_stops.append("PER_ATTEMPT_LIMIT_OVERRUN")
                if elapsed + measured > MAX_TOTAL_SECONDS:
                    expected_stops.append("GLOBAL_BUDGET_OVERRUN")
                if record.get("stop_reasons") != expected_stops:
                    raise LedgerError("R2 stop reasons differ from observed elapsed time")
                if expected_stops and status != "INFRA_ERROR":
                    raise LedgerError("R2 budget overrun must be archived as INFRA_ERROR")
                elapsed += measured
                if (record.get("campaign_attempts_used_after") != baseline_attempts + len(seen_cases)
                        or record.get("campaign_seconds_actual_after") != baseline_elapsed + elapsed):
                    raise LedgerError("R2 finish cumulative accounting differs from the immutable R1 baseline")
                stopped = status != "PASS" or bool(expected_stops)
            else:
                raise LedgerError("R2 ledger contains an unsupported event")
        if (len(seen_cases) > MAX_R2_ATTEMPTS
                or baseline_attempts + len(seen_cases) > MAX_GLOBAL_ATTEMPTS
                or baseline_elapsed + elapsed > MAX_TOTAL_SECONDS):
            raise LedgerError("R2 attempt cap exceeded")

    def _append_unlocked(self, fields: dict[str, Any]) -> dict[str, Any]:
        records = self._read_unlocked()
        body = {
            "sequence": len(records) + 1,
            "previous_record_sha256": records[-1]["record_sha256"] if records else _GENESIS,
            "campaign_id": CAMPAIGN_ID,
            "ledger_scope_id": LEDGER_SCOPE_ID,
            "r1_ledger_sha256": self.predecessor_sha256,
            **fields,
        }
        body["record_sha256"] = _sha256(_canonical(body))
        raw = _canonical(body) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            offset = 0
            while offset < len(raw):
                offset += os.write(fd, raw[offset:])
            os.fsync(fd)
        finally:
            os.close(fd)
        return body

    def start_runner_attempt(
        self,
        *,
        binding: RunBinding,
        case: RunnerCaseBinding,
        receipt_path: Path,
    ) -> dict[str, Any]:
        """Atomically reserve one exact R2 case and write its immutable receipt."""
        run = case.as_record()
        artifacts = binding.as_record()
        case_id = run["case_id"]
        expected_nodeid = NODEID_PREFIX + case_id + "]"
        if (case_id not in CASE_IDS or run["nodeid"] != expected_nodeid
                or run["timeout_seconds"] != MAX_ATTEMPT_SECONDS
                or run["selected_dofs"] <= 0 or run["rss_soft_limit_mib"] != 4096
                or run["archive_size_limit_mib"] != 256 or any(value is not None for value in (
                    artifacts.get("transition_receipt_sha256"), artifacts.get("transition_source_case_id"),
                    artifacts.get("transition_destination_case_id"),
                ))):
            raise LedgerError("R2 reservation case, budget or transition is outside the initial FEM tranche")
        receipt_path = receipt_path.resolve(strict=False)
        try:
            receipt_path.relative_to(self.allowed_root)
        except ValueError as exc:
            raise LedgerError("R2 reservation receipt must be inside its evidence root") from exc
        if receipt_path.exists():
            raise LedgerError("R2 reservation receipt already exists; refusing overwrite")
        r1 = R1BudgetLedger(self.predecessor_path, allowed_root=self.predecessor_path.parent)
        lock_paths = sorted((self.lock_path, r1.lock_path), key=lambda p: str(p.resolve(strict=False)).casefold())
        with ExitStack() as stack:
            for lock_path in lock_paths:
                stack.enter_context(_exclusive_lock(lock_path))
            baseline_attempts, baseline_elapsed = self._predecessor()
            records = self._read_unlocked()
            starts = [r for r in records if r["event"] == "ATTEMPT_STARTED"]
            finishes = {r["run_id"]: r for r in records if r["event"] == "ATTEMPT_FINISHED"}
            if any(r["run_id"] not in finishes for r in starts):
                raise LedgerError("an open R2 reservation blocks another attempt; no retry/recovery is implicit")
            if any(finishes[r["run_id"]].get("status") != "PASS" for r in starts):
                raise LedgerError("a non-PASS R2 result permanently stops the campaign")
            if any(r.get("case_id") == case_id for r in starts):
                raise LedgerError("R2 case already consumed its single attempt")
            if len(starts) >= MAX_R2_ATTEMPTS or baseline_attempts + len(starts) >= MAX_GLOBAL_ATTEMPTS:
                raise LedgerError("R2 or combined R1+R2 attempt budget is exhausted")
            spent = sum(float(r["elapsed_seconds"]) for r in finishes.values())
            if baseline_elapsed + spent + MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
                raise LedgerError("combined R1+R2 time budget cannot cover the full case timeout")
            run_id = run.get("reservation_id") or uuid.uuid4().hex
            if any(record.get("run_id") == run_id for record in records):
                raise LedgerError("R2 reservation ID already exists")
            start = self._append_unlocked({
                "event": "ATTEMPT_STARTED", "run_id": run_id, "attempt": len(starts) + 1,
                **artifacts, **run,
                "reserved_seconds": MAX_ATTEMPT_SECONDS,
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                "r1_attempts_before": baseline_attempts,
                "r1_elapsed_seconds_before": baseline_elapsed,
                "campaign_attempt_number": baseline_attempts + len(starts) + 1,
                "campaign_seconds_reserved_after": baseline_elapsed + spent + MAX_ATTEMPT_SECONDS,
                "started_utc": datetime.now(timezone.utc).isoformat(),
            })
            ledger_sha = _sha256(self.path.read_bytes())
            receipt = {
                "schema": "qf-wp12-vv3d-runner-reservation-v1", "status": "RESERVED",
                "campaign_id": CAMPAIGN_ID, "case_id": case_id, "nodeid": run["nodeid"],
                "manifest_sha256": artifacts["manifest_sha256"],
                "preflight_receipt_sha256": artifacts["preflight_sha256"],
                "decision_id": artifacts["decision_id"], "decision_sha256": artifacts["decision_sha256"],
                "contract_sha256": artifacts["contract_sha256"],
                "scientific_fingerprint": run["source_fingerprint"],
                "controller_fingerprint": run["controller_fingerprint"],
                "authorization_id": run["authorization_id"], "attempt_id": run["attempt_id"],
                "reservation_id": run_id, "selected_dofs": run["selected_dofs"],
                "timeout_seconds": run["timeout_seconds"], "rss_soft_limit_mib": run["rss_soft_limit_mib"],
                "archive_size_limit_mib": run["archive_size_limit_mib"],
                "ledger_scope_id": LEDGER_SCOPE_ID, "ledger_path": str(self.path),
                "ledger_sha256_after_reservation": ledger_sha,
                "attempt_number": 1, "campaign_attempt_number": baseline_attempts + len(starts) + 1,
                "max_attempts": 1, "attempt_reserved": True,
                "campaign_attempts_used_after": baseline_attempts + len(starts) + 1,
                "campaign_seconds_reserved_after": start["campaign_seconds_reserved_after"],
                "evidence_root": run["evidence_root"], "r1_ledger_sha256": self.predecessor_sha256,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            raw = _canonical(receipt) + b"\n"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with receipt_path.open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                checksum = receipt_path.with_suffix(receipt_path.suffix + ".sha256.json")
                with checksum.open("xb") as stream:
                    stream.write(_canonical({"schema": "qf-wp12-vv3d-runner-reservation-sha256-v1",
                                             "sha256": _sha256(raw)}) + b"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise LedgerError("R2 receipt or checksum already exists; refusing overwrite") from exc
            receipt["receipt_sha256"] = _sha256(raw)
            return receipt

    def finish_runner_attempt(self, *, run_id: str, status: str, elapsed_seconds: float) -> dict[str, Any]:
        if status not in _TERMINAL or not _valid_elapsed(elapsed_seconds):
            raise LedgerError("R2 terminal status or elapsed seconds are invalid")
        r1 = R1BudgetLedger(self.predecessor_path, allowed_root=self.predecessor_path.parent)
        lock_paths = sorted((self.lock_path, r1.lock_path), key=lambda p: str(p.resolve(strict=False)).casefold())
        with ExitStack() as stack:
            for lock_path in lock_paths:
                stack.enter_context(_exclusive_lock(lock_path))
            baseline_attempts, baseline_elapsed = self._predecessor()
            records = self._read_unlocked()
            starts = [r for r in records if r.get("event") == "ATTEMPT_STARTED"]
            finished = {r.get("run_id"): r for r in records if r.get("event") == "ATTEMPT_FINISHED"}
            start = next((r for r in starts if r.get("run_id") == run_id), None)
            if start is None or run_id in finished or any(r.get("run_id") not in finished and r.get("run_id") != run_id for r in starts):
                raise LedgerError("R2 finish must close exactly one existing open reservation")
            prior_elapsed = sum(float(r["elapsed_seconds"]) for r in finished.values())
            stops = []
            if elapsed_seconds > MAX_ATTEMPT_SECONDS:
                stops.append("PER_ATTEMPT_LIMIT_OVERRUN")
            if baseline_elapsed + prior_elapsed + elapsed_seconds > MAX_TOTAL_SECONDS:
                stops.append("GLOBAL_BUDGET_OVERRUN")
            final_status = "INFRA_ERROR" if stops else status
            finished_record = self._append_unlocked({
                "event": "ATTEMPT_FINISHED", "run_id": run_id, "case_id": start["case_id"],
                "status": final_status, "elapsed_seconds": float(elapsed_seconds),
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS, "stop_reasons": stops,
                "recovered_after_crash": False,
                "campaign_attempts_used_after": baseline_attempts + len(starts),
                "campaign_seconds_actual_after": baseline_elapsed + prior_elapsed + float(elapsed_seconds),
                "finished_utc": datetime.now(timezone.utc).isoformat(),
            })
            self._read_unlocked()
            return finished_record

    def summary(self) -> dict[str, int | float | bool]:
        r1 = R1BudgetLedger(self.predecessor_path, allowed_root=self.predecessor_path.parent)
        lock_paths = sorted((self.lock_path, r1.lock_path), key=lambda p: str(p.resolve(strict=False)).casefold())
        with ExitStack() as stack:
            for lock_path in lock_paths:
                stack.enter_context(_exclusive_lock(lock_path))
            baseline_attempts, baseline_elapsed = self._predecessor()
            records = self._read_unlocked()
            starts = [r for r in records if r["event"] == "ATTEMPT_STARTED"]
            finishes = {r.get("run_id"): r for r in records if r.get("event") == "ATTEMPT_FINISHED"}
            elapsed = sum(float(r["elapsed_seconds"]) for r in finishes.values())
            opened = any(r.get("run_id") not in finishes for r in starts)
            return {
                "r1_predecessor_sha256": self.predecessor_sha256,
                "attempts_used_r1": baseline_attempts,
                "attempts_used_r2": len(starts),
                "attempts_used_combined": baseline_attempts + len(starts),
                "attempts_remaining_r2": MAX_R2_ATTEMPTS - len(starts),
                "elapsed_seconds_r1": baseline_elapsed,
                "elapsed_seconds_r2": elapsed,
                "elapsed_seconds_combined": baseline_elapsed + elapsed,
                "seconds_remaining_combined": MAX_TOTAL_SECONDS - baseline_elapsed - elapsed,
                "attempt_open": opened,
                "stopped": any(finishes.get(r.get("run_id"), {}).get("status") != "PASS"
                               for r in starts if r.get("run_id") in finishes),
            }

    def verify(self) -> list[dict[str, Any]]:
        """Return the validated append-only R2 chain under both ledger locks."""
        r1 = R1BudgetLedger(self.predecessor_path, allowed_root=self.predecessor_path.parent)
        lock_paths = sorted((self.lock_path, r1.lock_path), key=lambda p: str(p.resolve(strict=False)).casefold())
        with ExitStack() as stack:
            for lock_path in lock_paths:
                stack.enter_context(_exclusive_lock(lock_path))
            return self._read_unlocked()
