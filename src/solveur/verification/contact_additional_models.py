"""Additional bounded contact models requested by the Owner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest


class AdditionalContactModelsCampaign:
    """Verify three geometrically distinct models inside the bounded V1 scope."""

    campaign_id = "VNV-CONTACT-ADDITIONAL-MODELS-008"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        cases = [
            self._solve_case("dual_stop_corner", _dual_stop_corner()),
            self._solve_case("faceted_ramp_patch", _faceted_ramp_patch()),
            self._solve_case("deformable_tet4_two_slaves", _deformable_tet4_two_slaves()),
        ]
        checks = [check for case in cases for check in case["checks"]]
        status = "PASS_INTERNAL" if all(check["status"] == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental_ready_for_human_recheck",
            "cases": cases,
            "checks": checks,
            "limitations": [
                "The three models remain small-displacement node-to-triangle contact.",
                "They do not demonstrate general surface-to-surface or large-sliding contact.",
                "The external Code_Aster evidence remains provided by the preceding controlled campaigns.",
            ],
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._plot(cases)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    @staticmethod
    def _solve_case(identifier: str, data: dict[str, object]) -> dict[str, Any]:
        model_data = {key: value for key, value in data.items() if not key.startswith("_")}
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(model_data))
        contacts = cast(list[dict[str, object]], result.solver["contact"]["contacts"])
        displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
        gaps = np.asarray([float(row["gap"]) for row in contacts])
        pressures = np.asarray([float(row["pressure"]) for row in contacts])
        active = np.asarray([bool(row["active"]) for row in contacts])
        checks = [
            _upper(identifier, "maximum_abs_gap", float(np.max(np.abs(gaps))), 1.0e-9),
            _upper(identifier, "inactive_contact_count", float(np.count_nonzero(~active)), 0.0),
            _lower(identifier, "minimum_pressure", float(np.min(pressures)), 0.0),
            _upper(
                identifier,
                "active_set_iterations",
                float(len(cast(list[object], result.solver["contact"]["history"]))),
                5.0,
            ),
        ]
        expected = cast(dict[str, object], data["_expected"])
        for node, target in cast(list[tuple[int, list[float | None]]], expected["positions"]):
            initial = np.asarray(cast(list[list[float]], data["nodes"])[node], dtype=float)
            final = initial + displacement[node]
            for component, value in enumerate(target):
                if value is not None:
                    checks.append(
                        _upper(
                            identifier,
                            f"node_{node}_component_{component}",
                            abs(float(final[component]) - float(value)),
                            1.0e-9,
                        )
                    )
        return {
            "id": identifier,
            "nodes": len(cast(list[object], data["nodes"])),
            "elements": len(cast(list[object], data["elements"])),
            "contacts": len(contacts),
            "gaps_m": gaps.tolist(),
            "pressures_n": pressures.tolist(),
            "selected_faces": [int(cast(int, row["master_face_index"])) for row in contacts],
            "max_displacement_m": float(np.max(np.linalg.norm(displacement, axis=1))),
            "checks": checks,
            "plot": cast(dict[str, object], data["_plot"]),
            "final_nodes": (np.asarray(data["nodes"], dtype=float) + displacement).tolist(),
        }

    def _plot(self, cases: list[dict[str, Any]]) -> None:
        figure = plt.figure(figsize=(12.0, 4.2), constrained_layout=True)
        for index, case in enumerate(cases, start=1):
            axis = figure.add_subplot(1, 3, index, projection="3d")
            plot = case["plot"]
            initial = np.asarray(plot["nodes"], dtype=float)
            final = np.asarray(case["final_nodes"], dtype=float)
            for face in plot["faces"]:
                loop = [*face, face[0]]
                axis.plot(*initial[loop].T, color="#57666d", linewidth=1.0)
            structural = np.asarray(plot["structural_elements"], dtype=int)
            if structural.size:
                edges = _unique_edges(structural)
                for left, right in edges[:: max(1, len(edges) // 350)]:
                    axis.plot(*initial[[left, right]].T, color="#9aa4a9", linewidth=0.25, alpha=0.35)
                    axis.plot(*final[[left, right]].T, color="#007c91", linewidth=0.35, alpha=0.45)
            slaves = np.asarray(plot["slaves"], dtype=int)
            axis.scatter(*initial[slaves].T, color="#d1495b", s=18, label="initial")
            axis.scatter(*final[slaves].T, color="#007c91", s=20, label="final")
            axis.set_title(str(case["id"]).replace("_", " "), fontsize=9)
            axis.set(xlabel="X", ylabel="Y", zlabel="Z")
            axis.legend(fontsize=7)
        figure.savefig(self.output_dir / "additional_contact_models.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [
            "# Trois modeles contact complementaires",
            "",
            f"Verdict : **{summary['status']}**.",
            "",
            "| Modele | Noeuds | TET4 | Contacts | Gap max | Pression min |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for case in summary["cases"]:
            lines.append(
                f"| {case['id']} | {case['nodes']} | {case['elements']} | {case['contacts']} | "
                f"{max(abs(value) for value in case['gaps_m']):.3e} | {min(case['pressures_n']):.6g} |"
            )
        lines.extend(
            [
                "",
                "![Modeles contact complementaires](additional_contact_models.png)",
                "",
                "Ces cas etendent la diversite geometrique dans le domaine V1 borne. "
                "Ils ne qualifient pas le grand glissement ou le contact surface-surface general.",
                "",
            ]
        )
        return "\n".join(lines)


def _dual_stop_corner() -> dict[str, object]:
    nodes = [
        [0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 0.0],
        [0.1, 0.45, 0.1],
    ]
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": nodes,
        "elements": [],
        "materials": {},
        "fixed_dofs": [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)]
        + [{"node": 4, "dofs": ["UY"]}],
        "springs": [{"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0] * 3}],
        "loads": [{"node": 4, "dof": "UX", "value": -200.0}, {"node": 4, "dof": "UZ", "value": -300.0}],
        "contacts": [
            {"name": "stop_x", "slave_node": 4, "master_nodes": [0, 1, 2]},
            {"name": "stop_z", "slave_node": 4, "master_nodes": [0, 3, 1]},
        ],
        "_expected": {"positions": [(4, [0.0, None, 0.0])]},
        "_plot": {"nodes": nodes, "faces": [[0, 1, 2], [0, 3, 1]], "slaves": [4], "structural_elements": []},
    }


def _faceted_ramp_patch() -> dict[str, object]:
    nodes = [
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.08], [2.0, 0.0, 0.25], [3.0, 0.0, 0.55],
        [0.0, 1.0, 0.0], [1.0, 1.0, 0.08], [2.0, 1.0, 0.25], [3.0, 1.0, 0.55],
        [0.45, 0.5, 0.20], [1.45, 0.5, 0.35], [2.45, 0.5, 0.65],
    ]
    faces = [[0, 1, 4], [1, 5, 4], [1, 2, 5], [2, 6, 5], [2, 3, 6], [3, 7, 6]]
    slaves = [8, 9, 10]
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": nodes, "elements": [], "materials": {},
        "fixed_dofs": [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(8)]
        + [{"node": node, "dofs": ["UX", "UY"]} for node in slaves],
        "springs": [{"node_a": node, "dofs": ["UZ"], "stiffness": 1200.0} for node in slaves],
        "loads": [{"node": node, "dof": "UZ", "value": -400.0} for node in slaves],
        "contacts": [{"name": f"ramp_{node}", "slave_node": node, "master_faces": faces} for node in slaves],
        "_expected": {"positions": []},
        "_plot": {"nodes": nodes, "faces": faces, "slaves": slaves, "structural_elements": []},
    }


def _deformable_tet4_two_slaves(
    nx: int = 6,
    ny: int = 4,
    nz: int = 4,
) -> dict[str, object]:
    nodes, elements = _structured_tet4_mesh(nx, ny, nz, 1.0, 1.0, 1.0)
    nodes[:, 0] += 0.1
    structural_count = len(nodes)
    master = np.array([[0.0, -1.0, -1.0], [0.0, 3.0, -1.0], [0.0, -1.0, 3.0]])
    nodes = np.vstack((nodes, master))
    slaves = [
        int(np.flatnonzero(np.all(np.isclose(nodes[:structural_count], [0.1, -0.25, -0.25]), axis=1))[0]),
        int(np.flatnonzero(np.all(np.isclose(nodes[:structural_count], [0.1, 0.25, 0.25]), axis=1))[0]),
    ]
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if index >= structural_count or np.isclose(point[0], 1.1)
    ]
    data: dict[str, object] = {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 20},
        "nodes": nodes.tolist(),
        "elements": [{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        "materials": {"solid": {"type": "isotropic_3d", "E": 1.0e4, "nu": 0.3}},
        "fixed_dofs": fixed,
        "loads": [{"node": node, "dof": "UX", "value": -2000.0} for node in slaves],
        "contacts": [
            {
                "name": f"two_slave_{node}",
                "slave_node": node,
                "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
            }
            for node in slaves
        ],
        "_expected": {"positions": [(node, [0.0, None, None]) for node in slaves]},
        "_plot": {
            "nodes": nodes.tolist(),
            "faces": [[structural_count, structural_count + 1, structural_count + 2]],
            "slaves": slaves,
            "structural_elements": elements.tolist(),
        },
    }
    return data


def _unique_edges(elements: np.ndarray) -> list[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for cell in elements:
        for left, right in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
            edge = tuple(sorted((int(cell[left]), int(cell[right]))))
            edges.add(edge)
    return sorted(edges)


def _upper(case: str, name: str, value: float, limit: float) -> dict[str, object]:
    return {"id": f"{case}:{name}", "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _lower(case: str, name: str, value: float, limit: float) -> dict[str, object]:
    return {"id": f"{case}:{name}", "value": value, "limit": limit, "status": "PASS" if value >= limit else "FAIL"}
