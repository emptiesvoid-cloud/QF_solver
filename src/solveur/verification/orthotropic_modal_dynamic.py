"""Modal and Newmark V&V for linear orthotropic TET4 solids."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.materials.solid import SolidConstitutiveMaterial
from solveur.verification.code_aster_tl_structural import code_aster_mesh, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class OrthotropicModalDynamicCampaign:
    """Verify axial modal and transient paths with an analytical and Code_Aster oracle."""

    study_id = "VNV-ORTHOTROPIC-MODAL-NEWMARK-010"

    def __init__(self, output_dir: str | Path, *, cells: tuple[int, ...] = (4, 8, 16)) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.cells = tuple(int(value) for value in cells)
        if len(self.cells) < 3 or any(value <= 0 for value in self.cells):
            raise ValueError("Orthotropic modal campaign requires at least three positive mesh levels.")

    def run(self, *, run_code_aster_external: bool = True) -> dict[str, Any]:
        """Execute all internal checks and optionally the same-mesh Code_Aster correlation."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_rows = [self._modal_row(cells) for cells in self.cells]
        dynamic_rows = [self._dynamic_row(step) for step in (2.0e-3, 1.0e-3, 5.0e-4, 2.5e-4, 1.25e-4, 6.25e-5)]
        external = self._code_aster_correlation(self.cells[-1]) if run_code_aster_external else None
        checks = _checks(modal_rows, dynamic_rows, external)
        status = "PASS_TECHNICAL_VERIFICATION" if all(row["status"] == "PASS" for row in checks) else "FAIL"
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": status,
            "maturity": "technical_verification",
            "scope": ["orthotropic-solid-modal", "orthotropic-solid-transient-dynamic"],
            "element": "TET4",
            "material": _material_data(),
            "modal": {"analytical_frequency_hz": _analytical_frequency(), "rows": modal_rows},
            "newmark": {"duration_s": _DURATION, "rows": dynamic_rows},
            "code_aster": external,
            "checks": checks,
            "limitations": [
                "The axial reduction constrains UY and UZ to isolate one analytical 3D material direction.",
                "The external comparison is same-mesh and same time grid; it does not replace a curved or multiaxial validation.",
                "Damage, delamination, anisotropic plasticity and large deformation remain outside this scope.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plots(summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _modal_row(self, cells: int) -> dict[str, Any]:
        model = _axial_model(cells, {"type": "modal", "method": "eigh", "modes": 2})
        result = solve_model(model)
        frequency = float(result.frequencies_hz[0])
        theoretical = _analytical_frequency()
        return {
            "cells": cells,
            "nodes": model.node_count,
            "elements": len(model.elements),
            "frequency_hz": frequency,
            "relative_error_theory": _relative(frequency, theoretical),
            "modal_residual": float(result.solver["max_relative_residual"]),
            "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
        }

    def _dynamic_row(self, step: float) -> dict[str, Any]:
        model = _axial_model(
            self.cells[-1],
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": step,
                "steps": round(_DURATION / step),
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": 0.0,
                "rayleigh_beta": 0.0,
                "load_table": _load_table(step),
                "history_probes": [{"node": _tip_node(self.cells[-1]), "dof": "UX", "label": "tip_ux"}],
            },
        )
        result = solve_model(model)
        history = result.solver["time_history"]
        values = np.asarray([row["probes"]["tip_ux"]["displacement"] for row in history], dtype=float)
        drifts = np.asarray([row["relative_energy_drift"] for row in history], dtype=float)
        return {
            "time_step_s": step,
            "step_count": len(history),
            "tip_displacement_m": values.tolist(),
            "max_tip_displacement_m": float(np.max(np.abs(values))),
            "max_energy_drift": float(np.max(np.abs(drifts))),
            "max_dynamic_residual": float(max(result.solver["residual_history"], default=0.0)),
        }

    def _code_aster_correlation(self, cells: int) -> dict[str, Any]:
        work = self.output_dir / "code_aster"
        work.mkdir(parents=True, exist_ok=True)
        modal_model = _axial_model(cells, {"type": "modal", "method": "eigh", "modes": 2})
        qf_modal = solve_model(modal_model)
        dynamic_model = _axial_model(
            cells,
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": 2.5e-4,
                "steps": round(_DURATION / 2.5e-4),
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": 0.0,
                "rayleigh_beta": 0.0,
                "load_table": _load_table(2.5e-4),
                "history_probes": [{"node": _tip_node(cells), "dof": "UX", "label": "tip_ux"}],
            },
        )
        qf_dynamic = solve_model(dynamic_model)
        nodes, elements = _mesh(cells)
        fixed, tip = _boundary_nodes(nodes)
        (work / "orthotropic.mail").write_text(
            code_aster_mesh(
                nodes,
                elements,
                (fixed + 1).tolist(),
                groups={"FIXED": (fixed + 1).tolist(), "TIP": [tip + 1]},
            ),
            encoding="ascii",
        )
        (work / "orthotropic.comm").write_text(_code_aster_commands(tip), encoding="utf-8")
        run_code_aster(work, "orthotropic")
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        qf_frequency = np.asarray(qf_modal.frequencies_hz[:2], dtype=float)
        aster_frequency = np.asarray(raw["frequencies_hz"][:2], dtype=float)
        qf_history = np.asarray(
            [row["probes"]["tip_ux"]["displacement"] for row in qf_dynamic.solver["time_history"]], dtype=float
        )
        aster_history = _align_external_history(np.asarray(raw["tip_ux_m"], dtype=float), qf_history)
        return {
            "solver": {"name": "Code_Aster", "version": "18.1.0", "element": "TETRA4"},
            "same_mesh": True,
            "same_time_grid": True,
            "frequency_relative_difference": _relative_vector(qf_frequency, aster_frequency),
            "transient_normalized_rms_difference": _normalized_rms(qf_history, aster_history),
            "transient_peak_difference": _relative(float(np.max(np.abs(qf_history))), float(np.max(np.abs(aster_history))), reference_first=True),
            "qf_frequencies_hz": qf_frequency.tolist(),
            "code_aster_frequencies_hz": aster_frequency.tolist(),
            "qf_tip_ux_m": qf_history.tolist(),
            "code_aster_tip_ux_m": aster_history.tolist(),
        }

    def _plots(self, summary: dict[str, Any]) -> None:
        import matplotlib.pyplot as plt

        modal = summary["modal"]
        rows = modal["rows"]
        figure, axis = plt.subplots(figsize=(6.8, 4.2))
        axis.loglog([row["elements"] for row in rows], [row["relative_error_theory"] for row in rows], "o-", label="QF_solver")
        axis.set(xlabel="Nombre de TET4", ylabel="Erreur relative frequence", title="Convergence modale orthotrope")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "modal_convergence.png", dpi=180)
        plt.close(figure)

        dynamic = summary["newmark"]["rows"]
        figure, axis = plt.subplots(figsize=(7.2, 4.4))
        for row in dynamic:
            values = np.asarray(row["tip_displacement_m"], dtype=float)
            local_times = np.linspace(_DURATION / len(values), _DURATION, len(values))
            axis.plot(local_times, values, label=f"dt={row['time_step_s']:.4g} s")
        axis.set(xlabel="Temps [s]", ylabel="UX pointe [m]", title="Convergence Newmark orthotrope")
        axis.grid(True, alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "newmark_convergence.png", dpi=180)
        plt.close(figure)

        external = summary["code_aster"]
        if external is not None:
            times = np.linspace(_DURATION / len(external["qf_tip_ux_m"]), _DURATION, len(external["qf_tip_ux_m"]))
            figure, axis = plt.subplots(figsize=(7.2, 4.4))
            axis.plot(times, external["qf_tip_ux_m"], label="QF_solver Newmark")
            axis.plot(times, external["code_aster_tip_ux_m"], "--", label="Code_Aster Newmark")
            axis.set(xlabel="Temps [s]", ylabel="UX pointe [m]", title="Correlation transitoire orthotrope")
            axis.grid(True, alpha=0.25)
            axis.legend()
            figure.tight_layout()
            figure.savefig(self.output_dir / "code_aster_newmark.png", dpi=180)
            plt.close(figure)

    def _write_report(self, summary: dict[str, Any]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Verdict automatise : **{summary['status']}**.",
            "",
            "## Modal",
            "",
            "| TET4 | Frequence QF [Hz] | Erreur theorie | Residu | Orthogonalite masse |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["modal"]["rows"]:
            lines.append(f"| {row['elements']} | {row['frequency_hz']:.6f} | {100*row['relative_error_theory']:.3f} % | {row['modal_residual']:.3e} | {row['mass_orthogonality_error']:.3e} |")
        lines.extend(["", "![Convergence modale](modal_convergence.png)", "", "## Newmark", "", "| Pas [s] | Pic UX [m] | Derive energie max | Residu dynamique max |", "| ---: | ---: | ---: | ---: |"])
        for row in summary["newmark"]["rows"]:
            lines.append(f"| {row['time_step_s']:.6g} | {row['max_tip_displacement_m']:.6e} | {row['max_energy_drift']:.3e} | {row['max_dynamic_residual']:.3e} |")
        lines.extend(["", "![Convergence Newmark](newmark_convergence.png)", ""])
        if summary["code_aster"] is not None:
            external = summary["code_aster"]
            lines.extend([
                "## Code_Aster", "",
                f"- ecart frequences : `{100*external['frequency_relative_difference']:.4f} %` ;",
                f"- RMS histoire UX : `{100*external['transient_normalized_rms_difference']:.4f} %` ;",
                f"- ecart pic UX : `{100*external['transient_peak_difference']:.4f} %`.", "",
                "![Correlation Newmark](code_aster_newmark.png)", "",
            ])
        lines.extend(["## Limites", "", *[f"- {item}" for item in summary["limitations"]], ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


_LENGTH = 1.0
_HEIGHT = 0.08
_DEPTH = 0.08
_DURATION = 0.02


def _material_data() -> dict[str, Any]:
    return {"type": "orthotropic_3d", "E1": 145.0e9, "E2": 12.0e9, "E3": 9.0e9, "nu12": 0.24, "nu13": 0.21, "nu23": 0.28, "G12": 5.5e9, "G13": 4.8e9, "G23": 3.9e9, "density": 1580.0}


def _axial_model(cells: int, analysis: dict[str, Any]) -> FiniteElementModel:
    nodes, elements = _mesh(cells)
    fixed, tip = _boundary_nodes(nodes)
    constraints = [{"node": int(node), "dofs": ["UY", "UZ"]} for node in range(nodes.shape[0])]
    constraints.extend({"node": int(node), "dofs": ["UX"]} for node in fixed)
    loads = [{"node": tip, "dof": "UX", "value": 1000.0}] if analysis["type"] == "transient_dynamic" else []
    return FiniteElementModel.from_raw(nodes=nodes.tolist(), elements=[{"type": "TET4", "nodes": element.tolist(), "material": "ortho"} for element in elements], materials={"ortho": _material_data()}, analysis=analysis, fixed_dofs=constraints, loads=loads)


def _mesh(cells: int) -> tuple[np.ndarray, np.ndarray]:
    nodes = np.array([[i * _LENGTH / cells, y, z] for i in range(cells + 1) for y in (0.0, _HEIGHT) for z in (0.0, _DEPTH)], dtype=float)
    elements: list[list[int]] = []
    for index in range(cells):
        start = 4 * index
        cube = (start, start + 4, start + 2, start + 6, start + 1, start + 5, start + 3, start + 7)
        for local in ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7)):
            elements.append([cube[value] for value in local])
    return nodes, np.asarray(elements, dtype=np.int64)


def _boundary_nodes(nodes: np.ndarray) -> tuple[np.ndarray, int]:
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = int(np.flatnonzero(np.isclose(nodes[:, 0], _LENGTH))[0])
    return fixed.astype(np.int64), tip


def _tip_node(cells: int) -> int:
    return 4 * cells


def _analytical_frequency() -> float:
    material = MaterialFactory.create(_material_data())
    assert isinstance(material, SolidConstitutiveMaterial)
    c11 = float(material.elasticity_matrix[0, 0])
    return math.sqrt(c11 / material.density) / (4.0 * _LENGTH)


def _load_table(step: float) -> list[dict[str, float]]:
    times = np.arange(0.0, _DURATION + 0.5 * step, step)
    return [
        {"time": float(time), "factor": math.sin(math.pi * time / 0.005) if time <= 0.005 else 0.0}
        for time in times
    ]


def _code_aster_commands(tip: int) -> str:
    times = _load_table(2.5e-4)
    values = ", ".join(f"{item['time']:.16g}, {item['factor']:.16g}" for item in times)
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS_ORTH=_F(E_L=145.0e9, E_T=12.0e9, E_N=9.0e9, NU_LT=0.24, NU_LN=0.21, NU_TN=0.28, G_LT=5.5e9, G_LN=4.8e9, G_TN=3.9e9, RHO=1580.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(_F(GROUP_NO="NALL", DY=0.0, DZ=0.0), _F(GROUP_NO="FIXED", DX=0.0)))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="TIP", FX=1000.0))
rig_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rig_e)
rig = ASSE_MATRICE(MATR_ELEM=rig_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rig, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=2), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
times = DEFI_LIST_REEL(VALE=({', '.join(f"{item['time']:.16g}" for item in times)}))
function = DEFI_FONCTION(NOM_PARA="INST", PROL_GAUCHE="CONSTANT", PROL_DROITE="CONSTANT", VALE=({values}))
response = DYNA_VIBRA(TYPE_CALCUL="TRAN", BASE_CALCUL="PHYS", MATR_RIGI=rig, MATR_MASS=mass, EXCIT=_F(VECT_ASSE=load, FONC_MULT=function), INCREMENT=_F(LIST_INST=times), SCHEMA_TEMPS=_F(SCHEMA="NEWMARK", BETA=0.25, GAMMA=0.5))
raw = {{"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]], "tip_ux_m": []}}
for order in response.getIndexes():
    field_u = response.getField("DEPL", order)
    values_u, _ = field_u.getValuesWithDescription("DX", ["TIP"])
    raw["tip_ux_m"].append(float(values_u[0]))
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _checks(modal: list[dict[str, Any]], dynamic: list[dict[str, Any]], external: dict[str, Any] | None) -> list[dict[str, Any]]:
    reference = np.asarray(dynamic[-1]["tip_displacement_m"], dtype=float)
    rows = [
        _upper("modal_fine_theory", modal[-1]["relative_error_theory"], 0.03),
        _upper("modal_refinement", modal[-1]["relative_error_theory"] / max(modal[0]["relative_error_theory"], 1e-30), 0.50),
        _upper("modal_residual", modal[-1]["modal_residual"], 1.0e-8),
        _upper("modal_mass_orthogonality", modal[-1]["mass_orthogonality_error"], 1.0e-8),
        _upper("newmark_time_refinement", _normalized_rms(np.asarray(dynamic[-2]["tip_displacement_m"]), reference[::2]), 0.05),
        _upper("newmark_residual", max(row["max_dynamic_residual"] for row in dynamic), 1.0e-7),
    ]
    if external is not None:
        rows.extend([_upper("code_aster_modal", external["frequency_relative_difference"], 1.0e-6), _upper("code_aster_newmark", external["transient_normalized_rms_difference"], 1.0e-5)])
    return rows


def _upper(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if value <= limit else "FAIL"}


def _relative(value: float, reference: float, *, reference_first: bool = False) -> float:
    denominator = value if reference_first else reference
    return abs(value - reference) / max(abs(denominator), np.finfo(float).tiny)


def _relative_vector(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), np.finfo(float).tiny))


def _normalized_rms(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((value - reference) ** 2)) / max(np.max(np.abs(reference)), np.finfo(float).tiny))


def _align_external_history(external: np.ndarray, qf_history: np.ndarray) -> np.ndarray:
    """Align Code_Aster's optional t=0 sample with QF_solver's step history."""
    if external.size == qf_history.size + 1:
        external = external[1:]
    if external.size != qf_history.size:
        raise RuntimeError(
            "Code_Aster returned an incompatible transient history: "
            f"{external.size} samples for {qf_history.size} QF_solver steps."
        )
    return external
