from __future__ import annotations

import hashlib
import argparse
import json
import math
from pathlib import Path

import numpy as np

LIMIT_NM = 0.002
DOFS = ("UX", "UY", "UZ")
SCENARIO = "B_SLIP_R14"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def norm(value) -> float:
    return float(np.linalg.norm(np.asarray(value, dtype=float)))


def cross_moment(points, forces, origin=None):
    points = np.asarray(points, dtype=float)
    forces = np.asarray(forces, dtype=float)
    ref = np.zeros(3) if origin is None else np.asarray(origin, dtype=float)
    return np.sum(np.cross(points - ref, forces), axis=0)


def triangle_geometry(nodes, master, slave):
    coordinates = np.asarray(nodes, dtype=float)
    a, b, c = coordinates[list(master)]
    s = coordinates[slave]
    e1, e2 = b - a, c - a
    cross = np.cross(e1, e2)
    area2 = norm(cross)
    if area2 == 0.0:
        raise ValueError("degenerate master triangle")
    normal = cross / area2
    d00, d01, d11 = float(e1 @ e1), float(e1 @ e2), float(e2 @ e2)
    v = s - a
    d20, d21 = float(v @ e1), float(v @ e2)
    denominator = d00 * d11 - d01 * d01
    beta1 = (d11 * d20 - d01 * d21) / denominator
    beta2 = (d00 * d21 - d01 * d20) / denominator
    beta = np.array([1.0 - beta1 - beta2, beta1, beta2])
    g1 = np.cross(e2, normal) / area2
    g2 = np.cross(normal, e1) / area2
    gradients = np.array([-g1 - g2, g1, g2])
    gap = float(normal @ (s - beta @ coordinates[list(master)]))
    return normal, beta, gradients, gap


def event_rows(result):
    return [json.loads(line) for line in result.get("telemetry_events", [])]


def dof_map(result):
    return {(int(row["node"]), str(row["dof"])): int(row["index"])
            for row in result["dof_labels"]}


def reconstruct_trial_margin(
    operator: np.ndarray,
    displacement: np.ndarray,
    previous_reference: np.ndarray,
    tangential_stiffness: float,
    pressure: float,
    friction_coefficient: float,
) -> tuple[np.ndarray, float, float]:
    """Reconstruct the elastic Coulomb trial from the archived B* state.

    The event stream omits this trial on the accepted slip branch. ``pressure``
    is the accepted normal multiplier, and the reference is the last committed
    slip reference; this helper does not infer either missing quantity.
    """
    basis = np.asarray(operator, dtype=float)
    values = np.asarray(displacement, dtype=float).reshape(-1)
    reference = np.asarray(previous_reference, dtype=float).reshape(-1)
    if basis.ndim != 2 or basis.shape[0] != 2 or basis.shape[1] != values.size:
        raise ValueError("B* operator must have shape (2, ndof) matching displacement")
    if reference.shape != (2,):
        raise ValueError("previous committed slip reference must have two local components")
    scalars = np.asarray([tangential_stiffness, pressure, friction_coefficient], dtype=float)
    if not np.all(np.isfinite(basis)) or not np.all(np.isfinite(values)) \
            or not np.all(np.isfinite(reference)) or not np.all(np.isfinite(scalars)):
        raise ValueError("trial-margin reconstruction inputs must be finite")
    if tangential_stiffness <= 0.0 or pressure < 0.0 or friction_coefficient < 0.0:
        raise ValueError("stiffness must be positive; pressure and friction must be nonnegative")
    trial = tangential_stiffness * (basis @ values - reference)
    capacity = friction_coefficient * pressure
    return trial, float(np.linalg.norm(trial)), float(np.linalg.norm(trial) - capacity)


