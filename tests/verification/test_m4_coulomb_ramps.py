"""Instrumented R10 M4 Coulomb ramps; intended for the registered runner only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import psutil
import pytest

from research.contact_r10_r16.m4_stick_capture import validate_capture_archive


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "research/contact_r10_r16"
STATE_CODE = {"open": 0, "stick": 1, "slip": 2, "frictionless": 3}


def _digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.ascontiguousarray(value)
        digest.update(str((array.dtype.str, array.shape)).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contact_observations(
    operators,
    active,
    displacement,
    pressures,
    slip_references,
    states,
    forces,
    relative_displacements,
    *,
    configured_friction_tolerance: float,
):
    rows = []
    active_set = set(active)
    for index, operator in enumerate(operators):
        trial = operator.tangential_stiffness * (
            relative_displacements[index] - slip_references[index]
        )
        trial_norm = float(np.linalg.norm(trial))
        limit = operator.friction_coefficient * max(float(pressures[index]), 0.0)
        rows.append(
            {
                "operator_index": index,
                "slave_node": int(operator.slave_node),
                "active": index in active_set,
                "state": str(states[index]),
                "gap_m": float(operator.gap(displacement)),
                "initial_gap_m": float(operator.initial_gap),
                "normal": operator.normal.tolist(),
                "normal_multiplier_N": float(pressures[index]),
                "friction_coefficient": float(operator.friction_coefficient),
                "coulomb_capacity_N": float(limit),
                "tangent_one": operator.tangents[0].tolist(),
                "tangent_two": operator.tangents[1].tolist(),
                "tangential_displacement_m": relative_displacements[index].tolist(),
                "slip_reference_in_m": slip_references[index].tolist(),
                "trial_tangential_force_N": trial.tolist(),
                "trial_tangential_force_norm_N": trial_norm,
                "returned_tangential_force_N": forces[index].tolist(),
                "returned_tangential_force_norm_N": float(np.linalg.norm(forces[index])),
                "coulomb_margin_N": float(trial_norm - limit),
                "gap_tolerance_m": float(operator.tolerance),
                "classifier_force_band_N": float(configured_friction_tolerance * max(limit, 1.0) if limit else 0.0),
                "configured_contact_friction_tolerance": float(configured_friction_tolerance),
                "effective_tangential_stiffness_N_per_m": float(operator.tangential_stiffness),
                "friction_limit_if_stick_N": float(limit),
                "normal_contact_force_global_N": (operator.normal * float(pressures[index])).tolist(),
                "tangential_contact_force_global_N": (
                    -forces[index, 0] * operator.tangents[0]
                    - forces[index, 1] * operator.tangents[1]
                ).tolist(),
            }
        )
    return rows


def _write_capture_archive(output: Path, model, fields, contract, contract_sha256: str):
    node_count = len(model.nodes)
    contact_count = len(model.contacts[0].slave_patch_nodes)
    element_connectivity = np.asarray([element.nodes for element in model.elements], dtype=np.int64)
    dof_map = np.asarray(fields["dof_map"], dtype=np.int64)
    operator_rows = fields["contact_descriptor_rows"]
    dof_count = 3 * node_count
    step_count = len(fields["displacements"])

    def stack_or_shape(key: str, shape: tuple[int, ...], dtype=None):
        values = fields[key]
        if values:
            return np.asarray(values, dtype=dtype)
        return np.empty(shape, dtype=dtype or float)

    archive_path = output / "m4-stick-fields.npz"
    arrays = {
        "nodes": np.asarray(model.nodes, dtype=float),
        "tet4_connectivity": element_connectivity,
        "displacements": stack_or_shape("displacements", (0, dof_count)),
        "loads": stack_or_shape("loads", (0, dof_count)),
        "fixed_dof_indices": np.asarray(fields.get("fixed_dof_indices", ()), dtype=np.int64),
        "dof_map": dof_map,
        "contact_slave_nodes": np.asarray([row["slave_node"] for row in operator_rows], dtype=np.int64),
        "contact_normals": np.asarray([row["normal"] for row in operator_rows], dtype=float),
        "contact_tangents": np.asarray(
            [[row["tangent_one"], row["tangent_two"]] for row in operator_rows], dtype=float
        ),
        "contact_pressures": stack_or_shape("contact_pressures", (0, contact_count)),
        "contact_gaps": stack_or_shape("contact_gaps", (0, contact_count)),
        "contact_active": stack_or_shape("contact_active", (0, contact_count), dtype=bool),
        "contact_states": stack_or_shape("contact_states", (0, contact_count), dtype=np.int8),
        "slip_references_in": stack_or_shape("slip_references_in", (0, contact_count, 2)),
        "slip_references_out": stack_or_shape("slip_references_out", (0, contact_count, 2)),
        "tangential_displacements": stack_or_shape("tangential_displacements", (0, contact_count, 2)),
        "trial_tangential_forces": stack_or_shape("trial_tangential_forces", (0, contact_count, 2)),
        "tangential_forces": stack_or_shape("tangential_forces", (0, contact_count, 2)),
        "friction_capacities": stack_or_shape("friction_capacities", (0, contact_count)),
        "coulomb_margins": stack_or_shape("coulomb_margins", (0, contact_count)),
        "gap_tolerances": np.asarray([row["gap_tolerance_m"] for row in operator_rows], dtype=float),
        "tangent_stiffnesses": np.asarray(
            [row["effective_tangential_stiffness_N_per_m"] for row in operator_rows], dtype=float
        ),
    }
    with archive_path.open("xb") as stream:
        np.savez_compressed(stream, **arrays)

    descriptor = {
        "schema": "qf.m4-stick-diagnostic-capture.v1",
        "nodeid": contract["nodeid"],
        "scope": contract["scope"],
        "source_commit": contract["source"]["product_source_commit"],
        "source_tree": contract["source"]["solver_src_tree"],
        "contract_sha256": contract_sha256,
        "archive_sha256": _sha256(archive_path),
        "captured_steps": step_count,
        "contact_count": contact_count,
        "node_count": node_count,
        "element_count": len(element_connectivity),
        "fixed_dof_count": len(fields.get("fixed_dof_indices", ())),
        "field_units": {
            "nodes": "m",
            "displacements": "m",
            "loads": "N",
            "contact_pressures": "N normal multipliers",
            "contact_gaps": "m",
            "slip_references_in": "m local tangential components",
            "slip_references_out": "m local tangential components",
            "tangential_displacements": "m local components",
            "trial_tangential_forces": "N local components",
            "tangential_forces": "N local components",
            "friction_capacities": "N",
            "coulomb_margins": "N",
            "gap_tolerances": "m",
            "tangent_stiffnesses": "N/m",
        },
    }
    (output / "capture-manifest.json").write_text(
        json.dumps(descriptor, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return validate_capture_archive(output, contract_sha256=contract_sha256)


def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@pytest.mark.parametrize("case", ["stick", "slip"])
def test_instrumented_m4_coulomb_ramp(monkeypatch, request, case):
    output_value = os.environ.get("QF_M4_STICK_DIAGNOSTIC_OUTPUT_DIR")
    if not output_value:
        pytest.skip("The registered DEVELOPMENT_AUTONOMOUS M4 scope supplies the archive directory")
    output = Path(output_value).resolve()
    output.mkdir(parents=True, exist_ok=True)
    contract_path = CONTRACT_DIR / f"m4-coulomb-{case}-contract-2026-11-24.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_sha256 = _sha256(contract_path)
    assert contract["nodeid"] == request.node.nodeid
    target_case = f"{case}_target"

    import solveur
    from scripts.run_wp08_area_supported_m4_diagnostic_r1_10 import _build_model, _case_gates
    from solveur.api.public import solve_model
    from solveur.contact import solver as contact_solver_module
    from solveur.contact.solver import FrictionlessActiveSetSolver
    from solveur.core.errors import NumericalConvergenceError
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter

    assert Path(solveur.__file__).resolve() == ROOT / "src/solveur/__init__.py"
    model, body, slave_nodes, area_by_node = _build_model(target_case)
    assert model.analysis.parameters.get("contact_restart_path") is None
    assert model.analysis.parameters.get("contact_checkpoint_path") is None
    assert tuple(model.contacts[0].slave_patch_nodes) == tuple(slave_nodes)
    connectivity = np.asarray([element.nodes for element in model.elements], dtype=np.int64)
    assert connectivity.shape == (6144, 4)

    telemetry = TelemetryEmitter(
        analysis_id=contract["scope"],
        analysis_type="linear_static",
        route="linear_static",
        sinks=(JsonlSink(output / "telemetry.jsonl", fsync=True),),
    )
    original_increment = FrictionlessActiveSetSolver._solve_friction_increment
    original_update = contact_solver_module._friction_update
    steps: list[dict] = []
    iteration_number = 0
    current_step = 0
    current_friction_tolerance = float(model.analysis.parameters["contact_friction_tolerance"])
    fields = {
        "displacements": [],
        "loads": [],
        "dof_map": None,
        "fixed_dof_indices": (),
        "contact_pressures": [],
        "contact_gaps": [],
        "contact_active": [],
        "contact_states": [],
        "slip_references_in": [],
        "slip_references_out": [],
        "tangential_displacements": [],
        "trial_tangential_forces": [],
        "tangential_forces": [],
        "friction_capacities": [],
        "coulomb_margins": [],
        "contact_descriptor_rows": [],
    }
    started = perf_counter()
    summary = {"status": "INCOMPLETE", "scope": contract["scope"], "nodeid": contract["nodeid"]}

    def observe_update(ops, active, displacement, pressures, refs, prior_states, *, friction_tolerance):
        nonlocal iteration_number
        states, forces, tangential_displacements, next_refs = original_update(
            ops, active, displacement, pressures, refs, prior_states, friction_tolerance=friction_tolerance
        )
        iteration_number += 1
        rows = _contact_observations(
            ops,
            active,
            displacement,
            pressures,
            refs,
            states,
            forces,
            tangential_displacements,
            configured_friction_tolerance=current_friction_tolerance,
        )
        for row, prior in zip(rows, prior_states, strict=True):
            row["prior_state"] = str(prior)
            row["iteration"] = iteration_number
        _append_jsonl(
            output / "friction-iterations.jsonl",
            {
                "step": current_step,
                "iteration": iteration_number,
                "active_indices": list(active),
                "contact_count": len(rows),
                "contacts": rows,
            },
        )
        return states, forces, tangential_displacements, next_refs

    def observe(dofs, k, loads, fixed, ops, refs, max_iterations, tolerance, *, telemetry=None, step=1):
        nonlocal current_step, current_friction_tolerance, iteration_number
        current_step = step
        current_friction_tolerance = float(tolerance)
        iteration_number = 0
        assert max_iterations == 25 and tolerance == 1e-9
        assert len(ops) == len(slave_nodes) == 81
        assert dofs.ndof == 3 * len(model.nodes)
        if not fields["contact_descriptor_rows"]:
            zero_u = np.zeros(dofs.ndof, dtype=float)
            zero_states = tuple("open" for _ in ops)
            zero_forces = np.zeros((len(ops), 2), dtype=float)
            zero_pressure = np.zeros(len(ops), dtype=float)
            rows = _contact_observations(
                ops,
                (),
                zero_u,
                zero_pressure,
                np.zeros((len(ops), 2), dtype=float),
                zero_states,
                zero_forces,
                np.zeros((len(ops), 2), dtype=float),
                configured_friction_tolerance=current_friction_tolerance,
            )
            fields["contact_descriptor_rows"] = rows
        if not fields["fixed_dof_indices"]:
            fields["fixed_dof_indices"] = tuple(int(item) for item in fixed)
        if fields["dof_map"] is None:
            fields["dof_map"] = np.asarray(
                [[dofs.index(node, axis) for axis in ("UX", "UY", "UZ")] for node in range(len(model.nodes))],
                dtype=np.int64,
            )
        if step == 1:
            assert not np.any(refs)
        monkeypatch.setattr(contact_solver_module, "_friction_update", observe_update)
        try:
            state = original_increment(
                dofs, k, loads, fixed, ops, refs, max_iterations, tolerance, telemetry=telemetry, step=step
            )
        except NumericalConvergenceError as exc:
            _append_jsonl(
                output / "steps.jsonl",
                {
                    "step": step,
                    "status": "SOLVER_REJECTED",
                    "diagnostics": exc.diagnostics or {},
                    "loads_sha256": _digest(loads),
                    "refs_in_sha256": _digest(refs),
                    "iteration_count": iteration_number,
                },
            )
            raise

        u = np.asarray(state.displacement, dtype=float)
        pressure = np.asarray(state.pressures, dtype=float)
        gap = np.asarray(state.gaps, dtype=float)
        active_mask = np.asarray([i in state.active for i in range(len(ops))], dtype=bool)
        relative = np.asarray(state.tangential_displacements, dtype=float)
        tangential_force = np.asarray(state.tangential_forces, dtype=float)
        trial = np.stack(
            [op.tangential_stiffness * (relative[i] - refs[i]) for i, op in enumerate(ops)]
        )
        capacity = np.asarray(
            [op.friction_coefficient * max(float(pressure[i]), 0.0) for i, op in enumerate(ops)], dtype=float
        )
        margins = np.linalg.norm(trial, axis=1) - capacity
        contact_rows = _contact_observations(
            ops,
            state.active,
            u,
            pressure,
            refs,
            state.states,
            tangential_force,
            relative,
            configured_friction_tolerance=float(tolerance),
        )
        external_minus_internal = np.asarray(loads - k @ u, dtype=float)
        dof_map = np.asarray(
            [[dofs.index(node, axis) for axis in ("UX", "UY", "UZ")] for node in range(len(model.nodes))],
            dtype=np.int64,
        )
        fixed_mask = np.zeros(dofs.ndof, dtype=bool)
        fixed_mask[np.asarray(fixed, dtype=np.int64)] = True
        normal_internal_force = -np.stack([op.vector for op in ops]).T @ pressure
        tangential_internal_force = np.einsum(
            "ij,ijk->k", tangential_force, np.stack([op.tangential_vectors for op in ops])
        )
        equilibrium_residual = np.asarray(
            k @ u + normal_internal_force + tangential_internal_force - loads,
            dtype=float,
        )
        free = equilibrium_residual[~fixed_mask]
        support_residual = equilibrium_residual
        nodal_load = np.asarray(loads, dtype=float).reshape(-1)
        normal_load = np.stack([op.vector for op in ops]).T @ pressure
        tangent_load = -np.einsum("ij,ijk->k", tangential_force, np.stack([op.tangential_vectors for op in ops]))
        support_residual = np.where(fixed_mask, support_residual, 0.0)
        nodal = (nodal_load + support_residual + normal_load + tangent_load)[dof_map]
        resultant = float(np.linalg.norm(nodal.sum(axis=0)))
        moment = float(np.linalg.norm(np.cross(model.nodes, nodal).sum(axis=0)))
        force_scale = max(float(np.linalg.norm(nodal_load[dof_map], axis=1).sum()), 1.0)
        moment_scale = force_scale * max(float(np.linalg.norm(model.nodes, axis=1).max()), 1.0)
        free_relative = float(np.linalg.norm(free) / max(np.linalg.norm(loads[~fixed_mask]), 1.0))
        target_factor = np.minimum(1.0, capacity / np.maximum(np.linalg.norm(trial, axis=1), np.finfo(float).tiny))
        coulomb_errors = np.linalg.norm(tangential_force - target_factor[:, None] * trial, axis=1)
        coulomb_scaled = float(np.max(coulomb_errors / np.maximum(capacity, 1.0), initial=0.0))
        counts = {name: int(state.states.count(name)) for name in ("open", "stick", "slip", "frictionless")}
        load_xyz = np.asarray(loads, dtype=float)[dof_map]
        record = {
            "step": step,
            "status": "INCREMENT_RETURNED",
            "load_sha256": _digest(loads),
            "refs_in_sha256": _digest(refs),
            "refs_out_sha256": _digest(state.slip_references),
            "applied_load_resultant_N": load_xyz.sum(axis=0).tolist(),
            "counts": counts,
            "states": list(state.states),
            "active_indices": list(state.active),
            "iterations": state.history,
            "max_gap_abs_m": float(np.max(np.abs(gap[active_mask]), initial=0.0)),
            "max_scaled_normal_complementarity_m": float(
                np.max(np.abs(gap * pressure) / np.maximum(np.abs(pressure), 1.0), initial=0.0)
            ),
            "max_penetration_m": float(max(0.0, -float(np.min(gap, initial=0.0)))),
            "min_active_normal_multiplier_N": (
                float(np.min(pressure[active_mask])) if np.any(active_mask) else None
            ),
            "max_coulomb_scaled_residual": coulomb_scaled,
            "max_abs_coulomb_margin_N": float(np.max(np.abs(margins), initial=0.0)),
            "max_free_equilibrium_inf_N": float(np.max(np.abs(free), initial=0.0)),
            "free_equilibrium_relative": free_relative,
            "global_force_residual_N": resultant,
            "global_force_residual_relative": float(resultant / force_scale),
            "global_moment_residual_Nm": moment,
            "global_moment_residual_relative": float(moment / moment_scale),
            "normal_multiplier_vs_load_minus_internal_inf_N": float(
                np.max(np.abs(external_minus_internal[
                    np.asarray([dofs.index(op.slave_node, "UX") for op in ops], dtype=np.int64)
                ] - pressure), initial=0.0)
            ),
            "max_active_gap_tolerance_m": float(max(op.tolerance for op in ops)),
            "configured_contact_friction_tolerance": float(tolerance),
            "contact_classification_rule": "positive capacity: margin <= eps * max(mu*p, 1 N); slip hysteresis uses the same band",
            "contacts": contact_rows,
            "elapsed_seconds": float(perf_counter() - started),
            "rss_after_solve_bytes": int(psutil.Process().memory_info().rss),
        }
        steps.append(record)
        _append_jsonl(output / "steps.jsonl", record)
        fields["displacements"].append(u.copy())
        fields["loads"].append(np.asarray(loads, dtype=float).copy())
        fields["contact_pressures"].append(pressure.copy())
        fields["contact_gaps"].append(gap.copy())
        fields["contact_active"].append(active_mask.copy())
        fields["contact_states"].append(np.asarray([STATE_CODE[item] for item in state.states], dtype=np.int8))
        fields["slip_references_in"].append(np.asarray(refs, dtype=float).copy())
        fields["slip_references_out"].append(np.asarray(state.slip_references, dtype=float).copy())
        fields["tangential_displacements"].append(relative.copy())
        fields["trial_tangential_forces"].append(trial.copy())
        fields["tangential_forces"].append(tangential_force.copy())
        fields["friction_capacities"].append(capacity.copy())
        fields["coulomb_margins"].append(margins.copy())
        return state

    monkeypatch.setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(observe))
    try:
        result = solve_model(model, telemetry=telemetry)
        payload = result.to_dict()
        gates = _case_gates(payload, target_case, body, slave_nodes, area_by_node)["gates"]
        per_step = len(steps) == 8 and all(
            row["max_gap_abs_m"] <= 1.0e-10
            and row["max_penetration_m"] <= 1.0e-10
            and row["min_active_normal_multiplier_N"] is not None
            and row["min_active_normal_multiplier_N"] >= -1.0e-10
            and row["max_scaled_normal_complementarity_m"] <= 1.0e-10
            and row["max_coulomb_scaled_residual"] <= 1.0e-9
            and row["free_equilibrium_relative"] <= 1.0e-8
            and row["global_force_residual_relative"] <= 1.0e-10
            and row["global_moment_residual_relative"] <= 1.0e-10
            for row in steps
        )
        summary = {
            "status": "RAMP_DIAGNOSTIC_PASS" if all(gates.values()) and per_step else "RAMP_GATE_FAILED",
            "scope": contract["scope"],
            "nodeid": contract["nodeid"],
            "contract_sha256": contract_sha256,
            "source_head": contract["source"]["product_source_commit"],
            "solver_source_tree": contract["source"]["solver_src_tree"],
            "historical_numeric_gates": gates,
            "per_step_gates": per_step,
            "returned_steps": len(steps),
            "final_product_equilibrium": {
                key: value
                for key, value in payload["audit"]["equilibrium"].items()
                if key in {"force_balance_relative_error", "moment_balance_relative_error", "free_relative_residual"}
            },
        }
    except NumericalConvergenceError as exc:
        summary = {
            "status": "SOLVER_REJECTED",
            "scope": contract["scope"],
            "nodeid": contract["nodeid"],
            "contract_sha256": contract_sha256,
            "source_head": contract["source"]["product_source_commit"],
            "solver_source_tree": contract["source"]["solver_src_tree"],
            "cause": (exc.diagnostics or {}).get("cause"),
            "message": str(exc),
            "returned_steps": len(steps),
        }
    finally:
        if fields["contact_descriptor_rows"]:
            archive_validation = _write_capture_archive(output, model, fields, contract, contract_sha256)
        else:
            archive_validation = {"status": "NO_CONTACT_ITERATION_CAPTURED"}
        summary.update(
            captured_steps=len(fields["displacements"]),
            elapsed_seconds=perf_counter() - started,
            archive_validation=archive_validation,
        )
        (output / "ramp-result.json").write_text(
            json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    assert summary["status"] == "RAMP_DIAGNOSTIC_PASS", json.dumps(summary, sort_keys=True)
