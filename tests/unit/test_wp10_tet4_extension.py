"""Static contract and model-construction checks for the WP10 TET4 extension."""

import json
from pathlib import Path

from scripts.run_wp10_tet4_coupled import ELEMENT_TYPE, _model


ROOT = Path(__file__).resolve().parents[2]


def test_wp10_tet4_contract_is_separate_from_hex8() -> None:
    contract = json.loads(
        (ROOT / "qualification" / "0_2_9" / "wp10_extension_contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["first_extension"] == "TET4"
    assert contract["base_wp10_scope"]["element"] == "HEX8"
    assert contract["runner"] == "scripts/run_wp10_tet4_coupled.py"
    assert contract["fail_closed"] is True


def test_wp10_tet4_model_route_and_contact_are_explicit() -> None:
    model, slave = _model(with_contact=True)
    parameters = model.analysis.parameters
    assert ELEMENT_TYPE == "TET4"
    assert {element.type for element in model.elements} == {"TET4"}
    assert parameters["kinematics"] == "corotational_j2"
    assert parameters["contact_mode"] == "penalty"
    assert parameters["contact_search_mode"] == "initial"
    assert parameters["contact_finite_sliding"] is False
    assert slave in {contact.slave_node for contact in model.contacts}


def test_wp10_tet4_model_without_contact_has_no_contact_route() -> None:
    model, _ = _model(with_contact=False)
    assert len(model.contacts) == 0
    assert model.analysis.parameters["contact_mode"] == "none"
