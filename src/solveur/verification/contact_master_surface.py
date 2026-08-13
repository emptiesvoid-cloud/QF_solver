"""V&V for bounded initial selection on a multi-facet contact master surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


class MasterSurfaceContactCampaign:
    """Verify initial selection and bounded updated switching on two faces."""

    campaign_id = "VNV-CONTACT-MASTER-SURFACE-005"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        """Solve the closed-form normal-contact problem and write evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(_model_data()))
        row = cast(dict[str, object], cast(list[object], result.solver["contact"]["contacts"])[0])
        slave_uz = float(result.displacements[result.dofs.index(4, "UZ")])
        checks = _checks(row, slave_uz)
        updated = LinearStaticSolver().solve(JsonModelReader().from_dict(_updated_model_data()))
        updated_row = cast(dict[str, object], cast(list[object], updated.solver["contact"]["contacts"])[0])
        updated_checks = _updated_checks(updated, updated_row)
        checks.extend(updated_checks)
        folded = LinearStaticSolver().solve(JsonModelReader().from_dict(_folded_updated_model_data()))
        folded_row = cast(dict[str, object], cast(list[object], folded.solver["contact"]["contacts"])[0])
        folded_checks = _folded_updated_checks(folded, folded_row)
        checks.extend(folded_checks)
        patch = LinearStaticSolver().solve(JsonModelReader().from_dict(_folded_slave_patch_model_data()))
        patch_rows = cast(list[dict[str, object]], patch.solver["contact"]["contacts"])
        checks.extend(_folded_slave_patch_checks(patch, patch_rows))
        status = "PASS_INTERNAL" if all(check["status"] == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "linear_static_node_to_bounded_master_surface_with_optional_updated_search",
            "reference": {
                "kind": "closed_form_spring_contact_with_initial_facet_selection",
                "faces": [[0, 1, 2], [1, 3, 2]],
                "selected_face_index": 1,
                "selected_master_nodes": [1, 3, 2],
                "initial_gap_m": 0.1,
                "normal_load_n": 200.0,
                "slave_stiffness_n_per_m": 1000.0,
            },
            "results": {
                "selected_face_index": int(cast(int, row["master_face_index"])),
                "selected_master_nodes": list(cast(list[int], row["master_nodes"])),
                "gap_m": float(cast(float, row["gap"])),
                "pressure_n": float(cast(float, row["pressure"])),
                "slave_uz_m": slave_uz,
            },
            "updated_switch": {
                "initial_face_index": 0,
                "selected_face_index": int(cast(int, updated_row["master_face_index"])),
                "slave_ux_m": float(updated.displacements[updated.dofs.index(4, "UX")]),
                "gap_m": float(cast(float, updated_row["gap"])),
                "search_iteration_count": int(cast(int, updated.solver["contact"]["search_iteration_count"])),
            },
            "folded_updated_switch": {
                "initial_face_index": 0,
                "selected_face_index": int(cast(int, folded_row["master_face_index"])),
                "slave_displacement_m": [
                    float(folded.displacements[folded.dofs.index(4, dof)]) for dof in ("UX", "UY", "UZ")
                ],
                "normal": list(cast(list[float], folded_row["normal"])),
                "gap_m": float(cast(float, folded_row["gap"])),
                "search_iteration_count": int(cast(int, folded.solver["contact"]["search_iteration_count"])),
            },
            "folded_slave_patch": {
                "selected_face_indices": [int(cast(int, row["master_face_index"])) for row in patch_rows],
                "mean_displacement_m": [
                    float(np.mean([patch.displacements[patch.dofs.index(node, dof)] for node in (4, 5, 6)]))
                    for dof in ("UX", "UY", "UZ")
                ],
                "max_gap_m": max(abs(float(cast(float, row["gap"]))) for row in patch_rows),
                "search_iteration_count": int(cast(int, patch.solver["contact"]["search_iteration_count"])),
            },
            "checks": checks,
            "artifacts": [
                "master_surface_selection.png",
                "master_surface_updated_switch.png",
                "master_surface_folded_updated_switch.png",
            ],
            "limitations": [
                "Updated search is a bounded fixed-point iteration with small translations and frozen material stiffness.",
                "The study proves one slave on planar and folded two-triangle surfaces, not general surface-to-surface contact.",
                "Large sliding, changing topology and frictional multi-facet correlation remain outside scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        _plot(self.output_dir / "master_surface_selection.png", np.asarray(_model_data()["nodes"], dtype=float))
        _plot_updated(self.output_dir / "master_surface_updated_switch.png")
        _plot_folded_updated(self.output_dir / "master_surface_folded_updated_switch.png")
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary


def _checks(row: dict[str, object], slave_uz: float) -> list[dict[str, float | int | str]]:
    values = (
        ("selected_face_index", float(abs(int(cast(int, row["master_face_index"])) - 1)), 0.0),
        ("closed_normal_gap", abs(float(cast(float, row["gap"]))), 1.0e-12),
        ("contact_pressure", abs(float(cast(float, row["pressure"])) - 100.0), 1.0e-10),
        ("slave_normal_displacement", abs(slave_uz + 0.1), 1.0e-12),
    )
    return [{"id": name, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"} for name, value, limit in values]


def _updated_checks(result: Any, row: dict[str, object]) -> list[dict[str, float | int | str]]:
    values = (
        ("updated_selected_face_index", float(abs(int(cast(int, row["master_face_index"])) - 1)), 0.0),
        ("updated_closed_gap", abs(float(cast(float, row["gap"]))), 1.0e-12),
        ("updated_slave_ux", abs(float(result.displacements[result.dofs.index(4, "UX")]) - 0.6), 1.0e-12),
        ("updated_search_iterations", max(0.0, 2.0 - float(result.solver["contact"]["search_iteration_count"])), 0.0),
    )
    return [{"id": name, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"} for name, value, limit in values]


def _folded_updated_checks(result: Any, row: dict[str, object]) -> list[dict[str, float | int | str]]:
    """Verify a true normal update across a bounded folded master surface."""
    normal = np.asarray(cast(list[float], row["normal"]), dtype=float)
    displacement = np.array([result.displacements[result.dofs.index(4, dof)] for dof in ("UX", "UY", "UZ")])
    final = np.asarray(_folded_updated_model_data()["nodes"], dtype=float)[4] + displacement
    expected_normal = np.array([-0.5, -0.5, 1.0], dtype=float)
    expected_normal /= np.linalg.norm(expected_normal)
    values = (
        ("folded_updated_selected_face_index", float(abs(int(cast(int, row["master_face_index"])) - 1)), 0.0),
        ("folded_updated_closed_gap", abs(float(cast(float, row["gap"]))), 1.0e-12),
        ("folded_updated_normal", float(np.linalg.norm(normal - expected_normal)), 1.0e-12),
        ("folded_updated_surface_compatibility", abs(final[2] - 0.5 * (final[0] + final[1] - 1.0)), 1.0e-12),
        ("folded_updated_search_iterations", max(0.0, 2.0 - float(result.solver["contact"]["search_iteration_count"])), 0.0),
    )
    return [{"id": name, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"} for name, value, limit in values]


def _folded_slave_patch_checks(result: Any, rows: list[dict[str, object]]) -> list[dict[str, float | int | str]]:
    """Verify that a three-node slave patch relocates coherently to one facet."""
    normal = np.array([-0.5, -0.5, 1.0], dtype=float) / np.sqrt(1.5)
    values = (
        ("folded_patch_selected_faces", float(sum(int(cast(int, row["master_face_index"])) != 1 for row in rows)), 0.0),
        ("folded_patch_closed_gap", max(abs(float(cast(float, row["gap"]))) for row in rows), 1.0e-12),
        ("folded_patch_normals", max(float(np.linalg.norm(np.asarray(row["normal"], dtype=float) - normal)) for row in rows), 1.0e-12),
        ("folded_patch_search_iterations", max(0.0, 2.0 - float(result.solver["contact"]["search_iteration_count"])), 0.0),
    )
    return [{"id": name, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"} for name, value, limit in values]


def _model_data() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0], [0.75, 0.5, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
            {"node": 4, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "surface", "slave_node": 4, "master_faces": [[0, 1, 2], [1, 3, 2]]}],
    }


def _updated_model_data() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12, "contact_search_mode": "updated", "contact_search_max_iterations": 8},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0], [0.25, 0.5, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [*[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)], {"node": 4, "dofs": ["UY"]}],
        "springs": [{"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 4, "dof": "UX", "value": 600.0}, {"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "updated_surface", "slave_node": 4, "master_faces": [[0, 1, 2], [1, 3, 2]]}],
    }


def _folded_updated_model_data() -> dict[str, object]:
    """Return a two-facet folded surface used to expose a changed normal."""
    return {
        "analysis": {
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 12,
            "contact_search_mode": "updated",
            "contact_search_max_iterations": 8,
        },
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.5], [0.25, 0.5, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
            {"node": 4, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 4, "dof": "UX", "value": 600.0}, {"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "folded_updated_surface", "slave_node": 4, "master_faces": [[0, 1, 2], [1, 3, 2]]}],
    }


def _folded_slave_patch_model_data() -> dict[str, object]:
    """Return a three-node slave patch for the later surface-contact oracle."""
    nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.5]]
    nodes.extend([[0.2, 0.45, 0.1], [0.3, 0.45, 0.1], [0.25, 0.55, 0.1]])
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12, "contact_search_mode": "updated", "contact_search_max_iterations": 8},
        "nodes": nodes, "elements": [], "materials": {},
        "fixed_dofs": [*[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)], *[{"node": node, "dofs": ["UY"]} for node in range(4, 7)]],
        "springs": [{"node_a": node, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0 / 3.0] * 3} for node in range(4, 7)],
        "loads": [item for node in range(4, 7) for item in ({"node": node, "dof": "UX", "value": 200.0}, {"node": node, "dof": "UZ", "value": -200.0 / 3.0})],
        "contacts": [{"name": f"folded_patch_{node}", "slave_node": node, "master_faces": [[0, 1, 2], [1, 3, 2]]} for node in range(4, 7)],
    }


