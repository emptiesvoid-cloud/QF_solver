"""Regression tests for contact-event line-search diagnostics and refinement."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.analyses.geometric_nonlinear import _PenaltyContactAssembly
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.iteration import _line_search_assembly_with_result
from solveur.core.nonlinear.robustness import UnifiedNonlinearRobustnessController
from solveur.core.model import FiniteElementModel
from scripts.wp07d_execution_binding import (
    CONTACT_REQUAL_R2_3_ARTIFACT_ID,
    contact_requalification_profile,
)


class _SyntheticPenaltyContactAssembly:
    ndof = 1

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        del tangent_required
        alpha = float(displacement[0])
        residual = 0.5 if np.isclose(alpha, 0.175, rtol=0.0, atol=1.0e-14) else 2.0
        return np.asarray([residual]), None

    def diagnostics_snapshot(self) -> dict[str, object]:
        return {
            "active_contacts": [0],
            "gaps": [-0.075],
        }

    def line_search_activation_factors(
        self, displacement: np.ndarray, direction: np.ndarray
    ) -> tuple[float, ...]:
        del displacement, direction
        return (0.1,)


def test_penalty_event_refinement_uses_existing_merit_acceptance_rule() -> None:
    assembly = _SyntheticPenaltyContactAssembly()
    controller = UnifiedNonlinearRobustnessController(
        policy_source="COMPATIBILITY_ADAPTER",
        min_alpha=0.0,
        max_reductions=2,
        line_search_enabled=True,
    )

    result = _line_search_assembly_with_result(
        assembly,
        np.zeros(1),
        np.asarray([0]),
        np.asarray([1.0]),
        np.zeros(1),
        1.0,
        controller=controller,
    )

    assert result.accepted is True
    assert result.factor == 0.175
    assert result.merit_history[-1] == 0.5
    assert result.supplemental_trials == 2
    assert result.trial_diagnostics[-1]["candidate_phase"] == "contact_event_refinement"
    assert result.trial_diagnostics[-1]["contact_activation_factor_summary"] == {
        "count": 1,
        "minimum": 0.1,
        "median": 0.1,
        "maximum": 0.1,
    }
    assert result.trial_diagnostics[-1]["base_assembly"] == {
        "active_contacts": [0],
        "gaps": [-0.075],
    }
    assert result.trial_diagnostics[-1]["trial_assembly"] == {
        "active_contacts": [0],
        "gaps": [-0.075],
    }


def test_contact_event_refinement_does_not_change_standard_search_without_events() -> None:
    class _NoEventAssembly(_SyntheticPenaltyContactAssembly):
        def line_search_activation_factors(
            self, displacement: np.ndarray, direction: np.ndarray
        ) -> tuple[float, ...]:
            del displacement, direction
            return ()

    controller = UnifiedNonlinearRobustnessController(
        policy_source="COMPATIBILITY_ADAPTER",
        min_alpha=0.0,
        max_reductions=2,
        line_search_enabled=True,
    )
    with pytest.raises(NumericalConvergenceError) as error:
        _line_search_assembly_with_result(
            _NoEventAssembly(),
            np.zeros(1),
            np.asarray([0]),
            np.asarray([1.0]),
            np.zeros(1),
            1.0,
            controller=controller,
        )

    assert error.value.diagnostics["supplemental_trials"] == 0
    assert len(error.value.diagnostics["merit_history"]) == 3
    assert all(
        "candidate_phase" not in item
        for item in error.value.diagnostics["trial_diagnostics"]
    )


def test_fixed_search_penalty_predicts_exact_gap_activation_factor() -> None:
    model = FiniteElementModel.from_raw(
        nodes=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.25, 0.25, 0.1],
        ],
        elements=[],
        materials={},
        fixed_dofs=[],
        loads=[],
        contacts=[{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"contact_mode": "penalty", "contact_search_mode": "initial"},
        },
    )
    dofs = model.dof_manager()
    direction = np.zeros(dofs.ndof)
    direction[dofs.index(3, "UZ")] = -1.0
    assembly = _PenaltyContactAssembly(model, dofs)

    factors = assembly.line_search_activation_factors(np.zeros(dofs.ndof), direction)

    assert factors == pytest.approx((0.1,), rel=0.0, abs=1.0e-15)


def test_r2_3_profile_uses_new_non_overwriting_evidence_roots() -> None:
    profile = contact_requalification_profile(CONTACT_REQUAL_R2_3_ARTIFACT_ID)

    assert profile["run_root"].as_posix().endswith("runs_r2_5")
    assert profile["authorization_root"].as_posix().endswith("authorizations_r2_5")
    assert profile["replay_gate_path"].as_posix().endswith("replay_authorization_gate_r2_5.json")
    assert profile["final_report"].name == "analysis_final_r2_5.json"
