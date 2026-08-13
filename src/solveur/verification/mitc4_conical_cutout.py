"""Static MITC4 verification on a faceted conical shell with a central opening.

The geometry is deliberately more representative than a rectangular plate: a
conical annular access panel has a true inner free edge, strong circumferential
curvature, and a curved load direction.  It remains made of planar facets, as
required by the current MITC4 formulation.
"""

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
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-CONICAL-CUTOUT-STATIC-012"


class Mitc4ConicalCutoutStudy:
    """Demonstrate h-convergence on a conical shell with a circular cutout."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        """Solve the three mesh levels and publish reviewable artifacts."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        fine_model: FiniteElementModel | None = None
        fine_result: object | None = None
        for radial, circumferential in self.meshes:
            model, probe = build_conical_cutout_model(radial, circumferential)
            report = check_mesh(model)
            result = solve_model(model)
            displacement = _vector_displacements(result, model)
            rows.append(
                {
                    "radial_elements": radial,
                    "circumferential_elements": circumferential,
                    "elements": len(model.elements),
                    "nodes": model.node_count,
                    "dofs": result.dofs.ndof,
                    "probe_node": probe,
                    "probe_uz_m": float(displacement[probe, 2]),
                    "maximum_displacement_m": float(np.max(np.linalg.norm(displacement, axis=1))),
                    "free_relative_residual": float(result.audit.equilibrium["free_relative_residual"]),
                    "mesh_status": report.status,
                    "run_verdict": result.run_verdict.value,
                    "audit_warnings": [
                        str(check.name)
                        for check in result.audit.checks
                        if check.status == "WARNING"
                    ],
                }
            )
            fine_model, fine_result = model, result

        assert fine_model is not None and fine_result is not None
        increment = _relative(rows[-1]["probe_uz_m"], rows[-2]["probe_uz_m"])
        checks = [
            _upper("final_probe_increment", increment, 0.05),
            _upper(
                "maximum_free_relative_residual",
                max(float(row["free_relative_residual"]) for row in rows),
                1.0e-8,
            ),
            _equal("all_meshes_exploitable", [str(row["mesh_status"]) for row in rows], ["PASS"] * len(rows)),
            _equal(
                "no_run_failure",
                any(str(row["run_verdict"]) == "FAIL" for row in rows),
                False,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": STUDY_ID,
            "status": "PASS_TECHNICAL_VERIFICATION" if passed else "FAIL",
            "maturity": "engineering_internal_supplementary_evidence",
            "geometry": {
                "description": "Faceted conical annular shell with a circular central opening.",
                "inner_radius_m": 0.20,
                "outer_radius_m": 0.75,
                "cone_slope": 0.35,
                "thickness_m": 0.004,
                "facets": "Each quadrilateral lies on a conical generator plane; no warped MITC4 facet is introduced.",
            },
            "boundary_conditions": "Outer circular rim clamped in UX, UY, UZ, RX, RY and RZ; inner rim free.",
            "loading": "Uniform dead pressure of 2500 Pa, normal to each initial facet.",
            "convergence": rows,
            "checks": checks,
            "warnings": sorted(
                {warning for row in rows for warning in row["audit_warnings"]}  # type: ignore[index]
            ),
            "limitations": [
                "This is a faceted conical shell, not a curved-isoparametric MITC4 claim.",
                "The free-edge stress peak at the circular opening is published for inspection but is not an acceptance scalar.",
                "No Code_Aster or CalculiX correlation is claimed by this internal geometry campaign.",
                "Large rotations, contact, buckling and composite layups remain outside this study.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        JsonModelWriter().write(fine_model, self.output_dir / "fine_model.json")
        JsonResultWriter().write(fine_result, self.output_dir / "fine_results.json")
        VtuResultWriter().write(fine_result, fine_model, self.output_dir / "fine_deformation.vtu")
        self._plot_geometry_and_deformation(fine_model, fine_result)
        self._plot_convergence(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _plot_geometry_and_deformation(self, model: FiniteElementModel, result: object) -> None:
        displacement = _vector_displacements(result, model)
        scale = 0.12 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = model.nodes + scale * displacement
        outer = _outer_ring_nodes(model.nodes)
        figure = plt.figure(figsize=(10.2, 4.8))
        for position, (nodes, title, color) in enumerate(
            ((model.nodes, "Maillage initial", "#49759c"), (deformed, f"Deformee x{scale:.1f}", "#c44536")),
            start=1,
        ):
            axis = figure.add_subplot(1, 2, position, projection="3d")
            for element in model.elements:
                quad = np.asarray(element.nodes, dtype=int)
                loop = np.append(quad, quad[0])
                axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color=color, linewidth=0.34)
            if position == 1:
                axis.scatter(model.nodes[outer, 0], model.nodes[outer, 1], model.nodes[outer, 2], s=5, color="#202020", label="Bord encastre")
                axis.legend(loc="upper left")
            axis.set(title=title, xlabel="X [m]", ylabel="Y [m]", zlabel="Z [m]")
            axis.set_box_aspect((1.0, 1.0, 0.32))
            axis.view_init(elev=26.0, azim=-54.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_cutout_geometry_deformation.png", dpi=180)
        plt.close(figure)

    def _plot_convergence(self, rows: list[dict[str, object]]) -> None:
        elements = [int(row["elements"]) for row in rows]
        probe = [abs(float(row["probe_uz_m"])) for row in rows]
        maximum = [float(row["maximum_displacement_m"]) for row in rows]
        figure, axis = plt.subplots(figsize=(7.2, 4.4))
        axis.semilogx(elements, probe, "o-", label="|UZ| sonde radiale")
        axis.semilogx(elements, maximum, "s-", label="|U| maximum")
        axis.set(xlabel="Nombre d'elements MITC4", ylabel="Deplacement [m]", title="Convergence - panneau conique ajoure")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_cutout_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {STUDY_ID}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "## Objet",
            "",
            "Panneau annulaire conique facettise avec ouverture centrale libre. Le bord",
            "exterieur est encastre et une pression uniforme est integree de maniere",
            "coherente sur chaque facette. Ce cas etend les plaques et cylindres simples",
            "sans modifier le perimetre MITC4 statique deja accepte.",
            "",
            "## Convergence",
            "",
            "| Maillage radial x circulaire | Elements | Noeuds | UZ sonde [m] | |U| max [m] | Residu libre |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["convergence"]:
            lines.append(
                f"| {row['radial_elements']} x {row['circumferential_elements']} | {row['elements']} | {row['nodes']} | "
                f"{row['probe_uz_m']:.6e} | {row['maximum_displacement_m']:.6e} | {row['free_relative_residual']:.3e} |"
            )
        lines.extend(
            [
                "",
                "![Geometrie et deformee](conical_cutout_geometry_deformation.png)",
                "",
                "![Convergence](conical_cutout_convergence.png)",
                "",
                "## Limites de lecture",
                "",
                "La contrainte maximale au bord libre de l'ouverture depend du raffinement",
                "et ne doit pas etre employee seule comme critere d'acceptation. Le prochain",
                "niveau de preuve sera une correlation sur la meme geometrie et le meme",
                "maillage avec Code_Aster ou CalculiX, sur deplacements, resultantes et energie.",
                "",
                "## Avertissements de calcul",
                "",
                "Les niveaux fins declenchent uniquement l'avertissement global de bilan",
                "de moments de l'audit (`moment_balance_relative_error` entre `1e-10` et",
                "`1e-8`). Les residus libres, le bilan de forces et l'identite d'energie",
                "restent conformes. Cet avertissement est publie, non masque, et ne bloque",
                "pas cette evidence supplementaire.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def build_conical_cutout_model(radial_elements: int, circumferential_elements: int) -> tuple[FiniteElementModel, int]:
    """Build a planar-facet conical ring and return its deterministic probe node."""
    if radial_elements < 2 or circumferential_elements < 8:
        raise ValueError("Conical cutout mesh requires at least 2 radial and 8 circumferential elements.")
    inner, outer, slope = 0.20, 0.75, 0.35
    nodes = []
    for radial_index in range(radial_elements + 1):
        radius = inner + (outer - inner) * radial_index / radial_elements
        for angular_index in range(circumferential_elements):
            theta = 2.0 * np.pi * angular_index / circumferential_elements
            nodes.append([radius * np.cos(theta), radius * np.sin(theta), slope * (radius - inner)])
    node_array = np.asarray(nodes, dtype=float)
    elements = []
    for radial_index in range(radial_elements):
        for angular_index in range(circumferential_elements):
            next_angle = (angular_index + 1) % circumferential_elements
            start = radial_index * circumferential_elements
            next_start = (radial_index + 1) * circumferential_elements
            elements.append([start + angular_index, next_start + angular_index, next_start + next_angle, start + next_angle])
    outer_nodes = list(range(radial_elements * circumferential_elements, (radial_elements + 1) * circumferential_elements))
    probe = (radial_elements // 2) * circumferential_elements
    model = FiniteElementModel.from_raw(
        nodes=node_array.tolist(),
        elements=[{"type": "MITC4", "nodes": quad, "material": "aluminium"} for quad in elements],
        materials={
            "aluminium": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.33, "t": 0.004, "density": 2700.0, "drilling_scale": 1.0e-4}
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in outer_nodes],
        distributed_loads=[{"type": "pressure", "element": index, "value": 2500.0} for index in range(len(elements))],
        verification_profile="engineering",
    )
    return model, probe


def _vector_displacements(result: object, model: FiniteElementModel) -> np.ndarray:
    values = np.zeros((model.node_count, 3))
    for node in range(model.node_count):
        for component, dof in enumerate(("UX", "UY", "UZ")):
            values[node, component] = result.displacements[result.dofs.index(node, dof)]
    return values


def _outer_ring_nodes(nodes: np.ndarray) -> np.ndarray:
    radii = np.linalg.norm(nodes[:, :2], axis=1)
    return np.flatnonzero(np.isclose(radii, np.max(radii)))


def _relative(value: object, reference: object) -> float:
    return abs(float(value) - float(reference)) / max(abs(float(reference)), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _equal(identifier: str, value: object, expected: object) -> dict[str, object]:
    return {"id": identifier, "value": value, "expected": expected, "status": "PASS" if value == expected else "FAIL"}
