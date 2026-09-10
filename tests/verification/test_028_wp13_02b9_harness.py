"""Targeted WP13-02B9 harness guards; no full Newmark campaign."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import run_wp13_02b5_newmark_v2 as b5  # noqa: E402
import wp13_02b9_harness as b9  # noqa: E402


CONTRACT = json.loads(
    (ROOT / "qualification/0_2_8/wp13_02b4_newmark_v2_contract.json").read_text(
        encoding="utf-8"
    )
)


def test_b9_reads_replay_and_history_fields_from_frozen_contract() -> None:
    info = b9.validate_contract_for_harness(CONTRACT)
    assert info["contract_blob_sha"] == b9.CONTRACT_BLOB
    assert info["replay_fields"] == list(CONTRACT["replay"]["fields"])
    assert info["gate_values"]["interfaces"] == CONTRACT["interfaces"]
    assert info["gate_values"]["replay"]["tolerance"] == CONTRACT["replay"]["tolerance"]
    assert "residual full vector" in info["history_fields"]
    assert "family kinetic/strain energies" in info["history_fields"]


def test_b9_executes_all_failure_categories_through_runtime() -> None:
    base = b5.b2.build(1)
    reference = b5.b2.reference(base)
    failures = b9.run_failure_contract(base, reference)
    assert set(failures) == {
        "invalid_dt",
        "missing_mass",
        "unsupported_damping",
        "unsupported_time_load",
        "invalid_initial_conditions",
        "invalid_mixed_interface",
        "unsupported_family",
    }
    assert all(item["case_executed"] for item in failures.values())
    assert all(item["status"] == "REJECTED" for item in failures.values())
    assert all(item["pass"] for item in failures.values())
    assert failures["unsupported_family"]["expected_route_status"] == "UNSUPPORTED_ROUTE"


def test_b9_continuity_is_derived_from_family_fields() -> None:
    base = b5.b2.build(1)
    reference = b5.b2.reference(base)
    captured = b5.b2.capture(base, reference, 20)
    reference["current_time"] = captured["time"]
    run = b5.enrich_run(reference, captured)
    measured = b9.measured_interface_evidence(reference, run)
    assert all(values["continuity_relative"] == 0.0 for values in measured.values())

    perturbed = run["displacement"].copy()
    wedge_nodes = sorted(
        {
            node
            for item in base.elements
            if item.type == "WEDGE6"
            for node in item.nodes
        }
        & {
            node
            for item in base.elements
            if item.type == "HEX8"
            for node in item.nodes
        }
    )
    wedge_ids = [
        index
        for node in wedge_nodes
        for index in reference["dofs"].node_indices(node, ("UX", "UY", "UZ"))
    ]
    perturbed[:, wedge_ids[0]] += 1.0e-6
    family_histories = {
        family: {"u": run["displacement"], "v": run["velocity"], "a": run["acceleration"]}
        for family in b9.FAMILIES
    }
    family_histories["WEDGE6"]["u"] = perturbed
    changed = b9.measured_interface_evidence(
        reference, run, family_histories=family_histories
    )
    assert changed["WEDGE6_HEX8"]["continuity_relative"] > 0.0


def test_b9_replay_comparator_covers_full_contract_fields() -> None:
    time = np.asarray([0.0, 1.0])
    base = {
        "time": time,
        "omega": 2.0,
        "ustar": 1.0,
        "fstar": 1.0,
        "e0": 1.0,
        "q": np.asarray([1.0, 0.5]),
        "solver_status": "PASS",
        "iterations_total": 2,
    }
    for field in b9.REPLAY_FIELD_MAP.values():
        base[field] = np.ones((2, 2)) if field in {"displacement", "velocity", "acceleration", "residual_vector", "reactions"} else np.ones(2)
    result = b9.compare_replay_fields(base, dict(base), CONTRACT)
    assert result["all_fields_pass"] is True
    changed = dict(base)
    changed["residual_vector"] = base["residual_vector"].copy()
    changed["residual_vector"][1, 0] = 1.0e-2
    assert b9.compare_replay_fields(base, changed, CONTRACT)["all_fields_pass"] is False


def test_b9_conditioning_prechecks_execute_against_contract() -> None:
    base = b5.b2.build(1)
    reference = b5.b2.reference(base)
    checks = b9.conditioning_prechecks(reference, CONTRACT)
    assert checks["pass"] is True
    assert checks["global_condition_number"] == "NOT_COMPUTED_BY_CONTRACT"
    assert checks["limits_from_contract"]["max_aspect_ratio"] == 4.0
