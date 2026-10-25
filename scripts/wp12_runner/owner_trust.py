"""Ed25519 verification for detached WP12 Owner decisions.

The production trust root is read only from machine-scoped Windows settings.
Tests may inject an in-memory keyring, but the CLI never accepts a caller-owned
key file or environment variable as a trust root.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .contracts import ContractError, OWNER_DECISION_SCHEMA, sha256_bytes, validate_owner_decision_structure
from scripts.wp12_owner_canonicalization import CanonicalizationError, canonical_owner_payload


TRUST_STORE_PATH_VALUE = "QF_WP12_TRUST_STORE"
TRUST_STORE_SHA_VALUE = "QF_WP12_TRUST_STORE_SHA256"


@dataclass(frozen=True)
class TrustedOwnerKey:
    key_id: str
    principal: str
    public_key_base64: str
    revoked: bool = False


@dataclass(frozen=True)
class OwnerVerification:
    authenticated: bool
    key_id: str | None
    principal: str | None
    payload_sha256: str | None
    errors: tuple[str, ...]


def canonical_payload(decision: Mapping[str, Any]) -> bytes:
    """Return canonical bytes using the versioned Owner signing profile."""
    try:
        return canonical_owner_payload(decision)
    except CanonicalizationError as exc:
        raise ContractError("Owner decision contains non-canonical JSON values") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate Owner trust-store JSON key: {key}")
        result[key] = value
    return result


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def load_machine_trust_store(repository_root: Path) -> tuple[dict[str, TrustedOwnerKey], str]:
    """Load the pinned keyring via HKLM; caller/session environment is ignored."""
    if os.name != "nt":
        raise ContractError("machine-scoped Owner trust is supported only on Windows")
    try:
        import winreg
    except ImportError as exc:  # pragma: no cover - Windows standard library
        raise ContractError("Windows registry access is unavailable") from exc

    registry_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_READ) as key:
            configured_path, _ = winreg.QueryValueEx(key, TRUST_STORE_PATH_VALUE)
            expected_sha256, _ = winreg.QueryValueEx(key, TRUST_STORE_SHA_VALUE)
    except OSError as exc:
        raise ContractError("machine-scoped Owner trust root is not configured") from exc
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path, 0, winreg.KEY_SET_VALUE):
            raise ContractError("runner account can modify the machine-scoped Owner trust pin")
    except PermissionError:
        pass
    except OSError as exc:
        if getattr(exc, "winerror", None) not in {5, 1314}:
            raise ContractError("could not verify write protection for the machine-scoped Owner trust pin") from exc
    if not isinstance(configured_path, str) or not isinstance(expected_sha256, str):
        raise ContractError("machine-scoped Owner trust settings have invalid types")
    if len(expected_sha256) != 64 or any(character not in "0123456789abcdef" for character in expected_sha256):
        raise ContractError("machine-scoped Owner trust-store SHA-256 pin is invalid")

    trust_path = Path(configured_path)
    if not trust_path.is_absolute() or not trust_path.is_file() or trust_path.is_symlink():
        raise ContractError("pinned Owner trust-store path is absent, non-absolute, or a symlink")
    if len(trust_path.drive) != 2 or trust_path.drive[1] != ":":
        raise ContractError("Owner trust store must be on a local Windows volume")
    if bool(getattr(trust_path, "is_junction", lambda: False)()):
        raise ContractError("pinned Owner trust-store path is a junction")
    current = Path(trust_path.anchor)
    for part in trust_path.parts[1:]:
        current = current / part
        if current.is_symlink() or bool(getattr(current, "is_junction", lambda: False)()):
            raise ContractError("pinned Owner trust-store path contains a symlink or junction")
    try:
        writable_fd = os.open(trust_path, os.O_WRONLY)
    except PermissionError:
        writable_fd = None
    except OSError as exc:
        if getattr(exc, "winerror", None) != 5:
            raise ContractError("could not verify write protection for the Owner trust-store file") from exc
        writable_fd = None
    if writable_fd is not None:
        os.close(writable_fd)
        raise ContractError("runner account can open the Owner trust-store file for writing")
    parent = trust_path.parent
    while parent != Path(parent.anchor):
        if os.access(parent, os.W_OK):
            raise ContractError("runner account has write access to an Owner trust-store parent directory")
        parent = parent.parent
    root = repository_root.resolve(strict=True)
    try:
        trust_path.resolve(strict=True).relative_to(root)
    except ValueError:
        pass
    else:
        raise ContractError("Owner trust store must be outside the repository checkout")
    raw = trust_path.read_bytes()
    actual_sha256 = sha256_bytes(raw)
    if actual_sha256 != expected_sha256:
        raise ContractError("Owner trust-store bytes do not match the machine-scoped SHA-256 pin")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("pinned Owner trust store is invalid UTF-8 JSON") from exc
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "keys"}
        or document.get("schema") != "qf-wp12-owner-trust-store-v1"
    ):
        raise ContractError("pinned Owner trust-store schema is invalid")
    entries = document.get("keys")
    if not isinstance(entries, list) or not entries:
        raise ContractError("pinned Owner trust store contains no keys")
    keys: dict[str, TrustedOwnerKey] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ContractError("Owner trust-store key entry must be an object")
        if set(entry) != {"key_id", "principal", "public_key_base64", "revoked"}:
            raise ContractError("Owner trust-store key entry has missing or unexpected fields")
        key_id, principal, public_key = entry.get("key_id"), entry.get("principal"), entry.get("public_key_base64")
        if not all(isinstance(value, str) and value for value in (key_id, principal, public_key)):
            raise ContractError("Owner trust-store key entry is incomplete")
        if key_id in keys:
            raise ContractError("Owner trust-store key IDs must be unique")
        try:
            decoded = base64.b64decode(public_key, validate=True)
        except ValueError as exc:
            raise ContractError("Owner trust-store public key is invalid base64") from exc
        if len(decoded) != 32:
            raise ContractError("Ed25519 public key must be 32 bytes")
        if base64.b64encode(decoded).decode("ascii") != public_key or not isinstance(entry.get("revoked"), bool):
            raise ContractError("Owner trust-store public key encoding or revoked flag is invalid")
        keys[key_id] = TrustedOwnerKey(key_id, principal, public_key, entry["revoked"])
    return keys, actual_sha256


def verify_owner_decision(
    decision: Mapping[str, Any],
    *,
    trusted_keys: Mapping[str, TrustedOwnerKey],
    manifest_sha256: str,
    expected_campaign_id: str,
    expected_scientific_identity: Mapping[str, str],
    expected_runner_identity: Mapping[str, str],
    now: datetime | None = None,
) -> OwnerVerification:
    """Authenticate a signed decision and bind it to the exact requested identities."""
    errors = list(validate_owner_decision_structure(decision))
    if decision.get("schema") != OWNER_DECISION_SCHEMA:
        errors.append("unsupported Owner decision schema")
    signature = decision.get("signature")
    owner = decision.get("owner")
    key_id = signature.get("key_id") if isinstance(signature, Mapping) else None
    key = trusted_keys.get(key_id) if isinstance(key_id, str) else None
    if decision.get("owner_key_id") != key_id:
        errors.append("signed Owner key_id does not match the canonical decision payload")
    if key is None:
        errors.append("Owner signing key is unknown")
    elif key.revoked:
        errors.append("Owner signing key is revoked")
    if decision.get("campaign_id") != expected_campaign_id:
        errors.append("campaign ID does not match the selected manifest")
    if decision.get("manifest_sha256") != manifest_sha256:
        errors.append("manifest SHA-256 does not match the signed decision")
    if not isinstance(owner, Mapping) or key is None or owner.get("principal") != key.principal:
        errors.append("Owner principal does not match the trusted key")

    for field, expected in (
        ("scientific_identity", expected_scientific_identity),
        ("runner_identity", expected_runner_identity),
    ):
        actual = decision.get(field)
        if not isinstance(actual, Mapping):
            errors.append(f"{field} is missing")
        elif any(actual.get(key_name) != value for key_name, value in expected.items()):
            errors.append(f"{field} does not match the inspected identity")

    try:
        not_before = _parse_utc(decision.get("not_before_utc"), "not_before_utc")
        expires = _parse_utc(decision.get("expires_utc"), "expires_utc")
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if expires <= not_before:
            errors.append("authorization validity interval is empty")
        if current < not_before:
            errors.append("Owner decision is not yet valid")
        if current >= expires:
            errors.append("Owner decision has expired")
    except ContractError as exc:
        errors.append(str(exc))

    payload_hash: str | None = None
    if isinstance(signature, Mapping):
        try:
            payload = canonical_payload(decision)
            payload_hash = hashlib.sha256(payload).hexdigest()
            if signature.get("payload_sha256") != payload_hash:
                errors.append("canonical Owner payload SHA-256 mismatch")
            if key is not None and not key.revoked:
                public_bytes = base64.b64decode(key.public_key_base64, validate=True)
                if signature.get("public_key_sha256") != hashlib.sha256(public_bytes).hexdigest():
                    errors.append("Owner public-key SHA-256 mismatch")
                try:
                    signature_bytes = base64.b64decode(signature.get("signature_base64", ""), validate=True)
                    from cryptography.exceptions import InvalidSignature
                    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

                    Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature_bytes, payload)
                except ImportError:
                    errors.append("cryptography is required to verify Ed25519 signatures")
                except (ValueError, InvalidSignature):
                    errors.append("Owner Ed25519 signature is invalid")
        except (ContractError, ValueError) as exc:
            errors.append(str(exc))
    unique_errors = tuple(dict.fromkeys(errors))
    return OwnerVerification(
        not unique_errors,
        key_id if isinstance(key_id, str) else None,
        key.principal if key is not None else None,
        payload_hash,
        unique_errors,
    )
