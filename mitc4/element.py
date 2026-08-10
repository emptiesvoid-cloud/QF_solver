"""MITC4 and comparative Reissner-Mindlin Q4 shell elements."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from mitc4.constants import DOF_PER_NODE, RX, RY, RZ, UX, UY, UZ
from mitc4.material import ShellMaterial

ShearScheme = Literal["mitc", "full"]


@dataclass(frozen=True)
class StrainMatrices:
    Bm: np.ndarray
    Bb: np.ndarray
    Bs: np.ndarray
    Bd: np.ndarray
    detJ: float


class MITC4Element:
    """Four-node flat-facet shell using MITC transverse shear interpolation."""

    name = "MITC4"

    def __init__(self, material: ShellMaterial, shear_scheme: ShearScheme = "mitc"):
        self.material = material
        self.shear_scheme = shear_scheme
        g = 1.0 / math.sqrt(3.0)
        self.gauss_pts = [(-g, -g), (g, -g), (g, g), (-g, g)]
        self.tying_pts = {
            "A": (0.0, -1.0),
            "C": (0.0, 1.0),
            "B": (1.0, 0.0),
            "D": (-1.0, 0.0),
        }

    @staticmethod
    def shape_functions(xi: float, eta: float) -> tuple[np.ndarray, np.ndarray]:
        N = 0.25 * np.array(
            [
                (1.0 - xi) * (1.0 - eta),
                (1.0 + xi) * (1.0 - eta),
                (1.0 + xi) * (1.0 + eta),
                (1.0 - xi) * (1.0 + eta),
            ],
            dtype=float,
        )
        dN = 0.25 * np.array(
            [
                [-(1.0 - eta), -(1.0 - xi)],
                [+(1.0 - eta), -(1.0 + xi)],
                [+(1.0 + eta), +(1.0 + xi)],
                [-(1.0 + eta), +(1.0 - xi)],
            ],
            dtype=float,
        )
        return N, dN

    @staticmethod
    def local_frame(coords_3d: np.ndarray) -> np.ndarray:
        coords_3d = np.asarray(coords_3d, dtype=float)
        if coords_3d.shape != (4, 3):
            raise ValueError("MITC4 coordinates must have shape (4, 3).")

        d1 = coords_3d[2] - coords_3d[0]
        d2 = coords_3d[3] - coords_3d[1]
        e3 = np.cross(d1, d2)
        n3 = np.linalg.norm(e3)
        if n3 < 1.0e-14:
            raise ValueError(f"Degenerate shell element, null diagonal normal:\n{coords_3d}")
        e3 /= n3

        candidates = (
            coords_3d[1] - coords_3d[0],
            coords_3d[2] - coords_3d[3],
            coords_3d[3] - coords_3d[0],
            coords_3d[2] - coords_3d[1],
        )
        e1 = None
        for vec in candidates:
            trial = vec - np.dot(vec, e3) * e3
            n1 = np.linalg.norm(trial)
            if n1 > 1.0e-14:
                e1 = trial / n1
                break
        if e1 is None:
            raise ValueError(f"Degenerate shell element, no in-plane direction:\n{coords_3d}")

        e2 = np.cross(e3, e1)
        e2 /= np.linalg.norm(e2)
        return np.vstack((e1, e2, e3))

    @staticmethod
    def transform_dofs(local_frame: np.ndarray) -> np.ndarray:
        T6 = np.zeros((6, 6), dtype=float)
        T6[:3, :3] = local_frame
        T6[3:, 3:] = local_frame
        return np.kron(np.eye(4), T6)

    def project_to_local_midplane(self, coords_3d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        T = self.local_frame(coords_3d)
        centroid = coords_3d.mean(axis=0)
        coords_2d = ((coords_3d - centroid) @ T.T)[:, :2]
        return T, coords_2d

    def _check_jacobian(self, coords_2d: np.ndarray) -> None:
        dets = []
        for xi, eta in self.gauss_pts:
            _, dN = self.shape_functions(xi, eta)
            J = dN.T @ coords_2d
            dets.append(float(np.linalg.det(J)))
        min_det = min(dets)
        if min_det <= 1.0e-14:
            raise ValueError(
                "Invalid or inverted projected quadrilateral. "
                f"Minimum det(J) at Gauss points = {min_det:.6e}."
            )

    def shear_tying_vectors(self, coords_2d: np.ndarray) -> dict[str, np.ndarray]:
        tying = {}
        for key, (xi, eta) in self.tying_pts.items():
            N, dN = self.shape_functions(xi, eta)
            J = dN.T @ coords_2d
            alpha = 0 if key in ("A", "C") else 1
            B = np.zeros(24, dtype=float)
            for i in range(4):
                c = i * DOF_PER_NODE
                # gamma_alpha = dw/dalpha + ry * dx/dalpha - rx * dy/dalpha.
                B[c + UZ] = dN[i, alpha]
                B[c + RX] = -N[i] * J[alpha, 1]
                B[c + RY] = +N[i] * J[alpha, 0]
            tying[key] = B
        return tying

    def strain_matrices_local(
        self,
        coords_2d: np.ndarray,
        xi: float,
        eta: float,
        tying: dict[str, np.ndarray] | None = None,
    ) -> StrainMatrices:
        N, dN = self.shape_functions(xi, eta)
        J = dN.T @ coords_2d
        detJ = float(np.linalg.det(J))
        if detJ <= 1.0e-14:
            raise ValueError(f"Invalid quadrilateral at ({xi}, {eta}), det(J)={detJ:.6e}.")
        invJ = np.linalg.inv(J)
        dN_dx = dN @ invJ.T

        Bm = np.zeros((3, 24), dtype=float)
        Bb = np.zeros((3, 24), dtype=float)
        Bd = np.zeros((1, 24), dtype=float)

        for i in range(4):
            c = i * DOF_PER_NODE
            Bm[0, c + UX] = dN_dx[i, 0]
            Bm[1, c + UY] = dN_dx[i, 1]
            Bm[2, c + UX] = dN_dx[i, 1]
            Bm[2, c + UY] = dN_dx[i, 0]

            # kx = dry/dx, ky = -drx/dy, kxy = dry/dy - drx/dx.
            Bb[0, c + RY] = dN_dx[i, 0]
            Bb[1, c + RX] = -dN_dx[i, 1]
            Bb[2, c + RY] = dN_dx[i, 1]
            Bb[2, c + RX] = -dN_dx[i, 0]

            # gamma_drill = rz - 0.5 * (dv/dx - du/dy).
            Bd[0, c + UX] = 0.5 * dN_dx[i, 1]
            Bd[0, c + UY] = -0.5 * dN_dx[i, 0]
            Bd[0, c + RZ] = N[i]

        if self.shear_scheme == "mitc":
            if tying is None:
                tying = self.shear_tying_vectors(coords_2d)
            g_xi = 0.5 * ((1.0 - eta) * tying["A"] + (1.0 + eta) * tying["C"])
            g_eta = 0.5 * ((1.0 - xi) * tying["D"] + (1.0 + xi) * tying["B"])
            Bs = np.zeros((2, 24), dtype=float)
            Bs[0, :] = invJ[0, 0] * g_xi + invJ[0, 1] * g_eta
            Bs[1, :] = invJ[1, 0] * g_xi + invJ[1, 1] * g_eta
        elif self.shear_scheme == "full":
            Bs = np.zeros((2, 24), dtype=float)
            for i in range(4):
                c = i * DOF_PER_NODE
                Bs[0, c + UZ] = dN_dx[i, 0]
                Bs[0, c + RY] = N[i]
                Bs[1, c + UZ] = dN_dx[i, 1]
                Bs[1, c + RX] = -N[i]
        else:
            raise ValueError(f"Unknown shear scheme: {self.shear_scheme}")

        return StrainMatrices(Bm=Bm, Bb=Bb, Bs=Bs, Bd=Bd, detJ=detJ)

    def stiffness_local_components(
        self,
        coords_2d: np.ndarray,
        material: object | None = None,
    ) -> dict[str, np.ndarray]:
        self._check_jacobian(coords_2d)
        active_material = self.material if material is None else material
        tying = self.shear_tying_vectors(coords_2d) if self.shear_scheme == "mitc" else None
        Km = np.zeros((24, 24), dtype=float)
        Kb = np.zeros((24, 24), dtype=float)
        Kmb = np.zeros((24, 24), dtype=float)
        Ks = np.zeros((24, 24), dtype=float)
        Kd = np.zeros((24, 24), dtype=float)

        for xi, eta in self.gauss_pts:
            mats = self.strain_matrices_local(coords_2d, xi, eta, tying)
            Km += mats.Bm.T @ active_material.membrane_matrix @ mats.Bm * mats.detJ
            Kb += mats.Bb.T @ active_material.bending_matrix @ mats.Bb * mats.detJ
            coupling = getattr(active_material, "coupling_matrix", None)
            if coupling is not None:
                Kmb += (mats.Bm.T @ coupling @ mats.Bb + mats.Bb.T @ coupling.T @ mats.Bm) * mats.detJ
            Ks += mats.Bs.T @ active_material.shear_matrix @ mats.Bs * mats.detJ
            if active_material.drilling_stiffness > 0.0:
                Kd += mats.Bd.T @ mats.Bd * active_material.drilling_stiffness * mats.detJ

        components = {
            "membrane": Km,
            "bending": Kb,
            "shear": Ks,
            "drilling": Kd,
        }
        if getattr(active_material, "coupling_matrix", None) is not None:
            components["coupling"] = Kmb
        return {key: 0.5 * (value + value.T) for key, value in components.items()}

    def stiffness_local(self, coords_2d: np.ndarray, material: object | None = None) -> np.ndarray:
        components = self.stiffness_local_components(coords_2d, material)
        Ke = sum(components.values(), start=np.zeros((24, 24), dtype=float))
        return 0.5 * (Ke + Ke.T)

    def stiffness(self, coords_3d: np.ndarray) -> np.ndarray:
        coords_3d = np.asarray(coords_3d, dtype=float)
        T, coords_2d = self.project_to_local_midplane(coords_3d)
        material = self._material_for_frame(T)
        Ke_local = self.stiffness_local(coords_2d, material)
        Tdof = self.transform_dofs(T)
        return Tdof.T @ Ke_local @ Tdof

    def mass_local(self, coords_2d: np.ndarray) -> np.ndarray:
        """Return the consistent Reissner-Mindlin mass in element axes.

        Translations carry the surface mass ``rho * t`` and the two physical
        rotations carry ``rho * t**3 / 12``.  The drilling rotation has no
        physical inertia and is deliberately left massless.
        """
        self._check_jacobian(coords_2d)
        if self.material.density <= 0.0:
            raise ValueError("MITC4 dynamic analysis requires a positive material density.")
        mass = np.zeros((24, 24), dtype=float)
        translational_density = float(
            getattr(self.material, "surface_density", self.material.density * self.material.t)
        )
        rotary_density = float(
            getattr(self.material, "rotary_density", self.material.density * self.material.t**3 / 12.0)
        )
        inertias = (translational_density,) * 3 + (rotary_density,) * 2 + (0.0,)
        for xi, eta in self.gauss_pts:
            shape, derivatives = self.shape_functions(xi, eta)
            det_j = float(np.linalg.det(derivatives.T @ coords_2d))
            if det_j <= 1.0e-14:
                raise ValueError(f"Invalid quadrilateral at ({xi}, {eta}), det(J)={det_j:.6e}.")
            nodal_mass = np.outer(shape, shape) * det_j
            for component, inertia in enumerate(inertias):
                if inertia <= 0.0:
                    continue
                indices = np.arange(component, 24, DOF_PER_NODE)
                mass[np.ix_(indices, indices)] += inertia * nodal_mass
        return 0.5 * (mass + mass.T)

    def mass(self, coords_3d: np.ndarray) -> np.ndarray:
        """Return the consistent mass transformed to global axes."""
        coords_3d = np.asarray(coords_3d, dtype=float)
        T, coords_2d = self.project_to_local_midplane(coords_3d)
        Tdof = self.transform_dofs(T)
        mass = Tdof.T @ self.mass_local(coords_2d) @ Tdof
        return 0.5 * (mass + mass.T)

    def stiffness_components(self, coords_3d: np.ndarray) -> dict[str, np.ndarray]:
        T, coords_2d = self.project_to_local_midplane(coords_3d)
        Tdof = self.transform_dofs(T)
        components = self.stiffness_local_components(coords_2d, self._material_for_frame(T))
        return {key: Tdof.T @ value @ Tdof for key, value in components.items()}

    def _material_for_frame(self, local_frame: np.ndarray) -> object:
        orient = getattr(self.material, "oriented_for_frame", None)
        return orient(local_frame) if callable(orient) else self.material

    def shear_strain_local(self, coords_2d: np.ndarray, local_u: np.ndarray, xi: float, eta: float) -> np.ndarray:
        tying = self.shear_tying_vectors(coords_2d) if self.shear_scheme == "mitc" else None
        mats = self.strain_matrices_local(coords_2d, xi, eta, tying)
        return mats.Bs @ local_u


class Q4FullShearElement(MITC4Element):
    """Comparative Q4 element using full transverse shear interpolation.

    This element is intentionally kept for verification studies: it should show
    shear locking on thin Reissner-Mindlin plates, unlike the MITC projection.
    """

    name = "Q4-full-shear"

    def __init__(self, material: ShellMaterial):
        super().__init__(material, shear_scheme="full")
