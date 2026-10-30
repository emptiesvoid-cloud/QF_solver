"""Append-only ledger for the prospective nine-case VV3D family remainder.

The ledger reads four pinned predecessor ledgers, charges their attempts and
elapsed time conservatively, and writes only beneath its dedicated evidence
root. It never edits or repairs a predecessor. Controller code must use the
default predecessor bindings; the private injection parameter exists only for
synthetic tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence
import uuid

if __package__:
    from .wp12_vv3d_ledger import (
        RunBinding,
        RunnerCaseBinding,
        _canonical,
        _exclusive_lock,
        _sha256,
        _valid_elapsed,
    )
    from .wp12_vv3d_family_remainder_contract import (
        CAMPAIGN_ID,
        CASE_IDS,
        CASE_NODEIDS,
        PREDECESSOR_LEDGER_BINDINGS,
        SELECTED_DOFS,
        SCOPE_ID,
    )
else:
    from wp12_vv3d_ledger import (
        RunBinding,
        RunnerCaseBinding,
        _canonical,
        _exclusive_lock,
        _sha256,
        _valid_elapsed,
    )
    from wp12_vv3d_family_remainder_contract import (
        CAMPAIGN_ID,
        CASE_IDS,
        CASE_NODEIDS,
        PREDECESSOR_LEDGER_BINDINGS,
        SELECTED_DOFS,
        SCOPE_ID,
    )


MAX_SCOPE_ATTEMPTS = len(CASE_IDS)
MAX_COMBINED_ATTEMPTS = 24
MAX_TOTAL_SECONDS = 28_800
MAX_ATTEMPT_SECONDS = 1_200
RSS_SOFT_LIMIT_MIB = 4_096
ARCHIVE_LIMIT_MIB = 256
GENESIS = "0" * 64
TERMINAL_STATUSES = frozenset(
    {"PASS", "FAIL", "TIMEOUT", "INTERRUPTED", "RESOURCE_LIMIT", "INFRA_ERROR", "INCONCLUSIVE"}
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}\Z")


class FamilyRemainderLedgerError(ValueError):
    """Raised when the family-remainder history, budget or reservation is invalid."""


class FamilyRemainderLedger:
    """Budget-enforcing, hash-chained ledger bound to immutable predecessors."""

    def __init__(
        self,
        path: Path,
        *,
        allowed_root: Path,
        _predecessor_specs: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        self.allowed_root = allowed_root.resolve(strict=True)
        self.path = path.resolve(strict=False)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        specs = PREDECESSOR_LEDGER_BINDINGS if _predecessor_specs is None else _predecessor_specs
        self.predecessor_specs = tuple(dict(spec) for spec in specs)
        if len(self.predecessor_specs) != len(PREDECESSOR_LEDGER_BINDINGS):
            raise FamilyRemainderLedgerError("family remainder requires all four immutable predecessor ledgers")
        self.predecessor_sha256s = {
            str(spec["ledger_scope_id"]): str(spec["sha256"]) for spec in self.predecessor_specs
        }
        self._assert_safe_paths()
        for spec in self.predecessor_specs:
            predecessor_path = Path(str(spec["path"])).resolve(strict=True)
            if predecessor_path == self.path:
                raise FamilyRemainderLedgerError("family remainder ledger must be distinct from every predecessor")
            try:
                if self.path.exists() and os.path.samefile(self.path, predecessor_path):
                    raise FamilyRemainderLedgerError("family remainder ledger aliases an immutable predecessor")
            except OSError as exc:
                raise FamilyRemainderLedgerError("cannot prove ledger/predecessor path separation") from exc
        self._predecessor_totals()

    def _assert_safe_paths(self) -> None:
        for candidate in (self.path, self.lock_path):
            try:
                relative = candidate.relative_to(self.allowed_root)
            except ValueError as exc:
                raise FamilyRemainderLedgerError("family remainder ledger and lock must stay in its evidence root") from exc
            if not relative.parts:
                raise FamilyRemainderLedgerError("family remainder ledger must be a file below its evidence root")
            current = self.allowed_root
            for part in relative.parts:
                current = current / part
                if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
                    raise FamilyRemainderLedgerError("family remainder ledger path contains a symlink or junction")

    @staticmethod
    def _strict_records(raw: bytes, label: str) -> list[dict[str, Any]]:
        if not raw.endswith(b"\n"):
            raise FamilyRemainderLedgerError(f"{label} ledger is incomplete")

        def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result

        records = []
        for number, line in enumerate(raw.splitlines(), 1):
            try:
                record = json.loads(
                    line.decode("utf-8"), object_pairs_hook=unique_pairs,
                    parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
                )
            except (UnicodeDecodeError, ValueError) as exc:
                raise FamilyRemainderLedgerError(f"{label} ledger record {number} is invalid JSON") from exc
            if not isinstance(record, dict):
                raise FamilyRemainderLedgerError(f"{label} ledger record {number} is not an object")
            records.append(record)
        return records

    def _predecessor_totals(self) -> tuple[int, float]:
        attempts_total = 0
        elapsed_values_all: list[float] = []
        for spec in self.predecessor_specs:
            name = str(spec["ledger_scope_id"])
            path = Path(str(spec["path"])).resolve(strict=True)
            expected_sha = str(spec["sha256"])
            if not _SHA256.fullmatch(expected_sha):
                raise FamilyRemainderLedgerError(f"{name} predecessor SHA-256 is invalid")
            first_raw = path.read_bytes()
            if _sha256(first_raw) != expected_sha:
                raise FamilyRemainderLedgerError(f"immutable {name} predecessor SHA-256 changed")
            records = self._strict_records(first_raw, name)
            starts = [record for record in records if record.get("event") == "ATTEMPT_STARTED"]
            finishes = [record for record in records if record.get("event") == "ATTEMPT_FINISHED"]
            if len(starts) != spec.get("attempts") or len(finishes) != spec.get("attempts"):
                raise FamilyRemainderLedgerError(f"{name} predecessor attempt count differs from its pinned record")
            by_run = {record.get("run_id"): record for record in finishes}
            if len(by_run) != len(finishes) or any(not isinstance(record.get("run_id"), str) for record in finishes):
                raise FamilyRemainderLedgerError(f"{name} predecessor has a duplicate or invalid run identifier")
            statuses: list[str] = []
            elapsed_values: list[float] = []
            for start in starts:
                run_id = start.get("run_id")
                finish = by_run.get(run_id)
                if finish is None:
                    raise FamilyRemainderLedgerError(f"{name} predecessor contains an open attempt")
                status = finish.get("status")
                elapsed = finish.get("elapsed_seconds")
                if not isinstance(status, str) or not _valid_elapsed(elapsed):
                    raise FamilyRemainderLedgerError(f"{name} predecessor finish record is invalid")
                if start.get("campaign_id") not in (None, spec["campaign_id"]):
                    raise FamilyRemainderLedgerError(f"{name} predecessor campaign identity changed")
                if start.get("ledger_scope_id") not in (None, name):
                    raise FamilyRemainderLedgerError(f"{name} predecessor scope identity changed")
                if finish.get("campaign_id") not in (None, spec["campaign_id"]):
                    raise FamilyRemainderLedgerError(f"{name} predecessor finish campaign identity changed")
                if finish.get("ledger_scope_id") not in (None, name):
                    raise FamilyRemainderLedgerError(f"{name} predecessor finish scope identity changed")
                statuses.append(status)
                elapsed_values.append(float(elapsed))
            if tuple(statuses) != tuple(spec.get("statuses", ())):
                raise FamilyRemainderLedgerError(f"{name} predecessor statuses differ from the frozen history")
            expected_elapsed = tuple(spec.get("elapsed_seconds_by_attempt", ()))
            if len(expected_elapsed) != len(elapsed_values) or any(
                observed != expected for observed, expected in zip(elapsed_values, expected_elapsed, strict=True)
            ):
                raise FamilyRemainderLedgerError(f"{name} predecessor measured times differ from the frozen history")
            if _sha256(path.read_bytes()) != expected_sha:
                raise FamilyRemainderLedgerError(f"{name} predecessor changed while it was being checked")
            attempts_total += len(starts)
            elapsed_values_all.extend(elapsed_values)
        elapsed_total = sum(elapsed_values_all)
        if attempts_total != 7 or elapsed_total != 4069.326357999933:
            raise FamilyRemainderLedgerError("conservative predecessor accounting differs from the frozen four-ledger total")
        if attempts_total + MAX_SCOPE_ATTEMPTS > MAX_COMBINED_ATTEMPTS:
            raise FamilyRemainderLedgerError("nine-case scope exceeds the combined attempt ceiling")
        if elapsed_total + MAX_SCOPE_ATTEMPTS * MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
            raise FamilyRemainderLedgerError("nine-case scope cannot fit the cumulative seconds ceiling")
        return attempts_total, elapsed_total

    def predecessor_campaign_lock_paths(self) -> tuple[Path, ...]:
        """Return the predecessor runners' campaign locks in stable acquisition order.

        Both historical TET4 diagnostics execute under R2's campaign lock, so
        their ledger files deliberately resolve to that same lock. The first
        two ledgers use their own campaign evidence roots.
        """
        by_scope = {str(spec["ledger_scope_id"]): spec for spec in self.predecessor_specs}
        required_scopes = {str(spec["ledger_scope_id"]) for spec in PREDECESSOR_LEDGER_BINDINGS}
        if set(by_scope) != required_scopes or len(self.predecessor_specs) != len(by_scope):
            raise FamilyRemainderLedgerError("campaign locks require the exact four pinned predecessor scopes")
        r2_scope = "wp12_vv3d_recovery_r2"
        r2_path = Path(str(by_scope[r2_scope]["path"])).resolve(strict=True)
        roots = {
            "wp12_vv3d_adaptive": Path(str(by_scope["wp12_vv3d_adaptive"]["path"])).resolve(strict=True).parent,
            r2_scope: r2_path.parent,
            "wp12_vv3d_tet4_l3_diagnostic": r2_path.parent,
            "wp12_vv3d_tet4_l3_optimized_diagnostic": r2_path.parent,
        }
        paths: set[Path] = set()
        for scope_id in required_scopes:
            root = roots[scope_id].resolve(strict=True)
            lock_path = root / "locks" / "vv3d-campaign-exclusive.lock"
            if (root == self.allowed_root or root == self.path.parent
                    or (root / "locks").is_symlink() or lock_path.is_symlink()):
                raise FamilyRemainderLedgerError(f"unsafe {scope_id} campaign-lock path")
            paths.add(lock_path.resolve(strict=False))
        return tuple(sorted(paths, key=lambda path: str(path).casefold()))

    @staticmethod
    def _write_reservation_receipt(receipt_path: Path, raw: bytes, checksum_path: Path, checksum_raw: bytes) -> None:
        with receipt_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        with checksum_path.open("xb") as stream:
            stream.write(checksum_raw)
            stream.flush()
            os.fsync(stream.fileno())

    def _read_unlocked(self) -> list[dict[str, Any]]:
        self._assert_safe_paths()
        self._predecessor_totals()
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise FamilyRemainderLedgerError("family remainder ledger ends with an incomplete record")
        records: list[dict[str, Any]] = []
        previous = GENESIS
        for sequence, line in enumerate(raw.splitlines(), 1):
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise FamilyRemainderLedgerError(f"family remainder record {sequence} is invalid JSON") from exc
            if (
                not isinstance(record, dict)
                or type(record.get("sequence")) is not int
                or record.get("sequence") != sequence
                or record.get("previous_record_sha256") != previous
            ):
                raise FamilyRemainderLedgerError(f"family remainder hash chain is invalid at record {sequence}")
            claimed = record.pop("record_sha256", None)
            calculated = _sha256(_canonical(record))
            record["record_sha256"] = claimed
            if claimed != calculated:
                raise FamilyRemainderLedgerError(f"family remainder record hash mismatch at sequence {sequence}")
            if (
                record.get("campaign_id") != CAMPAIGN_ID
                or record.get("ledger_scope_id") != SCOPE_ID
                or record.get("predecessor_ledger_sha256s") != self.predecessor_sha256s
            ):
                raise FamilyRemainderLedgerError("family remainder record has a foreign scope or predecessor identity")
            previous = calculated
            records.append(record)
        baseline_attempts, baseline_elapsed = self._predecessor_totals()
        self._validate(records, baseline_attempts=baseline_attempts, baseline_elapsed=baseline_elapsed)
        return records

    @staticmethod
    def _validate(
        records: list[dict[str, Any]], *, baseline_attempts: int, baseline_elapsed: float,
    ) -> None:
        seen_cases: list[str] = []
        active: dict[str, dict[str, Any]] = {}
        stopped = False
        campaign_binding: tuple[Any, ...] | None = None
        elapsed_total = 0.0
        seen_preflights: set[str] = set()
        for record in records:
            event = record.get("event")
            run_id = record.get("run_id")
            if event == "ATTEMPT_STARTED":
                case_id = record.get("case_id")
                expected_attempt = len(seen_cases) + 1
                if (
                    stopped or active or case_id not in CASE_IDS or case_id in seen_cases
                    or case_id != CASE_IDS[len(seen_cases)]
                    or not isinstance(run_id, str) or not run_id or run_id in active
                    or record.get("attempt") != expected_attempt
                    or record.get("timeout_seconds") != MAX_ATTEMPT_SECONDS
                    or record.get("reserved_seconds") != MAX_ATTEMPT_SECONDS
                    or record.get("rss_soft_limit_mib") != RSS_SOFT_LIMIT_MIB
                    or record.get("selected_dofs") != SELECTED_DOFS.get(case_id)
                    or record.get("nodeid") != CASE_NODEIDS[CASE_IDS.index(case_id)]
                    or record.get("max_attempts") != 1
                    or record.get("campaign_attempt_number") != baseline_attempts + expected_attempt
                    or record.get("combined_seconds_reserved_after")
                    != baseline_elapsed + elapsed_total + MAX_ATTEMPT_SECONDS
                ):
                    raise FamilyRemainderLedgerError("attempt start is duplicate, out of order, over budget, or after STOP")
                binding = tuple(record.get(key) for key in (
                    "contract_sha256", "decision_id", "decision_sha256", "manifest_sha256", "preflight_sha256",
                ))
                if (
                    not isinstance(binding[0], str) or not _SHA256.fullmatch(binding[0])
                    or not isinstance(binding[1], str) or not _IDENTIFIER.fullmatch(binding[1])
                    or any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in binding[2:])
                ):
                    raise FamilyRemainderLedgerError("attempt reservation lacks contract/decision/manifest/preflight hashes")
                if campaign_binding is not None and binding[:3] != campaign_binding:
                    raise FamilyRemainderLedgerError("nine-case attempts do not share one frozen contract and decision")
                if binding[4] in seen_preflights:
                    raise FamilyRemainderLedgerError("collect-only preflight receipt cannot be reused")
                if record.get("predecessor_attempts_before") != baseline_attempts or record.get(
                    "predecessor_elapsed_seconds_before"
                ) != baseline_elapsed:
                    raise FamilyRemainderLedgerError("attempt start changed its immutable predecessor accounting")
                campaign_binding = binding[:3]
                seen_preflights.add(binding[4])
                seen_cases.append(case_id)
                active[run_id] = record
            elif event == "ATTEMPT_FINISHED":
                start = active.pop(run_id, None)
                measured = record.get("elapsed_seconds")
                status = record.get("status")
                if (
                    start is None or not _valid_elapsed(measured)
                    or not isinstance(status, str) or status not in TERMINAL_STATUSES
                    or record.get("case_id") != start.get("case_id")
                    or record.get("monitored_limit_seconds") != MAX_ATTEMPT_SECONDS
                ):
                    raise FamilyRemainderLedgerError("finish event does not match one valid reservation")
                expected_stops = []
                if measured > MAX_ATTEMPT_SECONDS:
                    expected_stops.append("PER_ATTEMPT_LIMIT_OVERRUN")
                if baseline_elapsed + elapsed_total + measured > MAX_TOTAL_SECONDS:
                    expected_stops.append("GLOBAL_BUDGET_OVERRUN")
                if record.get("stop_reasons") != expected_stops:
                    raise FamilyRemainderLedgerError("recorded STOP reasons differ from measured resource usage")
                if expected_stops and status != "INFRA_ERROR":
                    raise FamilyRemainderLedgerError("resource budget overrun must be recorded as INFRA_ERROR")
                elapsed_total += float(measured)
                if (
                    record.get("combined_attempts_used_after") != baseline_attempts + len(seen_cases)
                    or record.get("combined_elapsed_seconds_after") != baseline_elapsed + elapsed_total
                ):
                    raise FamilyRemainderLedgerError("finish cumulative totals differ from predecessor-linked accounting")
                stopped = status != "PASS" or bool(expected_stops)
            else:
                raise FamilyRemainderLedgerError("family remainder ledger contains an unsupported event")
        if (
            len(seen_cases) > MAX_SCOPE_ATTEMPTS
            or baseline_attempts + len(seen_cases) > MAX_COMBINED_ATTEMPTS
            or baseline_elapsed + elapsed_total > MAX_TOTAL_SECONDS
        ):
            raise FamilyRemainderLedgerError("family remainder attempt or cumulative time cap exceeded")

    def _append_unlocked(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        records = self._read_unlocked()
        body = {
            "sequence": len(records) + 1,
            "previous_record_sha256": records[-1]["record_sha256"] if records else GENESIS,
            "campaign_id": CAMPAIGN_ID,
            "ledger_scope_id": SCOPE_ID,
            "predecessor_ledger_sha256s": self.predecessor_sha256s,
            **dict(fields),
        }
        body["record_sha256"] = _sha256(_canonical(body))
        raw = _canonical(body) + b"\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            offset = 0
            while offset < len(raw):
                offset += os.write(descriptor, raw[offset:])
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return body

    def start_runner_attempt(
        self,
        *,
        binding: RunBinding,
        case: RunnerCaseBinding,
        receipt_path: Path,
    ) -> dict[str, Any]:
        """Reserve one exact case and write a durable reservation receipt."""
        run = case.as_record()
        artifacts = binding.as_record()
        case_id = run["case_id"]
        if (
            case_id not in CASE_IDS
            or run["nodeid"] != CASE_NODEIDS[CASE_IDS.index(case_id)]
            or run["selected_dofs"] != SELECTED_DOFS[case_id]
            or run["timeout_seconds"] != MAX_ATTEMPT_SECONDS
            or run["rss_soft_limit_mib"] != RSS_SOFT_LIMIT_MIB
            or run["archive_size_limit_mib"] != ARCHIVE_LIMIT_MIB
            or any(artifacts.get(key) is not None for key in (
                "transition_receipt_sha256", "transition_source_case_id", "transition_destination_case_id",
            ))
        ):
            raise FamilyRemainderLedgerError("case binding is outside the exact nine-case envelope")
        receipt_path = receipt_path.resolve(strict=False)
        try:
            receipt_path.relative_to(self.allowed_root)
        except ValueError as exc:
            raise FamilyRemainderLedgerError("reservation receipt must be inside the dedicated evidence root") from exc
        if receipt_path.exists():
            raise FamilyRemainderLedgerError("reservation receipt already exists; refusing overwrite")
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        checksum_path = receipt_path.with_suffix(receipt_path.suffix + ".sha256.json")
        if checksum_path.exists():
            raise FamilyRemainderLedgerError("reservation checksum already exists; refusing overwrite")
        run_id = run.get("reservation_id") or uuid.uuid4().hex
        if not isinstance(run_id, str) or not _IDENTIFIER.fullmatch(run_id):
            raise FamilyRemainderLedgerError("reservation ID is invalid")

        with _exclusive_lock(self.lock_path):
            baseline_attempts, baseline_elapsed = self._predecessor_totals()
            records = self._read_unlocked()
            starts = [record for record in records if record["event"] == "ATTEMPT_STARTED"]
            finishes = {record["run_id"]: record for record in records if record["event"] == "ATTEMPT_FINISHED"}
            if any(record["run_id"] not in finishes for record in starts):
                raise FamilyRemainderLedgerError("an open reservation blocks further work; recovery is not implicit")
            if any(finishes[record["run_id"]]["status"] != "PASS" for record in starts):
                raise FamilyRemainderLedgerError("a non-PASS result permanently stops the family remainder scope")
            if any(record.get("case_id") == case_id for record in starts):
                raise FamilyRemainderLedgerError("case already consumed its unique attempt")
            if len(starts) >= MAX_SCOPE_ATTEMPTS or baseline_attempts + len(starts) >= MAX_COMBINED_ATTEMPTS:
                raise FamilyRemainderLedgerError("scope or combined attempt budget is exhausted")
            spent = sum(float(record["elapsed_seconds"]) for record in finishes.values())
            if baseline_elapsed + spent + MAX_ATTEMPT_SECONDS > MAX_TOTAL_SECONDS:
                raise FamilyRemainderLedgerError("combined budget cannot reserve a full 1,200-second attempt")
            if any(record.get("run_id") == run_id for record in records):
                raise FamilyRemainderLedgerError("reservation ID is already used")
            expected_case = CASE_IDS[len(starts)]
            if case_id != expected_case:
                raise FamilyRemainderLedgerError("cases must run in the frozen family/level order")
            reservation_started_monotonic = time.monotonic()
            start = self._append_unlocked({
                "event": "ATTEMPT_STARTED",
                "run_id": run_id,
                "attempt": len(starts) + 1,
                "case_id": case_id,
                **artifacts,
                **run,
                "reserved_seconds": MAX_ATTEMPT_SECONDS,
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                "predecessor_attempts_before": baseline_attempts,
                "predecessor_elapsed_seconds_before": baseline_elapsed,
                "campaign_attempt_number": baseline_attempts + len(starts) + 1,
                "max_attempts": 1,
                "combined_seconds_reserved_after": baseline_elapsed + spent + MAX_ATTEMPT_SECONDS,
                "started_utc": datetime.now(timezone.utc).isoformat(),
            })
            ledger_sha = _sha256(self.path.read_bytes())
            receipt = {
                "schema": "qf-wp12-vv3d-runner-reservation-v1",
                "status": "RESERVED",
                "campaign_id": CAMPAIGN_ID,
                "case_id": case_id,
                "nodeid": run["nodeid"],
                "manifest_sha256": artifacts["manifest_sha256"],
                "preflight_receipt_sha256": artifacts["preflight_sha256"],
                "decision_id": artifacts["decision_id"],
                "decision_sha256": artifacts["decision_sha256"],
                "contract_sha256": artifacts["contract_sha256"],
                "scientific_fingerprint": run["source_fingerprint"],
                "controller_fingerprint": run["controller_fingerprint"],
                "authorization_id": run["authorization_id"],
                "attempt_id": run["attempt_id"],
                "reservation_id": run_id,
                "selected_dofs": run["selected_dofs"],
                "timeout_seconds": run["timeout_seconds"],
                "rss_soft_limit_mib": run["rss_soft_limit_mib"],
                "archive_size_limit_mib": run["archive_size_limit_mib"],
                "ledger_scope_id": SCOPE_ID,
                "ledger_path": str(self.path),
                "ledger_sha256_after_reservation": ledger_sha,
                "attempt_number": 1,
                "campaign_attempt_number": baseline_attempts + len(starts) + 1,
                "max_attempts": 1,
                "attempt_reserved": True,
                "combined_attempts_used_after": baseline_attempts + len(starts) + 1,
                "campaign_attempts_used_after": baseline_attempts + len(starts) + 1,
                "campaign_seconds_reserved_after": start["combined_seconds_reserved_after"],
                "combined_seconds_reserved_after": start["combined_seconds_reserved_after"],
                "predecessor_ledger_sha256s": self.predecessor_sha256s,
                "evidence_root": run["evidence_root"],
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            raw = _canonical(receipt) + b"\n"
            checksum_raw = _canonical({"schema": "qf-wp12-vv3d-runner-reservation-sha256-v1",
                                       "sha256": _sha256(raw)}) + b"\n"
            try:
                self._write_reservation_receipt(receipt_path, raw, checksum_path, checksum_raw)
            except Exception as exc:
                elapsed_seconds = max(0.0, time.monotonic() - reservation_started_monotonic)
                self._append_unlocked({
                    "event": "ATTEMPT_FINISHED",
                    "run_id": run_id,
                    "case_id": case_id,
                    "status": "INFRA_ERROR",
                    "elapsed_seconds": elapsed_seconds,
                    "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                    "stop_reasons": [],
                    "recovered_after_crash": False,
                    "combined_attempts_used_after": baseline_attempts + len(starts) + 1,
                    "campaign_attempts_used_after": baseline_attempts + len(starts) + 1,
                    "combined_elapsed_seconds_after": baseline_elapsed + spent + elapsed_seconds,
                    "finished_utc": datetime.now(timezone.utc).isoformat(),
                })
                raise FamilyRemainderLedgerError(
                    f"reservation receipt setup failed after ATTEMPT_STARTED; attempt closed as INFRA_ERROR: {exc}"
                ) from exc
            receipt["receipt_sha256"] = _sha256(raw)
            return receipt

    def finish_runner_attempt(self, *, run_id: str, status: str, elapsed_seconds: float) -> dict[str, Any]:
        """Close one reservation and record STOP on every non-PASS outcome."""
        if status not in TERMINAL_STATUSES or not _valid_elapsed(elapsed_seconds):
            raise FamilyRemainderLedgerError("terminal status or measured elapsed time is invalid")
        with _exclusive_lock(self.lock_path):
            baseline_attempts, baseline_elapsed = self._predecessor_totals()
            records = self._read_unlocked()
            starts = [record for record in records if record.get("event") == "ATTEMPT_STARTED"]
            finishes = {record.get("run_id"): record for record in records if record.get("event") == "ATTEMPT_FINISHED"}
            start = next((record for record in starts if record.get("run_id") == run_id), None)
            if (
                start is None or run_id in finishes
                or any(record.get("run_id") not in finishes and record.get("run_id") != run_id for record in starts)
            ):
                raise FamilyRemainderLedgerError("finish must close exactly one open reservation")
            prior_elapsed = sum(float(record["elapsed_seconds"]) for record in finishes.values())
            stop_reasons = []
            if elapsed_seconds > MAX_ATTEMPT_SECONDS:
                stop_reasons.append("PER_ATTEMPT_LIMIT_OVERRUN")
            if baseline_elapsed + prior_elapsed + elapsed_seconds > MAX_TOTAL_SECONDS:
                stop_reasons.append("GLOBAL_BUDGET_OVERRUN")
            terminal_status = "INFRA_ERROR" if stop_reasons else status
            return self._append_unlocked({
                "event": "ATTEMPT_FINISHED",
                "run_id": run_id,
                "case_id": start["case_id"],
                "status": terminal_status,
                "elapsed_seconds": float(elapsed_seconds),
                "monitored_limit_seconds": MAX_ATTEMPT_SECONDS,
                "stop_reasons": stop_reasons,
                "recovered_after_crash": False,
                "combined_attempts_used_after": baseline_attempts + len(starts),
                "combined_elapsed_seconds_after": baseline_elapsed + prior_elapsed + float(elapsed_seconds),
                "finished_utc": datetime.now(timezone.utc).isoformat(),
            })

    def verify(self) -> list[dict[str, Any]]:
        """Validate the new hash chain and all four immutable predecessor bindings."""
        with _exclusive_lock(self.lock_path):
            return self._read_unlocked()

    def summary(self) -> dict[str, int | float | bool]:
        with _exclusive_lock(self.lock_path):
            predecessor_attempts, predecessor_elapsed = self._predecessor_totals()
            records = self._read_unlocked()
            starts = [record for record in records if record.get("event") == "ATTEMPT_STARTED"]
            finishes = {record.get("run_id"): record for record in records if record.get("event") == "ATTEMPT_FINISHED"}
            elapsed = sum(float(record["elapsed_seconds"]) for record in finishes.values())
            active = any(record.get("run_id") not in finishes for record in starts)
            return {
                "predecessor_attempts_charged": predecessor_attempts,
                "attempts_used_scope": len(starts),
                "attempts_remaining_scope": MAX_SCOPE_ATTEMPTS - len(starts),
                "combined_attempts_used": predecessor_attempts + len(starts),
                "combined_attempts_remaining": MAX_COMBINED_ATTEMPTS - predecessor_attempts - len(starts),
                "predecessor_elapsed_seconds_charged": predecessor_elapsed,
                "elapsed_seconds_scope": elapsed,
                "combined_elapsed_seconds": predecessor_elapsed + elapsed,
                "seconds_remaining_after_reservation": MAX_TOTAL_SECONDS - predecessor_elapsed - elapsed
                - (MAX_ATTEMPT_SECONDS if active else 0),
                "attempt_open": active,
                "stopped": any(
                    finishes.get(record.get("run_id"), {}).get("status") != "PASS"
                    for record in starts if record.get("run_id") in finishes
                ),
            }
