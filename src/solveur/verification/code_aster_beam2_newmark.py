"""Pinned Code_Aster Newmark correlation for the axial BEAM2 dynamic path."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


_LENGTH = 10.0
_YOUNG = 210.0e9
_AREA = 0.01
_DENSITY = 7800.0
_TIME_STEP = 1.0e-4
_DURATION = 0.04
_LOAD = 1000.0


class CodeAsterBeam2NewmarkCampaign:
    """Compare an axial BEAM2 time history with Code_Aster ``POU_D_E``.

    The axial case is intentional: both formulations have the same linear
    one-dimensional continuum limit, so an observed difference is diagnostic
    of mass assembly, boundary reduction, load interpolation or Newmark rather
    than a Timoshenko-versus-Euler-Bernoulli shear modelling choice.
    """

    study_id = "VNV-BEAM2-NEWMARK-CODEASTER-POUDE-003"
    _history_limit = 1.0e-7

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Execute the QF_solver and pinned Code_Aster same-mesh decks."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        dynamic = solve_model(JsonModelReader().from_dict(_transient_model()), enforce_policy=False)
        harmonic = solve_model(JsonModelReader().from_dict(_harmonic_model()), enforce_policy=False)
        (self.output_dir / "beam.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "beam.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "beam")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))

        qf_history = np.asarray(
            [row["probes"]["tip_ux"]["displacement"] for row in dynamic.solver["time_history"]],
            dtype=float,
        )
        aster_history = _align_history(
            np.asarray(raw["tip_ux_m"], dtype=float), qf_history
        )
        history_error = _normalized_rms(qf_history, aster_history)
        qf_harmonic = np.asarray(harmonic.responses, dtype=complex)[:, harmonic.dofs.index(1, "UX")]
        aster_harmonic = np.asarray([complex(*value) for value in raw["harmonic_tip_ux_m"]], dtype=complex)
        harmonic_error = _complex_normalized_rms(qf_harmonic, aster_harmonic)
        checks = [
            _check("newmark_tip_history", history_error, self._history_limit),
            _check("harmonic_tip_response", harmonic_error, self._history_limit),
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION"
            if all(check["status"] == "PASS" for check in checks)
            else "FAIL",
            "maturity": "experimental",
            "scope": "beam2_axial_transient_newmark",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "POU_D_E",
            },
            "model": {
                "length_m": _LENGTH,
                "E_pa": _YOUNG,
                "area_m2": _AREA,
                "density_kg_m3": _DENSITY,
                "same_mesh": True,
                "same_time_grid": True,
            },
            "newmark": {
                "beta": 0.25,
                "gamma": 0.5,
                "time_step_s": _TIME_STEP,
                "duration_s": _DURATION,
                "load_table": _load_table(),
                "qf_tip_ux_m": qf_history.tolist(),
                "code_aster_tip_ux_m": aster_history.tolist(),
            },
            "harmonic": {
                "frequencies_hz": _harmonic_frequencies(),
                "qf_tip_ux_m": [[float(value.real), float(value.imag)] for value in qf_harmonic],
                "code_aster_tip_ux_m": [[float(value.real), float(value.imag)] for value in aster_harmonic],
            },
            "results": {
                "transient_normalized_rms_difference": history_error,
                "harmonic_normalized_rms_difference": harmonic_error,
                "qf_peak_tip_ux_m": float(np.max(np.abs(qf_history))),
                "code_aster_peak_tip_ux_m": float(np.max(np.abs(aster_history))),
            },
            "checks": checks,
            "limitations": [
                "Only the axial linear BEAM2 route is correlated externally.",
                "Transverse Timoshenko shear dynamics, Rayleigh damping, joints and multi-element convergence remain separate evidence items.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        _write_report(self.output_dir / "report.md", summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _transient_model() -> dict[str, object]:
    return _model(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": _TIME_STEP,
            "steps": round(_DURATION / _TIME_STEP),
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "load_table": _load_table(),
            "history_probes": [{"node": 1, "dof": "UX", "label": "tip_ux"}],
        },
        load=_LOAD,
    )


def _harmonic_model() -> dict[str, object]:
    return _model(
        {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": _harmonic_frequencies(), "rayleigh_alpha": 0.0, "rayleigh_beta": 0.0},
        load=_LOAD,
    )


def _model(analysis: dict[str, object], *, load: float) -> dict[str, object]:
    return {
        "analysis": analysis,
        "nodes": [[0.0, 0.0, 0.0], [_LENGTH, 0.0, 0.0]],
        "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        "materials": {
            "beam": {
                "type": "beam_isotropic",
                "E": _YOUNG,
                "nu": 0.3,
                "A": _AREA,
                "Iy": 2.0e-6,
                "Iz": 3.0e-6,
                "J": 5.0e-6,
                "density": _DENSITY,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        "loads": [{"node": 1, "dof": "UX", "value": load}] if load else [],
    }


def _load_table() -> list[dict[str, float]]:
    times = np.arange(0.0, _DURATION + 0.5 * _TIME_STEP, _TIME_STEP)
    pulse = 0.005
    return [
        {
            "time": float(time),
            "factor": float(math.sin(math.pi * time / pulse)) if time <= pulse else 0.0,
        }
        for time in times
    ]


def _harmonic_frequencies() -> list[float]:
    return [0.10, 0.25, 0.50, 1.00]


def _mesh() -> str:
    return """TITRE\nQF_solver BEAM2 axial transient external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 10.0 0.0 0.0\nFINSF\nSEG2\nE1 N1 N2\nFINSF\nGROUP_MA\nBEAM\nE1\nFINSF\nGROUP_NO\nROOT\nN1\nFINSF\nGROUP_NO\nTIP\nN2\nFINSF\nFIN\n"""


def _commands() -> str:
    table = _load_table()
    time_values = ", ".join(f"{item['time']:.16g}" for item in table)
    factors = ", ".join(f"{item['time']:.16g}, {item['factor']:.16g}" for item in table)
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
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FX=1000.0))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
times = DEFI_LIST_REEL(VALE=(__TIME_VALUES__))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=(__FACTORS__))
response = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
harmonic = DYNA_VIBRA(TYPE_CALCUL="HARM", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, COEF_MULT_C=1.0), FREQ=(__FREQUENCIES__))
history = []
for order in response.getIndexes():
    field_u = response.getField("DEPL", order)
    values, _ = field_u.getValuesWithDescription("DX", ["TIP"])
    history.append(float(values[0]))
harmonic_values = []
for order in harmonic.getIndexes():
    field_u = harmonic.getField("DEPL", order)
    values, _ = field_u.getValuesWithDescription("DX", ["TIP"])
    harmonic_values.append([float(values[0].real), float(values[0].imag)])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"tip_ux_m": history, "harmonic_tip_ux_m": harmonic_values}, stream, indent=2)
FIN()
'''.replace("__TIME_VALUES__", time_values).replace("__FACTORS__", factors).replace("__FREQUENCIES__", ", ".join(f"{value:.16g}" for value in _harmonic_frequencies()))


def _align_history(external: np.ndarray, qf: np.ndarray) -> np.ndarray:
    if external.size == qf.size + 1:
        external = external[1:]
    if external.size != qf.size:
        raise RuntimeError(f"Code_Aster returned {external.size} samples for {qf.size} QF_solver steps.")
    return external


def _normalized_rms(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((value - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _complex_normalized_rms(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(value - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    results = summary["results"]
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "| Grandeur | Ecart QF_solver / Code_Aster |",
        "| --- | ---: |",
        f"| Historique Newmark UX pointe | {100.0 * results['transient_normalized_rms_difference']:.3e} % RMS normalise |",
        f"| Balayage harmonique UX pointe | {100.0 * results['harmonic_normalized_rms_difference']:.3e} % RMS normalise |",
        "",
        "Le cas axial est un oracle dynamique borne. Les resultats de flexion, cisaillement, amortissement et convergence multi-elements restent hors de cette preuve.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
