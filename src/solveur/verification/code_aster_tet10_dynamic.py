"""Same-mesh Code_Aster TETRA10 correlation for linear TET10 dynamics.

The campaign deliberately separates three kinds of evidence:

* a spatial convergence study on a genuinely three-dimensional cantilever;
* a Newmark time-step study on the retained mesh;
* Code_Aster ``TETRA10`` comparisons using the exact same nodal mesh, clamp,
  resultant, time grid and frequency grid.

It is a bounded small-strain, isotropic-solid correlation.  The base campaign
is undamped; the dedicated damped subclass enables mass-proportional Rayleigh
damping with the same formulation and external protocol.
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
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterTet10DynamicsCampaign:
    """Compare a structural TET10 modal, Newmark and harmonic route to Aster."""

    study_id = "VNV-TET10-DYNAMICS-CODEASTER-TETRA10-018"
    external_limit = 0.05
    convergence_limit = 0.10
    element_type = "TET10"
    aster_element_type = "TETRA10"
    gmsh_order = 2
    deck_stem = "tet10_dynamic"
    require_static_spatial_convergence = True
    geometry_label = "rectangular cantilever"
    damping_ratio = 0.0

    def __init__(
        self,
        output_dir: str | Path,
        *,
        mesh_size: float = 0.60,
        length: float = 4.0,
        width: float = 0.4,
        height: float = 0.4,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.mesh_size = float(mesh_size)
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self._tip_load_weights: np.ndarray | None = None
        if not 0.20 <= self.mesh_size <= 1.00:
            raise ValueError("TET10 dynamic correlation mesh_size must be in [0.20, 1.00].")
        if min(self.length, self.width, self.height) <= 0.0:
            raise ValueError("TET10 dynamic geometry dimensions must be positive.")

    def run(self) -> dict[str, Any]:
        """Run internal mesh/time controls and the pinned external same-mesh deck."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        convergence = self._spatial_convergence()
        model, root, tip = self._model(self.mesh_size, _modal_analysis())
        modal = solve_model(model, enforce_policy=False)
        first_frequency = float(modal.frequencies_hz[0])
        damping = self._damping_parameters(first_frequency)
        time = self._time_convergence(first_frequency, damping)
        frequencies = [0.10 * first_frequency, 0.25 * first_frequency, 0.50 * first_frequency, 0.75 * first_frequency]
        table = _pulse_table(1.0 / first_frequency / 40.0, 80)
        dynamic = solve_model(
            self._model(
                self.mesh_size,
                _newmark_analysis(
                    1.0 / first_frequency / 40.0, 80, table, tip,
                    rayleigh_alpha=damping["rayleigh_alpha_s_inv"],
                    rayleigh_beta=damping["rayleigh_beta_s"],
                ),
                total_load=-1.0,
            )[0],
            enforce_policy=False,
        )
        harmonic = solve_model(
            self._model(
                self.mesh_size,
                _harmonic_analysis(
                    frequencies,
                    rayleigh_alpha=damping["rayleigh_alpha_s_inv"],
                    rayleigh_beta=damping["rayleigh_beta_s"],
                ),
                total_load=-1.0,
            )[0],
            enforce_policy=False,
        )
        stem = self.deck_stem
        (self.output_dir / f"{stem}.mail").write_text(
            self._code_aster_mesh(model.nodes, model.elements, root, tip), encoding="ascii"
        )
        (self.output_dir / f"{stem}.comm").write_text(
            self._code_aster_comm(
                tip, table, frequencies,
                rayleigh_alpha=damping["rayleigh_alpha_s_inv"],
                rayleigh_beta=damping["rayleigh_beta_s"],
            ), encoding="utf-8"
        )
        run_code_aster(self.output_dir, stem, timeout=1800)
        raw = json.loads((self.output_dir / "code_aster_raw.json").read_text(encoding="utf-8"))
        summary = self._summary(
            model, modal, dynamic, harmonic, raw, convergence, time, table, frequencies, tip, damping
        )
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _spatial_convergence(self) -> dict[str, Any]:
        """Measure modal and static tip convergence on three TET10 meshes."""
        rows: list[dict[str, float | int]] = []
        for mesh_size in self._spatial_mesh_sizes():
            modal_model, _, tip = self._model(mesh_size, _modal_analysis())
            modal = solve_model(modal_model, enforce_policy=False)
            static = solve_model(
                self._model(mesh_size, "linear_static", total_load=-1.0)[0],
                enforce_policy=False,
            )
            rows.append(
                {
                    "mesh_size": mesh_size,
                    "nodes": modal_model.node_count,
                    "elements": len(modal_model.elements),
                    "frequency_hz": float(modal.frequencies_hz[0]),
                    "mean_tip_uz_m": _mean_displacement(static.displacements, static.dofs, tip),
                }
            )
        final = rows[-1]
        previous = rows[-2]
        return {
            "levels": rows,
            "frequency_final_increment": _relative(float(final["frequency_hz"]), float(previous["frequency_hz"])),
            "static_tip_final_increment": _relative(float(final["mean_tip_uz_m"]), float(previous["mean_tip_uz_m"])),
        }

    def _spatial_mesh_sizes(self) -> tuple[float, float, float]:
        """Return coarse, retained and fine sizes in decreasing element size."""
        return (0.85, self.mesh_size, 0.42)

    def _damping_parameters(self, frequency: float) -> dict[str, float]:
        """Return mass-proportional Rayleigh damping fitted to mode one."""
        ratio = float(self.damping_ratio)
        if ratio < 0.0 or ratio >= 1.0:
            raise ValueError("TET10 damping_ratio must be in [0, 1).")
        # For C = alpha M, zeta_1 = alpha / (2 omega_1).
        return {
            "target_modal_damping_ratio": ratio,
            "rayleigh_alpha_s_inv": 4.0 * math.pi * ratio * frequency,
            "rayleigh_beta_s": 0.0,
        }

    def _time_convergence(
        self, frequency: float, damping: dict[str, float] | None = None
    ) -> dict[str, Any]:
        """Use a fine Newmark response as the controlled time discretisation reference."""
        points: list[dict[str, Any]] = []
        reference_times: np.ndarray | None = None
        reference_values: np.ndarray | None = None
        damping = damping or self._damping_parameters(frequency)
        for steps_per_period in (20, 40, 80, 160):
            step = 1.0 / frequency / steps_per_period
            steps = 2 * steps_per_period
            _, _, tip = self._model(self.mesh_size, _modal_analysis())
            table = _pulse_table(step, steps)
            result = solve_model(
                self._model(
                    self.mesh_size,
                    _newmark_analysis(
                        step, steps, table, tip,
                        rayleigh_alpha=damping["rayleigh_alpha_s_inv"],
                        rayleigh_beta=damping["rayleigh_beta_s"],
                    ),
                    total_load=-1.0,
                )[0],
                enforce_policy=False,
            )
            times = np.asarray([row["time"] for row in result.solver["time_history"]], dtype=float)
            values = _mean_history(result.solver["time_history"], tip)
            if steps_per_period == 160:
                reference_times, reference_values = times, values
                error = 0.0
            else:
                assert reference_times is None and reference_values is None
                error = math.nan
            points.append(
                {
                    "steps_per_period": steps_per_period,
                    "time_step_s": step,
                    "times_s": times.tolist(),
                    "mean_tip_uz_m": values.tolist(),
                    "maximum_energy_drift": max(abs(float(row["relative_energy_drift"])) for row in result.solver["time_history"]),
                    "maximum_dynamic_residual": max(float(value) for value in result.solver["residual_history"]),
                    "normalized_rms_to_fine": error,
                }
            )
        assert reference_times is not None and reference_values is not None
        for row in points[:-1]:
            times = np.asarray(row["times_s"], dtype=float)
            values = np.asarray(row["mean_tip_uz_m"], dtype=float)
            reference = np.interp(times, reference_times, reference_values)
            row["normalized_rms_to_fine"] = _normalized_rms(values, reference)
        return {"points": points, "fine_steps_per_period": 160}

    def _model(
        self,
        mesh_size: float,
        analysis: str | dict[str, Any],
        *,
        total_load: float = 0.0,
    ) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
        mesh = BenchmarkMeshFactory().box_tetra(
            self.output_dir / "meshes" / f"{self.element_type.lower()}_h_{mesh_size:.3f}.msh",
            length=self.length,
            width=self.width,
            height=self.height,
            mesh_size=mesh_size,
            order=self.gmsh_order,
        )
        setup_path = mesh.with_suffix(".setup.json")
        write_json_file(setup_path, self._mesh_setup())
        imported = GmshModelImporter().import_model(mesh, setup_path).model
        root = np.flatnonzero(np.isclose(imported.nodes[:, 0], 0.0, atol=1.0e-10))
        tip = np.flatnonzero(np.isclose(imported.nodes[:, 0], self.length, atol=1.0e-10))
        if not root.size or not tip.size:
            raise RuntimeError("TET10 dynamic mesh has no complete root or tip node group.")
        elements = [
            {"type": element.type, "nodes": list(element.nodes), "material": element.material}
            for element in imported.elements
        ]
        model = FiniteElementModel.from_raw(
            nodes=imported.nodes.tolist(),
            elements=elements,
            materials=imported.materials,
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in root],
            loads=self._tip_loads(imported.nodes, imported.elements, tip, total_load),
            analysis=analysis,
            verification_profile="quick",
        )
        return model, root, tip

    def _mesh_setup(self) -> dict[str, Any]:
        """Return the family-specific Gmsh import contract."""
        return _mesh_setup(self.element_type)

    def _tip_loads(
        self, nodes: np.ndarray, elements: list[Any], tip: np.ndarray, total_load: float
    ) -> list[dict[str, Any]]:
        """Distribute a resultant over the loaded face using triangle areas."""
        self._tip_load_weights = _tip_face_weights(nodes, elements, tip)
        return [
            {"node": int(node), "dof": "UZ", "value": total_load * float(weight)}
            for node, weight in zip(tip, self._tip_load_weights, strict=True)
        ] if total_load else []

    def _code_aster_mesh(
        self, nodes: np.ndarray, elements: list[Any], root: np.ndarray, tip: np.ndarray
    ) -> str:
        """Write the ASTER mesh with the campaign element keyword."""
        return _code_aster_tet_mesh(
            nodes, elements, root, tip, self.aster_element_type, self.element_type
        )

    def _code_aster_comm(
        self,
        tip: np.ndarray,
        table: list[dict[str, float]],
        frequencies: list[float],
        *,
        rayleigh_alpha: float = 0.0,
        rayleigh_beta: float = 0.0,
    ) -> str:
        """Return the shared mechanical deck for this tetrahedral family."""
        return _code_aster_tet_dynamic_comm(
            tip, table, frequencies, self._tip_load_weights,
            rayleigh_alpha=rayleigh_alpha, rayleigh_beta=rayleigh_beta,
        )

    def _summary(
        self,
        model: FiniteElementModel,
        modal: Any,
        dynamic: Any,
        harmonic: Any,
        raw: dict[str, Any],
        spatial: dict[str, Any],
        temporal: dict[str, Any],
        table: list[dict[str, float]],
        frequencies: list[float],
        tip: np.ndarray,
        damping: dict[str, float],
    ) -> dict[str, Any]:
        aster_frequencies = np.asarray(raw["frequencies_hz"], dtype=float)
        qf_frequencies = np.asarray(modal.frequencies_hz[: aster_frequencies.size], dtype=float)
        modal_error = np.abs(qf_frequencies - aster_frequencies) / np.maximum(np.abs(aster_frequencies), 1.0e-30)
        qf_history = _mean_history(dynamic.solver["time_history"], tip)
        aster_history = _align_history(np.asarray(raw["tip_uz_m"], dtype=float), qf_history)
        tip_dofs = [harmonic.dofs.index(int(node), "UZ") for node in tip]
        qf_harmonic = np.asarray(
            [np.mean(np.asarray(response, dtype=complex)[tip_dofs]) for response in harmonic.responses],
            dtype=complex,
        )
        aster_harmonic = np.asarray([complex(*value) for value in raw["harmonic_tip_uz_m"]], dtype=complex)
        temporal_points = temporal["points"]
        coarse = float(temporal_points[0]["normalized_rms_to_fine"])
        medium = float(temporal_points[1]["normalized_rms_to_fine"])
        checks = [
            _check("modal_frequencies_same_mesh", float(np.max(modal_error)), self.external_limit),
            _check("newmark_history_same_mesh", _normalized_rms(qf_history, aster_history), self.external_limit),
            _check("harmonic_response_same_mesh", _complex_normalized_rms(qf_harmonic, aster_harmonic), self.external_limit),
            _check("modal_mesh_final_increment", float(spatial["frequency_final_increment"]), self.convergence_limit),
            _check("newmark_time_refinement", medium, coarse),
        ]
        static_check = _check(
            "static_mesh_final_increment",
            float(spatial["static_tip_final_increment"]),
            self.convergence_limit,
        )
        if not self.require_static_spatial_convergence and static_check["status"] == "FAIL":
            static_check["status"] = "WARNING"
            static_check["note"] = (
                "Diagnostic only: the retained dynamic acceptance uses same-mesh "
                "modal, Newmark and harmonic observables; static spatial convergence "
                "is reported separately for this nodal-face load family."
            )
        checks.insert(4, static_check)
        return {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] != "FAIL" for row in checks) else "WARNING",
            "maturity": "experimental",
            "scope": f"{self.element_type} isotropic linear structural modal/Newmark/harmonic correlation",
            "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE, "element": f"3D/{self.aster_element_type}"},
            "model": {"nodes": model.node_count, "elements": len(model.elements), "length_m": self.length, "width_m": self.width, "height_m": self.height, "same_mesh": True, "same_time_grid": True, "same_frequency_grid": True, "tip_observable": "mean UZ over loaded end-face nodes"},
            "modal": {"qf_frequencies_hz": qf_frequencies.tolist(), "code_aster_frequencies_hz": aster_frequencies.tolist(), "relative_differences": modal_error.tolist()},
            "newmark": {"time_step_s": table[1]["time"], "load_table": table, "qf_tip_uz_m": qf_history.tolist(), "code_aster_tip_uz_m": aster_history.tolist()},
            "harmonic": {"frequencies_hz": frequencies, "qf_tip_uz_m": _complex_rows(qf_harmonic), "code_aster_tip_uz_m": _complex_rows(aster_harmonic)},
            "damping": damping,
            "spatial_convergence": spatial,
            "time_convergence": temporal,
            "checks": checks,
            "limitations": [
                f"The external case is an isotropic, small-strain, {self.geometry_label} {self.element_type} model ({self.length:g} x {self.width:g} x {self.height:g} m) with nodal end loading.",
                f"No external curved {self.element_type} dynamic, nonlinear material, finite-strain or contact response is claimed; the damping case, when enabled, is mass-proportional Rayleigh damping only.",
                "Harmonic frequencies are kept below the first undamped resonance to avoid an intentionally singular physical operator.",
            ],
        }

    def _plot(self, summary: dict[str, Any]) -> None:
        """Plot readable convergence and same-mesh external observables."""
        figure, axes = plt.subplots(2, 2, figsize=(11.5, 7.5))
        modal = summary["modal"]
        mode = np.arange(1, len(modal["qf_frequencies_hz"]) + 1)
        axes[0, 0].plot(mode, modal["qf_frequencies_hz"], "o-", label="QF_solver")
        axes[0, 0].plot(mode, modal["code_aster_frequencies_hz"], "s--", label="Code_Aster")
        axes[0, 0].set(xlabel="Mode", ylabel="Frequence [Hz]", title="Modes propres")
        axes[0, 0].legend(fontsize=8)
        newmark = summary["newmark"]
        time = np.arange(len(newmark["qf_tip_uz_m"])) * float(newmark["time_step_s"])
        axes[0, 1].plot(time, newmark["qf_tip_uz_m"], label="QF_solver")
        axes[0, 1].plot(time, newmark["code_aster_tip_uz_m"], "--", label="Code_Aster")
        axes[0, 1].set(xlabel="Temps [s]", ylabel="UZ moyen [m]", title="Newmark")
        axes[0, 1].legend(fontsize=8)
        harmonic = summary["harmonic"]
        axes[1, 0].plot(harmonic["frequencies_hz"], np.abs(_complex_values(harmonic["qf_tip_uz_m"])), "o-", label="QF_solver")
        axes[1, 0].plot(harmonic["frequencies_hz"], np.abs(_complex_values(harmonic["code_aster_tip_uz_m"])), "s--", label="Code_Aster")
        axes[1, 0].set(xlabel="Frequence [Hz]", ylabel="|UZ| moyen [m]", title="Harmonique")
        axes[1, 0].legend(fontsize=8)
        spatial = summary["spatial_convergence"]["levels"]
        axes[1, 1].plot([row["elements"] for row in spatial], [row["frequency_hz"] for row in spatial], "o-")
        axes[1, 1].set(xlabel=self.element_type, ylabel="f1 [Hz]", title="Raffinement spatial")
        axes[1, 1].grid(True, alpha=0.3)
        figure.tight_layout()
        figure.savefig(self.output_dir / "comparison.png", dpi=180)
        plt.close(figure)


