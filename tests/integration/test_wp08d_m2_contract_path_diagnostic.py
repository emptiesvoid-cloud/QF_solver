"""Diagnostic regression for the bounded WP08-D M2 friction path.

This test runs the frozen small M2 model in memory to exercise the production
path. It creates no qualification artifacts and awards no formal points.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from scripts import run_wp08d_independent_reference as independent_reference
from scripts.wp08d_phase1_common import build_production_model, extract_observables, read_contract
from solveur.core.solver import LinearStaticSolver
from solveur.core.telemetry import EventType, MemorySink, TelemetryEmitter


def test_wp08d_m2_contract_path_converges_on_current_source() -> None:
    model = build_production_model("M2")
    frozen_path = np.asarray(
        [
            [
                float(row["normal_factor"]),
                float(row["tangential_factor"]),
            ]
            for row in read_contract()["friction"]["load_path"]
        ],
        dtype=float,
    )
    expected_path = np.asarray(
        [
            [1.0, 0.0],
            [1.0, 0.25],
            [1.0, 0.75],
            [1.0, 1.0],
            [1.0, 1.25],
            [1.0, 0.25],
            [1.0, -0.5],
        ],
        dtype=float,
    )
    np.testing.assert_array_equal(frozen_path, expected_path)
    component_history = np.asarray(model.analysis.parameters["contact_load_history"], dtype=float)
    assert component_history.shape[0] == len(expected_path)
    assert component_history.shape[1] % 2 == 0
    actual_pairs = component_history.reshape(len(expected_path), -1, 2)
    expected_component_path = np.tile(expected_path[:, None, ::-1], (1, actual_pairs.shape[1], 1))
    np.testing.assert_array_equal(actual_pairs, expected_component_path)

    sink = MemorySink()
    telemetry = TelemetryEmitter("wp08d-m2-diagnostic", "linear_static", "linear_static", sink)

    result = LinearStaticSolver().solve(model, telemetry=telemetry)

    assert result.status == "PASS"
    contact = result.solver["contact"]
    assert contact["converged"] is True
    assert contact["active_contact_count"] == 3
    accepted_steps = [event.step for event in sink.events if event.event_type is EventType.STEP_ACCEPTED]
    assert accepted_steps == list(range(1, 8))
    hybrid_step_five = [
        event
        for event in sink.events
        if event.event_type is EventType.CONTACT_STATE
        and event.step == 5
        and event.metrics.get("phase") == "active_slip_hybrid_subset"
    ]
    assert len(hybrid_step_five) == 1
    assert hybrid_step_five[0].metrics["active_contacts"] == [3, 7, 11]
    assert hybrid_step_five[0].metrics["stick_frictional_contacts"] == [3, 7]
    assert hybrid_step_five[0].metrics["slip_frictional_contacts"] == [11]
    assert hybrid_step_five[0].metrics["tangential_unknown_dimension"] == 2
    assert not any(event.event_type is EventType.STEP_REJECTED for event in sink.events)

    reference_model = independent_reference._model("M2")
    references: np.ndarray = np.zeros((len(reference_model["slave_nodes"]), 2), dtype=float)
    cumulative_dissipation = 0.0
    reference_steps: list[dict[str, Any]] = []
    for normal_factor, tangential_factor in independent_reference.FROZEN_LOAD_PATH:
        reference_load = (
            normal_factor * np.asarray(reference_model["normal_load"])
            + tangential_factor * np.asarray(reference_model["tangent_load"])
        )
        previous_references = references.copy()
        reference_step = independent_reference._solve_increment(reference_model, reference_load, references)
        references = np.asarray(reference_step["references"], dtype=float).copy()
        dissipation = max(float(np.sum(np.asarray(reference_step["forces"]) * (references - previous_references))), 0.0)
        cumulative_dissipation += dissipation
        reference_step["dissipation"] = cumulative_dissipation
        reference_steps.append(reference_step)

    reference_final = reference_steps[-1]
    reference_load_final = (
        independent_reference.FROZEN_LOAD_PATH[-1][0] * np.asarray(reference_model["normal_load_full"])
        + independent_reference.FROZEN_LOAD_PATH[-1][1] * np.asarray(reference_model["tangent_load_full"])
    )
    reference_observables = independent_reference._reference_observables(
        reference_model,
        reference_final,
        reference_load_final,
    )
    deltas = independent_reference._deltas(reference_observables, extract_observables(result))

    assert reference_steps[4]["strategy"] == "hybrid_stick_slip_root"
    assert reference_steps[4]["root_diagnostics"]["root_residual_inf"] <= 1.0e-9
    assert deltas["displacement"] <= 0.02
    assert deltas["reaction"] <= 0.02
    assert deltas["moment"] <= 0.02
    assert deltas["normal_contact"] <= 0.03
    assert deltas["tangential_contact"] <= 0.03
    assert deltas["dissipation"] <= 0.05