def independent_contact(result, raw):
    nodes = np.asarray(raw["nodes"], dtype=float)
    master = raw["contacts"][0]["master_nodes"]
    slave = raw["contacts"][0]["slave_node"]
    normal, beta, gradients, gap = triangle_geometry(nodes, master, slave)
    contact = result["contact"]["contacts"][0]
    pressure = float(contact["pressure"])
    tangent_one = np.asarray(contact["tangent_one"], dtype=float)
    tangent_two = np.asarray(contact["tangent_two"], dtype=float)
    ft_local = np.asarray(contact.get("tangential_force", [0.0, 0.0]), dtype=float)
    ft_world = ft_local[0] * tangent_one + ft_local[1] * tangent_two
    labels = dof_map(result)
    ndof = len(result["displacements_m"])
    B = np.zeros((2, ndof), dtype=float)
    for axis, tangent in enumerate((tangent_one, tangent_two)):
        for component, dof in enumerate(DOFS):
            B[axis, labels[(slave, dof)]] += tangent[component]
        for j, node in enumerate(master):
            coefficient = -beta[j] * tangent + gap * float(gradients[j] @ tangent) * normal
            for component, dof in enumerate(DOFS):
                B[axis, labels[(node, dof)]] += coefficient[component]
    generalized = np.zeros((len(nodes), 3), dtype=float)
    generalized[slave] -= pressure * normal
    for j, node in enumerate(master):
        generalized[node] += beta[j] * pressure * normal
    tangential_generalized = B.T @ ft_local
    for node in range(len(nodes)):
        for component, dof in enumerate(DOFS):
            generalized[node, component] += tangential_generalized[labels[(node, dof)]]
    direction = np.sin(np.arange(ndof, dtype=float) + 0.37)
    virtual_work_local = float(ft_local @ (B @ direction))
    virtual_work_nodal = float(tangential_generalized @ direction)
    work_error = abs(virtual_work_local - virtual_work_nodal)
    work_relative = work_error / max(abs(virtual_work_local), abs(virtual_work_nodal), 1.0)
    return {
        "reference_normal": normal.tolist(), "reference_barycentric": beta.tolist(),
        "reference_gap_m": gap, "pressure_N": pressure,
        "friction_coefficient": float(contact["friction_coefficient"]),
        "coulomb_capacity_N": float(contact["friction_coefficient"]) * pressure,
        "accepted_tangential_force_local_N": ft_local.tolist(),
        "accepted_tangential_force_world_N": ft_world.tolist(),
        "accepted_tangential_force_norm_N": norm(ft_local),
        "accepted_state": contact.get("tangential_state"),
        "accepted_contact_active": bool(contact.get("active")),
        "generalized_contact_forces_N_by_node": generalized.tolist(),
        "contact_force_resultant_N": np.sum(generalized, axis=0).tolist(),
        "contact_force_resultant_norm_N": norm(np.sum(generalized, axis=0)),
        "contact_moment_about_origin_Nm": cross_moment(nodes, generalized).tolist(),
        "contact_moment_norm_Nm": norm(cross_moment(nodes, generalized)),
        "virtual_work_local_Nm": virtual_work_local,
        "virtual_work_nodal_Nm": virtual_work_nodal,
        "virtual_work_absolute_difference_Nm": work_error,
        "virtual_work_relative_difference": work_relative,
        "virtual_work_check": "B* work-conjugate identity evaluated independently from frozen geometry and archived force",
    }


