"""Run the bounded WP11 PETSc/MPI static campaign on a shared filesystem."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from mpi4py import MPI

from solveur.large.generator import generate_tet4_block
from solveur.large.io import load_large_model
from solveur.large.solver import solve_large_model

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp11_preparation_contract.json"
DOCKER_IMAGE_DIGEST = "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-dofs", type=int, default=24)
    args = parser.parse_args()
    comm = MPI.COMM_WORLD
    args.output.mkdir(parents=True, exist_ok=True)
    model_path = args.output / "model.h5"
    if comm.rank == 0:
        nx, ny, nz = 1, 1, 1
        if args.target_dofs > 24:
            from solveur.large.generator import recommended_block_for_dofs

            nx, ny, nz = recommended_block_for_dofs(args.target_dofs)
        generate_tet4_block(model_path, nx=nx, ny=ny, nz=nz, total_load=1000.0)
    comm.Barrier()
    model = load_large_model(model_path)
    result = solve_large_model(model, args.output, solver_backend="petsc", preconditioner="gamg")
    if comm.rank == 0:
        payload = {
            "status": result.status,
            "backend": result.backend,
            "mpi_rank_count": comm.size,
            "target_dofs": args.target_dofs,
            "actual_dofs": model.ndof,
            "source_sha": _git_sha(),
            "contract_sha256": _sha256(CONTRACT),
            "docker_image_digest": DOCKER_IMAGE_DIGEST,
            "summary": result.summary,
            "output_files": result.output_files,
        }
        (args.output / "wp11_mpi_result.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    comm.Barrier()
    return 0 if result.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
