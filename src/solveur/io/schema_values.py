"""Shared scalar and shape checks for input-schema validators."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_numeric_vector(value: Any, size: int) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == size
        and all(is_number(item) for item in value)
    )


def is_numeric_matrix(value: Any, rows: int, columns: int) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) == rows
        and all(is_numeric_vector(row, columns) for row in value)
    )


def require_fields(
    path: str,
    value: Mapping[str, Any],
    required: tuple[str, ...],
    errors: list[str],
) -> None:
    for field in required:
        if field not in value:
            errors.append(f"{path}.{field} is required.")


def reject_unknown(
    path: str,
    value: Mapping[str, Any],
    allowed: set[str],
    errors: list[str],
) -> None:
    unknown = sorted(str(key) for key in value if key not in allowed)
    if unknown:
        errors.append(f"{path} has unknown field(s): {', '.join(unknown)}.")
