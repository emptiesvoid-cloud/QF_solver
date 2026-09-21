from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp10_hex8_coupled import _model


def test_wp10_hex8_models_are_explicitly_bounded() -> None:
    open_model, _ = _model(False)
    contact_model, slave = _model(True)

    assert len(open_model.elements) == 1
    assert len(contact_model.elements) == 1
    assert contact_model.analysis.parameters["kinematics"] == "corotational_j2"
    assert contact_model.analysis.parameters["contact_search_mode"] == "initial"
    assert contact_model.analysis.parameters["contact_finite_sliding"] is False
    assert len(contact_model.contacts) == 1
    assert slave in contact_model.contacts[0].slave_nodes


def test_wp10_contract_is_preparation_only() -> None:
    root = Path(__file__).resolve().parents[2]
    contract = json.loads(
        (root / "qualification/0_2_9/wp10_preparation_contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["status"] == "FROZEN_EXECUTION"
    assert contract["structural_solves_allowed"] is True
    assert contract["official_points"] == "0/6"
