"""Compare separate and paired K/M assembly on standard finite-element models.

This is a manual V&V campaign. It deliberately omits host identity and local
paths from the JSON report. The separate path is the comparison baseline; the
paired path is the current modal/Newmark/harmonic assembly route.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.sparse.linalg import norm as sparse_norm

from solveur.core.assembler import GlobalAssembler
from solveur.core.analysis import AnalysisSettings
from solveur.core.model import ElementDefinition, FiniteElementModel
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs


def run_campaign(
    sizes: list[int],
    output: Path | None = None,
    *,
    chunk_size: int = 256,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for target_dofs in sizes:
        nx, ny, nz = recommended_block_for_dofs(target_dofs)
        generated = generate_tet4_block(
            Path("results") / "scaling_0_2_2" / f"standard_km_{target_dofs}.npz",
            nx=nx,
            ny=ny,
            nz=nz,
        )
        model = _standard_model(generated, chunk_size=chunk_size)
        dofs = model.dof_manager()

        separate_started = time.perf_counter()
        separate_assembler = GlobalAssembler(chunk_size=chunk_size)
        stiffness_separate = separate_assembler.assemble_stiffness(model, dofs)
        stiffness_diagnostics = dict(separate_assembler.last_diagnostics)
        mass_separate = separate_assembler.assemble_mass(model, dofs)
        mass_diagnostics = dict(separate_assembler.last_diagnostics)
        separate_seconds = time.perf_counter() - separate_started

        paired_started = time.perf_counter()
        paired_assembler = GlobalAssembler(chunk_size=chunk_size)
        stiffness_paired, mass_paired, paired_k, paired_m = paired_assembler.assemble_stiffness_and_mass(model, dofs)
        paired_seconds = time.perf_counter() - paired_started

        rows.append(
            {
                "target_dofs": int(target_dofs),
                "dofs": int(dofs.ndof),
                "nodes": int(model.node_count),
                "elements": int(len(model.elements)),
                "chunk_size": int(chunk_size),
                "separate_seconds": float(separate_seconds),
                "paired_seconds": float(paired_seconds),
                "paired_over_separate_ratio": float(paired_seconds / max(separate_seconds, 1.0e-15)),
                "stiffness": _matrix_comparison(stiffness_separate, stiffness_paired),
                "mass": _matrix_comparison(mass_separate, mass_paired),
                "separate_diagnostics": {
                    "stiffness": _diagnostic_summary(stiffness_diagnostics),
                    "mass": _diagnostic_summary(mass_diagnostics),
                },
                "paired_diagnostics": {
                    "stiffness": _diagnostic_summary(paired_k),
                    "mass": _diagnostic_summary(paired_m),
                },
            }
        )
    report: dict[str, object] = {
        "schema_version": 1,
        "campaign": "qf-solver-standard-km-pair-scaling-0.2.2-alpha",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "comparison": "separate K then M assembly versus paired K/M assembly",
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _standard_model(large_model: object, *, chunk_size: int) -> FiniteElementModel:
    """Convert the deterministic large-model geometry to the standard API."""
    nodes = np.asarray(large_model.nodes, dtype=float)  # type: ignore[attr-defined]
    connectivity = np.asarray(large_model.tet4, dtype=np.int64)  # type: ignore[attr-defined]
    material = dict(large_model.materials["steel"])  # type: ignore[attr-defined]
    elements = [
        ElementDefinition("TET4", tuple(int(node) for node in nodes_for_element), "steel")
        for nodes_for_element in connectivity
    ]
    return FiniteElementModel(
        nodes=nodes,
        elements=elements,
        materials={"steel": material},
        analysis=AnalysisSettings(
            type="linear_static",
            method="direct",
            parameters={"assembly_chunk_size": int(chunk_size)},
        ),
    )


def _matrix_comparison(reference: object, candidate: object) -> dict[str, object]:
    reference_matrix = reference.tocsr()  # type: ignore[attr-defined]
    candidate_matrix = candidate.tocsr()  # type: ignore[attr-defined]
    difference = (candidate_matrix - reference_matrix).tocsr()
    reference_norm = float(sparse_norm(reference_matrix))
    difference_norm = float(sparse_norm(difference))
    max_absolute = float(np.max(np.abs(difference.data))) if difference.nnz else 0.0
    return {
        "shape": [int(value) for value in reference_matrix.shape],
        "reference_nnz": int(reference_matrix.nnz),
        "candidate_nnz": int(candidate_matrix.nnz),
        "difference_nnz": int(difference.nnz),
        "max_absolute_difference": max_absolute,
        "relative_frobenius_difference": float(difference_norm / max(reference_norm, 1.0e-300)),
    }


def _diagnostic_summary(diagnostics: dict[str, object]) -> dict[str, object]:
    phases = dict(diagnostics.get("assembly_phase_seconds", {}))
    return {
        "final_nnz": int(diagnostics.get("final_nnz", 0)),
        "chunk_count": int(diagnostics.get("chunk_count", 0)),
        "assembly_peak_memory_estimate_bytes": int(
            diagnostics.get("assembly_peak_memory_estimate_bytes", 0)
        ),
        "assembly_phase_seconds": {key: float(value) for key, value in phases.items()},
        "paired_assembly": bool(diagnostics.get("paired_assembly", False)),
        "shared_chunk_pattern": bool(diagnostics.get("shared_chunk_pattern", False)),
        "assembly_index_dtype": str(diagnostics.get("assembly_index_dtype", "unknown")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1_000, 10_000, 100_000])
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/scaling_0_2_2/standard_km_pair.json"),
    )
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("all target sizes must be at least 2 DOF")
    if args.chunk_size <= 0:
        parser.error("chunk-size must be positive")
    print(json.dumps(run_campaign(args.sizes, args.output, chunk_size=args.chunk_size), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
