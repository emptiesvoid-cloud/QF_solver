"""Independent multi-DOF verification for springs and concentrated masses."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.linalg import eigh

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.io.manifest import write_json_file
from solveur.verification.vnv_manifest import write_vnv_manifest


_DT = 1.0e-3
_STEPS = 40
_BETA = 0.25
_GAMMA = 0.5
_TOLERANCE = 1.0e-10


def run_discrete_multidof_campaign() -> dict[str, Any]:
    """Compare QF_solver against independent dense matrix references."""

    static_model = _model("linear_static")
    modal_model = _model({"type": "modal", "method": "eigh", "parameters": {"modes": 3}})
    transient_model = _model(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "parameters": {
                "time_step": _DT,
                "steps": _STEPS,
                "beta": _BETA,
                "gamma": _GAMMA,
                "load_function": "linear_ramp",
                "history_probes": [{"node": 2, "dof": "UX", "label": "tip_ux"}],
                "postprocess_mode": "summary",
            },
        }
    )
    harmonic_model = _model(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "parameters": {"frequencies_hz": [0.5, 2.0, 4.0]},
        }
    )

    static_matrices = _reduced_matrices(static_model)
    stiffness, mass, load, free = static_matrices
    static_result = AnalysisRouter().solve(static_model)
    static_qf = static_result.displacements[free]
    static_reference = np.linalg.solve(stiffness, load)
    static_error = _relative_error(static_qf, static_reference)

    modal_result = AnalysisRouter().solve(modal_model)
    eigenvalues, modes = eigh(stiffness, mass)
    reference_frequencies = np.sqrt(eigenvalues[:3]) / (2.0 * np.pi)
    modal_error = _relative_error(modal_result.frequencies_hz[:3], reference_frequencies)

    transient_result = AnalysisRouter().solve(transient_model)
    reference_history = _newmark_reference(stiffness, mass, load)
    qf_history = np.asarray(
        [float(row["probes"]["tip_ux"]["displacement"]) for row in transient_result.solver["time_history"]]
    )
    transient_error = _relative_error(qf_history, reference_history)

    frequencies = np.asarray(harmonic_model.analysis.parameters["frequencies_hz"], dtype=float)
    harmonic_result = AnalysisRouter().solve(harmonic_model)
    harmonic_reference = [
        np.linalg.solve(stiffness - (2.0 * np.pi * frequency) ** 2 * mass, load)
        for frequency in frequencies
    ]
    harmonic_qf = [np.asarray(response)[free] for response in harmonic_result.responses]
    harmonic_error = max(
        _relative_error(qf, reference) for qf, reference in zip(harmonic_qf, harmonic_reference, strict=True)
    )

    checks = [
        _check("static_solution", static_error),
        _check("modal_frequencies", modal_error),
        _check("newmark_tip_history", transient_error),
        _check("harmonic_response", harmonic_error),
    ]
    return {
        "study_id": "VNV-DISCRETE-MULTIDOF-ANALYTIC-001",
        "status": "PASS_TECHNICAL_VERIFICATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "scope": "discrete-linear multi-DOF springs and concentrated masses",
        "reference": {
            "type": "independent dense K/M assembly and Newmark recurrence",
            "same_model": True,
            "note": "This is an internal algebraic verification; Code_Aster remains the external SDOF correlation oracle.",
        },
        "model": {
            "nodes": 3,
            "free_translation_dofs": 6,
            "springs": 3,
            "concentrated_masses": 2,
            "topology": "fixed node 0, node-to-node springs 0-1 and 1-2, grounded spring at node 2",
        },
        "static": {
            "qf_displacement": static_qf.tolist(),
            "reference_displacement": static_reference.tolist(),
            "relative_error": static_error,
        },
        "modal": {
            "qf_frequencies_hz": modal_result.frequencies_hz[:3].tolist(),
            "reference_frequencies_hz": reference_frequencies.tolist(),
            "relative_error_max": modal_error,
            "reference_mass_positive": bool(np.min(np.linalg.eigvalsh(mass)) > 0.0),
            "reference_stiffness_positive": bool(np.min(np.linalg.eigvalsh(stiffness)) > 0.0),
            "qf_residual_max": float(modal_result.solver["max_relative_residual"]),
        },
        "newmark": {
            "time_step_s": _DT,
            "steps": _STEPS,
            "beta": _BETA,
            "gamma": _GAMMA,
            "relative_tip_history_error": transient_error,
            "qf_tip_history": qf_history.tolist(),
            "reference_history": reference_history.tolist(),
            "qf_energy_drift_max": max(abs(float(row["relative_energy_drift"])) for row in transient_result.solver["time_history"]),
            "qf_dynamic_residual_max": max(float(row["dynamic_residual_norm"]) for row in transient_result.solver["time_history"]),
        },
        "harmonic": {
            "frequencies_hz": frequencies.tolist(),
            "relative_response_error_max": harmonic_error,
            "qf_relative_residual_max": float(harmonic_result.solver["max_relative_residual_norm"]),
        },
        "checks": checks,
        "limitations": [
            "The campaign does not replace external correlation.",
            "Rotary inertia, offsets, MPC/RBE links and nonlinear springs remain separate scopes.",
            "The stable claim remains bounded to the documented linear discrete entities.",
        ],
    }


def write_discrete_multidof_campaign(output: str | Path) -> dict[str, Any]:
    """Write the multi-DOF evidence, plot and manifest."""

    report = run_discrete_multidof_campaign()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    write_json_file(root / "summary.json", report)
    _plot(report, root / "discrete_multidof_results.png")
    (root / "report.md").write_text(_markdown(report), encoding="utf-8")
    write_vnv_manifest(root, report["study_id"])
    return report


def _model(analysis: str | dict[str, Any]) -> FiniteElementModel:
    def diagonal(kx: float) -> list[list[float]]:
        return [[kx, 0.0, 0.0], [0.0, 100.0, 0.0], [0.0, 0.0, 100.0]]

    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        elements=[],
        materials={},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}],
        loads=[{"node": 2, "dof": "UX", "value": 10.0}],
        springs=[
            {"node_a": 0, "node_b": 1, "dofs": ["UX", "UY", "UZ"], "stiffness": diagonal(1200.0)},
            {"node_a": 1, "node_b": 2, "dofs": ["UX", "UY", "UZ"], "stiffness": diagonal(800.0)},
            {"node_a": 2, "dofs": ["UX", "UY", "UZ"], "stiffness": diagonal(500.0)},
        ],
        concentrated_masses=[{"node": 1, "mass": 2.0}, {"node": 2, "mass": 3.0}],
        analysis=analysis,
    )


def _reduced_matrices(model: FiniteElementModel) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs).toarray()
    mass = assembler.assemble_mass(model, dofs).toarray()
    load = assembler.assemble_load_vectors(model, dofs)[0]
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof), fixed)
    return stiffness[np.ix_(free, free)], mass[np.ix_(free, free)], load[free], free


def _newmark_reference(stiffness: np.ndarray, mass: np.ndarray, load: np.ndarray) -> np.ndarray:
    displacement = np.zeros_like(load)
    velocity = np.zeros_like(load)
    acceleration = np.zeros_like(load)
    effective = stiffness + mass / (_BETA * _DT**2)
    history: list[float] = []
    for step in range(1, _STEPS + 1):
        factor = step / _STEPS
        force = factor * load
        rhs = force + mass @ (
            displacement / (_BETA * _DT**2)
            + velocity / (_BETA * _DT)
            + (1.0 / (2.0 * _BETA) - 1.0) * acceleration
        )
        next_displacement = np.linalg.solve(effective, rhs)
        next_acceleration = (next_displacement - displacement) / (_BETA * _DT**2)
        next_acceleration -= velocity / (_BETA * _DT)
        next_acceleration -= (1.0 / (2.0 * _BETA) - 1.0) * acceleration
        next_velocity = velocity + _DT * ((1.0 - _GAMMA) * acceleration + _GAMMA * next_acceleration)
        displacement, velocity, acceleration = next_displacement, next_velocity, next_acceleration
        history.append(float(displacement[-3]))
    return np.asarray(history)


def _relative_error(actual: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(actual) - np.asarray(reference)) / max(float(np.linalg.norm(reference)), 1.0e-30))


def _check(identifier: str, value: float) -> dict[str, Any]:
    return {"id": identifier, "value": float(value), "limit": _TOLERANCE, "status": "PASS" if value <= _TOLERANCE else "FAIL"}


def _plot(report: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(10.0, 7.0))
    static = np.asarray(report["static"]["qf_displacement"])
    reference = np.asarray(report["static"]["reference_displacement"])
    axes[0, 0].plot(static, "o-", label="QF_solver")
    axes[0, 0].plot(reference, "s--", label="reference")
    axes[0, 0].set_title("Statique multi-DDL")
    axes[0, 0].set_ylabel("Deplacement")
    axes[0, 0].legend()
    modal_qf = report["modal"]["qf_frequencies_hz"]
    modal_ref = report["modal"]["reference_frequencies_hz"]
    axes[0, 1].plot(modal_qf, "o-", label="QF_solver")
    axes[0, 1].plot(modal_ref, "s--", label="reference")
    axes[0, 1].set_title("Frequences propres")
    axes[0, 1].set_ylabel("Hz")
    axes[0, 1].legend()
    history = report["newmark"]["reference_history"] if "reference_history" in report["newmark"] else []
    if history:
        axes[1, 0].plot(history, label="reference")
    axes[1, 0].set_title("Newmark, historique de reference")
    axes[1, 0].set_xlabel("Pas")
    axes[1, 0].set_ylabel("UX pointe")
    frequencies = report["harmonic"]["frequencies_hz"]
    axes[1, 1].plot(frequencies, np.zeros(len(frequencies)), "o")
    axes[1, 1].set_title("Grille harmonique")
    axes[1, 1].set_xlabel("Frequence [Hz]")
    axes[1, 1].set_ylabel("Amplitude normalisee")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['study_id']}",
        "",
        f"Statut : **{report['status']}**.",
        "",
        "Cette campagne verifie une chaine discretes multi-DDL avec une reference matricielle independante. Elle complete la correlation externe Code_Aster du systeme mono-DDL, sans la remplacer.",
        "",
        "| Controle | Erreur relative | Limite | Verdict |",
        "| --- | ---: | ---: | --- |",
    ]
    for check in report["checks"]:
        lines.append(f"| {check['id']} | {check['value']:.3e} | {check['limit']:.3e} | {check['status']} |")
    lines.extend(
        [
            "",
            "![Resultats discret multi-DDL](discrete_multidof_results.png)",
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"
