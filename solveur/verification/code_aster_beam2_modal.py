"""Pinned Code_Aster modal correlation for the BEAM2 slender-beam limit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.modal import ModalAnalysisSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterBeam2ModalCampaign:
    """Compare the first six fixed-free BEAM2 modes with ``POU_D_E``.

    The model deliberately uses a slender, one-element cantilever.  It checks
    the implementation of the mass matrix and its local signs, rather than
    qualifying thick-beam Timoshenko dynamics.
    """

    study_id = "VNV-BEAM2-MODAL-CODEASTER-POUDE-002"
    _limit = 0.01

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Execute the pinned external oracle and write a self-contained V&V bundle."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        qf = ModalAnalysisSolver().solve(JsonModelReader().from_dict(_qf_model()))
        (self.output_dir / "beam.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "beam.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "beam")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        reference = np.asarray(raw["frequencies_hz"], dtype=float)
        observed = np.asarray(qf.frequencies_hz[: reference.size], dtype=float)
        differences = np.abs(observed - reference) / np.maximum(np.abs(reference), 1.0e-12)
        rows = [
            {
                "mode": index + 1,
                "qf_frequency_hz": float(observed[index]),
                "code_aster_frequency_hz": float(reference[index]),
                "relative_difference": float(differences[index]),
            }
            for index in range(reference.size)
        ]
        checks = [
            {
                "id": f"mode_{row['mode']}_qf_code_aster",
                "value": row["relative_difference"],
                "limit": self._limit,
                "status": "PASS" if row["relative_difference"] <= self._limit else "FAIL",
            }
            for row in rows
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "beam2_modal_slender_one_element_mass_matrix",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "POU_D_E",
            },
            "modes": rows,
            "checks": checks,
            "limitations": [
                "This one-element slender-beam correlation verifies the implemented mass signs and ordering.",
                "It does not qualify thick-beam shear dynamics, mesh convergence, damping, distributed inertia, or joints.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _mesh() -> str:
    return """TITRE\nQF_solver BEAM2 modal external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 10.0 0.0 0.0\nFINSF\nSEG2\nE1 N1 N2\nFINSF\nGROUP_MA\nBEAM\nE1\nFINSF\nGROUP_NO\nROOT\nN1\nFINSF\nFIN\n"""


def _commands() -> str:
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"))
material = DEFI_MATERIAU(ELAS=_F(E=2.1e11, NU=0.3, RHO=7800.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", MATER=material))
section = AFFE_CARA_ELEM(MODELE=model, POUTRE=_F(GROUP_MA="BEAM", SECTION="GENERALE", CARA=("A", "IY", "IZ", "JX"), VALE=(0.01, 2.0e-6, 3.0e-6, 5.0e-6)))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=boundary)
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=boundary)
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=6), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]]}, stream, indent=2)
FIN()
'''


def _qf_model() -> dict[str, object]:
    return {
        "analysis": {"type": "modal", "method": "eigh", "modes": 6},
        "nodes": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]],
        "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        "materials": {"beam": {"type": "beam_isotropic", "E": 2.1e11, "nu": 0.3, "A": 0.01, "Iy": 2.0e-6, "Iz": 3.0e-6, "J": 5.0e-6, "density": 7800.0, "reference_vector": [0.0, 1.0, 0.0]}},
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
    }


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Mode | QF_solver [Hz] | Code_Aster [Hz] | Ecart |", "| ---: | ---: | ---: | ---: |"]
    for row in summary["modes"]:
        lines.append(f"| {row['mode']} | {row['qf_frequency_hz']:.9g} | {row['code_aster_frequency_hz']:.9g} | {100.0 * row['relative_difference']:.5g} % |")
    lines.extend(["", "L'oracle `POU_D_E` est Euler-Bernoulli. Le cas est tres elance afin que cette comparaison isole la masse BEAM2 et ses conventions locales.", ""])
    return "\n".join(lines)
