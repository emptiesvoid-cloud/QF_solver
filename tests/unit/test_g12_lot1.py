"""Unit tests for the controlled 026-G12 lot-1 benchmark infrastructure."""

from __future__ import annotations

import json

from scripts.benchmark_g12_lot1 import build_model, run_case


def test_g12_contract_is_machine_readable() -> None:
    from pathlib import Path

    contract = json.loads(Path("qualification/0_2_6/g12_lot1_contract.json").read_text(encoding="utf-8"))
    assert contract["contract_id"] == "026-G12-LOT1"
    assert contract["scope"]["families"] == ["TET4", "HEX8", "TET10", "HEX20"]
    assert contract["repetition_policy"]["measured_repetitions"] == 3
    assert "peak_rss_bytes" in contract["metrics"]["required"]


def test_g12_builders_have_expected_real_element_families() -> None:
    for family in ("TET4", "HEX8", "TET10", "HEX20"):
        model, metadata = build_model(family, 100)
        assert model.elements
        assert {element.type for element in model.elements} == {family}
        assert metadata["topology"]


def test_g12_small_case_records_reproducible_finite_metrics() -> None:
    report = run_case("TET4", 100, repetitions=2)
    assert report["deterministic"] is True
    assert report["finite_metrics"] is True
    assert report["max_relative_residual_norm"] <= 1.0e-8
    assert len(report["measured_repetitions"]) == 2
