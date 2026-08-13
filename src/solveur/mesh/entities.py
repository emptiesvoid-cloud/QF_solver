"""Mesh-related lightweight entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeshIssue:
    """A validation message emitted by mesh checks."""

    level: str
    message: str