def _mesh_setup(element_type: str = "TET10") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": "quick",
        "analysis": "linear_static",
        "materials": {"solid": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3, "density": 2700.0}},
        "groups": [{"name": "domain", "dimension": 3, "actions": [{"type": "elements", "element_type": element_type, "material": "solid"}]}],
    }


def _modal_analysis() -> dict[str, Any]:
    return {"type": "modal", "method": "eigsh", "modes": 6, "arpack_tolerance": 1.0e-10}


def _newmark_analysis(
    step: float,
    steps: int,
    table: list[dict[str, float]],
    tip: np.ndarray,
    *,
    rayleigh_alpha: float = 0.0,
    rayleigh_beta: float = 0.0,
) -> dict[str, Any]:
    return {
        "type": "transient_dynamic",
        "method": "newmark",
        "time_step": step,
        "steps": steps,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "load_table": table,
        "history_probes": [{"node": int(node), "dof": "UZ", "label": f"tip_{node}"} for node in tip],
        "rayleigh_alpha": rayleigh_alpha,
        "rayleigh_beta": rayleigh_beta,
    }


def _harmonic_analysis(
    frequencies: list[float],
    *,
    rayleigh_alpha: float = 0.0,
    rayleigh_beta: float = 0.0,
) -> dict[str, Any]:
    return {
        "type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies,
        "rayleigh_alpha": rayleigh_alpha, "rayleigh_beta": rayleigh_beta,
    }


