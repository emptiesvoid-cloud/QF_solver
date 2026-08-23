"""Compare sparse chunk-construction variants without changing the assembler."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from scipy.sparse import coo_matrix, csr_matrix
import numpy as np

from solveur.large.assembler import _material_cache, _stiffness_batch
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs
from solveur.large.tet4_batch import element_dofs_batch


def run_conversion_probe(
    target_dofs: int = 100_000,
    *,
    chunk_size: int = 4096,
    repeats: int = 3,
    output: Path | None = None,
) -> dict[str, object]:
    """Compare COO->CSR with SciPy's direct CSR constructor on one chunk."""
    if target_dofs < 2:
        raise ValueError("target_dofs must be at least 2")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    nx, ny, nz = recommended_block_for_dofs(target_dofs)
    model = generate_tet4_block(
        Path("results") / "scaling_0_2_2" / f"conversion_probe_{target_dofs}.npz",
        nx=nx,
        ny=ny,
        nz=nz,
    )
    stop = min(chunk_size, model.element_count)
    edofs = element_dofs_batch(model.tet4[:stop])
    stiffness = _stiffness_batch(model, 0, stop, _material_cache(model))
    values = stiffness.ravel()
    rows = np.repeat(edofs, 12, axis=1).ravel()
    cols = np.tile(edofs, (1, 12)).ravel()
    shape = (model.ndof, model.ndof)
    builders = {
        "coo_tocsr": lambda: coo_matrix((values, (rows, cols)), shape=shape).tocsr(),
        "csr_constructor": lambda: csr_matrix((values, (rows, cols)), shape=shape),
    }
    reference = builders["coo_tocsr"]()
    variants: list[dict[str, object]] = []
    for name, builder in builders.items():
        samples: list[float] = []
        candidate = None
        for _ in range(repeats):
            started = time.perf_counter()
            candidate = builder()
            samples.append(time.perf_counter() - started)
        assert candidate is not None
        candidate.sum_duplicates()
        difference = (reference - candidate).tocsr()
        variants.append(
            {
                "name": name,
                "median_seconds": float(statistics.median(samples)),
                "seconds_samples": [float(value) for value in samples],
                "nnz": int(candidate.nnz),
                "difference_nnz": int(difference.nnz),
                "max_abs_difference": float(np.max(np.abs(difference.data), initial=0.0)),
            }
        )
    report = {
        "schema_version": 1,
        "campaign": "qf-solver-tet4-assembly-conversion-probe-0.2.2-alpha",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "target_dofs": int(target_dofs),
        "dofs": int(model.ndof),
        "elements_in_chunk": int(stop),
        "chunk_size": int(chunk_size),
        "repeats": int(repeats),
        "variants": variants,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dofs", type=int, default=100_000)
    parser.add_argument("--chunk-size", type=int, default=4096)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/benchmarks/qf_solver_0_2_2_assembly_conversion_reference.json"),
    )
    args = parser.parse_args()
    print(json.dumps(run_conversion_probe(args.target_dofs, chunk_size=args.chunk_size, repeats=args.repeats, output=args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
