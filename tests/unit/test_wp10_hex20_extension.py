"""Static checks for the bounded WP10 HEX20 extension."""

import json
from pathlib import Path

import scripts.run_wp10_tet4_coupled as base


ROOT = Path(__file__).resolve().parents[2]


def test_hex20_extension_contract_is_separate() -> None:
    contract = json.loads(
        (ROOT / "qualification" / "0_2_9" / "wp10_hex20_extension_contract.json").read_text(
            encoding="utf-8"
        )
    )
    assert contract["extension"]["element"] == "HEX20"
    assert contract["extension"]["runner"] == "scripts/run_wp10_hex20_coupled.py"
    assert contract["fail_closed"] is True


def test_hex20_model_uses_only_hex20_elements(monkeypatch) -> None:
    monkeypatch.setattr(base, "ELEMENT_TYPE", "HEX20")
    model, _ = base._model(with_contact=True)
    assert {element.type for element in model.elements} == {"HEX20"}
    assert model.analysis.parameters["kinematics"] == "corotational_j2"
    assert model.analysis.parameters["contact_mode"] == "penalty"
    assert len(model.contacts) == 1
