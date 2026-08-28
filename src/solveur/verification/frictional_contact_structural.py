"""TET4 mesh-refinement evidence for a strongly coupled frictional contact."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class FrictionalStructuralContactCheck:
    """One scalar acceptance check for the spatial friction campaign."""

    name: str
    value: float
    limit: float
    status: str
    criterion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FrictionalStructuralContactCampaign:
    """Refine a deformable TET4 bar with a normal load and saturated sliding."""

    campaign_id = "VNV-CONTACT-FRICTION-TET4-STRUCTURAL-002"
    levels = FrictionlessStructuralContactCampaign.levels

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._solve_level(*cells) for cells in self.levels]
        checks = self._checks(rows)
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_tet4_node_triangle_regularized_coulomb",
            "reference": {
                "kind": "internal_mesh_refinement",
                "description": "Deformable TET4 bar on one rigid triangle with normal and tangential load.",
                "normal_load": -4000.0,
                "tangential_load": 1500.0,
                "friction_coefficient": 0.4,
                "tangential_stiffness": 100000.0,
            },
            "levels": rows,
            "checks": [check.to_dict() for check in checks],
            "limitations": [
                "This is node-to-triangle contact with frozen initial normal and small transformations.",
                "The root fallback is an internal nonlinear robustness measure, not an external correlation.",
                "Surface-to-surface contact, large sliding, rate dependence and thermal effects remain outside scope.",
            ],
        }
        (self.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._plot(rows)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    @staticmethod
    def _solve_level(nx: int, ny: int, nz: int) -> dict[str, Any]:
        from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh

        nodes, elements = _structured_tet4_mesh(nx, ny, nz, 1.0, 1.0, 1.0)
        nodes[:, 0] += 0.1
        structural_count = len(nodes)
        nodes = np.vstack((nodes, [[0.0, -1.0, -1.0], [0.0, 1.0, -1.0], [0.0, -1.0, 1.0]]))
        slave = FrictionlessStructuralContactCampaign._slave_node(nodes[:structural_count])
        data = FrictionlessStructuralContactCampaign._model_data(nodes, elements, structural_count, slave)
        data["analysis"] = {"type": "linear_static", "method": "direct", "contact_max_iterations": 25}
        data["loads"] = [
            {"node": slave, "dof": "UX", "value": -4000.0},
            {"node": slave, "dof": "UZ", "value": 1500.0},
        ]
        data["contacts"] = [{
            "name": "rough_rigid_plane", "slave_node": slave,
            "master_nodes": [structural_count, structural_count + 1, structural_count + 2],
            "friction_coefficient": 0.4, "tangential_stiffness": 100000.0,
        }]
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
        contact = result.solver["contact"]
        detail = contact["contacts"][0]
        history = contact["history"]
        return {
            "cells": [nx, ny, nz], "nodes": structural_count, "elements": int(len(elements)),
            "dofs": int(result.dofs.ndof), "gap": float(detail["gap"]), "pressure": float(detail["pressure"]),
            "tangential_force_norm": float(detail["tangential_force_norm"]),
            "friction_limit": float(detail["friction_limit"]), "state": str(detail["tangential_state"]),
            "solver_strategy": str(history[-1]["strategy"]),
            "root_evaluations": int(history[-1]["iteration"]),
        }

    @staticmethod
    def _checks(rows: list[dict[str, Any]]) -> list[FrictionalStructuralContactCheck]:
        max_gap = max(abs(float(row["gap"])) for row in rows)
        cone_excess = max(float(row["tangential_force_norm"]) - float(row["friction_limit"]) for row in rows)
        invalid_states = float(sum(str(row["state"]) not in {"stick", "slip"} for row in rows))
        missing_slip = 0.0 if any(str(row["state"]) == "slip" for row in rows) else 1.0
        missing_root = 0.0 if any(str(row["solver_strategy"]) == "active_slip_root" for row in rows) else 1.0
        evaluations = max(float(row["root_evaluations"]) for row in rows)
        return [
            _upper("normal gap", max_gap, 1.0e-10, "maximum absolute gap [m]"),
            _upper("Coulomb cone excess", cone_excess, 1.0e-8, "maximum ||t|| - mu p [N]"),
            _upper("invalid tangential-state count", invalid_states, 0.0, "each level must be stick or slip"),
            _upper("missing sliding branch", missing_slip, 0.0, "at least one level must exercise sliding"),
            _upper("missing active-slip fallback", missing_root, 0.0, "at least one level must exercise the coupled fallback"),
            _upper("root evaluations", evaluations, 100.0, "maximum nonlinear function evaluations"),
        ]

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        elements = np.asarray([row["elements"] for row in rows], dtype=float)
        forces = np.asarray([row["tangential_force_norm"] for row in rows], dtype=float)
        limits = np.asarray([row["friction_limit"] for row in rows], dtype=float)
        figure, axis = plt.subplots(figsize=(7.4, 4.4), constrained_layout=True)
        axis.semilogx(elements, forces, "o-", color="#006d77", label="QF_solver |t|")
        axis.semilogx(elements, limits, "s--", color="#c44536", label="mu p")
        axis.set(xlabel="Nombre de TET4", ylabel="Effort tangent [N]")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend()
        figure.savefig(self.output_dir / "friction_structural_convergence.png", dpi=170)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [
            "# V&V contact avec frottement : raffinement structurel TET4", "",
            f"- Etude : `{summary['campaign_id']}`", f"- Verdict interne : `{summary['status']}`",
            "- Maturite : `experimental`", "",
            "| Maillage | TET4 | Gap [m] | |t| [N] | mu p [N] | Strategie |", "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for row in summary["levels"]:
            lines.append(
                f"| {'x'.join(map(str, row['cells']))} | {row['elements']} | {float(row['gap']):.3e} | "
                f"{float(row['tangential_force_norm']):.6f} | {float(row['friction_limit']):.6f} | {row['solver_strategy']} |"
            )
        lines.extend([
            "", "Le repli actif est trace lorsqu'un niveau atteint le glissement. Un maillage plus fin peut revenir en adherence "
            "si la reaction normale augmente et fait passer la borne mu p au-dessus de la charge tangentielle. Le resultat "
            "confirme la fermeture normale et le cone de Coulomb, mais ne constitue pas encore une correlation externe ni une "
            "qualification surface-a-surface.", "",
            "![Raffinement contact frottant](friction_structural_convergence.png)", "",
        ])
        return "\n".join(lines)


def _upper(name: str, value: float, limit: float, criterion: str) -> FrictionalStructuralContactCheck:
    return FrictionalStructuralContactCheck(name, value, limit, "PASS" if value <= limit else "FAIL", criterion)
