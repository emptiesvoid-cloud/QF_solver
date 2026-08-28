"""Survey three frictional-contact geometries without promoting the scope."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.contact_additional_models import (
    _deformable_tet4_two_slaves,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class FrictionalContactFamilySurvey:
    """Run one controlled frictional case for each of three geometry families."""

    campaign_id = "VNV-CONTACT-FRICTION-FAMILIES-004"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        families = [
            self._run_family("dual_stop_corner", self._build_dual, self._prepare_dual),
            self._run_family("faceted_ramp_patch", self._build_ramp, self._prepare_ramp),
            self._run_family("deformable_tet4_two_slaves", self._build_tet4, self._prepare_tet4),
        ]
        checks = self._checks(families)
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "geometry_family_count": len(families),
            "families": {family["id"]: family for family in families},
            "checks": checks,
            "mesh_policy": {
                "mesh_level_count_per_family": min(family["mesh_level_count"] for family in families),
                "required_for_promotion": 3,
                "status": "PASS_INTERNAL" if all(family["mesh_level_count"] >= 3 for family in families) else "INCOMPLETE_FOR_PROMOTION",
            },
            "limitations": [
                "The survey does not prove surface-to-surface contact, large sliding or dynamic contact.",
                "External correlation remains limited to the separately archived controlled slip case.",
            ],
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self._plot([family["levels"][-1] for family in families])
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    @staticmethod
    def _run_family(
        family_id: str,
        builder: Callable[[int], dict[str, Any]],
        preparer: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        levels = [
            FrictionalContactFamilySurvey._solve_case(
                f"{family_id}-L{level}", builder(level), preparer
            )
            for level in (1, 2, 3)
        ]
        return {
            "id": family_id,
            "mesh_level_count": len(levels),
            "levels": levels,
            "states": sorted({state for level in levels for state in level["states"]}),
            "maximum_abs_gap_m": max(level["maximum_abs_gap_m"] for level in levels),
            "maximum_cone_excess_n": max(level["maximum_cone_excess_n"] for level in levels),
            "finite_response": all(level["finite_response"] for level in levels),
        }

    @staticmethod
    def _solve_case(
        identifier: str,
        data: dict[str, Any],
        preparer: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        preparer(data)
        model_data = {key: value for key, value in data.items() if not key.startswith("_")}
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(model_data))
        contacts = result.solver["contact"]["contacts"]
        rows = [
            {
                "state": str(contact["tangential_state"]),
                "gap_m": float(contact["gap"]),
                "tangential_force_n": float(contact["tangential_force_norm"]),
                "friction_limit_n": float(contact["friction_limit"]),
            }
            for contact in contacts
        ]
        return {
            "id": identifier,
            "family": identifier.rsplit("-L", 1)[0],
            "mesh_level_count": 1,
            "nodes": len(data["nodes"]),
            "elements": len(data["elements"]),
            "contacts": rows,
            "maximum_abs_gap_m": max(abs(row["gap_m"]) for row in rows),
            "maximum_cone_excess_n": max(
                row["tangential_force_n"] - row["friction_limit_n"] for row in rows
            ),
            "states": sorted({row["state"] for row in rows}),
            "finite_response": bool(np.all(np.isfinite(result.displacements))),
        }

    @staticmethod
    def _build_dual(level: int) -> dict[str, Any]:
        master_triangles = [
            (np.asarray([0.0, 0.0, 0.0]), np.asarray([0.0, 1.0, 0.0]), np.asarray([0.0, 0.0, 1.0])),
            (np.asarray([0.0, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0]), np.asarray([0.0, 1.0, 0.0])),
        ]
        nodes: list[list[float]] = []
        node_lookup: dict[tuple[float, float, float], int] = {}
        face_sets: list[list[list[int]]] = []
        for triangle in master_triangles:
            faces: list[list[int]] = []
            index: dict[tuple[int, int], int] = {}
            for i in range(level + 1):
                for j in range(level + 1 - i):
                    point = (
                        (1.0 - (i + j) / level) * triangle[0]
                        + (i / level) * triangle[1]
                        + (j / level) * triangle[2]
                    )
                    key = tuple(float(value) for value in np.round(point, 12))
                    if key not in node_lookup:
                        node_lookup[key] = len(nodes)
                        nodes.append(point.tolist())
                    index[(i, j)] = node_lookup[key]
            for i in range(level):
                for j in range(level - i):
                    faces.append([index[(i, j)], index[(i + 1, j)], index[(i, j + 1)]])
                    if i + j < level - 1:
                        faces.append([index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]])
            face_sets.append(faces)
        slave = len(nodes)
        nodes.append([0.1, 0.45, 0.1])
        return {
            "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
            "nodes": nodes,
            "elements": [],
            "materials": {},
            "fixed_dofs": [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(slave)]
            + [{"node": slave, "dofs": ["UY"]}],
            "springs": [{"node_a": slave, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0] * 3}],
            "loads": [{"node": slave, "dof": "UX", "value": -200.0}, {"node": slave, "dof": "UZ", "value": -300.0}],
            "contacts": [
                {"name": "stop_x", "slave_node": slave, "master_faces": face_sets[0]},
                {"name": "stop_z", "slave_node": slave, "master_faces": face_sets[1]},
            ],
            "_plot": {"nodes": nodes, "faces": face_sets[0] + face_sets[1], "slaves": [slave], "structural_elements": []},
        }

    @staticmethod
    def _build_ramp(level: int) -> dict[str, Any]:
        nx = 3 * (2 ** (level - 1))
        ny = 2 ** (level - 1)
        nodes: list[list[float]] = []
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = 3.0 * i / nx
                z = float(np.interp(x, [0.0, 1.0, 2.0, 3.0], [0.0, 0.08, 0.25, 0.55]))
                nodes.append([x, j / ny, z])
        faces: list[list[int]] = []
        for j in range(ny):
            for i in range(nx):
                a = j * (nx + 1) + i
                b, c, d = a + 1, a + nx + 1, a + nx + 2
                faces.extend([[a, b, c], [b, d, c]])
        slaves: list[int] = []
        for x, z in ((0.45, 0.20), (1.45, 0.35), (2.45, 0.65)):
            slaves.append(len(nodes))
            nodes.append([x, 0.5, z])
        master_count = len(nodes) - len(slaves)
        return {
            "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
            "nodes": nodes,
            "elements": [],
            "materials": {},
            "fixed_dofs": [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(master_count)]
            + [{"node": node, "dofs": ["UX", "UY"]} for node in slaves],
            "springs": [{"node_a": node, "dofs": ["UZ"], "stiffness": 1200.0} for node in slaves],
            "loads": [{"node": node, "dof": "UZ", "value": -400.0} for node in slaves],
            "contacts": [{"name": f"ramp_{node}", "slave_node": node, "master_faces": faces} for node in slaves],
            "_plot": {"nodes": nodes, "faces": faces, "slaves": slaves, "structural_elements": []},
        }

    @staticmethod
    def _build_tet4(level: int) -> dict[str, Any]:
        sizes = ((4, 4, 4), (6, 4, 4), (8, 8, 8))
        return _deformable_tet4_two_slaves(*sizes[level - 1])

    @staticmethod
    def _prepare_dual(data: dict[str, Any]) -> None:
        for contact in data["contacts"]:
            contact["friction_coefficient"] = 0.4
            contact["tangential_stiffness"] = 100000.0

    @staticmethod
    def _prepare_ramp(data: dict[str, Any]) -> None:
        for contact in data["contacts"]:
            contact["friction_coefficient"] = 0.4
            contact["tangential_stiffness"] = 100000.0
        data["loads"].extend(
            {"node": int(contact["slave_node"]), "dof": "UX", "value": -20.0}
            for contact in data["contacts"]
        )

    @staticmethod
    def _prepare_tet4(data: dict[str, Any]) -> None:
        for contact in data["contacts"]:
            contact["friction_coefficient"] = 0.4
            contact["tangential_stiffness"] = 100000.0
        data["loads"].extend(
            {"node": int(contact["slave_node"]), "dof": "UZ", "value": 200.0}
            for contact in data["contacts"]
        )

    @staticmethod
    def _checks(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
        states = {state for family in families for state in family["states"]}
        levels = [level for family in families for level in family["levels"]]
        return [
            _check("three_geometry_families", len(families), 3, "greater_equal"),
            _check("three_mesh_levels_each", min(family["mesh_level_count"] for family in families), 3, "greater_equal"),
            _check("finite_response", all(level["finite_response"] for level in levels), True, "equals"),
            _check("maximum_gap", max(level["maximum_abs_gap_m"] for level in levels), 1.0e-9, "less_equal"),
            _check("maximum_coulomb_cone_excess", max(level["maximum_cone_excess_n"] for level in levels), 1.0e-8, "less_equal"),
            _check("stick_or_slip_only", states.issubset({"stick", "slip"}), True, "equals"),
            _check("sliding_branch_exercised", "slip" in states, True, "equals"),
        ]

    def _plot(self, cases: list[dict[str, Any]]) -> None:
        figure, axis = plt.subplots(figsize=(7.5, 4.2), constrained_layout=True)
        labels = [case["id"].replace("_", " ") for case in cases]
        forces = [max(row["tangential_force_n"] for row in case["contacts"]) for case in cases]
        limits = [max(row["friction_limit_n"] for row in case["contacts"]) for case in cases]
        x = np.arange(len(cases))
        axis.bar(x - 0.18, forces, 0.36, color="#007c91", label="|t|")
        axis.bar(x + 0.18, limits, 0.36, color="#d1495b", label="mu p")
        axis.set_xticks(x, labels, rotation=15, ha="right")
        axis.set_ylabel("Effort tangent [N]")
        axis.set_title("Diversite des familles de contact frottant")
        axis.grid(axis="y", alpha=0.3)
        axis.legend()
        figure.savefig(self.output_dir / "frictional_contact_family_survey.png", dpi=170)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [
            f"# {summary['campaign_id']}",
            "",
            f"Statut interne : **{summary['status']}**.",
            "",
            "| Famille | Niveaux | Noeuds au niveau fin | Elements au niveau fin | Contacts | Etats | Gap max [m] | Cone max [N] |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
        ]
        for family in summary["families"].values():
            final = family["levels"][-1]
            lines.append(
                f"| {family['id']} | {family['mesh_level_count']} | {final['nodes']} | {final['elements']} | "
                f"{len(final['contacts'])} | {', '.join(family['states'])} | {family['maximum_abs_gap_m']:.3e} | "
                f"{family['maximum_cone_excess_n']:.3e} |"
            )
        lines.extend(
            [
                "",
                "![Survey contact frottant](frictional_contact_family_survey.png)",
                "",
                "Chaque famille comporte trois niveaux de maillage. Cette preuve "
                "interne ne ferme pas la decision Owner ni les limites surface-surface, "
                "grand glissement et dynamique.",
                "",
            ]
        )
        return "\n".join(lines)


def _check(name: str, value: object, limit: object, operation: str) -> dict[str, object]:
    if operation == "greater_equal":
        passed = bool(value >= limit)
    elif operation == "less_equal":
        passed = bool(value <= limit)
    else:
        passed = value == limit
    return {"name": name, "value": value, "limit": limit, "operation": operation, "status": "PASS" if passed else "FAIL"}
