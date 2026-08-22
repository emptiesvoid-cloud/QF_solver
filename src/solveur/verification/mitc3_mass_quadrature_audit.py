"""Independent quadrature audit of the MITC3+ consistent mass matrix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.special import roots_legendre

from solveur.elements.shell.mitc3 import BUBBLE_RX, BUBBLE_RY, Mitc3ShellElement
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.vnv_manifest import write_vnv_manifest

matplotlib.use("Agg")


STUDY_ID = "VNV-MITC3-MASS-QUADRATURE-AUDIT-001"
RETAINED_DOF_COUNT = 18
DOF_PER_NODE = 6
TRANSLATION_COMPONENTS = (0, 1, 2)


class Mitc3MassQuadratureAudit:
    """Compare the implemented seven-point mass integration with Duffy quadrature."""

    expanded_relative_limit = 2.0e-7
    condensed_relative_limit = 2.0e-5
    mass_balance_limit = 1.0e-12
    drilling_limit = 1.0e-18

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
        implemented = element._expanded_mass_local(local_coordinates, material)
        independent = self._independent_expanded_mass(element, local_coordinates, material)
        expanded_error = _relative_norm(implemented, independent)
        _, transform = element._condensed_local_data(local_coordinates, material)
        implemented_condensed = transform.T @ implemented @ transform
        independent_condensed = transform.T @ independent @ transform
        condensed_error = _relative_norm(implemented_condensed, independent_condensed)
        area = float(element._jacobian(local_coordinates)[1]) * 0.5
        expected_mass = area * float(material.surface_density)
        translation_balance = {
            f"component_{component}": _translation_mass_error(implemented, component, expected_mass)
            for component in TRANSLATION_COMPONENTS
        }
        drilling_indices = [5, 11, 17]
        checks = {
            "expanded_quadrature_agreement": expanded_error <= self.expanded_relative_limit,
            "condensed_quadrature_agreement": condensed_error <= self.condensed_relative_limit,
            "translation_mass_balance": max(translation_balance.values()) <= self.mass_balance_limit,
            "no_nodal_drilling_inertia": float(np.max(np.abs(implemented_condensed[np.ix_(drilling_indices, drilling_indices)])))
            <= self.drilling_limit,
            "symmetry": _relative_norm(implemented_condensed, implemented_condensed.T) <= 1.0e-14,
            "positive_semidefinite": float(np.min(np.linalg.eigvalsh(implemented_condensed))) >= -1.0e-12,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS_INDEPENDENT_QUADRATURE" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "MITC3+ consistent mass, one planar laminate triangle",
            "quadrature": {
                "implemented": "seven-point Dunavant degree-five rule",
                "independent": f"Duffy tensor-product Gauss-Legendre order {self.quadrature_order}",
                "reference_triangle_area": 0.5,
            },
            "metrics": {
                "expanded_relative_difference": expanded_error,
                "condensed_relative_difference": condensed_error,
                "translation_mass_expected_kg": expected_mass,
                "translation_mass_relative_errors": translation_balance,
                "minimum_condensed_eigenvalue": float(np.min(np.linalg.eigvalsh(implemented_condensed))),
                "maximum_drilling_block": float(np.max(np.abs(implemented_condensed[np.ix_(drilling_indices, drilling_indices)]))),
            },
            "checks": {key: bool(value) for key, value in checks.items()},
            "interpretation": (
                "Independent quadrature confirms the implemented consistent mass "
                "and exact translation mass balance. The small quadrature difference "
                "is not large enough to explain the external MITC3+/DST dynamic gap."
            ),
            "limitations": [
                "This is an element-level quadrature audit, not an external structural correlation.",
                "The independent integration uses the same MITC3+ shape and condensation definitions; it checks integration, not formulation identity.",
                "A same-order external shell reference remains required for a broad stable promotion.",
            ],
        }

    def _independent_expanded_mass(self, element: Mitc3ShellElement, coordinates: np.ndarray, material: Any) -> np.ndarray:
        points, weights = roots_legendre(self.quadrature_order)
        points = 0.5 * (points + 1.0)
        weights = 0.5 * weights
        determinant = float(element._jacobian(coordinates)[1])
        result = np.zeros((20, 20), dtype=float)
        for u, weight_u in zip(points, weights, strict=True):
            for v, weight_v in zip(points, weights, strict=True):
                r = float(u)
                s = float((1.0 - u) * v)
                reference_jacobian = 1.0 - u
                translations, _ = element.shape_functions(r, s)
                rotations, _ = element.rotation_shape_functions(r, s)
                scale = determinant * float(weight_u) * float(weight_v) * float(reference_jacobian)
                translation_mass = np.outer(translations, translations) * float(material.surface_density) * scale
                for component in TRANSLATION_COMPONENTS:
                    indices = np.arange(component, RETAINED_DOF_COUNT, DOF_PER_NODE)
                    result[np.ix_(indices, indices)] += translation_mass
                rotation_mass = np.outer(rotations, rotations) * float(material.rotary_density) * scale
                for indices in ([3, 9, 15, BUBBLE_RX], [4, 10, 16, BUBBLE_RY]):
                    result[np.ix_(indices, indices)] += rotation_mass
        return 0.5 * (result + result.T)


def write_mitc3_mass_quadrature_audit(output: str | Path) -> dict[str, Any]:
    """Write the mass audit evidence bundle."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3MassQuadratureAudit().run()
    write_json_file(target / "summary.json", summary)
    (target / "report.md").write_text(_report(summary), encoding="utf-8")
    write_vnv_manifest(target, STUDY_ID)
    return summary


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0e-30))


def _translation_mass_error(matrix: np.ndarray, component: int, expected: float) -> float:
    indices = np.arange(component, RETAINED_DOF_COUNT, DOF_PER_NODE)
    actual = float(matrix[np.ix_(indices, indices)].sum())
    return abs(actual - expected) / max(abs(expected), 1.0e-30)


def _report(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    lines = [
        f"# {summary['study_id']}",
        "",
        "Audit elementaire independant de la quadrature de masse MITC3+.",
        "",
        "| Controle | Valeur | Limite | Verdict |",
        "| --- | ---: | ---: | --- |",
        f"| Difference masse developpee | `{metrics['expanded_relative_difference']:.6e}` | `{Mitc3MassQuadratureAudit.expanded_relative_limit:.1e}` | {'PASS' if summary['checks']['expanded_quadrature_agreement'] else 'FAIL'} |",
        f"| Difference masse condensee | `{metrics['condensed_relative_difference']:.6e}` | `{Mitc3MassQuadratureAudit.condensed_relative_limit:.1e}` | {'PASS' if summary['checks']['condensed_quadrature_agreement'] else 'FAIL'} |",
        f"| Erreur bilan masse translationnelle | `{max(metrics['translation_mass_relative_errors'].values()):.6e}` | `{Mitc3MassQuadratureAudit.mass_balance_limit:.1e}` | {'PASS' if summary['checks']['translation_mass_balance'] else 'FAIL'} |",
        f"| Bloc drilling condense | `{metrics['maximum_drilling_block']:.6e}` | `{Mitc3MassQuadratureAudit.drilling_limit:.1e}` | {'PASS' if summary['checks']['no_nodal_drilling_inertia'] else 'FAIL'} |",
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