def global_balance(result, raw, contact):
    nodes = np.asarray(raw["nodes"], dtype=float)
    displacement = np.asarray(result["displacements_m"], dtype=float)
    labels = dof_map(result)
    forces = np.zeros((len(nodes), 3), dtype=float)
    final_factors = raw["analysis"]["contact_load_history"][-1]
    for factor, load in zip(final_factors, raw["loads"]):
        forces[int(load["node"]), DOFS.index(load["dof"])] += float(factor) * float(load["value"])
    eq = result["audit"]["equilibrium"]
    fixed_reactions = eq.get("reactions")
    if fixed_reactions is None:
        raise ValueError("fixed reactions unavailable; global balance cannot be verified")
    for row in fixed_reactions:
        forces[int(row["node"]), DOFS.index(row["dof"])] += float(row["value"])
    spring_reactions = {}
    for spring in raw.get("springs", []):
        node = int(spring["node_a"])
        names = spring["dofs"]
        for dof, stiffness in zip(names, spring["stiffness"]):
            value = -float(stiffness) * displacement[labels[(node, dof)]]
            forces[node, DOFS.index(dof)] += value
            spring_reactions.setdefault(str(node), {})[dof] = value
    external_support_force = np.sum(forces, axis=0)
    external_support_moment = cross_moment(nodes, forces)
    contact_force = np.asarray(contact["contact_force_resultant_N"], dtype=float)
    contact_moment = np.asarray(contact["contact_moment_about_origin_Nm"], dtype=float)
    total_force = external_support_force + contact_force
    total_moment = external_support_moment + contact_moment
    raw_force = np.asarray(eq.get("force_imbalance"), dtype=float)
    raw_moment_value = eq.get("raw_moment_imbalance_about_origin", eq.get("moment_imbalance_about_origin"))
    if raw_moment_value is None:
        raise ValueError("raw global moment unavailable")
    raw_moment = np.asarray(raw_moment_value, dtype=float)
    correction = eq.get("contact_reference_moment_correction")
    if correction is None:
        correction = [None, None, None]
    correction_norm = None if any(value is None for value in correction) else norm(correction)
    return {
        "moment_reference": "common reference origin [0,0,0] m",
        "external_plus_fixed_and_spring_force_resultant_N": external_support_force.tolist(),
        "independent_contact_force_resultant_N": contact_force.tolist(),
        "combined_independent_force_resultant_N": total_force.tolist(),
        "combined_independent_force_resultant_norm_N": norm(total_force),
        "solver_force_imbalance_N": raw_force.tolist(),
        "external_plus_fixed_and_spring_moment_Nm": external_support_moment.tolist(),
        "independent_contact_moment_Nm": contact_moment.tolist(),
        "combined_independent_moment_Nm": total_moment.tolist(),
        "combined_independent_moment_norm_Nm": norm(total_moment),
        "solver_raw_moment_imbalance_Nm": raw_moment.tolist(),
        "solver_raw_moment_norm_Nm": norm(raw_moment),
        "raw_moment_limit_Nm": LIMIT_NM,
        "raw_moment_limit_pass": bool(norm(raw_moment) <= LIMIT_NM),
        "postprocess_moment_correction_Nm": correction,
        "postprocess_correction_norm_Nm": correction_norm,
        "fixed_reactions": fixed_reactions,
        "spring_reactions_N": spring_reactions,
        "solver_force_balance_relative_error": eq.get("force_balance_relative_error"),
        "solver_moment_balance_relative_error": eq.get("moment_balance_relative_error"),
        "solver_free_residual_norm": eq.get("free_residual_norm"),
        "solver_free_relative_residual": eq.get("free_relative_residual"),
    }


