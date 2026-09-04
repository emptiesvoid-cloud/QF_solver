"""Execute one frozen WP16 one-million-DOF matrix-free qualification run.

The runner records evidence around the existing public large-model generator
and matrix-free solver.  It does not change solver parameters or numerical
formulations; a second invocation reuses the byte-identical HDF5 input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from solveur.large.assembler import ChunkedScipyAssembler, assemble_loads, fixed_dof_indices
from solveur.large.io import load_large_model
from solveur.large.matrix_free import StructuredBlockOperator, solve_structured_matrix_free
from solveur.large.readiness import check_large_readiness
from solveur.large.runtime import collect_runtime_environment
from solveur.large.generator import generate_tet4_block
from solveur.large.memory import process_memory_snapshot
from solveur.large.solver import _solve_scipy


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "qualification" / "0_2_7" / "wp14_execution_contract.json"
EXPECTED_SHA = "15534b87387c3bd73c73971703e22bf275ffc8cc"


def main() -> None:
    args = _parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    source_sha = _git_sha()
    if source_sha != EXPECTED_SHA:
        raise RuntimeError(f"WP16 must run at the qualified source SHA {EXPECTED_SHA}, got {source_sha}.")
    model_path = args.model.resolve()
    if args.subscale:
        record = _run_subscale(output, source_sha)
        path = output / "wp16_subscale_current.json"
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2, sort_keys=True), flush=True)
        return
    if not model_path.exists():
        print("MODEL_GENERATION_START", flush=True)
        _generate_reference_model(model_path, contract)
        print("MODEL_GENERATION_DONE", flush=True)
    record = _run_once(args.run_id, model_path, output, contract, source_sha)
    path = output / f"wp16_{args.run_id}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, sort_keys=True), flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", choices=("run1", "run2"), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subscale", action="store_true")
    return parser.parse_args()


def _generate_reference_model(path: Path, contract: dict[str, Any]) -> None:
    mesh = contract["reference_model"]["mesh"]
    geometry = contract["reference_model"]["geometry_m"]
    material = contract["reference_model"]["material"]
    load = contract["reference_model"]["loading"]
    generate_tet4_block(
        path,
        nx=int(mesh["nx"]),
        ny=int(mesh["ny"]),
        nz=int(mesh["nz"]),
        length=float(geometry["length_x"]),
        height=float(geometry["height_y"]),
        depth=float(geometry["depth_z"]),
        young=float(material["young_pa"]),
        poisson=float(material["poisson"]),
        density=float(material["density_kg_per_m3"]),
        total_load=float(load["total_force_n"]),
        load_component=0,
        load_distribution="uniform",
        decomposition="six",
    )


def _run_once(
    run_id: str,
    model_path: Path,
    output: Path,
    contract: dict[str, Any],
    source_sha: str,
) -> dict[str, Any]:
    solver_contract = contract["solver_contract"]
    mesh_contract = contract["reference_model"]["mesh"]
    expected_dof = int(mesh_contract["true_dof"])
    config = {
        "backend": solver_contract["reference_backend"],
        "solver": solver_contract["reference_solver"],
        "preconditioner": solver_contract["reference_preconditioner"],
        "chunk_size": int(solver_contract["chunk_size"]),
        "rtol": float(solver_contract["rtol"]),
        "atol": float(solver_contract["atol"]),
        "max_iterations": int(solver_contract["max_iterations"]),
        "random_seed": int(solver_contract["random_seed"]),
    }
    config_digest = _digest_json(config)
    input_digest = _sha256_file(model_path)
    preflight = check_large_readiness(
        output,
        target_dofs=1_000_000,
        nx=69,
        ny=69,
        nz=69,
        solver_backend="matrix_free",
        chunk_size=config["chunk_size"],
    )
    started = time.perf_counter()
    memory_before = process_memory_snapshot()
    record: dict[str, Any] = {
        "schema_version": 1,
        "case_id": "WP16-TET4-STRUCTURED-BLOCK-1M-001",
        "run_id": run_id,
        "tier": "T2",
        "source_sha": source_sha,
        "contract_sha": contract["source_snapshot"],
        "contract_id": contract["contract_id"],
        "model_generator": contract["reference_model"]["mesh"]["generator"],
        "input_path": "qualification/0_2_7/wp16_runtime/wp16_reference.h5",
        "input_digest_sha256": input_digest,
        "configuration": config,
        "configuration_digest_sha256": config_digest,
        "preflight": preflight,
        "environment": collect_runtime_environment(
            {
                "kind": "WP16_true_1m_qualification",
                "run_id": run_id,
                "source_sha": source_sha,
                "input_digest_sha256": input_digest,
            },
            packages=("numpy", "scipy", "h5py"),
        ),
        "status": "RUNNING",
    }
    _write_partial(output, run_id, record)
    print(f"SOLVE_START {run_id} dof={expected_dof} elements={mesh_contract['element_count']}", flush=True)
    rss_sampler = _PeakRSSSampler()
    rss_sampler.start()
    try:
        model = load_large_model(model_path)
        if model.ndof != expected_dof or model.element_count != int(mesh_contract["element_count"]):
            raise RuntimeError("Loaded model does not match the frozen WP14 topology contract.")
        loads = assemble_loads(model)
        fixed = fixed_dof_indices(model)
        free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
        load_total = float(np.sum(loads.reshape((-1, 3)), axis=0)[0])
        expected_load = float(contract["reference_model"]["loading"]["total_force_n"])
        if not np.isclose(load_total, expected_load, rtol=1.0e-12, atol=0.0):
            raise RuntimeError(f"Reference resultant mismatch: {load_total} != {expected_load}.")
        result = solve_structured_matrix_free(
            model,
            chunk_size=config["chunk_size"],
            rtol=config["rtol"],
            atol=config["atol"],
            maxiter=config["max_iterations"],
        )
        operator = StructuredBlockOperator(model, free=free, chunk_size=config["chunk_size"])
        internal = operator.apply_full(result.displacement)
        residual = internal - loads
        free_residual = float(np.linalg.norm(residual[free]))
        free_load_norm = float(np.linalg.norm(loads[free]))
        reaction = np.zeros_like(residual)
        reaction[fixed] = residual[fixed]
        reaction_resultant = np.sum(reaction.reshape((-1, 3)), axis=0)
        applied_resultant = np.sum(loads.reshape((-1, 3)), axis=0)
        equilibrium = reaction_resultant + applied_resultant
        equilibrium_relative = float(np.linalg.norm(equilibrium) / max(float(np.linalg.norm(loads)), 1.0))
        external_work = float(result.displacement @ loads)
        strain_energy = float(0.5 * result.displacement @ internal)
        energy_relative = abs(2.0 * strain_energy - external_work) / max(abs(external_work), 1.0)
        finite = bool(np.isfinite(result.displacement).all() and np.isfinite(internal).all())
        result_path = output / f"wp16_{run_id}_displacement.npy"
        np.save(result_path, result.displacement, allow_pickle=False)
        record.update(
            {
                "status": "PASS",
                "node_count": int(model.node_count),
                "element_count": int(model.element_count),
                "true_dof": int(model.ndof),
                "fixed_dof": int(fixed.size),
                "free_dof": int(free.size),
                "load_node_count": int(model.load_nodes.size),
                "reference_force_total_n": expected_load,
                "force_total_n": load_total,
                "solver_info": result.solver_info,
                "operator_memory_bytes": int(result.operator_memory_bytes),
                "residual_relative": free_residual / max(free_load_norm, 1.0),
                "equilibrium_relative": equilibrium_relative,
                "strain_energy": strain_energy,
                "external_work": external_work,
                "energy_relative": float(energy_relative),
                "displacement_norm": float(np.linalg.norm(result.displacement)),
                "max_displacement": float(np.max(np.abs(result.displacement))),
                "finite_outputs": finite,
                "output_digest_sha256": _sha256_file(result_path),
                "output_path": result_path.name,
                "spd_probe": _spd_probe(operator, free.size),
            }
        )
    except Exception as exc:
        record.update({"status": "FAIL", "failure_type": type(exc).__name__, "failure_reason": str(exc)})
    record["wall_time_seconds"] = float(time.perf_counter() - started)
    record["peak_rss_bytes"] = rss_sampler.stop()
    record["memory_before"] = memory_before
    record["memory_after"] = process_memory_snapshot()
    record["acceptance"] = _acceptance(record, contract)
    if record["status"] == "PASS" and record["acceptance"]["verdict"] != "PASS":
        record["status"] = "FAIL"
    _write_partial(output, run_id, record)
    print(f"SOLVE_DONE {run_id} status={record['status']}", flush=True)
    return record


def _run_subscale(output: Path, source_sha: str) -> dict[str, Any]:
    """Recheck the frozen WP14 assembled/matrix-free observables."""
    from benchmark_wp15_matrix_free import _model_workspace

    levels: list[dict[str, Any]] = []
    for level in (2, 4, 8, 16):
        with _model_workspace(level) as model:
            loads = assemble_loads(model)
            fixed = fixed_dof_indices(model)
            free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
            operator = StructuredBlockOperator(model, free=free, chunk_size=4096)
            vector = _probe_vector(free.size)
            matrix_free = solve_structured_matrix_free(
                model, chunk_size=4096, rtol=1.0e-8, atol=0.0, maxiter=10000
            )
            assembly = ChunkedScipyAssembler(chunk_size=4096).assemble(model)
            _, assembled = _solve_scipy(
                model,
                preconditioner="jacobi",
                chunk_size=4096,
                params={"method": "cg", "rtol": 1.0e-8, "atol": 0.0, "max_it": 10000},
            )
            mf_action = operator @ vector
            full_probe = np.zeros(model.ndof, dtype=float)
            full_probe[free] = vector
            assembled_action = (assembly.stiffness @ full_probe)[free]
            mf_internal = operator.apply_full(matrix_free.displacement)
            assembled_internal = assembly.stiffness @ assembled
            mf_reaction = (mf_internal - loads)[fixed]
            assembled_reaction = (assembled_internal - loads)[fixed]
            mf_energy = float(0.5 * matrix_free.displacement @ mf_internal)
            assembled_energy = float(0.5 * assembled @ assembled_internal)
            levels.append(
                {
                    "level": level,
                    "true_dof": int(model.ndof),
                    "operator_action_relative_error": _relative_norm(mf_action, assembled_action),
                    "displacement_relative_error": _relative_norm(
                        matrix_free.displacement[free], assembled[free]
                    ),
                    "reaction_relative_error": _relative_norm(mf_reaction, assembled_reaction),
                    "energy_relative_error": abs(mf_energy - assembled_energy)
                    / max(abs(assembled_energy), 1.0),
                    "residual_relative": matrix_free.solver_info["relative_residual"],
                }
            )
    errors = {
        key: max(float(level[key]) for level in levels)
        for key in (
            "operator_action_relative_error",
            "displacement_relative_error",
            "reaction_relative_error",
            "energy_relative_error",
            "residual_relative",
        )
    }
    passed = all(value <= 1.0e-8 for value in errors.values())
    return {
        "schema_version": 1,
        "case_id": "WP16-SUBSCALE-MATRIX-FREE-ASSEMBLED-001",
        "source_sha": source_sha,
        "contract_id": "QF-027-WP14-LARGE-EXECUTION-001",
        "levels": levels,
        "max_errors": errors,
        "tolerance": 1.0e-8,
        "verdict": "PASS" if passed else "FAIL",
        "artifact_classification": "CONTROLLED_PROOF",
    }


def _probe_vector(size: int) -> np.ndarray:
    values = np.arange(size, dtype=float) + 1.0
    return values / max(float(size), 1.0)


def _relative_norm(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), 1.0))


def _spd_probe(operator: StructuredBlockOperator, free_size: int) -> dict[str, Any]:
    first = np.arange(free_size, dtype=float) + 1.0
    first /= max(float(free_size), 1.0)
    second = np.roll(first, 17)
    first_action = operator @ first
    second_action = operator @ second
    symmetry = abs(float(first @ second_action - second @ first_action)) / max(
        float(np.linalg.norm(first_action) * np.linalg.norm(second)), 1.0
    )
    curvature = float(first @ first_action)
    return {
        "symmetric_relative": symmetry,
        "positive_curvature": curvature > 0.0,
        "finite": bool(np.isfinite(symmetry) and np.isfinite(curvature)),
    }


def _acceptance(record: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    limits = contract["acceptance_metrics"]
    if record.get("status") != "PASS":
        return {"verdict": record.get("status"), "reason": record.get("failure_reason", "run failed")}
    checks = {
        "residual": float(record["residual_relative"]) <= float(limits["residual"]["max"]),
        "equilibrium": float(record["equilibrium_relative"]) <= float(limits["equilibrium"]["max"]),
        "energy": float(record["energy_relative"]) <= float(limits["energy"]["relative_max"]),
        "finite": bool(record["finite_outputs"]),
        "spd_probe": bool(record["spd_probe"]["finite"] and record["spd_probe"]["positive_curvature"]),
    }
    return {"verdict": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "limits": limits}


def _write_partial(output: Path, run_id: str, record: dict[str, Any]) -> None:
    path = output / f"wp16_{run_id}.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _PeakRSSSampler:
    """Sample process RSS without changing the solver or its dependencies."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._peak = 0
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        try:
            import psutil
        except ImportError:
            return

        process = psutil.Process()

        def sample() -> None:
            while not self._stop.is_set():
                try:
                    self._peak = max(self._peak, int(process.memory_info().rss))
                except (psutil.Error, OSError):
                    return
                self._stop.wait(1.0)

        self._thread = threading.Thread(target=sample, name="wp16-rss", daemon=True)
        self._thread.start()

    def stop(self) -> int | None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return self._peak or None


def _digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


if __name__ == "__main__":
    main()
