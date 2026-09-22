"""Run one bounded WP11 multi-element M1 or M2 case.

This runner is intentionally separate from ``run_wp11_mpi.py``.  It keeps the
legacy TET4 route immutable while exercising the existing standard element
kernels through a small PETSc/MPI envelope for TET4, HEX8, TET10 and HEX20.
The MPI extension uses root-side reference assembly and replicated input; it
must not be used for a scaling claim.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.large.multifamily import (  # noqa: E402
    SUPPORTED_WP11_FAMILIES,
    LinearSystem,
    assemble_linear_system,
    build_wp11_family_model,
    displacement_fingerprint,
    linear_observables,
    model_fingerprint,
    normalize_family,
    solve_linear_system,
)


CONTRACT_DEFAULT = ROOT / "qualification" / "0_2_9" / "wp11_multifamily_extension_contract.json"
RESIDUAL_TOLERANCE = 1.0e-10
CONTAINER_IMAGE_DIGEST = (
    "ghcr.io/fenics/dolfinx/dolfinx@sha256:"
    "2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
)


def _source_sha(contract: Path) -> str:
    explicit = os.environ.get("QF_WP11_EXECUTION_SHA")
    if explicit:
        return explicit
    declared = json.loads(contract.read_text(encoding="utf-8")).get("source_sha")
    if isinstance(declared, str) and declared and not declared.startswith("TO_BE_"):
        return declared
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _contract_sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_result(
    output: Path,
    result: dict[str, Any],
    displacement: np.ndarray,
    system: Any,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "displacement.npy", np.asarray(displacement, dtype=np.float64))
    np.save(output / "stiffness.npy", np.asarray(system.stiffness.toarray(), dtype=np.float64))
    np.save(output / "loads.npy", np.asarray(system.loads, dtype=np.float64))
    np.save(output / "fixed.npy", np.asarray(system.fixed, dtype=np.int64))
    result["evidence_files"] = {
        "displacement": "displacement.npy",
        "stiffness": "stiffness.npy",
        "loads": "loads.npy",
        "fixed": "fixed.npy",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_payload(
    *,
    family: str,
    backend: str,
    ranks: int,
    model: Any,
    displacement: np.ndarray,
    observables: dict[str, Any],
    contract: Path,
    started: float,
    phase: str,
) -> dict[str, Any]:
    return {
        "status": "PASS" if bool(observables.get("finite")) and observables["free_residual_relative_l2"] <= RESIDUAL_TOLERANCE else "FAIL",
        "work_package": "WP11",
        "scope": "MULTIFAMILY_BOUNDED",
        "element_family": family,
        "backend": backend,
        "phase": phase,
        "fresh_process": phase == "M3",
        "process_id": os.getpid(),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "mpi_rank_count": int(ranks),
        "assembly_scope": "standard_global_assembler" if backend == "scipy" else "root_global_assembly_bounded",
        "replicated_input": True,
        "scaling_claim": False,
        "actual_nodes": int(model.node_count),
        "actual_elements": int(len(model.elements)),
        "actual_dofs": int(model.dof_manager().ndof),
        "model_fingerprint": model_fingerprint(model),
        "displacement_fingerprint": displacement_fingerprint(displacement),
        "source_sha": _source_sha(contract),
        "contract_sha256": _contract_sha(contract),
        "observables": observables,
        "residual_tolerance": RESIDUAL_TOLERANCE,
        "container_image_digest": CONTAINER_IMAGE_DIGEST if backend == "petsc" else "local-python-runtime",
        "elapsed_seconds": float(time.perf_counter() - started),
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "fallback_count": 0,
    }


def _run_scipy(family: str, output: Path, contract: Path, phase: str) -> int:
    started = time.perf_counter()
    model = build_wp11_family_model(family)
    displacement, observables = solve_linear_system(assemble_linear_system(model))
    result = _base_payload(
        family=family,
        backend="scipy",
        ranks=1,
        model=model,
        displacement=displacement,
        observables=observables,
        contract=contract,
        started=started,
        phase=phase,
    )
    _write_result(output, result, displacement, assemble_linear_system(model))
    return 0 if result["status"] == "PASS" else 2


def _run_petsc(family: str, output: Path, contract: Path, phase: str) -> int:
    from mpi4py import MPI
    from petsc4py import PETSc

    started = time.perf_counter()
    comm = MPI.COMM_WORLD
    rank = int(comm.Get_rank())
    size = int(comm.Get_size())
    model = build_wp11_family_model(family)
    if rank == 0:
        system = assemble_linear_system(model)
        payload = (system.stiffness.toarray(), system.loads, system.fixed)
    else:
        payload = None
    matrix_dense, loads, fixed = comm.bcast(payload, root=0)
    matrix_dense = np.asarray(matrix_dense, dtype=float)
    loads = np.asarray(loads, dtype=float)
    fixed = np.asarray(fixed, dtype=np.int64)
    loads[fixed] = 0.0
    ndof = int(matrix_dense.shape[0])
    petsc_int = PETSc.IntType
    rows = np.arange(ndof, dtype=petsc_int)
    matrix = PETSc.Mat().createAIJ([ndof, ndof], comm=comm)
    matrix.setUp()
    if rank == 0:
        for row in range(ndof):
            matrix.setValues(row, rows, matrix_dense[row, :])
    matrix.assemblyBegin()
    matrix.assemblyEnd()
    matrix.zeroRowsColumns(np.asarray(fixed, dtype=petsc_int), diag=1.0)
    rhs = matrix.createVecRight()
    rhs.set(0.0)
    if rank == 0:
        rhs.setValues(rows, loads)
    rhs.assemblyBegin()
    rhs.assemblyEnd()
    solution = matrix.createVecRight()
    ksp = PETSc.KSP().create(comm=comm)
    ksp.setOperators(matrix)
    ksp.setType("cg")
    ksp.getPC().setType("gamg")
    ksp.setTolerances(rtol=1.0e-12, max_it=10_000)
    ksp.setFromOptions()
    ksp.solve(rhs, solution)
    start, stop = solution.getOwnershipRange()
    local_values = np.asarray(solution.getArray(readonly=True), dtype=float).copy()
    gathered = comm.gather((int(start), local_values), root=0)
    if rank == 0:
        if gathered is None:
            raise RuntimeError("PETSc/MPI gather returned no rank-owned vectors on rank 0.")
        displacement: np.ndarray = np.zeros(ndof, dtype=float)
        for offset, values in gathered:
            displacement[offset : offset + values.size] = values
        system = LinearSystem(stiffness=csr_matrix(matrix_dense), loads=loads, fixed=fixed)
        observables = linear_observables(system, displacement)
        observables.update(
            {
                "ksp_converged_reason": int(ksp.getConvergedReason()),
                "ksp_iterations": int(ksp.getIterationNumber()),
                "ksp_residual_norm": float(ksp.getResidualNorm()),
                "preconditioner": "gamg",
            }
        )
        result = _base_payload(
            family=family,
            backend="petsc",
            ranks=size,
            model=model,
            displacement=displacement,
            observables=observables,
            contract=contract,
            started=started,
            phase=phase,
        )
        _write_result(output, result, displacement, system)
        status = result["status"]
    else:
        status = None
    status = comm.bcast(status, root=0)
    ksp.destroy()
    solution.destroy()
    rhs.destroy()
    matrix.destroy()
    return 0 if status == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=SUPPORTED_WP11_FAMILIES, required=True)
    parser.add_argument("--backend", choices=("scipy", "petsc"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=CONTRACT_DEFAULT)
    parser.add_argument("--phase", choices=("M1", "M2", "M3"), default="M1")
    args = parser.parse_args()
    family = normalize_family(args.family)
    contract = args.contract if args.contract.is_absolute() else ROOT / args.contract
    if not contract.is_file():
        raise SystemExit(f"Contract not found: {contract}")
    if args.backend == "scipy":
        return _run_scipy(family, args.output, contract, args.phase)
    return _run_petsc(family, args.output, contract, args.phase)


if __name__ == "__main__":
    raise SystemExit(main())
