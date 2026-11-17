"""Bounded NAFEMS 13H resonance diagnostics for J15.

The frequency-window vectors produced by this module are explicitly labeled
as unguarded diagnostics when the normal QF route rejects its residual guard.
They are not promoted to accepted QF solver results.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import time
import warnings
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.analyses.dynamic_controls import rayleigh_damping_definition
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.dofs import DofManager
from solveur.io.manifest import git_source_state
from solveur.paths import project_root
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor
from solveur.verification.external_correlation import load_abaqus_nafems_13h_reference
from solveur.verification.mitc4_harmonic_nafems import (
    _center_node,
    _navier_peak_reference,
    _navier_plate_response,
    build_nafems_13h_model,
)


PROJECT_ROOT = Path(project_root()).resolve()
DEFAULT_OUTPUT = PROJECT_ROOT / "research/j15/results/diagnostic-2026-11-17/nafems_13h_resonance"
CONTRACT_ID = "J15-MITC4-NAFEMS13H-RESONANCE-001"
ATTEMPT_ID = "J15-NAFEMS13H-RES-001"
FREQUENCY_START_HZ = 2.30
FREQUENCY_STOP_HZ = 2.45
FREQUENCY_COUNT = 151
COARSE_STRIDE = 5
MPMATH_DPS = 50


def rayleigh_modal_damping_ratio(alpha_s_inv: float, beta_s: float, frequency_hz: float) -> float:
    """Return the classical modal damping ratio for C=alpha*M+beta*K."""
    values = (alpha_s_inv, beta_s, frequency_hz)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("Rayleigh coefficients and frequency must be finite")
    if alpha_s_inv < 0.0 or beta_s < 0.0 or frequency_hz <= 0.0:
        raise ValueError("Rayleigh coefficients must be nonnegative and frequency positive")
    omega = 2.0 * math.pi * frequency_hz
    return float(0.5 * (alpha_s_inv / omega + beta_s * omega))


def analytic_resonance_reference(reference: dict[str, Any]) -> dict[str, float | str | int]:
    """Evaluate the independent thin-plate Navier frequency and damped peak."""
    signed = copy.deepcopy(reference)
    signed["model"]["pressure_pa"] = -abs(float(signed["model"]["pressure_pa"]))
    peak = _navier_peak_reference(signed)
    natural_hz = float(peak["fundamental_frequency_hz"])
    alpha = float(signed["model"]["rayleigh_damping"]["alpha_s_inv"])
    beta = float(signed["model"]["rayleigh_damping"]["beta_s"])
    band = (natural_hz * 0.95, natural_hz * 1.02)
    optimum = minimize_scalar(
        lambda frequency: -float(abs(_navier_plate_response(np.asarray([frequency]), signed)[0][0])),
        bounds=band,
        method="bounded",
        options={"xatol": 1.0e-12},
    )
    frequency = float(optimum.x)
    displacement, stress = _navier_plate_response(np.asarray([frequency]), signed)
    return {
        "method": "Kirchhoff-Love Navier odd-odd series evaluated independently of QF matrices",
        "series_max_odd_index": 51,
        "fundamental_frequency_hz": natural_hz,
        "damped_series_peak_frequency_hz": frequency,
        "damped_series_peak_uz_amplitude_mm": float(1000.0 * abs(displacement[0])),
        "damped_series_peak_uz_phase_degrees": float(np.degrees(np.angle(displacement[0]))),
        "damped_series_peak_top_s11_mpa": float(abs(stress[0]) / 1.0e6),
        "modal_damping_ratio_at_fundamental": rayleigh_modal_damping_ratio(alpha, beta, natural_hz),
    }


def complex_relative_difference(actual: complex, reference: complex, scale: float) -> float:
    """Normalize a complex error by a finite window scale, not a local response."""
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("normalization scale must be finite and positive")
    return float(abs(actual - reference) / scale)


def wrapped_phase_difference_degrees(actual: complex, reference: complex) -> float:
    """Return the smallest magnitude phase difference in degrees."""
    if abs(actual) == 0.0 or abs(reference) == 0.0:
        return float("nan")
    delta = np.angle(actual * np.conjugate(reference))
    return float(abs(np.degrees(delta)))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        result = float(value)
        return result if math.isfinite(result) else str(result)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _build_reduced_system(
    reference: dict[str, Any], frequency_hz: float
) -> tuple[
    FiniteElementModel,
    DofManager,
    DynamicDofReducer,
    csr_matrix,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    float,
]:
    damping = reference["model"]["rayleigh_damping"]
    analysis = {
        "type": "harmonic_response",
        "method": "direct_frequency",
        "frequencies_hz": [float(frequency_hz)],
        "rayleigh_alpha": float(damping["alpha_s_inv"]),
        "rayleigh_beta": float(damping["beta_s"]),
    }
    model, _quads = build_nafems_13h_model(reference, analysis=analysis, mesh_size=8)
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness, mass, _element_stiffness, _element_mass = assembler.assemble_stiffness_and_mass(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
    damping_definition = rayleigh_damping_definition(model.analysis.parameters)
    reduced_stiffness = reducer.stiffness
    reduced_mass = reducer.mass
    reduced_damping = (
        damping_definition.alpha * reduced_mass + damping_definition.beta * reduced_stiffness
    ).tocsr()
    reduced_loads = reducer.reduce_load(loads).astype(complex)
    return (
        model,
        dofs,
        reducer,
        csr_matrix(reduced_stiffness),
        np.asarray(reduced_mass.toarray(), dtype=float),
        np.asarray(reduced_damping.toarray(), dtype=complex),
        np.asarray(reduced_loads, dtype=complex),
        np.asarray(loads, dtype=complex),
        float(damping_definition.alpha),
        float(damping_definition.beta),
    )


def _system_at_frequency(
    reduced_stiffness: csr_matrix,
    reduced_mass: np.ndarray,
    reduced_damping: np.ndarray,
    reduced_loads: np.ndarray,
    frequency_hz: float,
) -> tuple[np.ndarray, np.ndarray]:
    omega = 2.0 * math.pi * frequency_hz
    impedance = reduced_stiffness.toarray().astype(complex)
    impedance += 1j * omega * reduced_damping
    impedance -= omega**2 * reduced_mass
    return impedance, reduced_loads.copy()


def _float_to_mpf_exact(value: float, mp: Any) -> Any:
    numerator, denominator = float(value).as_integer_ratio()
    return mp.mpf(numerator) / denominator


def _high_precision_solve(
    impedance: np.ndarray,
    loads: np.ndarray,
    scipy_solution: np.ndarray,
    *,
    decimal_places: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    import mpmath as mp

    mp.mp.dps = decimal_places
    size = loads.size
    matrix = mp.matrix(size, size)
    rhs = mp.matrix(size, 1)
    for row in range(size):
        rhs[row] = mp.mpc(
            _float_to_mpf_exact(loads[row].real, mp),
            _float_to_mpf_exact(loads[row].imag, mp),
        )
        for column in range(size):
            value = impedance[row, column]
            matrix[row, column] = mp.mpc(
                _float_to_mpf_exact(value.real, mp),
                _float_to_mpf_exact(value.imag, mp),
            )
    solution = mp.lu_solve(matrix, rhs)
    high_precision = np.asarray(
        [complex(solution[index]) for index in range(size)],
        dtype=complex,
    )
    max_delta = mp.mpf("0")
    max_reference = mp.mpf("0")
    max_solution = mp.mpf("0")
    for index in range(size):
        reference_value = solution[index]
        scipy_value = mp.mpc(
            _float_to_mpf_exact(scipy_solution[index].real, mp),
            _float_to_mpf_exact(scipy_solution[index].imag, mp),
        )
        max_delta = max(max_delta, abs(scipy_value - reference_value))
        max_reference = max(max_reference, abs(reference_value))
        max_solution = max(max_solution, abs(scipy_value))
    max_matrix_row_sum = max(sum(abs(matrix[row, column]) for column in range(size)) for row in range(size))
    max_rhs = max(abs(rhs[row]) for row in range(size))
    backward_denominator = max_matrix_row_sum * max_solution + max_rhs
    max_residual = mp.mpf("0")
    for row in range(size):
        residual = sum(matrix[row, column] * mp.mpc(
            _float_to_mpf_exact(scipy_solution[column].real, mp),
            _float_to_mpf_exact(scipy_solution[column].imag, mp),
        ) for column in range(size)) - rhs[row]
        max_residual = max(max_residual, abs(residual))
    relative_solution_difference = max_delta / max_reference if max_reference else mp.mpf("inf")
    backward_error = max_residual / backward_denominator if backward_denominator else mp.mpf("inf")
    return high_precision, {
        "library": "mpmath",
        "version": mp.__version__,
        "decimal_places": decimal_places,
        "same_binary64_impedance_and_load": True,
        "sparse_vs_high_precision_relative_solution_inf": float(relative_solution_difference),
        "sparse_solution_high_precision_backward_error_inf": float(backward_error),
    }


def _qf_route_status(frequency_hz: float, reference: dict[str, Any]) -> tuple[str, dict[str, Any], np.ndarray | None]:
    damping = reference["model"]["rayleigh_damping"]
    started = time.perf_counter()
    try:
        model, _quads = build_nafems_13h_model(
            reference,
            analysis={
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": [float(frequency_hz)],
                "rayleigh_alpha": float(damping["alpha_s_inv"]),
                "rayleigh_beta": float(damping["beta_s"]),
            },
            mesh_size=8,
        )
    except Exception as exc:
        return "HARNESS_ERROR", {
            "phase": "model_build",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "elapsed_seconds": float(time.perf_counter() - started),
        }, None
    try:
        result = solve_model(model, enforce_policy=False)
    except NumericalConvergenceError as exc:
        diagnostics = _json_value(getattr(exc, "diagnostics", {}))
        is_guard = bool(diagnostics) or "cannot demonstrate residual convergence" in str(exc).lower()
        category = "QF_GUARD_REJECTED" if is_guard else "QF_NUMERICAL_REJECTED"
        return category, {
            "phase": "solve_model",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "diagnostics": diagnostics,
            "elapsed_seconds": float(time.perf_counter() - started),
        }, None
    except Exception as exc:
        return "HARNESS_ERROR", {
            "phase": "solve_model",
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "elapsed_seconds": float(time.perf_counter() - started),
        }, None
    return (
        "QF_SOLVE_ACCEPTED",
        {
            "max_relative_residual": float(result.solver["max_relative_residual_norm"]),
            "elapsed_seconds": float(time.perf_counter() - started),
        },
        np.asarray(result.responses[0], dtype=complex),
    )


def _solution_observables(
    model: FiniteElementModel,
    dofs: DofManager,
    reducer: DynamicDofReducer,
    response: np.ndarray,
    full_loads: np.ndarray,
    stiffness_factor: complex,
) -> dict[str, Any]:
    expanded = reducer.expand_complex_state(response, full_loads, stiffness_factor=stiffness_factor)
    node = _center_node(model.nodes)
    displacement = complex(expanded[dofs.index(node, "UZ")])
    stress = complex(
        HarmonicShellStressPostProcessor().averaged_nodal_stress(
            model,
            dofs,
            expanded,
            node,
            face="top",
        )[0]
    )
    return {
        "expanded_response": expanded,
        "center_node": int(node),
        "center_probe_m": [5.0, 5.0, 0.0],
        "center_uz_real_mm": float(1000.0 * displacement.real),
        "center_uz_imag_mm": float(1000.0 * displacement.imag),
        "center_uz_amplitude_mm": float(1000.0 * abs(displacement)),
        "center_uz_phase_degrees": float(np.degrees(np.angle(displacement))),
        "center_top_s11_real_mpa": float(stress.real / 1.0e6),
        "center_top_s11_imag_mpa": float(stress.imag / 1.0e6),
        "center_top_s11_amplitude_mpa": float(abs(stress) / 1.0e6),
        "center_top_s11_phase_degrees": float(np.degrees(np.angle(stress))),
    }


def _atomic_frequency_record(
    output: Path,
    frequency_hz: float,
    row: dict[str, Any],
    diagnostic_response: np.ndarray,
    qf_response: np.ndarray | None,
    high_precision_response: np.ndarray | None = None,
    diagnostic_reduced_response: np.ndarray | None = None,
) -> None:
    key = f"{frequency_hz:.9f}".replace(".", "p")
    arrays: dict[str, np.ndarray] = {
        "diagnostic_response_real": diagnostic_response.real,
        "diagnostic_response_imag": diagnostic_response.imag,
    }
    if qf_response is not None:
        arrays["qf_route_response_real"] = qf_response.real
        arrays["qf_route_response_imag"] = qf_response.imag
    if diagnostic_reduced_response is not None:
        arrays["diagnostic_reduced_response_real"] = diagnostic_reduced_response.real
        arrays["diagnostic_reduced_response_imag"] = diagnostic_reduced_response.imag
    if high_precision_response is not None:
        arrays["high_precision_response_real"] = high_precision_response.real
        arrays["high_precision_response_imag"] = high_precision_response.imag
    checkpoint_dir = output / "raw" / "frequency_checkpoints"
    _atomic_npz(checkpoint_dir / f"frequency_{key}.npz", **arrays)
    clean_row = {key: value for key, value in row.items() if key != "_internal"}
    clean_row["checkpoint_stage"] = "POSTPROCESSED"
    clean_row["response_file"] = f"frequency_checkpoints/frequency_{key}.npz"
    _atomic_json(checkpoint_dir / f"frequency_{key}.json", clean_row)


def _checkpoint_reduced_response(
    output: Path,
    frequency_hz: float,
    response: np.ndarray,
    *,
    solver_warnings: list[str],
) -> None:
    """Persist the raw reduced vector before any observable recovery runs."""
    key = f"{frequency_hz:.9f}".replace(".", "p")
    checkpoint_dir = output / "raw" / "frequency_checkpoints"
    _atomic_npz(
        checkpoint_dir / f"frequency_{key}.npz",
        diagnostic_reduced_response_real=response.real,
        diagnostic_reduced_response_imag=response.imag,
    )
    _atomic_json(
        checkpoint_dir / f"frequency_{key}.json",
        {
            "schema": "qfsolver-j15-frequency-checkpoint-v1",
            "contract_id": CONTRACT_ID,
            "attempt_id": ATTEMPT_ID,
            "frequency_hz": frequency_hz,
            "checkpoint_stage": "RAW_REDUCED_SOLUTION_BEFORE_POSTPROCESSING",
            "qf_route_status": "NOT_RUN",
            "diagnostic_status": "RAW_UNGUARDED_QF_ASSEMBLED_SYSTEM_SPSOLVE",
            "diagnostic_solver": "scipy.sparse.linalg.spsolve",
            "diagnostic_vector_space": "reduced_dynamic_dofs",
            "solver_warnings": solver_warnings,
            "response_file": f"frequency_checkpoints/frequency_{key}.npz",
        },
    )


def _plot_response(rows: list[dict[str, Any]], reference_rows: list[dict[str, Any]], path: Path) -> None:
    if len(rows) != len(reference_rows):
        raise ValueError(
            "_plot_response requires the same number of QF and reference rows "
            f"(got {len(rows)} and {len(reference_rows)})"
        )

    def column(source_rows: list[dict[str, Any]], field: str, label: str) -> np.ndarray:
        values: list[float] = []
        for index, row in enumerate(source_rows):
            if field not in row:
                raise ValueError(f"_plot_response missing required field {field!r} in {label} row {index}")
            try:
                value = float(row[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"_plot_response field {field!r} in {label} row {index} must be numeric"
                ) from exc
            if not math.isfinite(value):
                raise ValueError(f"_plot_response field {field!r} in {label} row {index} must be finite")
            values.append(value)
        return np.asarray(values, dtype=float)

    frequencies = column(rows, "frequency_hz", "QF")
    reference_frequencies = column(reference_rows, "frequency_hz", "reference")
    if not np.allclose(frequencies, reference_frequencies, rtol=0.0, atol=1.0e-12):
        raise ValueError("_plot_response QF and reference rows must use the same frequencies")
    qf_amplitude = column(rows, "diagnostic_center_uz_amplitude_mm", "QF")
    qf_phase = column(rows, "diagnostic_center_uz_phase_degrees", "QF")
    ref_amplitude = column(reference_rows, "reference_uz_amplitude_mm", "reference")
    ref_phase = column(reference_rows, "reference_uz_phase_degrees", "reference")
    route_statuses = [row.get("qf_route_status") for row in rows]
    if any(not isinstance(status, str) or not status for status in route_statuses):
        raise ValueError("_plot_response requires a non-empty qf_route_status for every QF row")
    if np.any(qf_amplitude < 0.0) or np.any(ref_amplitude < 0.0):
        raise ValueError("_plot_response amplitude fields must be nonnegative")

    max_amplitude = float(np.max(qf_amplitude))
    phase_mask = (qf_amplitude >= 0.05 * max_amplitude) & (qf_amplitude > 0.0)
    rejected = np.asarray([status != "QF_SOLVE_ACCEPTED" for status in route_statuses], dtype=bool)
    figure, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True, constrained_layout=True)
    axes[0].plot(frequencies, qf_amplitude, color="#b23a48", label="QF-assembled direct diagnostic (unaccepted)")
    axes[0].plot(frequencies, ref_amplitude, "--", color="#176b87", label="Signed Navier thin-plate reference")
    axes[0].scatter(frequencies[rejected], qf_amplitude[rejected], marker="x", s=15, color="#5f0f40", label="QF route rejected; diagnostic vector shown")
    axes[0].set_ylabel("Center |UZ| (mm)")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    axes[1].plot(frequencies[phase_mask], qf_phase[phase_mask], color="#b23a48", label="QF-assembled diagnostic")
    axes[1].plot(frequencies[phase_mask], ref_phase[phase_mask], "--", color="#176b87", label="Navier reference")
    rejected_phase = rejected & phase_mask
    axes[1].scatter(
        frequencies[rejected_phase],
        qf_phase[rejected_phase],
        marker="x",
        s=15,
        color="#5f0f40",
        label="QF route rejected; diagnostic phase shown",
    )
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].set_ylabel("Phase of UZ (degrees)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    axes[0].set_title("NAFEMS 13H first-mode neighborhood — raw diagnostic vectors retain QF guard status")
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_deformed(
    model: FiniteElementModel,
    quads: np.ndarray,
    response: np.ndarray,
    frequency_hz: float,
    path: Path,
) -> float:
    node = _center_node(model.nodes)
    dofs = model.dof_manager()
    phase = np.angle(response[dofs.index(node, "UZ")])
    phase_aligned = response * np.exp(-1j * phase)
    uz = np.asarray([phase_aligned[dofs.index(index, "UZ")].real for index in range(model.node_count)])
    maximum = max(float(np.max(np.abs(uz))), 1.0e-30)
    target_display_amplitude_m = 0.1
    factor = target_display_amplitude_m / maximum
    deformed = np.asarray(model.nodes, dtype=float).copy()
    deformed[:, 2] += factor * uz
    figure = plt.figure(figsize=(8, 6))
    axis = figure.add_subplot(111, projection="3d")
    for face in quads:
        closed = np.append(face, face[0])
        axis.plot(*deformed[closed].T, color="#176b87", linewidth=0.65)
    axis.scatter(*deformed.T, c=factor * uz * 1000.0, cmap="coolwarm", s=13)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_zlabel("z display (m)")
    axis.set_title(f"Unaccepted direct-system diagnostic at {frequency_hz:.4f} Hz; display factor {factor:.3e}")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return factor


def _condition_number(impedance: np.ndarray) -> float:
    return float(np.linalg.cond(impedance, p=2))


def _artifact_manifest(output: Path) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "artifact_manifest.json"):
        manifest.append(
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    _atomic_json(output / "artifact_manifest.json", {"schema": "qfsolver-j15-artifact-manifest-v1", "artifacts": manifest})
    return manifest


def run_j15_resonance_diagnostic(output_dir: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    """Sweep the first-mode window and preserve QF route and diagnostic statuses separately."""
    output = Path(output_dir)
    checkpoint_dir = output / "raw" / "frequency_checkpoints"
    assets = output / "site_assets"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    reference = load_abaqus_nafems_13h_reference()
    signed_reference = copy.deepcopy(reference)
    signed_reference["model"]["pressure_pa"] = -abs(float(signed_reference["model"]["pressure_pa"]))
    reference_summary = analytic_resonance_reference(reference)
    frequencies = np.linspace(FREQUENCY_START_HZ, FREQUENCY_STOP_HZ, FREQUENCY_COUNT)
    high_precision_frequency = float(reference_summary["damped_series_peak_frequency_hz"])
    all_frequencies = [float(value) for value in frequencies] + [high_precision_frequency]

    (
        model,
        dofs,
        reducer,
        reduced_stiffness,
        reduced_mass,
        reduced_damping,
        reduced_loads,
        full_loads,
        alpha,
        beta,
    ) = _build_reduced_system(reference, all_frequencies[0])
    _quads = build_nafems_13h_model(
        reference,
        analysis={
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [all_frequencies[0]],
            "rayleigh_alpha": alpha,
            "rayleigh_beta": beta,
        },
        mesh_size=8,
    )[1]
    reference_u, reference_s = _navier_plate_response(frequencies, signed_reference)
    qf_rows: list[dict[str, Any]] = []
    route_counts: dict[str, int] = {}
    probe_records: list[dict[str, Any]] = []
    high_precision_metadata: dict[str, Any] | None = None
    high_precision_full_response: np.ndarray | None = None
    started = time.perf_counter()
    coarse_indices = set(range(0, FREQUENCY_COUNT, COARSE_STRIDE)) | {FREQUENCY_COUNT - 1}

    for index, frequency in enumerate(all_frequencies):
        frequency_started = time.perf_counter()
        impedance, load_vector = _system_at_frequency(
            reduced_stiffness,
            reduced_mass,
            reduced_damping,
            reduced_loads,
            frequency,
        )
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            diagnostic_reduced_response = np.asarray(spsolve(csr_matrix(impedance), load_vector), dtype=complex)
        _checkpoint_reduced_response(
            output,
            frequency,
            diagnostic_reduced_response,
            solver_warnings=[str(item.message) for item in caught_warnings],
        )
        if diagnostic_reduced_response.ndim != 1 or not np.all(np.isfinite(diagnostic_reduced_response)):
            row = {
                "schema": "qfsolver-j15-frequency-checkpoint-v1",
                "contract_id": CONTRACT_ID,
                "attempt_id": ATTEMPT_ID,
                "frequency_hz": frequency,
                "qf_route_status": "NOT_RUN_AFTER_DIAGNOSTIC_FAILURE",
                "diagnostic_status": "RAW_SPARSE_SOLVE_FAILED",
                "diagnostic_exception_type": "NonFiniteOrMalformedResponse",
            }
            _atomic_json(checkpoint_dir / f"frequency_{frequency:.9f}".replace(".", "p") + ".json", row)
            raise NumericalConvergenceError("The J15 unguarded diagnostic solve returned a non-finite response.")

        omega = 2.0 * math.pi * frequency
        stiffness_factor = 1.0 + 1j * omega * beta
        observables = _solution_observables(
            model,
            dofs,
            reducer,
            diagnostic_reduced_response,
            full_loads,
            stiffness_factor,
        )
        full_response = observables.pop("expanded_response")
        product = impedance @ diagnostic_reduced_response
        residual = product - load_vector
        residual_l2 = float(np.linalg.norm(residual))
        reference_l2 = max(float(np.linalg.norm(load_vector)), float(np.linalg.norm(product)))
        relative_l2 = residual_l2 / reference_l2 if reference_l2 else (0.0 if residual_l2 == 0.0 else float("inf"))
        matrix_inf = float(np.linalg.norm(impedance, ord=np.inf))
        solution_inf = float(np.linalg.norm(diagnostic_reduced_response, ord=np.inf))
        rhs_inf = float(np.linalg.norm(load_vector, ord=np.inf))
        residual_inf = float(np.linalg.norm(residual, ord=np.inf))
        denominator = matrix_inf * solution_inf + rhs_inf
        backward_error = residual_inf / denominator if denominator else float("inf")
        qf_status, qf_details, qf_response = _qf_route_status(frequency, reference)
        route_counts[qf_status] = route_counts.get(qf_status, 0) + 1

        if index < FREQUENCY_COUNT:
            navier_u = complex(reference_u[index])
            navier_s = complex(reference_s[index])
            qf_u = complex(full_response[dofs.index(_center_node(model.nodes), "UZ")])
            qf_amplitude = float(abs(qf_u) * 1000.0)
            navier_amplitude = float(abs(navier_u) * 1000.0)
            qf_rows.append(
                {
                    "frequency_hz": frequency,
                    "qf_route_status": qf_status,
                    "qf_route_details": qf_details,
                    "diagnostic_status": "RAW_UNGUARDED_QF_ASSEMBLED_SYSTEM_SPSOLVE",
                    "diagnostic_solution_method": "scipy.sparse.linalg.spsolve; production residual guard not applied to this returned vector",
                    "diagnostic_center_uz_amplitude_mm": qf_amplitude,
                    "diagnostic_center_uz_phase_degrees": float(np.degrees(np.angle(qf_u))),
                    "diagnostic_center_top_s11_amplitude_mpa": observables["center_top_s11_amplitude_mpa"],
                    "diagnostic_center_top_s11_phase_degrees": observables["center_top_s11_phase_degrees"],
                    "reference_uz_amplitude_mm": navier_amplitude,
                    "reference_uz_phase_degrees": float(np.degrees(np.angle(navier_u))),
                    "reference_top_s11_amplitude_mpa": float(abs(navier_s) / 1.0e6),
                    "reference_top_s11_phase_degrees": float(np.degrees(np.angle(navier_s))),
                    "complex_uz_difference_m": float(abs(qf_u - navier_u)),
                    "phase_difference_degrees": wrapped_phase_difference_degrees(qf_u, navier_u),
                    "diagnostic_reduced_residual_l2": residual_l2,
                    "diagnostic_reduced_relative_residual_l2": relative_l2,
                    "diagnostic_reduced_backward_error_inf": backward_error,
                    "diagnostic_full_response_finite": bool(np.all(np.isfinite(full_response))),
                    "scipy_warnings": [str(item.message) for item in caught_warnings],
                }
            )

        condition_number = None
        if any(abs(frequency - target) <= 5.1e-4 for target in (FREQUENCY_START_HZ, high_precision_frequency, FREQUENCY_STOP_HZ)):
            condition_number = _condition_number(impedance)
        row = {
            "schema": "qfsolver-j15-frequency-checkpoint-v1",
            "contract_id": CONTRACT_ID,
            "attempt_id": ATTEMPT_ID,
            "frequency_hz": frequency,
            "frequency_role": "dense_grid" if index < FREQUENCY_COUNT else "exact_Navier_damped_peak_probe",
            "qf_route_status": qf_status,
            "qf_route_details": qf_details,
            "diagnostic_status": "RAW_UNGUARDED_QF_ASSEMBLED_SYSTEM_SPSOLVE",
            "diagnostic_solver": "scipy.sparse.linalg.spsolve",
            "reduced_system_size": int(impedance.shape[0]),
            "diagnostic_reduced_residual_l2": residual_l2,
            "diagnostic_reduced_relative_residual_l2": relative_l2,
            "diagnostic_reduced_backward_error_inf": backward_error,
            "diagnostic_center_uz_amplitude_mm": observables["center_uz_amplitude_mm"],
            "diagnostic_center_uz_phase_degrees": observables["center_uz_phase_degrees"],
            "diagnostic_center_top_s11_amplitude_mpa": observables["center_top_s11_amplitude_mpa"],
            "diagnostic_center_top_s11_phase_degrees": observables["center_top_s11_phase_degrees"],
            "condition_number_2": condition_number,
            "scipy_warnings": [str(item.message) for item in caught_warnings],
            "conclusion_scope": "diagnostic solution of the QF-assembled reduced system; not an accepted QF route result",
        }

        high_precision_response: np.ndarray | None = None
        if index == FREQUENCY_COUNT:
            high_precision_response, high_precision_metadata = _high_precision_solve(
                impedance,
                load_vector,
                diagnostic_reduced_response,
                decimal_places=MPMATH_DPS,
            )
            high_precision_response = reducer.expand_complex_state(
                high_precision_response,
                full_loads,
                stiffness_factor=stiffness_factor,
            )
            high_precision_metadata["frequency_hz"] = frequency
            high_precision_full_response = high_precision_response.copy()
            probe_records.append(row)

        row["frequency_elapsed_seconds"] = float(time.perf_counter() - frequency_started)
        _atomic_frequency_record(
            output,
            frequency,
            row,
            full_response,
            qf_response,
            high_precision_response,
            diagnostic_reduced_response,
        )
        if index < FREQUENCY_COUNT:
            qf_rows[-1]["frequency_elapsed_seconds"] = row["frequency_elapsed_seconds"]
        if qf_status == "HARNESS_ERROR":
            probe_records.append({"frequency_hz": frequency, "qf_route_status": qf_status, "details": qf_details})

    qf_amplitudes = np.asarray([row["diagnostic_center_uz_amplitude_mm"] for row in qf_rows])
    reference_amplitudes = np.asarray([row["reference_uz_amplitude_mm"] for row in qf_rows])
    qf_peak_index = int(np.argmax(qf_amplitudes))
    reference_peak_index = int(np.argmax(reference_amplitudes))
    comparison_scale_m = max(float(np.max(qf_amplitudes)), 1.0e-30) / 1000.0
    complex_errors = np.asarray([row["complex_uz_difference_m"] / comparison_scale_m for row in qf_rows])
    phase_mask = qf_amplitudes >= 0.05 * float(np.max(qf_amplitudes))
    for row, complex_error, interpretable in zip(qf_rows, complex_errors, phase_mask, strict=True):
        row["complex_uz_difference_normalized_by_qf_window_peak"] = float(complex_error)
        if not interpretable:
            row["phase_difference_degrees"] = None
    phase_errors = np.asarray(
        [row["phase_difference_degrees"] for row in qf_rows if row["phase_difference_degrees"] is not None],
        dtype=float,
    )
    coarse_rows = [row for index, row in enumerate(qf_rows) if index in coarse_indices]
    coarse_peak = max(coarse_rows, key=lambda row: row["diagnostic_center_uz_amplitude_mm"])
    coarse_reference_peak = max(coarse_rows, key=lambda row: row["reference_uz_amplitude_mm"])
    _plot_response(qf_rows, [
        {
            "frequency_hz": row["frequency_hz"],
            "reference_uz_amplitude_mm": row["reference_uz_amplitude_mm"],
            "reference_uz_phase_degrees": row["reference_uz_phase_degrees"],
        }
        for row in qf_rows
    ], assets / "harmonic_amplitude_phase.png")
    peak_row = qf_rows[qf_peak_index]
    peak_vector_path = checkpoint_dir / (f"frequency_{peak_row['frequency_hz']:.9f}".replace(".", "p") + ".npz")
    with np.load(peak_vector_path) as peak_data:
        peak_response = peak_data["diagnostic_response_real"] + 1j * peak_data["diagnostic_response_imag"]
    amplification = _plot_deformed(
        model,
        _quads,
        peak_response,
        peak_row["frequency_hz"],
        assets / "harmonic_peak_displacement.png",
    )
    output_payload = {
        "schema": "qfsolver-j15-harmonic-resonance-v1",
        "classification": "COMPLETED_EXPLORATORY_WITH_QF_GUARD_STATUSES_AND_UNGUARDED_DIAGNOSTIC_VECTORS",
        "contract_id": CONTRACT_ID,
        "attempt_id": ATTEMPT_ID,
        "source": git_source_state(PROJECT_ROOT),
        "runtime": {
            "python": __import__("platform").python_version(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "model": {
            "geometry_m": [10.0, 10.0, 0.05],
            "material": reference["model"]["material"],
            "element": "MITC4",
            "mesh": [8, 8],
            "pressure_qf_pa": float(reference["model"]["pressure_pa"]),
            "pressure_direction_qf": "-Z from positive shell pressure and +Z oriented face normal",
            "pressure_signed_reference_pa": float(signed_reference["model"]["pressure_pa"]),
            "rayleigh_alpha_s_inv": alpha,
            "rayleigh_beta_s": beta,
            "observable": "center UZ at (5,5,0)m; top S11 by complex nodal averaging",
            "reduced_dof_count": int(reduced_loads.size),
            "full_dof_count": int(model.dof_manager().ndof),
        },
        "reference": reference_summary,
        "frequency_study": {
            "dense_hz": [FREQUENCY_START_HZ, FREQUENCY_STOP_HZ, FREQUENCY_COUNT],
            "dense_spacing_hz": float((FREQUENCY_STOP_HZ - FREQUENCY_START_HZ) / (FREQUENCY_COUNT - 1)),
            "coarse_indices": sorted(coarse_indices),
            "coarse_count": len(coarse_rows),
            "coarse_spacing_hz": float(COARSE_STRIDE * (FREQUENCY_STOP_HZ - FREQUENCY_START_HZ) / (FREQUENCY_COUNT - 1)),
            "coarse_sampled_peak_frequency_hz": float(coarse_peak["frequency_hz"]),
            "coarse_sampled_peak_uz_mm": float(coarse_peak["diagnostic_center_uz_amplitude_mm"]),
            "coarse_reference_sampled_peak_frequency_hz": float(coarse_reference_peak["frequency_hz"]),
            "coarse_reference_sampled_peak_uz_mm": float(coarse_reference_peak["reference_uz_amplitude_mm"]),
            "high_precision_probe_hz": high_precision_frequency,
        },
        "residual_and_conditioning": {
            "qf_production_route_status_counts": route_counts,
            "qf_threshold_unchanged": 1.0e-7,
            "production_route_rejection_policy": "NumericalConvergenceError statuses and diagnostics are preserved pointwise; no threshold is relaxed.",
            "condition_number_probe_status": "recorded at band endpoints and exact Navier damped-series peak",
            "high_precision_same_matrix_probe": high_precision_metadata,
        },
        "comparison": {
            "qf_diagnostic_sampled_peak_frequency_hz": float(peak_row["frequency_hz"]),
            "qf_diagnostic_sampled_peak_uz_mm": float(peak_row["diagnostic_center_uz_amplitude_mm"]),
            "navier_sampled_peak_frequency_hz": float(qf_rows[reference_peak_index]["frequency_hz"]),
            "navier_sampled_peak_uz_mm": float(qf_rows[reference_peak_index]["reference_uz_amplitude_mm"]),
            "sampled_peak_shift_hz": float(peak_row["frequency_hz"] - qf_rows[reference_peak_index]["frequency_hz"]),
            "max_complex_uz_difference_normalized_by_qf_window_peak": float(np.max(complex_errors)),
            "rms_complex_uz_difference_normalized_by_qf_window_peak": float(np.sqrt(np.mean(complex_errors**2))),
            "max_absolute_uz_amplitude_difference_mm": float(max(abs(a - b) for a, b in zip(qf_amplitudes, reference_amplitudes, strict=True))),
            "rms_absolute_uz_amplitude_difference_mm": float(np.sqrt(np.mean((qf_amplitudes - reference_amplitudes) ** 2))),
            "phase_reporting_threshold": "diagnostic |UZ| >= 5% of its own band maximum",
            "phase_comparison_count": int(np.count_nonzero(phase_mask)),
            "max_absolute_phase_difference_degrees": float(np.max(phase_errors)) if phase_errors.size else None,
            "reference_limit": "Navier is a thin Kirchhoff-Love plate; QF is finite-mesh MITC4/Reissner-Mindlin. Diagnostic vectors are not accepted QF results when the production guard rejects them.",
        },
        "display": {
            "peak_displacement_display_amplification": amplification,
            "target_display_amplitude_m": 0.1,
            "phase_aligned": True,
            "diagnostic_vector_frequency_hz": float(peak_row["frequency_hz"]),
        },
        "elapsed_seconds": float(time.perf_counter() - started),
        "frequency_rows": qf_rows,
        "additional_probes": probe_records,
    }
    _atomic_json(output / "site_data.json", output_payload)
    _write_csv(qf_rows, output / "frequency_response.csv")
    manifest = _artifact_manifest(output)
    output_payload["artifact_count"] = len(manifest)
    _atomic_json(output / "site_data.json", output_payload)
    # Refresh the manifest for the final site_data.json bytes.
    _artifact_manifest(output)
    if len(qf_rows) != FREQUENCY_COUNT or any(not row["diagnostic_full_response_finite"] for row in qf_rows):
        raise AssertionError("J15 requires one finite durable diagnostic response for every contracted frequency")
    if any(row["qf_route_status"] == "HARNESS_ERROR" for row in qf_rows):
        raise AssertionError("unexpected QF route harness error; the pointwise trace is preserved")
    if high_precision_full_response is None or not np.all(np.isfinite(high_precision_full_response)):
        raise AssertionError("J15 high-precision probe did not produce a finite diagnostic vector")
    return output_payload


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = (
        "frequency_hz",
        "qf_route_status",
        "diagnostic_status",
        "diagnostic_center_uz_amplitude_mm",
        "diagnostic_center_uz_phase_degrees",
        "reference_uz_amplitude_mm",
        "reference_uz_phase_degrees",
        "complex_uz_difference_normalized_by_qf_window_peak",
        "phase_difference_degrees",
        "diagnostic_reduced_relative_residual_l2",
        "diagnostic_reduced_backward_error_inf",
    )
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
