"""Pinned Code_Aster static correlation for the RBE2 rigid-arm limit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterRbe2Campaign:
    """Compare a grounded rigid arm to explicit Code_Aster constraints."""

    study_id = "VNV-RBE2-CODEASTER-RIGID-ARM-001"
    _limit = 1.0e-10

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run the one-arm static correlation in the pinned Docker image."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_qf_model()))
        qf_tip = float(qf.displacements[qf.dofs.index(1, "UX")])
        qf_moment = next(
            float(item["value"])
            for item in qf.audit.equilibrium["reactions"]
            if item["node"] == 0 and item["dof"] == "RZ"
        )
        (self.output_dir / "rigid_arm.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "rigid_arm.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "rigid_arm")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        rows = [_row("tip_ux_m", qf_tip, float(raw["tip_ux_m"]))]
        checks = [
            {
                "id": f"qf_code_aster_{row['quantity']}",
                "value": float(row["relative_difference"]),
                "limit": self._limit,
                "status": "PASS" if float(row["relative_difference"]) <= self._limit else "FAIL",
            }
            for row in rows
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_rigid_arm_displacement",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "constraint": "LIAISON_DDL",
            },
            "qf_root_rz_reaction_n_m": qf_moment,
            "results": rows,
            "checks": checks,
            "limitations": [
                "The external model verifies a rigid-arm kinematic transfer in linear statics.",
                "Code_Aster REAC_NODA does not expose the dual constraint reaction on this setup.",
                "It does not correlate multiplier recovery, RBE3 weighting, dynamic constraints, or flexible joints.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _row(quantity: str, qf_value: float, reference: float) -> dict[str, float | str]:
    return {
        "quantity": quantity,
        "qf_value": qf_value,
        "code_aster_value": reference,
        "relative_difference": abs(qf_value - reference) / max(abs(reference), 1.0),
    }


def _mesh() -> str:
    return """TITRE\nQF_solver RBE2 rigid arm external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 0.0 2.0 0.0\nFINSF\nPOI1\nE1 N1\nE2 N2\nFINSF\nGROUP_MA\nROOT_ELEM\nE1\nFINSF\nGROUP_MA\nTIP_ELEM\nE2\nFINSF\nGROUP_NO\nROOT\nN1\nFINSF\nGROUP_NO\nTIP\nN2\nFINSF\nGROUP_NO\nRIGID\nN1 N2\nFINSF\nFIN\n"""


def _commands() -> str:
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DIS_TR"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MATER=material))
characteristics = AFFE_CARA_ELEM(MODELE=model, DISCRET=(
    _F(GROUP_MA="ROOT_ELEM", REPERE="GLOBAL", CARA="K_TR_D_N", VALE=(1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0)),
    _F(GROUP_MA="TIP_ELEM", REPERE="GLOBAL", CARA="K_TR_D_N", VALE=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)),
))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
rigid = AFFE_CHAR_MECA(
    MODELE=model,
    LIAISON_DDL=(
        _F(GROUP_NO=("TIP", "ROOT", "ROOT"), DDL=("DX", "DX", "DRZ"), COEF_MULT=(1.0, -1.0, 2.0), COEF_IMPO=0.0),
        _F(GROUP_NO=("TIP", "ROOT"), DDL=("DY", "DY"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),
        _F(GROUP_NO=("TIP", "ROOT", "ROOT"), DDL=("DZ", "DZ", "DRX"), COEF_MULT=(1.0, -1.0, -2.0), COEF_IMPO=0.0),
        _F(GROUP_NO=("TIP", "ROOT"), DDL=("DRX", "DRX"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),
        _F(GROUP_NO=("TIP", "ROOT"), DDL=("DRY", "DRY"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),
        _F(GROUP_NO=("TIP", "ROOT"), DDL=("DRZ", "DRZ"), COEF_MULT=(1.0, -1.0), COEF_IMPO=0.0),
    ),
)
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FX=20.0))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=characteristics, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=rigid), _F(CHARGE=load)))
field_u = result.getField("DEPL", result.getIndexes()[-1])
tip, _ = field_u.getValuesWithDescription("DX", ["TIP"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"tip_ux_m": float(tip[0])}, stream, indent=2)
FIN()
'''


def _qf_model() -> dict[str, object]:
    return {
        "analysis": "linear_static",
        "nodes": [[0.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
        "elements": [],
        "materials": {},
        "springs": [{"node_a": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"], "stiffness": 1000.0}],
        "fixed_dofs": [{"node": 0, "dofs": ["UY", "UZ", "RX", "RY", "RZ"]}],
        "loads": [{"node": 1, "dof": "UX", "value": 20.0}],
        "rbe2": [{"name": "rigid_arm", "master": 0, "slaves": [1]}],
    }


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Grandeur | QF_solver | Code_Aster | Ecart |", "| --- | ---: | ---: | ---: |"]
    for row in summary["results"]:
        lines.append(f"| {row['quantity']} | {float(row['qf_value']):.12g} | {float(row['code_aster_value']):.12g} | {100.0 * float(row['relative_difference']):.3e} % |")
    lines.extend(["", f"QF_solver recupere aussi la reaction de blocage `RZ = {float(summary['qf_root_rz_reaction_n_m']):.12g} N.m` dans son audit. La preuve externe porte sur la cinematique, pas sur une equivalence de format RBE proprietaire.", ""])
    return "\n".join(lines)
