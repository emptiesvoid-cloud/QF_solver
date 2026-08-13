"""Prepared same-mesh Code_Aster DKT correlation for MITC3+ dynamics.

The deck is intentionally external-only: it is executed with the pinned
Docker image when available and otherwise raises ``InfrastructureError``.
No missing backend can ever be reported as a numerical comparison result.
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
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc3 import code_aster_triangle_mesh
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.mitc3_models import rectangular_tri_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterMitc3DynamicsCampaign:
    """Compare bounded MITC3+ modal, Newmark and harmonic responses to DKT."""

    study_id = "VNV-MITC3-DYNAMICS-CODEASTER-DKT-017"
    modal_limit = 0.10
    dynamic_limit = 0.10

    def __init__(self, output_dir: str | Path, *, nx: int = 16, ny: int = 4) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx, self.ny = int(nx), int(ny)
        if self.nx < 4 or self.ny < 1:
            raise ValueError("MITC3 dynamic correlation requires nx >= 4 and ny >= 1.")

    def run(self) -> dict[str, Any]:
        """Run the identical mesh, time grid and frequency grid in Code_Aster."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model, triangles, root, tip = self._model(_modal_analysis())
        modal = solve_model(modal_model, enforce_policy=False)
        first_frequency = float(modal.frequencies_hz[0])
        time_step = 1.0 / first_frequency / 40.0
        steps = 80
        table = _pulse_table(time_step, steps)
        frequencies = [ratio * first_frequency for ratio in (0.10, 0.25, 0.50, 0.75)]
        dynamic_model, _, _, _ = self._model(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "load_table": table,
                "history_probes": [
                    {"node": int(node), "dof": "UZ", "label": f"tip_{node}"}
                    for node in tip
                ],
            },
            total_load=-1.0,
        )
        harmonic_model, _, _, _ = self._model(
            {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies, "rayleigh_alpha": 0.0, "rayleigh_beta": 0.0},
            total_load=-1.0,
        )
        dynamic = solve_model(dynamic_model, enforce_policy=False)
        harmonic = solve_model(harmonic_model, enforce_policy=False)
        stem = "mitc3_dynamic"
        (self.output_dir / f"{stem}.mail").write_text(code_aster_triangle_mesh(modal_model.nodes, triangles, root, tip), encoding="ascii")
        (self.output_dir / f"{stem}.comm").write_text(code_aster_dynamic_comm(len(tip), time_step, steps, table, frequencies), encoding="utf-8")
        run_code_aster(self.output_dir, stem, timeout=1800)
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(
            modal, dynamic, harmonic, raw, time_step, table, frequencies, tip
        )
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _summary(
        self,
        modal: Any,
        dynamic: Any,
        harmonic: Any,
        raw: dict[str, object],
        time_step: float,
        table: list[dict[str, float]],
        frequencies: list[float],
        tip: np.ndarray,
    ) -> dict[str, Any]:
        reference_frequencies = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_frequencies = np.asarray(modal.frequencies_hz[: reference_frequencies.size], dtype=float)
        modal_errors = np.abs(qf_frequencies - reference_frequencies) / np.maximum(np.abs(reference_frequencies), 1.0e-30)
        probe = _tip_mean_history(dynamic.solver["time_history"], tip)
        external_history = _align_history(np.asarray(raw["tip_uz_m"], dtype=float), probe)
        tip_dofs = [harmonic.dofs.index(int(node), "UZ") for node in tip]
        qf_harmonic = np.asarray(
            [np.mean(np.asarray(response, dtype=complex)[tip_dofs]) for response in harmonic.responses],
            dtype=complex,
        )
        external_harmonic = np.asarray(
            [complex(*value) for value in raw["harmonic_tip_uz_m"]], dtype=complex
        )
        checks = [
            _check("modal_frequencies", float(np.max(modal_errors)), self.modal_limit),
            _check("newmark_tip_history", _normalized_rms(probe, external_history), self.dynamic_limit),
            _check("harmonic_tip_response", _complex_normalized_rms(qf_harmonic, external_harmonic), self.dynamic_limit),
        ]
        return {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "WARNING",
            "maturity": "experimental",
            "scope": "MITC3+ isotropic thin-shell same-mesh DKT dynamic correlation",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "DKT/TRIA3"},
            "model": {"mesh": [self.nx, self.ny], "triangles": 2 * self.nx * self.ny, "same_mesh": True, "same_time_grid": True, "same_frequency_grid": True},
            "modal": {"qf_frequencies_hz": qf_frequencies.tolist(), "code_aster_frequencies_hz": reference_frequencies.tolist(), "relative_differences": modal_errors.tolist()},
            "newmark": {"time_step_s": time_step, "steps": len(probe), "load_table": table, "qf_tip_uz_m": probe.tolist(), "code_aster_tip_uz_m": external_history.tolist()},
            "harmonic": {"frequencies_hz": frequencies, "qf_tip_uz_m": [[float(value.real), float(value.imag)] for value in qf_harmonic], "code_aster_tip_uz_m": [[float(value.real), float(value.imag)] for value in external_harmonic]},
            "checks": checks,
            "limitations": [
                "DKT is a Kirchhoff triangle whereas MITC3+ is Reissner-Mindlin; the thin-shell mesh is selected to reduce shear-model differences.",
                "The sweep stays below the first resonance because both zero-damping physical operators are intentionally compared away from singular amplification.",
                "This deck does not correlate curved shells, free-free modes, laminate dynamics, damping or nodal stress histories.",
            ],
        }

    def _model(self, analysis: dict[str, object], *, total_load: float = 0.0) -> tuple[FiniteElementModel, np.ndarray, np.ndarray, np.ndarray]:
        nodes, triangles, node = rectangular_tri_mesh(1.0, 0.2, self.nx, self.ny)
        root = np.asarray([node(0, j) for j in range(self.ny + 1)], dtype=int)
        tip = np.asarray([node(self.nx, j) for j in range(self.ny + 1)], dtype=int)
        return FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[{"type": "MITC3", "nodes": triangle.tolist(), "material": "skin"} for triangle in triangles],
            materials={"skin": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.3, "t": 0.01, "density": 2700.0, "drilling_scale": 1.0e-4}},
            fixed_dofs=[{"node": int(current), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for current in root],
            loads=[{"node": int(current), "dof": "UZ", "value": total_load / len(tip)} for current in tip] if total_load else [],
            analysis=analysis,
            verification_profile="quick",
        ), triangles, root, tip

    def _plot(self, summary: dict[str, Any]) -> None:
        """Create readable modal, transient and harmonic comparison figures."""
        modal = summary["modal"]
        figure, axes = plt.subplots(1, 3, figsize=(14.0, 3.8))
        modes = np.arange(1, len(modal["qf_frequencies_hz"]) + 1)
        axes[0].plot(modes, modal["qf_frequencies_hz"], "o-", label="QF_solver")
        axes[0].plot(modes, modal["code_aster_frequencies_hz"], "s--", label="Code_Aster DKT")
        axes[0].set(xlabel="Mode", ylabel="Frequence [Hz]", title="Modes propres")
        axes[0].legend(fontsize=8)

        newmark = summary["newmark"]
        time = np.arange(len(newmark["qf_tip_uz_m"])) * float(newmark["time_step_s"])
        axes[1].plot(time, newmark["qf_tip_uz_m"], label="QF_solver")
        axes[1].plot(time, newmark["code_aster_tip_uz_m"], "--", label="Code_Aster DKT")
        axes[1].set(xlabel="Temps [s]", ylabel="UZ moyen pointe [m]", title="Newmark")
        axes[1].legend(fontsize=8)

        harmonic = summary["harmonic"]
        qf = np.asarray([complex(*value) for value in harmonic["qf_tip_uz_m"]])
        aster = np.asarray([complex(*value) for value in harmonic["code_aster_tip_uz_m"]])
        axes[2].plot(harmonic["frequencies_hz"], np.abs(qf), "o-", label="QF_solver")
        axes[2].plot(harmonic["frequencies_hz"], np.abs(aster), "s--", label="Code_Aster DKT")
        axes[2].set(xlabel="Frequence [Hz]", ylabel="|UZ| moyen pointe [m]", title="Harmonique")
        axes[2].legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "comparison.png", dpi=180)
        plt.close(figure)


