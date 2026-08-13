"""Pinned Code_Aster correlation for the slender transverse BEAM2 dynamic path.

The QF_solver element is Timoshenko while Code_Aster ``POU_D_E`` is an
Euler-Bernoulli reference.  The selected beam is deliberately slender, so the
analytical Timoshenko shear correction is negligible.  This keeps the external
comparison useful without claiming that it validates thick-beam dynamics.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


_LENGTH = 10.0
_YOUNG = 210.0e9
_AREA = 0.01
_IY = 2.0e-6
_IZ = 3.0e-6
_J = 5.0e-6
_DENSITY = 7800.0
_LOAD = 1000.0
_TIME_STEP = 1.0e-4
_DURATION = 0.04
_LIMIT = 0.01


class CodeAsterBeam2TransverseDynamicsCampaign:
    """Compare one slender cantilever in modal, Newmark and harmonic bending."""

    study_id = "VNV-BEAM2-TRANSVERSE-DYNAMICS-CODEASTER-POUDE-019"

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run the same nodal beam, clamp, force, time and frequency grids."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal = solve_model(JsonModelReader().from_dict(_model(_modal_analysis())), enforce_policy=False)
        dynamic = solve_model(JsonModelReader().from_dict(_model(_newmark_analysis())), enforce_policy=False)
        harmonic = solve_model(JsonModelReader().from_dict(_model(_harmonic_analysis())), enforce_policy=False)
        (self.output_dir / "beam.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "beam.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "beam")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(modal, dynamic, harmonic, raw)
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _summary(self, modal: Any, dynamic: Any, harmonic: Any, raw: dict[str, Any]) -> dict[str, Any]:
        aster_modes = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_modes = np.asarray(modal.frequencies_hz[: aster_modes.size], dtype=float)
        modal_error = np.abs(qf_modes - aster_modes) / np.maximum(np.abs(aster_modes), 1.0e-30)
        qf_history = np.asarray(
            [row["probes"]["tip_uy"]["displacement"] for row in dynamic.solver["time_history"]],
            dtype=float,
        )
        aster_history = _align_history(np.asarray(raw["tip_uy_m"], dtype=float), qf_history)
        qf_harmonic = np.asarray(harmonic.responses, dtype=complex)[:, harmonic.dofs.index(1, "UY")]
        aster_harmonic = np.asarray([complex(*row) for row in raw["harmonic_tip_uy_m"]], dtype=complex)
        checks = [
            _check("modal_frequencies_same_mesh", float(np.max(modal_error)), _LIMIT),
            _check("newmark_tip_history_same_mesh", _normalized_rms(qf_history, aster_history), _LIMIT),
            _check("harmonic_tip_response_same_mesh", _complex_normalized_rms(qf_harmonic, aster_harmonic), _LIMIT),
            _check("timoshenko_shear_correction", _shear_correction(), 0.001),
        ]
        return {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "BEAM2 slender transverse linear modal/Newmark/harmonic correlation",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "POU_D_E (Euler-Bernoulli)",
            },
            "model": {
                "nodes": 2,
                "elements": 1,
                "length_m": _LENGTH,
                "same_mesh": True,
                "same_time_grid": True,
                "same_frequency_grid": True,
                "load": "FY at tip",
                "observable": "tip UY",
                "timoshenko_shear_correction": _shear_correction(),
            },
            "modal": {
                "qf_frequencies_hz": qf_modes.tolist(),
                "code_aster_frequencies_hz": aster_modes.tolist(),
                "relative_differences": modal_error.tolist(),
            },
            "newmark": {
                "time_step_s": _TIME_STEP,
                "load_table": _load_table(),
                "qf_tip_uy_m": qf_history.tolist(),
                "code_aster_tip_uy_m": aster_history.tolist(),
            },
            "harmonic": {
                "frequencies_hz": _harmonic_frequencies(),
                "qf_tip_uy_m": _complex_rows(qf_harmonic),
                "code_aster_tip_uy_m": _complex_rows(aster_harmonic),
            },
            "checks": checks,
            "limitations": [
                "POU_D_E is Euler-Bernoulli; the case is slender and the analytical Timoshenko shear correction is reported.",
                "This does not validate thick-beam shear dynamics, damping, distributed inertia, joints, geometric nonlinearity or contact.",
                "Frequencies remain below the undamped resonance to avoid a singular harmonic physical operator.",
            ],
        }

    def _plot(self, summary: dict[str, Any]) -> None:
        figure, axes = plt.subplots(1, 3, figsize=(12.0, 3.6))
        modal = summary["modal"]
        mode = np.arange(1, len(modal["qf_frequencies_hz"]) + 1)
        axes[0].plot(mode, modal["qf_frequencies_hz"], "o-", color="#0072B2", label="QF_solver")
        axes[0].plot(mode, modal["code_aster_frequencies_hz"], "s--", color="#D55E00", label="Code_Aster")
        axes[0].set(xlabel="Mode", ylabel="Frequence [Hz]", title="Modes de flexion")
        axes[0].legend(fontsize=8)
        newmark = summary["newmark"]
        time = np.arange(len(newmark["qf_tip_uy_m"])) * float(newmark["time_step_s"])
        axes[1].plot(time, newmark["qf_tip_uy_m"], color="#0072B2", label="QF_solver")
        axes[1].plot(time, newmark["code_aster_tip_uy_m"], "--", color="#D55E00", label="Code_Aster")
        axes[1].set(xlabel="Temps [s]", ylabel="UY pointe [m]", title="Newmark")
        axes[1].legend(fontsize=8)
        harmonic = summary["harmonic"]
        axes[2].plot(harmonic["frequencies_hz"], np.abs(_complex_values(harmonic["qf_tip_uy_m"])), "o-", color="#0072B2", label="QF_solver")
        axes[2].plot(harmonic["frequencies_hz"], np.abs(_complex_values(harmonic["code_aster_tip_uy_m"])), "s--", color="#D55E00", label="Code_Aster")
        axes[2].set(xlabel="Frequence [Hz]", ylabel="|UY| pointe [m]", title="Harmonique")
        axes[2].legend(fontsize=8)
        for axis in axes:
            axis.grid(True, alpha=0.25)
        figure.tight_layout()
        figure.savefig(self.output_dir / "comparison.png", dpi=180)
        plt.close(figure)


def _model(analysis: dict[str, object]) -> dict[str, object]:
    return {
        "analysis": analysis,
        "nodes": [[0.0, 0.0, 0.0], [_LENGTH, 0.0, 0.0]],
        "elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "beam"}],
        "materials": {"beam": {"type": "beam_isotropic", "E": _YOUNG, "nu": 0.3, "A": _AREA, "Iy": _IY, "Iz": _IZ, "J": _J, "density": _DENSITY, "reference_vector": [0.0, 1.0, 0.0]}},
        "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        "loads": [{"node": 1, "dof": "UY", "value": _LOAD}],
    }


def _modal_analysis() -> dict[str, object]:
    return {"type": "modal", "method": "eigh", "modes": 6}


def _newmark_analysis() -> dict[str, object]:
    return {"type": "transient_dynamic", "method": "newmark", "time_step": _TIME_STEP, "steps": round(_DURATION / _TIME_STEP), "newmark_beta": 0.25, "newmark_gamma": 0.5, "load_table": _load_table(), "history_probes": [{"node": 1, "dof": "UY", "label": "tip_uy"}]}


def _harmonic_analysis() -> dict[str, object]:
    return {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": _harmonic_frequencies(), "rayleigh_alpha": 0.0, "rayleigh_beta": 0.0}


def _load_table() -> list[dict[str, float]]:
    times = np.arange(0.0, _DURATION + 0.5 * _TIME_STEP, _TIME_STEP)
    pulse = 0.005
    return [{"time": float(time), "factor": float(math.sin(math.pi * time / pulse)) if time <= pulse else 0.0} for time in times]


def _harmonic_frequencies() -> list[float]:
    return [0.10, 0.25, 0.50, 1.00]


def _shear_correction() -> float:
    shear = _YOUNG / 2.6
    return 3.0 * _YOUNG * _IZ / ((5.0 / 6.0) * shear * _AREA * _LENGTH**2)


def _mesh() -> str:
    return """TITRE\nQF_solver BEAM2 slender transverse dynamic external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nN2 10.0 0.0 0.0\nFINSF\nSEG2\nE1 N1 N2\nFINSF\nGROUP_MA\nBEAM\nE1\nFINSF\nGROUP_NO\nROOT\nN1\nFINSF\nGROUP_NO\nTIP\nN2\nFINSF\nFIN\n"""


def _commands() -> str:
    times = ", ".join(f"{row['time']:.16g}" for row in _load_table())
    factors = ", ".join(f"{row['time']:.16g}, {row['factor']:.16g}" for row in _load_table())
    frequencies = ", ".join(f"{value:.16g}" for value in _harmonic_frequencies())
    return f'''# coding=utf-8
import json
from code_aster.Commands import *
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", PHENOMENE="MECANIQUE", MODELISATION="POU_D_E"))
material = DEFI_MATERIAU(ELAS=_F(E={_YOUNG:.16g}, NU=0.3, RHO={_DENSITY:.16g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="BEAM", MATER=material))
section = AFFE_CARA_ELEM(MODELE=model, POUTRE=_F(GROUP_MA="BEAM", SECTION="GENERALE", CARA=("A", "IY", "IZ", "JX"), VALE=({_AREA:.16g}, {_IY:.16g}, {_IZ:.16g}, {_J:.16g})))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FY={_LOAD:.16g}))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=section, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=6), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
times = DEFI_LIST_REEL(VALE=({times}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({factors}))
response = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
harmonic = DYNA_VIBRA(TYPE_CALCUL="HARM", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, COEF_MULT_C=1.0), FREQ=({frequencies}))
history = []
for order in response.getIndexes():
    values, _ = response.getField("DEPL", order).getValuesWithDescription("DY", ["TIP"])
    history.append(float(values[0]))
harmonic_values = []
for order in harmonic.getIndexes():
    values, _ = harmonic.getField("DEPL", order).getValuesWithDescription("DY", ["TIP"])
    harmonic_values.append([float(values[0].real), float(values[0].imag)])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]], "tip_uy_m": history, "harmonic_tip_uy_m": harmonic_values}}, stream, indent=2)
FIN()
'''


def _align_history(external: np.ndarray, observed: np.ndarray) -> np.ndarray:
    if external.size == observed.size + 1:
        external = external[1:]
    if external.size != observed.size:
        raise RuntimeError(f"Code_Aster returned {external.size} samples for {observed.size} QF_solver steps.")
    return external


def _normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _complex_normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _complex_rows(values: np.ndarray) -> list[list[float]]:
    return [[float(value.real), float(value.imag)] for value in values]


def _complex_values(values: list[list[float]]) -> np.ndarray:
    return np.asarray([complex(*value) for value in values], dtype=complex)


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Controle | Ecart / valeur | Limite |", "| --- | ---: | ---: |"]
    for row in summary["checks"]:
        lines.append(f"| {row['id']} | {100.0 * row['value']:.5g} % | {100.0 * row['limit']:.5g} % |")
    lines.extend(["", "Le modele est volontairement elance : le facteur analytique de cisaillement Timoshenko est explicite dans le tableau. L'oracle `POU_D_E` ne couvre pas la poutre epaisse.", ""])
    return "\n".join(lines)
