"""Three-dimensional reference for the structured TET4 flexion study."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.model_writer import JsonModelWriter
from solveur.large.generator import generate_tet4_cantilever_block
from solveur.large.io import load_large_model
from solveur.large.matrix_free import solve_structured_matrix_free
from solveur.verification.tet4_structured_convergence import (
    relative_error,
    timoshenko_tip_displacement,
)
from solveur.verification.tet10_structural_convergence import plot_tetra_vector
from solveur.verification.vnv_manifest import write_vnv_manifest


TET10_EDGE_ORDER = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))


def convert_structured_tet4_to_tet10(large_model: object) -> FiniteElementModel:
    """Convert a pure array-based TET4 model to a conforming TET10 model.

    Mid-edge nodes are created once per global edge in deterministic element
    order. Fixed components are propagated to a midpoint when both edge
    endpoints carry that component, which preserves a clamped boundary.
    Nodal loads remain on the original nodes so the total resultant is exactly
    conserved; the conversion is intended as a 3D reference, not a new load
    integration scheme.
    """
    tet4 = np.asarray(large_model.tet4, dtype=np.int64)
    if tet4.ndim != 2 or tet4.shape[1] != 4 or tet4.size == 0:
        raise ValueError("TET10 reference conversion requires a non-empty TET4 model.")
    nodes = np.asarray(large_model.nodes, dtype=float)
    edge_nodes: dict[tuple[int, int], int] = {}
    converted_nodes = [row.tolist() for row in nodes]
    connectivity: list[list[int]] = []

    def midpoint_node(first: int, second: int) -> int:
        edge = (min(first, second), max(first, second))
        existing = edge_nodes.get(edge)
        if existing is not None:
            return existing
        index = len(converted_nodes)
        converted_nodes.append(((nodes[edge[0]] + nodes[edge[1]]) * 0.5).tolist())
        edge_nodes[edge] = index
        return index

    for corners in tet4:
        corner_ids = [int(value) for value in corners]
        mids = [midpoint_node(corner_ids[first], corner_ids[second]) for first, second in TET10_EDGE_ORDER]
        connectivity.append(corner_ids + mids)

    fixed_by_node: dict[int, set[int]] = {}
    for node, component in zip(large_model.fixed_nodes, large_model.fixed_components, strict=True):
        fixed_by_node.setdefault(int(node), set()).add(int(component))
    fixed_pairs: set[tuple[int, int]] = set()
    for node, components in fixed_by_node.items():
        for component in components:
            fixed_pairs.add((node, component))
    for (first, second), midpoint in edge_nodes.items():
        for component in fixed_by_node.get(first, set()) & fixed_by_node.get(second, set()):
            fixed_pairs.add((midpoint, component))

    material_names = tuple(large_model.material_names)
    elements = [
        {
            "type": "TET10",
            "nodes": item,
            "material": material_names[int(material_id)],
        }
        for item, material_id in zip(connectivity, large_model.material_ids, strict=True)
    ]
    fixed_dofs = [
        {"node": node, "dofs": [("UX", "UY", "UZ")[component]]}
        for node, component in sorted(fixed_pairs)
    ]
    loads = [
        {
            "node": int(node),
            "dof": ("UX", "UY", "UZ")[int(component)],
            "value": float(value),
        }
        for node, component, value in zip(
            large_model.load_nodes,
            large_model.load_components,
            large_model.load_values,
            strict=True,
        )
    ]
    analysis = dict(large_model.analysis)
    analysis["method"] = "direct"
    return FiniteElementModel.from_raw(
        nodes=converted_nodes,
        elements=elements,
        materials=dict(large_model.materials),
        fixed_dofs=fixed_dofs,
        loads=loads,
        analysis=analysis,
        units=dict(large_model.units),
        verification_profile="quick",
    )


def run_tet4_tet10_reference(
    output_dir: str | Path,
    *,
    base_nx: int = 8,
    base_ny: int = 2,
    base_nz: int = 2,
    refinement_factors: tuple[int, ...] = (1, 2, 4),
    relative_limit: float = 0.01,
    decomposition: str = "six",
    load_distribution: str = "tributary",
    study_id: str = "VNV-TET4-TET10-3D-REFERENCE-001",
) -> dict[str, Any]:
    """Compare structured TET4 and conforming TET10 against a beam diagnostic."""
    if not refinement_factors or tuple(sorted(set(refinement_factors))) != refinement_factors:
        raise ValueError("Reference factors must be strictly increasing.")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    length, width, height = 4.0, 0.4, 0.4
    young, poisson, total_load = 70.0e9, 0.3, -1.0
    reference = timoshenko_tip_displacement(total_load, length, width, height, young, poisson)
    rows: list[dict[str, Any]] = []
    fine_model: FiniteElementModel | None = None
    fine_result: object | None = None
    for factor in refinement_factors:
        level = output / f"level_{factor}"
        large_path = level / "tet4_model.npz"
        large = generate_tet4_cantilever_block(
            large_path,
            nx=base_nx * factor,
            ny=base_ny * factor,
            nz=base_nz * factor,
            length=length,
            height=height,
            depth=width,
            young=young,
            poisson=poisson,
            total_load=total_load,
            decomposition=decomposition,
            load_distribution=load_distribution,
        )
        tet10_model = convert_structured_tet4_to_tet10(load_large_model(large_path))
        JsonModelWriter().write(tet10_model, level / "tet10_reference.json")
        tet10_result = solve_model(tet10_model, enforce_policy=False)
        tet4_result = solve_structured_matrix_free(load_large_model(large_path), rtol=1.0e-9, maxiter=10_000)
        tip_nodes_tet10 = np.flatnonzero(np.isclose(tet10_model.nodes[:, 0], length, atol=1.0e-12))
        tip_indices = np.asarray([tet10_model.dof_manager().index(int(node), "UZ") for node in tip_nodes_tet10])
        tet10_tip = float(np.mean(np.asarray(tet10_result.displacements)[tip_indices]))
        tip_nodes_tet4 = np.flatnonzero(np.isclose(large.nodes[:, 0], length, atol=1.0e-12))
        tet4_tip = float(np.mean(tet4_result.displacement.reshape((-1, 3))[tip_nodes_tet4, 2]))
        rows.append(
            {
                "factor": int(factor),
                "tet4_elements": int(large.element_count),
                "tet10_nodes": int(tet10_model.node_count),
                "tet10_dofs": int(tet10_model.dof_manager().ndof),
                "tet4_tip_uz_m": tet4_tip,
                "tet10_tip_uz_m": tet10_tip,
                "reference_tip_uz_m": reference,
                "tet4_reference_error": relative_error(tet4_tip, reference),
                "tet10_reference_error": relative_error(tet10_tip, reference),
                "tet4_tet10_difference": relative_error(tet4_tip, tet10_tip),
                "tet4_residual": float(tet4_result.solver_info["relative_residual"]),
                "tet10_residual": float(tet10_result.audit.equilibrium["free_residual_norm"]),
            }
        )
        fine_model, fine_result = tet10_model, tet10_result
    fine = rows[-1]
    checks = {
        "finite": bool(all(np.isfinite(row["tet10_tip_uz_m"]) for row in rows)),
        "tet10_reference_under_one_percent": bool(fine["tet10_reference_error"] <= relative_limit),
        "tet10_residual": bool(fine["tet10_residual"] <= 1.0e-8),
    }
    summary: dict[str, Any] = {
        "study_id": study_id,
        "status": "PASS" if all(checks.values()) else "WARNING",
        "maturity": "stable_candidate",
        "reference": {"type": "Timoshenko beam diagnostic", "tip_uz_m": reference},
        "discretization": {
            "decomposition": decomposition,
            "load_distribution": load_distribution,
            "same_mesh_tet4_tet10": True,
        },
        "rows": rows,
        "criteria": {"relative_limit": relative_limit, "checks": checks},
        "limitations": [
            "TET10 is an internal higher-order 3D reference on the same structured geometry.",
            "The nodal load resultant is conserved, but the TET10 face load interpolation is not an external oracle.",
            "Code_Aster TETRA10 or an independent 3D reference remains required for stable promotion.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "report.md").write_text(_report(summary), encoding="utf-8")
    if fine_model is not None and fine_result is not None:
        plot_tetra_vector(output / "tet10_deformation.png", fine_model, np.asarray(fine_result.displacements), "TET10 reference 3D")
        _plot_convergence(output / "convergence.png", rows, relative_limit)
        (output / "tet10_tip_summary.json").write_text(
            json.dumps(
                {
                    "study_id": summary["study_id"],
                    "factor": fine["factor"],
                    "tip_uz_m": fine["tet10_tip_uz_m"],
                    "reference_tip_uz_m": fine["reference_tip_uz_m"],
                    "relative_error": fine["tet10_reference_error"],
                    "residual": fine["tet10_residual"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    write_vnv_manifest(output, str(summary["study_id"]))
    return summary


def _plot_convergence(path: Path, rows: list[dict[str, Any]], relative_limit: float) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    elements = [row["tet4_elements"] for row in rows]
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.loglog(elements, [100.0 * row["tet4_reference_error"] for row in rows], "o-", label="TET4 / poutre")
    axis.loglog(elements, [100.0 * row["tet10_reference_error"] for row in rows], "s-", label="TET10 / poutre")
    axis.axhline(100.0 * relative_limit, color="#c92a2a", linestyle="--", label="seuil 1 %")
    axis.set(xlabel="Elements TET4 par niveau", ylabel="Erreur relative [%]", title="Reference 3D et convergence")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut : **{summary['status']}**.",
        "",
        "| Facteur | TET4 elements | TET10 DDL | Erreur TET4/poutre | Erreur TET10/poutre | Ecart TET4/TET10 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['factor']} | {row['tet4_elements']} | {row['tet10_dofs']} | "
            f"{100.0 * row['tet4_reference_error']:.6f} % | "
            f"{100.0 * row['tet10_reference_error']:.6f} % | "
            f"{100.0 * row['tet4_tet10_difference']:.6f} % |"
        )
    lines.extend(["", "Le TET10 est utilise comme reference 3D interne ; il ne remplace pas Code_Aster TETRA10.", ""])
    return "\n".join(lines)
