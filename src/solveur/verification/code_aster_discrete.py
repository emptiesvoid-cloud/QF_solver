"""Pinned Code_Aster correlation for the linear discrete SDOF path."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.analyses.modal import ModalAnalysisSolver
from solveur.core.solvers.static import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


_STIFFNESS = 1000.0
_MASS = 10.0
_LOAD = 25.0
_TIME_STEP = 2.0e-3
_DURATION = 0.20


class CodeAsterDiscreteCampaign:
    """Compare one grounded spring and concentrated mass with Code_Aster.

    The transient stage deliberately keeps the same single physical degree of
    freedom as the static and modal stages.  It therefore tests the Newmark
    implementation and the external deck without conflating the result with a
    distributed-element formulation difference.
    """

    study_id = "VNV-DISCRETE-CODEASTER-SDOF-001"
    _limit = 1.0e-10
    _transient_limit = 1.0e-7

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run the controlled static, modal and Newmark case in Docker."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        static = LinearStaticSolver().solve(JsonModelReader().from_dict(_qf_static_model()))
        modal = ModalAnalysisSolver().solve(JsonModelReader().from_dict(_qf_modal_model()))
        dynamic = solve_model(JsonModelReader().from_dict(_qf_transient_model()), enforce_policy=False)
        harmonic = solve_model(JsonModelReader().from_dict(_qf_harmonic_model()), enforce_policy=False)
        (self.output_dir / "sdof.mail").write_text(_mesh(), encoding="ascii")
        (self.output_dir / "sdof.comm").write_text(_commands(), encoding="utf-8")
        run_code_aster(self.output_dir, "sdof")
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        qf_displacement = float(static.displacements[static.dofs.index(0, "UX")])
        qf_frequency = float(modal.frequencies_hz[0])
        qf_history = np.asarray(
            [row["probes"]["node_0_UX"]["displacement"] for row in dynamic.solver["time_history"]],
            dtype=float,
        )
        aster_history = _align_history(
            np.asarray(raw["transient_displacement_x_m"], dtype=float), qf_history
        )
        qf_harmonic = np.asarray(harmonic.responses, dtype=complex)[:, harmonic.dofs.index(0, "UX")]
        aster_harmonic = np.asarray(
            [complex(real, imaginary) for real, imaginary in raw["harmonic_displacement_x_m"]],
            dtype=complex,
        )
        rows = [
            _row("static_displacement", qf_displacement, float(raw["displacement_x_m"])),
            _row("first_frequency", qf_frequency, float(raw["frequency_hz"])),
            _row(
                "newmark_history_normalized_rms",
                _normalized_rms(qf_history, aster_history),
                0.0,
                reference_scale=max(float(np.max(np.abs(aster_history))), 1.0e-18),
            ),
            _row(
                "harmonic_response_normalized_rms",
                _complex_normalized_rms(qf_harmonic, aster_harmonic),
                0.0,
                reference_scale=max(float(np.max(np.abs(aster_harmonic))), 1.0e-18),
            ),
        ]
        checks = [
            {
                "id": f"qf_code_aster_{row['quantity']}",
                "value": float(row["relative_difference"]),
                "limit": self._transient_limit if "normalized_rms" in str(row["quantity"]) else self._limit,
                "status": "PASS"
                if float(row["relative_difference"])
                <= (self._transient_limit if "normalized_rms" in str(row["quantity"]) else self._limit)
                else "FAIL",
            }
            for row in rows
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(check["status"] == "PASS" for check in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_and_modal_ground_spring_concentrated_mass",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "DIS_T"},
            "parameters": {"stiffness_n_per_m": _STIFFNESS, "mass_kg": _MASS, "load_n": _LOAD},
            "transient": {
                "method": "Newmark average acceleration",
                "beta": 0.25,
                "gamma": 0.5,
                "time_step_s": _TIME_STEP,
                "duration_s": _DURATION,
                "load_table": _load_table(),
                "qf_displacement_x_m": qf_history.tolist(),
                "code_aster_displacement_x_m": aster_history.tolist(),
            },
            "harmonic": {
                "frequencies_hz": _harmonic_frequencies(),
                "qf_displacement_x_m": [[float(value.real), float(value.imag)] for value in qf_harmonic],
                "code_aster_displacement_x_m": [[float(value.real), float(value.imag)] for value in aster_harmonic],
            },
            "results": rows,
            "checks": checks,
            "limitations": [
                "Only the translational one-degree-of-freedom grounded spring and point mass are correlated.",
                "Offsets, rotary inertia, coupled matrices, local orientations and multi-node assemblies remain separate evidence items.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary


def _row(
    quantity: str,
    qf_value: float,
    reference: float,
    *,
    reference_scale: float | None = None,
) -> dict[str, float | str]:
    difference = abs(qf_value - reference) / (
        reference_scale if reference_scale is not None else max(abs(reference), 1.0e-12)
    )
    return {"quantity": quantity, "qf_value": qf_value, "code_aster_value": reference, "relative_difference": difference}


def _normalized_rms(values: np.ndarray, reference: np.ndarray) -> float:
    return float(
        np.sqrt(np.mean((values - reference) ** 2))
        / max(float(np.max(np.abs(reference))), 1.0e-18)
    )


def _complex_normalized_rms(values: np.ndarray, reference: np.ndarray) -> float:
    return float(
        np.sqrt(np.mean(np.abs(values - reference) ** 2))
        / max(float(np.max(np.abs(reference))), 1.0e-18)
    )


def _align_history(external: np.ndarray, qf_history: np.ndarray) -> np.ndarray:
    """Remove Code_Aster's optional initial sample before comparison."""
    if external.size == qf_history.size + 1:
        external = external[1:]
    if external.size != qf_history.size:
        raise RuntimeError(
            "Code_Aster returned an incompatible SDOF transient history: "
            f"{external.size} samples for {qf_history.size} QF_solver steps."
        )
    return external


