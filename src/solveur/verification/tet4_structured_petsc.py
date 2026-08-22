"""PETSc/GAMG evidence runner for a structured TET4 cantilever."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.large.io import load_large_model
from solveur.large.solver import solve_large_model
from solveur.verification.tet4_structured_convergence import (
    relative_error,
    timoshenko_tip_displacement,
)


def run_tet4_petsc_probe(
    model_path: str | Path,
    output_dir: str | Path,
    *,
    relative_limit: float = 0.01,
    residual_limit: float = 1.0e-8,
    chunk_size: int = 8192,
) -> dict[str, Any]:
    """Solve one generated TET4 cantilever with PETSc/GAMG and write evidence."""
    if relative_limit <= 0.0 or residual_limit <= 0.0:
        raise ValueError("PETSc probe limits must be positive.")
    model = load_large_model(model_path)
    metadata = dict(model.analysis.get("large_model", {}))
    length = float(metadata.get("length", 4.0))
    width = float(metadata.get("depth", 0.4))
    height = float(metadata.get("height", 0.4))
    material = model.materials[model.material_names[0]]
    young = float(material["E"])
    poisson = float(material["nu"])
    total_load = float(np.sum(model.load_values))
    reference = timoshenko_tip_displacement(total_load, length, width, height, young, poisson)
    output = Path(output_dir)
    result = solve_large_model(
        model,
        output,
        solver_backend="petsc",
        preconditioner="gamg",
        chunk_size=chunk_size,
    )
    displacement = _read_displacements(output, model.node_count)
    tip_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], length, atol=1.0e-12))
    tip_uz = float(np.mean(displacement[tip_nodes, 2]))
    relative = relative_error(tip_uz, reference)
    solver = result.summary["solver"]
    checks = {
        "solver_converged": bool(solver["converged"]),
        "finite_displacement": bool(np.all(np.isfinite(displacement))),
        "residual": float(solver["residual_norm"]) <= residual_limit,
        "relative_error": relative <= relative_limit,
    }
    summary: dict[str, Any] = {
        "study_id": "VNV-TET4-STRUCTURED-FLEXION-PETSC-001",
        "status": "PASS" if all(checks.values()) else "WARNING",
        "maturity": "stable_candidate",
        "model_path": str(Path(model_path).resolve()),
        "node_count": model.node_count,
        "element_count": model.element_count,
        "ndof": model.ndof,
        "backend": result.backend,
        "preconditioner": solver.get("preconditioner"),
        "mpi_size": solver.get("mpi_size"),
        "tip_uz_m": tip_uz,
        "reference_tip_uz_m": reference,
        "relative_error": relative,
        "solver": solver,
        "audit": result.audit.to_dict(),
        "criteria": {
            "relative_limit": relative_limit,
            "residual_limit": residual_limit,
            "checks": checks,
        },
        "limitations": [
            "The beam reference is a flexion diagnostic, not the final 3D oracle.",
            "This is a single-rank PETSc evidence run; multi-rank scalability is separate.",
            "Code_Aster TETRA4 same-mesh correlation remains required for stable promotion.",
        ],
    }
    write_json_file(output / "tet4_petsc_probe_summary.json", summary)
    (output / "tet4_petsc_probe_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _read_displacements(output: Path, node_count: int) -> np.ndarray:
    npz_path = output / "displacements.npz"
    if npz_path.is_file():
        values = np.load(npz_path, allow_pickle=False)["displacements"]
        return np.asarray(values, dtype=float).reshape((node_count, 3))
    h5_path = output / "displacements.h5"
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("PETSc probe output requires h5py when NPZ fallback is absent.") from exc
    with h5py.File(h5_path, "r") as handle:
        return np.asarray(handle["displacements"], dtype=float).reshape((node_count, 3))


def _report(summary: dict[str, Any]) -> str:
    checks = summary["criteria"]["checks"]
    return "\n".join(
        [
            f"# {summary['study_id']}",
            "",
            f"Statut : **{summary['status']}**.",
            "",
            f"- Elements : `{summary['element_count']}`",
            f"- DDL : `{summary['ndof']}`",
            f"- Backend : `{summary['backend']} + {summary['preconditioner']}`",
            f"- Iterations : `{summary['solver']['iterations']}`",
            f"- Residu : `{summary['solver']['residual_norm']:.6e}`",
            f"- Erreur de fleche : `{100.0 * summary['relative_error']:.6f} %`",
            f"- Checks : `{checks}`",
            "",
            "Le resultat sous 1 % ne ferme pas seul la qualification TET4 : une reference 3D et une correlation externe restent necessaires.",
            "",
        ]
    )
