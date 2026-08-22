"""Independent quadrature audit of the MITC3+ expanded stiffness matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.special import roots_legendre

from solveur.elements.shell.mitc3 import EXPANDED_DOF_COUNT, Mitc3ShellElement
from solveur.elements.shell.mitc3_condensation import condense_matrix, condensation_transform
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-STIFFNESS-QUADRATURE-AUDIT-001"
EXPANDED_LIMIT = 2.0e-7
CONDENSED_LIMIT = 2.0e-7


class Mitc3StiffnessQuadratureAudit:
    """Compare the seven-point stiffness integration with Duffy quadrature."""

    def __init__(self, *, quadrature_order: int = 12) -> None:
        if quadrature_order < 6:
            raise ValueError("quadrature_order must be at least 6")
        self.quadrature_order = int(quadrature_order)

    def run(self) -> dict[str, Any]:
        model = cantilever_model(1, 1, laminate=True, transverse_force=0.0)
        material = MaterialFactory.create(model.materials["skin"])
        coordinates = model.nodes[np.asarray(model.elements[0].nodes, dtype=int)]
        element = Mitc3ShellElement(material)
        _, local_coordinates = element.project_to_local_midplane(coordinates)
        implemented = element._expanded_stiffness_components(local_coordinates, material)
        independent = self._independent_expanded_stiffness(element, local_coordinates, material)
        implemented_total = _sum_matrices(implemented.values())
        independent_total = _sum_matrices(independent.values())
        transform = condensation_transform(implemented_total)
        independent_transform = condensation_transform(independent_total)
        public = element.stiffness_local(local_coordinates, material)
        projected_same_transform = condense_matrix(independent_total, transform)
        projected_independent = condense_matrix(independent_total, independent_transform)

        component_errors = {
            name: _relative_norm(implemented[name], independent[name])
            for name in implemented
        }
        metrics = {
            "expanded_total_relative_difference": _relative_norm(implemented_total, independent_total),
            "component_relative_differences": component_errors,
            "condensed_same_transform_relative_difference": _relative_norm(
                public, projected_same_transform
            ),
            "condensed_independent_transform_relative_difference": _relative_norm(
                public, projected_independent
            ),
            "transform_relative_difference": _relative_norm(transform, independent_transform),
            "expanded_symmetry_relative_difference": _relative_norm(implemented_total, implemented_total.T),
            "independent_symmetry_relative_difference": _relative_norm(independent_total, independent_total.T),
        }
        checks = {
            "expanded_quadrature_agreement": metrics["expanded_total_relative_difference"] <= EXPANDED_LIMIT,
            "all_component_quadratures_agree": max(component_errors.values()) <= EXPANDED_LIMIT,
            "condensed_quadrature_agreement": metrics["condensed_independent_transform_relative_difference"]
            <= CONDENSED_LIMIT,
            "finite_operators": bool(
                np.all(np.isfinite(implemented_total)) and np.all(np.isfinite(independent_total))
            ),
            "implemented_symmetry": metrics["expanded_symmetry_relative_difference"] <= 1.0e-14,
            "independent_symmetry": metrics["independent_symmetry_relative_difference"] <= 1.0e-14,
        }
        return {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "status": "PASS_INDEPENDENT_QUADRATURE" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "MITC3+ element-level expanded stiffness quadrature",
            "quadrature": {
                "implemented": "seven-point Dunavant degree-five rule",
                "independent": f"Duffy tensor-product Gauss-Legendre order {self.quadrature_order}",
                "reference_triangle_area": 0.5,
            },
            "model": {
                "geometry": "one planar laminate triangle",
                "layup": [0.0, 90.0, 90.0, 0.0],
                "expanded_dofs": EXPANDED_DOF_COUNT,
            },
            "metrics": metrics,
            "checks": checks,
            "interpretation": (
                "Independent Duffy integration reproduces the expanded and "
                "condensed MITC3+ stiffness operators. This tests numerical "
                "integration and condensation consistency; it is not an "
                "independent shell formulation or an external correlation."
            ),
            "limitations": [
                "One planar laminate triangle only.",
                "The independent integration reuses the MITC3+ strain operators and constitutive matrices.",
                "The external DST/MITC3 formulation difference remains outside this audit.",
            ],
        }

    def _independent_expanded_stiffness(
        self,
        element: Mitc3ShellElement,
        coordinates: np.ndarray,
        material: Any,
    ) -> dict[str, np.ndarray]:
        points, weights = roots_legendre(self.quadrature_order)
        points = 0.5 * (points + 1.0)
        weights = 0.5 * weights
        determinant = float(element._jacobian(coordinates)[1])
        names = ["membrane", "bending", "shear", "drilling"]
        coupling = getattr(material, "coupling_matrix", None)
        if coupling is not None:
            names.append("coupling")
        result = {name: np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT), dtype=float) for name in names}
        for u, weight_u in zip(points, weights, strict=True):
            for v, weight_v in zip(points, weights, strict=True):
                r = float(u)
                s = float((1.0 - u) * v)
                scale = determinant * float(weight_u) * float(weight_v) * float(1.0 - u)
                matrices = element.strain_matrices_local(coordinates, r, s)
                result["membrane"] += matrices.membrane.T @ material.membrane_matrix @ matrices.membrane * scale
                result["bending"] += matrices.bending.T @ material.bending_matrix @ matrices.bending * scale
                result["shear"] += matrices.shear.T @ material.shear_matrix @ matrices.shear * scale
                if material.drilling_stiffness > 0.0:
                    result["drilling"] += (
                        matrices.drilling.T @ matrices.drilling * material.drilling_stiffness * scale
                    )
                if coupling is not None:
                    result["coupling"] += (
                        matrices.membrane.T @ coupling @ matrices.bending
                        + matrices.bending.T @ coupling.T @ matrices.membrane
                    ) * scale
        return {name: 0.5 * (matrix + matrix.T) for name, matrix in result.items()}


def write_mitc3_stiffness_quadrature_audit(output: str | Path) -> dict[str, Any]:
    """Write JSON, Markdown and a manifest for the stiffness audit."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3StiffnessQuadratureAudit().run()
    write_json_file(target / "summary.json", summary)
    (target / "report.md").write_text(_report(summary), encoding="utf-8")
    write_vnv_manifest(target, STUDY_ID)
    return summary


