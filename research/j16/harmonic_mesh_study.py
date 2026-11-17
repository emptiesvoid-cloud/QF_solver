from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh, spsolve

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from research.j15.harmonic_resonance import wrapped_phase_difference_degrees
from solveur.api import solve_model
from solveur.core.analyses.dynamic_controls import rayleigh_damping_definition
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.verification.external_correlation import load_abaqus_nafems_13h_reference
from solveur.verification.mitc4_harmonic_nafems import (
    _center_node,
    _navier_plate_response,
    build_nafems_13h_model,
)


DENSE_FREQUENCIES_HZ = tuple(float(value) for value in np.linspace(2.25, 2.55, 61))
REFERENCE_PEAK_PROBE_HZ = 2.375818178440047
FREQUENCIES_HZ = tuple(sorted(set(DENSE_FREQUENCIES_HZ + (REFERENCE_PEAK_PROBE_HZ,))))
RESIDUAL_LIMIT = 1.0e-7
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "research/j16/contracts/nafems_13h_mesh_study_001.json"
REFERENCE_PATH = PROJECT_ROOT / "qualification/external_reference_digests/abaqus_nafems_13h_harmonic.json"
OUTPUT_ROOT = PROJECT_ROOT / "research/j16/results/diagnostic-2026-11-17/mesh_study_001"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    temporary = path.with_name(f".{path.stem}.tmp.npz")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_identity() -> dict[str, str]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=PROJECT_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    return {"commit": commit, "branch": branch}


def _validate_contract(mesh_size: int, reference: dict[str, Any]) -> tuple[dict[str, Any], str]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if (
        contract.get("contract_id") != "J16-MITC4-NAFEMS13H-MESH-STUDY-001"
        or contract.get("state") != "FROZEN_BEFORE_EXECUTION"
    ):
        raise ValueError("the J16 multi-mesh contract is missing or not frozen")
    inputs = contract.get("inputs", {})
    if mesh_size not in inputs.get("mesh_sizes_per_edge", []):
        raise ValueError(f"mesh size {mesh_size} is not registered in the frozen contract")
    grid = inputs.get("frequency_grid_hz", {})
    dense = np.linspace(float(grid.get("dense_start", math.nan)), float(grid.get("dense_stop", math.nan)), int(grid.get("dense_count", 0)))
    expected_frequencies = tuple(sorted(set(float(value) for value in dense) | {float(grid.get("additional_probe_hz", math.nan))}))
    if (
        len(expected_frequencies) != len(FREQUENCIES_HZ)
        or not np.allclose(expected_frequencies, FREQUENCIES_HZ, rtol=0.0, atol=1.0e-12)
        or grid.get("total_count") != len(FREQUENCIES_HZ)
    ):
        raise ValueError("the runtime frequency grid differs from the frozen contract")
    if _sha256(REFERENCE_PATH) != inputs.get("reference_artifact_sha256"):
        raise ValueError("the NAFEMS external reference digest differs from the frozen contract")
    for relative_path, expected_sha256 in contract.get("source_sha256", {}).items():
        source_path = (PROJECT_ROOT / relative_path).resolve(strict=True)
        if not source_path.is_relative_to(PROJECT_ROOT.resolve()) or _sha256(source_path) != expected_sha256:
            raise ValueError(f"a source file differs from the frozen contract: {relative_path}")
    expected_model = inputs.get("model", {})
    if (
        reference["model"].get("geometry_m") != expected_model.get("geometry_m")
        or reference["model"].get("material") != expected_model.get("material")
        or reference["model"].get("pressure_pa") != expected_model.get("pressure_pa")
        or reference["model"].get("rayleigh_damping") != expected_model.get("rayleigh_damping")
        or reference["model"].get("boundary_conditions") != expected_model.get("boundary_conditions")
    ):
        raise ValueError("the loaded NAFEMS model inputs differ from the frozen contract")
    return contract, _sha256(CONTRACT_PATH)