def checkpoint_diagnostics(result, raw):
    events = event_rows(result)
    accepted = [event for event in events if event.get("event_type") == "STEP_ACCEPTED"
                and event.get("status") == "ACCEPTED"
                and event.get("metrics", {}).get("accepted") is True]
    rejected = [event for event in events if "REJECT" in str(event.get("event_type", ""))]
    contact_events = [event for event in events if event.get("event_type") == "CONTACT_STATE"]
    rows = []
    nodes = np.asarray(raw["nodes"], dtype=float)
    master = raw["contacts"][0]["master_nodes"]
    slave = raw["contacts"][0]["slave_node"]
    contact = result["contact"]["contacts"][0]
    normal, beta, gradients, gap = triangle_geometry(nodes, master, slave)
    t1 = np.asarray(contact["tangent_one"], dtype=float)
    t2 = np.asarray(contact["tangent_two"], dtype=float)
    ndof = len(result["displacements_m"])
    labels = dof_map(result)
    B = np.zeros((2, ndof), dtype=float)
    for axis, tangent in enumerate((t1, t2)):
        for component, dof in enumerate(DOFS):
            B[axis, labels[(slave, dof)]] += tangent[component]
        for j, node in enumerate(master):
            coefficient = -beta[j] * tangent + gap * float(gradients[j] @ tangent) * normal
            for component, dof in enumerate(DOFS):
                B[axis, labels[(node, dof)]] += coefficient[component]
    tangent_stiffness = float(raw["contacts"][0]["tangential_stiffness"])
    previous_reference = np.zeros(2, dtype=float)
    load_steps = {int(row["step"]): row for row in result.get("contact", {}).get("load_steps", [])}
    for event in accepted:
        metrics = event.get("metrics", {})
        state = metrics.get("committed_contact_state") or {}
        step = int(state.get("step", event.get("step", -1)))
        states = state.get("tangential_states") or []
        pressures = state.get("pressures") or []
        tangential_forces = state.get("tangential_forces") or []
        slip_refs = state.get("slip_references") or []
        active = state.get("active_contacts") or []
        matching = [row for row in contact_events if int(row.get("step", -2)) == step]
        final_contact_event = None
        for row in matching:
            cm = row.get("metrics", {})
            if cm.get("fixed_point_converged") and cm.get("coulomb_trial_margins") is not None:
                final_contact_event = row
        cm = final_contact_event.get("metrics", {}) if final_contact_event else {}
        margins = cm.get("coulomb_trial_margins") or []
        contact_index = 0
        state_name = states[contact_index] if len(states) > contact_index else None
        pressure = float(pressures[contact_index]) if len(pressures) > contact_index else None
        capacity = float(raw["contacts"][0]["friction_coefficient"]) * pressure if pressure is not None else None
        displacement = np.asarray(state.get("displacement", []), dtype=float)
        current_reference = np.asarray(slip_refs[contact_index], dtype=float) if len(slip_refs) > contact_index else None
        trial = trial_norm = computed_margin = None
        if displacement.size == ndof and pressure is not None:
            trial, trial_norm, computed_margin = reconstruct_trial_margin(
                B, displacement, previous_reference, tangent_stiffness, pressure,
                float(raw["contacts"][0]["friction_coefficient"]),
            )
        reported = margins[contact_index] if len(margins) > contact_index else None
        if isinstance(reported, dict):
            reported_value = reported.get("value")
            margin_reason = reported.get("reason")
        else:
            reported_value = reported
            margin_reason = "NUMERIC" if reported is not None else "NOT_RECORDED"
        accepted_force = tangential_forces[contact_index] if len(tangential_forces) > contact_index else None
        load_step = load_steps.get(step, {})
        if reported_value is None and computed_margin is not None:
            margin_source = "independently reconstructed from accepted displacement, prior committed slip reference, k_t, and accepted pressure; slip-branch trial margin is not emitted in CONTACT_STATE telemetry"
        else:
            margin_source = "CONTACT_STATE telemetry, independently cross-checked from accepted state"
        current_reference_change = (norm(current_reference - previous_reference)
                                    if current_reference is not None else None)
        rows.append({
            "step": step, "sequence_number": event.get("sequence_number"),
            "accepted": True, "load_factors": raw["analysis"]["contact_load_history"][step - 1]
                if 0 < step <= len(raw["analysis"]["contact_load_history"]) else None,
            "active_contact": contact_index in active,
            "state": state_name, "pressure_N": pressure,
            "mu_p_capacity_N": capacity,
            "trial_tangential_force_N_components": trial.tolist() if trial is not None else None,
            "trial_tangential_force_norm_N": trial_norm,
            "reported_coulomb_trial_margin_N": reported_value,
            "reported_margin_reason": margin_reason,
            "independently_recomputed_trial_margin_N": computed_margin,
            "margin_source": margin_source,
            "reported_minus_recomputed_margin_N": (float(reported_value) - computed_margin)
                if isinstance(reported_value, (int, float)) and computed_margin is not None else None,
            "accepted_return_map_force_N_components": accepted_force,
            "accepted_return_map_force_norm_N": norm(accepted_force) if accepted_force is not None else None,
            "slip_reference": slip_refs[contact_index] if len(slip_refs) > contact_index else None,
            "slip_reference_change_magnitude": current_reference_change,
            "dissipation_increment_J": load_step.get("local_dissipation_increment"),
            "iterations": metrics.get("active_set_iterations"),
            "contact_transition_cause": cm.get("convergence_cause"),
            "contact_state_event_sequence": final_contact_event.get("sequence_number")
                if final_contact_event else None,
            "accepted_checkpoint": state,
        })
        if current_reference is not None:
            previous_reference = current_reference.copy()
    return {"accepted_checkpoints": rows, "accepted_checkpoint_count": len(accepted),
            "rejected_step_events": [{"event_type": row.get("event_type"),
                "sequence_number": row.get("sequence_number"), "step": row.get("step"),
                "status": row.get("status"), "metrics": row.get("metrics")}
                for row in rejected],
            "rejected_step_event_count": len(rejected),
            "all_telemetry_event_count": len(events),
            "event_types": sorted({str(row.get("event_type")) for row in events})}


