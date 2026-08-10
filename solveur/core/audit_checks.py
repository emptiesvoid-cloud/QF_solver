"""Automatic white-box audit checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.mesh.validation import MeshReport


@dataclass(frozen=True)
class AuditCheck:
    """One auditable numerical or mechanical invariant."""

    name: str
    status: str
    value: Any
    limit: Any
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "limit": self.limit,
            "message": self.message,
        }


def build_audit_checks(
    *,
    analysis: str,
    report: MeshReport,
    boundary: dict[str, Any],
    matrices: list[object],
    elements: list[object],
    equilibrium: dict[str, Any],
    post_results: list[dict[str, Any]] | None = None,
) -> list[AuditCheck]:
    """Build PASS/WARNING/FAIL checks from white-box audit data."""
    checks: list[AuditCheck] = [_mesh_check(report)]
    if boundary:
        checks.extend(_boundary_checks(boundary))
    for matrix in matrices:
        checks.extend(_matrix_checks(matrix, scope=f"matrix:{matrix.name}"))
    for element in elements:
        checks.extend(_element_checks(element))
    for post_result in post_results or []:
        checks.extend(_post_result_checks(post_result))
    if equilibrium:
        checks.extend(_equilibrium_checks(analysis, equilibrium))
    return checks


def check_status_counts(checks: list[AuditCheck]) -> dict[str, int]:
    """Count checks by status."""
    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    for check in checks:
        if check.status in counts:
            counts[check.status] += 1
    return counts


def audit_gate_failed(checks: list[AuditCheck], policy: str) -> bool:
    """Return True when checks fail the selected CLI/API gate policy."""
    normalized = policy.lower()
    if normalized == "none":
        return False
    counts = check_status_counts(checks)
    if normalized == "fail":
        return counts["FAIL"] > 0
    if normalized == "warning":
        return counts["FAIL"] > 0 or counts["WARNING"] > 0
    raise ValueError(f"Unsupported audit gate policy {policy!r}.")


def _mesh_check(report: MeshReport) -> AuditCheck:
    if report.status == "FAIL":
        return AuditCheck("mesh_validation", "FAIL", report.status, "PASS or WARNING", "Mesh validation blocks the solve.")
    if report.status == "WARNING":
        return AuditCheck("mesh_validation", "WARNING", report.status, "PASS", "Mesh is usable with warnings.")
    return AuditCheck("mesh_validation", "PASS", report.status, "PASS", "Mesh validation passed.")


def _boundary_checks(boundary: dict[str, Any]) -> list[AuditCheck]:
    fixed = int(boundary.get("fixed_dof_count", 0))
    free = int(boundary.get("free_dof_count", 0))
    return [
        AuditCheck(
            "boundary_has_fixed_dofs",
            "PASS" if fixed > 0 else "FAIL",
            fixed,
            "> 0",
            "At least one fixed dof is required to constrain the model.",
        ),
        AuditCheck(
            "boundary_has_free_dofs",
            "PASS" if free > 0 else "FAIL",
            free,
            "> 0",
            "At least one free dof is required to solve the model.",
        ),
    ]


def _matrix_checks(matrix: object, *, scope: str) -> list[AuditCheck]:
    checks = [
        AuditCheck(
            f"{scope}:finite_norm",
            "PASS" if np.isfinite(matrix.data_norm) else "FAIL",
            matrix.data_norm,
            "finite",
            "Matrix norm must be finite.",
        )
    ]
    if np.isfinite(matrix.symmetry_relative_error):
        checks.append(
            AuditCheck(
                f"{scope}:symmetry",
                _threshold_status(matrix.symmetry_relative_error, pass_limit=1.0e-9, warning_limit=1.0e-8),
                matrix.symmetry_relative_error,
                "<= 1e-9 PASS, <= 1e-8 WARNING",
                "Conservative mechanical matrices are expected to be symmetric.",
            )
        )
    if str(matrix.name).startswith("reduced") and matrix.condition_estimate is not None:
        checks.append(
            AuditCheck(
                f"{scope}:condition_estimate",
                _threshold_status(matrix.condition_estimate, pass_limit=1.0e12, warning_limit=1.0e16),
                matrix.condition_estimate,
                "<= 1e12 PASS, <= 1e16 WARNING",
                "High condition estimates indicate numerical fragility.",
            )
        )
    if matrix.name in {"reduced_stiffness", "reduced_mass"} and matrix.positive_definite_estimate is not None:
        checks.append(
            AuditCheck(
                f"{scope}:positive_definite",
                "PASS" if matrix.positive_definite_estimate else "FAIL",
                matrix.positive_definite_estimate,
                "true",
                "Reduced stiffness/mass matrices should be positive definite after constraints.",
            )
        )
    return checks


def _element_checks(element: object) -> list[AuditCheck]:
    prefix = f"element:{element.index}:{element.type}"
    geometry = element.geometry
    checks: list[AuditCheck] = []
    if "signed_corner_volume" in geometry:
        volume = float(geometry["signed_corner_volume"])
        checks.append(
            AuditCheck(
                f"{prefix}:positive_volume",
                "PASS" if volume > 1.0e-14 else "FAIL",
                volume,
                "> 1e-14",
                "Solid element corner volume must be positive.",
            )
        )
    if "area" in geometry:
        area = float(geometry["area"])
        checks.append(
            AuditCheck(
                f"{prefix}:positive_area",
                "PASS" if area > 1.0e-14 else "FAIL",
                area,
                "> 1e-14",
                "Shell element area must be positive.",
            )
        )
    if "corner_quality" in geometry:
        quality = float(geometry["corner_quality"])
        checks.append(
            AuditCheck(
                f"{prefix}:corner_quality",
                _threshold_status(quality, pass_limit=0.05, warning_limit=0.01, larger_is_better=True),
                quality,
                ">= 0.05 PASS, >= 0.01 WARNING",
                "Low tetrahedral quality can degrade conditioning and stress accuracy.",
            )
        )
    for matrix in element.matrices:
        checks.extend(_matrix_checks(matrix, scope=f"{prefix}:{matrix.name}"))
    return checks


def _post_result_checks(result: dict[str, Any]) -> list[AuditCheck]:
    prefix = f"post:{int(result.get('element', -1))}:{result.get('type', 'UNKNOWN')}"
    checks = [_finite_check(f"{prefix}:finite_calculation_displacement", result.get("calculation_displacement", []))]
    for key in (
        "strain",
        "stress",
        "principal_strain",
        "principal_stress",
        "deviatoric_stress",
        "plastic_strain",
        "membrane_strain",
        "curvature",
        "shear_strain",
        "membrane_force",
        "bending_moment",
        "shear_force",
    ):
        if key in result:
            checks.append(_finite_check(f"{prefix}:finite_{key}", result[key]))
    if "von_mises" in result:
        value = _finite_float(result["von_mises"])
        checks.append(
            AuditCheck(
                f"{prefix}:von_mises_nonnegative",
                "PASS" if value is not None and value >= 0.0 else "FAIL",
                result["von_mises"],
                ">= 0",
                "Von Mises stress must be finite and non-negative.",
            )
        )
    if "equivalent_plastic_strain" in result:
        value = _finite_float(result["equivalent_plastic_strain"])
        checks.append(
            AuditCheck(
                f"{prefix}:equivalent_plastic_strain_nonnegative",
                "PASS" if value is not None and value >= 0.0 else "FAIL",
                result["equivalent_plastic_strain"],
                ">= 0",
                "Equivalent plastic strain must be finite and non-negative.",
            )
        )
    for face in result.get("shell_faces", []):
        face_name = str(face.get("face", "face"))
        checks.append(_finite_check(f"{prefix}:{face_name}:finite_stress", face.get("stress", [])))
        checks.append(_finite_check(f"{prefix}:{face_name}:finite_principal_stress", face.get("principal_stress", [])))
        value = _finite_float(face.get("von_mises", None))
        checks.append(
            AuditCheck(
                f"{prefix}:{face_name}:von_mises_nonnegative",
                "PASS" if value is not None and value >= 0.0 else "FAIL",
                face.get("von_mises", None),
                ">= 0",
                "Shell face Von Mises stress must be finite and non-negative.",
            )
        )
    for point in result.get("integration_points", []):
        point_index = int(point.get("index", -1))
        for key in (
            "strain",
            "stress",
            "principal_strain",
            "principal_stress",
            "plastic_strain",
            "membrane_strain",
            "curvature",
        ):
            if key in point:
                checks.append(_finite_check(f"{prefix}:ip{point_index}:finite_{key}", point[key]))
        if "von_mises" in point:
            value = _finite_float(point["von_mises"])
            checks.append(
                AuditCheck(
                    f"{prefix}:ip{point_index}:von_mises_nonnegative",
                    "PASS" if value is not None and value >= 0.0 else "FAIL",
                    point["von_mises"],
                    ">= 0",
                    "Integration-point Von Mises stress must be finite and non-negative.",
                )
            )
    for item in result.get("nodal_results", []):
        node = int(item.get("node", -1))
        for key in (
            "strain",
            "stress",
            "principal_strain",
            "principal_stress",
            "plastic_strain",
            "membrane_strain",
            "curvature",
        ):
            if key in item:
                checks.append(_finite_check(f"{prefix}:node{node}:finite_{key}", item[key]))
    return checks


def _finite_check(name: str, value: Any) -> AuditCheck:
    try:
        values = np.asarray(value, dtype=float)
        finite = bool(np.all(np.isfinite(values)))
    except (TypeError, ValueError):
        finite = False
    return AuditCheck(name, "PASS" if finite else "FAIL", finite, "all finite", "Recovered post-processing values must be finite.")


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _equilibrium_checks(analysis: str, equilibrium: dict[str, Any]) -> list[AuditCheck]:
    checks = [
        AuditCheck(
            "equilibrium:free_relative_residual",
            _threshold_status(float(equilibrium.get("free_relative_residual", float("inf"))), 1.0e-8, 1.0e-6),
            equilibrium.get("free_relative_residual", float("inf")),
            "<= 1e-8 PASS, <= 1e-6 WARNING",
            "Free dofs should satisfy the solved equilibrium equations.",
        )
    ]
    if "force_balance_relative_error" in equilibrium:
        force_error = float(equilibrium["force_balance_relative_error"])
        checks.append(
            AuditCheck(
                "equilibrium:global_force_balance",
                _threshold_status(force_error, 1.0e-10, 1.0e-8),
                force_error,
                "<= 1e-10 PASS, <= 1e-8 WARNING",
                "Applied forces and support reactions should have a zero global resultant.",
            )
        )
    if "moment_balance_relative_error" in equilibrium:
        moment_error = float(equilibrium["moment_balance_relative_error"])
        checks.append(
            AuditCheck(
                "equilibrium:global_moment_balance",
                _threshold_status(moment_error, 1.0e-10, 1.0e-8),
                moment_error,
                "<= 1e-10 PASS, <= 1e-8 WARNING",
                "Applied loads and support reactions should have a zero global moment about the origin.",
            )
        )
    constraints = equilibrium.get("constraint_forces")
    if isinstance(constraints, dict) and int(constraints.get("equation_count", 0)):
        violation = float(constraints.get("constraint_violation_norm", float("inf")))
        closure = float(constraints.get("equilibrium_relative_error", float("inf")))
        checks.extend(
            [
                AuditCheck(
                    "equilibrium:constraint_compatibility",
                    _threshold_status(violation, 1.0e-10, 1.0e-8),
                    violation,
                    "<= 1e-10 PASS, <= 1e-8 WARNING",
                    "Kinematic constraint equations must be satisfied after reconstruction.",
                ),
                AuditCheck(
                    "equilibrium:constraint_force_closure",
                    _threshold_status(closure, 1.0e-10, 1.0e-8),
                    closure,
                    "<= 1e-10 PASS, <= 1e-8 WARNING",
                    "Recovered constraint forces must close full-space equilibrium.",
                ),
                AuditCheck(
                    "equilibrium:constraint_global_force_closure",
                    _threshold_status(
                        float(constraints.get("global_force_closure_relative_error", float("inf"))),
                        1.0e-10,
                        1.0e-8,
                    ),
                    constraints.get("global_force_closure_relative_error", float("inf")),
                    "<= 1e-10 PASS, <= 1e-8 WARNING",
                    "Constraint generalized forces must close the global force balance of the residual.",
                ),
                AuditCheck(
                    "equilibrium:constraint_global_moment_closure",
                    _threshold_status(
                        float(constraints.get("global_moment_closure_relative_error", float("inf"))),
                        1.0e-10,
                        1.0e-8,
                    ),
                    constraints.get("global_moment_closure_relative_error", float("inf")),
                    "<= 1e-10 PASS, <= 1e-8 WARNING",
                    "Constraint generalized forces must close the global moment balance of the residual.",
                ),
            ]
        )
    if analysis == "linear_static":
        checks.append(
            AuditCheck(
                "equilibrium:linear_energy_identity",
                _threshold_status(
                    float(equilibrium.get("linear_energy_identity_relative_error", float("inf"))),
                    1.0e-8,
                    1.0e-6,
                ),
                equilibrium.get("linear_energy_identity_relative_error", float("inf")),
                "<= 1e-8 PASS, <= 1e-6 WARNING",
                "For linear statics, external work should equal twice the strain energy.",
            )
        )
    return checks


def _threshold_status(
    value: float,
    pass_limit: float,
    warning_limit: float,
    *,
    larger_is_better: bool = False,
) -> str:
    if larger_is_better:
        if value >= pass_limit:
            return "PASS"
        if value >= warning_limit:
            return "WARNING"
        return "FAIL"
    if value <= pass_limit:
        return "PASS"
    if value <= warning_limit:
        return "WARNING"
    return "FAIL"
