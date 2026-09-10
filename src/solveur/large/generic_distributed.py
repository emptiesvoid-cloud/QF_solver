"""Family-aware distributed architecture for the WP13 mixed-solid bridge.

This module is an architecture layer, not a PETSc backend.  It deliberately
keeps the existing TET4 large route untouched while providing a fail-closed,
partition-testable representation for TET4/WEDGE6/HEX8.  ``GenericDistributedModel``
is deliberately a serial partitioning envelope; ``RankLocalModel`` is the
future-adapter boundary and contains only owned/ghost data for one rank.  The
shadow assembly is used only by targeted WP13 validation; it is not a new
solver route.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from solveur.core.dofs import DofManager, TRANSLATION_DOFS
from solveur.core.errors import InputValidationError
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel, NodalLoad
from solveur.elements.registry import ElementRegistry, ElementSpec
from solveur.materials.factory import MaterialFactory


SUPPORTED_DISTRIBUTED_FAMILIES = ("TET4", "WEDGE6", "HEX8")


@dataclass(frozen=True)
class ElementBlock:
    """Family-homogeneous connectivity block for distributed input."""

    family: str
    connectivity: np.ndarray
    element_ids: np.ndarray
    material_ids: np.ndarray
    region_ids: np.ndarray
    material_names: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        family = str(self.family).upper()
        if family not in SUPPORTED_DISTRIBUTED_FAMILIES:
            raise InputValidationError(f"Unsupported distributed element family {family!r}.")
        spec = ElementRegistry.get(family)
        connectivity = np.asarray(self.connectivity, dtype=np.int64)
        element_ids = np.asarray(self.element_ids, dtype=np.int64)
        material_ids = np.asarray(self.material_ids, dtype=np.int64)
        region_ids = np.asarray(self.region_ids, dtype=np.int64)
        if connectivity.ndim != 2 or connectivity.shape[1] != spec.node_count:
            raise InputValidationError(
                f"{family} distributed connectivity must have shape (n, {spec.node_count})."
            )
        count = connectivity.shape[0]
        for name, values in (
            ("element_ids", element_ids),
            ("material_ids", material_ids),
            ("region_ids", region_ids),
        ):
            if values.shape != (count,):
                raise InputValidationError(f"{family} distributed {name} must have one entry per element.")
        if np.unique(element_ids).size != element_ids.size:
            raise InputValidationError(f"{family} distributed element_ids must be unique within a block.")
        if np.any(connectivity < 0):
            raise InputValidationError(f"{family} distributed connectivity contains a negative node id.")
        if np.any(material_ids < 0) or np.any(material_ids >= len(self.material_names)):
            raise InputValidationError(f"{family} distributed material_ids reference an unknown material.")
        if not self.material_names:
            raise InputValidationError(f"{family} distributed block must declare material_names.")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "connectivity", connectivity)
        object.__setattr__(self, "element_ids", element_ids)
        object.__setattr__(self, "material_ids", material_ids)
        object.__setattr__(self, "region_ids", region_ids)
        object.__setattr__(self, "material_names", tuple(str(name) for name in self.material_names))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def element_count(self) -> int:
        return int(self.connectivity.shape[0])

    @property
    def node_count_per_element(self) -> int:
        return int(self.connectivity.shape[1])

    def element(self, index: int) -> "DistributedElement":
        position = int(index)
        if position < 0 or position >= self.element_count:
            raise IndexError(f"Element block index {position} is out of range.")
        return DistributedElement(
            element_id=int(self.element_ids[position]),
            family=self.family,
            nodes=tuple(int(node) for node in self.connectivity[position]),
            material_id=int(self.material_ids[position]),
            material=self.material_names[int(self.material_ids[position])],
            region_id=int(self.region_ids[position]),
        )


@dataclass(frozen=True)
class DistributedElement:
    """One family-aware element record used by partition and dispatch code."""

    element_id: int
    family: str
    nodes: tuple[int, ...]
    material_id: int
    material: str
    region_id: int


@dataclass(frozen=True)
class GenericDistributedModel:
    """Family-aware model schema independent of a PETSc implementation."""

    nodes: np.ndarray
    blocks: tuple[ElementBlock, ...]
    materials: Mapping[str, Mapping[str, Any]]
    dofs: DofManager
    fixed_dofs: tuple[BoundaryCondition, ...] = ()
    loads: tuple[NodalLoad, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        nodes = np.asarray(self.nodes, dtype=float)
        if nodes.ndim != 2 or nodes.shape[1] != 3:
            raise InputValidationError("Generic distributed nodes must have shape (n, 3).")
        if not self.blocks:
            raise InputValidationError("Generic distributed model requires at least one element block.")
        elements = list(self.iter_elements())
        if len({element.element_id for element in elements}) != len(elements):
            raise InputValidationError("Generic distributed element ids must be globally unique.")
        for element in elements:
            if any(node >= nodes.shape[0] for node in element.nodes):
                raise InputValidationError(
                    f"{element.family} element {element.element_id} references an invalid node."
                )
            if element.material not in self.materials:
                raise InputValidationError(
                    f"{element.family} element {element.element_id} references unknown material {element.material!r}."
                )
        if not set(self.dofs.node_dofs).issubset(set(range(nodes.shape[0]))):
            raise InputValidationError("Generic distributed DOF map references an invalid node.")
        active_names = {name for names in self.dofs.node_dofs.values() for name in names}
        if not active_names <= set(TRANSLATION_DOFS):
            raise InputValidationError("Generic distributed solid schema supports translational DOFs only.")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "materials", {str(key): dict(value) for key, value in self.materials.items()})
        object.__setattr__(self, "fixed_dofs", tuple(self.fixed_dofs))
        object.__setattr__(self, "loads", tuple(self.loads))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def node_count(self) -> int:
        return int(self.nodes.shape[0])

    @property
    def element_count(self) -> int:
        return sum(block.element_count for block in self.blocks)

    @property
    def ndof(self) -> int:
        return int(self.dofs.ndof)

    def iter_elements(self) -> Iterable[DistributedElement]:
        elements = [block.element(index) for block in self.blocks for index in range(block.element_count)]
        return iter(sorted(elements, key=lambda item: item.element_id))

    def element_counts(self) -> dict[str, int]:
        return {family: sum(block.element_count for block in self.blocks if block.family == family) for family in SUPPORTED_DISTRIBUTED_FAMILIES}

    @classmethod
    def from_finite_element_model(cls, model: FiniteElementModel) -> "GenericDistributedModel":
        """Convert only the WP13-01B static mixed-solid scope.

        Unsupported features fail closed rather than being silently dropped.
        The original ``FiniteElementModel`` and the legacy TET4 large route are
        not mutated.
        """

        if model.analysis.type != "linear_static":
            raise InputValidationError("WP13-01B distributed schema supports only linear_static analysis.")
        if model.distributed_loads or model.springs or model.concentrated_masses:
            raise InputValidationError("WP13-01B schema supports nodal loads only; unsupported loads were supplied.")
        if model.multipoint_constraints or model.rbe2 or model.rbe3 or model.contacts:
            raise InputValidationError("WP13-01B schema does not silently absorb MPC, RBE or contact records.")
        grouped: dict[str, list[tuple[int, ElementDefinition]]] = defaultdict(list)
        for element_id, definition in enumerate(model.elements):
            family = str(definition.type).upper()
            if family not in SUPPORTED_DISTRIBUTED_FAMILIES:
                raise InputValidationError(
                    f"WP13-01B distributed schema does not support element family {family!r}."
                )
            spec = ElementRegistry.get(family)
            if len(definition.nodes) != spec.node_count:
                raise InputValidationError(f"{family} element {element_id} has invalid connectivity length.")
            grouped[family].append((element_id, definition))
        blocks: list[ElementBlock] = []
        for family in SUPPORTED_DISTRIBUTED_FAMILIES:
            rows = grouped.get(family, [])
            if not rows:
                continue
            material_names = tuple(sorted({definition.material for _, definition in rows}))
            material_index = {name: index for index, name in enumerate(material_names)}
            blocks.append(
                ElementBlock(
                    family=family,
                    connectivity=np.asarray([definition.nodes for _, definition in rows], dtype=np.int64),
                    element_ids=np.asarray([element_id for element_id, _ in rows], dtype=np.int64),
                    material_ids=np.asarray(
                        [material_index[definition.material] for _, definition in rows], dtype=np.int64
                    ),
                    region_ids=np.zeros(len(rows), dtype=np.int64),
                    material_names=material_names,
                    metadata={"source": "FiniteElementModel", "region_policy": "single_default_region"},
                )
            )
        dofs = model.dof_manager()
        active_names = {name for names in dofs.node_dofs.values() for name in names}
        if not active_names <= set(TRANSLATION_DOFS):
            raise InputValidationError("WP13-01B distributed solid schema supports translational DOFs only.")
        return cls(
            nodes=model.nodes.copy(),
            blocks=tuple(blocks),
            materials=model.materials,
            dofs=dofs,
            fixed_dofs=tuple(model.fixed_dofs),
            loads=tuple(model.loads),
            metadata={"analysis": "linear_static", "source_schema_version": model.schema_version},
        )


@dataclass(frozen=True)
class DistributedDofMap:
    """Global/local DOF map with explicit owned and ghost node sets."""

    global_node_ids: np.ndarray
    local_node_ids: np.ndarray
    owned_node_ids: np.ndarray
    ghost_node_ids: np.ndarray
    global_dof_ids: np.ndarray
    local_dof_ids: np.ndarray
    owned_dof_ids: np.ndarray
    ghost_dof_ids: np.ndarray
    constrained_dof_ids: np.ndarray
    node_global_to_local: Mapping[int, int]
    dof_global_to_local: Mapping[int, int]

    def __post_init__(self) -> None:
        arrays = {
            "global_node_ids": self.global_node_ids,
            "local_node_ids": self.local_node_ids,
            "owned_node_ids": self.owned_node_ids,
            "ghost_node_ids": self.ghost_node_ids,
            "global_dof_ids": self.global_dof_ids,
            "local_dof_ids": self.local_dof_ids,
            "owned_dof_ids": self.owned_dof_ids,
            "ghost_dof_ids": self.ghost_dof_ids,
            "constrained_dof_ids": self.constrained_dof_ids,
        }
        for name, values in arrays.items():
            value = np.asarray(values, dtype=np.int64)
            if value.ndim != 1 or np.unique(value).size != value.size:
                raise InputValidationError(f"Distributed DOF map {name} must be a unique one-dimensional array.")
            object.__setattr__(self, name, value)
        if np.intersect1d(self.owned_node_ids, self.ghost_node_ids).size:
            raise InputValidationError("Distributed DOF map owned and ghost nodes overlap.")
        if not np.array_equal(np.sort(np.concatenate((self.owned_node_ids, self.ghost_node_ids))), self.local_node_ids):
            raise InputValidationError("Distributed DOF map local nodes do not equal owned plus ghost nodes.")
        node_map = {int(key): int(value) for key, value in self.node_global_to_local.items()}
        dof_map = {int(key): int(value) for key, value in self.dof_global_to_local.items()}
        if set(node_map) != set(int(value) for value in self.local_node_ids) or set(node_map.values()) != set(range(self.local_node_ids.size)):
            raise InputValidationError("Distributed DOF map node local/global mapping is invalid.")
        if set(dof_map) != set(int(value) for value in self.local_dof_ids) or set(dof_map.values()) != set(range(self.local_dof_ids.size)):
            raise InputValidationError("Distributed DOF map DOF local/global mapping is invalid.")
        object.__setattr__(self, "node_global_to_local", node_map)
        object.__setattr__(self, "dof_global_to_local", dof_map)

    @property
    def global_dof_count(self) -> int:
        return int(self.global_dof_ids.size)

    def local_index(self, global_node: int) -> int:
        try:
            return int(self.node_global_to_local[int(global_node)])
        except KeyError as exc:
            raise InputValidationError(f"Node {global_node} is not present in the local map.") from exc


@dataclass(frozen=True)
class DistributedPartition:
    """Logical rank partition used by shadow validation and future adapters."""

    rank: int
    size: int
    elements: tuple[DistributedElement, ...]
    local_node_ids: np.ndarray
    owned_node_ids: np.ndarray
    ghost_node_ids: np.ndarray
    interface_node_ids: np.ndarray
    neighboring_ranks: tuple[int, ...]
    element_owner: Mapping[int, int]
    node_owner: Mapping[int, int]
    dof_map: DistributedDofMap

    @property
    def owned_element_ids(self) -> tuple[int, ...]:
        return tuple(element.element_id for element in self.elements)

    @property
    def element_counts(self) -> dict[str, int]:
        return {family: sum(element.family == family for element in self.elements) for family in SUPPORTED_DISTRIBUTED_FAMILIES}


def partition_generic_model(model: GenericDistributedModel, size: int) -> tuple[DistributedPartition, ...]:
    """Create deterministic contiguous element ownership without family branches."""

    size = int(size)
    if size <= 0:
        raise InputValidationError("Distributed partition size must be positive.")
    elements = tuple(model.iter_elements())
    element_owner = {
        element.element_id: min(size - 1, index * size // max(len(elements), 1))
        for index, element in enumerate(elements)
    }
    node_ranks: dict[int, set[int]] = defaultdict(set)
    for element in elements:
        rank = element_owner[element.element_id]
        for node in element.nodes:
            node_ranks[node].add(rank)
    node_owner = {node: min(ranks) for node, ranks in node_ranks.items()}
    partitions: list[DistributedPartition] = []
    constrained = _constrained_dofs(model)
    for rank in range(size):
        local_elements = tuple(element for element in elements if element_owner[element.element_id] == rank)
        local_nodes = np.asarray(sorted({node for element in local_elements for node in element.nodes}), dtype=np.int64)
        owned_nodes = np.asarray([node for node in local_nodes if node_owner[node] == rank], dtype=np.int64)
        ghost_nodes = np.asarray([node for node in local_nodes if node_owner[node] != rank], dtype=np.int64)
        interface_nodes = np.asarray(
            sorted(node for node in local_nodes if len(node_ranks[node]) > 1),
            dtype=np.int64,
        )
        neighbors = tuple(sorted({neighbor for node in interface_nodes for neighbor in node_ranks[node] if neighbor != rank}))
        dof_map = _build_dof_map(model.dofs, local_nodes, owned_nodes, ghost_nodes, constrained)
        partitions.append(
            DistributedPartition(
                rank=rank,
                size=size,
                elements=local_elements,
                local_node_ids=local_nodes,
                owned_node_ids=owned_nodes,
                ghost_node_ids=ghost_nodes,
                interface_node_ids=interface_nodes,
                neighboring_ranks=neighbors,
                element_owner=element_owner,
                node_owner=node_owner,
                dof_map=dof_map,
            )
        )
    validate_partitions(model, tuple(partitions))
    return tuple(partitions)


def validate_partitions(model: GenericDistributedModel, partitions: tuple[DistributedPartition, ...]) -> None:
    """Fail closed on lost/duplicated elements or incoherent local maps."""

    if not partitions:
        raise InputValidationError("At least one distributed partition is required.")
    expected = {element.element_id for element in model.iter_elements()}
    actual = [element.element_id for partition in partitions for element in partition.elements]
    if set(actual) != expected or len(actual) != len(set(actual)):
        raise InputValidationError("Distributed partitioning lost or duplicated an element.")
    if {partition.rank for partition in partitions} != set(range(len(partitions))):
        raise InputValidationError("Distributed partition ranks must be contiguous and unique.")
    expected_nodes = {node for element in model.iter_elements() for node in element.nodes}
    element_owners = {int(key): int(value) for key, value in partitions[0].element_owner.items()}
    node_owners = {int(key): int(value) for key, value in partitions[0].node_owner.items()}
    if set(element_owners) != expected or any(owner < 0 or owner >= len(partitions) for owner in element_owners.values()):
        raise InputValidationError("Distributed partition element ownership is invalid.")
    if set(node_owners) != expected_nodes or any(owner < 0 or owner >= len(partitions) for owner in node_owners.values()):
        raise InputValidationError("Distributed partition node ownership is invalid.")
    for partition in partitions:
        if partition.size != len(partitions):
            raise InputValidationError("Distributed partition sizes disagree.")
        if {int(key): int(value) for key, value in partition.element_owner.items()} != element_owners:
            raise InputValidationError("Distributed partition element-owner maps disagree.")
        if {int(key): int(value) for key, value in partition.node_owner.items()} != node_owners:
            raise InputValidationError("Distributed partition node-owner maps disagree.")
        if np.intersect1d(partition.owned_node_ids, partition.ghost_node_ids).size:
            raise InputValidationError("Distributed partition owned and ghost node sets overlap.")
        if not set(partition.interface_node_ids).issubset(set(partition.local_node_ids)):
            raise InputValidationError("Distributed partition interface nodes are not local.")
        if not np.array_equal(
            np.sort(np.concatenate((partition.owned_node_ids, partition.ghost_node_ids))),
            partition.local_node_ids,
        ):
            raise InputValidationError("Distributed partition local node map is incoherent.")
        for element in partition.elements:
            if element_owners.get(element.element_id) != partition.rank:
                raise InputValidationError("Distributed partition has an element with an invalid owner.")
            if any(node not in partition.dof_map.node_global_to_local for node in element.nodes):
                raise InputValidationError("Distributed partition element references a missing local node.")
    owner_counts = defaultdict(int)
    for partition in partitions:
        for node in partition.owned_node_ids:
            owner_counts[int(node)] += 1
    if set(owner_counts) != expected_nodes or any(count != 1 for count in owner_counts.values()):
        raise InputValidationError("Distributed node ownership is missing or duplicated.")


@dataclass(frozen=True)
class ElementContribution:
    """Dispatched local matrix and its family-aware global DOF map."""

    element_id: int
    family: str
    material: str
    region_id: int
    global_dofs: np.ndarray
    stiffness: np.ndarray


@dataclass(frozen=True)
class RankLocalDofMap:
    """Rank-local map that intentionally carries no global node/DOF arrays."""

    local_node_ids: np.ndarray
    owned_node_ids: np.ndarray
    ghost_node_ids: np.ndarray
    local_dof_ids: np.ndarray
    owned_dof_ids: np.ndarray
    ghost_dof_ids: np.ndarray
    constrained_dof_ids: np.ndarray
    node_global_to_local: Mapping[int, int]
    dof_global_to_local: Mapping[int, int]

    def __post_init__(self) -> None:
        arrays = {
            "local_node_ids": self.local_node_ids,
            "owned_node_ids": self.owned_node_ids,
            "ghost_node_ids": self.ghost_node_ids,
            "local_dof_ids": self.local_dof_ids,
            "owned_dof_ids": self.owned_dof_ids,
            "ghost_dof_ids": self.ghost_dof_ids,
            "constrained_dof_ids": self.constrained_dof_ids,
        }
        for name, raw in arrays.items():
            values = np.asarray(raw, dtype=np.int64)
            if values.ndim != 1 or np.unique(values).size != values.size:
                raise InputValidationError(f"Rank-local DOF map {name} must be a unique one-dimensional array.")
            object.__setattr__(self, name, values)
        if np.intersect1d(self.owned_node_ids, self.ghost_node_ids).size:
            raise InputValidationError("Rank-local DOF map owned and ghost nodes overlap.")
        if not np.array_equal(np.sort(np.concatenate((self.owned_node_ids, self.ghost_node_ids))), self.local_node_ids):
            raise InputValidationError("Rank-local nodes do not equal owned plus ghost nodes.")
        node_map = {int(key): int(value) for key, value in self.node_global_to_local.items()}
        dof_map = {int(key): int(value) for key, value in self.dof_global_to_local.items()}
        if set(node_map) != set(int(value) for value in self.local_node_ids) or set(node_map.values()) != set(range(self.local_node_ids.size)):
            raise InputValidationError("Rank-local node local/global mapping is invalid.")
        if set(dof_map) != set(int(value) for value in self.local_dof_ids) or set(dof_map.values()) != set(range(self.local_dof_ids.size)):
            raise InputValidationError("Rank-local DOF local/global mapping is invalid.")
        if not set(self.owned_dof_ids).issubset(set(self.local_dof_ids)) or not set(self.ghost_dof_ids).issubset(set(self.local_dof_ids)):
            raise InputValidationError("Rank-local owned or ghost DOFs are not local.")
        if not set(self.constrained_dof_ids).issubset(set(self.local_dof_ids)):
            raise InputValidationError("Rank-local constrained DOFs are not local.")
        object.__setattr__(self, "node_global_to_local", node_map)
        object.__setattr__(self, "dof_global_to_local", dof_map)


@dataclass(frozen=True)
class RankLocalElement:
    """One locally-owned element with descriptor-derived global DOF ids."""

    element_id: int
    family: str
    nodes: tuple[int, ...]
    global_dofs: np.ndarray
    material: str
    region_id: int

    def __post_init__(self) -> None:
        family = str(self.family).upper()
        if family not in SUPPORTED_DISTRIBUTED_FAMILIES:
            raise InputValidationError(f"Unsupported rank-local element family {family!r}.")
        spec = ElementRegistry.get(family)
        nodes = tuple(int(node) for node in self.nodes)
        global_dofs = np.asarray(self.global_dofs, dtype=np.int64)
        expected_count = spec.node_count * len(spec.dofs)
        if len(nodes) != spec.node_count or len(set(nodes)) != len(nodes):
            raise InputValidationError(f"{family} rank-local element {self.element_id} has invalid connectivity.")
        if global_dofs.shape != (expected_count,) or np.unique(global_dofs).size != global_dofs.size:
            raise InputValidationError(f"{family} rank-local element {self.element_id} has an invalid global DOF map.")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "global_dofs", global_dofs)
        object.__setattr__(self, "material", str(self.material))


@dataclass(frozen=True)
class OwnedNodalLoad:
    """A load record assigned exactly once to its node-owning rank."""

    load_id: int
    node: int
    global_dof: int
    value: float

    def __post_init__(self) -> None:
        if not np.isfinite(float(self.value)):
            raise InputValidationError("Rank-local load value must be finite.")


@dataclass(frozen=True)
class RankLocalModel:
    """Self-sufficient mixed data envelope for one future MPI rank.

    It contains neither the global connectivity nor a global coordinate or
    displacement array.  Values needed by a local element kernel are carried
    directly by this object or arrive through its owned/ghost DOF map.
    """

    rank: int
    size: int
    local_node_ids: np.ndarray
    node_coordinates: np.ndarray
    elements: tuple[RankLocalElement, ...]
    materials: Mapping[str, Mapping[str, Any]]
    node_owner: Mapping[int, int]
    element_owner: Mapping[int, int]
    dof_owner: Mapping[int, int]
    dof_map: RankLocalDofMap
    owned_fixed_dof_ids: np.ndarray
    owned_loads: tuple[OwnedNodalLoad, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        local_nodes = np.asarray(self.local_node_ids, dtype=np.int64)
        coordinates = np.asarray(self.node_coordinates, dtype=float)
        fixed = np.asarray(self.owned_fixed_dof_ids, dtype=np.int64)
        if local_nodes.ndim != 1 or np.unique(local_nodes).size != local_nodes.size:
            raise InputValidationError("Rank-local node ids must be a unique one-dimensional array.")
        if coordinates.shape != (local_nodes.size, 3) or not np.all(np.isfinite(coordinates)):
            raise InputValidationError("Rank-local coordinates must be finite with shape (local_nodes, 3).")
        if int(self.rank) < 0 or int(self.size) <= 0 or int(self.rank) >= int(self.size):
            raise InputValidationError("Rank-local rank/size values are invalid.")
        if not np.array_equal(local_nodes, self.dof_map.local_node_ids):
            raise InputValidationError("Rank-local nodes disagree with the rank-local DOF map.")
        node_owner = {int(key): int(value) for key, value in self.node_owner.items()}
        if set(node_owner) != set(int(value) for value in local_nodes):
            raise InputValidationError("Rank-local node ownership does not cover exactly local nodes.")
        dof_owner = {int(key): int(value) for key, value in self.dof_owner.items()}
        if set(dof_owner) != set(int(value) for value in self.dof_map.local_dof_ids):
            raise InputValidationError("Rank-local DOF ownership does not cover exactly local DOFs.")
        material_data = {str(key): dict(value) for key, value in self.materials.items()}
        local_node_set = set(int(value) for value in local_nodes)
        for element in self.elements:
            if any(node not in local_node_set for node in element.nodes):
                raise InputValidationError("Rank-local element references a non-local node.")
            if element.material not in material_data:
                raise InputValidationError(f"Rank-local element references unknown material {element.material!r}.")
            if self.element_owner.get(element.element_id) != int(self.rank):
                raise InputValidationError("Rank-local element does not belong to this rank.")
        if fixed.ndim != 1 or np.unique(fixed).size != fixed.size or not set(fixed).issubset(set(self.dof_map.owned_dof_ids)):
            raise InputValidationError("Rank-local fixed DOFs must be unique owned DOFs.")
        if len({load.load_id for load in self.owned_loads}) != len(self.owned_loads):
            raise InputValidationError("Rank-local load ids must be unique.")
        for load in self.owned_loads:
            if load.node not in local_node_set or self.node_owner[load.node] != int(self.rank):
                raise InputValidationError("Rank-local load is not assigned to its node owner.")
            if load.global_dof not in set(self.dof_map.owned_dof_ids):
                raise InputValidationError("Rank-local load is not assigned to an owned DOF.")
        object.__setattr__(self, "local_node_ids", local_nodes)
        object.__setattr__(self, "node_coordinates", coordinates)
        object.__setattr__(self, "materials", material_data)
        object.__setattr__(self, "node_owner", node_owner)
        object.__setattr__(self, "element_owner", {int(key): int(value) for key, value in self.element_owner.items()})
        object.__setattr__(self, "dof_owner", dof_owner)
        object.__setattr__(self, "owned_fixed_dof_ids", fixed)
        object.__setattr__(self, "owned_loads", tuple(self.owned_loads))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def coordinates_for(self, nodes: tuple[int, ...]) -> np.ndarray:
        try:
            positions = [self.dof_map.node_global_to_local[int(node)] for node in nodes]
        except KeyError as exc:
            raise InputValidationError("Rank-local element requested a missing node coordinate.") from exc
        return self.node_coordinates[positions]


@dataclass(frozen=True)
class LocalAssemblyPacket:
    """Local-to-global insertions consumable by a future PETSc adapter."""

    rank: int
    owned_row_ids: np.ndarray
    row_ids: np.ndarray
    column_ids: np.ndarray
    values: np.ndarray
    contributions: tuple[ElementContribution, ...]

    def __post_init__(self) -> None:
        rows = np.asarray(self.row_ids, dtype=np.int64)
        columns = np.asarray(self.column_ids, dtype=np.int64)
        values = np.asarray(self.values, dtype=float)
        owned_rows = np.asarray(self.owned_row_ids, dtype=np.int64)
        if rows.ndim != 1 or columns.shape != rows.shape or values.shape != rows.shape:
            raise InputValidationError("Local assembly packet row, column and value arrays must have matching one-dimensional shapes.")
        if not np.all(np.isfinite(values)) or np.unique(owned_rows).size != owned_rows.size:
            raise InputValidationError("Local assembly packet contains invalid values or owned rows.")
        object.__setattr__(self, "row_ids", rows)
        object.__setattr__(self, "column_ids", columns)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "owned_row_ids", owned_rows)
        object.__setattr__(self, "contributions", tuple(self.contributions))


@dataclass(frozen=True)
class ElementResultRecord:
    """Family-aware element output record for a future scalable post-process."""

    element_id: int
    family: str
    material: str
    region_id: int
    fields: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        family = str(self.family).upper()
        if family not in SUPPORTED_DISTRIBUTED_FAMILIES:
            raise InputValidationError(f"Unsupported distributed result family {family!r}.")
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "fields", dict(self.fields))


@dataclass(frozen=True)
class FamilyAwareResults:
    """Minimal result envelope separating nodal and family-specific fields."""

    nodal_displacement: np.ndarray
    element_results: tuple[ElementResultRecord, ...]

    def __post_init__(self) -> None:
        displacement = np.asarray(self.nodal_displacement, dtype=float)
        if displacement.ndim != 2 or displacement.shape[1] != len(TRANSLATION_DOFS):
            raise InputValidationError("Family-aware nodal displacement must have shape (n_nodes, 3).")
        ids = [result.element_id for result in self.element_results]
        if len(ids) != len(set(ids)):
            raise InputValidationError("Family-aware element results must have unique element ids.")
        object.__setattr__(self, "nodal_displacement", displacement)
        object.__setattr__(self, "element_results", tuple(self.element_results))


def build_result_schema(
    model: GenericDistributedModel,
    displacement: np.ndarray,
    *,
    element_fields: Mapping[int, Mapping[str, Any]] | None = None,
) -> FamilyAwareResults:
    """Build the architecture-only result envelope without computing fields."""

    values = np.asarray(displacement, dtype=float)
    if values.shape == (model.ndof,):
        nodal = np.zeros((model.node_count, len(TRANSLATION_DOFS)), dtype=float)
        for node in range(model.node_count):
            for component, name in enumerate(TRANSLATION_DOFS):
                if model.dofs.has(node, name):
                    nodal[node, component] = values[model.dofs.index(node, name)]
    elif values.shape == (model.node_count, len(TRANSLATION_DOFS)):
        nodal = values.copy()
    else:
        raise InputValidationError("Displacement must be a global DOF vector or a nodal (n, 3) array.")
    fields = element_fields or {}
    records = tuple(
        ElementResultRecord(
            element_id=element.element_id,
            family=element.family,
            material=element.material,
            region_id=element.region_id,
            fields=fields.get(element.element_id, {}),
        )
        for element in model.iter_elements()
    )
    return FamilyAwareResults(nodal_displacement=nodal, element_results=records)


def dispatch_element(model: GenericDistributedModel, element: DistributedElement) -> ElementContribution:
    """Dispatch a local kernel through ``ElementRegistry`` without fixed sizes."""

    spec: ElementSpec = ElementRegistry.get(element.family)
    if len(element.nodes) != spec.node_count:
        raise InputValidationError(f"{element.family} element {element.element_id} has invalid connectivity length.")
    coordinates = model.nodes[list(element.nodes)]
    material = MaterialFactory.create(dict(model.materials[element.material]))
    kernel = spec.factory(material)
    local_matrix = np.asarray(kernel.stiffness(coordinates), dtype=float)
    local_dof_count = len(element.nodes) * len(spec.dofs)
    expected_shape = (local_dof_count, local_dof_count)
    if local_matrix.shape != expected_shape:
        raise InputValidationError(
            f"{element.family} dispatch returned {local_matrix.shape}; expected descriptor-derived {expected_shape}."
        )
    global_dofs = np.asarray(
        [index for node in element.nodes for index in model.dofs.node_indices(node, spec.dofs)],
        dtype=np.int64,
    )
    return ElementContribution(
        element_id=element.element_id,
        family=element.family,
        material=element.material,
        region_id=element.region_id,
        global_dofs=global_dofs,
        stiffness=local_matrix,
    )


def build_rank_local_model(model: GenericDistributedModel, partition: DistributedPartition) -> RankLocalModel:
    """Materialize only one partition's data for a future MPI rank.

    ``GenericDistributedModel`` is allowed here solely as the serial
    partitioning source.  The returned envelope is intentionally independent
    from it: local dispatch, preallocation, load insertion and reaction
    packets do not retain or consult the global model.
    """

    validate_partitions(model, (partition,)) if partition.size == 1 else None
    local_nodes = np.asarray(partition.local_node_ids, dtype=np.int64)
    constrained = set(int(value) for value in _constrained_dofs(model))
    local_dofs = np.asarray(
        sorted(index for node in local_nodes for index in model.dofs.node_indices(int(node), model.dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    owned_dofs = np.asarray(
        sorted(index for node in partition.owned_node_ids for index in model.dofs.node_indices(int(node), model.dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    ghost_dofs = np.asarray(
        sorted(index for node in partition.ghost_node_ids for index in model.dofs.node_indices(int(node), model.dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    rank_dof_map = RankLocalDofMap(
        local_node_ids=local_nodes,
        owned_node_ids=partition.owned_node_ids,
        ghost_node_ids=partition.ghost_node_ids,
        local_dof_ids=local_dofs,
        owned_dof_ids=owned_dofs,
        ghost_dof_ids=ghost_dofs,
        constrained_dof_ids=np.asarray(sorted(constrained.intersection(local_dofs)), dtype=np.int64),
        node_global_to_local={int(node): index for index, node in enumerate(local_nodes)},
        dof_global_to_local={int(dof): index for index, dof in enumerate(local_dofs)},
    )
    local_elements = tuple(
        RankLocalElement(
            element_id=element.element_id,
            family=element.family,
            nodes=element.nodes,
            global_dofs=np.asarray(
                [index for node in element.nodes for index in model.dofs.node_indices(node, ElementRegistry.get(element.family).dofs)],
                dtype=np.int64,
            ),
            material=element.material,
            region_id=element.region_id,
        )
        for element in partition.elements
    )
    local_materials = {
        element.material: dict(model.materials[element.material])
        for element in local_elements
    }
    owned_loads = tuple(
        OwnedNodalLoad(
            load_id=index,
            node=int(load.node),
            global_dof=model.dofs.index(load.node, load.dof),
            value=float(load.value),
        )
        for index, load in enumerate(model.loads)
        if partition.node_owner[int(load.node)] == partition.rank
    )
    owned_fixed = np.asarray(
        sorted(
            model.dofs.index(condition.node, name)
            for condition in model.fixed_dofs
            for name in condition.dofs
            if partition.node_owner[int(condition.node)] == partition.rank
        ),
        dtype=np.int64,
    )
    dof_owner = {
        model.dofs.index(int(node), name): int(partition.node_owner[int(node)])
        for node in local_nodes
        for name in model.dofs.node_dofs[int(node)]
    }
    return RankLocalModel(
        rank=partition.rank,
        size=partition.size,
        local_node_ids=local_nodes,
        node_coordinates=np.asarray(model.nodes[local_nodes], dtype=float).copy(),
        elements=local_elements,
        materials=local_materials,
        node_owner={int(node): int(partition.node_owner[int(node)]) for node in local_nodes},
        element_owner={element.element_id: partition.rank for element in local_elements},
        dof_owner=dof_owner,
        dof_map=rank_dof_map,
        owned_fixed_dof_ids=owned_fixed,
        owned_loads=owned_loads,
        metadata={"source": "partition_generic_model", "global_model_retained": False},
    )


def dispatch_rank_local_element(model: RankLocalModel, element: RankLocalElement) -> ElementContribution:
    """Dispatch one local element without access to a global model envelope."""

    spec: ElementSpec = ElementRegistry.get(element.family)
    expected_shape = (len(element.nodes) * len(spec.dofs),) * 2
    coordinates = model.coordinates_for(element.nodes)
    material = MaterialFactory.create(dict(model.materials[element.material]))
    stiffness = np.asarray(spec.factory(material).stiffness(coordinates), dtype=float)
    if stiffness.shape != expected_shape:
        raise InputValidationError(
            f"{element.family} rank-local dispatch returned {stiffness.shape}; expected {expected_shape}."
        )
    return ElementContribution(
        element_id=element.element_id,
        family=element.family,
        material=element.material,
        region_id=element.region_id,
        global_dofs=element.global_dofs.copy(),
        stiffness=stiffness,
    )


def rank_local_assembly_packet(model: RankLocalModel) -> LocalAssemblyPacket:
    """Create ordered local-to-global stiffness insertions without a gather."""

    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    contributions: list[ElementContribution] = []
    for element in sorted(model.elements, key=lambda item: item.element_id):
        contribution = dispatch_rank_local_element(model, element)
        contributions.append(contribution)
        dofs = contribution.global_dofs
        rows.extend(np.repeat(dofs, dofs.size).tolist())
        columns.extend(np.tile(dofs, dofs.size).tolist())
        values.extend(contribution.stiffness.reshape(-1).tolist())
    return LocalAssemblyPacket(
        rank=model.rank,
        owned_row_ids=model.dof_map.owned_dof_ids.copy(),
        row_ids=np.asarray(rows, dtype=np.int64),
        column_ids=np.asarray(columns, dtype=np.int64),
        values=np.asarray(values, dtype=float),
        contributions=tuple(contributions),
    )


def recompose_local_assembly_packets(packets: Iterable[LocalAssemblyPacket], ndof: int) -> csr_matrix:
    """Debug-only serial reconstruction of locally-produced insertion packets."""

    packet_rows = list(packets)
    if ndof < 0 or len({packet.rank for packet in packet_rows}) != len(packet_rows):
        raise InputValidationError("Local assembly packets have invalid global size or duplicate ranks.")
    rows = np.concatenate([packet.row_ids for packet in packet_rows]) if packet_rows else np.zeros(0, dtype=np.int64)
    columns = np.concatenate([packet.column_ids for packet in packet_rows]) if packet_rows else np.zeros(0, dtype=np.int64)
    values = np.concatenate([packet.values for packet in packet_rows]) if packet_rows else np.zeros(0, dtype=float)
    matrix = coo_matrix((values, (rows, columns)), shape=(int(ndof), int(ndof))).tocsr()
    matrix.sum_duplicates()
    return matrix


def rank_local_preallocation_metadata(model: RankLocalModel) -> dict[str, Any]:
    """Derive provisional row patterns from this rank's owned elements only.

    Exact owned-row metadata is obtained by
    :func:`exchange_preallocation_metadata`, which routes these local patterns
    to each row owner without transferring the model globally.
    """

    row_columns: dict[int, set[int]] = defaultdict(set)
    family_counts = {family: 0 for family in SUPPORTED_DISTRIBUTED_FAMILIES}
    for element in model.elements:
        family_counts[element.family] += 1
        for row in element.global_dofs:
            row_columns[int(row)].update(int(column) for column in element.global_dofs)
    owned_rows = sorted(int(value) for value in model.dof_map.owned_dof_ids)
    diag = []
    offdiag = []
    for row in owned_rows:
        columns = row_columns.get(row, set())
        diag.append(sum(model.dof_owner[column] == model.rank for column in columns))
        offdiag.append(sum(model.dof_owner[column] != model.rank for column in columns))
    return {
        "strategy": "connectivity_exact_family_aware_rank_local",
        "rank": model.rank,
        "owned_row_ids": owned_rows,
        "diag_nnz_per_owned_row": diag,
        "offdiag_nnz_per_owned_row": offdiag,
        "max_diag_nnz": max(diag, default=0),
        "max_offdiag_nnz": max(offdiag, default=0),
        "ghost_coupling_rows": sum(value > 0 for value in offdiag),
        "reallocations_expected": 0,
        "family_element_counts": family_counts,
        "global_connectivity_required": False,
        "owned_row_pattern_complete": False,
    }


def exchange_preallocation_metadata(models: Iterable[RankLocalModel]) -> tuple[dict[str, Any], ...]:
    """Simulate the row-owner sparsity exchange required by a PETSc adapter.

    Each rank contributes only connectivity-derived row/column pairs for its
    owned elements.  Pairs are routed to their row owner; no rank requires the
    global connectivity or global matrix.  The collective list exists solely
    in this backend-neutral test harness and maps directly to an MPI all-to-all
    exchange in WP13-01C.
    """

    local_models = sorted(tuple(models), key=lambda item: item.rank)
    if not local_models:
        raise InputValidationError("Preallocation exchange requires at least one rank-local model.")
    size = local_models[0].size
    if len(local_models) != size or {model.rank for model in local_models} != set(range(size)):
        raise InputValidationError("Preallocation exchange has inconsistent rank-local models.")
    incoming: dict[int, dict[int, dict[int, int]]] = {
        rank: defaultdict(dict) for rank in range(size)
    }
    family_counts: dict[int, dict[str, int]] = {
        rank: {family: 0 for family in SUPPORTED_DISTRIBUTED_FAMILIES} for rank in range(size)
    }
    for model in local_models:
        for element in model.elements:
            family_counts[model.rank][element.family] += 1
            for row in element.global_dofs:
                destination = model.dof_owner[int(row)]
                columns = incoming[destination][int(row)]
                for column in element.global_dofs:
                    columns[int(column)] = model.dof_owner[int(column)]
    metadata: list[dict[str, Any]] = []
    for model in local_models:
        owned_rows = [int(value) for value in model.dof_map.owned_dof_ids]
        rows = incoming[model.rank]
        if set(rows) != set(owned_rows):
            raise InputValidationError("Preallocation row-owner exchange lost an owned row pattern.")
        diag = []
        offdiag = []
        for row in owned_rows:
            columns = rows[row]
            diag.append(sum(owner == model.rank for owner in columns.values()))
            offdiag.append(sum(owner != model.rank for owner in columns.values()))
        metadata.append({
            "strategy": "connectivity_exact_family_aware_row_owner_exchange",
            "rank": model.rank,
            "owned_row_ids": owned_rows,
            "diag_nnz_per_owned_row": diag,
            "offdiag_nnz_per_owned_row": offdiag,
            "max_diag_nnz": max(diag, default=0),
            "max_offdiag_nnz": max(offdiag, default=0),
            "ghost_coupling_rows": sum(value > 0 for value in offdiag),
            "reallocations_expected": 0,
            "family_element_counts": family_counts[model.rank],
            "global_connectivity_required": False,
            "owned_row_pattern_complete": True,
        })
    return tuple(metadata)


def rank_local_load_packet(model: RankLocalModel) -> dict[int, float]:
    """Return owned nodal loads once, ready for local-to-global vector insertion."""

    values: dict[int, float] = defaultdict(float)
    for load in model.owned_loads:
        values[int(load.global_dof)] += float(load.value)
    return dict(sorted(values.items()))


def rank_local_reaction_packet(
    model: RankLocalModel,
    local_displacement: Mapping[int, float],
) -> dict[int, float]:
    """Produce local ``K*u-F`` residual contributions without a global vector."""

    values = {int(key): float(value) for key, value in local_displacement.items()}
    required = set(int(value) for value in model.dof_map.local_dof_ids)
    if not required.issubset(values) or not all(np.isfinite(values[dof]) for dof in required):
        raise InputValidationError("Rank-local reaction packet requires finite values for every local and ghost DOF.")
    residual: dict[int, float] = defaultdict(float)
    for element in model.elements:
        contribution = dispatch_rank_local_element(model, element)
        local_u = np.asarray([values[int(dof)] for dof in contribution.global_dofs], dtype=float)
        for dof, value in zip(contribution.global_dofs, contribution.stiffness @ local_u, strict=True):
            residual[int(dof)] += float(value)
    for dof, value in rank_local_load_packet(model).items():
        residual[int(dof)] -= float(value)
    return dict(sorted(residual.items()))


def shadow_assemble(
    model: GenericDistributedModel,
    partitions: tuple[DistributedPartition, ...],
) -> tuple[csr_matrix, tuple[ElementContribution, ...]]:
    """Recompose rank-local contributions for architecture-only validation."""

    validate_partitions(model, partitions)
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []
    contributions: list[ElementContribution] = []
    for partition in partitions:
        for element in partition.elements:
            contribution = dispatch_element(model, element)
            contributions.append(contribution)
            dofs = contribution.global_dofs
            rows.extend(np.repeat(dofs, dofs.size).tolist())
            cols.extend(np.tile(dofs, dofs.size).tolist())
            values.extend(contribution.stiffness.reshape(-1).tolist())
    matrix = coo_matrix((values, (rows, cols)), shape=(model.ndof, model.ndof)).tocsr()
    matrix.sum_duplicates()
    return matrix, tuple(sorted(contributions, key=lambda item: item.element_id))


def preallocation_metadata(partition: DistributedPartition, model: GenericDistributedModel) -> dict[str, Any]:
    """Build exact row patterns from real connectivity for a future PETSc adapter."""

    owner_by_dof = _owner_by_dof(partition, model.dofs)
    row_columns: dict[int, set[int]] = defaultdict(set)
    family_counts = {family: 0 for family in SUPPORTED_DISTRIBUTED_FAMILIES}
    for element in partition.elements:
        family_counts[element.family] += 1
        contribution = dispatch_element(model, element)
        for row in contribution.global_dofs:
            row_columns[int(row)].update(int(column) for column in contribution.global_dofs)
    owned_rows = sorted(row for row, owner in owner_by_dof.items() if owner == partition.rank)
    diag = []
    offdiag = []
    for row in owned_rows:
        columns = row_columns.get(row, set())
        diag.append(sum(owner_by_dof[column] == partition.rank for column in columns))
        offdiag.append(sum(owner_by_dof[column] != partition.rank for column in columns))
    return {
        "strategy": "connectivity_exact_family_aware",
        "rank": partition.rank,
        "owned_row_ids": owned_rows,
        "diag_nnz_per_owned_row": diag,
        "offdiag_nnz_per_owned_row": offdiag,
        "max_diag_nnz": max(diag, default=0),
        "max_offdiag_nnz": max(offdiag, default=0),
        "ghost_coupling_rows": sum(value > 0 for value in offdiag),
        "reallocations_expected": 0,
        "family_element_counts": family_counts,
    }


def boundary_ownership(
    model: GenericDistributedModel,
    partitions: tuple[DistributedPartition, ...],
) -> dict[str, Any]:
    """Assign each constrained/load DOF to exactly one node owner."""

    validate_partitions(model, partitions)
    node_owner = partitions[0].node_owner
    fixed_by_rank: dict[int, list[int]] = defaultdict(list)
    load_by_rank: dict[int, list[int]] = defaultdict(list)
    fixed_records: list[dict[str, int]] = []
    load_records: list[dict[str, int | float]] = []
    for condition in model.fixed_dofs:
        for name in condition.dofs:
            dof = model.dofs.index(condition.node, name)
            rank = node_owner[int(condition.node)]
            fixed_by_rank[rank].append(dof)
            fixed_records.append({"node": int(condition.node), "dof": int(dof), "rank": rank})
    for index, load in enumerate(model.loads):
        dof = model.dofs.index(load.node, load.dof)
        rank = node_owner[int(load.node)]
        load_by_rank[rank].append(dof)
        load_records.append({"index": index, "node": int(load.node), "dof": int(dof), "rank": rank, "value": float(load.value)})
    duplicate_fixed = len(fixed_records) != len({item["dof"] for item in fixed_records})
    duplicate_load_records = len(load_records) != len({item["index"] for item in load_records})
    if duplicate_fixed:
        raise InputValidationError("Distributed boundary ownership received duplicate constrained DOFs.")
    if duplicate_load_records:
        raise InputValidationError("Distributed boundary ownership duplicated a nodal-load record.")
    return {
        "fixed": fixed_records,
        "loads": load_records,
        "fixed_by_rank": {str(rank): sorted(values) for rank, values in fixed_by_rank.items()},
        "loads_by_rank": {str(rank): values for rank, values in load_by_rank.items()},
        "duplicate_fixed_ownership": duplicate_fixed,
        "duplicate_load_ownership": duplicate_load_records,
    }


def reduce_reactions(
    local_contributions: Mapping[int, Mapping[int, float]],
    dof_owner: Mapping[int, int],
) -> dict[int, dict[str, float | int]]:
    """Define the future local-contribution -> owner reduction contract."""

    totals: dict[int, float] = defaultdict(float)
    for rank, values in local_contributions.items():
        for dof, value in values.items():
            dof = int(dof)
            if dof not in dof_owner:
                raise InputValidationError(f"Reaction contribution DOF {dof} has no owner.")
            if not np.isfinite(float(value)):
                raise InputValidationError("Non-finite distributed reaction contribution.")
            totals[dof] += float(value)
    return {
        dof: {"owner": int(dof_owner[dof]), "value": float(value)}
        for dof, value in sorted(totals.items())
    }


def _build_dof_map(
    dofs: DofManager,
    local_nodes: np.ndarray,
    owned_nodes: np.ndarray,
    ghost_nodes: np.ndarray,
    constrained: np.ndarray,
) -> DistributedDofMap:
    global_nodes = np.asarray(sorted(dofs.node_dofs), dtype=np.int64)
    global_dof_ids = np.asarray(sorted(dofs._indices.values()), dtype=np.int64)
    local_dof_ids = np.asarray(
        sorted(index for node in local_nodes for index in dofs.node_indices(int(node), dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    owned_dof_ids = np.asarray(
        sorted(index for node in owned_nodes for index in dofs.node_indices(int(node), dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    ghost_dof_ids = np.asarray(
        sorted(index for node in ghost_nodes for index in dofs.node_indices(int(node), dofs.node_dofs[int(node)])),
        dtype=np.int64,
    )
    return DistributedDofMap(
        global_node_ids=global_nodes,
        local_node_ids=np.asarray(local_nodes, dtype=np.int64),
        owned_node_ids=np.asarray(owned_nodes, dtype=np.int64),
        ghost_node_ids=np.asarray(ghost_nodes, dtype=np.int64),
        global_dof_ids=global_dof_ids,
        local_dof_ids=local_dof_ids,
        owned_dof_ids=owned_dof_ids,
        ghost_dof_ids=ghost_dof_ids,
        constrained_dof_ids=np.asarray(constrained, dtype=np.int64),
        node_global_to_local={int(node): index for index, node in enumerate(local_nodes)},
        dof_global_to_local={int(dof): index for index, dof in enumerate(local_dof_ids)},
    )


def _constrained_dofs(model: GenericDistributedModel) -> np.ndarray:
    values = [model.dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
    return np.asarray(sorted(set(values)), dtype=np.int64)


def _owner_by_dof(partition: DistributedPartition, dofs: DofManager) -> dict[int, int]:
    result: dict[int, int] = {}
    for node, owner in partition.node_owner.items():
        for dof in dofs.node_dofs[int(node)]:
            result[dofs.index(int(node), dof)] = int(owner)
    return result