def kinematics(result, raw):
    reference = np.asarray(raw["nodes"], dtype=float)
    displacement = np.asarray(result["displacements_m"], dtype=float)
    current = reference + displacement.reshape((-1, 3))
    rotations = []
    strains = []
    for index, element in enumerate(raw["elements"]):
        nodes = list(element["nodes"])
        x0 = reference[nodes]
        x1 = current[nodes]
        ref_edges = np.column_stack((x0[1] - x0[0], x0[2] - x0[0], x0[3] - x0[0]))
        cur_edges = np.column_stack((x1[1] - x1[0], x1[2] - x1[0], x1[3] - x1[0]))
        deformation = cur_edges @ np.linalg.inv(ref_edges)
        left, _, right = np.linalg.svd(deformation)
        rotation = left @ right
        if np.linalg.det(rotation) < 0:
            left[:, -1] *= -1
            rotation = left @ right
        angle = math.acos(float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0)))
        strain = 0.5 * (deformation + deformation.T) - np.eye(3)
        rotations.append({"element_index": index, "nodes": nodes,
                          "polar_rotation_rad": angle,
                          "max_abs_linear_strain_principal": float(np.max(np.abs(np.linalg.eigvalsh(strain))))})
        strains.append(strain)
    contact = result["contact"]["contacts"][0]
    master = raw["contacts"][0]["master_nodes"]
    slave = raw["contacts"][0]["slave_node"]
    _, deformed_beta, _, deformed_gap = triangle_geometry(current, master, slave)
    ref_beta = np.asarray(contact["master_barycentric"], dtype=float)
    relative = displacement.reshape((-1, 3))[slave] - ref_beta @ displacement.reshape((-1, 3))[master]
    t1, t2 = np.asarray(contact["tangent_one"], dtype=float), np.asarray(contact["tangent_two"], dtype=float)
    relative_tangent = [float(t1 @ relative), float(t2 @ relative)]
    return {
        "max_nodal_displacement_m": float(np.max(np.linalg.norm(displacement.reshape((-1, 3)), axis=1))),
        "master_element_polar_rotation_rad": rotations[0]["polar_rotation_rad"],
        "slave_element_polar_rotation_rad": rotations[1]["polar_rotation_rad"],
        "element_polar_rotations": rotations,
        "contact_relative_tangential_displacement_m": relative_tangent,
        "solver_reported_tangential_displacement_m": contact.get("tangential_displacement"),
        "deformed_master_projection_barycentric": deformed_beta.tolist(),
        "deformed_geometric_gap_m": deformed_gap,
        "frozen_initial_pair": [master, slave],
        "finite_sliding": raw["analysis"]["contact_finite_sliding"],
        "kinematic_scope": "small rotations; initial master-slave pair and projection frozen",
    }


