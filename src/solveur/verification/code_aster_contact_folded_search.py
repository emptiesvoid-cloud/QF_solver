"""Exploratory autonomous Code_Aster search on the bounded folded surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.contact_master_surface import _folded_slave_patch_model_data
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterFoldedSearchCampaign:
    """Compare a three-node QF patch to Aster's autonomous surface contact."""

    study_id = "VNV-CONTACT-CODEASTER-FOLDED-SEARCH-007"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_folded_slave_patch_model_data()))
        qf_mean = np.array([np.mean([qf.displacements[qf.dofs.index(node, dof)] for node in (4, 5, 6)]) for dof in ("UX", "UY", "UZ")])
        qf_faces = [int(cast(int, row["master_face_index"])) for row in cast(list[dict[str, object]], qf.solver["contact"]["contacts"])]
        (self.output_dir / "folded_search.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "folded_search.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "folded_search")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_mean = np.asarray(cast(list[object], raw["mean_displacement_m"]), dtype=float)
        difference = float(np.linalg.norm(qf_mean - aster_mean) / max(float(np.linalg.norm(qf_mean)), 1.0e-12))
        checks = [
            _check("qf_patch_relocates_all_nodes", float(sum(face != 1 for face in qf_faces)), 0.0),
            _check("qf_code_aster_mean_displacement", difference, 0.01),
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_folded_surface_autonomous_contact_search",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "formulation": "DEFI_CONTACT / CONTINUE / frictionless"},
            "qf_mean_displacement_m": qf_mean.tolist(),
            "code_aster_mean_displacement_m": aster_mean.tolist(),
            "relative_difference": difference,
            "qf_selected_face_indices": qf_faces,
            "checks": checks,
            "limitations": [
                "Aster uses a triangular shell slave surface while QF_solver uses three independent slave nodes and springs.",
                "The comparison observes the autonomous contact response through the mean displacement; it does not map Aster contact pairs one-to-one.",
                "Large sliding and general surface-to-surface contact remain outside scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _check(identifier: str, value: float, limit: float) -> dict[str, float | str]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _mesh() -> str:
    return """TITRE\nQF_solver folded autonomous search\nFINSF\nCOOR_3D\nM1 0 0 0\nM2 1 0 0\nM3 0 1 0\nM4 1 1 0.5\nS1 0.2 0.45 0.1\nS2 0.3 0.45 0.1\nS3 0.25 0.55 0.1\nG1 0.2 0.45 1.1\nG2 0.3 0.45 1.1\nG3 0.25 0.55 1.1\nFINSF\nTRIA3\nE1 M1 M2 M3\nE2 M2 M4 M3\nE3 S1 S2 S3\nFINSF\nSEG2\nR1 S1 G1\nR2 S2 G2\nR3 S3 G3\nFINSF\nGROUP_MA\nMASTER\nE1 E2\nFINSF\nGROUP_MA\nSLAVE\nE3\nFINSF\nGROUP_MA\nSPRINGS\nR1 R2 R3\nFINSF\nGROUP_NO\nMASTER_NO\nM1 M2 M3 M4\nFINSF\nGROUP_NO\nSLAVE_NO\nS1 S2 S3\nFINSF\nGROUP_NO\nGROUND\nG1 G2 G3\nFINSF\nFIN\n"""


def _commands() -> str:
    return '''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA=("MASTER", "SLAVE"), PHENOMENE="MECANIQUE", MODELISATION="DKT"),
    _F(GROUP_MA="SPRINGS", PHENOMENE="MECANIQUE", MODELISATION="DIS_TR"),
))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e-3, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA=("MASTER", "SLAVE"), MATER=material))
stiffness = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA=("MASTER", "SLAVE"), EPAIS=1.0), DISCRET=_F(GROUP_MA="SPRINGS", REPERE="GLOBAL", CARA="K_TR_D_L", VALE=(333.3333333333333, 0.0, 333.3333333333333, 0.0, 0.0, 0.0)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
    _F(GROUP_NO="MASTER_NO", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    _F(GROUP_NO="SLAVE_NO", DY=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    _F(GROUP_NO="GROUND", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="SLAVE_NO", FX=200.0, FZ=-66.66666666666667))
contact = DEFI_CONTACT(MODELE=model, FORMULATION="CONTINUE", FROTTEMENT="SANS", ALGO_RESO_GEOM="POINT_FIXE", REAC_GEOM="AUTOMATIQUE", ALGO_RESO_CONT="NEWTON", ZONE=_F(GROUP_MA_MAIT="MASTER", GROUP_MA_ESCL="SLAVE", VECT_MAIT="AUTO", CONTACT_INIT="NON", ALGO_CONT="PENALISATION", ADAPTATION="NON", COEF_PENA_CONT=1.0e8))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(MODELE=model, CHAM_MATER=field, CARA_ELEM=stiffness, EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)), CONTACT=contact, COMPORTEMENT=_F(RELATION="ELAS"), INCREMENT=_F(LIST_INST=times), NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1), CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=50))
depl = result.getField("DEPL", result.getIndexes()[-1])
raw = []
for component in ("DX", "DY", "DZ"):
    values, _ = depl.getValuesWithDescription(component, ["SLAVE_NO"])
    raw.append(float(sum(values) / len(values)))
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"mean_displacement_m": raw}, stream, indent=2)
FIN()
'''


def _report(summary: dict[str, Any]) -> str:
    return "\n".join([f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", f"Ecart moyen QF_solver / Code_Aster : `{100 * float(summary['relative_difference']):.4g} %`.", "", *summary["limitations"], ""])