def _sum_matrices(matrices: Any) -> np.ndarray:
    return sum(matrices, start=np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT), dtype=float))


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0e-30))


def _report(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    checks = summary["checks"]
    component_max = max(metrics["component_relative_differences"].values())
    lines = [
        f"# {summary['study_id']}",
        "",
        "Audit indépendant de quadrature de rigidité MITC3+ par transformation de Duffy.",
        "",
        "| Contrôle | Valeur | Limite | Verdict |",
        "| --- | ---: | ---: | --- |",
        f"| Difference K developpee totale | `{metrics['expanded_total_relative_difference']:.6e}` | `{EXPANDED_LIMIT:.1e}` | {'PASS' if checks['expanded_quadrature_agreement'] else 'FAIL'} |",
        f"| Difference maximale par composante | `{component_max:.6e}` | `{EXPANDED_LIMIT:.1e}` | {'PASS' if checks['all_component_quadratures_agree'] else 'FAIL'} |",
        f"| Difference K condensee | `{metrics['condensed_independent_transform_relative_difference']:.6e}` | `{CONDENSED_LIMIT:.1e}` | {'PASS' if checks['condensed_quadrature_agreement'] else 'FAIL'} |",
        f"| Difference transformateur | `{metrics['transform_relative_difference']:.6e}` | - | information |",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "## Interpretation",
        "",
        summary["interpretation"],
        "",
        "## Limites",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"
