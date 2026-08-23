"""Compare large-model backends on one identical mechanical observable."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from solveur.core.errors import InfrastructureError
from solveur.large.io import load_large_model
from solveur.large.solver import solve_large_model


def compare_large_backends(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    backends: Sequence[str] = ("scipy", "matrix_free", "petsc"),
    displacement_tolerance: float = 1.0e-7,
    chunk_size: int = 4096,
) -> dict[str, Any]:
    """Run requested backends and compare file-backed displacement fields."""
    names = _validate_backends(backends)
    if displacement_tolerance <= 0.0:
        raise ValueError("displacement_tolerance must be positive.")
    model = load_large_model(input_path)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    fields: dict[str, np.ndarray] = {}
    for backend in names:
        run_dir = root / backend
        try:
            result = solve_large_model(
                model,
                run_dir,
                solver_backend=backend,
                chunk_size=chunk_size,
            )
            field = _read_displacement(run_dir)
            fields[backend] = field
            runs.append(
                {
                    "backend": backend,
                    "status": result.status,
                    "result_backend": result.backend,
                    "summary": result.summary,
                    "audit_status": result.audit.status,
                    "displacement_size": int(field.size),
                }
            )
        except InfrastructureError as exc:
            runs.append({"backend": backend, "status": "SKIP", "reason": str(exc)})
        except Exception as exc:  # preserve the failing backend in the V&V record
            runs.append({"backend": backend, "status": "FAIL", "reason": f"{type(exc).__name__}: {exc}"})

    available = [run["backend"] for run in runs if run["status"] == "PASS"]
    comparisons: list[dict[str, Any]] = []
    if available:
        reference = available[0]
        for backend in available[1:]:
            error = _relative_error(fields[reference], fields[backend])
            comparisons.append(
                {
                    "reference_backend": reference,
                    "candidate_backend": backend,
                    "relative_displacement_error": error,
                    "tolerance": float(displacement_tolerance),
                    "status": "PASS" if error <= displacement_tolerance else "FAIL",
                }
            )
    failed = any(run["status"] == "FAIL" for run in runs) or any(
        comparison["status"] == "FAIL" for comparison in comparisons
    )
    skipped = any(run["status"] == "SKIP" for run in runs)
    status = "FAIL" if failed else "PARTIAL" if skipped else "PASS"
    summary = {
        "comparison_schema_version": 1,
        "status": status,
        "input": str(Path(input_path)),
        "ndof": int(model.ndof),
        "element_count": int(model.element_count),
        "backends_requested": list(names),
        "backends_completed": available,
        "chunk_size": int(chunk_size),
        "displacement_tolerance": float(displacement_tolerance),
        "runs": runs,
        "comparisons": comparisons,
        "interpretation": (
            "All requested backends completed and matched."
            if status == "PASS"
            else "Some optional backends were unavailable; this is not a complete backend qualification."
            if status == "PARTIAL"
            else "At least one backend or field comparison failed."
        ),
    }
    (root / "backend_comparison.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (root / "backend_comparison.md").write_text(_markdown(summary), encoding="utf-8")
    return summary


def _validate_backends(values: Sequence[str]) -> tuple[str, ...]:
    names = tuple(str(value).strip().lower() for value in values)
    allowed = {"scipy", "matrix_free", "petsc"}
    if not names or any(name not in allowed for name in names):
        raise ValueError("backends must contain only scipy, matrix_free or petsc.")
    if len(set(names)) != len(names):
        raise ValueError("backends must be unique.")
    return names


def _read_displacement(directory: Path) -> np.ndarray:
    hdf5_path = directory / "displacements.h5"
    if hdf5_path.is_file():
        try:
            import h5py
        except ImportError as exc:
            raise InfrastructureError("Reading HDF5 displacement output requires h5py.") from exc
        with h5py.File(hdf5_path, "r") as handle:
            return np.asarray(handle["displacements"], dtype=float).reshape(-1)
    npz_path = directory / "displacements.npz"
    if npz_path.is_file():
        with np.load(npz_path) as archive:
            return np.asarray(archive["displacements"], dtype=float).reshape(-1)
    raise InfrastructureError(f"No displacement output found in {directory}.")


def _relative_error(reference: np.ndarray, candidate: np.ndarray) -> float:
    if reference.shape != candidate.shape:
        raise ValueError("Compared displacement fields have different shapes.")
    numerator = float(np.linalg.norm(reference - candidate))
    denominator = float(np.linalg.norm(reference))
    return numerator / denominator if denominator > 0.0 else numerator


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Comparaison des backends grands modeles",
        "",
        f"Statut : **{summary['status']}**",
        "",
        "Le statut `PARTIAL` indique qu'un backend optionnel n'etait pas disponible ; il ne vaut pas qualification complete.",
        "",
        "| Backend | Statut | DDL | Audit | Motif |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for run in summary["runs"]:
        lines.append(
            f"| {run['backend']} | {run['status']} | "
            f"{run.get('summary', {}).get('ndof', '')} | {run.get('audit_status', '')} | {run.get('reason', '')} |"
        )
    lines.extend(("", "| Reference | Candidat | Ecart deplacement | Seuil | Statut |", "| --- | --- | ---: | ---: | --- |"))
    for comparison in summary["comparisons"]:
        lines.append(
            f"| {comparison['reference_backend']} | {comparison['candidate_backend']} | "
            f"{comparison['relative_displacement_error']:.6e} | {comparison['tolerance']:.6e} | {comparison['status']} |"
        )
    lines.extend(("", summary["interpretation"], ""))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backends", nargs="+", default=["scipy", "matrix_free", "petsc"])
    parser.add_argument("--displacement-tolerance", type=float, default=1.0e-7)
    parser.add_argument("--chunk-size", type=int, default=4096)
    args = parser.parse_args()
    summary = compare_large_backends(
        args.input,
        args.output,
        backends=args.backends,
        displacement_tolerance=args.displacement_tolerance,
        chunk_size=args.chunk_size,
    )
    print(f"BACKEND COMPARISON STATUS: {summary['status']}")
    print(f"report: {args.output / 'backend_comparison.md'}")
    return 0 if summary["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
