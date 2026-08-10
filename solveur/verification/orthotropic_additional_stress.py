"""Two additional stress-field studies for the orthotropic Owner review."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.io.manifest import write_json_file
from solveur.verification.orthotropic_complex_mesh import (
    OrthotropicComplexCase,
    OrthotropicComplexMeshFactory,
)
from solveur.verification.orthotropic_singularity_vnv import (
    OrthotropicSingularityStressCampaign,
    _relative_scalar,
    _relative_vector,
    _sample_stress,
    _tetra_volumes,
)
from solveur.verification.singularity_stress import SingularityStressAssessor, StressPathSample
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class _StressCase:
    identifier: str
    builder: Callable[[str | Path, float], OrthotropicComplexCase]
    point: tuple[float, float]
    direction: tuple[float, float]
    distances: tuple[float, ...]
    band: tuple[float, float]


class AdditionalOrthotropicStressCampaign:
    """Refine an edge notch and a double-hole coupon with visible S11 fields."""

    campaign_id = "VNV-ORTHOTROPIC-ADDITIONAL-STRESS-006"
    mesh_sizes = (0.20, 0.15, 0.11, 0.085, 0.065)

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        factory = OrthotropicComplexMeshFactory()
        definitions = (
            _StressCase(
                "edge_notched_coupon",
                factory.edge_notched_coupon,
                (2.0, 0.65),
                (0.0, -1.0),
                (0.40, 0.65, 0.90),
                (0.35, 0.85),
            ),
            _StressCase(
                "double_hole_coupon",
                factory.double_hole_coupon,
                (2.83, 0.0),
                (1.0, 0.0),
                (0.40, 0.65, 0.90),
                (0.35, 0.85),
            ),
        )
        cases = [self._run_case(definition) for definition in definitions]
        status = "PASS_STRESS_ACCEPTANCE" if all(case["assessment"]["status"] == "PASS" for case in cases) else "FAIL"
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "engineering_internal_pending_human_recheck",
            "observable": "material-axis S11 [Pa]",
            "blocking_oracle": "Code_Aster 18.1.0 integration-point stress on identical TET4 meshes",
            "cases": cases,
            "limitations": [
                "The two new geometries contain finite-radius concentrations, not mathematical point singularities.",
                "S11 is a stress observable and not an anisotropic failure criterion.",
                "The accepted domain remains small-strain homogeneous orthotropy.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(cases)
        self._plot_fields(cases)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    def _run_case(self, definition: _StressCase) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        samples: list[StressPathSample] = []
        references: list[dict[str, object]] = []
        finest_field: dict[str, object] | None = None
        for level, mesh_size in enumerate(self.mesh_sizes, start=1):
            work = self.output_dir / definition.identifier / f"h{level}"
            work.mkdir(parents=True, exist_ok=True)
            case = definition.builder(work / "mesh.msh", mesh_size)
            qf, aster, _, _ = OrthotropicSingularityStressCampaign._solve_same_mesh(case, work)
            centroids = np.mean(case.nodes[case.elements], axis=1)
            volumes = _tetra_volumes(case.nodes, case.elements)
            qf_path, qf_band = _sample_stress(
                centroids,
                qf,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=0.18,
                weights=volumes,
            )
            aster_path, aster_band = _sample_stress(
                centroids,
                aster,
                definition.point,
                definition.direction,
                definition.distances,
                definition.band,
                path_radius=0.18,
                weights=volumes,
            )
            samples.append(StressPathSample(mesh_size, definition.distances, tuple(qf_path), qf_band))
            references.append({"path": aster_path, "band": aster_band})
            rows.append(
                {
                    "level": level,
                    "mesh_size": mesh_size,
                    "nodes": int(case.nodes.shape[0]),
                    "elements": int(case.elements.shape[0]),
                    "qf_path_S11_pa": qf_path,
                    "qf_band_S11_pa": qf_band,
                    "code_aster_path_S11_pa": aster_path,
                    "code_aster_band_S11_pa": aster_band,
                    "same_mesh_path_error": _relative_vector(qf_path, aster_path),
                    "same_mesh_band_error": _relative_scalar(qf_band, aster_band),
                }
            )
            finest_field = {
                "centroids": centroids.tolist(),
                "qf_S11_pa": qf.tolist(),
                "code_aster_S11_pa": aster.tolist(),
            }
        fine = references[-1]
        assessment = SingularityStressAssessor().assess(
            samples,
            true_singularity=False,
            reference_values=fine["path"],
            reference_band_average=float(fine["band"]),
            reference_kind="code_aster",
        )
        same_mesh_pass = all(
            max(float(row["same_mesh_path_error"]), float(row["same_mesh_band_error"])) <= 0.05
            for row in rows
        )
        if not same_mesh_pass:
            assessment["status"] = "FAIL"
        return {
            "id": definition.identifier,
            "levels": rows,
            "assessment": assessment,
            "same_mesh_code_aster_status": "PASS" if same_mesh_pass else "FAIL",
            "fine_field": finest_field,
        }

    def _plot_convergence(self, cases: list[dict[str, object]]) -> None:
        figure, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), constrained_layout=True)
        for axis, case in zip(axes, cases, strict=True):
            levels = case["levels"]
            elements = [row["elements"] for row in levels]
            for sample_index in range(3):
                axis.semilogx(
                    elements,
                    [row["qf_path_S11_pa"][sample_index] / 1.0e6 for row in levels],
                    "o-",
                    label=f"point {sample_index + 1}",
                )
            axis.set(
                title=str(case["id"]).replace("_", " "),
                xlabel="Nombre de TET4",
                ylabel="S11 materiau [MPa]",
            )
            axis.grid(True, which="both", alpha=0.3)
            axis.legend(fontsize=8)
        figure.savefig(self.output_dir / "additional_stress_convergence.png", dpi=180)
        plt.close(figure)

    def _plot_fields(self, cases: list[dict[str, object]]) -> None:
        figure, axes = plt.subplots(2, 2, figsize=(11.0, 8.0), constrained_layout=True)
        for column, case in enumerate(cases):
            field = case["fine_field"]
            centroids = np.asarray(field["centroids"], dtype=float)
            for row, key in enumerate(("qf_S11_pa", "code_aster_S11_pa")):
                values = np.asarray(field[key], dtype=float) / 1.0e6
                axis = axes[row, column]
                points = axis.scatter(
                    centroids[:, 0],
                    centroids[:, 1],
                    c=values,
                    s=3,
                    cmap="turbo",
                    rasterized=True,
                )
                axis.set_aspect("equal", adjustable="box")
                axis.set(
                    title=f"{case['id']} - {'QF_solver' if row == 0 else 'Code_Aster'}",
                    xlabel="X [m]",
                    ylabel="Y [m]",
                )
                figure.colorbar(points, ax=axis, label="S11 materiau [MPa]")
        figure.savefig(self.output_dir / "additional_stress_fields.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, object]) -> str:
        lines = [
            "# Deux champs de contraintes orthotropes complementaires",
            "",
            f"Verdict : **{summary['status']}**.",
            "",
            "| Cas | Niveaux | TET4 fin | Incr. chemin | Incr. bande | Code_Aster |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for case in summary["cases"]:
            checks = {row["id"]: row["value"] for row in case["assessment"]["checks"]}
            lines.append(
                f"| {case['id']} | {len(case['levels'])} | {case['levels'][-1]['elements']} | "
                f"{100 * checks['final_path_increment']:.3f} % | "
                f"{100 * checks['final_band_increment']:.3f} % | "
                f"{case['same_mesh_code_aster_status']} |"
            )
        lines.extend(
            [
                "",
                "![Convergence](additional_stress_convergence.png)",
                "",
                "![Champs S11 QF_solver et Code_Aster](additional_stress_fields.png)",
                "",
            ]
        )
        return "\n".join(lines)
