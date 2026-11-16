"""Independent, non-FEM post-processing for the J5B MITC4 modal archive.

This module intentionally does not import QF Solver.  It checks archived
candidate data and constructs a continuum Reissner--Mindlin Ritz reference.
The result is diagnostic and cannot change the historical J5B statuses.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import sys
import threading
import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from scripts.j5c_modal_ritz import (
    MODE_ORDERS,
    _build_ritz_sweep,
    _quad_gauss_samples,
    _reference_fields_at,
    _weighted_mac,
    _weighted_subspace_mac_min,
    _write_frequency_figure,
    _write_shape_figure,
)

ROOT = Path(__file__).resolve().parents[1]
J5C_ROOT = ROOT / "research" / "j5c"
INPUT_DIR = J5C_ROOT / "inputs" / "j5b_attempt_0001"
CONTRACT_PATH = J5C_ROOT / "contracts" / "independent_modal_postprocess.json"
EXECUTION_MANIFEST_PATH = J5C_ROOT / "contracts" / "execution_manifest.json"
OUTPUT_DIR = J5C_ROOT / "results" / "diagnostic-2026-11-16" / "postprocess-0001"
EXPECTED_MESH_SIZES = (4, 6, 8, 12, 16)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_archive(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {name: np.array(archive[name], copy=True) for name in archive.files}


def _mac(first: np.ndarray, second: np.ndarray) -> float:
    first = np.asarray(first, dtype=float).reshape(-1)
    second = np.asarray(second, dtype=float).reshape(-1)
    denominator = float(first @ first) * float(second @ second)
    if denominator <= np.finfo(float).tiny:
        raise ValueError("MAC is undefined for a zero vector")
    return float((first @ second) ** 2 / denominator)


def _subspace_mac_min(first: np.ndarray, second: np.ndarray) -> float:
    first_q, _ = np.linalg.qr(np.asarray(first, dtype=float))
    second_q, _ = np.linalg.qr(np.asarray(second, dtype=float))
    singular_values = np.linalg.svd(first_q.T @ second_q, compute_uv=False)
    return float(np.min(singular_values) ** 2)


def _navier_frequencies_hz(model: dict[str, Any]) -> np.ndarray:
    geometry = model["geometry"]
    material = model["material"]
    length = float(geometry["length_m"])
    thickness = float(geometry["thickness_m"])
    young = float(material["young_modulus_pa"])
    poisson = float(material["poisson_ratio"])
    density = float(material["density_kg_m3"])
    rigidity = young * thickness**3 / (12.0 * (1.0 - poisson**2))
    width = float(geometry["width_m"])
    factor = math.pi / 2.0 * math.sqrt(rigidity / (density * thickness))
    return np.asarray([factor * ((m / length) ** 2 + (n / width) ** 2) for m, n in MODE_ORDERS])


def _navier_shape(nodes: np.ndarray, order: tuple[int, int], model: dict[str, Any]) -> np.ndarray:
    length = float(model["geometry"]["length_m"])
    width = float(model["geometry"]["width_m"])
    m, n = order
    x = np.asarray(nodes)[:, 0]
    y = np.asarray(nodes)[:, 1] + 0.5 * width
    return np.sin(m * math.pi * x / length) * np.sin(n * math.pi * y / width)


def _check_mesh(arrays: dict[str, np.ndarray], size: int, model: dict[str, Any]) -> dict[str, Any]:
    nodes = arrays["nodes"]
    quads = arrays["quads"]
    length = float(model["geometry"]["length_m"])
    width = float(model["geometry"]["width_m"])
    checks: dict[str, Any] = {
        "mesh_size": [size, size],
        "node_count_expected": (size + 1) ** 2,
        "node_count_observed": int(nodes.shape[0]),
        "element_count_expected": size * size,
        "element_count_observed": int(quads.shape[0]),
    }
    if nodes.shape != ((size + 1) ** 2, 3) or quads.shape != (size * size, 4):
        raise ValueError(f"mesh {size}x{size}: unexpected node/quad array shape")
    x_levels = np.unique(nodes[:, 0])
    y_levels = np.unique(nodes[:, 1])
    if len(x_levels) != size + 1 or len(y_levels) != size + 1:
        raise ValueError(f"mesh {size}x{size}: coordinates are not a structured grid")
    expected_x = np.linspace(0.0, length, size + 1)
    expected_y = np.linspace(-0.5 * width, 0.5 * width, size + 1)
    grid_error = max(
        float(np.max(np.abs(x_levels - expected_x))),
        float(np.max(np.abs(y_levels - expected_y))),
    )
    z_error = float(np.max(np.abs(nodes[:, 2])))
    coordinates = nodes[quads, :2]
    signed_areas = 0.5 * np.sum(
        coordinates[:, :, 0] * np.roll(coordinates[:, :, 1], -1, axis=1)
        - coordinates[:, :, 1] * np.roll(coordinates[:, :, 0], -1, axis=1),
        axis=1,
    )
    area_error = float(np.max(np.abs(signed_areas - length * width / (size * size))))
    checks.update(
        {
            "grid_coordinate_max_error_m": grid_error,
            "mid_surface_z_max_abs_m": z_error,
            "quad_signed_area_min_m2": float(np.min(signed_areas)),
            "quad_signed_area_max_error_m2": area_error,
            "total_mesh_area_m2": float(np.sum(signed_areas)),
            "structured_geometry_ok": bool(
                grid_error <= 1.0e-12
                and z_error <= 1.0e-12
                and np.all(signed_areas > 0.0)
                and area_error <= 1.0e-12
                and abs(float(np.sum(signed_areas)) - length * width) <= 1.0e-12
            ),
        }
    )
    if not checks["structured_geometry_ok"]:
        raise ValueError(f"mesh {size}x{size}: geometry/orientation check failed")
    return checks


def _mesh_archive_path(size: int) -> Path:
    return INPUT_DIR / "checkpoints" / f"mesh-{size:04d}.npz"


def _validate_inputs(contract: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative, expected in contract["copied_inputs"]["files_sha256"].items():
        path = INPUT_DIR / relative
        if not path.is_file():
            raise FileNotFoundError(f"contract input is missing: {relative}")
        actual = sha256_file(path)
        hashes[relative] = actual
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch for {relative}: {actual} != {expected}")
    return hashes


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _run_campaign_body(output_dir: Path) -> dict[str, Any]:
    contract = _read_json(CONTRACT_PATH)
    execution = _read_json(EXECUTION_MANIFEST_PATH)
    input_hashes = _validate_inputs(contract)
    model = _read_json(INPUT_DIR / "j5b_model_input.json")
    site_data = _read_json(INPUT_DIR / "site_data.json")
    attempt = _read_json(INPUT_DIR / "attempt-0001.json")
    if attempt["campaign_status"] != site_data["campaign_status"]:
        raise ValueError("portable attempt and archived site campaign statuses disagree")
    if attempt["modal_validation_statuses"] != [item["modal_validation_status"] for item in site_data["mesh_results"]]:
        raise ValueError("portable attempt modal statuses differ from archived site data")
    if attempt["modal_validation_reasons"] != [item["modal_validation_reason"] for item in site_data["mesh_results"]]:
        raise ValueError("portable attempt modal reasons differ from archived site data")

    reference_history = {tuple(item["mesh"]): item for item in site_data["mesh_results"]}
    mesh_rows: list[dict[str, Any]] = []
    local_arrays: dict[int, dict[str, np.ndarray]] = {}
    hashes_for_mesh: dict[int, str] = {}
    navier = _navier_frequencies_hz(model)
    for size in EXPECTED_MESH_SIZES:
        archive_path = _mesh_archive_path(size)
        arrays = _load_archive(archive_path)
        local_arrays[size] = arrays
        hashes_for_mesh[size] = sha256_file(archive_path)
        geometry = _check_mesh(arrays, size, model)
        frequencies = np.asarray(arrays["frequencies_hz"], dtype=float)
        eigenvalues = np.asarray(arrays["eigenvalues"], dtype=float)
        if frequencies.shape != (6,) or eigenvalues.shape != (6,) or np.min(eigenvalues) <= 0:
            raise ValueError(f"mesh {size}x{size}: invalid archived modal vector")
        recomputed = np.sqrt(eigenvalues) / (2.0 * math.pi)
        relative = np.abs(recomputed - frequencies) / np.maximum(np.abs(frequencies), np.finfo(float).tiny)
        if float(np.max(relative)) > 1.0e-12:
            raise ValueError(f"mesh {size}x{size}: eigenvalue-frequency relation mismatch")

        translations = np.asarray(arrays["translations"], dtype=float)
        if translations.shape != (arrays["nodes"].shape[0], 3, 6):
            raise ValueError(f"mesh {size}x{size}: unexpected translation array shape")
        full_modes = np.asarray(arrays["modes_full_dof"], dtype=float)
        if full_modes.shape != (arrays["nodes"].shape[0] * 6, 6):
            raise ValueError(f"mesh {size}x{size}: unexpected full modal vector shape")
        translation_export_error = float(np.max(np.abs(full_modes.reshape(-1, 6, 6)[:, :3, :] - translations)))
        if translation_export_error > 1.0e-13:
            raise ValueError(f"mesh {size}x{size}: translations disagree with full modal vectors")
        uz_modes = translations[:, 2, :4]
        boundary = (
            np.isclose(arrays["nodes"][:, 0], 0.0)
            | np.isclose(arrays["nodes"][:, 0], float(model["geometry"]["length_m"]))
            | np.isclose(arrays["nodes"][:, 1], -0.5 * float(model["geometry"]["width_m"]))
            | np.isclose(arrays["nodes"][:, 1], 0.5 * float(model["geometry"]["width_m"]))
        )
        boundary_uz_relative_max = float(
            np.max(np.abs(uz_modes[boundary])) / max(float(np.max(np.abs(uz_modes))), np.finfo(float).tiny)
        )
        if boundary_uz_relative_max > 1.0e-12:
            raise ValueError(f"mesh {size}x{size}: transverse edge constraint is not reflected in modes")
        analytic = np.column_stack([_navier_shape(arrays["nodes"], order, model) for order in MODE_ORDERS])
        nodal_metrics = {
            "first_mode_mac": _mac(uz_modes[:, 0], analytic[:, 0]),
            "repeated_mode_subspace_mac": _subspace_mac_min(uz_modes[:, 1:3], analytic[:, 1:3]),
            "fourth_mode_mac": _mac(uz_modes[:, 3], analytic[:, 3]),
        }
        archived = reference_history[(size, size)]
        site_frequencies = np.asarray(archived["candidate_frequencies_hz"], dtype=float)
        if float(np.max(np.abs(site_frequencies - frequencies))) > 1.0e-10:
            raise ValueError(f"mesh {size}x{size}: frequency vector differs from archived site data")
        archived_errors = np.asarray(archived["relative_frequency_errors"], dtype=float)
        computed_errors = np.abs(frequencies[:4] - navier) / navier
        if float(np.max(np.abs(archived_errors - computed_errors))) > 1.0e-12:
            raise ValueError(f"mesh {size}x{size}: archived Navier frequency errors did not reproduce")
        for name, value in nodal_metrics.items():
            expected = float(archived[name])
            if abs(value - expected) > 1.0e-10:
                raise ValueError(f"mesh {size}x{size}: local {name} did not reproduce J5B")
        mesh_rows.append(
            {
                "mesh_size": size,
                "element_count": int(arrays["quads"].shape[0]),
                "node_count": int(arrays["nodes"].shape[0]),
                "candidate_frequencies_hz": [float(value) for value in frequencies[:4]],
                "navier_frequencies_hz": [float(value) for value in navier],
                "navier_relative_errors": [float(abs(frequencies[i] - navier[i]) / navier[i]) for i in range(4)],
                "recomputed_nodal_mac": nodal_metrics,
                "archived_nodal_mac": {name: float(archived[name]) for name in nodal_metrics},
                "mesh_geometry": geometry,
                "eigenvalue_to_frequency_max_relative_difference": float(np.max(relative)),
                "translation_export_max_abs_difference": translation_export_error,
                "boundary_uz_relative_max": boundary_uz_relative_max,
                "modal_validation_status": archived["modal_validation_status"],
                "modal_validation_reason": archived["modal_validation_reason"],
                "candidate_status": archived["candidate_status"],
            }
        )

    ritz_rows, ritz_reference = _build_ritz_sweep(model, contract)
    modal_comparisons: list[dict[str, Any]] = []
    shape_metrics: dict[str, dict[str, float]] = {}
    for size in EXPECTED_MESH_SIZES:
        arrays = local_arrays[size]
        qf_modes = arrays["translations"][:, 2, :4]
        qf_points, weights, qf_fields = _quad_gauss_samples(arrays, qf_modes, model)
        ref_fields = _reference_fields_at(qf_points, ritz_reference, model)
        shape_metrics[str(size)] = {
            "mode_11_weighted_l2_mac": _weighted_mac(qf_fields[:, 0], ref_fields[:, 0], weights),
            "repeated_12_21_weighted_subspace_mac_min": _weighted_subspace_mac_min(
                qf_fields[:, 1:3], ref_fields[:, 1:3], weights
            ),
            "mode_22_weighted_l2_mac": _weighted_mac(qf_fields[:, 3], ref_fields[:, 3], weights),
        }
        frequencies = mesh_rows[EXPECTED_MESH_SIZES.index(size)]["candidate_frequencies_hz"]
        records = (
            ("mode_11", 0, [1, 1], shape_metrics[str(size)]["mode_11_weighted_l2_mac"]),
            (
                "repeated_12_21_subspace",
                1,
                [1, 2],
                shape_metrics[str(size)]["repeated_12_21_weighted_subspace_mac_min"],
            ),
            ("mode_22", 3, [2, 2], shape_metrics[str(size)]["mode_22_weighted_l2_mac"]),
        )
        for key, mode_index, order_label, mac_value in records:
            modal_comparisons.append(
                {
                    "mesh_size": size,
                    "comparison": key,
                    "reference_mode_order": json.dumps(order_label),
                    "qf_frequency_hz": float(frequencies[mode_index]),
                    "mindlin_ritz_frequency_hz": float(ritz_reference.frequencies_hz[mode_index]),
                    "qf_minus_ritz_relative": float(
                        (frequencies[mode_index] - ritz_reference.frequencies_hz[mode_index])
                        / ritz_reference.frequencies_hz[mode_index]
                    ),
                    "weighted_l2_mac_or_subspace_min": float(mac_value),
                    "metric_definition": (
                        "quadrature-weighted L2 MAC; repeated pair is minimum squared principal-angle cosine"
                    ),
                }
            )

    monotonic_rows = []
    for sequence in ("rotation_degree_refinement", "transverse_harmonic_refinement"):
        rows = [row for row in ritz_rows if row["sequence"] == sequence]
        for previous, current in zip(rows, rows[1:]):
            old = np.asarray(previous["frequencies_hz"])
            new = np.asarray(current["frequencies_hz"])
            monotonic_rows.append(
                {
                    "sequence": sequence,
                    "previous_basis": [previous["transverse_order"], previous["rotation_degree"]],
                    "current_basis": [current["transverse_order"], current["rotation_degree"]],
                    "max_relative_frequency_change": float(
                        np.max(np.abs(new - old) / np.maximum(np.abs(old), np.finfo(float).tiny))
                    ),
                    "max_relative_increase": float(np.max((new - old) / np.maximum(np.abs(old), np.finfo(float).tiny))),
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        output_dir / "modal_comparison.csv",
        modal_comparisons,
        [
            "mesh_size",
            "comparison",
            "reference_mode_order",
            "qf_frequency_hz",
            "mindlin_ritz_frequency_hz",
            "qf_minus_ritz_relative",
            "weighted_l2_mac_or_subspace_min",
            "metric_definition",
        ],
    )
    _write_csv(
        output_dir / "ritz_convergence.csv",
        [
            {
                "sequence": row["sequence"],
                "transverse_order": row["transverse_order"],
                "rotation_degree": row["rotation_degree"],
                "quadrature_order_per_axis": row["quadrature_order_per_axis"],
                "system_dimension": row["system_dimension"],
                "frequency_11_hz": row["frequencies_hz"][0],
                "frequency_12_hz": row["frequencies_hz"][1],
                "frequency_21_hz": row["frequencies_hz"][2],
                "frequency_22_hz": row["frequencies_hz"][3],
                "is_highest_basis_reference": row["is_highest_basis_reference"],
            }
            for row in ritz_rows
        ],
        [
            "sequence",
            "transverse_order",
            "rotation_degree",
            "quadrature_order_per_axis",
            "system_dimension",
            "frequency_11_hz",
            "frequency_12_hz",
            "frequency_21_hz",
            "frequency_22_hz",
            "is_highest_basis_reference",
        ],
    )
    _write_frequency_figure(output_dir / "frequency_comparison.png", mesh_rows, ritz_reference, navier)
    _write_shape_figure(output_dir / "mode_shape_comparison.png", local_arrays[16], ritz_reference, model)

    archived_statuses = [row["modal_validation_status"] for row in mesh_rows]
    archived_reasons = [row["modal_validation_reason"] for row in mesh_rows]
    result_payload: dict[str, Any] = {
        "schema": "qf-j5c-independent-modal-postprocess-result-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "status": "DIAGNOSTIC_ONLY",
        "source_commit": execution["source_commit"],
        "execution_manifest_sha256": sha256_file(EXECUTION_MANIFEST_PATH),
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "input_sha256": input_hashes,
        "archived_attempt": {
            "attempt_id": attempt["attempt_id"],
            "source_commit": attempt["source_commit"],
            "campaign_status": attempt["campaign_status"],
            "j5b_modal_validation_statuses": attempt["modal_validation_statuses"],
            "j5b_modal_validation_reasons": attempt["modal_validation_reasons"],
            "status_preserved": True,
        },
        "independent_checks": {
            "all_input_hashes_match_contract": True,
            "all_meshes_structured_positive_area_and_correct_domain": True,
            "eigenvalue_frequency_relation_max_relative_difference": max(
                row["eigenvalue_to_frequency_max_relative_difference"] for row in mesh_rows
            ),
            "j5b_nodal_mac_reproduced_within_1e_10": True,
            "ritz_nested_basis_frequency_monotonicity_within_1e_8": True,
            "K_matrix_available": False,
            "M_matrix_available": False,
            "eigenpair_residual": "NOT_RECOMPUTED: archived K matrix is unavailable",
            "mass_orthogonality": "NOT_RECOMPUTED: archived M matrix is unavailable",
        },
        "model": {
            "case_id": model["case_id"],
            "geometry": model["geometry"],
            "material": model["material"],
            "boundary_conditions": model["boundary_conditions"],
            "reference_support_interpretation": (
                "soft simply supported: w=0 on all four edges; rotations free, natural moments"
            ),
            "ritz_rotation_basis": "tensor Legendre P0..P20 on the full domain",
            "ritz_transverse_basis": "sin(m*pi*x/a)sin(n*pi*(y+b/2)/b), m,n=1..7",
            "ritz_quadrature_order_per_axis": 48,
            "ritz_highest_system_dimension": ritz_reference.system_dimension,
            "ritz_mass": "rho*h translation plus rho*h^3/12 rotary inertia per independent rotation",
        },
        "reference": {
            "mindlin_ritz_frequencies_hz_first_four": [float(value) for value in ritz_reference.frequencies_hz[:4]],
            "ritz_basis_sweep": ritz_rows,
            "ritz_nested_changes": monotonic_rows,
            "navier_kirchhoff_frequencies_hz": [float(value) for value in navier],
            "scope": (
                "independent continuum Galerkin/Rayleigh-Ritz calculation; a numerical reference estimate, "
                "not a closed-form exact solution or a QF residual check"
            ),
        },
        "mesh_results": mesh_rows,
        "weighted_continuum_shape_comparisons": shape_metrics,
        "limits": [
            "J5B K and M matrices were not archived; QF eigenpair residual and mass orthogonality were not recomputed.",
            "The independent Reissner-Mindlin Ritz sequence is a bounded numerical reference; quadrature order was fixed at 48 and not separately varied.",
            "No published numerical result with verified soft-support conditions was available as an independent tabulated oracle.",
            "The published hard-support plate table is not a direct comparison for J5B soft support.",
            "J5B validation remains INCONCLUSIVE on all five meshes; no diagnostic here promotes that status.",
        ],
    }
    _write_json(output_dir / "independent_check.json", result_payload)
    _write_readme(output_dir / "README.md", result_payload)

    artifact_names = [
        "independent_check.json",
        "modal_comparison.csv",
        "ritz_convergence.csv",
        "frequency_comparison.png",
        "mode_shape_comparison.png",
        "README.md",
    ]
    artifact_manifest = {
        "schema": "qf-j5c-artifact-manifest-v1",
        "classification": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "source_commit": execution["source_commit"],
        "execution_manifest_sha256": sha256_file(EXECUTION_MANIFEST_PATH),
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "input_sha256": input_hashes,
        "artifacts": {
            name: {"sha256": sha256_file(output_dir / name), "bytes": (output_dir / name).stat().st_size}
            for name in artifact_names
        },
    }
    _write_json(output_dir / "artifact_manifest.json", artifact_manifest)
    run_record = {
        "schema": "qf-j5c-sanitized-run-record-v1",
        "attempt_id": "j5c-independent-postprocess-0001",
        "status": "COMPLETED_DIAGNOSTIC_ONLY",
        "source_commit": execution["source_commit"],
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "execution_manifest_sha256": sha256_file(EXECUTION_MANIFEST_PATH),
        "input_sha256": input_hashes,
        "external_solver_calls": 0,
        "fem_calls": 0,
        "candidate_process_count": 1,
        "resource_limits": contract["bounded_run"],
        "measured_resource_note": "Process RSS and elapsed time are recorded by the test/runner log; no OS quota is implied.",
        "historical_j5b_status": attempt["campaign_status"],
        "historical_modal_statuses_preserved": archived_statuses,
        "historical_modal_reasons_preserved": archived_reasons,
        "artifact_manifest_sha256": sha256_file(output_dir / "artifact_manifest.json"),
    }
    _write_json(output_dir / "sanitized_run_record.json", run_record)
    return result_payload


def run_campaign(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Run once while sampling elapsed time, process count, and observed RSS."""
    import psutil
    import scipy

    process = psutil.Process(os.getpid())
    stop = threading.Event()
    observed: dict[str, int] = {"peak_rss_bytes": 0, "peak_process_count": 0}

    def sample_process_tree() -> None:
        while not stop.is_set():
            try:
                processes = [process, *process.children(recursive=True)]
                rss = 0
                for child in processes:
                    try:
                        rss += child.memory_info().rss
                    except psutil.Error:
                        continue
                observed["peak_rss_bytes"] = max(observed["peak_rss_bytes"], rss)
                observed["peak_process_count"] = max(observed["peak_process_count"], len(processes))
            except psutil.Error:
                pass
            stop.wait(0.05)

    observed["peak_rss_bytes"] = process.memory_info().rss
    observed["peak_process_count"] = 1
    available_start = int(psutil.virtual_memory().available)
    total_memory = int(psutil.virtual_memory().total)
    started = time.perf_counter()
    sampler = threading.Thread(target=sample_process_tree, name="j5c-resource-sampler", daemon=True)
    sampler.start()
    try:
        result = _run_campaign_body(output_dir)
    finally:
        stop.set()
        sampler.join(timeout=1.0)
    elapsed = time.perf_counter() - started
    measured = {
        "elapsed_seconds": elapsed,
        "peak_observed_rss_bytes": observed["peak_rss_bytes"],
        "peak_observed_rss_mib": observed["peak_rss_bytes"] / (1024.0 * 1024.0),
        "peak_observed_process_count": observed["peak_process_count"],
        "rss_sampling_interval_seconds": 0.05,
        "available_memory_at_start_bytes": available_start,
        "physical_memory_bytes": total_memory,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "matplotlib": matplotlib.__version__,
        "psutil": psutil.__version__,
        "qf_solver_imported": False,
        "external_solver_calls": 0,
        "fem_calls": 0,
        "budget_targets": _read_json(CONTRACT_PATH)["bounded_run"],
        "case_target_seconds_met": elapsed <= 120.0,
        "case_target_rss_mib_met": observed["peak_rss_bytes"] <= 1024 * 1024 * 1024,
    }
    result["measured_resources"] = measured
    result_path = output_dir / "independent_check.json"
    saved_result = _read_json(result_path)
    saved_result["measured_resources"] = measured
    _write_json(result_path, saved_result)

    manifest_path = output_dir / "artifact_manifest.json"
    manifest = _read_json(manifest_path)
    for name in manifest["artifacts"]:
        artifact_path = output_dir / name
        manifest["artifacts"][name] = {
            "sha256": sha256_file(artifact_path),
            "bytes": artifact_path.stat().st_size,
        }
    _write_json(manifest_path, manifest)
    record_path = output_dir / "sanitized_run_record.json"
    record = _read_json(record_path)
    record["measured_resources"] = measured
    record["artifact_manifest_sha256"] = sha256_file(manifest_path)
    _write_json(record_path, record)
    return result


