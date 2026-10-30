"""Exclusive WP12 evidence paths, append-only journals, and hash receipts."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import re
import os
import secrets
from datetime import datetime, timezone
import uuid
from typing import Any, Mapping

from .contracts import ContractError, safe_repo_relative_path, sha256_bytes, sha256_file


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RECEIPT = "receipt.json"
_RECEIPT_HASH = "receipt.sha256"


def _has_symlink_component(base: Path, target: Path) -> bool:
    try:
        relative = target.relative_to(base)
    except ValueError:
        return True
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
            return True
    return False


def reserve_pilot_evidence_directory(
    evidence_root: Path,
    campaign_id: str,
    run_id: str,
    manifest_sha256: str,
) -> Path:
    """Atomically reserve a new campaign/run directory before the attempt ledger.

    The marker binds this exclusive directory to the exact manifest and run ID.
    It is a race/collision control, not an OS sandbox or an authenticated Owner
    decision; those checks are performed by the caller and Windows ACL policy.
    """
    if not _IDENTIFIER.fullmatch(campaign_id) or not _IDENTIFIER.fullmatch(run_id):
        raise ContractError("campaign_id and run_id must be safe single path components")
    if len(manifest_sha256) != 64 or any(character not in "0123456789abcdef" for character in manifest_sha256):
        raise ContractError("manifest SHA-256 must be a full lowercase digest")
    root = evidence_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink() or bool(getattr(root, "is_junction", lambda: False)()):
        raise ContractError("evidence root must be an existing ordinary directory")
    campaign_root = root / campaign_id
    destination = campaign_root / run_id
    if _has_symlink_component(root, destination):
        raise ContractError("evidence reservation path contains a symlink or junction")
    try:
        destination.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ContractError("evidence reservation escapes its exclusive root") from exc
    if campaign_root.exists():
        if (
            not campaign_root.is_dir()
            or campaign_root.is_symlink()
            or bool(getattr(campaign_root, "is_junction", lambda: False)())
        ):
            raise ContractError("existing evidence campaign path is not an ordinary directory")
    else:
        campaign_root.mkdir(exist_ok=False)
    try:
        destination.mkdir(exist_ok=False)
    except BaseException:
        # Preserve any concurrent or partial directory for investigation.
        raise
    marker = {
        "schema": "qf-wp12-evidence-reservation-v1",
        "campaign_id": campaign_id,
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
        "nonce": secrets.token_hex(32),
        "reserved_utc": datetime.now(timezone.utc).isoformat(),
    }
    raw = (json.dumps(marker, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    with (destination / ".reservation.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return destination


def verify_pilot_evidence_reservation(
    run_directory: Path,
    *,
    campaign_id: str,
    run_id: str,
    manifest_sha256: str,
) -> tuple[str, ...]:
    """Check a create-new reservation and ensure no artifacts predate launch."""
    if run_directory.is_symlink() or bool(getattr(run_directory, "is_junction", lambda: False)()):
        return ("evidence run directory is a reparse point",)
    marker_path = run_directory / ".reservation.json"
    if marker_path.is_symlink() or bool(getattr(marker_path, "is_junction", lambda: False)()):
        return ("evidence reservation marker is a reparse point",)
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ("evidence reservation marker is absent or invalid",)
    expected = {
        "schema": "qf-wp12-evidence-reservation-v1",
        "campaign_id": campaign_id,
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
    }
    if not isinstance(marker, dict) or any(marker.get(key) != value for key, value in expected.items()):
        return ("evidence reservation does not match the approved unit",)
    if not isinstance(marker.get("nonce"), str) or len(marker["nonce"]) != 64:
        return ("evidence reservation nonce is malformed",)
    entries = {path.name for path in run_directory.iterdir()}
    if entries != {".reservation.json"}:
        return ("reserved evidence directory is not empty",)
    return ()


def create_evidence_directory(repository_root: Path, campaign_id: str, run_id: str) -> Path:
    if not _IDENTIFIER.fullmatch(campaign_id) or not _IDENTIFIER.fullmatch(run_id):
        raise ContractError("campaign_id and run_id must be safe single path components")
    root = repository_root.resolve(strict=True)
    evidence_root = root / "qualification" / "0_2_12" / "wp12_evidence"
    destination = evidence_root / campaign_id / run_id
    if _has_symlink_component(root, destination):
        raise ContractError("evidence path contains a symlink or escapes the repository")
    try:
        destination.resolve(strict=False).relative_to(evidence_root.resolve(strict=False))
    except ValueError as exc:
        raise ContractError("evidence destination escapes the WP12 evidence root") from exc
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"evidence destination already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    return destination


class JsonlJournal:
    """Append-only JSONL journal; truncated or malformed records are rejected."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("xb"):
            pass

    def append(self, event: Mapping[str, Any]) -> None:
        line = (
            json.dumps(dict(event), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        )
        with self.path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def read(path: Path) -> list[dict[str, Any]]:
        raw = path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise ContractError("journal ends with an incomplete record")
        records: list[dict[str, Any]] = []
        for number, line in enumerate(raw.splitlines(), start=1):
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContractError(f"journal record {number} is invalid") from exc
            if not isinstance(value, dict):
                raise ContractError(f"journal record {number} is not an object")
            records.append(value)
        return records


def _artifact_inventory(run_directory: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(run_directory.rglob("*")):
        if path.is_symlink():
            raise ContractError(f"symlink in evidence directory: {path.relative_to(run_directory)}")
        if not path.is_file() or path.name in {_RECEIPT, _RECEIPT_HASH}:
            continue
        relative = path.relative_to(run_directory).as_posix()
        if not safe_repo_relative_path(relative):
            raise ContractError(f"unsafe evidence artifact path: {relative}")
        files.append({"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    return files


def write_receipt(run_directory: Path, metadata: Mapping[str, Any]) -> tuple[str, Path]:
    if not run_directory.is_dir() or run_directory.is_symlink():
        raise ContractError("run directory must be an existing non-symlink directory")
    receipt = {
        "schema": "qf-solver-wp12-runner-receipt-v1",
        "metadata": dict(metadata),
        "artifacts": _artifact_inventory(run_directory),
    }
    raw = (json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    receipt_path = run_directory / _RECEIPT
    try:
        with receipt_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise FileExistsError("refusing to overwrite an existing WP12 receipt") from exc
    digest = sha256_bytes(raw)
    hash_path = run_directory / _RECEIPT_HASH
    with hash_path.open("xb") as stream:
        stream.write(f"{digest}  {_RECEIPT}\n".encode("ascii"))
        stream.flush()
        os.fsync(stream.fileno())
    return digest, receipt_path


def verify_receipt(run_directory: Path) -> tuple[str, ...]:
    errors: list[str] = []
    receipt_path = run_directory / _RECEIPT
    hash_path = run_directory / _RECEIPT_HASH
    if not receipt_path.is_file() or not hash_path.is_file():
        return ("receipt or receipt hash sidecar is missing",)
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ("receipt JSON is unreadable",)
    if not isinstance(receipt, dict) or receipt.get("schema") != "qf-solver-wp12-runner-receipt-v1":
        errors.append("receipt schema is invalid")
        return tuple(errors)
    expected_sidecar = f"{sha256_file(receipt_path)}  {_RECEIPT}"
    try:
        actual_sidecar = hash_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return ("receipt hash sidecar is unreadable",)
    if actual_sidecar != expected_sidecar:
        errors.append("receipt sidecar SHA-256 mismatch")
    expected_artifacts = receipt.get("artifacts")
    if not isinstance(expected_artifacts, list):
        return tuple(errors + ["receipt artifact inventory is malformed"])
    try:
        actual_artifacts = _artifact_inventory(run_directory)
    except (OSError, ContractError) as exc:
        return tuple(errors + [f"artifact inventory failed: {exc}"])
    if actual_artifacts != expected_artifacts:
        errors.append("evidence artifact inventory differs from receipt")
    return tuple(errors)


def record_refusal(audit_directory: Path, event: Mapping[str, Any], *, allowed_root: Path) -> Path:
    """Persist a denial event outside scientific evidence, without overwrite."""
    root = allowed_root.resolve(strict=True)
    try:
        audit_directory.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise ContractError("refusal audit path must remain inside the configured repository") from exc
    if audit_directory.is_symlink() or _has_symlink_component(root, audit_directory):
        raise ContractError("refusal audit path must not contain symlinks or junctions")
    audit_directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qf-solver-wp12-runner-refusal-v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        **dict(event),
    }
    filename = f"refusal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex}.json"
    path = audit_directory / filename
    raw = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def validate_evidence_relative_path(value: str) -> bool:
    if not safe_repo_relative_path(value):
        return False
    parts = PurePosixPath(value).parts
    return len(parts) >= 5 and parts[:3] == ("qualification", "0_2_12", "wp12_evidence")
