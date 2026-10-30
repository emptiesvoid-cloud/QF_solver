"""Versioned, dependency-free canonical payload profile for Owner decisions.

This module contains no signing key handling.  It is shared by the runner
verifier and the separate Owner payload-preparation utility.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


PROFILE = "qf-owner-json-v1"


class CanonicalizationError(ValueError):
    """A payload is outside the deliberately restricted signing profile."""


def _check_value(value: Any, location: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise CanonicalizationError(f"object key must be ASCII text at {location}")
            _check_value(item, f"{location}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_value(item, f"{location}[{index}]")
        return
    if value is None or isinstance(value, (str, bool, int)):
        return
    raise CanonicalizationError(f"unsupported JSON scalar at {location}; floating-point numbers are forbidden")


def canonical_owner_payload(decision: Mapping[str, Any]) -> bytes:
    """Encode the unsigned decision payload according to ``qf-owner-json-v1``.

    The `signature` envelope is omitted. Keys are ASCII; values may be strings,
    booleans, null, integers, arrays, or objects; floats are forbidden. UTF-8
    is emitted with non-ASCII string characters unescaped, keys sorted by
    Unicode/code-point order, compact separators, and no trailing newline.
    Strings are not Unicode-normalized. Duplicate JSON keys must be rejected by
    the caller's parser before this function is used.
    """
    if decision.get("canonicalization") != PROFILE:
        raise CanonicalizationError("unsupported Owner canonicalization profile")
    payload = {key: value for key, value in decision.items() if key != "signature"}
    _check_value(payload)
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError("Owner decision contains non-canonical JSON values") from exc
