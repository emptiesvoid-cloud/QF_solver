"""Small pure helpers used by the maturity-promotion audit."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def get_path(value: Any, path: str) -> tuple[Any, bool]:
    """Read a dotted path from nested dictionaries or lists."""
    current = value
    if not path:
        return current, True
    for token in path.split("."):
        try:
            if isinstance(current, list):
                current = current[int(token)]
            elif isinstance(current, dict) and token in current:
                current = current[token]
            else:
                return None, False
        except (IndexError, KeyError, TypeError, ValueError):
            return None, False
    return current, True


def compare(actual: Any, op: str, expected: Any) -> bool:
    """Evaluate the small comparison vocabulary used by the registry."""
    if op == "exists":
        return actual is not None
    if op == "equals":
        return actual == expected
    if op == "greater_equal":
        return actual >= expected
    if op == "less_equal":
        return actual <= expected
    if op == "between":
        return len(expected) == 2 and expected[0] <= actual <= expected[1]
    return False


def unique(values: Any) -> list[str]:
    """Return non-empty values once, preserving source order."""
    result: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in result:
            result.append(text)
    return result


def relative(path: Path, root: Path) -> str:
    """Return a stable project-relative path, or the basename outside it."""
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name
