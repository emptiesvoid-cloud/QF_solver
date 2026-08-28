# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_contact."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403
from solveur.verification.robustness_mesh import _refinement_model
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.verification.robustness_contact_extended import (
    run_contact_facet_transition_rollback_benchmark,
    run_contact_surface_patch_benchmark,
    run_contact_three_facet_sliding_benchmark,
)



def run_common_contact_benchmark() -> dict[str, Any]:
    """Record local unilateral contact and common-driver composition evidence."""

    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    parameters = dict(model.analysis.parameters)
    parameters.update({"contact_mode": "penalty", "contact_penalty": 1.0e6, "load_steps": 2})
    model.analysis = replace(model.analysis, parameters=parameters)
    dofs = model.dof_manager()
    open_internal, open_tangent, open_details = assemble_penalty_contact(
        model, dofs, np.zeros(dofs.ndof), penalty=1.0e6
    )
    closed = np.zeros(dofs.ndof)
    closed[dofs.index(1, "UX")] = -1.2
    closed_internal, closed_tangent, closed_details = assemble_penalty_contact(
        model, dofs, closed, penalty=1.0e6
    )
    result = solve_model(model, enforce_policy=False)
    updated_model = deepcopy(model)
    updated_model.analysis = replace(
        updated_model.analysis,
        parameters={**updated_model.analysis.parameters, "contact_search_mode": "updated"},
    )
    updated_result = solve_model(updated_model, enforce_policy=False)
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS"
        and updated_result.status == "PASS"
        and np.allclose(open_internal, 0.0)
        and open_tangent.nnz == 0
        and closed_details["active_contacts"]
        and closed_tangent.nnz > 0
        else "FAIL",
        "global_solver_status": result.status,
        "updated_global_solver_status": updated_result.status,
        "contact_mode": result.to_dict()["solver"]["contact_mode"],
        "updated_contact_search_mode": "updated",
        "open": open_details,
        "closed": closed_details,
        "open_tangent_nnz": int(open_tangent.nnz),
        "closed_tangent_nnz": int(closed_tangent.nnz),
        "closed_internal_norm": float(np.linalg.norm(closed_internal)),
        "global_max_relative_residual": float(max(step["relative_residual"] for step in result.to_dict()["solver"]["steps"])),
        "updated_global_max_relative_residual": float(max(step["relative_residual"] for step in updated_result.to_dict()["solver"]["steps"])),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Initial-configuration node-to-triangle frictionless penalty only.",
            "No finite-sliding, recontact-search or friction qualification is claimed.",
        ],
    }