def _plot(path: Path, nodes: np.ndarray) -> None:
    figure, axis = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
    for face_index, face in enumerate(((0, 1, 2), (1, 3, 2))):
        loop = (*face, face[0])
        color = "#adb5bd" if face_index == 0 else "#0077b6"
        axis.fill(nodes[list(face), 0], nodes[list(face), 1], color=color, alpha=0.2)
        axis.plot(nodes[list(loop), 0], nodes[list(loop), 1], color=color, linewidth=1.5, label=f"face {face_index}")
    axis.scatter(*nodes[4, :2], color="#d00000", s=45, label="slave projection")
    axis.annotate("facette retenue", xy=(0.74, 0.68), xytext=(0.22, 0.78), arrowprops={"arrowstyle": "->"})
    axis.set(xlabel="X [m]", ylabel="Y [m]", title="Selection initiale d'une facette maitre")
    axis.set_aspect("equal", adjustable="box")
    axis.legend(loc="lower left")
    axis.grid(True, alpha=0.25)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_updated(path: Path) -> None:
    figure, axis = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
    nodes = np.asarray(_updated_model_data()["nodes"], dtype=float)
    for face_index, face in enumerate(((0, 1, 2), (1, 3, 2))):
        loop = (*face, face[0])
        color = "#adb5bd" if face_index == 0 else "#0077b6"
        axis.fill(nodes[list(face), 0], nodes[list(face), 1], color=color, alpha=0.2)
        axis.plot(nodes[list(loop), 0], nodes[list(loop), 1], color=color, linewidth=1.5)
    axis.scatter(0.25, 0.5, color="#6c757d", s=45, label="projection initiale (face 0)")
    axis.scatter(0.85, 0.5, color="#d00000", s=45, label="projection actualisee (face 1)")
    axis.annotate("commutation", xy=(0.76, 0.56), xytext=(0.45, 0.78), arrowprops={"arrowstyle": "->"})
    axis.set(xlabel="X [m]", ylabel="Y [m]", title="Recherche actualisee et changement de facette")
    axis.set_aspect("equal", adjustable="box")
    axis.legend(loc="lower left")
    axis.grid(True, alpha=0.25)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_folded_updated(path: Path) -> None:
    """Plot the centre section of the folded surface and the relocalized point."""
    figure, axis = plt.subplots(figsize=(6.6, 4.8), constrained_layout=True)
    axis.plot([0.0, 0.5, 1.0], [0.0, 0.0, 0.25], color="#0077b6", linewidth=2.0, label="surface maitre pliee")
    axis.scatter(0.25, 0.1, color="#6c757d", s=45, label="projection initiale (face 0)")
    axis.scatter(0.74, 0.12, color="#d00000", s=45, label="projection actualisee (face 1)")
    axis.annotate("normale actualisee", xy=(0.74, 0.12), xytext=(0.42, 0.31), arrowprops={"arrowstyle": "->"})
    axis.set(xlabel="X [m] a Y=0.5 m", ylabel="Z [m]", title="Recherche actualisee sur surface maitre pliee")
    axis.legend(loc="upper left")
    axis.grid(True, alpha=0.25)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V&V selection de surface maitre multi-facettes",
            "",
            f"- Etude : `{summary['campaign_id']}`",
            f"- Verdict interne : `{summary['status']}`",
            "",
            "La projection initiale de l'esclave appartient seulement a la seconde des deux faces adjacentes. Le solveur retient donc cette facette avant l'iteration active-set.",
            "",
            "| Grandeur | Valeur | Reference |",
            "| --- | ---: | ---: |",
            f"| Face selectionnee | {summary['results']['selected_face_index']} | 1 |",
            f"| Gap [m] | {summary['results']['gap_m']:.3e} | 0 |",
            f"| Pression [N] | {summary['results']['pressure_n']:.12g} | 100 |",
            f"| UZ esclave [m] | {summary['results']['slave_uz_m']:.12g} | -0.1 |",
            "",
            "![Selection initiale](master_surface_selection.png)",
            "",
            "## Recherche actualisee",
            "",
            f"L'esclave passe de la face 0 a la face {summary['updated_switch']['selected_face_index']} sous une translation X de {summary['updated_switch']['slave_ux_m']:.6g} m. La boucle geometrique converge en {summary['updated_switch']['search_iteration_count']} iterations.",
            "",
            "![Changement de facette](master_surface_updated_switch.png)",
            "",
            "## Normale actualisee sur surface pliee",
            "",
            f"Sur deux facettes non coplanaires, l'esclave finit sur la face {summary['folded_updated_switch']['selected_face_index']} avec la normale {summary['folded_updated_switch']['normal']}. Le gap reste nul et la position finale satisfait le plan de la seconde facette.",
            "",
            "![Surface pliee](master_surface_folded_updated_switch.png)",
            "",
            "Cette preuve ne qualifie pas le grand glissement ou le contact surface-surface. La recherche reste une iteration bornee de petites translations sans frottement.",
            "",
        ]
    )
