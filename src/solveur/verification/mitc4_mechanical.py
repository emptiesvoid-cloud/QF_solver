"""Mechanical verification suite for the MITC4 implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from solveur.elements.shell.mitc4.constants import DOF_PER_NODE, RX, RY, UZ
from solveur.elements.shell.mitc4.element import MITC4Element
from solveur.elements.shell.mitc4.geometry import block_rotation_transform, node_dofs, polygon_area_xy, rotation_matrix_xyz
from solveur.elements.shell.mitc4.material import ShellMaterial
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.elements.shell.mitc4.model import ShellModel
from solveur.verification.mitc4_benchmarks import ScordelisLoBenchmark, ShearLockingStudy


@dataclass(frozen=True)
class VerificationResult:
    name: str
    value: float
    limit: float
    passed: bool
    details: str


class MechanicalVerifier:
    """Run element, patch, benchmark and shear-locking checks."""

    def __init__(self):
        self.element_material = ShellMaterial(E=210.0e9, nu=0.3, t=0.017)

    def run(self, *, include_benchmark: bool = True, png: Path | None = None) -> list[VerificationResult]:
        results = []
        results.extend(self.element_mechanics())
        results.append(self.membrane_patch())
        results.append(self.transverse_shear_patch())
        results.append(self.constant_bending_energy("x"))
        results.append(self.constant_bending_energy("y"))
        results.append(self.constant_bending_energy("xy"))
        results.append(self.constant_shear_energy("x"))
        results.append(self.constant_shear_energy("y"))
        results.append(self.shear_locking_comparison())
        if include_benchmark:
            results.append(self.scordelis_benchmark(png=png))
        return results

    def element_mechanics(self) -> list[VerificationResult]:
        element = MITC4Element(self.element_material)
        coords = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.7, 0.08, 0.0],
                [1.95, 1.2, 0.0],
                [-0.18, 0.95, 0.0],
            ],
            dtype=float,
        )
        K = element.stiffness(coords)
        normK = max(np.linalg.norm(K, ord=np.inf), 1.0)
        results: list[VerificationResult] = []

        symmetry = np.linalg.norm(K - K.T, ord=np.inf) / normK
        results.append(
            VerificationResult("element symmetry", symmetry, 1.0e-12, symmetry < 1.0e-12, "Conservative elasticity requires symmetric K.")
        )

        rigid_ratios = []
        for mode in self.rigid_body_modes(coords).values():
            rigid_ratios.append(np.linalg.norm(K @ mode, ord=np.inf) / (normK * max(np.linalg.norm(mode, ord=np.inf), 1.0)))
        rigid = max(rigid_ratios)
        results.append(
            VerificationResult("six rigid body modes", rigid, 1.0e-10, rigid < 1.0e-10, "Tx, Ty, Tz, Rx, Ry, Rz give zero internal force.")
        )

        evals = np.linalg.eigvalsh(K)
        first_elastic = max(float(evals[6]), 1.0e-30)
        rigid_gap = float(np.max(np.abs(evals[:6])) / first_elastic)
        results.append(
            VerificationResult(
                "rank and hourglass check",
                rigid_gap,
                1.0e-8,
                rigid_gap < 1.0e-8 and first_elastic > 0.0,
                f"Six rigid modes separated from first elastic mode lambda7={first_elastic:.6e}.",
            )
        )

        Q = rotation_matrix_xyz(0.37, -0.21, 0.58)
        shifted_rotated = coords @ Q.T + np.array([4.0, -2.0, 1.5])
        K_rot = element.stiffness(shifted_rotated)
        P = block_rotation_transform(Q, 4)
        objective = np.linalg.norm(K - P.T @ K_rot @ P, ord=np.inf) / normK
        results.append(
            VerificationResult("frame objectivity", objective, 1.0e-10, objective < 1.0e-10, "Rigid coordinate rotation keeps element energy unchanged.")
        )
        return results

    def membrane_patch(self) -> VerificationResult:
        material = ShellMaterial(E=73.0e9, nu=0.29, t=0.012)
        mesh = MeshFactory.distorted_patch_2x2()
        model = ShellModel(mesh.nodes, mesh.quads, material)
        K = model.assemble_stiffness()

        U = np.zeros(model.ndof, dtype=float)
        exx = 1.1e-4
        eyy = -0.7e-4
        gxy = 0.8e-4
        for i, (x, y, _) in enumerate(mesh.nodes):
            c = i * DOF_PER_NODE
            U[c + 0] = exx * x + 0.5 * gxy * y
            U[c + 1] = 0.5 * gxy * x + eyy * y

        ratio = self._internal_node_residual_ratio(K @ U, mesh.nodes.shape[0], interior_node=4)
        return VerificationResult(
            "distorted membrane patch",
            ratio,
            1.0e-10,
            ratio < 1.0e-10,
            "Affine membrane strain equilibrates the interior node.",
        )

    def transverse_shear_patch(self) -> VerificationResult:
        material = ShellMaterial(E=73.0e9, nu=0.29, t=0.012)
        mesh = MeshFactory.distorted_patch_2x2()
        element = MITC4Element(material)
        expected = np.array([2.5e-4, -1.4e-4], dtype=float)
        max_error = 0.0
        for conn in mesh.quads:
            _, coords_2d = element.project_to_local_midplane(mesh.nodes[conn])
            Ue = np.zeros(24, dtype=float)
            for i, (x, y) in enumerate(coords_2d):
                Ue[i * DOF_PER_NODE + UZ] = expected[0] * x + expected[1] * y
            for xi, eta in element.gauss_pts:
                measured = element.shear_strain_local(coords_2d, Ue, xi, eta)
                max_error = max(max_error, float(np.linalg.norm(measured - expected, ord=np.inf)))

        ratio = max_error / max(np.linalg.norm(expected, ord=np.inf), 1.0e-30)
        return VerificationResult(
            "distorted transverse shear strain",
            ratio,
            1.0e-10,
            ratio < 1.0e-10,
            "MITC tying reproduces constant transverse shear on distorted Q4 facets.",
        )

    def constant_shear_energy(self, direction: str) -> VerificationResult:
        material = ShellMaterial(E=10.0e6, nu=0.25, t=0.08, shear_factor=5.0 / 6.0)
        element = MITC4Element(material)
        coords = np.array([[0.0, 0.0, 0.0], [1.8, 0.0, 0.0], [1.8, 1.2, 0.0], [0.0, 1.2, 0.0]], dtype=float)
        T, coords_2d = element.project_to_local_midplane(coords)
        components = element.stiffness_local_components(coords_2d)
        U = np.zeros(24, dtype=float)
        gamma = 3.0e-3
        if direction == "x":
            for i, (x, _, _) in enumerate(coords):
                U[i * DOF_PER_NODE + UZ] = gamma * x
        elif direction == "y":
            for i, (_, y, _) in enumerate(coords):
                U[i * DOF_PER_NODE + UZ] = gamma * y
        else:
            raise ValueError("direction must be 'x' or 'y'.")

        shear_energy = 0.5 * float(U @ (components["shear"] @ U))
        area = polygon_area_xy(coords[:, :2])
        reference = 0.5 * material.shear_factor * material.G * material.t * area * gamma**2
        ratio_error = abs(shear_energy - reference) / reference
        return VerificationResult(
            f"constant gamma_{direction} shear energy",
            ratio_error,
            1.0e-12,
            ratio_error < 1.0e-12,
            "Matches 0.5*kappa*G*t*A*gamma^2 with kappa=5/6.",
        )

    def constant_bending_energy(self, mode: str) -> VerificationResult:
        material = ShellMaterial(E=10.0e6, nu=0.25, t=0.08)
        element = MITC4Element(material)
        coords = np.array([[0.0, 0.0, 0.0], [1.8, 0.0, 0.0], [1.8, 1.2, 0.0], [0.0, 1.2, 0.0]], dtype=float)
        _, coords_2d = element.project_to_local_midplane(coords)
        components = element.stiffness_local_components(coords_2d)
        U = np.zeros(24, dtype=float)
        kappa = 4.0e-3
        target = np.zeros(3, dtype=float)
        for i, (x, y) in enumerate(coords_2d):
            c = i * DOF_PER_NODE
            if mode == "x":
                U[c + RY] = kappa * x
                target[0] = kappa
            elif mode == "y":
                U[c + RX] = -kappa * y
                target[1] = kappa
            elif mode == "xy":
                U[c + RY] = kappa * y
                target[2] = kappa
            else:
                raise ValueError("mode must be 'x', 'y' or 'xy'.")

        bending_energy = 0.5 * float(U @ (components["bending"] @ U))
        area = polygon_area_xy(coords_2d)
        reference = 0.5 * area * float(target @ (material.bending_matrix @ target))
        ratio_error = abs(bending_energy - reference) / reference
        return VerificationResult(
            f"constant kappa_{mode} bending energy",
            ratio_error,
            1.0e-12,
            ratio_error < 1.0e-12,
            "Matches 0.5*A*kappa^T*Db*kappa for a constant curvature field.",
        )

    def shear_locking_comparison(self) -> VerificationResult:
        study = ShearLockingStudy(nx=8, ny=2).run()
        mitc_spread = abs(study.values["mitc_ratio_spread"])
        full_thin = abs(study.values["full_thin_ratio"])
        contrast = study.values["locking_contrast"]
        passed = mitc_spread < 3.0e-2 and full_thin < 0.2 and contrast > 5.0
        metric = max(mitc_spread / 3.0e-2, full_thin / 0.2, 5.0 / max(contrast, 1.0e-30))
        return VerificationResult(
            "thin-plate shear locking study",
            metric,
            1.0,
            passed,
            (
                f"MITC normalized deflection spread={mitc_spread:.3e}; "
                f"full Q4 thin ratio={full_thin:.3e}; contrast={contrast:.2f}."
            ),
        )

    def scordelis_benchmark(self, *, png: Path | None) -> VerificationResult:
        r8 = ScordelisLoBenchmark(8, 8).run()
        r16 = ScordelisLoBenchmark(16, 16).run()
        r24 = ScordelisLoBenchmark(24, 24).run(png=png)
        err24 = r24.values["error_percent"]
        passed = err24 < 1.5 and err24 <= r16.values["error_percent"] + 0.25 and r16.values["error_percent"] <= r8.values["error_percent"] + 0.25
        return VerificationResult(
            "Scordelis-Lo benchmark 24x24",
            err24,
            1.5,
            passed,
            (
                f"w={r24.values['w_edge_center']:.6e}, ref={r24.values['reference']:.6e}; "
                f"errors 8x8={r8.values['error_percent']:.3f}%, 16x16={r16.values['error_percent']:.3f}%."
            ),
        )

    @staticmethod
    def rigid_body_modes(coords: np.ndarray) -> dict[str, np.ndarray]:
        modes: dict[str, np.ndarray] = {}
        axes = np.eye(3)
        for k, name in enumerate(("Tx", "Ty", "Tz")):
            mode = np.zeros(24, dtype=float)
            for i in range(4):
                mode[i * DOF_PER_NODE + k] = 1.0
            modes[name] = mode

        for k, name in enumerate(("Rx", "Ry", "Rz")):
            omega = axes[k]
            mode = np.zeros(24, dtype=float)
            for i, x in enumerate(coords):
                u = np.cross(omega, x)
                c = i * DOF_PER_NODE
                mode[c : c + 3] = u
                mode[c + 3 : c + 6] = omega
            modes[name] = mode
        return modes

    @staticmethod
    def _internal_node_residual_ratio(internal: np.ndarray, node_count: int, *, interior_node: int) -> float:
        center_residual = np.linalg.norm(internal[node_dofs(interior_node)], ord=np.inf)
        boundary = np.delete(np.arange(node_count), interior_node)
        boundary_dofs = np.concatenate([node_dofs(int(n)) for n in boundary])
        boundary_scale = max(np.linalg.norm(internal[boundary_dofs], ord=np.inf), 1.0)
        return float(center_residual / boundary_scale)


def print_results_table(results: Sequence[VerificationResult]) -> None:
    print("\nMechanical verification")
    print("-" * 112)
    print(f"{'test':38s} {'value':>14s} {'limit':>14s} {'status':>8s}  details")
    print("-" * 112)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.name:38s} {result.value:14.6e} {result.limit:14.6e} {status:>8s}  {result.details}")
    print("-" * 112)
    print("GLOBAL STATUS: PASS" if all(r.passed for r in results) else "GLOBAL STATUS: FAIL")
