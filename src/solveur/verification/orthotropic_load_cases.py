"""Verification of rotated, biaxial and combined-shear orthotropic states."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import write_json_file
from solveur.materials.orthotropic import (
    OrthotropicSolidMaterial,
    material_orientation,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-ORTHOTROPIC-SOLID-LOAD-CASES-007"
_LOAD_CASES = {
    "biaxial": np.array([2.0e-4, -1.0e-4, 0.5e-4, 0.0, 0.0, 0.0]),
    "combined_shear": np.array([0.0, 0.0, 0.0, 1.4e-4, -0.9e-4, 1.1e-4]),
    "mixed": np.array([1.5e-4, -0.5e-4, 0.75e-4, 1.1e-4, -0.7e-4, 0.9e-4]),
}


class OrthotropicLoadCaseCampaign:
    """Check material-axis projections on affine TET4 and TET10 states."""

    study_id = STUDY_ID
    angles_deg = (0.0, 17.0, 31.0, 45.0, 73.0)

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        checks: list[dict[str, object]] = []
        for angle in self.angles_deg:
            basis = _z_rotation(angle)
            material = _reference_material(basis)
            for case_name, local_strain in _LOAD_CASES.items():
                global_strain = material.strain_global_axes(local_strain)
                expected_local_stress = material.material_elasticity_matrix @ local_strain
                global_stress = material.elasticity_matrix @ global_strain
                recovered_local_stress = material.stress_material_axes(global_stress)
                stress_error = _relative(recovered_local_stress, expected_local_stress)
                energy_error = _relative(
                    float(global_stress @ global_strain),
                    float(expected_local_stress @ local_strain),
                )
                checks.extend(
                    [
                        _upper(f"angle_{angle:g}_{case_name}_stress_projection", stress_error, 1.0e-12),
                        _upper(f"angle_{angle:g}_{case_name}_energy_invariance", energy_error, 1.0e-12),
                    ]
                )
                rows.append(
                    {
                        "angle_deg": angle,
                        "load_case": case_name,
                        "stress_projection_error": stress_error,
                        "energy_invariance_error": energy_error,
                    }
                )
                for family, element, coordinates in (
                    ("TET4", Tet4Element(material), _tet4_coordinates()),
                    ("TET10", Tet10Element(material), _tet10_coordinates()),
                ):
                    gradient = _gradient_from_engineering_strain(global_strain)
                    displacement = (coordinates @ gradient.T).reshape(-1)
                    element_strain = element.strain(coordinates, displacement)
                    element_stress = element.stress(coordinates, displacement)
                    strain_error = _relative(element_strain, global_strain)
                    element_stress_error = _relative(element_stress, global_stress)
                    checks.extend(
                        [
                            _upper(
                                f"angle_{angle:g}_{case_name}_{family.lower()}_strain", strain_error, 1.0e-10
                            ),
                            _upper(
                                f"angle_{angle:g}_{case_name}_{family.lower()}_stress", element_stress_error, 1.0e-10
                            ),
                        ]
                    )
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "technical_verification",
            "scope": "orthotropic-solid-tet4-tet10",
            "orientations_deg": list(self.angles_deg),
            "load_cases": list(_LOAD_CASES),
            "rows": rows,
            "checks": checks,
            "limitations": [
                "The cases verify a homogeneous small-strain material law, not ply-resolved damage.",
                "The campaign is a constitutive and element verification, not a structural oracle.",
                "Curvilinear orientation fields remain limited to one basis per linear element.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Verdict automatise : **{summary['status']}**",
            "",
            "Cette campagne couvre des orientations tournees et trois etats de deformation : biaxial, cisaillement combine et mixte.",
            "La comparaison est faite dans les axes materiau puis reprojetee dans le repere global.",
            "",
            "| Angle | Cas | Erreur projection contrainte | Erreur energie |",
            "| ---: | --- | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['angle_deg']:.0f} deg | {row['load_case']} | "
                f"{row['stress_projection_error']:.3e} | {row['energy_invariance_error']:.3e} |"
            )
        lines.extend(
            [
                "",
                "Les essais TET4 et TET10 utilisent un champ affine, pour lequel la deformation constante est une reference exacte.",
                "Cette preuve ne ferme pas la convergence structurale TET4 en flexion orthotrope ; elle isole seulement la projection constitutive.",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _reference_material(orientation: np.ndarray) -> OrthotropicSolidMaterial:
    return OrthotropicSolidMaterial(
        E1=135.0e9,
        E2=10.0e9,
        E3=8.0e9,
        nu12=0.28,
        nu13=0.22,
        nu23=0.35,
        G12=5.2e9,
        G13=4.1e9,
        G23=3.3e9,
        density=1580.0,
        orientation=orientation,
    )


def _z_rotation(angle_deg: float) -> np.ndarray:
    angle = np.deg2rad(angle_deg)
    return material_orientation(
        orientation=np.array(
            [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
        )
    )


def _tet4_coordinates() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def _tet10_coordinates() -> np.ndarray:
    corners = _tet4_coordinates()
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    midpoints = [0.5 * (corners[first] + corners[second]) for first, second in edges]
    return np.vstack((corners, midpoints))


def _gradient_from_engineering_strain(strain: np.ndarray) -> np.ndarray:
    e1, e2, e3, g12, g23, g13 = strain
    return np.array([[e1, 0.5 * g12, 0.5 * g13], [0.5 * g12, e2, 0.5 * g23], [0.5 * g13, 0.5 * g23, e3]])


def _relative(value: np.ndarray | float, reference: np.ndarray | float) -> float:
    value_array = np.asarray(value, dtype=float)
    reference_array = np.asarray(reference, dtype=float)
    return float(np.linalg.norm(value_array - reference_array) / max(np.linalg.norm(reference_array), np.finfo(float).tiny))


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
