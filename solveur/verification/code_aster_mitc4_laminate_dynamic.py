"""Same-mesh Code_Aster correlation for bounded MITC4 laminate dynamics.

The comparison intentionally remains a *cross-formulation* correlation:
QF_solver uses a MITC4 Reissner-Mindlin shell while Code_Aster uses its DST
laminate shell.  Coordinates, QUAD4 connectivity, layup, density, supports,
load table and frequency grid are nevertheless identical.  It is therefore
useful independent evidence, not an assertion that both element formulations
are algebraically equivalent.
"""

from __future__ import annotations

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
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc4_laminate_dynamic import Mitc4LaminateDynamicStudy
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-LAMINATE-DYNAMICS-CODEASTER-DST-018"


class CodeAsterMitc4LaminateDynamicsCampaign:
    """Compare modal, Newmark and harmonic laminate responses on common QUAD4s."""

    study_id = STUDY_ID
    modal_limit = 0.10
    transient_limit = 0.12
    harmonic_limit = 0.12

    def __init__(
        self,
        output_dir: str | Path,
        *,
        nx: int = 12,
        ny: int = 3,
        layup: tuple[float, ...] = (0.0, 90.0, 90.0, 0.0),
        damping_ratio: float = 0.0,
        publish_reference: bool = True,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx, self.ny = int(nx), int(ny)
        self.layup = tuple(float(angle) for angle in layup)
        self.damping_ratio = float(damping_ratio)
        self.publish_reference = bool(publish_reference)
        if self.nx < 4 or self.ny < 1:
            raise ValueError("MITC4 laminate dynamics requires nx >= 4 and ny >= 1.")
        if len(self.layup) != 4:
            raise ValueError("MITC4 laminate dynamics requires exactly four plies.")
        if not 0.0 <= self.damping_ratio <= 0.10:
            raise ValueError("damping_ratio must be between 0 and 0.10.")

    def run(self) -> dict[str, Any]:
        """Execute the QF_solver and pinned Code_Aster calculations."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model, nodes = self._model(_modal_analysis())
        modal = solve_model(modal_model, enforce_policy=False)
        first_frequency = float(modal.frequencies_hz[0])
        time_step = 1.0 / first_frequency / 40.0
        rayleigh_alpha = 2.0 * self.damping_ratio * 2.0 * math.pi * first_frequency
        steps = 80
        load_table = _pulse_table(time_step, steps)
        frequencies = [ratio * first_frequency for ratio in (0.10, 0.25, 0.50, 0.75)]
        tip = _tip_nodes(nodes)

        transient_model, _ = self._model(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": rayleigh_alpha,
                "rayleigh_beta": 0.0,
                "load_table": load_table,
                "history_probes": [
                    {"node": int(node), "dof": "UZ", "label": f"tip_{int(node)}"} for node in tip
                ],
            },
            total_load=-1.0,
        )
        harmonic_model, _ = self._model(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies,
                "rayleigh_alpha": rayleigh_alpha,
                "rayleigh_beta": 0.0,
            },
            total_load=-1.0,
        )
        transient = solve_model(transient_model, enforce_policy=False)
        harmonic = solve_model(harmonic_model, enforce_policy=False)

        stem = "mitc4_laminate_dynamic"
        (self.output_dir / f"{stem}.mail").write_text(_code_aster_mesh(modal_model), encoding="ascii")
        (self.output_dir / f"{stem}.comm").write_text(
            code_aster_dynamic_comm(
                len(tip), time_step, load_table, frequencies, layup=self.layup, rayleigh_alpha=rayleigh_alpha
            ),
        )
        run_code_aster(self.output_dir, stem, timeout=1800)
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(
            modal, transient, harmonic, raw, tip, time_step, load_table, frequencies, rayleigh_alpha
        )
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        if self.publish_reference:
            self._publish_reference()
        return summary

    def _model(
        self, analysis: dict[str, object], *, total_load: float = 0.0
    ) -> tuple[FiniteElementModel, np.ndarray]:
        campaign = Mitc4LaminateDynamicStudy(mesh=(self.nx, self.ny), layup=self.layup)
        model, nodes = campaign.build_model()
        model.analysis = model.analysis.from_raw(analysis)
        if total_load:
            tip = _tip_nodes(nodes)
            model.loads = [
                NodalLoad(node=int(node), dof="UZ", value=total_load / len(tip)) for node in tip
            ]
        return model, nodes

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
        rayleigh_alpha: float,
    ) -> dict[str, Any]:
        aster_frequencies = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_frequencies = np.asarray(modal.frequencies_hz[: aster_frequencies.size], dtype=float)
        modal_error = np.abs(qf_frequencies - aster_frequencies) / np.maximum(np.abs(aster_frequencies), 1.0e-30)
        qf_history = _tip_mean_history(transient.solver["time_history"], tip)
        aster_history = _align_history(np.asarray(raw["tip_uz_m"], dtype=float), qf_history)
        tip_dofs = [harmonic.dofs.index(int(node), "UZ") for node in tip]
        qf_harmonic = np.asarray(
            [np.mean(np.asarray(response, dtype=complex)[tip_dofs]) for response in harmonic.responses], dtype=complex
        )
        aster_harmonic = np.asarray([complex(*value) for value in raw["harmonic_tip_uz_m"]], dtype=complex)
        checks = [
            _check("modal_frequencies", float(np.max(modal_error)), self.modal_limit),
            _check("newmark_tip_history", _normalized_rms(qf_history, aster_history), self.transient_limit),
            _check("harmonic_tip_response", _complex_normalized_rms(qf_harmonic, aster_harmonic), self.harmonic_limit),
            _check("qf_modal_residual", float(modal.solver["max_relative_residual"]), 1.0e-7),
            _check("qf_dynamic_residual", _max_dynamic_residual(transient), 1.0e-7),
        ]
        if self.damping_ratio > 0.0:
            damping_decay = _damped_decay_ratio(qf_history, load_table)
            checks.append(_check("newmark_damped_decay", damping_decay, 0.95))
        return {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "verified_development_external_correlation",
            "scope": "Planar MITC4 [0/90/90/0] laminate, small-displacement linear dynamics",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "DST / QUAD4 / DEFI_COMPOSITE",
            },
            "comparison_basis": {
                "same_mesh": True,
                "same_layup": list(self.layup),
                "same_density": True,
                "same_supports": True,
                "same_time_grid": True,
                "same_frequency_grid": True,
                "same_load_table": True,
            },
            "model": {
                "mesh": [self.nx, self.ny],
                "quad4_elements": self.nx * self.ny,
                "tip_nodes": tip.tolist(),
                "layup_deg": list(self.layup),
            },
            "damping": {
                "rayleigh_alpha": rayleigh_alpha,
                "rayleigh_beta": 0.0,
                "target_mode_1_ratio": self.damping_ratio,
            },
            "modal": {
                "qf_frequencies_hz": qf_frequencies.tolist(),
                "code_aster_frequencies_hz": aster_frequencies.tolist(),
                "relative_differences": modal_error.tolist(),
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
                "Code_Aster DST and QF_solver MITC4 are distinct Reissner-Mindlin shell formulations.",
                "The comparison is planar, symmetric, linear and below the first resonance for the harmonic sweep.",
                "It does not validate curved laminate dynamics, projected material axes, damping calibration beyond the stated mass-proportional target, ply failure, damage or delamination.",
                "Ply stress histories are retained by QF_solver but are not an acceptance observable in this campaign.",
            ],
        }

    def _plot(self, summary: dict[str, Any]) -> None:
        figure, axes = plt.subplots(1, 3, figsize=(14.2, 4.0))
        modal = summary["modal"]
        modes = np.arange(1, len(modal["qf_frequencies_hz"]) + 1)
        axes[0].plot(modes, modal["qf_frequencies_hz"], "o-", color="#087f5b", label="QF_solver MITC4")
        axes[0].plot(modes, modal["code_aster_frequencies_hz"], "s--", color="#c92a2a", label="Code_Aster DST")
        axes[0].set(xlabel="Mode", ylabel="Frequence [Hz]", title="Modes propres")
        axes[0].grid(alpha=0.25)
        axes[0].legend(fontsize=8)

        newmark = summary["newmark"]
        time = np.arange(len(newmark["qf_tip_uz_m"])) * float(newmark["time_step_s"])
        axes[1].plot(time, newmark["qf_tip_uz_m"], color="#087f5b", label="QF_solver MITC4")
        axes[1].plot(time, newmark["code_aster_tip_uz_m"], "--", color="#c92a2a", label="Code_Aster DST")
        axes[1].set(xlabel="Temps [s]", ylabel="UZ moyen pointe [m]", title="Newmark")
        axes[1].grid(alpha=0.25)
        axes[1].legend(fontsize=8)

        harmonic = summary["harmonic"]
        qf = np.asarray([complex(*value) for value in harmonic["qf_tip_uz_m"]])
        aster = np.asarray([complex(*value) for value in harmonic["code_aster_tip_uz_m"]])
        axes[2].semilogy(harmonic["frequencies_hz"], np.abs(qf), "o-", color="#087f5b", label="QF_solver MITC4")
        axes[2].semilogy(harmonic["frequencies_hz"], np.abs(aster), "s--", color="#c92a2a", label="Code_Aster DST")
        axes[2].set(xlabel="Frequence [Hz]", ylabel="|UZ| moyen pointe [m]", title="Harmonique")
        axes[2].grid(alpha=0.25)
        axes[2].legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc4_laminate_code_aster_comparison.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        root = Path(__file__).resolve().parents[2]
        reference = root / "qualification" / "vnv" / "external" / "code_aster_mitc4_laminate_dynamic" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "report.md", "vnv_manifest.json", "mitc4_laminate_code_aster_comparison.png"):
            shutil.copy2(self.output_dir / name, reference / name)
        assets = root / "docs" / "assets" / "reviews"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.output_dir / "mitc4_laminate_code_aster_comparison.png", assets / "mitc4_laminate_code_aster_comparison.png")


def _modal_analysis() -> dict[str, object]:
    return {"type": "modal", "method": "eigh", "modes": 4, "dense_modal_max_dofs": 6000}


def _tip_nodes(nodes: np.ndarray) -> np.ndarray:
    return np.flatnonzero(np.isclose(nodes[:, 0], np.max(nodes[:, 0]))).astype(np.int64)


def _pulse_table(step: float, steps: int) -> list[dict[str, float]]:
    duration = 0.25 * steps * step
    return [
        {"time": index * step, "factor": math.sin(math.pi * index * step / duration) if index * step <= duration else 0.0}
        for index in range(steps + 1)
    ]


def _code_aster_mesh(model: FiniteElementModel) -> str:
    lines = ["TITRE", "QF_solver MITC4 laminate dynamic correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(model.nodes)
    )
    lines.extend(["FINSF", "QUAD4"])
    lines.extend(
        f"M{index + 1} " + " ".join(f"N{int(node) + 1}" for node in element.nodes)
        for index, element in enumerate(model.elements)
    )
    root = np.flatnonzero(np.isclose(model.nodes[:, 0], np.min(model.nodes[:, 0])))
    tip = np.flatnonzero(np.isclose(model.nodes[:, 0], np.max(model.nodes[:, 0])))
    lines.extend(["FINSF", "GROUP_MA", "SHELL"])
    lines.extend(f"M{index + 1}" for index in range(len(model.elements)))
    lines.extend(["FINSF", "GROUP_NO", "ROOT"])
    lines.extend(f"N{int(node) + 1}" for node in root)
    lines.extend(["FINSF", "GROUP_NO", "TIP"])
    lines.extend(f"N{int(node) + 1}" for node in tip)
    lines.extend(["FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def code_aster_dynamic_comm(
    tip_count: int,
    step: float,
    table: list[dict[str, float]],
    frequencies: list[float],
    *,
    layup: tuple[float, ...] = (0.0, 90.0, 90.0, 0.0),
    rayleigh_alpha: float = 0.0,
) -> str:
    """Return a Code_Aster DST/DEFI_COMPOSITE dynamic deck."""
    times = ", ".join(f"{row['time']:.16g}" for row in table)
    factors = ", ".join(f"{row['time']:.16g}, {row['factor']:.16g}" for row in table)
    frequency_text = ", ".join(f"{value:.16g}" for value in frequencies)
    layers = ",\n        ".join(
        f"_F(EPAIS=0.0025, MATER=lamina, ORIENTATION={angle:.1f})" for angle in layup
    )
    force = -1.0 / tip_count
    damping_definition = (
        f'damping = COMB_MATR_ASSE(COMB_R=_F(MATR_ASSE=mass, COEF_R={rayleigh_alpha:.16g}))\n'
        if rayleigh_alpha > 0.0
        else ""
    )
    damping_argument = ", MATR_AMOR=damping" if rayleigh_alpha > 0.0 else ""
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DST"))
lamina = DEFI_MATERIAU(ELAS_ORTH=_F(E_L=135.0e9, E_T=10.0e9, E_N=10.0e9, NU_LT=0.3, NU_LN=0.3, NU_TN=0.3, G_LT=5.0e9, G_LN=4.5e9, G_TN=3.8e9, RHO=1600.0))
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
{damping_definition}load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=4), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
times = DEFI_LIST_REEL(VALE=({times}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({factors}))
response = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass{damping_argument}, EXCIT=_F(VECT_ASSE=load, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
harmonic = DYNA_VIBRA(TYPE_CALCUL="HARM", BASE_CALCUL="PHYS", MATR_RIGI=rigidity, MATR_MASS=mass{damping_argument}, EXCIT=_F(VECT_ASSE=load, COEF_MULT_C=1.0), FREQ=({frequency_text}))
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


def _damped_decay_ratio(history: np.ndarray, load_table: list[dict[str, float]]) -> float:
    """Return the last-cycle envelope relative to the post-pulse envelope."""
    factors = np.asarray([float(row["factor"]) for row in load_table], dtype=float)
    release_index = int(np.flatnonzero(np.isclose(factors, 0.0))[1])
    post_pulse = np.abs(history[release_index:])
    early_peak = float(np.max(post_pulse[: max(1, post_pulse.size // 2)]))
    late_peak = float(np.max(post_pulse[max(1, post_pulse.size // 2) :]))
    return late_peak / max(early_peak, 1.0e-30)


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
        value = float(item["value"])
        limit = float(item["limit"])
        lines.append(f"| {item['id']} | {value:.4e} | {limit:.4e} | {item['status']} |")
    lines.extend(
        [
            "",
            "Le protocole fige le maillage QUAD4, l'empilement, les proprietes par pli, la densite, les blocages, la table Newmark et la grille harmonique.",
            "La comparaison reste inter-formulation : MITC4 QF_solver et DST Code_Aster ne sont pas algebriquement identiques.",
            "",
            "![Correlation MITC4 multicouche / Code_Aster](mitc4_laminate_code_aster_comparison.png)",
            "",
        ]
    )
    return "\n".join(lines)
