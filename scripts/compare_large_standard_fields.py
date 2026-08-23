"""Compare the large TET4 SciPy path with the standard solver on one mesh family.

The campaign is a numerical cross-check, not a performance claim.  It keeps
the same generated geometry, material, loads and fixed DOFs, then compares
displacements, reactions, strains and stresses between the chunked large path
and the standard sparse path.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from solveur.core.assembler import GlobalAssembler
from solveur.core.analysis import AnalysisSettings
from solveur.core.model import BoundaryCondition, ElementDefinition, FiniteElementModel, NodalLoad
from solveur.core.solver import LinearStaticSolver
from solveur.large.assembler import ChunkedScipyAssembler, fixed_dof_indices
from solveur.large.generator import generate_tet4_block, recommended_block_for_dofs
from solveur.large.solver import solve_large_model
from solveur.large.tet4_batch import element_dofs_batch, tet4_response_batch


_DOF_NAMES = ("UX", "UY", "UZ")


def run_campaign(
    sizes: list[int],
    output: Path | None = None,
    *,
    chunk_size: int = 4096,
    decomposition: str = "centered",
    material: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Run cross-backend field and reaction comparisons for deterministic blocks."""
    if not sizes or any(size < 2 for size in sizes):
        raise ValueError("sizes must contain positive targets of at least 2 DOF")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    rows: list[dict[str, object]] = []
    for target_dofs in sizes:
        nx, ny, nz = recommended_block_for_dofs(target_dofs)
        generated = generate_tet4_block(
            Path("results") / "scaling_0_2_2" / f"field_comparison_{target_dofs}.npz",
            nx=nx,
            ny=ny,
            nz=nz,
            decomposition=decomposition,
            material=material,
        )
        standard_model = _standard_model(generated, chunk_size=chunk_size)
        standard_solver = LinearStaticSolver()
        standard_solver.assembler = GlobalAssembler(chunk_size=chunk_size)
        standard_result = standard_solver.solve(standard_model, detail_level="full")

        large_assembly = ChunkedScipyAssembler(chunk_size=chunk_size).assemble(generated)
        with tempfile.TemporaryDirectory(prefix="qf_field_compare_") as temporary:
            large_result = solve_large_model(generated, Path(temporary), solver_backend="scipy", chunk_size=chunk_size)
            large_displacement = _read_displacements(Path(temporary), large_result.output_files)

        standard_dofs = standard_model.dof_manager()
        standard_stiffness = GlobalAssembler(chunk_size=chunk_size).assemble_stiffness(
            standard_model, standard_dofs
        )
        standard_loads = GlobalAssembler(chunk_size=chunk_size).assemble_loads(standard_model, standard_dofs)
        standard_reactions = standard_stiffness @ standard_result.displacements - standard_loads
        large_loads = large_assembly.loads
        large_reactions = large_assembly.stiffness @ large_displacement - large_loads
        fixed = fixed_dof_indices(generated)

        standard_fields = _standard_fields(standard_result.element_results)
        large_fields = _large_fields(generated, large_displacement)
        rows.append(
            {
                "target_dofs": int(target_dofs),
                "dofs": int(generated.ndof),
                "nodes": int(generated.node_count),
                "elements": int(generated.element_count),
                "decomposition": decomposition,
                "matrix_nnz": int(large_assembly.stiffness.nnz),
                "displacement": _comparison(standard_result.displacements, large_displacement),
                "fixed_reaction": _comparison(standard_reactions[fixed], large_reactions[fixed]),
                "free_residual_standard": float(
                    np.linalg.norm(np.delete(standard_reactions, fixed))
                ),
                "free_residual_large": float(np.linalg.norm(np.delete(large_reactions, fixed))),
                "strain": _comparison(standard_fields["strain"], large_fields["strain"]),
                "stress": _comparison(standard_fields["stress"], large_fields["stress"]),
                "von_mises": _comparison(standard_fields["von_mises"], large_fields["von_mises"]),
                "standard_status": standard_result.status,
                "large_status": large_result.status,
            }
        )

    report: dict[str, object] = {
        "schema_version": 1,
        "campaign": "qf-solver-tet4-large-standard-field-comparison-0.2.2-alpha",
        "environment": "local numerical comparison; host identity and local paths intentionally omitted",
        "configuration": {
            "decomposition": decomposition,
            "material": dict(material) if material is not None else "generator_default",
            "chunk_size": int(chunk_size),
            "standard_backend": "scipy_sparse_direct",
            "large_backend": "scipy_sparse_iterative",
        },
        "acceptance": {
            "relative_field_tolerance": 1.0e-7,
            "relative_displacement_tolerance": 1.0e-7,
            "relative_reaction_tolerance": 1.0e-7,
            "all_cases_pass": all(_row_passes(row) for row in rows),
        },
        "sizes": rows,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _standard_model(large_model: Any, *, chunk_size: int) -> FiniteElementModel:
    nodes = np.asarray(large_model.nodes, dtype=float)
    elements = [
        ElementDefinition("TET4", tuple(int(node) for node in connectivity), "steel")
        for connectivity in np.asarray(large_model.tet4, dtype=np.int64)
    ]
    fixed = [
        BoundaryCondition(int(node), tuple(_DOF_NAMES[int(component)] for component in components))
        for node in np.unique(large_model.fixed_nodes)
        for components in [np.unique(large_model.fixed_components[large_model.fixed_nodes == node])]
    ]
    loads = [
        NodalLoad(int(node), _DOF_NAMES[int(component)], float(value))
        for node, component, value in zip(
            large_model.load_nodes, large_model.load_components, large_model.load_values, strict=True
        )
    ]
    return FiniteElementModel(
        nodes=nodes,
        elements=elements,
        materials={"steel": dict(large_model.materials["steel"])},
        fixed_dofs=fixed,
        loads=loads,
        analysis=AnalysisSettings(
            type="linear_static",
            method="direct",
            parameters={"assembly_chunk_size": int(chunk_size)},
        ),
    )


def _standard_fields(results: list[dict[str, object]]) -> dict[str, np.ndarray]:
    return {
        "strain": np.asarray([row["strain"] for row in results], dtype=float),
        "stress": np.asarray([row["stress"] for row in results], dtype=float),
        "von_mises": np.asarray([row["von_mises"] for row in results], dtype=float),
    }


def _large_fields(model: Any, displacement: np.ndarray) -> dict[str, np.ndarray]:
    edofs = element_dofs_batch(model.tet4)
    material = model.materials["steel"]
    from solveur.large.materials import create_large_material

    response = tet4_response_batch(
        model.nodes[model.tet4],
        displacement[edofs],
        create_large_material(material).elasticity_matrix,
    )
    return {name: np.asarray(response[name], dtype=float) for name in ("strain", "stress", "von_mises")}


def _comparison(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float | bool]:
    ref = np.asarray(reference, dtype=float)
    value = np.asarray(candidate, dtype=float)
    difference = value - ref
    relative = float(np.linalg.norm(difference) / max(float(np.linalg.norm(ref)), 1.0e-300))
    return {
        "relative_l2": relative,
        "max_absolute": float(np.max(np.abs(difference), initial=0.0)),
        "finite": bool(np.all(np.isfinite(value))),
    }


def _row_passes(row: dict[str, object]) -> bool:
    tolerance = 1.0e-7
    return all(
        bool(row[name]["finite"]) and float(row[name]["relative_l2"]) <= tolerance
        for name in ("displacement", "fixed_reaction", "strain", "stress", "von_mises")
    ) and row["standard_status"] == row["large_status"] == "PASS"


def _read_displacements(directory: Path, files: dict[str, str]) -> np.ndarray:
    path = directory / files["displacements"]
    if path.suffix == ".npz":
        return np.asarray(np.load(path)["displacements"], dtype=float).reshape(-1)
    import h5py

    with h5py.File(path, "r") as handle:
        return np.asarray(handle["displacements"], dtype=float).reshape(-1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=[1_000, 10_000])
    parser.add_argument("--chunk-size", type=int, default=4096)
    parser.add_argument("--decomposition", choices=("six", "centered"), default="centered")
    parser.add_argument("--young", type=float, default=70.0e9)
    parser.add_argument("--poisson", type=float, default=0.27)
    parser.add_argument("--density", type=float, default=2700.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("qualification/benchmarks/qf_solver_0_2_2_large_standard_field_comparison.json"),
    )
    args = parser.parse_args()
    material = {"type": "isotropic_3d", "E": args.young, "nu": args.poisson, "density": args.density}
    report = run_campaign(
        args.sizes,
        args.output,
        chunk_size=args.chunk_size,
        decomposition=args.decomposition,
        material=material,
    )
    print(json.dumps(report, indent=2))
    return 0 if bool(report["acceptance"]["all_cases_pass"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