def analyze(archive: Path, output: Path | None = None):
    archive = archive.resolve()
    output = (output or archive / "independent_reanalysis_corrected.json").resolve()
    protected = {
        (archive / "manifest.json").resolve(),
        (archive / "manifest.sha256").resolve(),
        (archive / "independent_postprocess.json").resolve(),
        (archive / "independent_reanalysis.json").resolve(),
        (archive / "campaign_receipt.json").resolve(),
        (archive / "runs" / SCENARIO / "solver_result.json").resolve(),
        (archive / "inputs" / "scenario_B_R14_slip.json").resolve(),
    }
    if output in protected:
        raise ValueError("supplemental output must not overwrite an archive or historical verdict")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing supplemental output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = archive / "manifest.json"
    digest = (archive / "manifest.sha256").read_text(encoding="ascii").split()[0]
    if sha(manifest_path) != digest:
        raise RuntimeError("execution manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out = archive / "runs" / SCENARIO
    result_path = out / "solver_result.json"
    if not result_path.is_file():
        receipt = json.loads((archive / "campaign_receipt.json").read_text(encoding="utf-8"))
        summary = receipt["scenario_attempts"][0]
        verdict = "B_STAR_RESOURCE_LIMIT_REACHED" if summary.get("budget_incident") else "B_STAR_SLIP_FAILED"
        write_json(output, {
            "record_type": "WP-C01-R14-POST-RUN-REANALYSIS",
            "campaign_id": manifest["campaign_id"], "manifest_sha256": digest,
            "scenario_status": "NO_SOLVER_RESULT", "preliminary_verdict": verdict,
            "reason": "No solver result was produced; see resource summary and captured logs.",
            "reanalysis_note": "Supplemental post-run analysis; execution manifest and original run outputs are preserved.",
        })
        print(verdict)
        return
    result = json.loads(result_path.read_text(encoding="utf-8"))
    raw = json.loads((archive / "inputs" / "scenario_B_R14_slip.json").read_text(encoding="utf-8"))
    if result.get("manifest_sha256") != digest or result.get("campaign_id") != manifest["campaign_id"]:
        raise RuntimeError("solver result is not bound to the consumed manifest")
    checkpoints = checkpoint_diagnostics(result, raw)
    contact = independent_contact(result, raw)
    balance = global_balance(result, raw, contact)
    motion = kinematics(result, raw)
    slip_steps = [row for row in checkpoints["accepted_checkpoints"]
                  if row.get("accepted") and row.get("active_contact")
                  and row.get("state") == "slip" and row.get("pressure_N") is not None
                  and row["pressure_N"] > 0.0]
    all_margins_present = all(row["independently_recomputed_trial_margin_N"] is not None
                              for row in checkpoints["accepted_checkpoints"]
                              if row.get("active_contact"))
    correction = balance.get("postprocess_moment_correction_Nm")
    correction_zero = correction is not None and all(value is not None for value in correction) \
        and np.allclose(np.asarray(correction, dtype=float), 0.0, atol=0.0, rtol=0.0)
    solver_pass = str(result.get("status", "")).upper() == "PASS"
    raw_moment_pass = balance["raw_moment_limit_pass"]
    work_pass = contact["virtual_work_relative_difference"] <= 1e-12
    protocol_integrity = (checkpoints["accepted_checkpoint_count"] > 0 and all_margins_present
                          and correction_zero)
    if not solver_pass:
        verdict = "B_STAR_SLIP_FAILED"
    elif not slip_steps:
        verdict = "B_STAR_SLIP_NOT_REACHED"
    elif not protocol_integrity or not raw_moment_pass or not work_pass:
        verdict = "B_STAR_SLIP_FAILED"
    else:
        verdict = "B_STAR_STICK_SLIP_VALIDATED_EXPLORATORY"
    report = {
        "record_type": "WP-C01-R14-POST-RUN-REANALYSIS",
        "campaign_id": manifest["campaign_id"], "scenario_id": SCENARIO,
        "manifest_sha256": digest, "solver_result_sha256": sha(result_path),
        "solver_status": result.get("status"), "solver_message": result.get("message"),
        "independent_method": "reconstruct force/moment resultants and B* work pairing from frozen input, archived nodal displacements, reactions, springs, contact force, and telemetry; no solver correction applied",
        "checkpoints": checkpoints, "accepted_slip_checkpoints": slip_steps,
        "accepted_slip_checkpoint_count": len(slip_steps),
        "all_active_checkpoint_margins_reconstructable": all_margins_present,
        "independent_contact": contact, "global_balance": balance,
        "kinematics": motion,
        "contact_load_steps": result.get("contact", {}).get("load_steps", []),
        "contact_convergence": result.get("contact", {}).get("convergence", {}),
        "contact_cumulative_local_dissipation_J": result.get("contact", {}).get("cumulative_local_dissipation"),
        "contact_slip_references_final": result.get("contact", {}).get("slip_references"),
        "protocol_integrity_check": protocol_integrity,
        "raw_moment_limit_pass": raw_moment_pass,
        "virtual_work_check_pass": work_pass,
        "postprocess_moment_correction_zero": correction_zero,
        "slip_tangent_status": "Global consistent tangent in slip remains unestablished.",
        "scope_limit": "One frozen master-triangle/slave-node pair, small rotations, finite_sliding=false; no finite-sliding or physical qualification claim.",
        "reanalysis_note": "Supplemental post-run reconstruction; the manifest-bound original postprocess result is preserved unchanged.",
        "superseded_initial_postprocess_sha256": sha(archive / "independent_postprocess.json"),
        "correction_note": "The initial manifest-bound postprocessor read contact_reference_moment_correction and free residuals from the wrong audit nesting and required CONTACT_STATE margins even when slip-branch trial margins were not emitted. This report reads those audit fields at equilibrium and independently reconstructs slip trial margins from accepted displacement, the previous accepted slip reference, k_t, and accepted pressure.",
        "preliminary_verdict": verdict,
    }
    write_json(output, report)
    print(verdict)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Supplemental, non-destructive R14 B* post-run analysis.")
    parser.add_argument("--archive", type=Path, required=True, help="R14 archive directory (read-only input)")
    parser.add_argument("--output", type=Path, help="new output path; defaults to archive/independent_reanalysis_corrected.json")
    arguments = parser.parse_args()
    analyze(arguments.archive, arguments.output)
