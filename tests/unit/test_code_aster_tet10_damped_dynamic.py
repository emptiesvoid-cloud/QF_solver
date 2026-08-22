"""Contract tests for the TET10 damped external campaign."""

from __future__ import annotations

import numpy as np

from solveur.verification.code_aster_tet10_damped_cylinder_dynamic import (
    CodeAsterTet10DampedCylinderDynamicsCampaign,
)
from solveur.verification.code_aster_tet10_dynamic import (
    _modal_analysis,
    _pulse_table,
    code_aster_tet10_dynamic_comm,
)


def test_damped_campaign_declares_a_bounded_target() -> None:
    campaign = CodeAsterTet10DampedCylinderDynamicsCampaign("results/test-damped")
    parameters = campaign._damping_parameters(100.0)
    assert parameters["target_modal_damping_ratio"] == 0.02
    assert parameters["rayleigh_alpha_s_inv"] > 0.0
    assert parameters["rayleigh_beta_s"] == 0.0


def test_damped_tet10_deck_contains_mass_rayleigh_matrix() -> None:
    tip = np.asarray([0, 1, 2], dtype=int)
    deck = code_aster_tet10_dynamic_comm(
        tip,
        _pulse_table(0.001, 4),
        [10.0, 20.0],
        rayleigh_alpha=0.5,
    )
    assert "COMB_MATR_ASSE" in deck
    assert "MATR_ASSE=mass" in deck
    assert "MATR_AMOR=damping" in deck
    assert 'SCHEMA="NEWMARK"' in deck


def test_damped_campaign_keeps_same_mesh_modal_model(tmp_path) -> None:
    campaign = CodeAsterTet10DampedCylinderDynamicsCampaign(tmp_path, mesh_size=0.80)
    model, _, _ = campaign._model(0.80, _modal_analysis())
    assert {element.type for element in model.elements} == {"TET10"}

