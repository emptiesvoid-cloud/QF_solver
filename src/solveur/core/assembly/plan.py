"""Reusable structural data for sparse finite-element assembly."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
from typing import Any

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.model import ElementDefinition, FiniteElementModel
from solveur.elements.registry import ElementRegistry, ElementSpec


@dataclass(frozen=True)
class AssemblyElementPlan:
    """Precomputed data that is independent of the assembled matrix type."""

    definition: ElementDefinition
    spec: ElementSpec
    coordinates: np.ndarray
    global_dofs: np.ndarray
    entry_count: int


@dataclass(frozen=True)
class AssemblyPlan:
    """Immutable element specification and DDL map for one model instance."""

    model_token: int
    node_count: int
    ndof: int
    dof_signature: tuple[tuple[int, tuple[str, ...]], ...]
    elements: tuple[AssemblyElementPlan, ...]
    chunk_size: int
    fingerprint: str
    build_seconds: float = 0.0

    @classmethod
    def build(
        cls,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        chunk_size: int = 256,
    ) -> "AssemblyPlan":
        """Prepare element specs, coordinates and global DDL maps once."""
        if chunk_size <= 0:
            raise ValueError("Assembly chunk_size must be positive.")
        elements: list[AssemblyElementPlan] = []
        for definition in model.elements:
            spec = ElementRegistry.get(definition.type)
            coordinates = np.asarray(model.nodes[list(definition.nodes)], dtype=float)
            global_dofs = np.asarray(
                [
                    index
                    for node in definition.nodes
                    for index in dofs.node_indices(int(node), spec.dofs)
                ],
                dtype=np.int64,
            )
            elements.append(
                AssemblyElementPlan(
                    definition=definition,
                    spec=spec,
                    coordinates=coordinates,
                    global_dofs=global_dofs,
                    entry_count=int(global_dofs.size**2),
                )
            )
        signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
        return cls(
            model_token=id(model),
            node_count=model.node_count,
            ndof=dofs.ndof,
            dof_signature=signature,
            elements=tuple(elements),
            chunk_size=int(chunk_size),
            fingerprint=_model_fingerprint(model, signature, int(chunk_size)),
        )

    def matches(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        *,
        chunk_size: int | None = None,
    ) -> bool:
        """Return whether this plan belongs to the supplied model and DDL map."""
        signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
        expected_chunk_size = self.chunk_size if chunk_size is None else int(chunk_size)
        return (
            self.model_token == id(model)
            and self.node_count == model.node_count
            and self.ndof == dofs.ndof
            and len(self.elements) == len(model.elements)
            and self.dof_signature == signature
            and self.chunk_size == expected_chunk_size
            and self.fingerprint == _model_fingerprint(model, signature, expected_chunk_size)
        )


def _model_fingerprint(
    model: FiniteElementModel,
    dof_signature: tuple[tuple[int, tuple[str, ...]], ...],
    chunk_size: int,
) -> str:
    """Hash assembly-relevant model state without retaining local matrices."""
    payload = {
        "model": _canonicalize(model),
        "dof_signature": dof_signature,
        "chunk_size": int(chunk_size),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonicalize(value: Any) -> Any:
    """Convert model values into deterministic JSON-compatible primitives."""
    if isinstance(value, np.ndarray):
        return {
            "__ndarray__": True,
            "dtype": str(value.dtype),
            "shape": list(value.shape),
            "values": value.tolist(),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonicalize(getattr(value, field.name))
            for field in sorted(fields(value), key=lambda item: item.name)
        }
    if isinstance(value, dict):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        return sorted((_canonicalize(item) for item in value), key=repr)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value
