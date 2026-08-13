"""Three-dimensional two-node Timoshenko beam element."""

from __future__ import annotations

import numpy as np

from solveur.materials.beam import BeamSectionMaterial


class Beam2Element:
    """Linear 3D Timoshenko beam with six degrees of freedom per node."""

    def __init__(self, material: BeamSectionMaterial) -> None:
        self.material = material

    @staticmethod
    def length(coords: np.ndarray) -> float:
        values = Beam2Element._coordinates(coords)
        return float(np.linalg.norm(values[1] - values[0]))

    def local_frame(self, coords: np.ndarray) -> np.ndarray:
        values = self._coordinates(coords)
        axis = values[1] - values[0]
        length = float(np.linalg.norm(axis))
        if length <= 1.0e-14:
            raise ValueError("Invalid BEAM2 length; nodes must be distinct.")
        e1 = axis / length
        if self.material.reference_vector is None:
            reference = np.array([0.0, 1.0, 0.0])
            if abs(float(np.dot(reference, e1))) > 0.9:
                reference = np.array([0.0, 0.0, 1.0])
        else:
            reference = np.asarray(self.material.reference_vector, dtype=float)
        transverse = reference - float(np.dot(reference, e1)) * e1
        norm = float(np.linalg.norm(transverse))
        if norm <= 1.0e-12:
            raise ValueError("BEAM2 reference_vector must not be parallel to the beam axis.")
        e2 = transverse / norm
        e3 = np.cross(e1, e2)
        return np.vstack((e1, e2, e3))

    def transformation(self, coords: np.ndarray) -> np.ndarray:
        """Return the global-to-local displacement transformation."""
        rotation = self.local_frame(coords)
        transform: np.ndarray = np.zeros((12, 12), dtype=float)
        for offset in (0, 3, 6, 9):
            transform[offset : offset + 3, offset : offset + 3] = rotation
        return transform

    def local_stiffness(self, coords: np.ndarray) -> np.ndarray:
        length = self.length(coords)
        if length <= 1.0e-14:
            raise ValueError("Invalid BEAM2 length; nodes must be distinct.")
        section = self.material
        matrix: np.ndarray = np.zeros((12, 12), dtype=float)
        self._pair(matrix, (0, 6), section.E * section.A / length)
        self._pair(matrix, (3, 9), section.G * section.J / length)

        phi_y = 12.0 * section.E * section.Iz / (section.kappa_y * section.G * section.A * length**2)
        phi_z = 12.0 * section.E * section.Iy / (section.kappa_z * section.G * section.A * length**2)
        self._bending_block(matrix, (1, 5, 7, 11), section.E * section.Iz, length, phi_y, sign=1.0)
        self._bending_block(matrix, (2, 4, 8, 10), section.E * section.Iy, length, phi_z, sign=-1.0)
        return 0.5 * (matrix + matrix.T)

    def stiffness(self, coords: np.ndarray) -> np.ndarray:
        transform = self.transformation(coords)
        return transform.T @ self.local_stiffness(coords) @ transform

    def local_mass(self, coords: np.ndarray) -> np.ndarray:
        """Return the local consistent mass matrix.

        The transverse inertia uses cubic Hermite interpolation of the
        displacement field, while the independent Timoshenko rotations keep
        their cross-section rotary inertia.  Interpolating transverse
        displacement and rotation independently with linear functions gives a
        positive matrix, but is dynamically inconsistent with the bending
        stiffness and severely distorts the first bending and torsional modes.
        """
        if self.material.density <= 0.0:
            raise ValueError("BEAM2 dynamic analysis requires a positive material density.")
        length = self.length(coords)
        if length <= 1.0e-14:
            raise ValueError("Invalid BEAM2 length; nodes must be distinct.")
        matrix: np.ndarray = np.zeros((12, 12), dtype=float)
        linear = np.array([[2.0, 1.0], [1.0, 2.0]], dtype=float)
        self._add_block(matrix, (0, 6), self.material.density * self.material.A * length / 6.0 * linear)
        self._add_block(matrix, (3, 9), self.material.density * self.material.J * length / 6.0 * linear)

        hermite = np.array(
            [
                [156.0, 22.0 * length, 54.0, -13.0 * length],
                [22.0 * length, 4.0 * length**2, 13.0 * length, -3.0 * length**2],
                [54.0, 13.0 * length, 156.0, -22.0 * length],
                [-13.0 * length, -3.0 * length**2, -22.0 * length, 4.0 * length**2],
            ],
            dtype=float,
        )
        bending_mass = self.material.density * self.material.A * length / 420.0 * hermite
        self._add_block(matrix, (1, 5, 7, 11), bending_mass)
        sign = np.diag((1.0, -1.0, 1.0, -1.0))
        self._add_block(matrix, (2, 4, 8, 10), sign @ bending_mass @ sign)

        # Independent Timoshenko rotations carry their physical sectional inertia.
        self._add_block(matrix, (4, 10), self.material.density * self.material.Iy * length / 6.0 * linear)
        self._add_block(matrix, (5, 11), self.material.density * self.material.Iz * length / 6.0 * linear)
        return 0.5 * (matrix + matrix.T)

    def mass(self, coords: np.ndarray) -> np.ndarray:
        transform = self.transformation(coords)
        return transform.T @ self.local_mass(coords) @ transform

    def response(self, coords: np.ndarray, global_displacement: np.ndarray) -> dict[str, object]:
        """Recover local generalized strains and nodal section forces."""
        length = self.length(coords)
        transform = self.transformation(coords)
        local = transform @ np.asarray(global_displacement, dtype=float)
        if local.shape != (12,):
            raise ValueError("BEAM2 local displacement must contain 12 values.")
        slope_y = (local[7] - local[1]) / length
        slope_z = (local[8] - local[2]) / length
        generalized_strain = np.array(
            [
                (local[6] - local[0]) / length,
                slope_y - 0.5 * (local[5] + local[11]),
                slope_z + 0.5 * (local[4] + local[10]),
                (local[9] - local[3]) / length,
                (local[10] - local[4]) / length,
                (local[11] - local[5]) / length,
            ],
            dtype=float,
        )
        local_forces = self.local_stiffness(coords) @ local
        return {
            "local_frame": self.local_frame(coords).tolist(),
            "length": length,
            "local_displacement": local.tolist(),
            "generalized_strain": generalized_strain.tolist(),
            "local_end_forces": {
                "node_1": local_forces[:6].tolist(),
                "node_2": local_forces[6:].tolist(),
                "order": ["N", "Vy", "Vz", "T", "My", "Mz"],
            },
        }

    @staticmethod
    def _pair(matrix: np.ndarray, indices: tuple[int, int], stiffness: float) -> None:
        first, second = indices
        matrix[np.ix_(indices, indices)] += stiffness * np.array([[1.0, -1.0], [-1.0, 1.0]])

    @staticmethod
    def _add_block(matrix: np.ndarray, indices: tuple[int, ...], block: np.ndarray) -> None:
        matrix[np.ix_(indices, indices)] += block

    @staticmethod
    def _bending_block(
        matrix: np.ndarray,
        indices: tuple[int, int, int, int],
        bending_rigidity: float,
        length: float,
        phi: float,
        *,
        sign: float,
    ) -> None:
        factor = bending_rigidity / (length**3 * (1.0 + phi))
        coupling = sign * 6.0 * length
        block = factor * np.array(
            [
                [12.0, coupling, -12.0, coupling],
                [coupling, (4.0 + phi) * length**2, -coupling, (2.0 - phi) * length**2],
                [-12.0, -coupling, 12.0, -coupling],
                [coupling, (2.0 - phi) * length**2, -coupling, (4.0 + phi) * length**2],
            ]
        )
        matrix[np.ix_(indices, indices)] += block

    @staticmethod
    def _coordinates(coords: np.ndarray) -> np.ndarray:
        values = np.asarray(coords, dtype=float)
        if values.shape != (2, 3) or not np.all(np.isfinite(values)):
            raise ValueError("BEAM2 coordinates must have shape (2, 3) with finite values.")
        return values
