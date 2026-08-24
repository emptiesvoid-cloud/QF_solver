"""Deterministic HEX20 verification and internal V&V campaign."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex20 import Hex20Element
from solveur.io.manifest import write_json_file
from solveur.loads.integration import _hex20_body_vector, _solid_face_vector
from solveur.mesh.topology import HEX20_FACES
from solveur.verification.hex20_calculix import run_hex20_calculix_correlation
from solveur.verification.hex8_tet_benchmark import run_hex20_multi_model_benchmark


STUDY_ID = "VNV-HEX20-QF-SOLVER-0.2.3A0-INTERNAL-001"


class Hex20MechanicalVerifier:
    """Run formulation checks that do not require an external solver."""

    def run(self) -> dict[str, object]:
        checks = [
            self._shape_partition(),
            self._nodal_interpolation(),
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
            "element": "HEX20",
            "purpose": "mechanical_verification",
            "integration": "3x3x3_gauss",
            "checks": checks,
        }

    def _shape_partition(self) -> dict[str, object]:
        value = max(abs(float(np.sum(Hex20Element.shape_functions(point))) - 1.0) for point in Hex20Element.integration_points)
        return _check("shape function partition", value, 1.0e-14)

    def _nodal_interpolation(self) -> dict[str, object]:
        natural = _natural_nodes()
        matrix = np.vstack([Hex20Element.shape_functions(point) for point in natural])
        value = float(np.max(np.abs(matrix - np.eye(20))))
        return _check("Gmsh nodal interpolation", value, 1.0e-14)

    def _jacobian(self) -> dict[str, object]:
        values = [Hex20Element.jacobian_determinant(_unit_coords(), point) for point in Hex20Element.integration_points]
        return _check("unit cube Jacobian", max(abs(float(item) - 0.125) for item in values), 1.0e-14)

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
        coords = _unit_coords()
        displacement = np.concatenate([gradient @ point for point in coords])
        expected = np.asarray([gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]])
        values = [_element().strain_at(coords, displacement, point) for point in Hex20Element.integration_points]
        value = max(float(np.linalg.norm(item - expected)) for item in values) / max(float(np.linalg.norm(expected)), 1.0e-30)
        return _check("affine strain patch", value, 1.0e-11)

    def _affine_energy(self) -> dict[str, object]:
        gradient = np.asarray([[2.0e-4, 3.0e-5, -2.0e-5], [4.0e-5, -1.0e-4, 5.0e-5], [1.0e-5, 6.0e-5, 0.5e-4]])
        strain = np.asarray([gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]])
        coords = _unit_coords()
        displacement = np.concatenate([gradient @ point for point in coords])
        material = _element().material
        observed = 0.5 * displacement @ (_element().stiffness(coords) @ displacement)
        expected = 0.5 * strain @ material.elasticity_matrix @ strain
        return _check("affine analytical energy", abs(float(observed - expected)) / abs(float(expected)), 1.0e-11)

    def _rigid_modes(self) -> dict[str, object]:
        coords = _unit_coords()
        stiffness = _element().stiffness(coords)
        scale = max(float(np.linalg.norm(stiffness, ord=np.inf)), 1.0)
        modes = []
        for axis in range(3):
            mode = np.zeros(60)
            mode[axis::3] = 1.0
            modes.append(mode)
        for axis in np.eye(3):
            modes.append(np.concatenate([np.cross(axis, point) for point in coords]))
        value = max(float(np.linalg.norm(stiffness @ mode, ord=np.inf)) / scale for mode in modes)
        return _check("rigid body modes", value, 1.0e-10)

    def _distorted_geometry(self) -> dict[str, object]:
        coords = _unit_coords().copy()
        coords[6] += np.asarray([0.15, -0.08, 0.1])
        # Keep the midside nodes on the distorted corner edges.
        for index, (first, second) in enumerate(_edge_pairs(), start=8):
            coords[index] = 0.5 * (coords[first] + coords[second])
        determinants = [Hex20Element.jacobian_determinant(coords, point) for point in Hex20Element.integration_points]
        value = 0.0 if min(determinants) > 0.0 else 1.0
        return _check("positive Jacobian under bounded distortion", value, 0.0)

    def _near_incompressible_materials(self) -> dict[str, object]:
        values = []
        for poisson in (0.49, 0.499):
            stiffness = Hex20Element(_reference_material(poisson)).stiffness(_unit_coords())
            values.append(0.0 if np.all(np.isfinite(stiffness)) else 1.0)
        return _check("near incompressible finite stiffness", max(values), 0.0)


class Hex20InternalCampaign:
    """Run the internal HEX20 V&V package while keeping external gates explicit."""

    study_id = STUDY_ID

    def __init__(self, output_dir: str | Path | None = None, *, run_external: bool = False, external_image: str = "qf-solver/calculix-nafems13h:2.20"):
        self.output_dir = Path(output_dir).resolve() if output_dir is not None else None
        self.run_external = run_external
        self.external_image = external_image

    def run(self) -> dict[str, object]:
        started = perf_counter()
        kernel = Hex20MechanicalVerifier().run()
        analyses = self._common_analysis_paths()
        loads = self._load_checks()
        j2 = self._j2_case()
        benchmark_output = self.output_dir / "tet_hex20_multi_model" if self.output_dir is not None else None
        benchmark = run_hex20_multi_model_benchmark(benchmark_output)
        external = self._external_correlation()
        internal_pass = kernel["status"] == "PASS" and all(row["status"] == "PASS" for row in analyses) and loads["status"] == "PASS" and j2["status"] == "PASS" and benchmark["status"] == "PASS_INTERNAL"
        open_gates = ["H20-G11", "H20-G12"] if external["status"] == "PASS_EXTERNAL_CORRELATION" else ["H20-G10", "H20-G11", "H20-G12"]
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_INTERNAL" if internal_pass else "FAIL",
            "maturity": "research",
            "execution_seconds": perf_counter() - started,
            "kernel_verification": kernel,
            "common_analysis_paths": analyses,
            "load_cases": loads,
            "j2_case": j2,
            "tet_hex20_benchmark": benchmark,
            "external_correlation": external,
            "open_gates": open_gates,
        }
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            write_json_file(self.output_dir / "summary.json", summary)
            (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        return summary

    def _external_correlation(self) -> dict[str, object]:
        if not self.run_external:
            return {"status": "OPEN", "required": True, "solvers": ["CalculiX C3D20", "Code_Aster HEXA20"], "execution": "not_requested"}
        if self.output_dir is None:
            raise ValueError("An output directory is required to run the external HEX20 correlation.")
        return run_hex20_calculix_correlation(self.output_dir / "external_hex20_calculix", image=self.external_image)

    def _common_analysis_paths(self) -> list[dict[str, object]]:
        cases = (
            ("static", "linear_static"),
            ("modal", {"type": "modal", "modes": 5}),
            ("newmark", {"type": "transient_dynamic", "time_step": 0.01, "end_time": 0.02, "beta": 0.25, "gamma": 0.5}),
            ("harmonic", {"type": "harmonic_response", "frequencies": [1.0]}),
        )
        rows = []
        for name, analysis in cases:
            try:
                result = solve_model(_model(analysis))
                rows.append({"id": name, "status": "PASS" if result.status == "PASS" else "FAIL", "solver_status": result.status})
            except Exception as exc:  # pragma: no cover - campaign findings are data
                rows.append({"id": name, "status": "FAIL", "error": str(exc)})
        return rows

    @staticmethod
    def _load_checks() -> dict[str, object]:
        coords = _unit_coords()
        body = _hex20_body_vector(coords, np.asarray([1.0, 2.0, 3.0]))
        traction = _solid_face_vector(coords, HEX20_FACES[1], np.asarray([0.0, 0.0, 2.0]), None, "global")
        pressure = _solid_face_vector(coords, HEX20_FACES[1], None, 2.0, "global")
        checks = [
            {"name": "unit-volume body resultant", "value": float(np.linalg.norm(np.sum(body.reshape((-1, 3)), axis=0) - [1.0, 2.0, 3.0])), "limit": 1.0e-12},
            {"name": "QUAD8 traction resultant", "value": float(np.linalg.norm(np.sum(traction.reshape((-1, 3)), axis=0) - [0.0, 0.0, 2.0])), "limit": 1.0e-12},
            {"name": "QUAD8 pressure resultant", "value": float(np.linalg.norm(np.sum(pressure.reshape((-1, 3)), axis=0) - [0.0, 0.0, -2.0])), "limit": 1.0e-12},
        ]
        for check in checks:
            check["status"] = "PASS" if np.isfinite(check["value"]) and check["value"] <= check["limit"] else "FAIL"
        return {"status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL", "checks": checks}

    @staticmethod
    def _j2_case() -> dict[str, object]:
        analysis = {"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0]}
        try:
            result = solve_model(_model(analysis, nonlinear=True)).to_dict()
            steps = result["solver"]["steps"]
            value = float(max(step["relative_residual"] for step in steps))
            return {"status": "PASS" if result["status"] == "PASS" else "FAIL", "steps": len(steps), "max_relative_residual": value, "integration_points": 27}
        except Exception as exc:  # pragma: no cover - campaign findings are data
            return {"status": "FAIL", "error": str(exc)}

    @staticmethod
    def _markdown(summary: dict[str, object]) -> str:
        lines = [f"# {summary['study_id']}", "", f"Statut interne : **{summary['status']}**", "", "## Résultats", "", "| Domaine | Statut |", "| --- | --- |"]
        for key in ("kernel_verification", "load_cases", "j2_case", "tet_hex20_benchmark"):
            item = summary[key]
            lines.append(f"| {key} | {item['status']} |")
        lines.extend(["", "## Analyses communes", "", "| Cas | Statut |", "| --- | --- |"])
        for row in summary["common_analysis_paths"]:
            lines.append(f"| {row['id']} | {row['status']} |")
        lines.extend(["", "## Comparaison TET4/TET10/HEX8/HEX20", "", "| Modèle | Élément | DDL | Temps (s) | nnz | Résidu |", "| --- | --- | ---: | ---: | ---: | ---: |"])
        for row in summary["tet_hex20_benchmark"]["rows"]:
            lines.append(f"| {row['model']} | {row['element']} | {row['dofs']} | {row['solve_seconds']:.6e} | {row['nnz']} | {row['equilibrium_residual']:.6e} |")
        lines.extend(
            [
                "",
                "## Corrélations externes",
                "",
                f"CalculiX C3D20 : **{summary['external_correlation']['status']}** ; "
                "Code_Aster HEXA20 : **OPEN** ; Owner : **OPEN**.",
                "",
            ]
        )
        return "\n".join(lines)


def _model(analysis: str | dict[str, object], *, nonlinear: bool = False) -> FiniteElementModel:
    coords = _unit_coords()
    material = (
        {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "density": 1.0, "yield_stress": 0.02, "hardening_modulus": 10.0}
        if nonlinear
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    return FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": "HEX20", "nodes": list(range(20)), "material": "solid"}],
        materials={"solid": material},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7, 9, 10, 15, 17)],
        loads=[{"node": 1, "dof": "UX", "value": 5.0 if nonlinear else 1.0}],
        analysis=analysis,
    )


def _unit_coords() -> np.ndarray:
    corners = np.asarray([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=float)
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in _edge_pairs()]])


def _edge_pairs() -> tuple[tuple[int, int], ...]:
    return ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))


def _natural_nodes() -> np.ndarray:
    return np.asarray([(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1), (0, -1, -1), (-1, 0, -1), (-1, -1, 0), (1, 0, -1), (1, -1, 0), (0, 1, -1), (1, 1, 0), (-1, 1, 0), (0, -1, 1), (-1, 0, 1), (1, 0, 1), (0, 1, 1)], dtype=float)


def _element(*, density: float = 0.0) -> Hex20Element:
    return Hex20Element(_reference_material(0.3, density=density))


def _reference_material(poisson: float, *, density: float = 0.0):
    from solveur.materials.solid import SolidMaterial

    return SolidMaterial(E=210.0e9, nu=poisson, density=density)


def _check(name: str, value: float, limit: float) -> dict[str, object]:
    return {"name": name, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}
