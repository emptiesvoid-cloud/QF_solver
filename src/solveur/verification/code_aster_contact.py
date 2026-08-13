"""Reproducible Code_Aster correlation for the bounded contact V1 normal law."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterFrictionlessContactCampaign:
    """Compare QF_solver to Code_Aster ``LIAISON_UNIL`` on one normal DOF.

    The common model has a spring-supported point initially at ``z=0.1 m``.
    Code_Aster enforces the same unilateral plane ``z + UZ >= 0`` through
    ``DEFI_CONTACT(... FORMULATION='LIAISON_UNIL')``.  This is a controlled
    correlation of the V1 normal law, not an assertion that the two solvers
    share the same node-to-triangle or surface-contact implementation.
    """

    study_id = "VNV-CONTACT-CODEASTER-LIAISON-UNIL-001"
    _gap = 0.1
    _stiffness = 1000.0

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run compression and separation with the pinned Code_Aster image."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [
            self._run_case("compression", -200.0, -0.1, True),
            self._run_case("separation", 20.0, 0.02, False),
        ]
        checks = self._checks(rows)
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_unilateral_normal_constraint",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "formulation": "DEFI_CONTACT / LIAISON_UNIL",
            },
            "model": {
                "initial_normal_gap_m": self._gap,
                "normal_spring_n_per_m": self._stiffness,
                "constraint": "z + UZ >= 0",
                "same_normal_loads_and_units": True,
            },
            "cases": rows,
            "checks": checks,
            "limitations": [
                "Code_Aster LIAISON_UNIL validates the equivalent scalar normal inequality.",
                "The QF_solver master triangle is deliberately reduced to its planar normal condition for this oracle.",
                "This study does not validate surface-to-surface contact, large sliding, updated normals, or friction.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(self._report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, identifier: str, load: float, expected: float, expected_active: bool) -> dict[str, Any]:
        work = self.output_dir / identifier
        work.mkdir(exist_ok=True)
        model = JsonModelReader().from_dict(_qf_model(load))
        qf = LinearStaticSolver().solve(model)
        qf_uz = float(qf.displacements[qf.dofs.index(3, "UZ")])
        qf_contact = qf.solver["contact"]["contacts"][0]
        (work / f"{identifier}.mail").write_text(single_node_mesh(), encoding="ascii")
        (work / f"{identifier}.comm").write_text(unilateral_contact_comm(load), encoding="utf-8")
        run_code_aster(work, identifier)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_uz = float(raw["uz_m"])
        return {
            "id": identifier,
            "load_z_n": load,
            "expected_uz_m": expected,
            "expected_active": expected_active,
            "qf_uz_m": qf_uz,
            "code_aster_uz_m": aster_uz,
            "qf_gap_m": float(qf_contact["gap"]),
            "qf_active": bool(qf_contact["active"]),
            "code_aster_gap_m": self._gap + aster_uz,
            "qf_theory_error": _relative(qf_uz, expected),
            "code_aster_theory_error": _relative(aster_uz, expected),
            "qf_code_aster_difference": _relative(qf_uz, aster_uz),
        }

    @staticmethod
    def _checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compression, separation = rows
        return [
            _upper("compression_qf_code_aster_uz", compression["qf_code_aster_difference"], 1.0e-10),
            _upper("separation_qf_code_aster_uz", separation["qf_code_aster_difference"], 1.0e-10),
            _upper("compression_exact_closure", abs(float(compression["code_aster_gap_m"])), 1.0e-10),
            _upper("separation_open_gap", max(0.0, -float(separation["code_aster_gap_m"])), 1.0e-12),
            {
                "id": "qf_active_set_branch",
                "value": float(
                    int(bool(compression["qf_active"]) != bool(compression["expected_active"]))
                    + int(bool(separation["qf_active"]) != bool(separation["expected_active"]))
                ),
                "limit": 0.0,
                "status": "PASS"
                if bool(compression["qf_active"]) and not bool(separation["qf_active"])
                else "FAIL",
            },
        ]

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        labels = [str(row["id"]) for row in rows]
        positions: np.ndarray = np.arange(len(rows), dtype=float)
        figure, axis = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
        axis.bar(positions - 0.17, [float(row["qf_uz_m"]) for row in rows], 0.34, label="QF_solver")
        axis.bar(positions + 0.17, [float(row["code_aster_uz_m"]) for row in rows], 0.34, label="Code_Aster")
        axis.axhline(0.0, color="#555555", linewidth=0.8)
        axis.set(xticks=positions, xticklabels=labels, ylabel="UZ esclave [m]")
        axis.grid(True, axis="y", alpha=0.3)
        axis.legend()
        figure.savefig(self.output_dir / "code_aster_contact_comparison.png", dpi=180)
        plt.close(figure)

    def _report(self, summary: dict[str, Any]) -> str:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**.",
            "",
            "## Perimetre compare",
            "",
            "QF_solver utilise son contact normal noeud-triangle a normale initiale figee. "
            "Code_Aster 18.1.0 est execute dans le conteneur Docker epingle avec "
            "`DEFI_CONTACT(... FORMULATION='LIAISON_UNIL')`. Les deux problemes ont le "
            "meme ressort normal, le meme gap initial et les memes charges. Le plan est "
            "reduit a l'inegalite scalaire `z + UZ >= 0` pour isoler la loi unilaterale.",
            "",
            "| Cas | Charge Z [N] | QF UZ [m] | Aster UZ [m] | Ecart | Gap Aster [m] |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["cases"]:
            lines.append(
                f"| {row['id']} | {float(row['load_z_n']):.6g} | {float(row['qf_uz_m']):.12g} | "
                f"{float(row['code_aster_uz_m']):.12g} | {100 * float(row['qf_code_aster_difference']):.3e} % | "
                f"{float(row['code_aster_gap_m']):.3e} |"
            )
        lines.extend(
            [
                "",
                "![Comparaison QF_solver et Code_Aster](code_aster_contact_comparison.png)",
                "",
                "## Limites",
                "",
                "Cette correlation externe ferme uniquement le comportement unidirectionnel ouverture/fermeture. "
                "Le contact avec frottement, les faces deformables, les normales actualisees, le grand glissement "
                "et les maillages non conformes restent hors preuve externe.",
                "",
            ]
        )
        return "\n".join(lines)


def single_node_mesh() -> str:
    """Return the controlled Code_Aster mesh for one discrete point."""
    return """TITRE\nQF_solver unilateral contact external correlation\nFINSF\nCOOR_3D\nN1 0.25 0.25 0.1\nFINSF\nPOI1\nM1 N1\nFINSF\nGROUP_MA\nPOINT\nM1\nFINSF\nGROUP_NO\nSLAVE\nN1\nFINSF\nFIN\n"""


def unilateral_contact_comm(load_z_n: float) -> str:
    """Return the pinned Code_Aster command deck for one unilateral normal test."""
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="POINT", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="POINT", MATER=material))
spring = AFFE_CARA_ELEM(MODELE=model, DISCRET=_F(GROUP_MA="POINT", REPERE="GLOBAL", CARA="K_T_D_N", VALE=(0.0, 0.0, 1000.0)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="SLAVE", DX=0.0, DY=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="SLAVE", FZ={load_z_n:.16g}))
gap = DEFI_CONSTANTE(VALE=0.1)
multiplier = DEFI_CONSTANTE(VALE=-1.0)
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION="LIAISON_UNIL",
    ZONE=_F(GROUP_NO="SLAVE", NOM_CMP="DZ", COEF_IMPO=gap, COEF_MULT=multiplier),
)
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=2))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    CARA_ELEM=spring,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)),
    CONTACT=contact,
    COMPORTEMENT=_F(RELATION="ELAS"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=30),
)
order = result.getIndexes()[-1]
displacement = result.getField("DEPL", order)
values, _ = displacement.getValuesWithDescription("DZ", ["SLAVE"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"uz_m": float(values[0])}}, stream, indent=2)
FIN()
'''


def _qf_model(load_z_n: float) -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 3, "dof": "UZ", "value": load_z_n}],
        "contacts": [{"name": "support_plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0)


def _upper(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": float(value), "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
