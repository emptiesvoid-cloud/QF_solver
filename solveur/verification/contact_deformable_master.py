"""Bounded V&V study for a frictionless contact with elastic master nodes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class DeformableMasterCheck:
    """One scalar criterion for the elastic-master contact study."""

    name: str
    value: float
    limit: float
    status: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class DeformableMasterContactCampaign:
    """Verify barycentric master displacement in the exact normal-gap equation."""

    campaign_id = "VNV-CONTACT-DEFORMABLE-MASTER-003"
    _slave_stiffness = 1000.0
    _master_stiffness = 600.0
    _load = 200.0
    _initial_gap = 0.1
    _weights = np.array([0.5, 0.25, 0.25])

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        """Solve the controlled contact pair and write reviewable evidence."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(_model_data()))
        contact = result.solver["contact"]["contacts"][0]
        displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
        pressure = self._analytic_pressure()
        expected_master = -pressure * self._weights / self._master_stiffness
        expected_slave = (-self._load + pressure) / self._slave_stiffness
        checks = self._checks(contact, displacement, pressure, expected_master, expected_slave)
        status = "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "linear_static_node_triangle_elastic_master_nodes",
            "reference": {
                "kind": "closed_form_spring_contact",
                "slave_stiffness_n_per_m": self._slave_stiffness,
                "master_node_stiffness_n_per_m": self._master_stiffness,
                "normal_load_n": self._load,
                "initial_gap_m": self._initial_gap,
                "barycentric_weights": self._weights.tolist(),
            },
            "results": {
                "pressure_n": float(contact["pressure"]),
                "gap_m": float(contact["gap"]),
                "slave_uz_m": float(displacement[3, 2]),
                "master_uz_m": displacement[:3, 2].tolist(),
            },
            "analytic": {
                "pressure_n": pressure,
                "slave_uz_m": expected_slave,
                "master_uz_m": expected_master.tolist(),
            },
            "checks": [check.to_dict() for check in checks],
            "limitations": [
                "The master triangle is represented by three elastic nodal supports, not a general finite-element surface.",
                "The normal and barycentric coordinates are frozen in the initial configuration.",
                "Surface-to-surface contact, large sliding, changing normals and external correlation remain open.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    def _analytic_pressure(self) -> float:
        compliance = 1.0 / self._slave_stiffness + float(self._weights @ self._weights) / self._master_stiffness
        return (self._load / self._slave_stiffness - self._initial_gap) / compliance

    @staticmethod
    def _checks(
        contact: dict[str, object], displacement: np.ndarray, pressure: float, expected_master: np.ndarray, expected_slave: float
    ) -> list[DeformableMasterCheck]:
        gap = float(cast(float, contact["gap"]))
        observed_pressure = float(cast(float, contact["pressure"]))
        values = (
            ("normal gap", abs(gap), 1.0e-12),
            ("contact pressure", abs(observed_pressure - pressure), 1.0e-10),
            ("slave normal displacement", abs(float(displacement[3, 2]) - expected_slave), 1.0e-12),
            ("master barycentric displacement", float(np.max(np.abs(displacement[:3, 2] - expected_master))), 1.0e-12),
        )
        return [DeformableMasterCheck(name, value, limit, "PASS" if value <= limit else "FAIL") for name, value, limit in values]


def _model_data() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "springs": [
            {"node_a": node, "dofs": ["UX", "UY", "UZ"], "stiffness": [600.0, 600.0, 600.0]}
            for node in range(3)
        ] + [{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 3, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "elastic_master", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# V&V contact avec triangle maitre elastique",
        "",
        f"- Etude : `{summary['campaign_id']}`",
        f"- Verdict interne : `{summary['status']}`",
        "- Domaine : `linear_static_node_triangle_elastic_master_nodes`",
        "",
        "Le gap utilise le deplacement barycentrique du maitre :",
        "",
        "$$ g = g_0 + u_{s,z} - \\sum_i b_i u_{i,z}. $$",
        "",
        "| Grandeur | QF_solver | Analytique | Ecart |",
        "| --- | ---: | ---: | ---: |",
        f"| Pression [N] | {summary['results']['pressure_n']:.12g} | {summary['analytic']['pressure_n']:.12g} | {summary['checks'][1]['value']:.3e} |",
        f"| Gap [m] | {summary['results']['gap_m']:.12g} | 0 | {summary['checks'][0]['value']:.3e} |",
        f"| Deplacement esclave Z [m] | {summary['results']['slave_uz_m']:.12g} | {summary['analytic']['slave_uz_m']:.12g} | {summary['checks'][2]['value']:.3e} |",
        "",
        "Les trois noeuds maitres sont elastiques. Cette etude ne prouve pas encore une face EF deformable generalisee.",
        "",
    ]
    return "\n".join(lines)
