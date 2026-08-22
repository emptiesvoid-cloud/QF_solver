"""Algebraic audit of the MITC3+ stiffness and mass condensation path.

This campaign checks that the public 18-DOF matrices are the exact Guyan
projection of the corresponding 20-DOF element matrices.  It is an internal
consistency proof, not an independent shell formulation or an external
Code_Aster correlation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.elements.shell.mitc3 import (
    EXPANDED_DOF_COUNT,
    RETAINED_DOF_COUNT,
    Mitc3ShellElement,
)
from solveur.elements.shell.mitc3_condensation import condense_matrix, condensation_transform
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-MATRIX-CONDENSATION-AUDIT-001"
RELATIVE_LIMIT = 1.0e-12
SYMMETRY_LIMIT = 1.0e-14
STATIONARITY_LIMIT = 1.0e-10
MASS_PSD_LIMIT = 1.0e-12


class Mitc3MatrixCondensationAudit:
    """Verify the algebraic K/M projection used by MITC3+ dynamics."""

    def run(self) -> dict[str, Any]:
        model = cantilever_model(1, 1, laminate=True, transverse_force=0.0)
        material = MaterialFactory.create(model.materials["skin"])
        coordinates = model.nodes[np.asarray(model.elements[0].nodes, dtype=int)]
        element = Mitc3ShellElement(material)
        _, local_coordinates = element.project_to_local_midplane(coordinates)

        expanded_components = element._expanded_stiffness_components(local_coordinates, material)
        expanded_stiffness = _sum_matrices(expanded_components.values(), EXPANDED_DOF_COUNT)
        transform = condensation_transform(expanded_stiffness, RETAINED_DOF_COUNT)
        projected_stiffness = condense_matrix(expanded_stiffness, transform)
        public_components = element.stiffness_local_components(local_coordinates, material)
        public_stiffness = element.stiffness_local(local_coordinates, material)

        expanded_mass = element._expanded_mass_local(local_coordinates, material)
        projected_mass = condense_matrix(expanded_mass, transform)
        public_mass = element.mass_local(local_coordinates, material)

        internal_residual = expanded_stiffness[RETAINED_DOF_COUNT:, :] @ transform
        drilling_indices = np.array([5, 11, 17], dtype=int)
        mass_eigenvalues = np.linalg.eigvalsh(public_mass)
        stiffness_eigenvalues = np.linalg.eigvalsh(public_stiffness)
        stiffness_component_sum = _sum_matrices(public_components.values(), RETAINED_DOF_COUNT)

        metrics = {
            "expanded_stiffness_dimension": list(expanded_stiffness.shape),
            "condensed_stiffness_dimension": list(public_stiffness.shape),
            "expanded_mass_dimension": list(expanded_mass.shape),
            "condensed_mass_dimension": list(public_mass.shape),
            "stiffness_projection_relative_difference": _relative_norm(public_stiffness, projected_stiffness),
            "stiffness_component_sum_relative_difference": _relative_norm(public_stiffness, stiffness_component_sum),
            "mass_projection_relative_difference": _relative_norm(public_mass, projected_mass),
            "condensation_stationarity_relative_residual": float(
                np.linalg.norm(internal_residual) / max(np.linalg.norm(expanded_stiffness), 1.0)
            ),
            "stiffness_symmetry_relative_difference": _relative_norm(public_stiffness, public_stiffness.T),
            "mass_symmetry_relative_difference": _relative_norm(public_mass, public_mass.T),
            "minimum_mass_eigenvalue": float(np.min(mass_eigenvalues)),
            "minimum_stiffness_eigenvalue": float(np.min(stiffness_eigenvalues)),
            "maximum_nodal_drilling_mass_block": float(
                np.max(np.abs(public_mass[np.ix_(drilling_indices, drilling_indices)]))
            ),
            "near_zero_stiffness_mode_count": int(
                np.count_nonzero(np.abs(stiffness_eigenvalues) <= 1.0e-10 * max(np.max(np.abs(stiffness_eigenvalues)), 1.0))
            ),
        }
        checks = {
            "expanded_dimension_is_20_dof": tuple(expanded_stiffness.shape) == (EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT),
            "condensed_dimension_is_18_dof": public_stiffness.shape == (RETAINED_DOF_COUNT, RETAINED_DOF_COUNT),
            "stiffness_projection_identity": metrics["stiffness_projection_relative_difference"] <= RELATIVE_LIMIT,
            "stiffness_component_additivity": metrics["stiffness_component_sum_relative_difference"] <= RELATIVE_LIMIT,
            "mass_projection_identity": metrics["mass_projection_relative_difference"] <= RELATIVE_LIMIT,
            "condensation_stationarity": metrics["condensation_stationarity_relative_residual"] <= STATIONARITY_LIMIT,
            "stiffness_symmetry": metrics["stiffness_symmetry_relative_difference"] <= SYMMETRY_LIMIT,
            "mass_symmetry": metrics["mass_symmetry_relative_difference"] <= SYMMETRY_LIMIT,
            "mass_positive_semidefinite": metrics["minimum_mass_eigenvalue"] >= -MASS_PSD_LIMIT,
            "no_nodal_drilling_mass": metrics["maximum_nodal_drilling_mass_block"] <= 1.0e-30,
            "six_shell_rigid_modes_present": metrics["near_zero_stiffness_mode_count"] >= 6,
        }
        return {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "status": "PASS_ALGEBRAIC_CONDENSATION" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "MITC3+ element-level K/M Guyan condensation",
            "model": {
                "geometry": "one planar laminate triangle",
                "layup": [0.0, 90.0, 90.0, 0.0],
                "expanded_dofs": EXPANDED_DOF_COUNT,
                "retained_dofs": RETAINED_DOF_COUNT,
                "internal_dofs": 2,
            },
            "operator_definition": {
                "stiffness": "Kc = T.T @ Kexpanded @ T",
                "mass": "Mc = T.T @ Mexpanded @ T",
                "transform": "T = [I; -Kii^-1 Kia]",
            },
            "metrics": metrics,
            "checks": checks,
            "interpretation": (
                "The public MITC3+ stiffness and mass matrices reproduce the "
                "same 20-DOF operators projected through the same condensation "
                "transform. This closes an internal K/M chain-consistency item; "
                "it does not establish identity with Code_Aster DST or another "
                "independent shell formulation."
            ),
            "limitations": [
                "Element-level algebraic audit only; no structural external correlation.",
                "The audit uses the existing MITC3+ shape, constitutive and tying definitions.",
                "The general MITC3 dynamic scope remains blocked by external errors above one percent.",
            ],
        }


def write_mitc3_matrix_condensation_audit(output: str | Path) -> dict[str, Any]:
    """Write JSON, Markdown and a manifest for the condensation audit."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3MatrixCondensationAudit().run()
    write_json_file(target / "summary.json", summary)
    (target / "report.md").write_text(_report(summary), encoding="utf-8")
    write_vnv_manifest(target, STUDY_ID)
    return summary


