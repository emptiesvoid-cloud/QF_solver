# ruff: noqa: F401, F403, F405

"""Extended contact robustness evidence helpers."""

from __future__ import annotations

from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.verification.robustness_support import *  # noqa: F401,F403


def run_contact_surface_patch_benchmark() -> dict[str, Any]:
    """Exercise a stateless multi-node slave patch on a faceted surface."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.25, 0.25, -0.1],
            [0.25, 0.75, -0.1],
        ],
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
            name="slave_patch",
            slave_node=4,
            slave_patch_nodes=(4, 5),
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (0, 2, 3)),
        )
    )
    dofs = model.dof_manager()
    internal, tangent, details = assemble_penalty_contact(
        model, dofs, np.zeros(dofs.ndof), penalty=1.0e3
    )
    selected = [int(index) for index in details["master_face_indices"]]
    active = [int(index) for index in details["active_contacts"]]
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if selected == [0, 1]
        and active == [0, 1]
        and details["slave_surface_mode"] == "node_patch_to_faceted_surface"
        and int(details["slave_node_count"]) == 2
        and tangent.nnz > 0
        and np.all(np.isfinite(internal))
        else "FAIL",
        "slave_surface_mode": details["slave_surface_mode"],
        "slave_node_count": int(details["slave_node_count"]),
        "master_face_count": int(details["master_face_counts"][0]),
        "selected_face_indices": selected,
        "active_contacts": active,
        "gaps": [float(gap) for gap in details["gaps"]],
        "tangent_nnz": int(tangent.nnz),
        "common_sparse_assembly": True,
        "state_transaction": "stateless contact operators; caller owns trial/committed displacement",
        "owner_acceptance_band_required": True,
        "limitations": [
            "Each slave patch node contributes one node-to-faceted-surface point constraint.",
            "This is not a mortar or segment-to-segment formulation and is not externally correlated here.",
        ],
    }


def run_contact_three_facet_sliding_benchmark() -> dict[str, Any]:
    """Exercise updated search across three connected master facets."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [2.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [3.0, 0.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.25, 0.25, -0.1],
        ],
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
    faces = ((0, 1, 2), (1, 3, 4), (3, 5, 6))
    model.contacts.append(
        FrictionlessContact(
            name="three_facet_surface",
            slave_node=7,
            master_nodes=faces[0],
            master_faces=faces,
        )
    )
    dofs = model.dof_manager()
    reference = np.asarray(model.nodes[7], dtype=float)
    positions = (
        np.asarray([0.25, 0.25, -0.1], dtype=float),
        np.asarray([1.25, 0.25, -0.1], dtype=float),
        np.asarray([2.25, 0.25, -0.1], dtype=float),
    )
    rows: list[dict[str, Any]] = []
    for position in positions:
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[[dofs.index(7, dof) for dof in ("UX", "UY", "UZ")]] = position - reference
        internal, tangent, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e3
        )
        rows.append(
            {
                "position": position.tolist(),
                "master_face_index": int(details["master_face_indices"][0]),
                "gap": float(details["gaps"][0]),
                "active_contacts": list(details["active_contacts"]),
                "projection_clamped": bool(details["projection_clamped"][0]),
                "tangent_nnz": int(tangent.nnz),
                "internal_norm": float(np.linalg.norm(internal)),
            }
        )
    selected = [int(row["master_face_index"]) for row in rows]
    return {
        "status": "PASS_INTERNAL_RESEARCH"
        if selected == [0, 1, 2]
        and all(row["active_contacts"] == [0] for row in rows)
        and all(abs(float(row["gap"]) + 0.1) <= 1.0e-12 for row in rows)
        and all(not row["projection_clamped"] for row in rows)
        and all(int(row["tangent_nnz"]) > 0 for row in rows)
        else "FAIL",
        "search_mode": "updated",
        "finite_sliding": True,
        "surface_mode": "single_node_to_three_facet_surface",
        "facet_count": len(faces),
        "rows": rows,
        "selected_face_indices": selected,
        "face_switch_count": sum(left != right for left, right in zip(selected, selected[1:])),
        "common_sparse_assembly": True,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Internal planar three-facet node-to-surface traversal only.",
            "No mortar, segment-to-segment or external correlation claim.",
        ],
    }


def run_contact_facet_transition_rollback_benchmark() -> dict[str, Any]:
    """Verify that a failed facet transition leaves no hidden contact state."""

    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [2.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [3.0, 0.0, 0.0],
            [2.0, 1.0, 0.0],
            [0.25, 0.25, -0.1],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        analysis={
            "type": "nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_search_mode": "updated", "contact_finite_sliding": True},
        },
    )
    model.contacts.append(
        FrictionlessContact(
            name="rollback_surface",
            slave_node=7,
            master_nodes=(0, 1, 2),
            master_faces=((0, 1, 2), (1, 3, 4), (3, 5, 6)),
        )
    )
    dofs = model.dof_manager()
    reference = np.asarray(model.nodes[7], dtype=float)

    def trial_at(position: tuple[float, float, float]) -> tuple[np.ndarray, dict[str, object]]:
        displacement = np.zeros(dofs.ndof, dtype=float)
        displacement[[dofs.index(7, dof) for dof in ("UX", "UY", "UZ")]] = (
            np.asarray(position, dtype=float) - reference
        )
        internal, _, details = assemble_penalty_contact(
            model, dofs, displacement, penalty=1.0e3
        )
        return internal, details

    committed, committed_details = trial_at((1.25, 0.25, -0.1))
    trial, trial_details = trial_at((2.25, 0.25, -0.1))
    failure_reason = NonlinearFailureReason.CONTACT_UPDATE_FAILURE.value
    rollback, rollback_details = trial_at((1.25, 0.25, -0.1))
    retry, retry_details = trial_at((2.25, 0.25, -0.1))
    clean_retry = bool(
        np.array_equal(committed, rollback)
        and np.array_equal(trial, retry)
        and committed_details["master_face_indices"] == rollback_details["master_face_indices"]
        and trial_details["master_face_indices"] == retry_details["master_face_indices"]
    )
    return {
        "status": "PASS_INTERNAL_RESEARCH" if clean_retry else "FAIL",
        "failure_reason": failure_reason,
        "committed_face": int(committed_details["master_face_indices"][0]),
        "failed_trial_face": int(trial_details["master_face_indices"][0]),
        "rollback_face": int(rollback_details["master_face_indices"][0]),
        "retry_face": int(retry_details["master_face_indices"][0]),
        "facet_transition_observed": int(trial_details["master_face_indices"][0])
        != int(committed_details["master_face_indices"][0]),
        "clean_retry": clean_retry,
        "state_transaction": "contact geometry is recomputed from trial displacement; no contact state is committed",
        "owner_acceptance_band_required": True,
        "limitations": [
            "The failure is a controlled transaction replay at the contact assembly boundary.",
            "No external solver correlation or general surface-to-surface claim is made.",
        ],
    }

__all__ = [
    "run_contact_surface_patch_benchmark",
    "run_contact_three_facet_sliding_benchmark",
    "run_contact_facet_transition_rollback_benchmark",
]
