# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_buckling."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_foundations import element_coordinates
from solveur.verification.robustness_mesh import mesh_refinement_mesh



def _buckling_model(element_type: str) -> FiniteElementModel:
    """Build the bounded homogeneous model used by the buckling evidence."""

    family = str(element_type).upper()
    if family == "TET4":
        nodes = element_coordinates("TET4")
        fixed = [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ]
        load_node = 1
    elif family == "HEX8":
        nodes = element_coordinates("HEX8")
        fixed = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7)]
        load_node = 1
    elif family in {"TET10", "HEX20"}:
        nodes = element_coordinates(family)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0)).tolist()
        load_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0)).tolist()
        if not fixed_nodes or not load_nodes:
            raise ValueError(f"Cannot construct the bounded {family} buckling boundary planes.")
        fixed = [{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes]
        load_node = int(load_nodes[0])
    else:
        raise ValueError("The bounded buckling campaign supports TET4, TET10, HEX8 and HEX20.")
    load_value = {"TET4": -1.0, "TET10": -0.1, "HEX8": -1.0, "HEX20": -10.0}[family]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": load_value}],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 100.0,
            "eigensolver_tolerance": 1.0e-8,
            "factor_tolerance": 1.0e-4,
        },
    )


def run_linear_buckling_benchmark(
    element_types: tuple[str, ...] = ("TET4", "HEX8"),
) -> dict[str, Any]:
    """Record a bounded sparse tangent-buckling path.

    The default remains TET4/HEX8 for compatibility with the original public
    benchmark. The internal robustness campaign supplies all four supported
    solid families explicitly, including research-only TET10/HEX20 rows.
    """

    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _buckling_model(family)
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        solver = data["solver"]
        bracket = solver["critical_bracket"]
        formulation = str(solver.get("eigen_formulation", bracket.get("method", "unknown")))
        if formulation == "generalized_eigsh":
            # The generalized solve returns an eigenvalue directly rather
            # than a bisection interval.
            width = 0.0
            relative_width = 0.0
        else:
            width = float(bracket["upper"] - bracket["lower"])
            relative_width = width / max(abs(float(bracket["upper"])), 1.0)
        dofs = model.dof_manager()
        fixed_indices = {
            dofs.index(condition.node, name)
            for condition in model.fixed_dofs
            for name in condition.dofs
        }
        reduced_dof_count = int(result.displacements.size - len(fixed_indices))
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and np.isfinite(float(solver["critical_factor"])) else "FAIL",
                "critical_factor": float(solver["critical_factor"]),
                # Keep the historical numeric bracket contract stable;
                # formulation metadata is exported beside it.
                "bracket": {
                    "lower": float(bracket["lower"]),
                    "upper": float(bracket["upper"]),
                },
                "bracket_width": width,
                "relative_bracket_width": relative_width,
                "eigen_formulation": formulation,
                "generalized_fallback_reason": bracket.get("generalized_fallback_reason"),
                "dof_count": int(result.displacements.size),
                "initial_tangent_nnz": int(solver["initial_tangent_nnz"]),
                "geometric_tangent_nnz": int(solver["geometric_tangent_nnz"]),
                "critical_mode_norm": float(solver["critical_mode_norm"]),
                "critical_mode_residual_relative": float(solver["critical_mode_residual_relative"]),
                "critical_mode_free_dof_count": int(solver["critical_mode_free_dof_count"]),
                "eigen_backend": solver["backend"],
                "dense_fallback_possible": reduced_dof_count <= 3,
                "preload_residual": float(
                    max(
                        step["relative_residual"]
                        for step in solver["preload_diagnostics"]["increments"]
                    )
                ),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "scope": "bounded homogeneous sparse linearized tangent buckling for requested solid families",
        "owner_acceptance_band_required": True,
        "limitations": [
            "This evidence does not close Euler, external-correlation or post-buckling requirements.",
            "The reported factor is the first loss of positive definiteness on the bounded preload path.",
            "TET10 and HEX20 rows are internal research evidence only; no high-order buckling qualification is claimed.",
        ],
    }


def _buckling_mesh_model(element_type: str, cells: int) -> FiniteElementModel:
    """Build one assembled, homogeneous mesh for buckling trend evidence."""

    family = str(element_type).upper()
    nodes, elements = mesh_refinement_mesh(family, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    if fixed_nodes.size == 0 or loaded_nodes.size == 0:
        raise ValueError(f"Cannot construct the {family} buckling mesh boundary planes.")
    load_value = {"TET4": -1.0, "TET10": -10.0, "HEX8": -1.0, "HEX20": -10.0}[family]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[
            {"node": int(node), "dof": "UX", "value": load_value / len(loaded_nodes)}
            for node in loaded_nodes
        ],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "maximum_factor": 100000.0,
            "eigensolver_tolerance": 1.0e-7,
            "factor_tolerance": 1.0e-3,
        },
    )


