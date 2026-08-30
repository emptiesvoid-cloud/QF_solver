"""Targeted tests for the controlled 026-G12 lot-2 diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark_g12_lot2 import build_diagnostic_report, _same_domain_model, build_model, run_measured_case


def test_g12_lot2_contract_declares_unambiguous_nnz_and_timeout() -> None:
    contract = json.loads(Path("qualification/0_2_6/g12_lot2_contract.json").read_text(encoding="utf-8"))
    assert contract["contract_id"] == "026-G12-LOT2"
    assert contract["measurement_semantics"]["nnz"].startswith("global assembled")
    assert contract["scaling"]["timeout_seconds"] == 120
    assert contract["numeric_policy"]["numerical_regression_detected"].startswith("YES only")


def test_instrumented_case_separates_global_and_reduced_nnz() -> None:
    def factory():
        return build_model("TET4", 100)

    report = run_measured_case(factory, label="unit TET4", repetitions=1, warmup=False)
    row = report["measurements"][0]
    assert report["status"] == "PASS"
    assert report["finite_metrics"] is True
    assert row["global_stiffness_nnz"] == row["nnz"]
    assert row["global_stiffness_nnz"] > row["reduced_stiffness_nnz"]
    assert row["sparse_conversion_seconds"] >= 0.0
    assert row["global_matrix_storage_bytes"] > 0


def test_same_domain_comparison_preserves_physical_domain_pairing() -> None:
    tet4, tet4_meta = _same_domain_model("TET4")
    tet10, tet10_meta = _same_domain_model("TET10")
    hex8, hex8_meta = _same_domain_model("HEX8")
    hex20, hex20_meta = _same_domain_model("HEX20")
    assert tet4_meta["domain"] == tet10_meta["domain"] == "unit_tetrahedron"
    assert hex8_meta["domain"] == hex20_meta["domain"] == "unit_cube"
    assert tet4.node_count == 4 and tet10.node_count == 10
    assert hex8.node_count == 8 and hex20.node_count == 20


def test_diagnostic_aggregate_preserves_completed_measurement_scope() -> None:
    report = build_diagnostic_report()
    assert report["status"] == "PASS"
    assert report["baseline_sha"] == "4dc8af83d8d45d6a4d61f242aa6b1f974d87bdb3"
    assert report["harness_audit"]["harness_valid"] is True
    assert report["harness_audit"]["nnz_measurement_valid"] is True
    assert report["harness_audit"]["lot1_10k_resource_observation"]["classification"] == "HARNESS_ERROR"
    assert len(report["scaling"]["completed_rows"]) == 4
    assert report["scaling"]["completed_rows"][-1]["actual_dofs"] == 10125
    assert report["numerical_regression"]["detected"] == "NO"
    assert report["bottleneck_classification"]["primary"] == "PYTHON_ASSEMBLY"
    assert all(candidate["implemented"] is False for candidate in report["optimization_candidates"])
