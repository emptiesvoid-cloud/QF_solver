"""Reproducible SciPy/PETSc agreement campaign on a distributed TET4 block."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from solveur.core.errors import InfrastructureError
from solveur.io.manifest import write_json_file
from solveur.large.generator import generate_tet4_block
from solveur.large.io import load_large_model
from solveur.large.solver import solve_large_model
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-LARGE-PETSC-SCIPY-001"
_IMAGE = "qf-solver-large:0.2.0"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LargePetscScipyCorrelation:
    """Compare an in-process SciPy solve to an MPI PETSc solve in Docker."""

    study_id = STUDY_ID

    def __init__(self, output_dir: str | Path, *, image: str = _IMAGE, ranks: int = 2) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.image = image
        self.ranks = int(ranks)
        if self.ranks < 1:
            raise ValueError("PETSc/SciPy correlation requires at least one MPI rank.")

    def run(self) -> dict[str, Any]:
        """Generate, solve and compare a small distributed TET4 evidence case."""
        relative_output = _relative_to_project(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.output_dir / "model.h5"
        model = generate_tet4_block(model_path, nx=6, ny=4, nz=3)
        scipy_output = self.output_dir / "scipy"
        scipy_result = solve_large_model(
            load_large_model(model_path), scipy_output, solver_backend="scipy", preconditioner="jacobi"
        )
        petsc_output = self.output_dir / "petsc_mpi"
        self._run_petsc(relative_output, petsc_output.name)
        scipy_displacement = _read_hdf5_displacement(scipy_output / "displacements.h5")
        petsc_displacement = _read_mpi_binary_displacement(petsc_output / "displacements.bin", model.node_count)
        petsc_summary = json.loads((petsc_output / "summary.json").read_text(encoding="utf-8"))
        relative_difference = _relative_difference(scipy_displacement, petsc_displacement)
        checks = [
            _check("displacement_agreement", relative_difference, 1.0e-8),
            _check("scipy_residual", float(scipy_result.summary["solver"]["residual_norm"]), 1.0e-7),
            _check("petsc_residual", float(petsc_summary["solver"]["residual_norm"]), 1.0e-7),
            _equal("petsc_distributed", bool(petsc_summary["solver"]["distributed"]), self.ranks > 1),
        ]
        summary: dict[str, Any] = {
            "study_id": STUDY_ID,
            "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
            "purpose": "SciPy/PETSc numerical agreement, not large-scale performance qualification.",
            "model": {
                "nodes": model.node_count,
                "elements": model.element_count,
                "dofs": model.ndof,
                "topology": "structured TET4 block 6x4x3 cells",
            },
            "scipy": scipy_result.summary["solver"],
            "petsc": petsc_summary["solver"],
            "docker": {"image": self.image, "mpi_ranks": self.ranks},
            "relative_displacement_difference": relative_difference,
            "checks": checks,
            "limitations": [
                "The model is deliberately small and proves solution/residual agreement only.",
                "The separate P4 campaigns remain authoritative for million-DOF timing, memory and scaling.",
                "PETSc executes in the pinned Docker runtime; the host Python environment need not contain petsc4py.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _run_petsc(self, relative_output: Path, output_name: str) -> None:
        container_root = f"/workspace/{relative_output.as_posix()}"
        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{_PROJECT_ROOT}:/workspace",
            "-w",
            "/workspace",
            self.image,
            "mpiexec",
            "-n",
            str(self.ranks),
            "python3",
            "qf_solver.py",
            "solve-large",
            "--input",
            f"{container_root}/model.h5",
            "--output",
            f"{container_root}/{output_name}",
            "--solver-backend",
            "petsc",
            "--preconditioner",
            "gamg",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
        except FileNotFoundError as exc:
            raise InfrastructureError("PETSc/SciPy correlation requires the Docker CLI.") from exc
        except subprocess.TimeoutExpired as exc:
            raise InfrastructureError("PETSc/SciPy Docker solve exceeded the 300 second infrastructure timeout.") from exc
        (self.output_dir / "petsc_stdout.log").write_text(completed.stdout, encoding="utf-8")
        (self.output_dir / "petsc_stderr.log").write_text(completed.stderr, encoding="utf-8")
        if completed.returncode:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
            raise InfrastructureError(f"PETSc/SciPy Docker correlation failed:\n{tail}")


def _relative_to_project(path: Path) -> Path:
    try:
        return path.relative_to(_PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("PETSc/SciPy correlation output must be located inside the project root.") from exc


def _read_hdf5_displacement(path: Path) -> np.ndarray:
    with h5py.File(path, "r") as handle:
        return np.asarray(handle["displacements"], dtype=float)


def _read_mpi_binary_displacement(path: Path, node_count: int) -> np.ndarray:
    values = np.fromfile(path, dtype=np.float64)
    expected = 3 * node_count
    if values.size != expected:
        raise ValueError(f"PETSc MPI displacement file contains {values.size} values; expected {expected}.")
    return values.reshape((node_count, 3))


def _relative_difference(reference: np.ndarray, candidate: np.ndarray) -> float:
    return float(np.linalg.norm(reference - candidate) / max(float(np.linalg.norm(reference)), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}


def _equal(identifier: str, value: bool, expected: bool) -> dict[str, object]:
    return {"id": identifier, "value": value, "expected": expected, "status": "PASS" if value == expected else "FAIL"}


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "| Observable | Valeur |",
        "| --- | ---: |",
        f"| Ecart relatif deplacement SciPy/PETSc | {summary['relative_displacement_difference']:.6e} |",
        f"| Residus SciPy / PETSc | {summary['scipy']['residual_norm']:.6e} / {summary['petsc']['residual_norm']:.6e} |",
        f"| Rangs MPI PETSc | {summary['docker']['mpi_ranks']} |",
        "",
        "Cette campagne compare les deux routes numeriques sur le meme HDF5 TET4. Elle ne mesure pas la performance de passage a l'echelle.",
    ]
    return "\n".join(lines) + "\n"
