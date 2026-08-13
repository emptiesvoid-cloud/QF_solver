"""Multi-element TET4 cyclic J2 verification campaign."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.j2_material import solve_uniaxial_stress_path


class J2StructuralCyclicCampaign:
    """Compare a meshed cyclic TET4 or TET10 bar to a material-point path."""

    campaign_id = "VNV-J2-TET4-CYCLIC-003"

    def __init__(self, output_dir: str | Path, *, element_type: str = "TET4"):
        self.output_dir = Path(output_dir).resolve()
        self.element_type = str(element_type).upper()
        if self.element_type not in {"TET4", "TET10"}:
            raise ValueError("J2 structural campaign supports TET4 or TET10 only.")
        self.campaign_id = (
            "VNV-J2-TET10-CYCLIC-001" if self.element_type == "TET10" else "VNV-J2-TET4-CYCLIC-003"
        )

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mesh = BenchmarkMeshFactory().box_tetra(
            self.output_dir / f"j2_cyclic_bar_{self.element_type.lower()}.msh",
            length=1.0,
            width=0.2,
            height=0.2,
            mesh_size=0.18,
            order=2 if self.element_type == "TET10" else 1,
            anchors=True,
        )
        setup = self._setup(self.element_type)
        setup_path = self.output_dir / "model.setup.json"
        write_json_file(setup_path, setup)
        imported = GmshModelImporter().import_model(mesh, setup_path)
        model = imported.model
        result = solve_model(model)
        data = result.to_dict()
        JsonModelWriter().write(model, self.output_dir / "model.json")
        JsonResultWriter().write(result, self.output_dir / "results.json")
        VtuResultWriter().write(result, model, self.output_dir / "deformation.vtu")
        write_json_file(self.output_dir / "import_report.json", imported.report.to_dict())
        structural = np.asarray(
            [step["equivalent_plastic_strain_max"] for step in data["solver"]["steps"]], dtype=float
        )
        factors = np.asarray(setup["analysis"]["load_path"], dtype=float)
        applied = float(setup["groups"][-1]["actions"][0]["value"][0])
        material_data = setup["materials"]["j2"]
        material = VonMisesElastoplasticMaterial(
            E=float(material_data["E"]),
            nu=float(material_data["nu"]),
            yield_stress=float(material_data["yield_stress"]),
            hardening_modulus=float(material_data["hardening_modulus"]),
        )
        oracle_rows = solve_uniaxial_stress_path(material, factors * applied)
        oracle = np.asarray([row["equivalent_plastic_strain"] for row in oracle_rows], dtype=float)
        scale = max(float(np.max(oracle)), np.finfo(float).tiny)
        plastic_error = float(np.max(np.abs(structural - oracle)) / scale)
        final_target = float(factors[-1] * applied)
        final_stress = float(np.mean([row["stress"][0] for row in data["element_results"]]))
        stress_error = abs(final_stress - final_target) / abs(final_target)
        maximum_residual = max(float(step["relative_residual"]) for step in data["solver"]["steps"])
        monotonicity_violation = max(0.0, -float(np.min(np.diff(structural))))
        first_peak = int(np.where(factors == 1.0)[0][0])
        reverse_peak = int(np.argmin(factors))
        reverse_growth = float(structural[reverse_peak] - structural[first_peak])
        reload_growth = float(structural[-1] - structural[reverse_peak])
        checks = [
            _check("material_point_path_error", plastic_error, 1.0e-8),
            _check("final_axial_stress_error", stress_error, 1.0e-8),
            _check("maximum_step_residual", maximum_residual, 1.0e-7),
            _check("plastic_strain_monotonicity", monotonicity_violation, 1.0e-14),
            _lower_check("reverse_plastic_flow", reverse_growth, 1.0e-6),
            _lower_check("reload_plastic_flow", reload_growth, 1.0e-6),
        ]
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "maturity": "experimental",
            "mesh": {
                "nodes": model.node_count,
                "elements": len(model.elements),
                "element_type": self.element_type,
                "integration_points_per_element": 4 if self.element_type == "TET10" else 1,
            },
            "load_path": factors.tolist(),
            "structural_equivalent_plastic_strain": structural.tolist(),
            "oracle_equivalent_plastic_strain": oracle.tolist(),
            "checks": checks,
            "rollback_test": "tests/unit/test_nonlinear_load_path.py::test_adaptive_rejection_rolls_back_displacement_and_material_state",
            "limitations": [
                "Small-strain isotropic hardening only.",
                "The external CalculiX correlation is monotonic; this signed cycle uses the analytical material-point oracle.",
                "The published baseline uses full Newton; Armijo is covered separately on the same cyclic path.",
                "No geometric nonlinearity, kinematic hardening or damage.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        self._plot(summary)
        return summary

    @staticmethod
    def _setup(element_type: str = "TET4") -> dict[str, object]:
        family = str(element_type).upper()
        if family not in {"TET4", "TET10"}:
            raise ValueError("J2 structural setup supports TET4 or TET10 only.")
        return {
            "schema_version": 1,
            "mesh_scale_to_m": 1.0,
            "units": {"system": "SI"},
            "verification_profile": "engineering",
            "analysis": {
                "type": "nonlinear_static",
                "method": "newton_raphson",
                "load_steps": 25,
                "load_path": [
                    0.25,
                    0.5,
                    0.75,
                    1.0,
                    0.75,
                    0.5,
                    0.25,
                    0.0,
                    -0.25,
                    -0.5,
                    -0.75,
                    -1.0,
                    -1.2,
                    -1.0,
                    -0.75,
                    -0.5,
                    -0.25,
                    0.0,
                    0.25,
                    0.5,
                    0.75,
                    1.0,
                    1.2,
                    1.4,
                ],
                "max_iterations": 50,
                "tolerance": 1.0e-7,
            },
            "materials": {
                "j2": {
                    "type": "von_mises_elastoplastic_3d",
                    "E": 210.0e9,
                    "nu": 0.3,
                    "yield_stress": 250.0e6,
                    "hardening_modulus": 50.0e9,
                }
            },
            "groups": [
                {"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": family, "material": "j2"}]},
                {"name": "x_min", "dimension": 2, "actions": [{"type": "fixed_dofs", "dofs": ["UX"]}]},
                {"name": "anchor_origin", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UY", "UZ"]}]},
                {"name": "anchor_xy", "dimension": 0, "actions": [{"type": "fixed_dofs", "dofs": ["UZ"]}]},
                {"name": "x_max", "dimension": 2, "actions": [{"type": "surface_traction", "value": [300.0e6, 0.0, 0.0]}]},
            ],
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            (
                f"Maillage : {summary['mesh']['nodes']} noeuds, {summary['mesh']['elements']} "
                f"{summary['mesh']['element_type']}, "
                f"{summary['mesh']['integration_points_per_element']} points d'integration par element."
            ),
            "",
            "| Verification | Valeur | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
        ]
        for check in summary["checks"]:
            lines.append(f"| {check['id']} | {check['value']:.6e} | {check['limit']:.6e} | {check['status']} |")
        lines.extend(["", "![Cycle structurel](cyclic_response.png)", "", "Le rollback est verifie par injection d'un increment rejete dans le test unitaire reference par le resume JSON.", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        factors = np.asarray(summary["load_path"])
        structural = np.asarray(summary["structural_equivalent_plastic_strain"])
        oracle = np.asarray(summary["oracle_equivalent_plastic_strain"])
        steps = np.arange(1, len(factors) + 1)
        figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
        axes[0].plot(steps, factors, marker="o", color="#c92a2a")
        axes[0].axhline(0.0, color="#343a40", linewidth=0.8)
        axes[0].set(xlabel="Increment", ylabel="Facteur de charge", title="Cycle signe")
        axes[1].plot(steps, oracle, color="#c92a2a", linewidth=2.2, label="Oracle material-point")
        axes[1].plot(
            steps,
            structural,
            "o--",
            color="#0b7285",
            label=f"Barre {self.element_type}",
        )
        axes[1].set(xlabel="Increment", ylabel="Deformation plastique equivalente", title="Etat interne commite")
        axes[1].legend()
        for axis in axes:
            axis.grid(alpha=0.25)
        figure.suptitle(f"J2 isotrope {self.element_type} - chargement, inversion et rechargement")
        figure.savefig(self.output_dir / "cyclic_response.png", dpi=180)
        plt.close(figure)


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower_check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
