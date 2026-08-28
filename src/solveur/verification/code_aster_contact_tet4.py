"""Pinned Code_Aster correlation for one active contact on a TET4 face."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterTet4MasterContactCampaign:
    """Compare a known active contact state with an explicit Aster MPC."""

    study_id = "VNV-CONTACT-CODEASTER-TET4-MASTER-004"
    _limit = 1.0e-10

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run QF_solver and the identical active-contact constraint in Aster."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_qf_model()))
        qf_u = np.asarray(qf.displacements, dtype=float).reshape(-1, 3)
        (self.output_dir / "tet4_master.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "tet4_master.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "tet4_master")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        rows = _rows(qf_u, raw)
        checks = [_check(row) for row in rows]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_active_node_triangle_contact_on_planar_tet4_face",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "formulation": "3D/TETRA4 plus LIAISON_DDL active-contact kinematics",
            },
            "active_constraint": "UZ_slave - 0.5 UZ_n1 - 0.25 UZ_n2 - 0.25 UZ_n3 = -0.1 m",
            "results": rows,
            "checks": checks,
            "limitations": [
                "The active state is imposed by LIAISON_DDL; this is not an external validation of active-set detection.",
                "The separate LIAISON_UNIL study covers normal opening and closure for the scalar inequality.",
                "Only one planar TET4 boundary face with fixed tangential directions is correlated.",
                "General surfaces, surface-to-surface search, large sliding and friction remain outside this correlation.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _rows(qf_u: np.ndarray, raw: dict[str, object]) -> list[dict[str, float | str]]:
    master_values = cast(list[object], raw["master_uz_m"])
    aster_master = [float(cast(float, value)) for value in master_values]
    values = [("slave_uz_m", float(qf_u[4, 2]), float(cast(float, raw["slave_uz_m"])))]
    values.extend((f"master_{index + 1}_uz_m", float(qf_u[index, 2]), value) for index, value in enumerate(aster_master))
    return [
        {
            "quantity": name,
            "qf_value": qf_value,
            "code_aster_value": aster_value,
            "relative_difference": abs(qf_value - aster_value) / max(abs(aster_value), 1.0),
        }
        for name, qf_value, aster_value in values
    ]


def _check(row: dict[str, float | str]) -> dict[str, float | str]:
    difference = float(row["relative_difference"])
    return {
        "id": f"qf_code_aster_{row['quantity']}",
        "value": difference,
        "limit": CodeAsterTet4MasterContactCampaign._limit,
        "status": "PASS" if difference <= CodeAsterTet4MasterContactCampaign._limit else "FAIL",
    }


def _qf_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.25, 0.25, -1.0], [0.25, 0.25, 0.1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "elastic"}],
        "materials": {"elastic": {"type": "isotropic_3d", "E": 100000.0, "nu": 0.3}},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY"]} for node in range(3)],
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            {"node": 4, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "tet4_master", "slave_node": 4, "master_nodes": [0, 2, 1]}],
    }


def _mesh() -> str:
    return """TITRE\nQF_solver active contact on TET4 master face\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 0.0 1.0 0.0\nN3 1.0 0.0 0.0\nN4 0.25 0.25 -1.0\nN5 0.25 0.25 0.1\nFINSF\nTETRA4\nE1 N1 N2 N3 N4\nFINSF\nPOI1\nE2 N5\nFINSF\nGROUP_MA\nSOLID\nE1\nFINSF\nGROUP_MA\nPOINT\nE2\nFINSF\nGROUP_NO\nFACE\nN1 N2 N3\nFINSF\nGROUP_NO\nN1_GROUP\nN1\nFINSF\nGROUP_NO\nN2_GROUP\nN2\nFINSF\nGROUP_NO\nN3_GROUP\nN3\nFINSF\nGROUP_NO\nAPEX\nN4\nFINSF\nGROUP_NO\nSLAVE\nN5\nFINSF\nFIN\n"""


def _commands() -> str:
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"),
    _F(GROUP_MA="POINT", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"),
))
material = DEFI_MATERIAU(ELAS=_F(E=100000.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MATER=material))
spring = AFFE_CARA_ELEM(MODELE=model, DISCRET=_F(GROUP_MA="POINT", REPERE="GLOBAL", CARA="K_T_D_N", VALE=(0.0, 0.0, 1000.0)))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
    _F(GROUP_NO="FACE", DX=0.0, DY=0.0),
    _F(GROUP_NO="APEX", DX=0.0, DY=0.0, DZ=0.0),
    _F(GROUP_NO="SLAVE", DX=0.0, DY=0.0),
))
active_contact = AFFE_CHAR_MECA(MODELE=model, LIAISON_DDL=_F(
    GROUP_NO=("SLAVE", "N1_GROUP", "N2_GROUP", "N3_GROUP"),
    DDL=("DZ", "DZ", "DZ", "DZ"),
    COEF_MULT=(1.0, -0.5, -0.25, -0.25),
    COEF_IMPO=-0.1,
))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="SLAVE", FZ=-200.0))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=spring, EXCIT=(
    _F(CHARGE=boundary), _F(CHARGE=active_contact), _F(CHARGE=load),
))
depl = result.getField("DEPL", result.getIndexes()[-1])
slave, _ = depl.getValuesWithDescription("DZ", ["SLAVE"])
master, _ = depl.getValuesWithDescription("DZ", ["FACE"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"slave_uz_m": float(slave[0]), "master_uz_m": [float(value) for value in master]}, stream, indent=2)
FIN()
'''


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Grandeur | QF_solver [m] | Code_Aster [m] | Ecart |", "| --- | ---: | ---: | ---: |"]
    for row in summary["results"]:
        lines.append(f"| {row['quantity']} | {float(row['qf_value']):.12g} | {float(row['code_aster_value']):.12g} | {100 * float(row['relative_difference']):.3e} % |")
    lines.extend(["", "La correlation impose l'etat actif avec `LIAISON_DDL`; la detection active-set est couverte separement par la correlation `LIAISON_UNIL`.", ""])
    return "\n".join(lines)
