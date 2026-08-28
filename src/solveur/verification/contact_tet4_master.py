"""V&V of a bounded frictionless contact against a deformable TET4 face."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class Tet4MasterCheck:
    """One scalar acceptance criterion for the deformable-face study."""

    name: str
    value: float
    limit: float
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Tet4MasterContactCampaign:
    """Compare contact response against a separately measured TET4 compliance."""

    campaign_id = "VNV-CONTACT-TET4-MASTER-FACE-004"
    _weights = np.array([0.5, 0.25, 0.25])
    _slave_stiffness = 1000.0
    _load = 200.0
    _gap = 0.1

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        """Run reference and coupled solves, then write V&V evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        reference = LinearStaticSolver().solve(JsonModelReader().from_dict(_reference_model(self._weights)))
        reference_u = np.asarray(reference.displacements, dtype=float).reshape(-1, 3)
        master_unit_z = reference_u[:3, 2]
        compliance = -float(self._weights @ master_unit_z)
        pressure = self._analytic_pressure(compliance)
        coupled = LinearStaticSolver().solve(JsonModelReader().from_dict(_contact_model()))
        contact = cast(dict[str, object], coupled.solver["contact"])["contacts"]
        row = cast(dict[str, object], cast(list[object], contact)[0])
        displacement = np.asarray(coupled.displacements, dtype=float).reshape(-1, 3)
        expected_slave = (-self._load + pressure) / self._slave_stiffness
        expected_master = pressure * master_unit_z
        checks = self._checks(row, displacement, pressure, expected_slave, expected_master)
        status = "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "linear_static_node_triangle_deformable_tet4_master_face",
            "reference": {
                "kind": "separate_linear_tet4_compliance",
                "unit_load_distribution": self._weights.tolist(),
                "master_normal_compliance_m_per_n": compliance,
                "slave_stiffness_n_per_m": self._slave_stiffness,
                "normal_load_n": self._load,
                "initial_gap_m": self._gap,
            },
            "results": {
                "pressure_n": float(cast(float, row["pressure"])),
                "gap_m": float(cast(float, row["gap"])),
                "slave_uz_m": float(displacement[4, 2]),
                "master_uz_m": displacement[:3, 2].tolist(),
            },
            "reference_solution": {
                "pressure_n": pressure,
                "slave_uz_m": expected_slave,
                "master_uz_m": expected_master.tolist(),
            },
            "checks": [check.to_dict() for check in checks],
            "artifacts": ["tet4_master_deformation.png"],
            "limitations": [
                "The master is one planar TET4 boundary face with fixed tangential directions.",
                "The normal and barycentric coordinates are frozen in the initial configuration.",
                "General deformable surfaces, surface-to-surface search, large sliding and external correlation remain open.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_deformation(np.asarray(cast(list[list[float]], _contact_model()["nodes"]), dtype=float), displacement)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    def _plot_deformation(self, nodes: np.ndarray, displacement: np.ndarray) -> None:
        """Write a compact geometry/deformation figure for Owner review."""
        scale = 12.0
        current = nodes + scale * displacement
        figure = plt.figure(figsize=(7.2, 5.0), constrained_layout=True)
        axis = figure.add_subplot(111, projection="3d")
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        for coordinates, color, label in ((nodes, "#6c757d", "initial"), (current, "#0077b6", "deformed x12")):
            for first, second in edges:
                axis.plot(*coordinates[[first, second]].T, color=color, linewidth=1.0, alpha=0.8)
            face = coordinates[[0, 1, 2, 0]]
            axis.plot(*face.T, color=color, linewidth=1.5)
            axis.scatter(*coordinates[:4].T, color=color, s=16, label=label)
        axis.scatter(*current[4], color="#d00000", s=42, label="slave")
        axis.plot(*np.vstack((nodes[4], current[4])).T, color="#d00000", linestyle="--", linewidth=1.1)
        axis.set(
            xlabel="X [m]",
            ylabel="Y [m]",
            zlabel="Z [m]",
            title="Face maitre TET4 deformable - contact ferme",
        )
        axis.set_box_aspect((1.0, 1.0, 1.1))
        axis.legend(loc="upper left")
        figure.savefig(self.output_dir / "tet4_master_deformation.png", dpi=180)
        plt.close(figure)

    def _analytic_pressure(self, master_compliance: float) -> float:
        return (self._load / self._slave_stiffness - self._gap) / (1.0 / self._slave_stiffness + master_compliance)

    @staticmethod
    def _checks(
        row: dict[str, object], displacement: np.ndarray, pressure: float, expected_slave: float, expected_master: np.ndarray
    ) -> list[Tet4MasterCheck]:
        values = (
            ("normal gap", abs(float(cast(float, row["gap"]))), 1.0e-12),
            ("contact pressure", abs(float(cast(float, row["pressure"])) - pressure), 1.0e-10),
            ("slave normal displacement", abs(float(displacement[4, 2]) - expected_slave), 1.0e-12),
            ("master face displacement", float(np.max(np.abs(displacement[:3, 2] - expected_master))), 1.0e-12),
        )
        return [Tet4MasterCheck(name, value, limit, "PASS" if value <= limit else "FAIL") for name, value, limit in values]


def _base_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.25, 0.25, -1.0]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "elastic"}],
        "materials": {"elastic": {"type": "isotropic_3d", "E": 100000.0, "nu": 0.3}},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY"]} for node in range(3)],
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
    }


def _reference_model(weights: np.ndarray) -> dict[str, object]:
    model = _base_model()
    model["loads"] = [{"node": index, "dof": "UZ", "value": float(-weight)} for index, weight in enumerate(weights)]
    return model


def _contact_model() -> dict[str, object]:
    model = _base_model()
    nodes = cast(list[list[float]], model["nodes"])
    nodes.append([0.25, 0.25, 0.1])
    fixed = cast(list[dict[str, object]], model["fixed_dofs"])
    fixed.append({"node": 4, "dofs": ["UX", "UY"]})
    model["springs"] = [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}]
    model["loads"] = [{"node": 4, "dof": "UZ", "value": -200.0}]
    model["contacts"] = [{"name": "tet4_master", "slave_node": 4, "master_nodes": [0, 2, 1]}]
    return model


def _markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V&V contact sur face maitre TET4 deformable",
            "",
            f"- Etude : `{summary['campaign_id']}`",
            f"- Verdict interne : `{summary['status']}`",
            "",
            "La compliance de la face est mesuree par une resolution lineaire distincte sous une charge unitaire repartie selon les poids barycentriques.",
            "",
            "$$ p = \\frac{F/k_s-g_0}{1/k_s+c_m}. $$",
            "",
            "| Grandeur | QF_solver | Reference par compliance | Ecart |",
            "| --- | ---: | ---: | ---: |",
            f"| Pression [N] | {summary['results']['pressure_n']:.12g} | {summary['reference_solution']['pressure_n']:.12g} | {summary['checks'][1]['value']:.3e} |",
            f"| Gap [m] | {summary['results']['gap_m']:.12g} | 0 | {summary['checks'][0]['value']:.3e} |",
            f"| Deplacement esclave Z [m] | {summary['results']['slave_uz_m']:.12g} | {summary['reference_solution']['slave_uz_m']:.12g} | {summary['checks'][2]['value']:.3e} |",
            "",
            "La preuve couvre une face TET4 plane et des mouvements normaux. Elle ne qualifie pas une recherche de surface generale ni les grandes transformations.",
            "",
            "![Geometrie et deformee](tet4_master_deformation.png)",
            "",
        ]
    )
