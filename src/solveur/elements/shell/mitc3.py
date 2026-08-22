"""Linear flat-facet MITC3+ shell with condensed bubble rotations.

The assumed covariant transverse-shear field follows Lee, Lee and Bathe,
Computers & Structures 138 (2014), equations (7), (13), and (15)-(17).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solveur.elements.shell.mitc4.constants import DOF_PER_NODE, RX, RY, RZ, UX, UY, UZ

from solveur.elements.shell.mitc3_condensation import condense_matrix, condensation_transform

RETAINED_DOF_COUNT = 18
EXPANDED_DOF_COUNT = 20
BUBBLE_RX = 18
BUBBLE_RY = 19
TWIST_TYING_DISTANCE = 1.0e-4


@dataclass(frozen=True)
class Mitc3StrainMatrices:
    """Expanded local strain operators at one integration point."""

    membrane: np.ndarray
    bending: np.ndarray
    shear: np.ndarray
    drilling: np.ndarray
    det_jacobian: float


def triangle_rule_7() -> tuple[tuple[float, float, float], ...]:
    """Return the degree-five Dunavant rule on the area-1/2 reference triangle."""
    a1 = 0.059715871789770
    b1 = 0.470142064105115
    a2 = 0.797426985353087
    b2 = 0.101286507323456
    return (
        (1.0 / 3.0, 1.0 / 3.0, 0.1125),
        (a1, b1, 0.066197076394253),
        (b1, a1, 0.066197076394253),
        (b1, b1, 0.066197076394253),
        (a2, b2, 0.062969590272414),
        (b2, a2, 0.062969590272414),
        (b2, b2, 0.062969590272414),
    )


class Mitc3ShellElement:
    """Three-node MITC3+ Reissner-Mindlin shell.

    The two cubic-bubble rotations are statically condensed at element level,
    so the public matrix contains only the 18 nodal shell DOFs.
    """

    name = "MITC3"

    def __init__(self, material: object, *, tying_distance: float = TWIST_TYING_DISTANCE):
        if not 0.0 < float(tying_distance) <= 1.0 / 6.0:
            raise ValueError("MITC3+ tying_distance must be in (0, 1/6].")
        self.material = material
        self.tying_distance = float(tying_distance)
        self.gauss_points = triangle_rule_7()

    @staticmethod
    def shape_functions(r: float, s: float) -> tuple[np.ndarray, np.ndarray]:
        """Return linear translations and derivatives with respect to r,s."""
        values = np.array([1.0 - r - s, r, s], dtype=float)
        derivatives = np.array([[-1.0, -1.0], [1.0, 0.0], [0.0, 1.0]], dtype=float)
        return values, derivatives

    @staticmethod
    def rotation_shape_functions(r: float, s: float) -> tuple[np.ndarray, np.ndarray]:
        """Return the three corrected nodal and one cubic-bubble rotation shapes."""
        translations, translation_derivatives = Mitc3ShellElement.shape_functions(r, s)
        bubble = 27.0 * r * s * (1.0 - r - s)
        bubble_derivatives = np.array(
            [27.0 * s * (1.0 - 2.0 * r - s), 27.0 * r * (1.0 - r - 2.0 * s)],
            dtype=float,
        )
        values = np.concatenate((translations - bubble / 3.0, [bubble]))
        derivatives = np.vstack(
            (
                translation_derivatives - bubble_derivatives[None, :] / 3.0,
                bubble_derivatives,
            )
        )
        return values, derivatives

    @staticmethod
    def local_frame(coords_3d: np.ndarray) -> np.ndarray:
        """Return the deterministic right-handed facet frame."""
        coords = np.asarray(coords_3d, dtype=float)
        if coords.shape != (3, 3):
            raise ValueError("MITC3 coordinates must have shape (3, 3).")
        edge_1 = coords[1] - coords[0]
        edge_2 = coords[2] - coords[0]
        length = float(np.linalg.norm(edge_1))
        normal = np.cross(edge_1, edge_2)
        normal_norm = float(np.linalg.norm(normal))
        if length <= 1.0e-14 or normal_norm <= 1.0e-14:
            raise ValueError("Degenerate MITC3 triangle.")
        e1 = edge_1 / length
        e3 = normal / normal_norm
        e2 = np.cross(e3, e1)
        e2 /= np.linalg.norm(e2)
        return np.vstack((e1, e2, e3))

    @staticmethod
    def transform_dofs(local_frame: np.ndarray) -> np.ndarray:
        block = np.zeros((6, 6), dtype=float)
        block[:3, :3] = local_frame
        block[3:, 3:] = local_frame
        return np.kron(np.eye(3), block)

    def project_to_local_midplane(self, coords_3d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        coords = np.asarray(coords_3d, dtype=float)
        frame = self.local_frame(coords)
        local = ((coords - coords.mean(axis=0)) @ frame.T)[:, :2]
        self._jacobian(local)
        return frame, local

    @staticmethod
    def _jacobian(coords_2d: np.ndarray) -> tuple[np.ndarray, float, np.ndarray]:
        points = np.asarray(coords_2d, dtype=float)
        if points.shape != (3, 2):
            raise ValueError("MITC3 local coordinates must have shape (3, 2).")
        _, derivatives = Mitc3ShellElement.shape_functions(1.0 / 3.0, 1.0 / 3.0)
        jacobian = derivatives.T @ points
        determinant = float(np.linalg.det(jacobian))
        if determinant <= 1.0e-14:
            raise ValueError(f"Invalid or inverted MITC3 triangle, det(J)={determinant:.6e}.")
        return jacobian, determinant, np.linalg.inv(jacobian)

    @staticmethod
    def _compatible_covariant_shear(
        coords_2d: np.ndarray,
        r: float,
        s: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return gamma_rt and gamma_st rows for the expanded 20-DOF vector."""
        _, translation_derivatives = Mitc3ShellElement.shape_functions(r, s)
        rotation_shapes, _ = Mitc3ShellElement.rotation_shape_functions(r, s)
        jacobian, _, _ = Mitc3ShellElement._jacobian(coords_2d)
        rows = []
        for natural_direction in range(2):
            row = np.zeros(EXPANDED_DOF_COUNT, dtype=float)
            dx = jacobian[natural_direction, 0]
            dy = jacobian[natural_direction, 1]
            for node in range(3):
                offset = node * DOF_PER_NODE
                row[offset + UZ] = translation_derivatives[node, natural_direction]
                row[offset + RX] = -rotation_shapes[node] * dy
                row[offset + RY] = rotation_shapes[node] * dx
            row[BUBBLE_RX] = -rotation_shapes[3] * dy
            row[BUBBLE_RY] = rotation_shapes[3] * dx
            rows.append(row)
        return rows[0], rows[1]

    def assumed_covariant_shear(self, coords_2d: np.ndarray, r: float, s: float) -> tuple[np.ndarray, np.ndarray]:
        """Return the MITC3+ assumed gamma_rt and gamma_st operators."""
        points = {
            "A": (1.0 / 6.0, 2.0 / 3.0),
            "B": (2.0 / 3.0, 1.0 / 6.0),
            "C": (1.0 / 6.0, 1.0 / 6.0),
            "D": (1.0 / 3.0 + self.tying_distance, 1.0 / 3.0 - 2.0 * self.tying_distance),
            "E": (1.0 / 3.0 - 2.0 * self.tying_distance, 1.0 / 3.0 + self.tying_distance),
            "F": (1.0 / 3.0 + self.tying_distance, 1.0 / 3.0 + self.tying_distance),
        }
        sampled = {key: self._compatible_covariant_shear(coords_2d, *point) for key, point in points.items()}
        ar, ass = sampled["A"]
        br, bs = sampled["B"]
        cr, cs = sampled["C"]
        dr, _ = sampled["D"]
        _, es = sampled["E"]
        fr, fs = sampled["F"]
        constant_r = (2.0 / 3.0) * (br - 0.5 * bs) + (cr + cs) / 3.0
        constant_s = (2.0 / 3.0) * (ass - 0.5 * ar) + (cr + cs) / 3.0
        twist = (fr - dr) - (fs - es)
        gamma_r = constant_r + twist * (3.0 * s - 1.0) / 3.0
        gamma_s = constant_s + twist * (1.0 - 3.0 * r) / 3.0
        return gamma_r, gamma_s

    def strain_matrices_local(self, coords_2d: np.ndarray, r: float, s: float) -> Mitc3StrainMatrices:
        translations, translation_derivatives = self.shape_functions(r, s)
        _, rotation_derivatives = self.rotation_shape_functions(r, s)
        _, determinant, inverse = self._jacobian(coords_2d)
        translation_xy = translation_derivatives @ inverse.T
        rotation_xy = rotation_derivatives @ inverse.T
        membrane = np.zeros((3, EXPANDED_DOF_COUNT), dtype=float)
        bending = np.zeros((3, EXPANDED_DOF_COUNT), dtype=float)
        drilling = np.zeros((1, EXPANDED_DOF_COUNT), dtype=float)
        for node in range(3):
            offset = node * DOF_PER_NODE
            dx, dy = translation_xy[node]
            membrane[0, offset + UX] = dx
            membrane[1, offset + UY] = dy
            membrane[2, offset + UX] = dy
            membrane[2, offset + UY] = dx
            drilling[0, offset + UX] = 0.5 * dy
            drilling[0, offset + UY] = -0.5 * dx
            drilling[0, offset + RZ] = translations[node]
        for rotation_node in range(4):
            dx, dy = rotation_xy[rotation_node]
            if rotation_node < 3:
                rx = rotation_node * DOF_PER_NODE + RX
                ry = rotation_node * DOF_PER_NODE + RY
            else:
                rx, ry = BUBBLE_RX, BUBBLE_RY
            bending[0, ry] = dx
            bending[1, rx] = -dy
            bending[2, ry] = dy
            bending[2, rx] = -dx
        gamma_r, gamma_s = self.assumed_covariant_shear(coords_2d, r, s)
        shear = inverse @ np.vstack((gamma_r, gamma_s))
        return Mitc3StrainMatrices(membrane, bending, shear, drilling, determinant)

    def _expanded_stiffness_components(
        self,
        coords_2d: np.ndarray,
        material: object,
    ) -> dict[str, np.ndarray]:
        components = {
            key: np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT), dtype=float)
            for key in ("membrane", "bending", "shear", "drilling")
        }
        coupling = getattr(material, "coupling_matrix", None)
        if coupling is not None:
            components["coupling"] = np.zeros_like(components["membrane"])
        for r, s, weight in self.gauss_points:
            matrices = self.strain_matrices_local(coords_2d, r, s)
            scale = matrices.det_jacobian * weight
            components["membrane"] += matrices.membrane.T @ material.membrane_matrix @ matrices.membrane * scale
            components["bending"] += matrices.bending.T @ material.bending_matrix @ matrices.bending * scale
            components["shear"] += matrices.shear.T @ material.shear_matrix @ matrices.shear * scale
            if material.drilling_stiffness > 0.0:
                components["drilling"] += (
                    matrices.drilling.T @ matrices.drilling * material.drilling_stiffness * scale
                )
            if coupling is not None:
                components["coupling"] += (
                    matrices.membrane.T @ coupling @ matrices.bending
                    + matrices.bending.T @ coupling.T @ matrices.membrane
                ) * scale
        return {key: 0.5 * (value + value.T) for key, value in components.items()}

    def _condensed_local_data(
        self, coords_2d: np.ndarray, material: object
    ) -> tuple[dict[str, np.ndarray], np.ndarray]:
        expanded = self._expanded_stiffness_components(coords_2d, material)
        total = sum(expanded.values(), start=np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT)))
        transform = condensation_transform(total, RETAINED_DOF_COUNT)
        return {key: condense_matrix(value, transform) for key, value in expanded.items()}, transform

    def stiffness_local_components(self, coords_2d: np.ndarray, material: object | None = None) -> dict[str, np.ndarray]:
        active = self.material if material is None else material
        components, _ = self._condensed_local_data(coords_2d, active)
        return components

    def stiffness_local(self, coords_2d: np.ndarray, material: object | None = None) -> np.ndarray:
        components = self.stiffness_local_components(coords_2d, material)
        result = sum(components.values(), start=np.zeros((RETAINED_DOF_COUNT, RETAINED_DOF_COUNT)))
        return 0.5 * (result + result.T)

    def stiffness(self, coords_3d: np.ndarray) -> np.ndarray:
        frame, coords_2d = self.project_to_local_midplane(coords_3d)
        local = self.stiffness_local(coords_2d, self._material_for_frame(frame))
        transform = self.transform_dofs(frame)
        result = transform.T @ local @ transform
        return 0.5 * (result + result.T)

    def stiffness_components(self, coords_3d: np.ndarray) -> dict[str, np.ndarray]:
        frame, coords_2d = self.project_to_local_midplane(coords_3d)
        transform = self.transform_dofs(frame)
        components = self.stiffness_local_components(coords_2d, self._material_for_frame(frame))
        return {key: transform.T @ value @ transform for key, value in components.items()}

    def _expanded_mass_local(self, coords_2d: np.ndarray, material: object) -> np.ndarray:
        if material.density <= 0.0:
            raise ValueError("MITC3 dynamic analysis requires a positive material density.")
        result = np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT), dtype=float)
        surface_density = float(getattr(material, "surface_density", material.density * material.t))
        rotary_density = float(getattr(material, "rotary_density", material.density * material.t**3 / 12.0))
        _, determinant, _ = self._jacobian(coords_2d)
        for r, s, weight in self.gauss_points:
            translations, _ = self.shape_functions(r, s)
            rotations, _ = self.rotation_shape_functions(r, s)
            scale = determinant * weight
            translation_mass = np.outer(translations, translations) * surface_density * scale
            for component in (UX, UY, UZ):
                indices = np.arange(component, RETAINED_DOF_COUNT, DOF_PER_NODE)
                result[np.ix_(indices, indices)] += translation_mass
            rotation_indices = (
                [RX, 6 + RX, 12 + RX, BUBBLE_RX],
                [RY, 6 + RY, 12 + RY, BUBBLE_RY],
            )
            rotation_mass = np.outer(rotations, rotations) * rotary_density * scale
            for indices in rotation_indices:
                result[np.ix_(indices, indices)] += rotation_mass
        return 0.5 * (result + result.T)

    def mass_local(self, coords_2d: np.ndarray, material: object | None = None) -> np.ndarray:
        active = self.material if material is None else material
        _, transform = self._condensed_local_data(coords_2d, active)
        return condense_matrix(self._expanded_mass_local(coords_2d, active), transform)

    def mass(self, coords_3d: np.ndarray) -> np.ndarray:
        frame, coords_2d = self.project_to_local_midplane(coords_3d)
        local = self.mass_local(coords_2d, self._material_for_frame(frame))
        transform = self.transform_dofs(frame)
        result = transform.T @ local @ transform
        return 0.5 * (result + result.T)

    def generalized_strains(
        self,
        coords_3d: np.ndarray,
        global_displacement: np.ndarray,
        r: float = 1.0 / 3.0,
        s: float = 1.0 / 3.0,
    ) -> dict[str, np.ndarray]:
        """Recover condensed membrane, curvature, shear and drilling strains."""
        frame, coords_2d = self.project_to_local_midplane(coords_3d)
        material = self._material_for_frame(frame)
        expanded = self._expanded_stiffness_components(coords_2d, material)
        total = sum(expanded.values(), start=np.zeros((EXPANDED_DOF_COUNT, EXPANDED_DOF_COUNT)))
        recovery = condensation_transform(total, RETAINED_DOF_COUNT)
        local_retained = self.transform_dofs(frame) @ np.asarray(global_displacement)
        complete = recovery @ local_retained
        matrices = self.strain_matrices_local(coords_2d, r, s)
        return {
            "membrane": matrices.membrane @ complete,
            "curvature": matrices.bending @ complete,
            "shear": matrices.shear @ complete,
            "drilling": matrices.drilling @ complete,
        }

    def _material_for_frame(self, local_frame: np.ndarray) -> object:
        orient = getattr(self.material, "oriented_for_frame", None)
        return orient(local_frame) if callable(orient) else self.material
