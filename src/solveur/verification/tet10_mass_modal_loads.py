"""TET10 consistent mass, modal, curved load and stress-recovery V&V."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.elements.solid.quadrature import tetra_duffy_rule, triangle_duffy_rule, triangle_shape_functions
from solveur.elements.solid.tet10 import Tet10Element
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.materials.solid import SolidMaterial
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.topology import TET10_FACES
from solveur.post.stress import StressPostProcessor
from solveur.verification.tet10_geometry_quadrature import curved_tet10_fixture
from solveur.verification.tet10_structural_convergence import plot_tetra_vector
from solveur.verification.vnv_manifest import write_vnv_manifest


class Tet10MassModalLoadsCampaign:
    """Verify the remaining linear TET10 mass, modal, face-load and recovery chain."""

    study_id = "VNV-TET10-MASS-MODAL-LOADS-013"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mass = self._curved_mass()
        pressure = self._curved_pressure()
        recovery = self._curved_recovery()
        modal = self._cantilever_modal()
        checks = [
            _upper("curved_mass_total", float(mass["relative_total_mass_error"]), 1.0e-10),
            _upper("curved_mass_symmetry", float(mass["symmetry_error"]), 1.0e-13),
            _lower("curved_mass_minimum_eigenvalue", float(mass["minimum_eigenvalue"]), 0.0),
            _upper("curved_pressure_resultant", float(pressure["relative_resultant_error"]), 1.0e-10),
            _upper("curved_pressure_moment", float(pressure["relative_moment_error"]), 1.0e-10),
            _upper("curved_recovery_strain", float(recovery["relative_strain_error"]), 1.0e-11),
            _upper("curved_recovery_stress", float(recovery["relative_stress_error"]), 1.0e-11),
            _upper("modal_first_pair_frequency", float(modal["maximum_frequency_error"]), 0.02),
            _upper("modal_first_pair_split", float(modal["pair_relative_split"]), 1.0e-3),
            _upper("modal_residual", float(modal["maximum_relative_residual"]), 1.0e-8),
            _upper("modal_mass_orthogonality", float(modal["mass_orthogonality_error"]), 1.0e-8),
            _upper("modal_stiffness_orthogonality", float(modal["stiffness_diagonal_error"]), 1.0e-8),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "mass": mass,
            "curved_pressure": pressure,
            "curved_stress_recovery": recovery,
            "modal": modal,
            "checks": checks,
            "scope_limit": (
                "Consistent mass and linear elastic TET10 only. Lumped mass, path-dependent "
                "curved TET10 and nonlinear geometry remain excluded."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    @staticmethod
    def _curved_mass() -> dict[str, float]:
        coords = curved_tet10_fixture()
        density = 7800.0
        element = Tet10Element(SolidMaterial(E=210.0e9, nu=0.3, density=density))
        mass = element.mass(coords)
        reference_volume = sum(
            weight * float(np.linalg.det(element.shape_derivatives_reference(point).T @ coords))
            for point, weight in tetra_duffy_rule(8)
        )
        expected = density * reference_volume
        observed = float(np.sum(mass) / 3.0)
        return {
            "reference_volume": reference_volume,
            "expected_physical_mass": expected,
            "observed_physical_mass": observed,
            "relative_total_mass_error": _relative(observed, expected),
            "symmetry_error": float(np.linalg.norm(mass - mass.T) / np.linalg.norm(mass)),
            "minimum_eigenvalue": float(np.min(np.linalg.eigvalsh(mass))),
        }

    @staticmethod
    def _curved_pressure() -> dict[str, object]:
        coords = curved_tet10_fixture()
        pressure = 2.0
        model = _single_element_model(
            coords,
            distributed_loads=[{"type": "pressure", "element": 0, "face": 1, "value": pressure}],
        )
        dofs = model.dof_manager()
        assembler = GlobalAssembler()
        assembler.assemble_loads(model, dofs)
        observed_resultant = np.asarray(assembler.last_load_diagnostics["resultant"], dtype=float)
        observed_moment = np.asarray(assembler.last_load_diagnostics["moment_about_origin"], dtype=float)
        reference_resultant, reference_moment = _pressure_reference(coords, 1, pressure)
        return {
            "face": 1,
            "pressure": pressure,
            "observed_resultant": observed_resultant.tolist(),
            "reference_resultant": reference_resultant.tolist(),
            "observed_moment": observed_moment.tolist(),
            "reference_moment": reference_moment.tolist(),
            "relative_resultant_error": _vector_relative(observed_resultant, reference_resultant),
            "relative_moment_error": _vector_relative(observed_moment, reference_moment),
        }

    @staticmethod
    def _curved_recovery() -> dict[str, object]:
        coords = curved_tet10_fixture()
        model = _single_element_model(coords)
        dofs = model.dof_manager()
        gradient = np.array(
            [[1.0e-3, 2.0e-4, 0.0], [1.0e-4, -4.0e-4, 3.0e-4], [0.0, 2.0e-4, 5.0e-4]]
        )
        displacement = np.concatenate([gradient @ point for point in coords])
        expected_strain = np.array([1.0e-3, -4.0e-4, 5.0e-4, 3.0e-4, 5.0e-4, 0.0])
        material = SolidMaterial(E=210.0e9, nu=0.3)
        expected_stress = material.elasticity_matrix @ expected_strain
        result = StressPostProcessor().element_results(model, dofs, displacement)[0]
        nodal_strains = np.asarray([row["strain"] for row in result["nodal_results"]], dtype=float)
        nodal_stresses = np.asarray([row["stress"] for row in result["nodal_results"]], dtype=float)
        return {
            "integration_point_count": len(result["integration_points"]),
            "recovery_method": result["nodal_results"][0]["method"],
            "relative_strain_error": float(
                np.linalg.norm(nodal_strains - expected_strain) / np.linalg.norm(np.tile(expected_strain, (10, 1)))
            ),
            "relative_stress_error": float(
                np.linalg.norm(nodal_stresses - expected_stress) / np.linalg.norm(np.tile(expected_stress, (10, 1)))
            ),
        }

    def _cantilever_modal(self) -> dict[str, object]:
        length, width, height = 8.0, 1.0, 1.0
        young, poisson, density = 70.0e9, 0.3, 2700.0
        mesh = BenchmarkMeshFactory().box_tetra(
            self.output_dir / "modal_tet10.msh",
            length=length,
            width=width,
            height=height,
            mesh_size=0.5,
            order=2,
        )
        setup = _modal_setup(young, poisson, density)
        setup_path = self.output_dir / "modal_tet10.setup.json"
        write_json_file(setup_path, setup)
        imported = GmshModelImporter().import_model(mesh, setup_path)
        JsonModelWriter().write(imported.model, self.output_dir / "modal_tet10.model.json")
        result = enforce_qualification_policy(AnalysisRouter().solve(imported.model), imported.model)
        JsonResultWriter().write(result, self.output_dir / "modal_tet10.result.json")
        data = result.to_dict()
        frequencies = np.asarray([mode["frequency_hz"] for mode in data["modes"]], dtype=float)
        beta = 1.875104068711961
        inertia = width * height**3 / 12.0
        analytical = beta**2 / (2.0 * np.pi * length**2) * np.sqrt(young * inertia / (density * width * height))
        first_pair = frequencies[:2]
        solver = data["solver"]
        plot_tetra_vector(
            self.output_dir / "tet10_modal_mode1.png",
            imported.model,
            _mode_vector(data["modes"][0]["shape"], imported.model),
            "TET10 premier mode de flexion",
        )
        return {
            "analytical_euler_bernoulli_hz": analytical,
            "frequencies_hz": frequencies.tolist(),
            "first_pair_frequency_errors": [float(_relative(value, analytical)) for value in first_pair],
            "maximum_frequency_error": max(_relative(value, analytical) for value in first_pair),
            "pair_relative_split": _relative(float(first_pair[1]), float(first_pair[0])),
            "maximum_relative_residual": float(solver["max_relative_residual"]),
            "mass_orthogonality_error": float(solver["mass_orthogonality_error"]),
            "stiffness_diagonal_error": float(solver["stiffness_diagonal_error"]),
            "node_count": imported.model.node_count,
            "element_count": len(imported.model.elements),
            "dof_count": imported.model.dof_manager().ndof,
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        modal = summary["modal"]
        pressure = summary["curved_pressure"]
        recovery = summary["curved_stress_recovery"]
        mass = summary["mass"]
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "| Verification | Valeur |",
            "| --- | ---: |",
            f"| erreur masse courbe | {mass['relative_total_mass_error']:.3e} |",
            f"| erreur resultante pression | {pressure['relative_resultant_error']:.3e} |",
            f"| erreur moment pression | {pressure['relative_moment_error']:.3e} |",
            f"| erreur contrainte nodale | {recovery['relative_stress_error']:.3e} |",
            f"| frequence analytique | {modal['analytical_euler_bernoulli_hz']:.6f} Hz |",
            f"| premiere paire TET10 | {modal['frequencies_hz'][0]:.6f} / {modal['frequencies_hz'][1]:.6f} Hz |",
            f"| residu modal maximal | {modal['maximum_relative_residual']:.3e} |",
            "",
            "La masse concentree et les materiaux dependants du chemin restent hors scope.",
            "",
            "![Premier mode TET10](tet10_modal_mode1.png)",
            "",
        ]
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _single_element_model(
    coords: np.ndarray,
    *,
    distributed_loads: list[dict[str, object]] | None = None,
) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": "TET10", "nodes": list(range(10)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        distributed_loads=distributed_loads,
    )


def _pressure_reference(coords: np.ndarray, face_index: int, pressure: float) -> tuple[np.ndarray, np.ndarray]:
    face_coords = coords[list(TET10_FACES[face_index])]
    resultant = np.zeros(3)
    moment = np.zeros(3)
    for barycentric, weight in triangle_duffy_rule(9):
        shape, derivatives = triangle_shape_functions(6, barycentric)
        tangent_u = derivatives[:, 0] @ face_coords
        tangent_v = derivatives[:, 1] @ face_coords
        force = -pressure * np.cross(tangent_u, tangent_v) * weight
        point = shape @ face_coords
        resultant += force
        moment += np.cross(point, force)
    return resultant, moment


def _mode_vector(shape: list[dict[str, object]], model: FiniteElementModel) -> np.ndarray:
    dofs = model.dof_manager()
    vector = np.zeros(dofs.ndof, dtype=float)
    for row in shape:
        node = int(row["node"])
        values = row["dofs"]
        for dof, value in values.items():
            vector[dofs.index(node, str(dof))] = float(value)
    return vector


def _modal_setup(young: float, poisson: float, density: float) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "engineering",
        "analysis": {"type": "modal", "method": "eigsh", "num_modes": 6},
        "materials": {
            "solid": {"type": "isotropic_3d", "E": young, "nu": poisson, "density": density}
        },
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": "TET10", "material": "solid"}],
            },
            {
                "name": "x_min",
                "dimension": 2,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}],
            },
        ],
    }


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _vector_relative(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), np.finfo(float).tiny))


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value > limit else "FAIL"}
