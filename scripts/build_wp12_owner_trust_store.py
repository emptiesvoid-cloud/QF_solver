"""Build a public WP12 trust-store file from an Owner-controlled Ed25519 key.

This tool never creates, copies, prints, or stores a private key. The Owner
chooses and supplies the key path locally; the passphrase is read without echo.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def build_public_trust_store(
    private_key_path: Path,
    *,
    key_id: str,
    principal: str,
    passphrase: str,
    repository_root: Path,
) -> tuple[dict[str, Any], str]:
    """Derive only the public Ed25519 key and a create-new trust-store digest."""
    key_path = private_key_path.resolve(strict=True)
    root = repository_root.resolve(strict=True)
    if not key_path.is_file() or private_key_path.is_symlink():
        raise ValueError("private-key path must be a regular non-symlink file")
    try:
        key_path.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("private keys must remain outside the repository")
    if not key_id or any(ord(character) < 32 for character in key_id):
        raise ValueError("key_id must be non-empty and contain no control characters")
    if not principal or any(ord(character) < 32 for character in principal):
        raise ValueError("principal must be non-empty and contain no control characters")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(), password=passphrase.encode("utf-8") if passphrase else None
    )
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Owner key must be Ed25519")
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    document: dict[str, Any] = {
        "schema": "qf-wp12-owner-trust-store-v1",
        "keys": [
            {
                "key_id": key_id,
                "principal": principal,
                "public_key_base64": base64.b64encode(public_bytes).decode("ascii"),
                "revoked": False,
            }
        ],
    }
    raw = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    return document, hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key", required=True, type=Path, help="Owner key path outside the repository")
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument(
        "--output", required=True, type=Path, help="New public trust-store JSON path outside repository"
    )
    args = parser.parse_args(argv)

    repository_root = Path(__file__).resolve().parents[1]
    try:
        output = args.output.resolve(strict=False)
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite an existing trust-store file")
        try:
            output.relative_to(repository_root)
        except ValueError:
            pass
        else:
            raise ValueError("public trust stores must remain outside the repository")
        document, digest = build_public_trust_store(
            args.private_key,
            key_id=args.key_id,
            principal=args.principal,
            passphrase=getpass.getpass("Owner Ed25519 private-key passphrase: "),
            repository_root=repository_root,
        )
        raw = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            import os

            os.fsync(stream.fileno())
        print(
            json.dumps(
                {
                    "state": "PUBLIC_TRUST_STORE_CREATED",
                    "key_id": args.key_id,
                    "sha256": digest,
                    "public_key_only": True,
                    "private_key_written": False,
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"TRUST_STORE_CREATION_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
