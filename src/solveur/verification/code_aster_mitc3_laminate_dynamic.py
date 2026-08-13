"""Same-mesh Code_Aster DST correlation for bounded MITC3+ laminate dynamics.

This campaign compares modal frequencies, a Newmark history and a sub-resonant
harmonic response.  It deliberately does not call its displacements a ply
stress correlation: that requires a separately controlled through-thickness
stress extraction from the external solver.
"""

from __future__ import annotations

from solveur.paths import project_root

import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc3 import code_aster_triangle_mesh
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc3_models import cantilever_model, rectangular_tri_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-LAMINATE-DYNAMICS-CODEASTER-DST-019"


class CodeAsterMitc3LaminateDynamicsCampaign:
    """Compare a flat symmetric MITC3+ laminate with Code_Aster DST."""

    study_id = STUDY_ID
    modal_limit = 0.12
    transient_limit = 0.15
    harmonic_limit = 0.15

    def __init__(self, output_dir: str | Path, *, nx: int = 12, ny: int = 3) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx, self.ny = int(nx), int(ny)
        if self.nx < 4 or self.ny < 1:
            raise ValueError("MITC3 laminate dynamics requires nx >= 4 and ny >= 1.")

    def run(self) -> dict[str, Any]:
        """Run the common TRIA3 mesh protocol through both solvers."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model, triangles, root, tip = self._model(_modal_analysis(), transverse_force=0.0)
        modal = solve_model(modal_model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        time_step = 1.0 / frequency / 40.0
        steps = 80
        load_table = _pulse_table(time_step, steps)
        frequencies = [ratio * frequency for ratio in (0.10, 0.25, 0.50, 0.75)]
        transient_model, _, _, _ = self._model(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "load_table": load_table,
                "history_probes": [
                    {"node": int(node), "dof": "UZ", "label": f"tip_{int(node)}"} for node in tip
                ],
            },
            transverse_force=-1.0,
        )
        harmonic_model, _, _, _ = self._model(
            {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies},
            transverse_force=-1.0,
        )
        transient = solve_model(transient_model, enforce_policy=False)
        harmonic = solve_model(harmonic_model, enforce_policy=False)

        stem = "mitc3_laminate_dynamic"
        (self.output_dir / f"{stem}.mail").write_text(
            code_aster_triangle_mesh(modal_model.nodes, triangles, root, tip), encoding="ascii"
        )
        (self.output_dir / f"{stem}.comm").write_text(
            code_aster_dynamic_comm(len(tip), load_table, frequencies), encoding="utf-8"
        )
        run_code_aster(self.output_dir, stem, timeout=1800)
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(modal, transient, harmonic, raw, tip, time_step, load_table, frequencies)
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        self._publish_reference()
        return summary

    def _model(
        self, analysis: dict[str, object], *, transverse_force: float
    ) -> tuple[FiniteElementModel, np.ndarray, np.ndarray, np.ndarray]:
        model = cantilever_model(
            self.nx,
            self.ny,
            laminate=True,
            transverse_force=transverse_force,
            analysis={**analysis, "dense_modal_max_dofs": 6000},
        )
        _, triangles, node = rectangular_tri_mesh(1.0, 0.2, self.nx, self.ny)
        root = np.asarray([node(0, row) for row in range(self.ny + 1)], dtype=np.int64)
        tip = np.asarray([node(self.nx, row) for row in range(self.ny + 1)], dtype=np.int64)
        return model, triangles, root, tip

    def _summary(
        self,
        modal: Any,
        transient: Any,
        harmonic: Any,
        raw: dict[str, Any],
        tip: np.ndarray,
        time_step: float,
        load_table: list[dict[str, float]],
        frequencies: list[float],
    ) -> dict[str, Any]:
        aster_frequencies = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_frequencies = np.asarray(modal.frequencies_hz[: aster_frequencies.size], dtype=float)
        modal_errors = np.abs(qf_frequencies - aster_frequencies) / np.maximum(np.abs(aster_frequencies), 1.0e-30)
        qf_history = _tip_mean_history(transient.solver["time_history"], tip)
        aster_history = _align_history(np.asarray(raw["tip_uz_m"], dtype=float), qf_history)
        tip_dofs = [harmonic.dofs.index(int(node), "UZ") for node in tip]
        qf_harmonic = np.asarray(
            [np.mean(np.asarray(response, dtype=complex)[tip_dofs]) for response in harmonic.responses], dtype=complex
        )
        aster_harmonic = np.asarray([complex(*value) for value in raw["harmonic_tip_uz_m"]], dtype=complex)
        checks = [
            _check("modal_frequencies", float(np.max(modal_errors)), self.modal_limit),
            _check("newmark_tip_history", _normalized_rms(qf_history, aster_history), self.transient_limit),
            _check("harmonic_tip_response", _complex_normalized_rms(qf_harmonic, aster_harmonic), self.harmonic_limit),
            _check("qf_modal_residual", float(modal.solver["max_relative_residual"]), 1.0e-7),
            _check("qf_dynamic_residual", _max_dynamic_residual(transient), 1.0e-7),
        ]
        return {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "verified_development_external_correlation",
            "scope": "Planar MITC3+ [0/90/90/0] laminate, small-displacement linear dynamics",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DST / TRIA3 / DEFI_COMPOSITE",
            },
            "comparison_basis": {
                "same_mesh": True,
                "same_layup": [0.0, 90.0, 90.0, 0.0],
                "same_density": True,
                "same_supports": True,
                "same_time_grid": True,
                "same_frequency_grid": True,
                "same_load_table": True,
            },
            "model": {"mesh": [self.nx, self.ny], "tria3_elements": 2 * self.nx * self.ny, "tip_nodes": tip.tolist()},
            "modal": {
                "qf_frequencies_hz": qf_frequencies.tolist(),
                "code_aster_frequencies_hz": aster_frequencies.tolist(),
                "relative_differences": modal_errors.tolist(),
            },
            "newmark": {
                "time_step_s": time_step,
                "steps": len(qf_history),
                "load_table": load_table,
                "qf_tip_uz_m": qf_history.tolist(),
                "code_aster_tip_uz_m": aster_history.tolist(),
            },
            "harmonic": {
                "frequencies_hz": frequencies,
                "qf_tip_uz_m": _complex_rows(qf_harmonic),
                "code_aster_tip_uz_m": _complex_rows(aster_harmonic),
            },
            "checks": checks,
            "limitations": [
                "Code_Aster DST and QF_solver MITC3+ are distinct shell formulations.",
                "The cross-code response comparison is planar, symmetric and below the first harmonic resonance.",
                "Ply stress values are not extracted from Code_Aster in this campaign, so no external per-ply stress claim is made.",
                "Curved laminate dynamics, non-zero B coupling, damping calibration, damage and delamination remain outside this evidence.",
            ],
        }

    def _plot(self, summary: dict[str, Any]) -> None:
        figure, axes = plt.subplots(1, 3, figsize=(14.2, 4.0))
        modal = summary["modal"]
        modes = np.arange(1, len(modal["qf_frequencies_hz"]) + 1)
        axes[0].plot(modes, modal["qf_frequencies_hz"], "o-", color="#087f5b", label="QF_solver MITC3+")
        axes[0].plot(modes, modal["code_aster_frequencies_hz"], "s--", color="#c92a2a", label="Code_Aster DST")
        axes[0].set(xlabel="Mode", ylabel="Frequence [Hz]", title="Modes propres")
        axes[0].grid(alpha=0.25)
        axes[0].legend(fontsize=8)
        newmark = summary["newmark"]
        time = np.arange(len(newmark["qf_tip_uz_m"])) * float(newmark["time_step_s"])
        axes[1].plot(time, newmark["qf_tip_uz_m"], color="#087f5b", label="QF_solver MITC3+")
        axes[1].plot(time, newmark["code_aster_tip_uz_m"], "--", color="#c92a2a", label="Code_Aster DST")
        axes[1].set(xlabel="Temps [s]", ylabel="UZ moyen pointe [m]", title="Newmark")
        axes[1].grid(alpha=0.25)
        axes[1].legend(fontsize=8)
        harmonic = summary["harmonic"]
        qf = np.asarray([complex(*value) for value in harmonic["qf_tip_uz_m"]])
        aster = np.asarray([complex(*value) for value in harmonic["code_aster_tip_uz_m"]])
        axes[2].semilogy(harmonic["frequencies_hz"], np.abs(qf), "o-", color="#087f5b", label="QF_solver MITC3+")
        axes[2].semilogy(harmonic["frequencies_hz"], np.abs(aster), "s--", color="#c92a2a", label="Code_Aster DST")
        axes[2].set(xlabel="Frequence [Hz]", ylabel="|UZ| moyen pointe [m]", title="Harmonique")
        axes[2].grid(alpha=0.25)
        axes[2].legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc3_laminate_code_aster_comparison.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        root = project_root()
        reference = root / "qualification" / "vnv" / "external" / "code_aster_mitc3_laminate_dynamic" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "report.md", "vnv_manifest.json", "mitc3_laminate_code_aster_comparison.png"):
            shutil.copy2(self.output_dir / name, reference / name)
        assets = root / "docs" / "assets" / "reviews"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.output_dir / "mitc3_laminate_code_aster_comparison.png", assets / "mitc3_laminate_code_aster_comparison.png")


def _modal_analysis() -> dict[str, object]:
    return {"type": "modal", "method": "eigh", "modes": 4, "dense_modal_max_dofs": 6000}


def _pulse_table(step: float, steps: int) -> list[dict[str, float]]:
    duration = 0.25 * steps * step
    return [
        {"time": index * step, "factor": math.sin(math.pi * index * step / duration) if index * step <= duration else 0.0}
        for index in range(steps + 1)
    ]


def code_aster_dynamic_comm(tip_count: int, table: list[dict[str, float]], frequencies: list[float]) -> str:
    """Return the controlled TRIA3/DST laminate dynamics deck."""
    times = ", ".join(f"{row['time']:.16g}" for row in table)
    factors = ", ".join(f"{row['time']:.16g}, {row['factor']:.16g}" for row in table)
    frequency_text = ", ".join(f"{value:.16g}" for value in frequencies)
    layers = ",\n        ".join(
        f"_F(EPAIS=0.0025, MATER=lamina, ORIENTATION={angle:.1f})" for angle in (0.0, 90.0, 90.0, 0.0)
    )
    force = -1.0 / tip_count
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DST"))
lamina = DEFI_MATERIAU(ELAS_ORTH=_F(E_L=130.0e9, E_T=9.0e9, E_N=9.0e9, NU_LT=0.28, NU_LN=0.28, NU_TN=0.28, G_LT=5.0e9, G_LN=4.0e9, G_TN=3.5e9, RHO=1550.0))
laminate = DEFI_COMPOSITE(COUCHE=(
        {layers}
))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=laminate))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.01, COQUE_NCOU=4))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FZ={force:.16g}))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=4), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
times = DEFI_LIST_REEL(VALE=({times}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({factors}))
response = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
harmonic = DYNA_VIBRA(TYPE_CALCUL="HARM", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, COEF_MULT_C=1.0), FREQ=({frequency_text}))
history = []
for order in response.getIndexes():
    values, _ = response.getField("DEPL", order).getValuesWithDescription("DZ", ["TIP"])
    history.append(float(sum(values) / len(values)))
harmonic_values = []
for order in harmonic.getIndexes():
    values, _ = harmonic.getField("DEPL", order).getValuesWithDescription("DZ", ["TIP"])
    value = sum(values) / len(values)
    harmonic_values.append([float(value.real), float(value.imag)])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]], "tip_uz_m": history, "harmonic_tip_uz_m": harmonic_values}}, stream, indent=2)
FIN()
'''


def _tip_mean_history(history: list[dict[str, Any]], tip: np.ndarray) -> np.ndarray:
    labels = [f"tip_{int(node)}" for node in tip]
    return np.asarray([np.mean([float(row["probes"][label]["displacement"]) for label in labels]) for row in history], dtype=float)


def _align_history(external: np.ndarray, observed: np.ndarray) -> np.ndarray:
    if external.size == observed.size + 1:
        external = external[1:]
    if external.size != observed.size:
        raise RuntimeError(f"Code_Aster returned {external.size} samples for {observed.size} QF_solver steps.")
    return external


def _max_dynamic_residual(result: Any) -> float:
    return max(float(row["dynamic_residual_norm"]) for row in result.solver["time_history"])


def _complex_rows(values: np.ndarray) -> list[list[float]]:
    return [[float(value.real), float(value.imag)] for value in values]


def _normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _complex_normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "| Controle | Ecart / valeur | Seuil | Statut |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in summary["checks"]:
        lines.append(f"| {item['id']} | {float(item['value']):.4e} | {float(item['limit']):.4e} | {item['status']} |")
    lines.extend(
        [
            "",
            "Le protocole fige le maillage TRIA3, l'empilement, la densite, les blocages, la table Newmark et la grille harmonique.",
            "Il ne compare pas de contrainte par pli : cette sortie externe doit etre qualifiee par une campagne separee.",
            "",
            "![Correlation MITC3 multicouche / Code_Aster](mitc3_laminate_code_aster_comparison.png)",
            "",
        ]
    )
    return "\n".join(lines)
