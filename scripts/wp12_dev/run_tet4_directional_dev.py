"""Run the bounded H3/W1/W2 TET4 flexion development study.

This harness is intentionally separate from the formal local V&V runner. It
uses only the frozen ``solveur.large`` source API and never changes the
scientific checkout. Outputs are written to a new, caller-selected directory;
existing destinations are refused.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CASES: dict[str, tuple[int, int, int]] = {
    "H3": (8, 4, 4),
    "W1": (16, 4, 4),
    "W2": (8, 8, 8),
}
THREAD_VARIABLES = (
    "BLIS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
BEAM_REFERENCE_M = -1.4397142857142855e-7
TIMEOUT_SECONDS = 300
EXPECTED_SCIENCE_COMMIT = "00428adf38e9397340ac136f6f503a268eb671da"
EXPECTED_SCIENCE_TREE = "df4ec667bf746b042c900fad1f86bf542e1a437b"
EXPECTED_ENVIRONMENT = {
    "python": "3.13.17",
    "numpy": "2.2.6",
    "scipy": "1.15.2",
    "h5py": "3.14.0",
    "threadpoolctl": "3.6.0",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_identity(path: Path) -> dict[str, str]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()

    status = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "status": "CLEAN" if not status else "DIRTY",
    }


def _peak_working_set() -> dict[str, int | str]:
    """Observe this process's peak working set on Windows; not a hard limit."""
    if os.name != "nt":
        return {"status": "NOT_AVAILABLE", "peak_working_set_bytes": "NOT_MEASURED"}

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ProcessMemoryCounters),
            ctypes.c_ulong,
        ]
        psapi.GetProcessMemoryInfo.restype = ctypes.c_int
        ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
        if not ok:
            return {"status": "QUERY_FAILED", "peak_working_set_bytes": "NOT_MEASURED"}
    except (AttributeError, OSError):
        return {"status": "QUERY_FAILED", "peak_working_set_bytes": "NOT_MEASURED"}
    return {
        "status": "OBSERVED_PEAK_WORKING_SET",
        "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
    }


