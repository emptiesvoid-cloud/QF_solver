"""External Code_Aster correlation for a curved axial one-ply MITC4 panel."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_mitc4_laminate_dynamic import (
    CODE_ASTER_IMAGE,
    _align_history,
    _check,
    _code_aster_mesh,
    _complex_rows,
    _normalized_rms,
    code_aster_dynamic_comm,
)
from solveur.verification.code_aster_tl_structural import run_code_aster
from solveur.verification.mitc4_orthotropic_curved_dynamic import (
    Mitc4OrthotropicCurvedDynamicStudy,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC4-ORTHOTROPIC-CURVED-DYNAMIC-CODEASTER-001"


class CodeAsterMitc4OrthotropicCurvedDynamicCampaign:
    """Compare modal, forced Newmark and harmonic responses on the same panel."""

    modal_limit = 0.05
    transient_limit = 0.10
    harmonic_limit = 0.10

    def __init__(
        self,
        output_dir: str | Path,
        *,
        mesh: tuple[int, int] = (8, 4),
        angle_deg: float = 0.0,
        modal_method: str = "eigh",
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.study = Mitc4OrthotropicCurvedDynamicStudy(
            mesh=mesh, angle_deg=angle_deg, modal_method=modal_method
        )
        self.mesh = mesh
        self.angle_deg = float(angle_deg)

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model, nodes = self._build(
            {"type": "modal", "method": self.study.modal_method, "modes": 4}
        )
        modal = solve_model(modal_model, enforce_policy=False)
        f1 = float(modal.frequencies_hz[0])
        dt = 1.0 / f1 / 40.0
        steps = 80
        times = np.arange(steps + 1, dtype=float) * dt
        factors = np.sin(np.pi * times / max(times[-1], 1.0e-30))
        frequencies = [ratio * f1 for ratio in (0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0)]
        tip = _nodes_at_x_array(nodes, float(np.max(nodes[:, 0])))
        load_table = [
            {"time": float(time), "factor": float(factor)}
            for time, factor in zip(times, factors)
        ]
        alpha = 2.0 * 0.02 * 2.0 * math.pi * f1
        transient_model, _ = self._build(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": dt,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "load_table": load_table,
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
                "history_probes": [
                    {"node": int(node), "dof": "UY", "label": f"tip_{int(node)}"}
                    for node in tip
                ],
            },
            total_load=-1.0,
        )
        harmonic_model, _ = self._build(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies,
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
            },
            total_load=-1.0,
        )
        transient = solve_model(transient_model, enforce_policy=False)
        harmonic = solve_model(harmonic_model, enforce_policy=False)
        stem = "mitc4_orthotropic_curved_dynamic"
        (self.output_dir / f"{stem}.mail").write_text(_code_aster_mesh(modal_model), encoding="ascii")
        (self.output_dir / f"{stem}.comm").write_text(
            code_aster_dynamic_comm(
                len(tip), dt, load_table, frequencies,
                layup=(self.angle_deg,), ply_thickness=1.0e-2,
                rayleigh_alpha=alpha, probe_dof="UY",
            ),
            encoding="utf-8",
        )
        run_code_aster(self.output_dir, stem, timeout=1800)
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        aligned = self._aligned_harmonic(nodes, tip, raw, alpha)
        summary = self._summary(
            modal, transient, harmonic, raw, aligned, tip, f1, dt, frequencies, alpha
        )
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(self._report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _build(
        self, analysis: dict[str, object], *, total_load: float = 0.0
    ) -> tuple[FiniteElementModel, np.ndarray]:
        model, nodes = self.study.build_model()
        model.analysis = AnalysisSettings.from_raw(analysis)
        if total_load:
            tip = _nodes_at_x_array(nodes, float(np.max(nodes[:, 0])))
            model.loads = [NodalLoad(node=int(node), dof="UY", value=total_load / len(tip)) for node in tip]
        return model, nodes

    def _summary(
        self, modal: Any, transient: Any, harmonic: Any, raw: dict[str, Any],
        aligned: dict[str, Any], tip: list[int], f1: float, dt: float,
        frequencies: list[float], alpha: float,
    ) -> dict[str, Any]:
        aster_f = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_f = np.asarray(modal.frequencies_hz[: aster_f.size], dtype=float)
        modal_error = np.abs(qf_f - aster_f) / np.maximum(np.abs(aster_f), 1.0e-30)
        qf_history = _mean_history(transient.solver["time_history"], tip)
        aster_history = _align_history(np.asarray(raw["tip_uy_m"], dtype=float), qf_history)
        tip_dofs = [harmonic.dofs.index(int(node), "UY") for node in tip]
        qf_harmonic = np.asarray(
            [np.mean(np.asarray(row, dtype=complex)[tip_dofs]) for row in harmonic.responses],
            dtype=complex,
        )
        aster_harmonic = np.asarray([complex(*row) for row in raw["harmonic_tip_uy_m"]], dtype=complex)
        checks = [
            _check("modal_frequencies", float(np.max(modal_error)), self.modal_limit),
            _check("newmark_tip_history", _normalized_rms(qf_history, aster_history), self.transient_limit),
            _check("harmonic_frequency_aligned_response", float(aligned["relative_rms"]), self.harmonic_limit),
            _check("qf_modal_residual", float(modal.solver["max_relative_residual"]), 1.0e-7),
            _check("qf_dynamic_residual", _max_residual(transient), 1.0e-7),
        ]
        return {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "WARNING",
            "maturity": "verified_development_external_correlation",
            "scope": "faceted cylindrical MITC4 one-ply orthotropic axial orientation",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": "DST / QUAD4"},
            "model": {"mesh": list(self.mesh), "elements": self.mesh[0] * self.mesh[1], "angle_deg": self.angle_deg, "probe_dof": "UY"},
            "damping": {"rayleigh_alpha": alpha, "rayleigh_beta": 0.0},
            "modal": {"qf_frequencies_hz": qf_f.tolist(), "code_aster_frequencies_hz": aster_f.tolist(), "relative_differences": modal_error.tolist()},
            "newmark": {"time_step_s": dt, "qf_tip_uy_m": qf_history.tolist(), "code_aster_tip_uy_m": aster_history.tolist()},
            "harmonic": {"frequencies_hz": frequencies, "qf_tip_uy_m": _complex_rows(qf_harmonic), "code_aster_tip_uy_m": _complex_rows(aster_harmonic)},
            "harmonic_aligned": aligned,
            "harmonic_pointwise_diagnostic": {
                "frequencies_hz": frequencies,
                "relative_rms": _complex_rms(qf_harmonic, aster_harmonic),
                "interpretation": "Diagnostic sensible au décalage de fréquence propre; non utilisé comme critère principal.",
            },
            "checks": checks,
            "limitations": [
                "The comparison is axial 0 degree only; projected non-axial curved orientation remains outside the stable scope.",
                "Code_Aster DST and QF_solver MITC4 are distinct shell formulations.",
                "Damage, rupture, delamination and large deformation are excluded.",
            ],
        }

    def _aligned_harmonic(
        self, nodes: np.ndarray, tip: list[int], raw: dict[str, Any], alpha: float
    ) -> dict[str, Any]:
        """Compare both solvers on Code_Aster's normalized frequency grid."""
        aster_f1 = float(raw["frequencies_hz"][0])
        ratios = np.asarray((0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0), dtype=float)
        frequencies = (ratios * aster_f1).tolist()
        model, _ = self._build(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies,
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
            },
            total_load=-1.0,
        )
        qf_result = solve_model(model, enforce_policy=False)
        tip_dofs = [qf_result.dofs.index(int(node), "UY") for node in tip]
        qf_values = np.asarray(
            [np.mean(np.asarray(row, dtype=complex)[tip_dofs]) for row in qf_result.responses],
            dtype=complex,
        )
        work = self.output_dir / "frequency_aligned"
        work.mkdir(parents=True, exist_ok=True)
        mesh_model, _ = self._build({"type": "modal", "method": "eigh", "modes": 4})
        stem = "mitc4_orthotropic_curved_dynamic_aligned"
        (work / f"{stem}.mail").write_text(_code_aster_mesh(mesh_model), encoding="ascii")
        (work / f"{stem}.comm").write_text(
            code_aster_dynamic_comm(
                len(tip), 1.0e-3,
                [{"time": 0.0, "factor": 0.0}, {"time": 1.0e-3, "factor": 1.0}],
                frequencies, layup=(self.angle_deg,), ply_thickness=1.0e-2,
                rayleigh_alpha=alpha, probe_dof="UY",
            ),
            encoding="utf-8",
        )
        run_code_aster(work, stem, timeout=1800)
        aster_raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_values = np.asarray(
            [complex(*row) for row in aster_raw["harmonic_tip_uy_m"]], dtype=complex
        )
        return {
            "frequency_ratios": ratios.tolist(),
            "frequencies_hz": frequencies,
            "qf_tip_uy_m": _complex_rows(qf_values),
            "code_aster_tip_uy_m": _complex_rows(aster_values),
            "relative_rms": _complex_rms(qf_values, aster_values),
            "reference_frequency_hz": aster_f1,
            "comparison": "same normalized frequency ratios on the external first frequency",
        }

    @staticmethod
    def _report(summary: dict[str, Any]) -> str:
        lines = [f"# {STUDY_ID}", "", f"Statut : **{summary['status']}**", "", "| Contrôle | Valeur | Seuil | Statut |", "|---|---:|---:|---|"]
        lines.extend(f"| {row['id']} | {row['value']:.6e} | {row['limit']:.6e} | {row['status']} |" for row in summary["checks"])
        lines.extend(["", "La corrélation est réalisée sur la même géométrie facettisée, le même maillage, les mêmes propriétés, blocages et chargements.", "La comparaison dynamique courbe est limitée à l'orientation axiale 0 degré."])
        return "\n".join(lines) + "\n"


def _mean_history(history: list[dict[str, Any]], tip: list[int]) -> np.ndarray:
    return np.asarray([np.mean([float(row["probes"][f"tip_{node}"]["displacement"]) for node in tip]) for row in history], dtype=float)


def _nodes_at_x_array(nodes: np.ndarray, value: float) -> list[int]:
    return [int(index) for index in np.flatnonzero(np.isclose(nodes[:, 0], value))]


def _complex_rms(observed: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(observed - reference) ** 2)) / max(float(np.max(np.abs(reference))), 1.0e-30))


def _max_residual(result: Any) -> float:
    return max(float(row["dynamic_residual_norm"]) for row in result.solver["time_history"])