def _pulse_table(step: float, steps: int) -> list[dict[str, float]]:
    duration = 0.25 * steps * step
    return [{"time": index * step, "factor": math.sin(math.pi * index * step / duration) if index * step <= duration else 0.0} for index in range(steps + 1)]


def code_aster_tet10_mesh(nodes: np.ndarray, elements: list[Any], root: np.ndarray, tip: np.ndarray) -> str:
    """Write a deterministic ASTER mesh preserving QF_solver TET10 order."""
    return _code_aster_tet_mesh(nodes, elements, root, tip, "TETRA10", "TET10")


def _code_aster_tet_mesh(
    nodes: np.ndarray,
    elements: list[Any],
    root: np.ndarray,
    tip: np.ndarray,
    aster_element_type: str,
    qf_element_type: str,
) -> str:
    """Write a deterministic ASTER tetrahedral mesh preserving node order."""
    lines = ["TITRE", f"QF_solver {qf_element_type} same-mesh dynamic correlation", "FINSF", "COOR_3D"]
    lines.extend(f"N{i + 1} {node[0]:.16g} {node[1]:.16g} {node[2]:.16g}" for i, node in enumerate(nodes))
    lines.extend(["FINSF", aster_element_type])
    lines.extend(f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in element.nodes) for i, element in enumerate(elements))
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i}" for i in range(1, len(elements) + 1)), "FINSF", "GROUP_NO", "ROOT", *(f"N{int(node) + 1}" for node in root), "FINSF", "GROUP_NO", "TIP", *(f"N{int(node) + 1}" for node in tip), "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def code_aster_tet10_dynamic_comm(
    tip: np.ndarray,
    table: list[dict[str, float]],
    frequencies: list[float],
    *,
    rayleigh_alpha: float = 0.0,
    rayleigh_beta: float = 0.0,
) -> str:
    """Return the pinned 3D/TETRA10 modal, Newmark and harmonic deck."""
    return _code_aster_tet_dynamic_comm(
        tip, table, frequencies,
        rayleigh_alpha=rayleigh_alpha, rayleigh_beta=rayleigh_beta,
    )


