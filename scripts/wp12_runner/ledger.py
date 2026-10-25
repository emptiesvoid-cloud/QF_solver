"""Hash-chained append-only logical ledger for WP12 execution attempts."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import threading
import uuid
from typing import Any, Iterator, Mapping

from .contracts import ContractError, is_exact_nodeid, sha256_bytes


_TERMINAL = frozenset({"PASS", "FAIL", "TIMEOUT", "RESOURCE_LIMIT", "INTERRUPTED", "INFRA_ERROR", "INCONCLUSIVE"})
_GENESIS = "0" * 64
_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _canonical(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise ContractError("ledger record is not canonical JSON") from exc


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
            else:  # pragma: no cover - exercised on non-Windows development hosts
                import fcntl

                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


class AttemptLedger:
    """Append events with a sequence and SHA-256 predecessor chain.

    The chain detects accidental edits/truncation. It is not physically
    immutable: an actor with write access can replace the ledger and recompute
    the chain. External anchoring is required for stronger assurance.
    """

    def __init__(self, path: Path, *, allowed_root: Path) -> None:
        self.allowed_root = allowed_root.resolve(strict=True)
        self.path = path.resolve(strict=False)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._assert_safe_paths()

    def _assert_safe_paths(self) -> None:
        for candidate in (self.path, self.lock_path):
            try:
                candidate.resolve(strict=False).relative_to(self.allowed_root)
            except ValueError as exc:
                raise ContractError("attempt ledger paths must remain under the configured audit root") from exc
            current = self.allowed_root
            try:
                relative = candidate.relative_to(self.allowed_root)
            except ValueError as exc:
                raise ContractError("attempt ledger path is outside the audit root") from exc
            if not relative.parts:
                raise ContractError("attempt ledger file path must be below the audit root")
            for part in relative.parts:
                current = current / part
                if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                    raise ContractError("attempt ledger path contains a symlink or junction")

    def _read_unlocked(self) -> list[dict[str, Any]]:
        self._assert_safe_paths()
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ContractError("attempt ledger ends with an incomplete record")
        records: list[dict[str, Any]] = []
        previous = _GENESIS
        for sequence, line in enumerate(raw.splitlines(), start=1):
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContractError(f"attempt ledger record {sequence} is invalid") from exc
            if not isinstance(record, dict) or record.get("sequence") != sequence:
                raise ContractError(f"attempt ledger sequence {sequence} is invalid")
            if record.get("previous_record_sha256") != previous:
                raise ContractError(f"attempt ledger predecessor hash at sequence {sequence} is invalid")
            claimed_hash = record.pop("record_sha256", None)
            calculated_hash = sha256_bytes(_canonical(record))
            record["record_sha256"] = claimed_hash
            if claimed_hash != calculated_hash:
                raise ContractError(f"attempt ledger hash at sequence {sequence} is invalid")
            previous = calculated_hash
            records.append(record)
        return records

    def verify(self) -> tuple[dict[str, Any], ...]:
        with _exclusive_lock(self.lock_path):
            return tuple(self._read_unlocked())

    def _append_unlocked(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        self._assert_safe_paths()
        records = self._read_unlocked()
        record: dict[str, Any] = {
            "sequence": len(records) + 1,
            "previous_record_sha256": records[-1]["record_sha256"] if records else _GENESIS,
            **dict(fields),
        }
        record["record_sha256"] = sha256_bytes(_canonical(record))
        line = _canonical(record) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            written = os.write(descriptor, line)
            if written != len(line):
                raise OSError("short append while writing attempt ledger")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return record

    def start_attempt(
        self,
        *,
        campaign_id: str,
        manifest_sha256: str,
        run_id: str,
        nodeid: str,
        attempt: int,
        maximum_attempts: int,
        git_identity: Mapping[str, str],
        started_utc: str,
        owner_decision_sha256: str | None = None,
        environment_sha256: str | None = None,
    ) -> dict[str, Any]:
        identifier_pattern = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
        if (
            not isinstance(run_id, str)
            or re.fullmatch(identifier_pattern, run_id) is None
            or not isinstance(campaign_id, str)
            or re.fullmatch(identifier_pattern, campaign_id) is None
            or not is_exact_nodeid(nodeid)
        ):
            raise ContractError("attempt identity fields are invalid")
        if (
            isinstance(attempt, bool)
            or not isinstance(attempt, int)
            or isinstance(maximum_attempts, bool)
            or not isinstance(maximum_attempts, int)
            or attempt < 1
            or maximum_attempts < 1
            or attempt > maximum_attempts
        ):
            raise ContractError("attempt exceeds the approved maximum")
        if len(manifest_sha256) != 64 or any(character not in "0123456789abcdef" for character in manifest_sha256):
            raise ContractError("manifest SHA-256 must be 64 hexadecimal characters")
        if not isinstance(git_identity, Mapping):
            raise ContractError("ledger Git identity must be an object")
        if {"runner_commit", "runner_tree", "scientific_commit", "scientific_tree"}.issubset(git_identity):
            git_hashes = [git_identity[key] for key in ("runner_commit", "runner_tree", "scientific_commit", "scientific_tree")]
        else:
            git_hashes = [git_identity.get("commit"), git_identity.get("git_tree")]
        if any(
            not isinstance(value, str)
            or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
            for value in git_hashes
        ):
            raise ContractError("ledger Git identity must include full runner and scientific commit/tree IDs")
        for label, digest in (("owner decision", owner_decision_sha256), ("environment", environment_sha256)):
            if digest is not None and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ContractError(f"ledger {label} identity must be a lowercase SHA-256")
        if not isinstance(started_utc, str) or not started_utc:
            raise ContractError("attempt start timestamp is required")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            starts = [
                record
                for record in records
                if record.get("event") == "ATTEMPT_STARTED"
                and record.get("campaign_id") == campaign_id
                and record.get("manifest_sha256") == manifest_sha256
                and record.get("nodeid") == nodeid
            ]
            run_ids = {record.get("run_id") for record in records}
            if run_id in run_ids:
                raise ContractError("run_id has already appeared in the attempt ledger")
            if any(
                record.get("event") == "ATTEMPT_STARTED" and not self._has_terminal(records, record)
                for record in starts
            ):
                raise ContractError("an earlier attempt is still open and must be reconciled")
            if attempt != len(starts) + 1:
                raise ContractError("attempt number is not the next unused attempt for this unit")
            if len(starts) >= maximum_attempts:
                raise ContractError("approved attempt budget is exhausted")
            return self._append_unlocked(
                {
                    "event": "ATTEMPT_STARTED",
                    "campaign_id": campaign_id,
                    "manifest_sha256": manifest_sha256,
                    "run_id": run_id,
                    "nodeid": nodeid,
                    "attempt": attempt,
                    "maximum_attempts": maximum_attempts,
                    "git_identity": dict(git_identity),
                    "owner_decision_sha256": owner_decision_sha256,
                    "environment_sha256": environment_sha256,
                    "started_utc": started_utc,
                    "status": "RUNNING",
                }
            )

    @staticmethod
    def _has_terminal(records: list[dict[str, Any]], start: Mapping[str, Any]) -> bool:
        return any(
            record.get("event") == "ATTEMPT_FINISHED" and record.get("run_id") == start.get("run_id")
            for record in records
        )

    def finish_attempt(
        self,
        *,
        run_id: str,
        status: str,
        finished_utc: str,
        reason: str | None,
        stdout_sha256: str | None,
        stderr_sha256: str | None,
        evidence_sha256: Mapping[str, str],
    ) -> dict[str, Any]:
        if status not in _TERMINAL:
            raise ContractError("attempt terminal status is invalid")
        if not isinstance(finished_utc, str) or not finished_utc:
            raise ContractError("attempt finish timestamp is required")
        if reason is not None and not isinstance(reason, str):
            raise ContractError("attempt finish reason must be text or null")
        for digest in (stdout_sha256, stderr_sha256, *evidence_sha256.values()):
            if digest is not None and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ContractError("ledger artifact identity must be a lowercase SHA-256")
        with _exclusive_lock(self.lock_path):
            records = self._read_unlocked()
            starts = [
                record
                for record in records
                if record.get("event") == "ATTEMPT_STARTED" and record.get("run_id") == run_id
            ]
            if len(starts) != 1:
                raise ContractError("run_id must identify exactly one started attempt")
            if self._has_terminal(records, starts[0]):
                raise ContractError("attempt already has a terminal record")
            return self._append_unlocked(
                {
                    "event": "ATTEMPT_FINISHED",
                    "campaign_id": starts[0]["campaign_id"],
                    "manifest_sha256": starts[0]["manifest_sha256"],
                    "run_id": run_id,
                    "nodeid": starts[0]["nodeid"],
                    "attempt": starts[0]["attempt"],
                    "finished_utc": finished_utc,
                    "status": status,
                    "reason": reason,
                    "stdout_sha256": stdout_sha256,
                    "stderr_sha256": stderr_sha256,
                    "evidence_sha256": dict(evidence_sha256),
                }
            )


def new_run_id() -> str:
    """Create a non-reused identifier; no scientific operation is performed."""
    return uuid.uuid4().hex
