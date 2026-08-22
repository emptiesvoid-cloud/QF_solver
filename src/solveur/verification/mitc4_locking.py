"""Reproducible thickness, mesh and distortion study for MITC4 locking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve

from solveur.elements.shell.mitc4.constants import DOF_PER_NODE, UZ
from solveur.elements.shell.mitc4.element import MITC4Element, Q4FullShearElement
from solveur.elements.shell.mitc4.geometry import element_dofs
from solveur.elements.shell.mitc4.material import ShellMaterial
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.elements.shell.mitc4.model import ShellModel


@dataclass(frozen=True)
class LockingCase:
    element: str
    nx: int
    ny: int
    thickness_ratio: float
    distortion: float
    element_count: int
    tip_displacement: float
    reference_displacement: float
    displacement_ratio: float
    relative_error: float
    shear_energy_fraction: float
    drilling_energy_fraction: float
    relative_residual: float
    condition_estimate: float
    final_mesh_increment: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LockingCampaign:
    identifier: str
    cases: tuple[LockingCase, ...]
    checks: tuple[dict[str, object], ...]
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "study_id": self.identifier,
            "status": self.status,
            "checks": list(self.checks),
            "cases": [case.to_dict() for case in self.cases],
        }


class EnhancedShearLockingStudy:
    """Compare MITC4 with a deliberately locking full-shear Q4 control."""

    identifier = "VNV-MITC4-SHEAR-LOCKING-001"

    def __init__(
        self,
        meshes: tuple[tuple[int, int], ...] = ((4, 1), (8, 2), (16, 4), (24, 6), (32, 8)),
        thickness_ratios: tuple[float, ...] = (1.0e-1, 1.0e-2, 1.0e-3, 1.0e-4),
        distortions: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3),
    ) -> None:
        self.meshes = meshes
        self.thickness_ratios = thickness_ratios
        self.distortions = distortions

    def run(self) -> LockingCampaign:
        raw: list[LockingCase] = []
        for element_type in (MITC4Element, Q4FullShearElement):
            for thickness in self.thickness_ratios:
                for distortion in self.distortions:
                    previous: LockingCase | None = None
                    for nx, ny in self.meshes:
                        current = self._run_case(element_type, nx, ny, thickness, distortion)
                        if previous is not None:
                            increment = abs(current.tip_displacement - previous.tip_displacement) / max(
                                abs(current.tip_displacement), 1.0e-30
                            )
                            current = LockingCase(**{**current.to_dict(), "final_mesh_increment": increment})
                        raw.append(current)
                        previous = current
        checks = tuple(self._acceptance_checks(raw))
        status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
        return LockingCampaign(self.identifier, tuple(raw), checks, status)

    @staticmethod
    def _run_case(
        element_type: type[MITC4Element], nx: int, ny: int, thickness: float, distortion: float
    ) -> LockingCase:
        length = 1.0
        width = 0.2
        force = -1000.0
        young = 210.0e9
        poisson = 0.3
        shear_factor = 5.0 / 6.0
        mesh = MeshFactory.rectangular_plate(nx, ny, length, width)
        nodes = _distorted_nodes(mesh.nodes, length, width, nx, ny, distortion)
        material = ShellMaterial(
            E=young,
            nu=poisson,
            t=thickness,
            shear_factor=shear_factor,
            drilling_scale=1.0e-4,
        )
        model = ShellModel(nodes, mesh.quads, material, element_type=element_type)
        tip_nodes = np.where(np.isclose(nodes[:, 0], length))[0]
        root_nodes = np.where(np.isclose(nodes[:, 0], 0.0))[0]
        for node in tip_nodes:
            model.add_nodal_load(int(node), UZ, force / len(tip_nodes))
        for node in root_nodes:
            model.fix_node(int(node))

        stiffness = model.assemble_stiffness()
        fixed = np.array(sorted(model.fixed_dofs), dtype=int)
        free = np.setdiff1d(np.arange(model.ndof, dtype=int), fixed)
        displacement = np.zeros(model.ndof, dtype=float)
        reduced_stiffness = stiffness[free, :][:, free]
        reduced_load = model.loads[free]
        diagonal_scale = 1.0 / np.sqrt(np.maximum(np.abs(reduced_stiffness.diagonal()), 1.0e-30))
        scaling = diags(diagonal_scale, format="csr")
        scaled_stiffness = (scaling @ reduced_stiffness @ scaling).tocsr()
        displacement[free] = diagonal_scale * spsolve(scaled_stiffness, diagonal_scale * reduced_load)
        for _ in range(10):
            correction_load = -_accurate_residual(reduced_stiffness, displacement[free], reduced_load)
            if np.linalg.norm(correction_load) <= 1.0e-10 * max(np.linalg.norm(reduced_load), 1.0):
                break
            displacement[free] += diagonal_scale * spsolve(scaled_stiffness, diagonal_scale * correction_load)
        if not np.all(np.isfinite(displacement)):
            raise RuntimeError("Shear-locking study produced non-finite displacements.")

        energies = {name: 0.0 for name in ("membrane", "coupling", "bending", "shear", "drilling")}
        element = element_type(material)
        for connectivity in mesh.quads:
            indices = element_dofs(connectivity)
            local_u = displacement[indices]
            for name, component in element.stiffness_components(nodes[connectivity]).items():
                energies[name] += float(0.5 * local_u @ (component @ local_u))
        energies = {name: max(value, 0.0) for name, value in energies.items()}
        total_energy = max(sum(energies.values()), 1.0e-30)
        residual = _accurate_residual(stiffness, displacement, model.loads)
        stiffness_norm = float(np.asarray(abs(stiffness[free, :][:, free]).sum(axis=1)).max())
        backward_reference = max(
            stiffness_norm * float(np.max(np.abs(displacement[free])))
            + float(np.max(np.abs(model.loads[free]))),
            1.0,
        )
        diagonal = np.abs(stiffness[free, :][:, free].diagonal())
        positive_diagonal = diagonal[diagonal > 1.0e-30]
        condition_estimate = float(positive_diagonal.max() / positive_diagonal.min())
        tip = float(np.mean(displacement[tip_nodes * DOF_PER_NODE + UZ]))
        reference = _timoshenko_tip(force, length, width, thickness, young, poisson, shear_factor)
        ratio = tip / reference
        return LockingCase(
            element=element.name,
            nx=nx,
            ny=ny,
            thickness_ratio=thickness / length,
            distortion=distortion,
            element_count=int(mesh.quads.shape[0]),
            tip_displacement=tip,
            reference_displacement=reference,
            displacement_ratio=ratio,
            relative_error=abs(ratio - 1.0),
            shear_energy_fraction=energies["shear"] / total_energy,
            drilling_energy_fraction=energies["drilling"] / total_energy,
            relative_residual=float(np.max(np.abs(residual[free])) / backward_reference),
            condition_estimate=condition_estimate,
        )

    def _acceptance_checks(self, cases: list[LockingCase]) -> list[dict[str, object]]:
        fine = self.meshes[-1]

        def case(element: str, thickness: float, distortion: float) -> LockingCase:
            return next(
                item
                for item in cases
                if item.element == element
                and (item.nx, item.ny) == fine
                and np.isclose(item.thickness_ratio, thickness)
                and np.isclose(item.distortion, distortion)
            )

        mitc_regular = [case("MITC4", thickness, 0.0) for thickness in self.thickness_ratios]
        mitc_distorted = [case("MITC4", thickness, 0.3) for thickness in self.thickness_ratios]
        thin = mitc_regular[-1]
        previous_thin = mitc_regular[-2]
        full_thin = case("Q4-full-shear", self.thickness_ratios[-1], 0.0)
        criteria = [
            ("fine_reference_error", max(item.relative_error for item in mitc_regular), 0.05, "less_equal"),
            ("thin_limit_ratio", thin.displacement_ratio, 0.90, "greater_equal"),
            (
                "thin_limit_spread",
                abs(thin.displacement_ratio - previous_thin.displacement_ratio),
                0.02,
                "less_equal",
            ),
            ("distorted_reference_error", max(item.relative_error for item in mitc_distorted), 0.10, "less_equal"),
            (
                "thin_shear_energy_fraction",
                max(item.shear_energy_fraction for item in mitc_regular[-2:]),
                0.01,
                "less_equal",
            ),
            (
                "drilling_energy_fraction",
                max(item.drilling_energy_fraction for item in mitc_regular),
                0.01,
                "less_equal",
            ),
            ("full_q4_thin_ratio", full_thin.displacement_ratio, 0.20, "less_equal"),
            ("locking_contrast", thin.displacement_ratio / max(full_thin.displacement_ratio, 1.0e-30), 5.0, "greater_equal"),
            ("relative_residual", max(item.relative_residual for item in mitc_regular), 1.0e-8, "less_equal"),
        ]
        return [
            {
                "name": name,
                "value": float(value),
                "limit": float(limit),
                "operator": operator,
                "status": "PASS"
                if (value <= limit if operator == "less_equal" else value >= limit)
                else "FAIL",
            }
            for name, value, limit, operator in criteria
        ]


def _timoshenko_tip(
    force: float,
    length: float,
    width: float,
    thickness: float,
    young: float,
    poisson: float,
    shear_factor: float,
) -> float:
    area = width * thickness
    inertia = width * thickness**3 / 12.0
    shear = young / (2.0 * (1.0 + poisson))
    return force * length**3 / (3.0 * young * inertia) + force * length / (shear_factor * shear * area)


def _distorted_nodes(
    nodes: np.ndarray, length: float, width: float, nx: int, ny: int, distortion: float
) -> np.ndarray:
    if distortion <= 0.0:
        return nodes.copy()
    result = nodes.copy()
    scale = distortion * min(length / nx, width / ny)
    for index, (x_coord, y_coord, _) in enumerate(nodes):
        if np.isclose(x_coord, 0.0) or np.isclose(x_coord, length):
            continue
        normalized_y = 2.0 * y_coord / width
        result[index, 0] += 0.5 * scale * np.sin(np.pi * x_coord / length) * normalized_y
        if abs(normalized_y) < 1.0 - 1.0e-12:
            result[index, 1] += 0.5 * scale * np.sin(2.0 * np.pi * x_coord / length)
    return result


def _accurate_residual(matrix: object, solution: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    """Evaluate a sparse residual with compensated row summation."""
    csr = matrix.tocsr()
    residual = np.empty(csr.shape[0], dtype=float)
    for row in range(csr.shape[0]):
        start, end = csr.indptr[row], csr.indptr[row + 1]
        products = (float(csr.data[index]) * float(solution[csr.indices[index]]) for index in range(start, end))
        residual[row] = math.fsum(products) - float(rhs[row])
    return residual
