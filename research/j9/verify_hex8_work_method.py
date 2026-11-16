"""Post-process the archived J9 HEX8-SRI affine-patch matrices.

This script does not assemble elements or run a new FEM solve. It solves the
same nine-DOF reduced systems with NumPy and SciPy, then compares stored and
reconstructed work/energy observables.
"""

from __future__ import annotations

import hashlib
import json
import platform
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil
import scipy
from scipy.linalg import cho_factor, cho_solve
from threadpoolctl import threadpool_info, threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j9/hex8_work_method_postprocess_attempt_03_contract.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
RESULT_DIR = ROOT / "research/j9/results/diagnostic-2026-11-16/hex8_constant_domain"
STATE_PATH = RESULT_DIR / "hex8_distortion_states.npz"
RESULT_PATH = RESULT_DIR / "result.json"
OUTPUT_PATH = RESULT_DIR / "work_method_postprocess.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_norm(numerator: np.ndarray, denominator: np.ndarray) -> float:
    return float(
        np.linalg.norm(numerator - denominator)
        / max(float(np.linalg.norm(denominator)), np.finfo(float).tiny)
    )


def main() -> None:
    source = CONTRACT["source"]
    required_source_fields = {
        "source_head_for_archived_fem_data",
        "postprocessor_sha256",
        "inputs",
    }
    missing_source_fields = required_source_fields - source.keys()
    if missing_source_fields:
        raise RuntimeError(f"contract source fields are missing: {sorted(missing_source_fields)}")
    actual_script_sha = sha256(Path(__file__))
    if actual_script_sha != source["postprocessor_sha256"]:
        raise RuntimeError(
            f"postprocessor SHA-256 differs from contract: {actual_script_sha}"
        )

    expected = {item["path"]: item["sha256"] for item in source["inputs"]}
    for path in (STATE_PATH, RESULT_PATH):
        rel = path.relative_to(ROOT).as_posix()
        actual = sha256(path)
        if actual != expected[rel]:
            raise RuntimeError(f"input SHA-256 mismatch for {rel}: {actual}")

    source_result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    archive = np.load(STATE_PATH, allow_pickle=False)
    coordinates = archive["coordinates_m"]
    stiffnesses = archive["stiffness_n_per_m"]
    displacements = archive["displacement_m"]
    archived_reactions = archive["reactions_n"]
    ijk = archive["ijk"]
    divisions = np.asarray(source_result["model"]["mesh_divisions"], dtype=int)
    if divisions.tolist() != CONTRACT["model_scope"]["mesh_divisions"]:
        raise RuntimeError("mesh dimensions differ from the frozen retry contract")
    interior_nodes = np.all((ijk > 0) & (ijk < divisions), axis=1)
    free_dofs = np.repeat(interior_nodes, 3)
    boundary_dofs = ~free_dofs
    if int(np.count_nonzero(free_dofs)) != 9:
        raise RuntimeError("the archived patch no longer has the contracted nine free DOFs")

    process = psutil.Process()
    peak_rss = [process.memory_info().rss]
    sampler_stop = threading.Event()

    def sample_rss() -> None:
        while not sampler_stop.wait(0.01):
            try:
                peak_rss[0] = max(peak_rss[0], process.memory_info().rss)
            except psutil.Error:
                return

    started = time.perf_counter()
    sampler = threading.Thread(target=sample_rss, name="rss-sampler", daemon=True)
    sampler.start()
    levels: list[dict[str, object]] = []

    try:
        with threadpool_limits(limits=1):
            for level_index, alpha in enumerate(archive["distortion_amplitudes"]):
                stiffness = np.asarray(stiffnesses[level_index], dtype=float)
                archived_u = np.asarray(displacements[level_index], dtype=float).reshape(-1)
                archived_r = np.asarray(archived_reactions[level_index], dtype=float).reshape(-1)
                if stiffness.shape != (135, 135):
                    raise RuntimeError(f"unexpected stiffness shape: {stiffness.shape}")
                if not np.all(np.isfinite(stiffness)):
                    raise RuntimeError("stored stiffness contains non-finite values")
                symmetry_indicator = float(
                    np.linalg.norm(stiffness - stiffness.T, ord=np.inf)
                    / max(np.linalg.norm(stiffness, ord=np.inf), np.finfo(float).tiny)
                )
                if symmetry_indicator > 100.0 * np.finfo(float).eps:
                    raise RuntimeError(
                        f"stored stiffness symmetry indicator exceeds contract: {symmetry_indicator}"
                    )
                kff = stiffness[np.ix_(free_dofs, free_dofs)]
                kfc = stiffness[np.ix_(free_dofs, boundary_dofs)]
                uc = archived_u[boundary_dofs]
                rhs = -(kfc @ uc)

                numpy_uf = np.linalg.solve(kff, rhs)
                factor = cho_factor(kff, lower=True, check_finite=True)
                scipy_uf = cho_solve(factor, rhs, check_finite=True)

                methods = []
                full_states = []
                for method, uf in (("numpy.linalg.solve", numpy_uf), ("scipy.linalg.cho_solve", scipy_uf)):
                    full_u = archived_u.copy()
                    full_u[free_dofs] = uf
                    full_force = stiffness @ full_u
                    residual = kff @ uf - rhs
                    energy = float(0.5 * full_u @ (stiffness @ full_u))
                    work = float(0.5 * uc @ full_force[boundary_dofs])
                    methods.append({
                        "method": method,
                        "free_residual_norm_n": float(np.linalg.norm(residual)),
                        "free_residual_relative_to_rhs": float(
                            np.linalg.norm(residual)
                            / max(float(np.linalg.norm(rhs)), np.finfo(float).tiny)
                        ),
                        "free_displacement_relative_difference_from_archived": relative_norm(
                            uf, archived_u[free_dofs]
                        ),
                        "energy_j": energy,
                        "boundary_control_work_j": work,
                        "energy_work_relative_difference": abs(energy - work)
                        / max(abs(energy), abs(work), np.finfo(float).tiny),
                        "energy_relative_difference_from_continuum_reference": (
                            energy - 0.1
                        ) / 0.1,
                        "max_reaction_difference_from_archived_n": float(
                            np.max(np.abs(full_force - archived_r))
                        ),
                    })
                    full_states.append(uf)

                original_level = source_result["levels"][level_index]
                levels.append({
                    "distortion_amplitude_fraction_of_height": float(alpha),
                    "interior_free_dof_count": int(np.count_nonzero(free_dofs)),
                    "archived_condition_2_estimate": original_level[
                        "condition_2_free_stiffness_estimate"
                    ],
                    "relative_stiffness_symmetry_indicator": symmetry_indicator,
                    "numpy_vs_scipy_relative_solution_difference": relative_norm(
                        full_states[0], full_states[1]
                    ),
                    "methods": methods,
                })
    finally:
        sampler_stop.set()
        sampler.join(timeout=1.0)
        peak_rss[0] = max(peak_rss[0], process.memory_info().rss)

    elapsed = time.perf_counter() - started
    payload = {
        "schema": "qfsolver.j9.hex8-work-method-postprocess-result.v1",
        "execution_id": CONTRACT["execution_id"],
        "classification": "DEVELOPMENT_EXPLORATORY_POSTPROCESS_NOT_QUALIFICATION",
        "status": "COMPLETED_EXPLORATORY_POSTPROCESS",
        "source_head_for_archived_fem_data": source[
            "source_head_for_archived_fem_data"
        ],
        "contract_sha256": sha256(CONTRACT_PATH),
        "inputs": [
            {"path": item["path"], "sha256": sha256(ROOT / item["path"])}
            for item in CONTRACT["source"]["inputs"]
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "threadpools": threadpool_info(),
        },
        "execution": {
            "wall_time_seconds": elapsed,
            "peak_rss_sampled_bytes": int(peak_rss[0]),
            "process_count": 1,
            "temporary_bytes": 0,
            "archive_bytes": 0,
            "solver_source_modified": False,
        },
        "work_definition": CONTRACT["observables"]["boundary_control_work_j"],
        "interpretation": "Agreement is limited to two direct solves of each same archived 9-DOF system and an energy/work identity for the archived linear displacement ramp; no new FEM solve or general HEX8-SRI qualification is performed.",
        "levels": levels,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "output": OUTPUT_PATH.relative_to(ROOT).as_posix(),
        "wall_time_seconds": elapsed,
        "peak_rss_sampled_bytes": peak_rss[0],
        "levels": len(levels),
    }, indent=2))


if __name__ == "__main__":
    main()