def _sum_matrices(matrices: Any, dimension: int) -> np.ndarray:
    return sum(matrices, start=np.zeros((dimension, dimension), dtype=float))


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0e-30))


def _report(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    checks = summary["checks"]
    rows = [
        ("Projection K 20→18", "stiffness_projection_relative_difference", RELATIVE_LIMIT),
        ("Additivité des composantes K", "stiffness_component_sum_relative_difference", RELATIVE_LIMIT),
        ("Projection M 20→18", "mass_projection_relative_difference", RELATIVE_LIMIT),
        ("Stationnarité interne", "condensation_stationarity_relative_residual", STATIONARITY_LIMIT),
        ("Symétrie K", "stiffness_symmetry_relative_difference", SYMMETRY_LIMIT),
        ("Symétrie M", "mass_symmetry_relative_difference", SYMMETRY_LIMIT),
    ]
    lines = [
        f"# {summary['study_id']}",
        "",
        "Audit algébrique élémentaire de la condensation MITC3+.",
        "",
        "La preuve compare explicitement les opérateurs développés 20 DDL et les opérateurs publics condensés 18 DDL.",
        "",
        "| Contrôle | Valeur | Limite | Verdict |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {label} | `{metrics[key]:.6e}` | `{limit:.1e}` | {'PASS' if _check_value(key, metrics, checks) else 'FAIL'} |"
        for label, key, limit in rows
    )
    lines.extend(
        [
            "",
            f"Statut : **{summary['status']}**.",
            "",
            "## Interprétation",
            "",
            summary["interpretation"],
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"


def _check_value(key: str, metrics: dict[str, Any], checks: dict[str, bool]) -> bool:
    mapping = {
        "stiffness_projection_relative_difference": "stiffness_projection_identity",
        "stiffness_component_sum_relative_difference": "stiffness_component_additivity",
        "mass_projection_relative_difference": "mass_projection_identity",
        "condensation_stationarity_relative_residual": "condensation_stationarity",
        "stiffness_symmetry_relative_difference": "stiffness_symmetry",
        "mass_symmetry_relative_difference": "mass_symmetry",
    }
    return bool(checks[mapping[key]])
