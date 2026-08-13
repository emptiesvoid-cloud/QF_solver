"""Generic finite element model entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from solveur.contact.entities import FrictionlessContact
from solveur.core.analysis import AnalysisSettings
from solveur.core.constraints import ConstraintTerm, LinearConstraint
from solveur.core.dofs import DOF_ORDER, DofManager, normalize_dof_name
from solveur.core.errors import InputValidationError
from solveur.core.rbe import Rbe2Definition, Rbe3Definition, rbe2_constraints, rbe3_constraints
from solveur.elements.registry import ElementRegistry
from solveur.elements.discrete import ConcentratedMass, SpringDefinition
from solveur.loads.entities import DistributedLoad, parse_distributed_loads


@dataclass(frozen=True)
class ElementDefinition:
    """Connectivity and material reference for one finite element."""

    type: str
    nodes: tuple[int, ...]
    material: str


@dataclass(frozen=True)
class BoundaryCondition:
    """A set of fixed named dofs on one node."""

    node: int
    dofs: tuple[str, ...]


@dataclass(frozen=True)
class NodalLoad:
    """A scalar nodal load applied to one named dof."""

    node: int
    dof: str
    value: float


@dataclass
class FiniteElementModel:
    """Input model independent from CLI, JSON and solver implementation."""

    nodes: np.ndarray
    elements: list[ElementDefinition]
    materials: dict[str, dict[str, Any]]
    fixed_dofs: list[BoundaryCondition] = field(default_factory=list)
    loads: list[NodalLoad] = field(default_factory=list)
    distributed_loads: list[DistributedLoad] = field(default_factory=list)
    springs: list[SpringDefinition] = field(default_factory=list)
    concentrated_masses: list[ConcentratedMass] = field(default_factory=list)
    multipoint_constraints: list[LinearConstraint] = field(default_factory=list)
    rbe2: list[Rbe2Definition] = field(default_factory=list)
    rbe3: list[Rbe3Definition] = field(default_factory=list)
    contacts: list[FrictionlessContact] = field(default_factory=list)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)
    schema_version: int = 1
    units: dict[str, str] = field(default_factory=lambda: {"system": "SI"})
    verification_profile: str = "engineering"

    def __post_init__(self) -> None:
        self.nodes = np.asarray(self.nodes, dtype=float)
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("nodes must have shape (n, 3).")
        if not isinstance(self.analysis, AnalysisSettings):
            self.analysis = AnalysisSettings.from_raw(self.analysis)
        self.analysis.validate()
        self.schema_version = int(self.schema_version or 1)
        self.units = dict(self.units or {"system": "SI"})
        self.verification_profile = str(self.verification_profile or "engineering").lower()

    @property
    def node_count(self) -> int:
        return int(self.nodes.shape[0])

    def dof_manager(self) -> DofManager:
        requirements: dict[int, set[str]] = {node: set() for node in range(self.node_count)}
        for element in self.elements:
            spec = ElementRegistry.get(element.type)
            for node in element.nodes:
                requirements[int(node)].update(spec.dofs)
        for spring in self.springs:
            requirements[spring.node_a].update(spring.active_dofs())
            if spring.node_b is not None:
                requirements[spring.node_b].update(spring.active_dofs())
        for mass in self.concentrated_masses:
            requirements[mass.node].update(mass.active_dofs())
        for contact in self.contacts:
            requirements[contact.slave_node].update(("UX", "UY", "UZ"))
            for node in contact.referenced_master_nodes:
                requirements[node].update(("UX", "UY", "UZ"))
        for constraint in self.linear_constraints():
            for term in constraint.terms:
                requirements[term.node].add(normalize_dof_name(term.dof))
        return DofManager.from_node_requirements(requirements)

    def linear_constraints(self) -> list[LinearConstraint]:
        """Return direct MPCs and generated RBE relations in a single solver form."""
        constraints = list(self.multipoint_constraints)
        for definition in self.rbe2:
            constraints.extend(rbe2_constraints(self.nodes, definition))
        for definition in self.rbe3:
            constraints.extend(rbe3_constraints(self.nodes, definition))
        return constraints

    @classmethod
    def from_raw(
        cls,
        *,
        nodes: list[list[float]],
        elements: list[dict[str, Any]],
        materials: dict[str, dict[str, Any]],
        fixed_dofs: list[dict[str, Any]] | None = None,
        loads: list[dict[str, Any]] | None = None,
        distributed_loads: list[dict[str, Any]] | None = None,
        springs: list[dict[str, Any]] | None = None,
        concentrated_masses: list[dict[str, Any]] | None = None,
        multipoint_constraints: list[dict[str, Any]] | None = None,
        rbe2: list[dict[str, Any]] | None = None,
        rbe3: list[dict[str, Any]] | None = None,
        contacts: list[dict[str, Any]] | None = None,
        analysis: str | dict[str, Any] | None = "linear_static",
        schema_version: int = 1,
        units: dict[str, str] | None = None,
        verification_profile: str = "engineering",
    ) -> "FiniteElementModel":
        parsed_elements = [
            ElementDefinition(
                type=str(item["type"]).upper(),
                nodes=tuple(int(node) for node in item["nodes"]),
                material=str(item["material"]),
            )
            for item in elements
        ]
        parsed_fixed = [
            BoundaryCondition(
                node=int(item["node"]),
                dofs=tuple(normalize_dof_name(dof) for dof in item["dofs"]),
            )
            for item in fixed_dofs or []
        ]
        parsed_loads = [
            NodalLoad(
                node=int(item["node"]),
                dof=normalize_dof_name(item["dof"]),
                value=float(item["value"]),
            )
            for item in loads or []
        ]
        try:
            parsed_distributed_loads = parse_distributed_loads(distributed_loads)
        except ValueError as exc:
            raise InputValidationError(str(exc)) from exc
        parsed_springs = [_parse_spring(item) for item in springs or []]
        parsed_masses = [_parse_mass(item) for item in concentrated_masses or []]
        parsed_constraints = [_parse_constraint(item) for item in multipoint_constraints or []]
        parsed_rbe2 = [_parse_rbe2(item) for item in rbe2 or []]
        parsed_rbe3 = [_parse_rbe3(item) for item in rbe3 or []]
        parsed_contacts = [_parse_contact(item) for item in contacts or []]
        return cls(
            nodes=np.asarray(nodes, dtype=float),
            elements=parsed_elements,
            materials=materials,
            fixed_dofs=parsed_fixed,
            loads=parsed_loads,
            distributed_loads=parsed_distributed_loads,
            springs=parsed_springs,
            concentrated_masses=parsed_masses,
            multipoint_constraints=parsed_constraints,
            rbe2=parsed_rbe2,
            rbe3=parsed_rbe3,
            contacts=parsed_contacts,
            analysis=AnalysisSettings.from_raw(analysis),
            schema_version=schema_version,
            units=units or {"system": "SI"},
            verification_profile=verification_profile,
        )


def _parse_spring(item: dict[str, Any]) -> SpringDefinition:
    dofs = tuple(normalize_dof_name(name) for name in item["dofs"])
    raw = item.get("stiffness_matrix", item.get("stiffness"))
    if isinstance(raw, (int, float)):
        matrix = np.diag([float(raw)] * len(dofs))
    else:
        values = np.asarray(raw, dtype=float)
        matrix = np.diag(values) if values.ndim == 1 else values
    orientation = item.get("orientation")
    return SpringDefinition(
        node_a=int(item["node_a"]),
        node_b=int(item["node_b"]) if item.get("node_b") is not None else None,
        dofs=dofs,
        stiffness=tuple(tuple(float(value) for value in row) for row in matrix),
        coordinate_system=str(item.get("coordinate_system", "global")).lower(),
        orientation=(
            tuple(tuple(float(value) for value in row) for row in orientation)
            if orientation is not None
            else None
        ),
    )


def _parse_mass(item: dict[str, Any]) -> ConcentratedMass:
    inertia = item.get("inertia")
    return ConcentratedMass(
        node=int(item["node"]),
        mass=float(item["mass"]),
        center_of_mass=tuple(float(value) for value in item.get("center_of_mass", (0.0, 0.0, 0.0))),
        inertia=(
            tuple(tuple(float(value) for value in row) for row in inertia)
            if inertia is not None
            else None
        ),
    )


def _parse_constraint(item: dict[str, Any]) -> LinearConstraint:
    return LinearConstraint(
        terms=tuple(
            ConstraintTerm(
                node=int(term["node"]),
                dof=normalize_dof_name(term["dof"]),
                coefficient=float(term["coefficient"]),
            )
            for term in item["terms"]
        ),
        value=float(item.get("value", 0.0)),
        name=str(item.get("name", "")),
    )


def _parse_rbe2(item: dict[str, Any]) -> Rbe2Definition:
    return Rbe2Definition(
        master=int(item["master"]),
        slaves=tuple(int(node) for node in item["slaves"]),
        tie_rotations=bool(item.get("tie_rotations", False)),
        name=str(item.get("name", "")),
    )


def _parse_rbe3(item: dict[str, Any]) -> Rbe3Definition:
    return Rbe3Definition(
        reference=int(item["reference"]),
        independents=tuple((int(entry["node"]), float(entry["weight"])) for entry in item["independents"]),
        dofs=tuple(normalize_dof_name(name) for name in item.get("dofs", DOF_ORDER)),
        mode=str(item.get("mode", "rigid_body_projection")).lower(),
        name=str(item.get("name", "")),
    )


def _parse_contact(item: dict[str, Any]) -> FrictionlessContact:
    raw_faces = item.get("master_faces")
    if raw_faces is not None:
        if not isinstance(raw_faces, list) or not raw_faces:
            raise InputValidationError("A contact master surface needs one or more triangular faces.")
        parsed_faces = tuple(
            (int(face[0]), int(face[1]), int(face[2]))
            for face in raw_faces
            if isinstance(face, list) and len(face) == 3
        )
        if len(parsed_faces) != len(raw_faces):
            raise InputValidationError("A contact master surface needs one or more triangular faces.")
        raw_master_nodes = parsed_faces[0]
    else:
        raw_master = tuple(int(node) for node in item["master_nodes"])
        if len(raw_master) != 3:
            raise InputValidationError("A frictionless contact needs exactly three master nodes.")
        raw_master_nodes = (raw_master[0], raw_master[1], raw_master[2])
        parsed_faces = None
    return FrictionlessContact(
        slave_node=int(item["slave_node"]),
        master_nodes=(raw_master_nodes[0], raw_master_nodes[1], raw_master_nodes[2]),
        master_faces=parsed_faces,
        name=str(item.get("name", "")),
        gap_tolerance=float(item.get("gap_tolerance", 1.0e-10)),
        friction_coefficient=float(item.get("friction_coefficient", 0.0)),
        tangential_stiffness=(
            float(item["tangential_stiffness"]) if item.get("tangential_stiffness") is not None else None
        ),
    )
