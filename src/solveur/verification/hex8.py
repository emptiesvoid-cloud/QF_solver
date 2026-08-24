"""Deterministic element-level verification for the HEX8 formulation."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.hex8 import Hex8Element
from solveur.materials.solid import SolidMaterial


class Hex8MechanicalVerifier:
    """Run the mandatory analytical checks that do not require an external solver."""

    def run(self) -> dict[str, object]:
        checks = [
            self._shape_partition(),
            self._jacobian(),
            self._stiffness_symmetry(),
            self._mass_total_and_symmetry(),
            self._mass_positive(),
            self._affine_patch(),
            self._affine_energy(),
            self._rigid_modes(),
            self._distorted_geometry(),
            self._near_incompressible_materials(),
        ]
        return {
            "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "element": "HEX8",
            "purpose": "mechanical_verification",
            "integration": "2x2x2_gauss",
            "checks": checks,
        }

    def _shape_partition(self) -> dict[str, object]:
        points = [(0.0, 0.0, 0.0), *Hex8Element.integration_points]
        value = max(abs(float(np.sum(Hex8Element.shape_functions(point))) - 1.0) for point in points)
        return _check("shape function partition", value, 1.0e-14)

    def _jacobian(self) -> dict[str, object]:
        values = [Hex8Element.jacobian_determinant(_unit_coords(), point) for point in Hex8Element.integration_points]
        value = max(abs(float(item) - 0.125) for item in values)
        return _check("unit cube Jacobian", value, 1.0e-14)

    def _stiffness_symmetry(self) -> dict[str, object]:
        stiffness = _element().stiffness(_unit_coords())
        value = np.linalg.norm(stiffness - stiffness.T) / max(np.linalg.norm(stiffness), 1.0)
        return _check("stiffness symmetry", float(value), 1.0e-13)

    def _mass_total_and_symmetry(self) -> dict[str, object]:
        mass = _element(density=7800.0).mass(_unit_coords())
        symmetry = np.linalg.norm(mass - mass.T) / max(np.linalg.norm(mass), 1.0)
        total = abs(float(np.sum(mass)) - 3.0 * 7800.0) / (3.0 * 7800.0)
        return _check("consistent mass symmetry and total", max(float(symmetry), float(total)), 1.0e-12)

    def _mass_positive(self) -> dict[str, object]:
        eigenvalues = np.linalg.eigvalsh(_element(density=7800.0).mass(_unit_coords()))
        value = max(0.0, -float(np.min(eigenvalues))) / max(float(np.max(eigenvalues)), 1.0)
        return _check("consistent mass positive definiteness", value, 1.0e-13)

    def _affine_patch(self) -> dict[str, object]:
        gradient = np.asarray([[2.0e-4, 3.0e-5, -2.0e-5], [4.0e-5, -1.0e-4, 5.0e-5], [1.0e-5, 6.0e-5, 0.5e-4]])
        displacement = np.concatenate([gradient @ point for point in _unit_coords()])
        expected = np.asarray([gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]])
        values = [_element().strain_at(_unit_coords(), displacement, point) for point in Hex8Element.integration_points]
        value = max(float(np.linalg.norm(item - expected)) for item in values) / max(float(np.linalg.norm(expected)), 1.0e-30)
        return _check("affine strain patch", value, 1.0e-11)

    def _affine_energy(self) -> dict[str, object]:
        gradient = np.asarray([[2.0e-4, 3.0e-5, -2.0e-5], [4.0e-5, -1.0e-4, 5.0e-5], [1.0e-5, 6.0e-5, 0.5e-4]])
        strain = np.asarray([gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]])
        displacement = np.concatenate([gradient @ point for point in _unit_coords()])
        material = SolidMaterial(E=210.0e9, nu=0.3)
        observed = 0.5 * displacement @ (_element().stiffness(_unit_coords()) @ displacement)
        expected = 0.5 * strain @ material.elasticity_matrix @ strain
        return _check("affine analytical energy", abs(float(observed - expected)) / abs(float(expected)), 1.0e-11)

    def _rigid_modes(self) -> dict[str, object]:
        coords = _unit_coords()
        stiffness = _element().stiffness(coords)
        scale = max(float(np.linalg.norm(stiffness, ord=np.inf)), 1.0)
        modes = []
        for axis in range(3):
            mode = np.zeros(24)
            mode[axis::3] = 1.0
            modes.append(mode)
        for axis in np.eye(3):
            modes.append(np.concatenate([np.cross(axis, point) for point in coords]))
        value = max(float(np.linalg.norm(stiffness @ mode, ord=np.inf)) / scale for mode in modes)
        return _check("rigid body modes", value, 1.0e-10)

    def _distorted_geometry(self) -> dict[str, object]:
        coords = _unit_coords().copy()
        coords[6] += np.asarray([0.15, -0.08, 0.1])
        determinants = [Hex8Element.jacobian_determinant(coords, point) for point in Hex8Element.integration_points]
        value = 0.0 if min(determinants) > 0.0 else 1.0
        return _check("positive Jacobian under bounded distortion", value, 0.0)

    def _near_incompressible_materials(self) -> dict[str, object]:
        values = []
        for poisson in (0.49, 0.499):
            stiffness = Hex8Element(SolidMaterial(E=1.0, nu=poisson)).stiffness(_unit_coords())
            values.append(0.0 if np.all(np.isfinite(stiffness)) else 1.0)
        return _check("near incompressible finite stiffness", max(values), 0.0)


def _unit_coords() -> np.ndarray:
    return np.asarray(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        dtype=float,
    )


def _element(*, density: float = 0.0) -> Hex8Element:
    return Hex8Element(SolidMaterial(E=210.0e9, nu=0.3, density=density))


def _check(name: str, value: float, limit: float) -> dict[str, object]:
    return {"name": name, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}
