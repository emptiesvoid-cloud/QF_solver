"""Benchmark sparse TET4 assembly separately from solver scaling.

This campaign is intentionally manual. It compares the chunked SciPy
assembler at several model sizes and records only reproducible numerical and
resource metrics, without host identity or local paths.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Mapping

from solveur.large.assembler import ChunkedScipyAssembler
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs


def run_campaign(
    sizes: list[int],
    output: Path | None = None,
    *,
    chunk_size: int = 4096,
    repeats: int = 1,
    decomposition: str = "six",
    material: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    if repeats <= 0:
        raise ValueError("repeats must be positive")
    if decomposition not in {"six", "centered"}:
        raise ValueError("decomposition must be 'six' or 'centered'")
    rows: list[dict[str, object]] = []
    for target_dofs in sizes:
        nx, ny, nz = recommended_block_for_dofs(target_dofs)
        model_path = Path("results") / "scaling_0_2_2" / f"assembly_{target_dofs}.npz"
        model = generate_tet4_block(
            model_path,
            nx=nx,
            ny=ny,
            nz=nz,
            decomposition=decomposition,
            material=material,
        )
        elapsed_samples: list[float] = []
        phase_samples: dict[str, list[float]] = {}
        assembly = None
        nnz_samples: list[int] = []
        for _ in range(repeats):
            started = time.perf_counter()
            assembly = ChunkedScipyAssembler(chunk_size=chunk_size).assemble(model)
            elapsed_samples.append(time.perf_counter() - started)
            nnz_samples.append(int(assembly.stiffness.nnz))
            phases = dict((assembly.diagnostics or {}).get("assembly_phase_seconds", {}))
            for name, value in phases.items():
                phase_samples.setdefault(name, []).append(float(value))
        assert assembly is not None
        if len(set(nnz_samples)) != 1:
            raise RuntimeError(f"Assembly NNZ changed across repeats: {nnz_samples}")
        diagnostics = dict(assembly.diagnostics or {})
        diagnostics["repeat_count"] = int(repeats)
        diagnostics["assembly_seconds_samples"] = [float(value) for value in elapsed_samples]
        diagnostics["assembly_phase_seconds"] = {
            name: float(statistics.median(values)) for name, values in phase_samples.items()
        }
        rows.append(
            {
                "target_dofs": int(target_dofs),
                "dofs": int(model.ndof),
                "nodes": int(model.node_count),
                "elements": int(model.element_count),
                "assembly_seconds": float(statistics.median(elapsed_samples)),
                "assembly_seconds_samples": [float(value) for value in elapsed_samples],
                "repeat_count": int(repeats),
                "nnz": int(assembly.stiffness.nnz),
                "chunk_size": int(chunk_size),
                "assembly_diagnostics": diagnostics,
            }
        )
    report: dict[str, object] = {
        "schema_version": 1,
        "campaign": "qf-solver-tet4-assembly-scaling-0.2.2-alpha",
        "environment": "local reproducibility sample; host identity intentionally omitted",
        "configuration": {
            "decomposition": decomposition,
            "material": dict(material) if material is not None else "generator_default",
        },
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1_000, 10_000, 100_000])
    parser.add_argument("--chunk-size", type=int, default=4096)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--decomposition", choices=("six", "centered"), default="six")
    parser.add_argument("--young", type=float, default=210.0e9)
    parser.add_argument("--poisson", type=float, default=0.3)
    parser.add_argument("--density", type=float, default=7800.0)
    parser.add_argument("--output", type=Path, default=Path("results/scaling_0_2_2/assembly.json"))
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("all target sizes must be at least 2 DOF")
    if args.chunk_size <= 0:
        parser.error("chunk-size must be positive")
    if args.repeats <= 0:
        parser.error("repeats must be positive")
    material = {"type": "isotropic_3d", "E": args.young, "nu": args.poisson, "density": args.density}
    print(
        json.dumps(
            run_campaign(
                args.sizes,
                args.output,
                chunk_size=args.chunk_size,
                repeats=args.repeats,
                decomposition=args.decomposition,
                material=material,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
