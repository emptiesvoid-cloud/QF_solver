"""White-box audit data for finite element model assembly."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.sparse import spmatrix

from solveur.core.audit_checks import AuditCheck, build_audit_checks
from solveur.core.dofs import DofManager
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory
from solveur.mesh.quality import MeshQuality
from solveur.mesh.validation import MeshReport
from solveur.mesh.validation import MeshValidator
from solveur.core.qualification import qualification_metadata


@dataclass(frozen=True)
class MatrixAudit:
    """Transparent numerical summary for one sparse matrix."""

    name: str
    shape: tuple[int, int]
    nnz: int
    density: float
    data_norm: float
    symmetry_relative_error: float
    is_symmetric: bool
    diagonal_min: float
    diagonal_max: float
    rank_estimate: int | None = None
    eigenvalue_min: float | None = None
    eigenvalue_max: float | None = None
    condition_estimate: float | None = None
    positive_definite_estimate: bool | None = None
    values: list[list[float]] | None = None

    @classmethod
    def from_sparse(cls, name: str, matrix: spmatrix) -> "MatrixAudit":
        matrix = matrix.tocsr()
        row_count, col_count = matrix.shape
        slots = max(row_count * col_count, 1)
        data_norm = float(np.linalg.norm(matrix.data))
        if row_count == col_count:
            diff = matrix - matrix.T
            symmetry = float(np.linalg.norm(diff.data) / max(data_norm, 1.0))
        else:
            symmetry = float("nan")
        diagonal = matrix.diagonal() if row_count == col_count else np.array([], dtype=float)
        if diagonal.size:
            diagonal_min = float(np.min(diagonal))
            diagonal_max = float(np.max(diagonal))
        else:
            diagonal_min = 0.0
            diagonal_max = 0.0
        rank = None
        eigen_min = None
        eigen_max = None
        condition = None
        positive = None
        if row_count == col_count and row_count <= 200 and np.isfinite(symmetry) and symmetry <= 1.0e-9:
            spectrum = np.linalg.eigvalsh(0.5 * (matrix.toarray() + matrix.toarray().T))
            rank = int(np.linalg.matrix_rank(matrix.toarray()))
            eigen_min = float(np.min(spectrum))
            eigen_max = float(np.max(spectrum))
            condition = _condition_estimate(spectrum)
            positive = bool(eigen_min > 1.0e-12 * max(abs(eigen_max), 1.0))
        return cls(
            name=name,
            shape=(int(row_count), int(col_count)),
            nnz=int(matrix.nnz),
            density=float(matrix.nnz / slots),
            data_norm=data_norm,
            symmetry_relative_error=symmetry,
            is_symmetric=bool(np.isfinite(symmetry) and symmetry <= 1.0e-9),
            diagonal_min=diagonal_min,
            diagonal_max=diagonal_max,
            rank_estimate=rank,
            eigenvalue_min=eigen_min,
            eigenvalue_max=eigen_max,
            condition_estimate=condition,
            positive_definite_estimate=positive,
        )

    @classmethod
    def from_array(cls, name: str, matrix: np.ndarray, *, include_values: bool = False) -> "MatrixAudit":
        values = np.asarray(matrix, dtype=float)
        row_count, col_count = values.shape
        slots = max(row_count * col_count, 1)
        data_norm = float(np.linalg.norm(values))
        if row_count == col_count:
            symmetry = float(np.linalg.norm(values - values.T) / max(data_norm, 1.0))
            symmetric = np.isfinite(symmetry) and symmetry <= 1.0e-9
            diagonal = np.diag(values)
            rank = int(np.linalg.matrix_rank(values))
            if symmetric:
                eigenvalues = np.linalg.eigvalsh(0.5 * (values + values.T))
                eigen_min = float(np.min(eigenvalues))
                eigen_max = float(np.max(eigenvalues))
                condition = _condition_estimate(eigenvalues)
                positive = bool(eigen_min > 1.0e-12 * max(abs(eigen_max), 1.0))
            else:
                eigen_min = None
                eigen_max = None
                condition = None
                positive = None
        else:
            symmetry = float("nan")
            symmetric = False
            diagonal = np.array([], dtype=float)
            rank = int(np.linalg.matrix_rank(values))
            eigen_min = None
            eigen_max = None
            condition = None
            positive = None
        return cls(
            name=name,
            shape=(int(row_count), int(col_count)),
            nnz=int(np.count_nonzero(np.abs(values) > 1.0e-30)),
            density=float(np.count_nonzero(np.abs(values) > 1.0e-30) / slots),
            data_norm=data_norm,
            symmetry_relative_error=symmetry,
            is_symmetric=bool(symmetric),
            diagonal_min=float(np.min(diagonal)) if diagonal.size else 0.0,
            diagonal_max=float(np.max(diagonal)) if diagonal.size else 0.0,
            rank_estimate=rank,
            eigenvalue_min=eigen_min,
            eigenvalue_max=eigen_max,
            condition_estimate=condition,
            positive_definite_estimate=positive,
            values=values.tolist() if include_values else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "shape": list(self.shape),
            "nnz": self.nnz,
            "density": self.density,
            "data_norm": self.data_norm,
            "symmetry_relative_error": self.symmetry_relative_error,
            "is_symmetric": self.is_symmetric,
            "diagonal_min": self.diagonal_min,
            "diagonal_max": self.diagonal_max,
        }
        if self.rank_estimate is not None:
            data["rank_estimate"] = self.rank_estimate
        if self.eigenvalue_min is not None:
            data["eigenvalue_min"] = self.eigenvalue_min
        if self.eigenvalue_max is not None:
            data["eigenvalue_max"] = self.eigenvalue_max
        if self.condition_estimate is not None:
            data["condition_estimate"] = self.condition_estimate
        if self.positive_definite_estimate is not None:
            data["positive_definite_estimate"] = self.positive_definite_estimate
        if self.values is not None:
            data["values"] = self.values
        return data


@dataclass(frozen=True)
class ElementAudit:
    """White-box summary for one finite element contribution."""

    index: int
    type: str
    nodes: list[int]
    material: str
    material_data: dict[str, Any]
    dofs_per_node: list[str]
    global_dof_indices: list[int]
    geometry: dict[str, Any]
    local_dofs: list[dict[str, Any]] = field(default_factory=list)
    assembly_entries: list[dict[str, Any]] = field(default_factory=list)
    matrices: list[MatrixAudit] = field(default_factory=list)
    vectors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "type": self.type,
            "nodes": self.nodes,
            "material": self.material,
            "material_data": self.material_data,
            "dofs_per_node": self.dofs_per_node,
            "global_dof_indices": self.global_dof_indices,
            "geometry": self.geometry,
            "local_dofs": self.local_dofs,
            "assembly_entries": self.assembly_entries,
            "matrices": [matrix.to_dict() for matrix in self.matrices],
            "vectors": self.vectors,
        }


@dataclass(frozen=True)
class SolverAudit:
    """Structured trace that explains how the solver sees a model."""

    analysis: str
    method: str
    node_count: int
    element_count: int
    ndof: int
    mesh_status: str
    mesh_errors: list[str] = field(default_factory=list)
    mesh_warnings: list[str] = field(default_factory=list)
    mesh_details: dict[str, Any] = field(default_factory=dict)
    element_types: dict[str, int] = field(default_factory=dict)
    material_names: list[str] = field(default_factory=list)
    dof_map: list[dict[str, Any]] = field(default_factory=list)
    element_dofs: list[dict[str, Any]] = field(default_factory=list)
    boundary: dict[str, Any] = field(default_factory=dict)
    vectors: list[dict[str, Any]] = field(default_factory=list)
    load_assembly: dict[str, Any] = field(default_factory=dict)
    matrices: list[MatrixAudit] = field(default_factory=list)
    element_audits: list[ElementAudit] = field(default_factory=list)
    post_results: list[dict[str, Any]] = field(default_factory=list)
    equilibrium: dict[str, Any] = field(default_factory=dict)
    solver_selection: dict[str, Any] = field(default_factory=dict)
    checks: list[AuditCheck] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    qualification: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def partial(cls, model: FiniteElementModel, report: MeshReport) -> "SolverAudit":
        """Build an audit for invalid models without assembling matrices."""
        return cls(
            analysis=model.analysis.type,
            method=model.analysis.method,
            node_count=model.node_count,
            element_count=len(model.elements),
            ndof=0,
            mesh_status=report.status,
            mesh_errors=list(report.errors),
            mesh_warnings=list(report.warnings),
            mesh_details=dict(report.details),
            element_types=_element_type_counts(model),
            material_names=sorted(model.materials),
            checks=build_audit_checks(
                analysis=model.analysis.type,
                report=report,
                boundary={},
                matrices=[],
                elements=[],
                equilibrium={},
            ),
            notes=["Model audit stopped before assembly because mesh validation failed."],
            qualification=qualification_metadata(model),
        )

    @classmethod
    def from_state(
        cls,
        *,
        model: FiniteElementModel,
        dofs: DofManager,
        report: MeshReport,
        fixed: np.ndarray,
        free: np.ndarray,
        method: str | None = None,
        vectors: dict[str, np.ndarray] | None = None,
        load_assembly: dict[str, Any] | None = None,
        matrices: dict[str, Any] | None = None,
        equilibrium: dict[str, Any] | None = None,
        post_results: list[dict[str, Any]] | None = None,
        solver_selection: dict[str, Any] | None = None,
        include_values: bool = False,
        include_element_audits: bool = True,
        include_element_dofs: bool = True,
        notes: list[str] | None = None,
    ) -> "SolverAudit":
        """Build an audit from validated model data and assembled arrays."""
        boundary = _boundary_summary(fixed, free)
        matrix_audits = [MatrixAudit.from_sparse(name, matrix) for name, matrix in (matrices or {}).items()]
        element_audits = (
            _element_audits(model, dofs, include_values=include_values) if include_element_audits else []
        )
        equilibrium_data = dict(equilibrium or {})
        return cls(
            analysis=model.analysis.type,
            method=method or model.analysis.method,
            node_count=model.node_count,
            element_count=len(model.elements),
            ndof=dofs.ndof,
            mesh_status=report.status,
            mesh_errors=list(report.errors),
            mesh_warnings=list(report.warnings),
            mesh_details=dict(report.details),
            element_types=_element_type_counts(model),
            material_names=sorted(model.materials),
            dof_map=_dof_map(dofs),
            element_dofs=_element_dofs(model, dofs) if include_element_dofs else [],
            boundary=boundary,
            vectors=[_vector_summary(name, vector) for name, vector in (vectors or {}).items()],
            load_assembly=dict(load_assembly or {}),
            matrices=matrix_audits,
            element_audits=element_audits,
            post_results=list(post_results or []),
            equilibrium=equilibrium_data,
            solver_selection=dict(solver_selection or {}),
            checks=build_audit_checks(
                analysis=model.analysis.type,
                report=report,
                boundary=boundary,
                matrices=matrix_audits,
                elements=element_audits,
                equilibrium=equilibrium_data,
                post_results=post_results or [],
            ),
            notes=list(notes or []),
            qualification=qualification_metadata(model),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "purpose": "white_box_solver_audit",
            "analysis": self.analysis,
            "method": self.method,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": self.ndof,
            "mesh_status": self.mesh_status,
            "mesh_errors": self.mesh_errors,
            "mesh_warnings": self.mesh_warnings,
            "mesh_details": self.mesh_details,
            "element_types": self.element_types,
            "material_names": self.material_names,
            "dof_map": self.dof_map,
            "element_dofs": self.element_dofs,
            "boundary": self.boundary,
            "vectors": self.vectors,
            "load_assembly": self.load_assembly,
            "matrices": [matrix.to_dict() for matrix in self.matrices],
            "element_audits": [element.to_dict() for element in self.element_audits],
            "post_results": self.post_results,
            "equilibrium": self.equilibrium,
            "solver_selection": self.solver_selection,
            "checks": [check.to_dict() for check in self.checks],
            "notes": self.notes,
            "qualification": self.qualification,
        }


def _element_type_counts(model: FiniteElementModel) -> dict[str, int]:
    return dict(sorted(Counter(element.type for element in model.elements).items()))


def _dof_map(dofs: DofManager) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for node, names in sorted(dofs.node_dofs.items()):
        entries.append({"node": int(node), "dofs": {name: int(dofs.index(node, name)) for name in names}})
    return entries


def _element_dofs(model: FiniteElementModel, dofs: DofManager) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for index, element in enumerate(model.elements):
        spec = ElementRegistry.get(element.type)
        indices: list[int] = []
        for node in element.nodes:
            indices.extend(dofs.node_indices(node, spec.dofs))
        entries.append(
            {
                "index": int(index),
                "type": element.type,
                "nodes": [int(node) for node in element.nodes],
                "material": element.material,
                "dofs_per_node": list(spec.dofs),
                "global_dof_indices": indices,
            }
        )
    return entries


def _element_audits(model: FiniteElementModel, dofs: DofManager, *, include_values: bool = False) -> list[ElementAudit]:
    audits: list[ElementAudit] = []
    for index, definition in enumerate(model.elements):
        spec = ElementRegistry.get(definition.type)
        material_data = model.materials[definition.material]
        coords = model.nodes[list(definition.nodes)]
        material = MaterialFactory.create(material_data, coordinates=coords)
        element = spec.factory(material)
        global_dofs: list[int] = []
        for node in definition.nodes:
            global_dofs.extend(dofs.node_indices(node, spec.dofs))
        local_stiffness = element.stiffness(coords)
        matrices = [MatrixAudit.from_array("local_stiffness", local_stiffness, include_values=include_values)]
        vectors: list[dict[str, Any]] = []
        if model.analysis.type == "modal" and hasattr(element, "mass"):
            matrices.append(MatrixAudit.from_array("local_mass", element.mass(coords), include_values=include_values))
        if model.analysis.type == "nonlinear_static" and hasattr(element, "internal_force_and_tangent"):
            local_u: np.ndarray = np.zeros(len(global_dofs), dtype=float)
            local_internal, local_tangent = element.internal_force_and_tangent(coords, local_u)
            matrices.append(
                MatrixAudit.from_array("initial_local_tangent", local_tangent, include_values=include_values)
            )
            vectors.append(_vector_summary("initial_local_internal_force", local_internal))
        audits.append(
            ElementAudit(
                index=index,
                type=definition.type,
                nodes=[int(node) for node in definition.nodes],
                material=definition.material,
                material_data=_material_summary(material_data),
                dofs_per_node=list(spec.dofs),
                global_dof_indices=global_dofs,
                geometry=_geometry_summary(definition.type, coords),
                local_dofs=_local_dof_map(definition.nodes, spec.dofs, dofs),
                assembly_entries=_assembly_entries(local_stiffness, global_dofs) if include_values else [],
                matrices=matrices,
                vectors=vectors,
            )
        )
    return audits


def _material_summary(data: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key, value in sorted(data.items()):
        if isinstance(value, (int, float)):
            summary[key] = float(value)
        else:
            summary[key] = value
    return summary


def _local_dof_map(nodes: tuple[int, ...], names: tuple[str, ...], dofs: DofManager) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    local = 0
    for node in nodes:
        for name in names:
            entries.append(
                {
                    "local_index": local,
                    "node": int(node),
                    "dof": name,
                    "global_index": int(dofs.index(node, name)),
                }
            )
            local += 1
    return entries


def _assembly_entries(local_matrix: np.ndarray, global_dofs: list[int]) -> list[dict[str, Any]]:
    values = np.asarray(local_matrix, dtype=float)
    entries: list[dict[str, Any]] = []
    rows, cols = np.nonzero(np.abs(values) > 1.0e-30)
    for row, col in zip(rows.tolist(), cols.tolist()):
        entries.append(
            {
                "local_row": int(row),
                "local_col": int(col),
                "global_row": int(global_dofs[row]),
                "global_col": int(global_dofs[col]),
                "value": float(values[row, col]),
            }
        )
    return entries


def _condition_estimate(eigenvalues: np.ndarray) -> float | None:
    magnitudes = np.abs(np.asarray(eigenvalues, dtype=float))
    if magnitudes.size == 0:
        return None
    scale = float(np.max(magnitudes))
    if scale <= 0.0:
        return None
    active = magnitudes[magnitudes > 1.0e-12 * scale]
    if active.size == 0:
        return None
    return float(scale / np.min(active))


def _geometry_summary(element_type: str, coords: np.ndarray) -> dict[str, Any]:
    coords = np.asarray(coords, dtype=float)
    summary: dict[str, Any] = {
        "centroid": [float(value) for value in np.mean(coords, axis=0)],
        "bounding_box_min": [float(value) for value in np.min(coords, axis=0)],
        "bounding_box_max": [float(value) for value in np.max(coords, axis=0)],
    }
    if element_type in {"TET4", "TET10"}:
        corners = coords[:4]
        summary["signed_corner_volume"] = MeshQuality.tet4_volume(corners)
        summary["corner_quality"] = MeshQuality.tet4_quality(corners)
        summary.update(_edge_summary(corners))
    elif element_type == "MITC4":
        summary["area"] = _quad_area(coords)
        summary.update(_edge_summary(coords[[0, 1, 2, 3]]))
    elif element_type == "MITC3":
        summary["area"] = float(
            0.5 * np.linalg.norm(np.cross(coords[1] - coords[0], coords[2] - coords[0]))
        )
        summary.update(_edge_summary(coords[[0, 1, 2]]))
    elif element_type == "BEAM2":
        summary["length"] = float(np.linalg.norm(coords[1] - coords[0]))
        summary.update(_edge_summary(coords))
    return summary


def _edge_summary(coords: np.ndarray) -> dict[str, float]:
    lengths: list[float] = []
    for i in range(coords.shape[0]):
        for j in range(i + 1, coords.shape[0]):
            lengths.append(float(np.linalg.norm(coords[j] - coords[i])))
    if not lengths:
        return {"edge_length_min": 0.0, "edge_length_max": 0.0}
    return {"edge_length_min": min(lengths), "edge_length_max": max(lengths)}


def _quad_area(coords: np.ndarray) -> float:
    first = 0.5 * np.linalg.norm(np.cross(coords[1] - coords[0], coords[2] - coords[0]))
    second = 0.5 * np.linalg.norm(np.cross(coords[2] - coords[0], coords[3] - coords[0]))
    return float(first + second)


def _boundary_summary(fixed: np.ndarray, free: np.ndarray) -> dict[str, Any]:
    return {
        "fixed_dof_count": int(fixed.size),
        "free_dof_count": int(free.size),
        "fixed_indices": [int(index) for index in fixed.tolist()],
        "free_indices": [int(index) for index in free.tolist()],
    }


def _vector_summary(name: str, vector: np.ndarray) -> dict[str, Any]:
    values = np.asarray(vector, dtype=float).ravel()
    nonzero = np.flatnonzero(np.abs(values) > 1.0e-30)
    return {
        "name": name,
        "size": int(values.size),
        "norm": float(np.linalg.norm(values)),
        "max_abs": float(np.max(np.abs(values))) if values.size else 0.0,
        "nonzero_count": int(nonzero.size),
        "nonzero_entries": [{"index": int(index), "value": float(values[index])} for index in nonzero],
    }


def static_equilibrium_summary(
    *,
    model: FiniteElementModel,
    dofs: DofManager,
    loads: np.ndarray,
    internal: np.ndarray,
    displacement: np.ndarray,
    fixed: np.ndarray,
    free: np.ndarray,
    constraint_transform: spmatrix | None = None,
    ground_spring_reactions: np.ndarray | None = None,
    fixed_constraint_reactions: np.ndarray | None = None,
    load_factor: float = 1.0,
) -> dict[str, Any]:
    """Summarize the solved static balance in solver sign conventions."""
    external = float(load_factor) * np.asarray(loads, dtype=float)
    internal = np.asarray(internal, dtype=float)
    displacement = np.asarray(displacement, dtype=float)
    residual = internal - external
    reaction = np.zeros_like(residual)
    if fixed_constraint_reactions is None:
        reaction[fixed] = residual[fixed]
    else:
        fixed_reactions = np.asarray(fixed_constraint_reactions, dtype=float)
        if fixed_reactions.shape != residual.shape:
            raise ValueError("Fixed constraint reactions have an incompatible size.")
        reaction[fixed] = fixed_reactions[fixed]
    if ground_spring_reactions is not None:
        reaction += np.asarray(ground_spring_reactions, dtype=float)
    reduced_residual = residual[free] if constraint_transform is None else np.asarray(constraint_transform.T @ residual).ravel()
    reduced_external = external[free] if constraint_transform is None else np.asarray(constraint_transform.T @ external).ravel()
    free_norm = float(np.linalg.norm(reduced_residual))
    fixed_norm = float(np.linalg.norm(reaction[fixed]))
    external_norm = float(np.linalg.norm(external))
    internal_norm = float(np.linalg.norm(internal))
    external_work = float(displacement @ external)
    secant_internal_energy = float(0.5 * displacement @ internal)
    energy_error = abs(2.0 * secant_internal_energy - external_work) / max(abs(external_work), 1.0)
    from solveur.loads.integration import load_balance

    external_resultant, external_moment = load_balance(model, dofs, external)
    reaction_resultant, reaction_moment = load_balance(model, dofs, reaction)
    force_imbalance = external_resultant + reaction_resultant
    moment_imbalance = external_moment + reaction_moment
    force_scale = max(float(np.linalg.norm(external_resultant)), float(np.linalg.norm(reaction_resultant)), 1.0)
    moment_scale = max(float(np.linalg.norm(external_moment)), float(np.linalg.norm(reaction_moment)), 1.0)
    return {
        "sign_convention": "residual = internal_force - external_force; reactions are residuals on fixed dofs",
        "load_factor": float(load_factor),
        "free_residual_norm": free_norm,
        "free_relative_residual": free_norm / max(float(np.linalg.norm(reduced_external)), 1.0),
        "fixed_reaction_norm": fixed_norm,
        "ground_spring_reaction_norm": float(np.linalg.norm(ground_spring_reactions)) if ground_spring_reactions is not None else 0.0,
        "external_load_norm": external_norm,
        "internal_force_norm": internal_norm,
        "displacement_norm": float(np.linalg.norm(displacement)),
        "external_work_at_final_load": external_work,
        "secant_internal_energy": secant_internal_energy,
        "linear_energy_identity_relative_error": float(energy_error),
        "external_resultant": external_resultant.tolist(),
        "reaction_resultant": reaction_resultant.tolist(),
        "force_imbalance": force_imbalance.tolist(),
        "force_balance_relative_error": float(np.linalg.norm(force_imbalance) / force_scale),
        "external_moment_about_origin": external_moment.tolist(),
        "reaction_moment_about_origin": reaction_moment.tolist(),
        "moment_imbalance_about_origin": moment_imbalance.tolist(),
        "moment_balance_relative_error": float(np.linalg.norm(moment_imbalance) / moment_scale),
        "reactions": _reaction_entries(dofs, reaction, fixed),
    }


def _reaction_entries(dofs: DofManager, reaction: np.ndarray, fixed: np.ndarray) -> list[dict[str, Any]]:
    labels: dict[int, tuple[int, str]] = {}
    for node, names in sorted(dofs.node_dofs.items()):
        for name in names:
            labels[dofs.index(node, name)] = (int(node), name)
    entries: list[dict[str, Any]] = []
    for index in fixed.tolist():
        node, name = labels[int(index)]
        entries.append({"index": int(index), "node": node, "dof": name, "value": float(reaction[int(index)])})
    return entries


class ModelInspector:
    """Build a white-box audit without running the final analysis solve."""

    def __init__(self) -> None:
        self.validator = MeshValidator()

    def inspect(self, model: FiniteElementModel, *, detail: str = "summary") -> SolverAudit:
        if detail not in {"summary", "values"}:
            raise ValueError(f"Unsupported audit detail {detail!r}.")
        include_values = detail == "values"
        report = self.validator.validate(model)
        if report.status == "FAIL":
            return SolverAudit.partial(model, report)
        dofs = model.dof_manager()
        from solveur.core.assembly.assembler import GlobalAssembler

        assembler = GlobalAssembler()
        fixed = assembler.fixed_indices(model, dofs)
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        loads = assembler.assemble_loads(model, dofs)
        matrices: dict[str, spmatrix] = {}
        vectors = {"loads": loads}
        notes: list[str] = []
        if model.analysis.type == "modal":
            stiffness = assembler.assemble_stiffness(model, dofs)
            mass = assembler.assemble_mass(model, dofs)
            matrices["stiffness"] = stiffness
            matrices["mass"] = mass
            if free.size:
                matrices["reduced_stiffness"] = stiffness[free, :][:, free]
                matrices["reduced_mass"] = mass[free, :][:, free]
        elif model.analysis.type == "nonlinear_static":
            displacement = np.zeros(dofs.ndof, dtype=float)
            from solveur.core.assembly.nonlinear import assemble_internal_tangent

            internal, tangent, _ = assemble_internal_tangent(model, dofs, displacement)
            vectors["initial_internal_force"] = internal
            matrices["initial_tangent"] = tangent
            if free.size:
                matrices["reduced_initial_tangent"] = tangent[free, :][:, free]
            notes.append("Nonlinear inspection uses the tangent at zero displacement.")
        else:
            stiffness = assembler.assemble_stiffness(model, dofs)
            matrices["stiffness"] = stiffness
            if free.size:
                matrices["reduced_stiffness"] = stiffness[free, :][:, free]
        return SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            vectors=vectors,
            load_assembly=assembler.last_load_diagnostics,
            matrices=matrices,
            include_values=include_values,
            notes=notes,
        )