def _build_mesh_system(
    reference: dict[str, Any], mesh_size: int
) -> tuple[
    FiniteElementModel,
    np.ndarray,
    DofManager,
    DynamicDofReducer,
    csr_matrix,
    csr_matrix,
    csr_matrix,
    np.ndarray,
    np.ndarray,
    float,
    dict[str, Any],
]:
    damping = reference["model"]["rayleigh_damping"]
    model, quads = build_nafems_13h_model(
        reference,
        analysis={
            "type": "harmonic_response",
            "method": "direct_frequency",
            "frequencies_hz": [DENSE_FREQUENCIES_HZ[0]],
            "rayleigh_alpha": float(damping["alpha_s_inv"]),
            "rayleigh_beta": float(damping["beta_s"]),
        },
        mesh_size=mesh_size,
    )
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness, mass, _element_stiffness, _element_mass = assembler.assemble_stiffness_and_mass(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
    damping_definition = rayleigh_damping_definition(model.analysis.parameters)
    reduced_stiffness = csr_matrix(reducer.stiffness)
    reduced_mass = csr_matrix(reducer.mass)
    reduced_damping = csr_matrix(
        damping_definition.alpha * reduced_mass + damping_definition.beta * reduced_stiffness
    )
    reduced_loads = reducer.reduce_load(loads).astype(complex)
    return (
        model,
        quads,
        dofs,
        reducer,
        reduced_stiffness,
        reduced_mass,
        reduced_damping,
        reduced_loads,
        np.asarray(loads, dtype=float),
        float(damping_definition.beta),
        assembler.last_load_diagnostics.copy(),
    )


def _load_resultant(
    model: FiniteElementModel,
    dofs: DofManager,
    full_loads: np.ndarray,
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    assembled = [float(value) for value in diagnostic["resultant"]]
    direct = []
    for component in ("UX", "UY", "UZ"):
        indices = [dofs.index(node, component) for node in range(model.node_count) if dofs.has(node, component)]
        direct.append(float(np.sum(np.asarray(full_loads, dtype=float)[indices])))
    return {
        "assembler_load_balance_resultant_n": assembled,
        "direct_sum_of_nodal_translational_load_dofs_n": direct,
        "direct_minus_assembler_resultant_n": [direct[index] - assembled[index] for index in range(3)],
        "assembler_moment_about_origin_nm": [float(value) for value in diagnostic["moment_about_origin"]],
        "analytic_expected_force_n": [0.0, 0.0, -10000.0],
        "direct_minus_analytic_expected_force_n": [
            direct[component] - expected for component, expected in enumerate((0.0, 0.0, -10000.0))
        ],
        "analytic_basis": "100 Pa uniform pressure over 10 m x 10 m flat reference area, physical direction -Z",
    }


def _quadratic_peak(frequencies: np.ndarray, amplitudes: np.ndarray, index: int) -> dict[str, float | None]:
    if index <= 0 or index >= len(frequencies) - 1:
        return {"frequency_hz": None, "amplitude_mm": None}
    x = frequencies[index - 1 : index + 2]
    y = np.log(np.maximum(amplitudes[index - 1 : index + 2], np.finfo(float).tiny))
    a, b, c = np.polyfit(x, y, 2)
    if a >= 0.0:
        return {"frequency_hz": None, "amplitude_mm": None}
    peak_frequency = float(-b / (2.0 * a))
    if not (x[0] <= peak_frequency <= x[-1]):
        return {"frequency_hz": None, "amplitude_mm": None}
    return {"frequency_hz": peak_frequency, "amplitude_mm": float(np.exp(np.polyval((a, b, c), peak_frequency)))}


def _route_solve(reference: dict[str, Any], mesh_size: int, frequency_hz: float) -> tuple[str, dict[str, Any], np.ndarray | None]:
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
            mesh_size=mesh_size,
        )
        result = solve_model(model, enforce_policy=False)
    except NumericalConvergenceError as exc:
        diagnostics = getattr(exc, "diagnostics", {})
        message = str(exc).lower()
        guard = (
            "relative_residual_upper_bound" in diagnostics
            or "residual_failure_tolerance" in diagnostics
            or "cannot demonstrate residual convergence" in message
        )
        return (
            "QF_GUARD_REJECTED" if guard else "QF_NUMERICAL_REJECTED",
            {
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "diagnostics": diagnostics,
                "elapsed_seconds": float(time.perf_counter() - started),
            },
            None,
        )
    except Exception as exc:
        return (
            "HARNESS_ERROR",
            {"exception_type": type(exc).__name__, "message": str(exc), "elapsed_seconds": time.perf_counter() - started},
            None,
        )
    response = np.asarray(result.responses[0], dtype=complex)
    if response.ndim != 1 or not np.all(np.isfinite(response)):
        return (
            "HARNESS_ERROR",
            {
                "exception_type": "MalformedResponseError",
                "message": "QF returned a non-vector or non-finite complex response",
                "elapsed_seconds": float(time.perf_counter() - started),
            },
            None,
        )
    return (
        "QF_SOLVE_ACCEPTED",
        {
            "max_relative_residual": (
                float(result.solver["max_relative_residual_norm"])
                if result.solver.get("max_relative_residual_norm") is not None
                else None
            ),
            "elapsed_seconds": float(time.perf_counter() - started),
        },
        response,
    )


def _frequency_checkpoint(
    output: Path,
    mesh_size: int,
    frequency_hz: float,
    qf_status: str,
    qf_details: dict[str, Any],
    reduced_response: np.ndarray,
    full_response: np.ndarray,
    residual_metrics: dict[str, float],
    reference_response: complex,
    center_response: complex,
    qf_center_response: complex | None,
    phase_mask: bool,
    reference_band_peak_m: float,
) -> dict[str, Any]:
    key = f"frequency_{frequency_hz:.9f}".replace(".", "p")
    npz_name = f"mesh_{mesh_size:02d}_{key}.npz"
    _atomic_npz(
        output / npz_name,
        raw_reduced_real=reduced_response.real,
        raw_reduced_imag=reduced_response.imag,
        raw_full_real=full_response.real,
        raw_full_imag=full_response.imag,
        qf_center_uz_real=np.asarray(qf_center_response.real if qf_center_response is not None else np.nan),
        qf_center_uz_imag=np.asarray(qf_center_response.imag if qf_center_response is not None else np.nan),
    )
    row = {
        "frequency_hz": float(frequency_hz),
        "frequency_role": "reference_peak_probe" if frequency_hz == REFERENCE_PEAK_PROBE_HZ else "shared_dense_grid",
        "mesh_size": mesh_size,
        "qf_route_status": qf_status,
        "qf_route_details": qf_details,
        "raw_solution_status": "RAW_UNGUARDED_QF_ASSEMBLED_SYSTEM_SPSOLVE",
        "raw_center_uz_amplitude_mm": float(abs(center_response) * 1000.0),
        "raw_center_uz_phase_degrees": float(np.degrees(np.angle(center_response))),
        "reference_center_uz_amplitude_mm": float(abs(reference_response) * 1000.0),
        "reference_center_uz_phase_degrees": float(np.degrees(np.angle(reference_response))),
        "absolute_amplitude_difference_mm": float(abs(abs(center_response) - abs(reference_response)) * 1000.0),
        "complex_error_normalized_by_reference_band_peak": float(
            abs(center_response - reference_response) / reference_band_peak_m
        ),
        "phase_difference_degrees": (
            wrapped_phase_difference_degrees(center_response, reference_response) if phase_mask else None
        ),
        **residual_metrics,
        "raw_vector_archive": npz_name,
        "status_policy": "Raw diagnostic remains unaccepted whenever qf_route_status is not QF_SOLVE_ACCEPTED.",
    }
    _atomic_json(output / f"mesh_{mesh_size:02d}_{key}.json", row)
    return row


def run_mesh_study(mesh_size: int, output_dir: str | Path | None = None) -> dict[str, Any]:
    if mesh_size not in {6, 8, 10}:
        raise ValueError("J16 prospective mesh sizes are frozen to 6, 8, and 10 cells per edge")
    output = Path(output_dir) if output_dir is not None else OUTPUT_ROOT / f"mesh_{mesh_size:02d}"
    if output.exists():
        raise FileExistsError(f"refusing to overwrite mesh study output: {output}")
    reference = load_abaqus_nafems_13h_reference()
    contract, contract_sha256 = _validate_contract(mesh_size, reference)
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    signed_reference = copy.deepcopy(reference)
    signed_reference["model"]["pressure_pa"] = -abs(float(signed_reference["model"]["pressure_pa"]))
    (
        model,
        quads,
        dofs,
        reducer,
        stiffness,
        mass,
        damping,
        loads_reduced,
        full_loads,
        beta,
        load_diagnostics,
    ) = _build_mesh_system(reference, mesh_size)
    load_resultant = _load_resultant(model, dofs, full_loads, load_diagnostics)

    modal_values, _modal_vectors = eigsh(reducer.stiffness, M=reducer.mass, k=1, sigma=0.0, which="LM")
    first_eigenvalue = float(modal_values[0])
    if not math.isfinite(first_eigenvalue) or first_eigenvalue <= 0.0:
        raise ValueError(f"nonpositive or nonfinite first generalized eigenvalue: {first_eigenvalue}")
    first_mode_hz = math.sqrt(first_eigenvalue) / (2.0 * math.pi)
    reference_u, _reference_s = _navier_plate_response(np.asarray(FREQUENCIES_HZ), signed_reference)
    reference_band_peak = float(np.max(np.abs(reference_u[: len(DENSE_FREQUENCIES_HZ)])))
    reference_phase_mask = np.abs(reference_u) >= 0.05 * reference_band_peak
    center_node = _center_node(model.nodes)
    center_index = dofs.index(center_node, "UZ")
    rows: list[dict[str, Any]] = []
    expanded_states: list[np.ndarray] = []
    raw_solve_seconds = 0.0

    for index, frequency in enumerate(FREQUENCIES_HZ):
        frequency_started = time.perf_counter()
        omega = 2.0 * math.pi * frequency
        impedance = (
            stiffness.astype(complex)
            + (1j * omega) * damping
            - (omega**2) * mass
        ).tocsr()
        solve_started = time.perf_counter()
        reduced_response = np.asarray(spsolve(impedance, loads_reduced), dtype=complex)
        raw_solve_seconds += time.perf_counter() - solve_started
        if reduced_response.ndim != 1 or not np.all(np.isfinite(reduced_response)):
            raise ValueError(f"raw spsolve returned a malformed response at {frequency:.9f} Hz")
        full_response = reducer.expand_complex_state(
            reduced_response,
            full_loads,
            stiffness_factor=1.0 + 1j * omega * beta,
        )
        product = impedance @ reduced_response
        residual = product - loads_reduced
        relative = float(np.linalg.norm(residual) / max(np.linalg.norm(loads_reduced), np.linalg.norm(product)))
        matrix_inf = float(np.linalg.norm(impedance, ord=np.inf))
        solution_inf = float(np.max(np.abs(reduced_response), initial=0.0))
        rhs_inf = float(np.max(np.abs(loads_reduced), initial=0.0))
        denominator = matrix_inf * solution_inf + rhs_inf
        backward = float(np.max(np.abs(residual), initial=0.0) / denominator) if denominator else math.inf
        center_response = complex(full_response[center_index])
        residual_metrics = {
            "raw_reduced_residual_l2": float(np.linalg.norm(residual)),
            "raw_reduced_relative_residual_l2": relative,
            "raw_reduced_backward_error_eta_inf": backward,
            "raw_sparse_solve_elapsed_seconds": float(time.perf_counter() - solve_started),
            "pre_route_elapsed_seconds": float(time.perf_counter() - frequency_started),
        }
        # Persist the raw diagnostic before the QF route so an interrupted route still
        # leaves the assembled-system response and an explicit pending status.
        _frequency_checkpoint(
            output,
            mesh_size,
            frequency,
            "QF_ROUTE_PENDING",
            {"phase": "raw_matrix_solve_checkpointed_before_qf_route"},
            reduced_response,
            full_response,
            residual_metrics,
            complex(reference_u[index]),
            center_response,
            None,
            bool(reference_phase_mask[index]),
            reference_band_peak,
        )
        qf_status, qf_details, qf_full_response = _route_solve(reference, mesh_size, frequency)
        qf_center_response = complex(qf_full_response[center_index]) if qf_full_response is not None else None
        completed_metrics = {
            **residual_metrics,
            "qf_route_elapsed_seconds": float(qf_details.get("elapsed_seconds", 0.0)),
            "frequency_total_elapsed_seconds": float(time.perf_counter() - frequency_started),
        }
        row = _frequency_checkpoint(
            output,
            mesh_size,
            frequency,
            qf_status,
            qf_details,
            reduced_response,
            full_response,
            completed_metrics,
            complex(reference_u[index]),
            center_response,
            qf_center_response,
            bool(reference_phase_mask[index]),
            reference_band_peak,
        )
        if qf_center_response is not None:
            row["accepted_qf_center_uz_amplitude_mm"] = float(abs(qf_center_response) * 1000.0)
            row["accepted_qf_center_uz_phase_degrees"] = float(np.degrees(np.angle(qf_center_response)))
        rows.append(row)
        expanded_states.append(full_response)

    dense_rows = [row for row in rows if row["frequency_role"] == "shared_dense_grid"]
    dense_amplitudes = np.asarray([row["raw_center_uz_amplitude_mm"] for row in dense_rows], dtype=float)
    dense_frequencies = np.asarray([row["frequency_hz"] for row in dense_rows], dtype=float)
    peak_index = int(np.argmax(dense_amplitudes))
    sampled_peak = {
        "frequency_hz": float(dense_frequencies[peak_index]),
        "amplitude_mm": float(dense_amplitudes[peak_index]),
    }
    quadratic_peak = _quadratic_peak(dense_frequencies, dense_amplitudes, peak_index)
    reference_dense = np.abs(reference_u[: len(DENSE_FREQUENCIES_HZ)])
    reference_sampled_peak = {
        "frequency_hz": float(DENSE_FREQUENCIES_HZ[int(np.argmax(reference_dense))]),
        "amplitude_mm": float(np.max(reference_dense) * 1000.0),
    }
    exact_probe_index = FREQUENCIES_HZ.index(REFERENCE_PEAK_PROBE_HZ)
    peak_state = expanded_states[FREQUENCIES_HZ.index(sampled_peak["frequency_hz"])]
    summary = {
        "schema": "qfsolver-j16-mitc4-mesh-study-v1",
        "classification": "PROSPECTIVE_EXPLORATORY_MULTI_MESH_HARMONIC_STUDY",
        "contract_id": contract["contract_id"],
        "series_id": f"dev-j16-nafems13h-mesh-{mesh_size:02d}-001",
        "contract_sha256": contract_sha256,
        "source_git": _git_identity(),
        "source_file_sha256": contract["source_sha256"],
        "reference_artifact_sha256": contract["inputs"]["reference_artifact_sha256"],
        "attempt_id": f"J16-NAFEMS13H-MESH-{mesh_size:02d}-001",
        "mesh_size": mesh_size,
        "mesh_shape": [mesh_size, mesh_size],
        "element": "MITC4",
        "nodes": model.node_count,
        "full_dofs": dofs.ndof,
        "free_dofs": int(reducer.free.size),
        "fixed_dofs": int(reducer.fixed.size),
        "geometry_m": reference["model"]["geometry_m"],
        "material": reference["model"]["material"],
        "pressure_pa": reference["model"]["pressure_pa"],
        "rayleigh_damping": reference["model"]["rayleigh_damping"],
        "conditions": "Frozen NAFEMS 13H: UX=UY=RZ=0 globally; UZ=0 on perimeter; RY=0 on top/bottom; RX=0 on left/right.",
        "observable": "Complex center UZ at physical point (5,5,0) m.",
        "assembled_load_resultant": load_resultant,
        "modal_frequency_from_qf_assembled_KM_hz": first_mode_hz,
        "frequency_grid_hz": {
            "dense_start": DENSE_FREQUENCIES_HZ[0],
            "dense_stop": DENSE_FREQUENCIES_HZ[-1],
            "dense_count": len(DENSE_FREQUENCIES_HZ),
            "dense_spacing": 0.005,
            "additional_probe_hz": REFERENCE_PEAK_PROBE_HZ,
            "total_count": len(FREQUENCIES_HZ),
        },
        "raw_diagnostic_sampled_peak": sampled_peak,
        "raw_diagnostic_local_quadratic_peak_estimate": quadratic_peak,
        "production_residual_guard_threshold": RESIDUAL_LIMIT,
        "production_residual_guard_threshold_source": "frozen J16 contract; unchanged from historical 1e-7",
        "navier_damped_peak_estimate_hz": REFERENCE_PEAK_PROBE_HZ,
        "navier_sampled_peak_on_shared_dense_grid": reference_sampled_peak,
        "raw_at_reference_peak_probe": {
            "frequency_hz": REFERENCE_PEAK_PROBE_HZ,
            "amplitude_mm": rows[exact_probe_index]["raw_center_uz_amplitude_mm"],
            "phase_degrees": rows[exact_probe_index]["raw_center_uz_phase_degrees"],
        },
        "normalization": "Complex UZ error divided by the maximum Navier amplitude on the common 2.25-2.55 Hz dense grid; phase reported only where Navier amplitude >=5% of that maximum.",
        "rows": rows,
        "resources_observed_in_test": {
            "body_elapsed_seconds": float(time.perf_counter() - started),
            "raw_sparse_solve_seconds_sum": raw_solve_seconds,
        },
        "limitations": [
            "SciPy raw vectors are not accepted QF route results when the route status is rejected.",
            "Navier reference is thin Kirchhoff-Love; MITC4 is Reissner-Mindlin and uses a finite mesh.",
            "A few mesh levels do not establish general spatial convergence.",
        ],
    }
    result_path = output / "site_data.json"
    _atomic_json(result_path, summary)
    csv_path = output / "frequency_response.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "frequency_hz", "frequency_role", "qf_route_status", "raw_center_uz_amplitude_mm",
            "raw_center_uz_phase_degrees", "reference_center_uz_amplitude_mm", "reference_center_uz_phase_degrees",
            "complex_error_normalized_by_reference_band_peak", "phase_difference_degrees", "raw_reduced_relative_residual_l2",
            "raw_reduced_backward_error_eta_inf",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})

    _plot_mesh_setup(model, quads, mesh_size, output / "mesh_setup.png")
    _plot_frequency_response(rows, output / "harmonic_amplitude_phase.png")
    deformed_factor = _plot_peak_deformation(model, quads, peak_state, sampled_peak["frequency_hz"], output / "peak_deformation.png")
    summary["deformation_display_amplification_factor"] = deformed_factor
    _atomic_json(result_path, summary)
    artifacts = []
    for path in sorted(item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"):
        artifacts.append({"path": path.name, "bytes": path.stat().st_size, "sha256_raw": hashlib.sha256(path.read_bytes()).hexdigest()})
    _atomic_json(output / "artifact_manifest.json", {"schema": "qfsolver-j16-mesh-output-manifest-v1", "artifacts": artifacts})
    return summary


def _plot_mesh_setup(model: FiniteElementModel, quads: np.ndarray, mesh_size: int, path: Path) -> None:
    figure, (axis, details) = plt.subplots(
        1, 2, figsize=(10, 7), gridspec_kw={"width_ratios": (1.0, 0.72)}, constrained_layout=True
    )
    for face in quads:
        closed = np.append(face, face[0])
        axis.plot(model.nodes[closed, 0], model.nodes[closed, 1], color="#176b87", linewidth=0.75)
    axis.scatter(model.nodes[:, 0], model.nodes[:, 1], s=8, color="#176b87")
    axis.set_aspect("equal")
    axis.set_xlim(0.0, 10.0)
    axis.set_ylim(0.0, 10.0)
    axis.set_xlabel("x (m)")
    axis.set_ylabel("y (m)")
    axis.set_title(f"MITC4 mesh {mesh_size}×{mesh_size}")
    details.axis("off")
    details.text(
        0.02,
        0.96,
        "NAFEMS 13H harmonic plate\n\n"
        "Plan dimensions: 10 × 10 m\n"
        "Thickness: 0.05 m\n"
        "Uniform pressure: 100 Pa toward −Z\n"
        "Expected resultant: 10 kN toward −Z\n\n"
        "Simply supported edges:\n"
        "• UZ = 0 on the perimeter\n"
        "• tangential rotation = 0 on each edge\n\n"
        "All nodes:\n"
        "• UX = UY = RZ = 0\n\n"
        "Responses are computed per mesh; red status marks in the plots\n"
        "identify points rejected by the QF production route.",
        va="top",
        ha="left",
        fontsize=10,
        linespacing=1.45,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f4f6f8", "edgecolor": "#d0d7de"},
    )
    figure.suptitle("NAFEMS 13H square plate and harmonic loading")
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_frequency_response(rows: list[dict[str, Any]], path: Path) -> None:
    dense = [row for row in rows if row["frequency_role"] == "shared_dense_grid"]
    frequencies = np.asarray([row["frequency_hz"] for row in dense], dtype=float)
    qf_amp = np.asarray([row["raw_center_uz_amplitude_mm"] for row in dense], dtype=float)
    qf_phase = np.asarray([row["raw_center_uz_phase_degrees"] for row in dense], dtype=float)
    ref_amp = np.asarray([row["reference_center_uz_amplitude_mm"] for row in dense], dtype=float)
    ref_phase = np.asarray([row["reference_center_uz_phase_degrees"] for row in dense], dtype=float)
    rejected = np.asarray([row["qf_route_status"] != "QF_SOLVE_ACCEPTED" for row in dense], dtype=bool)
    phase_mask = np.asarray([row["phase_difference_degrees"] is not None for row in dense], dtype=bool)
    figure, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    axes[0].plot(frequencies, qf_amp, color="#b23a48", label="QF-assembled spsolve diagnostics (unaccepted where marked)")
    axes[0].plot(frequencies, ref_amp, "--", color="#176b87", label="Navier Kirchhoff-Love")
    axes[0].scatter(frequencies[rejected], qf_amp[rejected], marker="x", s=16, color="#5f0f40", label="QF route rejected")
    axes[0].set_ylabel("Center |UZ| (mm)")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend(fontsize=8)
    axes[1].plot(frequencies[phase_mask], qf_phase[phase_mask], color="#b23a48", label="QF-assembled diagnostic")
    axes[1].plot(frequencies[phase_mask], ref_phase[phase_mask], "--", color="#176b87", label="Navier reference")
    axes[1].scatter(frequencies[rejected & phase_mask], qf_phase[rejected & phase_mask], marker="x", s=16, color="#5f0f40", label="QF route rejected")
    axes[1].set_ylabel("Phase of UZ (degrees)")
    axes[1].set_xlabel("Frequency (Hz)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    axes[0].set_title("Exploratory frequency response; status retained at every point")
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_peak_deformation(
    model: FiniteElementModel,
    quads: np.ndarray,
    response: np.ndarray,
    frequency_hz: float,
    path: Path,
) -> float:
    dofs = model.dof_manager()
    center = _center_node(model.nodes)
    phase = np.angle(response[dofs.index(center, "UZ")])
    aligned = response * np.exp(-1j * phase)
    uz = np.asarray([aligned[dofs.index(node, "UZ")].real for node in range(model.node_count)])
    maximum = max(float(np.max(np.abs(uz))), 1.0e-30)
    target = 0.1
    factor = target / maximum
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
    axis.set_title(f"Unaccepted QF-assembled diagnostic, {frequency_hz:.4f} Hz; display factor {factor:.3e}")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
    return factor