def _modal_analysis() -> dict[str, object]:
    return {"type": "modal", "method": "eigh", "modes": 6, "dense_modal_max_dofs": 6000}


def _pulse_table(step: float, steps: int) -> list[dict[str, float]]:
    duration = 0.25 * steps * step
    return [{"time": index * step, "factor": math.sin(math.pi * index * step / duration) if index * step <= duration else 0.0} for index in range(steps + 1)]


def code_aster_dynamic_comm(tip_count: int, step: float, steps: int, table: list[dict[str, float]], frequencies: list[float]) -> str:
    """Create a DKT deck with modal, Newmark and sub-resonant harmonic outputs."""
    times = ", ".join(f"{row['time']:.16g}" for row in table)
    factors = ", ".join(f"{row['time']:.16g}, {row['factor']:.16g}" for row in table)
    frequency_text = ", ".join(f"{value:.16g}" for value in frequencies)
    force = -1.0 / tip_count
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", PHENOMENE="MECANIQUE", MODELISATION="DKT"))
material = DEFI_MATERIAU(ELAS=_F(E=7.0e10, NU=0.3, RHO=2700.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SHELL", MATER=material))
shell = AFFE_CARA_ELEM(MODELE=model, COQUE=_F(GROUP_MA="SHELL", EPAIS=0.01))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FZ={force:.16g}))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CARA_ELEM=shell, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=6), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
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


def _align_history(external: np.ndarray, observed: np.ndarray) -> np.ndarray:
    if external.size == observed.size + 1:
        external = external[1:]
    if external.size != observed.size:
        raise RuntimeError(f"Code_Aster returned {external.size} samples for {observed.size} QF_solver steps.")
    return external


def _tip_mean_history(history: list[dict[str, Any]], tip: np.ndarray) -> np.ndarray:
    """Return the mean ``UZ`` history on the physical tip group."""
    labels = [f"tip_{int(node)}" for node in tip]
    return np.asarray(
        [
            np.mean([float(row["probes"][label]["displacement"]) for label in labels])
            for row in history
        ],
        dtype=float,
    )


def _normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _complex_normalized_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Controle | Ecart QF_solver / Code_Aster |", "| --- | ---: |"]
    for row in summary["checks"]:
        lines.append(f"| {row['id']} | {100.0 * row['value']:.4g} % |")
    lines.extend(["", "Le protocole impose meme maillage, materiau, epaisseur, conditions limites, table temporelle et grille frequentielle. DKT et MITC3+ restent des formulations distinctes.", ""])
    return "\n".join(lines)
