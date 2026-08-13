"""Extended internal modal and linear-dynamic V&V for MITC3+ shells.

This campaign adds the structural evidence that is not covered by the compact
first-mode campaign: a free-free assembly, a curved faceted shell, h-refinement
and an eigsh sparse solve.  Its temporal and frequency references are modal
invariants, not external solver correlations.
"""

from __future__ import annotations

from solveur.paths import project_root

import math
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.linalg import eigh

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.analysis import AnalysisSettings
from solveur.core.assembler import GlobalAssembler
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc3_models import cylindrical_panel_mesh, rectangular_tri_mesh, split_quads
from solveur.verification.mitc4_harmonic import _analytical_response
from solveur.verification.mitc4_newmark import _initial_state
from solveur.verification.mitc4_newmark_extended import modal_nodal_loads


PROJECT_ROOT = project_root()
CAMPAIGN_ID = "VNV-MITC3-DYNAMIC-EXTENDED-001"
FREE_FREE_ID = "VNV-MITC3-MODAL-FREEFREE-013"
CURVED_ID = "VNV-MITC3-MODAL-CURVED-014"
SPARSE_ID = "VNV-MITC3-MODAL-EIGSH-015"
DYNAMIC_ID = "VNV-MITC3-NEWMARK-HARMONIC-CURVED-016"


