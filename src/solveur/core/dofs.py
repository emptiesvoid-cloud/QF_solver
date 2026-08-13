"""Degree-of-freedom naming and global numbering."""

from __future__ import annotations

from dataclasses import dataclass

DOF_ORDER = ("UX", "UY", "UZ", "RX", "RY", "RZ")
TRANSLATION_DOFS = ("UX", "UY", "UZ")
SHELL_DOFS = DOF_ORDER
BEAM_DOFS = DOF_ORDER
SOLID_DOFS = TRANSLATION_DOFS


def normalize_dof_name(dof: str | int) -> str:
    """Convert a JSON dof value to a canonical dof name."""
    if isinstance(dof, int):
        try:
            return DOF_ORDER[dof]
        except IndexError as exc:
            raise ValueError(f"Unknown dof index {dof}.") from exc
    value = str(dof).upper()
    if value not in DOF_ORDER:
        raise ValueError(f"Unknown dof name {dof!r}.")
    return value


@dataclass(frozen=True)
class DofManager:
    """Map node-local named dofs to compact global indices."""

    node_dofs: dict[int, tuple[str, ...]]
    _indices: dict[tuple[int, str], int]

    @classmethod
    def from_node_requirements(cls, requirements: dict[int, set[str]]) -> "DofManager":
        node_dofs: dict[int, tuple[str, ...]] = {}
        indices: dict[tuple[int, str], int] = {}
        counter = 0
        for node in sorted(requirements):
            ordered = tuple(name for name in DOF_ORDER if name in requirements[node])
            node_dofs[node] = ordered
            for name in ordered:
                indices[(node, name)] = counter
                counter += 1
        return cls(node_dofs=node_dofs, _indices=indices)

    @property
    def ndof(self) -> int:
        return len(self._indices)

    def has(self, node: int, dof: str | int) -> bool:
        return (int(node), normalize_dof_name(dof)) in self._indices

    def index(self, node: int, dof: str | int) -> int:
        key = (int(node), normalize_dof_name(dof))
        if key not in self._indices:
            raise ValueError(f"DOF {key[1]} is not active on node {key[0]}.")
        return self._indices[key]

    def node_indices(self, node: int, dofs: tuple[str, ...]) -> list[int]:
        return [self.index(node, dof) for dof in dofs]