def run_contact_tangent_fd_benchmark(
    perturbation_steps: tuple[float, ...] = (1.0e-4, 1.0e-6, 1.0e-8),
) -> dict[str, Any]:
    """Check the fixed-active penalty contact tangent by finite differences.

    The test intentionally freezes the initial master geometry and stays away
    from the active-set boundary. It verifies the smooth local tangent used by
    the common residual assembly, not the non-smooth opening/closing transition
    or a general surface-to-surface formulation.
    """

    if not perturbation_steps or any(
        not np.isfinite(step) or step <= 0.0 for step in perturbation_steps
    ):
        raise ValueError("perturbation_steps must contain finite positive values.")
    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.1, 0.25, 0.25],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_search_mode": "initial"},
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="fixed_active_contact",
            slave_node=3,
            master_nodes=(0, 1, 2),
        )
    )
    dofs = model.dof_manager()
    base = np.zeros(dofs.ndof, dtype=float)
    base[dofs.index(3, "UX")] = -0.2
    penalty = 1.0e3
    _, tangent, base_details = assemble_penalty_contact(model, dofs, base, penalty=penalty)
    direction_indices = [
        dofs.index(node, dof)
        for node in range(4)
        for dof in ("UX", "UY", "UZ")
    ]
    rows: list[dict[str, Any]] = []
    for step in perturbation_steps:
        errors: list[float] = []
        for index in direction_indices:
            direction = np.zeros(dofs.ndof, dtype=float)
            direction[index] = 1.0
            plus, _, _ = assemble_penalty_contact(
                model, dofs, base + step * direction, penalty=penalty
            )
            minus, _, _ = assemble_penalty_contact(
                model, dofs, base - step * direction, penalty=penalty
            )
            finite_difference = (plus - minus) / (2.0 * step)
            tangent_direction = tangent @ direction
            denominator = max(
                float(np.linalg.norm(finite_difference)),
                float(np.linalg.norm(tangent_direction)),
                1.0,
            )
            errors.append(
                float(np.linalg.norm(finite_difference - tangent_direction) / denominator)
            )
        rows.append(
            {
                "perturbation_step": float(step),
                "maximum_relative_error": max(errors, default=float("inf")),
                "direction_count": len(direction_indices),
            }
        )
    maximum_error = max(
        (row["maximum_relative_error"] for row in rows), default=float("inf")
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if maximum_error <= 1.0e-8 else "FAIL",
        "formulation": "frictionless_penalty_fixed_active_initial_geometry",
        "penalty": penalty,
        "active_contacts": list(base_details["active_contacts"]),
        "base_gap": float(base_details["gaps"][0]),
        "tangent_nnz": int(tangent.nnz),
        "rows": rows,
        "maximum_relative_error": float(maximum_error),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Smooth fixed-active local tangent only; active-set transitions are excluded.",
            "Bounded node-to-triangle penalty contact; no general surface-to-surface claim.",
            "Internal verification only; no external correlation or physical validation claim.",
        ],
    }


def _geometric_contact_model() -> FiniteElementModel:
    """Build a small geometric/contact composition model with fixed master nodes."""

    nodes = [
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.9, -0.5, -0.5],
        [0.9, 0.5, -0.5],
        [0.9, -0.5, 0.5],
        [1.0, 0.5, 0.5],
    ]
    fixed_nodes = (0, 2, 3, 4, 5, 6, 7)
    model = FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"},
            {"type": "TET4", "nodes": [4, 5, 6, 7], "material": "solid"},
        ],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ"]}
            for node in fixed_nodes
        ]
        + [{"node": 1, "dofs": ["UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": -20.0}],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "load_increments": 20,
                "max_iterations": 100,
                "tolerance": 1.0e-8,
                "contact_mode": "penalty",
                "contact_penalty": 1.0e5,
                "contact_search_mode": "initial",
            },
        },
    )
    model.contacts.append(
        FrictionlessContact(name="geometric_master", slave_node=1, master_nodes=(4, 5, 6))
    )
    return model


def run_geometric_contact_benchmark() -> dict[str, Any]:
    """Verify geometric Total-Lagrangian assembly plus common penalty contact."""

    result = solve_model(_geometric_contact_model(), enforce_policy=False)
    solver = result.to_dict()["solver"]
    contact = dict(solver.get("contact", {}))
    steps = solver["increments"]
    gaps = list(contact.get("gaps", []))
    maximum_relative_residual = float(max(step["relative_residual"] for step in steps))
    return {
        "status": (
            "PASS_INTERNAL_RESEARCH"
            if result.status == "success"
            and contact.get("active_contacts")
            and gaps
            and float(gaps[0]) < 0.0
            and float(contact.get("maximum_penetration", float("inf"))) < 1.0e-3
            and float(solver["minimum_det_f"]) > 0.0
            and maximum_relative_residual < 1.0e-7
            else "FAIL"
        ),
        "solver_status": result.status,
        "analysis": result.analysis,
        "element_count": int(result.element_count),
        "dof_count": int(result.displacements.size),
        "contact": contact,
        "maximum_relative_residual": maximum_relative_residual,
        "minimum_det_f": float(solver["minimum_det_f"]),
        "strain_energy": float(solver["strain_energy"]),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two disconnected TET4 blocks with a fixed triangular master patch.",
            "Frictionless node-to-triangle penalty contact only; no surface-to-surface or finite-sliding qualification.",
            "Internal composition evidence only; no external or physical validation claim.",
        ],
    }


