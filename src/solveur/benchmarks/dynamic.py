"""Multi-element modal, Newmark and harmonic benchmark."""

from __future__ import annotations

import copy
import math

import numpy as np

from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.benchmarks.support import BenchmarkContext, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun
from solveur.core.analysis import AnalysisSettings
from solveur.core.qualification import enforce_qualification_policy
from solveur.core.router import AnalysisRouter
from solveur.io.json_writer import JsonResultWriter


def run_dynamic_cantilever(context: BenchmarkContext) -> BenchmarkRun:
    """Exercise three vibration solvers on the same meshed cantilever."""
    length, width, height = 4.0, 0.5, 0.5
    young, poisson, density = 210.0e9, 0.3, 7800.0
    mesh = BenchmarkMeshFactory().box_tetra(
        context.root / "dynamic_cantilever_tet4.msh",
        length=length,
        width=width,
        height=height,
        mesh_size=0.48,
    )
    setup = {
        "schema_version": 1,
        "mesh_scale_to_m": 1.0,
        "units": {"system": "SI"},
        "verification_profile": context.profile,
        "analysis": {"type": "linear_static", "method": "direct"},
        "materials": {"steel": {"type": "isotropic_3d", "E": young, "nu": poisson, "density": density}},
        "groups": [
            {
                "name": "domain",
                "dimension": 3,
                "actions": [{"type": "elements", "element_type": "TET4", "material": "steel"}],
            },
            {
                "name": "x_min",
                "dimension": 2,
                "actions": [{"type": "fixed_dofs", "dofs": ["UX", "UY", "UZ"]}],
            },
            {
                "name": "x_max",
                "dimension": 2,
                "actions": [{"type": "surface_traction", "value": [0.0, 0.0, -4000.0]}],
            },
        ],
    }
    model, static_result, files = context.import_and_solve(mesh, setup, prefix="static")
    modal_model = copy.deepcopy(model)
    modal_model.analysis = AnalysisSettings.from_raw(
        {"type": "modal", "method": "eigsh", "modes": 3, "arpack_tolerance": 1.0e-11}
    )
    modal = enforce_qualification_policy(AnalysisRouter().solve(modal_model), modal_model)
    modal_path = context.root / "modal.json"
    JsonResultWriter().write(modal, modal_path)
    files["modal_result"] = modal_path.name
    modal_data = modal.to_dict()
    frequency = float(modal_data["modes"][0]["frequency_hz"])
    modal_residual = max(float(value) for value in modal_data["solver"]["relative_residuals"])

    dynamic_model = copy.deepcopy(model)
    first_mode = np.asarray(modal.modes[:, 0], dtype=float)
    amplitude = 1.0e-4 / max(float(np.max(np.abs(first_mode))), 1.0e-30)
    period = 1.0 / frequency
    dt = period / 80.0
    dynamic_model.analysis = AnalysisSettings.from_raw(
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": dt,
            "steps": 240,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "load_factors": [0.0],
            "initial_displacements": _initial_entries(dynamic_model, first_mode * amplitude),
        }
    )
    dynamic = enforce_qualification_policy(AnalysisRouter().solve(dynamic_model), dynamic_model)
    dynamic_path = context.root / "newmark.json"
    JsonResultWriter().write(dynamic, dynamic_path)
    files["newmark_result"] = dynamic_path.name
    history = dynamic.to_dict()["solver"]["time_history"]
    energy_drift = max(abs(float(row["relative_energy_drift"])) for row in history)

    harmonic_model = copy.deepcopy(model)
    frequencies = [0.0, 0.5 * frequency, 0.85 * frequency, frequency, 1.15 * frequency, 1.5 * frequency]
    damping_ratio = 0.01
    harmonic_model.analysis = AnalysisSettings.from_raw(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": frequencies,
            "rayleigh_alpha": 2.0 * damping_ratio * 2.0 * math.pi * frequency,
            "rayleigh_beta": 0.0,
        }
    )
    harmonic = enforce_qualification_policy(AnalysisRouter().solve(harmonic_model), harmonic_model)
    harmonic_path = context.root / "harmonic.json"
    JsonResultWriter().write(harmonic, harmonic_path)
    files["harmonic_result"] = harmonic_path.name
    zero_hz_error = float(
        np.linalg.norm(np.asarray(harmonic.responses[0]).real - static_result.displacements)
        / max(np.linalg.norm(static_result.displacements), 1.0e-30)
    )
    tip_node = int(np.argmax(model.nodes[:, 0]))
    tip_dof = harmonic.dofs.index(tip_node, "UZ")
    amplitudes = [abs(response[tip_dof]) for response in harmonic.responses]
    peak_index = int(np.argmax(amplitudes))
    inertia = width * height**3 / 12.0
    area = width * height
    analytical_frequency = 1.875104068711961**2 / (2.0 * math.pi * length**2) * math.sqrt(
        young * inertia / (density * area)
    )
    criteria = context.descriptor.criteria
    checks = [
        upper_check("modal-residual", modal_residual, criteria["modal_residual_max"]),
        upper_check("newmark-energy", energy_drift, criteria["energy_drift_max"]),
        upper_check("harmonic-zero-hz", zero_hz_error, criteria["zero_hz_error_max"]),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks),
            {
                "first_frequency_hz": frequency,
                "analytical_beam_frequency_hz": analytical_frequency,
                "frequency_relative_error": abs((frequency - analytical_frequency) / analytical_frequency),
                "modal_max_relative_residual": modal_residual,
                "mass_orthogonality_error": modal_data["solver"]["mass_orthogonality_error"],
                "newmark_time_step": dt,
                "newmark_max_energy_drift": energy_drift,
                "harmonic_frequencies_hz": frequencies,
                "harmonic_tip_amplitudes": [float(value) for value in amplitudes],
                "harmonic_peak_frequency_hz": frequencies[peak_index],
                "harmonic_zero_hz_relative_error": zero_hz_error,
            },
            checks,
            files,
        )
    )


def _initial_entries(model: object, values: np.ndarray) -> list[dict[str, object]]:
    dofs = model.dof_manager()
    entries: list[dict[str, object]] = []
    for node, names in dofs.node_dofs.items():
        for name in names:
            value = float(values[dofs.index(node, name)])
            if abs(value) > 1.0e-18:
                entries.append({"node": node, "dof": name, "value": value})
    return entries