def _mesh() -> str:
    return """TITRE\nQF_solver discrete SDOF external correlation\nFINSF\nCOOR_3D\nN1 0.0 0.0 0.0\nFINSF\nPOI1\nP1 N1\nFINSF\nGROUP_MA\nPOINT\nP1\nFINSF\nGROUP_NO\nNODE\nN1\nFINSF\nFIN\n"""


def _commands() -> str:
    times = _load_table()
    time_values = ", ".join(f"{item['time']:.16g}" for item in times)
    factors = ", ".join(f"{item['time']:.16g}, {item['factor']:.16g}" for item in times)
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="POINT", PHENOMENE="MECANIQUE", MODELISATION="DIS_T"))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e6, NU=0.3, RHO=1.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="POINT", MATER=material))
characteristics = AFFE_CARA_ELEM(MODELE=model, DISCRET=(
    _F(GROUP_MA="POINT", REPERE="GLOBAL", CARA="K_T_D_N", VALE=(1000.0, 1000.0, 1000.0)),
    _F(GROUP_MA="POINT", REPERE="GLOBAL", CARA="M_T_D_N", VALE=10.0),
))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="NODE", DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="NODE", FX=25.0))
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, CARA_ELEM=characteristics, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=load)))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=characteristics, CHARGE=boundary)
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=characteristics, CHARGE=boundary)
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=1), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
load_vector_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=characteristics, CHARGE=(boundary, load))
load_vector = ASSE_VECTEUR(VECT_ELEM=load_vector_e, NUME_DDL=numbering)
times = DEFI_LIST_REEL(VALE=(__TIME_VALUES__))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=(__FACTORS__))
transient = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load_vector, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
harmonic = DYNA_VIBRA(TYPE_CALCUL="HARM", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load_vector, COEF_MULT_C=1.0), FREQ=(__FREQUENCIES__))
displacement = static.getField("DEPL", static.getIndexes()[-1])
static_values, _ = displacement.getValuesWithDescription("DX", ["NODE"])
transient_values = []
for order in transient.getIndexes():
    displacement = transient.getField("DEPL", order)
    values, _ = displacement.getValuesWithDescription("DX", ["NODE"])
    transient_values.append(float(values[0]))
harmonic_values = []
for order in harmonic.getIndexes():
    displacement = harmonic.getField("DEPL", order)
    values, _ = displacement.getValuesWithDescription("DX", ["NODE"])
    harmonic_values.append([float(values[0].real), float(values[0].imag)])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"displacement_x_m": float(static_values[0]), "frequency_hz": float(modes.getAccessParameters()["FREQ"][0]), "transient_displacement_x_m": transient_values, "harmonic_displacement_x_m": harmonic_values}, stream, indent=2)
FIN()
'''.replace("__TIME_VALUES__", time_values).replace("__FACTORS__", factors).replace("__FREQUENCIES__", ", ".join(f"{value:.16g}" for value in _harmonic_frequencies()))


def _qf_static_model() -> dict[str, object]:
    return _qf_model("linear_static", load=25.0)


def _qf_modal_model() -> dict[str, object]:
    return _qf_model({"type": "modal", "method": "eigh", "modes": 1}, load=0.0)


def _qf_transient_model() -> dict[str, object]:
    model = _qf_model(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": _TIME_STEP,
            "steps": round(_DURATION / _TIME_STEP),
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "load_table": _load_table(),
            "history_probes": [{"node": 0, "dof": "UX", "label": "node_0_UX"}],
        },
        load=_LOAD,
    )
    return model


def _qf_harmonic_model() -> dict[str, object]:
    return _qf_model(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": _harmonic_frequencies(),
            "rayleigh_alpha": 0.0,
            "rayleigh_beta": 0.0,
        },
        load=_LOAD,
    )


def _qf_model(analysis: str | dict[str, object], *, load: float) -> dict[str, object]:
    return {
        "analysis": analysis,
        "nodes": [[0.0, 0.0, 0.0]],
        "elements": [],
        "materials": {},
        "springs": [{"node_a": 0, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "concentrated_masses": [{"node": 0, "mass": 10.0}],
        "fixed_dofs": [{"node": 0, "dofs": ["UY", "UZ"]}],
        "loads": [{"node": 0, "dof": "UX", "value": load}] if load else [],
    }


def _load_table() -> list[dict[str, float]]:
    """Use a smooth, finite pulse shared verbatim by both solvers."""
    values = np.arange(0.0, _DURATION + 0.5 * _TIME_STEP, _TIME_STEP)
    pulse = 0.04
    return [
        {
            "time": float(time),
            "factor": float(math.sin(math.pi * time / pulse)) if time <= pulse else 0.0,
        }
        for time in values
    ]


def _harmonic_frequencies() -> list[float]:
    """Off-resonance frequencies shared with the Code_Aster complex solve."""
    return [0.25, 0.75, 1.25, 2.25]


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Grandeur | QF_solver | Code_Aster | Ecart |", "| --- | ---: | ---: | ---: |"]
    for row in summary["results"]:
        lines.append(f"| {row['quantity']} | {float(row['qf_value']):.12g} | {float(row['code_aster_value']):.12g} | {100.0 * float(row['relative_difference']):.3e} % |")
    lines.extend(["", "Le cas couvre le statique, le premier mode et un transitoire Newmark sur le meme ressort lineaire au sol et la meme masse ponctuelle translationnelle. Il isole la chaine discrete avant toute extension aux inerties excentrees ou aux assemblages.", ""])
    return "\n".join(lines)
