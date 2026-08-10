"""Benchmark problems and shear-locking studies."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mitc4.constants import DOF_PER_NODE, UY, UZ
from mitc4.element import MITC4Element, Q4FullShearElement
from mitc4.material import ShellMaterial
from mitc4.mesh import MeshFactory
from mitc4.model import ShellModel
from mitc4.visualization import DeformationPlotter


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    values: dict[str, float]


class ScordelisLoBenchmark:
    reference_w = -0.3024

    def __init__(self, nx: int = 24, ny: int = 24):
        self.nx = nx
        self.ny = ny

    def run(self, *, show: bool = False, png: Path | None = None, scale: float = 20.0) -> BenchmarkResult:
        E = 4.32e8
        nu = 0.0
        t = 0.25
        R = 25.0
        L = 50.0
        angle = math.radians(80.0)
        qz = -90.0

        mesh = MeshFactory.scordelis_lo(self.nx, self.ny)
        model = ShellModel(mesh.nodes, mesh.quads, ShellMaterial(E=E, nu=nu, t=t))
        area_element = (L / self.nx) * (R * angle / self.ny)
        for conn in mesh.quads:
            for node in conn:
                model.add_nodal_load(int(node), UZ, qz * area_element / 4.0)

        for i, p in enumerate(mesh.nodes):
            if abs(p[0]) < 1.0e-10 or abs(p[0] - L) < 1.0e-10:
                model.add_fixed_dof(i, UY)
                model.add_fixed_dof(i, UZ)

        model.add_fixed_dof(0, 0)
        model.add_fixed_dof(0, 5)
        U = model.solve()

        mid_x = self.nx // 2
        node_a = mid_x * (self.ny + 1) + 0
        node_b = mid_x * (self.ny + 1) + self.ny
        w_a = float(U[node_a * DOF_PER_NODE + UZ])
        w_b = float(U[node_b * DOF_PER_NODE + UZ])
        error = abs((w_a - self.reference_w) / self.reference_w) * 100.0
        symmetry_error = abs(w_a - w_b) / abs(self.reference_w) * 100.0

        if show or png is not None:
            DeformationPlotter(scale=scale).plot(
                mesh.nodes,
                mesh.quads,
                U,
                title=f"Scordelis-Lo roof {self.nx}x{self.ny} - error {error:.2f}%",
                png=png,
                show=show,
            )

        return BenchmarkResult(
            "Scordelis-Lo",
            {
                "w_edge_center": w_a,
                "w_opposite_edge_center": w_b,
                "reference": self.reference_w,
                "error_percent": error,
                "symmetry_error_percent": symmetry_error,
                "num_nodes": float(mesh.nodes.shape[0]),
                "num_elements": float(mesh.quads.shape[0]),
            },
        )


class CantileverPlateBenchmark:
    def __init__(
        self,
        nx: int = 16,
        ny: int = 4,
        *,
        length: float = 1.0,
        width: float = 0.2,
        thickness: float = 0.01,
        force: float = -1000.0,
        E: float = 210.0e9,
        nu: float = 0.3,
        element_type: type[MITC4Element] = MITC4Element,
    ):
        self.nx = nx
        self.ny = ny
        self.length = length
        self.width = width
        self.thickness = thickness
        self.force = force
        self.E = E
        self.nu = nu
        self.element_type = element_type

    def run(self, *, show: bool = False, png: Path | None = None, scale: float | None = None) -> BenchmarkResult:
        mesh = MeshFactory.rectangular_plate(self.nx, self.ny, self.length, self.width)
        material = ShellMaterial(E=self.E, nu=self.nu, t=self.thickness)
        model = ShellModel(mesh.nodes, mesh.quads, material, element_type=self.element_type)

        tip_nodes = np.where(np.isclose(mesh.nodes[:, 0], self.length))[0]
        for node in tip_nodes:
            model.add_nodal_load(int(node), UZ, self.force / len(tip_nodes))

        root_nodes = np.where(np.isclose(mesh.nodes[:, 0], 0.0))[0]
        for node in root_nodes:
            model.fix_node(int(node))

        U = model.solve()
        tip_w = float(np.mean(U[tip_nodes * DOF_PER_NODE + UZ]))
        D = self.E * self.thickness**3 / (12.0 * (1.0 - self.nu**2))
        reference = self.force * self.length**3 / (3.0 * D * self.width)
        error = abs((tip_w - reference) / reference) * 100.0

        if scale is None:
            scale = 0.15 * self.length / max(abs(tip_w), 1.0e-30)
        if show or png is not None:
            DeformationPlotter(scale=scale).plot(
                mesh.nodes,
                mesh.quads,
                U,
                title=f"Cantilever plate {self.nx}x{self.ny} - {self.element_type.name}",
                png=png,
                show=show,
            )

        return BenchmarkResult(
            "Cantilever plate",
            {
                "tip_w": tip_w,
                "reference": reference,
                "error_percent": error,
                "ratio_to_reference": tip_w / reference,
                "num_nodes": float(mesh.nodes.shape[0]),
                "num_elements": float(mesh.quads.shape[0]),
            },
        )


class ShearLockingStudy:
    """Compare MITC shear interpolation with full Q4 shear interpolation."""

    def __init__(self, nx: int = 8, ny: int = 2, thicknesses: tuple[float, ...] = (1.0e-2, 1.0e-3, 1.0e-4)):
        self.nx = nx
        self.ny = ny
        self.thicknesses = thicknesses

    def run(self) -> BenchmarkResult:
        values: dict[str, float] = {}
        mitc_ratios = []
        full_ratios = []
        for t in self.thicknesses:
            mitc = CantileverPlateBenchmark(self.nx, self.ny, thickness=t, element_type=MITC4Element).run()
            full = CantileverPlateBenchmark(self.nx, self.ny, thickness=t, element_type=Q4FullShearElement).run()
            mitc_ratio = mitc.values["ratio_to_reference"]
            full_ratio = full.values["ratio_to_reference"]
            mitc_ratios.append(mitc_ratio)
            full_ratios.append(full_ratio)
            values[f"mitc_ratio_t_{t:.0e}"] = mitc_ratio
            values[f"full_ratio_t_{t:.0e}"] = full_ratio

        values["mitc_ratio_spread"] = max(mitc_ratios) - min(mitc_ratios)
        values["full_thin_ratio"] = full_ratios[-1]
        values["locking_contrast"] = mitc_ratios[-1] / max(full_ratios[-1], 1.0e-30)
        return BenchmarkResult("Shear locking study", values)

