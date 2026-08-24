"""Internal HEX8 V&V campaign for the 0.2.3 alpha gate."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex8 import Hex8Element
from solveur.loads.integration import _hex8_body_vector, _solid_face_vector
from solveur.io.manifest import write_json_file
from solveur.mesh.topology import HEX8_FACES
from solveur.verification.hex8_calculix import run_hex8_calculix_correlation
from solveur.verification.hex8 import Hex8MechanicalVerifier
from solveur.verification.hex8_tet_benchmark import run_multi_model_benchmark


STUDY_ID = "VNV-HEX8-QF-SOLVER-0.2.3A0-INTERNAL-001"


class Hex8InternalCampaign:
    """Run reproducible internal checks without pretending external validation."""

    study_id = STUDY_ID

    def __init__(
        self,
        output_dir: str | Path | None = None,
        *,
        run_external: bool = False,
        external_image: str = "qf-solver/calculix-nafems13h:2.20",
    ):
        self.output_dir = Path(output_dir).resolve() if output_dir is not None else None
        self.run_external = run_external
        self.external_image = external_image

    def run(self) -> dict[str, object]:
        started = perf_counter()
        kernel = Hex8MechanicalVerifier().run()
        analyses = self._common_analysis_paths()
        loads = self._load_checks()
        fields = self._field_cases()
        convergence = self._h_convergence()
        benchmark_output = self.output_dir / "tet_hex_multi_model" if self.output_dir is not None else None
        tet_hex = run_multi_model_benchmark(benchmark_output)
        external = self._external_correlation()
        internal_pass = (
            kernel["status"] == "PASS"
            and all(row["status"] == "PASS" for row in analyses)
            and loads["status"] == "PASS"
            and fields["status"] == "PASS"
            and convergence["status"] == "PASS"
            and tet_hex["status"] == "PASS_INTERNAL"
        )
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_INTERNAL" if internal_pass else "FAIL",
            "maturity": "research",
            "execution_seconds": perf_counter() - started,
            "kernel_verification": kernel,
            "common_analysis_paths": analyses,
            "load_cases": loads,
            "field_cases": fields,
            "h_convergence": convergence,
            "tet_hex_benchmark": tet_hex,
            "external_correlation": external,
            "open_gates": ([] if external["status"] == "PASS_EXTERNAL_CORRELATION" else ["H8-G09"]) + ["H8-G12"],
        }
        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            write_json_file(self.output_dir / "summary.json", summary)
            (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        return summary

    def _external_correlation(self) -> dict[str, object]:
        if not self.run_external:
            return {"status": "OPEN", "required": True, "solver": "CalculiX or Code_Aster", "execution": "not_requested"}
        if self.output_dir is None:
            raise ValueError("An output directory is required to run the external HEX8 correlation.")
        return run_hex8_calculix_correlation(self.output_dir / "external_hex8_calculix", image=self.external_image)

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
            except Exception as exc:  # pragma: no cover - reported as a campaign finding
                rows.append({"id": name, "status": "FAIL", "error": str(exc)})
        return rows

    def _h_convergence(self) -> dict[str, object]:
        rows = []
        for divisions in (1, 2, 4, 8, 16, 32, 64):
            error, dofs = _quadratic_strain_error(divisions)
            rows.append({"divisions": divisions, "dofs": dofs, "relative_strain_error": error})
        final_error = float(rows[-1]["relative_strain_error"])
        return {
            "status": "PASS" if final_error <= 0.01 else "FAIL",
            "target": 0.01,
            "method": "reproducible 3D stratified sample of a quadratic displacement field over a structured cube",
            "levels": rows,
        }

    @staticmethod
    def _load_checks() -> dict[str, object]:
        coords = _unit_coords()
        body = _hex8_body_vector(coords, np.asarray([1.0, 2.0, 3.0]))
        traction = _solid_face_vector(coords, HEX8_FACES[1], np.asarray([0.0, 0.0, 2.0]), None, "global")
        pressure = _solid_face_vector(coords, HEX8_FACES[1], None, 2.0, "global")
        checks = [
            {"name": "unit-volume body resultant", "value": float(np.linalg.norm(np.sum(body.reshape((-1, 3)), axis=0) - [1.0, 2.0, 3.0])), "limit": 1.0e-12},
            {"name": "QUAD4 traction resultant", "value": float(np.linalg.norm(np.sum(traction.reshape((-1, 3)), axis=0) - [0.0, 0.0, 2.0])), "limit": 1.0e-12},
            {"name": "QUAD4 pressure resultant", "value": float(np.linalg.norm(np.sum(pressure.reshape((-1, 3)), axis=0) - [0.0, 0.0, -2.0])), "limit": 1.0e-12},
        ]
        for check in checks:
            check["status"] = "PASS" if np.isfinite(check["value"]) and check["value"] <= check["limit"] else "FAIL"
        return {"status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL", "checks": checks}

    @staticmethod
    def _field_cases() -> dict[str, object]:
        element = Hex8Element(_reference_material())
        coords = _unit_coords()
        cases = {
            "tension": np.diag([1.0e-4, 0.0, 0.0]),
            "compression": np.diag([-1.0e-4, 0.0, 0.0]),
            "shear": np.asarray([[0.0, 2.0e-4, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        }
        checks = []
        for name, gradient in cases.items():
            displacement = np.concatenate([gradient @ point for point in coords])
            expected = np.asarray(
                [gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]]
            )
            value = max(float(np.linalg.norm(element.strain_at(coords, displacement, point) - expected)) for point in Hex8Element.integration_points)
            checks.append({"name": name, "value": value, "limit": 1.0e-11, "status": "PASS" if value <= 1.0e-11 else "FAIL"})
        bending_error, _ = _quadratic_strain_error(64)
        checks.append({"name": "bending_quadratic_field_at_final_h", "value": bending_error, "limit": 0.01, "status": "PASS" if bending_error <= 0.01 else "FAIL"})
        return {"status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL", "checks": checks}

    @staticmethod
    def _markdown(summary: dict[str, object]) -> str:
        lines = [f"# {summary['study_id']}", "", f"Statut interne : **{summary['status']}**", "", "## Analyses communes", "", "| Cas | Statut |", "| --- | --- |"]
        for row in summary["common_analysis_paths"]:
            lines.append(f"| {row['id']} | {row['status']} |")
        lines.extend(["", "## Convergence h", "", "| Divisions | DDL | Erreur deformation |", "| ---: | ---: | ---: |"])
        for row in summary["h_convergence"]["levels"]:
            lines.append(f"| {row['divisions']} | {row['dofs']} | {row['relative_strain_error']:.6e} |")
        lines.extend(["", "## Chargements distribues", "", "| Verification | Ecart | Limite | Statut |", "| --- | ---: | ---: | --- |"])
        for check in summary["load_cases"]["checks"]:
            lines.append(f"| {check['name']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
        lines.extend(["", "## Champs traction/compression/cisaillement/flexion", "", "| Cas | Ecart | Limite | Statut |", "| --- | ---: | ---: | --- |"])
        for check in summary["field_cases"]["checks"]:
            lines.append(f"| {check['name']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
        lines.extend(["", "## Comparatif TET4/TET10/HEX8 sur trois modèles", "", "| Modele | Element | DDL | Elements | Temps (s) | nnz | CSR estime (octets) | Delta RSS (octets) | Residuel |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["tet_hex_benchmark"]["rows"]:
            lines.append(f"| {row['model']} | {row['element']} | {row['dofs']} | {row['elements']} | {row['solve_seconds']:.6e} | {row['nnz']} | {row['estimated_csr_bytes']} | {row['rss_delta_bytes']} | {row['equilibrium_residual']:.6e} |")
        lines.extend(["", "## Correlation externe", "", f"Statut : **{summary['external_correlation']['status']}**"])
        lines.extend(["", "## Gates encore ouverts", "", "La revue Owner et la non-regression complete restent obligatoires avant toute release."])
        return "\n".join(lines) + "\n"


def _model(analysis: str | dict[str, object]) -> FiniteElementModel:
    nodes = _unit_coords()
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7)],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis=analysis,
    )


def _unit_coords() -> np.ndarray:
    return np.asarray(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        dtype=float,
    )


def _quadratic_strain_error(divisions: int) -> tuple[float, int]:
    errors = []
    weights = []
    size = 1.0 / divisions
    element = Hex8Element(_reference_material())
    sample = sorted({0, divisions // 4, divisions // 2, (3 * divisions) // 4, divisions - 1})
    for k in sample:
        for j in sample:
            for i in sample:
                origin = np.asarray([i * size, j * size, k * size])
                element_coords = np.asarray(
                    [origin + size * np.asarray(offset) for offset in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))]
                )
                displacement = np.concatenate([np.asarray([point[0] ** 2, point[1] ** 2, point[2] ** 2]) for point in element_coords])
                for point in Hex8Element.integration_points:
                    observed = element.strain_at(element_coords, displacement, point)
                    x = Hex8Element.shape_functions(point) @ element_coords
                    expected = np.asarray([2.0 * x[0], 2.0 * x[1], 2.0 * x[2], 0.0, 0.0, 0.0])
                    determinant = Hex8Element.jacobian_determinant(element_coords, point)
                    errors.append(float(np.linalg.norm(observed - expected)) ** 2 * determinant)
                    weights.append(float(np.linalg.norm(expected)) ** 2 * determinant)
    return float(np.sqrt(sum(errors) / max(sum(weights), 1.0e-30))), int((divisions + 1) ** 3 * 3)


def _reference_material():
    from solveur.materials.solid import SolidMaterial

    return SolidMaterial(E=210.0e9, nu=0.3)