def run_contact_recontact_benchmark() -> dict[str, Any]:
    """Exercise open/close/reopen/reclose through one common load path."""

    model = _refinement_model("TET4", 1)
    model.materials["j2"] = {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
    model.loads = [replace(load, value=-5.0) for load in model.loads]
    model.contacts.append(FrictionlessContact(name="plane", slave_node=1, master_nodes=(0, 3, 4)))
    load_path = [0.25, 1.0, 0.0, 1.0]
    model.analysis = replace(
        model.analysis,
        parameters={
            **model.analysis.parameters,
            "load_path": load_path,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e5,
            "contact_search_mode": "initial",
        },
    )
    result = solve_model(model, enforce_policy=False)
    steps = result.to_dict()["solver"]["steps"]
    active = [bool(step["contact_active_contacts"]) for step in steps]
    gaps = [float(step["contact_gaps"][0]) for step in steps]
    expected = [False, True, False, True]
    residuals = [float(step["relative_residual"]) for step in steps]
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS" and active == expected and max(residuals) <= 1.0e-7
        else "FAIL",
        "load_path": load_path,
        "active_by_step": active,
        "expected_active_by_step": expected,
        "gaps_by_step": gaps,
        "maximum_relative_residual": max(residuals),
        "search_mode": "initial",
        "common_driver": True,
        "state_transaction": "no material state; contact active set recomputed per Newton increment",
        "owner_acceptance_band_required": True,
        "limitations": [
            "One elastic TET4 contact path with a fixed planar master triangle.",
            "This verifies common load-path active-set transitions, not finite sliding or friction.",
        ],
    }


def run_contact_penalty_sensitivity_benchmark(
    penalties: tuple[float, ...] = (1.0e2, 1.0e3, 1.0e4, 1.0e5, 1.0e6),
) -> dict[str, Any]:
    """Measure bounded penalty/contact penetration behaviour on one common case.

    This is a conditioning and observability study, not a claim that a
    penalty value is universally acceptable.  The expected internal trend is
    decreasing penetration as the penalty increases while the common Newton
    path remains converged.  The Owner must still define the production
    acceptance band and scaling strategy for contact stiffness.
    """

    if not penalties or any(not np.isfinite(value) or value <= 0.0 for value in penalties):
        raise ValueError("penalties must be a non-empty tuple of finite positive values.")
    ordered = tuple(sorted(float(value) for value in penalties))
    rows: list[dict[str, Any]] = []
    for penalty in ordered:
        model = _refinement_model("TET4", 1)
        model.materials["j2"] = {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}
        model.loads = [replace(load, value=-5.0) for load in model.loads]
        model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
        model.analysis = replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "load_path": [1.0],
                "contact_mode": "penalty",
                "contact_penalty": penalty,
                "contact_search_mode": "initial",
            },
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.to_dict()["solver"]
        step = solver["steps"][-1]
        gap = float(step["contact_gaps"][0])
        rows.append(
            {
                "penalty": penalty,
                "solver_status": result.status,
                "converged": result.status == "PASS",
                "maximum_penetration": max(-gap, 0.0),
                "gap": gap,
                "relative_residual": float(step["relative_residual"]),
                "iterations": int(step["iterations"]),
                "active_contacts": list(step["contact_active_contacts"]),
                "contact_tangent_nnz": int(step.get("contact_tangent_nnz", 0)),
            }
        )
    penetrations = [row["maximum_penetration"] for row in rows]
    trend_ok = all(left >= right for left, right in zip(penetrations, penetrations[1:]))
    converged = all(row["converged"] for row in rows)
    finite = all(np.isfinite(row["relative_residual"]) for row in rows)
    return {
        "status": "PASS_INTERNAL_RESEARCH" if trend_ok and converged and finite else "FAIL",
        "rows": rows,
        "penetration_monotone_nonincreasing": trend_ok,
        "common_driver": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "One TET4 node-to-triangle frictionless penalty case in the initial configuration.",
            "Penalty selection, conditioning and finite-sliding behaviour are not qualified.",
            "No surface-to-surface or external correlation claim is made.",
        ],
    }