def _write_readme(path: Path, result: dict[str, Any]) -> None:
    reference = result["reference"]["mindlin_ritz_frequencies_hz_first_four"]
    mesh_table = "\n".join(
        "| {n}×{n} | {freqs} | {errors} | {status} / {reason} |".format(
            n=row["mesh_size"],
            freqs=", ".join(f"{value:.5f}" for value in row["candidate_frequencies_hz"]),
            errors=", ".join(f"{100.0 * value:.3f}%" for value in row["navier_relative_errors"]),
            status=row["modal_validation_status"],
            reason=row["modal_validation_reason"],
        )
        for row in result["mesh_results"]
    )
    text = f"""# J5C — independent modal post-processing

Status: **DIAGNOSTIC_ONLY**. This post-processing does not change the J5B
campaign or any modal validation verdict.

## Provenance

The inputs are byte-exact copies from J5B attempt `{result["archived_attempt"]["attempt_id"]}`
at source commit `{result["archived_attempt"]["source_commit"]}`. Hashes are recorded
in `independent_check.json` and `artifact_manifest.json`. The J5B campaign status
remains `{result["archived_attempt"]["campaign_status"]}`; all five modal candidates
remain `INCONCLUSIVE` with their archived reasons.

## Independent checks

- Recomputed `sqrt(eigenvalue)/(2π)` against the five archived frequency/vector
  checkpoints.
- Checked the structured square meshes, positive CCW quad areas, mid-surface,
  and total represented area.
- Reproduced the J5B **unweighted nodal UZ MAC** and repeated-pair subspace MAC.
- Compared QF UZ interpolated bilinearly inside each element to independent
  Reissner–Mindlin soft-support continuum Ritz modes using an area-weighted L2
  MAC. The repeated pair is compared by the minimum squared principal-angle
  cosine in that weighted space. This is not a mass MAC.
- Evaluated the Kirchhoff/Navier formula independently and built a separate
  soft-support Reissner–Mindlin Galerkin/Rayleigh–Ritz frequency sequence.

The first four frequencies from the largest Ritz basis are `{", ".join(f"{v:.6f}" for v in reference)} Hz`.
The basis uses `w=0` on all edges and free rotations (natural moment conditions),
translation mass `rho*h`, and rotary inertia `rho*h^3/12`. Rotation polynomials
and transverse sine harmonics were expanded in nested spaces; the maximum
problem dimension was {result["model"]["ritz_highest_system_dimension"]} at a fixed
48-point Gauss rule per axis. This is a numerical reference estimate, not an
exact closed-form result. No formal acceptance threshold was set.

## Archived J5B candidates

| Mesh | QF candidate frequencies (11,12,21,22), Hz | Relative errors to thin Kirchhoff/Navier | Historical status / reason |
|---:|---|---|---|
{mesh_table}

`modal_comparison.csv` adds differences to the Mindlin Ritz frequencies and
quadrature-weighted mode-shape metrics. `ritz_convergence.csv` contains the
predeclared basis sweeps. The PNG files are normalized comparison figures;
mode amplitudes are not physical forced-response displacements.

## Limits

The archived payload does not contain the assembled stiffness or mass matrix.
Therefore this work did **not** recompute eigenpair residuals or mass
orthogonality. The literature table found during J5C uses hard simple-support
conditions; it is context only, because J5B uses soft support. The Ritz
quadrature order was fixed and not separately converged. The study does not
qualify the MITC4 modal route or the solver as a whole.

## Reproduction

From the J5C clean worktree, run the single predeclared node:

```powershell
python -m pytest tests/unit/test_j5c_modal_postprocess.py::test_j5c_archive_postprocess_and_ritz_reference -q
```

The test writes the artifacts listed in `artifact_manifest.json` below
`research/j5c/results/diagnostic-2026-11-16/postprocess-0001/`. Input hashes,
contract and source commit are frozen in `research/j5c/contracts/`.
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    result = run_campaign()
    print(json.dumps({"status": result["status"], "output_dir": str(OUTPUT_DIR)}, indent=2))