def _code_aster_tet_dynamic_comm(
    tip: np.ndarray,
    table: list[dict[str, float]],
    frequencies: list[float],
    weights: np.ndarray | None = None,
    *,
    rayleigh_alpha: float = 0.0,
    rayleigh_beta: float = 0.0,
) -> str:
    """Return the common 3D tetrahedral modal, Newmark and harmonic deck."""
    load_weights = np.full(tip.size, 1.0 / tip.size) if weights is None else np.asarray(weights, dtype=float)
    load_rows = ",\n    ".join(
        f'_F(NOEUD="N{int(node) + 1}", FZ={-float(weight):.16g})'
        for node, weight in zip(tip, load_weights, strict=True)
    )
    times = ", ".join(f"{row['time']:.16g}" for row in table)
    factors = ", ".join(f"{row['time']:.16g}, {row['factor']:.16g}" for row in table)
    frequency_text = ", ".join(f"{value:.16g}" for value in frequencies)
    damping_definition = ""
    damping_argument = ""
    if rayleigh_alpha > 0.0 or rayleigh_beta > 0.0:
        terms: list[str] = []
        if rayleigh_alpha > 0.0:
            terms.append(f"_F(MATR_ASSE=mass, COEF_R={rayleigh_alpha:.16g})")
        if rayleigh_beta > 0.0:
            terms.append(f"_F(MATR_ASSE=rigidity, COEF_R={rayleigh_beta:.16g})")
        combination = terms[0] if len(terms) == 1 else "(" + ", ".join(terms) + ")"
        damping_definition = f"damping = COMB_MATR_ASSE(COMB_R={combination})\n"
        damping_argument = ", MATR_AMOR=damping"
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=7.0e10, NU=0.3, RHO=2700.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    {load_rows}
))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CHARGE=(boundary, force))
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CHARGE=(boundary, force))
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
{damping_definition}load_e = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHAM_MATER=field, CHARGE=(boundary, force))
load = ASSE_VECTEUR(VECT_ELEM=load_e, NUME_DDL=numbering)
modes = CALC_MODES(OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass, CALC_FREQ=_F(NMAX_FREQ=6), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7))
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