def run_buckling_mesh_sensitivity_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    levels: tuple[int, ...] = (1, 2),
) -> dict[str, Any]:
    """Record a bounded assembled-mesh buckling sensitivity trend.

    This deliberately reports a coarse-to-medium sensitivity study rather
    than claiming mesh convergence. Every level uses the public sparse
    ``linear_buckling`` route and the same boundary/load convention for a
    given element family.
    """

    if not levels or any(
        isinstance(level, bool) or not isinstance(level, int) or level < 1 for level in levels
    ):
        raise ValueError("Buckling mesh levels must be a non-empty tuple of positive integers.")
    if tuple(sorted(set(levels))) != levels:
        raise ValueError("Buckling mesh levels must be strictly increasing.")
    rows: list[dict[str, Any]] = []
    for family in element_types:
        normalized = str(family).upper()
        family_rows: list[dict[str, Any]] = []
        for cells in levels:
            started = perf_counter()
            try:
                model = _buckling_mesh_model(normalized, cells)
                result = solve_model(model, enforce_policy=False)
                solver = result.solver
                bracket = solver["critical_bracket"]
                bracket_width = float(bracket["upper"] - bracket["lower"])
                family_rows.append(
                    {
                        "element": normalized,
                        "cells_x": cells,
                        "node_count": int(result.node_count),
                        "element_count": int(result.element_count),
                        "dof_count": int(result.displacements.size),
                        "critical_factor": float(solver["critical_factor"]),
                        "bracket_width": bracket_width,
                        "relative_bracket_width": bracket_width
                        / max(abs(float(bracket["upper"])), 1.0),
                        "initial_tangent_nnz": int(solver["initial_tangent_nnz"]),
                        "geometric_tangent_nnz": int(solver["geometric_tangent_nnz"]),
                        "critical_mode_norm": float(solver["critical_mode_norm"]),
                        "critical_mode_residual_relative": float(solver["critical_mode_residual_relative"]),
                        "critical_mode_free_dof_count": int(solver["critical_mode_free_dof_count"]),
                        "preload_residual": float(
                            max(
                                step["relative_residual"]
                                for step in solver["preload_diagnostics"]["increments"]
                            )
                        ),
                        "elapsed_seconds": float(perf_counter() - started),
                        "status": "PASS"
                        if result.status == "PASS" and np.isfinite(float(solver["critical_factor"]))
                        else "FAIL",
                    }
                )
            except Exception as error:
                family_rows.append(
                    {
                        "element": normalized,
                        "cells_x": cells,
                        "status": "FAIL",
                        "failure_reason": type(error).__name__,
                        "failure_message": str(error),
                        "elapsed_seconds": float(perf_counter() - started),
                    }
                )
        if all(row["status"] == "PASS" for row in family_rows):
            coarse = family_rows[0]
            fine = family_rows[-1]
            fine["critical_factor_relative_change"] = abs(
                fine["critical_factor"] - coarse["critical_factor"]
            ) / max(abs(fine["critical_factor"]), 1.0e-15)
            fine["dof_growth"] = fine["dof_count"] / max(coarse["dof_count"], 1)
            fine["nnz_growth"] = fine["initial_tangent_nnz"] / max(
                coarse["initial_tangent_nnz"], 1
            )
        rows.append(
            {
                "element": normalized,
                "levels": family_rows,
                "status": "PASS" if all(row["status"] == "PASS" for row in family_rows) else "FAIL",
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "levels": list(levels),
        "rows": rows,
        "scope": "assembled homogeneous mesh sensitivity for sparse linearized tangent buckling",
        "owner_acceptance_band_required": True,
        "limitations": [
            "Coarse-to-medium trend only; this is not a mesh-convergence closure.",
            "The one-block-in-y/z topology is a bounded structural trend case, not a general column qualification.",
            "No post-buckling continuation or external multi-family correlation is claimed.",
        ],
    }


def run_euler_buckling_benchmark(output_dir: str | Path) -> dict[str, Any]:
    """Run a bounded analytical Euler reference for the TET4 TL route.

    The existing Euler campaign is reused rather than copied into the 0.2.5
    runner. Two medium-to-fine levels keep this evidence suitable for targeted
    execution while retaining a refinement check. It remains internal research
    evidence until external and high-order buckling cells close.
    """
    summary = TotalLagrangianBucklingCampaign(
        output_dir,
        levels=((24, 6, 6), (32, 8, 8)),
    ).run()
    return {
        "status": "PASS_INTERNAL_RESEARCH" if summary["status"] == "PASS_BUCKLING_RESEARCH" else "FAIL",
        "study_id": summary["study_id"],
        "reference": summary["reference"],
        "levels": summary["levels"],
        "checks": summary["checks"],
        "artifacts": [
            "summary.json",
            "report.md",
            "buckling_convergence.png",
            "buckling_mode.png",
        ],
        "owner_acceptance_band_required": True,
        "limitations": [
            "TET4 total-Lagrangian Euler column only; no TET10/HEX8/HEX20 claim.",
            "Bifurcation detection is precritical and does not provide post-buckling continuation.",
            "The result is internal research evidence until external correlation is attached to a clean SHA.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
