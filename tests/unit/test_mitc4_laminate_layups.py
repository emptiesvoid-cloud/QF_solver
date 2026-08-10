"""Contracts for the three-layup MITC4 laminate dynamic campaign."""

from solveur.verification.code_aster_mitc4_laminate_dynamic import code_aster_dynamic_comm
from solveur.verification.mitc4_laminate_dynamic import Mitc4LaminateDynamicStudy
from solveur.verification.mitc4_laminate_layups import LAYUP_CASES, _checks


def test_layup_campaign_has_three_symmetric_four_ply_cases_and_one_damped_case() -> None:
    assert len(LAYUP_CASES) == 3
    assert sum(float(case["damping_ratio"]) > 0.0 for case in LAYUP_CASES) == 1
    for case in LAYUP_CASES:
        layup = tuple(case["layup_deg"])
        assert len(layup) == 4
        assert layup == tuple(reversed(layup))


def test_off_axis_layup_reaches_the_mitc4_material_definition() -> None:
    model, _ = Mitc4LaminateDynamicStudy(mesh=(4, 1), layup=(45.0, -45.0, -45.0, 45.0)).build_model()
    assert [ply["angle_deg"] for ply in model.materials["laminate"]["plies"]] == [45.0, -45.0, -45.0, 45.0]


def test_damped_code_aster_deck_uses_mass_proportional_damping_and_layup() -> None:
    deck = code_aster_dynamic_comm(
        2,
        1.0e-4,
        [{"time": 0.0, "factor": 0.0}, {"time": 1.0e-4, "factor": 1.0}],
        [10.0],
        layup=(0.0, 45.0, 45.0, 0.0),
        rayleigh_alpha=0.5,
    )
    assert "ORIENTATION=45.0" in deck
    assert "COMB_MATR_ASSE" in deck
    assert "MATR_AMOR=damping" in deck


def test_aggregate_checks_keep_each_case_identifier() -> None:
    checks = _checks(
        [{"id": "angle_ply_45", "summary": {"checks": [{"id": "newmark_damped_decay", "value": 0.5, "limit": 0.95, "status": "PASS"}]}}]
    )
    assert checks[0]["id"] == "angle_ply_45::newmark_damped_decay"