def _run_case(case_id: str, output_dir: Path) -> dict[str, Any]:
    import numpy as np
    import scipy
    import solveur
    from threadpoolctl import threadpool_info

    from solveur.large.assembler import ChunkedScipyAssembler, assemble_loads, fixed_dof_indices
    from solveur.large.audit import inspect_large_model
    from solveur.large.generator import generate_tet4_cantilever_block
    from solveur.large.matrix_free import solve_structured_matrix_free

    if case_id not in CASES:
        raise ValueError(f"Unknown fixed case ID: {case_id}")
    source_root = Path.cwd().resolve()
    identity = _git_identity(source_root)
    if identity != {
        "commit": EXPECTED_SCIENCE_COMMIT,
        "tree": EXPECTED_SCIENCE_TREE,
        "status": "CLEAN",
    }:
        raise RuntimeError(f"Frozen scientific checkout identity mismatch: {identity}")
    expected_source = (source_root / "src" / "solveur" / "__init__.py").resolve()
    if Path(solveur.__file__).resolve() != expected_source:
        raise RuntimeError(f"solveur import origin mismatch: {solveur.__file__}")
    observed_versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "h5py": importlib.metadata.version("h5py"),
        "threadpoolctl": importlib.metadata.version("threadpoolctl"),
    }
    if observed_versions != EXPECTED_ENVIRONMENT:
        raise RuntimeError(f"Numerical environment profile mismatch: {observed_versions}")
    if any(os.environ.get(name) != "1" for name in THREAD_VARIABLES):
        raise RuntimeError("All six BLAS/OpenMP thread variables must be fixed to one")
    observed_native_threads = threadpool_info()
    if any(int(item.get("num_threads", 1)) != 1 for item in observed_native_threads):
        raise RuntimeError(f"A loaded native numerical library is not single-threaded: {observed_native_threads}")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite evidence destination: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)

    nx, ny, nz = CASES[case_id]
    model_path = output_dir / "model.h5"
    start = time.perf_counter()
    generate_tet4_cantilever_block(
        model_path,
        nx=nx,
        ny=ny,
        nz=nz,
        length=4.0,
        height=0.4,
        depth=0.4,
        young=70.0e9,
        poisson=0.3,
        density=7800.0,
        total_load=-1.0,
        decomposition="six",
        load_distribution="tributary",
    )

    from solveur.large.io import load_large_model

    model = load_large_model(model_path)
    expected_elements = 6 * nx * ny * nz
    expected_nodes = (nx + 1) * (ny + 1) * (nz + 1)
    if (model.element_count, model.node_count, model.ndof) != (
        expected_elements,
        expected_nodes,
        3 * expected_nodes,
    ):
        raise RuntimeError("Generated model identity does not match the frozen case dimensions")

    solved = solve_structured_matrix_free(model, chunk_size=8192, rtol=1.0e-8, atol=0.0, maxiter=10_000)
    displacement = np.asarray(solved.displacement, dtype=float)
    np.save(output_dir / "displacement.npy", displacement, allow_pickle=False)

    assembly_start = time.perf_counter()
    assembled = ChunkedScipyAssembler(chunk_size=8192).assemble(model)
    assembly_wall_seconds = time.perf_counter() - assembly_start
    stiffness = assembled.stiffness
    loads = assemble_loads(model)
    fixed = fixed_dof_indices(model)
    all_dofs = np.arange(model.ndof, dtype=np.int64)
    free = np.setdiff1d(all_dofs, fixed, assume_unique=True)

    internal = np.asarray(stiffness @ displacement, dtype=float)
    residual = internal - loads
    free_residual = residual[free]
    fixed_reaction = np.zeros(model.ndof, dtype=float)
    fixed_reaction[fixed] = residual[fixed]
    nodal_load = loads.reshape((-1, 3))
    nodal_reaction = fixed_reaction.reshape((-1, 3))
    coordinates = np.asarray(model.nodes, dtype=float)
    tip_nodes = np.flatnonzero(np.isclose(coordinates[:, 0], 4.0, rtol=0.0, atol=1.0e-12))
    tip_displacements = displacement.reshape((-1, 3))[tip_nodes]
    mean_tip_uz = float(np.mean(tip_displacements[:, 2]))
    total_load_z = float(np.sum(nodal_load[:, 2]))
    load_conjugate_displacement = float(np.dot(loads, displacement) / total_load_z)

    displacement_vectors = displacement.reshape((-1, 3))
    nodal_displacement_norms = np.linalg.norm(displacement_vectors, axis=1)
    max_node = int(np.argmax(nodal_displacement_norms))
    max_displacement = float(nodal_displacement_norms[max_node])
    applied_moments = np.sum(np.cross(coordinates, nodal_load), axis=0)
    support_moments = np.sum(np.cross(coordinates, nodal_reaction), axis=0)
    force_sum = np.sum(nodal_load, axis=0)
    reaction_sum = np.sum(nodal_reaction, axis=0)
    energy = float(0.5 * np.dot(displacement, internal))
    external_work = float(np.dot(displacement, loads))
    exact_discrete_energy_residual = float(2.0 * energy - external_work)
    free_residual_norm = float(np.linalg.norm(free_residual))
    free_load_norm = float(np.linalg.norm(loads[free]))
    relative_residual = free_residual_norm / max(free_load_norm, 1.0)
    audit = inspect_large_model(model, stiffness=stiffness, loads=loads, displacement=displacement)
    quality = audit.details["tet4_quality"]
    tet_coordinates = coordinates[model.tet4]
    volume = float(
        np.sum(
            np.einsum(
                "ij,ij->i",
                np.cross(tet_coordinates[:, 1] - tet_coordinates[:, 0], tet_coordinates[:, 2] - tet_coordinates[:, 0]),
                tet_coordinates[:, 3] - tet_coordinates[:, 0],
            )
            / 6.0
        )
    )
    beam_error = abs(mean_tip_uz - BEAM_REFERENCE_M) / abs(BEAM_REFERENCE_M)

    import h5py

    report = {
        "schema": "qf-wp12-w-directional-dev-result-v1",
        "status": "DEVELOPMENT_OBSERVATION_ONLY",
        "case_id": case_id,
        "dimensions_cells": [nx, ny, nz],
        "model": {
            "nodes": model.node_count,
            "elements": model.element_count,
            "total_dofs": model.ndof,
            "fixed_dofs": int(fixed.size),
            "free_dofs": int(free.size),
            "fixed_face": "x=0; UX, UY, UZ fixed",
            "loaded_face": "x=L=4 m; tributary nodal weights; global FZ",
            "volume_m3": volume,
            "element_quality": quality,
            "mesh_audit_status": audit.status,
            "mesh_audit_warnings": list(audit.warnings),
        },
        "material": {"model": "isotropic_3d", "young_pa": 70.0e9, "poisson": 0.3, "density_kg_m3": 7800.0},
        "load": {
            "total_force_n": [float(v) for v in force_sum],
            "loaded_face_node_count": int(tip_nodes.size),
            "moment_about_origin_nm": [float(v) for v in applied_moments],
            "sum_input_nodal_values_z_n": total_load_z,
        },
        "solution": {
            "mean_loaded_face_uz_m": mean_tip_uz,
            "load_conjugate_displacement_m": load_conjugate_displacement,
            "max_nodal_translation_m": max_displacement,
            "max_nodal_translation_node_id_zero_based": max_node,
            "max_nodal_translation_node_xyz_m": [float(v) for v in coordinates[max_node]],
            "max_nodal_translation_components_m": [float(v) for v in displacement_vectors[max_node]],
            "matrix_free_solver": dict(solved.solver_info),
            "support_reaction_force_sum_n": [float(v) for v in reaction_sum],
            "support_reaction_moment_about_origin_nm": [float(v) for v in support_moments],
            "force_equilibrium_residual_n": [float(v) for v in force_sum + reaction_sum],
            "moment_equilibrium_residual_nm": [float(v) for v in applied_moments + support_moments],
            "free_residual_norm_n": free_residual_norm,
            "free_residual_normalization": "||r_free||_2 / max(||F_free||_2, 1.0 N); the 1.0 is a numerical SI-value floor and is unit-system dependent",
            "free_residual_normalized": relative_residual,
            "assembled_route_free_relative_residual": float(audit.details["solution"]["free_relative_residual"]),
            "strain_energy_j": energy,
            "external_work_j": external_work,
            "twice_energy_minus_work_j": exact_discrete_energy_residual,
            "two_energy_over_work": float(2.0 * energy / external_work) if external_work else None,
        },
        "diagnostic_reference": {
            "type": "1D Euler-Bernoulli plus Timoshenko cantilever formula; diagnostic, not a 3D oracle",
            "tip_uz_m": BEAM_REFERENCE_M,
            "relative_difference": float(beam_error),
        },
        "performance_observations": {
            "matrix_free_solve_seconds": float(solved.solve_time_seconds),
            "sparse_assembly_wall_seconds": assembly_wall_seconds,
            "sparse_assembly_phase_seconds": assembled.diagnostics["assembly_phase_seconds"],
            "sparse_matrix_nnz": int(stiffness.nnz),
            "sparse_matrix_storage_bytes": int(assembled.diagnostics["sparse_memory_bytes"]),
            "matrix_free_operator_storage_bytes": int(solved.operator_memory_bytes),
            "peak_working_set": _peak_working_set(),
            "case_wall_seconds": float(time.perf_counter() - start),
            "resource_note": "Local observed usage only; no hard CPU/RAM/disk quota or sandbox.",
        },
        "environment": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": sys.version,
            "platform": platform.platform(),
            "solveur_file": str(Path(solveur.__file__).resolve()),
            "solveur_version": solveur.__version__,
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "h5py_version": h5py.__version__,
            "thread_environment": {name: os.environ.get(name) for name in THREAD_VARIABLES},
            "native_libraries": observed_native_threads,
        },
        "files": {
            "model_h5_sha256": _sha256(model_path),
            "displacement_npy_sha256": _sha256(output_dir / "displacement.npy"),
        },
        "limitations": [
            "One development solve per mesh; this is not a formal qualification run.",
            "The 1D beam formula is only a diagnostic; no independent 3D reference is included.",
            "W2 doubles both transverse directions and does not isolate their separate effects.",
            "Sparse assembly is used for post-solve residual, reaction and energy recovery; no second linear solve is performed.",
            "The matrix-free and sparse paths share the frozen TET4 constitutive/element formulation and are not independent physical validations.",
        ],
    }
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _campaign(output_root: Path) -> int:
    if output_root.exists():
        raise FileExistsError(f"Refusing to overwrite campaign destination: {output_root}")
    output_root.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve()
    env = os.environ.copy()
    source_root = Path.cwd()
    identity = _git_identity(source_root)
    if identity != {
        "commit": EXPECTED_SCIENCE_COMMIT,
        "tree": EXPECTED_SCIENCE_TREE,
        "status": "CLEAN",
    }:
        raise RuntimeError(f"Frozen scientific checkout identity mismatch: {identity}")
    env["PYTHONPATH"] = str(source_root / "src")
    for name in THREAD_VARIABLES:
        env[name] = "1"

    runs: list[dict[str, Any]] = []
    for case_id in ("H3", "W1", "W2"):
        case_dir = output_root / case_id
        argv = [sys.executable, str(script), "--case", case_id, "--output-dir", str(case_dir)]
        started = datetime.now(timezone.utc).isoformat()
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                argv,
                cwd=source_root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            return_code = completed.returncode
            status = "PROCESS_EXIT_ZERO" if return_code == 0 else "PROCESS_EXIT_NONZERO"
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            )
            stderr = (
                exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            )
            return_code = None
            status = "TIMEOUT"
        duration = time.perf_counter() - start
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "stdout.log").write_text(stdout, encoding="utf-8")
        (case_dir / "stderr.log").write_text(stderr, encoding="utf-8")
        receipt = {
            "case_id": case_id,
            "status": status,
            "started_at_utc": started,
            "duration_seconds": duration,
            "timeout_seconds": TIMEOUT_SECONDS,
            "argv": argv,
            "cwd": str(source_root),
            "exit_code": return_code,
            "stdout_sha256": _sha256(case_dir / "stdout.log"),
            "stderr_sha256": _sha256(case_dir / "stderr.log"),
            "result_json_sha256": _sha256(case_dir / "result.json") if (case_dir / "result.json").is_file() else None,
            "model_h5_sha256": _sha256(case_dir / "model.h5") if (case_dir / "model.h5").is_file() else None,
            "displacement_npy_sha256": _sha256(case_dir / "displacement.npy")
            if (case_dir / "displacement.npy").is_file()
            else None,
        }
        (case_dir / "process_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        runs.append(receipt)
        print(json.dumps(receipt, sort_keys=True))
        if status != "PROCESS_EXIT_ZERO":
            break
    summary = {
        "schema": "qf-wp12-w-directional-dev-campaign-v1",
        "status": "DEVELOPMENT_ONLY",
        "campaign_started_at_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_git": _git_identity(source_root),
        "harness_path": str(script),
        "harness_sha256": _sha256(script),
        "output_root": str(output_root),
        "thread_environment": {name: env.get(name) for name in THREAD_VARIABLES},
        "maximum_attempts_per_case": 1,
        "sequential": True,
        "stop_on_first_nonzero_or_timeout": True,
        "runs": runs,
    }
    (output_root / "campaign_receipt.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0 if len(runs) == len(CASES) and all(run["status"] == "PROCESS_EXIT_ZERO" for run in runs) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--campaign", action="store_true")
    group.add_argument("--case", choices=tuple(CASES))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.campaign:
        if args.output_root is None or args.output_dir is not None:
            parser.error("--campaign requires --output-root and forbids --output-dir")
        return _campaign(args.output_root.resolve())
    if args.output_dir is None or args.output_root is not None:
        parser.error("--case requires --output-dir and forbids --output-root")
    _run_case(args.case, args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
