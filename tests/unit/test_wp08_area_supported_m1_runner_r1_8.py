"""Model-construction tests for the prospective M1 diagnostic (no solve)."""

from __future__ import annotations

import pytest

import numpy as np

from scripts.run_wp08_area_supported_m1_diagnostic import (
    _json_safe,
    _raw_contact_arrays,
    build_m1_model,
)
from scripts.run_wp08_area_supported_m1_diagnostic_r1_8 import ARTIFACT_ID as R1_8_ARTIFACT_ID
from scripts.run_wp08_area_supported_m1_diagnostic_r1_8 import _contract as r1_8_contract
from scripts.run_wp08_area_supported_m1_diagnostic_r1_8 import freeze as r1_8_freeze


@pytest.mark.parametrize("case", ["stick_target", "slip_target"])
def test_m1_model_uses_full_2d_slave_patch_and_frozen_eight_step_path(case: str) -> None:
    model = build_m1_model(case)
    assert model.node_count == 16
    assert len(model.elements) == 12
    assert len(model.contacts) == 1
    contact = model.contacts[0]
    assert len(contact.slave_nodes) == 4
    assert len(contact.slave_patch_faces or ()) == 2
    assert contact.tangential_stiffness_mode == "surface"
    assert model.analysis.parameters["contact_search_mode"] == "initial"
    history = model.analysis.parameters["contact_load_history"]
    assert len(history) == 8
    assert len({len(row) for row in history}) == 1


def test_m1_model_keeps_contact_free_face_separate_from_fixed_face() -> None:
    model = build_m1_model("stick_target")
    fixed = {condition.node for condition in model.fixed_dofs}
    slave = set(model.contacts[0].slave_nodes)
    assert slave.isdisjoint(fixed)


def test_strict_json_conversion_handles_numpy_boolean_and_nested_arrays() -> None:
    converted = _json_safe({"gate": np.bool_(True), "values": np.asarray([1.0, 2.0])})
    assert converted == {"gate": True, "values": [1.0, 2.0]}
    assert type(converted["gate"]) is bool


def test_m1_raw_schema_contains_refinement_fields_and_global_contact_forces() -> None:
    arrays = _raw_contact_arrays(
        body=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        master=np.asarray([[1.1, 0.0, 0.0]]),
        slave_nodes=(1,),
        active_nodes=[1],
        area_by_node={1: 0.5},
        rows=[
            {
                "slave_node": 1,
                "active": True,
                "pressure": 2.0,
                "gap": 0.0,
                "normal": [-1.0, 0.0, 0.0],
                "tangential_state": "slip",
                "tangential_force": [3.0, 4.0],
                "tangent_one": [0.0, 1.0, 0.0],
                "tangent_two": [0.0, 0.0, 1.0],
                "reference_slave_area": 0.5,
            }
        ],
        displacement=np.zeros(9),
        equilibrium={
            "reaction_resultant": [0.0, 0.0, 0.0],
            "reaction_moment_about_origin": [0.0, 0.0, 0.0],
            "force_balance_relative_error": 0.0,
            "moment_balance_relative_error": 0.0,
        },
    )

    assert arrays["node_coordinates"].shape == (3, 3)
    assert arrays["body_node_count"].tolist() == [2]
    assert arrays["contact_normal_force"].tolist() == [[2.0, 0.0, 0.0]]
    assert arrays["contact_tangential_force_global"].tolist() == [[0.0, 3.0, 4.0]]
    assert arrays["contact_tangential_force_local"].tolist() == [[3.0, 4.0]]


def test_m1_raw_schema_fails_closed_when_equilibrium_observables_are_missing() -> None:
    with pytest.raises(ValueError, match="missing required equilibrium fields"):
        _raw_contact_arrays(
            body=np.empty((0, 3)),
            master=np.empty((0, 3)),
            slave_nodes=(),
            active_nodes=[],
            area_by_node={},
            rows=[],
            displacement=np.empty(0),
            equilibrium={},
        )


def test_r1_8_contract_binds_the_sparse_root_implementation_without_parameter_changes(tmp_path) -> None:
    contract, inventory, source_digest = r1_8_contract(tmp_path)

    assert R1_8_ARTIFACT_ID.endswith("R1.8")
    assert contract["artifact_id"] == R1_8_ARTIFACT_ID
    assert "normal active set" in contract["solver_implementation_revision"]
    assert "cycle detection" in contract["solver_implementation_revision"]
    assert "geometry, mesh, material, loads" in contract["implementation_scope"]
    assert contract["thresholds_changed"] is False
    assert contract["owner_authorization"]["execution_authorized"] is False
    assert contract["m2_m3_authorized"] is False
    assert contract["source_bundle_sha256"] == source_digest
    assert contract["source_file_count"] == len(inventory)


def test_r1_8_freeze_requires_explicit_owner_authorization(tmp_path) -> None:
    output = tmp_path / "not-authorized"

    with pytest.raises(PermissionError, match="explicit Owner authorization"):
        r1_8_freeze(output)

    assert not output.exists()