def _mean_displacement(values: np.ndarray, dofs: Any, tip: np.ndarray) -> float:
    return float(np.mean([values[dofs.index(int(node), "UZ")] for node in tip]))


def _mean_history(history: list[dict[str, Any]], tip: np.ndarray) -> np.ndarray:
    labels = [f"tip_{int(node)}" for node in tip]
    return np.asarray([np.mean([float(row["probes"][label]["displacement"]) for label in labels]) for row in history], dtype=float)


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


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _tip_face_weights(nodes: np.ndarray, elements: list[Any], tip: np.ndarray) -> np.ndarray:
    """Return consistent nodal weights for boundary triangles on a tip face."""
    tip_set = {int(node) for node in tip}
    face_counts: dict[tuple[int, int, int], int] = {}
    for element in elements:
        corners = tuple(int(node) for node in element.nodes[:4])
        faces = (
            (corners[0], corners[1], corners[2]),
            (corners[0], corners[1], corners[3]),
            (corners[0], corners[2], corners[3]),
            (corners[1], corners[2], corners[3]),
        )
        for face in faces:
            key = tuple(sorted(face))
            face_counts[key] = face_counts.get(key, 0) + 1
    weights = {int(node): 0.0 for node in tip}
    total_area = 0.0
    for face, count in face_counts.items():
        if count != 1 or not set(face).issubset(tip_set):
            continue
        point_a, point_b, point_c = (np.asarray(nodes[node], dtype=float) for node in face)
        area = 0.5 * float(np.linalg.norm(np.cross(point_b - point_a, point_c - point_a)))
        total_area += area
        for node in face:
            weights[node] += area / 3.0
    if not total_area or any(value <= 0.0 for value in weights.values()):
        return np.full(tip.size, 1.0 / tip.size)
    return np.asarray([weights[int(node)] / total_area for node in tip], dtype=float)


