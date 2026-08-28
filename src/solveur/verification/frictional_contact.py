"""Analytical verification campaign for bounded regularized Coulomb contact."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class FrictionContactCheck:
    """One scalar acceptance check from the frictional block campaign."""

    name: str
    value: float
    limit: float
    status: str
    criterion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class FrictionalContactVerificationCampaign:
    """Compare the node-triangle contact law to an analytical sliding block.

    A node is supported by independent normal and tangential springs above a
    rigid triangle.  The normal active set gives a known pressure and the
    tangential response has a closed-form stick/slip solution.  This proves
    the V1 implementation, not general surface-to-surface friction.
    """

    campaign_id = "VNV-CONTACT-FRICTION-BLOCK-001"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    def run(self) -> dict[str, Any]:
        rows = [self._solve_case(force, 10000.0) for force in (0.0, 10.0, 30.0, 55.0, 70.0, 100.0, 200.0)]
        positive = self._solve_case(200.0, 10000.0)
        negative = self._solve_case(-200.0, 10000.0)
        regularization = [self._solve_case(200.0, stiffness) for stiffness in (1000.0, 10000.0, 100000.0)]
        checks = self._checks(rows, positive, negative, regularization)
        status = "PASS_INTERNAL" if all(check.status == "PASS" for check in checks) else "FAIL"
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": status,
            "maturity": "experimental",
            "scope": "linear_static_node_triangle_regularized_coulomb",
            "reference": {
                "kind": "closed_form_sliding_block",
                "normal_force": 100.0,
                "friction_coefficient": 0.5,
                "normal_spring": 1000.0,
                "tangential_spring": 1000.0,
                "contact_tangential_stiffness": 10000.0,
            },
            "load_path": rows,
            "reverse_sliding": {"positive": positive, "negative": negative},
            "regularization_sensitivity": regularization,
            "checks": [check.to_dict() for check in checks],
            "limitations": [
                "Each load point is a separate static solve; no rate or incremental slip history is represented.",
                "Incremental slip memory is checked separately at unit-test level; it is not an external structural validation.",
                "Strongly coupled structural sliding can be rejected by the active-set iteration and remains outside this campaign.",
                "No external solver correlation is claimed by this internal analytical campaign.",
                "The formulation remains node-to-triangle with frozen initial normal and small transformations.",
            ],
        }
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._plot(rows)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.campaign_id)
        return summary

    @staticmethod
    def _solve_case(tangential_load: float, tangential_stiffness: float) -> dict[str, Any]:
        normal_spring = 1000.0
        contact_stiffness = float(tangential_stiffness)
        normal_load = -200.0
        friction = 0.5
        model = JsonModelReader().from_dict(
            {
                "analysis": {
                    "type": "linear_static",
                    "method": "direct",
                    "contact_max_iterations": 20,
                    "contact_friction_tolerance": 1.0e-11,
                },
                "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
                "elements": [],
                "materials": {},
                "fixed_dofs": [
                    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                    {"node": 1, "dofs": ["UX", "UY", "UZ"]},
                    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                    {"node": 3, "dofs": ["UY"]},
                ],
                "springs": [{"node_a": 3, "dofs": ["UX", "UZ"], "stiffness": [normal_spring, normal_spring]}],
                "loads": [
                    {"node": 3, "dof": "UX", "value": tangential_load},
                    {"node": 3, "dof": "UZ", "value": normal_load},
                ],
                "contacts": [
                    {
                        "name": "analytical_rough_plane",
                        "slave_node": 3,
                        "master_nodes": [0, 1, 2],
                        "friction_coefficient": friction,
                        "tangential_stiffness": contact_stiffness,
                    }
                ],
            }
        )
        result = LinearStaticSolver().solve(model)
        row = result.solver["contact"]["contacts"][0]
        pressure = float(row["pressure"])
        limit = friction * pressure
        stick_limit = limit * (normal_spring + contact_stiffness) / contact_stiffness
        if abs(tangential_load) <= stick_limit:
            expected_displacement = tangential_load / (normal_spring + contact_stiffness)
            expected_force = contact_stiffness * expected_displacement
            expected_state = "stick"
        else:
            expected_force = float(np.copysign(limit, tangential_load))
            expected_displacement = (tangential_load - expected_force) / normal_spring
            expected_state = "slip"
        measured_displacement = float(result.displacements[result.dofs.index(3, "UX")])
        force = float(row["tangential_force"][0])
        relative_displacement = float(row["tangential_displacement"][0])
        return {
            "tangential_load": tangential_load,
            "tangential_stiffness": contact_stiffness,
            "pressure": pressure,
            "friction_limit": float(row["friction_limit"]),
            "state": str(row["tangential_state"]),
            "displacement": measured_displacement,
            "relative_displacement": relative_displacement,
            "tangential_force": force,
            "local_work": force * relative_displacement,
            "expected_state": expected_state,
            "expected_displacement": expected_displacement,
            "expected_tangential_force": expected_force,
            "displacement_relative_error": _relative_error(measured_displacement, expected_displacement),
            "force_relative_error": _relative_error(force, expected_force),
        }

    @staticmethod
    def _checks(
        rows: list[dict[str, Any]],
        positive: dict[str, Any],
        negative: dict[str, Any],
        regularization: list[dict[str, Any]],
    ) -> list[FrictionContactCheck]:
        displacement_error = max(float(row["displacement_relative_error"]) for row in rows)
        force_error = max(float(row["force_relative_error"]) for row in rows)
        pressure_error = max(abs(float(row["pressure"]) - 100.0) / 100.0 for row in rows)
        cone_excess = max(
            abs(float(row["tangential_force"])) - float(row["friction_limit"]) for row in rows
        )
        work_minimum = min(float(row["local_work"]) for row in rows)
        states_match = float(sum(str(row["state"]) != str(row["expected_state"]) for row in rows))
        reverse_error = max(
            _relative_error(float(positive["tangential_force"]), -float(negative["tangential_force"])),
            _relative_error(float(positive["displacement"]), -float(negative["displacement"])),
        )
        sliding_force_spread = max(abs(float(row["tangential_force"]) - 50.0) for row in regularization)
        return [
            _upper("analytical displacement", displacement_error, 1.0e-10, "maximum relative error"),
            _upper("analytical tangential force", force_error, 1.0e-10, "maximum relative error"),
            _upper("normal pressure", pressure_error, 1.0e-10, "relative error against 100 N"),
            _upper("Coulomb cone excess", cone_excess, 1.0e-10, "force norm minus mu times pressure"),
            _lower("non-negative local friction work", work_minimum, -1.0e-12, "q dot s"),
            _upper("stick/slip state mismatch count", states_match, 0.0, "analytical branch classification"),
            _upper("reversed sliding symmetry", reverse_error, 1.0e-10, "relative force and displacement mismatch"),
            _upper("sliding regularization sensitivity", sliding_force_spread, 1.0e-10, "force spread at 200 N tangential load"),
        ]

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        loads = np.array([float(row["tangential_load"]) for row in rows])
        displacements = np.array([float(row["displacement"]) for row in rows])
        analytical = np.array([float(row["expected_displacement"]) for row in rows])
        forces = np.array([float(row["tangential_force"]) for row in rows])
        expected_forces = np.array([float(row["expected_tangential_force"]) for row in rows])
        figure, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
        axes[0].plot(loads, displacements, "o-", label="QF_solver")
        axes[0].plot(loads, analytical, "k--", label="analytique")
        axes[0].set(xlabel="Force tangentielle [N]", ylabel="Deplacement tangent [m]")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        axes[1].plot(loads, forces, "o-", label="QF_solver")
        axes[1].plot(loads, expected_forces, "k--", label="Coulomb regularise")
        axes[1].set(xlabel="Force tangentielle [N]", ylabel="Force de frottement [N]")
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        figure.savefig(self.output_dir / "friction_block_comparison.png", dpi=160)
        plt.close(figure)

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        checks = cast(list[dict[str, Any]], summary["checks"])
        lines = [
            "# V&V contact avec frottement : bloc analytique",
            "",
            f"- Etude : `{summary['campaign_id']}`",
            f"- Verdict interne : `{summary['status']}`",
            "- Maturite : `experimental`",
            "- Reference : bloc glissant a ressorts, solution analytique de la loi regularisee implementee.",
            "",
            "## Criteres automatiques",
            "",
            "| Critere | Valeur | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
        ]
        for check in checks:
            lines.append(
                f"| {check['name']} | {float(check['value']):.3e} | {float(check['limit']):.3e} | {check['status']} |"
            )
        lines.extend(
            [
                "",
                "## Lecture",
                "",
                "La campagne couvre l'adherence, le glissement sature a la borne de Coulomb, le changement de signe et l'effet de la regularisation. Chaque point est toutefois une statique independante. La memoire incremental charge-decharge est verifiee par un test unitaire distinct; la convergence structurelle en glissement fort reste ouverte.",
                "",
                "![Comparaison bloc rugueux](friction_block_comparison.png)",
            ]
        )
        return "\n".join(lines) + "\n"


def _relative_error(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0)


def _upper(name: str, value: float, limit: float, criterion: str) -> FrictionContactCheck:
    return FrictionContactCheck(name, value, limit, "PASS" if value <= limit else "FAIL", criterion)


def _lower(name: str, value: float, limit: float, criterion: str) -> FrictionContactCheck:
    return FrictionContactCheck(name, value, limit, "PASS" if value >= limit else "FAIL", criterion)
