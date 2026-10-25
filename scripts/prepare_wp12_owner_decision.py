"""Prepare canonical bytes for an Owner-controlled external Ed25519 signer.

This tool never reads, accepts, generates, or stores a private key. The
resulting bytes must be signed by the Owner's separately controlled signer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from scripts.wp12_owner_canonicalization import canonical_owner_payload


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", type=Path, help="unsigned or signature-enveloped decision JSON")
    parser.add_argument("--output", type=Path, required=True, help="new file for canonical payload bytes")
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error("refusing to overwrite an existing canonical payload")
    try:
        decision = json.loads(args.decision.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        if not isinstance(decision, dict):
            raise ValueError("decision must be a JSON object")
        payload = canonical_owner_payload(decision)
        with args.output.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"profile": decision["canonicalization"], "payload_sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "private_key_accessed": False}, sort_keys=True))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
        print(f"OWNER_PAYLOAD_PREPARATION_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
