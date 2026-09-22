from __future__ import annotations

import json
from typing import cast

from scripts import run_wp10_tet10_surface_r2 as runner


def test_r2_contract_covers_m1_m2_m3() -> None:
    contract = json.loads(runner.CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "R2_EXECUTION_AUTHORIZED"
    assert set(contract["m1"]["levels"]) == {"H1", "H2", "H3"}
    assert contract["m2"]["level"] == "H3"
    assert contract["m3"]["type"] == "fresh_process_replay_of_M2"


def test_r2_m1_model_preserves_surface_load_and_has_no_contact() -> None:
    model, slave, metadata = runner._model(4, with_contact=False)
    assert slave in range(model.node_count)
    assert not model.contacts
    assert metadata["total_area"] == 1.0
    assert model.distributed_loads


def test_r2_m2_model_adds_frozen_frictionless_penalty_contact() -> None:
    model, slave, metadata = runner._model(4, with_contact=True)
    assert model.contacts
    contact = model.contacts[0]
    assert contact.slave_node == slave
    assert contact.friction_coefficient == 0.0
    contact_metadata = cast(dict[str, object], metadata["contact"])
    assert contact_metadata["plane_x"] == runner.PLANE_X
    assert contact_metadata["penalty"] == runner.PENALTY
