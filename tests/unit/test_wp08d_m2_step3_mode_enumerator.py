"""Regression coverage for the independent WP08-D M2 step-3 forensic path."""

from __future__ import annotations

import inspect
from pathlib import Path

from scripts import diagnose_wp08d_m2_step3_modes as diagnostic
from scripts.wp08d_phase1_common import build_production_model, ensure_workspace_source_import
from solveur.api.public import solve_model


def _checkpoint() -> Path:
    return Path("qualification/0_2_9/wp08d_phase1_mixed_open_active_slip_step2_reconstruction/M2/checkpoint_step_002.json")


def test_enumerator_covers_every_mask_without_a_production_contact_import() -> None:
    assert diagnostic.mode_labels() == ("SSS", "SSK", "SKS", "SKK", "KSS", "KSK", "KKS", "KKK")
    assert "solveur.contact" not in inspect.getsource(diagnostic)


def test_independent_mode_enumerator_finds_unique_stick_solution() -> None:
    report = diagnostic.enumerate_modes(_checkpoint())

    assert report["production_contact_implementation_called"] is False
    assert report["admissible_modes"] == ["SSS"]
    assert report["admissible_mode_count"] == 1


def test_normal_set_change_reseeds_stick_and_recovers_frozen_m2_step3() -> None:
    """A retained pair must receive a fresh stick trial after neighbours open."""

    model = build_production_model("M2", diagnostic_load_step_limit=3)
    result = solve_model(model, enforce_policy=False).to_dict()
    step = result["solver"]["contact"]["load_steps"][-1]

    assert step["step"] == 3
    assert step["states"] == [
        "open", "open", "open", "stick", "open", "open",
        "open", "stick", "open", "open", "open", "stick",
    ]


def test_runner_source_selector_points_at_the_checkout() -> None:
    source = ensure_workspace_source_import()
    assert (source / "solveur").is_dir()
