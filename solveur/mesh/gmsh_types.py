"""Typed intermediate entities for deterministic Gmsh imports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from solveur.core.model import FiniteElementModel


@dataclass(frozen=True)
class GmshCell:
    """One native Gmsh cell before node-tag remapping."""

    tag: int
    gmsh_type: int
    dimension: int
    order: int
    name: str
    nodes: tuple[int, ...]


@dataclass(frozen=True)
class GmshPhysicalGroup:
    """Named physical group and its native cell/node membership."""

    name: str
    dimension: int
    tag: int
    cell_tags: tuple[int, ...]
    node_tags: tuple[int, ...]


@dataclass(frozen=True)
class GmshMeshData:
    """Dependency-neutral representation extracted from a MSH 4.1 file."""

    path: Path
    format_version: str
    binary: bool
    gmsh_version: str
    nodes: dict[int, tuple[float, float, float]]
    cells: dict[int, GmshCell]
    groups: dict[tuple[int, str], GmshPhysicalGroup]


@dataclass
class GmshImportReport:
    """Machine-readable provenance and validation report for one import."""

    status: str
    solver_name: str
    solver_version: str
    source_path: str
    source_sha256: str
    setup_path: str
    setup_sha256: str
    gmsh_version: str
    msh_version: str
    binary: bool
    element_family: str
    node_count: int
    element_count: int
    group_count: int
    physical_groups: list[dict[str, Any]] = field(default_factory=list)
    action_counts: dict[str, int] = field(default_factory=dict)
    orientation_repairs: int = 0
    mesh_status: str = "PASS"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GmshImportResult:
    """Imported finite-element model paired with its provenance report."""

    model: FiniteElementModel
    report: GmshImportReport
