"""Executable mechanical verification checks for the TET10 formulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.materials.solid import SolidMaterial


@dataclass(frozen=True)
class Tet10VerificationCheck:
    """One bounded numerical observation."""

    name: str
    value: float
    limit: float
    status: str
    details: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Tet10MechanicalVerifier:
    """Run deterministic element-level analytical and convergence checks."""

    def run(self) -> dict[str, object]:
        checks = [
            self._mass_symmetry(),
            self._mass_total(),
            self._mass_positive(),
            self._affine_patch(),
            self._affine_energy(),
            self._quadratic_recovery(),
            self._tet4_refinement_rate(),
            self._closed_form_edge_mode(),
        ]
        return {
            "status": "PASS" if all(check.status == "PASS" for check in checks) else "FAIL",
            "element": "TET10",
            "purpose": "mechanical_verification",
            "checks": [check.to_dict() for check in checks],
        }

    def _mass_symmetry(self) -> Tet10VerificationCheck:
        mass = self._element(density=7800.0).mass(_unit_coords())
        scale = max(float(np.linalg.norm(mass)), 1.0)
        value = float(np.linalg.norm(mass - mass.T) / scale)
        return _upper_check("consistent mass symmetry", value, 1.0e-13, "M must be symmetric.")

    def _mass_total(self) -> Tet10VerificationCheck:
        density = 7800.0
        mass = self._element(density=density).mass(_unit_coords())
        expected = 3.0 * density / 6.0
        value = abs(float(np.sum(mass)) - expected) / expected
        return _upper_check("consistent mass total", value, 1.0e-12, "Three translations carry rho*V each.")

    def _mass_positive(self) -> Tet10VerificationCheck:
        mass = self._element(density=7800.0).mass(_unit_coords())
        eigenvalues = np.linalg.eigvalsh(mass)
        value = max(0.0, -float(np.min(eigenvalues))) / max(float(np.max(eigenvalues)), 1.0)
        return _upper_check("consistent mass positive definiteness", value, 1.0e-13, "No negative mass mode.")

    def _affine_patch(self) -> Tet10VerificationCheck:
        element = self._element()
        coords = _unit_coords()
        displacement, expected = _affine_field(coords)
        errors = []
        for point in element.integration_points:
            b_matrix, _ = element.b_matrix(coords, point)
            errors.append(float(np.linalg.norm(b_matrix @ displacement - expected)))
        value = max(errors) / max(float(np.linalg.norm(expected)), 1.0e-30)
        return _upper_check("affine strain patch", value, 1.0e-11, "All Hammer points reproduce affine strain.")

    def _affine_energy(self) -> Tet10VerificationCheck:
        material = SolidMaterial(E=210.0e9, nu=0.3)
        element = Tet10Element(material)
        coords = _unit_coords()
        displacement, expected_strain = _affine_field(coords)
        observed = float(0.5 * displacement @ (element.stiffness(coords) @ displacement))
        expected = float(0.5 / 6.0 * expected_strain @ (material.elasticity_matrix @ expected_strain))
        value = abs(observed - expected) / max(abs(expected), 1.0e-30)
        return _upper_check("affine analytical energy", value, 1.0e-11, "u^T K u / 2 matches volume energy.")

    def _quadratic_recovery(self) -> Tet10VerificationCheck:
        element = self._element()
        coords = _unit_coords()
        displacement = np.zeros(30)
        displacement[0::3] = coords[:, 0] ** 2
        point_strains = []
        for point in element.integration_points:
            b_matrix, _ = element.b_matrix(coords, point)
            point_strains.append(b_matrix @ displacement)
        nodal = element.extrapolate_integration_values(np.asarray(point_strains))
        expected = 2.0 * coords[:, 0]
        value = float(np.max(np.abs(nodal[:, 0] - expected)))
        return _upper_check("quadratic field recovery", value, 1.0e-12, "Linear strain is exact at TET10 nodes.")

    def _tet4_refinement_rate(self) -> Tet10VerificationCheck:
        element = Tet4Element(SolidMaterial(E=1000.0, nu=0.25))
        errors = []
        for size in (1.0, 0.5, 0.25):
            coords = _unit_coords()[:4] * size
            displacement = np.zeros(12)
            displacement[0::3] = coords[:, 0] ** 2
            observed = element.strain(coords, displacement)[0]
            errors.append(abs(float(observed) - 0.5 * size))
        ratios = np.asarray(errors[:-1]) / errors[1:]
        value = float(np.max(np.abs(ratios - 2.0)))
        return _upper_check("TET4 linear refinement reference", value, 1.0e-12, "TET4 error halves when h halves.")

    def _closed_form_edge_mode(self) -> Tet10VerificationCheck:
        density = 7800.0
        material = SolidMaterial(E=210.0e9, nu=0.3, density=density)
        element = Tet10Element(material)
        stiffness = element.stiffness(_unit_coords())
        mass = element.mass(_unit_coords())
        edge_node_ux = 12
        observed = float(stiffness[edge_node_ux, edge_node_ux] / mass[edge_node_ux, edge_node_ux])
        lame = material.nu * material.E / ((1.0 + material.nu) * (1.0 - 2.0 * material.nu))
        shear = material.E / (2.0 * (1.0 + material.nu))
        expected = 21.0 * (lame + 4.0 * shear) / density
        value = abs(observed - expected) / expected
        return _upper_check(
            "closed-form one-dof edge eigenvalue",
            value,
            1.0e-11,
            "lambda_mode = 21*(lambda_Lame + 4*mu)/rho.",
        )

    @staticmethod
    def _element(density: float = 0.0) -> Tet10Element:
        return Tet10Element(SolidMaterial(E=210.0e9, nu=0.3, density=density))


def _upper_check(name: str, value: float, limit: float, details: str) -> Tet10VerificationCheck:
    return Tet10VerificationCheck(name, value, limit, "PASS" if np.isfinite(value) and value <= limit else "FAIL", details)


def _unit_coords() -> np.ndarray:
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
        ]
    )


def _affine_field(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gradient = np.array(
        [[1.0e-3, 2.0e-4, -1.0e-4], [3.0e-4, -4.0e-4, 5.0e-5], [2.0e-4, 1.0e-4, 6.0e-4]]
    )
    displacement = np.concatenate([gradient @ point for point in coords])
    strain = np.array(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )
    return displacement, strain
