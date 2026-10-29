"""Prospective controller ledger for the WP12 VV3D campaign.

The candidate development runner uses this module to reserve and account for
exact, prevalidated campaign jobs. The ledger records authorization bindings;
it does not authenticate Owner identity, validate external artifacts by itself,
or launch a child process. The caller must validate the policy, manifest,
decision, preflight and source identities before reserving. The candidate
controller is not the official launcher until separately designated through
the repository's reviewed controller-selection procedure.

The primitives are also safe to exercise in isolated temporary directories.
An open attempt found after a process restart keeps elapsed time explicitly
unknown, reserves the full per-attempt cap, and blocks further campaign work.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import numbers
import os
from pathlib import Path
import re
import threading
from typing import Any, Iterator, Mapping
import uuid


MAX_ATTEMPTS = 24
MAX_TOTAL_SECONDS = 28_800
MAX_ATTEMPT_SECONDS = 1_200
CAMPAIGN_ID = "WP12-VV3D-ADAPTIVE-20261029-R1"
LEDGER_SCOPE_ID = "wp12_vv3d_adaptive"
GENESIS = "0" * 64
TERMINAL_STATUSES = frozenset(
    {"PASS", "FAIL", "TIMEOUT", "INTERRUPTED", "RESOURCE_LIMIT", "INFRA_ERROR", "INCONCLUSIVE"}
)
QPOST_JOB_IDS = frozenset(
    {
        "VV3D-ADAPT-TET4-QPOST",
        "VV3D-ADAPT-TET10-QPOST",
        "VV3D-ADAPT-HEX8-QPOST",
        "VV3D-ADAPT-HEX20-QPOST",
    }
)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class LedgerError(ValueError):
    """Raised when the ledger is invalid or a budget operation is refused."""


@dataclass(frozen=True)
class RunBinding:
    """Caller-supplied identities recorded with each reserved campaign job.

    This binds ledger records to named artifacts. It does not authenticate an
    Owner decision; the runner validates the decision and preflight separately.
    """

    contract_sha256: str
    decision_id: str
    decision_sha256: str
    manifest_sha256: str
    preflight_sha256: str
    transition_receipt_sha256: str | None = None
    transition_source_case_id: str | None = None
    transition_destination_case_id: str | None = None

    def as_record(self) -> dict[str, str]:
        if not isinstance(self.decision_id, str) or _IDENTIFIER.fullmatch(self.decision_id) is None:
            raise LedgerError("decision_id must be a short safe identifier")
        for name in ("contract_sha256", "decision_sha256", "manifest_sha256", "preflight_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise LedgerError(f"{name} must be 64 lowercase hexadecimal characters")
        transition = (self.transition_receipt_sha256, self.transition_source_case_id,
                      self.transition_destination_case_id)
        if any(value is not None for value in transition):
            if (not isinstance(self.transition_receipt_sha256, str)
                    or re.fullmatch(r"[0-9a-f]{64}", self.transition_receipt_sha256) is None
                    or not isinstance(self.transition_source_case_id, str)
                    or _IDENTIFIER.fullmatch(self.transition_source_case_id) is None
                    or not isinstance(self.transition_destination_case_id, str)
                    or _IDENTIFIER.fullmatch(self.transition_destination_case_id) is None):
                raise LedgerError("adaptive transition binding must be complete and hash-bound")
        return {
            "contract_sha256": self.contract_sha256,
            "decision_id": self.decision_id,
            "decision_sha256": self.decision_sha256,
            "manifest_sha256": self.manifest_sha256,
            "preflight_sha256": self.preflight_sha256,
            "transition_receipt_sha256": self.transition_receipt_sha256,
            "transition_source_case_id": self.transition_source_case_id,
            "transition_destination_case_id": self.transition_destination_case_id,
        }


@dataclass(frozen=True)
class RunnerCaseBinding:
    """Exact run identity and limits included in the immutable reservation receipt."""

    case_id: str
    nodeid: str
    attempt_id: str
    authorization_id: str
    source_fingerprint: str
    controller_fingerprint: str
    selected_dofs: int
    timeout_seconds: int
    rss_soft_limit_mib: int
    archive_limit_mib: int
    evidence_root: str
    reservation_id: str | None = None

    def as_record(self) -> dict[str, Any]:
        for name, value in (("case_id", self.case_id), ("attempt_id", self.attempt_id),
                            ("authorization_id", self.authorization_id)):
            if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
                raise LedgerError(f"{name} must be a short safe identifier")
        if self.reservation_id is not None and (
                not isinstance(self.reservation_id, str) or _IDENTIFIER.fullmatch(self.reservation_id) is None):
            raise LedgerError("reservation_id must be a short safe identifier")
        if not isinstance(self.nodeid, str) or self.nodeid.count("::") != 1 or len(self.nodeid) > 512:
            raise LedgerError("nodeid must be one exact pytest test-function identity")
        for name, value in (("source_fingerprint", self.source_fingerprint),
                            ("controller_fingerprint", self.controller_fingerprint)):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise LedgerError(f"{name} must be a SHA-256 fingerprint")
        if type(self.selected_dofs) is not int or not 0 < self.selected_dofs <= 30_000:
            raise LedgerError("selected DDL exceeds the campaign limit")
        if type(self.timeout_seconds) is not int or not 0 < self.timeout_seconds <= MAX_ATTEMPT_SECONDS:
            raise LedgerError("case timeout exceeds the campaign limit")
        if self.rss_soft_limit_mib != 4096 or self.archive_limit_mib != 256:
            raise LedgerError("case RSS/archive limits differ from the approved campaign caps")
        if not isinstance(self.evidence_root, str) or not self.evidence_root:
            raise LedgerError("evidence_root is required for the runner receipt")
        return {
            "case_id": self.case_id, "nodeid": self.nodeid, "attempt_id": self.attempt_id,
            "reservation_id": self.reservation_id,
            "authorization_id": self.authorization_id,
            "source_fingerprint": self.source_fingerprint,
            "controller_fingerprint": self.controller_fingerprint,
            "selected_dofs": self.selected_dofs, "timeout_seconds": self.timeout_seconds,
            "rss_soft_limit_mib": self.rss_soft_limit_mib,
            "archive_size_limit_mib": self.archive_limit_mib,
            "evidence_root": self.evidence_root,
        }


def _canonical(record: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LedgerError("record is not canonical JSON") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_elapsed(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or value < 0:
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


@contextmanager
def _exclusive_lock(lock_path: Path) -> Iterator[None]:
    key = str(lock_path.resolve(strict=False)).casefold()
    with _THREAD_LOCKS_GUARD:
        thread_lock = _THREAD_LOCKS.setdefault(key, threading.RLock())
    with thread_lock:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as lock_file:
            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
                os.fsync(lock_file.fileno())
            lock_file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - platform-specific branch
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class BudgetLedger:
    """Append-only budget accounting, rooted at an explicit evidence area.

    The hash chain detects accidental edits but is not tamper-proof. The
    explicit allowed_root prevents accidental use of paths outside the
    caller-selected evidence area; it does not provide a security boundary.
    """

    def __init__(self, path: Path, *, allowed_root: Path) -> None:
        self.allowed_root = allowed_root.resolve(strict=True)
        self.path = path.resolve(strict=False)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._assert_safe_paths()

    def _assert_safe_paths(self) -> None:
        for candidate in (self.path, self.lock_path):
            try:
                relative = candidate.relative_to(self.allowed_root)
            except ValueError as exc:
                raise LedgerError("draft ledger paths must stay under the explicit allowed root") from exc
            if not relative.parts:
                raise LedgerError("ledger path must be a file below the allowed root")
            current = self.allowed_root
            for part in relative.parts:
                current = current / part
                if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                    raise LedgerError("draft ledger path contains a symlink or junction")

    def _read_unlocked(self) -> list[dict[str, Any]]:
        self._assert_safe_paths()
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise LedgerError("ledger ends with an incomplete record")
        records: list[dict[str, Any]] = []
        previous = GENESIS
        for sequence, line in enumerate(raw.splitlines(), 1):
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LedgerError(f"ledger record {sequence} is invalid JSON") from exc
            if not isinstance(record, dict) or record.get("sequence") != sequence:
                raise LedgerError(f"ledger sequence {sequence} is invalid")
            if record.get("previous_record_sha256") != previous:
                raise LedgerError(f"ledger predecessor hash at sequence {sequence} is invalid")
            claimed = record.pop("record_sha256", None)
            calculated = _sha256(_canonical(record))
            record["record_sha256"] = claimed
            if claimed != calculated:
                raise LedgerError(f"ledger record hash at sequence {sequence} is invalid")
            previous = calculated
            records.append(record)
        self._validate_events(records)
        return records

    @staticmethod
    def _validate_events(records: list[dict[str, Any]]) -> None:
        active: dict[str, dict[str, Any]] = {}
        seen: set[str] = set()
        seen_cases: set[str] = set()
        seen_post_jobs: set[str] = set()
        seen_preflights: set[str] = set()
        crashed: set[str] = set()
        completed_cases: dict[str, tuple[str, str]] = {}
        campaign_identity: tuple[str, str, str] | None = None
        attempts = 0
        starts = 0
        spent = 0.0
        for index, record in enumerate(records):
            event = record.get("event")
            run_id = record.get("run_id")
            if event in {"ATTEMPT_STARTED", "POSTPROCESS_STARTED"}:
                if not isinstance(run_id, str) or run_id in seen:
                    raise LedgerError("run identity is invalid or duplicated")
                if active:
                    raise LedgerError("ledger contains overlapping FEM or postprocessing jobs")
                if event == "ATTEMPT_STARTED":
                    case_id = record.get("case_id")
                    attempt = record.get("attempt")
                    if (
                        not isinstance(case_id, str)
                        or _IDENTIFIER.fullmatch(case_id) is None
                        or case_id in seen_cases
                        or isinstance(attempt, bool)
                        or not isinstance(attempt, int)
                    ):
                        raise LedgerError("attempt start identity is invalid or duplicated")
                    seen_cases.add(case_id)
                    attempts += 1
                    if record.get("attempt") != attempts:
                        raise LedgerError("attempt sequence is invalid")
                else:
                    job_id = record.get("job_id")
                    digest = record.get("archived_state_sha256")
                    source_case_id = record.get("source_case_id")
                    if (
                        not isinstance(job_id, str)
                        or job_id not in QPOST_JOB_IDS
                        or job_id in seen_post_jobs
                        or not isinstance(digest, str)
                        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                        or not isinstance(source_case_id, str)
                        or source_case_id not in completed_cases
                        or completed_cases[source_case_id][1] != record.get("manifest_sha256")
                    ):
                        raise LedgerError("QPOST job must bind a passed source case and its manifest/archive fingerprints")
                    source_status = completed_cases[source_case_id][0]
                    if (source_status not in {"PASS", "FAIL"}
                            or record.get("transition_source_case_id") != source_case_id
                            or record.get("transition_destination_case_id") != job_id
                            or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("transition_receipt_sha256", "")))):
                        raise LedgerError("QPOST requires an exact approved PASS-trigger or scientific-FAIL transition")
                    seen_post_jobs.add(job_id)
                binding_values = tuple(
                    record.get(key)
                    for key in ("contract_sha256", "decision_id", "decision_sha256", "manifest_sha256", "preflight_sha256")
                )
                if (
                    not isinstance(binding_values[0], str)
                    or re.fullmatch(r"[0-9a-f]{64}", binding_values[0]) is None
                    or not isinstance(binding_values[1], str)
                    or _IDENTIFIER.fullmatch(binding_values[1]) is None
                    or any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None for value in binding_values[2:])
                ):
                    raise LedgerError("job is missing a valid decision, contract, manifest or preflight identity")
                # Per-case manifests differ by design. Campaign identity is the
                # frozen contract and its Owner decision, never one case hash.
                identity = (binding_values[0], binding_values[1], binding_values[2])
                if campaign_identity is not None and identity != campaign_identity:
                    raise LedgerError("ledger job differs from the campaign contract/decision identity")
                campaign_identity = identity
                preflight_sha256 = binding_values[4]
                if preflight_sha256 in seen_preflights:
                    raise LedgerError("a preflight identity cannot be reused for another job")
                seen_preflights.add(preflight_sha256)
                seen.add(run_id)
                active[run_id] = record
                starts += 1
            elif event in {"ATTEMPT_CRASH_OBSERVED", "POSTPROCESS_CRASH_OBSERVED"}:
                start = active.get(run_id)
                if start is None or run_id in crashed:
                    raise LedgerError("crash observation has no unique open job")
                is_post = start["event"] == "POSTPROCESS_STARTED"
                if event != ("POSTPROCESS_CRASH_OBSERVED" if is_post else "ATTEMPT_CRASH_OBSERVED"):
                    raise LedgerError("crash observation type does not match the open job")
                if record.get("elapsed_seconds") is not None or record.get("elapsed_state") != "NOT_EXPOSED":
                    raise LedgerError("crash observation must preserve unknown real elapsed time")
                if record.get("reserved_seconds") != MAX_ATTEMPT_SECONDS:
                    raise LedgerError("crash observation does not reserve the full job cap")
                if record.get("monitored_limit_seconds") != MAX_ATTEMPT_SECONDS:
                    raise LedgerError("crash observation does not preserve the monitored job limit")
                crashed.add(run_id)
            elif event in {"ATTEMPT_FINISHED", "POSTPROCESS_FINISHED"}:
                start = active.get(run_id)
                if start is None:
                    raise LedgerError("finish event has no matching open job")
                is_post = start["event"] == "POSTPROCESS_STARTED"
                if event != ("POSTPROCESS_FINISHED" if is_post else "ATTEMPT_FINISHED"):
                    raise LedgerError("finish event type does not match the open job")
                if is_post and (
                    record.get("job_id") != start.get("job_id")
                    or record.get("archived_state_sha256") != start.get("archived_state_sha256")
                ):
                    raise LedgerError("QPOST finish identity differs from its start record")
                elapsed = record.get("elapsed_seconds")
                if not _valid_elapsed(elapsed):
                    raise LedgerError("finished elapsed time must be finite and non-negative")
                if record.get("monitored_limit_seconds") != MAX_ATTEMPT_SECONDS:
                    raise LedgerError("finish record does not preserve the monitored job limit")
                status = record.get("status")
                if not isinstance(status, str) or status not in TERMINAL_STATUSES:
                    raise LedgerError("job terminal status is invalid")
                stop_reasons = record.get("stop_reasons")
                if not isinstance(stop_reasons, list) or any(not isinstance(reason, str) for reason in stop_reasons):
                    raise LedgerError("stop_reasons must be a list of strings")
                expected_reasons = []
                if elapsed > MAX_ATTEMPT_SECONDS:
                    expected_reasons.append("PER_ATTEMPT_LIMIT_OVERRUN")
                if spent + elapsed > MAX_TOTAL_SECONDS:
                    expected_reasons.append("GLOBAL_BUDGET_OVERRUN")
                if stop_reasons != expected_reasons:
                    raise LedgerError("recorded stop reasons do not match measured elapsed time")
                if expected_reasons and status != "INFRA_ERROR":
                    raise LedgerError("a budget overrun must be archived as INFRA_ERROR")
                if run_id in crashed:
                    if (
                        not isinstance(record.get("recovery_decision_id"), str)
                        or not record["recovery_decision_id"].strip()
                        or not isinstance(record.get("recovery_decision_rationale"), str)
                        or not record["recovery_decision_rationale"].strip()
                        or record.get("recovered_after_crash") is not True
                    ):
                        raise LedgerError("crashed job lacks a documented resolution decision")
                elif record.get("recovered_after_crash") is not False:
                    raise LedgerError("ordinary finish has an invalid recovery marker")
                spent += elapsed
                if not is_post:
                    case_id = start["case_id"]
                    completed_cases[case_id] = (status, start["manifest_sha256"])
                del active[run_id]
                crashed.discard(run_id)
            else:
                raise LedgerError("ledger event type is invalid")
        if attempts > MAX_ATTEMPTS:
            raise LedgerError("ledger exceeds the global attempt cap")
        if not _valid_elapsed(spent) or starts > MAX_ATTEMPTS + len(QPOST_JOB_IDS):
            raise LedgerError("ledger total time or number of jobs is invalid")

    @staticmethod
    def _projection(records: list[dict[str, Any]]) -> tuple[int, float, int, str | None, bool]:
        attempts = [r for r in records if r["event"] == "ATTEMPT_STARTED"]
        starts = [r for r in records if r["event"] in {"ATTEMPT_STARTED", "POSTPROCESS_STARTED"}]
        finished = [
            r for r in records if r["event"] in {"ATTEMPT_FINISHED", "POSTPROCESS_FINISHED"}
        ]
        active = next((r["run_id"] for r in starts if not any(f["run_id"] == r["run_id"] for f in finished)), None)
        spent = sum(r["elapsed_seconds"] for r in finished)
        reserved = MAX_ATTEMPT_SECONDS if active is not None else 0
        crashed = active is not None and any(
            r.get("event") in {"ATTEMPT_CRASH_OBSERVED", "POSTPROCESS_CRASH_OBSERVED"}
            and r.get("run_id") == active
            for r in records
        )
        return len(attempts), spent, reserved, active, crashed

    def verify(self) -> tuple[dict[str, Any], ...]:
        with _exclusive_lock(self.lock_path):
            return tuple(self._read_unlocked())

    def _append_unlocked(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_safe_paths()
        records = self._read_unlocked()
        record = {
            "sequence": len(records) + 1,
            "previous_record_sha256": records[-1]["record_sha256"] if records else GENESIS,
            **dict(fields),
        }
        record["record_sha256"] = _sha256(_canonical(record))
        line = _canonical(record) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            offset = 0
            while offset < len(line):
                offset += os.write(descriptor, line[offset:])
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return record

    def start_synthetic_attempt(self, *, case_id: str, binding: RunBinding) -> str:
        """Record a synthetic attempt start; this function never launches work."""
        if not isinstance(case_id, str) or _IDENTIFIER.fullmatch(case_id) is None:
            raise LedgerError("synthetic case_id must be a short identifier")
        binding_fields = binding.as_record()
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, _ = self._projection(records)
            if active is not None:
                raise LedgerError("an attempt is already open; recover it explicitly after confirming its process is absent")
            attempts, seconds, reserved, _, _ = self._projection(records)
            if any(record.get("event") == "ATTEMPT_STARTED" and record.get("case_id") == case_id for record in records):
                raise LedgerError("case_id has already been attempted in this campaign")
            if attempts >= MAX_ATTEMPTS:
                raise LedgerError("global attempt budget is exhausted")
            finished = [
                r for r in records if r.get("event") in {"ATTEMPT_FINISHED", "POSTPROCESS_FINISHED"}
            ]
            if any(r["elapsed_seconds"] > MAX_ATTEMPT_SECONDS for r in finished):
                raise LedgerError("a per-attempt watchdog overrun stopped this campaign")
            if seconds > MAX_TOTAL_SECONDS:
                raise LedgerError("global measured time budget was exceeded; campaign is stopped")
            if any(record.get("status") != "PASS" for record in finished):
                raise LedgerError("a non-PASS result stopped the campaign; no approved transition table is configured")
            if seconds + reserved + MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
                raise LedgerError("global time budget cannot cover another maximum-length attempt")
            run_id = uuid.uuid4().hex
            self._append_unlocked(
                {
                    "event": "ATTEMPT_STARTED",
                    "run_id": run_id,
                    "case_id": case_id,
                    "attempt": attempts + 1,
                    **binding_fields,
                    "started_utc": _utc_now(),
                }
            )
            return run_id

    def start_runner_attempt(
        self, *, binding: RunBinding, case: RunnerCaseBinding, receipt_path: Path,
        receipt_fields: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically reserve a VV3D attempt and create its immutable runner receipt.

        The caller must complete official source/controller/Owner/preflight and
        manifest validation before entering this method. It does not launch a
        process. If receipt creation fails after the ledger append, the open
        full-cap reservation is intentionally retained and blocks another run.
        """
        run = case.as_record()
        artifacts = binding.as_record()
        receipt_path = receipt_path.resolve(strict=False)
        try:
            receipt_path.relative_to(self.allowed_root)
        except ValueError as exc:
            raise LedgerError("reservation receipt must be inside the campaign evidence root") from exc
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            attempts, spent, reserved, active, crashed = self._projection(records)
            if any(r.get("event") == "ATTEMPT_STARTED" and r.get("case_id") == run["case_id"] for r in records):
                raise LedgerError("case_id has already been attempted; retries are forbidden")
            if active is not None or crashed:
                raise LedgerError("an open or interrupted reservation blocks another attempt")
            finished = [r for r in records if r.get("event") in {"ATTEMPT_FINISHED", "POSTPROCESS_FINISHED"}]
            if attempts >= MAX_ATTEMPTS:
                raise LedgerError("global attempt budget is exhausted")
            transition_sha = artifacts.get("transition_receipt_sha256")
            if transition_sha is not None:
                source_case_id = artifacts.get("transition_source_case_id")
                source_start = next((r for r in reversed(records) if r.get("event") == "ATTEMPT_STARTED"
                                     and r.get("case_id") == source_case_id), None)
                source_finish = next((r for r in reversed(records) if r.get("event") == "ATTEMPT_FINISHED"
                                      and source_start is not None and r.get("run_id") == source_start.get("run_id")), None)
                if (source_start is None or source_finish is None
                        or source_finish.get("status") not in {"PASS", "FAIL"}
                        or artifacts.get("transition_destination_case_id") != run["case_id"]):
                    raise LedgerError("adaptive transition receipt does not bind an exact completed source case")
            elif any(r.get("status") != "PASS" for r in finished):
                raise LedgerError("infrastructure, provenance or ledger failures permanently stop the campaign")
            if spent + reserved + MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
                raise LedgerError("remaining global time cannot cover the full attempt cap")
            if any(r.get("elapsed_seconds", 0) > MAX_ATTEMPT_SECONDS for r in finished):
                raise LedgerError("a previous timeout overrun stopped the campaign")
            run_id = run.get("reservation_id") or uuid.uuid4().hex
            if any(r.get("run_id") == run_id for r in records):
                raise LedgerError("reservation_id has already been used")
            self._append_unlocked({
                "event": "ATTEMPT_STARTED", "run_id": run_id, "case_id": run["case_id"],
                "attempt": attempts + 1, **artifacts, **run,
                "reserved_seconds": MAX_ATTEMPT_SECONDS,
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                "started_utc": _utc_now(),
            })
            ledger_sha = _sha256(self.path.read_bytes())
            receipt = {
                "schema": "qf-wp12-vv3d-runner-reservation-v1",
                "campaign_id": CAMPAIGN_ID,
                "case_id": run["case_id"], "nodeid": run["nodeid"],
                "manifest_sha256": artifacts["manifest_sha256"],
                "preflight_receipt_sha256": artifacts["preflight_sha256"],
                "decision_id": artifacts["decision_id"],
                "decision_sha256": artifacts["decision_sha256"],
                "contract_sha256": artifacts["contract_sha256"],
                "scientific_fingerprint": run["source_fingerprint"],
                "controller_fingerprint": run["controller_fingerprint"],
                "authorization_id": run["authorization_id"],
                "attempt_id": run["attempt_id"], "reservation_id": run_id,
                "selected_dofs": run["selected_dofs"], "timeout_seconds": run["timeout_seconds"],
                "rss_soft_limit_mib": run["rss_soft_limit_mib"],
                "archive_size_limit_mib": run["archive_size_limit_mib"],
                "ledger_scope_id": LEDGER_SCOPE_ID, "ledger_path": str(self.path),
                "ledger_sha256_after_reservation": ledger_sha,
                # A case is single-use; campaign sequence is recorded separately.
                # Adaptive science receipts define attempt_number per candidate.
                "attempt_number": 1, "campaign_attempt_number": attempts + 1,
                "max_attempts": 1, "attempt_reserved": True,
                "campaign_attempts_used_after": attempts + 1,
                "campaign_seconds_reserved_after": spent + reserved + MAX_ATTEMPT_SECONDS,
                "transition_receipt_sha256": artifacts.get("transition_receipt_sha256"),
                "transition_source_case_id": artifacts.get("transition_source_case_id"),
                "transition_destination_case_id": artifacts.get("transition_destination_case_id"),
                "evidence_root": run["evidence_root"],
                "status": "RESERVED", "created_at_utc": _utc_now(),
            }
            if receipt_fields is not None:
                if not isinstance(receipt_fields, Mapping):
                    raise LedgerError("custom receipt fields must be a mapping")
                for key in set(receipt).intersection(receipt_fields) - {"schema", "status"}:
                    if receipt_fields[key] != receipt[key]:
                        raise LedgerError(f"custom receipt cannot alter reserved identity field {key}")
                receipt.update(dict(receipt_fields))
            raw = _canonical(receipt) + b"\n"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with receipt_path.open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise LedgerError("reservation receipt already exists; refusing overwrite") from exc
            receipt_digest = _sha256(raw)
            sidecar = {"schema": "qf-wp12-vv3d-runner-reservation-sha256-v1", "sha256": receipt_digest}
            try:
                with receipt_path.with_suffix(receipt_path.suffix + ".sha256.json").open("xb") as stream:
                    stream.write(_canonical(sidecar) + b"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise LedgerError("reservation receipt checksum sidecar already exists; refusing overwrite") from exc
            receipt["receipt_sha256"] = receipt_digest
            return receipt

    def finish_runner_attempt(self, *, run_id: str, status: str, elapsed_seconds: float) -> dict[str, Any]:
        """Replace the reserved duration with observed elapsed time exactly once."""
        if status not in TERMINAL_STATUSES or not _valid_elapsed(elapsed_seconds):
            raise LedgerError("terminal status or elapsed time is invalid")
        return self.finish_synthetic_attempt(run_id=run_id, status=status, elapsed_seconds=elapsed_seconds)

    def start_runner_postprocess_job(
        self, *, job_id: str, source_case_id: str, archived_state_sha256: str,
        binding: RunBinding, nodeid: str, source_fingerprint: str,
        controller_fingerprint: str, evidence_root: str, receipt_path: Path,
        job_manifest_sha256: str,
        receipt_fields: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically reserve a monitored QPOST operation without consuming FEM attempts."""
        for name, value in (("source_fingerprint", source_fingerprint),
                            ("controller_fingerprint", controller_fingerprint)):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise LedgerError(f"{name} must be a SHA-256 fingerprint")
        if not isinstance(nodeid, str) or nodeid.count("::") != 1 or len(nodeid) > 512:
            raise LedgerError("QPOST nodeid must be one exact pytest function identity")
        if not isinstance(evidence_root, str) or not evidence_root:
            raise LedgerError("QPOST evidence_root is required")
        if not isinstance(job_manifest_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", job_manifest_sha256) is None:
            raise LedgerError("QPOST execution manifest SHA-256 is required")
        receipt_path = receipt_path.resolve(strict=False)
        try:
            receipt_path.relative_to(self.allowed_root)
        except ValueError as exc:
            raise LedgerError("QPOST reservation receipt must be inside the campaign evidence root") from exc
        # Append and receipt creation share one lock acquisition.  Calling the
        # public synthetic helper here would release the lock between those
        # operations and permit another runner to observe an incomplete job.
        with _exclusive_lock(self.lock_path):
            run_id = self._start_synthetic_postprocess_job_unlocked(
                job_id=job_id, source_case_id=source_case_id,
                archived_state_sha256=archived_state_sha256, binding=binding,
            )
            records = self._read_unlocked()
            start = next(r for r in records if r.get("event") == "POSTPROCESS_STARTED" and r.get("run_id") == run_id)
            attempts, spent, reserved, _, _ = self._projection(records)
            receipt = {
                "schema": "qf-wp12-vv3d-qpost-reservation-v1", "campaign_id": CAMPAIGN_ID,
                "job_id": job_id, "source_case_id": source_case_id,
                "archived_state_sha256": archived_state_sha256, "nodeid": nodeid,
                "source_case_manifest_sha256": start["manifest_sha256"],
                "manifest_sha256": job_manifest_sha256,
                "preflight_receipt_sha256": start["preflight_sha256"],
                "decision_id": start["decision_id"], "decision_sha256": start["decision_sha256"],
                "contract_sha256": start["contract_sha256"],
                "scientific_fingerprint": source_fingerprint,
                "controller_fingerprint": controller_fingerprint,
                "reservation_id": run_id, "ledger_scope_id": LEDGER_SCOPE_ID,
                "ledger_path": str(self.path), "ledger_sha256_after_reservation": _sha256(self.path.read_bytes()),
                "attempt_number": None, "max_attempts": 0, "attempt_reserved": False,
                "campaign_attempts_used_after": attempts,
                "campaign_seconds_reserved_after": spent + reserved,
                "timeout_seconds": MAX_ATTEMPT_SECONDS, "rss_soft_limit_mib": 4096,
                "archive_size_limit_mib": 256, "evidence_root": evidence_root,
                "status": "RESERVED", "created_at_utc": _utc_now(),
            }
            if receipt_fields is not None:
                if not isinstance(receipt_fields, Mapping):
                    raise LedgerError("custom QPOST receipt fields must be a mapping")
                for key in set(receipt).intersection(receipt_fields) - {"schema", "status"}:
                    if receipt_fields[key] != receipt[key]:
                        raise LedgerError(f"custom QPOST receipt cannot alter reserved identity field {key}")
                receipt.update(dict(receipt_fields))
            raw = _canonical(receipt) + b"\n"
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with receipt_path.open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                checksum_path = receipt_path.with_suffix(receipt_path.suffix + ".sha256.json")
                with checksum_path.open("xb") as stream:
                    stream.write(_canonical({"schema": "qf-wp12-vv3d-qpost-reservation-sha256-v1",
                                             "sha256": _sha256(raw)}) + b"\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError as exc:
                raise LedgerError("QPOST receipt already exists; refusing overwrite") from exc
            receipt["receipt_sha256"] = _sha256(raw)
            return receipt

    def finish_runner_postprocess_job(self, *, run_id: str, status: str, elapsed_seconds: float) -> dict[str, Any]:
        """Close a QPOST reservation with observed elapsed time and no FEM attempt increment."""
        return self.finish_synthetic_postprocess_job(
            run_id=run_id, status=status, elapsed_seconds=elapsed_seconds,
        )

    def start_synthetic_postprocess_job(
        self,
        *,
        job_id: str,
        source_case_id: str,
        archived_state_sha256: str,
        binding: RunBinding,
    ) -> str:
        """Record a catalogued QPOST job; does not read archives or run postprocessing.

        QPOST identities are unique and separate from the 24 FEM-attempt slots,
        while sharing the same global lock, one-job-at-a-time rule, and seconds
        budget. The caller supplies an archive fingerprint for binding only.
        """
        if job_id not in QPOST_JOB_IDS:
            raise LedgerError("QPOST job_id is outside the four-entry closed catalog")
        if not isinstance(archived_state_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", archived_state_sha256) is None:
            raise LedgerError("archived state SHA-256 must be 64 lowercase hexadecimal characters")
        if not isinstance(source_case_id, str) or _IDENTIFIER.fullmatch(source_case_id) is None:
            raise LedgerError("QPOST source_case_id must be a short safe identifier")
        with _exclusive_lock(self.lock_path):
            return self._start_synthetic_postprocess_job_unlocked(
                job_id=job_id, source_case_id=source_case_id,
                archived_state_sha256=archived_state_sha256, binding=binding,
            )

    def _start_synthetic_postprocess_job_unlocked(
        self, *, job_id: str, source_case_id: str, archived_state_sha256: str,
        binding: RunBinding,
    ) -> str:
        """Append one QPOST start while the caller owns the ledger lock."""
        if job_id not in QPOST_JOB_IDS:
            raise LedgerError("QPOST job_id is outside the four-entry closed catalog")
        if not isinstance(archived_state_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", archived_state_sha256) is None:
            raise LedgerError("archived state SHA-256 must be 64 lowercase hexadecimal characters")
        if not isinstance(source_case_id, str) or _IDENTIFIER.fullmatch(source_case_id) is None:
            raise LedgerError("QPOST source_case_id must be a short safe identifier")
        binding_fields = binding.as_record()
        if (binding_fields.get("transition_source_case_id") != source_case_id
                or binding_fields.get("transition_destination_case_id") != job_id
                or not binding_fields.get("transition_receipt_sha256")):
            raise LedgerError("QPOST requires an exact source-to-job eligibility receipt")
        records = self._read_unlocked()
        _, seconds, reserved, active, _ = self._projection(records)
        if active is not None:
            raise LedgerError("another FEM or postprocessing job is already open")
        if any(record.get("event") == "POSTPROCESS_STARTED" and record.get("job_id") == job_id for record in records):
            raise LedgerError("QPOST job_id has already been consumed")
        source_start = next(
            (
                start
                for start in reversed(records)
                if start.get("event") == "ATTEMPT_STARTED"
                and start.get("case_id") == source_case_id
                and any(finish.get("event") == "ATTEMPT_FINISHED"
                        and finish.get("run_id") == start.get("run_id")
                        and finish.get("status") in {"PASS", "FAIL"} for finish in records)
            ),
            None,
        )
        if source_start is None or source_start.get("manifest_sha256") != binding_fields["manifest_sha256"]:
            raise LedgerError("QPOST requires the exact manifest identity of a completed source case")
        prior_finish = next((r for r in reversed(records) if r.get("event") == "ATTEMPT_FINISHED"), None)
        prior_start = next((r for r in reversed(records) if r.get("event") == "ATTEMPT_STARTED"), None)
        if (prior_finish is None or prior_start is None
                or prior_start.get("case_id") != source_case_id
                or prior_finish.get("status") not in {"PASS", "FAIL"}):
            raise LedgerError("QPOST can only follow its exact immediately preceding source result")
        finished = [
            r for r in records if r.get("event") in {"ATTEMPT_FINISHED", "POSTPROCESS_FINISHED"}
        ]
        if any(r["elapsed_seconds"] > MAX_ATTEMPT_SECONDS for r in finished):
            raise LedgerError("a per-attempt watchdog overrun stopped this campaign")
        if seconds > MAX_TOTAL_SECONDS:
            raise LedgerError("global measured time budget was exceeded; campaign is stopped")
        if any(r.get("status") not in {"PASS", "FAIL"} for r in finished):
            raise LedgerError("infrastructure, provenance or ledger failures permanently stop the campaign")
        if len([r for r in records if r.get("event") == "POSTPROCESS_STARTED"]) >= len(QPOST_JOB_IDS):
            raise LedgerError("all catalogued QPOST jobs have been consumed")
        if seconds + reserved + MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
            raise LedgerError("global time budget cannot cover another maximum-length job")
        run_id = uuid.uuid4().hex
        self._append_unlocked(
            {
                "event": "POSTPROCESS_STARTED",
                "run_id": run_id,
                "job_id": job_id,
                "source_case_id": source_case_id,
                "archived_state_sha256": archived_state_sha256,
                **binding_fields,
                "transition_receipt_sha256": binding_fields["transition_receipt_sha256"],
                "transition_source_case_id": binding_fields["transition_source_case_id"],
                "transition_destination_case_id": binding_fields["transition_destination_case_id"],
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                "started_utc": _utc_now(),
            }
        )
        return run_id

    def finish_synthetic_postprocess_job(
        self, *, run_id: str, status: str, elapsed_seconds: float
    ) -> dict[str, Any]:
        """Finish a synthetic QPOST record, preserving measured wall time."""
        if not isinstance(run_id, str) or not run_id:
            raise LedgerError("run_id is required")
        if not isinstance(status, str) or status not in TERMINAL_STATUSES:
            raise LedgerError("terminal status is invalid")
        if not _valid_elapsed(elapsed_seconds):
            raise LedgerError("elapsed_seconds must be finite and non-negative")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, prior_spent, _, active, crashed = self._projection(records)
            start = next((r for r in records if r.get("event") == "POSTPROCESS_STARTED" and r.get("run_id") == run_id), None)
            if active != run_id or start is None:
                raise LedgerError("run_id is not the open QPOST job")
            if crashed:
                raise LedgerError("crash-blocked QPOST job requires documented resolution")
            stop_reasons = _stop_reasons(elapsed_seconds, prior_spent)
            return self._append_unlocked(
                {
                    "event": "POSTPROCESS_FINISHED",
                    "run_id": run_id,
                    "job_id": start["job_id"],
                    "archived_state_sha256": start["archived_state_sha256"],
                    "status": "INFRA_ERROR" if stop_reasons else status,
                    "elapsed_seconds": elapsed_seconds,
                    "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                    "stop_reasons": stop_reasons,
                    "recovered_after_crash": False,
                    "finished_utc": _utc_now(),
                }
            )

    def recover_interrupted_after_crash(self, *, confirmed_process_absent: bool) -> dict[str, Any]:
        """Record a FEM or QPOST crash without inventing elapsed time or clearing the blocker.

        The event stores ``elapsed_seconds: null`` and ``elapsed_state:
        NOT_EXPOSED`` while reserving the full cap. The process-absence
        confirmation is an operator assertion, not a liveness check.
        """
        if confirmed_process_absent is not True:
            raise LedgerError("crash recovery requires explicit confirmation that the worker process is absent")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, crashed = self._projection(records)
            if active is None:
                raise LedgerError("there is no open job to recover")
            if crashed:
                raise LedgerError("crash has already been recorded and remains unresolved")
            start = next(
                r for r in records if r.get("event") in {"ATTEMPT_STARTED", "POSTPROCESS_STARTED"} and r.get("run_id") == active
            )
            is_post = start["event"] == "POSTPROCESS_STARTED"
            return self._append_unlocked(
                {
                    "event": "POSTPROCESS_CRASH_OBSERVED" if is_post else "ATTEMPT_CRASH_OBSERVED",
                    "run_id": active,
                    "elapsed_seconds": None,
                    "elapsed_state": "NOT_EXPOSED",
                    "reserved_seconds": MAX_ATTEMPT_SECONDS,
                    "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                    "observed_utc": _utc_now(),
                }
            )

    def recover_postprocess_after_crash(self, *, confirmed_process_absent: bool) -> dict[str, Any]:
        """QPOST-specific entrypoint for the shared conservative crash recorder."""
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, _ = self._projection(records)
            if active is None or not any(
                r.get("event") == "POSTPROCESS_STARTED" and r.get("run_id") == active for r in records
            ):
                raise LedgerError("there is no open QPOST job to recover")
        return self.recover_interrupted_after_crash(confirmed_process_absent=confirmed_process_absent)

    def resolve_crashed_attempt(
        self,
        *,
        elapsed_seconds: float,
        decision_id: str,
        decision_rationale: str,
    ) -> dict[str, Any]:
        """Resolve a crash only with reliable measured time and a documented decision.

        Until this append succeeds, the unknown duration remains NOT_EXPOSED,
        the full cap remains reserved, and all new attempts stay blocked.
        """
        if not _valid_elapsed(elapsed_seconds):
            raise LedgerError("reliable elapsed_seconds must be finite and non-negative")
        if not isinstance(decision_id, str) or not decision_id.strip():
            raise LedgerError("documented recovery decision_id is required")
        if not isinstance(decision_rationale, str) or not decision_rationale.strip():
            raise LedgerError("documented recovery rationale is required")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, crashed = self._projection(records)
            if active is None or not crashed:
                raise LedgerError("there is no crash-blocked job to resolve")
            start = next(
                r for r in records if r.get("event") in {"ATTEMPT_STARTED", "POSTPROCESS_STARTED"} and r.get("run_id") == active
            )
            is_post = start["event"] == "POSTPROCESS_STARTED"
            _, prior_spent, _, _, _ = self._projection(records)
            stop_reasons = _stop_reasons(elapsed_seconds, prior_spent)
            return self._append_unlocked(
                {
                    "event": "POSTPROCESS_FINISHED" if is_post else "ATTEMPT_FINISHED",
                    "run_id": active,
                    "job_id": start.get("job_id"),
                    "archived_state_sha256": start.get("archived_state_sha256"),
                    "status": "INFRA_ERROR" if stop_reasons else "INTERRUPTED",
                    "elapsed_seconds": elapsed_seconds,
                    "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                    "stop_reasons": stop_reasons,
                    "recovered_after_crash": True,
                    "recovery_decision_id": decision_id.strip(),
                    "recovery_decision_rationale": decision_rationale.strip(),
                    "finished_utc": _utc_now(),
                }
            )

    def resolve_crashed_postprocess_job(
        self,
        *,
        elapsed_seconds: float,
        decision_id: str,
        decision_rationale: str,
    ) -> dict[str, Any]:
        """QPOST-specific entrypoint for measured, documented crash resolution."""
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, crashed = self._projection(records)
            if active is None or not crashed or not any(
                r.get("event") == "POSTPROCESS_STARTED" and r.get("run_id") == active for r in records
            ):
                raise LedgerError("there is no crash-blocked QPOST job to resolve")
        return self.resolve_crashed_attempt(
            elapsed_seconds=elapsed_seconds,
            decision_id=decision_id,
            decision_rationale=decision_rationale,
        )

    def finish_synthetic_attempt(self, *, run_id: str, status: str, elapsed_seconds: float) -> dict[str, Any]:
        """Close a synthetic attempt using observed integer wall seconds."""
        if not isinstance(run_id, str) or not run_id:
            raise LedgerError("run_id is required")
        if not isinstance(status, str) or status not in TERMINAL_STATUSES:
            raise LedgerError("terminal status is invalid")
        if not _valid_elapsed(elapsed_seconds):
            raise LedgerError("elapsed_seconds must be finite and non-negative")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            _, _, _, active, crashed = self._projection(records)
            if active != run_id:
                raise LedgerError("run_id is not the one open attempt")
            if crashed:
                raise LedgerError("crash-blocked attempt requires documented resolution")
            attempts, prior_spent, _, _, _ = self._projection(records)
            stop_reasons = _stop_reasons(elapsed_seconds, prior_spent)
            finished = self._append_unlocked(
                {
                    "event": "ATTEMPT_FINISHED",
                    "run_id": run_id,
                    "status": "INFRA_ERROR" if stop_reasons else status,
                    "elapsed_seconds": elapsed_seconds,
                    "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                    "stop_reasons": stop_reasons,
                    "recovered_after_crash": False,
                    "finished_utc": _utc_now(),
                }
            )
            records = self._read_unlocked()
            attempts, seconds, reserved, _, _ = self._projection(records)
            if attempts > MAX_ATTEMPTS:
                raise LedgerError("global budget invariant violated")
            return finished

    def summary(self) -> dict[str, int | float | bool]:
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            attempts, spent, reserved, active, crashed = self._projection(records)
            postprocess_jobs = sum(r.get("event") == "POSTPROCESS_STARTED" for r in records)
            return {
                "attempts_used": attempts,
                "attempts_remaining": MAX_ATTEMPTS - attempts,
                "postprocess_jobs_used": postprocess_jobs,
                "postprocess_jobs_remaining": len(QPOST_JOB_IDS) - postprocess_jobs,
                "elapsed_seconds_actual": spent,
                "seconds_reserved": reserved,
                "seconds_remaining_after_reservation": MAX_TOTAL_SECONDS - spent - reserved,
                "attempt_open": active is not None,
                "crash_blocked": crashed,
            }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _stop_reasons(elapsed_seconds: float, prior_spent: float) -> list[str]:
    reasons = []
    if elapsed_seconds > MAX_ATTEMPT_SECONDS:
        reasons.append("PER_ATTEMPT_LIMIT_OVERRUN")
    if prior_spent + elapsed_seconds > MAX_TOTAL_SECONDS:
        reasons.append("GLOBAL_BUDGET_OVERRUN")
    return reasons