def run_contact_surface_search_benchmark() -> dict[str, Any]:
    """Check deterministic selection across a bounded two-face master surface."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.1, 0.5, 0.5],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "linear_static",
            "method": "direct",
            "parameters": {"contact_search_mode": "updated"},
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="two_face_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
        )
    )
    dofs = model.dof_manager()
    face_indices: list[int] = []
    rows: list[dict[str, Any]] = []
    for position in ((0.75, 0.25), (0.25, 0.75)):
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[dofs.index(4, "UY")] = position[0] - 0.5
        displacement[dofs.index(4, "UZ")] = position[1] - 0.5
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e6
        )
        face_indices.append(int(details["master_face_indices"][0]))
        rows.append(
            {
                "position_yz": list(position),
                "master_face_index": int(details["master_face_indices"][0]),
                "master_face_count": int(details["master_face_counts"][0]),
                "gap": float(details["gaps"][0]),
                "active_contacts": list(details["active_contacts"]),
                "tangent_nnz": int(tangent.nnz),
                "internal_norm": float(np.linalg.norm(internal)),
            }
        )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if face_indices == [0, 1]
        and all(row["master_face_count"] == 2 for row in rows)
        and all(not row["active_contacts"] for row in rows)
        else "FAIL",
        "rows": rows,
        "selected_face_indices": face_indices,
        "surface_face_count": 2,
        "common_contact_assembly": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Bounded node-to-triangle master surface with two planar faces.",
            "This observes face selection only; it is not a general surface-to-surface or finite-sliding qualification.",
        ],
    }


def run_contact_updated_sliding_benchmark() -> dict[str, Any]:
    """Exercise a controlled multi-face crossing in the common nonlinear driver.

    The case is intentionally small: two connected TET4 elements provide the
    deformable body, while a fixed two-face master surface constrains one
    loaded node. The tangential load moves the projection from face 0 to face
    1 while the normal load closes the contact. This is bounded internal
    evidence for updated local search, not a general finite-sliding claim.
    """

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.25, 0.5, 0.1],
        ],
        elements=[
            {"type": "TET4", "nodes": [0, 1, 2, 4], "material": "j2"},
            {"type": "TET4", "nodes": [1, 3, 2, 4], "material": "j2"},
        ],
        materials={
            "j2": {
                "type": "von_mises_elastoplastic_3d",
                "E": 10.0,
                "nu": 0.3,
                "yield_stress": 1.0e9,
                "hardening_modulus": 10.0,
            }
        },
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
        loads=[
            {"node": 4, "dof": "UX", "value": 5.0},
            {"node": 4, "dof": "UZ", "value": -5.0},
        ],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "load_path": [0.25, 0.5, 0.75, 1.0],
            "max_iterations": 60,
            "tolerance": 1.0e-8,
            "contact_mode": "penalty",
            "contact_penalty": 1.0e5,
            "contact_search_mode": "updated",
            "contact_search_max_iterations": 20,
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="updated_sliding_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (1, 3, 2)),
        )
    )
    result = solve_model(model, enforce_policy=False)
    solver = result.to_dict()["solver"]
    steps = solver["steps"]
    face_sequence = [list(step.get("contact_master_face_indices", [])) for step in steps]
    gaps = [float(step.get("contact_gaps", [0.0])[0]) for step in steps]
    residuals = [float(step["relative_residual"]) for step in steps]
    expected_faces = [[0], [0], [1], [1]]
    finite = bool(
        all(np.isfinite(value) for value in gaps + residuals)
        and np.all(np.isfinite(result.displacements))
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if result.status == "PASS" and face_sequence == expected_faces and finite
        else "FAIL",
        "solver_status": result.status,
        "common_driver": True,
        "search_mode": "updated",
        "load_path": [0.25, 0.5, 0.75, 1.0],
        "face_sequence": face_sequence,
        "expected_face_sequence": expected_faces,
        "face_switch_count": sum(
            left != right for left, right in zip(face_sequence, face_sequence[1:])
        ),
        "gaps": gaps,
        "maximum_penetration": max(-min(gaps, default=0.0), 0.0),
        "maximum_relative_residual": max(residuals, default=0.0),
        "iterations": int(sum(step["iterations"] for step in steps)),
        "final_slave_displacement": result.displacements[
            [result.dofs.index(4, dof) for dof in ("UX", "UY", "UZ")]
        ].tolist(),
        "owner_acceptance_band_required": True,
        "limitations": [
            "Two connected TET4 elements and one fixed two-face planar master surface.",
            "This verifies a bounded updated local face crossing, not general finite sliding, surface-to-surface contact or external correlation.",
        ],
    }


def run_contact_finite_sliding_benchmark() -> dict[str, Any]:
    """Record the bounded clamped-projection contract on a two-face surface.

    The slave point is deliberately placed just outside each side of a square
    master surface.  The opt-in finite-sliding path must retain the closest
    triangle, mark the projection as clamped, preserve the normal gap and
    assemble a sparse penalty tangent.  This is direct assembly evidence for
    the bounded node-to-triangle approximation; it is not a general contact
    or physical validation claim.
    """

    master_nodes = np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
        dtype=float,
    )
    slave_reference = np.asarray([1.2, 0.25, -0.1], dtype=float)
    model = FiniteElementModel.from_raw(
        nodes=np.vstack([master_nodes, slave_reference]).tolist(),
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {
                "contact_search_mode": "updated",
                "contact_finite_sliding": True,
            },
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="finite_sliding_surface",
            slave_node=4,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
        )
    )
    dofs = model.dof_manager()
    positions = (
        np.asarray([1.2, 0.25, -0.1], dtype=float),
        np.asarray([0.25, 1.2, -0.1], dtype=float),
    )
    rows: list[dict[str, Any]] = []
    for position in positions:
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[[dofs.index(4, dof) for dof in ("UX", "UY", "UZ")]] = position - slave_reference
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e3
        )
        rows.append(
            {
                "position": position.tolist(),
                "master_face_index": int(details["master_face_indices"][0]),
                "projection_clamped": bool(details["projection_clamped"][0]),
                "gap": float(details["gaps"][0]),
                "closest_distance": float(details["closest_distances"][0]),
                "active_contacts": list(details["active_contacts"]),
                "tangent_nnz": int(tangent.nnz),
                "internal_norm": float(np.linalg.norm(internal)),
            }
        )
    faces = [row["master_face_index"] for row in rows]
    status = (
        "PASS_INTERNAL_RESEARCH"
        if faces == [0, 1]
        and all(row["projection_clamped"] for row in rows)
        and all(row["gap"] == -0.1 for row in rows)
        and all(row["active_contacts"] == [0] for row in rows)
        and all(row["tangent_nnz"] > 0 for row in rows)
        and all(np.isfinite(row["closest_distance"]) for row in rows)
        else "FAIL"
    )
    return {
        "status": status,
        "search_mode": "updated",
        "finite_sliding": True,
        "projection_mode": "bounded_closest_point_node_to_triangle",
        "rows": rows,
        "selected_face_indices": faces,
        "face_switch_count": int(faces[0] != faces[1]),
        "common_sparse_assembly": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Opt-in bounded projection on a fixed two-face planar master surface.",
            "No continuous large-sliding, surface-to-surface, friction or external correlation claim.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
