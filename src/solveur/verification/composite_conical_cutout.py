"""Curved laminate MITC4 campaign on a faceted conical panel with a cutout."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.json_writer import JsonResultWriter
from solveur.io.manifest import write_json_file
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.verification.composite_structural import _laminate_definition
from solveur.verification.mitc4_conical_cutout import _outer_ring_nodes, _relative, _vector_displacements, build_conical_cutout_model
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-COMP-CONICAL-CUTOUT-009"


class CompositeConicalCutoutStudy:
    """Exercise projected laminate axes on a curved shell with a free opening."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))
    angles = (0.0, 45.0, -45.0, 90.0)

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        fine_model: FiniteElementModel | None = None
        fine_result: object | None = None
        for radial, circumferential in self.meshes:
            model, probe = build_composite_conical_cutout_model(radial, circumferential)
            report = check_mesh(model)
            result = solve_model(model)
            displacements = _vector_displacements(result, model)
            offsets = np.asarray([float(item["material_angle_offset_deg"]) for item in result.element_results])
            top_vm = np.asarray(
                [
                    float(next(face["von_mises"] for face in item["shell_faces"] if face["face"] == "top"))
                    for item in result.element_results
                ]
            )
            rows.append(
                {
                    "radial_elements": radial,
                    "circumferential_elements": circumferential,
                    "elements": len(model.elements),
                    "nodes": model.node_count,
                    "probe_node": probe,
                    "probe_uz_m": float(displacements[probe, 2]),
                    "maximum_displacement_m": float(np.max(np.linalg.norm(displacements, axis=1))),
                    "top_von_mises_max_pa": float(np.max(top_vm)),
                    "orientation_offset_min_deg": float(np.min(offsets)),
                    "orientation_offset_max_deg": float(np.max(offsets)),
                    "free_relative_residual": float(result.audit.equilibrium["free_relative_residual"]),
                    "mesh_status": report.status,
                    "run_verdict": result.run_verdict.value,
                }
            )
            fine_model, fine_result = model, result
        assert fine_model is not None and fine_result is not None
        checks = [
            _upper("final_probe_increment", _relative(rows[-1]["probe_uz_m"], rows[-2]["probe_uz_m"]), 0.05),
            _upper("maximum_free_relative_residual", max(float(row["free_relative_residual"]) for row in rows), 1.0e-8),
            _equal("all_meshes_exploitable", [str(row["mesh_status"]) for row in rows], ["PASS"] * len(rows)),
            _equal("no_run_failure", any(str(row["run_verdict"]) == "FAIL" for row in rows), False),
            _upper("orientation_span_deg", max(float(row["orientation_offset_max_deg"]) - float(row["orientation_offset_min_deg"]) for row in rows), 360.0),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": STUDY_ID,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "experimental",
            "geometry": "Faceted conical annular shell, central free opening and clamped outer rim.",
            "laminate": {"angles_deg": list(self.angles), "reference_direction_global": [1.0, 0.0, 0.0], "thickness_m": 0.008},
            "orientation_rule": "Project global reference_direction into every facet plane, then apply each ply angle around the local shell normal.",
            "loading": "Uniform initial-normal pressure of 2500 Pa integrated coherently by MITC4.",
            "convergence": rows,
            "checks": checks,
            "limitations": [
                "Internal curved-geometry evidence only; no external oracle is claimed by this campaign.",
                "MITC4 facets are planar; no curved-isoparametric shell interpolation is claimed.",
                "Free-edge peak stresses and interlaminar S13 are inspection outputs, not acceptance scalars.",
                "Damage, delamination, thermal loading and large rotations remain outside scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        JsonModelWriter().write(fine_model, self.output_dir / "fine_model.json")
        JsonResultWriter().write(fine_result, self.output_dir / "fine_results.json")
        VtuResultWriter().write(fine_result, fine_model, self.output_dir / "fine_deformation.vtu")
        self._plot(fine_model, fine_result, rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _plot(self, model: FiniteElementModel, result: object, rows: list[dict[str, object]]) -> None:
        displacement = _vector_displacements(result, model)
        scale = 0.12 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = model.nodes + scale * displacement
        directions = np.asarray([item["ply_directions_global"][0] for item in result.element_results], dtype=float)
        figure = plt.figure(figsize=(10.4, 4.8))
        for index, (nodes, title, color) in enumerate(((model.nodes, "Maillage et axes projetes", "#315d84"), (deformed, f"Deformee x{scale:.1f}", "#c44536")), start=1):
            axis = figure.add_subplot(1, 2, index, projection="3d")
            for element_index, element in enumerate(model.elements):
                quad = np.asarray(element.nodes, dtype=int)
                loop = np.append(quad, quad[0])
                axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color=color, linewidth=0.32)
                if index == 1 and element_index % 12 == 0:
                    center = np.mean(nodes[quad], axis=0)
                    direction = 0.035 * directions[element_index]
                    axis.quiver(center[0], center[1], center[2], direction[0], direction[1], direction[2], color="#1b1b1b", linewidth=0.45)
            axis.set(title=title, xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
            axis.set_box_aspect((1.0, 1.0, 0.32))
            axis.view_init(elev=26.0, azim=-54.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_conical_cutout_geometry.png", dpi=180)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(7.1, 4.3))
        elements = [int(row["elements"]) for row in rows]
        axis.semilogx(elements, [abs(float(row["probe_uz_m"])) for row in rows], "o-", label="|UZ| sonde")
        axis.semilogx(elements, [float(row["maximum_displacement_m"]) for row in rows], "s-", label="|U| maximum")
        axis.set(xlabel="Elements MITC4", ylabel="Deplacement [m]", title="Convergence composite sur coque conique")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "composite_conical_cutout_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [f"# {STUDY_ID}", "", f"Statut automatise : **{summary['status']}**", "", "Empilement `[0/+45/-45/90]` sur panneau annulaire conique facettise avec ouverture centrale libre.", "", "| Maillage | Elements | UZ sonde [m] | |U| max [m] | VM face sup. max [Pa] | Orientation min/max [deg] |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for row in summary["convergence"]:
            lines.append(f"| {row['radial_elements']}x{row['circumferential_elements']} | {row['elements']} | {row['probe_uz_m']:.6e} | {row['maximum_displacement_m']:.6e} | {row['top_von_mises_max_pa']:.6e} | {row['orientation_offset_min_deg']:.2f}/{row['orientation_offset_max_deg']:.2f} |")
        lines.extend(["", "![Geometrie et deformee](composite_conical_cutout_geometry.png)", "", "![Convergence](composite_conical_cutout_convergence.png)", "", "La contrainte maximale est publiee a titre d'inspection. La zone de bord libre de l'ouverture demande une evaluation par chemin a distance fixee et un oracle externe avant toute acceptance de contrainte locale.", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def build_composite_conical_cutout_model(radial_elements: int, circumferential_elements: int) -> tuple[FiniteElementModel, int]:
    """Return the conical-cutout geometry with a projected-axis laminate."""
    isotropic, probe = build_conical_cutout_model(radial_elements, circumferential_elements)
    laminate = _laminate_definition(list(CompositeConicalCutoutStudy.angles), 0.008)
    laminate["reference_direction"] = [1.0, 0.0, 0.0]
    outer = _outer_ring_nodes(isotropic.nodes)
    model = FiniteElementModel.from_raw(
        nodes=isotropic.nodes.tolist(),
        elements=[{"type": "MITC4", "nodes": list(element.nodes), "material": "laminate"} for element in isotropic.elements],
        materials={"laminate": laminate},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in outer],
        distributed_loads=[{"type": "pressure", "element": index, "value": 2500.0} for index in range(len(isotropic.elements))],
        verification_profile="engineering",
    )
    return model, probe


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _equal(identifier: str, value: object, expected: object) -> dict[str, object]:
    return {"id": identifier, "value": value, "expected": expected, "status": "PASS" if value == expected else "FAIL"}
