"""White-box audit data for finite element model assembly."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.sparse import spmatrix

from solveur.core.audit_checks import (
    AuditCheck,
    _element_checks,
    _post_result_checks,
    build_audit_checks,
    check_status_counts,
)
from solveur.core.dofs import DofManager
from solveur.core.model import FiniteElementModel
from solveur.elements.registry import ElementRegistry
from solveur.materials.factory import MaterialFactory
from solveur.mesh.quality import MeshQuality
from solveur.mesh.validation import MeshReport
from solveur.mesh.validation import MeshValidator
from solveur.core.qualification import qualification_metadata


AUDIT_DETAILS = ("summary", "diagnostic", "values")
DEFAULT_DIAGNOSTIC_WORST_N = 10
DEFAULT_AUDIT_SIZE_WARNING_ROWS = 100_000


def validate_audit_detail(detail: str) -> str:
    """Validate and return one of the public audit serialization levels."""
    if detail not in AUDIT_DETAILS:
        raise ValueError(f"Unsupported audit detail {detail!r}; expected one of {AUDIT_DETAILS}.")
    return detail


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
    detail: str = "summary"
    diagnostic: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def partial(
        cls,
        model: FiniteElementModel,
        report: MeshReport,
        *,
        detail: str = "summary",
    ) -> "SolverAudit":
        """Build an audit for invalid models without assembling matrices."""
        detail = validate_audit_detail(detail)
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
            detail=detail,
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
        include_indices: bool = True,
        notes: list[str] | None = None,
        detail: str = "values",
        max_worst: int = DEFAULT_DIAGNOSTIC_WORST_N,
        compact_serialization: bool = False,
        values_warning_rows: int = DEFAULT_AUDIT_SIZE_WARNING_ROWS,
    ) -> "SolverAudit":
        """Build an audit from validated model data and assembled arrays."""
        detail = validate_audit_detail(detail)
        if max_worst < 1:
            raise ValueError("max_worst must be at least 1.")
        if values_warning_rows < 0:
            raise ValueError("values_warning_rows must be non-negative.")
        compact = compact_serialization or detail in {"summary", "diagnostic"}
        boundary = _boundary_summary(fixed, free, include_indices=include_indices and not compact)
        matrix_audits = [MatrixAudit.from_sparse(name, matrix) for name, matrix in (matrices or {}).items()]
        element_diagnostic: dict[str, Any] = {}
        if include_element_audits:
            element_audits, element_diagnostic = _build_element_audits(
                model,
                dofs,
                include_values=include_values,
                detail=detail,
                max_worst=max_worst,
            )
        else:
            element_audits = []
        equilibrium_data = dict(equilibrium or {})
        vector_data = [
            _vector_summary(
                name,
                vector,
                include_values=(include_values or detail == "values") and not compact,
            )
            for name, vector in (vectors or {}).items()
        ]
        load_data = (
            _load_assembly_summary(load_assembly or {})
            if compact
            else dict(load_assembly or {})
        )
        compact_post_results: list[dict[str, Any]] = []
        post_issue_checks: list[AuditCheck] = []
        post_check_counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
        for post_result in post_results or []:
            result_checks = _post_result_checks(post_result)
            for check in result_checks:
                if check.status in post_check_counts:
                    post_check_counts[check.status] += 1
            if any(check.status != "PASS" for check in result_checks):
                compact_post_results.append(post_result)
                post_issue_checks.extend(check for check in result_checks if check.status != "PASS")
        global_checks = build_audit_checks(
            analysis=model.analysis.type,
            report=report,
            boundary=boundary,
            matrices=matrix_audits,
            elements=[],
            equilibrium=equilibrium_data,
            post_results=(post_results or []) if detail == "values" and not compact else [],
        )
        checks = build_audit_checks(
            analysis=model.analysis.type,
            report=report,
            boundary=boundary,
            matrices=matrix_audits,
            elements=element_audits,
            equilibrium=equilibrium_data,
            post_results=(post_results or []) if detail == "values" and not compact else [],
        )
        if compact:
            checks.extend(post_issue_checks)
        diagnostic = dict(element_diagnostic)
        size_estimate = estimate_audit_rows(
            element_count=len(model.elements),
            post_result_count=len(post_results or []),
            contribution_count=len((load_assembly or {}).get("contributions", [])),
            detail=detail,
        )
        size_warning = None
        if detail == "values" and size_estimate > values_warning_rows:
            size_warning = (
                f"detail='values' est estime a {size_estimate:,} lignes/controles, "
                f"au-dessus du seuil configurable {values_warning_rows:,}; "
                "utiliser detail='diagnostic' pour l'audit humain."
            )
        if detail == "values" and size_warning:
            diagnostic["export_size_estimate"] = size_estimate
            diagnostic["export_size_warning"] = size_warning
        if detail in {"summary", "diagnostic"}:
            counts = check_status_counts(global_checks)
            element_counts = element_diagnostic.get("element_check_counts", {})
            for status in ("PASS", "WARNING", "FAIL"):
                counts[status] += int(element_counts.get(status, 0))
                counts[status] += int(post_check_counts.get(status, 0))
            diagnostic["automatic_checks"] = counts
            diagnostic["post_check_counts"] = post_check_counts
            diagnostic["equilibrium"] = _equilibrium_diagnostic(equilibrium_data)
            diagnostic["issue_checks"] = [
                check.to_dict() for check in checks if check.status != "PASS"
            ]
            diagnostic["matrix_stats"] = _matrix_diagnostic(matrix_audits)
            diagnostic["result_stats"] = _result_diagnostic(post_results or [])
            diagnostic["residual_stats"] = _residual_diagnostic(solver_selection or {})
            diagnostic["residual_stats"].update(_vector_residual_diagnostic(vector_data))
            diagnostic["post_result_count"] = len(post_results or [])
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
            dof_map=_dof_map(dofs) if not compact else [],
            element_dofs=_element_dofs(model, dofs) if include_element_dofs and not compact else [],
            boundary=boundary,
            vectors=vector_data,
            load_assembly=load_data,
            matrices=matrix_audits,
            element_audits=element_audits,
            post_results=list(post_results or []) if not compact else compact_post_results,
            equilibrium=equilibrium_data,
            solver_selection=dict(solver_selection or {}),
            checks=checks if not compact else [check for check in checks if check.status != "PASS"],
            notes=[*(notes or []), size_warning] if size_warning else list(notes or []),
            qualification=qualification_metadata(model),
            detail=detail,
            diagnostic=diagnostic,
        )

    def to_dict(self, *, detail: str | None = None) -> dict[str, Any]:
        selected_detail = validate_audit_detail(detail or self.detail)
        if selected_detail != "values":
            return _compact_audit_dict(self, selected_detail)
        return self._to_values_dict()

    def _to_values_dict(self) -> dict[str, Any]:
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
            "detail": self.detail,
            "diagnostic": self.diagnostic,
        }


def _compact_audit_dict(audit: SolverAudit, detail: str) -> dict[str, Any]:
    """Serialize an existing audit without rebuilding exhaustive PASS rows."""
    element_audits: list[ElementAudit] = []
    element_check_counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    by_type: dict[str, dict[str, Any]] = {}
    worst: dict[str, list[dict[str, Any]]] = {
        "corner_quality": [],
        "signed_corner_volume": [],
        "matrix_condition_estimate": [],
    }
    for element in audit.element_audits:
        element_checks = _element_checks(element)
        for check in element_checks:
            if check.status in element_check_counts:
                element_check_counts[check.status] += 1
        if any(check.status != "PASS" for check in element_checks):
            element_audits.append(element)
        _update_element_diagnostic(by_type, worst, element, max_worst=DEFAULT_DIAGNOSTIC_WORST_N)

    compact_post_results: list[dict[str, Any]] = []
    post_check_counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    post_issue_checks: list[AuditCheck] = []
    for result in audit.post_results:
        result_checks = _post_result_checks(result)
        for check in result_checks:
            if check.status in post_check_counts:
                post_check_counts[check.status] += 1
        issues = [check for check in result_checks if check.status != "PASS"]
        if issues:
            compact_post_results.append(result)
            post_issue_checks.extend(issues)

    base_checks = [check for check in audit.checks if check.status != "PASS"]
    for check in post_issue_checks:
        if check not in base_checks:
            base_checks.append(check)
    existing_compact = audit.detail != "values" and bool(audit.diagnostic)
    if audit.detail == "values":
        counts = check_status_counts(audit.checks)
    else:
        counts = dict(audit.diagnostic.get("automatic_checks", check_status_counts(audit.checks)))
    element_quality = (
        audit.diagnostic.get("element_quality", {})
        if existing_compact
        else {key: _finalize_element_type_stats(value) for key, value in by_type.items()}
    )
    worst_data = audit.diagnostic.get("worst_n", worst) if existing_compact else worst
    element_counts_data = (
        audit.diagnostic.get("element_check_counts", element_check_counts)
        if existing_compact
        else element_check_counts
    )
    result_stats = audit.diagnostic.get("result_stats", {}) if existing_compact else _result_diagnostic(audit.post_results)
    residual_stats = (
        audit.diagnostic.get("residual_stats", {})
        if existing_compact
        else _residual_diagnostic(audit.solver_selection)
    )
    if not existing_compact:
        residual_stats.update(_vector_residual_diagnostic(audit.vectors))
    diagnostic = dict(audit.diagnostic)
    diagnostic.update(
        {
            "automatic_checks": counts,
            "element_audit_count": audit.diagnostic.get("element_audit_count", len(audit.element_audits)),
            "retained_issue_element_count": audit.diagnostic.get(
                "retained_issue_element_count", len(element_audits)
            ),
            "element_check_counts": element_counts_data,
            "element_quality": element_quality,
            "worst_n": worst_data,
            "issue_checks": [check.to_dict() for check in base_checks],
            "matrix_stats": audit.diagnostic.get("matrix_stats", _matrix_diagnostic(audit.matrices)),
            "result_stats": result_stats,
            "residual_stats": residual_stats,
            "post_result_count": audit.diagnostic.get("post_result_count", len(audit.post_results)),
            "equilibrium": _equilibrium_diagnostic(audit.equilibrium),
        }
    )
    data = {
        "version": 1,
        "purpose": "white_box_solver_audit",
        "analysis": audit.analysis,
        "method": audit.method,
        "node_count": audit.node_count,
        "element_count": audit.element_count,
        "ndof": audit.ndof,
        "mesh_status": audit.mesh_status,
        "mesh_errors": audit.mesh_errors,
        "mesh_warnings": audit.mesh_warnings,
        "mesh_details": audit.mesh_details,
        "element_types": audit.element_types,
        "material_names": audit.material_names,
        "dof_map": [],
        "element_dofs": [],
        "boundary": _compact_boundary(audit.boundary),
        "vectors": [_compact_vector(item) for item in audit.vectors],
        "load_assembly": _compact_load_assembly(audit.load_assembly),
        "matrices": [matrix.to_dict() for matrix in audit.matrices],
        "element_audits": [element.to_dict() for element in element_audits],
        "post_results": compact_post_results,
        "equilibrium": _compact_equilibrium(audit.equilibrium),
        "solver_selection": audit.solver_selection,
        "checks": [check.to_dict() for check in base_checks],
        "notes": audit.notes,
        "qualification": audit.qualification,
        "detail": detail,
        "diagnostic": diagnostic,
    }
    return data


def _compact_boundary(boundary: dict[str, Any]) -> dict[str, Any]:
    return {
        key: boundary[key]
        for key in ("fixed_dof_count", "free_dof_count")
        if key in boundary
    }


def _compact_vector(vector: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in vector.items() if key != "nonzero_entries"}


def _compact_load_assembly(load_assembly: dict[str, Any]) -> dict[str, Any]:
    return _load_assembly_summary(load_assembly)


def _compact_equilibrium(equilibrium: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "sign_convention",
        "load_factor",
        "free_residual_norm",
        "free_relative_residual",
        "fixed_reaction_norm",
        "ground_spring_reaction_norm",
        "external_load_norm",
        "internal_force_norm",
        "displacement_norm",
        "external_work_at_final_load",
        "secant_internal_energy",
        "linear_energy_identity_relative_error",
        "external_resultant",
        "reaction_resultant",
        "force_imbalance",
        "force_balance_relative_error",
        "external_moment_about_origin",
        "reaction_moment_about_origin",
        "moment_imbalance_about_origin",
        "moment_balance_relative_error",
    )
    result = {key: equilibrium[key] for key in keys if key in equilibrium}
    constraints = equilibrium.get("constraint_forces")
    if isinstance(constraints, dict):
        result["constraint_forces"] = {
            key: constraints[key]
            for key in (
                "equation_count",
                "constraint_violation_norm",
                "constraint_violation_max_abs",
                "equilibrium_relative_error",
                "global_force_closure_relative_error",
                "global_moment_closure_relative_error",
            )
            if key in constraints
        }
    return result


def estimate_audit_rows(
    *,
    element_count: int,
    post_result_count: int = 0,
    contribution_count: int = 0,
    detail: str = "values",
) -> int:
    """Estimate serialized audit rows before materializing an export."""
    detail = validate_audit_detail(detail)
    if detail == "summary":
        return 80
    if detail == "diagnostic":
        return 140 + min(element_count, DEFAULT_DIAGNOSTIC_WORST_N * 3)
    return 120 + (9 * element_count) + post_result_count + contribution_count


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


def _build_element_audits(
    model: FiniteElementModel,
    dofs: DofManager,
    *,
    include_values: bool,
    detail: str,
    max_worst: int,
) -> tuple[list[ElementAudit], dict[str, Any]]:
    """Build exhaustive values or compact issue/worst-element audit data."""
    if detail == "values":
        return (
            [
                _make_element_audit(
                    model,
                    dofs,
                    index,
                    definition,
                    include_values=True,
                    compact=False,
                )
                for index, definition in enumerate(model.elements)
            ],
            {},
        )

    audits: list[ElementAudit] = []
    check_counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    by_type: dict[str, dict[str, Any]] = {}
    worst: dict[str, list[dict[str, Any]]] = {
        "corner_quality": [],
        "signed_corner_volume": [],
        "matrix_condition_estimate": [],
    }
    for index, definition in enumerate(model.elements):
        audit = _make_element_audit(
            model,
            dofs,
            index,
            definition,
            include_values=False,
            compact=True,
        )
        element_checks = _element_checks(audit)
        for check in element_checks:
            if check.status in check_counts:
                check_counts[check.status] += 1
        if any(check.status != "PASS" for check in element_checks):
            audits.append(audit)
        _update_element_diagnostic(by_type, worst, audit, max_worst=max_worst)

    return audits, {
        "element_audit_count": len(model.elements),
        "retained_issue_element_count": len(audits),
        "element_check_counts": check_counts,
        "element_quality": {key: _finalize_element_type_stats(value) for key, value in by_type.items()},
        "worst_n": worst,
    }


def _make_element_audit(
    model: FiniteElementModel,
    dofs: DofManager,
    index: int,
    definition: Any,
    *,
    include_values: bool,
    compact: bool,
) -> ElementAudit:
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
        vectors.append(
            _vector_summary(
                "initial_local_internal_force",
                local_internal,
                include_values=include_values,
            )
        )
    return ElementAudit(
        index=index,
        type=definition.type,
        nodes=[int(node) for node in definition.nodes],
        material=definition.material,
        material_data=_material_summary(material_data),
        dofs_per_node=list(spec.dofs),
        global_dof_indices=global_dofs,
        geometry=_geometry_summary(definition.type, coords),
        local_dofs=[] if compact else _local_dof_map(definition.nodes, spec.dofs, dofs),
        assembly_entries=_assembly_entries(local_stiffness, global_dofs) if include_values else [],
        matrices=matrices,
        vectors=vectors,
    )


def _empty_metric() -> dict[str, Any]:
    return {"count": 0, "finite_count": 0, "min": None, "max": None, "mean": None, "sum": 0.0}


def _update_metric(metric: dict[str, Any], value: Any) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return
    if not np.isfinite(number):
        return
    metric["count"] = int(metric["count"]) + 1
    metric["finite_count"] = int(metric["finite_count"]) + 1
    metric["sum"] = float(metric["sum"]) + number
    metric["min"] = number if metric["min"] is None else min(float(metric["min"]), number)
    metric["max"] = number if metric["max"] is None else max(float(metric["max"]), number)


def _finalize_metric(metric: dict[str, Any]) -> dict[str, Any]:
    count = int(metric["count"])
    return {
        "count": count,
        "finite_count": int(metric["finite_count"]),
        "min": metric["min"],
        "max": metric["max"],
        "mean": (float(metric["sum"]) / count) if count else None,
    }


def _update_element_diagnostic(
    by_type: dict[str, dict[str, Any]],
    worst: dict[str, list[dict[str, Any]]],
    audit: ElementAudit,
    *,
    max_worst: int,
) -> None:
    summary = by_type.setdefault(
        audit.type,
        {
            "count": 0,
            "signed_corner_volume": _empty_metric(),
            "corner_quality": _empty_metric(),
            "edge_length_min": _empty_metric(),
            "edge_length_max": _empty_metric(),
            "matrices": {},
        },
    )
    summary["count"] += 1
    geometry = audit.geometry
    _update_metric(summary["signed_corner_volume"], geometry.get("signed_corner_volume"))
    _update_metric(summary["corner_quality"], geometry.get("corner_quality"))
    _update_metric(summary["edge_length_min"], geometry.get("edge_length_min"))
    _update_metric(summary["edge_length_max"], geometry.get("edge_length_max"))
    element_context = {
        "index": audit.index,
        "type": audit.type,
        "nodes": audit.nodes,
    }
    if "corner_quality" in geometry:
        _offer_worst(worst["corner_quality"], {**element_context, "value": geometry["corner_quality"]}, max_worst)
    if "signed_corner_volume" in geometry:
        _offer_worst(
            worst["signed_corner_volume"],
            {**element_context, "value": geometry["signed_corner_volume"]},
            max_worst,
        )
    for matrix in audit.matrices:
        matrix_stats = summary["matrices"].setdefault(
            matrix.name,
            {
                "count": 0,
                "data_norm": _empty_metric(),
                "symmetry_relative_error": _empty_metric(),
                "condition_estimate": _empty_metric(),
            },
        )
        matrix_stats["count"] += 1
        _update_metric(matrix_stats["data_norm"], matrix.data_norm)
        _update_metric(matrix_stats["symmetry_relative_error"], matrix.symmetry_relative_error)
        if matrix.condition_estimate is not None:
            _update_metric(matrix_stats["condition_estimate"], matrix.condition_estimate)
            _offer_worst(
                worst["matrix_condition_estimate"],
                {
                    **element_context,
                    "matrix": matrix.name,
                    "value": matrix.condition_estimate,
                },
                max_worst,
                reverse=True,
            )


def _offer_worst(
    values: list[dict[str, Any]],
    entry: dict[str, Any],
    max_worst: int,
    *,
    reverse: bool = False,
) -> None:
    try:
        float(entry["value"])
    except (TypeError, ValueError):
        return
    values.append(entry)
    values.sort(key=lambda item: float(item["value"]), reverse=reverse)
    del values[max_worst:]


def _finalize_element_type_stats(by_type: dict[str, Any]) -> dict[str, Any]:
    finalized: dict[str, Any] = {"count": by_type["count"]}
    for key in ("signed_corner_volume", "corner_quality", "edge_length_min", "edge_length_max"):
        finalized[key] = _finalize_metric(by_type[key])
    matrices: dict[str, Any] = {}
    for name, matrix in by_type["matrices"].items():
        matrices[name] = {
            "count": matrix["count"],
            **{key: _finalize_metric(value) for key, value in matrix.items() if key != "count"},
        }
    finalized["matrices"] = matrices
    return finalized


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


def _boundary_summary(
    fixed: np.ndarray,
    free: np.ndarray,
    *,
    include_indices: bool = True,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "fixed_dof_count": int(fixed.size),
        "free_dof_count": int(free.size),
    }
    if include_indices:
        summary.update(
            {
                "fixed_indices": [int(index) for index in fixed.tolist()],
                "free_indices": [int(index) for index in free.tolist()],
            }
        )
    return summary


def _vector_summary(
    name: str,
    vector: np.ndarray,
    *,
    include_values: bool = False,
) -> dict[str, Any]:
    values = np.asarray(vector, dtype=float).ravel()
    nonzero = np.flatnonzero(np.abs(values) > 1.0e-30)
    summary = {
        "name": name,
        "size": int(values.size),
        "norm": float(np.linalg.norm(values)),
        "max_abs": float(np.max(np.abs(values))) if values.size else 0.0,
        "nonzero_count": int(nonzero.size),
    }
    if include_values:
        summary["nonzero_entries"] = [
            {"index": int(index), "value": float(values[index])} for index in nonzero
        ]
    return summary


def _load_assembly_summary(load_assembly: dict[str, Any]) -> dict[str, Any]:
    """Keep load totals while omitting per-element contribution dumps."""
    summary: dict[str, Any] = {}
    for key in (
        "nodal_load_count",
        "distributed_load_count",
        "resultant",
        "moment_about_origin",
    ):
        if key in load_assembly:
            summary[key] = load_assembly[key]
    contributions = load_assembly.get("contributions", [])
    summary["contribution_count"] = len(contributions) if isinstance(contributions, list) else 0
    if isinstance(contributions, list):
        summary["contribution_types"] = sorted(
            {str(item.get("type", "")) for item in contributions if isinstance(item, dict)}
        )
    return summary


def _equilibrium_diagnostic(equilibrium: dict[str, Any]) -> dict[str, Any]:
    """Select equilibrium observables needed for compact human review."""
    keys = (
        "free_relative_residual",
        "force_balance_relative_error",
        "moment_balance_relative_error",
        "linear_energy_identity_relative_error",
        "external_load_norm",
        "internal_force_norm",
    )
    result = {key: equilibrium[key] for key in keys if key in equilibrium}
    constraints = equilibrium.get("constraint_forces")
    if isinstance(constraints, dict):
        result["constraint_forces"] = {
            key: constraints[key]
            for key in (
                "equation_count",
                "constraint_violation_norm",
                "constraint_violation_max_abs",
                "equilibrium_relative_error",
                "global_force_closure_relative_error",
                "global_moment_closure_relative_error",
            )
            if key in constraints
        }
    return result


def _matrix_diagnostic(matrices: list[MatrixAudit]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for matrix in matrices:
        summary[matrix.name] = {
            "count": 1,
            "data_norm": _finalize_metric(_metric_from_values([matrix.data_norm])),
            "symmetry_relative_error": _finalize_metric(
                _metric_from_values([matrix.symmetry_relative_error])
            ),
            "condition_estimate": _finalize_metric(
                _metric_from_values([matrix.condition_estimate])
            ),
        }
    return summary


def _metric_from_values(values: list[Any]) -> dict[str, float | int | None]:
    metric = _empty_metric()
    for value in values:
        _update_metric(metric, value)
    return metric


def _result_diagnostic(results: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_keys = {
        "von_mises",
        "equivalent_plastic_strain",
        "calculation_displacement_norm",
        "strain_energy_density",
        "stress_norm",
    }
    metrics: dict[str, dict[str, float | int | None]] = {}
    for result in results:
        for key in numeric_keys:
            if key in result and np.isscalar(result[key]):
                metrics.setdefault(key, _empty_metric())
                _update_metric(metrics[key], result[key])
        for key in ("strain", "stress", "principal_stress", "principal_strain"):
            if key in result:
                values = np.asarray(result[key], dtype=float).ravel()
                metrics.setdefault(key, _empty_metric())
                for value in values:
                    _update_metric(metrics[key], value)
    return {key: _finalize_metric(value) for key, value in metrics.items()}


def _residual_diagnostic(solver_selection: dict[str, Any]) -> dict[str, Any]:
    history = solver_selection.get("residual_history", [])
    if not isinstance(history, list):
        return {}
    return {"residual_history": _finalize_metric(_metric_from_values(history))}


def _vector_residual_diagnostic(vectors: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for vector in vectors:
        name = str(vector.get("name", "")).lower()
        if "residual" not in name:
            continue
        result[str(vector.get("name", "residual"))] = {
            key: vector[key]
            for key in ("size", "norm", "max_abs", "nonzero_count")
            if key in vector
        }
    return result


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

    def inspect(
        self,
        model: FiniteElementModel,
        *,
        detail: str = "summary",
        values_warning_rows: int = DEFAULT_AUDIT_SIZE_WARNING_ROWS,
    ) -> SolverAudit:
        detail = validate_audit_detail(detail)
        include_values = detail == "values"
        report = self.validator.validate(model)
        if report.status == "FAIL":
            return SolverAudit.partial(model, report, detail=detail)
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
            include_element_dofs=detail == "values",
            include_indices=detail == "values",
            detail=detail,
            compact_serialization=detail != "values",
            values_warning_rows=values_warning_rows,
            notes=notes,
        )
