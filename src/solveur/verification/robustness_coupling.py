# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_coupling."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_mesh import _multi_element_model, mesh_refinement_mesh



def run_multifamily_coupled_geometry_benchmark() -> dict[str, Any]:
    """Exercise connected J2 plus geometric nonlinearity on all solid families."""

    rows: list[dict[str, Any]] = []
    for family in ELEMENT_TYPES:
        model = _multi_element_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "kinematics": "total_lagrangian_j2",
                "load_steps": 2,
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "solver_status": result.status,
                "kinematics": solver["kinematics"],
                "contact_mode": solver["contact_mode"],
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "step_count": len(steps),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two connected elements per family and no contact contribution.",
            "Internal research evidence only; no external coupled correlation or physical validation claim.",
            "The contact-coupled cases remain the bounded TET4 observations in the companion campaign.",
        ],
    }


def run_multifamily_coupled_contact_benchmark() -> dict[str, Any]:
    """Exercise finite-kinematic penalty contact on all four solid families.

    The body is deliberately reduced to one regular block per family.  A
    fixed triangular master surface is placed just in front of one loaded
    corner, so the same common ``total_lagrangian_j2`` residual/tangent path
    must cross from open to active contact for TET4, TET10, HEX8 and HEX20.
    This is composition evidence only; it is not a general surface-contact
    qualification.
    """

    rows: list[dict[str, Any]] = []
    load_path = [float(value) for value in np.linspace(0.02, 1.0, 50)]
    for family in ELEMENT_TYPES:
        try:
            nodes, elements = mesh_refinement_mesh(family, 1)
            nodes = np.asarray(nodes, dtype=float).copy()
            nodes[:, 0] *= 0.2
            slave = int(np.flatnonzero(np.isclose(nodes[:, 0], 0.2))[0])
            master_start = len(nodes)
            master_nodes = (master_start, master_start + 1, master_start + 2)
            nodes = np.vstack(
                (
                    nodes,
                    np.asarray(
                        [[0.19, -0.5, -0.5], [0.19, 0.5, -0.5], [0.19, 0.0, 0.5]],
                        dtype=float,
                    ),
                )
            )
            fixed_dofs = [
                {"node": node, "dofs": ["UX", "UY", "UZ"]}
                for node in range(len(nodes))
                if node != slave
            ]
            fixed_dofs.append({"node": slave, "dofs": ["UY", "UZ"]})
            model = FiniteElementModel.from_raw(
                nodes=nodes.tolist(),
                elements=[
                    {"type": family, "nodes": item, "material": "j2"}
                    for item in elements
                ],
                materials={
                    "j2": {
                        "type": "von_mises_elastoplastic_3d",
                        "E": 10.0,
                        "nu": 0.3,
                        "yield_stress": 0.02,
                        "hardening_modulus": 10.0,
                    }
                },
                fixed_dofs=fixed_dofs,
                loads=[{"node": slave, "dof": "UX", "value": -1.0}],
                analysis={
                    "type": "nonlinear_static",
                    "method": "newton_raphson",
                    "load_path": load_path,
                    "max_iterations": 100,
                    "tolerance": 1.0e-8,
                    "kinematics": "total_lagrangian_j2",
                    "contact_mode": "penalty",
                    "contact_penalty": 1.0e6,
                    "contact_search_mode": "updated",
                    "contact_max_penetration": 5.0e-3,
                },
            )
            model.contacts.append(
                FrictionlessContact(
                    name="nearby_master_plane",
                    slave_node=slave,
                    master_nodes=master_nodes,
                    master_faces=(master_nodes,),
                )
            )
            result = solve_model(model, enforce_policy=False)
            steps = result.to_dict()["solver"]["steps"]
            gaps = [float(step["contact_gaps"][0]) for step in steps]
            residuals = [float(step["relative_residual"]) for step in steps]
            active_steps = sum(bool(step["contact_active_contacts"]) for step in steps)
            maximum_penetration = max(-min(gaps, default=0.0), 0.0)
            final_peeq = float(steps[-1]["equivalent_plastic_strain_max"])
            row_status = (
                result.status == "PASS"
                and active_steps > 0
                and gaps[0] > 0.0
                and gaps[-1] < 0.0
                and maximum_penetration < 1.0e-4
                and max(residuals) < 1.0e-7
                and final_peeq > 0.0
            )
            rows.append(
                {
                    "element": family,
                    "status": "PASS" if row_status else "FAIL",
                    "solver_status": result.status,
                    "kinematics": "total_lagrangian_j2",
                    "contact_mode": "penalty",
                    "contact_search_mode": "updated",
                    "node_count": int(len(nodes)),
                    "element_count": int(len(elements)),
                    "active_step_count": int(active_steps),
                    "step_count": len(steps),
                    "initial_gap": gaps[0],
                    "final_gap": gaps[-1],
                    "maximum_penetration": maximum_penetration,
                    "maximum_relative_residual": max(residuals),
                    "newton_iterations": int(sum(step["iterations"] for step in steps)),
                    "final_peeq": final_peeq,
                    "final_slave_displacement": result.displacements[
                        [result.dofs.index(slave, dof) for dof in ("UX", "UY", "UZ")]
                    ].tolist(),
                }
            )
        except Exception as error:  # pragma: no cover - retained as explicit campaign evidence
            rows.append(
                {
                    "element": family,
                    "status": "FAIL",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if rows and all(row["status"] == "PASS" for row in rows)
        else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "load_path": load_path,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One regular block and one fixed triangular master plane per family.",
            "The small-strain J2 hardening law is active, but this remains a bounded composition case rather than a material qualification.",
            "This does not qualify general surface-to-surface contact, finite sliding, friction or external correlation.",
        ],
    }


def run_coupling_benchmark() -> dict[str, Any]:
    """Exercise the common driver with pairwise and triple nonlinear couplings.

    This is deliberately a bounded internal composition check.  It verifies
    that material, geometric and penalty-contact contributions coexist in one
    residual/tangent path; it does not qualify large deformation, contact
    search, or external physical behaviour.
    """

    cases = (
        ("j2_plus_geometry", {"kinematics": "total_lagrangian_j2"}, False),
        (
            "geometry_plus_contact",
            {
                "kinematics": "total_lagrangian_j2",
                "contact_mode": "penalty",
                "contact_penalty": 1.0e6,
            },
            True,
        ),
        (
            "j2_geometry_plus_updated_contact",
            {
                "kinematics": "total_lagrangian_j2",
                "contact_mode": "penalty",
                "contact_search_mode": "updated",
                "contact_penalty": 1.0e6,
            },
            True,
        ),
    )
    rows: list[dict[str, Any]] = []
    for name, updates, with_contact in cases:
        model = _multi_element_model("TET4")
        if with_contact:
            model.loads = [replace(load, value=-load.value) for load in model.loads]
            model.contacts.append(FrictionlessContact(slave_node=4, master_nodes=(1, 2, 3)))
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, **updates, "load_steps": 2},
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        steps = solver["steps"]
        rows.append(
            {
                "case": name,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "solver_status": result.status,
                "kinematics": solver["kinematics"],
                "contact_mode": solver["contact_mode"],
                "contact_search_mode": solver["contact_search_mode"],
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "step_count": len(steps),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "shared_driver": True,
        "shared_residual_and_tangent": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One bounded two-element TET4 composition model only.",
            "Penalty contact is frictionless and limited to initial or updated local geometry.",
            "No multi-element coupled qualification, finite sliding, friction or external correlation is claimed.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
