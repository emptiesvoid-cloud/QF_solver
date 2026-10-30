"""Owner-controlled Ed25519 signer for one externally prepared WP12 decision.

The script never generates or stores private keys.  The key file must live
outside the repository; its passphrase is requested through a non-echoing
prompt.  The runner remains the only component that authorizes execution.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from scripts.wp12_owner_canonicalization import canonical_owner_payload
from scripts.wp12_runner.contracts import (
    ContractError,
    OWNER_DECISION_SCHEMA,
    load_json,
    owner_decision_binding_errors,
    validate_owner_decision_structure,
)


def sign_owner_decision(decision: dict[str, Any], private_key: Any) -> dict[str, Any]:
    """Sign canonical bytes with a caller-supplied Ed25519 key object."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if not isinstance(private_key, Ed25519PrivateKey):
        raise ContractError("Owner signing key must be Ed25519")
    if decision.get("schema") != OWNER_DECISION_SCHEMA:
        raise ContractError("Owner signer accepts only the run-bound Owner decision schema v4")
    key_envelope = decision.get("signature")
    envelope_key_id = key_envelope.get("key_id") if isinstance(key_envelope, dict) else None
    if decision.get("owner_key_id") != envelope_key_id:
        raise ContractError("canonical owner_key_id must equal the selected trust-store key_id")
    payload = canonical_owner_payload(decision)
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    signed = dict(decision)
    signed["signature"] = {
        "algorithm": "ed25519",
        "key_id": decision.get("signature", {}).get("key_id")
        if isinstance(decision.get("signature"), dict)
        else decision.get("key_id"),
        "public_key_sha256": hashlib.sha256(public_raw).hexdigest(),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_base64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }
    return signed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", required=True, type=Path, help="Owner-edited unsigned decision JSON")
    parser.add_argument("--manifest", required=True, type=Path, help="exact frozen manifest to authorize")
    parser.add_argument("--private-key", required=True, type=Path, help="Owner-controlled Ed25519 PEM outside the repo")
    parser.add_argument("--output", required=True, type=Path, help="new signed decision path outside the repo")
    args = parser.parse_args(argv)

    repository_root = Path(__file__).resolve().parents[1]
    try:
        key_path = args.private_key.resolve(strict=True)
        if args.private_key.is_symlink() or not key_path.is_file():
            raise ContractError("private-key path must be a regular non-symlink file")
        try:
            key_path.relative_to(repository_root)
        except ValueError:
            pass
        else:
            raise ContractError("private keys must remain outside the repository")
        if args.output.exists() or args.output.is_symlink():
            raise ContractError("refusing to overwrite a signed decision")
        if args.output.resolve(strict=False).is_relative_to(repository_root):
            raise ContractError("signed decisions must be written outside the repository")

        decision_raw = args.decision.read_text(encoding="utf-8")
        decision = json.loads(decision_raw, object_pairs_hook=_unique_object)
        if not isinstance(decision, dict):
            raise ContractError("Owner decision must be a JSON object")
        manifest, manifest_sha = load_json(args.manifest)
        if decision.get("manifest_sha256") != manifest_sha:
            raise ContractError("unsigned Owner decision does not bind the manifest bytes")
        unsigned_signature = decision.get("signature")
        key_id = decision.get("owner_key_id")
        if isinstance(unsigned_signature, dict) and unsigned_signature.get("key_id") != key_id:
            raise ContractError("signature key_id and canonical owner_key_id must match")
        if not isinstance(key_id, str) or not key_id:
            raise ContractError("Owner decision must identify its trust-store key_id")
        decision["signature"] = {"key_id": key_id}

        from cryptography.hazmat.primitives import serialization

        passphrase = getpass.getpass(
            "Owner Ed25519 key passphrase (leave empty only for an unencrypted hardware-managed export): "
        )
        password = passphrase.encode("utf-8") if passphrase else None
        private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=password)
        signed = sign_owner_decision(decision, private_key)
        structural_errors = validate_owner_decision_structure(signed)
        binding_errors = owner_decision_binding_errors(signed, manifest, manifest_sha)
        if structural_errors or binding_errors:
            raise ContractError("signed decision contract failed: " + "; ".join((*structural_errors, *binding_errors)))

        payload = (json.dumps(signed, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        print(
            json.dumps(
                {
                    "decision_id": signed.get("decision_id"),
                    "manifest_sha256": manifest_sha,
                    "payload_sha256": signed["signature"]["payload_sha256"],
                    "key_id": key_id,
                    "signature_written": True,
                    "private_key_bytes_written": False,
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"OWNER_DECISION_SIGNING_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
