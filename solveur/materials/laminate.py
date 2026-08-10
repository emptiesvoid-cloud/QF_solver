"""Classical laminate theory built from orthotropic plane-stress plies."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cached_property
from math import atan2, degrees, isfinite

import numpy as np

from solveur.materials.composite import OrthotropicLamina
from solveur.materials.failure import PlyStrainAllowables, PlyStrengths


@dataclass(frozen=True)
class LaminaPly:
    """One constant-thickness ply in a classical laminate stack."""

    material: OrthotropicLamina
    thickness: float
    angle_deg: float
    name: str = ""
    strengths: PlyStrengths | None = None
    strain_allowables: PlyStrainAllowables | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.material, OrthotropicLamina):
            raise TypeError("material must be an OrthotropicLamina.")
        if not isfinite(self.thickness) or self.thickness <= 0.0:
            raise ValueError("Ply thickness must be positive and finite.")
        if not isfinite(self.angle_deg):
            raise ValueError("Ply angle must be finite.")
        if self.strengths is not None and not isinstance(self.strengths, PlyStrengths):
            raise TypeError("strengths must be PlyStrengths when provided.")
        if self.strain_allowables is not None and not isinstance(
            self.strain_allowables, PlyStrainAllowables
        ):
            raise TypeError("strain_allowables must be PlyStrainAllowables when provided.")

    @cached_property
    def transformed_stiffness(self) -> np.ndarray:
        return self.material.transformed_stiffness(self.angle_deg)


@dataclass(frozen=True)
class PlyPointResult:
    """Strain and stress at one through-thickness position of one ply."""

    ply_index: int
    ply_name: str
    location: str
    z: float
    strain_element: np.ndarray
    stress_element: np.ndarray
    strain_material: np.ndarray
    stress_material: np.ndarray


@dataclass(frozen=True)
class ClassicalLaminate:
    """Linear classical laminate theory with a geometric mid-plane origin."""

    plies: tuple[LaminaPly, ...]

    def __post_init__(self) -> None:
        plies = tuple(self.plies)
        if not plies:
            raise ValueError("A laminate must contain at least one ply.")
        if not all(isinstance(ply, LaminaPly) for ply in plies):
            raise TypeError("plies must contain only LaminaPly objects.")
        object.__setattr__(self, "plies", plies)

    @property
    def thickness(self) -> float:
        return float(sum(ply.thickness for ply in self.plies))

    @property
    def interfaces(self) -> np.ndarray:
        """Return bottom-to-top interface coordinates about the mid-plane."""
        values = [-0.5 * self.thickness]
        for ply in self.plies:
            values.append(values[-1] + ply.thickness)
        result = np.asarray(values, dtype=float)
        result[-1] = 0.5 * self.thickness
        return result

    @cached_property
    def extensional_matrix(self) -> np.ndarray:
        return self._integrated_matrix(power=1, factor=1.0)

    @cached_property
    def coupling_matrix(self) -> np.ndarray:
        return self._integrated_matrix(power=2, factor=0.5)

    @cached_property
    def bending_matrix(self) -> np.ndarray:
        return self._integrated_matrix(power=3, factor=1.0 / 3.0)

    @cached_property
    def stiffness_matrix(self) -> np.ndarray:
        """Return the symmetric 6-by-6 ``ABD`` generalized stiffness."""
        a = self.extensional_matrix
        b = self.coupling_matrix
        d = self.bending_matrix
        return np.block([[a, b], [b, d]])

    def resultants(self, midplane_strain: np.ndarray, curvature: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return membrane forces ``N`` and moments ``M`` per unit length."""
        generalized = np.concatenate((_vector3(midplane_strain, "midplane_strain"), _vector3(curvature, "curvature")))
        result = self.stiffness_matrix @ generalized
        return result[:3], result[3:]

    def generalized_strains(self, membrane_force: np.ndarray, moment: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Solve ``ABD [epsilon0, kappa] = [N, M]``."""
        loads = np.concatenate((_vector3(membrane_force, "membrane_force"), _vector3(moment, "moment")))
        try:
            values = np.linalg.solve(self.stiffness_matrix, loads)
        except np.linalg.LinAlgError as exc:
            raise ValueError("Laminate ABD matrix is singular.") from exc
        return values[:3], values[3:]

    def ply_results(self, midplane_strain: np.ndarray, curvature: np.ndarray) -> tuple[PlyPointResult, ...]:
        """Evaluate lower, middle and upper values in every ply."""
        epsilon0 = _vector3(midplane_strain, "midplane_strain")
        kappa = _vector3(curvature, "curvature")
        interfaces = self.interfaces
        results: list[PlyPointResult] = []
        for index, ply in enumerate(self.plies):
            lower = float(interfaces[index])
            upper = float(interfaces[index + 1])
            for location, z in (("lower", lower), ("middle", 0.5 * (lower + upper)), ("upper", upper)):
                strain_element = epsilon0 + z * kappa
                strain_material = ply.material.strain_in_material_axes(strain_element, ply.angle_deg)
                results.append(
                    PlyPointResult(
                        ply_index=index,
                        ply_name=ply.name,
                        location=location,
                        z=z,
                        strain_element=strain_element,
                        stress_element=ply.transformed_stiffness @ strain_element,
                        strain_material=strain_material,
                        stress_material=ply.material.reduced_stiffness @ strain_material,
                    )
                )
        return tuple(results)

    def is_symmetric(self, tolerance: float = 1.0e-10) -> bool:
        """Return whether membrane-bending coupling is negligible."""
        scale = max(float(np.linalg.norm(self.extensional_matrix) * self.thickness), 1.0)
        return float(np.linalg.norm(self.coupling_matrix)) <= tolerance * scale

    def is_balanced(self, tolerance: float = 1.0e-10) -> bool:
        """Return whether extensional normal-shear couplings are negligible."""
        a = self.extensional_matrix
        scale = max(float(np.linalg.norm(a)), 1.0)
        return float(np.linalg.norm(a[:2, 2])) <= tolerance * scale

    def _integrated_matrix(self, *, power: int, factor: float) -> np.ndarray:
        interfaces = self.interfaces
        matrix = np.zeros((3, 3), dtype=float)
        for index, ply in enumerate(self.plies):
            lower = interfaces[index]
            upper = interfaces[index + 1]
            matrix += factor * ply.transformed_stiffness * (upper**power - lower**power)
        return 0.5 * (matrix + matrix.T)


def _vector3(value: np.ndarray, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain three finite components.")
    return result


@dataclass(frozen=True)
class LaminateShellMaterial:
    """Experimental Reissner-Mindlin shell material derived from a laminate."""

    laminate: ClassicalLaminate
    shear_factor: float = 5.0 / 6.0
    drilling_scale: float = 1.0e-4
    reference_direction: np.ndarray | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.laminate, ClassicalLaminate):
            raise TypeError("laminate must be a ClassicalLaminate.")
        if not isfinite(self.shear_factor) or self.shear_factor <= 0.0:
            raise ValueError("shear_factor must be positive and finite.")
        if not isfinite(self.drilling_scale) or self.drilling_scale < 0.0:
            raise ValueError("drilling_scale must be non-negative and finite.")
        if self.reference_direction is not None:
            direction = np.asarray(self.reference_direction, dtype=float)
            if direction.shape != (3,) or not np.all(np.isfinite(direction)):
                raise ValueError("reference_direction must contain three finite components.")
            norm = float(np.linalg.norm(direction))
            if norm <= 1.0e-14:
                raise ValueError("reference_direction must have a non-zero norm.")
            object.__setattr__(self, "reference_direction", direction / norm)
        for index, ply in enumerate(self.laminate.plies):
            if ply.material.G13 is None or ply.material.G23 is None:
                raise ValueError(f"Ply {index} requires positive G13 and G23 for MITC4 transverse shear.")

    def orientation_angle_deg(self, local_frame: np.ndarray) -> float:
        """Return the projected reference-axis angle in the facet plane."""
        if self.reference_direction is None:
            return 0.0
        frame = np.asarray(local_frame, dtype=float)
        if frame.shape != (3, 3) or not np.all(np.isfinite(frame)):
            raise ValueError("local_frame must be a finite 3x3 matrix.")
        e1, e2, normal = frame
        projected = self.reference_direction - np.dot(self.reference_direction, normal) * normal
        norm = float(np.linalg.norm(projected))
        if norm <= 1.0e-10:
            raise ValueError(
                "Laminate reference_direction is parallel to the shell normal; "
                "the in-plane material orientation is undefined."
            )
        projected /= norm
        return float(degrees(atan2(np.dot(projected, e2), np.dot(projected, e1))))

    def oriented_for_frame(self, local_frame: np.ndarray) -> LaminateShellMaterial:
        """Return an equivalent facet material expressed in local element axes."""
        if self.reference_direction is None:
            return self
        offset = self.orientation_angle_deg(local_frame)
        plies = tuple(replace(ply, angle_deg=ply.angle_deg + offset) for ply in self.laminate.plies)
        return LaminateShellMaterial(
            ClassicalLaminate(plies),
            shear_factor=self.shear_factor,
            drilling_scale=self.drilling_scale,
        )

    @property
    def t(self) -> float:
        return self.laminate.thickness

    @property
    def density(self) -> float:
        return self.surface_density / self.t

    @cached_property
    def surface_density(self) -> float:
        return float(sum(ply.material.density * ply.thickness for ply in self.laminate.plies))

    @cached_property
    def rotary_density(self) -> float:
        interfaces = self.laminate.interfaces
        return float(
            sum(
                ply.material.density * (interfaces[index + 1] ** 3 - interfaces[index] ** 3) / 3.0
                for index, ply in enumerate(self.laminate.plies)
            )
        )

    @cached_property
    def membrane_matrix(self) -> np.ndarray:
        return self.laminate.extensional_matrix

    @cached_property
    def coupling_matrix(self) -> np.ndarray:
        return self.laminate.coupling_matrix

    @cached_property
    def bending_matrix(self) -> np.ndarray:
        return self.laminate.bending_matrix

    @cached_property
    def shear_matrix(self) -> np.ndarray:
        matrix = np.zeros((2, 2), dtype=float)
        for ply in self.laminate.plies:
            matrix += ply.material.transformed_transverse_shear(ply.angle_deg) * ply.thickness
        return self.shear_factor * 0.5 * (matrix + matrix.T)

    @cached_property
    def drilling_stiffness(self) -> float:
        reference = sum(
            np.sqrt(ply.material.E1 * ply.material.E2) * ply.thickness for ply in self.laminate.plies
        )
        return float(self.drilling_scale * reference)