def _check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _complex_rows(values: np.ndarray) -> list[list[float]]:
    return [[float(value.real), float(value.imag)] for value in values]


def _complex_values(values: list[list[float]]) -> np.ndarray:
    return np.asarray([complex(*value) for value in values], dtype=complex)


def _report(summary: dict[str, Any]) -> str:
    damping = summary.get("damping", {})
    damping_text = (
        f"Amortissement Rayleigh massique : ratio modal cible "
        f"`{100.0 * float(damping.get('target_modal_damping_ratio', 0.0)):.3g} %`, "
        f"alpha = `{float(damping.get('rayleigh_alpha_s_inv', 0.0)):.6g} s^-1`, "
        f"beta = `{float(damping.get('rayleigh_beta_s', 0.0)):.6g} s`."
    )
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", damping_text, "", "| Controle | Ecart / valeur | Limite |", "| --- | ---: | ---: |"]
    for row in summary["checks"]:
        lines.append(f"| {row['id']} | {100.0 * row['value']:.5g} % | {100.0 * row['limit']:.5g} % |")
    lines.extend(["", "Le protocole conserve la connectivite TETRA10, les coordonnees, le clamp, les charges nodales, le pas de temps et les frequences. Les resultats ne sont valables que pour ce domaine borne.", ""])
    return "\n".join(lines)