class Mitc3DynamicExtendedStudy:
    """Produce bounded, reproducible evidence for MITC3+ linear dynamics."""

    rigid_gap_limit = 1.0e-8
    rigid_residual_limit = 1.0e-12
    modal_residual_limit = 1.0e-7
    curved_increment_limit = 6.0e-2
    rotation_limit = 1.0e-8
    eigsh_frequency_limit = 1.0e-8
    newmark_rms_limit = 1.0e-2
    energy_drift_limit = 1.0e-4
    harmonic_error_limit = 1.0e-6
    minimum_sparse_dofs = 2500

    def run(self) -> dict[str, Any]:
        """Run all four extended studies and retain data for deterministic plots."""
        free_free = self._free_free()
        curved = self._curved_modal()
        sparse = self._sparse_modal()
        dynamic = self._curved_dynamic()
        checks = {
            **{f"free_free_{key}": bool(value) for key, value in free_free["checks"].items()},
            **{f"curved_{key}": bool(value) for key, value in curved["checks"].items()},
            **{f"sparse_{key}": bool(value) for key, value in sparse["checks"].items()},
            **{f"dynamic_{key}": bool(value) for key, value in dynamic["checks"].items()},
        }
        return {
            "campaign": CAMPAIGN_ID,
            "status": "PASS_INTERNAL" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "MITC3+ isotropic linear dynamics, internal structural evidence",
            "studies": {
                "free_free": free_free,
                "curved_modal": curved,
                "sparse_modal": sparse,
                "curved_dynamic": dynamic,
            },
            "checks": checks,
            "limitations": [
                "All temporal and harmonic references are the first computed mode of the same assembled model; they prove algorithmic consistency, not an external element correlation.",
                "The curved shell uses planar MITC3+ facets. It does not claim a curved isoparametric triangular mapping.",
                "No same-mesh Code_Aster or CalculiX correlation is supplied for modal, Newmark or harmonic MITC3+ response.",
                "Nodal shell-stress histories are excluded when adjacent MITC3+ local frames are not aligned. Element-level harmonic stresses remain available.",
            ],
        }

    def _free_free(self) -> dict[str, Any]:
        model, triangles = _free_free_model()
        dofs = model.dof_manager()
        assembler = GlobalAssembler()
        stiffness = assembler.assemble_stiffness(model, dofs)
        mass = assembler.assemble_mass(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, np.array([], dtype=int))
        eigenvalues, vectors = eigh(reducer.stiffness.toarray(), reducer.mass.toarray())
        first_elastic = float(eigenvalues[6])
        rigid_values = np.asarray(eigenvalues[:6], dtype=float)
        scale = max(float(np.linalg.norm(stiffness.data)), 1.0)
        residuals = [
            float(np.linalg.norm(reducer.stiffness @ vector))
            / max(scale * float(np.linalg.norm(vector)), 1.0)
            for vector in _rigid_vectors(model, dofs, reducer)
        ]
        checks = {
            "exactly_six_rigid_modes": int(np.count_nonzero(np.abs(eigenvalues) < first_elastic * 1.0e-8)) == 6,
            "rigid_elastic_separation": float(np.max(np.abs(rigid_values)) / first_elastic) <= self.rigid_gap_limit,
            "analytical_rigid_residuals": max(residuals) <= self.rigid_residual_limit,
            "positive_first_elastic_mode": first_elastic > 0.0,
            "drilling_condensed": reducer.diagnostics["condensed_drilling_dof_count"] > 0,
        }
        return {
            "study_id": FREE_FREE_ID,
            "model": {
                "geometry": "flat assembled MITC3+ strip",
                "element_count": len(model.elements),
                "node_count": model.node_count,
                "boundary_conditions": "free-free",
                "retained_dof_count": int(reducer.stiffness.shape[0]),
                "condensed_drilling_dof_count": reducer.diagnostics["condensed_drilling_dof_count"],
            },
            "metrics": {
                "rigid_eigenvalues": rigid_values.tolist(),
                "first_elastic_eigenvalue": first_elastic,
                "rigid_to_first_elastic_ratio": float(np.max(np.abs(rigid_values)) / first_elastic),
                "maximum_analytical_rigid_residual": max(residuals),
                "first_six_elastic_frequencies_hz": (np.sqrt(eigenvalues[6:12]) / (2.0 * math.pi)).tolist(),
            },
            "checks": {key: bool(value) for key, value in checks.items()},
            "_plot": {"nodes": model.nodes, "triangles": triangles, "eigenvalues": eigenvalues[:12]},
        }

    def _curved_modal(self) -> dict[str, Any]:
        points = [self._modal_point(nx, nx // 4, method="eigh") for nx in (16, 24, 32)]
        regular = np.asarray(points[-1]["frequencies_hz"], dtype=float)
        previous = np.asarray(points[-2]["frequencies_hz"], dtype=float)
        rotated = self._modal_point(32, 8, method="eigh", rotated=True)
        increment = _relative_error(previous, regular)
        rotation = _relative_error(np.asarray(rotated["frequencies_hz"], dtype=float), regular)
        checks = {
            "ten_modes": all(len(point["frequencies_hz"]) == 10 for point in points),
            "h_refinement": max(increment) <= self.curved_increment_limit,
            "rigid_rotation_objectivity": max(rotation) <= self.rotation_limit,
            "residual": max(point["maximum_relative_residual"] for point in (*points, rotated)) <= self.modal_residual_limit,
            "orthogonality": max(
                max(point["mass_orthogonality_error"], point["stiffness_orthogonality_error"])
                for point in (*points, rotated)
            ) <= self.modal_residual_limit,
        }
        return {
            "study_id": CURVED_ID,
            "model": {
                "geometry": "cylindrical cantilever, radius 0.5 m, angle pi/6",
                "boundary_conditions": "six dofs clamped at x=0",
                "element": "MITC3+ planar facets",
            },
            "points": points,
            "metrics": {
                "last_mesh_relative_frequency_increment": increment,
                "rigid_rotation_relative_frequency_difference": rotation,
            },
            "checks": {key: bool(value) for key, value in checks.items()},
        }

    def _sparse_modal(self) -> dict[str, Any]:
        dense = self._modal_point(16, 4, method="eigh")
        sparse = self._modal_point(16, 4, method="eigsh")
        large = self._modal_point(40, 10, method="eigsh")
        difference = _relative_error(
            np.asarray(sparse["frequencies_hz"], dtype=float), np.asarray(dense["frequencies_hz"], dtype=float)
        )
        checks = {
            "eigh_eigsh_frequency_agreement": max(difference) <= self.eigsh_frequency_limit,
            "large_sparse_problem": large["retained_dof_count"] >= self.minimum_sparse_dofs,
            "large_uses_eigsh": large["method"] == "eigsh" and not large["dense_conversion_used"],
            "large_ten_modes": len(large["frequencies_hz"]) == 10,
            "large_residual": large["maximum_relative_residual"] <= self.modal_residual_limit,
            "large_orthogonality": max(large["mass_orthogonality_error"], large["stiffness_orthogonality_error"])
            <= self.modal_residual_limit,
        }
        return {
            "study_id": SPARSE_ID,
            "medium_crosscheck": {
                "dense": dense,
                "sparse": sparse,
                "relative_frequency_difference": difference,
            },
            "large_sparse": large,
            "checks": {key: bool(value) for key, value in checks.items()},
        }

    def _curved_dynamic(self) -> dict[str, Any]:
        model = _curved_model(16, 4, _modal_analysis("eigh"))
        modal = solve_model(model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        tip = _tip_node(model.nodes)
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        tip_index = modal.dofs.index(tip, "UZ")
        amplitude = 1.0e-4
        initial = _initial_state(modal.dofs, mode * (amplitude / mode[tip_index]))
        newmark = [self._newmark_point(model, tip, initial, frequency, amplitude, count) for count in (20, 40, 80)]
        harmonic = self._harmonic_point(model, modal, tip, frequency, mode)
        checks = {
            "newmark_time_step_convergence": all(
                current["normalized_rms_error"] < previous["normalized_rms_error"]
                for previous, current in zip(newmark, newmark[1:])
            ),
            "newmark_fine_error": newmark[-1]["normalized_rms_error"] <= self.newmark_rms_limit,
            "newmark_energy": max(row["maximum_relative_energy_drift"] for row in newmark) <= self.energy_drift_limit,
            "newmark_residual": max(row["maximum_dynamic_residual_norm"] for row in newmark) <= self.modal_residual_limit,
            **{f"harmonic_{key}": bool(value) for key, value in harmonic["checks"].items()},
        }
        return {
            "study_id": DYNAMIC_ID,
            "first_frequency_hz": frequency,
            "probe": {"node": tip, "dof": "UZ"},
            "newmark": newmark,
            "harmonic": harmonic,
            "checks": {key: bool(value) for key, value in checks.items()},
        }

    def _modal_point(self, nx: int, ny: int, *, method: str, rotated: bool = False) -> dict[str, Any]:
        model = _curved_model(nx, ny, _modal_analysis(method), rotated=rotated)
        started = time.perf_counter()
        result = solve_model(model, enforce_policy=False)
        return {
            "mesh": [nx, ny],
            "element_count": len(model.elements),
            "retained_dof_count": result.solver["dynamic_reduction"]["retained_dof_count"],
            "method": result.method,
            "dense_conversion_used": bool(result.solver["dense_conversion_used"]),
            "elapsed_seconds": time.perf_counter() - started,
            "frequencies_hz": [float(value) for value in result.frequencies_hz[:10]],
            "maximum_relative_residual": float(result.solver["max_relative_residual"]),
            "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
            "stiffness_orthogonality_error": float(result.solver["stiffness_diagonal_error"]),
            "rotated": rotated,
        }

    @staticmethod
    def _newmark_point(
        model: FiniteElementModel,
        tip: int,
        initial: list[dict[str, object]],
        frequency: float,
        amplitude: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        step = 1.0 / frequency / steps_per_period
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "transient_dynamic", "method": "newmark", "time_step": step,
                "steps": 2 * steps_per_period, "newmark_beta": 0.25, "newmark_gamma": 0.5,
                "load_factors": [0.0], "initial_displacements": initial,
                "history_probes": [{"node": tip, "dof": "UZ", "label": "tip_uz"}],
            }
        )
        result = solve_model(model, enforce_policy=False)
        history = result.solver["time_history"]
        times = np.asarray([row["time"] for row in history], dtype=float)
        response = np.asarray([row["probes"]["tip_uz"]["displacement"] for row in history], dtype=float)
        expected = amplitude * np.cos(2.0 * math.pi * frequency * times)
        return {
            "steps_per_period": steps_per_period,
            "time_step_s": step,
            "normalized_rms_error": float(np.sqrt(np.mean((response - expected) ** 2)) / amplitude),
            "maximum_relative_energy_drift": max(abs(float(row["relative_energy_drift"])) for row in history),
            "maximum_dynamic_residual_norm": max(float(row["dynamic_residual_norm"]) for row in history),
            "times_s": times.tolist(), "tip_uz_m": response.tolist(), "reference_tip_uz_m": expected.tolist(),
        }

    def _harmonic_point(self, model: FiniteElementModel, modal: Any, tip: int, frequency: float, mode: np.ndarray) -> dict[str, Any]:
        ratios = np.asarray((0.0, 0.25, 0.5, 0.75, 0.95, 1.0, 1.05, 1.25, 1.5, 2.0))
        frequencies = ratios * frequency
        alpha = 0.04 * math.pi * frequency
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        model.analysis = AnalysisSettings.from_raw(
            {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies.tolist(), "rayleigh_alpha": alpha, "rayleigh_beta": 0.0}
        )
        result = solve_model(model, enforce_policy=False)
        index = result.dofs.index(tip, "UZ")
        numerical = np.asarray([row[index] for row in result.responses], dtype=complex)
        reference = _analytical_response(float(mode[modal.dofs.index(tip, "UZ")]), 2.0 * math.pi * frequency, frequencies, alpha)
        errors = np.abs(numerical - reference) / np.maximum(np.abs(reference), 1.0e-30)
        static_error = self._harmonic_static_limit(modal, mode, tip, numerical[0])
        stress_rows = result.shell_stress_response
        peak = int(np.argmax(np.abs(numerical)))
        checks = {
            "complex_modal_response": float(np.max(errors)) <= self.harmonic_error_limit,
            "zero_hz_static_limit": static_error <= 1.0e-9,
            "residual": float(result.solver["max_relative_residual_norm"]) <= self.modal_residual_limit,
            "broadband_stress_output": len(stress_rows) == len(frequencies) and bool(stress_rows[0]["element_results"]),
            "resonance_peak": bool(0.95 <= ratios[peak] <= 1.05),
        }
        return {
            "frequency_ratios": ratios.tolist(), "frequencies_hz": frequencies.tolist(),
            "amplitudes_m": np.abs(numerical).tolist(), "phases_degrees": np.degrees(np.angle(numerical)).tolist(),
            "maximum_relative_error": float(np.max(errors)), "zero_hz_static_relative_error": static_error,
            "maximum_relative_residual": float(result.solver["max_relative_residual_norm"]),
            "stress_frequency_count": len(stress_rows), "checks": {key: bool(value) for key, value in checks.items()},
        }

    @staticmethod
    def _harmonic_static_limit(modal: Any, mode: np.ndarray, tip: int, zero_value: complex) -> float:
        model = _curved_model(16, 4, {"type": "linear_static", "method": "direct"})
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        static = solve_model(model, enforce_policy=False)
        expected = float(static.displacements[static.dofs.index(tip, "UZ")])
        return abs(zero_value.real - expected) / max(abs(expected), 1.0e-30)


def write_mitc3_dynamic_extended_evidence(output: str | Path) -> dict[str, Any]:
    """Write controlled reports, plots and a manifest for the extended campaign."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3DynamicExtendedStudy().run()
    free_plot = summary["studies"]["free_free"].pop("_plot")
    write_json_file(target / "summary.json", summary)
    _write_report(target / "report.md", summary)
    _plot_free_free(free_plot, target / f"{FREE_FREE_ID}.png")
    _plot_modal_convergence(summary, target / f"{CURVED_ID}.png")
    _plot_curved_dynamics(summary, target / f"{DYNAMIC_ID}.png")
    write_json_file(
        target / "vnv_manifest.json",
        {"schema_version": 1, "campaign": CAMPAIGN_ID, "source": git_source_state(PROJECT_ROOT), "files": discovered_file_entries(target, lambda _: "mitc3_dynamic_extended_vnv", exclude_names=("vnv_manifest.json",))},
    )
    return summary


def _free_free_model() -> tuple[FiniteElementModel, np.ndarray]:
    nodes, triangles, _ = rectangular_tri_mesh(1.0, 0.2, 2, 1)
    return _shell_model(nodes, triangles, fixed=[], analysis=_modal_analysis("eigh")), triangles


def _curved_model(nx: int, ny: int, analysis: dict[str, object], *, rotated: bool = False) -> FiniteElementModel:
    nodes, quads, _ = cylindrical_panel_mesh(1.0, 0.5, math.pi / 6.0, nx, ny)
    root = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    if rotated:
        nodes = nodes @ _rotation().T
    fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in root]
    return _shell_model(nodes, split_quads(quads), fixed=fixed, analysis=analysis)


def _shell_model(nodes: np.ndarray, triangles: np.ndarray, *, fixed: list[dict[str, object]], analysis: dict[str, object]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "MITC3", "nodes": triangle.tolist(), "material": "skin"} for triangle in triangles],
        materials={"skin": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.3, "t": 0.01, "density": 2700.0, "drilling_scale": 1.0e-4}},
        fixed_dofs=fixed,
        analysis=analysis,
        verification_profile="quick",
    )


def _modal_analysis(method: str) -> dict[str, object]:
    values: dict[str, object] = {"type": "modal", "method": method, "modes": 10, "dense_modal_max_dofs": 6000, "modal_residual_failure_tolerance": 1.0e-7}
    if method == "eigsh":
        values.update({"arpack_tolerance": 1.0e-10, "arpack_maxiter": 10000, "arpack_ncv": 30})
    return values


def _rigid_vectors(model: FiniteElementModel, dofs: Any, reducer: DynamicDofReducer) -> list[np.ndarray]:
    vectors: list[np.ndarray] = []
    for translation in np.eye(3):
        full = np.zeros(dofs.ndof)
        for node in range(model.node_count):
            for name, value in zip(("UX", "UY", "UZ"), translation, strict=True):
                full[dofs.index(node, name)] = value
        vectors.append(reducer.reduce_state(full))
    for rotation in np.eye(3):
        full = np.zeros(dofs.ndof)
        for node, position in enumerate(model.nodes):
            displacement = np.cross(rotation, position)
            for name, value in zip(("UX", "UY", "UZ"), displacement, strict=True):
                full[dofs.index(node, name)] = value
            for name, value in zip(("RX", "RY", "RZ"), rotation, strict=True):
                full[dofs.index(node, name)] = value
        vectors.append(reducer.reduce_state(full))
    return vectors


def _tip_node(nodes: np.ndarray) -> int:
    candidates = np.flatnonzero(np.isclose(nodes[:, 0], np.max(nodes[:, 0])))
    return int(candidates[np.argmin(np.abs(nodes[candidates, 1]))])


def _rotation() -> np.ndarray:
    angle = math.radians(31.0)
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array(((cosine, -sine, 0.0), (sine, cosine, 0.0), (0.0, 0.0, 1.0)))


def _relative_error(first: np.ndarray, second: np.ndarray) -> list[float]:
    return (np.abs(first - second) / np.maximum(np.abs(second), 1.0e-30)).tolist()


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    free = summary["studies"]["free_free"]
    curved = summary["studies"]["curved_modal"]
    dynamic = summary["studies"]["curved_dynamic"]
    lines = [
        f"# {CAMPAIGN_ID}", "", "## Objet", "",
        "Verification interne MITC3+ isotrope pour une structure libre-libre, une coque cylindrique facettisee et les routes Newmark/harmonique. Il ne s'agit pas d'une correlation externe.", "",
        "## Libre-libre", "",
        f"Six valeurs propres rigides restent separees du premier mode elastique avec un ratio `{free['metrics']['rigid_to_first_elastic_ratio']:.3e}`. Le residu analytique maximal des mouvements rigides est `{free['metrics']['maximum_analytical_rigid_residual']:.3e}`.", "",
        "## Coque courbe et eigsh", "", "| Maillage | Elements | DDL retenus | Premier mode (Hz) | Residu |", "| --- | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(f"| {row['mesh'][0]} x {row['mesh'][1]} | {row['element_count']} | {row['retained_dof_count']} | {row['frequencies_hz'][0]:.6f} | {row['maximum_relative_residual']:.3e} |" for row in curved["points"])
    lines.extend(["", "## Newmark et harmonique", "", "| Pas/periode | Erreur RMS | Derive energie | Residu dynamique |", "| ---: | ---: | ---: | ---: |"])
    lines.extend(f"| {row['steps_per_period']} | {row['normalized_rms_error']:.3e} | {row['maximum_relative_energy_drift']:.3e} | {row['maximum_dynamic_residual_norm']:.3e} |" for row in dynamic["newmark"])
    harmonic = dynamic["harmonic"]
    lines.extend(["", f"Erreur harmonique complexe maximale : `{harmonic['maximum_relative_error']:.3e}`. Limite statique : `{harmonic['zero_hz_static_relative_error']:.3e}`.", "", f"![Libre-libre]({FREE_FREE_ID}.png)", "", f"![Coque courbe]({CURVED_ID}.png)", "", f"![Dynamique]({DYNAMIC_ID}.png)", "", "## Limites ouvertes", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_free_free(data: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    nodes, triangles = np.asarray(data["nodes"]), np.asarray(data["triangles"])
    for triangle in triangles:
        polygon = nodes[np.r_[triangle, triangle[0]]]
        axes[0].plot(polygon[:, 0], polygon[:, 1], color="#0077b6", linewidth=0.8)
    axes[0].set(aspect="equal", xlabel="x (m)", ylabel="y (m)", title="Assemblage libre-libre MITC3+")
    axes[1].semilogy(range(1, len(data["eigenvalues"]) + 1), np.maximum(np.abs(data["eigenvalues"]), 1.0e-14), "o-", color="#bc4749")
    axes[1].axvline(6.5, color="#212529", linestyle="--", linewidth=0.9)
    axes[1].set(xlabel="numero de mode", ylabel="|valeur propre|", title="Six modes rigides puis modes elastiques")
    for axis in axes:
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_modal_convergence(summary: dict[str, Any], path: Path) -> None:
    curved = summary["studies"]["curved_modal"]
    sparse = summary["studies"]["sparse_modal"]
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    points = curved["points"]
    axes[0].plot([row["element_count"] for row in points], [row["frequencies_hz"][0] for row in points], "o-", color="#0077b6")
    axes[0].set(xlabel="triangles", ylabel="f1 (Hz)", title="Convergence coque cylindrique")
    medium = sparse["medium_crosscheck"]
    axes[1].semilogy(range(1, 11), medium["relative_frequency_difference"], "o-", color="#bc4749")
    axes[1].set(xlabel="numero de mode", ylabel="ecart relatif eigh/eigsh", title="Controle eigsh")
    for axis in axes:
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_curved_dynamics(summary: dict[str, Any], path: Path) -> None:
    dynamic = summary["studies"]["curved_dynamic"]
    coarse, fine = dynamic["newmark"][0], dynamic["newmark"][-1]
    harmonic = dynamic["harmonic"]
    figure, axes = plt.subplots(2, 1, figsize=(7.2, 6.0))
    axes[0].plot(fine["times_s"], fine["reference_tip_uz_m"], "k--", label="reference modale")
    axes[0].plot(coarse["times_s"], coarse["tip_uz_m"], color="#bc4749", alpha=0.75, label=f"T/{coarse['steps_per_period']}")
    axes[0].plot(fine["times_s"], fine["tip_uz_m"], color="#0077b6", label=f"T/{fine['steps_per_period']}")
    axes[0].set(xlabel="temps (s)", ylabel="UZ pointe (m)")
    axes[0].legend()
    axes[1].semilogy(harmonic["frequency_ratios"], harmonic["amplitudes_m"], color="#0077b6")
    axes[1].set(xlabel="frequence / f1", ylabel="amplitude UZ (m)")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.axvline(1.0, color="#212529", linestyle="--", linewidth=0.9)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
