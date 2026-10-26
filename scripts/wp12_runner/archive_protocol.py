"""One-way hand-off to an administrator-owned WP12 evidence archive."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import time
import uuid
from typing import Any, Mapping

from .contracts import ContractError, safe_repo_relative_path, sha256_bytes, sha256_file
from .evidence import verify_receipt


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HEX_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _ordinary_directory(path: Path, label: str) -> Path:
    lexical = path.absolute()
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current = current / part
        if not current.exists():
            continue
        if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
            raise ContractError(f"{label} contains a reparse-point component")
    candidate = lexical.resolve(strict=True)
    if not candidate.is_dir():
        raise ContractError(f"{label} must be an existing ordinary directory")
    return candidate


def _assert_no_reparse_components(base: Path, candidate: Path, label: str) -> None:
    try:
        relative = candidate.absolute().relative_to(base.absolute())
    except ValueError as exc:
        raise ContractError(f"{label} escapes its configured root") from exc
    current = base.absolute()
    for part in relative.parts:
        current = current / part
        if current.exists() and (current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)())):
            raise ContractError(f"{label} contains a reparse point")


def _atomic_create_json(path: Path, payload: Mapping[str, Any]) -> tuple[Path, str]:
    raw = (json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    temporary_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return path, sha256_bytes(raw)


def reservation_key(*, campaign_id: str, manifest_sha256: str, nodeid: str) -> str:
    """Stable one-shot key for a campaign/manifest/nodeid, independent of run_id."""
    from .contracts import is_exact_nodeid

    if not _SAFE_ID.fullmatch(campaign_id) or not _HEX_SHA256.fullmatch(manifest_sha256) or not is_exact_nodeid(nodeid):
        raise ContractError("attempt reservation identity is invalid")
    payload = f"{campaign_id}\n{manifest_sha256}\n{nodeid}".encode("utf-8")
    return sha256_bytes(payload)


def create_attempt_reservation_request(
    *,
    request_root: Path,
    campaign_id: str,
    decision_id: str,
    unit_id: str,
    run_id: str,
    nodeid: str,
    destination: str,
    manifest_sha256: str,
    owner_decision_sha256: str,
    identities: Mapping[str, str],
) -> tuple[Path, str, str, str]:
    """Request SYSTEM-owned, create-once consumption of the approved attempt."""
    from .contracts import is_exact_nodeid

    if (
        not _SAFE_ID.fullmatch(campaign_id)
        or not _SAFE_ID.fullmatch(decision_id)
        or not _SAFE_ID.fullmatch(unit_id)
        or not _SAFE_ID.fullmatch(run_id)
        or not is_exact_nodeid(nodeid)
        or not safe_repo_relative_path(destination)
    ):
        raise ContractError("attempt reservation campaign, run, or nodeid is invalid")
    if not _HEX_SHA256.fullmatch(manifest_sha256) or not _HEX_SHA256.fullmatch(owner_decision_sha256):
        raise ContractError("attempt reservation requires exact manifest and Owner-decision hashes")
    required = {"scientific_commit", "scientific_tree", "runner_commit", "runner_tree"}
    if not isinstance(identities, Mapping) or not required.issubset(identities):
        raise ContractError("attempt reservation must identify both scientific and runner Git objects")
    for value in identities.values():
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40}", value):
            raise ContractError("attempt reservation Git identities must be full object IDs")
    root = _ordinary_directory(request_root, "archive request root")
    key = reservation_key(campaign_id=campaign_id, manifest_sha256=manifest_sha256, nodeid=nodeid)
    request_id = str(uuid.uuid4())
    payload = {
        "schema": "qf-wp12-attempt-reservation-request-v1",
        "request_id": request_id,
        "reservation_key": key,
        "campaign_id": campaign_id,
        "decision_id": decision_id,
        "unit_id": unit_id,
        "run_id": run_id,
        "nodeid": nodeid,
        "destination": destination,
        "manifest_sha256": manifest_sha256,
        "owner_decision_sha256": owner_decision_sha256,
        "identities": dict(identities),
        "attempt": 1,
        "maximum_attempts": 1,
    }
    path, digest = _atomic_create_json(root / f"{request_id}.reserve.json", payload)
    return path, digest, request_id, key


def wait_for_attempt_reservation_acknowledgement(
    *,
    archive_root: Path,
    request_id: str,
    request_sha256: str,
    reservation_key_value: str,
    decision_id: str,
    unit_id: str,
    destination: str,
    owner_decision_sha256: str,
    timeout_seconds: int,
    poll_interval_seconds: float = 0.25,
) -> dict[str, Any]:
    """Require a matching acknowledgement from the protected SYSTEM ledger."""
    if (
        not _SAFE_ID.fullmatch(request_id)
        or not _HEX_SHA256.fullmatch(request_sha256)
        or not _HEX_SHA256.fullmatch(reservation_key_value)
    ):
        raise ContractError("attempt reservation acknowledgement identity is malformed")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ContractError("attempt reservation acknowledgement timeout must be positive")
    root = _ordinary_directory(archive_root, "protected archive root")
    ack_path = root / "_wp12_ledger" / "reservation-acks" / f"{request_id}.json"
    _assert_no_reparse_components(root, ack_path, "attempt reservation acknowledgement path")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ack_path.exists() or ack_path.is_symlink() or bool(getattr(ack_path, "is_junction", lambda: False)()):
            break
        time.sleep(poll_interval_seconds)
    if not ack_path.is_file() or ack_path.is_symlink() or bool(getattr(ack_path, "is_junction", lambda: False)()):
        raise ContractError("protected attempt reservation acknowledgement was not received")
    try:
        ack = json.loads(ack_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("protected attempt reservation acknowledgement is unreadable") from exc
    if not isinstance(ack, Mapping) or any(
        ack.get(key) != value
        for key, value in {
            "schema": "qf-wp12-attempt-reservation-ack-v1",
            "request_id": request_id,
            "request_sha256": request_sha256,
            "reservation_key": reservation_key_value,
            "decision_id": decision_id,
            "unit_id": unit_id,
            "destination": destination,
            "owner_decision_sha256": owner_decision_sha256,
            "status": "RESERVED",
        }.items()
    ):
        raise ContractError("protected ledger refused or mismatched the attempt reservation")
    return {"acknowledgement_path": str(ack_path), **dict(ack)}


def create_archive_request(
    *,
    request_root: Path,
    campaign_id: str,
    decision_id: str,
    unit_id: str,
    run_id: str,
    nodeid: str,
    destination: str,
    manifest_sha256: str,
    owner_decision_sha256: str,
    reservation_key_value: str,
    runner_status_claim: str,
    run_directory: Path,
    receipt_sha256: str,
) -> tuple[Path, str]:
    """Write a create-new request; it cannot point outside the evidence run."""
    if (
        not _SAFE_ID.fullmatch(campaign_id)
        or not _SAFE_ID.fullmatch(decision_id)
        or not _SAFE_ID.fullmatch(unit_id)
        or not _SAFE_ID.fullmatch(run_id)
        or not safe_repo_relative_path(destination)
    ):
        raise ContractError("archive request campaign/run identifiers are unsafe")
    from .contracts import is_exact_nodeid

    if not is_exact_nodeid(nodeid):
        raise ContractError("archive request nodeid is not an exact test nodeid")
    if not _HEX_SHA256.fullmatch(manifest_sha256) or not _HEX_SHA256.fullmatch(owner_decision_sha256):
        raise ContractError("archive request manifest and Owner decision hashes must be SHA-256")
    expected_reservation_key = reservation_key(campaign_id=campaign_id, manifest_sha256=manifest_sha256, nodeid=nodeid)
    if reservation_key_value != expected_reservation_key:
        raise ContractError("archive request does not match the consumed one-shot attempt reservation")
    if runner_status_claim not in {
        "PASS",
        "FAIL",
        "INCONCLUSIVE",
        "TIMEOUT",
        "RESOURCE_LIMIT",
        "INTERRUPTED",
        "INFRA_ERROR",
    }:
        raise ContractError("archive request status is not a terminal result")
    request_directory = _ordinary_directory(request_root, "archive request root")
    source_directory = _ordinary_directory(run_directory, "archive source")
    if verify_receipt(source_directory):
        raise ContractError("archive source receipt failed integrity verification")
    actual_receipt_sha256 = sha256_file(source_directory / "receipt.json")
    if actual_receipt_sha256 != receipt_sha256:
        raise ContractError("archive request receipt SHA-256 differs from the verified run receipt")
    try:
        receipt = json.loads((source_directory / "receipt.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("archive receipt metadata is unreadable") from exc
    receipt_metadata = receipt.get("metadata") if isinstance(receipt, Mapping) else None
    if not isinstance(receipt_metadata, Mapping) or any(
        receipt_metadata.get(key) != value
        for key, value in {
            "campaign_id": campaign_id,
            "decision_id": decision_id,
            "unit_id": unit_id,
            "run_id": run_id,
            "nodeid": nodeid,
            "destination": destination,
            "reservation_key": reservation_key_value,
            "manifest_sha256": manifest_sha256,
            "owner_decision_sha256": owner_decision_sha256,
            "scientific_status": "INCONCLUSIVE",
            "runner_process_classification": runner_status_claim,
        }.items()
    ):
        raise ContractError("archive receipt metadata does not match the consumed attempt and result")
    payload: dict[str, Any] = {
        "schema": "qf-wp12-administrator-archive-request-v1",
        "campaign_id": campaign_id,
        "decision_id": decision_id,
        "unit_id": unit_id,
        "run_id": run_id,
        "nodeid": nodeid,
        "destination": destination,
        "manifest_sha256": manifest_sha256,
        "owner_decision_sha256": owner_decision_sha256,
        "reservation_key": reservation_key_value,
        "runner_status_claim": runner_status_claim,
        "claim_assurance": "UNATTESTED_RUNNER_OUTPUT",
        "source_run_directory": str(source_directory),
        "receipt_sha256": actual_receipt_sha256,
    }
    raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    request_path = request_directory / f"{campaign_id}-{run_id}.request.json"
    temporary_path = request_directory / f".{campaign_id}-{run_id}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard-link publishes the fully written request atomically and fails
        # if any concurrent actor already claimed this campaign/run identity.
        os.link(temporary_path, request_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return request_path, sha256_bytes(raw)


def wait_for_archive_acknowledgement(
    *,
    archive_root: Path,
    campaign_id: str,
    decision_id: str,
    unit_id: str,
    run_id: str,
    destination: str,
    manifest_sha256: str,
    request_sha256: str,
    receipt_sha256: str,
    reservation_key_value: str,
    nodeid: str,
    owner_decision_sha256: str,
    runner_status_claim: str,
    timeout_seconds: int,
    poll_interval_seconds: float = 0.25,
) -> dict[str, Any]:
    """Accept only an acknowledgement whose protected copy re-verifies."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ContractError("archive acknowledgement timeout must be a positive integer")
    root = archive_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink() or bool(getattr(root, "is_junction", lambda: False)()):
        raise ContractError("sealed archive root must be an existing ordinary directory")
    ack_path = root / campaign_id / f"{run_id}.archive-ack.json"
    _assert_no_reparse_components(root, ack_path, "archive acknowledgement path")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if ack_path.exists() or ack_path.is_symlink() or bool(getattr(ack_path, "is_junction", lambda: False)()):
            break
        time.sleep(poll_interval_seconds)
    if not ack_path.is_file() or ack_path.is_symlink() or bool(getattr(ack_path, "is_junction", lambda: False)()):
        raise ContractError("administrator archive acknowledgement was not received before timeout")
    try:
        ack = json.loads(ack_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("administrator archive acknowledgement is unreadable") from exc
    expected = {
        "schema": "qf-wp12-administrator-archive-ack-v1",
        "status": "ARCHIVED_BYTES_ONLY",
        "campaign_id": campaign_id,
        "decision_id": decision_id,
        "unit_id": unit_id,
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
        "request_sha256": request_sha256,
        "receipt_sha256": receipt_sha256,
        "reservation_key": reservation_key_value,
        "nodeid": nodeid,
        "destination": destination,
        "owner_decision_sha256": owner_decision_sha256,
        "runner_status_claim_unattested": runner_status_claim,
        "archive_relative_path": f"{campaign_id}/{run_id}",
        "archive_assurance": "BYTE_INTEGRITY_ONLY_PROCESS_EXECUTION_NOT_ATTESTED",
        "process_execution_attested": False,
        "scientific_status_attested": False,
    }
    if not isinstance(ack, Mapping) or any(ack.get(key) != value for key, value in expected.items()):
        raise ContractError("administrator archive acknowledgement does not match the requested run")
    archived_run = root / campaign_id / run_id
    _assert_no_reparse_components(root, archived_run, "archived run path")
    try:
        if archived_run.resolve(strict=True).parent != (root / campaign_id).resolve(strict=True):
            raise ContractError("archived run resolves outside its campaign directory")
    except OSError as exc:
        raise ContractError("archived run directory is absent") from exc
    if archived_run.is_symlink() or bool(getattr(archived_run, "is_junction", lambda: False)()):
        raise ContractError("archived run directory is a reparse point")
    receipt_path = archived_run / "receipt.json"
    if not receipt_path.is_file() or sha256_file(receipt_path) != receipt_sha256:
        raise ContractError("archived receipt SHA-256 does not match the submitted evidence")
    try:
        archived_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("archived receipt metadata is unreadable") from exc
    metadata = archived_receipt.get("metadata") if isinstance(archived_receipt, Mapping) else None
    if not isinstance(metadata, Mapping) or any(
        metadata.get(key) != value
        for key, value in {
            "campaign_id": campaign_id,
            "run_id": run_id,
            "nodeid": nodeid,
            "reservation_key": reservation_key_value,
            "manifest_sha256": manifest_sha256,
            "owner_decision_sha256": owner_decision_sha256,
        }.items()
    ):
        raise ContractError("archived receipt identity differs from the requested attempt")
    if sha256_file(receipt_path) != ack.get("archived_receipt_sha256") or verify_receipt(archived_run):
        raise ContractError("administrator archived evidence failed receipt verification")
    return {"acknowledgement_path": str(ack_path), "archive_path": str(archived_run), **dict(ack)}
