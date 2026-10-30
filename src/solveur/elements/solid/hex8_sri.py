"""Research-only selective reduced integration variant of HEX8."""

from __future__ import annotations

import numpy as np

from solveur.elements.solid.hex8 import Hex8Element
from solveur.materials.solid import SolidMaterial


_VOLUMETRIC_VECTOR = np.asarray((1.0, 1.0, 1.0, 0.0, 0.0, 0.0), dtype=float)


class Hex8SRIElement:
    """Internal isotropic HEX8 SRI research element.

    The class is intentionally separate from :class:`Hex8Element` and is not
    registered as a public element family.  Deviatoric stiffness uses the
    complete eight-point rule while volumetric stiffness uses the element
    centre.  Consistent mass remains the standard HEX8 mass matrix.
    """

    integration_point_count = Hex8Element.integration_point_count
    integration_points = Hex8Element.integration_points
    volumetric_integration_points = ((0.0, 0.0, 0.0),)
    volumetric_integration_weight = 8.0

    def __init__(self, material: SolidMaterial):
        if type(material) is not SolidMaterial:
            raise TypeError("HEX8-SRI currently supports SolidMaterial only.")
        self.material = material
        self._standard = Hex8Element(material)

    @staticmethod
    def shape_functions(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        return Hex8Element.shape_functions(point)

    @staticmethod
    def shape_derivatives_reference(point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        return Hex8Element.shape_derivatives_reference(point)

    @classmethod
    def jacobian(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> np.ndarray:
        return Hex8Element.jacobian(coords, point)

    @classmethod
    def jacobian_determinant(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> float:
        return Hex8Element.jacobian_determinant(coords, point)

    @classmethod
    def validate_geometry(cls, coords: np.ndarray) -> None:
        coords = Hex8Element._validated_coords(coords)
        if not np.all(np.isfinite(coords)):
            raise ValueError("Invalid HEX8-SRI geometry: coordinates must be finite.")
        tolerance = Hex8Element._jacobian_determinant_tolerance(coords)
        integration_points = (*cls.integration_points, *cls.volumetric_integration_points)
        determinants = np.asarray(
            [cls.jacobian_determinant(coords, point) for point in integration_points]
        )
        if np.any(~np.isfinite(determinants)) or np.any(determinants <= tolerance):
            minimum = float(np.min(determinants))
            raise ValueError(f"Invalid HEX8-SRI Jacobian determinant {minimum:.6e}.")

    @classmethod
    def b_matrix(cls, coords: np.ndarray, point: tuple[float, float, float] | np.ndarray) -> tuple[np.ndarray, float]:
        return Hex8Element.b_matrix(coords, point)

    @staticmethod
    def _constitutive_split(material: SolidMaterial) -> tuple[np.ndarray, np.ndarray]:
        shear_modulus = material.E / (2.0 * (1.0 + material.nu))
        deviatoric = np.zeros((6, 6), dtype=float)
        deviatoric[:3, :3] = 2.0 * shear_modulus * (
            np.eye(3) - np.ones((3, 3)) / 3.0
        )
        deviatoric[3:, 3:] = shear_modulus * np.eye(3)
        volumetric = material.E / (3.0 * (1.0 - 2.0 * material.nu)) * np.outer(
            _VOLUMETRIC_VECTOR, _VOLUMETRIC_VECTOR
        )
        return deviatoric, volumetric

    def deviatoric_stiffness(self, coords: np.ndarray) -> np.ndarray:
        self.validate_geometry(coords)
        deviatoric, _ = self._constitutive_split(self.material)
        stiffness = np.zeros((24, 24), dtype=float)
        for _, weight, b_matrix, determinant in self._standard.integration_data(coords):
            stiffness += weight * determinant * (b_matrix.T @ deviatoric @ b_matrix)
        return 0.5 * (stiffness + stiffness.T)

    def volumetric_stiffness(self, coords: np.ndarray) -> np.ndarray:
        self.validate_geometry(coords)
        _, volumetric = self._constitutive_split(self.material)
        point = self.volumetric_integration_points[0]
        b_matrix, determinant = self.b_matrix(coords, point)
        stiffness = self.volumetric_integration_weight * determinant * (
            b_matrix.T @ volumetric @ b_matrix
        )
        return 0.5 * (stiffness + stiffness.T)

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        return self.deviatoric_stiffness(coords) + self.volumetric_stiffness(coords)

    def mass(self, coords: np.ndarray) -> np.ndarray:
        """Return the standard consistent HEX8 mass matrix."""

        return self._standard.mass(coords)

    def mass_lumped(self, coords: np.ndarray) -> np.ndarray:
        return self._standard.mass_lumped(coords)

    def strain_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        return self._standard.strain_at(coords, local_displacement, point)

    def stress_at(self, coords: np.ndarray, local_displacement: np.ndarray, point) -> np.ndarray:
        return self._standard.stress_at(coords, local_displacement, point)

    def strain(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self._standard.strain(coords, local_displacement)

    def stress(self, coords: np.ndarray, local_displacement: np.ndarray) -> np.ndarray:
        return self._standard.stress(coords, local_displacement)

