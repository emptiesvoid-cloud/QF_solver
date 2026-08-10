"""Lightweight large-scale TET4 model container."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LargeModel:
    """Array-based model for large linear-static TET4 jobs."""

    nodes: np.ndarray
    tet4: np.ndarray
    material_ids: np.ndarray
    materials: dict[str, dict[str, Any]]
    material_names: tuple[str, ...]
    fixed_nodes: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    fixed_components: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int8))
    load_nodes: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    load_components: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int8))
    load_values: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=float))
    analysis: dict[str, Any] = field(default_factory=lambda: {"type": "linear_static", "method": "cg"})
    schema_version: int = 1
    units: dict[str, str] = field(default_factory=lambda: {"system": "SI"})
    verification_profile: str = "engineering"

    def __post_init__(self) -> None:
        self.nodes = np.asarray(self.nodes, dtype=float)
        self.tet4 = np.asarray(self.tet4, dtype=np.int64)
        self.material_ids = np.asarray(self.material_ids, dtype=np.int64)
        self.fixed_nodes = np.asarray(self.fixed_nodes, dtype=np.int64)
        self.fixed_components = np.asarray(self.fixed_components, dtype=np.int8)
        self.load_nodes = np.asarray(self.load_nodes, dtype=np.int64)
        self.load_components = np.asarray(self.load_components, dtype=np.int8)
        self.load_values = np.asarray(self.load_values, dtype=float)
        self.analysis = dict(self.analysis or {"type": "linear_static", "method": "cg"})
        self.units = dict(self.units or {"system": "SI"})
        self.material_names = tuple(self.material_names)
        self._validate_shapes()

    @property
    def node_count(self) -> int:
        return int(self.nodes.shape[0])

    @property
    def element_count(self) -> int:
        return int(self.tet4.shape[0])

    @property
    def ndof(self) -> int:
        return 3 * self.node_count

    def material_for_element(self, index: int) -> dict[str, Any]:
        return self.materials[self.material_names[int(self.material_ids[index])]]

    def _validate_shapes(self) -> None:
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("LargeModel nodes must have shape (n_nodes, 3).")
        if self.tet4.ndim != 2 or self.tet4.shape[1] != 4:
            raise ValueError("LargeModel tet4 connectivity must have shape (n_elements, 4).")
        if self.material_ids.shape != (self.element_count,):
            raise ValueError("LargeModel material_ids must have one entry per element.")
        if self.fixed_nodes.shape != self.fixed_components.shape:
            raise ValueError("LargeModel fixed_nodes and fixed_components must have same length.")
        if not (self.load_nodes.shape == self.load_components.shape == self.load_values.shape):
            raise ValueError("LargeModel load arrays must have the same length.")
        if np.any(self.tet4 < 0) or np.any(self.tet4 >= max(self.node_count, 1)):
            raise ValueError("LargeModel tet4 connectivity references invalid node indices.")
        if np.any(self.material_ids < 0) or np.any(self.material_ids >= max(len(self.material_names), 1)):
            raise ValueError("LargeModel material_ids reference unknown material names.")
        _check_node_components(self.fixed_nodes, self.fixed_components, self.node_count, "fixed")
        _check_node_components(self.load_nodes, self.load_components, self.node_count, "load")


def _check_node_components(nodes: np.ndarray, components: np.ndarray, node_count: int, label: str) -> None:
    if nodes.size and (np.any(nodes < 0) or np.any(nodes >= node_count)):
        raise ValueError(f"LargeModel {label} nodes reference invalid node indices.")
    if components.size and (np.any(components < 0) or np.any(components > 2)):
        raise ValueError(f"LargeModel {label} components must be in [0, 2].")
