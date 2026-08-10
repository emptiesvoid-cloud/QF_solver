"""Pinned Code_Aster correlation for the final normal of a folded contact face."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.contact_master_surface import _folded_updated_model_data
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterFoldedContactCampaign:
    """Compare the final tilted-facet normal constraint with Code_Aster."""

    study_id = "VNV-CONTACT-CODEASTER-FOLDED-NORMAL-006"
    _limit = 1.0e-10
    _normal = np.array([-0.5, -0.5, 1.0], dtype=float) / np.sqrt(1.5)

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run QF_solver then the same final normal constraint in Code_Aster."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_folded_updated_model_data()))
        qf_u = np.array([qf.displacements[qf.dofs.index(4, dof)] for dof in ("UX", "UY", "UZ")])
        initial_gap = float(self._normal @ np.array([-0.75, 0.5, 0.1]))
        (self.output_dir / "folded_normal.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "folded_normal.comm").write_text(_commands(self._normal, initial_gap), encoding="utf-8")
        run_code_aster(self.output_dir, "folded_normal")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_u = np.asarray(cast(list[object], raw["displacement_m"]), dtype=float)
        rows = [
            {
                "quantity": dof,
                "qf_value": float(qf_u[index]),
                "code_aster_value": float(aster_u[index]),
                "relative_difference": _relative(float(qf_u[index]), float(aster_u[index])),
            }
            for index, dof in enumerate(("UX", "UY", "UZ"))
        ]
        constraint_error = abs(float(self._normal @ (np.array([0.25, 0.5, 0.1]) + aster_u) - self._normal @ np.array([1.0, 0.0, 0.0])))
        checks = [
            _check(f"qf_code_aster_{row['quantity']}", float(cast(float, row["relative_difference"])), self._limit)
            for row in rows
        ] + [_check("code_aster_tilted_facet_gap", constraint_error, self._limit)]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_folded_master_final_normal_constraint",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE},
            "normal": self._normal.tolist(),
            "initial_gap_m": initial_gap,
            "results": rows,
            "checks": checks,
            "limitations": [
                "Code_Aster receives the final tilted-facet constraint through LIAISON_DDL.",
                "This correlation validates the final normal kinematics and coupled displacement, not facet-search detection.",
                "Large sliding, general surface search and surface-to-surface contact remain outside scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0)


def _check(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _mesh() -> str:
    return """TITRE\nQF_solver folded contact final normal\nFINSF\nCOOR_3D\nN1 0.25 0.5 0.1\nFINSF\nPOI1\nE1 N1\nFINSF\nGROUP_MA\nPOINT\nE1\nFINSF\nGROUP_NO\nSLAVE_X\nN1\nFINSF\nGROUP_NO\nSLAVE_Y\nN1\nFINSF\nGROUP_NO\nSLAVE_Z\nN1\nFINSF\nFIN\n"""


def _commands(normal: np.ndarray, initial_gap: float) -> str:
    nx, ny, nz = (float(value) for value in normal)
    return f'''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="POINT", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MATER=material))
spring = AFFE_CARA_ELEM(MODELE=model, DISCRET=_F(GROUP_MA="POINT", REPERE="GLOBAL", CARA="K_T_D_N", VALE=(1000.0, 1000.0, 1000.0)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="SLAVE_Y", DY=0.0))
normal_contact = AFFE_CHAR_MECA(MODELE=model, LIAISON_DDL=_F(GROUP_NO=("SLAVE_X", "SLAVE_Y", "SLAVE_Z"), DDL=("DX", "DY", "DZ"), COEF_MULT=({nx:.17g}, {ny:.17g}, {nz:.17g}), COEF_IMPO={-initial_gap:.17g}))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="SLAVE_X", FX=600.0, FZ=-200.0))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=spring, EXCIT=(_F(CHARGE=fixed), _F(CHARGE=normal_contact), _F(CHARGE=load)))
depl = result.getField("DEPL", result.getIndexes()[-1])
dx, _ = depl.getValuesWithDescription("DX", ["SLAVE_X"])
dy, _ = depl.getValuesWithDescription("DY", ["SLAVE_Y"])
dz, _ = depl.getValuesWithDescription("DZ", ["SLAVE_Z"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"displacement_m": [float(dx[0]), float(dy[0]), float(dz[0])]}}, stream, indent=2)
FIN()
'''


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| DDL | QF_solver [m] | Code_Aster [m] | Ecart |", "| --- | ---: | ---: | ---: |"]
    for row in summary["results"]:
        lines.append(f"| {row['quantity']} | {float(row['qf_value']):.12g} | {float(row['code_aster_value']):.12g} | {100 * float(row['relative_difference']):.3e} % |")
    lines.extend(["", "La contrainte inclinee finale est imposee dans Code_Aster avec `LIAISON_DDL`. Elle ne constitue pas une validation externe de la recherche de facette.", ""])
    return "\n".join(lines)
