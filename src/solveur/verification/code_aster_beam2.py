"""Pinned Code_Aster comparison for the bounded BEAM2 static formulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterBeam2Campaign:
    """Compare axial, torsional and slender-bending BEAM2 observables."""

    study_id = "VNV-BEAM2-CODEASTER-POUDE-001"
    _length = 10.0
    _young = 210.0e9
    _poisson = 0.3
    _area = 0.01
    _iy = 2.0e-6
    _iz = 3.0e-6
    _torsion = 5.0e-6

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run the three convention-controlled static cases in pinned Docker."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [
            self._run_case("axial", "UX", 2000.0),
            self._run_case("torsion", "RX", 500.0),
            self._run_case("bending_y", "UY", 1000.0),
        ]
        checks = [self._upper(f"{row['id']}_qf_code_aster", float(row["difference"]), 0.01) for row in rows]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "beam2_linear_static_axial_torsion_slender_bending",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "POU_D_E"},
            "model": {"length_m": self._length, "E_pa": self._young, "nu": self._poisson, "A_m2": self._area, "Iy_m4": self._iy, "Iz_m4": self._iz, "J_m4": self._torsion},
            "cases": rows,
            "checks": checks,
            "limitations": [
                "POU_D_E is an Euler-Bernoulli oracle; bending uses a slender beam so the QF_solver Timoshenko shear term is negligible.",
                "This does not externally qualify thick-beam shear response, distributed loads, dynamics, geometric nonlinearity, or joints.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, identifier: str, dof: str, value: float) -> dict[str, Any]:
        work = self.output_dir / identifier
        work.mkdir(exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_qf_model(dof, value)))
        qf_value = float(qf.displacements[qf.dofs.index(1, dof)])
        (work / f"{identifier}.mail").write_text(_mesh(), encoding="ascii")
        (work / f"{identifier}.comm").write_text(_comm(dof, value), encoding="utf-8")
        run_code_aster(work, identifier)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_value = float(raw["value"])
        return {"id": identifier, "dof": dof, "load": value, "qf_value": qf_value, "code_aster_value": aster_value, "difference": _relative(qf_value, aster_value)}

    @staticmethod
    def _upper(identifier: str, value: float, limit: float) -> dict[str, Any]:
        return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}

    @staticmethod
    def _markdown(summary: dict[str, Any]) -> str:
        lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Cas | DDL | QF_solver | Code_Aster | Ecart |", "| --- | --- | ---: | ---: | ---: |"]
        for row in summary["cases"]:
            lines.append(f"| {row['id']} | {row['dof']} | {float(row['qf_value']):.12g} | {float(row['code_aster_value']):.12g} | {100 * float(row['difference']):.4g} % |")
        lines.extend(["", "La flexion est elancee afin que le cisaillement Timoshenko soit negligeable face a l'oracle Euler-Bernoulli `POU_D_E`.", ""])
        return "\n".join(lines)


def _mesh() -> str:
    return """TITRE\nQF_solver BEAM2 external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 10.0 0.0 0.0\nFINSF\nSEG2\nE1 N1 N2\nFINSF\nGROUP_MA\nBEAM\nE1\nFINSF\nGROUP_NO\nROOT\nN1\nFINSF\nGROUP_NO\nTIP\nN2\nFINSF\nFIN\n"""


def _comm(dof: str, value: float) -> str:
    load = {"UX": f'FORCE_NODALE=_F(GROUP_NO="TIP", FX={value:.16g})', "UY": f'FORCE_NODALE=_F(GROUP_NO="TIP", FY={value:.16g})', "RX": f'FORCE_NODALE=_F(GROUP_NO="TIP", MX={value:.16g})'}[dof]
    component = {"UX": "DX", "UY": "DY", "RX": "DRX"}[dof]
    return f'''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"))
material = DEFI_MATERIAU(ELAS=_F(E=2.1e11, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", MATER=material))
section = AFFE_CARA_ELEM(MODELE=model, POUTRE=_F(GROUP_MA="BEAM", SECTION="GENERALE", CARA=("A", "IY", "IZ", "JX"), VALE=(0.01, 2.0e-6, 3.0e-6, 5.0e-6)))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, {load})
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=section, EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)))
displacement = result.getField("DEPL", result.getIndexes()[-1])
values, _ = displacement.getValuesWithDescription("{component}", ["TIP"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"value": float(values[0])}}, stream)
FIN()
'''


def _qf_model(dof: str, value: float) -> dict[str, object]:
    return {"analysis": {"type": "linear_static", "method": "direct"}, "nodes": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}], "materials": {"beam": {"type": "beam_isotropic", "E": 2.1e11, "nu": 0.3, "A": 0.01, "Iy": 2.0e-6, "Iz": 3.0e-6, "J": 5.0e-6, "reference_vector": [0.0, 1.0, 0.0]}}, "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}], "loads": [{"node": 1, "dof": dof, "value": value}]}


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-12)
