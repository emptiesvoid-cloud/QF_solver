"""Family-aware distributed architecture for the WP13 mixed-solid bridge.

This module is an architecture layer, not a PETSc backend.  It deliberately
keeps the existing TET4 large route untouched while providing a fail-closed,
partition-testable representation for TET4/WEDGE6/HEX8.  The shadow assembly
is used only by targeted WP13 validation; it is not a new solver route.
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
        object.__setattr__(self, "node_global_to_local", dict(self.node_global_to_local))
        object.__setattr__(self, "dof_global_to_local", dict(self.dof_global_to_local))

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
    for partition in partitions:
        if partition.size != len(partitions):
            raise InputValidationError("Distributed partition sizes disagree.")
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
            if any(node not in partition.dof_map.node_global_to_local for node in element.nodes):
                raise InputValidationError("Distributed partition element references a missing local node.")
    owner_counts = defaultdict(int)
    for partition in partitions:
        for node in partition.owned_node_ids:
            owner_counts[int(node)] += 1
    expected_nodes = {node for element in model.iter_elements() for node in element.nodes}
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
    return {
        "fixed": fixed_records,
        "loads": load_records,
        "fixed_by_rank": {str(rank): sorted(values) for rank, values in fixed_by_rank.items()},
        "loads_by_rank": {str(rank): values for rank, values in load_by_rank.items()},
        "duplicate_fixed_ownership": False,
        "duplicate_load_ownership": False,
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
            if int(dof_owner[dof]) != int(rank) and not np.isfinite(float(value)):
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
