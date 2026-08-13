"""Analytical verification campaign for oriented orthotropic TET4/TET10 solids."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import write_json_file
from solveur.materials.orthotropic import OrthotropicSolidMaterial, material_orientation
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-ORTHOTROPIC-SOLID-KERNEL-001"


class OrthotropicSolidKernelCampaign:
    """Verify constitutive axes, rotations and affine tetrahedral patches."""

    study_id = STUDY_ID

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        material = reference_material()
        checks = [
            _upper("compliance_symmetry", _relative_symmetry(material.compliance_matrix), 1.0e-12),
            _lower("compliance_minimum_eigenvalue", float(np.min(np.linalg.eigvalsh(material.compliance_matrix))), 0.0),
            _upper("stiffness_symmetry", _relative_symmetry(material.elasticity_matrix), 1.0e-12),
        ]
        for component in range(6):
            target = np.zeros(6)
            target[component] = 19.0e6
            strain = material.compliance_matrix @ target
            recovered = material.material_elasticity_matrix @ strain
            checks.append(_upper(f"material_unit_stress_{component}", _relative_vector(recovered, target), 1.0e-12))

        rotation = material_orientation(e1=[1.0, 2.0, 0.4], e2_hint=[-0.3, 0.2, 1.0])
        rotated = reference_material(rotation)
        local_strain = np.array([2.0e-4, -0.7e-4, 0.4e-4, 1.1e-4, -0.6e-4, 0.8e-4])
        global_strain = rotated.strain_global_axes(local_strain)
        local_stress = rotated.material_elasticity_matrix @ local_strain
        global_stress = rotated.elasticity_matrix @ global_strain
        checks.extend(
            [
                _upper(
                    "rotated_stress_transformation",
                    _relative_vector(rotated.stress_material_axes(global_stress), local_stress),
                    1.0e-12,
                ),
                _upper(
                    "rotated_energy_invariance",
                    _relative_scalar(global_stress @ global_strain, local_stress @ local_strain),
                    1.0e-12,
                ),
            ]
        )

        gradient = np.array([[2.0e-4, 3.0e-5, -2.0e-5], [4.0e-5, -1.0e-4, 5.0e-5], [1.0e-5, 6.0e-5, 0.5e-4]])
        expected_strain = _engineering_strain(gradient)
        expected_stress = rotated.elasticity_matrix @ expected_strain
        element_rows = []
        for name, element, coords in (
            ("TET4", Tet4Element(rotated), _tet4_coords()),
            ("TET10", Tet10Element(rotated), _tet10_coords()),
        ):
            displacement = (coords @ gradient.T).reshape(-1)
            strain = element.strain(coords, displacement)
            stress = element.stress(coords, displacement)
            stiffness = element.stiffness(coords)
            strain_error = _relative_vector(strain, expected_strain)
            stress_error = _relative_vector(stress, expected_stress)
            rigid_residual = _rigid_mode_residual(stiffness, coords)
            checks.extend(
                [
                    _upper(f"{name.lower()}_affine_strain", strain_error, 1.0e-10),
                    _upper(f"{name.lower()}_affine_stress", stress_error, 1.0e-10),
                    _upper(f"{name.lower()}_stiffness_symmetry", _relative_symmetry(stiffness), 1.0e-12),
                    _upper(f"{name.lower()}_rigid_modes", rigid_residual, 1.0e-10),
                ]
            )
            element_rows.append(
                {
                    "element": name,
                    "strain_error": strain_error,
                    "stress_error": stress_error,
                    "rigid_mode_residual": rigid_residual,
                }
            )

        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "research",
            "covered_specifications": [
                "SPEC-COMP-SOLID-001",
                "SPEC-COMP-SOLID-002",
                "SPEC-COMP-SOLID-003",
                "SPEC-COMP-SOLID-004",
                "SPEC-COMP-SOLID-005",
            ],
            "material": _material_summary(rotated),
            "element_results": element_rows,
            "checks": checks,
            "open_specifications": [],
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
            "| Element | Erreur deformation | Erreur contrainte | Residu modes rigides |",
            "| --- | ---: | ---: | ---: |",
        ]
        for row in summary["element_results"]:
            lines.append(
                f"| {row['element']} | {row['strain_error']:.3e} | {row['stress_error']:.3e} | "
                f"{row['rigid_mode_residual']:.3e} |"
            )
        lines.extend(
            [
                "",
                "Les specifications `001..005` sont couvertes. La convergence structurelle,",
                "les campagnes complementaires 002, 003 et 004 couvrent les specifications restantes.",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reference_material(orientation: np.ndarray | None = None) -> OrthotropicSolidMaterial:
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
        orientation=np.eye(3) if orientation is None else orientation,
    )


def _tet4_coords() -> np.ndarray:
    return np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def _tet10_coords() -> np.ndarray:
    corners = _tet4_coords()
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    return np.vstack((corners, [0.5 * (corners[first] + corners[second]) for first, second in edges]))


def _engineering_strain(gradient: np.ndarray) -> np.ndarray:
    return np.array(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )


def _rigid_mode_residual(stiffness: np.ndarray, coords: np.ndarray) -> float:
    norm = max(float(np.linalg.norm(stiffness, ord=np.inf)), 1.0)
    modes = []
    for axis in range(3):
        mode = np.zeros(coords.shape[0] * 3)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        modes.append(np.concatenate([np.cross(axis, point) for point in coords]))
    return max(float(np.linalg.norm(stiffness @ mode, ord=np.inf)) / norm for mode in modes)


def _relative_symmetry(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix - matrix.T) / max(np.linalg.norm(matrix), np.finfo(float).tiny))


def _relative_vector(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), np.finfo(float).tiny))


def _relative_scalar(value: float, reference: float) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value > limit else "FAIL"}


def _material_summary(material: OrthotropicSolidMaterial) -> dict[str, object]:
    return {
        "constants": {
            key: float(getattr(material, key))
            for key in ("E1", "E2", "E3", "nu12", "nu13", "nu23", "G12", "G13", "G23")
        },
        "orientation": material.orientation.tolist(),
    }
